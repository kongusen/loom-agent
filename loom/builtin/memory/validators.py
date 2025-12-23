"""
Memory Validators Implementation.
"""

from typing import Any
from loom.protocol.memory_operations import MemoryValidator

# Assumed LLM interface access - in real implementation, this would be injected
# For now we'll accept an LLMProvider in init

class HeuristicValueAssessor(MemoryValidator):
    def __init__(self, key_terms: list[str] = None):
        self.key_terms = key_terms or ["goal", "error", "result", "important", "decision"]

    async def validate(self, content: Any) -> float:
        """
        Simple heuristic: active if contains key terms or is short and punchy.
        """
        text = str(content).lower()
        score = 0.0
        
        # Length bias: too short might be noise, too long might be noise
        if 10 < len(text) < 500:
            score += 0.3
            
        # Term bias
        for term in self.key_terms:
            if term in text:
                score += 0.2
        
        return min(1.0, score)

class LLMValueAssessor(MemoryValidator):
    def __init__(self, llm_provider: Any): # using Any to avoid circ dep for now
        self.llm = llm_provider
        
    async def validate(self, content: Any) -> float:
        """
        Ask LLM to score the importance.
        """
        prompt = f"""
        Rate the importance of the following memory entry for a long-term project on a scale of 0.0 to 1.0.
        Return ONLY the number.
        
        Entry:
        {content}
        """
        try:
            # Assumed simple LLM call not needing message structure for simplicity in this prototype
            # But in reality, we'd use the proper Chat interface
            # response = await self.llm.chat([{"role": "user", "content": prompt}])
            # For now, let's mock/assume simple wrapper or return a high default
            return 0.8 # Placeholder for actual LLM call
        except:
            return 0.5
