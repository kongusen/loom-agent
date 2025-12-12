# Loom Agent v0.1.1 - Quick Reference Card

**30秒速查** | **立即可用的代码片段** | **复制粘贴即可运行**

---

## 🚀 5秒上手

```python
# 安装
pip install loom-agent

# 最简单的Agent
from loom import agent
my_agent = agent(provider="openai", model="gpt-4")
result = await my_agent.run("Hello!")
```

---

## 📦 核心API签名

### Agent创建

```python
from loom import agent

# 基础版本
agent(provider="openai", model="gpt-4")

# 生产版本
agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool(), BashTool()],           # 工具列表
    system_instructions="You are...",              # 系统提示
    enable_persistence=True,                        # 持久化
    journal_path=Path("./logs"),                   # 日志路径
    thread_id="user-123",                          # 会话ID
    hooks=[HITLHook(dangerous_tools=["bash"])],   # 生命周期钩子
    max_iterations=50,                             # 最大迭代
    max_context_tokens=8000                        # 上下文限制
)
```

### 执行方法

```python
# 方式1: 简单执行（等待最终结果）
result: str = await agent.run("Task")

# 方式2: 流式执行（实时进度）
async for event in agent.execute("Task"):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")
```

---

## 🛠️ 内置工具速查

```python
from loom.builtin.tools import (
    ReadFileTool,      # 读取文件
    WriteFileTool,     # 写入文件
    EditFileTool,      # 编辑文件（按行替换）
    GlobTool,         # 查找文件（支持通配符）
    GrepTool,         # 搜索文件内容
    BashTool,         # 执行shell命令
    WebSearchTool,    # Web搜索（需要API key）
)

# 使用工具
agent(llm=llm, tools=[ReadFileTool(), GlobTool(), GrepTool()])
```

---

## 📊 事件类型速查表（v0.1.1）

### Agent执行事件

```python
AgentEventType.AGENT_START           # Agent开始执行
AgentEventType.AGENT_FINISH          # Agent完成执行
AgentEventType.ITERATION_START       # 新迭代开始
AgentEventType.ERROR                 # 执行错误
```

### LLM事件

```python
AgentEventType.LLM_DELTA            # 流式文本块
AgentEventType.LLM_COMPLETE         # 生成完成
AgentEventType.LLM_TOOL_CALLS       # 工具调用请求
```

### 工具事件

```python
AgentEventType.TOOL_EXECUTION_START # 工具开始执行
AgentEventType.TOOL_RESULT          # 工具执行结果
AgentEventType.TOOL_ERROR           # 工具执行错误
```

### Memory事件（v0.1.1新增）

```python
AgentEventType.MEMORY_ADD_START         # 添加消息开始
AgentEventType.MEMORY_ADD_COMPLETE      # 添加消息完成
AgentEventType.MEMORY_SAVE_START        # 保存到磁盘开始
AgentEventType.MEMORY_SAVE_COMPLETE     # 保存到磁盘完成
AgentEventType.MEMORY_MESSAGES_LOADED   # 消息加载完成
```

### Context事件（v0.1.1新增）

```python
AgentEventType.CONTEXT_ASSEMBLY_START      # 上下文组装开始
AgentEventType.CONTEXT_COMPONENT_INCLUDED  # 组件已包含
AgentEventType.CONTEXT_COMPONENT_TRUNCATED # 组件被截断
AgentEventType.CONTEXT_COMPONENT_EXCLUDED  # 组件被排除
AgentEventType.CONTEXT_ASSEMBLY_COMPLETE   # 上下文组装完成
```

### Compression事件（v0.1.1新增）

```python
AgentEventType.COMPRESSION_START      # 压缩开始
AgentEventType.COMPRESSION_PROGRESS   # 压缩进度（含重试）
AgentEventType.COMPRESSION_FALLBACK   # 降级到滑动窗口
AgentEventType.COMPRESSION_COMPLETE   # 压缩完成
```

### Crew事件

```python
AgentEventType.CREW_KICKOFF_START    # Crew启动
AgentEventType.CREW_TASK_START       # 任务开始
AgentEventType.CREW_TASK_COMPLETE    # 任务完成
AgentEventType.CREW_KICKOFF_COMPLETE # Crew完成
```

---

## 💾 Memory API速查

```python
from loom.builtin.memory import InMemoryMemory, PersistentMemory
from loom.core.types import Message

# In-Memory（会话级）
memory = InMemoryMemory()

# Persistent（持久化）
memory = PersistentMemory(
    persist_dir=".loom",
    session_id="user-123",
    enable_persistence=True,
    auto_backup=True
)

# 添加消息
await memory.add_message(Message(role="user", content="Hello"))

# 流式添加（v0.1.1）
async for event in memory.add_message_stream(msg):
    if event.type == AgentEventType.MEMORY_SAVE_COMPLETE:
        print(f"Saved to {event.metadata['file']}")

# 获取消息
messages = await memory.get_messages(limit=10)  # 最近10条

# 清除消息
await memory.clear()
```

---

## 🎯 Context Assembly速查

```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority

assembler = ContextAssembler(max_tokens=4000)

# 添加组件
assembler.add_component(
    name="system_instructions",
    content="You are...",
    priority=ComponentPriority.CRITICAL,  # 100（永不删除）
    truncatable=False
)

assembler.add_component(
    name="retrieved_docs",
    content=docs,
    priority=ComponentPriority.HIGH,      # 90（高优先级）
    truncatable=True
)

# 组装上下文
context = assembler.assemble()

# 流式组装（v0.1.1）- 查看包含/排除/截断
async for event in assembler.assemble_stream():
    if event.type == AgentEventType.CONTEXT_COMPONENT_EXCLUDED:
        print(f"❌ Excluded: {event.metadata['component_name']}")
```

**Priority Levels**:
- `CRITICAL = 100` - 永不删除
- `HIGH = 90` - 高优先级
- `MEDIUM = 70` - 中优先级
- `LOW = 50` - 低优先级
- `OPTIONAL = 30` - 可选内容

---

## 🗜️ Compression速查

```python
from loom.core.compression_manager import CompressionManager

compressor = CompressionManager(
    llm=llm,
    max_retries=3,              # 最大重试次数
    compression_threshold=0.92, # 92%触发压缩
    target_reduction=0.75       # 目标减少75%
)

# 压缩消息
compressed_msgs, metadata = await compressor.compress(messages)

# 流式压缩（v0.1.1）- 查看重试和降级
async for event in compressor.compress_stream(messages):
    if event.type == AgentEventType.COMPRESSION_PROGRESS:
        if event.metadata['status'] == 'retry':
            print(f"⚠️ Retry {event.metadata['attempt']}")
    elif event.type == AgentEventType.COMPRESSION_FALLBACK:
        print(f"🔄 Fallback: {event.metadata['fallback_method']}")
```

---

## 👥 Crew System速查

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

# 1. 定义角色
roles = [
    Role(name="researcher", goal="Research", tools=["read_file", "web_search"]),
    Role(name="developer", goal="Code", tools=["read_file", "write_file"]),
    Role(name="tester", goal="Test", tools=["bash", "read_file"])
]

# 2. 创建Crew
crew = Crew(roles=roles, llm=llm)

# 3. 定义任务
tasks = [
    Task(id="research", assigned_role="researcher", prompt="Research OAuth"),
    Task(id="implement", assigned_role="developer", dependencies=["research"], prompt="Implement"),
    Task(id="test", assigned_role="tester", dependencies=["implement"], prompt="Test")
]

# 4. 执行
plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)

# 流式执行（v0.1.1）
async for event in crew.kickoff_stream(plan):
    if event.type == AgentEventType.CREW_TASK_START:
        print(f"🚀 {event.metadata['task_id']}")
```

**Orchestration Modes**:
- `SEQUENTIAL` - 顺序执行（尊重依赖）
- `PARALLEL` - 并行执行
- `CONDITIONAL` - 条件执行
- `HIERARCHICAL` - 层级协调

---

## 🪝 Lifecycle Hooks速查

```python
from loom.core.lifecycle_hooks import HITLHook, LoggingHook

# HITL（人在回路中）
hitl = HITLHook(
    dangerous_tools=["bash", "write_file", "delete_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

# 日志Hook
logging_hook = LoggingHook(log_level="DEBUG", log_file=Path("./agent.log"))

# 使用
agent(llm=llm, tools=tools, hooks=[hitl, logging_hook])
```

**Hook Points（执行顺序）**:
1. `before_iteration_start`
2. `before_context_assembly`
3. `after_context_assembly`
4. `before_llm_call`
5. `after_llm_response`
6. `before_tool_execution` ← HITL关键点
7. `after_tool_execution`
8. `before_recursion`
9. `after_iteration_end`

---

## 🐛 常见错误速查

### ToolNotFoundError

```python
# ❌ 错误
agent(llm=llm, tools=[])
await agent.run("Use bash tool")  # Tool 'bash' not found

# ✅ 修复
from loom.builtin.tools import BashTool
agent(llm=llm, tools=[BashTool()])
```

### MaxIterationsExceeded

```python
# ❌ 错误
agent(llm=llm, max_iterations=10)  # 太少
await agent.run("Complex task")  # Exceeded 10 iterations

# ✅ 修复
agent(llm=llm, max_iterations=100)  # 增加限制
```

### TokenLimitExceeded

```python
# ❌ 错误
agent(llm=llm, max_context_tokens=4000)  # 太少
# Context size 12000 exceeds limit 4000

# ✅ 修复
agent(llm=llm, max_context_tokens=16000)  # 增加限制
# 或启用压缩
agent(llm=llm, compressor=CompressionManager(llm=llm))
```

### ThreadIdRequired

```python
# ❌ 错误
agent(llm=llm, enable_persistence=True)  # 缺少thread_id

# ✅ 修复
agent(llm=llm, enable_persistence=True, thread_id="user-123")
```

---

## 🔥 常用代码片段（复制即用）

### 1. 基础Agent

```python
import asyncio
from loom import agent

async def main():
    my_agent = agent(provider="openai", model="gpt-4")
    result = await my_agent.run("Hello!")
    print(result)

asyncio.run(main())
```

### 2. 流式Agent

```python
from loom import agent
from loom.core.events import AgentEventType

async def main():
    my_agent = agent(provider="openai", model="gpt-4")
    
    async for event in my_agent.execute("Explain AI"):
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

asyncio.run(main())
```

### 3. 带工具的Agent

```python
from loom import agent
from loom.builtin.tools import ReadFileTool, GlobTool, GrepTool

code_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[ReadFileTool(), GlobTool(), GrepTool()],
    system_instructions="You are a code analyzer."
)

result = await code_agent.run("Find all TODO comments in *.py files")
```

### 4. 生产级Agent（带HITL）

```python
from pathlib import Path
from loom import agent
from loom.core.lifecycle_hooks import HITLHook
from loom.builtin.tools import WriteFileTool, BashTool

hitl = HITLHook(
    dangerous_tools=["bash", "write_file"],
    ask_user_callback=lambda msg: input(f"⚠️  {msg}\nAllow? (y/n): ") == "y"
)

prod_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[WriteFileTool(), BashTool()],
    enable_persistence=True,
    journal_path=Path("./logs"),
    hooks=[hitl],
    thread_id="user-session-123"
)

result = await prod_agent.run("Create backup.sh script and run it")
```

### 5. 多Agent协作（Crew）

```python
from loom.crew import Crew, Role, Task, OrchestrationPlan, OrchestrationMode

roles = [
    Role(name="researcher", goal="Research", tools=["web_search"]),
    Role(name="writer", goal="Write", tools=["write_file"])
]

crew = Crew(roles=roles, llm=llm)

tasks = [
    Task(id="research", assigned_role="researcher", prompt="Research AI trends"),
    Task(id="write", assigned_role="writer", dependencies=["research"], prompt="Write report")
]

plan = OrchestrationPlan(tasks=tasks, mode=OrchestrationMode.SEQUENTIAL)
results = await crew.kickoff(plan)
```

### 6. Memory持久化

```python
from loom.builtin.memory import PersistentMemory
from loom.core.types import Message

memory = PersistentMemory(
    persist_dir=".loom",
    session_id="user-123",
    enable_persistence=True
)

# 添加消息
await memory.add_message(Message(role="user", content="Hello"))
await memory.add_message(Message(role="assistant", content="Hi!"))

# 获取历史
history = await memory.get_messages()
print(f"Total: {len(history)} messages")

# 查看持久化信息
info = memory.get_persistence_info()
print(f"Saved to: {info['memory_file']}")
print(f"Backups: {len(info['backups'])}")
```

### 7. Context Budget监控

```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.core.events import AgentEventType

assembler = ContextAssembler(max_tokens=4000)

assembler.add_component("system", "You are...", ComponentPriority.CRITICAL, False)
assembler.add_component("docs", large_docs, ComponentPriority.HIGH, True)

async for event in assembler.assemble_stream():
    if event.type == AgentEventType.CONTEXT_COMPONENT_TRUNCATED:
        print(f"✂️  Truncated: {event.metadata['component_name']}")
    elif event.type == AgentEventType.CONTEXT_COMPONENT_EXCLUDED:
        print(f"❌ Excluded: {event.metadata['component_name']}")
    elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
        print(f"📦 Utilization: {event.metadata['utilization']:.1%}")
```

### 8. Crash Recovery

```python
from pathlib import Path
from loom.core import EventJournal

journal = EventJournal(storage_path=Path("./logs"))

# 首次执行
agent1 = agent(
    llm=llm,
    enable_persistence=True,
    event_journal=journal,
    thread_id="session-123"
)

try:
    await agent1.run("Long complex task")
except Exception:
    print("Crashed...")

# 恢复执行
agent2 = agent(
    llm=llm,
    enable_persistence=True,
    event_journal=journal,
    thread_id="session-123"
)

async for event in agent2.executor.resume(thread_id="session-123"):
    if event.type == AgentEventType.AGENT_FINISH:
        print("✅ Recovered and completed!")
```

---

## 🎯 最佳实践检查清单

- [ ] 生产环境启用 `enable_persistence=True`
- [ ] 危险工具添加 `HITLHook`
- [ ] 长任务使用 `execute()` 而非 `run()`
- [ ] 设置唯一 `thread_id` (格式: `user-{id}-{session}`)
- [ ] 启用 `ContextDebugger` 用于复杂任务
- [ ] 配置适当的 `max_iterations` 和 `max_context_tokens`
- [ ] 使用最小必要工具集（安全原则）
- [ ] 编写清晰的 `system_instructions`
- [ ] 测试crash recovery流程
- [ ] 监控token使用和成本

---

## 📚 更多资源

- **完整文档**: `docs/user/user-guide.md`
- **API参考**: `docs/user/api-reference.md`
- **Coding Guide**: `docs/user/coding_agent_guide.md`
- **示例代码**: `examples/`
- **测试用例**: `tests/`

---

**Version**: v0.1.1  
**Last Updated**: 2024-12-12  
**License**: MIT
