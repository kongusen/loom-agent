Run poetry run ruff check .
examples/01_hello_agent.py:10:1: I001 [*] Import block is un-sorted or un-formatted
examples/02_provider_config.py:11:1: I001 [*] Import block is un-sorted or un-formatted
examples/03_events_and_artifacts.py:9:1: I001 [*] Import block is un-sorted or un-formatted
examples/04_multi_task_session.py:9:1: I001 [*] Import block is un-sorted or un-formatted
examples/05_multi_agent.py:14:1: I001 [*] Import block is un-sorted or un-formatted
examples/05_multi_agent.py:15:68: F401 [*] `loom.orchestration.Task` imported but unused
examples/06_evolution.py:14:1: I001 [*] Import block is un-sorted or un-formatted
loom/__init__.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/__init__.py:6:26: F401 `.__version__.__version__` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:13:5: F401 `.api.AgentRuntime` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:14:5: F401 `.api.SessionHandle` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:15:5: F401 `.api.TaskHandle` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:16:5: F401 `.api.RunHandle` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:18:5: F401 `.api.Session` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:19:5: F401 `.api.Task` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:20:5: F401 `.api.Run` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:21:5: F401 `.api.Event` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:22:5: F401 `.api.Approval` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:23:5: F401 `.api.Artifact` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:24:5: F401 `.api.RunState` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:25:5: F401 `.api.RunResult` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:26:5: F401 `.api.EvidencePack` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:27:5: F401 `.api.Citation` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:29:5: F401 `.api.AgentConfig` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:30:5: F401 `.api.LLMConfig` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:31:5: F401 `.api.ToolConfig` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:32:5: F401 `.api.PolicyConfig` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:34:5: F401 `.api.AgentProfile` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:35:5: F401 `.api.PolicySet` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:37:5: F401 `.api.KnowledgeRegistry` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:38:5: F401 `.api.KnowledgeSource` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:39:5: F401 `.api.TrustTier` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:41:17: F401 `.api.EventBus` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:42:5: F401 `.api.EventStream` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:43:5: F401 `.api.ArtifactStore` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:46:24: F401 `.providers.LLMProvider` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:46:37: F401 `.providers.CompletionParams` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/__init__.py:46:55: F401 `.providers.TokenUsage` imported but unused; consider removing, adding to `__all__`, or using a redundant alias
loom/api/__init__.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/artifacts.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/artifacts.py:23:40: UP007 [*] Use `X | Y` for type annotations
loom/api/config.py:12:17: UP007 [*] Use `X | Y` for type annotations
loom/api/events.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/events.py:5:1: UP035 [*] Import from `collections.abc` instead: `Awaitable`, `Callable`
loom/api/events.py:24:21: UP007 [*] Use `X | Y` for type annotations
loom/api/events.py:35:21: UP007 [*] Use `X | Y` for type annotations
loom/api/events.py:104:24: UP041 [*] Replace aliased errors with `TimeoutError`
loom/api/handles.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/handles.py:7:1: UP035 [*] Import from `collections.abc` instead: `AsyncIterator`
loom/api/handles.py:25:52: F821 Undefined name `AgentRuntime`
loom/api/handles.py:37:18: UP007 [*] Use `X | Y` for type annotations
loom/api/handles.py:191:1: W293 [*] Blank line contains whitespace
loom/api/handles.py:195:1: W293 [*] Blank line contains whitespace
loom/api/handles.py:197:1: W293 [*] Blank line contains whitespace
loom/api/handles.py:206:1: W293 [*] Blank line contains whitespace
loom/api/handles.py:220:1: W293 [*] Blank line contains whitespace
loom/api/knowledge.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/knowledge.py:30:38: UP007 [*] Use `X | Y` for type annotations
loom/api/models.py:75:26: UP007 [*] Use `X | Y` for type annotations
loom/api/models.py:90:21: UP007 [*] Use `X | Y` for type annotations
loom/api/models.py:104:18: UP007 [*] Use `X | Y` for type annotations
loom/api/models.py:175:23: UP007 [*] Use `X | Y` for type annotations
loom/api/models.py:197:12: UP007 [*] Use `X | Y` for type annotations
loom/api/runtime.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/api/runtime.py:30:21: UP007 [*] Use `X | Y` for type annotations
loom/api/runtime.py:31:19: UP007 [*] Use `X | Y` for type annotations
loom/api/runtime.py:41:47: UP007 [*] Use `X | Y` for type annotations
loom/capabilities/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/capabilities/catalog.py:8:1: W293 [*] Blank line contains whitespace
loom/capabilities/catalog.py:11:1: W293 [*] Blank line contains whitespace
loom/capabilities/catalog.py:15:1: W293 [*] Blank line contains whitespace
loom/capabilities/loader.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/capabilities/loader.py:3:23: F401 [*] `.registry.Capability` imported but unused
loom/capabilities/plugin.py:8:1: W293 [*] Blank line contains whitespace
loom/capabilities/plugin.py:13:1: W293 [*] Blank line contains whitespace
loom/capabilities/plugin.py:22:1: W293 [*] Blank line contains whitespace
loom/capabilities/plugin.py:25:1: W293 [*] Blank line contains whitespace
loom/capabilities/plugin.py:30:1: W293 [*] Blank line contains whitespace
loom/capabilities/registry.py:11:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/event_bus.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/event_bus.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/cluster/event_bus.py:48:27: ARG002 Unused method argument: `since`
loom/cluster/fork.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/fork.py:5:21: F401 [*] `..types.Dashboard` imported but unused
loom/cluster/shared_memory.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/subagent_result.py:6:1: UP035 `typing.Dict` is deprecated, use `dict` instead
loom/cluster/subagent_result.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/subagent_result.py:14:13: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/cluster/subagent_result.py:15:19: UP007 [*] Use `X | Y` for type annotations
loom/cluster/subagent_result.py:15:28: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/cluster/subagent_result.py:17:26: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/cluster/versioned_writer.py:6:1: UP035 `typing.Dict` is deprecated, use `dict` instead
loom/cluster/versioned_writer.py:6:1: UP035 `typing.List` is deprecated, use `list` instead
loom/cluster/versioned_writer.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/cluster/versioned_writer.py:22:24: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/cluster/versioned_writer.py:22:34: UP006 [*] Use `list` instead of `List` for type annotation
loom/context/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/context/compression.py:13:1: I001 [*] Import block is un-sorted or un-formatted
loom/context/compression.py:105:57: ARG002 Unused method argument: `goal`
loom/context/event_aggregator.py:6:1: UP035 `typing.List` is deprecated, use `list` instead
loom/context/event_aggregator.py:6:1: UP035 `typing.Dict` is deprecated, use `dict` instead
loom/context/event_aggregator.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/context/event_aggregator.py:12:33: UP006 [*] Use `list` instead of `List` for type annotation
loom/context/event_aggregator.py:12:38: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/context/event_aggregator.py:12:58: UP006 [*] Use `list` instead of `List` for type annotation
loom/context/event_aggregator.py:12:63: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/context/manager.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/context/partitions.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/context/renewal.py:17:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/__init__.py:9:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/integration.py:9:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/mcp.py:131:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/mcp.py:131:9: E401 [*] Multiple imports on one line
loom/ecosystem/mcp.py:196:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/mcp.py:196:13: E401 [*] Multiple imports on one line
loom/ecosystem/mcp.py:245:1: E402 Module level import not at top of file
loom/ecosystem/mcp.py:245:1: I001 [*] Import block is un-sorted or un-formatted
loom/ecosystem/skill.py:13:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/evolution/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/evolution/dashboard.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/evolution/dashboard.py:7:1: UP035 `typing.List` is deprecated, use `list` instead
loom/evolution/dashboard.py:21:23: UP006 [*] Use `list` instead of `List` for type annotation
loom/evolution/engine.py:6:1: W293 [*] Blank line contains whitespace
loom/evolution/engine.py:9:1: W293 [*] Blank line contains whitespace
loom/evolution/engine.py:13:1: W293 [*] Blank line contains whitespace
loom/evolution/feedback.py:6:1: W293 [*] Blank line contains whitespace
loom/evolution/feedback.py:9:1: W293 [*] Blank line contains whitespace
loom/evolution/feedback.py:13:1: W293 [*] Blank line contains whitespace
loom/evolution/strategies.py:42:9: B010 [*] Do not call `setattr` with a constant attribute value. It is not any safer than normal property access.
loom/evolution/strategies.py:135:12: UP038 Use `X | Y` in `isinstance` call instead of `(X, Y)`
loom/memory/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/memory/persistent.py:9:1: W293 [*] Blank line contains whitespace
loom/memory/persistent.py:13:1: W293 [*] Blank line contains whitespace
loom/memory/persistent.py:19:1: W293 [*] Blank line contains whitespace
loom/memory/persistent.py:25:14: UP015 [*] Unnecessary open mode parameters
loom/memory/persistent.py:27:1: W293 [*] Blank line contains whitespace
loom/memory/semantic.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/memory/semantic.py:3:36: F401 [*] `dataclasses.field` imported but unused
loom/memory/semantic.py:70:43: B905 [*] `zip()` without an explicit `strict=` parameter
loom/memory/session.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/memory/session.py:12:1: W293 [*] Blank line contains whitespace
loom/memory/session.py:18:1: W293 [*] Blank line contains whitespace
loom/memory/session.py:22:1: W293 [*] Blank line contains whitespace
loom/memory/store.py:8:1: W293 [*] Blank line contains whitespace
loom/memory/store.py:12:1: W293 [*] Blank line contains whitespace
loom/memory/store.py:20:1: W293 [*] Blank line contains whitespace
loom/memory/store.py:23:1: W293 [*] Blank line contains whitespace
loom/memory/store.py:26:1: W293 [*] Blank line contains whitespace
loom/memory/working.py:8:1: W293 [*] Blank line contains whitespace
loom/memory/working.py:12:1: W293 [*] Blank line contains whitespace
loom/memory/working.py:18:1: W293 [*] Blank line contains whitespace
loom/memory/working.py:22:1: W293 [*] Blank line contains whitespace
loom/orchestration/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/orchestration/communication.py:8:1: W293 [*] Blank line contains whitespace
loom/orchestration/communication.py:11:1: W293 [*] Blank line contains whitespace
loom/orchestration/communication.py:15:1: W293 [*] Blank line contains whitespace
loom/orchestration/coordinator.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/orchestration/coordinator.py:12:1: W293 [*] Blank line contains whitespace
loom/orchestration/coordinator.py:16:1: W293 [*] Blank line contains whitespace
loom/orchestration/coordinator.py:20:1: W293 [*] Blank line contains whitespace
loom/orchestration/coordinator.py:55:24: UP041 [*] Replace aliased errors with `TimeoutError`
loom/orchestration/events.py:9:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/orchestration/events.py:9:1: I001 [*] Import block is un-sorted or un-formatted
loom/orchestration/events.py:20:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:25:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:28:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:34:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:40:9: F811 Redefinition of unused `publish` from line 21
loom/orchestration/events.py:44:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:46:1: W293 [*] Blank line contains whitespace
loom/orchestration/events.py:50:9: F811 Redefinition of unused `subscribe` from line 29
loom/orchestration/events.py:56:9: F811 Redefinition of unused `unsubscribe` from line 35
loom/orchestration/subagent.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/providers/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/providers/anthropic.py:3:1: UP035 [*] Import from `collections.abc` instead: `AsyncIterator`
loom/providers/base.py:6:36: F401 [*] `dataclasses.field` imported but unused
loom/providers/base.py:7:1: UP035 [*] Import from `collections.abc` instead: `AsyncIterator`
loom/providers/gemini.py:3:1: UP035 [*] Import from `collections.abc` instead: `AsyncIterator`
loom/providers/openai.py:3:1: UP035 [*] Import from `collections.abc` instead: `AsyncIterator`
loom/runtime/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/heartbeat.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/heartbeat.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/runtime/heartbeat.py:69:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/heartbeat_strategy.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/loop.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/loop.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/runtime/loop.py:5:32: F401 [*] `..types.Dashboard` imported but unused
loom/runtime/monitors.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/runtime/urgency_classifier.py:39:28: ARG002 Unused method argument: `event`
loom/safety/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/safety/constraints.py:8:1: W293 [*] Blank line contains whitespace
loom/safety/constraints.py:11:1: W293 [*] Blank line contains whitespace
loom/safety/constraints.py:17:1: W293 [*] Blank line contains whitespace
loom/safety/hooks.py:13:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/safety/veto.py:7:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/safety/veto_auditor.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/base.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/base.py:35:30: ARG002 Unused method argument: `input_data`
loom/tools/base.py:39:33: ARG002 Unused method argument: `context`
loom/tools/builtin/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/file_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/file_operations.py:5:8: F401 [*] `os` imported but unused
loom/tools/builtin/file_operations.py:15:10: UP015 [*] Unnecessary open mode parameters
loom/tools/builtin/file_operations.py:52:10: UP015 [*] Unnecessary open mode parameters
loom/tools/builtin/file_operations.py:107:18: UP015 [*] Unnecessary open mode parameters
loom/tools/builtin/file_operations.py:117:9: E722 Do not use bare `except`
loom/tools/builtin/misc_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/misc_operations.py:7:37: ARG001 Unused function argument: `block`
loom/tools/builtin/misc_operations.py:7:57: ARG001 Unused function argument: `timeout`
loom/tools/builtin/notebook_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/notebook_operations.py:9:10: UP015 [*] Unnecessary open mode parameters
loom/tools/builtin/shell_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/shell_operations.py:3:8: F401 [*] `subprocess` imported but unused
loom/tools/builtin/shell_operations.py:29:12: UP041 [*] Replace aliased errors with `TimeoutError`
loom/tools/builtin/shell_operations.py:31:9: B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
loom/tools/builtin/task_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_agent_task.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_file.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_file.py:4:31: F401 [*] `.shell_operations.bash` imported but unused
loom/tools/builtin/tools_file.py:5:29: F401 [*] `.web_operations.web_fetch` imported but unused
loom/tools/builtin/tools_file.py:5:40: F401 [*] `.web_operations.web_search` imported but unused
loom/tools/builtin/tools_file.py:6:31: F401 [*] `.agent_operations.spawn_agent` imported but unused
loom/tools/builtin/tools_file.py:6:44: F401 [*] `.agent_operations.ask_user` imported but unused
loom/tools/builtin/tools_file.py:7:30: F401 [*] `.task_operations.task_create` imported but unused
loom/tools/builtin/tools_file.py:7:43: F401 [*] `.task_operations.task_update` imported but unused
loom/tools/builtin/tools_file.py:7:56: F401 [*] `.task_operations.task_list` imported but unused
loom/tools/builtin/tools_file.py:7:67: F401 [*] `.task_operations.task_get` imported but unused
loom/tools/builtin/tools_file.py:8:29: F401 [*] `.mcp_operations.mcp_list_resources` imported but unused
loom/tools/builtin/tools_file.py:8:49: F401 [*] `.mcp_operations.mcp_read_resource` imported but unused
loom/tools/builtin/tools_file.py:8:68: F401 [*] `.mcp_operations.mcp_call_tool` imported but unused
loom/tools/builtin/tools_file.py:9:34: F401 [*] `.notebook_operations.notebook_edit` imported but unused
loom/tools/builtin/tools_file.py:10:31: F401 [*] `.skill_operations.skill_invoke` imported but unused
loom/tools/builtin/tools_file.py:10:45: F401 [*] `.skill_operations.skill_discover` imported but unused
loom/tools/builtin/tools_file.py:11:29: F401 [*] `.lsp_operations.lsp_get_diagnostics` imported but unused
loom/tools/builtin/tools_file.py:11:50: F401 [*] `.lsp_operations.lsp_execute_code` imported but unused
loom/tools/builtin/tools_file.py:12:34: F401 [*] `.workflow_operations.enter_plan_mode` imported but unused
loom/tools/builtin/tools_file.py:12:51: F401 [*] `.workflow_operations.exit_plan_mode` imported but unused
loom/tools/builtin/tools_file.py:12:67: F401 [*] `.workflow_operations.enter_worktree` imported but unused
loom/tools/builtin/tools_file.py:12:83: F401 [*] `.workflow_operations.exit_worktree` imported but unused
loom/tools/builtin/tools_file.py:13:32: F401 [*] `.config_operations.config_get` imported but unused
loom/tools/builtin/tools_file.py:13:44: F401 [*] `.config_operations.config_set` imported but unused
loom/tools/builtin/tools_file.py:13:56: F401 [*] `.config_operations.tool_search` imported but unused
loom/tools/builtin/tools_file.py:14:30: F401 [*] `.misc_operations.task_output` imported but unused
loom/tools/builtin/tools_file.py:14:43: F401 [*] `.misc_operations.task_stop` imported but unused
loom/tools/builtin/tools_file.py:14:54: F401 [*] `.misc_operations.sleep` imported but unused
loom/tools/builtin/tools_file.py:14:61: F401 [*] `.misc_operations.send_message` imported but unused
loom/tools/builtin/tools_file.py:14:75: F401 [*] `.misc_operations.todo_write` imported but unused
loom/tools/builtin/tools_file.py:15:30: F401 [*] `.team_operations.team_create` imported but unused
loom/tools/builtin/tools_file.py:15:43: F401 [*] `.team_operations.team_delete` imported but unused
loom/tools/builtin/tools_file.py:15:56: F401 [*] `.team_operations.remote_trigger` imported but unused
loom/tools/builtin/tools_mcp.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_notebook_skill_lsp.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_registry.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_shell_web.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/tools_workflow_config.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/web_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/builtin/web_operations.py:7:31: ARG001 Unused function argument: `prompt`
loom/tools/builtin/web_operations.py:156:44: ARG002 Unused method argument: `attrs`
loom/tools/builtin/web_operations.py:159:37: ARG002 Unused method argument: `tag`
loom/tools/evidence_compressor.py:6:1: UP035 `typing.List` is deprecated, use `list` instead
loom/tools/evidence_compressor.py:6:1: UP035 `typing.Dict` is deprecated, use `dict` instead
loom/tools/evidence_compressor.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/evidence_compressor.py:11:40: UP006 [*] Use `list` instead of `List` for type annotation
loom/tools/evidence_compressor.py:11:45: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/tools/evidence_compressor.py:11:65: UP006 [*] Use `list` instead of `List` for type annotation
loom/tools/evidence_compressor.py:11:70: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/tools/evidence_compressor.py:40:40: UP006 [*] Use `list` instead of `List` for type annotation
loom/tools/evidence_compressor.py:40:45: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/tools/executor.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/governance.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/governance.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/tools/governance.py:30:20: UP038 Use `X | Y` in `isinstance` call instead of `(X, Y)`
loom/tools/knowledge.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/tools/knowledge.py:97:13: SIM108 Use ternary operator `data = data["chunks"] if "chunks" in data else [data]` instead of `if`-`else`-block
loom/tools/knowledge.py:97:13: SIM401 Use `data = data.get("chunks", [data])` instead of an `if` block
loom/tools/knowledge.py:226:45: B905 [*] `zip()` without an explicit `strict=` parameter
loom/tools/pipeline.py:3:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/tools/pipeline.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/pipeline.py:45:9: F841 Local variable `risk` is assigned to but never used
loom/tools/pipeline.py:84:32: ARG002 Unused method argument: `data`
loom/tools/pipeline.py:84:44: ARG002 Unused method argument: `schema`
loom/tools/pipeline.py:88:42: ARG002 Unused method argument: `input_data`
loom/tools/registry.py:3:1: UP035 `typing.Dict` is deprecated, use `dict` instead
loom/tools/registry.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/registry.py:9:1: W293 [*] Blank line contains whitespace
loom/tools/registry.py:11:21: UP006 [*] Use `dict` instead of `Dict` for type annotation
loom/tools/registry.py:12:1: W293 [*] Blank line contains whitespace
loom/tools/registry.py:16:1: W293 [*] Blank line contains whitespace
loom/tools/registry.py:20:1: W293 [*] Blank line contains whitespace
loom/tools/registry.py:24:1: W293 [*] Blank line contains whitespace
loom/tools/resource_allocator.py:6:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/scenario.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/tools/scenario.py:4:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/tools/schema.py:9:1: UP035 [*] Import from `collections.abc` instead: `Callable`
loom/types/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/types/events.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/types/results.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/utils/__init__.py:3:1: I001 [*] Import block is un-sorted or un-formatted
loom/utils/logging.py:11:1: W293 [*] Blank line contains whitespace
loom/utils/logging.py:18:1: W293 [*] Blank line contains whitespace
loom/utils/tokens.py:4:29: ARG001 Unused function argument: `model`
tests/api/test_artifacts.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_artifacts.py:3:8: F401 [*] `pytest` imported but unused
tests/api/test_config.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_config.py:3:8: F401 [*] `pytest` imported but unused
tests/api/test_events.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_handles.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_models.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_models.py:3:8: F401 [*] `pytest` imported but unused
tests/api/test_profile.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_runtime.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/api/test_runtime.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_builtin_tools.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_builtin_tools.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_cluster.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_cluster.py:4:8: F401 [*] `json` imported but unused
tests/core/test_cluster.py:183:13: F841 Local variable `bus` is assigned to but never used
tests/core/test_context.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_context.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_context_extended.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_context_extended.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_ecosystem.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_evolution.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_evolution.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_memory.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_memory.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_more_tools.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_more_tools.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_orchestration.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_orchestration.py:11:33: F401 [*] `loom.providers.base.CompletionParams` imported but unused
tests/core/test_orchestration.py:11:51: F401 [*] `loom.providers.base.LLMProvider` imported but unused
tests/core/test_orchestration.py:192:9: E731 Do not assign a `lambda` expression, use a `def`
tests/core/test_providers.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_providers.py:9:5: F401 [*] `loom.providers.LLMProvider` imported but unused
tests/core/test_runtime.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_runtime.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_runtime_loop.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_runtime_loop.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_runtime_loop.py:5:8: F401 [*] `threading` imported but unused
tests/core/test_runtime_loop.py:15:35: F401 [*] `loom.types.Dashboard` imported but unused
tests/core/test_runtime_loop.py:103:13: F841 Local variable `result` is assigned to but never used
tests/core/test_safety.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_safety.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_safety.py:4:27: F401 [*] `unittest.mock.MagicMock` imported but unused
tests/core/test_safety.py:9:67: F401 [*] `loom.safety.permissions.Permission` imported but unused
tests/core/test_safety.py:22:9: E731 Do not assign a `lambda` expression, use a `def`
tests/core/test_tool_operations.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_tool_operations.py:7:27: F401 [*] `unittest.mock.patch` imported but unused
tests/core/test_tool_operations.py:7:34: F401 [*] `unittest.mock.AsyncMock` imported but unused
tests/core/test_tool_operations.py:14:52: F401 [*] `loom.tools.builtin.task_operations._tasks` imported but unused
tests/core/test_tool_operations.py:14:60: F401 [*] `loom.tools.builtin.task_operations.Task` imported but unused
tests/core/test_utils.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_utils.py:3:8: F401 [*] `pytest` imported but unused
tests/core/test_workflow_tools.py:3:1: I001 [*] Import block is un-sorted or un-formatted
tests/core/test_workflow_tools.py:3:8: F401 [*] `pytest` imported but unused
tests/integration/test_workflow.py:3:1: I001 [*] Import block is un-sorted or un-formatted
Found 358 errors.
[*] 289 fixable with the `--fix` option (9 hidden fixes can be enabled with the `--unsafe-fixes` option).




Run poetry run mypy loom
loom/tools/knowledge.py:138: error: Returning Any from function declared to return "float"  [no-any-return]
loom/tools/knowledge.py:239: error: Returning Any from function declared to return "float"  [no-any-return]
loom/ecosystem/skill.py:103: error: Library stubs not installed for "yaml"  [import-untyped]
loom/ecosystem/skill.py:103: note: Hint: "python3 -m pip install types-PyYAML"
loom/ecosystem/skill.py:103: note: (or run "mypy --install-types" to install all missing stub packages)
loom/ecosystem/skill.py:103: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
loom/ecosystem/skill.py:141: error: Cannot infer type of lambda  [misc]
loom/evolution/strategies.py:74: error: Unsupported operand types for + ("None" and "int")  [operator]
loom/evolution/strategies.py:74: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:74: error: Unsupported operand types for + ("str" and "int")  [operator]
loom/evolution/strategies.py:78: error: Unsupported operand types for + ("None" and "float")  [operator]
loom/evolution/strategies.py:78: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:78: error: Unsupported operand types for + ("str" and "float")  [operator]
loom/evolution/strategies.py:79: error: Unsupported operand types for + ("None" and "int")  [operator]
loom/evolution/strategies.py:79: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:79: error: Unsupported operand types for + ("str" and "int")  [operator]
loom/evolution/strategies.py:83: error: Unsupported operand types for + ("None" and "int")  [operator]
loom/evolution/strategies.py:83: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:83: error: Unsupported operand types for + ("str" and "int")  [operator]
loom/evolution/strategies.py:86: error: Unsupported operand types for + ("None" and "int")  [operator]
loom/evolution/strategies.py:86: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:86: error: Unsupported operand types for + ("str" and "int")  [operator]
loom/evolution/strategies.py:91: error: Argument 1 to "int" has incompatible type "float | int | str | None"; expected "str | Buffer | SupportsInt | SupportsIndex | SupportsTrunc"  [arg-type]
loom/evolution/strategies.py:92: error: Argument 1 to "int" has incompatible type "float | int | str | None"; expected "str | Buffer | SupportsInt | SupportsIndex | SupportsTrunc"  [arg-type]
loom/evolution/strategies.py:93: error: Argument 1 to "int" has incompatible type "float | int | str | None"; expected "str | Buffer | SupportsInt | SupportsIndex | SupportsTrunc"  [arg-type]
loom/evolution/strategies.py:94: error: Argument 1 to "int" has incompatible type "float | int | str | None"; expected "str | Buffer | SupportsInt | SupportsIndex | SupportsTrunc"  [arg-type]
loom/evolution/strategies.py:95: error: Unsupported operand types for / ("str" and "int")  [operator]
loom/evolution/strategies.py:95: error: Unsupported operand types for / ("None" and "int")  [operator]
loom/evolution/strategies.py:95: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:117: error: Unsupported operand types for <= ("int" and "None")  [operator]
loom/evolution/strategies.py:117: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:117: error: Unsupported operand types for >= ("str" and "int")  [operator]
loom/evolution/strategies.py:117: error: Unsupported operand types for <= ("float" and "None")  [operator]
loom/evolution/strategies.py:117: error: Unsupported operand types for >= ("str" and "float")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for <= ("int" and "None")  [operator]
loom/evolution/strategies.py:122: note: Left operand is of type "float | int | str | None"
loom/evolution/strategies.py:122: error: Unsupported operand types for >= ("str" and "int")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("float" and "str")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("float" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("int" and "str")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("int" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("str" and "float")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("str" and "int")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for > ("str" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for < ("float" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for < ("int" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported operand types for < ("str" and "None")  [operator]
loom/evolution/strategies.py:122: error: Unsupported left operand type for > ("None")  [operator]
loom/evolution/strategies.py:122: note: Both left and right operands are unions
loom/evolution/strategies.py:272: error: Need type annotation for "active" (hint: "active: dict[<type>, <type>] = ...")  [var-annotated]
loom/evolution/strategies.py:272: error: Need type annotation for "stale" (hint: "stale: dict[<type>, <type>] = ...")  [var-annotated]
loom/tools/pipeline.py:14: error: Incompatible types in assignment (expression has type "None", variable has type "dict[str, list[Callable[..., Any]]]")  [assignment]
loom/memory/persistent.py:26: error: Returning Any from function declared to return "dict[Any, Any] | None"  [no-any-return]
loom/cluster/shared_memory.py:23: error: Returning Any from function declared to return "dict[Any, Any] | None"  [no-any-return]
loom/ecosystem/mcp.py:59: error: Incompatible types in assignment (expression has type "None", variable has type "list[dict[Any, Any]]")  [assignment]
loom/ecosystem/mcp.py:60: error: Incompatible types in assignment (expression has type "None", variable has type "list[dict[Any, Any]]")  [assignment]
loom/ecosystem/mcp.py:136: error: Argument 1 to "Popen" has incompatible type "list[str | None]"; expected "str | bytes | PathLike[str] | PathLike[bytes] | Sequence[str | bytes | PathLike[str] | PathLike[bytes]]"  [arg-type]
loom/ecosystem/mcp.py:144: error: Item "None" of "IO[bytes] | None" has no attribute "write"  [union-attr]
loom/ecosystem/mcp.py:145: error: Item "None" of "IO[bytes] | None" has no attribute "flush"  [union-attr]
loom/ecosystem/mcp.py:152: error: Item "None" of "IO[bytes] | None" has no attribute "readline"  [union-attr]
loom/ecosystem/mcp.py:153: error: Returning Any from function declared to return "dict[Any, Any]"  [no-any-return]
loom/runtime/heartbeat.py:43: error: Incompatible types in assignment (expression has type "Thread", variable has type "None")  [assignment]
loom/runtime/heartbeat.py:44: error: "None" has no attribute "start"  [attr-defined]
loom/runtime/heartbeat.py:73: error: Need type annotation for "_fs_monitors" (hint: "_fs_monitors: dict[<type>, <type>] = ...")  [var-annotated]
loom/runtime/heartbeat.py:84: error: Need type annotation for "_proc_monitors" (hint: "_proc_monitors: dict[<type>, <type>] = ...")  [var-annotated]
loom/runtime/heartbeat.py:92: error: Need type annotation for "_res_monitors" (hint: "_res_monitors: dict[<type>, <type>] = ...")  [var-annotated]
loom/runtime/heartbeat.py:100: error: Need type annotation for "_mf_monitors" (hint: "_mf_monitors: dict[<type>, <type>] = ...")  [var-annotated]
loom/orchestration/events.py:40: error: Name "publish" already defined on line 21  [no-redef]
loom/orchestration/events.py:50: error: Name "subscribe" already defined on line 29  [no-redef]
loom/orchestration/events.py:56: error: Name "unsubscribe" already defined on line 35  [no-redef]
loom/providers/gemini.py:63: error: Return type "AsyncIterator[str]" of "stream" incompatible with return type "Coroutine[Any, Any, AsyncIterator[str]]" in supertype "loom.providers.base.LLMProvider"  [override]
loom/providers/gemini.py:63: note: Consider declaring "stream" in supertype "loom.providers.base.LLMProvider" without "async"
loom/providers/gemini.py:63: note: See https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
loom/providers/gemini.py:143: error: Returning Any from function declared to return "str"  [no-any-return]
loom/providers/anthropic.py:51: error: Return type "AsyncIterator[str]" of "stream" incompatible with return type "Coroutine[Any, Any, AsyncIterator[str]]" in supertype "loom.providers.base.LLMProvider"  [override]
loom/providers/anthropic.py:51: note: Consider declaring "stream" in supertype "loom.providers.base.LLMProvider" without "async"
loom/providers/anthropic.py:51: note: See https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
loom/api/handles.py:25: error: Name "AgentRuntime" is not defined  [name-defined]
loom/providers/openai.py:61: error: Return type "AsyncIterator[str]" of "stream" incompatible with return type "Coroutine[Any, Any, AsyncIterator[str]]" in supertype "loom.providers.base.LLMProvider"  [override]
loom/providers/openai.py:61: note: Consider declaring "stream" in supertype "loom.providers.base.LLMProvider" without "async"
loom/providers/openai.py:61: note: See https://mypy.readthedocs.io/en/stable/more_types.html#asynchronous-iterators
Found 63 errors in 13 files (checked 114 source files)
Error: Process completed with exit code 1.



Run poetry run pytest \
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.4.2, pluggy-1.6.0 -- /home/runner/work/loom-agent/loom-agent/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/runner/work/loom-agent/loom-agent
configfile: pytest.ini
testpaths: tests
plugins: asyncio-0.23.8, cov-7.1.0, mock-3.15.1, anyio-4.13.0
asyncio: mode=Mode.STRICT
collecting ... collected 308 items / 1 error

==================================== ERRORS ====================================
_______________ ERROR collecting tests/core/test_runtime_loop.py _______________
ImportError while importing test module '/home/runner/work/loom-agent/loom-agent/tests/core/test_runtime_loop.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
.venv/lib/python3.11/site-packages/_pytest/python.py:498: in importtestmodule
    mod = import_path(
.venv/lib/python3.11/site-packages/_pytest/pathlib.py:587: in import_path
    importlib.import_module(module_name)
/opt/hostedtoolcache/Python/3.11.15/x64/lib/python3.11/importlib/__init__.py:126: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1204: in _gcd_import
    ???
<frozen importlib._bootstrap>:1176: in _find_and_load
    ???
<frozen importlib._bootstrap>:1147: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:690: in _load_unlocked
    ???
.venv/lib/python3.11/site-packages/_pytest/assertion/rewrite.py:186: in exec_module
    exec(co, module.__dict__)
tests/core/test_runtime_loop.py:14: in <module>
    from loom.runtime.monitors import FilesystemMonitor, ProcessMonitor, ResourceMonitor, MFEventsMonitor
loom/runtime/monitors.py:5: in <module>
    import psutil
E   ModuleNotFoundError: No module named 'psutil'
=========================== short test summary info ============================
ERROR tests/core/test_runtime_loop.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
=============================== 1 error in 1.63s ===============================
Error: Process completed with exit code 2.