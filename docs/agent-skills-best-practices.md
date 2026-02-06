# Agent + Skills 最佳实践指南

本指南展示 Loom Agent 中 Agent 与 Skills 系统的最佳实践模式。

## 目录

1. [核心概念](#核心概念)
2. [单 Agent + 多 Skills](#单-agent--多-skills)
3. [分形架构与记忆机制](#分形架构与记忆机制)
4. [Agent + Skills + Pipeline](#agent--skills--pipeline)
5. [生产环境配置](#生产环境配置)

---

## 核心概念

### 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Skills    │  │   Memory    │  │    Tools            │  │
│  │  Registry   │  │   Manager   │  │  (Sandbox/MCP)      │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         ▼                ▼                     ▼             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              LLM Provider (Claude/GPT/...)              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │     Child Agents (分形)        │
              │  (继承 Skills/Memory/Tools)    │
              └───────────────────────────────┘
```

### 核心组件

| 组件 | 职责 |
|------|------|
| **Agent** | 任务执行主体，协调 Skills、Memory、Tools |
| **SkillRegistry** | 管理 Skill 加载器，提供统一访问接口 |
| **SkillActivator** | 激活 Skill，注入指令到 system_prompt |
| **MemoryManager** | 管理分层记忆（LOCAL/SHARED/GLOBAL） |
| **SandboxToolManager** | 沙盒化工具执行 |

---

## 单 Agent + 多 Skills

### 基础配置

```python
import asyncio
from loom.agent import Agent
from loom.providers.llm import create_llm_provider
from loom.tools.skills import (
    SkillRegistry,
    SkillActivator,
    FilesystemSkillLoader,
)
from loom.tools import create_sandbox_toolset
from loom.events import EventBus


async def create_multi_skill_agent():
    """创建支持多 Skills 的 Agent"""

    # 1. 创建 LLM Provider
    llm = create_llm_provider("anthropic", model="claude-sonnet-4-20250514")

    # 2. 创建事件总线
    event_bus = EventBus(debug_mode=True)

    # 3. 设置 Skills
    registry = SkillRegistry()
    loader = FilesystemSkillLoader("./skills")
    registry.register_loader(loader)

    activator = SkillActivator(llm_provider=llm)

    # 4. 创建工具集
    tool_manager = await create_sandbox_toolset(
        sandbox_dir="./workspace",
        event_bus=event_bus,
    )

    # 5. 创建 Agent
    agent = Agent(
        node_id="multi-skill-agent",
        llm_provider=llm,
        event_bus=event_bus,
        sandbox_manager=tool_manager,
        skill_registry=registry,
        skill_activator=activator,
    )

    return agent
```

### 动态激活 Skills

```python
async def activate_skills_for_task(agent: Agent, task_description: str):
    """根据任务动态激活相关 Skills"""

    # 获取所有 Skill 元数据
    metadata = await agent.skill_registry.get_all_metadata()

    # 查找相关 Skills
    relevant_ids = await agent.skill_activator.find_relevant_skills(
        task_description=task_description,
        skill_metadata=metadata,
        max_skills=3,
    )

    # 激活并注入
    injected_instructions = []
    for skill_id in relevant_ids:
        skill = await agent.skill_registry.get_skill(skill_id)
        if skill:
            result = await agent.skill_activator.activate(skill)
            if result.success:
                injected_instructions.append(result.content)
                print(f"✓ 激活 Skill: {skill_id}")

    # 增强 system_prompt
    if injected_instructions:
        enhanced_prompt = agent.system_prompt + "\n\n" + "\n\n".join(injected_instructions)
        agent.system_prompt = enhanced_prompt

    return relevant_ids
```

### Skills 目录结构

```
skills/
├── code-review/
│   ├── SKILL.md
│   └── references/
│       └── checklist.md
├── debugging/
│   └── SKILL.md
├── refactoring/
│   └── SKILL.md
└── testing/
    └── SKILL.md
```

### SKILL.md 模板

```markdown
---
name: Code Review
description: 代码审查技能，检查代码质量、安全性和最佳实践
required_tools:
  - read_file
  - grep
  - glob
---

# Code Review Instructions

## 审查流程

1. **结构分析**
   - 检查文件组织
   - 验证模块依赖

2. **代码质量**
   - 命名规范
   - 函数复杂度
   - 重复代码

3. **安全检查**
   - 输入验证
   - SQL 注入
   - XSS 防护

## 输出格式

```json
{
  "summary": "审查摘要",
  "issues": [...],
  "suggestions": [...]
}
```
```

---

## 分形架构与记忆机制

### 记忆作用域

```
┌─────────────────────────────────────────────────────────┐
│                    GLOBAL (全局共享)                     │
│  ┌───────────────────────────────────────────────────┐  │
│  │              SHARED (父子双向共享)                 │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │         INHERITED (从父继承，只读)           │  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │         LOCAL (节点私有)               │  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

| 作用域 | 可读 | 可写 | 向上传播 | 向下传播 |
|--------|------|------|----------|----------|
| LOCAL | ✓ | ✓ | ✗ | ✗ |
| SHARED | ✓ | ✓ | ✓ | ✓ |
| INHERITED | ✓ | ✗ | ✗ | ✓ |
| GLOBAL | ✓ | ✓ | ✓ | ✓ |

### 分形执行示例

```python
async def fractal_task_execution(agent: Agent, complex_task: str):
    """
    分形任务执行：父节点分解任务，子节点并行执行

    执行流程：
    1. 父节点分析任务，生成执行计划
    2. 将计划写入 SHARED 记忆
    3. 创建子节点执行各步骤
    4. 子节点结果同步回父节点
    """
    from loom.fractal.memory import MemoryScope
    from loom.protocol import Task

    # 1. 分析任务，生成计划
    plan = await agent.analyze_and_plan(complex_task)

    # 2. 将计划写入 SHARED 记忆（子节点可见）
    await agent.memory.write(
        entry_id="execution-plan",
        content=plan,
        scope=MemoryScope.SHARED,
    )

    # 3. 为每个步骤创建子节点
    results = []
    for i, step in enumerate(plan["steps"]):
        # 创建子任务
        subtask = Task(
            action="execute_step",
            parameters={
                "content": step["description"],
                "step_index": i + 1,
                "total_steps": len(plan["steps"]),
                "parent_plan": plan["summary"],
                "is_plan_step": True,
            },
        )

        # 创建子节点（自动继承 SHARED 记忆）
        child = await agent._create_child_node(subtask=subtask)

        # 执行子任务
        result = await child.run(step["description"])
        results.append(result)

        # 同步子节点记忆回父节点
        await agent._sync_memory_from_child(child)

    return results
```

### 记忆共享模式

```python
async def memory_sharing_patterns(agent: Agent):
    """记忆共享的常见模式"""
    from loom.fractal.memory import MemoryScope

    # 模式 1: 写入私有记忆（不共享）
    await agent.memory.write(
        "internal-state",
        {"status": "processing"},
        scope=MemoryScope.LOCAL,
    )

    # 模式 2: 写入共享记忆（父子双向）
    await agent.memory.write(
        "task-context",
        {"goal": "完成代码审查", "files": ["main.py"]},
        scope=MemoryScope.SHARED,
    )

    # 模式 3: 写入全局记忆（所有节点可见）
    await agent.memory.write(
        "project-config",
        {"language": "python", "framework": "fastapi"},
        scope=MemoryScope.GLOBAL,
    )

    # 模式 4: 读取继承的记忆（从父节点）
    inherited = await agent.memory.read(
        "parent-context",
        search_scopes=[MemoryScope.INHERITED],
    )
```

### 子节点创建与配置继承

```python
async def create_specialized_child(agent: Agent, task: str):
    """创建专门化的子节点"""

    # 子节点可以：
    # - 添加额外 Skills
    # - 移除不需要的 Skills
    # - 添加/移除工具

    child = await agent._create_child_node(
        subtask=Task(action="specialized_task", parameters={"content": task}),
        add_skills={"debugging", "testing"},  # 额外启用
        remove_skills={"code-review"},         # 禁用
        add_tools={"profiler"},                # 额外工具
    )

    return child
```

---

## Agent + Skills + Pipeline

### Pipeline 概念

Pipeline 是将多个 Agent 串联执行的模式，每个 Agent 专注于特定任务。

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Analyst │───▶│ Planner │───▶│ Coder   │───▶│ Reviewer│
│ Agent   │    │ Agent   │    │ Agent   │    │ Agent   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
  分析需求      制定计划       编写代码       审查代码
```

### Pipeline 实现

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class PipelineStage:
    """Pipeline 阶段定义"""
    name: str
    agent: Agent
    skills: list[str]
    input_key: str
    output_key: str


class AgentPipeline:
    """Agent Pipeline 执行器"""

    def __init__(self, stages: list[PipelineStage], event_bus: EventBus):
        self.stages = stages
        self.event_bus = event_bus
        self.context: dict[str, Any] = {}

    async def execute(self, initial_input: str) -> dict[str, Any]:
        """执行完整 Pipeline"""
        self.context["input"] = initial_input

        for stage in self.stages:
            print(f"\n{'='*50}")
            print(f"Stage: {stage.name}")
            print(f"{'='*50}")

            # 激活该阶段需要的 Skills
            await self._activate_stage_skills(stage)

            # 获取输入
            stage_input = self.context.get(stage.input_key, initial_input)

            # 执行 Agent
            result = await stage.agent.run(stage_input)

            # 存储输出
            self.context[stage.output_key] = result
            print(f"✓ {stage.name} 完成")

        return self.context

    async def _activate_stage_skills(self, stage: PipelineStage):
        """激活阶段所需的 Skills"""
        for skill_id in stage.skills:
            skill = await stage.agent.skill_registry.get_skill(skill_id)
            if skill:
                result = await stage.agent.skill_activator.activate(skill)
                if result.success:
                    # 注入到 agent 的 system_prompt
                    stage.agent.system_prompt += f"\n\n{result.content}"
```

### Pipeline 使用示例

```python
async def create_code_review_pipeline():
    """创建代码审查 Pipeline"""

    llm = create_llm_provider("anthropic", model="claude-sonnet-4-20250514")
    event_bus = EventBus()
    registry = SkillRegistry()
    registry.register_loader(FilesystemSkillLoader("./skills"))

    # 创建专门化的 Agents
    analyst = Agent(
        node_id="analyst",
        llm_provider=llm,
        system_prompt="你是需求分析专家，负责理解和分解任务。",
        skill_registry=registry,
    )

    coder = Agent(
        node_id="coder",
        llm_provider=llm,
        system_prompt="你是资深开发者，负责编写高质量代码。",
        skill_registry=registry,
    )

    reviewer = Agent(
        node_id="reviewer",
        llm_provider=llm,
        system_prompt="你是代码审查专家，负责发现问题和改进建议。",
        skill_registry=registry,
    )

    # 定义 Pipeline 阶段
    stages = [
        PipelineStage(
            name="需求分析",
            agent=analyst,
            skills=["requirement-analysis"],
            input_key="input",
            output_key="analysis",
        ),
        PipelineStage(
            name="代码编写",
            agent=coder,
            skills=["coding", "testing"],
            input_key="analysis",
            output_key="code",
        ),
        PipelineStage(
            name="代码审查",
            agent=reviewer,
            skills=["code-review", "security-check"],
            input_key="code",
            output_key="review",
        ),
    ]

    pipeline = AgentPipeline(stages, event_bus)
    return pipeline


# 使用
async def main():
    pipeline = await create_code_review_pipeline()
    result = await pipeline.execute("实现一个用户认证模块")
    print(result["review"])
```

### 分形 + Pipeline 混合模式

```python
async def fractal_pipeline_execution(agent: Agent, task: str):
    """
    分形 Pipeline：父节点协调，子节点并行执行 Pipeline 阶段

    适用场景：大型任务需要并行处理多个独立模块
    """
    from loom.fractal.memory import MemoryScope

    # 1. 父节点分析任务，拆分为独立模块
    modules = await agent.analyze_modules(task)

    # 2. 将全局配置写入 GLOBAL 记忆
    await agent.memory.write(
        "project-config",
        {"task": task, "modules": [m["name"] for m in modules]},
        scope=MemoryScope.GLOBAL,
    )

    # 3. 为每个模块创建子节点 Pipeline
    import asyncio

    async def process_module(module: dict) -> dict:
        # 创建子节点
        child = await agent._create_child_node(
            add_skills={module.get("required_skill", "coding")},
        )

        # 子节点执行完整 Pipeline
        result = await child.run(f"实现模块: {module['name']}\n{module['spec']}")

        # 同步记忆
        await agent._sync_memory_from_child(child)
        return {"module": module["name"], "result": result}

    # 4. 并行执行所有模块
    results = await asyncio.gather(*[process_module(m) for m in modules])

    # 5. 父节点整合结果
    await agent.memory.write(
        "integration-results",
        results,
        scope=MemoryScope.SHARED,
    )

    return results
```

---

## 生产环境配置

### 热更新配置

```python
from loom.tools.skills import HotReloadManager

async def setup_hot_reload(registry: SkillRegistry):
    """配置 Skills 热更新"""

    manager = HotReloadManager(
        registry=registry,
        watch_dirs=["./skills"],
        poll_interval=5.0,  # 生产环境：5秒
    )

    # 监听变更
    def on_change(event):
        print(f"Skill {event.skill_id} {event.change_type}")

    manager.on_skill_change(on_change)
    await manager.start()

    return manager
```

### 数据库加载配置

```python
from loom.tools.skills import CallbackSkillLoader

async def setup_database_loader(db_pool):
    """配置数据库 Skill 加载器"""

    async def query_skill(skill_id: str) -> dict | None:
        row = await db_pool.fetchrow(
            "SELECT * FROM skills WHERE skill_id = $1 AND is_active",
            skill_id
        )
        return dict(row) if row else None

    async def query_all() -> list[dict]:
        rows = await db_pool.fetch("SELECT * FROM skills WHERE is_active")
        return [dict(r) for r in rows]

    loader = CallbackSkillLoader(
        query_skill_fn=query_skill,
        query_all_fn=query_all,
    )

    return loader
```

### 完整生产配置示例

```python
async def create_production_agent():
    """生产环境 Agent 完整配置"""

    # LLM
    llm = create_llm_provider("anthropic", model="claude-sonnet-4-20250514")

    # 事件总线
    event_bus = EventBus(debug_mode=False)

    # Skills 注册表（多加载器）
    registry = SkillRegistry()
    registry.register_loader(FilesystemSkillLoader("./skills"))
    registry.register_loader(await setup_database_loader(db_pool))

    # 热更新
    hot_reload = await setup_hot_reload(registry)

    # 工具集
    tool_manager = await create_sandbox_toolset("./workspace")

    # Agent
    agent = Agent(
        node_id="production-agent",
        llm_provider=llm,
        event_bus=event_bus,
        sandbox_manager=tool_manager,
        skill_registry=registry,
        max_iterations=50,
    )

    return agent, hot_reload
```

---

## 总结

| 模式 | 适用场景 | 特点 |
|------|----------|------|
| 单 Agent + 多 Skills | 通用任务 | 灵活、易配置 |
| 分形架构 | 复杂任务分解 | 并行、记忆共享 |
| Pipeline | 流程化任务 | 阶段清晰、可追踪 |
| 分形 + Pipeline | 大型项目 | 模块化、高并发 |

**核心原则：**
1. Skills 按需激活，避免过度注入
2. 记忆分层管理，最小必要原则
3. 子节点独立执行，结果向上汇聚
4. Pipeline 阶段清晰，职责单一
