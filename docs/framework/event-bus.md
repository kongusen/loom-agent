# Event System (The Nervous System)

Loom is an **Event-Driven System**. If the Fractal Architecture is the skeletal structure, the Event System is the nervous system that connects everything.

## Axiom 2: Event Sovereignty
The second axiom of Loom states: **"All communication must happen via Tasks (Events)."**

This means there are no backdoor function calls between isolated agents. Every interaction—requests, responses, signals, errors—is encapsulated in a standardized event object.

## CloudEvents Standard
Loom strictly adheres to the **CNCF CloudEvents 1.0** specification. This ensures interoperability with external tools, monitoring systems, and other microservices.

### Event Structure
Every event in Loom contains:
*   `id`: Unique identifier.
*   `source`: URI of the sender (e.g., `node://agent-1`).
*   `type`: The kind of event (e.g., `com.loom.task.created`).
*   `data`: The payload (the task details, result, etc.).

## The Universal Bus
All events flow through a **Universal Event Bus**. This architecture decouples senders from receivers, allowing for:

1.  **Observability**: A monitoring tool can subscribe to the bus and see "thoughts" flowing in real-time.
2.  **Replayability**: Events can be logged and replayed for debugging or training.
3.  **Distribution**: Events can be routed over HTTP, WebSocket, or MQTT, allowing nodes to live on different physical machines.

## Key Benefits
*   **Decoupling**: Agents don't need to know who handles their request, just that it was sent.
*   **Traceability**: Every action in the system can be traced back to a specific event chain.
*   **Resilience**: If a node fails, the event acts as a durable record of the intent, allowing for retries.
