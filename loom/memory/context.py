"""
LoomContext - Context Assembly Engine
"""
from typing import List, Dict, Any, Optional
import tiktoken

from .core import LoomMemory
from .types import MemoryUnit, MemoryTier, MemoryType
from loom.config.memory import ContextConfig, CurationConfig
from .strategies import (
    CurationStrategy,
    StrategyFactory
)
from .compression import ContextCompressor, MemoryCompressor


class ContextAssembler:
    """
    Assembles memory units into an LLM-compatible prompt.
    Handles curation, token budgeting, and formatting.
    """
    
    def __init__(
        self,
        config: Optional[ContextConfig] = None,
        llm_provider: Optional[Any] = None
    ):
        self.config = config or ContextConfig()
        self.strategy = StrategyFactory.create(self.config.strategy)

        # Initialize Tokenizer (Default to cl100k_base for GPT-4)
        try:
            self.encoder = tiktoken.get_encoding(self.config.tokenizer_encoding)
        except:
             self.encoder = tiktoken.get_encoding("cl100k_base")

        # Initialize Memory Compressor
        self.compressor = MemoryCompressor(
            llm_provider=llm_provider,
            token_threshold=self.config.curation_config.max_tokens // 2
        )
    
    async def assemble(
        self,
        memory: LoomMemory,
        task: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Main entry point to build the context.
        """

        # 1. Curate
        curated_units = await self.strategy.curate(
            memory,
            self.config.curation_config,
            task_context=task
        )
        
        # 1.5 Compression (Token-based trigger)
        # Sort by time first to enable linear compression
        curated_units.sort(key=lambda u: u.created_at)

        # Check if we need compression using token count
        token_count = self.compressor._count_tokens(curated_units)
        if token_count > self.compressor.token_threshold:
            # Compress history
            curated_units = ContextCompressor.compress_history(curated_units)

            # Add system notification about compression
            from .types import MemoryUnit, MemoryTier, MemoryType
            notification = MemoryUnit(
                content=f"📦 System Notification: History compacted ({token_count} tokens compressed)",
                tier=MemoryTier.L3_SESSION,
                type=MemoryType.CONTEXT,
                importance=0.6
            )
            curated_units.insert(0, notification)

        # 2. Sort by Importance (For Budgeting Priority)
        # We want high importance items first in priority.
        curated_units.sort(
            key=lambda u: (u.importance, u.created_at),
            reverse=True
        )
        
        # 3. Budgeting & Selection (Dynamic)
        selected_units = []
        current_tokens = 0

        # Calculate dynamic budget based on task complexity
        max_tokens = self._calculate_dynamic_budget(task, memory)

        # Reserve space for system prompt
        if system_prompt:
             current_tokens += self._count_tokens_str(system_prompt)
        
        for unit in curated_units:
            msg = unit.to_message()
            msg_tokens = self._count_tokens_msg(msg)
            
            if current_tokens + msg_tokens > max_tokens:
                continue # Skip if over budget (greedy approach)
            
            selected_units.append(unit)
            current_tokens += msg_tokens
            
        # 4. Final Ordering (Cache-Aware)
        # Static/Long-term content first (System -> L4 -> L3 -> L2 -> L1)
        # This increases KV cache hit rate for persistent prefixes.
        if self.config.enable_prompt_caching:
            selected_units.sort(
                key=lambda u: (u.tier.value, u.created_at)
            )
        else:
            # Default chronological
            selected_units.sort(key=lambda u: u.created_at)
            
        # 5. Convert to Messages
        messages = []
        
        # System Prompt
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
            
        # Add Units
        for unit in selected_units:
            messages.append(unit.to_message())
            
        # Add Snippet Hint (Progressive Disclosure)
        if self.config.curation_config.use_snippets:
            load_hint = self._build_load_hint(selected_units)
            if load_hint:
                # Insert hint after system prompt
                insert_idx = 1 if system_prompt else 0
                messages.insert(insert_idx, {
                    "role": "system",
                    "content": load_hint
                })

        # 6. Insert cache boundaries for prompt caching optimization
        messages = self._insert_cache_boundaries(messages, selected_units)

        return messages
    
    def _count_tokens_msg(self, message: Dict[str, str]) -> int:
        """Count tokens in a message dict."""
        text = str(message.get("content", ""))
        return len(self.encoder.encode(text))

    def _count_tokens_str(self, text: str) -> int:
        """Count tokens in a string."""
        return len(self.encoder.encode(text))

    def _calculate_dynamic_budget(self, task: str, memory: LoomMemory) -> int:
        """
        Calculate dynamic token budget based on task complexity and context.

        Args:
            task: The task description
            memory: LoomMemory instance

        Returns:
            Adjusted token budget
        """
        base_budget = self.config.curation_config.max_tokens

        # Increase budget for complex tasks
        complexity_indicators = [
            "analyze", "refactor", "debug", "explain", "implement",
            "design", "architect", "optimize", "review"
        ]
        task_lower = task.lower() if task else ""
        complexity_matches = sum(1 for indicator in complexity_indicators if indicator in task_lower)

        if complexity_matches >= 2:
            base_budget = int(base_budget * 1.5)  # 50% increase for very complex tasks
        elif complexity_matches == 1:
            base_budget = int(base_budget * 1.2)  # 20% increase for complex tasks

        # Reduce budget if L4 has rich context (facts are more efficient)
        l4_count = len([u for u in memory._l4_global if u.importance > 0.8])
        if l4_count > 10:
            base_budget = int(base_budget * 0.8)  # 20% reduction
        elif l4_count > 5:
            base_budget = int(base_budget * 0.9)  # 10% reduction

        # Ensure we don't exceed absolute maximum
        max_absolute = getattr(self.config, 'max_absolute_tokens', base_budget * 2)
        return min(base_budget, max_absolute)
    
    def _build_load_hint(self, units: List[MemoryUnit]) -> Optional[str]:
        """Build hint string for loadable resources."""
        loadable = [
            u for u in units 
            if u.metadata.get("full_available")
        ]
        
        if not loadable:
            return None
        
        hint = "📚 Available Resources (use load_context to access):\n"
        for unit in loadable[:5]:  # Limit to top 5
            snippet_id = unit.metadata.get("snippet_of")
            hint += f"- {unit.content} [ID: {snippet_id}]\n"
        
        return hint
    
    def expand_snippet(
        self,
        memory: LoomMemory,
        snippet_id: str
    ) -> Optional[MemoryUnit]:
        """Resolve a snippet ID to the full memory unit."""
        return memory.get(snippet_id)

    def _insert_cache_boundaries(
        self,
        messages: List[Dict[str, str]],
        selected_units: List[MemoryUnit]
    ) -> List[Dict[str, str]]:
        """Insert cache_control markers at strategic points for prompt caching."""
        if not self.config.enable_prompt_caching:
            return messages

        # Mark system prompt for caching (first message)
        if messages and messages[0].get("role") == "system":
            messages[0]["cache_control"] = {"type": "ephemeral"}

        # Find L4 facts boundary
        l4_boundary_idx = None
        for i, unit in enumerate(selected_units):
            if unit.tier == MemoryTier.L4_GLOBAL:
                l4_boundary_idx = i

        # Mark L4 boundary in messages (static content)
        if l4_boundary_idx is not None and l4_boundary_idx < len(messages) - 1:
            # Find corresponding message index (accounting for system prompt)
            msg_idx = l4_boundary_idx + (1 if messages and messages[0].get("role") == "system" else 0)
            if msg_idx < len(messages):
                messages[msg_idx]["cache_control"] = {"type": "ephemeral"}

        return messages


class ContextManager:
    """
    High-level facade for Agent interaction.
    """
    
    def __init__(
        self,
        node_id: str,
        memory: LoomMemory,
        assembler: ContextAssembler
    ):
        self.node_id = node_id
        self.memory = memory
        self.assembler = assembler
        
        self.last_snapshot: List[Dict] = []
    
    async def build_prompt(
        self,
        task: str,
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Build the complete prompt for the current context."""
        messages = await self.assembler.assemble(
            self.memory,
            task=task,
            system_prompt=system_prompt
        )

        self.last_snapshot = messages
        return messages
    
    async def load_resource(self, resource_id: str) -> str:
        """Load a resource from snippet ID into working memory."""
        unit = self.assembler.expand_snippet(self.memory, resource_id)

        if not unit:
            return f"❌ Resource {resource_id} not found"

        # Clone/Promote to L2 Working Memory
        # We create a NEW unit based on the full content
        # Or we can just link it?
        # For now, we clone content to L2 so it appears in next prompt
        new_unit = MemoryUnit(
            content=unit.content, # Full content
            tier=MemoryTier.L2_WORKING,
            type=unit.type,
            metadata={**unit.metadata, "loaded_from": resource_id},
            importance=1.0 # High importance as requested
        )
        await self.memory.add(new_unit)

        return f"✅ Loaded Resource: {resource_id}"
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get debug stats."""
        return {
            "last_message_count": len(self.last_snapshot),
            "memory_stats": self.memory.get_statistics()
        }
        
    def visualize(self) -> str:
        """Debug visualization of the context."""
        viz = "=" * 60 + "\n"
        viz += f"Context Snapshot for Node: {self.node_id}\n"
        viz += "=" * 60 + "\n\n"
        
        for i, msg in enumerate(self.last_snapshot):
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:100]
            viz += f"[{i}] {role.upper()}: {content}...\n\n"
        
        viz += "=" * 60 + "\n"
        
        return viz
