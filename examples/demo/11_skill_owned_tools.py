"""Demo 11: Skill 持有工具机制

展示 Skill 如何持有工具，在激活时动态注册：
- scripts/ 目录中的脚本自动识别为工具
- 激活 Skill 时注册工具
- 卸载 Skill 时移除工具
"""

import asyncio
from pathlib import Path
from loom.types import Skill


def demo_skill_with_tools():
    """演示 Skill 持有工具的结构"""

    # 模拟从 SKILL.md 加载的 skill
    skill = Skill(
        name="python-expert",
        description="Python 编程专家",
        instructions="回答 Python 问题时给出代码示例",
        resources={
            "scripts": ["scripts/run_python.py", "scripts/lint_code.py"],
            "references": ["references/pep8.md"]
        },
        tools=["run_python", "lint_code"],  # 从 scripts/ 提取
    )

    print("=" * 60)
    print("Skill 持有工具机制")
    print("=" * 60)

    print(f"\n[1] Skill 结构")
    print(f"名称: {skill.name}")
    print(f"描述: {skill.description}")
    print(f"资源: {list(skill.resources.keys())}")
    print(f"工具: {skill.tools}")

    print(f"\n[2] 工具来源")
    print(f"✓ scripts/ 目录中的脚本自动识别为工具:")
    for script in skill.resources["scripts"]:
        tool_name = Path(script).stem
        print(f"  - {script} → {tool_name}")

    print(f"\n[3] 激活流程")
    print("✓ 激活 Skill 时:")
    print("  1. 加载完整 instructions")
    print("  2. 注册 tools 到 Agent.tools")
    print("  3. 工具可用于执行")

    print(f"\n[4] 卸载流程")
    print("✓ 卸载 Skill 时:")
    print("  1. 从 Agent.tools 移除工具")
    print("  2. 释放 Skill 分区预算")

    print("\n" + "=" * 60)
    print("Skill 持有工具的优势:")
    print("✓ 工具与 Skill 生命周期绑定")
    print("✓ 按需加载，节省资源")
    print("✓ 工具语义与 Skill 对齐")
    print("=" * 60)


if __name__ == "__main__":
    demo_skill_with_tools()

