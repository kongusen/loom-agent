# API总览

这一页只列出当前最值得关注的公共入口，而不是穷举所有内部类。重点是 `loom/api`。

## `loom/api` 包出口

`loom/api/__init__.py` 当前导出了以下几组对象：

| 类别 | 示例 |
|---|---|
| Models | `Session`、`Task`、`Run`、`Event`、`Approval`、`Artifact`、`RunResult` |
| Config | `AgentConfig`、`LLMConfig`、`ToolConfig`、`PolicyConfig` |
| Runtime | `AgentRuntime`、`SessionHandle`、`TaskHandle`、`RunHandle` |
| Observability | `EventBus`、`EventStream`、`ArtifactStore` |
| Profile / Policy | `AgentProfile`、`PolicySet` |
| Knowledge | `KnowledgeRegistry`、`KnowledgeSource` |

## 最常用入口

### 面向运行时接入

- `loom.api.runtime.AgentRuntime`
- `loom.api.profile.AgentProfile`
- `loom.api.handles.*`
- `loom.api.models.*`

### 面向扩展开发

- `loom.providers.base.LLMProvider`
- `loom.tools.registry.ToolRegistry`
- `loom.ecosystem.skill.SkillRegistry`
- `loom.ecosystem.plugin.PluginLoader`
- `loom.ecosystem.mcp.MCPBridge`

### 面向内核开发

- `loom.agent.core.Agent`
- `loom.agent.runtime.Runtime`
- `loom.context.manager.ContextManager`
- `loom.execution.loop.Loop`
- `loom.orchestration.subagent.SubAgentManager`
- `loom.safety.permissions.PermissionManager`

## 关键对象速查

| 对象 | 作用 |
|---|---|
| `AgentRuntime` | 运行时根入口 |
| `SessionHandle` | 会话操作入口 |
| `TaskHandle` | 任务操作入口 |
| `RunHandle` | 运行生命周期入口 |
| `EventBus` | 事件分发 |
| `ArtifactStore` | 产物存储 |
| `AgentProfile` | Agent 画像与预设配置 |
| `KnowledgeRegistry` | 知识源注册 |

## 说明

当前 API 面已经比较丰富，但仍处于持续演化中。

因此建议：

- 对外接入时优先使用 `loom/api`。
- 需要修改执行逻辑时再深入 `loom/agent`、`loom/context`、`loom/execution`。
