"""
Agent Output Context Source - Agent输出上下文源

从当前对话轮次的Agent输出获取上下文。
"""

from typing import TYPE_CHECKING

from loom.context.block import ContextBlock
from loom.context.source import ContextSource

if TYPE_CHECKING:
    from loom.memory.tokenizer import TokenCounter


class AgentOutputSource(ContextSource):
    """
    Agent输出源

    当前对话轮次中Agent的输出。
    与Memory不同，这是实时的、未持久化的输出。
    """

    def __init__(self):
        """初始化Agent输出源"""
        self._outputs: list[dict] = []

    @property
    def source_name(self) -> str:
        return "agent_output"

    def add_output(
        self,
        content: str,
        output_type: str = "message",
        metadata: dict | None = None,
    ) -> None:
        """
        添加Agent输出

        Args:
            content: 输出内容
            output_type: 输出类型 (message, thinking, tool_call)
            metadata: 额外元数据
        """
        self._outputs.append(
            {
                "content": content,
                "type": output_type,
                "metadata": metadata or {},
            }
        )

    def clear(self) -> None:
        """清空输出"""
        self._outputs.clear()

    async def collect(
        self,
        query: str,
        token_budget: int,
        token_counter: "TokenCounter",
        min_relevance: float = 0.5,
    ) -> list[ContextBlock]:
        """收集Agent输出"""
        if not self._outputs:
            return []

        blocks: list[ContextBlock] = []
        current_tokens = 0
        total = len(self._outputs)

        for idx, output in enumerate(reversed(self._outputs)):
            content = output["content"]
            if not content:
                continue

            tokens = self._count_tokens(content, "assistant", token_counter)
            if current_tokens + tokens > token_budget:
                break

            # 越近的输出优先级越高
            priority = 0.9 - (idx / max(total, 1)) * 0.3

            block = ContextBlock(
                content=content,
                role="assistant",
                token_count=tokens,
                priority=priority,
                source=self.source_name,
                compressible=True,
                metadata={
                    "type": output["type"],
                    **output["metadata"],
                },
            )
            blocks.append(block)
            current_tokens += tokens

        return blocks
