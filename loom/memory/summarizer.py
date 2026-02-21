"""LLM-based memory compressor — summarizes evicted entries."""

from __future__ import annotations

from ..types import MemoryEntry, LLMProvider, CompletionParams, UserMessage

_PROMPT = "Summarize these conversation fragments into a concise summary. Preserve key facts and decisions.\n\nFragments:\n"


class LLMSummarizer:
    def __init__(self, llm: LLMProvider, tokenizer) -> None:
        self._llm = llm
        self._tok = tokenizer

    async def compress(self, entries: list[MemoryEntry]) -> MemoryEntry:
        body = "\n".join(f"[{i+1}] {e.content}" for i, e in enumerate(entries))
        result = await self._llm.complete(CompletionParams(
            messages=[UserMessage(content=_PROMPT + body)],
            temperature=0, max_tokens=256,
        ))
        content = result.content
        max_imp = max(e.importance for e in entries)
        return MemoryEntry(
            content=content,
            tokens=self._tok.count(content),
            importance=min(1.0, max_imp + 0.1),
            metadata={"compressed": True, "source_count": len(entries)},
        )
