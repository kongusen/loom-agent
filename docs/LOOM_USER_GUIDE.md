Loom Agent 框架使用指南（用户向）

概述
- Loom 是一个面向开发者的 Agent 框架，强调“框架优先、组合式扩展、最小侵入”。
- 目标：让你在几行代码内创建可控、可扩展、可观测的多工具智能体；并按需引入子 Agent、权限、安全模式、流式回调、RAG/MCP 等高级能力。

安装
- 开发本仓库：
  - 使用 Poetry：在仓库根目录运行 `poetry install`；或使用 `pip install -e .`（如需 OpenAI 支持，安装 extras：`pip install -e .[openai]`）。
- 生产使用（发布后）：`pip install loom-agent[openai]`（不同 provider 可安装对应 extras）。

快速开始（Hello, Agent）
```python
import asyncio
from loom import agent

async def main():
    bot = agent(
        provider="openai",               # 也支持 anthropic/cohere/azure_openai/ollama/custom
        model="gpt-4o",                  # 模型名称
    )
    print(await bot.run("Say hi in one sentence"))

asyncio.run(main())
```

环境变量与配置
- 最简方式：`agent_from_env(provider=None, model=None)` 会读取环境变量：
  - `LOOM_PROVIDER` / `LOOM_MODEL`
  - Provider 相关：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`ANTHROPIC_API_KEY`、`COHERE_API_KEY`、`AZURE_OPENAI_API_KEY`、`AZURE_OPENAI_ENDPOINT`
- 示例：
```bash
export OPENAI_API_KEY=sk-...
export LOOM_PROVIDER=openai
export LOOM_MODEL=gpt-4o
```

内置工具与自定义工具
- 内置工具（示例）：
  - `ReadFileTool`, `WriteFileTool`, `GlobTool`, `GrepTool`, `Calculator`, `HTTPRequestTool`, `PythonREPLTool` 等
- 挂载工具：
```python
from loom import agent
from loom.builtin.tools import ReadFileTool, WriteFileTool, GlobTool, GrepTool

bot = agent(provider="openai", model="gpt-4o", tools=[
    ReadFileTool(), WriteFileTool(), GlobTool(), GrepTool()
])
```
- 自定义工具（@tool 装饰器）：
```python
from loom import tool

@tool(name="add", description="Add two integers")
def add(a: int, b: int) -> int:
    return a + b

bot = agent(provider="openai", model="gpt-4o", tools=[add()])
```

任务与子 Agent（Task 工具）
- 程序化定义 Agent（推荐）：
```python
from loom import AgentSpec, register_agent

register_agent(AgentSpec(
    agent_type="code-explorer",
    description="Broad code search and structure understanding",
    tools=["glob", "grep", "read_file"],
    model_name="gpt-4o",
    system_instructions=(
        "You are a code exploration agent. Start broad then narrow. "
        "Use glob/grep first, then read_file for details."
    ),
))
```
- 使用 Task 工具调用子 Agent：
```python
from loom.builtin.tools.task import TaskTool
from loom import agent, agent_ref, model_ref

def make_subagent(max_iterations: int = 20, **kwargs):
    # kwargs 可能包含 system_instructions / permission_policy / model_name
    # 你可以在此决定如何与 LLM 工厂整合
    return agent(
        provider="openai",
        model=kwargs.get("model_name", "gpt-4o"),
        tools=[...],
        max_iterations=max_iterations,
        system_instructions=kwargs.get("system_instructions"),
        permission_policy=kwargs.get("permission_policy"),
    )

task = TaskTool(agent_factory=make_subagent)
main = agent(provider="openai", model="gpt-4o", tools=[task])

# 引用式调用（框架化）
out = await task.run_ref(
    description="Explore repo",
    prompt="List Python files",
    agent=agent_ref("code-explorer"),
    model=model_ref("gpt-4o"),
)
```
- 说明：
  - Task 会根据注册的 AgentSpec 自动注入系统提示、应用工具白名单（默认 deny，白名单 allow），并可选择性覆盖模型。
  - 若未注册也可回退到文件式定义（可选，兼容 `.loom/agents/*.md` / `.claude/agents/*.md`）。

权限与安全模式
- 默认行为：不启用安全模式时，遵循 `permission_policy` 的简单 allow/deny/ask。
- 安全模式（框架能力）：
```python
from loom import agent

def ask(tool_name: str, args: dict) -> bool:
    print(f"[ask] {tool_name}({args}) ? [y/N]")
    return input().strip().lower().startswith("y")

bot = agent(
    provider="openai", model="gpt-4o",
    tools=[...],
    safe_mode=True,
    ask_handler=ask,
)
```
- 开启后：
  - 策略优先：`permission_policy` 的 allow/deny/ask 优先于安全模式。
  - 其余情况：从 `~/.loom/config.json` 的 `allowed_tools` 判断。未允许则询问，并可持久化批准（自动写入 allowed_tools，下次自动放行）。
- 参考实现：`loom/core/permissions.py:1`，`loom/core/permission_store.py:1`。

流式与回调
- 流式结果：
```python
async for ev in bot.stream("Tell me a joke"):
    if ev.type == "text_delta":
        print(ev.content, end="")
```
- 回调（可观测）：实现 `BaseCallback.on_event(type, payload)`，订阅 `request_start/tool_calls_start/tool_result/agent_finish/error` 等事件。规范：`docs/CALLBACKS_SPEC.md:3`。

指标（Metrics）
- `agent.get_metrics()` 返回本次执行中的迭代数、工具调用、错误计数等摘要。
  - 参考：`loom/components/agent.py:67`。

RAG 与上下文压缩（可选）
- 通过 `context_retriever` 将检索到的文档注入到系统提示或用户消息之前；并按需进行上下文压缩。
- 参见：`loom/core/agent_executor.py:25`（检索注入与压缩策略钩子），以及 `docs/LOOM_RAG_GUIDE.md`。

MCP（可选）
- Loom 提供最小 MCP 客户端与工具适配器，可从本地 MCP 服务加载工具并挂载为 Loom 工具。
- 参见：`loom/mcp/registry.py:11`、`loom/mcp/tool_adapter.py:11`。

常见问题（FAQ）
- ImportError: No module named 'loom'
  - 解决：在仓库根目录 `pip install -e .` 或 `poetry install` 后再运行。
- 提示缺少 API Key
  - 解决：按 provider 设置环境变量，如 `OPENAI_API_KEY`。
- 工具未放行
  - 解决：检查是否启用了 `safe_mode`；或在 `~/.loom/config.json` 中添加 `allowed_tools`，或为该工具配置 `permission_policy` 为 `allow`。

进阶建议
- 在团队/生产环境中推荐：
  - 通过 AgentSpec 程序化注册组织内标准子 Agent，版本化管理，并配合 `TaskTool.run_ref()` 使用引用。
  - 使用回调记录关键阶段 + 结合日志/指标汇总，便于调试与审计。
  - 在 CI 中使用安全模式白名单，避免危险工具误用。

