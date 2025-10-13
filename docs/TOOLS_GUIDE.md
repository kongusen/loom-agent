# Loom 工具开发指南（Tools Guide）

本指南面向使用 Loom 框架的开发者，介绍如何以最小成本编写、注册与使用工具（Tool），并给出并发、安全与测试的最佳实践。

## 什么时候用 @loom.tool，什么时候继承 BaseTool？

- 推荐：使用装饰器 `@loom.tool` 将现有 Python 函数快速“提升”为 Tool，零样板、自动参数模型、支持同步与异步函数。
- 需要强定制时：继承 `loom.interfaces.tool.BaseTool`，自行实现 `name/description/args_schema/run()`，适用于需要更复杂生命周期管理或自定义属性的场景。

## 快速开始：用装饰器创建工具

```python
import loom
from typing import List

@loom.tool(description="Sum a list of numbers")
def sum_list(nums: List[float]) -> float:
    return sum(nums)

SumTool = sum_list
agent = loom.agent(provider="openai", model="gpt-4o", tools=[SumTool()])
```

要点：
- `name` 默认为函数名（`sum_list`），可在装饰器参数中自定义。
- `description` 若不填，从函数 docstring 推断；建议简洁说明用途与参数。
- `args_schema` 自动从函数的参数注解推断；也可传入自定义 Pydantic 模型。
- 同步函数会在后台线程池执行；异步函数（`async def`）原生运行。

## 自定义参数模型（args_schema）

当自动推断不满足需求（如需要描述/校验或复杂嵌套）时，可自定义参数模型：

```python
from pydantic import BaseModel, Field

class SearchArgs(BaseModel):
    query: str = Field(description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Top results")

@loom.tool(name="search", description="Perform a local search", args_schema=SearchArgs)
def search_docs(query: str, top_k: int = 5) -> str:
    return f"Search '{query}', top_k={top_k}"
```

注意：模型字段名需与函数参数名一致（含默认值）。

## 并发安全与最佳实践

- 使用装饰器参数 `concurrency_safe` 指定工具是否可以并发执行：
  - `True`（默认）：I/O 安全读操作、纯计算函数；调度器可并发执行。
  - `False`：写文件、修改全局状态、非线程安全依赖等；调度器会序列化执行。
- 长耗时/阻塞型同步函数：装饰器会丢到线程池执行，但更推荐改为 `async` 版本（利于协程调度与吞吐）。
- 避免在 Tool 内部自行创建事件循环或阻塞主线程。

## 继承 BaseTool（进阶）

```python
from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool

class WriteArgs(BaseModel):
    path: str = Field(description="File path")
    content: str = Field(description="Content to write")

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write content to a file"
    args_schema = WriteArgs

    async def run(self, path: str, content: str) -> str:  # type: ignore[override]
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {path}"

    @property
    def is_concurrency_safe(self) -> bool:
        return False  # 写操作非并发安全
```

## 命名、描述与 UX 建议

- `name`：小写、下划线风格（如 `read_file`）；避免与其他工具重名。
- `description`：一句话清晰说明用途；如有敏感操作（写/删/网络），请显式标注。
- 入参：提供有意义的默认值与范围；必要时增加描述（Field.description）。

## 在 Agent 中注册与使用

- 直接传入 Tool 实例列表：

```python
from loom.builtin.tools import ReadFileTool, WriteFileTool
agent = loom.agent(provider="openai", model="gpt-4o", tools=[ReadFileTool(), WriteFileTool()])
print(await agent.ainvoke("Read ./README.md and summarize the first section"))
```

- 工具参数映射：LLM 的 function calling 会返回 `name/arguments`，框架将其映射为 `run(**arguments)` 调用。

## 权限策略与审计（可选）

- 创建 Agent 时可设置 `permission_policy` 与 `ask_handler`，由权限管理器在工具流水线阶段进行授权判断：

```python
policy = {
    "write_file": "ask",
    "http_request": "deny",
    "default": "allow",
}
agent = loom.agent(provider="openai", model="gpt-4o", tools=[...], permission_policy=policy)
```

- 回调（Callbacks）可用于记录工具调用与结果（参见 `CALLBACKS_SPEC.md`）。

## 错误处理与返回

- 工具内部抛出的异常会被框架捕获并计入 `error` 回调；请尽量返回清晰的错误信息。
- 对于结构化结果，建议返回字符串化 JSON 或简洁文本；框架不强加结果格式。

## 测试与调试建议

- 单元测试：直接创建 Tool 实例，调用 `await tool.run(**kwargs)`；或用 `RuleLLM/MockLLM` 驱动最小 Agent 场景测试。
- 观测：使用 `LoggingCallback` 或自定义回调观察 `tool_calls_start/tool_result/error` 等事件。

## 内置工具速览

- 目录：`loom/builtin/tools/`
- 示例（非完整）：
  - `ReadFileTool`/`WriteFileTool`
  - `Calculator`
  - `GlobTool`/`GrepTool`
  - `HTTPRequestTool`
  - `DocumentSearchTool`

---

更多：
- 快速开始：`QUICKSTART.md`
- 回调与事件：`CALLBACKS_SPEC.md`
- RAG 指南：`LOOM_RAG_GUIDE.md`

