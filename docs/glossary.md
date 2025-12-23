# Glossary

### Attention Router
A node that uses LLMs to classify an incoming task and route it to the most specific specialist agent.

### CloudEvent
A standard specification for describing event data. Loom uses it as the universal message envelope.

### Fractal Node
Any component (Agent, Tool, Crew) that implements `NodeProtocol`. Nodes can contain other nodes recursively.

### Metabolic Memory
A memory system that mimics biological metabolism: Ingest (Validation) -> Digest (Sanitization) -> Assimilate (PSO).

### PSO (Project State Object)
A structured JSON object representing the "long-term cognition" or current status of a project. Unlike a log, it is a snapshot.
