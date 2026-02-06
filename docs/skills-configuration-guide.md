# Skills 配置指南

本指南介绍如何在 Loom Agent 中配置和使用 Skills 系统。

## 目录

1. [概述](#概述)
2. [Skills 数据模型](#skills-数据模型)
3. [文件系统加载](#文件系统加载)
4. [数据库加载](#数据库加载)
5. [热更新配置](#热更新配置)
6. [与 Agent 集成](#与-agent-集成)
7. [最佳实践](#最佳实践)

---

## 概述

Skills 是可复用的能力包，通过**知识注入**模式工作：将 Skill 指令注入到 Agent 的 system_prompt 中。

### 核心概念

| 概念 | 说明 |
|------|------|
| **SkillDefinition** | Skill 的完整定义（指令、工具依赖、参考资料） |
| **SkillLoader** | 加载器接口（文件系统、数据库等） |
| **SkillRegistry** | 统一注册表，管理多个 Loader |
| **SkillActivator** | 激活控制器，执行注入 |

### 架构图

```
┌─────────────────────────────────────────────────────────┐
│                    SkillRegistry                        │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ _runtime_skills │  │         loaders[]           │  │
│  └─────────────────┘  └──────────────┬──────────────┘  │
└───────────────────────────────────────┼─────────────────┘
                                        │
         ┌──────────────────────────────┼──────────────────┐
         ▼                              ▼                  ▼
  FilesystemSkillLoader      CallbackSkillLoader    CustomLoader
         │                              │
         ▼                              ▼
     SKILL.md                       Database
```

---

## Skills 数据模型

### SkillDefinition 字段

```python
@dataclass
class SkillDefinition:
    skill_id: str           # 唯一标识
    name: str               # 显示名称
    description: str        # 描述（用于能力发现）
    instructions: str       # 执行指令（Markdown）
    required_tools: list[str] = []  # 依赖的工具
    references: dict[str, str] = {} # 参考资料
    metadata: dict = {}     # 扩展元数据
    source: str = "unknown" # 来源类型
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `skill_id` | ✅ | 唯一标识，用于加载和激活 |
| `name` | ✅ | 人类可读的名称 |
| `description` | ✅ | 简短描述，用于语义搜索 |
| `instructions` | ✅ | 注入到 system_prompt 的指令 |
| `required_tools` | ❌ | 依赖的工具列表，激活时验证 |
| `references` | ❌ | 参考资料 `{filename: content}` |
| `metadata` | ❌ | 自定义元数据 |
| `source` | ❌ | 来源：`filesystem`/`database`/`runtime` |

---

## 文件系统加载

### 目录结构

```
skills/
├── code-review/
│   ├── SKILL.md          # 必需：Skill 定义
│   └── references/       # 可选：参考资料
│       ├── checklist.md
│       └── examples.py
├── debugging/
│   └── SKILL.md
└── refactoring/
    └── SKILL.md
```

### SKILL.md 格式

```markdown
---
name: Code Review
description: 代码审查技能，检查代码质量和最佳实践
required_tools:
  - read_file
  - grep
---

# Code Review Instructions

## 审查流程

1. 首先阅读代码结构
2. 检查命名规范
3. 验证错误处理
...
```

### 代码示例

```python
from loom.tools.skills import FilesystemSkillLoader, SkillRegistry

# 创建加载器
loader = FilesystemSkillLoader("/path/to/skills")

# 注册到 Registry
registry = SkillRegistry()
registry.register_loader(loader)

# 加载 Skill
skill = await registry.get_skill("code-review")
print(skill.instructions)
```

---

## 数据库加载

### 推荐表结构

```sql
CREATE TABLE skills (
    id UUID PRIMARY KEY,
    skill_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    instructions TEXT NOT NULL,
    required_tools JSONB DEFAULT '[]',
    references JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 方式一：CallbackSkillLoader（推荐）

```python
from loom.tools.skills import CallbackSkillLoader, SkillRegistry

# 定义查询函数
async def query_skill(skill_id: str) -> dict | None:
    row = await db.fetch_one(
        "SELECT * FROM skills WHERE skill_id = $1 AND is_active",
        skill_id
    )
    if not row:
        return None
    return {
        "skill_id": row["skill_id"],
        "name": row["name"],
        "description": row["description"],
        "instructions": row["instructions"],
        "required_tools": row["required_tools"],
    }

async def query_all() -> list[dict]:
    rows = await db.fetch_all("SELECT * FROM skills WHERE is_active")
    return [dict(r) for r in rows]

# 创建加载器
loader = CallbackSkillLoader(
    query_skill_fn=query_skill,
    query_all_fn=query_all,
)

registry = SkillRegistry()
registry.register_loader(loader)
```

### 方式二：继承 DatabaseSkillLoader

```python
from loom.tools.skills import DatabaseSkillLoader

class PostgresSkillLoader(DatabaseSkillLoader):
    def __init__(self, pool):
        self.pool = pool

    async def query_skill(self, skill_id: str) -> dict | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM skills WHERE skill_id = $1",
                skill_id
            )

    async def query_all_skills(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM skills")
            return [dict(r) for r in rows]

    async def query_skill_metadata(self) -> list[dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT skill_id, name, description FROM skills"
            )
            return [dict(r) for r in rows]
```

---

## 热更新配置

热更新允许在运行时修改 SKILL.md 文件，自动重新加载。

### 基本用法

```python
from loom.tools.skills import (
    HotReloadManager,
    SkillRegistry,
    FilesystemSkillLoader,
)

# 设置 Registry
registry = SkillRegistry()
loader = FilesystemSkillLoader("/path/to/skills")
registry.register_loader(loader)

# 创建热更新管理器
manager = HotReloadManager(
    registry=registry,
    watch_dirs=["/path/to/skills"],
    poll_interval=1.0,  # 轮询间隔（秒）
)

# 启动监听
await manager.start()
```

### 监听变更事件

```python
from loom.tools.skills import SkillChangeEvent

def on_skill_change(event: SkillChangeEvent):
    print(f"Skill {event.skill_id} {event.change_type}")
    print(f"Old hash: {event.old_version.content_hash if event.old_version else None}")
    print(f"New hash: {event.new_version.content_hash if event.new_version else None}")

manager.on_skill_change(on_skill_change)
```

### 与 EventBus 集成

```python
from loom.events import EventBus

event_bus = EventBus()

manager = HotReloadManager(
    registry=registry,
    watch_dirs=["/path/to/skills"],
    event_bus=event_bus,  # 自动发布 skill.changed 事件
)

# Agent 可以订阅事件
@event_bus.subscribe("skill.changed")
async def handle_skill_change(data):
    skill_id = data["skill_id"]
    # 重新加载已激活的 Skill...
```

---

## 与 Agent 集成

### 基本集成流程

```python
from loom.agent import Agent
from loom.tools.skills import (
    SkillRegistry,
    SkillActivator,
    FilesystemSkillLoader,
    HotReloadManager,
)

# 1. 设置 Registry
registry = SkillRegistry()
loader = FilesystemSkillLoader("/path/to/skills")
registry.register_loader(loader)

# 2. 创建 Activator
activator = SkillActivator(
    llm_provider=llm,
    tool_manager=tool_manager,
)

# 3. 创建 Agent 时传入
agent = Agent(
    llm_provider=llm,
    skill_registry=registry,
    skill_activator=activator,
)
```

### 手动激活 Skill

```python
# 获取 Skill
skill = await registry.get_skill("code-review")

# 激活并获取注入内容
result = await activator.activate(
    skill=skill,
    tool_manager=tool_manager,
    event_bus=event_bus,
)

if result.success:
    # 将指令注入到 system_prompt
    enhanced_prompt = f"{base_prompt}\n\n{result.content}"
else:
    print(f"激活失败: {result.error}")
```

### 自动发现相关 Skills

```python
# 获取所有 Skill 元数据
metadata = await registry.get_all_metadata()

# 根据任务描述查找相关 Skills
task = "请帮我审查这段代码的安全性"
relevant_ids = await activator.find_relevant_skills(
    task_description=task,
    skill_metadata=metadata,
    max_skills=3,
)

# 激活找到的 Skills
for skill_id in relevant_ids:
    skill = await registry.get_skill(skill_id)
    result = await activator.activate(skill)
    # ...
```

### 带工具的 Skill 激活

```python
from loom.tools.skills import CallbackSkillLoader, SkillWithTools

# 数据库加载器支持带工具加载
loader = CallbackSkillLoader(query_skill_fn=query_fn)

# 加载 Skill 及其捆绑工具
skill_with_tools: SkillWithTools = await loader.load_skill_with_tools("data-analysis")

# 注册捆绑的工具
for tool in skill_with_tools.tools:
    tool_manager.register_tool(
        name=tool.name,
        description=tool.description,
        parameters=tool.parameters,
        handler=create_handler(tool.implementation),
    )

# 激活 Skill
result = await activator.activate(skill_with_tools.skill)
```

---

## 最佳实践

### Skill 设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个 Skill 专注一个任务领域 |
| **自包含** | 指令应完整，不依赖外部上下文 |
| **可组合** | 多个 Skill 可以同时激活 |
| **渐进式** | 从简单开始，按需扩展 |

### SKILL.md 编写建议

```markdown
---
name: 清晰的名称
description: 简短描述（用于语义搜索）
required_tools:
  - 只列出必需的工具
---

# 标题

## 何时使用
明确说明适用场景。

## 执行步骤
1. 具体步骤
2. 可操作的指令
3. 预期输出

## 注意事项
- 边界条件
- 常见错误
```

### 性能优化

#### 使用元数据查询

```python
# ✅ 推荐：只获取元数据（轻量）
metadata = await registry.get_all_metadata()

# ❌ 避免：获取完整 Skill（重量）
all_skills = await registry.get_all_skills()
```

#### 缓存策略

```python
# Registry 内置缓存
registry = SkillRegistry()

# 手动清除缓存（热更新后自动清除）
registry.clear_cache()
```

#### 热更新轮询间隔

```python
# 开发环境：快速响应
manager = HotReloadManager(poll_interval=0.5)

# 生产环境：降低 CPU 开销
manager = HotReloadManager(poll_interval=5.0)
```

### 错误处理

#### 激活失败处理

```python
result = await activator.activate(skill)

if not result.success:
    if result.missing_tools:
        # 缺少依赖工具
        logger.warning(f"Missing tools: {result.missing_tools}")
        # 可选：动态注册缺失工具
    else:
        # 其他错误
        logger.error(f"Activation failed: {result.error}")
```

#### 加载器容错

```python
# 多加载器场景：一个失败不影响其他
registry.register_loader(filesystem_loader)
registry.register_loader(database_loader)

# get_skill 会依次尝试所有加载器
skill = await registry.get_skill("my-skill")
```

### 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Skill 加载返回 None | 目录结构错误 | 检查 `skills/<id>/SKILL.md` 路径 |
| 热更新不生效 | 缓存未清除 | 确认 HotReloadManager 已启动 |
| 工具依赖验证失败 | 工具未注册 | 先注册工具再激活 Skill |
| 数据库查询返回空 | 字段映射错误 | 检查返回字典的 key 名称 |

### 目录结构示例

```
my-project/
├── skills/                    # Skill 定义目录
│   ├── code-review/
│   │   ├── SKILL.md
│   │   └── references/
│   └── debugging/
│       └── SKILL.md
├── loom/
│   └── agent/
│       └── core.py           # Agent 集成代码
└── config/
    └── skills.yaml           # 可选：Skill 配置
```

---

## 总结

Skills 系统提供了灵活的能力扩展机制：

1. **文件系统加载**：适合本地开发和版本控制
2. **数据库加载**：适合动态管理和多租户场景
3. **热更新**：支持运行时修改，无需重启
4. **知识注入**：通过 system_prompt 增强 Agent 能力

选择合适的加载方式，结合热更新和事件系统，可以构建灵活、可维护的 Agent 能力体系。
