"""Demo 10: Skill 渐进式加载与动态替换

展示 Skill 系统的按需激活机制：
- Layer 1: 元数据发现（所有 skills 的 name + description）
- Layer 2: 按需激活（根据用户对话选择相关 skills 完整加载）
- 分区预算：Skill 分区独立管理，不影响其他分区
"""

import asyncio
from pathlib import Path
from loom.types import Skill


def create_mock_skills() -> list[Skill]:
    """创建模拟的 skill 目录（Layer 1 - 只有元数据）"""
    return [
        Skill(
            name="code-review",
            description="审查代码质量，检查最佳实践",
            instructions="",
            _instructions_loaded=False,
        ),
        Skill(
            name="python-expert",
            description="Python 编程专家，解答 Python 问题",
            instructions="",
            _instructions_loaded=False,
        ),
        Skill(
            name="translator",
            description="翻译文本到不同语言",
            instructions="",
            _instructions_loaded=False,
        ),
        Skill(
            name="math-solver",
            description="解决数学问题和计算",
            instructions="",
            _instructions_loaded=False,
        ),
    ]


def select_relevant_skills(user_input: str, skills: list[Skill]) -> list[str]:
    """根据用户输入选择相关的 skills（简化版语义匹配）"""
    keywords = user_input.lower()
    selected = []

    if "code" in keywords or "python" in keywords or "review" in keywords:
        selected.append("code-review")
        selected.append("python-expert")
    if "translate" in keywords or "翻译" in keywords:
        selected.append("translator")
    if "math" in keywords or "计算" in keywords:
        selected.append("math-solver")

    return selected


def load_full_instructions(skill_name: str) -> str:
    """Layer 2: 加载完整 instructions（模拟）"""
    instructions_map = {
        "code-review": "审查代码时检查：1) 命名规范 2) 类型注解 3) 错误处理 4) 测试覆盖",
        "python-expert": "回答 Python 问题时：1) 给出代码示例 2) 解释原理 3) 提供最佳实践",
        "translator": "翻译时：1) 保持原意 2) 符合目标语言习惯 3) 注意专业术语",
        "math-solver": "解决数学问题：1) 列出步骤 2) 展示计算过程 3) 验证结果",
    }
    return instructions_map.get(skill_name, "")


async def main():
    print("=" * 60)
    print("Skill 渐进式加载与动态替换")
    print("=" * 60)

    # === Layer 1: 元数据发现 ===
    print("\n[1] Layer 1 - 加载所有 skill 元数据（轻量级）")
    all_skills = create_mock_skills()
    print(f"✓ 发现 {len(all_skills)} 个 skills:")
    for skill in all_skills:
        print(f"  - {skill.name}: {skill.description}")

    # === 模拟用户对话轮次 ===
    print("\n[2] 用户对话 - 动态选择相关 skills")

    # 第一轮对话
    user_input_1 = "帮我 review 这段 Python 代码"
    print(f"\n用户: {user_input_1}")
    selected_1 = select_relevant_skills(user_input_1, all_skills)
    print(f"✓ 选中 skills: {selected_1}")

    # Layer 2: 按需激活
    print("\n[3] Layer 2 - 激活选中的 skills（完整加载）")
    for name in selected_1:
        instructions = load_full_instructions(name)
        print(f"✓ 激活 {name}:")
        print(f"  {instructions}")

    # 第二轮对话 - 动态替换
    print("\n[4] 第二轮对话 - 动态替换 skills")
    user_input_2 = "帮我翻译这段文字"
    print(f"\n用户: {user_input_2}")
    selected_2 = select_relevant_skills(user_input_2, all_skills)
    print(f"✓ 选中 skills: {selected_2}")
    print(f"✓ 替换策略: 卸载 {selected_1}，激活 {selected_2}")

    for name in selected_2:
        instructions = load_full_instructions(name)
        print(f"✓ 激活 {name}:")
        print(f"  {instructions}")

    # === 总结 ===
    print("\n" + "=" * 60)
    print("Skill 渐进式加载机制:")
    print("✓ Layer 1: 元数据发现（所有 skills 轻量级目录）")
    print("✓ Layer 2: 按需激活（根据对话动态选择）")
    print("✓ 动态替换: 每轮对话重新选择相关 skills")
    print("✓ 分区独立: Skill 分区预算独立管理")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())



