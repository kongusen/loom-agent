# Loom Agent

<div align="center">

**The Stateful Recursive Agent Framework for Complex Logic**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

[Documentation](docs/) | [Quick Start](#-quick-start) | [Examples](examples/) | [v0.0.8 Release](docs/INTEGRATION_COMPLETE.md)

</div>

---

## 🎯 What is Loom Agent?

Loom Agent 是一个**递归状态机（RSM）**框架，专为构建复杂逻辑的 AI Agent 而设计。与传统的图状态机（如 LangGraph）不同，Loom Agent 采用**事件溯源 + 生命周期钩子**的架构，在保持代码简洁的同时，提供生产级的可靠性和可观测性。

### 🌟 核心特性 (v0.0.8 - Recursive State Machine)

#### **新架构亮点**：

- 🎬 **Event Sourcing** - 完整的事件溯源，支持崩溃恢复和时间旅行调试
- 🪝 **Lifecycle Hooks** - 9 个钩子点，优雅的控制流，无需显式连线
- 🛡️ **HITL Support** - Human-in-the-Loop，危险操作自动拦截和确认
- 🔄 **Crash Recovery** - 从任意断点恢复执行，生产环境必备
- 🐛 **Context Debugger** - 透明化上下文管理，回答"为什么 LLM 忘记了 X"
- 📊 **Execution Visualizer** - 火焰图式可视化，清晰展示递归深度和时序
- 🎯 **Strategy Upgrade** - 独家特性：用新策略重放旧事件（LangGraph 做不到）

#### **经典特性**：

- 🚀 **Simple API** - 3 行代码即可开始
- 🔄 **Smart Recursion** - 自动循环检测和预防
- 📨 **Context Management** - 智能上下文压缩和优化
- 🔧 **Tool System** - 装饰器工具 + 并行执行
- 💾 **Persistent Memory** - 跨会话历史记录
- 🌐 **Multi-LLM** - OpenAI, Anthropic, 等

---

## 📦 Installation

```bash
# 基础安装
pip install loom-agent

# 带 OpenAI 支持
pip install loom-agent[openai]

# 完整安装
pip install loom-agent[all]
```

**要求**: Python 3.11+

---

## 🚀 Quick Start

### 基本使用

```python
import asyncio
from loom import agent

async def main():
    # 创建 Agent（自动从环境变量读取 API key）
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        tools=[]
    )

    # 运行
    result = await my_agent.run("Hello, introduce yourself")
    print(result)

asyncio.run(main())
```

### 🆕 启用持久化和 HITL (v0.0.8)

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook, LoggingHook

# 定义需要用户确认的危险工具
hitl_hook = HITLHook(
    dangerous_tools=["delete_file", "send_email"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ") == "y"
)

# 创建带持久化和 HITL 的 Agent
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[delete_file_tool, send_email_tool],
    # 🆕 新特性
    enable_persistence=True,  # 自动持久化到 EventJournal
    journal_path=Path("./logs"),  # 日志存储路径
    hooks=[hitl_hook, LoggingHook()],  # 生命周期钩子
    thread_id="user-123"  # 线程 ID
)

result = await my_agent.run("Clean up old files and send report")
```

### 🆕 崩溃恢复 (v0.0.8)

```python
from loom.core import AgentExecutor, EventJournal
from pathlib import Path

# 系统崩溃后恢复
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

# 从断点继续执行
async for event in executor.resume(thread_id="user-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ 恢复完成: {event.content}")
```

### 🆕 上下文调试 (v0.0.8)

```python
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=tools,
    context_debugger=debugger  # 🆕 上下文调试器
)

# 执行后分析
await my_agent.run("Complex multi-step task")

# 查看上下文管理决策
print(debugger.generate_summary())

# 解释特定迭代的上下文
print(debugger.explain_iteration(5))

# 追踪特定组件
print(debugger.explain_component("file_content.py"))
```

### 流式执行与事件监控

```python
from loom.core.events import AgentEventType

async for event in my_agent.stream("Analyze this data"):
    match event.type:
        case AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        case AgentEventType.TOOL_RESULT:
            print(f"\n[Tool] {event.tool_result.tool_name}")

        case AgentEventType.EXECUTION_CANCELLED:
            # 🆕 HITL 中断
            if event.metadata.get("interrupt"):
                print(f"\n⏸️  User intervention required")

        case AgentEventType.COMPRESSION_APPLIED:
            saved = event.metadata['tokens_before'] - event.metadata['tokens_after']
            print(f"\n📉 Saved {saved} tokens")

        case AgentEventType.AGENT_FINISH:
            print(f"\n✅ Done: {event.content}")
```

---

## 🆕 What's New in v0.0.8

### **递归状态机 (Recursive State Machine) 架构**

v0.0.8 是 loom-agent 的重大架构升级，从"隐式递归框架"进化为"递归状态机"，补齐了工程化能力：

#### 1. **Event Sourcing (事件溯源)**

```python
from loom.core import EventJournal
from pathlib import Path

# 所有执行事件自动记录
journal = EventJournal(storage_path=Path("./logs"))

my_agent = agent(
    llm=llm,
    tools=tools,
    event_journal=journal,
    thread_id="user-session-1"
)

# 执行后可重放事件
events = await journal.replay(thread_id="user-session-1")
print(f"记录了 {len(events)} 个事件")
```

**优势**：
- 📼 完整执行历史
- 🔍 事后分析和审计
- 🐛 问题重现和调试
- ⏱️ Time Travel 调试

#### 2. **Lifecycle Hooks (生命周期钩子)**

```python
from loom.core.lifecycle_hooks import LifecycleHook

# 自定义钩子
class CustomAnalyticsHook:
    async def after_tool_execution(self, frame, tool_result):
        # 收集工具使用统计
        self.stats[tool_result["tool_name"]] += 1
        return None

    async def before_llm_call(self, frame, messages):
        # 记录 LLM 调用
        self.llm_calls.append({
            "iteration": frame.depth,
            "message_count": len(messages)
        })
        return None

my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[CustomAnalyticsHook()]  # 🆕 注入钩子
)
```

**9 个钩子点**：
1. `before_iteration_start` - 迭代开始前
2. `before_context_assembly` - 上下文组装前
3. `after_context_assembly` - 上下文组装后
4. `before_llm_call` - LLM 调用前
5. `after_llm_response` - LLM 响应后
6. `before_tool_execution` - 工具执行前 (HITL 关键)
7. `after_tool_execution` - 工具执行后
8. `before_recursion` - 递归调用前
9. `after_iteration_end` - 迭代结束时

#### 3. **HITL (Human-in-the-Loop)**

```python
from loom.core.lifecycle_hooks import HITLHook

# 内置 HITL 钩子
hitl_hook = HITLHook(
    dangerous_tools=["delete_file", "send_email", "execute_shell"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ") == "y"
)

my_agent = agent(
    llm=llm,
    tools=all_tools,
    hooks=[hitl_hook]
)

# 自动在危险操作前暂停，等待用户确认
result = await my_agent.run("Delete old logs and send report")
# ⏸️  输出: "Allow delete_file with args {'path': '/old/logs'}? (y/n):"
```

**特性**：
- 🛡️ 自动拦截危险操作
- 💬 可自定义确认界面
- 📸 保存 checkpoint 用于恢复
- 🔄 支持拒绝后重试

#### 4. **Crash Recovery (崩溃恢复)**

```python
from loom.core import AgentExecutor

executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=journal
)

# 从任意断点恢复
async for event in executor.resume(thread_id="user-123"):
    # 自动：
    # 1. 重放事件历史
    # 2. 重建执行状态
    # 3. 从断点继续
    if event.type == AgentEventType.AGENT_FINISH:
        print("恢复成功!")
```

**用途**：
- 🔌 服务器重启后恢复
- 💥 崩溃后继续执行
- ⏸️ HITL 确认后恢复
- 🔄 长时间任务中断恢复

#### 5. **Context Debugger (上下文调试)**

```python
from loom.core import ContextDebugger

debugger = ContextDebugger()

my_agent = agent(
    llm=llm,
    tools=tools,
    context_debugger=debugger
)

await my_agent.run("Long complex task")

# 回答："为什么第 5 次迭代 LLM 忘记了文件内容？"
print(debugger.explain_iteration(5))
# 输出:
# ❌ Excluded Components:
#   - file_content.py (2500 tokens, priority=70)
#     Reason: Token limit exceeded, RAG docs (priority=90) took priority
```

**功能**：
- 📊 决策透明化
- 🔍 组件追踪
- 📉 Token 使用分析
- 💡 优化建议

#### 6. **策略升级 (独家特性)**

```python
from loom.core import StateReconstructor

# 原始执行用的是 compression v1
# ... 系统崩溃 ...

# 重启时已经升级到 compression v2
reconstructor = StateReconstructor()
events = await journal.replay(thread_id="user-123")

# 🌟 用新策略重放旧事件！
frame, metadata = await reconstructor.reconstruct_with_new_strategy(
    events,
    compression_strategy=CompressionV2()
)

# 重建的状态使用 v2 压缩！
# LangGraph 的静态快照无法实现这一点
```

---

## 📊 loom-agent vs LangGraph

| 能力 | LangGraph | loom-agent 0.0.8 | 优势方 |
|------|-----------|------------------|--------|
| **核心抽象** | 图（StateGraph + 节点） | 递归执行栈（ExecutionFrame） | 🟡 各有优势 |
| **持久化** | 静态快照 (Checkpointing) | 事件溯源 (Event Sourcing) | 🟢 **loom** |
| **策略升级** | ❌ 不支持 | ✅ 重放时可注入新策略 | 🟢 **loom (独有)** |
| **HITL** | `interrupt_before` API | LifecycleHooks + InterruptException | 🟢 **loom** |
| **上下文治理** | 简单字典 | Context Fabric + ContextDebugger | 🟢 **loom (独有)** |
| **可视化** | 流程图 (DAG) | 火焰图 (时序+深度) | 🟡 各有优势 |
| **代码简洁性** | 需要显式连线 | 钩子注入 | 🟢 **loom** |
| **显式工作流** | ✅ 图结构清晰 | ❌ 隐式递归 | 🟠 **LangGraph** |

**定位差异**：
- **LangGraph**: 适合确定性强的标准操作流程（SOP）
- **loom-agent**: 适合探索性强、逻辑嵌套深的复杂任务

---

## 🔧 Architecture

### 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                   ExecutionFrame                        │
│  - 不可变执行栈帧                                          │
│  - 完整状态快照                                            │
│  - 父子链接（递归树）                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                   EventJournal                          │
│  - Append-only 事件日志                                   │
│  - JSON Lines 存储                                        │
│  - 异步批量写入                                            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                 LifecycleHooks                          │
│  - 9 个钩子点                                             │
│  - InterruptException (HITL)                            │
│  - HookManager (钩子链)                                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              StateReconstructor                         │
│  - 事件重放                                               │
│  - Time Travel                                          │
│  - 策略升级                                               │
└─────────────────────────────────────────────────────────┘
```

### 执行流程 (tt 递归循环)

```
用户输入
  ↓
[Hook] before_iteration_start
  ↓
┌─ Phase 1: Context Assembly ──────────┐
│ [Hook] before_context_assembly       │
│ [ContextAssembler] 组装系统上下文      │
│ [ContextDebugger] 记录决策             │
│ [Hook] after_context_assembly        │
└──────────────────────────────────────┘
  ↓
┌─ Phase 2: LLM Call ──────────────────┐
│ [Hook] before_llm_call               │
│ [LLM] Stream 或 Generate             │
│ [EventJournal] 记录 LLM_DELTA        │
│ [Hook] after_llm_response            │
└──────────────────────────────────────┘
  ↓
┌─ Phase 3: Decision ──────────────────┐
│ 检查是否有 tool_calls                 │
│ 如果没有 → AGENT_FINISH               │
│ 如果有 → 继续到 Phase 4                │
└──────────────────────────────────────┘
  ↓
┌─ Phase 4: Tool Execution ────────────┐
│ for each tool_call:                  │
│   [Hook] before_tool_execution ← HITL│
│   [ToolOrchestrator] 执行工具         │
│   [EventJournal] 记录 TOOL_RESULT    │
│   [Hook] after_tool_execution        │
└──────────────────────────────────────┘
  ↓
┌─ Phase 5: Recursion ─────────────────┐
│ next_frame = frame.next_frame()      │
│ [Hook] before_recursion              │
│ [EventJournal] 保存 checkpoint       │
│ 🔥 递归调用 tt(next_frame)            │
└──────────────────────────────────────┘
  ↓
[Hook] after_iteration_end
  ↓
完成 or 继续递归
```

---

## 📚 Documentation

### 新架构文档 (v0.0.8)

- 🏗️ [架构重构](docs/ARCHITECTURE_REFACTOR.md) - 完整设计理念 (600+ 行)
- ✅ [集成完成报告](docs/INTEGRATION_COMPLETE.md) - v0.0.8 特性总结
- 📊 [集成状态](docs/INTEGRATION_STATUS.md) - 开发进度追踪

### 经典文档

- 📖 [用户指南](docs/USAGE_GUIDE_V0_0_5.md) - 详细使用文档
- 🚀 [快速开始](docs/QUICKSTART.md) - 5 分钟上手
- 🔧 [API 参考](docs/user/api-reference.md) - 完整 API
- 💡 [示例代码](examples/) - 实用示例

### 示例

- 🎬 [完整集成示例](examples/integration_example.py) - 展示所有新特性
- 🪝 [自定义钩子示例](examples/integration_example.py#L169-L194)
- 🔄 [崩溃恢复示例](examples/integration_example.py#L89-L118)
- 🛡️ [HITL 示例](examples/integration_example.py#L122-L162)

---

## 🧪 Testing

```bash
# 运行所有测试
pytest

# 运行 v0.0.8 集成测试
pytest tests/integration/test_loom_2_0_integration.py -v

# 运行覆盖率测试
pytest --cov=loom --cov-report=html
```

**测试状态**:
- 核心功能测试: ✅ 50% 通过 (4/8)
- 单元测试: ✅ 全部通过
- 集成测试: 🔶 部分通过 (测试工具待完善)

---

## 🎯 Use Cases

### 1. 生产环境 Agent (带崩溃恢复)

```python
# 部署到生产环境，支持自动恢复
my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=production_tools,
    enable_persistence=True,  # 必须
    journal_path=Path("/var/log/loom"),
    hooks=[LoggingHook(), MetricsHook()],
    max_iterations=100
)

# 崩溃后自动恢复
if crashed:
    async for event in my_agent.resume(thread_id=session_id):
        handle_event(event)
```

### 2. 危险操作保护 (HITL)

```python
# 涉及危险操作的 Agent
hitl_hook = HITLHook(
    dangerous_tools=["delete_database", "send_mass_email", "charge_credit_card"],
    ask_user_callback=get_user_confirmation  # 自定义 UI
)

admin_agent = agent(
    llm=llm,
    tools=admin_tools,
    hooks=[hitl_hook]
)

# 危险操作会自动暂停等待确认
await admin_agent.run("Clean up old user data")
```

### 3. 研究和调试

```python
# 启用完整调试功能
debugger = ContextDebugger(enable_auto_export=True)

research_agent = agent(
    llm=llm,
    tools=research_tools,
    context_debugger=debugger,
    enable_persistence=True
)

# 执行后分析
await research_agent.run("Research quantum computing")

# 查看决策过程
print(debugger.generate_summary())
print(debugger.explain_iteration(5))
```

---

## 🗺️ Roadmap

### ✅ v0.0.9 (Current)
- ✅ Fixed hooks parameter integration in Agent class
- ✅ Comprehensive hooks usage documentation and examples
- ✅ Enhanced developer experience with clearer hook patterns

### ✅ v0.0.8 (Recursive State Machine)
- ✅ ExecutionFrame (执行栈帧)
- ✅ EventJournal (事件溯源)
- ✅ LifecycleHooks (生命周期钩子)
- ✅ HITL (Human-in-the-Loop)
- ✅ ContextDebugger (上下文调试)
- ✅ StateReconstructor (状态重建)
- ✅ Crash Recovery (崩溃恢复)

### 🔜 v0.1.0 (Planned)
- 📊 Web UI for debugging (基于 FastAPI)
- 🎨 Enhanced visualizations
- 🧪 完善测试工具 (MockLLMWithTools)
- 📈 性能基准测试

### 🎯 v0.1.0 (Goal)
- 🔌 Plugin system
- 🌐 分布式执行支持
- 💾 多后端存储 (Postgres)
- 📚 完整文档和教程

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Special thanks to:
- **Claude Code** - 递归 tt 模式的启发
- **LangGraph** - 图状态机的对比参考
- **React Fiber** - ExecutionFrame 设计灵感
- 早期用户和贡献者

---

## 🔗 Links

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **Issues**: https://github.com/kongusen/loom-agent/issues
- **Releases**: [v0.0.9](CHANGELOG.md) | [v0.0.8](docs/INTEGRATION_COMPLETE.md) | [v0.0.5](docs_dev/PHASES_2_3_COMBINED_SUMMARY.md)
- **Examples**: [Integration Example](examples/integration_example.py)

---

<div align="center">

**Built with ❤️ for reliable, stateful AI agents**

**v0.0.8 核心创新**:

🎬 Event Sourcing | 🪝 Lifecycle Hooks | 🛡️ HITL | 🔄 Crash Recovery | 🐛 Context Debugger

<sub>如果 Loom Agent 对您有帮助，请给我们一个 ⭐ !</sub>

</div>
