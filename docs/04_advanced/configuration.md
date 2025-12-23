# Configuration & Controls

Loom provides kernel-level controls to ensure your agents behave safely and efficiently. These are configured via the `LoomApp` constructor.

## 1. Budget Control (Token Usage)
Prevent runaway costs by setting a token budget on the dispatcher.

```python
app = LoomApp(control_config={
    "budget": 100000 # Max tokens
})
```
*   **Mechanism**: The `BudgetInterceptor` tracks token usage per node. If a node exceeds the budget, its next request is blocked.

## 2. Timeout Protection
Start tasks with a strict deadline.

```python
# app.run already enforces a default timeout (30s).
# Customize it per task:
result = await app.run("task", "agent", timeout=60.0) 
```
*   **Mechanism**: The `TimeoutInterceptor` injects a deadline into the event metadata. The kernel ensures the call raises `TimeoutError` if response isn't received.

## 3. Human-in-the-Loop (HITL)
Pause execution for sensitive actions (e.g., payments, deleting files).

```python
app = LoomApp(control_config={
    "hitl": ["payment", "rm -rf"] # Trigger keywords
})
```
*   **Mechanism**: The `HITLInterceptor` scans event types and subjects. If a match is found, it pauses execution and awaits manual approval (CLI input or API signal).

## 4. Recursion Depth
Prevent infinite fractal loops (Agent A calls Agent B calls Agent A...).

```python
app = LoomApp(control_config={
    "depth": {"max_depth": 5}
})
```
