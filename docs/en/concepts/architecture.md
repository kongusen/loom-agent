# Architecture Design

> **Understanding-oriented** - Deep dive into the core architecture of loom-agent

## Overview

loom-agent is an event-driven Agent framework based on Fractal design principles, where all components follow a unified protocol.

## Core Design Principles

### 1. Event-Driven Architecture

All components communicate via events instead of direct calls:

```
Agent A → Event Bus → Agent B
```

**Advantages**:
- **Decoupling**: No direct dependencies between components
- **Observability**: All interactions can be monitored
- **Extensibility**: Easy to add interceptors and middleware
- **Distributed**: Supports cross-process and cross-machine deployment

### 2. Fractal Design

All components are Nodes, following the same interface:

```
Node (Base Class)
├── AgentNode (Agent)
├── ToolNode (Tool)
├── CrewNode (Team)
└── RouterNode (Router)
```

**Features**:
- **Unified Interface**: All Nodes implement the `process()` method
- **Recursive Composition**: Structs can contain Agents or other Crews
- **Self-Similarity**: Use the same patterns at different levels

## Dual-Process Architecture

loom-agent draws from cognitive psychology's dual-process theory, implementing two parallel processing systems:

### System 1: Reactive System (Fast Path)

**Features**: Fast, intuitive, streaming output

```
User Input → EventBus → Agent → LLM Stream → StreamChunks → Real-time Output
```

**Mechanism**:
- Uses streaming API (`stream_chat()`)
- Emits `agent.stream.chunk` events
- Provides immediate feedback and response

**Use Cases**:
- Conversational interaction
- Quick Q&A
- Real-time feedback

### System 2: Deliberative System (Slow Path)

**Features**: Deep, rational, thought process

```
User Input → EventBus → Agent → Generate Thought → Deep Thinking → Projection → Insight Output
```

**Mechanism**:
- Creates Ephemeral Nodes
- Maintains Cognitive State Space (CognitiveState)
- Outputs insights via ProjectionOperator

**Use Cases**:
- Complex reasoning
- Multi-step planning
- Deep analysis

### Dual System Collaboration

Two systems work in parallel and complement each other:

```
┌─────────────────────────────────────────┐
│          User Input → EventBus          │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
   System 1         System 2
  (Fast Stream)    (Deep Thought)
       │               │
   StreamChunks    Thoughts
       │               │
       └───────┬───────┘
               │
         Projection
               │
          Final Output
```

**Collaboration Mechanism**:
- System 2 starts before or in parallel with System 1
- System 2 insights can be injected into System 1's stream via `thought_injection`
- CognitiveState maintains shared context for both systems

**Cognitive State Space (S)**:
- High-dimensional internal state: contains all active thoughts, memories, insights
- S is projected to low-dimensional observable output O via Projection Operator π
- Implements "Internal Chaos → External Order" transformation

## Core Components

### Dispatcher

The core of event scheduling, responsible for:
- Managing EventBus
- Routing events to the correct Node
- Handling Interceptors

### EventBus

Implementation of Publish-Subscribe pattern:
- Nodes subscribe to specific topics
- Publishes events to subscribers
- Supports asynchronous event delivery

### Node

Base class for all components:
- `node_id`: Unique identifier
- `source_uri`: Event source URI
- `process(event)`: Core method for handling events
- `call(target, data)`: Call other Nodes

### AgentNode

Intelligent node with LLM capabilities:
- Calls LLM to generate response
- Manages tool calls
- Maintains conversation memory

### ToolNode

Node encapsulating specific functionality:
- Executes specific tasks (calculation, file operations, etc.)
- Provides Tool Definition
- Returns execution results

### CrewNode

Orchestrates collaboration of multiple nodes:
- Manages list of Agents
- Implements collaboration patterns (sequential, parallel)
- Aggregates execution results

## Event Flow

### Basic Call Flow

```
1. User call → app.run(agent, task)
2. Create request event → CloudEvent(type="node.request")
3. Publish to Event Bus → EventBus.publish()
4. Agent receives event → agent.process(event)
5. Agent processes task → LLM call + Tool call
6. Return response event → CloudEvent(type="node.response")
7. User receives result ← Return response data
```

### Tool Call Flow

When an Agent needs to use a tool:

```
1. LLM returns tool call request
2. Agent calls Tool via Event Bus
3. Tool executes and returns result
4. Agent passes result back to LLM
5. LLM generates final response
```

## Protocol Design

### CloudEvents Standard

loom-agent uses CloudEvents as the event format:

```python
{
    "specversion": "1.0",
    "type": "node.request",
    "source": "/node/agent-1",
    "id": "unique-event-id",
    "datacontenttype": "application/json",
    "data": {
        "task": "User Task"
    }
}
```

**Advantages**:
- **Standardization**: Follows CNCF CloudEvents specification
- **Interoperability**: Easy to integrate with other systems
- **Traceability**: Supports distributed tracing (traceparent)

### Protocol-First

All components implement the `NodeProtocol` interface:

```python
class NodeProtocol(Protocol):
    node_id: str
    source_uri: str

    async def process(self, event: CloudEvent) -> Any:
        ...
```

This ensures component replaceability and testability.

## Summary

loom-agent's architecture design embodies the following characteristics:

1. **Event-Driven**: Decouples components, improves observability
2. **Fractal Design**: Unified interface, recursive composition
3. **Protocol-First**: Standardized communication, easy integration
4. **Simple & Elegant**: Minimizes complexity, maximizes flexibility

## Related Documentation

- [Cognitive Dynamics](cognitive-dynamics.md) - Understand Agent's cognitive process
- [Design Philosophy](design-philosophy.md) - Deep dive into design concepts
