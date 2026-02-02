# Loom Agent 0.5.0 深度研究报告

**版本**: v0.5.0
**日期**: 2026-02-02
**状态**: 研究阶段
**核心理念**: 基于公理系统，以LLM自我判断能力为核心

---

## 核心愿景

Loom Agent框架的设计围绕三个核心目标展开：

### 对抗认知熵增
在**复杂度**与**时间**两个维度上保持可扩展性：
- **空间维度**：通过分形架构实现O(1)认知负载，无论系统规模如何增长
- **时间维度**：通过记忆代谢（L1→L2→L3→L4）实现长期连贯性

### 认知即编排
**"Intelligence = emergent property of orchestration, not raw LLM power"**

认知不在单个节点内部，而是在节点间的编排中涌现。这是A5公理（认知调度公理）的哲学基础。

### 长时程可靠
解决Long Horizon Collapse问题（约20步后失去一致性）：
- 支持小时/天级任务执行
- 支持多日连贯运行
- 通过记忆层次和分形架构保持长期目标一致性

---

## 执行摘要

### 研究背景

本报告基于对Loom Agent框架六大管理体系的深入研究，旨在为0.5.0版本制定全面的优化方案。0.5.0版本将是一个**不向后兼容的重大重构**，其核心目标是：

1. **回归公理系统**：严格遵循六大公理（A1-A6），消除违背公理的设计
2. **LLM自主决策**：将决策权完全交给LLM，减少硬编码逻辑
3. **清理技术债务**：彻底移除废弃代码、向后兼容层和冗余设计
4. **简化API**：采用渐进式披露，降低学习曲线

### 核心发现

通过对五份研究文档的综合分析，我们发现了以下关键问题：

**架构层面**：
- ✅ 公理系统设计优雅，但实现中存在偏离
- ⚠️ 六大管理体系职责清晰，但存在重复和冗余
- ❌ API层过度设计，LoomApp成为不必要的抽象

**技术债务**：
- 两套SkillRegistry并存，命名冲突严重
- ToolRegistry与SandboxToolManager双轨并行
- Agent工具列表与执行来源不一致（P0级bug）
- 大量向后兼容代码影响代码质量

**设计偏离**：
- 过多的配置选项限制了LLM的自主性
- 硬编码的决策逻辑（如复杂度评估）违背A5公理
- 显式的工具创建开关（enable_tool_creation）不必要

### 0.5.0版本核心目标

**哲学转变**：从"配置驱动"转向"LLM驱动"

```
旧范式：框架告诉LLM能做什么
新范式：LLM自主决定要做什么
```

**三大支柱**：
1. **极简API**：Agent.create(llm) 即可开始
2. **自主决策**：LLM决定何时使用工具、委派、完成
3. **公理纯粹**：所有设计严格遵循A1-A6

---

## 第一部分：公理系统分析

### 1.1 六大公理回顾

Loom Agent的设计基于六个核心公理，这些公理定义了系统的本质：

#### A1: 统一接口公理
```
∀x ∈ System: x implements NodeProtocol
```

**含义**：系统中的所有节点都实现统一的NodeProtocol接口。

**实现状态**：✅ **良好**
- Agent、BaseNode、SkillAgentNode、Pipeline都实现了NodeProtocol
- 接口定义清晰：node_id, source_uri, agent_card, execute_task, get_capabilities

**发现的问题**：
- NodeContainer虽然实现了NodeProtocol，但使用场景不明确
- 部分节点的get_capabilities()返回值不一致

#### A2: 事件主权公理
```
∀communication ∈ System: communication = Task
```

**含义**：所有通信都以Task为载体的任务事件。

**实现状态**：✅ **优秀**
- EventBus按task.action路由，设计优雅
- Task同时承载路由键和数据，符合A2A协议
- Memory通过订阅"*"自动收集所有Task

**发现的问题**：
- EventBus同一action只调用第一个handler，限制了多订阅者场景
- Task字段命名混用snake_case和camelCase

#### A3: 分形自相似公理
```
∀node ∈ System: structure(node) ≅ structure(System)
```

**含义**：节点递归组合，子节点与父节点结构相同。

**实现状态**：⚠️ **部分偏离**
- Agent的子节点创建机制（_create_child_node）符合A3
- FractalMemory的作用域设计（LOCAL/SHARED/INHERITED/GLOBAL）优雅

**发现的问题**：
- **硬编码的分形决策**：should_use_fractal()使用启发式规则评估复杂度，违背"LLM自主决策"原则
- **显式的委派工具**：delegate_task作为meta-tool暴露给LLM是正确的，但复杂度评估不应由框架决定
- **预算控制过于严格**：BudgetTracker的max_depth/max_children限制了LLM的自主性

**核心矛盾**：
```python
# 当前实现（违背A3精神）
if estimate_task_complexity(task) > threshold:
    use_fractal = True  # 框架决定

# 应该的实现（符合A3精神）
# LLM看到delegate_task工具，自己决定是否委派
```

#### A4: 记忆层次公理
```
Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4
```

**含义**：四层记忆、有损压缩、层间自动迁移。

**实现状态**：✅ **优秀**
- LoomMemory的L1-L4设计精妙
- 自动重要性推断（_infer_importance）合理
- ContextOrchestrator的预算分配机制优雅

**发现的问题**：
- promote_tasks()同步版不执行L3→L4，容易被忽略
- L4向量化需要显式调用promote_tasks_async()
- MemoryManager与FractalMemory的职责边界模糊

#### A5: 认知调度公理
```
Cognition = Orchestration(N1, N2, …, Nk)
```

**含义**：认知通过节点编排涌现，"思考即是调度"。

**实现状态**：⚠️ **理念正确，实现偏离**
- Orchestrator抽象设计优雅（Router/Crew/Workflow/Pipeline）
- AgentWorkflow体现了"Agent自主决策与委派"的理念

**发现的问题**：
- **过度的编排抽象**：RouterOrchestrator按AgentCapability匹配节点，这是框架决策而非LLM决策
- **硬编码的路由逻辑**：_select_node()的匹配规则限制了灵活性
- **与Dispatcher职责重叠**：Dispatcher按target_agent路由，Orchestrator按策略路由，两者边界不清

**核心矛盾**：
A5的本质是"认知涌现于编排"，但当前实现中，编排策略由框架预定义，而非由LLM在运行时决定。

#### A6: 四范式工作公理
```
Agent = Reflection ∪ ToolUse ∪ Planning ∪ MultiAgent
```

**含义**：Agent的工作模式包含四种范式，由LLM自主选择。

**实现状态**：✅ **良好**
- AgentCapability枚举定义清晰（loom/protocol/agent_card.py:16-30）
- 四种能力：REFLECTION（反思）、TOOL_USE（工具使用）、PLANNING（规划）、MULTI_AGENT（多代理协作）
- Agent通过meta_tools（create_plan、delegate_task）实现规划和协作
- LLM可以自主决定何时使用哪种范式

**发现的问题**：
- RouterOrchestrator按AgentCapability匹配节点，这是框架决策而非LLM决策
- 四范式的边界在某些场景下不够清晰（如reflection与planning的区别）
- 缺少显式的reflection工具，反思能力主要依赖system prompt

**优秀的设计**：
- ✅ 四范式作为能力声明而非硬编码流程
- ✅ LLM通过工具调用自主选择工作模式
- ✅ 与A5（认知调度）协同，支持多范式组合

### 1.2 公理系统的哲学内核

通过对六大公理的深入分析，我们发现了Loom Agent设计的哲学内核：

**第一性原理**：
```
Agent = LLM + Protocol + Memory + Tools
```

其中：
- **LLM**：唯一的决策者
- **Protocol**：统一的通信语言（Task）
- **Memory**：上下文的来源
- **Tools**：能力的扩展

**涌现原则**：
- 复杂行为应该从简单规则中涌现
- 框架提供机制（mechanism），LLM提供策略（policy）
- 不应该硬编码"何时做什么"，只应该提供"能做什么"

**当前偏离的根源**：

在0.4.x版本的演进中，为了"帮助"LLM做出更好的决策，框架引入了大量的启发式规则和配置选项：

1. **复杂度评估**：estimate_task_complexity()
2. **分形触发器**：GrowthTrigger.COMPLEXITY
3. **能力匹配**：RouterOrchestrator的_select_node()
4. **工具创建开关**：enable_tool_creation
5. **上下文工具开关**：enable_context_tools

这些设计的初衷是好的，但违背了"LLM自主决策"的核心理念。

---

## 第二部分：当前架构深度分析

### 2.1 六大管理体系概览

Loom Agent框架由六大管理体系组成，每个体系负责特定的职责：

| 体系 | 核心模块 | 职责 | 公理对应 |
|------|---------|------|---------|
| **Agent Manager** | loom/agent | Agent生命周期、执行循环、子节点创建 | A1, A3 |
| **Tool Manager** | loom/tools | 工具注册、执行、沙盒管理 | - |
| **Skill Manager** | loom/skills | 技能加载、激活、依赖验证 | - |
| **Memory Manager** | loom/memory | L1-L4分层存储、上下文构建 | A4 |
| **Event Manager** | loom/events | Task发布订阅、事件路由 | A2 |
| **Orchestration Manager** | loom/orchestration | 多节点编排、工作流 | A5 |

**辅助体系**：
- **Protocol** (loom/protocol): 定义NodeProtocol、Task、AgentCard等核心协议
- **Runtime** (loom/runtime): Dispatcher、Interceptor、StateManager等运行时基础设施
- **Config** (loom/config): 类型安全的配置模型
- **Fractal** (loom/fractal): 分形容器、预算跟踪、结果合成
- **Capabilities** (loom/capabilities): 能力发现与验证的门面

### 2.2 Agent Manager 深度分析

**核心组件**：
- `BaseNode`: 观测、集体记忆、拦截器链
- `Agent`: LLM驱动的智能体，实现四范式（反思、工具、规划、协作）
- `AgentBuilder`: 链式构建API
- `SkillAgentNode`: Skill实例化形态（Form 3）

**执行流程**：
```python
# Agent._execute_impl 的核心循环
while iteration < max_iterations:
    1. build_context(task)  # 从Memory构建上下文
    2. llm.chat(messages, tools)  # LLM决策
    3. execute_tools()  # 执行工具调用
    4. check_done()  # 检查是否完成
```

**发现的问题**：

1. **工具列表不一致（P0 Bug）**：
   - `_get_available_tools()` 只合并 `self.tools` 和 `config.extra_tools`
   - 未包含 `sandbox_manager` 中的工具
   - 导致工具可执行但不在LLM的工具列表中

2. **过多的构造参数**：
   - `Agent.__init__` 有20+个参数
   - 违背"渐进式披露"原则
   - 新手难以上手

3. **配置驱动的决策**：
   ```python
   # 当前实现
   if self.enable_tool_creation:
       tools.append(create_tool)

   if self.enable_context_tools:
       tools.extend(context_tools)
   ```
   这些开关限制了LLM的自主性，应该始终提供所有工具，让LLM决定是否使用。

4. **子节点创建的复杂性**：
   - `_create_child_node` 需要手动传递大量参数
   - `AgentConfig.inherit` 的继承逻辑复杂
   - 违背A3的"自相似"原则

**优秀的设计**：
- ✅ `delegate_task` 作为meta-tool的设计正确
- ✅ `parent_memory` 的传递机制优雅
- ✅ `_sync_memory_from_child` 的SHARED作用域同步合理

### 2.3 Tool Manager 深度分析

**核心组件**：
- `ToolRegistry`: 同步工具注册表（func + MCP定义）
- `SandboxToolManager`: 沙盒工具管理器（推荐主入口）
- `ToolExecutor`: 工具执行器基类
- `SandboxedExecutor`: 沙盒执行器

**双轨问题**：

当前存在两套并行的工具管理系统：

| 维度 | ToolRegistry | SandboxToolManager |
|------|-------------|-------------------|
| **定位** | 旧版/兼容入口 | 新版推荐入口 |
| **API** | register_function, get_definition, has | register_tool, execute_tool, list_tools |
| **执行** | 无（只存定义） | 有（含scope、沙盒、事件） |
| **使用者** | LoomApp、SkillActivator、Agent extra_tools | CapabilityRegistry、Agent执行 |

**核心问题**：

1. **依赖校验与执行不一致**：
   - SkillActivator使用 `tool_registry.has(tool_name)` 验证依赖
   - Agent执行时使用 `sandbox_manager.execute_tool()`
   - 可能导致"依赖验证通过但执行失败"

2. **Agent工具来源分散**：
   ```python
   # 当前Agent的工具来源
   1. self.tools  # 直接传入
   2. config.extra_tools  # 从tool_registry
   3. sandbox_manager  # 执行时可用，但不在LLM工具列表中（Bug）
   ```

3. **LoomApp未使用SandboxToolManager**：
   - LoomApp只使用ToolRegistry
   - 与推荐的最佳实践不一致

**优秀的设计**：
- ✅ SandboxToolManager的scope机制（LOCAL/SHARED/GLOBAL）
- ✅ 工具执行的事件发布（tool.executing/tool.completed）
- ✅ MCP协议的完整支持

### 2.4 Skill Manager 深度分析

**核心问题：两套SkillRegistry并存**

| 维度 | loom/skills/registry.py | loom/skills/skill_registry.py |
|------|------------------------|------------------------------|
| **定位** | SKILL.md/DB技能包（Loader） | 可调用工具型Skill（类似OpenAI function） |
| **API** | async: get_skill, get_all_metadata | sync: get_skill, list_skills, register_skill |
| **返回** | SkillDefinition | dict（含_metadata, _handler） |
| **使用者** | Agent core、集成测试 | LoomApp、CapabilityRegistry |

**命名冲突**：
```python
# loom/skills/__init__.py
from .registry import SkillRegistry  # 第一个
from .skill_registry import skill_market  # 第二个也叫SkillRegistry

# 用户困惑：到底用哪个？
```

**不兼容问题**：
- CapabilityRegistry的 `validate_skill_dependencies` 只适配dict版
- Agent期望async + metadata（Loader版）
- 两套入口难以统一

**优秀的设计**：
- ✅ SkillActivator的三种激活形式（Form 1/2/3）
- ✅ find_relevant_skills的语义匹配
- ✅ Skill依赖验证机制

### 2.5 Memory Manager 深度分析

**核心组件**：
- `LoomMemory`: L1-L4分层存储
- `MemoryManager`: 整合LoomMemory + Fractal作用域
- `ContextOrchestrator`: 上下文构建与预算分配
- `ContextSource`: 多源上下文提供者

**优秀的设计**：

1. **L1-L4分层架构**：
   - L1: 循环缓冲区（完整Task）
   - L2: 优先队列（重要Task，importance > 0.6）
   - L3: TaskSummary（压缩表示）
   - L4: 向量存储（语义检索）

2. **自动重要性推断**：
   ```python
   # _infer_importance 的规则合理
   node.error → 0.9
   node.planning → 0.8
   node.tool_result → 0.75
   execute → 0.65
   ```

3. **作用域设计**：
   - LOCAL: 节点私有
   - SHARED: 父子共享
   - INHERITED: 从父节点继承
   - GLOBAL: 全局可见

**发现的问题**：

1. **promote_tasks的陷阱**：
   ```python
   # 同步版不执行L3→L4
   memory.promote_tasks()  # 只做L1→L2, L2→L3

   # 需要显式调用异步版
   await memory.promote_tasks_async()  # 才会做L3→L4向量化
   ```
   容易被忽略，导致L4长期不更新。

2. **MemoryManager与FractalMemory职责模糊**：
   - MemoryManager内部持有LoomMemory + _memory_by_scope
   - FractalMemory也有类似的作用域设计
   - 两者API对齐但实现分离，增加理解成本

3. **上下文预算的复杂性**：
   - BudgetConfig的l1_ratio/l2_ratio/l3_l4_ratio需要手动配置
   - 违背"LLM自主决策"原则

### 2.6 Event Manager 深度分析

**核心组件**：
- `EventBus`: Task发布订阅
- `Transport`: 传输层抽象（Memory/NATS）
- `TaskAction`: 类型安全的动作枚举

**优秀的设计**：
- ✅ 按task.action路由，设计简洁
- ✅ 支持"*"通配符订阅
- ✅ Memory通过订阅"*"自动收集所有Task
- ✅ Transport抽象支持分布式部署

**发现的问题**：

1. **单handler限制**：
   ```python
   # 同一action只调用第一个handler
   handler = self._handlers.get(action)
   if handler:
       return await handler(task)
   ```
   限制了多订阅者场景。

2. **与Dispatcher职责重叠**：
   - EventBus按action路由
   - Dispatcher按target_agent路由
   - 两者边界不清，容易混淆

### 2.7 Orchestration Manager 深度分析

**核心组件**：
- `Orchestrator`: 抽象基类
- `RouterOrchestrator`: 单节点路由
- `CrewOrchestrator`: 多节点并行
- `Workflow`: 工作流抽象
- `Pipeline`: 流水线（顺序/并行/条件步骤）

**发现的问题**：

1. **硬编码的路由逻辑**：
   ```python
   # RouterOrchestrator._select_node
   if task.action == "tool_use":
       return node_with_tool_use_capability
   ```
   这是框架决策，违背A5"认知涌现"原则。

2. **与Dispatcher职责重叠**：
   - Dispatcher: 按target_agent路由 + EventBus fallback
   - Orchestrator: 按策略路由
   - 两者可以组合，但边界不清

3. **过度的抽象**：
   - RouterOrchestrator、CrewOrchestrator、SequentialWorkflow、AgentWorkflow
   - 大多数场景只需要AgentWorkflow（LLM自主决策）

**优秀的设计**：
- ✅ AgentWorkflow体现了"LLM自主决策与委派"
- ✅ Pipeline的StepType设计灵活

---

## 第三部分：技术债务和问题清单

### 3.1 P0级问题（必须修复）

#### 问题1: Agent工具列表与执行来源不一致

**位置**: `loom/agent/core.py` 的 `_get_available_tools()`

**问题描述**:
```python
# 当前实现
def _get_available_tools(self):
    tools = []
    tools.extend(self.tools)  # 直接传入的工具
    tools.extend(config.extra_tools)  # 从tool_registry
    # ❌ 缺少：从sandbox_manager获取工具
    return tools

# 执行时
def _execute_tool(self, tool_call):
    # 先尝试context_tools
    # 再尝试sandbox_manager  # ✅ 可以执行
    # 最后尝试tool_registry
```

**影响**:
- 若用户只传 `sandbox_manager` 不传 `tool_registry`
- 这些工具可被执行，但**不会出现在发给LLM的工具列表中**
- LLM无法知道这些工具的存在，无法调用

**修复方案**:
```python
def _get_available_tools(self):
    tools = []
    tool_names_seen = set()

    # 1. 添加直接传入的工具
    for tool in self.tools:
        name = tool["function"]["name"]
        if name not in tool_names_seen:
            tool_names_seen.add(name)
            tools.append(tool)

    # 2. 添加config.extra_tools
    for tool_name in self.config.extra_tools:
        if tool_name not in tool_names_seen:
            tool_def = self.tool_registry.get_definition(tool_name)
            tool_names_seen.add(tool_name)
            tools.append(tool_def)

    # 3. ✅ 添加sandbox_manager中的工具
    if self.sandbox_manager:
        for mcp_def in self.sandbox_manager.list_tools():
            if mcp_def.name not in tool_names_seen:
                tool_names_seen.add(mcp_def.name)
                tools.append({
                    "type": "function",
                    "function": {
                        "name": mcp_def.name,
                        "description": mcp_def.description,
                        "parameters": mcp_def.input_schema,
                    },
                })

    return tools
```

**优先级**: P0 - 必须在0.5.0中修复

### 3.2 P1级问题（高优先级）

#### 问题2: 两套SkillRegistry命名冲突

**位置**: `loom/skills/`

**问题描述**:
- `loom/skills/registry.py`: SkillRegistry（Loader版）
- `loom/skills/skill_registry.py`: SkillRegistry（dict版）
- 两者同名但功能不同，用户困惑

**影响**:
- 用户不知道该用哪个
- CapabilityRegistry只适配dict版
- Agent期望Loader版
- 无法统一

**修复方案**:
合并为统一的SkillRegistry：
```python
class SkillRegistry:
    def __init__(self):
        self.loaders = []  # 预定义Skills（文件系统/数据库）
        self.runtimeSkills = {}  # 运行时注册的Skills

    async def getSkill(self, skillId: str):
        # 先查运行时，再查Loaders
        if skillId in self.runtimeSkills:
            return self.runtimeSkills[skillId]

        for loader in self.loaders:
            skill = await loader.load(skillId)
            if skill:
                return skill

        return None

    def registerSkill(self, skillId: str, skill: dict):
        """运行时注册"""
        self.runtimeSkills[skillId] = skill

    def registerLoader(self, loader):
        """注册Loader"""
        self.loaders.append(loader)
```

**优先级**: P1 - 应该在0.5.0中修复

#### 问题3: ToolRegistry与SandboxToolManager双轨并行

**位置**: `loom/tools/`

**问题描述**:
- 两套工具管理系统并存
- SkillActivator使用ToolRegistry验证依赖
- Agent执行使用SandboxToolManager
- 可能导致"依赖验证通过但执行失败"

**修复方案**:
1. 统一使用SandboxToolManager
2. SkillActivator支持SandboxToolManager
3. 逐步废弃ToolRegistry

**优先级**: P1 - 应该在0.5.0中修复

### 3.3 废弃代码清单

以下代码已标记为废弃，应在0.5.0中完全移除：

| 文件 | 内容 | 废弃版本 | 移除版本 |
|------|------|---------|---------|
| `loom/api/app.py` | LoomApp类 | 0.4.7 | 0.5.0 |
| `loom/api/models.py` | AgentConfig（Pydantic） | 0.4.7 | 0.5.0 |
| `loom/api/models.py` | MemoryConfig（Pydantic） | 0.4.7 | 0.5.0 |
| `loom/tools/tool_creation.py:216` | 本地工具存储（向后兼容） | - | 0.5.0 |
| `loom/tools/context_tools.py:730` | 未使用的event_bus参数 | - | 0.5.0 |
| `loom/agent/core.py` | enable_tool_creation参数 | - | 0.5.0 |
| `loom/agent/core.py` | enable_context_tools参数 | - | 0.5.0 |
| `loom/agent/core.py` | config: AgentConfig参数 | - | 0.5.0 |

### 3.4 设计偏离清单

以下设计违背了"LLM自主决策"的核心理念，应在0.5.0中重新设计：

#### 偏离1: 硬编码的复杂度评估

**位置**: `loom/fractal/utils.py` 的 `estimate_task_complexity()`

**问题**:
```python
def estimate_task_complexity(task_description: str) -> float:
    # 基于长度、连接词、步骤词的启发式规则
    complexity = len(task_description) / 100
    if "and" in task_description or "or" in task_description:
        complexity += 0.2
    # ...
    return complexity
```

**为什么违背公理**:
- 框架决定任务是否复杂，而非LLM
- 违背A3"分形自相似"的精神
- 限制了LLM的自主判断

**应该的设计**:
- 移除复杂度评估
- 始终提供delegate_task工具
- 让LLM自己决定是否需要委派

#### 偏离2: 配置驱动的工具开关

**位置**: `loom/agent/core.py`

**问题**:
```python
if self.enable_tool_creation:
    tools.append(create_tool)

if self.enable_context_tools:
    tools.extend(context_tools)
```

**为什么违背公理**:
- 框架决定LLM能看到哪些工具
- 限制了LLM的能力
- 违背"提供机制，不提供策略"原则

**应该的设计**:
- 移除所有enable_*开关
- 始终提供所有工具
- 让LLM决定是否使用

#### 偏离3: 硬编码的路由逻辑

**位置**: `loom/orchestration/router.py` 的 `RouterOrchestrator._select_node()`

**问题**:
```python
def _select_node(self, task):
    if task.action == "tool_use":
        return node_with_tool_use_capability
    elif task.action == "planning":
        return node_with_planning_capability
    # ...
```

**为什么违背公理**:
- 框架决定任务路由到哪个节点
- 违背A5"认知涌现"原则
- 应该由LLM决定委派给谁

**应该的设计**:
- 移除RouterOrchestrator
- 使用AgentWorkflow
- LLM通过delegate_task指定target_agent

#### 偏离4: 过度的预算控制

**位置**: `loom/fractal/budget.py` 的 `BudgetTracker`

**问题**:
```python
if depth >= max_depth:
    raise BudgetViolation("Max depth exceeded")

if children_count >= max_children:
    raise BudgetViolation("Max children exceeded")
```

**为什么违背公理**:
- 硬性限制阻止了LLM的探索
- 违背"LLM自主决策"原则
- 应该是软限制而非硬限制

**应该的设计**:
- 将预算信息作为上下文提供给LLM
- LLM自己决定是否继续委派
- 框架只记录使用情况，不强制限制

#### 偏离5: 硬编码的重要性推断

**位置**: `loom/memory/core.py` 的 `_infer_importance()`

**问题**:
```python
def _infer_importance(self, task: "Task") -> float:
    """基于动作类型的轻量默认重要性估计"""
    action = task.action
    if action == "node.error":
        return 0.9
    if action == "node.planning":
        return 0.8
    if action == "node.tool_result":
        return 0.75
    if action == "node.tool_call":
        return 0.7
    if action == "execute":
        return 0.65
    if action == "node.complete":
        return 0.6
    if action == "node.thinking":
        return 0.55
    return 0.5
```

**代码位置**: loom/memory/core.py:160-177

**为什么违背公理**:
- 重要性完全由固定规则推断，没有LLM参与
- 违背"LLM自主决策"的核心理念
- 不同场景下同一action的重要性可能不同，规则无法适应
- 限制了记忆系统的灵活性和准确性

**应该的设计**:
- 保留规则作为默认值（快速路径）
- 提供可选的LLM评估路径：让LLM对任务重要性打分
- 将LLM评分结果写入task.metadata
- L2/L3提升时优先使用LLM评分，降级使用规则评分
- 在ContextOrchestrator中可选择性地使用LLM评估的重要性

### 3.5 冗余设计清单

以下设计存在冗余，应在0.5.0中简化或合并：

| 冗余项 | 说明 | 建议 |
|-------|------|------|
| MemoryManager vs FractalMemory | 两者API对齐但实现分离 | 合并为统一的MemoryManager |
| Dispatcher vs EventBus | 职责重叠，路由逻辑分散 | 明确边界或合并 |
| RouterOrchestrator vs Dispatcher | 都做路由，逻辑重复 | 移除RouterOrchestrator |
| ToolRegistry vs SandboxToolManager | 双轨工具管理 | 统一使用SandboxToolManager |
| SkillRegistry (两套) | 命名冲突，功能重复 | 合并为统一的SkillRegistry |
| AgentConfig (两套) | api.models vs config.agent | 移除api.models版本 |

---

## 第四部分：0.5.0版本优化方案

### 4.1 核心设计原则

0.5.0版本将基于以下核心原则进行重构：

#### 原则1: LLM自主决策（LLM Autonomy）

**理念**：框架提供机制（mechanism），LLM提供策略（policy）

**具体实践**：
- ❌ 移除：所有enable_*开关（enable_tool_creation, enable_context_tools等）
- ❌ 移除：硬编码的决策逻辑（复杂度评估、路由匹配等）
- ✅ 保留：工具定义和执行机制
- ✅ 增强：LLM的上下文信息（预算使用情况、可用工具列表等）

**示例对比**：
```python
# 旧设计（框架决策）
if estimate_task_complexity(task) > threshold:
    use_fractal = True

# 新设计（LLM决策）
# 始终提供delegate_task工具
# LLM根据任务描述和上下文自己决定是否委派
```

#### 原则2: 渐进式披露（Progressive Disclosure）

**理念**：简单用法只需最少参数，高级用法支持深度定制

**具体实践**：
```python
# 极简用法
agent = Agent.create(llm)

# 常用配置
agent = Agent.create(
    llm=llm,
    systemPrompt="你是一个AI助手",
    maxIterations=20
)

# 高级配置
eventBus = EventBus()
capabilities = CapabilityRegistry()
agent = Agent.create(
    llm=llm,
    systemPrompt="...",
    eventBus=eventBus,
    capabilities=capabilities
)
```

#### 原则3: 驼峰命名法（camelCase）

**理念**：统一代码风格，提高可读性

**具体实践**：
- 所有新API使用camelCase
- 方法名：`executeTask`, `buildContext`, `publishThinking`
- 参数名：`systemPrompt`, `maxIterations`, `nodeId`
- 保持与JavaScript/TypeScript生态一致

#### 原则4: 显式传入全局组件（Explicit Dependency Injection）

**理念**：用户显式创建和管理全局组件，避免隐式的全局状态

**具体实践**：
```python
# 多Agent共享EventBus
eventBus = EventBus()
agent1 = Agent.create(llm=llm, eventBus=eventBus)
agent2 = Agent.create(llm=llm, eventBus=eventBus)

# 而非隐式的全局单例
# agent1 = Agent.create(llm=llm)  # 自动使用全局EventBus
```

#### 原则5: 不向后兼容（Breaking Changes）

**理念**：彻底清理技术债务，保持框架简洁

**具体实践**：
- 移除所有废弃代码（LoomApp, api.models.AgentConfig等）
- 移除所有向后兼容层
- 不保留旧API的别名或适配器
- 提供清晰的迁移指南

### 4.2 新的Agent API设计

#### 核心方法：Agent.create()

**设计理念**：直接创建Agent实例，无需中间层（LoomApp）

**完整签名**：
```python
@classmethod
def create(
    cls,
    llm: LLMProvider,
    *,
    # 基础配置
    nodeId: str | None = None,
    systemPrompt: str | None = None,
    maxIterations: int = 10,

    # 全局组件（显式传入）
    eventBus: EventBus | None = None,
    memory: MemoryManager | None = None,

    # 能力配置（简单用法）
    tools: list[dict] | None = None,
    skills: list[str] | None = None,

    # 能力配置（高级用法）
    capabilities: CapabilityRegistry | None = None,

    # 高级配置
    parentMemory: MemoryManager | None = None,
    recursiveDepth: int = 0,
    budgetTracker: BudgetTracker | None = None,
) -> Agent:
    """
    创建Agent实例

    简单用法：
        agent = Agent.create(llm)

    常用配置：
        agent = Agent.create(
            llm=llm,
            systemPrompt="你是一个AI助手",
            maxIterations=20
        )

    高级配置：
        eventBus = EventBus()
        agent = Agent.create(
            llm=llm,
            eventBus=eventBus,
            tools=[tool1, tool2],
            skills=["python-dev"]
        )
    """
```

**内部实现逻辑**：
```python
@classmethod
def create(cls, llm, **kwargs):
    # 1. 自动创建缺失的组件
    if kwargs.get('eventBus') is None:
        kwargs['eventBus'] = EventBus()

    if kwargs.get('memory') is None:
        kwargs['memory'] = MemoryManager(
            nodeId=kwargs.get('nodeId', 'agent'),
            eventBus=kwargs['eventBus'],
            parent=kwargs.get('parentMemory')
        )

    # 2. 处理能力配置
    if kwargs.get('capabilities') is None:
        # 简单用法：从tools和skills创建CapabilityRegistry
        capabilities = CapabilityRegistry()

        if kwargs.get('tools'):
            for tool in kwargs['tools']:
                capabilities.registerTool(tool)

        if kwargs.get('skills'):
            for skill_id in kwargs['skills']:
                capabilities.registerSkill(skill_id)

        kwargs['capabilities'] = capabilities

    # 3. 创建Agent实例
    return cls(llm=llm, **kwargs)
```

### 4.3 工具和技能管理优化

#### 统一的SkillRegistry

**问题**：当前两套SkillRegistry并存，命名冲突

**解决方案**：合并为统一的SkillRegistry

```python
class SkillRegistry:
    """统一的Skill注册表，支持Loader和运行时注册"""

    def __init__(self):
        self.loaders: list[SkillLoader] = []
        self.runtimeSkills: dict[str, dict] = {}

    async def getSkill(self, skillId: str) -> SkillDefinition | dict | None:
        """获取Skill（先查运行时，再查Loaders）"""
        # 1. 先查运行时注册的Skills
        if skillId in self.runtimeSkills:
            return self.runtimeSkills[skillId]

        # 2. 再查Loaders
        for loader in self.loaders:
            skill = await loader.load(skillId)
            if skill:
                return skill

        return None

    def registerSkill(self, skillId: str, skill: dict):
        """运行时注册Skill"""
        self.runtimeSkills[skillId] = skill

    def registerLoader(self, loader: SkillLoader):
        """注册Skill Loader"""
        self.loaders.append(loader)

    async def listSkills(self) -> list[str]:
        """列出所有可用的Skill IDs"""
        skill_ids = set(self.runtimeSkills.keys())

        for loader in self.loaders:
            loader_skills = await loader.list()
            skill_ids.update(loader_skills)

        return list(skill_ids)
```

#### 统一使用SandboxToolManager

**问题**：ToolRegistry与SandboxToolManager双轨并行

**解决方案**：
1. 统一使用SandboxToolManager作为主入口
2. ToolRegistry仅作为内部适配器（如果需要）
3. 更新SkillActivator使用SandboxToolManager验证依赖

```python
# 旧代码（使用ToolRegistry）
class SkillActivator:
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def validate_dependencies(self, skill):
        for tool_name in skill.required_tools:
            if not self.tool_registry.has(tool_name):
                return False
        return True

# 新代码（使用SandboxToolManager）
class SkillActivator:
    def __init__(self, tool_manager: SandboxToolManager):
        self.tool_manager = tool_manager

    def validate_dependencies(self, skill):
        available_tools = {t.name for t in self.tool_manager.list_tools()}
        for tool_name in skill.required_tools:
            if tool_name not in available_tools:
                return False
        return True
```

### 4.4 LLM自主决策的具体实现

#### 移除硬编码的决策逻辑

**1. 移除复杂度评估**：
```python
# ❌ 删除
def estimate_task_complexity(task_description: str) -> float:
    ...

def should_use_fractal(task, config: FractalConfig) -> bool:
    if config.growth_trigger == GrowthTrigger.COMPLEXITY:
        complexity = estimate_task_complexity(task.parameters.get("content", ""))
        return complexity > config.complexity_threshold
    ...
```

**2. 始终提供所有工具**：
```python
# ❌ 旧代码
if self.enable_tool_creation:
    tools.append(create_tool)

# ✅ 新代码
tools.append(create_tool)  # 始终提供
tools.append(delegate_task)  # 始终提供
tools.extend(context_tools)  # 始终提供
```

**3. 预算信息作为上下文**：
```python
# ❌ 旧代码（硬限制）
if depth >= max_depth:
    raise BudgetViolation("Max depth exceeded")

# ✅ 新代码（软限制，提供信息）
budget_info = {
    "current_depth": depth,
    "max_depth": max_depth,
    "remaining_depth": max_depth - depth,
    "tokens_used": tokens_used,
    "token_budget": token_budget,
    "remaining_tokens": token_budget - tokens_used,
}

# 将预算信息添加到system prompt或工具描述中
system_prompt += f"\n\n当前预算状态：{budget_info}"
```

### 4.5 命名规范统一

所有API使用驼峰命名法（camelCase）：

| 旧名称 | 新名称 |
|--------|--------|
| `execute_task` | `executeTask` |
| `build_context` | `buildContext` |
| `publish_thinking` | `publishThinking` |
| `publish_tool_call` | `publishToolCall` |
| `query_collective_memory` | `queryCollectiveMemory` |
| `get_available_tools` | `getAvailableTools` |
| `create_child_node` | `createChildNode` |
| `sync_memory_from_child` | `syncMemoryFromChild` |
| `node_id` | `nodeId` |
| `system_prompt` | `systemPrompt` |
| `max_iterations` | `maxIterations` |
| `event_bus` | `eventBus` |
| `parent_memory` | `parentMemory` |
| `recursive_depth` | `recursiveDepth` |
| `budget_tracker` | `budgetTracker` |

---

## 第五部分：实施路线图

### 5.1 Phase 1: 清理废弃代码（Week 1-2）

**目标**：移除所有已标记为废弃的代码

**任务清单**：
1. ✅ 删除 `loom/api/app.py` (LoomApp)
2. ✅ 删除 `loom/api/models.py` (AgentConfig, MemoryConfig)
3. ✅ 移除 `enable_tool_creation` 参数及相关逻辑
4. ✅ 移除 `enable_context_tools` 参数及相关逻辑
5. ✅ 清理 `tool_creation.py` 中的向后兼容代码
6. ✅ 移除 `context_tools.py` 中未使用的参数
7. ✅ 更新所有测试用例

**验证标准**：
- 所有测试通过
- 无废弃代码残留
- 文档已更新

### 5.2 Phase 2: 统一工具和技能管理（Week 3-4）

**目标**：解决双轨并行问题

**任务清单**：
1. ✅ 合并两套SkillRegistry为统一实现
2. ✅ 统一使用SandboxToolManager
3. ✅ 更新SkillActivator使用SandboxToolManager
4. ✅ 修复Agent工具列表bug（P0）
5. ✅ 更新CapabilityRegistry适配新的SkillRegistry
6. ✅ 更新所有测试用例

**验证标准**：
- 工具列表与执行来源一致
- Skill依赖验证与执行一致
- 所有测试通过

### 5.3 Phase 3: 实现新的Agent API（Week 5-6）

**目标**：实现Agent.create()和渐进式披露

**任务清单**：
1. ✅ 实现Agent.create()类方法
2. ✅ 实现自动创建默认组件的逻辑
3. ✅ 实现工具和Skill的简单配置
4. ✅ 集成CapabilityRegistry
5. ✅ 更新所有示例代码
6. ✅ 编写迁移指南

**验证标准**：
- 简单用法只需一行代码
- 高级用法支持深度定制
- 所有示例可运行

### 5.4 Phase 4: 命名规范统一（Week 7-8）

**目标**：所有API使用驼峰命名法

**任务清单**：
1. ✅ 重命名Agent方法
2. ✅ 重命名参数名
3. ✅ 更新所有内部方法名
4. ✅ 更新测试代码
5. ✅ 更新文档和示例

**验证标准**：
- 所有公开API使用camelCase
- 所有测试通过
- 文档已更新

### 5.5 Phase 5: LLM自主决策优化（Week 9-10）

**目标**：移除硬编码的决策逻辑

**任务清单**：
1. ✅ 移除复杂度评估逻辑
2. ✅ 移除所有enable_*开关
3. ✅ 将预算控制改为软限制
4. ✅ 移除RouterOrchestrator
5. ✅ 更新测试用例
6. ✅ 验证LLM自主决策效果

**验证标准**：
- 无硬编码决策逻辑
- LLM可以自主决定所有策略
- 所有测试通过

### 5.6 Phase 6: 测试和文档（Week 11-12）

**目标**：全面测试和完善文档

**任务清单**：
1. ✅ 编写集成测试
2. ✅ 编写端到端测试
3. ✅ 性能测试和优化
4. ✅ 编写完整的API文档
5. ✅ 编写迁移指南
6. ✅ 编写最佳实践指南
7. ✅ 更新所有示例

**验证标准**：
- 测试覆盖率 > 80%
- 所有API有文档
- 迁移指南清晰完整

---

## 总结

### 核心改进

1. **回归公理系统**：严格遵循A1-A5，消除违背公理的设计
2. **LLM自主决策**：移除硬编码逻辑，让LLM自己决定策略
3. **清理技术债务**：移除废弃代码、向后兼容层和冗余设计
4. **简化API**：Agent.create(llm)即可开始，渐进式披露
5. **统一命名**：所有API使用camelCase，保持风格一致

### 预期收益

- **降低学习曲线**：新手只需一行代码即可开始
- **提高灵活性**：LLM自主决策，适应更多场景
- **提升可维护性**：代码简洁清晰，易于理解和修改
- **增强扩展性**：渐进式披露，支持深度定制

### 风险与挑战

- **破坏性变更**：不向后兼容，用户需要迁移
- **LLM能力依赖**：依赖LLM的决策能力，需要好的prompt
- **测试工作量**：需要重写大量测试用例
- **文档工作量**：需要更新所有文档和示例

### 下一步行动

1. **评审本报告**：与团队讨论，确认方向
2. **制定详细计划**：细化每个Phase的任务
3. **开始Phase 1**：清理废弃代码
4. **持续迭代**：按Phase逐步推进

---

*报告版本: v1.0*
*创建日期: 2026-02-02*
*状态: 待评审*

