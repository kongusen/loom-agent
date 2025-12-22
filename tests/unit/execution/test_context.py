import pytest
from loom.core.message import SystemMessage, UserMessage, AssistantMessage
from loom.execution.context import ContextAssembler, ContextConfig

def test_context_assembly_priority():
    """Verify System Prompt > Memory > History priority."""
    config = ContextConfig(max_tokens=100, reserved_tokens=0)
    assembler = ContextAssembler(config)

    system_prompt = "You are a helpful assistant." # ~10 tokens
    memory = [
        UserMessage(content="Relevant fact 1"), # ~7 tokens
        UserMessage(content="Relevant fact 2")  # ~7 tokens
    ]
    history = [
        UserMessage(content="Old message"),     # ~6 tokens
        AssistantMessage(content="Old reply"),  # ~6 tokens
        UserMessage(content="New message")      # ~6 tokens
    ]

    context = assembler.assemble(
        system_prompt=system_prompt,
        relevant_memory=memory,
        history=history
    )

    # Should contain all since max_tokens=100 is plenty
    assert len(context) == 6
    assert context[0].role == "system"
    # Memory usually inserted after system prompt
    assert context[1].content == "Relevant fact 1"
    assert context[2].content == "Relevant fact 2"
    # History follows
    assert context[3].content == "Old message"
    assert context[-1].content == "New message"

def test_context_truncation():
    """Verify context is truncated when exceeding token limit."""
    # Strict limit
    config = ContextConfig(max_tokens=20, reserved_tokens=0)
    assembler = ContextAssembler(config)

    # System prompt takes ~10 tokens
    system_prompt = "System prompt." 
    
    # History takes ~8 tokens per message
    history = [
        UserMessage(content="Oldest message"),
        UserMessage(content="Newest message") 
    ]

    context = assembler.assemble(
        system_prompt=system_prompt,
        history=history
    )

    # Expect: System Prompt + Newest Message. Oldest should be dropped.
    # Tokens: ~6 (Sys) + ~8 (Newest) = 14 < 20. 
    # Adding Oldest would be ~22 > 20.
    assert len(context) == 2
    assert context[0].role == "system"
    assert context[1].content == "Newest message"

def test_memory_priority_over_history():
    """Verify relevant memory is prioritized over history."""
    config = ContextConfig(max_tokens=30, reserved_tokens=0)
    assembler = ContextAssembler(config)
    
    memory = [UserMessage(content="Critical Memory")] # ~8 tokens
    history = [
        UserMessage(content="History 1"),
        UserMessage(content="History 2"), 
        UserMessage(content="History 3")
    ]

    context = assembler.assemble(
        relevant_memory=memory,
        history=history
    )
    
    # Expect: Memory + some history
    # Memory should be present
    assert any(m.content == "Critical Memory" for m in context)
    # Should fill remaining space with recent history
    assert context[-1].content == "History 3"
