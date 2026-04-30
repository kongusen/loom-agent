# Public User API Taxonomy

This page defines the user-facing API naming taxonomy for Loom. It separates
the names users call from the internal architecture names used by the runtime.

## Design Principle

User API names should answer: "What does the user want to use?"

Architecture API names should answer: "How does Loom execute it?"

That gives Loom two clear layers:

```text
User API
    Agent(model=..., memory=..., tools=..., capabilities=..., skills=...)

Architecture API
    CapabilityCompiler, ToolRuntime, MemoryRuntime, SignalRuntime, ContextRuntime
```

The user API is direct and noun-based. The architecture API remains
abstract, composable, and runtime-oriented.

## Naming Rules

1. Use the common user term for first-level `Agent(...)` fields.
2. Keep `Model` as the provider and model configuration entry point.
3. Keep `instructions` as the simple system prompt entry point.
4. Use plural nouns when users provide collections: `tools`, `skills`, `gateways`.
5. Use `capabilities` for concrete tool/ability surfaces such as `Files`,
   `Web`, `Shell`, and `MCP`.
6. Keep architecture abstractions such as `Capability` and `Runtime` available
   for advanced use, but do not make them the only intuitive path.
7. Do not add aliases unless they become the single documented path for a user
   need.

## Top-Level User Categories

| Category | User API name | Primary user question | Internal mapping |
|---|---|---|---|
| Agent assembly | `Agent` | What agent am I creating? | Agent assembly / engine builder |
| Model/provider | `Model` | Which model and provider config should it use? | provider runtime / completion request |
| Instructions | `instructions` / `Instructions` | What should the agent be? | `C_system` |
| Tools | `tools` / `@tool` | What exact functions can it call? | `ToolSpec` / `ToolRuntime` |
| Capabilities | `capabilities` | Which tool/ability surfaces can it use? | capability compiler / governed tools |
| Skills | `skills` / `Skill` | Which task-specific workflows can it use? | skill registry / `C_skill` / skill injection |
| Memory | `memory` / `Memory` | What should persist or be recalled? | `MemoryRuntime` / memory sources |
| Knowledge | `knowledge` / `Knowledge` | What retrieval sources ground answers? | knowledge resolver / `RunContext.knowledge` |
| Session | `session` / `SessionConfig` | How is multi-run state scoped? | `Session` / session store |
| Signals | `signals` / `SignalAdapter` | How do external events enter? | `RuntimeSignal` / `SignalRuntime` |
| Gateway | `gateways` / `Gateway` | Which app/webhook producers send signals? | signal adapter / runtime signal |
| Schedule | `schedule` / `Cron` / `ScheduledJob` | What timed events should run? | cron scheduler / runtime signal |
| Harness | `harness` / `Harness` | How are long tasks controlled? | `HarnessRunner` |
| Quality | `quality` / `QualityGate` | How is output accepted or rejected? | runtime quality gate |
| Safety | `safety` / `governance` | What is allowed or blocked? | `GovernancePolicy` / veto / permissions |
| Delegation | `delegation` / `DelegationPolicy` | Can it dispatch subtasks? | delegation runtime |
| Feedback | `feedback` / `FeedbackPolicy` | How are outcomes collected? | feedback runtime |
| Persistence | `session_store` | Where are sessions and runs stored? | `SessionStore` |
| Observability | `events` / `stream` / tracing config | How do I observe execution? | run lifecycle / stream events |

## Recommended Constructor Shape

The supported user-facing constructor shape is:

```python
agent = Agent(
    model=Model.openai(
        "gpt-5.1",
        base_url="https://api.example.com/v1",
        timeout=30,
    ),
    instructions="You are a careful repository assistant.",
    memory=Memory.session(),
    knowledge=Knowledge.sources(["docs/", "wiki/"]),
    tools=[search_docs],
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
        Shell(require_approval=True),
        MCP.server("github"),
    ],
    skills=[
        Skill.from_directory("skills/"),
        Skill.inline(
            "repo-review",
            description="Review repository changes.",
            when_to_use="review,diff,pull request",
            content="Check diffs, tests, risks, and API impact.",
            allowed_tools=["Read", "Grep"],
        ),
    ],
    schedule=[
        Cron.daily("health-check", at="09:00"),
    ],
    gateways=[
        Gateway.webhook("slack", source="gateway:slack"),
    ],
    harness=Harness.generator_evaluator(max_sprints=3),
    quality=QualityGate.criteria(["tests pass", "docs updated"]),
    governance=GovernancePolicy.safe_default(),
)
```

This does not require a second runtime. Each user-facing field normalizes into
the existing architecture API.

## `Model` Owns Provider Configuration

Provider configuration stays under `Model`:

```python
model = Model.openai(
    "gpt-5.1",
    api_key="...",
    base_url="https://api.openai.com/v1",
    timeout=30,
    max_retries=2,
)
```

Avoid a separate top-level `Provider(...)` user API unless Loom later needs
provider objects independent of model selection.

Internal mapping:

```text
Model -> provider resolution -> ProviderRuntime -> CompletionRequest
```

## Instructions

Simple usage stays string-based:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    instructions="You are a concise code reviewer.",
)
```

Structured instructions can be added as an advanced user API:

```python
instructions=Instructions(
    role="code reviewer",
    style="concise",
    constraints=["prioritize correctness", "cite files"],
)
```

Internal mapping:

```text
instructions -> C_system
```

## Tools And Ability Surfaces

### Explicit Tools

Use `tools` for exact functions owned by the application:

```python
@tool(read_only=True)
def search_docs(query: str) -> str:
    return "..."


Agent(model=Model.openai("gpt-5.1"), tools=[search_docs])
```

### Capabilities: Files, Web, Shell, MCP

Use `capabilities` for common ability surfaces. The entries use direct
domain names, not the architecture term `Capability`:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    capabilities=[
        Files(read_only=True),
        Web.enabled(),
        Shell(require_approval=True),
        MCP.server("github"),
    ],
)
```

Internal mapping:

```text
capabilities=[Files/Web/Shell/MCP]
    -> CapabilitySpec
    -> CapabilityCompiler
    -> ToolSpec
    -> ToolRuntime
    -> GovernancePolicy
```

`Capability` remains the advanced architecture-facing way to express custom
ability sources.

## Skills

Skills need a first-class user API because they are a common user concept, not
just an internal capability source.

Supported shape:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    skills=[
        Skill.from_file("skills/release.md"),
        Skill.from_directory("skills/review/"),
        Skill.inline(
            "repo-review",
            description="Review repository changes.",
            when_to_use="review,diff,pull request",
            content="Check correctness risks and missing tests.",
            allowed_tools=["Read", "Grep"],
        ),
    ],
)
```

Runtime skill selection remains policy-driven:

```python
runtime=Runtime.sdk(
    skill_injection=SkillInjection.matching(max_skills=3, max_tokens=4000)
)
```

Internal mapping:

```text
skills
    -> Skill declarations
    -> skill registry
    -> SkillInjection
    -> C_skill
```

## Memory

Memory should answer "what should persist or be recalled?"

Supported shape:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    memory=Memory.session(),
)
```

Supported variants:

```python
Memory.none()
Memory.session()
Memory.semantic(store=...)
Memory.with_sources([...])
```

Internal mapping:

```text
memory -> MemoryRuntime -> C_memory / session persistence / semantic recall
```

## Knowledge

Knowledge should answer "what sources ground this agent's answers?"

Supported shape:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    knowledge=Knowledge.sources(["docs/", "wiki/"]),
)
```

Run-scoped knowledge still belongs in `RunContext`:

```python
result = await agent.run(
    "Answer from these sources.",
    context=RunContext(knowledge=knowledge_bundle),
)
```

Internal mapping:

```text
knowledge -> resolver -> KnowledgeBundle -> RunContext.knowledge -> context injection
```

## Gateway And Signals

Gateway is a user-side producer concept. Runtime signal is the normalized
contract.

Supported shape:

```python
gateway = Gateway.webhook(
    "slack",
    source="gateway:slack",
    summary=lambda event: event["text"],
)

Agent(model=Model.openai("gpt-5.1"), gateways=[gateway])
```

Direct signal adapters remain useful for lightweight integration:

```python
adapter = SignalAdapter(
    source="gateway:slack",
    type="message",
    summary=lambda event: event["text"],
)

await session.receive(event, adapter=adapter)
```

Internal mapping:

```text
Gateway -> SignalAdapter -> RuntimeSignal -> SignalRuntime -> AttentionPolicy
```

## Schedule And Cron

Schedule should answer "what timed events should this agent receive?"

Supported shape:

```python
Agent(
    model=Model.openai("gpt-5.1"),
    schedule=[
        Cron.daily("standup-summary", at="09:00"),
        Cron.interval("health-check", every="5m"),
    ],
)
```

Internal mapping:

```text
Cron / ScheduledJob -> scheduler -> RuntimeSignal -> AttentionPolicy
```

## Harness, Quality, Safety, Delegation, Feedback

These are advanced user APIs, but they still use user-facing names when
passed into `Agent(...)`.

```python
Agent(
    model=Model.openai("gpt-5.1"),
    harness=Harness.generator_evaluator(max_sprints=3),
    quality=QualityGate.criteria(["tests pass"]),
    governance=GovernancePolicy.safe_default(),
    delegation=DelegationPolicy.none(),
    feedback=FeedbackPolicy.collect(),
)
```

Internal mapping:

```text
harness -> HarnessRunner
quality -> RuntimeQualityGate
governance -> GovernancePolicy / safety managers
delegation -> DelegationPolicy
feedback -> FeedbackRuntime
```

## Supported API Paths

| User need | Supported user path | Architecture path |
|---|---|---|
| Model/provider config | `model=Model.openai(...)` | provider resolution |
| System prompt | `instructions="..."` or `Instructions(...)` | `C_system` |
| Function tools | `tools=[...]` | `ToolSpec -> ToolRuntime` |
| Files | `capabilities=[Files(...)]` | `CapabilitySpec -> Toolset.files` |
| Web | `capabilities=[Web.enabled()]` | `CapabilitySpec -> Toolset.web` |
| Shell | `capabilities=[Shell.approval_required()]` | `CapabilitySpec -> Toolset.shell` |
| MCP | `capabilities=[MCP.server(...)]` | MCP activation + scoped tools |
| Skills | `skills=[Skill...]` | skill registry + `C_skill` |
| Memory | `memory=Memory.session()` / `Memory.with_sources(...)` | `MemoryRuntime` |
| Knowledge | `knowledge=Knowledge...` / `RunContext.knowledge` | knowledge resolver |
| Gateway | `gateways=[Gateway...]` plus `SignalAdapter` | `RuntimeSignal` |
| Cron | `schedule=[Cron...]` | scheduler + `RuntimeSignal` |
| Harness | `harness=Harness...` or runtime profile | `HarnessRunner` |
| Quality | `quality=QualityGate...` | runtime quality gate |
| Safety | `governance=GovernancePolicy...` | governance / veto / permissions |

These paths normalize into the current architecture components instead of
creating a second execution system. `Capability` stays available as an advanced
architecture API for custom declarations.
