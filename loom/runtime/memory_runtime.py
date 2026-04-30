"""Memory coordination runtime extracted from AgentEngine internals."""

from __future__ import annotations

import logging
from typing import Any

from ..memory.semantic import MemoryEntry, SemanticMemory
from ..types import Message

logger = logging.getLogger(__name__)


class MemoryRuntime:
    """Owns session/semantic/provider memory lifecycle for runs."""

    def __init__(
        self,
        *,
        context_manager: Any,
        memory_store: Any,
        memory_providers: list[Any],
        semantic_memory: SemanticMemory | None,
    ) -> None:
        self.context_manager = context_manager
        self.memory_store = memory_store
        self.memory_providers = memory_providers
        self.semantic_memory = semantic_memory

    def load_session_memory(self, session_id: str) -> None:
        memory_data = self.memory_store.load(session_id)
        if memory_data and "memory" in memory_data:
            for msg_dict in memory_data["memory"]:
                self.context_manager.partitions.memory.append(Message(**msg_dict))

    def save_session_memory(self, session_id: str) -> None:
        memory_data = {
            "memory": [
                {"role": msg.role, "content": msg.content}
                for msg in self.context_manager.partitions.memory
            ]
        }
        self.memory_store.save(session_id, memory_data)

    def inject_semantic_memories(self, goal: str) -> None:
        if not self.semantic_memory:
            return
        relevant = self.semantic_memory.search(goal, top_k=5)
        for entry in relevant:
            self.context_manager.partitions.memory.append(
                Message(role="system", content=f"[recalled] {entry.content}")
            )

    def provider_system_prompt(self) -> str:
        blocks: list[str] = []
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                block = provider.system_prompt()
            except Exception as exc:
                self._log_memory_provider_error(provider, "system_prompt", exc)
                continue
            if block.strip():
                blocks.append(block.strip())
        return "\n\n".join(blocks)

    def inject_provider_memories(self, goal: str, session_id: str | None) -> None:
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                recalled = provider.prefetch(goal, session_id=session_id)
            except Exception as exc:
                self._log_memory_provider_error(provider, "prefetch", exc)
                continue
            if recalled.strip():
                self.context_manager.partitions.memory.append(
                    Message(
                        role="system",
                        content=f"[memory:{self._memory_provider_name(provider)}] {recalled}",
                    )
                )

    def sync_memory_providers(
        self,
        user_content: str,
        assistant_content: str,
        session_id: str | None,
    ) -> None:
        if not assistant_content:
            return
        for provider in self.memory_providers:
            if not self._is_memory_provider_available(provider):
                continue
            try:
                provider.sync_turn(
                    user_content,
                    assistant_content,
                    session_id=session_id,
                )
            except Exception as exc:
                self._log_memory_provider_error(provider, "sync_turn", exc)

    def remember_tool_result(self, *, content: Any, tool_name: str | None, iteration: int) -> None:
        if not (self.semantic_memory and isinstance(content, str) and content):
            return
        self.semantic_memory.add(
            MemoryEntry(
                content=content,
                metadata={
                    "tool": tool_name,
                    "iteration": iteration,
                    "goal": self.context_manager.current_goal or "",
                },
            )
        )

    def _is_memory_provider_available(self, provider: Any) -> bool:
        try:
            return bool(provider.is_available())
        except Exception as exc:
            self._log_memory_provider_error(provider, "is_available", exc)
            return False

    def _log_memory_provider_error(
        self,
        provider: Any,
        operation: str,
        exc: Exception,
    ) -> None:
        logger.warning(
            "Memory provider %s failed during %s: %s",
            self._memory_provider_name(provider),
            operation,
            exc,
        )

    def _memory_provider_name(self, provider: Any) -> str:
        try:
            return str(getattr(provider, "name", type(provider).__name__))
        except Exception:
            return type(provider).__name__
