# 技能系统

`loom/tools/skills/` 实现了基于 Anthropic Claude Skills 标准的技能系统，支持渐进式披露和多种激活模式。

## 文件结构

```
loom/tools/skills/
├── models.py           # SkillDefinition, ActivationResult
├── registry.py         # SkillRegistry - 技能注册表
├── activator.py        # SkillActivator - 技能激活器
├── loader.py           # SkillLoader 抽象接口
├── filesystem_loader.py# 文件系统加载器
├── database_loader.py  # 数据库加载器
└── hot_reload.py       # 热重载支持
```

## Skill 定义格式

遵循 Anthropic 标准，每个 Skill 是一个目录：

```
skills/
└── code_review/
    ├── SKILL.md          # YAML frontmatter + Markdown 指令
    └── references/       # 可选：参考资料
        └── style_guide.md
```

### SKILL.md 格式

```markdown
---
name: code_review
description: 代码审查技能，提供专业的代码质量分析
required_tools:
  - read_file
  - search_files
knowledge_domains:
  - software_engineering
  - code_quality
---

## Instructions

你是一个代码审查专家。请按照以下步骤进行审查：

1. 阅读代码文件
2. 检查代码质量
3. 提供改进建议
```

## SkillDefinition

```python
@dataclass
class SkillDefinition:
    skill_id: str              # 唯一标识
    name: str                  # 技能名称
    description: str           # 描述（用于能力发现）
    instructions: str          # 执行指令（SKILL.md 正文）
    required_tools: list[str]  # 需要的工具列表
    references: dict[str, str] # 参考资料 {filename: content}
    metadata: dict             # 其他元数据
    source: str                # 来源类型
    knowledge_domains: list[str]  # 知识领域
    search_guidance: str       # 搜索指引
```

## 渐进式披露（Progressive Disclosure）

Skill 的使用分为三个层次：

### Tier 1 — Discovery（发现）

Agent 获取所有 Skill 的元数据（name + description），了解有哪些能力可用。

```python
# Agent 的 system_prompt 中自动注入
## Available Skills
- **code_review**: 代码审查技能，提供专业的代码质量分析
  - Required Tools: read_file, search_files
```

### Tier 2 — Activation（激活）

当 Agent 判断某个 Skill 与当前任务相关时，激活该 Skill：

```python
result = await agent._activate_skill("code_review")
# result.success == True
# result.content → Skill 指令被注入到 system_prompt
```

### Tier 3 — Instantiation（实例化）

对于复杂 Skill，可以创建独立的子节点来执行。

## SkillActivator

负责 Skill 的激活流程：

```python
activator = SkillActivator(
    llm_provider=llm,
    tool_registry=tool_registry,
    tool_manager=sandbox_manager,
)

# 查找相关 Skill
relevant_ids = await activator.find_relevant_skills(
    task_description="审查这段 Python 代码",
    skill_metadata=all_metadata,
    max_skills=5,
)

# 激活 Skill
result: ActivationResult = await activator.activate(
    skill=skill_def,
    tool_manager=sandbox_manager,
    event_bus=event_bus,
)
```

### ActivationResult

```python
@dataclass
class ActivationResult:
    success: bool
    mode: str              # "injection" / "compilation" / "instantiation"
    content: str | None    # 注入的指令内容
    tool_names: list[str]  # 绑定的工具
    node: Any | None       # 实例化的子节点
    error: str | None
    missing_tools: list[str]  # 缺失的工具
```

## SkillRegistry

技能注册表，管理所有可用的 Skill：

```python
registry = SkillRegistry()

# 注册 Skill
await registry.register(skill_def)

# 获取 Skill
skill = await registry.get_skill("code_review")

# 获取所有元数据（用于 Discovery）
metadata = await registry.get_all_metadata()
```

## SkillLoader

技能加载器抽象，支持多种来源：

| 加载器 | 说明 |
|--------|------|
| `FilesystemLoader` | 从文件系统目录加载 SKILL.md |
| `DatabaseLoader` | 从数据库加载 |

```python
# 文件系统加载
loader = FilesystemLoader(skills_dir="/path/to/skills")
skills = await loader.load_all()

# 在 Agent.create 中使用
agent = Agent.create(
    llm,
    tool_config=ToolConfig(skills_dir="/path/to/skills"),
)
```

## 热重载

`hot_reload.py` 支持开发时 Skill 文件变更的自动重载。
