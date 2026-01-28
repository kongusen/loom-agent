"""
记忆系统核心实现 - 基于Task的分层存储

基于A4公理（记忆层次公理）：Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4

核心改动：
- L1: 存储完整Task对象（循环缓冲区）
- L2: 存储重要Task对象（按重要性排序）
- L3: 存储TaskSummary（压缩表示）
- L4: 向量存储（语义检索）
"""

from typing import TYPE_CHECKING, Any

from .fact_extractor import FactExtractor
from .layers import CircularBufferLayer, PriorityQueueLayer
from .types import Fact, MemoryTier, TaskSummary

if TYPE_CHECKING:
    from loom.protocol import Task

    from .vector_store import VectorStoreProvider


class LoomMemory:
    """
    基于Task的分层记忆系统

    L1: 完整Task对象（循环缓冲区，最近50个）
    L2: 会话工作记忆（按重要性排序，最多100个）
    L3: 会话摘要（最多500个）
    L4: 跨会话向量记忆（无限）
    """

    def __init__(
        self,
        node_id: str,
        max_l1_size: int = 50,
        max_l2_size: int = 100,
        max_l3_size: int = 500,
        enable_l4_vectorization: bool = True,
        max_task_index_size: int = 1000,
        max_fact_index_size: int = 5000,
    ):
        self.node_id = node_id
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size
        self.max_l3_size = max_l3_size
        self.enable_l4_vectorization = enable_l4_vectorization
        self.max_task_index_size = max_task_index_size
        self.max_fact_index_size = max_fact_index_size

        # L1: 完整Task（使用CircularBufferLayer）
        self._l1_layer = CircularBufferLayer(max_size=max_l1_size)

        # L2: 重要Task（使用PriorityQueueLayer）
        self._l2_layer = PriorityQueueLayer(max_size=max_l2_size)

        # L3: Task摘要
        self._l3_summaries: list[TaskSummary] = []

        # L4: 向量存储（延迟初始化）
        self._l4_vector_store: "VectorStoreProvider | None" = None
        self.embedding_provider = None

        # Task索引（用于快速查找）
        self._task_index: dict[str, "Task"] = {}

        # Fact索引（用于快速查找）
        self._fact_index: dict[str, Fact] = {}

        # 事实提取器
        self.fact_extractor = FactExtractor()

        # 设置L1驱逐回调（自动清理索引）
        self._l1_layer.on_eviction(self._on_l1_eviction)

    # ==================== L1管理 ====================

    @property
    def _l1_tasks(self) -> list["Task"]:
        """向后兼容：返回L1中的所有Task"""
        return list(self._l1_layer._buffer)

    def _on_l1_eviction(self, task: "Task") -> None:
        """L1驱逐回调：自动清理索引"""
        self._task_index.pop(task.task_id, None)

    def add_task(self, task: "Task", tier: MemoryTier = MemoryTier.L1_RAW_IO) -> None:
        """
        添加Task到指定层级

        Args:
            task: Task对象
            tier: 目标层级（默认L1）
        """
        # 添加到索引
        self._task_index[task.task_id] = task

        # 定期清理索引（防止内存泄漏）
        if len(self._task_index) > self.max_task_index_size:
            self._cleanup_task_index()

        # 根据层级分发
        if tier == MemoryTier.L1_RAW_IO:
            self._add_to_l1(task)
        elif tier == MemoryTier.L2_WORKING:
            self._add_to_l2(task)

    def _add_to_l1(self, task: "Task") -> None:
        """添加到L1循环缓冲区（同步版本）"""
        # 检查是否会发生驱逐
        if len(self._l1_layer._buffer) == self._l1_layer._buffer.maxlen:
            evicted = self._l1_layer._buffer[0]
            # 触发驱逐回调
            for callback in self._l1_layer._eviction_callbacks:
                callback(evicted)

        # 添加任务
        self._l1_layer._buffer.append(task)

    def get_l1_tasks(self, limit: int = 10, session_id: str | None = None) -> list["Task"]:
        """
        获取L1最近的Task

        Args:
            limit: 返回数量限制
            session_id: 可选的会话过滤

        Returns:
            最近的Task列表
        """
        # 直接访问layer的buffer以保持同步API
        tasks = list(self._l1_layer._buffer)
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]
        return tasks[-limit:]

    def _cleanup_task_index(self) -> None:
        """
        清理Task索引，防止内存泄漏

        保留L1、L2、L3中的活跃Task，删除不活跃的Task
        """
        # 收集活跃的Task ID
        active_task_ids: set[str] = set()
        active_task_ids.update(t.task_id for t in self._l1_layer._buffer)
        active_task_ids.update(item.item.task_id for item in self._l2_layer._heap)
        active_task_ids.update(s.task_id for s in self._l3_summaries)

        # 删除不活跃的Task
        self._task_index = {
            tid: task for tid, task in self._task_index.items() if tid in active_task_ids
        }

    # ==================== L2管理 ====================

    @property
    def _l2_tasks(self) -> list["Task"]:
        """向后兼容：返回L2中的所有Task（按重要性排序）"""
        return [item.item for item in sorted(self._l2_layer._heap)]

    def _add_to_l2(self, task: "Task") -> None:
        """
        添加到L2工作记忆（同步版本）

        使用PriorityQueueLayer自动按重要性排序
        """
        import heapq

        from loom.memory.layers.priority import PriorityItem

        importance = task.metadata.get("importance", 0.5)
        # 使用负数实现最大堆
        priority_item = PriorityItem(-importance, task)

        if len(self._l2_layer._heap) < self._l2_layer._max_size:
            heapq.heappush(self._l2_layer._heap, priority_item)
        else:
            # 找到堆中重要性最低的任务（负数最大的）
            max_item = max(self._l2_layer._heap)
            # 如果新任务重要性更高（负数更小），替换最低重要性的任务
            if priority_item < max_item:
                self._l2_layer._heap.remove(max_item)
                heapq.heapify(self._l2_layer._heap)
                heapq.heappush(self._l2_layer._heap, priority_item)

    def get_l2_tasks(self, limit: int | None = None, session_id: str | None = None) -> list["Task"]:
        """
        获取L2工作记忆Task

        Args:
            limit: 返回数量限制，None表示返回全部
            session_id: 可选的会话过滤

        Returns:
            L2中的Task（按重要性排序）
        """
        # 直接访问layer的heap以保持同步API
        sorted_items = sorted(self._l2_layer._heap)
        tasks = [item.item for item in sorted_items]
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]

        if limit is None:
            return tasks
        return tasks[:limit]

    def clear_l2(self) -> None:
        """清空L2工作记忆（任务结束时调用）"""
        # 清理索引
        for item in self._l2_layer._heap:
            self._task_index.pop(item.item.task_id, None)
        # 清空layer
        self._l2_layer.clear()

    # ==================== L3管理 ====================

    def _add_to_l3(self, summary: TaskSummary) -> None:
        """
        添加Task摘要到L3

        超过容量时移除最旧的
        """
        self._l3_summaries.append(summary)

        # 超过容量时驱逐最旧的
        if len(self._l3_summaries) > self.max_l3_size:
            self._l3_summaries.pop(0)

    def get_l3_summaries(
        self, limit: int | None = None, session_id: str | None = None
    ) -> list[TaskSummary]:
        """
        获取L3 Task摘要

        Args:
            limit: 返回数量限制
            session_id: 可选的会话过滤

        Returns:
            Task摘要列表
        """
        summaries = self._l3_summaries
        if session_id:
            summaries = [s for s in summaries if s.session_id == session_id]
        if limit is None:
            return summaries.copy()
        return summaries[-limit:]

    # ==================== L4管理 ====================

    async def _add_to_l4(self, summary: TaskSummary) -> None:
        """
        添加Task摘要到L4向量存储

        Args:
            summary: Task摘要
        """
        if not self.enable_l4_vectorization or not self.embedding_provider:
            return

        # 生成文本表示
        text = f"{summary.action}: {summary.param_summary} -> {summary.result_summary}"

        # 生成向量
        embedding = await self.embedding_provider.embed(text)

        # 存储到向量数据库
        if self._l4_vector_store:
            await self._l4_vector_store.add(
                id=summary.task_id,
                vector=embedding,
                metadata={
                    "action": summary.action,
                    "tags": summary.tags,
                    "importance": summary.importance,
                    "created_at": summary.created_at.isoformat(),
                    "session_id": summary.session_id,
                },
            )

    async def search_tasks(
        self, query: str, limit: int = 5, session_id: str | None = None
    ) -> list["Task"]:
        """
        从L4语义检索相关Task

        Args:
            query: 查询字符串
            limit: 返回数量限制
            session_id: 可选的会话过滤（仅在降级搜索时生效）

        Returns:
            相关Task列表
        """
        if not self._l4_vector_store or not self.embedding_provider:
            # 降级到简单搜索
            return self._simple_search_tasks(query, limit, session_id=session_id)

        # 向量化查询
        query_embedding = await self.embedding_provider.embed(query)

        # 向量搜索
        results = await self._l4_vector_store.search(query_embedding, limit)

        # 返回Task（如果还在索引中）
        tasks = []
        for result in results:
            task_id = result.get("id")
            if task_id and task_id in self._task_index:
                task = self._task_index[task_id]
                if session_id and task.session_id != session_id:
                    continue
                tasks.append(task)

        return tasks

    def _simple_search_tasks(
        self, query: str, limit: int, session_id: str | None = None
    ) -> list["Task"]:
        """
        简单的文本匹配搜索（降级方案）

        Args:
            query: 查询字符串
            limit: 返回数量限制
            session_id: 可选的会话过滤

        Returns:
            匹配的Task列表
        """
        query_lower = query.lower()
        matches = []

        # 搜索L1和L2中的Task
        l1_tasks = list(self._l1_layer._buffer)
        l2_tasks = [item.item for item in self._l2_layer._heap]
        all_tasks = l1_tasks + l2_tasks

        for task in all_tasks:
            if session_id and task.session_id != session_id:
                continue
            # 检查action和parameters中是否包含查询字符串
            if query_lower in task.action.lower() or query_lower in str(task.parameters).lower():
                matches.append(task)

        # 按重要性排序
        matches.sort(key=lambda t: t.metadata.get("importance", 0.5), reverse=True)

        return matches[:limit]

    async def search_facts(self, query: str, limit: int = 5) -> list[Fact]:
        """
        从L4检索相关事实

        Args:
            query: 查询字符串
            limit: 返回数量限制

        Returns:
            相关Fact列表
        """
        if not self._l4_vector_store or not self.embedding_provider:
            # 降级到简单搜索
            return self._simple_search_facts(query, limit)

        # 向量化查询
        query_embedding = await self.embedding_provider.embed(query)

        # 向量搜索（搜索fact_前缀的ID）
        results = await self._l4_vector_store.search(query_embedding, limit * 2)

        # 返回Fact对象
        facts = []
        for result in results:
            fact_id = result.get("id")
            if fact_id and fact_id.startswith("fact_") and fact_id in self._fact_index:
                fact = self._fact_index[fact_id]
                fact.update_access()  # 更新访问信息
                facts.append(fact)
                if len(facts) >= limit:
                    break

        return facts

    def _simple_search_facts(self, query: str, limit: int) -> list[Fact]:
        """
        简单的文本匹配搜索事实（降级方案）

        Args:
            query: 查询字符串
            limit: 返回数量限制

        Returns:
            匹配的Fact列表
        """
        query_lower = query.lower()
        matches = []

        for fact in self._fact_index.values():
            # 检查content和tags中是否包含查询字符串
            if query_lower in fact.content.lower() or any(
                query_lower in tag.lower() for tag in fact.tags
            ):
                matches.append(fact)

        # 按访问次数和置信度排序
        matches.sort(key=lambda f: (f.access_count, f.confidence), reverse=True)

        return matches[:limit]

    # ==================== Fact管理 ====================

    def add_fact(self, fact: Fact) -> None:
        """
        添加Fact到索引（公共API）

        Args:
            fact: Fact对象
        """
        self._fact_index[fact.fact_id] = fact

        # 定期清理索引（防止内存泄漏）
        if len(self._fact_index) > self.max_fact_index_size:
            self._cleanup_fact_index()

    def _cleanup_fact_index(self) -> None:
        """
        清理Fact索引，防止内存泄漏

        按访问次数和置信度排序，保留前80%的高价值Facts
        """
        if len(self._fact_index) <= self.max_fact_index_size:
            return

        # 按访问次数和置信度排序
        facts = sorted(
            self._fact_index.values(), key=lambda f: (f.access_count, f.confidence), reverse=True
        )

        # 保留前80%
        keep_count = int(len(facts) * 0.8)
        self._fact_index = {f.fact_id: f for f in facts[:keep_count]}

    # ==================== 压缩策略 ====================

    def promote_tasks(self) -> None:
        """
        触发L1→L2→L3→L4的压缩提升

        调用时机：
        - 每次添加Task后
        - 定期维护
        """
        # L1 → L2: 提升重要的Task
        self._promote_l1_to_l2()

        # L2 → L3: 当L2满时，将旧的Task压缩为摘要
        if len(self._l2_layer._heap) >= self.max_l2_size * 0.9:  # 90%阈值
            self._promote_l2_to_l3()

        # L3 → L4: 当L3满时，向量化摘要
        if len(self._l3_summaries) >= self.max_l3_size * 0.9:  # 90%阈值
            # 注意：这是异步操作，实际应该在异步上下文中调用
            # 这里只是标记，实际向量化需要在异步方法中完成
            pass

    async def promote_tasks_async(self) -> None:
        """
        异步版本的promote_tasks，支持L4向量化

        调用时机：
        - 在异步上下文中调用
        - 支持完整的L1→L2→L3→L4压缩流程
        """
        # L1 → L2: 提升重要的Task
        self._promote_l1_to_l2()

        # L2 → L3: 当L2满时，将旧的Task压缩为摘要
        if len(self._l2_layer._heap) >= self.max_l2_size * 0.9:
            self._promote_l2_to_l3()

        # L3 → L4: 当L3满时，向量化摘要（真正实现）
        if len(self._l3_summaries) >= self.max_l3_size * 0.9:
            await self._promote_l3_to_l4()

    def _promote_l1_to_l2(self) -> None:
        """
        L1 → L2: 提升重要的Task

        规则：
        - 重要性 > 0.6 的Task提升到L2
        - L2已满时，只保留最重要的
        """
        for task in list(self._l1_layer._buffer):
            importance = task.metadata.get("importance", 0.5)

            # 判断是否应该提升（重要性>0.6且不在L2中）
            l2_task_ids = [item.item.task_id for item in self._l2_layer._heap]
            if importance > 0.6 and task.task_id not in l2_task_ids:
                self._add_to_l2(task)

    def _promote_l2_to_l3(self) -> None:
        """
        L2 → L3: 生成Task摘要

        当L2接近满时，将最不重要的Task压缩为摘要
        """
        if len(self._l2_layer._heap) < self.max_l2_size * 0.9:
            return

        # 按重要性排序（从heap中提取）
        sorted_items = sorted(self._l2_layer._heap, reverse=True)  # 最低优先级在后

        # 移除最不重要的20%
        num_to_remove = max(1, int(len(sorted_items) * 0.2))
        tasks_to_summarize = [item.item for item in sorted_items[-num_to_remove:]]

        # 重建heap（保留高优先级的80%）
        self._l2_layer._heap = sorted_items[:-num_to_remove]

        # 生成摘要并添加到L3
        for task in tasks_to_summarize:
            summary = self._summarize_task(task)
            self._add_to_l3(summary)
            # 从索引中移除
            self._task_index.pop(task.task_id, None)

    def _summarize_task(self, task: "Task") -> TaskSummary:
        """
        将Task压缩为摘要

        Args:
            task: 要压缩的Task

        Returns:
            TaskSummary对象
        """
        # 参数摘要（截断）
        param_str = str(task.parameters)
        param_summary = param_str[:200] + "..." if len(param_str) > 200 else param_str

        # 结果摘要（截断）
        result_str = str(task.result)
        result_summary = result_str[:200] + "..." if len(result_str) > 200 else result_str

        # 提取标签
        tags = task.metadata.get("tags", [])
        if not tags:
            # 自动生成标签
            tags = [task.action, task.status.value]

        return TaskSummary(
            task_id=task.task_id,
            action=task.action,
            param_summary=param_summary,
            result_summary=result_summary,
            tags=tags,
            importance=task.metadata.get("importance", 0.5),
            created_at=task.created_at,
            session_id=task.session_id,
        )

    async def _promote_l3_to_l4(self) -> None:
        """
        L3 → L4: 向量化摘要

        当L3接近满时，将最旧的摘要向量化并存储到L4
        """
        if not self.enable_l4_vectorization or not self.embedding_provider:
            return

        # 移除最旧的20%
        num_to_vectorize = max(1, int(len(self._l3_summaries) * 0.2))
        summaries_to_vectorize = self._l3_summaries[:num_to_vectorize]
        self._l3_summaries = self._l3_summaries[num_to_vectorize:]

        # 向量化并存储到L4
        for summary in summaries_to_vectorize:
            await self._add_to_l4(summary)

    # ==================== 工具方法 ====================

    def get_task(self, task_id: str) -> "Task | None":
        """
        根据ID获取Task

        Args:
            task_id: Task ID

        Returns:
            Task对象，如果不存在则返回None
        """
        return self._task_index.get(task_id)

    def get_stats(self) -> dict[str, Any]:
        """
        获取记忆系统统计信息

        Returns:
            统计信息字典
        """
        return {
            "l1_size": len(self._l1_layer._buffer),
            "l2_size": len(self._l2_layer._heap),
            "l3_size": len(self._l3_summaries),
            "total_tasks": len(self._task_index),
            "max_l1_size": self.max_l1_size,
            "max_l2_size": self.max_l2_size,
            "max_l3_size": self.max_l3_size,
        }

    def clear_all(self) -> None:
        """清空所有记忆（慎用）"""
        self._l1_layer.clear()
        self._l2_layer.clear()
        self._l3_summaries.clear()
        self._task_index.clear()
