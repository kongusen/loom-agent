# Loom Agent Framework - 开发实现与统一设计指南 (v2.0)

> 面向工程实现的统一文档，融合 Loom v1.2/v2.0 设计、MCP 集成方案与 Claude Code Agent 技术实践，指导快速搭建对标 LangChain 且具备 Claude Code 级工程能力的 Agent 框架。

---

## 1. 文档目的与范围

- 明确框架定位、原则与架构分层，统一概念与接口。
- 固化 Agent 主循环、工具流水线、并发调度、上下文压缩的标准实现。
- 给出插件/MCP 集成、安全权限、可观测性、测试与部署的工程规范。
- 输出实施路线图与 DoD，确保可交付、可演进、可维护。

## 2. 设计目标与原则

- 组合优先：提供可拼装的构建块（LLM/Tool/Memory/Compressor/Agent/Chain/Router/Workflow）。
- 最小假设：不绑定具体应用，抽象清晰、依赖稳定、低耦合。
- 异步与流式：全链路 `asyncio`，文本/事件流式返回，提升交互体验与可插拔性。
- 插件优先：通过注册中心扩展生态，避免修改核心。
- 安全可控：权限网关、命名空间隔离、默认最小权限。
- 工程可用：强类型（Pydantic）、可测试、可观测、可部署、可降级。

## 3. 架构总览与分层

```
Developer Apps (ChatBot/CodeGen/RAG/Multi-Agent)
           │
  High-Level: Agent · Chain · Router · Workflow
           │
  Core: AgentExecutor · ToolPipeline · Scheduler · MemoryManager · EventBus
           │
  Interfaces: BaseLLM · BaseTool · BaseMemory · BaseCompressor
           │
  Ecosystem: PluginRegistry · MCP Adapter (Client/Tool/Registry)
```

## 4. 核心抽象与接口

- `BaseLLM`
  - `generate(messages) -> str`
  - `stream(messages) -> AsyncGenerator[str]`
  - `generate_with_tools(messages, tools) -> dict`（工具选择/调用）
  - `model_name: str`，`supports_tools: bool`

- `BaseTool`
  - `name: str`，`description: str`，`args_schema: BaseModel`
  - `run(**kwargs) -> Any`（异步）
  - `is_concurrency_safe: bool`

- `BaseMemory`
  - `add_message(message)`，`get_messages(limit=None) -> List[Message]`，`clear()`
  - 可选 `save(path)` / `load(path)`

- `BaseCompressor`
  - `compress(messages) -> List[Message]`
  - `should_compress(token_count, max_tokens) -> bool`

- `BaseRetriever`（RAG 支持）
  - `retrieve(query, top_k, filters) -> List[Document]`
  - `add_documents(documents) -> None`

## 4.5 RAG 能力（检索增强生成）

Loom 提供 **三层 RAG 架构**，实现 Context Engineering：

- **Layer 1: 核心组件 - ContextRetriever**
  - 自动检索（每次查询前）
  - 零侵入集成到 AgentExecutor
  - 适用场景：知识库问答、文档搜索

- **Layer 2: 工具版本 - DocumentSearchTool**
  - LLM 决定何时检索
  - 可与其他工具组合
  - 适用场景：复杂任务、多工具协作

- **Layer 3: 高级模式 - RAGPattern**
  - 完整控制 RAG 流程（检索 → 重排序 → 生成）
  - MultiQueryRAG（多查询变体）
  - HierarchicalRAG（文档 → 段落两级检索）
  - 适用场景：需要 Re-ranking、复杂检索策略

示例：
```python
from loom import Agent
from loom.builtin.retriever.in_memory import InMemoryRetriever
from loom.core.context_retriever import ContextRetriever

# 核心组件：自动检索
retriever = InMemoryRetriever()
context_retriever = ContextRetriever(retriever=retriever, top_k=3)
agent = Agent(llm=llm, context_retriever=context_retriever)

# 工具版本：LLM 控制
from loom.builtin.tools.document_search import DocumentSearchTool
doc_tool = DocumentSearchTool(retriever)
agent = Agent(llm=llm, tools=[doc_tool, other_tools])

# 高级模式：完整 RAG 流程
from loom.patterns.rag import RAGPattern, MultiQueryRAG
rag = RAGPattern(agent, retriever, reranker=my_reranker, top_k=10)
response = await rag.run("query")
```

详细文档：`LOOM_RAG_GUIDE.md`

## 5. Agent 主循环（对齐 Claude Code nO）

- 关键点
  - 统一系统提示动态生成（含工具目录、风格与边界提醒）。
  - 进入循环前执行上下文压缩检查；触发阈值默认 `0.92`。
  - 全程事件流：`text_delta`、`tool_calls_start`、`tool_result`、`agent_finish`、`error`。
  - 支持中断/暂停：`EventBus.abort/pause/resume/is_aborted`。

- 伪代码

```
async def execute(user_input: str, max_iterations: int = 50):
  yield {"type": "request_start"}

  messages = await memory.get_messages()
  if token_usage(messages) > 0.92:
    messages = await compressor.compress(messages)
    yield {"type": "compression_applied"}

  messages += [Message(role="user", content=user_input)]
  system_prompt = build_system_prompt(tools, context)

  for i in range(max_iterations):
    async for delta in llm.stream(messages_with(system_prompt)):
      if delta.text:
        yield {"type": "text_delta", "content": delta.text}
      if delta.tool_calls:
        yield {"type": "tool_calls_start", "tool_calls": delta.tool_calls}
        async for tr in tool_pipeline.execute_calls(delta.tool_calls):
          yield {"type": "tool_result", "result": tr}
          await memory.add_message(Message(role="tool", content=tr.content, tool_call_id=tr.tool_call_id))

    if event_bus.is_aborted():
      raise ExecutionAbortedError()

    if finished(messages):
      yield {"type": "agent_finish"}
      break
```

## 6. 工具执行流水线（MH1 · 六阶段）

- 阶段定义
  - Discover：注册表查找、可用性检查、错误 `ToolNotFound/Unavailable`。
  - Validate：Pydantic `args_schema` 校验，清晰错误路径与提示。
  - Authorize：权限网关 `allow/deny/ask`；ask 触发交互确认回调。
  - CheckCancel：尊重中断/超时信号。
  - Execute：调度器执行（并发/超时/优先级）。
  - Format：统一结果结构、阶段耗时指标、清理上下文。

- 错误自愈与降级
  - 参数错误 → 结构化提示如何修正。
  - 超时 → 建议分解任务/延长超时；可自动重试 N 次（指数退避）。
  - 权限拒绝 → 明确告知授权方式；可切换只读替代工具。
  - 未知错误 → 语义化转 `ToolResult(status=error)`，不中断主循环。

## 7. 并发调度器（UH1）

- 配置
  - `max_concurrency: int = 10`（默认，源自 Claude Code gW5）
  - `timeout_seconds: int = 120`
  - `enable_priority: bool = True`

- 策略
  - 并发安全工具批量并行；非并发安全工具串行执行。
  - `asyncio.Semaphore` 控并发；`asyncio.wait_for` 控超时；`as_completed` 提升吞吐。
  - 指标：并发数峰值、工具耗时分布、超时率。

## 8. 上下文管理与压缩（wU2/AU2）

- 触发阈值
  - 使用率 > `0.92` 自动压缩；> `0.80` 发出容量警告（可选）。

- 8 段式结构化摘要（AU2）
  1) 背景上下文  2) 关键决策  3) 工具使用记录  4) 用户意图演进
  5) 执行结果  6) 错误与解决  7) 未解决问题  8) 后续计划

- 压缩产物
  - 生成单条 `system` 摘要消息（含时间戳、比例、版本）。
  - 保留最近关键消息窗口，确保连续性与可追溯性。

## 9. 插件系统与生态

- 注册中心 `PluginRegistry`
  - `register_llm/register_tool/register_memory` 装饰器；`get_*` 实例化接口。
  - 官方包命名：`loom-llm-*`、`loom-tools-*`、`loom-memory-*`、`loom-mcp`。

- 包结构建议
```
loom/
  core/  interfaces/  components/  patterns/  plugins/  callbacks/  utils/  builtin/
```

## 10. MCP 集成（Adapter 层）

- 组件
  - `MCPClient`：JSON-RPC over stdio，`connect/list_tools/call_tool/close`。
  - `MCPTool`：将 MCP 工具规范（JSON Schema）适配为 `BaseTool`。
  - `MCPToolRegistry`：`discover_local_servers()` 读取 `~/.loom/mcp.json`，按 `server:tool` 命名加载。

- 类型安全
  - 自动将 JSON Schema 转换为 Pydantic 模型（必填/默认/描述）。

- 安全命名空间
  - 工具标识 `server:tool`，避免冲突；与权限系统统一管控。

- 最小示例
```
from loom import Agent
from loom.llms import OpenAI
from loom.mcp import MCPToolRegistry

registry = MCPToolRegistry()
await registry.discover_local_servers()
tools = await registry.load_servers(["filesystem", "github"])  # 命名: filesystem:list, github:create_issue

agent = Agent(llm=OpenAI(api_key="..."), tools=tools)
print(await agent.run("Read config.json and create a GitHub issue"))
await registry.close()
```

## 11. 数据模型（建议）

- `Message`
  - `role: user|assistant|system|tool`，`content: str`，`metadata: dict`
- `ToolCall`
  - `id: str`，`name: str`，`arguments: dict`
- `ToolResult`
  - `tool_call_id: str`，`status: success|error|warning`，`content: str`，`metadata: dict`
- `StreamEvent`
  - `type: text_delta|tool_calls_start|tool_result|agent_finish|error|aborted`，`payload`

## 12. 开发者 API 速览

- 核心导出
  - `from loom import Agent, Chain, Router, Workflow`
  - `from loom.patterns import MultiAgentSystem`
  - `from loom.callbacks import LoggingCallback, MetricsCallback`

- 配置
  - `config.set_default_llm(...)`
  - `config.set_default_memory(...)`
  - `config.set_max_iterations(50)`
  - `config.enable_metrics(True)`

## 13. 目录与文件布局（参考）

```
loom/
├── core/                # AgentExecutor · ToolPipeline · Scheduler · Memory · EventBus
├── interfaces/          # BaseLLM · BaseTool · BaseMemory · BaseCompressor
├── components/          # Agent · Chain · Router · Workflow
├── patterns/            # MultiAgent · RAG · ReAct
├── plugins/             # registry · loader
├── mcp/                 # client · tool_adapter · registry · permissions · cache
├── callbacks/           # logging · metrics
├── builtin/             # llms/tools/memory 的参考实现
└── examples/            # quickstart · rag · multi_agent · mcp
```

## 14. 安全与权限

- 策略：`allow | deny | ask`，可按工具名/参数/调用来源匹配。
- 默认最小权限：写文件/执行 Bash/网络请求 → `ask/deny`。
- 审计：记录敏感调用（人审/追踪）。

## 15. 可观测性与稳定性

- Metrics（核心 KPIs）
  - 迭代：总时长/均值；LLM：调用数、token、平均响应时长。
  - 工具：调用数、成功率、平均耗时、按工具分布。
  - 压缩：次数、平均压缩率；并发：峰值；错误：总量/类型/错误率。

- Prometheus 导出（建议指标准名）
  - `loom_iterations_total`，`loom_tool_calls_total{tool_name,status}`
  - `loom_llm_calls_total`，`loom_iteration_duration_seconds`
  - `loom_tool_execution_duration_seconds{tool_name}`，`loom_active_agents`

- 稳定性
  - 指数退避重试、熔断（错误率阈值/冷却时间）、主备降级。

## 16. 测试策略

- 金字塔
  - 单元（60%）· 组件集成（30%）· E2E（10%）。

- 覆盖重点
  - Pipeline 各阶段成功/失败路径；Scheduler 并发/超时；Compressor 触发与比例。
  - EventBus 中断/恢复；MCP 最小路径：工具列表/一次调用。
  - MockLLM/AgentTester：断言工具调用与最终回答。

## 17. 部署与配置

- 生产参数（建议默认）
  - `max_iterations=50`，`context_window≈200k`，`compression_threshold=0.92`
  - `max_concurrency=10`，`tool_timeout_seconds=120`，`enable_metrics=True`
  - LLM 限流/重试：`rpm`、最大重试次数、指数基数

- 容器化
  - 提供 `Dockerfile` 与 `docker-compose.yml`（含 Redis/Prometheus 可选）。

## 18. 实施路线图（DoD）

- Phase 1：核心最小可用
  - 定义 `interfaces`；实现 `AgentExecutor/ToolPipeline/Scheduler/InMemoryMemory/EventBus`。
  - 完成 quickstart 示例与基础单元测试（接口与主流程）。

- Phase 2：上下文与稳定性
  - StructuredCompressor(AU2) + 阈值策略；错误体系（分类/自愈/重试）；Metrics + LoggingCallback。

- Phase 3：生态与编排
  - PluginRegistry；Chain/Router/Workflow；内置工具集；MockLLM/AgentTester；RAG/Multi-Agent 示例。

- Phase 4：MCP 与安全
  - MCPClient/Tool/Registry；权限系统融合；缓存；命名空间；MCP examples。

- Phase 5：生产化
  - Prometheus 导出；熔断与降级；CI 集成与覆盖率阈值；部署清单与运维手册。

## 19. 与 LangChain 的差异化定位

- 抽象层次更清晰（Agent/Chain/Router/Workflow 分层）与强类型安全。
- 工具执行采用流水线模式（阶段化指标/权限/并发），内置调度与观察能力。
- 原生支持 MCP 生态，零改造接入社区工具。

## 20. 常见问题与建议

- 上下文长度溢出
  - 降低压缩阈值（如 `0.80`），提高目标压缩比（如 `0.5`），优先保留决策与近期消息。

- 工具执行超时
  - 增加超时（如 `300s`），降低并发（如 `5`），或拆分任务。

- 工具循环调用
  - 检测近窗重复调用模式，触发 system-reminder 或硬性中断并提示。

---

参考文档：
- `Loom Agent Framework - 详细设计文档 (v1.2).md`
- `LOOM_FRAMEWORK_DESIGN_V2.md`
- `LOOM_MCP_INTEGRATION.md`
- `LOOM_RAG_GUIDE.md` - RAG 完整指南（三层架构、检索器实现、高级模式）
- `Claude_Code_Agent系统完整技术解析.md`

