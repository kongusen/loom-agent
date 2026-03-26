# Loom v0.7.0 架构文档

> 基于 Agent 公理系统 v2.2 的 L2 完整 Agent 框架

---

## 目录

1. [架构概览](#架构概览)
2. [核心组件](#核心组件)
3. [执行流程](#执行流程)
4. [使用指南](#使用指南)
5. [高级特性](#高级特性)

---

## 架构概览

### 能力等级

Loom v0.7.0 实现了 **L2 完整**能力：

| 等级 | 名称 | 核心能力 | 状态 |
|------|------|----------|------|
| L0 | 基础 Agent | Context + Memory + Loop | ✅ |
| L1 | 可续存 Agent | 外部持久化 + 状态管理 | ✅ |
| L2 | 受约束 Agent | Scene + 边界 + 约束 | ✅ |
| L3 | 可验证 Agent | Verifier + 事件日志 | 未来 |

### 核心原则

1. **有界感知** - 所有决策在固定窗口内（128k tokens）
2. **显式状态** - 关键状态可序列化和恢复
3. **边界响应** - 触及边界时有明确策略
4. **约束收窄** - 场景组合时约束变得更严格

---

## 核心组件

### 1. Agent 核心

```python
from loom.agent import Agent
from loom.config import AgentConfig

agent = Agent(
    provider=your_llm_provider,
    config=AgentConfig(
        max_steps=10,
        max_tokens=100000,
        stream=True
    )
)
```

**职责**:
- 管理执行循环
- 协调各子系统
- 处理边界条件

### 2. StepExecutor (新增 v0.7.0)

**统一的工具调用执行入口**

```python
# 自动集成，无需手动调用
# 每个工具调用都会经过：
# 1. 资源配额检查
# 2. 约束验证
# 3. 工具执行
# 4. 轨迹记录
# 5. 状态更新
# 6. 输出过滤
```

**解决的问题**: 之前工具调用绕过了约束检查和资源配额

### 3. PartitionManager

**5 分区上下文管理**

```python
# 自动管理 5 个分区
partitions = {
    "system": "基础 prompt",
    "working": "当前任务状态",
    "memory": "L2/L3 检索结果",
    "skill": "激活的技能",
    "history": "对话历史"
}
```

**特性**:
- 自动计算腐烂系数 ρ
- 触发压缩和心跳续写
- 预算管理

### 4. SceneManager

**场景包系统**

```python
from loom.types.scene import ScenePackage

# 定义场景
scene = ScenePackage(
    id="safe_mode",
    tools=["read_file", "search"],
    constraints={
        "network": False,
        "write": False,
        "max_tokens": 1000
    }
)

# 注册和切换
agent.scene_mgr.register(scene)
agent.scene_mgr.switch("safe_mode")
```

**约束收窄** (v0.7.0):
```python
scene1 = ScenePackage(
    id="s1",
    constraints={"network": True, "max_tokens": 1000}
)
scene2 = ScenePackage(
    id="s2",
    constraints={"network": False, "max_tokens": 500}
)

# 组合后约束更严格
combined = scene1 + scene2
# network: False (AND 逻辑)
# max_tokens: 500 (取 min)
```

### 5. BoundaryDetector & BoundaryHandler (新增 v0.7.0)

**边界检测和响应**

```python
# 自动检测 4 类边界
BoundaryType.PHYSICAL    # token/memory 耗尽
BoundaryType.PERMISSION  # 缺少权限
BoundaryType.CAPABILITY  # 超出能力
BoundaryType.TIME        # 超时

# 5 种响应策略
BoundaryResponse.RENEW      # 压缩继续
BoundaryResponse.WAIT       # 等待输入
BoundaryResponse.HANDOFF    # 转交
BoundaryResponse.DECOMPOSE  # 拆解
BoundaryResponse.STOP       # 终止
```

**自定义策略**:
```python
# 修改默认响应策略
agent.boundary_handler.policy[BoundaryType.PHYSICAL] = [
    BoundaryResponse.RENEW,
    BoundaryResponse.STOP
]
```

### 6. WorkingState (新增 v0.7.0)

**预算化的灵活工作状态**

```python
from loom.types.working import WorkingState

# 自动管理，也可手动访问
state = agent.working_state
state.goal = "Complete task"
state.plan = "Step 1, Step 2"
state.next_action = "Execute step 1"

# 自动截断到预算
text = state.to_text(agent.tokenizer)  # 最多 2000 tokens
```

**特性**:
- 固定预算（2000 tokens）
- 推荐 schema（非强制）
- overflow 字段支持自由内容

---

## 执行流程

### 基础执行流程

```python
# 1. 创建 Agent
agent = Agent(provider=llm_provider)

# 2. 运行任务
result = await agent.run("Analyze this data")

# 3. 流式执行
async for event in agent.stream("Process request"):
    if event.type == "text_delta":
        print(event.text, end="")
```

### 完整执行流程 (v0.7.0)

```
用户输入
    ↓
检查边界 (BoundaryDetector)
    ↓ (如果触发边界)
边界响应 (BoundaryHandler)
    ↓ (renew/stop/handoff)
更新分区 (PartitionManager)
    ↓
构建消息 (包含 WorkingState)
    ↓
LLM 推理
    ↓
工具调用?
    ↓ (是)
StepExecutor 统一执行
    ├─ 资源配额检查
    ├─ 约束验证 (Scene)
    ├─ 执行工具
    ├─ 记录轨迹
    ├─ 更新 WorkingState
    └─ 过滤输出
    ↓
返回结果
```

---

## 使用指南

### 快速开始

```python
from loom.agent import Agent
from loom.providers.llm.anthropic import AnthropicProvider

# 1. 创建 Provider
provider = AnthropicProvider(api_key="your-key")

# 2. 创建 Agent
agent = Agent(provider=provider)

# 3. 运行
result = await agent.run("Hello, what can you do?")
print(result.content)
```

### 使用场景约束

```python
from loom.types.scene import ScenePackage

# 定义只读场景
readonly_scene = ScenePackage(
    id="readonly",
    tools=["read_file", "search", "list_files"],
    constraints={
        "write": False,
        "network": False,
        "bash": False
    }
)

agent.scene_mgr.register(readonly_scene)
agent.scene_mgr.switch("readonly")

# 现在 Agent 只能读取，不能写入
result = await agent.run("Read config.json")
```

### 监控边界

```python
# 检查当前边界状态
boundary = agent.boundary_detector.detect()
if boundary:
    boundary_type, context = boundary
    print(f"触发边界: {boundary_type}, 原因: {context}")

# 检查上下文压力
decay = agent.partition_mgr.compute_decay()
print(f"腐烂系数 ρ: {decay:.2f}")
if decay > 0.85:
    print("需要心跳续写")
elif decay > 0.60:
    print("需要压缩")
```

### 访问工作状态

```python
# 查看当前工作状态
print(f"目标: {agent.working_state.goal}")
print(f"计划: {agent.working_state.plan}")
print(f"下一步: {agent.working_state.next_action}")

# 手动更新
agent.working_state.blockers = ["等待 API 响应"]
```

---

*继续下一部分...*

## 高级特性

### 1. 记忆管理

```python
# 三层记忆架构
agent.memory.l1  # 短期记忆（对话历史）
agent.memory.l2  # 中期记忆（会话级）
agent.memory.l3  # 长期记忆（持久化）

# 写入长期记忆
from loom.types import MemoryEntry

entry = MemoryEntry(
    content="重要信息",
    importance=0.9,
    tokens=10
)
await agent.memory.l3.store(entry)

# 检索记忆
results = await agent.memory.extract_for("查询", budget=1000)
```

### 2. 技能系统

```python
from loom.types import Skill

# 定义技能
skill = Skill(
    name="code_review",
    description="代码审查专家",
    instructions="仔细检查代码质量、安全性和最佳实践"
)

# 注册技能
agent.skill_mgr.registry.register(skill)

# 激活技能（会占用 skill 分区预算）
agent.skill_mgr.activate("code_review", budget=1000)
```

### 3. 事件监听

```python
# 监听特定事件
agent.on("tool_call", lambda event: print(f"调用工具: {event.name}"))
agent.on("boundary", lambda event: print(f"触发边界: {event.type}"))

# 自定义事件处理
async def on_error(event):
    print(f"错误: {event.error}")
    # 自定义恢复逻辑

agent.on("error", on_error)
```

### 4. 拦截器

```python
from loom.agent.interceptor import InterceptorChain

# 添加消息拦截器
async def log_interceptor(ctx):
    print(f"消息数: {len(ctx.messages)}")
    # 可以修改 ctx.messages

agent.interceptors.add(log_interceptor)
```

---

## 配置参考

### AgentConfig

```python
from loom.config import AgentConfig

config = AgentConfig(
    max_steps=10,           # 最大循环步数
    max_tokens=100000,      # 最大 token 配额
    stream=True,            # 流式输出
    temperature=0.7,        # LLM 温度
    system_prompt="...",    # 系统提示词
)
```

### 资源配额

```python
# 修改资源限制
agent.resource_guard._max_tokens = 50000
agent.resource_guard._max_time = 600  # 秒
```

### 上下文窗口

```python
# 修改窗口大小
agent.partition_mgr.window = 200000  # 200k tokens

# 修改分区预算
agent.partition_mgr.get_available_budget("memory")  # 查询可用预算
```

---

## 最佳实践

### 1. 场景设计

```python
# 为不同任务定义专门场景
research_scene = ScenePackage(
    id="research",
    tools=["web_search", "read_file", "summarize"],
    constraints={"write": False}
)

coding_scene = ScenePackage(
    id="coding",
    tools=["read_file", "write_file", "bash"],
    constraints={"network": False}
)

# 组合场景
safe_coding = research_scene + coding_scene
# 结果：只能读写文件，不能联网
```

### 2. 边界处理

```python
# 自定义边界响应
async def custom_boundary_handler(boundary_type, context):
    if boundary_type == BoundaryType.PHYSICAL:
        # 先尝试压缩
        await agent._trigger_compression()
        return BoundaryResponse.RENEW
    return BoundaryResponse.STOP

# 替换默认处理器
agent.boundary_handler.handle = custom_boundary_handler
```

### 3. 状态持久化

```python
# 保存 Agent 状态
state = {
    "goal": agent._goal,
    "working": agent.working_state,
    "execution_trace": agent._execution_trace
}

# 恢复状态
agent._goal = state["goal"]
agent.working_state = state["working"]
agent._execution_trace = state["execution_trace"]
```

---

## 故障排查

### 约束不生效

**问题**: 工具调用没有被约束拦截

**检查**:
```python
# 1. 确认场景已切换
print(agent.scene_mgr.current)

# 2. 确认约束已设置
print(agent.scene_mgr.current.constraints)

# 3. 检查 StepExecutor 是否被调用
# 查看日志中是否有 "Constraint violation" 消息
```

### 边界未触发

**问题**: 上下文满了但没有触发边界

**检查**:
```python
# 1. 检查腐烂系数
print(f"ρ = {agent.partition_mgr.compute_decay()}")

# 2. 手动检测边界
boundary = agent.boundary_detector.detect()
print(boundary)

# 3. 确认阈值
# 边界触发条件: ρ > 0.9
```

### 内存占用过高

**解决方案**:
```python
# 1. 减小窗口
agent.partition_mgr.window = 64000

# 2. 更频繁压缩
# 修改 should_compress() 阈值

# 3. 清理历史
agent.memory.l1._messages.clear()
```

---

## 版本迁移

### 从 v0.6.6 升级到 v0.7.0

**不兼容变更**:
1. `ToolRegistry.execute()` 现在需要 `constraint_validator` 参数
2. `ScenePackage.__add__` 约束合并逻辑改变
3. `Agent.__init__` 移除了 `context` 参数

**迁移步骤**:
```python
# v0.6.6
agent = Agent(provider, context=my_context)

# v0.7.0
agent = Agent(provider)
# context 功能已集成到 PartitionManager
```

**新增特性**:
- StepExecutor 自动集成
- BoundaryDetector/Handler 自动创建
- WorkingState 自动管理

---

## 参考资料

- [Agent 公理系统 v2.2](./Langchain%20Agent%20Axioms%20v2.2.md)
- [实施路线图](./LOOM_V2.2_ROADMAP.md)
- [版本进度](./PROGRESS.md)

---

*Loom v0.7.0 架构文档 · 完*
