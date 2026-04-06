"""Demo: Ecosystem integration (Skill + Plugin + MCP)

演示 Loom 0.7.1 的生态系统集成，参考 Claude Code 架构
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loom.ecosystem.integration import EcosystemManager
from loom.ecosystem.skill import Skill
from loom.ecosystem.mcp import MCPServerConfig, MCPTransportType


def demo_skill_system():
    """演示 Skill 系统"""
    print("=" * 60)
    print("Demo 1: Skill System")
    print("=" * 60)

    manager = EcosystemManager()

    # 1. 注册内置 skill
    skill = Skill(
        name="code-review",
        description="Review code for best practices",
        content="Review the following code:\n\n{code}\n\nFocus on: {focus}",
        when_to_use="code review, review code, check code quality",
        allowed_tools=["read_file", "grep"],
        source="bundled",
    )
    manager.skill_registry.register(skill)

    # 2. 任务匹配
    task = "I need to review some code"
    matched = manager.skill_registry.match_task(task)
    print(f"\nTask: {task}")
    print(f"Matched skills: {[s.name for s in matched]}")

    # 3. 获取 skill
    skill = manager.skill_registry.get("code-review")
    print(f"\nSkill: {skill.name}")
    print(f"Description: {skill.description}")
    print(f"Allowed tools: {skill.allowed_tools}")


def demo_plugin_system():
    """演示 Plugin 系统"""
    print("\n" + "=" * 60)
    print("Demo 2: Plugin System")
    print("=" * 60)

    manager = EcosystemManager()

    # 创建示例 plugin 目录结构
    demo_dir = Path(__file__).parent / "demo_plugin"
    demo_dir.mkdir(exist_ok=True)

    # 创建 plugin.json
    import json
    plugin_manifest = {
        "name": "my-plugin",
        "version": "1.0.0",
        "description": "Example plugin",
        "author": "Demo",
        "skills": ["skills/"],
        "mcpServers": {
            "demo-server": {
                "type": "stdio",
                "command": "python",
                "args": ["-m", "demo_server"],
                "env": {"API_KEY": "${API_KEY}"}
            }
        }
    }
    (demo_dir / "plugin.json").write_text(json.dumps(plugin_manifest, indent=2))

    # 加载 plugin
    plugin = manager.plugin_loader.load_plugin(demo_dir, source="local")
    print(f"\nLoaded plugin: {plugin.name}")
    print(f"Version: {plugin.manifest.version}")
    print(f"MCP servers: {list(plugin.manifest.mcp_servers.keys())}")

    # 清理
    import shutil
    shutil.rmtree(demo_dir)


def demo_mcp_integration():
    """演示 MCP 集成"""
    print("\n" + "=" * 60)
    print("Demo 3: MCP Integration")
    print("=" * 60)

    manager = EcosystemManager()

    # 1. 注册 MCP server
    config = MCPServerConfig(
        type=MCPTransportType.STDIO,
        command="uvx",
        args=["mcp-server-git"],
        env={"GIT_ROOT": "/path/to/repo"}
    )
    manager.mcp_bridge.register_server("git-server", config)

    # 2. 设置 instructions
    instructions = """
Use the git-server MCP tools to:
- List git branches
- Show commit history
- Create branches
"""
    manager.mcp_bridge.set_instructions("git-server", instructions)

    # 3. 获取 system prompt 注入
    additions = manager.get_system_prompt_additions()
    print(f"\nSystem prompt additions:\n{additions}")

    # 4. 连接并列出工具
    manager.mcp_bridge.connect("git-server")
    tools = manager.mcp_bridge.list_tools("git-server")
    print(f"\nAvailable tools: {len(tools)}")


if __name__ == "__main__":
    demo_skill_system()
    demo_plugin_system()
    demo_mcp_integration()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
