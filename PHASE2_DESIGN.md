# Phase 2 设计文档：Skill 三层激活模型

> 设计时间：2026-01-30
> 基于：OPTIMIZATION_PLAN.md 第 2.2 节

## 一、设计目标

实现 Skill 三层激活模型，支持三种激活形态：
1. **Form 1: 知识注入**（90%）- 注入到 system_prompt，零额外 LLM 调用
2. **Form 2: 脚本编译为 Tool**（8%）- 编译脚本为可直接调用的 Tool
3. **Form 3: 实例化为 SkillAgentNode**（2%）- 独立的多轮 LLM 交互

## 二、三层激活模型架构

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Agent 执行任务                        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Configuration Layer (配置层)                   │
│  - 决定每个 Skill 使用哪种激活模式                        │
│  - 输入: SkillDefinition                                 │
│  - 输出: SkillActivationMode (INJECTION/COMPILATION/     │
│          INSTANTIATION)                                  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 2: Discovery Layer (发现层)                       │
│  - 使用 LLM 判断哪些 Skills 与任务相关                    │
│  - 输入: task_description, skill_metadata                │
│  - 输出: list[skill_id]                                  │
│  - 现有实现: SkillActivator.find_relevant_skills()       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Activation Layer (激活层)                      │
│  - 根据激活模式实际激活 Skill                             │
│  - Form 1: 注入 system_prompt                            │
│  - Form 2: 编译为 Tool 并注册                            │
│  - Form 3: 实例化为 SkillAgentNode                       │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Layer 1: Configuration Layer (配置层)

**职责**：决定每个 Skill 使用哪种激活模式

**决策逻辑**：
```python
def determine_activation_mode(skill: SkillDefinition) -> SkillActivationMode:
    """
    决定 Skill 的激活模式

    决策规则：
    1. 如果 skill.metadata 中指定了 activation_mode，使用指定的模式
    2. 否则，根据 Skill 特征自动判断：
       - 有脚本 (scripts) → COMPILATION
       - 标记为需要多轮交互 (metadata.multi_turn=True) → INSTANTIATION
       - 默认 → INJECTION
    """
```

**实现位置**：新增 `SkillActivator.determine_activation_mode()` 方法

### 2.3 Layer 2: Discovery Layer (发现层)

**职责**：使用 LLM 判断哪些 Skills 与任务相关

**现有实现**：`SkillActivator.find_relevant_skills()`
- 输入：task_description, skill_metadata, max_skills
- 输出：list[skill_id]
- 使用 LLM 进行相关性判断
- 实现了 Progressive Disclosure（只使用 metadata，不加载完整 Skill）

**无需修改**：此层已经实现，符合设计要求

### 2.4 Layer 3: Activation Layer (激活层)

**职责**：根据激活模式实际激活 Skill

**三种激活形态实现**：

#### Form 1: 知识注入 (INJECTION) - 90%

**适用场景**：
- 纯指令型 Skill（无脚本）
- 知识库、最佳实践、指南类 Skill
- 不需要执行代码的 Skill

**实现方式**：
```python
def activate_injection(skill: SkillDefinition) -> str:
    """
    Form 1: 知识注入

    将 Skill 的完整指令注入到 system_prompt

    Returns:
        注入的文本内容
    """
    return skill.get_full_instructions()
```

**集成点**：
- Agent 构建 system_prompt 时，调用此方法获取注入内容
- 位置：`Agent._build_full_system_prompt()` 方法

#### Form 2: 脚本编译为 Tool (COMPILATION) - 8%

**适用场景**：
- 包含可执行脚本的 Skill
- 需要沙盒执行的操作
- 可以编译为独立工具的 Skill

**实现方式**：
```python
async def activate_compilation(
    skill: SkillDefinition,
    tool_manager: SandboxToolManager
) -> list[str]:
    """
    Form 2: 脚本编译为 Tool

    将 Skill 的脚本编译为可调用的 Tool，并注册到 ToolManager

    Returns:
        注册的 Tool 名称列表
    """
    registered_tools = []

    for script_name, script_content in skill.scripts.items():
        # 1. 编译脚本为可执行函数
        tool_func = compile_script_to_function(script_content)

        # 2. 创建 Tool 定义
        tool_def = create_tool_definition(
            name=f"{skill.skill_id}_{script_name}",
            description=f"Script from {skill.name}: {script_name}",
            func=tool_func
        )

        # 3. 注册到 ToolManager
        await tool_manager.register_tool(
            name=tool_def.name,
            func=tool_def.func,
            definition=tool_def.definition,
            scope=ToolScope.SANDBOXED
        )

        registered_tools.append(tool_def.name)

    return registered_tools
```

**集成点**：
- Agent 初始化时，编译并注册 Tools
- 需要新增脚本编译器：`ScriptCompiler`

#### Form 3: 实例化为 SkillAgentNode (INSTANTIATION) - 2%

**适用场景**：
- 需要多轮 LLM 交互的复杂 Skill
- 需要独立上下文的 Skill
- 需要独立预算管理的 Skill

**实现方式**：
```python
async def activate_instantiation(
    skill: SkillDefinition,
    parent_agent: Agent
) -> AgentNode:
    """
    Form 3: 实例化为 SkillAgentNode

    创建独立的 AgentNode 实例来执行 Skill

    Returns:
        SkillAgentNode 实例
    """
    # 1. 创建 SkillAgentNode
    skill_node = SkillAgentNode(
        skill_id=skill.skill_id,
        skill_definition=skill,
        parent=parent_agent,
        llm_provider=parent_agent.llm_provider,
        event_bus=parent_agent.event_bus,
    )

    # 2. 配置 system_prompt（使用 Skill 的 instructions）
    skill_node.system_prompt = skill.get_full_instructions()

    # 3. 继承父节点的工具和记忆
    skill_node.inherit_from_parent()

    return skill_node
```

**集成点**：
- Agent 可以通过 delegate 调用 SkillAgentNode
- 需要新增：`SkillAgentNode` 类（继承自 AgentNode）

## 三、实现计划

### 3.1 新增组件

#### 1. SkillActivator 扩展

**文件**：`loom/skills/activator.py`

**新增方法**：
```python
class SkillActivator:
    # 现有方法
    async def find_relevant_skills(...) -> list[str]:
        """Layer 2: Discovery - 已实现"""
        pass

    # 新增方法
    def determine_activation_mode(
        self,
        skill: SkillDefinition
    ) -> SkillActivationMode:
        """Layer 1: Configuration - 决定激活模式"""
        pass

    def activate_injection(
        self,
        skill: SkillDefinition
    ) -> str:
        """Layer 3: Activation - Form 1 知识注入"""
        pass

    async def activate_compilation(
        self,
        skill: SkillDefinition,
        tool_manager: SandboxToolManager
    ) -> list[str]:
        """Layer 3: Activation - Form 2 脚本编译"""
        pass

    async def activate_instantiation(
        self,
        skill: SkillDefinition,
        parent_agent: Any
    ) -> Any:
        """Layer 3: Activation - Form 3 实例化"""
        pass
```

#### 2. ScriptCompiler（脚本编译器）

**文件**：`loom/skills/script_compiler.py`（新建）

**职责**：
- 将 Skill 脚本编译为可执行的 Python 函数
- 支持沙盒执行
- 处理脚本依赖和错误

**核心方法**：
```python
class ScriptCompiler:
    def compile_script(
        self,
        script_content: str,
        script_name: str
    ) -> Callable:
        """编译脚本为可执行函数"""
        pass
```

#### 3. SkillAgentNode

**文件**：`loom/agent/skill_node.py`（新建）

**职责**：
- 继承自 AgentNode
- 专门用于执行 Skill 的独立节点
- 支持多轮 LLM 交互

**核心结构**：
```python
class SkillAgentNode(AgentNode):
    def __init__(
        self,
        skill_id: str,
        skill_definition: SkillDefinition,
        parent: Agent,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.skill_id = skill_id
        self.skill_definition = skill_definition
        self.parent = parent
```

### 3.2 修改现有组件

#### 1. Agent 集成 Skill 激活

**文件**：`loom/agent/core.py`

**修改点**：
- `__init__()` - 添加 SkillActivator 参数
- `_build_full_system_prompt()` - 集成 Form 1（知识注入）
- 新增 `_activate_skills()` - 统一的 Skill 激活入口

#### 2. SkillDefinition 元数据扩展

**文件**：`loom/skills/models.py`

**修改点**：
- 添加 `activation_mode` 字段（可选）
- 添加 `multi_turn` 字段到 metadata

### 3.3 实现顺序

**阶段 1**：Form 1 - 知识注入（最简单，优先实现）
1. 扩展 SkillActivator 添加 `determine_activation_mode()`
2. 实现 `activate_injection()`
3. 集成到 Agent 的 system_prompt 构建

**阶段 2**：Form 2 - 脚本编译（中等复杂度）
1. 创建 ScriptCompiler
2. 实现 `activate_compilation()`
3. 集成到 Agent 初始化流程

**阶段 3**：Form 3 - 实例化为 AgentNode（最复杂）
1. 创建 SkillAgentNode 类
2. 实现 `activate_instantiation()`
3. 集成到 Agent 的 delegate 机制

## 四、测试策略

### 4.1 单元测试

**测试文件**：`tests/unit/test_skills/test_activator_extended.py`

**测试覆盖**：
- `determine_activation_mode()` - 各种 Skill 类型的模式判断
- `activate_injection()` - 知识注入功能
- `activate_compilation()` - 脚本编译功能
- `activate_instantiation()` - AgentNode 实例化

### 4.2 集成测试

**测试文件**：`tests/integration/test_skill_activation.py`

**测试场景**：
- Form 1: Agent 使用注入的 Skill 知识完成任务
- Form 2: Agent 调用编译后的 Skill Tool
- Form 3: Agent 委派任务给 SkillAgentNode

## 五、总结

### 5.1 设计要点

1. **三层分离**：Configuration → Discovery → Activation
2. **三种形态**：INJECTION (90%) / COMPILATION (8%) / INSTANTIATION (2%)
3. **渐进实现**：从简单到复杂，逐步实现三种形态
4. **最小侵入**：尽量复用现有组件，减少对 Agent 核心的修改

### 5.2 关键决策

- **Form 1 默认**：大多数 Skill 使用知识注入，性能最优
- **Form 2 按需**：只有包含脚本的 Skill 才编译为 Tool
- **Form 3 极少**：只有明确需要多轮交互的 Skill 才实例化

### 5.3 下一步

完成设计后，按照实现顺序开始编码：
1. ✅ 设计文档完成
2. 🔄 实现 Form 1（知识注入）
3. ⏳ 实现 Form 2（脚本编译）
4. ⏳ 实现 Form 3（实例化）

---

**Phase 2 设计完成 ✅**
