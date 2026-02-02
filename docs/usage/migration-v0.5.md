# Migration Guide: v0.4.x → v0.5.0

## Overview

Loom v0.5.0 introduces **Progressive Disclosure** and **LLM Autonomy**: simple use cases use fewer parameters, while advanced features remain available via explicit injection. This release includes **breaking changes** (removed parameters and async API changes); see [What's New in v0.5.0](whats-new-v0.5.md) for the full list.

**Key Principles**: Simple things should be simple; complex things should be possible; the framework provides mechanism, the LLM provides policy.

## What's New in v0.5.0

### 1. Auto-created EventBus

**Before v0.5.0**: You had to manually create and pass an EventBus:

```python
from loom.agent import Agent
from loom.events.event_bus import EventBus

event_bus = EventBus()
agent = Agent.create(
    llm,
    system_prompt="Hello",
    event_bus=event_bus,  # Required
)
```

**v0.5.0**: EventBus is auto-created when not provided:

```python
from loom.agent import Agent

agent = Agent.create(
    llm,
    system_prompt="Hello",
    # event_bus auto-created internally
)
```

**When to still pass EventBus explicitly**:
- When multiple agents need to share the same event bus
- When you need to observe events externally
- When integrating with existing event infrastructure

### 2. Simple Skills Configuration

**Before v0.5.0**: Enabling skills required manual SkillRegistry setup:

```python
from loom.agent import Agent
from loom.config.agent import AgentConfig
from loom.skills.skill_registry import skill_market

config = AgentConfig(enabled_skills={"python-dev", "testing"})
agent = Agent.create(
    llm,
    system_prompt="Code assistant",
    config=config,
    skill_registry=skill_market,
)
```

**v0.5.0**: Use the `skills=` parameter for simple configuration:

```python
from loom.agent import Agent

agent = Agent.create(
    llm,
    system_prompt="Code assistant",
    skills=["python-dev", "testing"],  # Simple!
)
```

The `skills=` parameter automatically:
- Uses the global `skill_market` as the skill registry
- Sets `config.enabled_skills` from the provided list
- Handles all the wiring for you

### 3. Advanced Capabilities Configuration

**v0.5.0** introduces the `capabilities=` parameter for advanced use cases where you need fine-grained control over tools, skills, and their dependencies.

**Before v0.5.0**: Manual component wiring:

```python
from loom.agent import Agent
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager
from loom.skills.skill_registry import skill_market
from loom.skills.activator import SkillActivator

# Create components manually
sandbox = Sandbox("/path/to/sandbox")
tool_manager = SandboxToolManager(sandbox)
skill_activator = SkillActivator(llm, skill_registry=skill_market)

# Wire them together
agent = Agent.create(
    llm,
    system_prompt="Advanced agent",
    sandbox_manager=tool_manager,
    skill_registry=skill_market,
    skill_activator=skill_activator,
)
```

**v0.5.0**: Use `CapabilityRegistry` for unified configuration. Note: `find_relevant_capabilities` and `validate_skill_dependencies` are **async** (use `await`).

```python
from loom.agent import Agent
from loom.capabilities.registry import CapabilityRegistry
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager
from loom.skills.registry import SkillRegistry  # or from loom.skills import skill_market
from loom.skills.activator import SkillActivator

# Create components (unified SkillRegistry: Loaders + runtime register_skill)
skill_registry = SkillRegistry()  # or use skill_market
sandbox = Sandbox("/path/to/sandbox")
tool_manager = SandboxToolManager(sandbox)
skill_activator = SkillActivator(llm, skill_registry=skill_registry, tool_manager=tool_manager)

# Bundle them in CapabilityRegistry
capabilities = CapabilityRegistry(
    sandbox_manager=tool_manager,
    skill_registry=skill_market,
    skill_activator=skill_activator,
)

# Pass as single parameter
agent = Agent.create(
    llm,
    system_prompt="Advanced agent",
    capabilities=capabilities,  # All components in one!
)
```

**Benefits**:
- Single parameter instead of three
- Components are validated together
- Easier to share configurations across agents
- Explicit parameters still override capabilities

## Breaking Changes (Must Address)

- **Agent**: Parameters `enable_tool_creation` and `enable_context_tools` are **removed**. All tools (context tools, tool creation, etc.) are always available; the LLM decides whether to use them. Remove these arguments from your `Agent.create()` / `Agent.from_llm()` calls.
- **CapabilityRegistry**: `find_relevant_capabilities(...)` and `validate_skill_dependencies(skill_id)` are now **async**. Use `await registry.find_relevant_capabilities(...)` and `await registry.validate_skill_dependencies(skill_id)`.
- **SkillRegistry**: There is now a **single** `SkillRegistry` in `loom.skills.registry` (and `loom.skills.skill_registry` re-exports it). Runtime-registered skills use `register_skill(...)`; Loader-based skills use `register_loader(...)` and async `get_skill` / `get_all_metadata`. If you imported the old dict-style class from `skill_registry.py`, the import still works but now points to the unified class.
- **fractal**: `estimate_task_complexity` and `should_use_fractal` are **removed** from the public API. Delegate/fractal decisions are made by the LLM via tools (e.g. `delegate_task`), not by framework heuristics.

## Migration Steps

### Step 1: Update Your Code (Required for Breaking Changes)

Apply the breaking changes above, then optionally adopt the new patterns below:

#### Simplify EventBus Creation

**Before**:
```python
from loom.events.event_bus import EventBus
event_bus = EventBus()
agent = Agent.create(llm, system_prompt="...", event_bus=event_bus)
```

**After** (if you don't need to share the EventBus):
```python
agent = Agent.create(llm, system_prompt="...")  # EventBus auto-created
```

#### Simplify Skills Configuration

**Before**:
```python
from loom.config.agent import AgentConfig
from loom.skills.skill_registry import skill_market

config = AgentConfig(enabled_skills={"skill1", "skill2"})
agent = Agent.create(llm, config=config, skill_registry=skill_market)
```

**After**:
```python
agent = Agent.create(llm, skills=["skill1", "skill2"])
```

### Step 2: Test Your Application

After removing deprecated parameters and updating any `CapabilityRegistry` calls to `await`, run your test suite:

```bash
pytest tests/
```

## Complete Examples

### Example 1: Simple Agent (Minimal Configuration)

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# Create LLM provider
llm = OpenAIProvider(api_key="your-key", model="gpt-4")

# Create agent with minimal configuration
agent = Agent.create(
    llm,
    system_prompt="You are a helpful assistant",
)

# EventBus is auto-created internally
print(f"Agent ready: {agent.node_id}")
```

### Example 2: Agent with Skills (Simple Configuration)

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4")

# Enable skills with simple parameter
agent = Agent.create(
    llm,
    system_prompt="You are a coding assistant",
    skills=["python-dev", "testing", "debugging"],
)

# Skills are automatically configured
print(f"Enabled skills: {agent.config.enabled_skills}")
```

### Example 3: Shared EventBus (Multiple Agents)

```python
from loom.agent import Agent
from loom.events.event_bus import EventBus
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4")

# Create shared EventBus for observability
shared_bus = EventBus()

# Create multiple agents sharing the same bus
agent1 = Agent.create(
    llm,
    system_prompt="Agent 1",
    event_bus=shared_bus,
)

agent2 = Agent.create(
    llm,
    system_prompt="Agent 2",
    event_bus=shared_bus,
)

# Both agents publish to the same bus
print(f"Agents share event bus: {agent1.event_bus is agent2.event_bus}")
```

### Example 4: Advanced Configuration with CapabilityRegistry

```python
from loom.agent import Agent
from loom.capabilities.registry import CapabilityRegistry
from loom.tools.sandbox import Sandbox
from loom.tools.sandbox_manager import SandboxToolManager
from loom.skills.skill_registry import skill_market
from loom.skills.activator import SkillActivator
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4")

# Create components
sandbox = Sandbox("/tmp/agent-sandbox")
tool_manager = SandboxToolManager(sandbox)
skill_activator = SkillActivator(llm, skill_registry=skill_market)

# Bundle in CapabilityRegistry
capabilities = CapabilityRegistry(
    sandbox_manager=tool_manager,
    skill_registry=skill_market,
    skill_activator=skill_activator,
)

# Create agent with unified capabilities
agent = Agent.create(
    llm,
    system_prompt="Advanced agent with full capabilities",
    capabilities=capabilities,
)

print(f"Agent has sandbox: {agent.sandbox_manager is not None}")
print(f"Agent has skills: {agent.skill_registry is not None}")
```

## Frequently Asked Questions

### Q: Do I need to update my existing code?

**A**: No. v0.5.0 is 100% backward compatible. All existing code will continue to work without any changes. The new features are purely additive and optional.

### Q: When should I use `skills=` vs `capabilities=`?

**A**:
- Use `skills=` for simple cases where you just want to enable some skills
- Use `capabilities=` for advanced cases where you need fine-grained control over tools, skills, and their dependencies
- Use explicit parameters (`sandbox_manager=`, `skill_registry=`, etc.) when you need maximum control

### Q: Can I mix the new and old patterns?

**A**: Yes! You can use the new convenience parameters alongside explicit parameters. Explicit parameters always take priority.

```python
# This works - explicit event_bus overrides auto-creation
agent = Agent.create(
    llm,
    skills=["python-dev"],  # New pattern
    event_bus=my_custom_bus,  # Old pattern
)
```

### Q: What if I pass both `capabilities=` and explicit parameters?

**A**: Explicit parameters always take priority over `capabilities=`. This allows you to override specific components while using `capabilities=` for the rest.

```python
capabilities = CapabilityRegistry(
    sandbox_manager=tool_manager1,
    skill_registry=skill_market,
)

# tool_manager2 overrides capabilities.tool_manager
agent = Agent.create(
    llm,
    capabilities=capabilities,
    sandbox_manager=tool_manager2,  # This takes priority
)
```

### Q: Are there any breaking changes?

**A**: No. v0.5.0 has zero breaking changes. All existing APIs continue to work exactly as before.

## Summary

v0.5.0 introduces **Progressive Disclosure** to make Loom easier to use:

- **Auto-created EventBus**: No need to create EventBus manually for simple cases
- **Simple Skills**: Use `skills=["skill1", "skill2"]` instead of manual configuration
- **Advanced Capabilities**: Use `capabilities=` to bundle components together
- **100% Backward Compatible**: All existing code continues to work

**Recommended approach**:
1. Keep your existing code as-is (it will work)
2. Gradually adopt new patterns as you write new code
3. Use the simplest pattern that meets your needs

## Next Steps

- Read the [Getting Started Guide](getting-started.md) for updated examples
- Check the [API Reference](api-reference.md) for complete documentation
- Explore the [examples directory](examples/) for real-world usage patterns

---

**Questions or issues?** Please open an issue on GitHub or reach out to the Loom community.
