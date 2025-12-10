# 🧵 Loom Agent

<div align="center">

**企业级递归状态机 Agent 框架**

**The Stateful Recursive Agent Framework with Event Sourcing & Multi-Agent Collaboration**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-106%2B%20passing-brightgreen.svg)](tests/)

**中文** | [English](README_EN.md)

[快速开始](#-快速开始) | [核心机制](#-核心机制) | [多代理协作](#-crew-多代理协作系统) | [插件系统](#-工具插件系统) | [文档](#-文档)

</div>

---

## 🎯 什么是 Loom Agent？

Loom Agent 是一个基于**递归状态机 (RSM)** 和**事件溯源 (Event Sourcing)** 的 AI Agent 框架，专为构建**生产级、可靠、可观测**的复杂 Agent 应用而设计。

### 🌟 为什么选择 Loom Agent？

与传统框架（如 LangGraph、AutoGen、CrewAI）相比，Loom Agent 的独特优势：

| 特性 | LangGraph | AutoGen | CrewAI | **Loom Agent** |
|------|-----------|---------|--------|----------------|
| **核心架构** | 图状态机 | 对话式 | 角色编排 | **递归状态机 + 事件溯源** |
| **事件溯源** | ❌ | ❌ | ❌ | ✅ **完整 Event Sourcing** |
| **崩溃恢复** | ⚠️ Checkpointing | ❌ | ❌ | ✅ **从任意断点恢复** |
| **策略升级** | ❌ | ❌ | ❌ | ✅ **重放时注入新策略 (独家)** |
| **HITL** | 基础 interrupt | ❌ | ❌ | ✅ **完整生命周期钩子** |
| **上下文调试** | ❌ | ❌ | ❌ | ✅ **ContextDebugger (独家)** |
| **多代理协作** | ❌ | ✅ | ✅ | ✅ **Crew 系统 + 4种编排模式** |
| **工具编排** | 基础 | 基础 | 基础 | ✅ **智能并行 + 依赖检测** |
| **代码简洁性** | 需要显式连线 | 配置复杂 | 配置复杂 | ✅ **钩子注入，零连线** |

**定位**：Loom Agent = **LangGraph 的可靠性** + **AutoGen 的协作能力** + **独家事件溯源能力**

---

## 📦 安装

```bash
# 基础安装
pip install loom-agent

# 带 OpenAI 支持
pip install loom-agent[openai]

# 完整安装（包含所有可选依赖）
pip install loom-agent[all]
```

**要求**: Python 3.11+

---

## 🚀 快速开始

### 30秒上手

```python
import asyncio
from loom import agent

async def main():
    # 创建 Agent（自动从环境变量读取 OPENAI_API_KEY）
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        system_instructions="You are a helpful assistant."
    )

    # 运行
    result = await my_agent.run("What is the weather in San Francisco?")
    print(result)

asyncio.run(main())
```

### 5分钟进阶：带工具的 Agent

```python
from loom import agent
from loom.builtin.tools import ReadFileTool, GlobTool, GrepTool

# 创建带工具的 Agent
code_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool(), GlobTool(), GrepTool()],
    system_instructions="You are a code analysis expert."
)

# 执行复杂任务
result = await code_agent.run(
    "Find all TODO comments in Python files and summarize them"
)
print(result)
```

### 10分钟高级：启用持久化和 HITL

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook, LoggingHook
from loom.builtin.tools import WriteFileTool, BashTool

# 定义危险工具列表
hitl_hook = HITLHook(
    dangerous_tools=["bash", "write_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

# 创建生产级 Agent
production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[WriteFileTool(), BashTool()],

    # 🔥 关键特性
    enable_persistence=True,           # 事件溯源
    journal_path=Path("./logs"),       # 日志存储
    hooks=[hitl_hook, LoggingHook()],  # 生命周期钩子
    thread_id="user-session-123"       # 会话 ID
)

# 运行（危险操作会自动暂停等待确认）
result = await production_agent.run(
    "Create a backup script and test it"
)
```

---

## 🏗️ 核心机制

### 1. 递归状态机 (Recursive State Machine)

Loom Agent 的核心是 **tt 递归循环** —— 一个自驱动的递归执行引擎。

#### 工作原理

```python
async def tt(frame: ExecutionFrame) -> str:
    """
    tt = think-tool-think-tool...
    递归循环直到任务完成
    """
    # Phase 1: 组装上下文
    messages = assemble_context(frame)

    # Phase 2: LLM 推理
    response = await llm.generate(messages)

    # Phase 3: 决策
    if response.finish_reason == "stop":
        return response.content  # 完成

    # Phase 4: 执行工具
    tool_results = await execute_tools(response.tool_calls)

    # Phase 5: 递归 🔥
    next_frame = frame.next_frame(tool_results)
    return await tt(next_frame)  # 递归调用自己
```

**执行流程**:

```
用户输入 → tt(frame_0)
             ↓
    ┌────────────────────┐
    │ 组装上下文           │
    │ LLM 推理            │
    │ 检查是否完成？       │
    └────────────────────┘
             ↓
        需要工具？
             ↓
    ┌────────────────────┐
    │ 执行工具            │
    │ 生成 tool_results   │
    └────────────────────┘
             ↓
    🔥 tt(frame_1) ← 递归
             ↓
           继续...
             ↓
         完成返回
```

**优势**:
- 🔄 **自然递归** - 无需显式状态机定义
- 📊 **完整执行树** - 每层递归都是一个 ExecutionFrame
- 🐛 **易于调试** - 执行栈清晰可见
- 🛡️ **循环检测** - 自动防止无限递归

---

### 2. 事件溯源 (Event Sourcing)

Loom Agent 使用**事件溯源**而非快照来持久化状态。

#### 为什么是事件溯源？

| 方法 | 快照 (Checkpointing) | 事件溯源 (Event Sourcing) |
|------|---------------------|--------------------------|
| **存储** | 定期保存完整状态 | 记录所有事件 |
| **恢复** | 加载最近快照 | 重放事件历史 |
| **审计** | 只有快照时的状态 | 完整执行历史 |
| **策略升级** | ❌ 无法改变过去 | ✅ 重放时注入新策略 |
| **调试** | 只能看快照 | 完整时间旅行 |

#### 事件类型

```python
class AgentEventType(Enum):
    # 核心事件
    AGENT_START = "agent_start"           # Agent 开始
    AGENT_FINISH = "agent_finish"         # Agent 完成

    # LLM 事件
    LLM_DELTA = "llm_delta"               # LLM 流式输出
    LLM_COMPLETE = "llm_complete"         # LLM 完成

    # 工具事件
    TOOL_CALL = "tool_call"               # 工具调用
    TOOL_RESULT = "tool_result"           # 工具结果

    # 状态事件
    COMPRESSION_APPLIED = "compression"   # 上下文压缩
    EXECUTION_CANCELLED = "cancelled"     # HITL 中断

    # 错误事件
    ERROR = "error"                       # 错误
```

#### 使用示例

```python
from loom.core import EventJournal
from pathlib import Path

# 创建事件日志
journal = EventJournal(storage_path=Path("./logs"))

# 创建 Agent（自动记录所有事件）
my_agent = agent(
    llm=llm,
    tools=tools,
    event_journal=journal,
    thread_id="user-123"
)

# 执行任务（所有事件自动记录）
await my_agent.run("Analyze this codebase")

# 重放事件
events = await journal.replay(thread_id="user-123")
print(f"记录了 {len(events)} 个事件")

# 按类型过滤
tool_events = [e for e in events if e.type == AgentEventType.TOOL_RESULT]
print(f"执行了 {len(tool_events)} 个工具")
```

---

### 3. 生命周期钩子 (Lifecycle Hooks)

Loom Agent 提供 **9 个钩子点**，让您在执行流程的关键节点注入自定义逻辑。

#### 钩子点列表

```python
class LifecycleHook:
    # 1. 迭代开始前
    async def before_iteration_start(self, frame: ExecutionFrame) -> Optional[dict]:
        """在新迭代开始前调用"""
        pass

    # 2. 上下文组装前
    async def before_context_assembly(self, frame: ExecutionFrame) -> Optional[dict]:
        """在组装上下文前调用"""
        pass

    # 3. 上下文组装后
    async def after_context_assembly(self, frame: ExecutionFrame, messages: list) -> Optional[dict]:
        """在组装上下文后调用"""
        pass

    # 4. LLM 调用前
    async def before_llm_call(self, frame: ExecutionFrame, messages: list) -> Optional[dict]:
        """在调用 LLM 前调用"""
        pass

    # 5. LLM 响应后
    async def after_llm_response(self, frame: ExecutionFrame, response: dict) -> Optional[dict]:
        """在 LLM 响应后调用"""
        pass

    # 6. 工具执行前 🔥 HITL 关键点
    async def before_tool_execution(self, frame: ExecutionFrame, tool_call: dict) -> Optional[dict]:
        """在执行工具前调用 - HITL 拦截点"""
        pass

    # 7. 工具执行后
    async def after_tool_execution(self, frame: ExecutionFrame, tool_result: dict) -> Optional[dict]:
        """在工具执行后调用"""
        pass

    # 8. 递归前
    async def before_recursion(self, frame: ExecutionFrame, next_frame: ExecutionFrame) -> Optional[dict]:
        """在递归调用前调用"""
        pass

    # 9. 迭代结束
    async def after_iteration_end(self, frame: ExecutionFrame, result: Any) -> Optional[dict]:
        """在迭代结束时调用"""
        pass
```

#### 自定义钩子示例

```python
from loom.core.lifecycle_hooks import LifecycleHook

class MetricsHook(LifecycleHook):
    """收集执行指标的钩子"""

    def __init__(self):
        self.tool_usage = {}
        self.llm_calls = 0
        self.total_tokens = 0

    async def before_llm_call(self, frame, messages):
        self.llm_calls += 1
        return None

    async def after_llm_response(self, frame, response):
        self.total_tokens += response.get("usage", {}).get("total_tokens", 0)
        return None

    async def after_tool_execution(self, frame, tool_result):
        tool_name = tool_result["tool_name"]
        self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        return None

    def get_report(self):
        return {
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "tool_usage": self.tool_usage
        }

# 使用
metrics = MetricsHook()

my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[metrics]  # 注入钩子
)

await my_agent.run("Complex task")

# 获取指标
print(metrics.get_report())
# {
#   "llm_calls": 5,
#   "total_tokens": 2500,
#   "tool_usage": {"read_file": 3, "grep": 2}
# }
```

#### 内置钩子

##### HITLHook - Human-in-the-Loop

```python
from loom.core.lifecycle_hooks import HITLHook

# 创建 HITL 钩子
hitl = HITLHook(
    dangerous_tools=["delete_file", "bash", "send_email"],
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ") == "y"
)

my_agent = agent(
    llm=llm,
    tools=all_tools,
    hooks=[hitl]
)

# 执行（危险工具会自动暂停）
await my_agent.run("Clean up old files and send report")
# ⏸️  输出: "Allow delete_file with args {'path': '/old'}? (y/n):"
```

##### LoggingHook - 日志记录

```python
from loom.core.lifecycle_hooks import LoggingHook

logging_hook = LoggingHook(
    log_level="INFO",
    log_file=Path("./agent.log")
)

my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[logging_hook]
)
```

---

### 4. ExecutionFrame（执行栈帧）

每次递归调用都会创建一个新的 `ExecutionFrame`，形成**执行树**。

#### ExecutionFrame 结构

```python
@dataclass
class ExecutionFrame:
    """
    不可变执行栈帧
    """
    # 身份
    id: str                              # 帧 ID
    depth: int                           # 递归深度
    parent_id: Optional[str]             # 父帧 ID
    thread_id: str                       # 线程 ID

    # 状态
    history: List[dict]                  # 对话历史
    context_fabric: dict                 # 上下文织物
    tool_results_buffer: List[dict]      # 工具结果缓冲

    # 元数据
    created_at: float                    # 创建时间
    metadata: dict                       # 自定义元数据

    def next_frame(self, tool_results: List[dict]) -> "ExecutionFrame":
        """创建下一帧（递归）"""
        return ExecutionFrame(
            id=generate_id(),
            depth=self.depth + 1,
            parent_id=self.id,
            thread_id=self.thread_id,
            history=self.history + [tool_results_to_messages(tool_results)],
            context_fabric=self.context_fabric.copy(),
            tool_results_buffer=tool_results,
            created_at=time.time(),
            metadata=self.metadata.copy()
        )
```

#### 执行树示例

```
frame_0 (depth=0) - "Analyze codebase"
  │
  ├─ tool_call: glob("**.py")
  │
  └─ frame_1 (depth=1) - [tool_results]
      │
      ├─ tool_call: read_file("main.py")
      │
      └─ frame_2 (depth=2) - [tool_results]
          │
          ├─ tool_call: grep("TODO")
          │
          └─ frame_3 (depth=3) - [tool_results]
              │
              └─ 完成返回
```

**优势**:
- 📊 **清晰的执行追踪** - 每层递归独立
- 🔍 **易于调试** - 可以查看任意深度的状态
- 🛡️ **不可变性** - 父帧状态不受子帧影响
- 🎯 **精确恢复** - 崩溃后可以从任意帧恢复

---

### 5. 上下文管理 (Context Fabric)

Loom Agent 使用 **ContextFabric（上下文织物）** 智能管理上下文，避免 token 超限。

#### ContextFabric 架构

```python
class ContextFabric:
    """
    上下文织物 - 管理各种上下文组件
    """
    components: Dict[str, ContextComponent]

    class ContextComponent:
        content: str         # 内容
        priority: int        # 优先级 (0-100)
        tokens: int          # token 数量
        strategy: str        # 压缩策略
        metadata: dict       # 元数据
```

#### 上下文组件类型

```python
from loom.core import ContextFabric

fabric = ContextFabric()

# 1. 系统指令（最高优先级）
fabric.add_system_instructions(
    content="You are a helpful assistant.",
    priority=100  # 永不删除
)

# 2. RAG 文档（高优先级）
fabric.add_rag_docs(
    content="Documentation content...",
    priority=90
)

# 3. 工具结果（中等优先级）
fabric.add_tool_results(
    results=[...],
    priority=70
)

# 4. 历史对话（低优先级）
fabric.add_history(
    messages=[...],
    priority=50
)

# 5. 临时数据（最低优先级）
fabric.add_scratch_pad(
    content="Temporary notes...",
    priority=30
)
```

#### 智能压缩

```python
from loom.core import ContextAssembler

assembler = ContextAssembler(
    max_tokens=4000,
    compression_strategies={
        "history": "summarize",      # 总结历史
        "tool_results": "truncate",   # 截断工具结果
        "scratch_pad": "drop"         # 丢弃草稿
    }
)

# 组装上下文（自动压缩）
messages, metadata = assembler.assemble(fabric, frame)

# 查看压缩统计
print(metadata["compression_stats"])
# {
#   "original_tokens": 6000,
#   "final_tokens": 3800,
#   "saved_tokens": 2200,
#   "components_dropped": ["scratch_pad"],
#   "components_compressed": ["history"]
# }
```

#### ContextDebugger - 上下文调试器

回答"**为什么 LLM 忘记了 X？**"

```python
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    llm=llm,
    tools=tools,
    context_debugger=debugger  # 启用调试器
)

# 执行任务
await my_agent.run("Long complex task")

# 查看第 5 次迭代的上下文决策
print(debugger.explain_iteration(5))
# 输出:
# ✅ Included Components:
#   - system_instructions (500 tokens, priority=100)
#   - rag_docs (2000 tokens, priority=90)
#   - history (1300 tokens, priority=50, compressed from 2500)
#
# ❌ Excluded Components:
#   - file_content.py (2500 tokens, priority=70)
#     Reason: Token limit exceeded, higher priority items took precedence
#
# 💡 Suggestion: Increase priority of 'file_content.py' to 85 to include it

# 追踪特定组件
print(debugger.explain_component("file_content.py"))
# Component 'file_content.py' history:
#   Iteration 1-3: ✅ Included
#   Iteration 4-6: ❌ Excluded (token limit)
#   Iteration 7-9: ✅ Included (after compression)

# 生成完整报告
print(debugger.generate_summary())
```

---

### 6. 工具编排 (Tool Orchestration)

Loom Agent 的 **ToolOrchestrator** 智能管理工具执行。

#### 工具类型

```python
from loom.interfaces.tool import BaseTool

class MyTool(BaseTool):
    name = "my_tool"
    description = "My custom tool"
    args_schema = MyToolInput

    # 🆕 工具属性
    is_read_only = True           # 只读工具（可并行）
    category = "general"          # 类别: general/destructive/network
    requires_confirmation = False # 是否需要确认

    async def run(self, **kwargs) -> str:
        # 工具实现
        return "result"
```

#### 智能并行执行

```python
from loom.core import ToolOrchestrator

orchestrator = ToolOrchestrator()

# 工具调用
tool_calls = [
    {"name": "read_file", "args": {"path": "a.py"}},  # 只读
    {"name": "read_file", "args": {"path": "b.py"}},  # 只读
    {"name": "write_file", "args": {"path": "c.py", "content": "..."}},  # 破坏性
]

# 自动并行/串行决策
results = await orchestrator.execute_batch(tool_calls, tools)

# 执行策略:
# 1. 两个 read_file 并行执行 ✅
# 2. write_file 等待它们完成后执行 ✅
```

#### 依赖检测

```python
# ToolOrchestrator 自动检测工具间依赖

tool_calls = [
    {"name": "glob", "args": {"pattern": "**.py"}},
    {"name": "read_file", "args": {"path": "{glob_result[0]}"}},  # 依赖 glob
]

# 自动串行执行:
# 1. glob 先执行
# 2. 结果注入到 read_file 的参数
# 3. read_file 再执行
```

---

### 7. 崩溃恢复 (Crash Recovery)

Loom Agent 支持从**任意断点**恢复执行。

#### 恢复流程

```python
from loom.core import AgentExecutor, EventJournal
from pathlib import Path

# 1. 系统崩溃前的执行
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

try:
    await executor.execute("Long running task", thread_id="user-123")
except SystemExit:
    print("系统崩溃...")

# 2. 系统重启后恢复
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    event_journal=EventJournal(Path("./logs"))
)

# 从断点继续（自动重放事件历史）
async for event in executor.resume(thread_id="user-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print(f"✅ 恢复完成: {event.content}")
```

#### 工作原理

```
崩溃前:
  执行到第 5 次迭代 → 系统崩溃
  EventJournal 已记录: [event_1, event_2, ..., event_5]

恢复时:
  1. 读取 EventJournal
  2. 重放事件历史 → 重建 ExecutionFrame
  3. 从第 6 次迭代继续执行
```

**优势**:
- 🛡️ **生产级可靠性** - 服务器重启不丢失进度
- 💰 **节省成本** - 避免重复 LLM 调用
- ⏱️ **用户体验** - 长任务中断后自动恢复
- 📊 **完整审计** - 所有执行历史都被记录

---

### 8. 统一协调模式 (Unified Coordination)

Loom Agent 提供 **UnifiedCoordinator** 统一管理复杂执行流程。

#### 什么是统一协调？

传统方式每个组件独立工作，UnifiedCoordinator 提供**中心化协调**：

```
传统方式:
  LLM → Tools → Context → ... (各自为政)

统一协调:
  UnifiedCoordinator
      ├─ ContextAssembler
      ├─ ToolOrchestrator
      ├─ LifecycleHooks
      └─ EventJournal
```

#### 使用示例

```python
from loom.core import UnifiedCoordinator, ExecutionFrame

coordinator = UnifiedCoordinator(
    llm=llm,
    tools=tools,
    context_assembler=assembler,
    tool_orchestrator=orchestrator,
    hooks=[hitl_hook, metrics_hook],
    event_journal=journal
)

# 执行（所有组件协调工作）
frame = ExecutionFrame.create(user_input="Task")
result = await coordinator.execute_iteration(frame)
```

---

## 🤝 Crew 多代理协作系统

Loom Agent 内置 **Crew 系统**，支持 CrewAI/AutoGen 级别的多代理协作。

### 核心概念

```
Crew (团队)
  ├─ Role (角色定义)
  ├─ Task (任务)
  ├─ OrchestrationPlan (编排计划)
  ├─ MessageBus (消息总线)
  └─ SharedState (共享状态)
```

### 快速开始

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# 1. 定义角色
roles = [
    Role(
        name="researcher",
        goal="Gather and analyze information",
        tools=["read_file", "grep", "web_search"],
        capabilities=["research", "analysis"]
    ),
    Role(
        name="developer",
        goal="Write and modify code",
        tools=["read_file", "write_file", "edit_file"],
        capabilities=["coding"]
    ),
    Role(
        name="qa_engineer",
        goal="Test and validate implementations",
        tools=["read_file", "bash"],
        capabilities=["testing"]
    )
]

# 2. 创建团队
crew = Crew(roles=roles, llm=llm)

# 3. 定义任务
tasks = [
    Task(
        id="research",
        description="Research OAuth 2.0",
        prompt="Research OAuth 2.0 best practices and security considerations",
        assigned_role="researcher",
        output_key="research_result"
    ),
    Task(
        id="implement",
        description="Implement OAuth",
        prompt="Implement OAuth 2.0 authentication based on research findings",
        assigned_role="developer",
        dependencies=["research"],  # 依赖研究任务
        output_key="code_result"
    ),
    Task(
        id="test",
        description="Test implementation",
        prompt="Test the OAuth implementation for security and functionality",
        assigned_role="qa_engineer",
        dependencies=["implement"]  # 依赖实现任务
    )
]

# 4. 创建编排计划
plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.SEQUENTIAL  # 顺序执行
)

# 5. 执行
results = await crew.kickoff(plan)

print(results["research"])   # 研究结果
print(results["implement"])  # 实现结果
print(results["test"])       # 测试结果
```

### 编排模式

#### 1. SEQUENTIAL - 顺序执行

```python
plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.SEQUENTIAL
)

# 执行顺序: task1 → task2 → task3
```

#### 2. PARALLEL - 并行执行

```python
plan = OrchestrationPlan(
    tasks=[
        Task(id="research_oauth", ...),
        Task(id="research_jwt", ...),
        Task(id="research_saml", ...),  # 三个研究任务并行
    ],
    mode=OrchestrationMode.PARALLEL,
    max_parallel=3
)

# 执行: 三个任务同时进行
```

#### 3. CONDITIONAL - 条件执行

```python
from loom.crew import ConditionBuilder

tasks = [
    Task(
        id="check_security",
        description="Check security requirements",
        prompt="Analyze if OAuth is required",
        assigned_role="researcher",
        output_key="needs_oauth"
    ),
    Task(
        id="implement_oauth",
        description="Implement OAuth",
        prompt="Implement OAuth 2.0",
        assigned_role="developer",
        # 🔥 条件：只在需要时执行
        condition=ConditionBuilder.key_equals("needs_oauth", True)
    )
]

plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.CONDITIONAL)

# 执行: implement_oauth 仅在 needs_oauth=True 时执行
```

#### 4. HIERARCHICAL - 层级协调

```python
roles = [
    Role(
        name="manager",
        goal="Coordinate team and ensure task completion",
        tools=["delegate"],  # 🔥 Manager 可以委托任务
        delegation=True
    ),
    Role(name="researcher", ...),
    Role(name="developer", ...),
]

plan = OrchestrationPlan(
    tasks=tasks,
    mode=OrchestrationMode.HIERARCHICAL  # Manager 协调执行
)

# 执行流程:
# 1. Manager 分析任务
# 2. Manager 委托给合适的团队成员
# 3. 收集结果并汇总
```

### Agent 间通信

#### MessageBus - 消息总线

```python
from loom.crew import MessageBus, AgentMessage, MessageType

# 创建消息总线
message_bus = MessageBus()

# Agent A 发送消息
await message_bus.publish(
    AgentMessage(
        from_agent="researcher",
        to_agent="developer",  # 点对点
        type=MessageType.NOTIFICATION,
        content="Found security vulnerability in OAuth implementation",
        thread_id="task-123"
    )
)

# Agent B 订阅消息
def handle_message(msg: AgentMessage):
    print(f"收到来自 {msg.from_agent} 的消息: {msg.content}")

message_bus.subscribe("developer", handle_message)
```

#### SharedState - 共享状态

```python
from loom.crew import SharedState

# 创建共享状态
shared_state = SharedState()

# 线程安全的读写
await shared_state.set("oauth_config", {"client_id": "...", "secret": "..."})
config = await shared_state.get("oauth_config")

# 原子更新
await shared_state.update("counter", lambda x: (x or 0) + 1)
```

### 完整示例

查看 [examples/crew_demo.py](examples/crew_demo.py) 获取完整的多代理协作示例，包括：
- 代码审查工作流 (Sequential)
- 并行功能实现 (Parallel)
- 条件任务执行 (Conditional)
- Manager 协调 (Hierarchical)
- Agent 间通信

---

## 🔌 工具插件系统

Loom Agent 提供**工具插件系统**，支持动态加载和管理自定义工具。

### 快速开始

#### 创建插件

创建文件 `weather_plugin.py`:

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata

# 1. 定义插件元数据
PLUGIN_METADATA = ToolPluginMetadata(
    name="weather-lookup",
    version="1.0.0",
    author="Your Name <you@example.com>",
    description="Weather lookup tool",
    tags=["weather", "data"],
)

# 2. 定义工具输入
class WeatherInput(BaseModel):
    location: str = Field(..., description="City name")
    units: str = Field("celsius", description="Temperature units")

# 3. 定义工具
class WeatherTool(BaseTool):
    name = "weather"
    description = "Get current weather"
    args_schema = WeatherInput

    async def run(self, location: str, units: str = "celsius", **kwargs) -> str:
        # 工具实现
        return f"Weather in {location}: 22°{units[0].upper()}"
```

#### 使用插件

```python
from loom.plugins import ToolPluginManager

# 创建插件管理器
manager = ToolPluginManager()

# 安装插件
await manager.install_from_file("weather_plugin.py", enable=True)

# 获取工具
weather_tool = manager.get_tool("weather")

# 使用工具
result = await weather_tool.run(location="Tokyo")
print(result)  # "Weather in Tokyo: 22°C"

# 在 Agent 中使用
my_agent = agent(
    llm=llm,
    tools=[weather_tool]
)
```

### 插件管理

```python
from loom.plugins import ToolPluginManager, PluginStatus

manager = ToolPluginManager(plugin_dir="./plugins")

# 发现并安装所有插件
plugins = await manager.discover_and_install("./plugins", enable=True)

# 列出已安装插件
for plugin in manager.list_installed():
    print(f"{plugin.metadata.name} v{plugin.metadata.version}")

# 搜索插件
finance_plugins = manager.registry.search_by_tag("finance")

# 启用/禁用
manager.disable("weather-lookup")
manager.enable("weather-lookup")

# 卸载
manager.uninstall("weather-lookup")

# 获取统计
stats = manager.get_stats()
print(f"Total plugins: {stats['total_plugins']}")
print(f"Enabled: {stats['enabled']}")
```

### 内置示例插件

```python
from examples.tool_plugins.example_plugins import EXAMPLE_PLUGINS

# 3 个示例插件:
# 1. WeatherTool - 天气查询
# 2. CurrencyConverterTool - 货币转换
# 3. SentimentAnalysisTool - 情感分析

for plugin in EXAMPLE_PLUGINS:
    manager.registry.register(plugin)
    plugin.enable()
```

详细文档: [docs/TOOL_PLUGIN_SYSTEM.md](docs/TOOL_PLUGIN_SYSTEM.md)

---

## 📊 与其他框架对比

### vs LangGraph

| 特性 | LangGraph | Loom Agent |
|------|-----------|------------|
| **核心抽象** | 图（节点+边） | 递归状态机 |
| **代码量** | 需要显式连线 | 钩子注入，零连线 |
| **持久化** | 静态快照 | 事件溯源 |
| **策略升级** | ❌ | ✅ 重放时注入新策略 |
| **HITL** | interrupt_before | LifecycleHooks |
| **上下文调试** | ❌ | ✅ ContextDebugger |
| **适合场景** | 确定性工作流 | 探索性复杂任务 |

### vs AutoGen

| 特性 | AutoGen | Loom Agent |
|------|---------|------------|
| **多代理** | ✅ 对话式 | ✅ Crew 系统 |
| **编排模式** | 基础 | 4 种 (Sequential/Parallel/Conditional/Hierarchical) |
| **持久化** | ❌ | ✅ Event Sourcing |
| **工具编排** | 基础 | 智能并行 + 依赖检测 |
| **配置复杂度** | 高 | 低 |

### vs CrewAI

| 特性 | CrewAI | Loom Agent |
|------|--------|------------|
| **角色系统** | ✅ | ✅ 更灵活 |
| **任务编排** | ✅ | ✅ + 条件逻辑 |
| **崩溃恢复** | ❌ | ✅ |
| **事件溯源** | ❌ | ✅ |
| **上下文管理** | 基础 | ContextFabric + Debugger |

**总结**: Loom Agent = **所有框架的优势** + **独家事件溯源能力**

---

## 📚 文档

### 核心文档
- 📖 [完整用户指南](docs/USAGE_GUIDE_V0_0_5.md)
- 🏗️ [架构设计](docs/ARCHITECTURE_REFACTOR.md)
- 🔧 [API 参考](docs/user/api-reference.md)

### 系统文档
- 🤝 [Crew 多代理系统](docs/CREW_SYSTEM.md)
- 🔌 [工具插件系统](docs/TOOL_PLUGIN_SYSTEM.md)
- 📊 [Context Fabric 详解](docs/CONTEXT_FABRIC.md)

### 发布文档
- ✅ [v0.0.8 集成完成](docs/INTEGRATION_COMPLETE.md)
- 📊 [Phase 5-8 总结](docs/PHASE_5-8_IMPLEMENTATION_SUMMARY.md)
- 🚀 [里程碑规划](docs/v0.1.0_MILESTONES.md)

---

## 🎯 使用场景

### 1. 生产环境 Agent

```python
# 企业级可靠性 Agent
production_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=production_tools,

    # 可靠性特性
    enable_persistence=True,
    journal_path=Path("/var/log/loom"),

    # 安全特性
    hooks=[
        HITLHook(dangerous_tools=["delete", "execute"]),
        LoggingHook(),
        MetricsHook()
    ],

    # 性能配置
    max_iterations=100,
    max_context_tokens=8000
)

# 崩溃后自动恢复
if crashed:
    async for event in production_agent.resume(thread_id=session_id):
        handle_event(event)
```

### 2. 代码审查工作流

```python
from loom.crew import Crew, Role, Task

# 创建代码审查团队
roles = [
    Role(name="architect", goal="Analyze structure", ...),
    Role(name="security", goal="Find vulnerabilities", ...),
    Role(name="writer", goal="Document findings", ...)
]

crew = Crew(roles=roles, llm=llm)

# 顺序审查流程
tasks = [
    Task(id="structure", assigned_role="architect", ...),
    Task(id="security", assigned_role="security", dependencies=["structure"]),
    Task(id="document", assigned_role="writer", dependencies=["security"])
]

plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)
```

### 3. 研究和分析

```python
# 启用完整调试
debugger = ContextDebugger(enable_auto_export=True)

research_agent = agent(
    llm=llm,
    tools=research_tools,
    context_debugger=debugger,
    enable_persistence=True
)

# 执行长期研究任务
await research_agent.run("Research quantum computing applications")

# 分析执行过程
print(debugger.generate_summary())
print(debugger.explain_iteration(5))
```

### 4. 多代理协作项目

```python
# 创建开发团队
team = Crew(
    roles=[
        Role(name="pm", goal="Plan and coordinate", delegation=True),
        Role(name="researcher", goal="Research solutions"),
        Role(name="developer", goal="Implement features"),
        Role(name="tester", goal="Test quality")
    ],
    llm=llm
)

# Hierarchical 模式：PM 协调团队
plan = OrchestrationPlan(
    tasks=project_tasks,
    mode=OrchestrationMode.HIERARCHICAL
)

results = await team.kickoff(plan)
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/crew/ -v
pytest tests/unit/plugins/ -v

# 运行覆盖率测试
pytest --cov=loom --cov-report=html

# 运行示例
python examples/integration_example.py
python examples/crew_demo.py
python examples/plugin_demo.py
```

**测试状态**:
- ✅ Crew 系统: 106 个测试，100% 通过
- ✅ 插件系统: 35 个测试，100% 通过
- ✅ 核心功能: 50+ 个测试通过

---

## 🗺️ Roadmap

### ✅ v0.0.8 (已完成)
- ✅ ExecutionFrame（执行栈帧）
- ✅ EventJournal（事件溯源）
- ✅ LifecycleHooks（9 个钩子点）
- ✅ HITL（Human-in-the-Loop）
- ✅ ContextDebugger（上下文调试）
- ✅ Crash Recovery（崩溃恢复）
- ✅ StateReconstructor（状态重建）

### ✅ v0.1.0 (已完成)
- ✅ Crew 多代理协作系统
  - ✅ 角色系统（6 个内置角色）
  - ✅ 4 种编排模式（Sequential/Parallel/Conditional/Hierarchical）
  - ✅ Agent 间通信（MessageBus + SharedState）
  - ✅ 委托工具（DelegateTool）
  - ✅ 条件构建器（ConditionBuilder）
  - ✅ 性能监控
- ✅ 工具插件系统
  - ✅ 插件注册表
  - ✅ 动态加载器
  - ✅ 生命周期管理
  - ✅ 3 个示例插件
- ✅ 完整双语文档（中文 + English）

### 🔜 v0.2.0 (计划中)
- 📊 Web UI（实时监控 Dashboard）
- 🎨 增强可视化（执行树、火焰图）
- 🧪 MockLLMWithTools 完善
- 📈 性能基准测试
- 🌐 分布式执行支持
- 💾 多后端存储（PostgreSQL, Redis）

### 🎯 v0.3.0 (目标)
- 🔌 更多插件（LLM, Memory, Storage）
- 🌍 多语言支持
- 📱 移动端适配
- 🔐 企业级安全特性

---

## 💡 最佳实践

### 1. 始终启用持久化（生产环境）

```python
# ✅ 推荐
agent(
    llm=llm,
    tools=tools,
    enable_persistence=True,
    journal_path=Path("./logs"),
    thread_id=session_id
)

# ❌ 不推荐（生产环境）
agent(llm=llm, tools=tools)  # 无持久化
```

### 2. 为危险工具添加 HITL

```python
# ✅ 推荐
hitl = HITLHook(dangerous_tools=["delete_file", "bash", "send_email"])

agent(llm=llm, tools=all_tools, hooks=[hitl])

# ❌ 不推荐
agent(llm=llm, tools=all_tools)  # 无保护
```

### 3. 使用 ContextDebugger 调试上下文问题

```python
# ✅ 推荐
debugger = ContextDebugger(enable_auto_export=True)

agent(llm=llm, tools=tools, context_debugger=debugger)

# 执行后分析
print(debugger.explain_iteration(5))
```

### 4. 合理使用 Crew 编排模式

```python
# ✅ 研究任务 - 并行
OrchestrationMode.PARALLEL

# ✅ 有依赖的流程 - 顺序
OrchestrationMode.SEQUENTIAL

# ✅ 条件分支 - 条件
OrchestrationMode.CONDITIONAL

# ✅ 复杂协调 - 层级
OrchestrationMode.HIERARCHICAL
```

### 5. 监控和日志

```python
# ✅ 推荐 - 添加监控钩子
agent(
    llm=llm,
    tools=tools,
    hooks=[
        LoggingHook(log_file=Path("./agent.log")),
        MetricsHook(),
        HITLHook(...)
    ]
)
```

---

## 🙏 致谢

特别感谢：
- **Claude Code** - tt 递归模式的启发
- **LangGraph** - 图状态机的对比参考
- **React Fiber** - ExecutionFrame 设计灵感
- **Event Sourcing 社区** - 事件溯源最佳实践
- **CrewAI & AutoGen** - 多代理协作的参考
- 早期用户和贡献者

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🔗 链接

- **GitHub**: https://github.com/kongusen/loom-agent
- **PyPI**: https://pypi.org/project/loom-agent/
- **文档**: [docs/](docs/)
- **示例**: [examples/](examples/)
- **Issues**: https://github.com/kongusen/loom-agent/issues

---

<div align="center">

**使用 ❤️ 构建，为可靠的、有状态的 AI Agents**

### 🎬 核心创新

**Event Sourcing** | **Lifecycle Hooks** | **HITL** | **Crash Recovery** | **Context Debugger** | **Crew System** | **Plugin System**

---

### ⭐ 如果 Loom Agent 对您有帮助，请给我们一个星标！

[⭐ Star on GitHub](https://github.com/kongusen/loom-agent)

</div>
