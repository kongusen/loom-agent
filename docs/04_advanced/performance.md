# Performance Optimization

Agents can be slow and expensive. Here's how to optimize Loom.

## Token Usage
Large contexts drive up cost and latency.
1.  **Metabolic Memory**: Ensure your `Sanitizer` is compressing history effectively.
2.  **Tool Definitions**: Keep tool descriptions concise. The LLM reads them on every turn.

## Caching
Avoid re-generating answers for identical queries.

```python
# Simple Dict Cache in Provider
class CachedProvider(LLMProvider):
    def __init__(self, wrapped):
        self.cache = {}
        self.wrapped = wrapped
        
    async def chat(self, messages, tools):
        key = str(messages)
        if key in self.cache:
            return self.cache[key]
        resp = await self.wrapped.chat(messages, tools)
        self.cache[key] = resp
        return resp
```

## Concurrency
Use `CrewNode` with `pattern="parallel"` (coming soon) or `asyncio.gather` for independent sub-tasks.
