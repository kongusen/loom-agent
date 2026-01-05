"""
Context Compression Engine
"""
from typing import List, Dict, Any, Optional, Protocol
from loom.memory.types import MemoryUnit, MemoryType, MemoryTier, MemoryStatus, MemoryQuery
import datetime
import tiktoken


class LLMProvider(Protocol):
    """Protocol for LLM providers used in compression."""
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Any:
        ...

class ContextCompressor:
    """
    Compresses conversation history by:
    1. Summarizing old message chains.
    2. Removing redundant tool call/result pairs if successful.
    3. Preserving critical facts (L4/L3).
    """

    @staticmethod
    def compress_history(
        units: List[MemoryUnit],
        keep_last_n: int = 4
    ) -> List[MemoryUnit]:
        """
        Compress a list of memory units.
        Args:
            units: Sorted list of memory units (Chronological).
            keep_last_n: Number of recent interaction turns to keep uncompressed.
        """
        if not units:
            return []

        # 1. Separate Immutable vs Compressible
        # Immutable: System prompts (handled outside), L4 Facts, Snippets
        # Compressible: L1 Messages, Thoughts, Tool Calls/Results

        immutable = []
        compressible = []

        for u in units:
            if u.tier == MemoryTier.L4_GLOBAL:
                immutable.append(u)
            elif u.type == MemoryType.FACT:
                immutable.append(u)
            else:
                compressible.append(u)

        # 2. Identify Compression Region
        # We want to keep the last N items (or turns) intact.
        if len(compressible) <= keep_last_n:
            return units # precise order might need reconstruction if we split lists.
            # Actually, if we just return units, we are fine.

        if keep_last_n > 0:
            to_compress = compressible[:-keep_last_n]
            kept_recent = compressible[-keep_last_n:]
        else:
            to_compress = compressible
            kept_recent = []

        # 3. Apply Compression Strategies
        compressed_segment = ContextCompressor._compress_segment(to_compress)

        # 4. Reassemble
        # Order: Immutable Facts -> Compressed Summary -> Recent History
        # Note: Original time order should ideally be preserved.
        # But summaries act as a "checkpoint" content.

        result = immutable + compressed_segment + kept_recent

        # Re-sort by time to be safe?
        # Summaries should have timestamp of the LATEST item they summarize.
        result.sort(key=lambda u: u.created_at)

        return result

    @staticmethod
    def _compress_segment(segment: List[MemoryUnit]) -> List[MemoryUnit]:
        """
        Compress a segment of memory units into a summary or simplified form.
        """
        if not segment:
            return []

        summary_text = ""
        tool_counts = {}

        # Iterate and build efficient representation
        for u in segment:
            if u.type == MemoryType.MESSAGE:
                role = u.metadata.get("role", "unknown")
                summary_text += f"{role}: {str(u.content)[:50]}...\n"

            elif u.type == MemoryType.THOUGHT:
                # Discard old thoughts or minimize
                pass

            elif u.type == MemoryType.TOOL_CALL:
                # Count usage
                calls = u.content if isinstance(u.content, list) else [u.content]
                for c in calls:
                    # Content might be the name itself if string, or dict
                    name = "unknown"
                    if isinstance(c, dict):
                        name = c.get("name", "unknown")
                    elif isinstance(c, str):
                        name = "unknown" # Content might be raw string of args?
                        # In agent.py we store list of dicts.

                    # If u.content is just a dict (single call)
                    if isinstance(u.content, dict):
                         name = u.content.get("name", "unknown")
                    elif isinstance(u.content, list):
                         pass # handled by iteration above if c is dict

                    # Better robustness
                    if isinstance(c, dict):
                        name = c.get("name", "unknown")

                    tool_counts[name] = tool_counts.get(name, 0) + 1

        # Create Summary Unit
        summary_content = "Previous Context Summary:\n"
        if summary_text:
            summary_content += summary_text
        if tool_counts:
            summary_content += "Tools used: " + ", ".join([f"{k} ({v})" for k,v in tool_counts.items()])

        summary_unit = MemoryUnit(
            content=summary_content,
            tier=MemoryTier.L2_WORKING, # Summary lives in Working Memory? Or L3?
            type=MemoryType.SUMMARY,
            created_at=segment[-1].created_at, # Timestamp of last item
            importance=0.5
        )

        return [summary_unit]


class MemoryCompressor:
    """
    Advanced memory compression with LLM-based summarization and fact extraction.
    Implements token-threshold-based compression triggers.
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        l1_to_l3_threshold: int = 30,
        l3_to_l4_threshold: int = 50,
        token_threshold: int = 4000,
        enable_llm_summarization: bool = True
    ):
        """
        Initialize the memory compressor.

        Args:
            llm_provider: Optional LLM provider for intelligent summarization
            l1_to_l3_threshold: Number of L1 units before compression
            l3_to_l4_threshold: Number of L3 units before fact extraction
            token_threshold: Token count threshold for triggering compression
            enable_llm_summarization: Whether to use LLM for summarization
        """
        self.llm_provider = llm_provider
        self.l1_to_l3_threshold = l1_to_l3_threshold
        self.l3_to_l4_threshold = l3_to_l4_threshold
        self.token_threshold = token_threshold
        self.enable_llm_summarization = enable_llm_summarization

        # Initialize tokenizer for token counting
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoder = None

    def _count_tokens(self, units: List[MemoryUnit]) -> int:
        """Count total tokens in memory units."""
        if not self.encoder:
            # Fallback: rough estimation
            return sum(len(str(u.content)) // 4 for u in units)

        total = 0
        for unit in units:
            content_str = str(unit.content)
            total += len(self.encoder.encode(content_str))
        return total

    async def compress_l1_to_l3(
        self,
        memory: "LoomMemory",
        session_id: str = "default"
    ) -> Optional[str]:
        """
        Compress L1 raw IO buffer to L3 session summary.

        Args:
            memory: LoomMemory instance
            session_id: Session identifier for grouping

        Returns:
            ID of created summary unit, or None if no compression needed
        """
        # Query L1 messages
        l1_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            types=[MemoryType.MESSAGE, MemoryType.THOUGHT, MemoryType.TOOL_CALL, MemoryType.TOOL_RESULT]
        )
        l1_messages = await memory.query(l1_query)

        # Check if compression is needed
        if len(l1_messages) < self.l1_to_l3_threshold:
            return None

        # Check token count
        token_count = self._count_tokens(l1_messages)
        if token_count < self.token_threshold:
            return None

        # Perform compression
        if self.enable_llm_summarization and self.llm_provider:
            summary_text = await self._summarize_with_llm(l1_messages)
        else:
            summary_text = self._simple_summary(l1_messages)

        # Create L3 summary unit
        summary_unit = MemoryUnit(
            content=summary_text,
            tier=MemoryTier.L3_SESSION,
            type=MemoryType.SUMMARY,
            importance=0.7,
            metadata={
                "session_id": session_id,
                "compressed_count": len(l1_messages),
                "original_tokens": token_count
            }
        )

        summary_id = await memory.add(summary_unit)

        # Mark compressed units as SUMMARIZED
        for unit in l1_messages:
            unit.status = MemoryStatus.SUMMARIZED

        return summary_id

    async def extract_facts_to_l4(
        self,
        memory: "LoomMemory"
    ) -> List[str]:
        """
        Extract facts from L2/L3 and promote to L4 global knowledge.

        Args:
            memory: LoomMemory instance

        Returns:
            List of IDs of created fact units
        """
        # Query L2 and L3 for potential facts
        query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING, MemoryTier.L3_SESSION],
            types=[MemoryType.MESSAGE, MemoryType.SUMMARY, MemoryType.CONTEXT]
        )
        candidates = await memory.query(query)

        if len(candidates) < self.l3_to_l4_threshold:
            return []

        # Extract facts
        if self.enable_llm_summarization and self.llm_provider:
            facts = await self._extract_facts_with_llm(candidates)
        else:
            facts = self._extract_facts_simple(candidates)

        # Create L4 fact units
        fact_ids = []
        for fact_text in facts:
            fact_unit = MemoryUnit(
                content=fact_text,
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.9,
                metadata={"extracted_from": "L2/L3"}
            )
            fact_id = await memory.add(fact_unit)
            fact_ids.append(fact_id)

        return fact_ids

    async def _summarize_with_llm(self, units: List[MemoryUnit]) -> str:
        """Use LLM to create intelligent summary."""
        # Build context from units
        context_parts = []
        for unit in units[:20]:  # Limit to avoid token overflow
            if unit.type == MemoryType.MESSAGE:
                context_parts.append(str(unit.content))
            elif unit.type == MemoryType.TOOL_CALL:
                context_parts.append(f"Tool: {unit.content}")
            elif unit.type == MemoryType.TOOL_RESULT:
                context_parts.append(f"Result: {str(unit.content)[:100]}")

        context_text = "\n".join(context_parts)

        # Create summarization prompt
        messages = [
            {
                "role": "system",
                "content": "You are a memory compression assistant. Summarize the conversation history concisely, preserving key information."
            },
            {
                "role": "user",
                "content": f"Summarize this conversation:\n\n{context_text}"
            }
        ]

        try:
            response = await self.llm_provider.chat(messages, max_tokens=200)
            return getattr(response, "content", str(response))
        except Exception as e:
            # Fallback to simple summary
            return self._simple_summary(units)

    def _simple_summary(self, units: List[MemoryUnit]) -> str:
        """Create rule-based summary."""
        message_count = sum(1 for u in units if u.type == MemoryType.MESSAGE)
        tool_count = sum(1 for u in units if u.type == MemoryType.TOOL_CALL)

        summary = f"Compressed {len(units)} memory units: "
        summary += f"{message_count} messages, {tool_count} tool calls."

        return summary

    async def _extract_facts_with_llm(self, units: List[MemoryUnit]) -> List[str]:
        """Use LLM to extract facts from memory units."""
        # Build context from units
        context_parts = []
        for unit in units[:30]:  # Limit to avoid token overflow
            context_parts.append(str(unit.content)[:200])

        context_text = "\n".join(context_parts)

        # Create fact extraction prompt
        messages = [
            {
                "role": "system",
                "content": "You are a knowledge extraction assistant. Extract key facts from the conversation. Return each fact on a new line."
            },
            {
                "role": "user",
                "content": f"Extract key facts from this conversation:\n\n{context_text}"
            }
        ]

        try:
            response = await self.llm_provider.chat(messages, max_tokens=300)
            content = getattr(response, "content", str(response))
            # Split by newlines and filter empty lines
            facts = [f.strip() for f in content.split("\n") if f.strip()]
            return facts[:10]  # Limit to top 10 facts
        except Exception as e:
            # Fallback to simple extraction
            return self._extract_facts_simple(units)

    def _extract_facts_simple(self, units: List[MemoryUnit]) -> List[str]:
        """Extract facts using simple heuristics."""
        facts = []

        # Look for high-importance units
        for unit in units:
            if unit.importance > 0.8 and unit.type in [MemoryType.MESSAGE, MemoryType.CONTEXT]:
                content_str = str(unit.content)[:100]
                if len(content_str) > 20:  # Skip very short content
                    facts.append(content_str)

        return facts[:5]  # Limit to top 5 facts
