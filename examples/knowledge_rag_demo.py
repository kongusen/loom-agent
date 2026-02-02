"""
智能RAG（检索增强生成）功能演示

本示例展示如何：
1. 实现自定义的KnowledgeBaseProvider
2. 使用Agent.create()创建带知识库的Agent
3. Agent自动查询知识库并生成答案
4. 验证知识库集成效果

特性：
- 按需查询：Agent根据任务内容自动查询相关知识
- 智能缓存：使用Fractal Memory缓存查询结果，避免重复查询
- 可配置：支持配置查询条目数和相关度阈值
"""

import asyncio
import os

from loom.agent import Agent
from loom.protocol import Task
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.llm.openai import OpenAIProvider

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

    # 1. 配置LLM提供者
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        print("   示例: export OPENAI_API_KEY='your-api-key-here'")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    print("✓ LLM已配置")

    # 2. 创建并配置知识库
    knowledge_base = SimpleKnowledgeBase()
    print(f"✓ 知识库已配置 ({len(knowledge_base.knowledge_data)} 条知识)")

    # 3. 使用新的简化API创建Agent（带知识库）
    agent = Agent.create(
        llm,
        system_prompt="你是一个智能助手，可以利用知识库回答问题。请基于知识库提供准确的答案。",
        knowledge_base=knowledge_base,
        knowledge_max_items=3,  # 每次查询最多返回3个知识条目
        knowledge_relevance_threshold=0.7,  # 相关度阈值
    )

    print(f"✓ Agent已创建: {agent.node_id}")
    print(
        f"  - 知识库配置: max_items={agent.knowledge_max_items}, "
        f"threshold={agent.knowledge_relevance_threshold}"
    )

    print("\n" + "=" * 60)
    print("开始测试智能RAG功能")
    print("=" * 60)

    # 测试场景1：查询Python相关知识
    print("\n[测试1] 询问Python相关问题")
    print("-" * 60)

    task1 = Task(
        task_id="task_1",
        action="execute",
        parameters={"content": "请介绍一下Python编程语言的特点"},
    )

    result1 = await agent.execute_task(task1)
    if result1.result:
        content = (
            result1.result.get("content", "")
            if isinstance(result1.result, dict)
            else str(result1.result)
        )
        print(f"✓ Agent回答:\n{content}\n")

    # 测试场景2：查询异步编程
    print("\n[测试2] 询问异步编程")
    print("-" * 60)

    task2 = Task(
        task_id="task_2",
        action="execute",
        parameters={"content": "什么是异步编程？它有什么优势？"},
    )

    result2 = await agent.execute_task(task2)
    if result2.result:
        content = (
            result2.result.get("content", "")
            if isinstance(result2.result, dict)
            else str(result2.result)
        )
        print(f"✓ Agent回答:\n{content}\n")

    # 测试场景3：查询RAG相关知识
    print("\n[测试3] 询问RAG技术")
    print("-" * 60)

    task3 = Task(
        task_id="task_3",
        action="execute",
        parameters={"content": "请解释一下RAG技术是什么"},
    )

    result3 = await agent.execute_task(task3)
    if result3.result:
        content = (
            result3.result.get("content", "")
            if isinstance(result3.result, dict)
            else str(result3.result)
        )
        print(f"✓ Agent回答:\n{content}\n")

    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)

    print("\n总结：")
    print("1. ✓ 知识库集成：Agent自动查询知识库获取相关信息")
    print("2. ✓ 智能回答：基于知识库内容生成准确答案")
    print("3. ✓ 可配置：支持自定义查询条目数和相关度阈值")
    print("4. ✓ 简化API：使用Agent.create()轻松创建带知识库的Agent")


if __name__ == "__main__":
    asyncio.run(main())
