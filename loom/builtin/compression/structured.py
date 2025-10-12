from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from loom.core.types import Message
from loom.interfaces.compressor import BaseCompressor
from loom.utils.token_counter import count_messages_tokens


@dataclass
class CompressionConfig:
    threshold: float = 0.92
    warning_threshold: float = 0.80
    target_ratio: float = 0.75
    max_tokens_per_section: int = 512


class StructuredCompressor(BaseCompressor):
    """简化版 8 段式结构化压缩器。

    不依赖 LLM，直观汇总近端消息片段，生成一条 system 摘要消息，并保留近端窗口。
    """

    def __init__(self, config: CompressionConfig | None = None, keep_recent: int = 6) -> None:
        self.config = config or CompressionConfig()
        self.keep_recent = keep_recent

    async def compress(self, messages: List[Message]) -> List[Message]:
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
        if max_tokens <= 0:
            return False
        ratio = token_count / max_tokens
        return ratio >= self.config.threshold

