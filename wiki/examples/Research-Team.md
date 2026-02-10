# 研究小组示例

## 场景

创建一个研究小组，包含研究员、撰稿人、编辑三个角色，协作完成一篇文章。

## 完整代码

```python
import asyncio
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.fractal import CompositeNode
from loom.fractal.strategies import SequentialStrategy
from loom.runtime import Task

async def main():
    # 配置 LLM
    llm = OpenAIProvider(api_key="your-api-key")

    # 创建研究员
    researcher_agent = Agent.create(
        llm,
        node_id="researcher",
        system_prompt="你是专业的研究员，擅长收集和分析信息。",
    )

    # 创建撰稿人
    writer_agent = Agent.create(
        llm,
        node_id="writer",
        system_prompt="你是专业的撰稿人，擅长将研究结果写成文章。",
    )

    # 创建编辑
    editor_agent = Agent.create(
        llm,
        node_id="editor",
        system_prompt="你是专业的编辑，负责校对和润色文章。",
    )

    # 组合成研究小组（顺序执行）
    research_team = CompositeNode(
        node_id="research_team",
        children=[researcher_agent, writer_agent, editor_agent],
        strategy=SequentialStrategy()
    )

    # 执行任务
    task = Task(
        task_id="article-1",
        action="write_article",
        parameters={
            "topic": "人工智能的发展历史",
            "requirements": "1000字左右，客观准确"
        }
    )

    result = await research_team.execute_task(task)
    print(result.result)

if __name__ == "__main__":
    asyncio.run(main())
```

## 执行流程

```
研究员 → 收集信息和分析
    ↓
撰稿人 → 撰写文章
    ↓
编辑 → 校对润色
    ↓
完成文章
```

## 并行执行

```python
from loom.fractal.strategies import ParallelStrategy

# 并行执行多个研究员
parallel_research = CompositeNode(
    node_id="parallel_research",
    children=[researcher1, researcher2, researcher3],
    strategy=ParallelStrategy()
)
```

## 智能路由

```python
from loom.fractal.strategies import SelectStrategy

# 根据任务类型路由
router = CompositeNode(
    node_id="router",
    children=[researcher, coder, writer],
    strategy=SelectStrategy(
        selector=lambda task: task.metadata.get("role")
    )
)

# 使用
task = Task(
    task_id="task-1",
    metadata={"role": "researcher"}  # 路由到研究员
)
```

## 下一步

- [工具开发](Tool-Development)
- [Agent API](API-Agent)

## 代码位置

- `examples/research_team.py`

## 反向链接

被引用于: [Home](Home) | [分形架构](Fractal-Architecture)
