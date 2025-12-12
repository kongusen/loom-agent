"""
Context Assembly Module - Stream-First Architecture

Provides intelligent context assembly with priority-based component management,
token budget constraints, and real-time event streaming.

This module fixes the RAG Context Bug where retrieved documents were being
overwritten by system prompts.

Stream-First Architecture:
- Core methods (*_stream) yield AgentEvent instances and are the source of truth
- Convenience methods consume streams internally
- All operations are observable via event streaming
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any, AsyncGenerator
from enum import IntEnum

from loom.core.events import AgentEvent, AgentEventType


class ComponentPriority(IntEnum):
    """
    Component priority levels for context assembly.

    Higher values = higher priority = less likely to be truncated.
    """
    CRITICAL = 100     # Base instructions (must be included)
    HIGH = 90          # RAG context, important configurations
    MEDIUM = 70        # Tool definitions
    LOW = 50           # Examples, additional hints
    OPTIONAL = 30      # Optional content


@dataclass
class ContextComponent:
    """
    A single component of the context.

    Attributes:
        name: Component identifier (e.g., "base_instructions", "retrieved_docs")
        content: The actual content text
        priority: Priority level (0-100)
        token_count: Estimated number of tokens
        truncatable: Whether this component can be truncated
    """
    name: str
    content: str
    priority: int
    token_count: int
    truncatable: bool = True


class ContextAssembler:
    """
    Intelligent context assembler with priority-based management.

    Features:
    - Priority-based component ordering
    - Token budget management
    - Smart truncation of low-priority components
    - Guarantee high-priority component integrity
    - Component caching for performance
    - Dynamic priority adjustment
    - Context reuse optimization

    Example:
        ```python
        assembler = ContextAssembler(max_tokens=4000)

        # Add components with priorities
        assembler.add_component(
            "base_instructions",
            "You are a helpful assistant.",
            priority=ComponentPriority.CRITICAL,
            truncatable=False
        )

        assembler.add_component(
            "retrieved_docs",
            doc_context,
            priority=ComponentPriority.HIGH,
            truncatable=True
        )

        # Assemble final context
        final_prompt = assembler.assemble()
        ```
    """

    def __init__(
        self,
        max_tokens: int = 16000,
        token_counter: Optional[Callable[[str], int]] = None,
        token_buffer: float = 0.9,  # Use 90% of budget for safety
        enable_caching: bool = True,
        cache_size: int = 100
    ):
        """
        Initialize the context assembler.

        Args:
            max_tokens: Maximum token budget
            token_counter: Custom token counting function (defaults to simple estimation)
            token_buffer: Safety buffer ratio (0.9 = use 90% of max_tokens)
            enable_caching: Enable component caching for performance
            cache_size: Maximum number of cached components
        """
        self.max_tokens = int(max_tokens * token_buffer)
        self.token_counter = token_counter or self._estimate_tokens
        self.components: List[ContextComponent] = []
        
        # Performance optimizations
        self.enable_caching = enable_caching
        self._component_cache: Dict[str, ContextComponent] = {}
        self._cache_size = cache_size
        self._assembly_cache: Optional[str] = None
        self._last_components_hash: Optional[str] = None

    # ===== Core Streaming Methods =====

    async def add_component_stream(
        self,
        name: str,
        content: str,
        priority: int,
        truncatable: bool = True
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Add a context component with streaming events (CORE METHOD).

        This is the core implementation. All component additions flow through here.

        Args:
            name: Component identifier (e.g., "base_instructions", "retrieved_docs")
            content: Component content
            priority: Priority level (0-100, higher = more important)
            truncatable: Whether this component can be truncated

        Yields:
            AgentEvent: Streaming events:
                - CONTEXT_ADD_START: Addition started
                - CONTEXT_ADD_COMPLETE: Component added successfully

        Example:
            ```python
            async for event in assembler.add_component_stream(
                "retrieved_docs", doc_content, ComponentPriority.HIGH
            ):
                if event.type == AgentEventType.CONTEXT_ADD_START:
                    print("Adding component...")
                elif event.type == AgentEventType.CONTEXT_ADD_COMPLETE:
                    print(f"Added {event.metadata['component_name']}")
            ```
        """
        # Emit start event
        yield AgentEvent(
            type=AgentEventType.CONTEXT_ADD_START,
            metadata={
                "component_name": name,
                "content_length": len(content) if content else 0,
                "priority": priority,
                "truncatable": truncatable
            }
        )

        # Skip empty content
        if not content or not content.strip():
            yield AgentEvent(
                type=AgentEventType.CONTEXT_ADD_COMPLETE,
                metadata={
                    "component_name": name,
                    "skipped": True,
                    "reason": "empty_content"
                }
            )
            return

        # Count tokens and create component
        token_count = self.token_counter(content)
        component = ContextComponent(
            name=name,
            content=content.strip(),
            priority=priority,
            token_count=token_count,
            truncatable=truncatable
        )
        self.components.append(component)

        # Update cache if enabled
        if self.enable_caching:
            self._component_cache[name] = component
            # Maintain cache size limit
            if len(self._component_cache) > self._cache_size:
                # Remove oldest entries (simple LRU)
                oldest_key = next(iter(self._component_cache))
                del self._component_cache[oldest_key]

        # Emit complete event
        yield AgentEvent(
            type=AgentEventType.CONTEXT_ADD_COMPLETE,
            metadata={
                "component_name": name,
                "priority": priority,
                "token_count": token_count,
                "truncatable": truncatable,
                "total_components": len(self.components),
                "total_tokens": sum(c.token_count for c in self.components)
            }
        )

    def add_component(
        self,
        name: str,
        content: str,
        priority: int,
        truncatable: bool = True
    ) -> None:
        """
        Add a context component (convenience wrapper - SYNCHRONOUS).

        This is a synchronous convenience wrapper for backward compatibility.
        For streaming support, use add_component_stream() instead.

        Note: This method uses asyncio.run() internally which may not work
        if called from an existing async context. In async contexts, use
        add_component_stream() directly.

        Args:
            name: Component identifier (e.g., "base_instructions", "retrieved_docs")
            content: Component content
            priority: Priority level (0-100, higher = more important)
            truncatable: Whether this component can be truncated
        """
        import asyncio

        # Create async wrapper
        async def _add_async():
            async for event in self.add_component_stream(name, content, priority, truncatable):
                pass  # Just consume the stream

        # Try to run in existing loop or create new one
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, we can't use asyncio.run()
            # Just fall back to synchronous behavior for backward compatibility
            if not content or not content.strip():
                return

            token_count = self.token_counter(content)
            component = ContextComponent(
                name=name,
                content=content.strip(),
                priority=priority,
                token_count=token_count,
                truncatable=truncatable
            )
            self.components.append(component)

            if self.enable_caching:
                self._component_cache[name] = component
                if len(self._component_cache) > self._cache_size:
                    oldest_key = next(iter(self._component_cache))
                    del self._component_cache[oldest_key]
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            asyncio.run(_add_async())

    async def assemble_stream(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Assemble the final context from all components with streaming events (CORE METHOD).

        This is the core implementation. All context assembly flows through here.

        Strategy:
        1. Emit CONTEXT_ASSEMBLY_START
        2. Check cache for identical component configuration
        3. Sort components by priority (descending)
        4. Add components until budget is reached
        5. Emit INCLUDED/EXCLUDED/TRUNCATED events for each component
        6. Merge all components into final string
        7. Emit CONTEXT_ASSEMBLY_COMPLETE

        Yields:
            AgentEvent: Streaming events:
                - CONTEXT_ASSEMBLY_START: Assembly started
                - CONTEXT_COMPONENT_INCLUDED: Component included
                - CONTEXT_COMPONENT_EXCLUDED: Component excluded due to budget
                - CONTEXT_COMPONENT_TRUNCATED: Component truncated to fit budget
                - CONTEXT_ASSEMBLY_COMPLETE: Assembly finished (contains assembled context)

        Example:
            ```python
            async for event in assembler.assemble_stream():
                if event.type == AgentEventType.CONTEXT_ASSEMBLY_START:
                    print(f"Assembling {event.metadata['component_count']} components...")
                elif event.type == AgentEventType.CONTEXT_COMPONENT_TRUNCATED:
                    print(f"Truncated: {event.metadata['component_name']}")
                elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
                    context = event.metadata['assembled_context']
            ```
        """
        # Handle empty case
        if not self.components:
            yield AgentEvent(
                type=AgentEventType.CONTEXT_ASSEMBLY_COMPLETE,
                metadata={
                    "assembled_context": "",
                    "component_count": 0,
                    "total_tokens": 0,
                    "budget": self.max_tokens,
                    "utilization": 0.0
                }
            )
            return

        # Check cache if enabled
        if self.enable_caching:
            current_hash = self._get_components_hash()
            if (self._assembly_cache is not None and
                self._last_components_hash == current_hash):
                # Return cached result
                yield AgentEvent(
                    type=AgentEventType.CONTEXT_ASSEMBLY_COMPLETE,
                    metadata={
                        "assembled_context": self._assembly_cache,
                        "component_count": len(self.components),
                        "cached": True
                    }
                )
                return

        # Calculate stats for start event
        total_tokens = sum(c.token_count for c in self.components)
        needs_truncation = total_tokens > self.max_tokens

        # Emit start event
        yield AgentEvent(
            type=AgentEventType.CONTEXT_ASSEMBLY_START,
            metadata={
                "component_count": len(self.components),
                "total_tokens": total_tokens,
                "budget": self.max_tokens,
                "needs_truncation": needs_truncation
            }
        )

        # Sort by priority (highest first)
        sorted_components = sorted(
            self.components,
            key=lambda c: c.priority,
            reverse=True
        )

        # Truncate if over budget
        included_components = []
        budget_remaining = self.max_tokens

        # Phase 1: Process non-truncatable components
        for comp in sorted_components:
            if not comp.truncatable:
                if comp.token_count <= budget_remaining:
                    included_components.append(comp)
                    budget_remaining -= comp.token_count

                    yield AgentEvent(
                        type=AgentEventType.CONTEXT_COMPONENT_INCLUDED,
                        metadata={
                            "component_name": comp.name,
                            "priority": comp.priority,
                            "token_count": comp.token_count,
                            "truncatable": False,
                            "budget_remaining": budget_remaining
                        }
                    )
                else:
                    # Non-truncatable component exceeds budget
                    yield AgentEvent(
                        type=AgentEventType.CONTEXT_COMPONENT_EXCLUDED,
                        metadata={
                            "component_name": comp.name,
                            "priority": comp.priority,
                            "token_count": comp.token_count,
                            "truncatable": False,
                            "reason": "exceeds_budget",
                            "budget_remaining": budget_remaining
                        }
                    )

        # Phase 2: Process truncatable components
        truncatable = [c for c in sorted_components if c.truncatable]

        for comp in truncatable:
            if comp.token_count <= budget_remaining:
                # Include complete component
                included_components.append(comp)
                budget_remaining -= comp.token_count

                yield AgentEvent(
                    type=AgentEventType.CONTEXT_COMPONENT_INCLUDED,
                    metadata={
                        "component_name": comp.name,
                        "priority": comp.priority,
                        "token_count": comp.token_count,
                        "truncatable": True,
                        "budget_remaining": budget_remaining
                    }
                )
            elif budget_remaining > 100:  # Minimum 100 tokens to be useful
                # Truncate and include
                truncated_content = self._truncate_content(
                    comp.content,
                    budget_remaining - 20  # Reserve 20 tokens for "... (truncated)" marker
                )
                truncated_comp = ContextComponent(
                    name=comp.name,
                    content=truncated_content,
                    priority=comp.priority,
                    token_count=self.token_counter(truncated_content),
                    truncatable=comp.truncatable
                )
                included_components.append(truncated_comp)

                yield AgentEvent(
                    type=AgentEventType.CONTEXT_COMPONENT_TRUNCATED,
                    metadata={
                        "component_name": comp.name,
                        "priority": comp.priority,
                        "original_tokens": comp.token_count,
                        "truncated_tokens": truncated_comp.token_count,
                        "reduction": comp.token_count - truncated_comp.token_count,
                        "budget_remaining": 0
                    }
                )

                budget_remaining = 0
                break
            else:
                # Not enough budget, exclude
                yield AgentEvent(
                    type=AgentEventType.CONTEXT_COMPONENT_EXCLUDED,
                    metadata={
                        "component_name": comp.name,
                        "priority": comp.priority,
                        "token_count": comp.token_count,
                        "truncatable": True,
                        "reason": "insufficient_budget",
                        "budget_remaining": budget_remaining
                    }
                )

        # Merge components
        sections = []
        for component in included_components:
            # Add section header and content
            header = f"# {component.name.replace('_', ' ').upper()}"
            sections.append(f"{header}\n{component.content}")

        result = "\n\n".join(sections)

        # Update cache if enabled
        if self.enable_caching:
            self._assembly_cache = result
            self._last_components_hash = self._get_components_hash()

        # Emit complete event
        final_tokens = sum(c.token_count for c in included_components)
        utilization = (final_tokens / self.max_tokens) if self.max_tokens > 0 else 0.0

        yield AgentEvent(
            type=AgentEventType.CONTEXT_ASSEMBLY_COMPLETE,
            metadata={
                "assembled_context": result,
                "component_count": len(self.components),
                "included_count": len(included_components),
                "excluded_count": len(self.components) - len(included_components),
                "total_tokens": final_tokens,
                "budget": self.max_tokens,
                "utilization": round(utilization, 4),
                "cached": False
            }
        )

    def assemble(self) -> str:
        """
        Assemble the final context from all components (convenience wrapper - SYNCHRONOUS).

        This is a synchronous convenience wrapper for backward compatibility.
        For streaming support, use assemble_stream() instead.

        Note: This method uses asyncio.run() internally which may not work
        if called from an existing async context. In async contexts, use
        assemble_stream() directly.

        Returns:
            Assembled context string
        """
        import asyncio

        # Create async wrapper
        async def _assemble_async():
            result = ""
            async for event in self.assemble_stream():
                if event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
                    result = event.metadata.get("assembled_context", "")
            return result

        # Try to run in existing loop or create new one
        try:
            loop = asyncio.get_running_loop()
            # If we're in an async context, fall back to synchronous behavior
            if not self.components:
                return ""

            # Check cache
            if self.enable_caching:
                current_hash = self._get_components_hash()
                if (self._assembly_cache is not None and
                    self._last_components_hash == current_hash):
                    return self._assembly_cache

            # Sort and assemble (simplified sync version)
            sorted_components = sorted(
                self.components,
                key=lambda c: c.priority,
                reverse=True
            )

            total_tokens = sum(c.token_count for c in sorted_components)
            if total_tokens > self.max_tokens:
                sorted_components = self._truncate_components(sorted_components)

            sections = []
            for component in sorted_components:
                header = f"# {component.name.replace('_', ' ').upper()}"
                sections.append(f"{header}\n{component.content}")

            result = "\n\n".join(sections)

            if self.enable_caching:
                self._assembly_cache = result
                self._last_components_hash = self._get_components_hash()

            return result
        except RuntimeError:
            # No running loop, safe to use asyncio.run()
            return asyncio.run(_assemble_async())

    async def clear_stream(self) -> AsyncGenerator[AgentEvent, None]:
        """
        Clear all components with streaming events (CORE METHOD).

        Yields:
            AgentEvent: Streaming events:
                - CONTEXT_CLEAR_START: Clear started
                - CONTEXT_CLEAR_COMPLETE: All components cleared

        Example:
            ```python
            async for event in assembler.clear_stream():
                if event.type == AgentEventType.CONTEXT_CLEAR_START:
                    print("Clearing context...")
                elif event.type == AgentEventType.CONTEXT_CLEAR_COMPLETE:
                    print(f"Cleared {event.metadata['components_cleared']} components")
            ```
        """
        # Emit start event
        components_before = len(self.components)
        yield AgentEvent(
            type=AgentEventType.CONTEXT_CLEAR_START,
            metadata={"component_count": components_before}
        )

        # Clear components
        self.components.clear()

        # Clear caches
        if self.enable_caching:
            self._component_cache.clear()
            self._assembly_cache = None
            self._last_components_hash = None

        # Emit complete event
        yield AgentEvent(
            type=AgentEventType.CONTEXT_CLEAR_COMPLETE,
            metadata={
                "components_cleared": components_before,
                "components_remaining": len(self.components)
            }
        )

    async def adjust_priority_stream(
        self, component_name: str, new_priority: int
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Dynamically adjust component priority with streaming events (CORE METHOD).

        Args:
            component_name: Name of the component to adjust
            new_priority: New priority value

        Yields:
            AgentEvent: Streaming events:
                - CONTEXT_ADJUST_PRIORITY: Priority adjusted (or not found)

        Example:
            ```python
            async for event in assembler.adjust_priority_stream("retrieved_docs", 95):
                if event.type == AgentEventType.CONTEXT_ADJUST_PRIORITY:
                    if event.metadata['success']:
                        print(f"Adjusted priority to {event.metadata['new_priority']}")
            ```
        """
        # Search for component
        found = False
        old_priority = None

        for component in self.components:
            if component.name == component_name:
                old_priority = component.priority
                component.priority = new_priority
                found = True

                # Clear cache since configuration changed
                if self.enable_caching:
                    self._assembly_cache = None
                    self._last_components_hash = None
                break

        # Emit event
        if found:
            yield AgentEvent(
                type=AgentEventType.CONTEXT_ADJUST_PRIORITY,
                metadata={
                    "component_name": component_name,
                    "old_priority": old_priority,
                    "new_priority": new_priority,
                    "success": True
                }
            )
        else:
            yield AgentEvent(
                type=AgentEventType.CONTEXT_ADJUST_PRIORITY,
                metadata={
                    "component_name": component_name,
                    "new_priority": new_priority,
                    "success": False,
                    "reason": "component_not_found"
                }
            )

    # ===== Convenience Wrappers =====

    def clear(self) -> None:
        """Clear all components (convenience wrapper - SYNCHRONOUS)."""
        import asyncio

        async def _clear_async():
            async for event in self.clear_stream():
                pass  # Just consume the stream

        try:
            loop = asyncio.get_running_loop()
            # In async context, fall back to sync
            self.components.clear()
            if self.enable_caching:
                self._component_cache.clear()
                self._assembly_cache = None
                self._last_components_hash = None
        except RuntimeError:
            asyncio.run(_clear_async())

    def adjust_priority(self, component_name: str, new_priority: int) -> bool:
        """
        Dynamically adjust component priority (convenience wrapper - SYNCHRONOUS).

        Args:
            component_name: Name of the component to adjust
            new_priority: New priority value

        Returns:
            True if component was found and adjusted, False otherwise
        """
        import asyncio

        async def _adjust_async():
            success = False
            async for event in self.adjust_priority_stream(component_name, new_priority):
                if event.type == AgentEventType.CONTEXT_ADJUST_PRIORITY:
                    success = event.metadata.get("success", False)
            return success

        try:
            loop = asyncio.get_running_loop()
            # In async context, fall back to sync
            for component in self.components:
                if component.name == component_name:
                    component.priority = new_priority
                    if self.enable_caching:
                        self._assembly_cache = None
                        self._last_components_hash = None
                    return True
            return False
        except RuntimeError:
            return asyncio.run(_adjust_async())

    # ===== Private Helper Methods =====

    def _get_components_hash(self) -> str:
        """
        Generate hash for current component configuration

        优化版本：
        - 使用 blake2b 替代 MD5（更快）
        - 直接update字节而非拼接字符串
        - 移除不必要的排序
        """
        # 使用 blake2b，比 MD5 更快且安全
        hasher = hashlib.blake2b(digest_size=16)

        # 直接更新hasher，避免字符串拼接
        for comp in self.components:
            hasher.update(comp.name.encode())
            hasher.update(str(comp.priority).encode())
            hasher.update(str(comp.token_count).encode())
            hasher.update(b'1' if comp.truncatable else b'0')

        return hasher.hexdigest()

    def get_component_stats(self) -> Dict[str, Any]:
        """Get statistics about current components"""
        if not self.components:
            return {"total_components": 0, "total_tokens": 0}
        
        total_tokens = sum(c.token_count for c in self.components)
        priority_distribution = {}
        
        for comp in self.components:
            priority_distribution[comp.priority] = priority_distribution.get(comp.priority, 0) + 1
        
        return {
            "total_components": len(self.components),
            "total_tokens": total_tokens,
            "budget_utilization": total_tokens / self.max_tokens if self.max_tokens > 0 else 0,
            "priority_distribution": priority_distribution,
            "cache_enabled": self.enable_caching,
            "cache_size": len(self._component_cache) if self.enable_caching else 0
        }

    def clear_cache(self) -> None:
        """Clear all caches"""
        if self.enable_caching:
            self._component_cache.clear()
            self._assembly_cache = None
            self._last_components_hash = None

    def _truncate_components(
        self,
        components: List[ContextComponent]
    ) -> List[ContextComponent]:
        """
        Intelligently truncate components to fit token budget.

        Strategy:
        1. Always include non-truncatable components
        2. Add truncatable components by priority
        3. Truncate lower-priority components if needed

        Args:
            components: Sorted list of components (by priority, descending)

        Returns:
            List of components that fit within budget
        """
        budget_remaining = self.max_tokens
        result = []

        # Phase 1: Add all non-truncatable components
        for comp in components:
            if not comp.truncatable:
                if comp.token_count <= budget_remaining:
                    result.append(comp)
                    budget_remaining -= comp.token_count
                else:
                    # Non-truncatable component is too large
                    print(
                        f"Warning: Non-truncatable component '{comp.name}' "
                        f"({comp.token_count} tokens) exceeds remaining budget "
                        f"({budget_remaining} tokens). Skipping."
                    )

        # Phase 2: Add truncatable components
        truncatable = [c for c in components if c.truncatable]

        for comp in truncatable:
            if comp.token_count <= budget_remaining:
                # Add complete component
                result.append(comp)
                budget_remaining -= comp.token_count
            elif budget_remaining > 100:  # Minimum 100 tokens to be useful
                # Truncate and add
                truncated_content = self._truncate_content(
                    comp.content,
                    budget_remaining - 20  # Reserve 20 tokens for "... (truncated)" marker
                )
                truncated_comp = ContextComponent(
                    name=comp.name,
                    content=truncated_content,
                    priority=comp.priority,
                    token_count=self.token_counter(truncated_content),
                    truncatable=comp.truncatable
                )
                result.append(truncated_comp)
                budget_remaining = 0
                break
            else:
                # Not enough budget left, skip remaining components
                break

        return result

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """
        Truncate content to fit within token limit.

        Strategy: Proportional character truncation with conservative estimation

        Args:
            content: Content to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated content with marker
        """
        current_tokens = self.token_counter(content)

        if current_tokens <= max_tokens:
            return content

        # Calculate target character count (conservative)
        ratio = max_tokens / current_tokens
        target_chars = int(len(content) * ratio * 0.95)  # 5% safety margin

        if target_chars < 100:
            # Too small to be useful
            return ""

        # Truncate and add marker
        truncated = content[:target_chars].rsplit(' ', 1)[0]  # Truncate at word boundary
        return f"{truncated}\n\n... (truncated due to token limit)"

    def _estimate_tokens(self, text: str) -> int:
        """
        Simple token estimation.

        Rule of thumb: 1 token ≈ 4 characters for English text
        This is a conservative estimate that works reasonably well.

        For precise counting, use a model-specific tokenizer.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def get_summary(self) -> Dict:
        """
        Get assembly summary for debugging and monitoring.

        Returns:
            Dictionary containing:
            - components: List of component info (name, priority, tokens, truncatable)
            - total_tokens: Sum of all component tokens
            - budget: Maximum token budget
            - overflow: Tokens over budget (0 if within budget)
            - utilization: Budget utilization percentage
        """
        total_tokens = sum(c.token_count for c in self.components)
        overflow = max(0, total_tokens - self.max_tokens)
        utilization = (total_tokens / self.max_tokens * 100) if self.max_tokens > 0 else 0

        return {
            "components": [
                {
                    "name": c.name,
                    "priority": c.priority,
                    "tokens": c.token_count,
                    "truncatable": c.truncatable
                }
                for c in sorted(self.components, key=lambda x: x.priority, reverse=True)
            ],
            "total_tokens": total_tokens,
            "budget": self.max_tokens,
            "overflow": overflow,
            "utilization": round(utilization, 2)
        }

    def clear(self) -> None:
        """Clear all components."""
        self.components.clear()

    def __len__(self) -> int:
        """Return number of components."""
        return len(self.components)

    def __repr__(self) -> str:
        """String representation."""
        summary = self.get_summary()
        return (
            f"ContextAssembler(components={len(self.components)}, "
            f"tokens={summary['total_tokens']}/{summary['budget']}, "
            f"utilization={summary['utilization']}%)"
        )
