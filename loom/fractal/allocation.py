"""
智能记忆分配策略 (Smart Memory Allocation Strategy)

根据任务特征自动分析和分配最相关的记忆给子节点，避免信息过载，保持O(1)复杂度。

核心组件：
- TaskFeatures: 任务特征数据结构
- TaskAnalyzer: 任务分析器
- SmartAllocationStrategy: 智能分配策略
"""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from loom.fractal.memory import FractalMemory, MemoryEntry, MemoryScope
    from loom.protocol import Task

from loom.fractal.memory import MemoryScope


@dataclass
class TaskFeatures:
    """
    任务特征

    从任务中提取的关键特征，用于智能记忆分配。
    """

    keywords: Set[str]  # 关键词集合
    action_type: str  # 动作类型
    complexity: float  # 复杂度评分 (0-1)
    required_context: Set[str]  # 需要的上下文类型


class TaskAnalyzer:
    """
    任务分析器

    分析任务特征，提取关键词、动作类型、复杂度等信息。
    """

    def analyze(self, task: "Task") -> TaskFeatures:
        """
        分析任务特征

        Args:
            task: 任务对象

        Returns:
            任务特征
        """
        # 提取关键词
        keywords = self._extract_keywords(task.action)

        # 判断动作类型
        action_type = self._classify_action(task.action)

        # 评估复杂度
        complexity = self._estimate_complexity(task)

        # 推断需要的上下文
        required_context = self._infer_required_context(task, keywords)

        return TaskFeatures(
            keywords=keywords,
            action_type=action_type,
            complexity=complexity,
            required_context=required_context,
        )

    def _extract_keywords(self, text: str) -> Set[str]:
        """提取关键词"""
        # 简单实现：分词 + 停用词过滤
        words = re.findall(r"\w+", text.lower())
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
        return {w for w in words if w not in stopwords and len(w) > 2}

    def _classify_action(self, action: str) -> str:
        """分类动作类型"""
        action_lower = action.lower()
        if any(kw in action_lower for kw in ["create", "build", "implement", "add"]):
            return "creation"
        elif any(kw in action_lower for kw in ["fix", "debug", "resolve", "repair"]):
            return "debugging"
        elif any(kw in action_lower for kw in ["analyze", "review", "check", "inspect"]):
            return "analysis"
        else:
            return "general"

    def _estimate_complexity(self, task: "Task") -> float:
        """评估任务复杂度"""
        factors = []

        # 描述长度
        desc_length = len(task.action)
        factors.append(min(desc_length / 200, 1.0))

        # 参数数量
        if hasattr(task, "parameters") and task.parameters:
            factors.append(min(len(task.parameters) / 10, 1.0))

        return sum(factors) / len(factors) if factors else 0.5

    def _infer_required_context(self, task: "Task", keywords: Set[str]) -> Set[str]:
        """推断需要的上下文"""
        context_types = set()

        # 基于关键词推断
        if any(kw in keywords for kw in ["auth", "login", "user", "password"]):
            context_types.add("authentication")
        if any(kw in keywords for kw in ["database", "sql", "query", "data"]):
            context_types.add("database")
        if any(kw in keywords for kw in ["api", "endpoint", "request", "response"]):
            context_types.add("api")

        return context_types


class SmartAllocationStrategy:
    """
    智能记忆分配策略

    根据任务特征自动选择最相关的记忆分配给子节点。
    """

    def __init__(
        self, max_inherited_memories: int = 10, analyzer: Optional[TaskAnalyzer] = None
    ):
        """
        初始化智能分配策略

        Args:
            max_inherited_memories: 最大继承记忆数量（保持O(1)复杂度）
            analyzer: 任务分析器（如果为None，将创建默认实例）
        """
        self.max_inherited_memories = max_inherited_memories
        self.analyzer = analyzer or TaskAnalyzer()

    async def allocate(
        self,
        parent_memory: "FractalMemory",
        child_task: "Task",
        context_hints: Optional[list[str]] = None,
    ) -> dict["MemoryScope", list["MemoryEntry"]]:
        """
        为子节点分配记忆

        Args:
            parent_memory: 父节点的记忆
            child_task: 子任务
            context_hints: 上下文提示（LLM提供的记忆ID列表）

        Returns:
            按作用域组织的记忆条目
        """
        # 1. 如果有context_hints，优先检索这些记忆
        if context_hints:
            selected = await self._allocate_with_hints(parent_memory, context_hints)
        else:
            selected = []

        # 2. 如果hints不足，使用任务特征分析补充
        if len(selected) < self.max_inherited_memories:
            features = self.analyzer.analyze(child_task)
            additional = await self._retrieve_relevant_memories(parent_memory, features)
            selected.extend(additional)

        return {MemoryScope.INHERITED: selected[: self.max_inherited_memories]}

    async def _allocate_with_hints(
        self, parent_memory: "FractalMemory", hints: list[str]
    ) -> list["MemoryEntry"]:
        """使用context_hints分配记忆"""
        selected = []
        for hint in hints:
            entry = await parent_memory.read(
                hint, search_scopes=[MemoryScope.SHARED, MemoryScope.GLOBAL]
            )
            if entry:
                selected.append(entry)
        return selected

    async def _retrieve_relevant_memories(
        self, parent_memory: "FractalMemory", features: TaskFeatures
    ) -> list["MemoryEntry"]:
        """检索相关记忆"""
        # 获取父节点的SHARED和GLOBAL记忆
        shared_memories = await parent_memory.list_by_scope(MemoryScope.SHARED)
        global_memories = await parent_memory.list_by_scope(MemoryScope.GLOBAL)

        all_memories = shared_memories + global_memories

        # 过滤相关记忆
        relevant = [entry for entry in all_memories if self._is_relevant(entry, features)]

        # 按相关性排序
        ranked = self._rank_by_relevance(relevant, features)

        return ranked

    def _is_relevant(self, entry: "MemoryEntry", features: TaskFeatures) -> bool:
        """判断记忆是否相关"""
        if not isinstance(entry.content, str):
            return False

        entry_keywords = set(re.findall(r"\w+", entry.content.lower()))
        overlap = features.keywords & entry_keywords

        # 至少有2个关键词重叠
        return len(overlap) >= 2

    def _rank_by_relevance(
        self, entries: list["MemoryEntry"], features: TaskFeatures
    ) -> list["MemoryEntry"]:
        """按相关性排序"""
        scored_entries = []

        for entry in entries:
            score = self._calculate_relevance_score(entry, features)
            scored_entries.append((score, entry))

        # 按分数降序排序
        scored_entries.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in scored_entries]

    def _calculate_relevance_score(
        self, entry: "MemoryEntry", features: TaskFeatures
    ) -> float:
        """计算相关性分数"""
        score = 0.0

        if not isinstance(entry.content, str):
            return score

        entry_keywords = set(re.findall(r"\w+", entry.content.lower()))
        overlap = features.keywords & entry_keywords

        # 关键词重叠度 (60%)
        if features.keywords:
            score += len(overlap) / len(features.keywords) * 0.6

        # 版本新鲜度 (20%)
        score += min(entry.version / 10, 0.2)

        # 作用域权重 (20%)
        if entry.scope == MemoryScope.GLOBAL:
            score += 0.2

        return score
