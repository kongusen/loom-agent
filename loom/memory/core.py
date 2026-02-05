"""
记忆系统核心实现 - 基于Task的分层存储

基于A4公理（记忆层次公理）：Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4

核心改动：
- L1: 存储完整Task对象（循环缓冲区）
- L2: 存储重要Task对象（按重要性排序）
- L3: 存储TaskSummary（压缩表示）
- L4: 向量存储（语义检索）
"""

import heapq
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from loom.config.memory import MemoryStrategyType

from .fact_extractor import FactExtractor
from .layers import CircularBufferLayer, PriorityQueueLayer
from .types import Fact, MemoryTier, TaskSummary

logger = logging.getLogger(__name__)

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
        max_l4_size: int | None = None,
        enable_l4_vectorization: bool = True,
        max_task_index_size: int = 1000,
        max_fact_index_size: int = 5000,
        event_bus: "Any | None" = None,
        # MemoryConfig support
        strategy: MemoryStrategyType = MemoryStrategyType.IMPORTANCE_BASED,
        enable_auto_migration: bool = True,
        enable_compression: bool = True,
        l1_retention_hours: int | None = None,
        l2_retention_hours: int | None = None,
        l3_retention_hours: int | None = None,
        l4_retention_hours: int | None = None,
        l1_promote_threshold: int = 3,
        l2_promote_threshold: int = 5,
        l3_promote_threshold: int = 10,
        l2_auto_compress: bool = True,
        l3_auto_compress: bool = True,
        importance_threshold: float = 0.6,
    ):
        self.node_id = node_id
        self.max_l1_size = max_l1_size
        self.max_l2_size = max_l2_size
        self.max_l3_size = max_l3_size
        self.max_l4_size = max_l4_size
        self.enable_l4_vectorization = enable_l4_vectorization
        self.max_task_index_size = max_task_index_size
        self.max_fact_index_size = max_fact_index_size
        self._event_bus = event_bus
        if isinstance(strategy, str):
            strategy = MemoryStrategyType(strategy)
        self.strategy = strategy
        self.enable_auto_migration = enable_auto_migration
        self.enable_compression = enable_compression
        self.l1_retention_hours = l1_retention_hours
        self.l2_retention_hours = l2_retention_hours
        self.l3_retention_hours = l3_retention_hours
        self.l4_retention_hours = l4_retention_hours
        self.l1_promote_threshold = l1_promote_threshold
        self.l2_promote_threshold = l2_promote_threshold
        self.l3_promote_threshold = l3_promote_threshold
        self.l2_auto_compress = l2_auto_compress
        self.l3_auto_compress = l3_auto_compress
        self.importance_threshold = importance_threshold

        # L1: 完整Task（使用CircularBufferLayer）
        self._l1_layer = CircularBufferLayer(max_size=max_l1_size)

        # L2: 重要Task（使用PriorityQueueLayer）
        self._l2_layer = PriorityQueueLayer(max_size=max_l2_size)

        # L3: Task摘要
        self._l3_summaries: list[TaskSummary] = []

        # L4: 向量存储（延迟初始化）
        self._l4_vector_store: VectorStoreProvider | None = None
        self.embedding_provider = None
        self._l4_count = 0
        self._l4_index: dict[str, datetime] = {}
        self._l4_pruned_count = 0
        self._l4_last_pruned_at: datetime | None = None

        # Task索引（用于快速查找）
        self._task_index: dict[str, Task] = {}

        # Fact索引（用于快速查找）
        self._fact_index: dict[str, Fact] = {}

        # 事实提取器
        self.fact_extractor = FactExtractor()

        # 设置L1驱逐回调（自动清理索引）
        self._l1_layer.on_eviction(self._on_l1_eviction)

        # 订阅EventBus（如果提供）
        if self._event_bus is not None:
            self._event_bus.register_handler("*", self._on_task)

    def close(self) -> None:
        """关闭 LoomMemory，清理资源"""
        if self._event_bus is not None:
            self._event_bus.unregister_handler("*", self._on_task)

    # ==================== EventBus订阅 ====================

    async def _on_task(self, task: "Task") -> "Task":
        """
        EventBus订阅处理器 - 自动接收所有Task

        根据A4公理（记忆层次公理）：
        - L1: 存储所有Task（最近的）
        - L2: 存储重要Task（importance > 0.6）

        Args:
            task: 从EventBus接收的Task

        Returns:
            原始Task（不修改）
        """
        self._apply_retention()
        # 0. 确保有默认的重要性（用于L2提升）
        self._ensure_importance(task)

        # 1. 添加到L1（所有Task）
        self._add_to_l1(task)

        # 2. 根据策略决定是否添加到L2
        if self.strategy == MemoryStrategyType.IMPORTANCE_BASED:
            importance = task.metadata.get("importance", 0.5)
            if importance > self.importance_threshold:
                self._add_to_l2(task)

        # 3. 触发提升（L1->L2->L3->L4）
        if self.enable_auto_migration:
            self.promote_tasks()

        # 4. 返回原始Task（不修改）
        return task

    # ==================== 内部辅助：访问与保留 ====================

    def _mark_access(self, task: "Task") -> None:
        """更新任务访问信息（用于基于访问次数的提升策略）"""
        if task is None:
            return
        count = task.metadata.get("loom_access_count", 0)
        task.metadata["loom_access_count"] = count + 1
        task.metadata["loom_last_accessed"] = datetime.now().isoformat()

    def _is_task_expired(self, task: "Task", retention_hours: int) -> bool:
        """判断任务是否过期"""
        if retention_hours <= 0:
            return True
        created_at = getattr(task, "created_at", None)
        if created_at is None:
            created_at = getattr(task, "createdAt", None)
        if created_at is None:
            return False
        cutoff = datetime.now() - timedelta(hours=retention_hours)
        return bool(created_at < cutoff)

    def _apply_retention(self) -> None:
        """按层级清理过期任务"""
        self._purge_expired_l1()
        self._purge_expired_l2()
        self._purge_expired_l3()

    def _purge_expired_l1(self) -> None:
        if self.l1_retention_hours is None:
            return
        # L1 按时间顺序存储，逐个从左侧清理
        while self._l1_layer._buffer:
            task = self._l1_layer._buffer[0]
            if not self._is_task_expired(task, self.l1_retention_hours):
                break
            evicted = self._l1_layer._buffer.popleft()
            for callback in self._l1_layer._eviction_callbacks:
                callback(evicted)

    def _purge_expired_l2(self) -> None:
        if self.l2_retention_hours is None:
            return
        before = len(self._l2_layer._heap)
        if before == 0:
            return
        filtered = [
            item
            for item in self._l2_layer._heap
            if not self._is_task_expired(item.item, self.l2_retention_hours)
        ]
        if len(filtered) == before:
            return
        self._l2_layer._heap = filtered
        heapq.heapify(self._l2_layer._heap)
        self._rebuild_task_index()

    def _purge_expired_l3(self) -> None:
        if self.l3_retention_hours is None:
            return
        cutoff = datetime.now() - timedelta(hours=self.l3_retention_hours)
        self._l3_summaries = [s for s in self._l3_summaries if s.created_at >= cutoff]

    def _rebuild_task_index(self) -> None:
        """根据 L1/L2 重新构建任务索引（用于保留清理后的一致性）"""
        active: dict[str, Task] = {}
        for task in list(self._l1_layer._buffer):
            active[task.task_id] = task
        for item in self._l2_layer._heap:
            active[item.item.task_id] = item.item
        self._task_index = active

    def _should_summarize_l2(self, task: "Task") -> bool:
        """判断 L2 任务是否应被摘要到 L3"""
        if self.strategy == MemoryStrategyType.IMPORTANCE_BASED:
            importance = float(task.metadata.get("importance", 0.5))
            return importance < self.importance_threshold
        if self.strategy == MemoryStrategyType.TIME_BASED:
            if self.l2_retention_hours is None:
                return False
            return self._is_task_expired(task, self.l2_retention_hours)
        # SIMPLE: access-count based
        access_count = int(task.metadata.get("loom_access_count", 0))
        return access_count < self.l2_promote_threshold

    async def _prune_l4(self) -> None:
        """按保留策略清理 L4 向量"""
        if not self._l4_vector_store:
            return

        now = datetime.now()

        # 1) 按 retention_hours 删除过期
        expired_ids: list[str] = []
        if self.l4_retention_hours is not None:
            cutoff = now - timedelta(hours=self.l4_retention_hours)
            for vid, created_at in list(self._l4_index.items()):
                if created_at < cutoff:
                    expired_ids.append(vid)

        # 2) 按容量删除最旧
        over_capacity_ids: list[str] = []
        if self.max_l4_size is not None and self.max_l4_size >= 0:
            current = len(self._l4_index)
            if current - len(expired_ids) > self.max_l4_size:
                remaining = {
                    vid: ts for vid, ts in self._l4_index.items() if vid not in expired_ids
                }
                sorted_ids = sorted(remaining.items(), key=lambda x: x[1])
                to_remove = current - len(expired_ids) - self.max_l4_size
                over_capacity_ids = [vid for vid, _ in sorted_ids[:to_remove]]

        ids_to_delete = list({*expired_ids, *over_capacity_ids})
        if not ids_to_delete:
            return

        logger.debug(
            "L4 prune triggered: expired=%d, over_capacity=%d, total=%d",
            len(expired_ids),
            len(over_capacity_ids),
            len(ids_to_delete),
        )

        deleted_ids: set[str] = set()
        if hasattr(self._l4_vector_store, "delete_by_metadata"):
            try:
                await self._l4_vector_store.delete_by_metadata({"id__in": ids_to_delete})
                deleted_ids = set(ids_to_delete)
            except Exception:
                deleted_ids = set()

        if not deleted_ids:
            for vid in ids_to_delete:
                try:
                    deleted = await self._l4_vector_store.delete(vid)
                except Exception:
                    deleted = False
                if deleted:
                    deleted_ids.add(vid)

        for vid in deleted_ids:
            self._l4_index.pop(vid, None)
            self._l4_count = max(0, self._l4_count - 1)
            self._l4_pruned_count += 1

        self._l4_last_pruned_at = now
        if deleted_ids:
            logger.info("L4 prune deleted %d vectors", len(deleted_ids))

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
        self._apply_retention()
        # 确保有默认的重要性（用于L2提升）
        self._ensure_importance(task)

        # 添加到索引
        self._task_index[task.task_id] = task

        # 定期清理索引（防止内存泄漏）
        if len(self._task_index) > self.max_task_index_size:
            self._cleanup_task_index()

        # 根据层级分发
        if tier == MemoryTier.L1_RAW_IO:
            self._add_to_l1(task)
            # 触发提升（L1->L2->L3->L4）
            if self.enable_auto_migration:
                self.promote_tasks()
        elif tier == MemoryTier.L2_WORKING:
            self._add_to_l2(task)

    def remove_task(self, task_id: str) -> bool:
        """
        从 L1/L2 和索引中移除任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功移除
        """
        # 1. 移除索引
        if task_id in self._task_index:
            del self._task_index[task_id]

        removed = False

        # 2. 尝试从 L1 移除
        # L1 是 deque，移除特定元素效率较低 O(N)
        try:
            # 查找并移除
            for task in self._l1_layer._buffer:
                if task.task_id == task_id:
                    self._l1_layer._buffer.remove(task)
                    removed = True
                    break
        except ValueError:
            pass

        # 3. 尝试从 L2 移除
        # L2 是 heap，只能重建
        # 检查是否在 L2
        found_in_l2 = False
        for item in self._l2_layer._heap:
            if item.item.task_id == task_id:
                found_in_l2 = True
                break

        if found_in_l2:
            self._l2_layer._heap = [i for i in self._l2_layer._heap if i.item.task_id != task_id]
            heapq.heapify(self._l2_layer._heap)
            removed = True

        return removed

    def _ensure_importance(self, task: "Task") -> None:
        """为任务设置默认重要性（若未显式提供）"""
        if "importance" not in task.metadata:
            task.metadata["importance"] = self._infer_importance()

    def _infer_importance(self) -> float:
        """
        返回统一的默认重要性值

        Phase 5: 移除硬编码的重要性判断规则。
        框架提供机制（importance 字段），LLM 提供策略（通过 metadata 显式设置）。
        """
        return 0.5

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
        self._apply_retention()
        # 直接访问layer的buffer以保持同步API
        tasks = list(self._l1_layer._buffer)
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]
        selected = tasks[-limit:]
        for task in selected:
            self._mark_access(task)
        return selected

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
        self._apply_retention()
        # 直接访问layer的heap以保持同步API
        sorted_items = sorted(self._l2_layer._heap)
        tasks = [item.item for item in sorted_items]
        if session_id:
            tasks = [t for t in tasks if t.session_id == session_id]

        selected = tasks if limit is None else tasks[:limit]

        for task in selected:
            self._mark_access(task)
        return selected

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
        self._apply_retention()
        summaries = self._l3_summaries
        if session_id:
            summaries = [s for s in summaries if s.session_id == session_id]
        selected = summaries.copy() if limit is None else summaries[-limit:]
        for summary in selected:
            summary.access_count += 1
        return selected

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
            added = await self._l4_vector_store.add(
                id=summary.task_id,
                embedding=embedding,
                metadata={
                    "action": summary.action,
                    "tags": summary.tags,
                    "importance": summary.importance,
                    "created_at": summary.created_at.isoformat(),
                    "session_id": summary.session_id,
                },
            )
            if added:
                self._l4_count += 1
                self._l4_index[summary.task_id] = summary.created_at
                await self._prune_l4()

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
            task_id = result.id if hasattr(result, "id") else result.get("id")
            if task_id and task_id in self._task_index:
                task = self._task_index[task_id]
                if session_id and task.session_id != session_id:
                    continue
                tasks.append(task)

        return tasks

    # ==================== L4配置 ====================

    def set_vector_store(self, store: "VectorStoreProvider") -> None:
        """设置 L4 向量存储"""
        self._l4_vector_store = store

    def set_embedding_provider(self, provider: Any) -> None:
        """设置嵌入提供者"""
        self.embedding_provider = provider

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
            fact_id = result.id if hasattr(result, "id") else result.get("id")
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
        if not self.enable_auto_migration:
            return

        self._apply_retention()
        # L1 → L2: 提升重要的Task
        self._promote_l1_to_l2()

        # L2 → L3: 当L2满时，将旧的Task压缩为摘要
        if (
            self.enable_compression
            and self.l2_auto_compress
            and len(self._l2_layer._heap) >= self.max_l2_size
        ):  # 100%阈值
            self._promote_l2_to_l3()

        # L3 → L4: 当L3满时，向量化摘要
        if (
            self.enable_compression
            and self.l3_auto_compress
            and len(self._l3_summaries) >= self.max_l3_size * 0.9
        ):  # 90%阈值
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
        if not self.enable_auto_migration:
            return

        self._apply_retention()
        await self._prune_l4()
        # L1 → L2: 提升重要的Task
        self._promote_l1_to_l2()

        # L2 → L3: 当L2满时，将旧的Task压缩为摘要
        if (
            self.enable_compression
            and self.l2_auto_compress
            and len(self._l2_layer._heap) >= self.max_l2_size * 0.9
        ):
            self._promote_l2_to_l3()

        # L3 → L4: 当L3满时，向量化摘要（真正实现）
        if (
            self.enable_compression
            and self.l3_auto_compress
            and len(self._l3_summaries) >= self.max_l3_size * 0.9
        ):
            await self._promote_l3_to_l4()

    def _promote_l1_to_l2(self) -> None:
        """
        L1 → L2: 提升重要的Task

        规则：
        - SIMPLE: 访问次数 >= l1_promote_threshold
        - IMPORTANCE_BASED: 重要性 >= importance_threshold
        - TIME_BASED: 任务年龄 >= l1_retention_hours
        """
        if self.strategy == MemoryStrategyType.SIMPLE and self.l1_promote_threshold <= 0:
            return

        for task in list(self._l1_layer._buffer):
            l2_task_ids = [item.item.task_id for item in self._l2_layer._heap]
            if task.task_id in l2_task_ids:
                continue

            if self.strategy == MemoryStrategyType.IMPORTANCE_BASED:
                importance = task.metadata.get("importance", 0.5)
                if importance > self.importance_threshold:
                    self._add_to_l2(task)
            elif self.strategy == MemoryStrategyType.TIME_BASED:
                if self.l1_retention_hours is None:
                    continue
                if self._is_task_expired(task, self.l1_retention_hours):
                    self._add_to_l2(task)
            else:
                # SIMPLE: access-count based
                access_count = task.metadata.get("loom_access_count", 0)
                if access_count >= self.l1_promote_threshold:
                    self._add_to_l2(task)

    def _promote_l2_to_l3(self) -> None:
        """
        L2 → L3: 生成Task摘要

        当L2接近满时，将最不重要的Task压缩为摘要
        """
        if len(self._l2_layer._heap) < self.max_l2_size:
            return

        # 按重要性排序（从heap中提取）
        # PriorityItem.priority = -importance, ascending gives highest importance first.
        sorted_items = sorted(self._l2_layer._heap)

        # 移除最不重要的20%
        num_to_remove = max(1, int(len(sorted_items) * 0.2))
        candidates = [item.item for item in sorted_items if self._should_summarize_l2(item.item)]
        if len(candidates) >= num_to_remove:
            tasks_to_summarize = candidates[:num_to_remove]
        else:
            extra_needed = num_to_remove - len(candidates)
            fallback = [item.item for item in sorted_items if item.item not in candidates]
            tasks_to_summarize = candidates + fallback[-extra_needed:]

        # 重建heap（移除被摘要的任务）
        summarize_ids = {t.task_id for t in tasks_to_summarize}
        self._l2_layer._heap = [
            item for item in self._l2_layer._heap if item.item.task_id not in summarize_ids
        ]
        heapq.heapify(self._l2_layer._heap)

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
        if self.l3_promote_threshold > 0:
            preferred = [
                s for s in self._l3_summaries if s.access_count >= self.l3_promote_threshold
            ]
            if len(preferred) >= num_to_vectorize:
                summaries_to_vectorize = preferred[:num_to_vectorize]
            else:
                remaining = [s for s in self._l3_summaries if s not in preferred]
                summaries_to_vectorize = preferred + remaining[: (num_to_vectorize - len(preferred))]
        else:
            summaries_to_vectorize = self._l3_summaries[:num_to_vectorize]

        vectorize_ids = {s.task_id for s in summaries_to_vectorize}
        self._l3_summaries = [s for s in self._l3_summaries if s.task_id not in vectorize_ids]

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
        task = self._task_index.get(task_id)
        if task:
            self._mark_access(task)
        return task

    def get_call_chain(self, task_id: str) -> list["Task"]:
        """
        获取任务调用链（从根任务到当前任务）

        通过递归查询 parent_task_id 构建完整的调用链。
        用于调试和追踪任务执行路径。

        Args:
            task_id: 任务ID

        Returns:
            任务列表，从根任务到当前任务的完整路径
            如果任务不存在，返回空列表

        Example:
            >>> chain = memory.get_call_chain("task-3")
            >>> # 返回: [root_task, parent_task, current_task]
        """
        chain = []
        current = self.get_task(task_id)

        # 递归查询父任务
        while current:
            chain.append(current)
            if current.parent_task_id:
                current = self.get_task(current.parent_task_id)
            else:
                break

        # 反转列表，使其从根任务到当前任务
        return list(reversed(chain))

    def get_stats(self) -> dict[str, Any]:
        """
        获取记忆系统统计信息

        Returns:
            统计信息字典
        """
        self._apply_retention()
        return {
            "l1_size": len(self._l1_layer._buffer),
            "l2_size": len(self._l2_layer._heap),
            "l3_size": len(self._l3_summaries),
            "l4_size": self._l4_count,
            "l4_index_size": len(self._l4_index),
            "total_tasks": len(self._task_index),
            "total_facts": len(self._fact_index),
            "max_l1_size": self.max_l1_size,
            "max_l2_size": self.max_l2_size,
            "max_l3_size": self.max_l3_size,
            "max_l4_size": self.max_l4_size,
            "l4_pruned_count": self._l4_pruned_count,
            "l4_last_pruned_at": (
                self._l4_last_pruned_at.isoformat() if self._l4_last_pruned_at else None
            ),
            "has_vector_store": self._l4_vector_store is not None,
            "has_embedding_provider": self.embedding_provider is not None,
        }

    def clear_all(self) -> None:
        """清空所有记忆（慎用）"""
        self._l1_layer.clear()
        self._l2_layer.clear()
        self._l3_summaries.clear()
        self._task_index.clear()
        self._l4_count = 0
        self._l4_index.clear()
