"""Context compression strategies - 五道压缩机制

按 token 压力渐进触发：
- Snip Compact (ρ > 0.7): 裁剪过长片段
- Micro Compact (ρ > 0.8): 缓存工具结果
- Context Collapse (ρ > 0.9): 折叠不活跃区域
- Auto Compact (ρ > 0.95): 全量压缩
- Reactive Compact (API 413): 紧急压缩 + 重试

关键原则：每轮只触发一种压缩，按优先级递增；Reactive 由 API 错误触发
"""

from ..types import Message
import math
from collections.abc import Iterable


class ContextCompressor:
    """Context compression with four-level strategy"""

    def __init__(self, micro_max_chars: int = 240, collapse_keep_first: int = 3, collapse_keep_last: int = 5):
        self.thresholds = {
            'snip': 0.7,
            'micro': 0.8,
            'collapse': 0.9,
            'auto': 0.95
        }
        self.micro_max_chars = micro_max_chars
        self.collapse_keep_first = collapse_keep_first
        self.collapse_keep_last = collapse_keep_last

    def should_compress(self, rho: float) -> str | None:
        """Determine which compression to trigger"""
        if rho >= self.thresholds['auto']:
            return 'auto'
        elif rho >= self.thresholds['collapse']:
            return 'collapse'
        elif rho >= self.thresholds['micro']:
            return 'micro'
        elif rho >= self.thresholds['snip']:
            return 'snip'
        return None

    def snip_compact(self, messages: list[Message], max_length: int = 2000) -> list[Message]:
        """Snip Compact: 裁剪过长片段"""
        result = []
        for msg in messages:
            if len(msg.content) > max_length:
                snipped = msg.content[:max_length] + f"\n[...snipped {len(msg.content) - max_length} chars]"
                result.append(Message(role=msg.role, content=snipped))
            else:
                result.append(msg)
        return result

    def micro_compact(self, messages: list[Message]) -> list[Message]:
        """Micro Compact: 基于 tool_use_id 缓存编辑结果"""
        result: list[Message] = []
        seen_by_call_id: dict[str, tuple[str | None, str]] = {}
        seen_by_signature: dict[tuple[str | None, str], str] = {}

        for msg in messages:
            if msg.role != "tool":
                result.append(msg)
                continue

            content = msg.content or ""
            if not content:
                result.append(msg)
                continue

            signature = (msg.name, content)

            if msg.tool_call_id and msg.tool_call_id in seen_by_call_id:
                cached_name, cached_content = seen_by_call_id[msg.tool_call_id]
                if cached_name == msg.name and cached_content == content:
                    result.append(self._cached_tool_message(msg, msg.tool_call_id))
                    continue

            cached_from = seen_by_signature.get(signature)
            if cached_from:
                result.append(self._cached_tool_message(msg, cached_from))
                if msg.tool_call_id:
                    seen_by_call_id[msg.tool_call_id] = signature
                continue

            compacted_content = content
            if len(content) > self.micro_max_chars:
                compacted_content = self._summarize_tool_result(content)

            compacted = Message(
                role=msg.role,
                content=compacted_content,
                tool_call_id=msg.tool_call_id,
                name=msg.name,
            )
            result.append(compacted)

            cache_key = msg.tool_call_id or f"cached:{len(seen_by_signature) + 1}"
            seen_by_signature[signature] = cache_key
            if msg.tool_call_id:
                seen_by_call_id[msg.tool_call_id] = signature

        return result

    def context_collapse(self, messages: list[Message], goal: str) -> list[Message]:
        """Context Collapse: 折叠不活跃区域，保护 system 消息"""
        min_len = self.collapse_keep_first + self.collapse_keep_last + 1
        if len(messages) < min_len:
            return messages

        system_msgs = [m for m in messages if m.role == "system"]
        non_system = [m for m in messages if m.role != "system"]

        if len(non_system) < min_len:
            return messages

        head = non_system[:self.collapse_keep_first]
        tail = non_system[-self.collapse_keep_last:]
        middle = non_system[self.collapse_keep_first:-self.collapse_keep_last]

        collapsed = system_msgs + head + [self._summarize_middle(middle)] + tail
        return collapsed

    def auto_compact(self, messages: list[Message], goal: str) -> list[Message]:
        """Auto Compact: 全量压缩，保留顺序"""
        scored = [(i, msg, self._score_message(msg, goal, i, len(messages)))
                  for i, msg in enumerate(messages)]
        scored.sort(key=lambda x: x[2], reverse=True)
        keep_count = max(5, len(messages) // 2)
        kept_indices = {i for i, _, _ in scored[:keep_count]}
        return [msg for i, msg in enumerate(messages) if i in kept_indices]

    def _score_message(self, msg: Message, goal: str, index: int, total: int) -> float:
        """score(h) = K(h) · rel(h,goal) · e^(-λ·age(h))"""
        K = 1.0  # 不可压缩核
        rel = self._relevance(msg.content, goal)
        age = (total - index) / total
        lambda_decay = 0.5
        return K * rel * math.exp(-lambda_decay * age)

    def _relevance(self, content: str, goal: str) -> float:
        """简单的相关性计算"""
        goal_words = set(goal.lower().split())
        content_words = set(content.lower().split())
        if not goal_words:
            return 0.5
        overlap = len(goal_words & content_words)
        return min(1.0, overlap / len(goal_words))

    def _summarize_middle(self, messages: list[Message]) -> Message:
        """Extractive summary: keep first sentence of each message, truncated."""
        if not messages:
            return Message(role="system", content="[no middle messages]")
        parts = []
        for msg in messages:
            content = (msg.content or "").strip()
            if not content:
                continue
            # first sentence or first 120 chars
            end = min(content.find(". ") + 1 if ". " in content else len(content), 120)
            parts.append(f"[{msg.role}] {content[:end]}")
        summary = " | ".join(parts) if parts else f"[{len(messages)} messages]"
        return Message(role="system", content=f"[collapsed {len(messages)} messages: {summary}]")

    def _cached_tool_message(self, msg: Message, cached_from: str) -> Message:
        """Replace duplicate tool output with a cache reference."""
        label = msg.name or "tool"
        content = f"[cached {label} result from {cached_from}]"
        return Message(
            role="tool",
            content=content,
            tool_call_id=msg.tool_call_id,
            name=msg.name,
        )

    def reactive_compact(self, messages: list[Message], goal: str) -> list[Message]:
        """Reactive Compact: emergency compression triggered by API 413 response.

        Applies auto_compact then snip_compact to aggressively reduce payload size.
        """
        messages = self.auto_compact(messages, goal)
        messages = self.snip_compact(messages, max_length=500)
        return messages

    def _summarize_tool_result(self, content: str) -> str:
        """Keep a short preview while preserving the existence of the full tool output."""
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        preview_source: Iterable[str] = lines if lines else (content.strip(),)
        preview_parts: list[str] = []
        total = 0

        for part in preview_source:
            if not part:
                continue
            remaining = self.micro_max_chars - total
            if remaining <= 0:
                break
            chunk = part[:remaining]
            preview_parts.append(chunk)
            total += len(chunk)
            if len(chunk) < len(part):
                break

        preview = " | ".join(preview_parts).strip()
        if len(preview) > self.micro_max_chars:
            preview = preview[: self.micro_max_chars].rstrip()

        return (
            f"[tool result cached: {len(content)} chars] {preview}"
            if preview
            else f"[tool result cached: {len(content)} chars]"
        )
