# Skills

技能系统根据用户输入自动匹配并激活技能，将专业指令注入 Agent。

## 定义与注册技能

```python
from loom import SkillRegistry
from loom.types import Skill, SkillTrigger

registry = SkillRegistry()

registry.register(Skill(
    name="python-expert",
    trigger=SkillTrigger(type="keyword", keywords=["python", "pip", "asyncio"]),
    instructions="你是资深 Python 专家，回答要包含最佳实践和代码示例。",
    priority=0.9,
))

registry.register(Skill(
    name="code-reviewer",
    trigger=SkillTrigger(type="pattern", pattern=r"\bdef\s+\w+|class\s+\w+"),
    instructions="你是代码审查专家，关注代码质量、性能和安全性。",
    priority=0.8,
))
```

## 自动激活

```python
query = "用 python asyncio 写一个并发爬虫"
activations = await registry.activate(query)
for a in activations:
    print(f"{a.skill.name}: score={a.score:.2f}")
# python-expert: score=0.60
```

## 注入 Agent

```python
from loom import Agent, AgentConfig

skill_prompt = "\n".join(
    a.skill.instructions for a in activations if a.skill.instructions
)
agent = Agent(
    provider=provider,
    config=AgentConfig(system_prompt=skill_prompt, max_steps=2),
)
result = await agent.run(query)
```

## 触发器类型

| 类型 | 字段 | 说明 |
|------|------|------|
| `keyword` | `keywords` | 关键词匹配 |
| `pattern` | `pattern` | 正则表达式匹配 |
| `semantic` | `threshold` | 语义相似度（需 embedder） |
| `custom` | `evaluator` | 自定义函数 `(text) -> float` |

## API 参考

```python
# Skill
@dataclass
class Skill:
    name: str
    instructions: str       # 注入的系统提示
    trigger: SkillTrigger
    priority: float = 0.5

# SkillRegistry
registry = SkillRegistry()
registry.register(skill)
registry.all() -> list[Skill]
await registry.activate(query) -> list[SkillActivation]
```

> 完整示例：[`examples/demo/08_skills.py`](../examples/demo/08_skills.py)
