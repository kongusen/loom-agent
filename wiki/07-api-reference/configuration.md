# Configuration

This page describes Loom's advanced configuration and compatibility objects.

For new application code, start from:

```python
from loom import Agent, Capability, Model, Runtime
```

Use `AgentConfig`, `ModelRef`, `GenerationConfig`, and `create_agent()` when maintaining existing `0.8.x` applications or when you need the lower-level config object vocabulary directly.

Two rules define the surface:

1. Top-level configuration uses explicit objects
2. Extension capacity is preserved through `extensions`, not loose dictionaries

## 1. `AgentConfig`

```python
from loom import AgentConfig, ModelRef
from loom.config import GenerationConfig, MemoryConfig, PolicyConfig, RuntimeConfig

config = AgentConfig(
    model=ModelRef.openai("gpt-4.1-mini"),
    instructions="You are a platform assistant.",
    generation=GenerationConfig(temperature=0.2, max_output_tokens=512),
    tools=[],
    policy=PolicyConfig(),
    memory=MemoryConfig(),
    heartbeat=None,
    runtime=RuntimeConfig(),
    safety_rules=[],
    knowledge=[],
)
```

Field overview:

| Field | Type | Description |
|---|---|---|
| `model` | `ModelRef` | Required model and provider definition |
| `instructions` | `str` | System instructions |
| `generation` | `GenerationConfig` | Generation controls |
| `tools` | `list[ToolSpec]` | Tool declarations |
| `policy` | `PolicyConfig \| None` | Tool governance policy |
| `memory` | `MemoryConfig \| None` | Session memory configuration |
| `heartbeat` | `HeartbeatConfig \| None` | Heartbeat monitoring configuration |
| `runtime` | `RuntimeConfig \| None` | Execution engine controls |
| `safety_rules` | `list[SafetyRule] \| None` | Safety rules |
| `knowledge` | `list[KnowledgeSource]` | Knowledge sources |

## 2. `ModelRef`

`ModelRef` is the stable model reference object and the provider selection entry point.

```python
from loom import ModelRef

anthropic = ModelRef.anthropic("claude-sonnet-4")
openai = ModelRef.openai("gpt-4.1-mini")
gemini = ModelRef.gemini("gemini-2.5-flash")
qwen = ModelRef.qwen("qwen-max")
ollama = ModelRef.ollama("llama3")
```

### Common fields

| Field | Description |
|---|---|
| `provider` | Provider name |
| `name` | Model name |
| `api_base` | Custom base URL |
| `organization` | OpenAI organization |
| `api_key_env` | Custom API key environment variable name |
| `extensions` | Extension fields |

### OpenAI-compatible endpoints

If you are targeting an OpenAI-compatible gateway:

```python
import os

from loom import ModelRef

model = ModelRef.openai(
    "gpt-4.1-mini",
    api_base=os.getenv("OPENAI_BASE_URL"),
)
```

By default, the API key is loaded from `OPENAI_API_KEY`.

If your gateway uses a different environment variable name:

```python
model = ModelRef.openai(
    "my-model",
    api_base=os.getenv("MY_LLM_BASE_URL"),
    api_key_env="MY_LLM_API_KEY",
)
```

## 3. `GenerationConfig`

```python
from loom.config import GenerationConfig

generation = GenerationConfig(
    temperature=0.2,
    max_output_tokens=512,
    extensions={"top_p": 0.95},
)
```

Fields:

| Field | Description |
|---|---|
| `temperature` | Sampling temperature |
| `max_output_tokens` | Maximum output tokens |
| `extensions` | Reserved space for provider-specific extension data |

## 4. Tool Configuration

### Recommended path 1: use `@tool`

```python
from loom import tool


@tool(description="Search documentation", read_only=True)
def search_docs(query: str) -> str:
    return "..."
```

### Recommended path 2: construct `ToolSpec` explicitly

```python
from loom.config import ToolSpec


def search_docs(query: str) -> str:
    return "..."


tool_spec = ToolSpec.from_function(
    search_docs,
    name="search_docs",
    description="Search documentation",
    read_only=True,
)
```

### Important `ToolSpec` fields

| Field | Description |
|---|---|
| `name` | Tool name |
| `description` | Tool description |
| `parameters` | Parameter schema |
| `read_only` | Whether the tool is read-only |
| `destructive` | Whether the tool is destructive |
| `concurrency_safe` | Whether the tool is safe to run concurrently |
| `requires_permission` | Whether the tool requires permission |
| `handler` | Local execution handler |
| `extensions` | Extension fields |

Notes:

- `AgentConfig.tools` accepts only `ToolSpec`
- raw Python callables are not accepted directly
- `@tool` is the simplest way to stay on the public path

## 5. `PolicyConfig`

`PolicyConfig` defines how an agent is allowed to use tools.

```python
from loom.config import (
    PolicyConfig,
    PolicyContext,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
)

policy = PolicyConfig(
    tools=ToolPolicy(
        access=ToolAccessPolicy(
            allow=["read_file", "search_docs"],
            deny=["delete_file"],
            read_only_only=False,
            allow_destructive=False,
        ),
        rate_limits=ToolRateLimitPolicy(max_calls_per_minute=30),
    ),
    context=PolicyContext.named("repo"),
)
```

Use it to:

- restrict the tool set
- block destructive operations
- assign a named policy context
- rate-limit tool calls

## 6. `MemoryConfig`

`MemoryConfig` defines whether session memory is enabled and which backend is used.

```python
from loom.config import MemoryBackend, MemoryConfig

memory = MemoryConfig(
    enabled=True,
    backend=MemoryBackend.in_memory(),
    namespace="assistant-prod",
)
```

If you have a custom backend:

```python
memory = MemoryConfig(
    enabled=True,
    backend=MemoryBackend.custom(
        "redis",
        options={"url": "redis://localhost:6379/0"},
    ),
)
```

Notes:

- `memory=None` means no explicit memory config
- `enabled=False` means memory is explicitly disabled
- the public API stabilizes the memory configuration shape first; backend behavior can continue to evolve

## 7. `HeartbeatConfig`

`HeartbeatConfig` declares watch sources and interrupt behavior.

```python
from loom.config import FilesystemWatchMethod, HeartbeatConfig, WatchConfig

heartbeat = HeartbeatConfig(
    interval=5.0,
    min_entropy_delta=0.1,
    watch_sources=[
        WatchConfig.filesystem(
            paths=["./src", "./configs"],
            method=FilesystemWatchMethod.HASH,
        ),
    ],
)
```

### Supported watch source constructors

- `WatchConfig.filesystem(...)`
- `WatchConfig.process(...)`
- `WatchConfig.resource(...)`
- `WatchConfig.mf_events(...)`

### Resource thresholds

```python
from loom.config import ResourceThresholds, WatchConfig

watch = WatchConfig.resource(
    thresholds=ResourceThresholds(
        cpu_pct=80.0,
        memory_pct=90.0,
    )
)
```

### Interrupt policy

```python
from loom.config import HeartbeatConfig, HeartbeatInterruptPolicy

heartbeat = HeartbeatConfig(
    interrupt_policy=HeartbeatInterruptPolicy(
        low="queue",
        high="request",
        critical="force",
    )
)
```

## 8. `RuntimeConfig`

`RuntimeConfig` controls execution engine behavior.

```python
from loom.config import RuntimeConfig, RuntimeFallback, RuntimeFallbackMode, RuntimeFeatures, RuntimeLimits

runtime = RuntimeConfig(
    limits=RuntimeLimits(
        max_iterations=12,
        max_context_tokens=64_000,
    ),
    features=RuntimeFeatures(
        enable_safety=True,
        fallback=RuntimeFallback(mode=RuntimeFallbackMode.ERROR),
    ),
)
```

### Key fields

| Object | Field | Description |
|---|---|---|
| `RuntimeLimits` | `max_iterations` | Maximum execution iterations |
| `RuntimeLimits` | `max_context_tokens` | Context token ceiling |
| `RuntimeFeatures` | `enable_safety` | Whether safety is enabled |
| `RuntimeFallback` | `mode` | Fallback behavior when the provider is unavailable |

### Fallback behavior

Supported modes:

- `RuntimeFallbackMode.LOCAL_SUMMARY`
- `RuntimeFallbackMode.ERROR`

The default is `LOCAL_SUMMARY`.

This means that when provider initialization fails, Loom can return a local fallback result instead of immediately failing.

If your production environment must fail hard when the model is unavailable:

```python
runtime = RuntimeConfig(
    features=RuntimeFeatures(
        fallback=RuntimeFallback(mode=RuntimeFallbackMode.ERROR),
    )
)
```

## 9. `SafetyRule`

`SafetyRule` declares tool-call veto rules.

### Block an entire class of tools

```python
from loom.config import SafetyRule

rule = SafetyRule.block_tool(
    name="no_delete",
    tool_names=["delete_file"],
    reason="File deletion is forbidden.",
)
```

### Match by argument equality

```python
rule = SafetyRule.when_argument_equals(
    name="no_prod_deploy",
    tool_name="deploy",
    argument="env",
    value="production",
    reason="Production deployment requires manual approval.",
)
```

### Match by argument prefix

```python
rule = SafetyRule.when_argument_startswith(
    name="no_prod_write",
    tool_name="write_file",
    argument="path",
    prefix="/prod/",
    reason="Writing into production paths is forbidden.",
)
```

### Match by argument substring set

```python
rule = SafetyRule.when_argument_contains_any(
    name="no_dangerous_shell",
    tool_name="execute_command",
    argument="cmd",
    values=["rm -rf", "mkfs"],
    reason="Dangerous commands are forbidden.",
)
```

### Custom rule

```python
from loom.config import SafetyEvaluator, SafetyRule

rule = SafetyRule.custom(
    name="business_hours_only",
    reason="Configuration changes are only allowed during business hours.",
    evaluator=SafetyEvaluator.callable(
        lambda tool_name, arguments: tool_name == "modify_config"
        and arguments.get("approved") is not True
    ),
)
```

## 10. `KnowledgeSource`

The stable knowledge contract currently has two parts:

1. declare knowledge sources in `AgentConfig.knowledge`
2. resolve them into a `KnowledgeBundle` with `agent.resolve_knowledge()`

### Inline knowledge

```python
from loom import KnowledgeDocument, KnowledgeSource

knowledge = [
    KnowledgeSource.inline(
        "product-docs",
        [
            KnowledgeDocument(
                title="Session",
                content="Loom provides Session and Run primitives.",
                uri="docs://session",
            ),
            KnowledgeDocument(
                title="Safety",
                content="Loom supports declarative safety rules.",
            ),
        ],
        description="Product documentation",
    )
]
```

### Dynamic knowledge source

```python
from loom.config import (
    KnowledgeCitation,
    KnowledgeEvidence,
    KnowledgeEvidenceItem,
    KnowledgeResolver,
)
from loom import KnowledgeQuery, KnowledgeSource


def resolve_docs(query: KnowledgeQuery) -> KnowledgeEvidence:
    item = KnowledgeEvidenceItem(
        source_name="docs",
        title="API Overview",
        content=f"Answer for: {query.text}",
        uri="kb://api-overview",
        score=0.9,
    )
    citation = KnowledgeCitation(
        source_name="docs",
        title="API Overview",
        uri="kb://api-overview",
        snippet=item.content,
    )
    return KnowledgeEvidence(
        query=query,
        items=[item],
        citations=[citation],
        relevance_score=0.9,
    )


knowledge = [
    KnowledgeSource.dynamic(
        "docs",
        resolver=KnowledgeResolver.callable(
            resolve_docs,
            description="Dynamic knowledge retrieval",
        ),
    )
]
```

### Recommended knowledge usage

```python
from loom import KnowledgeQuery, RunContext

bundle = agent.resolve_knowledge(
    KnowledgeQuery(
        text="How does Loom handle tool calling?",
        top_k=3,
    )
)

result = await agent.run(
    "Explain Loom's tool-calling model based on the provided knowledge.",
    context=RunContext(knowledge=bundle),
)
```

This is currently the clearest, most stable, and most controllable integration pattern.

## 11. The Role of `extensions`

Most stable config objects keep an `extensions` field.

Use it to:

- attach business-specific metadata
- pass through values that are not yet promoted into stable first-class fields
- preserve future extension capacity

Do not push core control logic into `extensions`, or the API will drift back toward an opaque dictionary surface.

## 12. Full Compatibility Configuration Example

This example shows the lower-level compatibility path for existing applications. New applications should usually prefer `Agent(model=Model..., runtime=Runtime..., capabilities=[...])`.

```python
from loom import AgentConfig, ModelRef, create_agent, tool
from loom.config import (
    GenerationConfig,
    HeartbeatConfig,
    MemoryBackend,
    MemoryConfig,
    PolicyConfig,
    PolicyContext,
    RuntimeConfig,
    RuntimeLimits,
    SafetyRule,
    ToolAccessPolicy,
    ToolPolicy,
    ToolRateLimitPolicy,
    WatchConfig,
)


@tool(description="Search documentation", read_only=True)
def search_docs(query: str) -> str:
    return f"results for {query}"


agent = create_agent(
    AgentConfig(
        model=ModelRef.openai("gpt-4.1-mini"),
        instructions="You are a platform engineering assistant.",
        generation=GenerationConfig(
            temperature=0.2,
            max_output_tokens=512,
        ),
        tools=[search_docs],
        policy=PolicyConfig(
            tools=ToolPolicy(
                access=ToolAccessPolicy(
                    allow=["search_docs"],
                    allow_destructive=False,
                ),
                rate_limits=ToolRateLimitPolicy(max_calls_per_minute=30),
            ),
            context=PolicyContext.named("repo-assistant"),
        ),
        memory=MemoryConfig(
            enabled=True,
            backend=MemoryBackend.in_memory(),
            namespace="repo-assistant",
        ),
        heartbeat=HeartbeatConfig(
            interval=5.0,
            watch_sources=[
                WatchConfig.filesystem(paths=["./src"]),
            ],
        ),
        safety_rules=[
            SafetyRule.block_tool(
                name="no_delete",
                tool_names=["delete_file"],
                reason="Delete operations are forbidden.",
            )
        ],
        runtime=RuntimeConfig(
            limits=RuntimeLimits(max_iterations=12),
        ),
    )
)
```

Related examples:

- [00_agent_overview.py](https://github.com/kongusen/loom-agent/blob/main/examples/00_agent_overview.py)
- [12_heartbeat_and_safety.py](https://github.com/kongusen/loom-agent/blob/main/examples/12_heartbeat_and_safety.py)
