# Deployment & Production

Deploying Loom in production requires considering Observability, State, and Scaling.

## 1. Observability (Logging & Tracing)
Loom uses `structlog` for structured JSON logging.
- Ensure your environment captures stdout/stderr.
- Use the `TracingInterceptor` (enabled by default) to trace requests across nodes using W3C Trace Context.

## 2. State Persistence
By default, `StateStore` is in-memory.
- For production, implement a `StateStore` backed by a database (Postgres/Redis) to persist the `ProjectStateObject` (PSO).

## 3. Scaling
To scale horizontally:
1. Use a distributed Transport (e.g., Redis Pub/Sub).
2. Deploy multiple instances of your App.
3. Ensure Nodes have unique IDs or are stateless workers consuming from a shared queue.
