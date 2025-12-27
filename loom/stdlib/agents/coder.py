"""
编码员 Agent

预构建的编码员 Agent，具备文件操作能力。
"""

from loom.weave import create_agent
from loom.node.agent import AgentNode
from loom.stdlib.skills import FileSystemSkill


def CoderAgent(name: str = "coder", base_dir: str = ".") -> AgentNode:
    """
    创建一个编码员 Agent。

    Args:
        name: Agent 名称
        base_dir: 文件操作的基础目录

    Returns:
        配置好的编码员 Agent

    Example:
        coder = CoderAgent("my-coder", base_dir="./project")
        result = run(coder, "创建一个 hello.py 文件")
    """
    # 创建基础 Agent
    agent = create_agent(
        name,
        role="编码员 - 负责编写和修改代码文件"
    )

    # 注册文件系统技能
    fs_skill = FileSystemSkill(base_dir=base_dir)
    fs_skill.register(agent)

    return agent
