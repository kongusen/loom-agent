"""
Knowledge Context Source - 智能 RAG 实现

提供按需查询的知识上下文，支持：
1. 智能缓存检查（避免重复查询）
2. 按需查询（根据任务内容）
3. Fractal Memory 集成（父子节点共享）
"""

from typing import TYPE_CHECKING, Any

from loom.memory.task_context import ContextSource

if TYPE_CHECKING:
    from loom.memory.manager import MemoryManager
    from loom.protocol import Task
    from loom.providers.knowledge.base import KnowledgeBaseProvider


class KnowledgeContextSource(ContextSource):
    """
    知识上下文源 - 智能 RAG 实现

    工作流程：
    1. 检查 MemoryManager 中是否有相关知识（缓存）
    2. 如果有缓存，直接使用
    3. 如果没有，查询知识库
    4. 将查询结果缓存到 MemoryManager（供子节点使用）
    """

    def __init__(
        self,
        knowledge_base: "KnowledgeBaseProvider",
        memory: "MemoryManager | None" = None,
        max_items: int = 3,
        relevance_threshold: float = 0.7,
    ):
        """
        初始化知识上下文源

        Args:
            knowledge_base: 知识库提供者
            memory: 记忆管理器（可选，用于缓存）
            max_items: 最大知识条目数
            relevance_threshold: 相关度阈值（0.0-1.0）
        """
        self.knowledge_base = knowledge_base
        self._memory = memory
        self.max_items = max_items
        self.relevance_threshold = relevance_threshold

    async def get_context(
        self,
        current_task: "Task",
        max_items: int | None = None,
    ) -> list["Task"]:
        """
        获取知识上下文（智能 RAG）

        Args:
            current_task: 当前任务对象
            max_items: 最大返回数量（可选，默认使用实例的max_items）

        Returns:
            知识上下文Task列表
        """
        from loom.protocol import Task

        # 使用传入的max_items，如果没有传入则使用实例的max_items
        limit = max_items if max_items is not None else self.max_items

        task_content = current_task.parameters.get("content", "")
        if not task_content:
            return []

        tasks: list[Task] = []

        # 1. 检查 Fractal Memory 缓存
        cached_knowledge = await self._check_cache(task_content)
        if cached_knowledge:
            # 使用缓存的知识
            for knowledge in cached_knowledge:
                tasks.append(
                    Task(
                        task_id=f"knowledge:cached:{knowledge.get('id', 'unknown')}",
                        action="node.message",
                        parameters={
                            "content": f"📚 Cached Knowledge: {knowledge['content']}\n"
                            f"(Source: {knowledge['source']}, Cached)",
                            "context_role": "system",
                        },
                        session_id=current_task.session_id,
                    )
                )
            return tasks

        # 2. 查询知识库（按需查询）
        knowledge_items = await self.knowledge_base.query(query=task_content, limit=limit)

        # 3. 过滤低相关度的知识
        filtered_items = [
            item for item in knowledge_items if item.relevance >= self.relevance_threshold
        ]

        # 4. 转换为Task对象
        for item in filtered_items:
            tasks.append(
                Task(
                    task_id=f"knowledge:{item.id}",
                    action="node.message",
                    parameters={
                        "content": f"📚 Domain Knowledge: {item.content}\n"
                        f"(Source: {item.source}, Relevance: {item.relevance:.2f})",
                        "context_role": "system",
                    },
                    session_id=current_task.session_id,
                )
            )

        # 5. 缓存到 Fractal Memory（供子节点使用）
        await self._cache_knowledge(task_content, filtered_items)

        return tasks

    async def _check_cache(self, query: str) -> list[dict[str, Any]] | None:
        """
        检查 Fractal Memory 中是否有相关知识

        Args:
            query: 查询内容

        Returns:
            缓存的知识列表，如果没有则返回 None
        """
        if not self._memory:
            return None

        # 生成缓存键（基于查询内容的哈希）
        import hashlib

        from loom.fractal.memory import MemoryScope

        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        cache_key = f"knowledge:query:{query_hash}"

        # 从 INHERITED 和 SHARED 作用域查询
        cached = await self._memory.read(
            cache_key, search_scopes=[MemoryScope.INHERITED, MemoryScope.SHARED]
        )

        if cached is not None and hasattr(cached, "content"):
            import json
            from typing import cast

            try:
                return cast(list[dict[str, Any]], json.loads(cached.content))
            except (json.JSONDecodeError, TypeError):
                return None

        return None

    async def _cache_knowledge(self, query: str, knowledge_items: list[Any]) -> None:
        """
        将查询结果缓存到 Fractal Memory

        Args:
            query: 查询内容
            knowledge_items: 知识条目列表
        """
        if not self._memory or not knowledge_items:
            return

        import hashlib
        import json

        from loom.fractal.memory import MemoryScope

        # 生成缓存键
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        cache_key = f"knowledge:query:{query_hash}"

        # 序列化知识条目
        cached_data = [
            {
                "id": item.id,
                "content": item.content,
                "source": item.source,
                "relevance": item.relevance,
            }
            for item in knowledge_items
        ]

        # 写入 SHARED 作用域（子节点可继承）
        await self._memory.write(
            cache_key, json.dumps(cached_data, ensure_ascii=False), scope=MemoryScope.SHARED
        )
