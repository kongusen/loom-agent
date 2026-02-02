# loom/protocol、loom/events、loom/runtime 研究总结

基于对三个模块的代码阅读与调用关系梳理的总结。

---

## 一、loom/protocol（A1 统一接口）

### 1.1 定位与公理

- **公理 A1**：∀x ∈ System: x implements NodeProtocol  
- 所有节点统一接口，符合 **Google A2A 协议**（能力声明、任务通信、JSON-RPC 2.0）。

### 1.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **node.py** | `NodeProtocol` | 协议：`node_id`, `source_uri`, `agent_card`, `execute_task(task) -> Task`, `get_capabilities() -> AgentCard` |
| **task.py** | `Task`, `TaskStatus` | A2A 任务模型：task_id, source/target_agent, action, parameters, status, result, error, metadata, parent_task_id, session_id；状态：pending/running/completed/failed/cancelled |
| **agent_card.py** | `AgentCard`, `AgentCapability` | A2A 能力声明：agent_id, name, description, version, capabilities（REFLECTION/TOOL_USE/PLANNING/MULTI_AGENT） |
| **memory_ops.py** | `MemoryOperation`, `MemoryRequest`, `MemoryResponse` | 记忆操作协议：store/retrieve/update/delete/search/compress；Pydantic 请求/响应 |
| **mcp.py** | MCP 数据模型与接口 | `MCPToolDefinition`（name, description, inputSchema）, `MCPResource`, `MCPPrompt`, `MCPToolCall`, `MCPToolResult`；`MCPServer` / `MCPClient` 抽象 |
| **streaming.py** | `StreamingProtocol`, `StreamingMixin` | 流式规范：stream_output(task_id)；Mixin 提供 _stream_text / _stream_tool_call_* / _stream_error / _stream_done，与 event_bus 联动 |

### 1.3 依赖关系

- **protocol** 不依赖 events 或 runtime，只依赖 `loom.providers.llm.interface.StreamChunk`（streaming）。
- 被 **events**（Task）、**runtime**（Task, NodeProtocol）、**agent**、**tools** 等广泛引用。

### 1.4 小结

- 协议层纯净：只定义「任务长什么样、节点要提供什么、能力如何声明、MCP/记忆/流式规范」。
- Task 同时承载「路由键」：EventBus 按 **action** 路由，Dispatcher 按 **target_agent** 找节点。

---

## 二、loom/events（A2 事件主权）

### 2.1 定位与公理

- **公理 A2**：∀communication ∈ System: communication = Task  
- 所有通信都以 Task 为载体的任务事件。

### 2.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **event_bus.py** | `EventBus` | 注册 handler(action)、publish(task, wait_result)；有 transport 时发到 `task.{task.action}`，无 transport 时本地按 action 调 handler；支持 `"*"` 通配符订阅 |
| **actions.py** | `TaskAction`, `MemoryAction`, `AgentAction` | 类型安全动作枚举：execute/cancel/query/stream；read/write/search/sync；start/stop/status/heartbeat |
| **handlers.py** | `TaskHandler`, `MemoryHandler`, `AgentHandler` | Protocol：Task→Task；dict→dict；(agent_id, dict)→dict |
| **transport.py** | `Transport` | 抽象：connect/disconnect, publish(topic, message), subscribe/unsubscribe, is_connected |
| **memory_transport.py** | `MemoryTransport` | 内存实现：defaultdict 存订阅者，publish 时 asyncio.gather 调 handler |
| **sse_formatter.py** | `SSEFormatter` | 静态方法 format_sse_message(event_type, data, event_id)，生成 SSE 文本 |
| **nats_transport.py** | `NATSTransport` | 可选，依赖 nats-py，分布式发布订阅 |
| **stream_converter.py** | - | 将 EventBus 的 Task 与外部流式/SSE 等格式转换，并 register_handler 到 event_bus |

### 2.3 路由语义

- **EventBus**：按 `task.action` 路由（字符串或枚举值）；同一 action 多个 handler 时只调第一个（单 handler 设计）。
- **Transport**：topic 为 `task.{task.action}`，即按 action 分发到不同主题。

### 2.4 使用方

- **agent/core**：`event_bus.publish(delegation_task)` 委派任务。
- **agent/base**：`event_bus.publish(event_task)` 发观测事件；BaseNode 持有 event_bus。
- **tools/sandbox_manager**：发布 tool.registered / tool.executing / tool.completed。
- **memory/core**：`register_handler("*", self._on_task)` 通配订阅所有任务。
- **api/app**：创建 EventBus，传给 Dispatcher 和 Agent。

### 2.5 小结

- 事件层 = Task 的发布/订阅 + 可选传输层；本地用 handler 字典，分布式用 Transport。
- 与 protocol 的衔接：只认 `Task`，不关心具体业务，符合 A2「通信即 Task」。

---

## 三、loom/runtime（运行时基础设施）

### 3.1 定位

- 在 protocol + events 之上，提供「调度、拦截、状态」等运行时能力。

### 3.2 核心组件

| 文件 | 内容 | 说明 |
|------|------|------|
| **dispatcher.py** | `Dispatcher` | 持有一个 EventBus 和 nodes: dict[node_id, NodeProtocol]；dispatch(task) 时若存在 task.target_agent 对应节点则直接 execute_task，否则 fallback 到 event_bus.publish(task) |
| **interceptor.py** | `Interceptor`, `InterceptorChain` | Interceptor：before(task)/after(task) 默认透传；Chain：按序 before → executor(task) → 逆序 after |
| **example_interceptors.py** | `LoggingInterceptor`, `TimingInterceptor`, `MetricsInterceptor` | 日志、耗时写入 task.metadata、指标计数 |
| **state.py** | `AgentStatus`, `AgentState` | 状态枚举：idle/busy/error/offline；AgentState：agent_id, status, current_task, metadata, updated_at |
| **state_store.py** | `StateStore`, `MemoryStateStore` | 抽象：save/get/delete/list_keys(prefix)/clear；内存实现用 dict |
| **state_manager.py** | `StateManager` | 封装 StateStore；key 约定 agent:{id} / task:{id}；提供 save/get/delete/list 与 clear_all，Task 序列化/反序列化用 task.to_dict() 与手动重建 |

### 3.3 调用关系

- **Dispatcher** 依赖 **EventBus** 和 **NodeProtocol**；调度路径：按 target_agent 找节点 → 有则节点执行，无则交给 EventBus 按 action 路由。
- **InterceptorChain** 只依赖 **Task**；不依赖 EventBus，需由调用方把 chain 与 executor 组合（如 agent/base 的 interceptor_chain）。
- **StateManager** 依赖 **Task**（protocol）、**AgentState**（state）、**StateStore**；不依赖 EventBus。

### 3.4 使用方

- **api/app**：`Dispatcher(event_bus)`，创建 Agent 时未直接传 dispatcher 给 Agent，dispatcher 主要用来 register_node。
- **agent/base**：每个 BaseNode 创建 `InterceptorChain()`，可在子类中挂拦截器。
- **runtime/__init__**：统一导出 Dispatcher、Interceptor、InterceptorChain、示例拦截器、State*。

### 3.5 小结

- **Dispatcher**：桥接「target_agent → 节点」与「无节点时 → EventBus」，实现「先本地节点，再总线」的调度策略。
- **InterceptorChain**：与 EventBus 解耦，适合在 Agent 执行前后做日志、计时、指标。
- **StateManager**：独立的 Agent/Task 状态存储，便于观测与恢复，未在 agent 核心执行路径中强制使用。

---

## 四、三者关系图（概念）

```
                    +------------------+
                    | loom.protocol    |
                    | Task, NodeProtocol,
                    | AgentCard, MCP,
                    | MemoryOps, Streaming
                    +--------+---------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
+----------------+  +----------------+  +----------------+
| loom.events    |  | loom.runtime   |  | agent/tools/   |
| EventBus       |  | Dispatcher     |  | memory/...     |
| Transport      |  | InterceptorChain|  | 使用 Task +    |
| 按 action 路由 |  | StateManager   |  | NodeProtocol   |
+--------+-------+  +-------+--------+  +----------------+
         |                  |
         |    Dispatcher 持 EventBus，dispatch(task) 时：
         |    - 有 target_agent 对应节点 → node.execute_task(task)
         |    - 无则 event_bus.publish(task) → 按 action 调 handler
         +------------------+
```

---

## 五、可优化点（简要）

1. **EventBus 多 handler**：同一 action 当前只调第一个 handler；若需多订阅者，需明确语义（全调 vs 选一）及返回值约定。
2. **Dispatcher 与 EventBus 的职责**：Dispatcher 按 target_agent 解析，EventBus 按 action 解析；文档中可明确「先 Dispatcher 再 EventBus」的推荐用法及适用场景。
3. **StateManager 与 Agent 的集成**：若要做「任务/Agent 状态持久化与恢复」，可在 Agent 执行前后挂 StateManager 的 save/get（或通过 Interceptor 接入）。
4. **protocol.streaming 与 events**：StreamingMixin 通过 hasattr 检查 event_bus 与 publish_*，与事件层是松耦合；若统一观测协议，可考虑在 events 层定义标准 action（如 node.stream_error, node.token_usage）并在 README 中说明。
5. **Task 字段命名**：to_dict() 使用 camelCase（taskId, sourceAgent 等）以对齐 A2A；Python 侧用 snake_case，两套命名在文档中注明可减少混淆。

---

*文档版本：基于当前代码库梳理，适用于 feature/agent-skill-refactor 及后续分支。*
