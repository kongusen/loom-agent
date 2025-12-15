"""
Context Assembler Demo - 智能上下文组装示例

展示 ContextAssembler 的核心功能：
- Primacy/Recency Effects
- XML Structure
- Priority Management
- Role/Task Separation
"""

import asyncio
from loom.core import ContextAssembler, ComponentPriority


def demo_basic():
    """基础示例：组装一个简单的上下文"""
    print("=" * 60)
    print("示例 1: 基础用法")
    print("=" * 60)

    assembler = ContextAssembler(
        max_tokens=100000,
        use_xml_structure=True,
        enable_primacy_recency=True
    )

    # 1. 添加关键指令（会在开头和结尾出现）
    assembler.add_critical_instruction("Always be helpful and accurate")
    assembler.add_critical_instruction("Never make up information")

    # 2. 设置角色
    assembler.add_role("You are an expert AI research assistant")

    # 3. 设置任务
    assembler.add_task("Research and explain AI alignment concepts")

    # 4. 添加上下文
    assembler.add_component(
        name="background",
        content="AI alignment is the field of ensuring AI systems act in accordance with human values and intentions.",
        priority=ComponentPriority.HIGH,
        xml_tag="background",
        truncatable=True
    )

    # 5. 组装
    context = assembler.assemble()
    print(context)
    print()


def demo_priority_management():
    """优先级管理示例：展示智能截断"""
    print("=" * 60)
    print("示例 2: 优先级管理")
    print("=" * 60)

    assembler = ContextAssembler(
        max_tokens=500,  # 设置较小的 token 预算以触发截断
        use_xml_structure=True,
        enable_primacy_recency=False  # 关闭以节省空间
    )

    # 添加不同优先级的组件
    assembler.add_component(
        name="critical_rule",
        content="CRITICAL: Always verify facts before responding",
        priority=ComponentPriority.CRITICAL,
        truncatable=False
    )

    assembler.add_component(
        name="important_context",
        content="User is asking about machine learning basics",
        priority=ComponentPriority.HIGH,
        truncatable=True
    )

    assembler.add_component(
        name="reference",
        content="Reference: Machine learning is a subset of AI that enables systems to learn from data. " * 20,
        priority=ComponentPriority.LOW,
        truncatable=True
    )

    # 组装（低优先级组件会被截断）
    context = assembler.assemble()
    print(context)
    print()

    # 查看统计
    stats = assembler.get_stats()
    print(f"统计信息:")
    print(f"  - 总 tokens: {stats['total_tokens']}")
    print(f"  - 最大 tokens: {stats['max_tokens']}")
    print(f"  - 利用率: {stats['utilization']:.1%}")
    print()


def demo_conversation_history():
    """对话历史示例：模拟多轮对话"""
    print("=" * 60)
    print("示例 3: 对话历史管理")
    print("=" * 60)

    assembler = ContextAssembler(
        max_tokens=100000,
        use_xml_structure=True,
        enable_primacy_recency=True
    )

    # 设置角色和任务
    assembler.add_role("You are a helpful programming assistant")
    assembler.add_task("Help users debug their code")
    assembler.add_critical_instruction("Always provide working code examples")

    # 模拟多轮对话（最近的消息优先级更高）
    conversation = [
        ("user", "How do I read a file in Python?"),
        ("assistant", "You can use open() function..."),
        ("user", "What about writing to a file?"),
        ("assistant", "You can use open() with 'w' mode..."),
        ("user", "Can you show me an example?"),  # 最新消息
    ]

    for i, (role, content) in enumerate(conversation):
        # 最近 3 条消息设为 HIGH 优先级
        if i >= len(conversation) - 3:
            priority = ComponentPriority.HIGH
        else:
            priority = ComponentPriority.MEDIUM

        assembler.add_component(
            name=f"message_{i}",
            content=f"[{role}]: {content}",
            priority=priority,
            xml_tag="message",
            truncatable=True
        )

    # 组装
    context = assembler.assemble()
    print(context)
    print()


def demo_few_shot_examples():
    """Few-Shot 示例"""
    print("=" * 60)
    print("示例 4: Few-Shot 示例管理")
    print("=" * 60)

    assembler = ContextAssembler(
        max_tokens=100000,
        use_xml_structure=True,
        enable_primacy_recency=True
    )

    # 设置角色和任务
    assembler.add_role("You are a sentiment analysis expert")
    assembler.add_task("Classify the sentiment of user input")
    assembler.add_critical_instruction("Return only: positive, negative, or neutral")

    # 添加 Few-Shot 示例
    assembler.add_few_shot_example("""
Input: "I love this product!"
Output: positive
""")

    assembler.add_few_shot_example("""
Input: "This is terrible."
Output: negative
""")

    assembler.add_few_shot_example("""
Input: "It's okay, nothing special."
Output: neutral
""")

    # 设置输出格式
    assembler.add_output_format("Return a single word: positive, negative, or neutral")

    # 组装
    context = assembler.assemble()
    print(context)
    print()


def demo_without_xml():
    """不使用 XML 结构的示例"""
    print("=" * 60)
    print("示例 5: 不使用 XML 结构")
    print("=" * 60)

    assembler = ContextAssembler(
        max_tokens=100000,
        use_xml_structure=False,  # 关闭 XML
        enable_primacy_recency=True
    )

    assembler.add_critical_instruction("Be concise")
    assembler.add_role("You are a helpful assistant")
    assembler.add_task("Answer user questions")
    assembler.add_component(
        name="context",
        content="User is learning Python",
        priority=ComponentPriority.MEDIUM
    )

    # 组装（使用 Markdown 标题代替 XML）
    context = assembler.assemble()
    print(context)
    print()


def main():
    """运行所有示例"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "Context Assembler Demo" + " " * 21 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    demo_basic()
    demo_priority_management()
    demo_conversation_history()
    demo_few_shot_examples()
    demo_without_xml()

    print("=" * 60)
    print("✅ 所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
