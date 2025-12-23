# Debugging & Observability

When an agent "goes off the rails," you need visibility into its thought process.

## The Event Trace
Loom emits a rich stream of events. A healthy trace looks like this:

1. `node.request`: User says "Research X".
2. `agent.thought`: Agent plans: "I need to search for X".
3. `tool.call`: Agent calls `search_tool("X")`.
4. `tool.result`: Tool returns search results.
5. `agent.thought`: Agent analyzes results along with memory.
6. `node.response`: Agent gives final answer.

### Common Pathologies

#### The Loop (Repetitive Thoughts)
Trace: `agent.thought` -> `agent.thought` -> `agent.thought`...
- **Diagnosis**: The LLM is stuck in a reasoning loop without calling a tool or concluding.
- **Fix**: Check your `System Prompt`. Explicitly tell it: "When you have enough information, output 'Final Answer:'".

#### The Hallucination (Fake Tools)
Trace: `tool.call` -> `node.error` (Tool Not Found)
- **Diagnosis**: Agent tried to call `SearchWeb` but you only gave it `Calculator`.
- **Fix**: Ensure `tools` list in `AgentNode` matches the prompt description.

## Using Interceptors for Debugging

You can write a custom interceptor to breakpoint or log specific conditions.

```python
class DebugInterceptor(Interceptor):
    async def pre_invoke(self, event):
        if event.type == "tool.call":
            print(f"DEBUG: Tool called with {event.data}")
            # import pdb; pdb.set_trace() # Breakpoint here
        return event
```
