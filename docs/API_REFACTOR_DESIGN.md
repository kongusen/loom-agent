# Loom Agent API 重构设计文档

**版本**: v0.5.0
**日期**: 2026-02-02
**状态**: 设计阶段
**不向后兼容**: 是

---

## 一、设计原则

### 1.1 核心原则

1. **驼峰命名法 (camelCase)**
   - 所有新 API 使用驼峰命名
   - 替代下划线命名 (snake_case)
   - 保持 API 风格一致

2. **显式传入全局组件**
   - 用户显式创建和管理全局组件
   - 避免隐式的全局状态
   - 支持多 Agent 共享组件

3. **渐进式披露 (Progressive Disclosure)**
   - 简单用法只需最少参数
   - 高级用法支持深度定制
   - 合理的默认值

4. **不向后兼容**
   - 彻底移除废弃代码
   - 保持框架简洁清晰
   - 解决历史技术债务

### 1.2 设计目标

- **易学习**: 新手可以快速上手
- **易使用**: 常见场景代码简洁
- **易扩展**: 高级用户可以深度定制
- **易维护**: 代码结构清晰，职责明确

---

## 二、核心 API 设计

### 2.1 Agent 创建

**核心方法**: `Agent.create()` - 直接创建 Agent 实例

#### 简单用法

```python
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider

# 创建 LLM
llm = OpenAIProvider(apiKey="...")

# 创建 Agent - 只需要 LLM
agent = Agent.create(llm)

# 执行任务
result = await agent.run("帮我分析这段代码")
```

#### 常用配置

```python
agent = Agent.create(
    llm=llm,
    systemPrompt="你是一个专业的 Python 开发助手",
    nodeId="python-assistant",
    maxIterations=20
)
```

#### 高级配置 - 显式传入全局组件

```python
from loom.events import EventBus

# 创建全局组件
eventBus = EventBus()

# 创建多个 Agent 共享同一个 EventBus
agent1 = Agent.create(
    llm=llm,
    systemPrompt="Agent 1",
    eventBus=eventBus
)

agent2 = Agent.create(
    llm=llm,
    systemPrompt="Agent 2",
    eventBus=eventBus
)

# 两个 Agent 可以通过 EventBus 通信
```

---

## 三、工具和 Skill 配置

### 3.1 简单配置 - 通过参数

```python
# 配置工具
agent = Agent.create(
    llm=llm,
    tools=[
        {"type": "function", "function": {...}},
        {"type": "function", "function": {...}}
    ]
)

# 配置 Skills
agent = Agent.create(
    llm=llm,
    skills=["python-dev", "testing", "database-design"]
)

# 同时配置工具和 Skills
agent = Agent.create(
    llm=llm,
    tools=[...],
    skills=["python-dev"]
)
```

### 3.2 高级配置 - 使用 CapabilityRegistry

```python
from loom.capabilities import CapabilityRegistry

# 创建并配置 CapabilityRegistry
capabilities = CapabilityRegistry()

# 注册自定义工具
capabilities.registerTool(customTool)

# 注册自定义 Skill
capabilities.registerSkill("advanced-skill")

# 传入 Agent
agent = Agent.create(
    llm=llm,
    capabilities=capabilities
)
```

**内部实现逻辑**：
- 如果传入 `capabilities`，直接使用
- 否则，Agent 内部创建 CapabilityRegistry，并注册 `tools` 和 `skills`

---

## 四、需要移除的废弃代码

### 4.1 废弃的 API 类

| 文件 | 类/函数 | 状态 | 替代方案 |
|------|---------|------|----------|
| `loom/api/app.py` | `LoomApp` | 已标记废弃 0.4.7 | `Agent.create()` |
| `loom/api/models.py` | `AgentConfig` | 已标记废弃 0.4.7 | `Agent.create()` 参数 |
| `loom/api/models.py` | `MemoryConfig` | 已标记废弃 0.4.7 | `memoryConfig` 参数 |

### 4.2 向后兼容代码

| 文件 | 位置 | 说明 | 操作 |
|------|------|------|------|
| `loom/tools/tool_creation.py` | 第 216 行 | 本地工具存储（向后兼容） | 移除 |
| `loom/tools/context_tools.py` | 第 730 行 | 未使用的 `event_bus` 参数 | 移除参数 |
| `loom/agent/core.py` | 多处 | `enable_tool_creation` 参数 | 移除参数和相关逻辑 |
| `loom/agent/core.py` | 多处 | `config: AgentConfig` 参数 | 移除参数 |

### 4.3 命名冲突

| 问题 | 文件 | 解决方案 |
|------|------|----------|
| 两个 `SkillRegistry` 类 | `loom/skills/registry.py`<br>`loom/skills/skill_registry.py` | 合并为统一的 `SkillRegistry` |

---

## 五、重构计划

### 5.1 Phase 1: 移除废弃代码

**目标**: 清理向后兼容代码，减少技术债务

**任务**:
1. 删除 `loom/api/app.py` (LoomApp)
2. 删除 `loom/api/models.py` (AgentConfig, MemoryConfig)
3. 移除 `enable_tool_creation` 参数及相关逻辑
4. 清理 `tool_creation.py` 中的向后兼容代码
5. 移除 `context_tools.py` 中未使用的参数

**预期影响**: 破坏性变更，不向后兼容

### 5.2 Phase 2: 合并 SkillRegistry

**目标**: 统一 Skills 管理，消除命名冲突

**任务**:
1. 合并 `registry.py` 和 `skill_registry.py` 为统一的 `SkillRegistry`
2. 支持两种 Skill 来源：
   - Loaders（文件系统/数据库）
   - 运行时注册
3. 提供统一的异步接口
4. 更新所有引用

**新的 SkillRegistry 设计**:
```python
class SkillRegistry:
    def __init__(self):
        self.loaders = []  # 预定义 Skills
        self.runtimeSkills = {}  # 运行时 Skills

    async def getSkill(self, skillId: str):
        # 先查运行时，再查 Loaders
        pass
```

### 5.3 Phase 3: 实现新的 Agent.create() API

**目标**: 实现渐进式披露的 Agent 创建 API

**任务**:
1. 实现 `Agent.create()` 类方法
2. 使用驼峰命名法重命名所有参数
3. 实现自动创建默认组件的逻辑
4. 实现工具和 Skill 的简单配置
5. 集成 CapabilityRegistry

**关键实现**:
- 如果未传入 `eventBus`，自动创建
- 如果传入 `tools` 或 `skills`，内部创建 CapabilityRegistry
- 如果传入 `capabilities`，直接使用

### 5.4 Phase 4: 更新命名为驼峰式

**目标**: 统一代码风格，使用驼峰命名法

**任务**:
1. 重命名 Agent 方法：`execute_task` → `executeTask`
2. 重命名 Agent 方法：`run` 保持不变（简短常用）
3. 更新所有内部方法名
4. 更新测试代码

**命名对照表**:
| 旧名称 | 新名称 |
|--------|--------|
| `execute_task` | `executeTask` |
| `publish_thinking` | `publishThinking` |
| `publish_tool_call` | `publishToolCall` |
| `query_collective_memory` | `queryCollectiveMemory` |

---

## 六、迁移指南

### 6.1 从 LoomApp 迁移到 Agent.create()

**旧代码 (v0.4.x)**:
```python
from loom.api import LoomApp
from loom.api.models import AgentConfig

app = LoomApp()
app.set_llm_provider(llm)

config = AgentConfig(
    agent_id="assistant",
    name="AI Assistant",
    system_prompt="你是一个AI助手",
    max_iterations=10
)

agent = app.create_agent(config)
```

**新代码 (v0.5.0)**:
```python
from loom.agent import Agent

agent = Agent.create(
    llm=llm,
    nodeId="assistant",
    systemPrompt="你是一个AI助手",
    maxIterations=10
)
```

### 6.2 工具配置迁移

**旧代码**:
```python
app = LoomApp()
app.register_tool(my_tool_func)
agent = app.create_agent(config)
```

**新代码**:
```python
agent = Agent.create(
    llm=llm,
    tools=[tool1, tool2]
)
```

### 6.3 多 Agent 共享 EventBus

**旧代码**:
```python
app = LoomApp()
agent1 = app.create_agent(config1)
agent2 = app.create_agent(config2)
# 自动共享 EventBus
```

**新代码**:
```python
from loom.events import EventBus

eventBus = EventBus()

agent1 = Agent.create(llm=llm, eventBus=eventBus)
agent2 = Agent.create(llm=llm, eventBus=eventBus)
```

---

## 七、总结

本次 API 重构的核心目标是：

1. **简化 API** - 移除 LoomApp 和 AgentConfig，使用 Agent.create()
2. **统一命名** - 使用驼峰命名法，保持风格一致
3. **渐进式披露** - 简单用法简洁，高级用法灵活
4. **清理技术债** - 移除向后兼容代码，保持框架简洁

**预期收益**：
- 降低学习曲线
- 提高代码可维护性
- 减少命名冲突
- 统一代码风格

**风险**：
- 破坏性变更，不向后兼容
- 需要更新所有示例和文档
- 用户需要迁移现有代码

---

*文档版本: v0.5.0*
*创建日期: 2026-02-02*
*状态: 设计阶段*

