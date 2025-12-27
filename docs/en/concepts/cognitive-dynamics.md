# Cognitive Dynamics

> **Understanding-oriented** - Deep dive into the theoretical basis of loom-agent

## Overview

Cognitive Dynamics is the theoretical foundation of loom-agent, analogizing the Agent's operation process to biological cognitive processes, emphasizing the flow, transformation, and metabolism of information.

## Core Concepts

### 1. Dual-Process Theory

loom-agent draws from cognitive psychology's dual-process theory (Daniel Kahneman "Thinking, Fast and Slow"), implementing two parallel cognitive processing modes:

**System 1 - Fast Thinking**:
- **Features**: Fast, automatic, intuitive, unconscious
- **Implementation**: Streaming Output (StreamChunks)
- **Cognitive Process**: Pattern recognition, quick reaction
- **Output Form**: Real-time text stream

**System 2 - Slow Thinking**:
- **Features**: Slow, controlled, rational, conscious
- **Implementation**: Thought Nodes (Thoughts)
- **Cognitive Process**: Deep reasoning, logical analysis
- **Output Form**: Structured insights

**Cognitive State Space (S → O)**:
```
S (State Space / Latent Space): High-dimensional internal state
  ├─ Active Thoughts (active_thoughts)
  ├─ Pending Insights (pending_insights)
  └─ Memory Embeddings (memory_embeddings)
         ↓
    Projection Operator π
         ↓
O (Observable / Explicit Space): Low-dimensional observable output
```

### 2. Cognitive Entropy

The degree of disorder and complexity of information:

- **High Entropy**: Information is chaotic, redundant, difficult to process
- **Low Entropy**: Information is ordered, refined, easy to understand

**Goal**: Reduce entropy through cognitive metabolism to maintain system order.

### 2. Cognitive Metabolism

Analogous to biological metabolism, the Agent needs to "digest" and "transform" information:

```
Input Information → Processing → Refining → Output Information
(High Entropy)    (Metabolism) (Entropy Reduction) (Low Entropy)
```

**Key Mechanisms**:
- **Ingestion**: Receiving external information
- **Digestion**: Understanding and processing information
- **Absorption**: Extracting key information
- **Excretion**: Discarding redundant information

### 3. Memory Management

Agent memory is similar to human memory systems:

**Working Memory**:
- Current conversation context
- Recent tool call results
- Temporary state information

**Long-term Memory**:
- Historical conversation records
- Learned knowledge
- User preferences

**Memory Metabolism**:
- Regularly clean up expired information
- Compress redundant content
- Retain key information

### 4. Context Window Management

LLM context window is limited and needs intelligent management:

**Challenges**:
- Token limits (e.g., 4K, 8K, 128K)
- Long conversations leading to context overflow
- Information redundancy reducing efficiency

**Solutions**:
- **Context Sanitizer**: Automatically compresses and refines context
- **Sliding Window**: Retains the last N messages
- **Summary Generation**: Compresses historical conversations into summaries

### 5. Fractal Metabolism

In a Crew, the metabolism process is fractal:

```
Crew Level:
Agent A → Output → Sanitizing → Agent B → Output → Sanitizing → Agent C
         (Metabolism)          (Metabolism)          (Metabolism)
```

**BubbleUpSanitizer**:
- Output of each Agent is sanitized
- Only key information is passed to the next Agent
- Prevents context pollution and information explosion

**Advantages**:
- Keeps information flow clean
- Avoids context overflow in long chains
- Improves overall system efficiency

## Practical Application

### Implementation in loom-agent

**ContextSanitizer**:
```python
class ContextSanitizer:
    async def sanitize(self, context: str, target_token_limit: int) -> str:
        """Compress context to target token limit"""
        # Use LLM to generate summary
        # Retain key information
        # Discard redundant content
```

**BubbleUpSanitizer**:
- Used in Crew's sequential mode
- Output of each Agent is sanitized
- Default limit is 100 tokens

### Design Recommendations

1. **Set logical token budgets**: Avoid excessive consumption
2. **Use Context Sanitizers**: Keep information flow clean
3. **Regularly clean memory**: Prevent memory bloating
4. **Monitor Entropy**: Detect information chaos early

## Summary

Cognitive Dynamics provides the theoretical foundation for Agent systems:

1. **Cognitive Entropy**: Measure of information order
2. **Cognitive Metabolism**: Transformation and refinement of information
3. **Memory Management**: Balance of short-term and long-term memory
4. **Context Management**: Intelligent handling of limited context windows
5. **Fractal Metabolism**: Maintaining clean information in multi-level systems

## Related Documentation

- [Architecture Design](architecture.md) - Understand system architecture
- [Design Philosophy](design-philosophy.md) - Deep dive into design concepts
