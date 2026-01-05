# Memory & Context Control

Loom v0.3.6 introduces a "Sentient" Memory System. It moves beyond simple rolling windows to a structured, 4-tier hierarchy that mimics biological memory.

## The L1-L4 Hierarchy

### L1: Reactionary Memory (Sensory Buffer)
*   **Duration**: Immediate / Current Turn.
*   **Storage**: RAM (Ephemeral).
*   **Content**: Raw user input, immediate tool outputs.
*   **Purpose**: Instant processing and sanity checking before commitment.

### L2: Working Memory (Short-Term)
*   **Duration**: Current Session / Task Interaction.
*   **Storage**: Redis / RAM.
*   **Content**: The current conversation thread, active goals, recent tool results.
*   **Purpose**: Context for the immediate task at hand.

### L3: Episodic Memory (Long-Term History)
*   **Duration**: Indefinite (Days/Months).
*   **Storage**: Vector Database (Qdrant) + SQL/File.
*   **Content**: Summaries of past sessions, "What happened last week".
*   **Purpose**: Providing continuity across different sessions. "Last time we talked about..."

### L4: Semantic Memory (Persisted Knowledge)
*   **Duration**: Permanent.
*   **Storage**: Vector Database (Qdrant).
*   **Content**: Crystallized facts, User Persona, World Knowledge.
*   **Example**: "User is a vegan", "Project X uses Python 3.11".
*   **Purpose**: Personalized experience and deep understanding.

## Composite Memory Adapter

The system uses a `CompositeMemory` adapter that unifies these layers. When an Agent requests context:

1.  **Recall**: It fetches recent messages (L2).
2.  **Retrieval**: It queries Qdrant for relevant Episodic (L3) and Semantic (L4) facts based on the current query vector.
3.  **Fusion**: It combines these into a single Prompt Context.

## Context Control & Metabolism

To prevent context bloat (and high costs), Loom implements a **Metabolic Lifecycle**:

### 1. Ingest (Eat)
New information enters L1. It is validated and cleaned.

### 2. Digest (Process)
Information moves to L2. If L2 is full, the **ContextCompressor** kicks in.
*   **Compression**: Old L2 messages are summarized.
*   **Extraction**: Key facts are extracted for L4 (e.g., "User updated preference X").

### 3. Assimilate (Store)
Summaries move to L3 (Episodes). Extracted facts move to L4 (Semantic). The raw L2 buffer is cleared or truncated.

This ensures that the "effective context" sent to the LLM is always **high-signal, low-noise**, and fits within token limits without losing important long-term details.
