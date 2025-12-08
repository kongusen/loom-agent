# loom-agent 架构重构：从隐式递归到递归状态机

**日期**: 2025-12-08
**版本**: 2.0.0 (Breaking Changes)
**状态**: 架构重构完成，待集成到 AgentExecutor

---

## 🎯 重构目标

将 loom-agent 从**隐式递归框架**进化为**递归状态机（Recursive State Machine, RSM）**，在保持代码简洁性的同时，补齐工程化能力：

✅ 持久化与崩溃恢复
✅ Time Travel 调试
✅ Human-in-the-Loop
✅ 可视化
✅ 上下文治理透明化

**核心战略**: 不模仿 LangGraph 的图结构，而是发挥 loom-agent 的"递归+流式"特性

---

## 📊 loom-agent vs LangGraph 定位对比

| 维度 | LangGraph | loom-agent 2.0 |
|------|-----------|----------------|
| **核心抽象** | 图（StateGraph + 节点） | 递归执行栈（ExecutionFrame） |
| **持久化** | 静态快照（Checkpointing） | 事件溯源（Event Sourcing） |
| **可视化** | 流程图（拓扑结构） | 火焰图（时序+深度） |
| **上下文管理** | 简单字典 | 优先级上下文编织层 |
| **适用场景** | 确定性强的 SOP | 探索性强、逻辑嵌套深的任务 |

---

## 🏗️ 新架构组件

### 1. ExecutionFrame (执行栈帧)
**文件**: `loom/core/execution_frame.py`

#### 设计理念
受 Python 调用栈和 React Fiber 架构启发，将每一层 tt 递归对象化为一个不可变的 Frame。

#### 核心特性
- **不可变状态** (`frozen=True`)
- **父子链接** (`parent_frame_id`)
- **完整快照** (messages, context, LLM response, tool results)
- **递归控制字段** (继承自原 `TurnState`)

#### 关键方法
```python
# 创建初始 Frame
frame0 = ExecutionFrame.initial(
    prompt="Search Python docs",
    max_iterations=10
)

# 不可变更新
frame1 = frame0.with_llm_response(
    response="I'll search for Python documentation",
    tool_calls=[ToolCall(name="search", args={"query": "Python"})]
)

# 递归到下一层
frame2 = frame1.next_frame(new_messages=updated_messages)

# 序列化为 checkpoint
checkpoint = frame2.to_checkpoint()
```

#### 对比
| | 旧版 TurnState | 新版 ExecutionFrame |
|-|---------------|-------------------|
| **状态完整性** | 只有递归控制字段 | 完整执行状态（messages, context, tools） |
| **持久化** | 不支持 | `to_checkpoint()` / `from_checkpoint()` |
| **父子关系** | 有 parent_turn_id | 完整的栈帧树结构 |
| **执行阶段** | 无 | `ExecutionPhase` 枚举 |

---

### 2. EventJournal (事件日志)
**文件**: `loom/core/event_journal.py`

#### 设计理念
Append-only 事件日志，记录所有执行事件，实现 Event Sourcing。

#### 核心特性
- **JSON Lines 格式** (简单、流式友好)
- **批量写入** (性能优化，默认 100 events/batch)
- **异步 I/O** (非阻塞)
- **按 thread_id 隔离** (多对话支持)

#### 关键方法
```python
# 创建日志
journal = EventJournal(storage_path=Path("./logs"))
await journal.start()

# 记录事件
async for event in agent.execute(prompt):
    await journal.append(event, thread_id="user-123")

# 重放事件
events = await journal.replay(thread_id="user-123")

# 查询特定类型
llm_events = await journal.replay(
    thread_id="user-123",
    event_types=[AgentEventType.LLM_DELTA, AgentEventType.LLM_COMPLETE]
)
```

#### 相比 LangGraph Checkpointing 的优势
```python
# LangGraph: 静态快照
snapshot = {"state": {...}, "values": {...}}  # 固定状态

# loom-agent: 事件流
events = [Event1, Event2, Event3, ...]

# 🌟 可以用新策略重放！
new_context = reconstruct_with_new_compression(events, compression_v2)
# LangGraph 做不到这一点！
```

---

### 3. StateReconstructor (状态重建器)
**文件**: `loom/core/state_reconstructor.py`

#### 设计理念
从事件流重建 ExecutionFrame，实现"时间旅行"和策略升级。

#### 核心特性
- **事件重放** (幂等重建)
- **时间旅行** (重建到任意迭代)
- **策略注入** (用新策略重放旧事件)
- **验证机制** (检测不一致)

#### 关键方法
```python
# 基本重建
reconstructor = StateReconstructor()
frame, metadata = await reconstructor.reconstruct(events)

print(f"Reconstructed {metadata.total_events} events")
print(f"Warnings: {metadata.warnings}")
print(frame.summary())

# 时间旅行：回到第 3 次迭代
frame, _ = await reconstructor.reconstruct_at_iteration(events, target_iteration=3)

# 策略升级：用新压缩算法重放
frame, _ = await reconstructor.reconstruct_with_new_strategy(
    events,
    compression_strategy=CompressionManagerV2()
)
```

#### 杀手级特性
```python
# 原始执行用的是 compression v1
original_execution(events, compression_v1)

# 系统崩溃，重启时已经升级到 v2
frame = reconstruct_with_strategy(events, compression_v2)

# 重建的状态使用 v2 压缩！
# 这是 LangGraph 的静态快照无法实现的
```

---

### 4. LifecycleHook (生命周期钩子)
**文件**: `loom/core/lifecycle_hooks.py`

#### 设计理念
通过钩子而非显式连线实现控制流，保持代码的简洁性。

#### 核心特性
- **Protocol 接口** (可选实现)
- **9 个钩子点** (覆盖 tt 递归的所有关键阶段)
- **中断支持** (`InterruptException` for HITL)
- **钩子链** (`HookManager`)

#### 钩子执行顺序
```
1. before_iteration_start(frame)
2. before_context_assembly(frame)
3. after_context_assembly(frame, context)
4. before_llm_call(frame, messages)
5. after_llm_response(frame, response, tool_calls)
6. before_tool_execution(frame, tool_call)  ← HITL
7. after_tool_execution(frame, tool_result)
8. before_recursion(frame, next_frame)
9. after_iteration_end(frame)
```

#### 使用示例
```python
# 定义 HITL 钩子
class DangerousToolHook:
    async def before_tool_execution(self, frame, tool_call):
        if tool_call["name"] in ["delete_file", "send_email"]:
            confirmed = await ask_user(f"Allow {tool_call['name']}?")
            if not confirmed:
                raise InterruptException("User rejected")
        return tool_call

# 应用钩子
agent = agent(
    llm=llm,
    tools=tools,
    hooks=[DangerousToolHook(), LoggingHook()]
)
```

#### 对比 LangGraph
```python
# LangGraph: 显式连线
graph.add_conditional_edges("node", router_function)

# loom-agent: 钩子注入
agent.use_hook(MyHook())  # 更简洁、更 Pythonic
```

---

### 5. ContextDebugger (上下文调试器)
**文件**: `loom/core/context_debugger.py`

#### 设计理念
让上下文管理决策透明化，回答"为什么 LLM 忘记了XXX"。

#### 核心特性
- **决策记录** (`ComponentDecision`)
- **迭代报告** (哪些组件被包含/截断/排除)
- **组件追踪** (跨迭代追踪组件状态)
- **导出分析** (JSON Lines 格式)

#### 关键方法
```python
debugger = ContextDebugger()

# 记录决策（从 frame）
debugger.record_from_frame(frame)

# 解释某次迭代
print(debugger.explain_iteration(5))
# 输出：
# 📊 Context Assembly Report (Iteration 5)
# Token Budget: 7500/8000 (93.8%)
#
# ✅ Included Components:
#   - system_instructions (500 tokens, priority=100)
#   - rag_docs (2000 tokens, priority=90, truncated from 3000)
#
# ❌ Excluded Components:
#   - file_content.py (2500 tokens, priority=70)
#     Reason: Token limit exceeded

# 追踪组件
print(debugger.explain_component("file_content.py"))
# 📦 Component Timeline: file_content.py
# ✅ Iteration 0: INCLUDED - 2500 tokens, priority=70
# ✂️ Iteration 3: TRUNCATED - 1000 tokens, priority=70 (from 2500)
# ❌ Iteration 5: EXCLUDED
#    Reason: Token limit exceeded, lower priority than RAG docs
```

#### loom-agent 的独特优势
这是 LangGraph 完全没有的能力：
- LangGraph: `State` 只是个字典，无法解释"为什么"
- loom-agent: **Context Fabric** 提供完整的决策追溯

---

### 6. ExecutionVisualizer (执行可视化)
**文件**: `loom/visualization/execution_visualizer.py`

#### 设计理念
火焰图/时序图更适合展示递归执行，而非流程图。

#### 核心特性
- **Timeline 模式** (火焰图式，按深度和时间展示)
- **Tree 模式** (递归树结构)
- **Summary 模式** (统计汇总)
- **实时更新** (可选)

#### 使用示例
```python
from loom.visualization import ExecutionVisualizer

# 从事件创建
viz = ExecutionVisualizer()
events = await journal.replay(thread_id="user-123")
viz.visualize_events(events)

# 渲染
viz.render(mode="timeline")
```

#### Timeline 输出示例
```
Execution Timeline
════════════════════════════════════════════════════════════
Depth 0 │ ████ Context ████ LLM ██████████ Tool: search █████
Depth 1 │           ████ Context ████ LLM ██████ Tool: analyze
Depth 2 │                     ████ Context ████ LLM ████ FINISH
════════════════════════════════════════════════════════════
        0s        2s        4s        6s        8s       10s

Legend:
🟦 Context Assembly  🟪 LLM Call  🟧 Tool Execution  🟩 Complete
```

#### 对比 LangGraph
- LangGraph: 流程图（拓扑结构），适合 DAG
- loom-agent: 火焰图（时序+深度），适合递归

---

## 🔄 架构流程图

### 新架构执行流程

```
用户请求
  ↓
[1] 创建 ExecutionFrame.initial()
  ↓
[2] 启动 EventJournal
  ↓
┌─ tt 递归循环 ────────────────────────┐
│                                      │
│ [Hook] before_iteration_start        │
│   ↓                                  │
│ [Phase 1] Context Assembly           │
│   - [Hook] before_context_assembly   │
│   - ContextAssembler.assemble()      │
│   - [ContextDebugger] 记录决策       │
│   - [Hook] after_context_assembly    │
│   - frame = frame.with_context()     │
│   ↓                                  │
│ [Phase 2] LLM Call                   │
│   - [Hook] before_llm_call           │
│   - LLM.stream()                     │
│   - [EventJournal] 记录 LLM_DELTA    │
│   - [Hook] after_llm_response        │
│   - frame = frame.with_llm_response()│
│   ↓                                  │
│ [Phase 3] Decision                   │
│   - 检查是否有 tool_calls            │
│   ↓                                  │
│ [Phase 4] Tool Execution             │
│   - for each tool_call:              │
│     - [Hook] before_tool_execution ← HITL
│     - [EventJournal] 记录 TOOL_RESULT│
│     - [Hook] after_tool_execution    │
│   - frame = frame.with_tool_results()│
│   ↓                                  │
│ [Phase 5] Recursion Decision         │
│   - if has_tool_calls:               │
│     - next_frame = frame.next_frame()│
│     - [Hook] before_recursion        │
│     - [EventJournal] 保存 checkpoint │
│     - 递归调用 tt(next_frame)  ← 尾递归
│   - else:                            │
│     - AGENT_FINISH                   │
│   ↓                                  │
│ [Hook] after_iteration_end           │
│                                      │
└──────────────────────────────────────┘
  ↓
[EventJournal] flush()
  ↓
完成
```

### 崩溃恢复流程

```
系统崩溃 ☠️
  ↓
重启应用
  ↓
[1] EventJournal.replay(thread_id)
  ↓
[2] StateReconstructor.reconstruct(events)
  ↓
[3] 重建 ExecutionFrame
  ↓
[4] agent.execute(None, initial_frame=frame)  ← 从断点继续！
  ↓
恢复执行 ✅
```

### Time Travel 调试流程

```
用户发现问题："为什么第 5 次迭代 LLM 忘记了文件内容？"
  ↓
[1] journal.replay(thread_id)
  ↓
[2] reconstructor.reconstruct_at_iteration(events, target_iteration=5)
  ↓
[3] 获取第 5 次迭代的 ExecutionFrame
  ↓
[4] debugger.explain_iteration(5)
  ↓
输出：
  ❌ Excluded Components:
    - file_content.py (2500 tokens, priority=70)
      Reason: Token limit exceeded, RAG docs (priority=90) took priority
  ↓
问题根因找到！ 🎯
```

---

## 📦 文件结构

```
loom-agent/
├── loom/
│   ├── core/
│   │   ├── execution_frame.py         # 🆕 执行栈帧
│   │   ├── event_journal.py           # 🆕 事件日志
│   │   ├── state_reconstructor.py     # 🆕 状态重建器
│   │   ├── lifecycle_hooks.py         # 🆕 生命周期钩子
│   │   ├── context_debugger.py        # 🆕 上下文调试器
│   │   ├── agent_executor.py          # 🔄 待重构（集成新架构）
│   │   ├── turn_state.py              # ⚠️  已被 ExecutionFrame 替代
│   │   ├── execution_context.py       # 保留（共享配置）
│   │   ├── events.py                  # 保留（事件定义）
│   │   ├── context_assembly.py        # 保留（核心优势）
│   │   ├── compression_manager.py     # 保留（核心优势）
│   │   └── ...
│   │
│   ├── visualization/
│   │   ├── __init__.py                # 🆕
│   │   └── execution_visualizer.py    # 🆕 CLI 可视化
│   │
│   └── ...
│
└── docs/
    └── ARCHITECTURE_REFACTOR.md       # 🆕 本文档
```

---

## 🚀 使用示例

### 示例 1: 基本使用（带持久化）

```python
from pathlib import Path
from loom import agent
from loom.core import EventJournal, ExecutionFrame

# 创建 agent（启用持久化）
my_agent = agent(
    llm=OpenAILLM(model="gpt-4"),
    tools={"search": search_tool()},
    enable_persistence=True,
    journal_path=Path("./logs")
)

# 执行
async with EventJournalContext(Path("./logs")) as journal:
    async for event in my_agent.execute(
        prompt="Search Python documentation",
        thread_id="user-123"
    ):
        await journal.append(event, thread_id="user-123")

        if event.type == AgentEventType.AGENT_FINISH:
            print(f"✅ {event.content}")
```

### 示例 2: 崩溃恢复

```python
from loom.core import EventJournal, StateReconstructor

# 系统重启后
journal = EventJournal(Path("./logs"))

# 获取最后的执行事件
events = await journal.replay(thread_id="user-123")

# 重建状态
reconstructor = StateReconstructor()
frame, metadata = await reconstructor.reconstruct(events)

print(f"✅ Reconstructed from {metadata.total_events} events")
print(f"Last iteration: {frame.depth}")

# 继续执行
async for event in my_agent.execute(
    prompt=None,  # 从断点继续
    initial_frame=frame,
    thread_id="user-123"
):
    print(event)
```

### 示例 3: HITL (Human-in-the-Loop)

```python
from loom.core.lifecycle_hooks import HITLHook

# 定义危险操作
dangerous_tools = ["delete_file", "send_email", "execute_shell"]

# 创建 HITL 钩子
hitl_hook = HITLHook(
    dangerous_tools=dangerous_tools,
    ask_user_callback=lambda msg: input(f"{msg} (y/n): ").lower() == "y"
)

# 使用
my_agent = agent(
    llm=llm,
    tools=tools,
    hooks=[hitl_hook]
)

# 执行时会自动在危险操作前暂停
async for event in my_agent.execute("Delete old log files"):
    if event.type == AgentEventType.EXECUTION_INTERRUPTED:
        # 等待用户确认
        print(f"⏸️  Waiting for user: {event.metadata['reason']}")
```

### 示例 4: 上下文调试

```python
from loom.core import ContextDebugger

debugger = ContextDebugger(enable_auto_export=True)

my_agent = agent(
    llm=llm,
    tools=tools,
    context_debugger=debugger
)

# 执行
await my_agent.run("Complex task with long context")

# 分析
print(debugger.generate_summary())

# 追踪特定组件
print(debugger.explain_component("file_content.py"))

# 解释特定迭代
print(debugger.explain_iteration(5))
```

### 示例 5: 可视化

```python
from loom.visualization import visualize_execution_from_events

# 获取事件
events = await journal.replay(thread_id="user-123")

# 时序图
visualize_execution_from_events(events, mode="timeline")

# 树形图
visualize_execution_from_events(events, mode="tree")

# 统计摘要
visualize_execution_from_events(events, mode="summary")
```

---

## 🔧 下一步：集成到 AgentExecutor

目前所有新组件已实现，但尚未集成到 `AgentExecutor.tt()` 方法中。

### 集成清单

- [ ] 重构 `AgentExecutor.__init__()` 接受新参数
  - `hooks: List[LifecycleHook]`
  - `event_journal: Optional[EventJournal]`
  - `context_debugger: Optional[ContextDebugger]`

- [ ] 重构 `AgentExecutor.tt()` 使用 `ExecutionFrame` 而非 `TurnState`

- [ ] 在各个 Phase 插入 Hook 调用点
  - Phase 0: `before_iteration_start`
  - Phase 1: `before/after_context_assembly`
  - Phase 2: `before_llm_call`, `after_llm_response`
  - Phase 4: `before/after_tool_execution`
  - Phase 5: `before_recursion`

- [ ] 集成 `EventJournal`
  - 所有事件都通过 `journal.append()` 记录

- [ ] 集成 `ContextDebugger`
  - 在 Context Assembly 后调用 `debugger.record_from_frame()`

- [ ] 添加崩溃恢复入口
  - `agent.resume(thread_id: str)` 方法

- [ ] 更新公共 API
  - `agent()` 工厂函数支持新参数
  - 添加 `agent.visualize()` 方法

---

## 🎁 核心优势总结

### 相比旧版 loom-agent

| 能力 | 旧版 | 新版 2.0 |
|------|------|---------|
| 持久化 | ❌ | ✅ Event Sourcing |
| 崩溃恢复 | ❌ | ✅ 从事件流重建 |
| Time Travel | ❌ | ✅ 任意时间点重建 |
| HITL | 🟡 权限回调 | ✅ 优雅的钩子中断 |
| 可视化 | ❌ | ✅ Timeline + Tree + Summary |
| 上下文调试 | ❌ | ✅ 完整决策追溯 |
| 策略升级 | ❌ | ✅ 重放时注入新策略 |

### 相比 LangGraph

| 能力 | LangGraph | loom-agent 2.0 | 谁更强 |
|------|-----------|----------------|--------|
| 持久化 | 静态快照 | 事件溯源 | 🟢 loom (可重新计算) |
| 可视化 | 流程图 | 火焰图 | 🟡 各有优势 |
| HITL | interrupt_before | Lifecycle Hooks | 🟢 loom (更灵活) |
| 上下文管理 | 简单字典 | Context Fabric | 🟢 loom (独有) |
| 显式工作流 | ✅ 图结构 | ❌ 隐式递归 | 🟠 LangGraph |
| 代码简洁性 | 🟡 需要连线 | ✅ 简洁递归 | 🟢 loom |

**结论**: loom-agent 2.0 在保持代码简洁的同时，补齐了工程化能力，形成差异化竞争力！

---

## 📝 API 变更（Breaking Changes）

### 1. `TurnState` → `ExecutionFrame`

```python
# 旧版
from loom.core.turn_state import TurnState
state = TurnState.initial(max_iterations=10)
next_state = state.next_turn()

# 新版
from loom.core.execution_frame import ExecutionFrame
frame = ExecutionFrame.initial(prompt="...", max_iterations=10)
next_frame = frame.next_frame(new_messages=[...])
```

### 2. Agent 创建（新参数）

```python
# 旧版
agent = agent(llm=llm, tools=tools, max_iterations=50)

# 新版
agent = agent(
    llm=llm,
    tools=tools,
    max_iterations=50,
    hooks=[HITLHook(), LoggingHook()],        # 🆕
    enable_persistence=True,                   # 🆕
    journal_path=Path("./logs"),               # 🆕
    context_debugger=ContextDebugger()         # 🆕
)
```

### 3. 事件处理

```python
# 旧版：仅消费事件
async for event in agent.execute(prompt):
    print(event.content)

# 新版：可选记录到 journal
async with EventJournalContext(Path("./logs")) as journal:
    async for event in agent.execute(prompt, thread_id="user-123"):
        await journal.append(event, thread_id="user-123")
        print(event.content)
```

---

## 🎯 结论

**loom-agent 2.0 成功实现了差异化进化**：

✅ 保持了简洁的递归编程模型
✅ 补齐了持久化、调试、可视化能力
✅ 强化了核心优势（上下文治理）
✅ 提供了 LangGraph 无法实现的特性（策略升级）

**下一步**：集成到 `AgentExecutor`，完成架构演进！

---

**文档版本**: 1.0
**作者**: Claude Sonnet 4.5
**日期**: 2025-12-08
