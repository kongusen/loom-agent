# Loom Agent Packs（框架化定义）

Loom 强调“框架优先”。你可以用纯 Python API 定义和注册子 Agent，而不是把配置写进文件。

## 快速开始

```python
from loom import Agent, agent, AgentSpec, register_agent
from loom.builtin.tools import ReadFileTool, WriteFileTool, GlobTool, GrepTool

# 1) 注册一个子 Agent（内存注册，可随时覆盖）
register_agent(
    AgentSpec(
        agent_type="code-explorer",
        description="Broad code search and structure understanding",
        tools=["glob", "grep", "read_file"],
        model_name="gpt-4o",
        system_instructions=(
            "You are a code exploration agent. Start broad then narrow. "
            "Use glob/grep to find candidates, then read_file for details."
        ),
    )
)

# 2) 提供 TaskTool 需要的 agent_factory（示例：使用 openai）
def make_subagent(max_iterations: int = 20, **kwargs):
    # kwargs 可能包含 system_instructions / permission_policy / model_name
    # 使用者可选择拦截处理 model_name（例如切换 provider/model）
    return agent(
        provider="openai",
        model=kwargs.get("model_name", "gpt-4o"),
        tools=[ReadFileTool(), WriteFileTool(), GlobTool(), GrepTool()],
        max_iterations=max_iterations,
        system_instructions=kwargs.get("system_instructions"),
        permission_policy=kwargs.get("permission_policy"),
    )

# 3) 在主 Agent 中挂载 Task 工具（省略其余初始化）
from loom.builtin.tools.task import TaskTool

task_tool = TaskTool(agent_factory=make_subagent)
main = agent(provider="openai", model="gpt-4o", tools=[task_tool])

# 4) 运行子 Agent 任务（两种方式）

# 4.1 文本/JSON 方式（供 LLM 工具调用）：
#   传入 subagent_type / model_name 字符串（已自动解析 AgentSpec 与权限）
out1 = await task_tool.run(
    description="Explore repo",
    prompt="List all Python files under src/",
    subagent_type="code-explorer",
    model_name="gpt-4o",
)

# 4.2 引用方式（框架化，供上层 Python 调用）：
#   避免字符串，使用引用保持类型安全与可维护性
from loom import agent_ref, model_ref

out2 = await task_tool.run_ref(
    description="Explore repo",
    prompt="List all Python files under src/",
    agent=agent_ref("code-explorer"),
    model=model_ref("gpt-4o"),
)
```

## 运行时行为
- 当 `TaskTool` 收到引用或 `subagent_type="code-explorer"` 时：
  - 自动注入对应的系统提示（system_instructions）。
  - 根据 `tools=[...]` 生成权限策略：默认 `deny`，白名单工具 `allow`。
  - 如未显式传 `model_name`，使用注册时的 `model_name`。
  - 通过 `agent_factory` 创建子 Agent，若构造器不接受这些扩展参数，会自动回退到最小签名，并在运行时替换权限管理器。

## 与文件形式的兼容
- 如果需要兼容 Claude Code 的 `.claude/agents/` 或项目内 `.loom/agents/` Markdown 定义，Loom 仍然会在找不到“内存注册”时回退加载文件定义（非必须）。
- 框架理念上推荐“程序化注册”为主，便于版本化、类型检查与组合式扩展。

## API 参考
- `AgentSpec(agent_type, description, system_instructions, tools='*', model_name=None)`
- `register_agent(spec: AgentSpec) -> None`
- `get_agent_by_type(name: str) -> Optional[AgentSpec]`
- `list_agent_types() -> list[str]`
