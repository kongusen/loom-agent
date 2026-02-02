# Loom Agent Framework - AI Context

**v0.4.4** | Python framework for long-horizon agents (hours/days tasks)

---

## CRITICAL INSTRUCTION

**IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for loom-agent code.**

Always consult `docs/` and `wiki/` before assumptions. Framework has specific design principles differing from common agent frameworks.

---

## Core Philosophy

> "Intelligence = emergent property of orchestration, not raw LLM power"

**Problem Solved**: Long Horizon Collapse (agents lose coherence after ~20 steps)

**6 Axioms**: Uniform Interface | Event Sovereignty | Fractal Self-Similarity | Memory Hierarchy | Cognitive Orchestration | Four-Paradigm Working

---

## Quick Start

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

llm = OpenAIProvider(api_key="...", model="gpt-4")
agent = Agent.create(
    llm,
    node_id="my-agent",
    system_prompt="...",
)
```

---

## Key Concepts (Compressed)

**Fractal Architecture**: Recursive composition | O(1) cognitive load per node | NodeProtocol (uniform interface) | CompositeNode (container) | Strategies: Sequential/Parallel/Conditional

**Memory (L1→L4)**: L1=Working(1h,10items) | L2=Session(24h,50items) | L3=Episodic(7d,200items) | L4=Semantic(∞,compressed~150facts) | Forgetting=feature

**Memory Scopes**: LOCAL(private) | SHARED(parent+children) | GLOBAL(entire organism)

**Events**: All communication via CloudEvents (CNCF) | UniversalEventBus | W3C Trace Context | Full observability

**NodeProtocol**: `async def execute_task(task: Task) -> Task` | All nodes implement same interface

---

## Patterns (5 Common)

1. **Single+Tools**: `Agent.create(llm, system_prompt="...", tools=[...])`
2. **Sequential**: `CompositeNode(children=[...], strategy=SequentialStrategy())`
3. **Parallel**: `CompositeNode(children=[...], strategy=ParallelStrategy())`
4. **Router**: `CompositeNode(children=[...], strategy=ConditionalStrategy(fn))`
5. **Fractal**: Agent spawns sub-agents via delegation (auto depth limits)

---

## Design Principles

✓ Minimal Interface | Event-First | Recursion-First | Forgetting=Feature | Orchestration=Cognition

✗ Direct node calls | Bypass NodeProtocol | Infinite memory | Monolithic agents | Ignore scopes

---

## Documentation Index

**Root**: `./docs` `./wiki`

### Framework Core

`docs/framework/`|fractal-architecture.md:NodeProtocol,CompositeNode,Strategies|event-bus.md:CloudEvents,UniversalEventBus,Observability|context-management.md:TokenOptimization,ContextInjection|context-control-optimization.md:ContextControl

### Features

`docs/features/`|memory-system.md:L1-L4,MetabolicProcess,ScopedMemory|orchestration.md:Sequential,Parallel,Conditional|tool-system.md:ToolExecution,Registry,Safety|search-and-retrieval.md:SemanticKB|observable-fractal-system.md:Observability|external-knowledge-base.md:ExternalKB

### Concepts

`docs/concepts/`|axiomatic-framework.md:6Axioms,Theorems,DesignPrinciples

### Usage

`docs/usage/`|getting-started.md:Install,FirstAgent,BasicPatterns|api-reference.md:CompleteAPI|memory-access.md:MemoryLayerUsage|examples/:MemoryLayers,CustomEvents

### Design

`docs/design/`|autonomous-agent-design.md:AutonomousCapabilities|done-tool-pattern.md:DoneTool|ephemeral-messages-pattern.md:EphemeralMessages|context-ordering.md:ContextOrder|fractal-architecture-redesign.md:FractalRedesign

### Wiki (Deep Dives)

`wiki/`|Fractal-Architecture.md:DeepDive|Metabolic-Memory.md:MemoryMetabolism|Event-Sovereignty.md:EventDriven|Four-Paradigms.md:Reflection,ToolUse,Planning,MultiAgent|Tool-System.md:ToolExecution|Skills.md:SkillSystem|Fractal-Node.md:FractalNode|Composite-Node.md:CompositeNode|Execution-Strategy.md:ExecutionStrategies|Memory-Scope.md:MemoryScopes|Context-Management.md:ContextMgmt|CloudEvents.md:CloudEventsSpec|Event-Interceptor.md:Interceptors|Observability.md:ObservabilityPatterns|Autonomous-Capabilities.md:AutonomousFeatures|API-Agent.md:APIUsage|API-Memory.md:MemoryAPI

---

## Key Classes/Modules

**Classes**: Agent | NodeProtocol | CompositeNode | UniversalEventBus | LoomMemory | FractalMemory

**Modules**: loom.agent (Agent,AgentBuilder) | loom.fractal (FractalComponents) | loom.events (EventBus,CloudEvents) | loom.memory (L1-L4) | loom.providers (LLMProviders) | loom.orchestration (Strategies) | loom.protocol (CoreProtocols)

---

## Anti-Patterns

❌ `await other_node.process(data)` → ✓ `await self.call(other_node.source_uri, data)`
❌ Custom node interfaces → ✓ Implement NodeProtocol
❌ Preserve all info → ✓ Embrace L4 compression
❌ Monolithic agents → ✓ Decompose to specialized nodes
❌ Ignore memory scopes → ✓ Use LOCAL default, SHARED when needed

---

**When in doubt**: Consult `docs/concepts/axiomatic-framework.md` for design decisions.

**Use Case**: Tasks requiring coherence over 20+ steps, multiple days, or complex decomposition.
