"""
10_knowledge_rag.py - 知识库 RAG 示例

演示：
- InMemoryKnowledgeBase 使用
- KnowledgeItem 创建
- Agent 集成知识库
- RAG 查询流程
"""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from loom.agent import Agent
from loom.providers.llm import OpenAIProvider
from loom.config.llm import LLMConfig
from loom.providers.knowledge.memory import InMemoryKnowledgeBase
from loom.providers.knowledge.base import KnowledgeItem

# 加载 .env 文件
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    # 1. 创建内存知识库
    knowledge_base = InMemoryKnowledgeBase()

    # 2. 添加知识条目
    items = [
        KnowledgeItem(
            id="doc-1",
            content="Loom Agent 是一个分形架构的 AI Agent 框架，支持多层级任务分解。",
            source="docs/overview.md",
            metadata={"category": "introduction"},
        ),
        KnowledgeItem(
            id="doc-2",
            content="Agent.create() 是创建 Agent 的主要方法，支持 llm、tools、system_prompt 等参数。",
            source="docs/api.md",
            metadata={"category": "api"},
        ),
        KnowledgeItem(
            id="doc-3",
            content="Skills 系统允许通过 Markdown 文件定义可复用的提示词模板。",
            source="docs/skills.md",
            metadata={"category": "features"},
        ),
        KnowledgeItem(
            id="doc-4",
            content="EventBus 提供发布-订阅模式，用于 Agent 间的事件通信。",
            source="docs/events.md",
            metadata={"category": "features"},
        ),
        KnowledgeItem(
            id="doc-5",
            content="MemoryScope 支持 LOCAL、SHARED、INHERITED、GLOBAL 四种作用域。",
            source="docs/memory.md",
            metadata={"category": "features"},
        ),
    ]

    for item in items:
        knowledge_base.add_item(item)

    print(f"知识库条目数: {len(knowledge_base.items)}")

    # 3. 测试知识库查询
    results = await knowledge_base.query("Agent", limit=3)
    print(f"\n查询 'Agent' 结果:")
    for r in results:
        print(f"  - [{r.id}] {r.content[:50]}...")

    # 4. 创建 LLM Provider（从环境变量获取配置）
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        print("请设置 OPENAI_API_KEY 环境变量")
        return

    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    llm = OpenAIProvider(config)

    # 5. 创建带知识库的 Agent
    agent = Agent.create(
        llm=llm,
        node_id="rag-agent",
        system_prompt="你是一个知识助手，使用知识库回答问题。",
        knowledge_base=knowledge_base,
    )

    print(f"\nAgent 已创建，知识库已集成")

    # 6. 运行查询（Agent 会自动使用知识库）
    # result = await agent.run("Loom Agent 有哪些主要功能？")
    # print(f"Agent 回答: {result}")


if __name__ == "__main__":
    asyncio.run(main())
