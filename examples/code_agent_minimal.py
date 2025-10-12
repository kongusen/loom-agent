import asyncio

from loom import Agent
from loom.builtin.llms import RuleLLM
from loom.builtin.tools import ReadFileTool, WriteFileTool, GlobTool, GrepTool
from loom.builtin.memory import InMemoryMemory


def always_yes(tool_name: str, args: dict) -> bool:
    print(f"[ask] 允许执行工具: {tool_name}({args})")
    return True


async def main() -> None:
    # 权限策略：读/查找允许，写入需要确认
    permission_policy = {
        "read_file": "allow",
        "glob": "allow",
        "grep": "allow",
        "write_file": "ask",
        "default": "deny",
    }

    agent = Agent(
        llm=RuleLLM(),
        tools=[ReadFileTool(), WriteFileTool(), GlobTool(), GrepTool()],
        memory=InMemoryMemory(),
        max_context_tokens=16000,
        permission_policy=permission_policy,
        ask_handler=always_yes,
    )

    # 触发 glob
    print("\n--- glob 示例 ---")
    print(await agent.run("glob: **/*.md"))

    # 触发 read
    print("\n--- read 示例 ---")
    print(await agent.run("read: README.md"))

    # 触发 grep (glob)
    print("\n--- grep 示例 ---")
    print(await agent.run("grep: Loom in glob: **/*.md"))

    # 触发 write（ask 确认）
    print("\n--- write 示例 ---")
    print(await agent.run("write: tmp_demo.txt <<< hello loom"))

    # 输出指标
    print("\n--- metrics ---")
    print(agent.get_metrics())


if __name__ == "__main__":
    asyncio.run(main())

