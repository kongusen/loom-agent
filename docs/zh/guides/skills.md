# 技能系统 (Skill System) 指南

技能 (Skills) 是比工具更高层级的能力组合。如果说工具是单个函数，那么技能就是一整套解决问题的方案，包含多个工具、领域专用的提示词以及文档资料。

## 1. 概念

- **Tool (工具)**: "锤子"。一个特定的函数（如 `calculator`）。
- **Skill (技能)**: "木工能力"。一整套工具（`hammer`, `saw`） + 知识（"如何制作桌子"的提示词）。

## 2. 使用技能

技能通常通过 `SkillManager` 加载，也可以手动定义。

```python
from loom.skills import Skill, SkillManager

# 1. 手动定义技能
coding_skill = Skill(
    name="PythonCoding",
    description="编写和执行 Python 代码的能力",
    tools=[run_python_code],
    prompts={"system": "你是一个 Python 专家..."}
)

# 2. 注入 Agent
agent = Agent(
    name="Coder",
    llm=llm,
    skills=[coding_skill]
)
```

## 3. 技能管理器 (Skill Manager)

对于大型 Agent，你不需要一次性加载所有工具。`SkillManager` 允许动态发现和加载技能。

```python
manager = SkillManager(skill_dir="./my_skills")

# 检索与任务相关的技能
relevant_skills = await manager.retrieve("analyze data")
agent.add_skills(relevant_skills)
```

## 4. 技能目录结构

标准技能在磁盘上的结构如下：

```
my_skills/
  data_analysis/
    skill.yaml       # 元数据
    tools.py         # @tool 定义
    prompts.yaml     # 系统提示词
    docs/            # RAG 文档资料
```
