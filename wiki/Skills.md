# Skills

## 定义

**Skills** 是 Progressive Disclosure 的能力加载机制，只在需要时加载相关技能。

## 核心思想

不是一次性加载所有能力，而是：
1. 分析任务需求
2. 检索相关 Skills
3. 动态加载到上下文

这样可以：
- 减少 Token 消耗
- 提高响应速度
- 避免信息过载

## Skill 定义

```python
from loom.skills import SkillDefinition

skill = SkillDefinition(
    skill_id="python-programming",
    name="Python 编程",
    description="Python 语言相关的编程知识和最佳实践",
    instructions="""
你是 Python 编程专家，熟知：
- Python 语法和特性
- 常用库和框架
- 最佳实践和设计模式
- 性能优化技巧
""",
    keywords=["python", "编程", "代码", "开发"],
    examples=[
        "用 Python 实现快速排序",
        "优化这段 Python 代码"
    ]
)
```

## Skill 注册

```python
from loom.skills import SkillRegistry

registry = SkillRegistry()
await registry.register_skill(skill)
```

## Progressive Disclosure

```python
# 1. 分析任务
task_description = "用 Python 实现一个爬虫"

# 2. 检索相关 Skills
skills = await skill_registry.find_relevant(task_description)

# 3. 加载到上下文
for skill in skills:
    messages.append({
        "role": "system",
        "content": skill.get_full_instructions()
    })
```

## 相关概念

- → [四范式工作](Four-Paradigms)

## 代码位置

- `loom/skills/`

## 反向链接

被引用于: [Agent API](API-Agent) | [四范式工作](Four-Paradigms)
