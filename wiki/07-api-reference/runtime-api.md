# Runtime API

## AgentRuntime

```python
from loom.api import AgentRuntime, AgentProfile

runtime = AgentRuntime(
    profile=AgentProfile.from_preset("default"),
    provider=provider,          # optional
    event_bus=event_bus,        # optional
    artifact_store=store,       # optional
)

session = runtime.create_session(session_id="s1", metadata={})
session = runtime.get_session("s1")
sessions = runtime.list_sessions()
```

## SessionHandle

```python
task = session.create_task(goal="...", context={"key": "value"})
task = session.get_task(task_id)
tasks = session.list_tasks()
session.close()
```

## TaskHandle

```python
run = task.start()
run = task.get_run(run_id)
runs = task.list_runs()
```

## RunHandle

```python
result = await run.wait()           # RunResult
async for event in run.events():    # AsyncIterator[Event]
    ...
await run.approve(approval_id, "approved")
await run.pause()
await run.resume()
await run.cancel()
artifacts = await run.artifacts()   # list[Artifact]
transcript = await run.transcript() # dict
```

## RunResult

```python
result.state      # RunState.COMPLETED
result.output     # str
result.events     # list[Event]
result.artifacts  # list[Artifact]
result.error      # str | None
```

## RunState

`PENDING` → `RUNNING` → `COMPLETED`  
`RUNNING` → `PAUSED` → `RUNNING`  
`RUNNING` → `FAILED`  
`RUNNING` → `CANCELLED`
