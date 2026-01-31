# AgentConfig 继承使用指南

**版本**: 1.0
**更新日期**: 2026-01-31

---

## 概述

Loom Agent 框架支持 **AgentConfig 继承机制**，允许父 Agent 在创建子节点时动态定制子节点的配置。这个机制在分形架构中特别有用，可以根据不同的子任务需求灵活调整子节点的能力。

### 核心特性

- ✅ **完整实现**: `AgentConfig.inherit()` 方法已完整实现
- ✅ **自动继承**: 子节点自动继承父节点的配置
- ✅ **增量覆盖**: 支持添加或移除 Skills 和 Tools
- ✅ **按需使用**: 机制已就绪，可在需要时直接使用

### 继承规则

在分形架构中，父子节点之间的配置遵循以下继承规则：

| 组件 | 继承方式 | 说明 |
|------|---------|------|
| `skill_registry` | 共享 | 全局单例，所有节点共享同一个注册表 |
| `tool_registry` | 共享 | 全局单例，所有节点共享同一个注册表 |
| `event_bus` | 共享 | 全局单例，所有节点共享同一个事件总线 |
| `sandbox_manager` | 共享 | 全局单例，所有节点共享同一个沙盒管理器 |
| `config` | 继承（可覆盖） | 子节点继承父节点配置，可通过参数增量修改 |
| `_active_skills` | 独立 | 每个节点独立维护自己的激活状态 |
| `fractal_memory` | 独立（有继承关系） | 子节点创建新的 FractalMemory，但可访问父节点记忆 |

---

## API 参考

### AgentConfig.inherit()

```python
@classmethod
def inherit(
    cls,
    parent: "AgentConfig",
    add_skills: set[str] | None = None,
    remove_skills: set[str] | None = None,
    add_tools: set[str] | None = None,
    remove_tools: set[str] | None = None,
) -> "AgentConfig":
    """
    从父配置继承并创建新的子配置

    Args:
        parent: 父节点的 AgentConfig
        add_skills: 子节点额外启用的 Skills
        remove_skills: 子节点禁用的 Skills
        add_tools: 子节点额外启用的工具
        remove_tools: 子节点禁用的工具

    Returns:
        新的 AgentConfig 实例
    """
```

### Agent._create_child_node()

```python
async def _create_child_node(
    self,
    subtask: Task,
    context_hints: list[str],
    add_skills: set[str] | None = None,
    remove_skills: set[str] | None = None,
    add_tools: set[str] | None = None,
    remove_tools: set[str] | None = None,
) -> "Agent":
    """
    创建子节点并智能分配上下文

    子节点会自动继承父节点的配置，并可通过参数进行增量修改。
    """
```

---

## 使用场景

### 场景 1: 按规划步骤定制 Skills

当使用规划能力（Planning）将复杂任务分解为多个步骤时，不同的步骤可能需要不同的专业知识。通过 AgentConfig 继承，可以为每个步骤启用相应的 Skills。

**示例：全栈开发任务**

```python
async def _execute_plan(self, plan_args: dict, parent_task: Task) -> str:
    """执行规划 - 根据步骤类型定制 Skills"""

    steps = plan_args.get("steps", [])
    results = []

    for idx, step in enumerate(steps):
        # 根据步骤内容判断需要的 Skills
        add_skills = set()

        if "database" in step.lower() or "sql" in step.lower():
            # 数据库相关步骤：启用数据库设计 Skill
            add_skills.add("database-design")
            add_skills.add("sql-optimization")

        elif "frontend" in step.lower() or "ui" in step.lower():
            # 前端相关步骤：启用前端设计 Skill
            add_skills.add("frontend-design")
            add_skills.add("react-patterns")

        elif "api" in step.lower() or "backend" in step.lower():
            # 后端相关步骤：启用 API 设计 Skill
            add_skills.add("api-design")
            add_skills.add("microservices")

        # 创建子节点，传入定制的 Skills
        child_agent = await self._create_child_node(
            subtask=subtask,
            context_hints=context_hints,
            add_skills=add_skills  # 增量添加 Skills
        )

        result = await child_agent.execute_task(subtask)
        results.append(result)

    return self._aggregate_results(results)
```

**效果**：
- ✅ 每个子任务只加载相关的专业知识
- ✅ 减少无关 Skills 的干扰
- ✅ 提升任务执行的精准度

---

### 场景 2: 按委派目标定制工具

当委派任务给子节点时，可以根据子任务的特性动态添加所需的工具，而不是让所有子节点都拥有全部工具。

**示例：数据处理任务**

```python
async def _auto_delegate(self, args: dict, parent_task: Task) -> str:
    """自动委派 - 根据任务需求定制工具"""

    subtask_description = args.get("subtask_description", "")
    add_tools = set()
    remove_tools = set()

    # 根据任务描述判断需要的工具
    if "数据库" in subtask_description or "database" in subtask_description.lower():
        # 数据库操作任务：添加数据库工具
        add_tools.add("postgres")
        add_tools.add("redis")
        add_tools.add("mongodb")

    if "文件处理" in subtask_description or "file" in subtask_description.lower():
        # 文件处理任务：添加文件操作工具
        add_tools.add("file_read")
        add_tools.add("file_write")
        add_tools.add("file_search")

    if "网络请求" in subtask_description or "http" in subtask_description.lower():
        # 网络请求任务：添加 HTTP 工具
        add_tools.add("http_get")
        add_tools.add("http_post")

    # 创建子节点，传入定制的工具
    child_agent = await self._create_child_node(
        subtask=subtask,
        context_hints=context_hints,
        add_tools=add_tools  # 增量添加工具
    )

    result = await child_agent.execute_task(subtask)
    return self._format_result(result)
```

**效果**：
- ✅ 子节点只获得完成任务所需的工具
- ✅ 减少工具列表的复杂度
- ✅ 提升 LLM 选择工具的准确性

---

### 场景 3: 限制子节点能力（安全考虑）

在某些场景下，出于安全考虑，需要限制子节点的能力，防止子节点执行危险操作。

**示例：沙盒执行环境**

```python
async def execute_untrusted_code(self, code: str, parent_task: Task) -> str:
    """执行不受信任的代码 - 限制子节点能力"""

    # 移除危险工具
    remove_tools = {
        "bash",              # 禁止执行系统命令
        "system_command",    # 禁止系统调用
        "file_write",        # 禁止写入文件
        "network_access",    # 禁止网络访问
    }

    # 只保留安全的工具
    add_tools = {
        "safe_eval",         # 安全的代码执行
        "memory_read",       # 只读内存访问
    }

    # 创建受限的子节点
    child_agent = await self._create_child_node(
        subtask=Task(
            task_id=f"{parent_task.task_id}:sandbox",
            action="execute",
            parameters={"content": f"Execute code in sandbox: {code}"}
        ),
        context_hints=[],
        add_tools=add_tools,
        remove_tools=remove_tools  # 移除危险工具
    )

    result = await child_agent.execute_task(subtask)
    return self._sanitize_result(result)
```

**效果**：
- ✅ 子节点无法执行危险操作
- ✅ 提供安全的沙盒执行环境
- ✅ 防止恶意代码破坏系统

---

## 最佳实践

### 1. 按需使用，避免过度定制

**推荐**：
```python
# 只在确实需要时才定制配置
if task_requires_special_skills:
    add_skills = {"special-skill"}
else:
    add_skills = None  # 使用默认继承
```

**避免**：
```python
# 不要为每个子任务都定制配置
add_skills = {"skill1", "skill2", "skill3"}  # 过度定制
```

### 2. 使用集合（set）而非列表

**推荐**：
```python
add_skills = {"skill1", "skill2"}  # 使用 set，自动去重
```

**避免**：
```python
add_skills = ["skill1", "skill2", "skill1"]  # 使用 list，可能重复
```

### 3. 安全优先：移除危险工具

当处理不受信任的输入时，优先考虑移除危险工具：

```python
# 安全第一
remove_tools = {"bash", "system_command", "file_write"}
child_agent = await self._create_child_node(
    subtask=subtask,
    context_hints=context_hints,
    remove_tools=remove_tools
)
```

### 4. 文档化定制逻辑

为配置定制逻辑添加清晰的注释：

```python
# 数据库步骤需要 SQL 优化 Skill
if "database" in step.lower():
    add_skills = {"sql-optimization"}  # 原因：提升查询性能
```

---

## 注意事项

### 1. 共享组件不受继承影响

以下组件是全局共享的，不会因为配置继承而改变：
- `skill_registry`: 所有节点共享同一个 Skill 注册表
- `tool_registry`: 所有节点共享同一个工具注册表
- `event_bus`: 所有节点共享同一个事件总线
- `sandbox_manager`: 所有节点共享同一个沙盒管理器

### 2. 激活状态是独立的

每个节点的 `_active_skills` 是独立维护的，即使父子节点启用了相同的 Skills，它们的激活状态也是独立的。

### 3. 配置继承不是强制的

如果不传入 `add_skills`/`remove_skills`/`add_tools`/`remove_tools` 参数，子节点会完全继承父节点的配置，这在大多数情况下是合适的。

### 4. 性能考虑

频繁的配置定制可能会增加系统复杂度，建议只在确实需要时才使用。

---

## 总结

AgentConfig 继承机制为 Loom Agent 框架提供了灵活的配置管理能力：

✅ **已完整实现**: `AgentConfig.inherit()` 和 `_create_child_node()` 已完整实现
✅ **按需使用**: 机制已就绪，可在需要时直接使用
✅ **三大场景**: 支持按步骤定制 Skills、按任务定制工具、限制子节点能力
✅ **安全可靠**: 支持移除危险工具，提供安全的沙盒执行环境

**何时使用**：
- 不同子任务需要不同的专业知识（Skills）
- 不同子任务需要不同的工具集
- 需要限制子节点的能力（安全考虑）

**何时不使用**：
- 子任务与父任务能力需求相同
- 默认继承已经足够
- 避免过度定制增加系统复杂度

---

## 相关文档

- [Agent 基础使用](./getting-started.md)
- [Skill 系统](../../wiki/Skills.md)
- [工具系统](../../wiki/Tool-System.md)
- [分形架构](../../wiki/Fractal-Architecture.md)
- [AgentConfig API](./api-reference.md)

---

**文档版本**: 1.0
**最后更新**: 2026-01-31
**维护者**: Loom Agent Team
