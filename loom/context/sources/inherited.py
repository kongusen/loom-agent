"""
Inherited Context Source - 继承上下文源

从 Fractal Memory 的 INHERITED/SHARED/GLOBAL 作用域获取上下文。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.fractal.memory import MemoryScope
    from loom.memory.manager import MemoryManager
    from loom.memory.tokenizer import TokenCounter


class InheritedSource(ContextSource):
    """
    继承上下文源

    从 MemoryManager 的作用域记忆中获取：
    - INHERITED: 从父节点继承的上下文
    - SHARED: 当前节点共享的上下文
    - GLOBAL: 全局上下文
    """

    def __init__(
        self,
        memory: "MemoryManager",
        scopes: list["MemoryScope"] | None = None,
    ):
        """
        初始化继承源

        Args:
            memory: 记忆管理器
            scopes: 要搜索的作用域列表
        """
        self.memory = memory
        self._scopes = scopes

    @property
    def source_name(self) -> str:
        return "INHERITED"

    @property
    def scopes(self) -> list["MemoryScope"]:
        """获取作用域列表"""
        if self._scopes:
            return self._scopes

        from loom.fractal.memory import MemoryScope
        return [MemoryScope.INHERITED, MemoryScope.SHARED, MemoryScope.GLOBAL]

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集继承上下文"""
        blocks: list[ContextBlock] = []
        current_tokens = 0

        # 作用域优先级权重
        scope_weights = {
            "inherited": 0.9,
            "shared": 1.0,
            "global": 0.7,
        }

        for scope in self.scopes:
            if current_tokens >= token_budget:
                break

            try:
                entries = await self.memory.list_context()
            except Exception:
                continue

            for entry in entries:
                if current_tokens >= token_budget:
                    break

                content = str(entry.content) if entry.content else ""
                if not content:
                    continue

                # 计算 token
                tokens = self._count_tokens(content, "system", token_counter)

                # 检查预算
                if current_tokens + tokens > token_budget:
                    continue

                # 优先级基于作用域
                scope_key = scope.value if hasattr(scope, "value") else str(scope)
                priority = scope_weights.get(scope_key, 0.5)

                block = ContextBlock(
                    content=f"[{scope_key.upper()}] {content}",
                    role="system",
                    token_count=tokens,
                    priority=priority,
                    source=self.source_name,
                    compressible=True,
                    metadata={
                        "entry_id": entry.id,
                        "scope": scope_key,
                    },
                )

                blocks.append(block)
                current_tokens += tokens

        return blocks
