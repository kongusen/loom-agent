"""
对话助手 Demo - 语义连贯的复杂问题分析

特性：
- 语义连贯的自然对话体验
- 内部复杂分析过程可观测
- 集成智能RAG知识库
- 流式输出思考过程
- 支持多轮对话

运行：
  OPENAI_API_KEY=... python examples/conversational_assistant_demo.py

示例对话：
  用户: 解释一下Python的异步编程原理
  助手: [展示思考过程] [查询知识库] [给出连贯的解释]
"""

import asyncio
import os
from typing import Any

from loom.api import LoomApp
from loom.api.models import AgentConfig
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.events import EventBus
from loom.protocol import Task
from loom.providers.llm.openai import OpenAIProvider


# ==================== 知识库实现 ====================

class ConversationalKnowledgeBase(KnowledgeBaseProvider):
    """
    对话助手的知识库

    包含编程、技术、AI等领域的知识
    """

    def __init__(self):
        self.knowledge_data = [
            {
                "id": "kb_python_async_001",
                "content": "Python异步编程基于事件循环（Event Loop）和协程（Coroutine）。"
                          "事件循环负责调度和执行异步任务，协程是可以暂停和恢复的函数。"
                          "使用async/await语法可以编写非阻塞的异步代码。",
                "source": "Python异步编程指南",
                "tags": ["python", "async", "coroutine", "event-loop"],
            },
            {
                "id": "kb_python_async_002",
                "content": "asyncio是Python的标准异步I/O库，提供了事件循环、协程、任务等核心组件。"
                          "常用的异步操作包括：网络请求、文件I/O、数据库查询等。"
                          "异步编程可以显著提高I/O密集型应用的性能。",
                "source": "asyncio官方文档",
                "tags": ["python", "asyncio", "performance", "io"],
            },
            {
                "id": "kb_llm_001",
                "content": "大语言模型（LLM）是基于Transformer架构的深度学习模型，"
                          "通过在海量文本数据上进行预训练，学习语言的统计规律和语义表示。"
                          "代表性模型包括GPT系列、Claude、LLaMA等。",
                "source": "LLM技术概览",
                "tags": ["llm", "ai", "transformer", "deep-learning"],
            },
            {
                "id": "kb_rag_001",
                "content": "RAG（检索增强生成）是一种结合检索和生成的技术，"
                          "通过从外部知识库检索相关信息，增强LLM的回答准确性和时效性。"
                          "RAG系统通常包括：向量化、检索、重排序、生成等步骤。",
                "source": "RAG技术白皮书",
                "tags": ["rag", "llm", "retrieval", "generation"],
            },
            {
                "id": "kb_agent_001",
                "content": "AI Agent是能够感知环境、做出决策并采取行动的智能系统。"
                          "现代Agent通常基于LLM，具备工具使用、规划、反思等能力。"
                          "Agent可以自主完成复杂任务，如代码生成、数据分析、问题求解等。",
                "source": "AI Agent架构设计",
                "tags": ["agent", "ai", "llm", "autonomous"],
            },
            {
                "id": "kb_memory_001",
                "content": "分层记忆系统模拟人类记忆机制，包括短期记忆、工作记忆、长期记忆等层次。"
                          "L1层存储原始交互，L2层存储重要信息，L3层存储摘要，L4层使用向量存储。"
                          "这种设计可以高效管理大量历史信息。",
                "source": "记忆系统设计文档",
                "tags": ["memory", "architecture", "hierarchy"],
            },
        ]

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        """查询知识库"""
        query_lower = query.lower()
        results = []

        for item in self.knowledge_data:
            content_lower = item["content"].lower()
            tags_lower = [tag.lower() for tag in item["tags"]]

            # 计算相关度
            relevance = 0.0
            if query_lower in content_lower:
                relevance = 0.95
            elif any(query_lower in tag for tag in tags_lower):
                relevance = 0.85
            elif any(word in content_lower for word in query_lower.split()):
                relevance = 0.75

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

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]


# ==================== 工具定义 ====================

def create_calculator_tool():
    """创建计算器工具"""
    return {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "执行数学计算，支持基本运算和数学函数",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的数学表达式，如 '2 + 2' 或 'sqrt(16)'",
                    }
                },
                "required": ["expression"],
            },
        },
    }


def create_search_tool():
    """创建搜索工具"""
    return {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库中的相关信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询",
                    }
                },
                "required": ["query"],
            },
        },
    }


# ==================== 事件处理器（可观测性）====================

class ConversationObserver:
    """
    对话观察器 - 展示内部思考过程
    """

    def __init__(self):
        self.thinking_buffer = []
        self.knowledge_queries = []
        self.tool_calls = []

    async def on_event(self, task: Task) -> Task:
        """处理事件"""
        action = task.action

        if action == "node.thinking":
            # 思考过程
            content = task.parameters.get("content", "")
            if content:
                self.thinking_buffer.append(content)
                print(f"💭 {content}", end="", flush=True)

        elif action == "node.tool_call":
            # 工具调用
            tool_name = task.parameters.get("tool_name", "unknown")
            self.tool_calls.append(tool_name)
            print(f"\n🔧 调用工具: {tool_name}")

        elif action == "node.tool_result":
            # 工具结果
            result = task.parameters.get("result", "")
            if "Knowledge" in str(result):
                self.knowledge_queries.append(result)
                print(f"📚 查询知识库")

        return task


# ==================== 对话循环 ====================

async def conversation_loop(agent: Any, observer: ConversationObserver):
    """
    对话循环 - 处理用户输入和Agent响应
    """
    print("\n" + "=" * 60)
    print("🤖 对话助手已启动")
    print("=" * 60)
    print("\n特性：")
    print("  - 💭 可观测的思考过程")
    print("  - 📚 智能知识库查询")
    print("  - 🔄 多轮对话记忆")
    print("\n输入 'quit' 或 'exit' 退出\n")

    conversation_history = []

    while True:
        # 获取用户输入
        try:
            user_input = input("\n👤 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "退出"]:
            print("\n👋 再见！")
            break

        # 清空观察器缓冲区
        observer.thinking_buffer.clear()
        observer.knowledge_queries.clear()
        observer.tool_calls.clear()

        print(f"\n🤖 助手: ", end="", flush=True)

        # 创建任务
        task = Task(
            task_id=f"chat-{len(conversation_history)}",
            action="chat",
            parameters={
                "content": user_input,
                "history": conversation_history[-5:],  # 保留最近5轮对话
            },
        )

        # 执行任务
        try:
            result = await agent.execute(task)
            response = result.result.get("response", "抱歉，我无法回答这个问题。")

            # 添加到对话历史
            conversation_history.append({
                "role": "user",
                "content": user_input,
            })
            conversation_history.append({
                "role": "assistant",
                "content": response,
            })

            print(f"\n\n✓ 完成")

        except Exception as e:
            print(f"\n\n❌ 错误: {e}")


# ==================== 主函数 ====================

async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("对话助手 Demo")
    print("=" * 60)

    # 1. 创建EventBus和观察器
    event_bus = EventBus()
    observer = ConversationObserver()
    event_bus.register_handler("*", observer.on_event)

    # 2. 创建LoomApp
    app = LoomApp(event_bus=event_bus)

    # 3. 配置LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return

    llm = OpenAIProvider(
        api_key=api_key,
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )
    app.set_llm_provider(llm)

    print("✓ LLM已配置")

    # 3. 配置知识库
    knowledge_base = ConversationalKnowledgeBase()
    app.set_knowledge_base(knowledge_base)
    print(f"✓ 知识库已配置 ({len(knowledge_base.knowledge_data)} 条知识)")

    # 4. 创建EventBus和观察器
    event_bus = EventBus()
    observer = ConversationObserver()
    event_bus.register_handler("*", observer.on_event)
    print("✓ 事件观察器已配置")

    # 4.5 添加工具
    tools = [
        create_calculator_tool(),
        create_search_tool(),
    ]
    app.add_tools(tools)
    print(f"✓ 工具已配置 ({len(tools)} 个工具)")

    # 5. 创建Agent配置
    config = AgentConfig(
        agent_id="conversational-assistant",
        name="对话助手",
        system_prompt="""你是一个友好、专业的AI助手。

你的特点：
- 语义连贯，表达清晰
- 善于分析复杂问题
- 能够利用知识库提供准确信息
- 思考过程透明可见

请用自然、流畅的语言回答用户问题。""",
        knowledge_max_items=3,
        knowledge_relevance_threshold=0.75,
    )

    # 6. 创建Agent
    agent = app.create_agent(config)
    print(f"✓ Agent已创建: {agent.node_id}")

    # 7. 启动对话循环
    await conversation_loop(agent, observer)


if __name__ == "__main__":
    asyncio.run(main())

