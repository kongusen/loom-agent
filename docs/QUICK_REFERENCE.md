# Loom Agent 快速参考卡片

**版本**: 0.0.2 | **更新**: 2025-10-25

---

## 🚀 快速开始（3 行代码）

```python
from loom import Agent
from loom.llm.factory import LLMFactory

llm = LLMFactory.create_openai(api_key="sk-...", model="gpt-4")
agent = Agent(llm=llm)
result = await agent.run("你的任务")
```

---

## 📦 安装

```bash
# 基础安装
pip install loom-agent==0.0.2

# 带 OpenAI 支持
pip install loom-agent[openai]

# 完整安装
pip install loom-agent[all]
```

---

## 🎯 三大核心能力

| 能力 | 一句话说明 | 何时使用 |
|-----|-----------|---------|
| **ContextAssembler** | 智能管理 prompt 上下文 | RAG 系统、长文档、token 优化 |
| **TaskTool** | 启动子代理执行子任务 | 多步骤任务、并行处理 |
| **AgentEvent** | 流式监控执行过程 | 实时 UI、进度追踪 |

---

## 1️⃣ ContextAssembler - 上下文管理

### 基础模板

```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority

# 创建组装器
assembler = ContextAssembler(max_tokens=8000)

# 添加组件（按优先级）
assembler.add_component(
    name="base_instructions",           # 组件名
    content="你是...",                  # 内容
    priority=ComponentPriority.CRITICAL, # 优先级
    truncatable=False                    # 是否可截断
)

assembler.add_component(
    name="rag_docs",
    content=retrieved_docs,
    priority=ComponentPriority.HIGH,
    truncatable=True
)

# 组装 prompt
final_prompt = assembler.assemble()

# 使用组装好的 prompt
agent = Agent(llm=llm, system_instructions=final_prompt)
```

### 优先级速查

```python
ComponentPriority.CRITICAL = 100  # 必须包含（基础指令）
ComponentPriority.HIGH     = 90   # 高优先级（RAG 文档）
ComponentPriority.MEDIUM   = 70   # 中等（工具定义）
ComponentPriority.LOW      = 50   # 低（示例）
ComponentPriority.OPTIONAL = 30   # 可选（提示）
```

### 典型场景

```python
# RAG 问答系统
assembler.add_component("instructions", "...", ComponentPriority.CRITICAL, False)
assembler.add_component("retrieved_docs", docs, ComponentPriority.HIGH, True)
assembler.add_component("examples", examples, ComponentPriority.LOW, True)
```

---

## 2️⃣ TaskTool - 子代理系统

### 基础模板

```python
from loom.builtin.tools import TaskTool
from loom.agents.registry import register_agent_spec
from loom.agents.refs import AgentSpec

# 1. 注册子代理类型
register_agent_spec(
    AgentSpec(
        agent_type="my-specialist",          # 类型名
        system_instructions="你是专家...",   # 系统提示
        tools=["read_file", "grep"],         # 允许的工具
        model_name="gpt-4"                   # 使用的模型
    )
)

# 2. 创建 TaskTool
def agent_factory(max_iterations=20, **kwargs):
    llm = LLMFactory.create_openai(api_key="sk-...", model="gpt-4")
    return Agent(llm=llm, max_iterations=max_iterations, **kwargs)

task_tool = TaskTool(agent_factory=agent_factory)

# 3. 主 agent 使用 TaskTool
main_agent = agent_factory(tools=[task_tool])

# 4. LLM 会自动调用子代理
result = await main_agent.run("""
使用 my-specialist 类型的子代理分析文件 example.py
""")
```

### 常见子代理类型

```python
# 只读分析器
register_agent_spec(
    AgentSpec(
        agent_type="analyzer",
        system_instructions="分析代码质量",
        tools=["read_file", "grep", "glob"],  # 只读工具
        model_name="gpt-3.5-turbo"  # 便宜的模型
    )
)

# 代码编辑器
register_agent_spec(
    AgentSpec(
        agent_type="editor",
        system_instructions="修改代码文件",
        tools=["read_file", "write_file"],  # 读写工具
        model_name="gpt-4"
    )
)

# 数据处理器
register_agent_spec(
    AgentSpec(
        agent_type="data-processor",
        system_instructions="处理数据",
        tools=["read_file", "write_file", "python_repl"],
        model_name="gpt-4"
    )
)
```

### 多步骤流水线

```python
# 注册 3 个专业子代理
register_agent_spec(AgentSpec("data-cleaner", "清洗数据", ["read_file", "write_file", "python_repl"], "gpt-4"))
register_agent_spec(AgentSpec("data-analyzer", "分析数据", ["read_file", "python_repl"], "gpt-4"))
register_agent_spec(AgentSpec("report-writer", "生成报告", ["read_file", "write_file"], "gpt-4"))

# 主协调器
coordinator = agent_factory(tools=[task_tool])

result = await coordinator.run("""
1. 使用 data-cleaner 清洗 raw.csv
2. 使用 data-analyzer 分析 cleaned.csv
3. 使用 report-writer 生成报告
""")
```

---

## 3️⃣ AgentEvent - 流式执行

### 基础模板

```python
from loom.core.events import AgentEventType, EventCollector

# 流式执行
async for event in agent.execute("你的任务"):

    # LLM 输出
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)

    # 工具调用
    elif event.type == AgentEventType.TOOL_EXECUTION_START:
        print(f"\n[工具] {event.tool_call.name}")

    # 工具结果
    elif event.type == AgentEventType.TOOL_RESULT:
        print(f"[完成] {event.tool_result.execution_time_ms:.0f}ms")

    # 完成
    elif event.type == AgentEventType.AGENT_FINISH:
        print("\n✓ 完成")
```

### 事件类型速查

```python
# LLM 相关
LLM_START          # LLM 开始
LLM_DELTA          # LLM 输出一个 token
LLM_COMPLETE       # LLM 完成
LLM_TOOL_CALLS     # LLM 决定调用工具

# 工具相关
TOOL_EXECUTION_START   # 工具开始执行
TOOL_PROGRESS          # 工具执行进度
TOOL_RESULT            # 工具执行结果
TOOL_ERROR             # 工具执行错误

# 阶段相关
PHASE_START        # 阶段开始
PHASE_END          # 阶段结束
ITERATION_START    # 新一轮迭代

# 完成相关
AGENT_FINISH       # Agent 完成
ERROR              # 发生错误
```

### 事件收集和分析

```python
from loom.core.events import EventCollector

collector = EventCollector()

# 收集所有事件
async for event in agent.execute(prompt):
    collector.add(event)
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)

# 分析
print(f"总事件数: {len(collector.events)}")
print(f"LLM 输出: {collector.get_llm_content()}")
print(f"工具数: {len(collector.get_tool_results())}")
print(f"错误数: {len(collector.get_errors())}")
```

### 进度追踪模板

```python
class ProgressTracker:
    def __init__(self):
        self.current_phase = ""
        self.tools_used = []

    async def track(self, agent, prompt):
        async for event in agent.execute(prompt):
            if event.type == AgentEventType.PHASE_START:
                self.current_phase = event.phase
                print(f"[阶段] {event.phase}")

            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                self.tools_used.append(event.tool_call.name)
                print(f"[工具 {len(self.tools_used)}] {event.tool_call.name}")

            elif event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)

            elif event.type == AgentEventType.AGENT_FINISH:
                print(f"\n✓ 完成！使用了 {len(self.tools_used)} 个工具")

# 使用
tracker = ProgressTracker()
await tracker.track(agent, "分析项目代码")
```

---

## 🔥 常见模式速查

### 模式 1：RAG 问答

```python
# 1. 检索文档
docs = vector_store.search(query)

# 2. 组装上下文
assembler = ContextAssembler(max_tokens=8000)
assembler.add_component("instructions", "...", ComponentPriority.CRITICAL, False)
assembler.add_component("docs", format_docs(docs), ComponentPriority.HIGH, True)
prompt = assembler.assemble()

# 3. 流式回答
agent = Agent(llm=llm, system_instructions=prompt)
async for event in agent.execute(query):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="", flush=True)
```

### 模式 2：多步骤任务

```python
# 1. 注册专业子代理
register_agent_spec(AgentSpec("step1", "步骤1专家", ["tool1"], "gpt-4"))
register_agent_spec(AgentSpec("step2", "步骤2专家", ["tool2"], "gpt-4"))

# 2. 创建协调器
coordinator = agent_factory(tools=[TaskTool(agent_factory=agent_factory)])

# 3. 执行流水线
result = await coordinator.run("""
1. 使用 step1 完成第一步
2. 使用 step2 完成第二步
""")
```

### 模式 3：实时进度显示

```python
async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        ui.append_text(event.content)  # 更新 UI

    elif event.type == AgentEventType.TOOL_EXECUTION_START:
        ui.show_progress(f"执行: {event.tool_call.name}")

    elif event.type == AgentEventType.TOOL_RESULT:
        ui.hide_progress()
```

---

## ⚠️ 常见陷阱

### ❌ 不推荐

```python
# 1. 手动拼接 prompt（可能超 token）
prompt = f"{instructions}\n{docs}\n{tools}"

# 2. 给子代理所有权限（不安全）
AgentSpec("unsafe", "...", tools="*", ...)

# 3. 不处理错误
result = await agent.run(prompt)  # 如果出错会抛异常

# 4. 顺序执行（慢）
for file in files:
    result = await analyze(file)
```

### ✅ 推荐

```python
# 1. 使用 ContextAssembler
assembler = ContextAssembler(max_tokens=8000)
assembler.add_component(...)
prompt = assembler.assemble()

# 2. 限制子代理权限
AgentSpec("safe", "...", tools=["read_file", "grep"], ...)

# 3. 处理错误
try:
    result = await agent.run(prompt)
except Exception as e:
    logger.error(f"Agent failed: {e}")

# 4. 并发执行（快）
results = await asyncio.gather(*[analyze(f) for f in files])
```

---

## 📊 成本优化

```python
# 根据任务选择模型
SIMPLE_TASKS = "gpt-3.5-turbo"     # $0.002/1K tokens
COMPLEX_TASKS = "gpt-4"            # $0.03/1K tokens
LONG_CONTEXT = "gpt-4-32k"         # $0.06/1K tokens

# 示例：分级处理
register_agent_spec(AgentSpec("summarizer", "...", tools=[...], model_name="gpt-3.5-turbo"))
register_agent_spec(AgentSpec("analyzer", "...", tools=[...], model_name="gpt-4"))

# 使用 ContextAssembler 减少 token
assembler = ContextAssembler(max_tokens=4000)  # 控制输入大小
```

---

## 🔗 相关文档

| 文档 | 内容 |
|-----|------|
| **PRODUCTION_GUIDE.md** | 完整产品开发指南（必读） |
| **agent_events_guide.md** | AgentEvent 详细文档 |
| **examples/** | 可运行的示例代码 |
| **tests/unit/** | 单元测试（用法参考） |

---

## 💡 快速诊断

**问题**：Token 超限 → 使用 `ContextAssembler` 管理上下文

**问题**：任务太复杂 → 使用 `TaskTool` 分解为子任务

**问题**：需要实时进度 → 使用 `AgentEvent` 流式执行

**问题**：子任务权限过大 → 在 `AgentSpec` 中限制 `tools`

**问题**：成本太高 → 为简单任务使用 `gpt-3.5-turbo`

---

**版本**: Loom Agent 0.0.2
**更新**: 2025-10-25
**完整文档**: `docs/PRODUCTION_GUIDE.md`
