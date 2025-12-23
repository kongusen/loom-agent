import pytest
import asyncio
from loom.builtin.memory.metabolic import MetabolicMemory

@pytest.mark.asyncio
async def test_metabolic_memory_lifecycle():
    memory = MetabolicMemory()
    memory.limit = 4 # Small limit for testing
    
    # 1. Add typical start sequence
    await memory.add("user", "My goal is to build a rocket.")
    await memory.add("assistant", "I can help with that.")
    
    # Check Context
    context = await memory.get_context()
    assert "activity" in context.lower()
    assert "rocket" in context
    
    # Check PSO state (should be empty goals initially until consolidation or robust PSO)
    # Our SimplePSO updates on 'consolidate' (triggered at limit)? 
    # Current impl: consolidate called when adding > limit.
    
    # 2. Trigger Consolidation
    await memory.add("user", "Show me a design.")
    await memory.add("tool", "Here is a blueprint result.") 
    # Count now 4. Not > 4.
    
    await memory.add("assistant", "Design looks good.")
    # Count now 5. Trigger consolidate!
    # Consolidate: updates PSO, keeps last 2.
    
    # PSO should now have captured the goal from the first message (passed in events)
    pso_md = memory.pso.to_markdown()
    print(f"PSO Markdown: {pso_md}")
    
    assert "rocket" in pso_md
    
    # Short term should be pruned
    assert len(memory.short_term) == 2
    assert "Design looks good" in memory.short_term[-1].content
