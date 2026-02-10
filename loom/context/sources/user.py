"""
User Input Context Source - 用户输入上下文源

从用户输入获取上下文，优先级最高。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class UserInputSource(ContextSource):
    """
    用户输入源

    用户当前输入是最高优先级的上下文。
    必须包含，不可压缩。
    """

    def __init__(self, user_input: str = ""):
        """
        初始化用户输入源

        Args:
            user_input: 用户输入内容
        """
        self._user_input = user_input

    @property
    def source_name(self) -> str:
        return "user_input"

    def set_input(self, user_input: str) -> None:
        """设置用户输入"""
        self._user_input = user_input

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """
        收集用户输入

        用户输入始终返回，不受相关性阈值影响。
        """
        if not self._user_input:
            return []

        tokens = self._count_tokens(self._user_input, "user", token_counter)

        # 用户输入优先级最高，不可压缩
        block = ContextBlock(
            content=self._user_input,
            role="user",
            token_count=tokens,
            priority=1.0,  # 最高优先级
            source=self.source_name,
            compressible=False,  # 不可压缩
            metadata={"type": "current_input"},
        )

        return [block]
