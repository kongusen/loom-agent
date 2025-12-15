"""
Compression 压缩器集成示例 - BaseCompressor Protocol 实现

这是一个集成示例，展示如何实现 BaseCompressor Protocol 来实现上下文压缩。

**使用方式**:
```python
from examples.integrations.compression import StructuredCompressor, CompressionConfig
import loom, create_context_manager
from examples.integrations.openai_llm import OpenAILLM

# 创建压缩器
compressor = StructuredCompressor(
    config=CompressionConfig(threshold=0.9),
    keep_recent=6
)

# 创建带压缩的上下文管理器
context_mgr = create_context_manager(
    max_history=100,
    compressor=compressor
)

# 创建 Agent
llm = OpenAILLM(api_key="sk-...")
agent = loom.agent(
    name="assistant",
    llm=llm,
    context_manager=context_mgr
)
```

**特点**:
- 不依赖 LLM，基于规则的压缩
- 8 段式结构化摘要
- 保留近端消息窗口
- 自动触发压缩
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from loom.core.message import Message
from loom.interfaces.compressor import BaseCompressor


@dataclass
class CompressionConfig:
    """压缩配置

    Attributes:
        threshold: 触发压缩的阈值（token 占比）
        warning_threshold: 警告阈值
        target_ratio: 目标压缩比例
        max_tokens_per_section: 每个段落最大 token 数
    """
    threshold: float = 0.92
    warning_threshold: float = 0.80
    target_ratio: float = 0.75
    max_tokens_per_section: int = 512


class StructuredCompressor(BaseCompressor):
    """简化版 8 段式结构化压缩器

    不依赖 LLM，直观汇总近端消息片段，生成一条 system 摘要消息，并保留近端窗口。

    Example::

        compressor = StructuredCompressor(
            config=CompressionConfig(threshold=0.9),
            keep_recent=6
        )

        # 压缩消息历史
        compressed = await compressor.compress(messages)

        # 检查是否需要压缩
        if compressor.should_compress(token_count, max_tokens):
            compressed = await compressor.compress(messages)
    """

    def __init__(self, config: CompressionConfig | None = None, keep_recent: int = 6) -> None:
        """
        初始化压缩器

        Args:
            config: 压缩配置
            keep_recent: 保留最近 N 条消息
        """
        self.config = config or CompressionConfig()
        self.keep_recent = keep_recent

    async def compress(self, messages: List[Message]) -> List[Message]:
        """
        压缩消息历史

        Args:
            messages: 消息历史

        Returns:
            压缩后的消息列表（摘要 + 近端消息）
        """
        recent = messages[-self.keep_recent :] if self.keep_recent > 0 else []

        # 粗略提取要点：截取用户与助手的近端内容片段
        user_snippets = [m.content for m in messages if m.role == "user"][-3:]
        assistant_snippets = [m.content for m in messages if m.role == "assistant"][-3:]
        tool_snippets = [m.content for m in messages if m.role == "tool"][-5:]

        summary = [
            "# 对话历史压缩摘要",
            f"时间: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "## background_context",
            "- 最近用户/助手对话被压缩为摘要，保留关键近端消息窗口。",
            "",
            "## key_decisions",
            "- 见 assistant 近端结论片段（如有）。",
            "",
            "## tool_usage_log",
            *[f"- {t[:200]}" for t in tool_snippets],
            "",
            "## user_intent_evolution",
            *[f"- {u[:200]}" for u in user_snippets],
            "",
            "## execution_results",
            *[f"- {a[:200]}" for a in assistant_snippets],
            "",
            "## errors_and_solutions",
            "- （占位）如有错误会在此归档。",
            "",
            "## open_issues",
            "- （占位）后续待解问题列表。",
            "",
            "## future_plans",
            "- （占位）下一步行动建议。",
        ]

        compressed_msg = Message(
            role="system",
            content="\n".join(summary),
            metadata={"compressed": True, "compression_time": datetime.now().isoformat()},
        )

        return [compressed_msg, *recent]

    def should_compress(self, token_count: int, max_tokens: int) -> bool:
        """
        检查是否需要压缩

        Args:
            token_count: 当前 token 数
            max_tokens: 最大 token 数

        Returns:
            是否需要压缩
        """
        if max_tokens <= 0:
            return False
        ratio = token_count / max_tokens
        return ratio >= self.config.threshold
