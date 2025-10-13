# Loom Agent Framework

> 一个强大、灵活、可扩展的 AI Agent 开发框架，对标 LangChain，具备 Claude Code 级工程能力

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 核心特性

### 架构优势
- **组合优先**: 提供可拼装的构建块,而非完整应用
- **分层清晰**: Interface → Core → Components → Patterns 四层架构
- **强类型**: 基于 Pydantic 的强类型系统,减少运行时错误
- **异步优先**: 全链路 async/await,原生支持流式输出

### Claude Code 级工程实践
- **6 阶段工具流水线**: Discover → Validate → Authorize → CheckCancel → Execute → Format
- **智能上下文压缩**: 92% 阈值触发,8 段式结构化压缩算法
- **并发调度器**: 最大 10 并发,智能区分并发安全/非安全工具
- **动态系统提示**: 自动生成工具目录、风格指引与边界提醒
- **Multi-Agent 支持**: SubAgent 隔离执行,支持任务分解与结果汇总

### 生态集成
- **MCP 协议支持**: 原生接入 Model Context Protocol 工具生态
- **插件化扩展**: 通过注册中心扩展 LLM/Tool/Memory,无需修改核心
- **多 LLM 支持**: OpenAI, Anthropic, 本地模型等

## 🚀 快速开始

### 安装

```bash
# 基础安装
pip install -e .

# 可选依赖
pip install openai          # OpenAI LLM
pip install anthropic       # Anthropic Claude
pip install httpx           # HTTP 请求工具
pip install duckduckgo-search  # Web 搜索工具
```

### 最简单的示例（推荐，一行构建）

```python
import asyncio
import loom
from loom.builtin.llms import MockLLM

# 使用便捷构建函数，一行创建 Agent
agent = loom.agent(llm=MockLLM(responses=["The answer is 42"]))
print(asyncio.run(agent.ainvoke("What is the meaning of life?")))
```

### 带工具的 Agent

```python
import asyncio, os, loom
from loom.builtin.tools import Calculator, ReadFileTool, WriteFileTool

async def main():
    # 建议从环境变量读取 OPENAI_API_KEY
    agent = loom.agent(
        provider="openai", model="gpt-4o",
        tools=[Calculator(), ReadFileTool(), WriteFileTool()],
        max_iterations=10
    )

    result = await agent.ainvoke(
        "Calculate 123 * 456, write the result to result.txt, then read it back"
    )
    print(result)

asyncio.run(main())
```

### 自定义工具（@loom.tool 装饰器）

```python
import loom
from typing import List

@loom.tool(description="Sum a list of numbers")
def sum_list(nums: List[float]) -> float:
    return sum(nums)

SumTool = sum_list
agent = loom.agent(provider="openai", model="gpt-4o", tools=[SumTool()])
```

### Multi-Agent 系统

```python
from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.patterns import MultiAgentSystem

# 定义专业 Agent
researcher = Agent(llm=OpenAILLM(api_key="...", model="gpt-4"), tools=[...])
analyst = Agent(llm=OpenAILLM(api_key="...", model="gpt-4"), tools=[...])
writer = Agent(llm=OpenAILLM(api_key="...", model="gpt-4"), tools=[...])

# 创建协作系统
system = MultiAgentSystem(
    agents={"researcher": researcher, "analyst": analyst, "writer": writer},
    coordinator=OpenAILLM(api_key="...", model="gpt-4")
)

result = await system.run("Research Python trends, analyze data, write report")
```

## 📚 核心概念

### 1. 分层架构

```
Developer Apps (ChatBot, CodeGen, RAG, Multi-Agent)
           │
  High-Level: Agent · Chain · Router · Workflow
           │
  Core: AgentExecutor · ToolPipeline · Scheduler · MemoryManager
           │
  Interfaces: BaseLLM · BaseTool · BaseMemory · BaseCompressor
           │
  Ecosystem: PluginRegistry · MCP Adapter
```

### 2. Agent 主循环

```python
# Agent 主循环执行流程
1. 消息预处理 & 压缩检查 (92% 阈值)
2. 动态生成系统提示 (工具目录 + 风格指引)
3. LLM 生成 (支持工具调用)
4. 工具执行 (6 阶段流水线)
5. 结果聚合 & 状态更新
6. 循环判断 (最大迭代次数)
```

### 3. 工具执行流水线

```python
# 6 阶段流水线
tool_call → Discover → Validate → Authorize → CheckCancel → Execute → Format → Result

# 每个阶段都有:
- 清晰的职责边界
- 错误处理与自愈
- 性能指标收集
- 阶段耗时统计
```

### 4. 并发调度

```python
# 并发安全工具 (最大 10 并发)
Read, Glob, Grep, WebSearch, Task ...

# 非并发安全工具 (串行执行)
Write, Edit, Bash, TodoWrite ...

# 调度器自动处理
scheduler.schedule_batch(tools)  # 自动并发/串行决策
```

## 🧩 内置组件

### LLM 提供者

| 提供者 | 类名 | 支持工具调用 | 流式输出 |
|--------|------|-------------|---------|
| OpenAI | `OpenAILLM` | ✅ | ✅ |
| Mock (测试) | `MockLLM` | ❌ | ❌ |
| Rule (规则) | `RuleLLM` | ✅ | ❌ |

### 内置工具

| 工具 | 类名 | 并发安全 | 依赖 |
|------|------|---------|------|
| 计算器 | `Calculator` | ✅ | - |
| 文件读取 | `ReadFileTool` | ✅ | - |
| 文件写入 | `WriteFileTool` | ❌ | - |
| 文件搜索 | `GlobTool` | ✅ | - |
| 内容搜索 | `GrepTool` | ✅ | - |
| Web 搜索 | `WebSearchTool` | ✅ | duckduckgo-search |
| Python REPL | `PythonREPLTool` | ❌ | - |
| HTTP 请求 | `HTTPRequestTool` | ✅ | httpx |
| SubAgent | `TaskTool` | ✅ | - |

### 内存后端

- `InMemoryMemory`: 内存存储 (开发/测试)
- `RedisMemory`: Redis 持久化 (生产环境) - 待实现
- `PostgreSQLMemory`: PostgreSQL 存储 - 待实现

### 压缩策略

- `StructuredCompressor`: 8 段式结构化压缩 (对齐 Claude Code AU2 算法)
- `SlidingWindowCompressor`: 滑动窗口压缩 - 待实现

## 🔌 MCP 集成

Loom 原生支持 Model Context Protocol,可直接使用整个 MCP 工具生态!

```python
from loom import Agent
from loom.builtin.llms import OpenAILLM
from loom.mcp import MCPToolRegistry

# 自动发现本地 MCP servers
registry = MCPToolRegistry()
await registry.discover_local_servers()

# 加载 MCP 工具
tools = await registry.load_servers(["filesystem", "github", "postgres"])

# 在 Agent 中使用
agent = Agent(llm=OpenAILLM(api_key="..."), tools=tools)
result = await agent.run("Read config.json and create a GitHub issue")

await registry.close()
```

**可用的 MCP Servers**:
- `@modelcontextprotocol/server-filesystem` - 文件系统
- `@modelcontextprotocol/server-github` - GitHub 集成
- `@modelcontextprotocol/server-postgres` - PostgreSQL 数据库
- `@modelcontextprotocol/server-puppeteer` - Web 自动化
- 以及数百个社区 servers...

详见: [LOOM_MCP_INTEGRATION.md](./LOOM_MCP_INTEGRATION.md)

## 🎨 高级用法

### 自定义工具

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool

class WeatherInput(BaseModel):
    city: str = Field(description="City name")

class WeatherTool(BaseTool):
    name = "get_weather"
    description = "Get current weather"
    args_schema = WeatherInput
    is_concurrency_safe = True

    async def run(self, city: str, **kwargs):
        return f"Weather in {city}: Sunny, 25°C"

# 使用
agent = Agent(llm=llm, tools=[WeatherTool()])
```

### 自定义 LLM

```python
from loom.interfaces.llm import BaseLLM

class MyLLM(BaseLLM):
    @property
    def model_name(self) -> str:
        return "my-model"

    @property
    def supports_tools(self) -> bool:
        return True

    async def generate(self, messages):
        # 实现生成逻辑
        return "response"

    async def stream(self, messages):
        # 实现流式输出
        yield "chunk"

    async def generate_with_tools(self, messages, tools):
        # 实现工具调用
        return {"content": "...", "tool_calls": [...]}
```

### 链式组合

```python
from loom.components import Chain

# 构建处理链
chain = (
    Chain([preprocess])
    | agent
    | Chain([postprocess])
)

result = await chain.run(input)
```

### 权限控制

```python
from loom import Agent

agent = Agent(
    llm=llm,
    tools=tools,
    permission_policy={
        "write_file": "ask",      # 需要用户确认
        "http_request": "deny",   # 直接拒绝
        "default": "allow"        # 默认允许
    }
)
```

## 📊 性能指标

```python
# 获取运行指标
metrics = agent.get_metrics()

print(metrics)
# {
#   'total_iterations': 5,
#   'llm_calls': 6,
#   'tool_calls': 8,
#   'total_errors': 0,
#   'compression_count': 1
# }
```

## 🧪 测试

```python
# 使用 MockLLM 进行测试
from loom.builtin.llms import MockLLM

mock_llm = MockLLM(responses=[
    "I will use the calculator",
    "The answer is 4"
])

agent = Agent(llm=mock_llm, tools=[Calculator()])
result = await agent.run("What is 2+2?")
assert "4" in result
```

## 📖 文档

- [完整设计文档](../department/LOOM_UNIFIED_DEVELOPER_GUIDE.md)
- [MCP 集成指南](./LOOM_MCP_INTEGRATION.md)
- [架构设计 v2.0](../department/LOOM_FRAMEWORK_DESIGN_V2.md)
- [Claude Code 技术解析](../department/Claude_Code_Agent系统完整技术解析.md)

## 🗺️ 路线图

- [x] **Phase 1**: 核心接口与基础组件
- [x] **Phase 2**: 上下文压缩与稳定性
- [x] **Phase 3**: 工具生态与 Multi-Agent
- [x] **Phase 4**: MCP 协议集成
- [ ] **Phase 5**: 生产化 (Prometheus, 熔断, CI/CD)

## 🤝 贡献

欢迎贡献! 请查看 [贡献指南](./CONTRIBUTING.md)

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

## 🙏 致谢

- 设计灵感来自 Claude Code, LangChain, AutoGPT
- MCP 协议由 Anthropic 提供

---

**Loom: Build Intelligent Agents with Building Blocks** 🧩
