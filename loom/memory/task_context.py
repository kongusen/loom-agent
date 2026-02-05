"""
Task-based Context Management

基于 Task 的上下文管理，整合 LoomMemory 和 EventBus。

核心功能：
1. 从多个来源收集上下文（Memory + EventBus）
2. 将 Task 转换为 LLM 消息格式
3. 智能压缩和总结
4. 精确的 token 控制
5. 上下文预算分配（Context Budgeter）

设计理念：
- 防止上下文腐化
- 最大化智能
- 支持长时间任务
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from loom.memory.tokenizer import TokenCounter
from loom.protocol import Task

if TYPE_CHECKING:
    from loom.fractal.memory import MemoryScope
    from loom.memory.core import LoomMemory
    from loom.memory.manager import MemoryManager


# ==================== 上下文预算分配器 ====================


@dataclass
class BudgetAllocation:
    """
    上下文预算分配结果

    Attributes:
        l1_tokens: L1层（最近任务）分配的token数
        l2_tokens: L2层（重要任务）分配的token数
        l3_l4_tokens: L3/L4层（摘要/向量）分配的token数
        eventbus_tokens: EventBus事件分配的token数
        system_tokens: 系统提示词预留的token数
    """

    l1_tokens: int = 0
    l2_tokens: int = 0
    l3_l4_tokens: int = 0
    eventbus_tokens: int = 0
    system_tokens: int = 0

    @property
    def total(self) -> int:
        """总分配token数"""
        return self.l1_tokens + self.l2_tokens + self.l3_l4_tokens + self.eventbus_tokens


@dataclass
class BudgetConfig:
    """
    上下文预算配置

    Attributes:
        l1_ratio: L1层分配比例（默认30%）
        l2_ratio: L2层分配比例（默认25%，用于Bus相关上下文）
        l3_l4_ratio: L3/L4层分配比例（默认20%）
        direct_min_items: Direct最小保留条数（默认1）
        bus_min_items: Bus最小保留条数（默认2）
        system_reserve: 系统提示词预留比例（默认15%）
    """

    l1_ratio: float = 0.30
    l2_ratio: float = 0.25
    l3_l4_ratio: float = 0.20
    direct_min_items: int = 1
    bus_min_items: int = 2
    system_reserve: float = 0.15


@dataclass
class EventCandidate:
    """
    事件候选项（用于排序）

    Attributes:
        task: 事件Task对象
        score: 综合评分
        time_score: 时间衰减分数
        action_score: 动作权重分数
        relevance_score: 相关性分数
        node_score: 节点权重分数
    """

    task: Task
    score: float = 0.0
    time_score: float = 0.0
    action_score: float = 0.0
    relevance_score: float = 0.0
    node_score: float = 0.0


class ContextBudgeter:
    """
    上下文预算分配器

    负责智能分配上下文token预算到不同层级，并对事件候选进行排序。

    预算分配策略：
    - L1（最近任务 + Direct）: 30% - 保证直连与最近上下文的完整性
    - L2（Bus相关）: 25% - 保留跨节点相关信息
    - L3/L4（摘要/向量）: 20% - 长期记忆检索

    事件排序策略：
    - 时间衰减（40%）: 越近的事件权重越高
    - 动作权重（25%）: thinking > tool_call > other
    - 相关性（20%）: 关键词/embedding匹配
    - 节点权重（15%）: 父节点 > 兄弟节点 > 其他
    """

    def __init__(
        self,
        token_counter: TokenCounter,
        max_tokens: int = 4000,
        config: BudgetConfig | None = None,
    ):
        """
        初始化上下文预算分配器

        Args:
            token_counter: Token计数器
            max_tokens: 最大token数
            config: 预算配置（可选）
        """
        self.token_counter = token_counter
        self.max_tokens = max_tokens
        self.config = self._normalize_config(config or BudgetConfig())

        # 动作类型权重
        self._action_weights = {
            "node.thinking": 1.0,
            "node.tool_call": 0.8,
            "node.planning": 0.9,
            "node.error": 0.7,
            "execute": 0.6,
        }

    def _normalize_config(self, config: BudgetConfig) -> BudgetConfig:
        """归一化比例配置，避免错误配置导致预算失真"""
        l1 = max(0.0, config.l1_ratio)
        l2 = max(0.0, config.l2_ratio)
        l3 = max(0.0, config.l3_l4_ratio)

        total = l1 + l2 + l3
        if total <= 0:
            return BudgetConfig()

        l1 /= total
        l2 /= total
        l3 /= total
        direct_min_items = int(max(0, config.direct_min_items))
        bus_min_items = int(max(0, config.bus_min_items))

        return BudgetConfig(
            l1_ratio=l1,
            l2_ratio=l2,
            l3_l4_ratio=l3,
            direct_min_items=direct_min_items,
            bus_min_items=bus_min_items,
            system_reserve=config.system_reserve,
        )

    def allocate_budget(self, system_prompt_tokens: int = 0) -> BudgetAllocation:
        """
        分配上下文预算

        Args:
            system_prompt_tokens: 系统提示词占用的token数

        Returns:
            预算分配结果
        """
        # 计算可用token（扣除系统提示词）
        available = self.max_tokens - system_prompt_tokens

        if available <= 0:
            return BudgetAllocation(system_tokens=system_prompt_tokens)

        # 按比例分配
        return BudgetAllocation(
            l1_tokens=int(available * self.config.l1_ratio),
            l2_tokens=int(available * self.config.l2_ratio),
            l3_l4_tokens=int(available * self.config.l3_l4_ratio),
            system_tokens=system_prompt_tokens,
        )

    def rank_events(
        self,
        events: list[Task],
        current_task: Task,
        current_node_id: str | None = None,
        parent_node_id: str | None = None,
        keywords: list[str] | None = None,
    ) -> list[EventCandidate]:
        """
        对事件候选进行排序

        排序策略：
        - 时间衰减（40%）: 越近的事件权重越高
        - 动作权重（25%）: thinking > tool_call > other
        - 相关性（20%）: 关键词匹配
        - 节点权重（15%）: 父节点 > 兄弟节点 > 其他

        Args:
            events: 事件列表
            current_task: 当前任务
            current_node_id: 当前节点ID
            parent_node_id: 父节点ID
            keywords: 相关关键词列表

        Returns:
            排序后的事件候选列表
        """
        if not events:
            return []

        if keywords is None:
            content = current_task.parameters.get("content", "")
            keywords = self._fallback_keywords(content)

        candidates = []
        now = datetime.now(UTC)

        for event in events:
            candidate = EventCandidate(task=event)

            # 1. 时间衰减分数（40%权重）
            candidate.time_score = self._calc_time_score(event, now)

            # 2. 动作权重分数（25%权重）
            candidate.action_score = self._calc_action_score(event)

            # 3. 相关性分数（20%权重）
            candidate.relevance_score = self._calc_relevance_score(event, keywords)

            # 4. 节点权重分数（15%权重）
            candidate.node_score = self._calc_node_score(event, current_node_id, parent_node_id)

            # 综合评分
            candidate.score = (
                candidate.time_score * 0.40
                + candidate.action_score * 0.25
                + candidate.relevance_score * 0.20
                + candidate.node_score * 0.15
            )

            candidates.append(candidate)

        # 按分数降序排序
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates

    def _calc_time_score(self, event: Task, now: datetime) -> float:
        """计算时间衰减分数"""
        if not event.created_at:
            return 0.5  # 无时间戳，给中等分数

        # 计算时间差（秒）
        delta = (now - event.created_at).total_seconds()

        # 指数衰减：半衰期为1小时（3600秒）
        half_life = 3600
        return 2 ** (-delta / half_life)

    def _calc_action_score(self, event: Task) -> float:
        """计算动作权重分数"""
        return self._action_weights.get(event.action, 0.5)

    def _calc_relevance_score(self, event: Task, keywords: list[str] | None) -> float:
        """计算相关性分数（基于关键词匹配）"""
        embedded_score = event.metadata.get("_relevance_score")
        if isinstance(embedded_score, int | float):
            return float(embedded_score)
        if not keywords:
            return 0.5  # 无关键词，给中等分数

        # 从事件内容中提取文本
        content = event.parameters.get("content", "")
        if not content:
            return 0.3

        # 计算关键词匹配率
        content_lower = content.lower()
        matches = sum(1 for kw in keywords if kw.lower() in content_lower)
        return min(1.0, matches / len(keywords))

    def _fallback_keywords(self, text: str) -> list[str]:
        """无外部分词器时的简单关键词提取（含中文二/三元组）"""
        import re

        if not text:
            return []
        words = re.findall(r"\w+", text.lower())
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]

        if not keywords:
            cjk_sequences = re.findall(r"[\u4e00-\u9fff]+", text)
            cjk_terms: list[str] = []
            for seq in cjk_sequences:
                if len(seq) <= 1:
                    continue
                for i in range(len(seq) - 1):
                    cjk_terms.append(seq[i : i + 2])
                for i in range(len(seq) - 2):
                    cjk_terms.append(seq[i : i + 3])
            keywords = list(dict.fromkeys(cjk_terms))[:20]

        return list(dict.fromkeys(keywords))

    def _calc_node_score(
        self,
        event: Task,
        current_node_id: str | None,
        parent_node_id: str | None,
    ) -> float:
        """计算节点权重分数"""
        event_node_id = event.parameters.get("node_id")

        if not event_node_id:
            return 0.3

        # 父节点事件权重最高
        if parent_node_id and event_node_id == parent_node_id:
            return 1.0

        # 当前节点事件次之
        if current_node_id and event_node_id == current_node_id:
            return 0.8

        # 其他节点
        return 0.5


# ==================== 接口定义 ====================


class ContextSource(ABC):
    """
    上下文源抽象接口

    定义从不同来源获取上下文的统一接口。
    """

    @abstractmethod
    async def get_context(
        self,
        current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        """
        获取上下文 Task 列表

        Args:
            current_task: 当前任务
            max_items: 最大返回数量

        Returns:
            相关的 Task 列表
        """
        pass


# ==================== 消息转换器 ====================


class MessageConverter:
    """
    Task → LLM Message 转换器

    将不同类型的 Task 转换为 LLM API 消息格式。
    """

    def convert_task_to_message(self, task: Task) -> dict[str, str] | None:
        """
        将单个 Task 转换为消息

        Args:
            task: Task 对象

        Returns:
            LLM 消息字典，如果不应该包含则返回 None
        """
        action = task.action
        params = task.parameters

        # 根据 action 类型转换
        if action == "node.thinking":
            # 思考过程 → assistant 消息
            content = params.get("content", "")
            if content:
                return {"role": "assistant", "content": content}

        elif action == "node.tool_call":
            # 工具调用 → assistant 消息
            tool_name = params.get("tool_name", "")
            tool_args = params.get("tool_args", {})
            return {"role": "assistant", "content": f"[Calling {tool_name}({tool_args})]"}

        elif action == "node.message":
            # 节点消息 → assistant 消息
            content = params.get("content") or params.get("message", "")
            if content:
                role = params.get("context_role")
                if role in {"system", "assistant", "user"}:
                    return {"role": role, "content": content}
                return {"role": "assistant", "content": f"[Direct message] {content}"}

        elif action == "node.delegation_request":
            # 委派请求 → assistant 消息（避免混淆为用户指令）
            subtask = (
                params.get("subtask")
                or params.get("subtask_description")
                or params.get("content", "")
            )
            source = task.source_agent or params.get("source_agent") or "unknown"
            if subtask:
                return {
                    "role": "assistant",
                    "content": f"[Delegation request from {source}] {subtask}",
                }

        elif action == "node.delegation_response":
            # 委派响应 → assistant 消息
            result = params.get("result") or params.get("content", "")
            source = task.source_agent or params.get("source_agent") or "unknown"
            if result:
                return {
                    "role": "assistant",
                    "content": f"[Delegation response from {source}] {result}",
                }

        elif action == "node.planning":
            # 规划事件 → system 消息（作为上下文，让子节点看到父节点的计划）
            goal = params.get("goal", "")
            steps = params.get("steps", [])
            reasoning = params.get("reasoning", "")
            step_count = params.get("step_count", len(steps))

            if not goal and not steps:
                return None

            content = f"[Parent Plan] Goal: {goal}\n"
            if reasoning:
                content += f"Reasoning: {reasoning}\n"
            content += f"Steps ({step_count}):\n"
            for idx, step in enumerate(steps, 1):
                content += f"  {idx}. {step}\n"

            return {"role": "system", "content": content}

        elif action == "execute":
            # 任务执行 → user 消息
            content = params.get("content", "")
            if content:
                return {"role": "user", "content": content}

        # 其他类型暂不转换
        return None

    def convert_tasks_to_messages(
        self,
        tasks: list[Task],
    ) -> list[dict[str, str]]:
        """
        批量转换 Task 为消息

        Args:
            tasks: Task 列表

        Returns:
            消息列表
        """
        messages = []
        for task in tasks:
            msg = self.convert_task_to_message(task)
            if msg:
                messages.append(msg)
        return messages


# ==================== 上下文源实现 ====================


class MemoryContextSource(ContextSource):
    """
    从 LoomMemory 获取上下文

    优先级：L2 (工作记忆) > L1 (最近任务)
    """

    def __init__(self, memory: "LoomMemory"):
        self.memory = memory

    async def get_context(
        self,
        current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        """获取记忆中的相关任务"""
        # 1. 优先从 L2 获取（重要任务）
        l2_tasks = self.memory.get_l2_tasks(
            limit=max_items // 2, session_id=current_task.session_id
        )

        # 2. 从 L1 获取最近任务
        l1_tasks = self.memory.get_l1_tasks(
            limit=max_items // 2, session_id=current_task.session_id
        )

        # 3. 合并去重
        seen_ids = set()
        context_tasks = []

        for task in l2_tasks + l1_tasks:
            if task.task_id not in seen_ids:
                context_tasks.append(task)
                seen_ids.add(task.task_id)

        return context_tasks[:max_items]


class MemoryScopeContextSource(ContextSource):
    """
    从作用域记忆（MemoryManager）获取跨节点共享上下文

    读取 INHERITED / SHARED / GLOBAL 作用域，注入为系统消息。
    """

    def __init__(
        self,
        memory: "MemoryManager",
        scopes: list["MemoryScope"] | None = None,
        max_items: int = 6,
        include_additional: bool = True,
        max_additional: int = 4,
    ):
        self.memory = memory
        self.scopes = scopes or []
        self.max_items = max_items
        self.include_additional = include_additional
        self.max_additional = max_additional

        if not self.scopes:
            from loom.fractal.memory import MemoryScope

            self.scopes = [MemoryScope.INHERITED, MemoryScope.SHARED, MemoryScope.GLOBAL]

    async def get_context(
        self,
        current_task: Task,
        max_items: int = 10,
    ) -> list[Task]:
        limit = min(max_items, self.max_items)
        entries: list[tuple[str, str]] = []  # (label, entry_id)

        root_context_id = current_task.parameters.get("root_context_id")
        root_content = ""
        if root_context_id:
            entries.append(("ROOT GOAL", root_context_id))
            root_entry = await self.memory.read(root_context_id)
            if root_entry and root_entry.content:
                root_content = str(root_entry.content)

        parent_task_id = current_task.parent_task_id
        parent_content = ""
        if parent_task_id:
            entries.append(("PARENT TASK", f"task:{parent_task_id}:content"))
            parent_entry = await self.memory.read(f"task:{parent_task_id}:content")
            if parent_entry and parent_entry.content:
                parent_content = str(parent_entry.content)

        tasks: list[Task] = []
        seen_ids: set[str] = set()

        async def _append_entry(label: str, entry_id: str) -> None:
            if entry_id in seen_ids:
                return
            entry = await self.memory.read(entry_id)
            if not entry:
                return
            content = entry.content
            if content is None or content == "":
                return
            seen_ids.add(entry_id)
            scope_label = entry.scope.value if hasattr(entry, "scope") else "shared"
            if label == "ROOT GOAL":
                message = f"[ROOT GOAL - MUST FOLLOW] {content}"
            elif label == "PARENT TASK":
                message = f"[PARENT TASK - MUST ALIGN] {content}"
            else:
                message = f"[{label}] {content}"
            tasks.append(
                Task(
                    task_id=f"fractal:{entry_id}",
                    action="node.message",
                    parameters={
                        "content": message,
                        "context_role": "system",
                        "memory_id": entry_id,
                        "scope": scope_label,
                        "label": label,
                    },
                    session_id=current_task.session_id,
                )
            )

        # High priority: root goal + parent task
        for label, entry_id in entries:
            if len(tasks) >= limit:
                break
            await _append_entry(label, entry_id)

        # Optional: include additional shared/inherited/global context (ranked)
        if self.include_additional and len(tasks) < limit:
            content = current_task.parameters.get("content", "") or current_task.action
            query_text = " ".join(
                part for part in [root_content, parent_content, str(content)] if part
            )
            keywords = self._extract_keywords(query_text)
            candidates: list[tuple[float, Any]] = []

            for scope in self.scopes:
                scope_entries = await self.memory.list_by_scope(scope)
                for entry in scope_entries:
                    if entry.id in seen_ids:
                        continue
                    entry_content = str(entry.content or "")
                    if not entry_content:
                        continue
                    score = self._score_entry(entry_content, keywords, entry.scope)
                    candidates.append((score, entry))

            # Rank within scopes
            by_scope: dict[str, list[tuple[float, Any]]] = {
                "shared": [],
                "inherited": [],
                "global": [],
            }
            for score, entry in candidates:
                scope_key = entry.scope.value if hasattr(entry, "scope") else "shared"
                by_scope.setdefault(scope_key, []).append((score, entry))

            for scope_key in by_scope:
                by_scope[scope_key].sort(key=lambda x: x[0], reverse=True)

            remaining = min(limit - len(tasks), self.max_additional)
            if remaining > 0:
                # Per-scope caps to balance signal vs. noise
                weights = [("shared", 0.5), ("inherited", 0.3), ("global", 0.2)]
                caps: dict[str, int] = {}
                used = 0
                for scope_key, weight in weights:
                    cap = int(remaining * weight)
                    cap = min(cap, len(by_scope.get(scope_key, [])))
                    caps[scope_key] = cap
                    used += cap

                # Distribute leftover slots by priority
                leftover = remaining - used
                if leftover > 0:
                    for scope_key, _ in weights:
                        if leftover <= 0:
                            break
                        available = len(by_scope.get(scope_key, [])) - caps.get(scope_key, 0)
                        if available <= 0:
                            continue
                        take = min(available, leftover)
                        caps[scope_key] = caps.get(scope_key, 0) + take
                        leftover -= take

                for scope_key, _ in weights:
                    for _, entry in by_scope.get(scope_key, [])[: caps.get(scope_key, 0)]:
                        await _append_entry(entry.scope.value.upper(), entry.id)

        return tasks

    def _extract_keywords(self, text: str) -> set[str]:
        import re

        if not text:
            return set()
        words = re.findall(r"\w+", text.lower())
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        return {w for w in words if w not in stopwords and len(w) > 2}

    def _score_entry(
        self,
        content: str,
        keywords: set[str],
        scope: "MemoryScope",
    ) -> float:
        scope_weights = {
            "shared": 1.0,
            "inherited": 0.9,
            "global": 0.7,
        }
        scope_weight = scope_weights.get(scope.value, 0.8)

        if not keywords:
            return scope_weight

        content_lower = content.lower()
        hits = sum(1 for kw in keywords if kw in content_lower)
        overlap = hits / max(len(keywords), 1)

        # Penalize overly long entries to avoid bloating context
        length_penalty = 0.0
        if len(content) > 400:
            length_penalty = min(0.2, (len(content) - 400) / 2000)

        return (0.7 * overlap) + (0.3 * scope_weight) - length_penalty


# ==================== 核心管理器 ====================
