# 工具系统 (Tool System)

## 定义

**工具系统**是 Agent 执行具体操作的机制，提供安全、可扩展的工具调用能力。

## 工具定义

```python
from loom.tools import tool

@tool(
    name="web_search",
    description="搜索网络信息"
)
async def web_search(query: str) -> str:
    """搜索网络并返回结果"""
    results = await search_api.search(query)
    return results
```

## 工具注册

```python
from loom.tools import ToolRegistry

registry = ToolRegistry()

# 注册工具
registry.register_tool(web_search)

# 或使用装饰器自动注册
@tool(name="calculator")
async def calculator(expr: str) -> float:
    return eval(expr)
```

## 工具执行

```python
# Agent 调用工具
result = await tool_registry.execute(
    tool_name="web_search",
    arguments={"query": "AI news"}
)
```

## 元工具

### create_plan

```python
{
    "name": "create_plan",
    "description": "为复杂任务创建执行计划",
    "parameters": {
        "goal": "要实现的目标",
        "steps": ["步骤1", "步骤2", ...],
        "reasoning": "为什么需要这个计划"
    }
}
```

### delegate_task

```python
{
    "name": "delegate_task",
    "description": "将子任务委派给其他专业 agent",
    "parameters": {
        "target_agent": "目标 agent ID",
        "subtask": "要委派的子任务",
        "reasoning": "为什么需要委派"
    }
}
```

## 安全等级

| 等级 | 描述 | 示例 |
|------|------|------|
| **Safe** | 无限制 | read_file, web_search |
| **Cautious** | 需要验证 | write_file, delete_file |
| **Exclusive** | 最大限制 | execute_code |

## 相关概念

- → [四范式工作](Four-Paradigms) (工具使用范式)

## 代码位置

- `loom/tools/`
- `loom/orchestration/meta_tools.py`

## 反向链接

被引用于: [四范式工作](Four-Paradigms) | [Agent API](API-Agent)
