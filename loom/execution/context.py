from typing import List, Optional
from dataclasses import dataclass
from loom.core.message import Message, SystemMessage, UserMessage, AssistantMessage, ToolMessage

@dataclass
class ContextConfig:
    """Configuration for context assembly."""
    max_tokens: int = 4096
    reserved_tokens: int = 500  # Reserve for response
    system_prompt_priority: bool = True
    keep_recent_n: int = 0  # 0 means try to keep as many as possible within token limit

class ContextAssembler:
    """
    Assembles context from various sources (system prompt, history, memory)
    while respecting token limits.
    """

    def __init__(self, config: Optional[ContextConfig] = None):
        self.config = config or ContextConfig()

    def assemble(
        self,
        system_prompt: Optional[str] = None,
        history: Optional[List[Message]] = None,
        relevant_memory: Optional[List[Message]] = None,
        max_tokens: Optional[int] = None
    ) -> List[Message]:
        """
        Assembles the final context list.

        Priority:
        1. System Prompt (Highest)
        2. Relevant Memory (High)
        3. Recent History (Medium - Truncated from oldest if needed)
        """
        limit = max_tokens or self.config.max_tokens
        limit -= self.config.reserved_tokens
        
        context: List[Message] = []
        current_tokens = 0

        # 1. System Prompt
        if system_prompt:
            sys_msg = SystemMessage(content=system_prompt)
            sys_tokens = self._estimate_tokens(sys_msg)
            if current_tokens + sys_tokens <= limit:
                context.append(sys_msg)
                current_tokens += sys_tokens
        
        # 2. Relevant Memory
        if relevant_memory:
            # We want to keep the order of relevant_memory
            # So we collect valid ones first
            valid_memories = []
            for msg in relevant_memory:
                tokens = self._estimate_tokens(msg)
                if current_tokens + tokens <= limit:
                    valid_memories.append(msg)
                    current_tokens += tokens
            
            # Then insert them all at once after system prompt
            insert_idx = 1 if context and context[0].role == "system" else 0
            context[insert_idx:insert_idx] = valid_memories
        
        # 3. History (Reverse iterate to keep most recent)
        if history:
            history_segment: List[Message] = []
            
            # Use 'reversed' to process from newest to oldest
            for msg in reversed(history):
                tokens = self._estimate_tokens(msg)
                if current_tokens + tokens <= limit:
                    history_segment.append(msg)
                    current_tokens += tokens
                else:
                    break
            
            # Add to context (need to reverse back to chronological order)
            context.extend(reversed(history_segment))

        return context

    def _estimate_tokens(self, message: Message) -> int:
        """
        Simple heuristic for token counting.
        In production, this should use tiktoken or similar.
        Ratio: 1 token ~= 4 chars (English) or 0.7 chars (Chinese)
        Here we use a safe upper bound approximation.
        """
        content = message.get_text_content()
        # Rough estimation: characters / 2.5 to be safe
        text_tokens = len(content) // 2.5 
        
        # Overhead for message structure
        structure_tokens = 4 
        
        return int(text_tokens + structure_tokens)
