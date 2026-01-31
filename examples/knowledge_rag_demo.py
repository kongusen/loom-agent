"""
智能RAG（检索增强生成）功能演示

本示例展示如何：
1. 实现自定义的KnowledgeBaseProvider
2. 配置LoomApp使用知识库
3. 创建Agent并使用智能RAG功能
4. 验证知识库查询和缓存机制

特性：
- 按需查询：Agent根据任务内容自动查询相关知识
- 智能缓存：使用Fractal Memory缓存查询结果，避免重复查询
- 可配置：支持配置查询条目数和相关度阈值
"""

import asyncio
from typing import Any

from loom.api import LoomApp
from loom.api.models import AgentConfig
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.llm import OpenAIProvider


# ==================== 1. 实现自定义知识库提供者 ====================

class SimpleKnowledgeBase(KnowledgeBaseProvider):
    """
    简单的内存知识库实现

    在实际应用中，你可以：
    - 连接到向量数据库（如Pinecone, Weaviate, Qdrant）
    - 使用Elasticsearch进行全文搜索
    - 集成企业知识库系统
    """

    def __init__(self):
        # 模拟知识库数据
        self.knowledge_data = [
            {
                "id": "kb_001",
                "content": "Python是一种高级编程语言，以其简洁的语法和强大的功能而闻名。",
                "source": "Python基础教程",
                "tags": ["python", "programming", "basics"],
            },
            {
                "id": "kb_002",
                "content": "异步编程允许程序在等待I/O操作时执行其他任务，提高效率。",
                "source": "异步编程指南",
                "tags": ["async", "python", "performance"],
            },
            {
                "id": "kb_003",
                "content": "LLM（大语言模型）可以理解和生成人类语言，用于各种NLP任务。",
                "source": "AI技术概览",
                "tags": ["llm", "ai", "nlp"],
            },
            {
                "id": "kb_004",
                "content": "RAG（检索增强生成）结合了检索和生成，提供更准确的答案。",
                "source": "RAG技术白皮书",
                "tags": ["rag", "llm", "retrieval"],
            },
            {
                "id": "kb_005",
                "content": "向量数据库用于存储和检索高维向量，支持语义搜索。",
                "source": "向量数据库指南",
                "tags": ["vector", "database", "search"],
            },
        ]

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        """
        查询知识库

        这是一个简单的关键词匹配实现。
        在实际应用中，应该使用向量相似度搜索。
        """
        query_lower = query.lower()
        results = []

        for item in self.knowledge_data:
            # 简单的关键词匹配
            content_lower = item["content"].lower()
            tags_lower = [tag.lower() for tag in item["tags"]]

            # 计算相关度（简化版）
            relevance = 0.0
            if query_lower in content_lower:
                relevance = 0.9
            elif any(query_lower in tag for tag in tags_lower):
                relevance = 0.8
            elif any(word in content_lower for word in query_lower.split()):
                relevance = 0.7

            if relevance > 0:
                results.append(
                    KnowledgeItem(
                        id=item["id"],
                        content=item["content"],
                        source=item["source"],
                        relevance=relevance,
                        metadata={"tags": item["tags"]},
                    )
                )

        # 按相关度排序并返回前N个
        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]


# ==================== 2. 配置和使用 ====================

async def main():
    """主函数：演示智能RAG功能"""

    print("=" * 60)
    print("智能RAG功能演示")
    print("=" * 60)

    # 1. 创建LoomApp
    app = LoomApp()

    # 2. 配置LLM提供者
    llm = OpenAIProvider(
        api_key="your-api-key-here",  # 替换为你的API密钥
        model="gpt-4",
    )
    app.set_llm_provider(llm)

    # 3. 创建并配置知识库
    knowledge_base = SimpleKnowledgeBase()
    app.set_knowledge_base(knowledge_base)

    print("\n✓ 知识库已配置")
    print(f"  - 知识条目数: {len(knowledge_base.knowledge_data)}")

    # 4. 创建Agent配置（使用自定义RAG参数）
    config = AgentConfig(
        agent_id="rag-agent",
        name="RAG演示Agent",
        system_prompt="你是一个智能助手，可以利用知识库回答问题。",
        knowledge_max_items=3,  # 每次查询最多返回3个知识条目
        knowledge_relevance_threshold=0.7,  # 相关度阈值
    )

    # 5. 创建Agent
    agent = app.create_agent(config)

    print("\n✓ Agent已创建")
    print(f"  - Agent ID: {agent.node_id}")
    print(f"  - 知识库配置: max_items={agent.knowledge_max_items}, "
          f"threshold={agent.knowledge_relevance_threshold}")

    print("\n" + "=" * 60)
    print("开始测试智能RAG功能")
    print("=" * 60)

    # 测试场景1：查询Python相关知识
    print("\n[测试1] 查询Python相关知识")
    print("-" * 60)

    from loom.protocol import Task

    task1 = Task(
        task_id="task_1",
        action="query",
        parameters={"content": "Python编程语言"},
    )

    # 获取上下文（会触发知识库查询）
    context1 = await agent.context_manager.get_context(task1)

    print(f"✓ 上下文已生成，包含 {len(context1)} 条消息")
    for i, msg in enumerate(context1):
        if "Knowledge" in msg.get("content", ""):
            print(f"  [{i+1}] {msg['content'][:100]}...")

    # 测试场景2：查询相同内容（应该使用缓存）
    print("\n[测试2] 再次查询相同内容（测试缓存）")
    print("-" * 60)

    task2 = Task(
        task_id="task_2",
        action="query",
        parameters={"content": "Python编程语言"},
    )

    context2 = await agent.context_manager.get_context(task2)

    print(f"✓ 上下文已生成，包含 {len(context2)} 条消息")
    for i, msg in enumerate(context2):
        if "Cached" in msg.get("content", ""):
            print(f"  [{i+1}] 使用缓存: {msg['content'][:100]}...")

    # 测试场景3：查询不同内容
    print("\n[测试3] 查询RAG相关知识")
    print("-" * 60)

    task3 = Task(
        task_id="task_3",
        action="query",
        parameters={"content": "RAG技术"},
    )

    context3 = await agent.context_manager.get_context(task3)

    print(f"✓ 上下文已生成，包含 {len(context3)} 条消息")
    for i, msg in enumerate(context3):
        if "Knowledge" in msg.get("content", ""):
            print(f"  [{i+1}] {msg['content'][:100]}...")

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    print("\n总结：")
    print("1. ✓ 知识库查询：Agent根据任务内容自动查询相关知识")
    print("2. ✓ 智能缓存：相同查询使用缓存，避免重复查询")
    print("3. ✓ 可配置：支持自定义查询条目数和相关度阈值")
    print("4. ✓ Fractal Memory：子节点可以继承父节点的知识缓存")


if __name__ == "__main__":
    asyncio.run(main())
