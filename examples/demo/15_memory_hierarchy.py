"""
15_memory_hierarchy.py - 多Agent记忆层级与协作

演示：
- 多 Agent 交叉 Session 协作
- L1-L4 四层记忆机制
- RAG 知识库集成
- 不同节点激活不同的 Skill 和 Tool
- 记忆聚合与分散
- 基于真实 LLM 的完整流程

场景：研究团队协作
- Coordinator: 协调者，管理任务分配
- Researcher: 研究员，负责信息检索和分析
- Writer: 写作者，负责内容生成
- Reviewer: 审核者，负责质量检查
"""

import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# 加载环境变量
load_dotenv(Path(__file__).parent.parent.parent / ".env")


async def main():
    """主入口"""
    print("=" * 70)
    print("多Agent记忆层级与协作 Demo")
    print("=" * 70)

    # 检查 API Key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n[警告] 未设置 OPENAI_API_KEY，将使用 MockLLMProvider")
        print("设置环境变量后可使用真实 LLM")

    # 1. 初始化基础设施
    infra = await setup_infrastructure()

    # 2. 创建知识库
    kb = await setup_knowledge_base()

    # 3. 创建多 Agent 团队
    team = await create_agent_team(infra, kb)

    # 4. 演示记忆层级
    await demo_memory_layers(team)

    # 5. 演示跨 Session 协作
    await demo_cross_session_collaboration(team)

    # 6. 演示记忆聚合与分散
    await demo_memory_aggregation(team)

    # 7. 演示 RAG 集成
    await demo_rag_integration(team, kb)

    # 8. 演示完整协作流程
    await demo_full_collaboration(team)

    print("\n" + "=" * 70)
    print("Demo 完成!")
    print("=" * 70)


# ==================== 基础设施 ====================

async def setup_infrastructure() -> dict[str, Any]:
    """设置基础设施"""
    print("\n" + "-" * 50)
    print("[1] 初始化基础设施")
    print("-" * 50)

    from loom.api import ContextController, EventBus, Session

    # 创建共享的 EventBus
    event_bus = EventBus()
    print("    创建 EventBus")

    # 创建 ContextController
    controller = ContextController()
    print("    创建 ContextController")

    # 创建多个 Session（每个 Agent 一个）
    sessions = {
        "coordinator": Session(session_id="session-coordinator", event_bus=event_bus),
        "researcher": Session(session_id="session-researcher", event_bus=event_bus),
        "writer": Session(session_id="session-writer", event_bus=event_bus),
        "reviewer": Session(session_id="session-reviewer", event_bus=event_bus),
    }

    for name, session in sessions.items():
        controller.register_session(session)
        print(f"    注册 Session: {name}")

    return {
        "event_bus": event_bus,
        "controller": controller,
        "sessions": sessions,
    }


async def setup_knowledge_base():
    """设置知识库"""
    print("\n" + "-" * 50)
    print("[2] 创建知识库")
    print("-" * 50)

    from loom.providers.knowledge.rag import Document, GraphRAGKnowledgeBase, RAGConfig

    config = RAGConfig(
        strategy="graph_first",
        chunk_size=256,
        chunk_overlap=50,
    )
    kb = GraphRAGKnowledgeBase.from_config(config=config)

    # 添加领域知识
    documents = [
        Document(
            id="doc-ai-agents",
            content="""
            AI Agent 是能够自主执行任务的智能系统。
            核心能力包括：感知环境、做出决策、执行动作、学习改进。
            现代 Agent 框架通常采用 ReAct 模式：推理 + 行动的循环。
            """,
            metadata={"domain": "ai", "topic": "agents"},
        ),
        Document(
            id="doc-memory-systems",
            content="""
            Agent 记忆系统通常分为多个层级：
            - 工作记忆（L1）：当前任务的即时信息
            - 短期记忆（L2）：重要的近期信息
            - 长期记忆（L3）：压缩的历史摘要
            - 持久记忆（L4）：向量化的永久存储
            """,
            metadata={"domain": "ai", "topic": "memory"},
        ),
        Document(
            id="doc-collaboration",
            content="""
            多 Agent 协作模式：
            - 层级式：主 Agent 协调子 Agent
            - 对等式：Agent 之间平等协作
            - 混合式：结合层级和对等
            关键是信息共享和任务分配机制。
            """,
            metadata={"domain": "ai", "topic": "collaboration"},
        ),
    ]

    await kb.add_documents(documents, extract_entities=True)
    print(f"    添加 {len(documents)} 个知识文档")

    return kb


# ==================== Agent 团队 ====================

async def create_agent_team(infra: dict[str, Any], kb) -> dict[str, Any]:
    """创建 Agent 团队"""
    print("\n" + "-" * 50)
    print("[3] 创建 Agent 团队")
    print("-" * 50)

    from loom.agent import Agent
    from loom.config.llm import LLMConfig
    from loom.providers.llm import MockLLMProvider, OpenAIProvider

    # 获取 LLM 配置
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    # 创建 LLM Provider
    if api_key:
        config = LLMConfig(
            provider="openai",
            model=model,
            api_key=api_key,
            base_url=base_url,
        )
        llm = OpenAIProvider(config)
        print(f"    使用 OpenAI Provider: {model}")
    else:
        llm = MockLLMProvider()
        print("    使用 MockLLMProvider")

    event_bus = infra["event_bus"]
    sessions = infra["sessions"]

    # 定义工具
    search_tool = {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库获取相关信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索查询"},
                },
                "required": ["query"],
            },
        },
    }

    analyze_tool = {
        "type": "function",
        "function": {
            "name": "analyze_content",
            "description": "分析内容并提取关键信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要分析的内容"},
                },
                "required": ["content"],
            },
        },
    }

    write_tool = {
        "type": "function",
        "function": {
            "name": "write_document",
            "description": "撰写文档内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "文档主题"},
                    "outline": {"type": "string", "description": "文档大纲"},
                },
                "required": ["topic"],
            },
        },
    }

    review_tool = {
        "type": "function",
        "function": {
            "name": "review_content",
            "description": "审核内容质量",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "要审核的内容"},
                    "criteria": {"type": "string", "description": "审核标准"},
                },
                "required": ["content"],
            },
        },
    }

    # 创建 Agents（不同角色配置不同工具）
    agents = {}

    # Coordinator - 协调者
    agents["coordinator"] = Agent.create(
        llm=llm,
        node_id="coordinator",
        system_prompt="你是团队协调者，负责分配任务和整合结果。",
        tools=[],  # 协调者主要使用委派
        event_bus=event_bus,
        knowledge_base=kb,
        max_iterations=5,
    )
    print("    创建 Coordinator Agent")

    # Researcher - 研究员
    agents["researcher"] = Agent.create(
        llm=llm,
        node_id="researcher",
        system_prompt="你是研究员，负责搜索和分析信息。",
        tools=[search_tool, analyze_tool],
        event_bus=event_bus,
        knowledge_base=kb,
        max_iterations=5,
    )
    print("    创建 Researcher Agent")

    # Writer - 写作者
    agents["writer"] = Agent.create(
        llm=llm,
        node_id="writer",
        system_prompt="你是写作者，负责撰写高质量内容。",
        tools=[write_tool],
        event_bus=event_bus,
        max_iterations=5,
    )
    print("    创建 Writer Agent")

    # Reviewer - 审核者
    agents["reviewer"] = Agent.create(
        llm=llm,
        node_id="reviewer",
        system_prompt="你是审核者，负责检查内容质量。",
        tools=[review_tool],
        event_bus=event_bus,
        max_iterations=5,
    )
    print("    创建 Reviewer Agent")

    return {
        "agents": agents,
        "sessions": sessions,
        "controller": infra["controller"],
        "event_bus": event_bus,
        "llm": llm,
    }


# ==================== 记忆层级演示 ====================

async def demo_memory_layers(team: dict[str, Any]):
    """演示 L1-L4 四层记忆机制"""
    print("\n" + "-" * 50)
    print("[4] 记忆层级演示 (L1-L4)")
    print("-" * 50)

    from loom.api import Task

    sessions = team["sessions"]
    agents = team["agents"]

    # 向 Researcher Session 添加任务（模拟对话）
    researcher_session = sessions["researcher"]
    researcher_agent = agents["researcher"]

    print("\n    [L1] 添加即时任务到 Researcher Session")
    for i in range(3):
        task = Task(
            action="node.message",
            parameters={"content": f"研究任务 {i+1}: 分析 AI Agent 架构"},
        )
        researcher_session.add_task(task)
        print(f"        添加: 研究任务 {i+1}")

    # 查看 L1 任务
    l1_tasks = researcher_session.get_l1_tasks(limit=10)
    print(f"\n    [L1] Researcher Session L1 任务数: {len(l1_tasks)}")

    # 演示 L2 提升
    print("\n    [L2] 触发任务提升 (L1 → L2)")
    researcher_session.promote_tasks()
    l2_tasks = researcher_session.get_l2_tasks(limit=10)
    print(f"        L2 重要任务数: {len(l2_tasks)}")

    # 演示 Agent 记忆
    print("\n    [Agent Memory] 查看 Agent 内部记忆")
    memory = researcher_agent.memory
    print(f"        L1 任务: {len(memory.get_l1_tasks(limit=100))}")
    print(f"        L2 任务: {len(memory.get_l2_tasks(limit=100))}")

    # 演示记忆统计
    stats = researcher_session.get_stats()
    print("\n    [Stats] Session 统计:")
    print(f"        Session ID: {stats['session_id']}")
    print(f"        状态: {stats['status']}")


# ==================== 跨 Session 协作 ====================

async def demo_cross_session_collaboration(team: dict[str, Any]):
    """演示跨 Session 协作与记忆共享"""
    print("\n" + "-" * 50)
    print("[5] 跨 Session 协作演示")
    print("-" * 50)

    from loom.api import Task

    controller = team["controller"]
    sessions = team["sessions"]
    team["agents"]

    # 1. Coordinator 分配任务给 Researcher
    print("\n    [Step 1] Coordinator 分配任务")
    coordinator_session = sessions["coordinator"]
    task = Task(
        action="delegate.task",
        parameters={
            "target": "researcher",
            "task": "研究 AI Agent 的记忆系统设计",
            "priority": "high",
        },
    )
    coordinator_session.add_task(task)
    print("        Coordinator → Researcher: 研究记忆系统设计")

    # 2. 共享上下文到 Researcher
    print("\n    [Step 2] 共享上下文 (Coordinator → Researcher)")
    result = await controller.share_context(
        from_session_id="session-coordinator",
        to_session_ids=["session-researcher"],
        task_limit=5,
    )
    for sid, count in result.items():
        print(f"        共享到 {sid}: {count} 个任务")

    # 3. Researcher 完成研究，添加结果
    print("\n    [Step 3] Researcher 完成研究")
    researcher_session = sessions["researcher"]
    research_result = Task(
        action="node.response",
        parameters={
            "content": "研究结果: AI Agent 记忆系统通常采用分层架构，包括工作记忆、短期记忆、长期记忆等层级。",
            "metadata": {"type": "research_result", "quality": "high"},
        },
    )
    researcher_session.add_task(research_result)
    print("        Researcher 添加研究结果")

    # 4. 共享研究结果到 Writer
    print("\n    [Step 4] 共享研究结果 (Researcher → Writer)")
    result = await controller.share_context(
        from_session_id="session-researcher",
        to_session_ids=["session-writer"],
        task_limit=3,
    )
    for sid, count in result.items():
        print(f"        共享到 {sid}: {count} 个任务")

    # 5. Writer 基于研究结果撰写内容
    print("\n    [Step 5] Writer 撰写内容")
    writer_session = sessions["writer"]
    writer_tasks = writer_session.get_l1_tasks(limit=10)
    print(f"        Writer 收到 {len(writer_tasks)} 个上下文任务")

    draft = Task(
        action="node.response",
        parameters={
            "content": "文章草稿: AI Agent 记忆系统深度解析...",
            "metadata": {"type": "draft", "version": 1},
        },
    )
    writer_session.add_task(draft)
    print("        Writer 生成草稿")

    # 6. 共享草稿到 Reviewer
    print("\n    [Step 6] 共享草稿 (Writer → Reviewer)")
    result = await controller.share_context(
        from_session_id="session-writer",
        to_session_ids=["session-reviewer"],
        task_limit=3,
    )
    for sid, count in result.items():
        print(f"        共享到 {sid}: {count} 个任务")

    # 7. 显示协作链路
    print("\n    [协作链路]")
    print("        Coordinator → Researcher → Writer → Reviewer")
    for name, session in sessions.items():
        task_count = len(session.get_l1_tasks(limit=100))
        print(f"        {name}: {task_count} 个任务")


# ==================== 记忆聚合与分散 ====================

async def demo_memory_aggregation(team: dict[str, Any]):
    """演示记忆聚合（L1→L2→L3）与分散"""
    print("\n" + "-" * 50)
    print("[6] 记忆聚合与分散演示")
    print("-" * 50)

    from loom.api import Task

    controller = team["controller"]
    sessions = team["sessions"]

    # 1. 向多个 Session 添加大量任务（模拟工作负载）
    print("\n    [Step 1] 模拟工作负载 - 添加大量任务")
    for name, session in sessions.items():
        for i in range(5):
            task = Task(
                action="node.message",
                parameters={
                    "content": f"{name} 工作任务 {i+1}: 处理数据分析",
                    "metadata": {"importance": i % 3},  # 0, 1, 2 循环
                },
            )
            session.add_task(task)
        print(f"        {name}: 添加 5 个任务")

    # 2. 触发 L1 → L2 提升（基于重要性）
    print("\n    [Step 2] 触发 L1 → L2 提升")
    for name, session in sessions.items():
        session.promote_tasks()
        l1_count = len(session.get_l1_tasks(limit=100))
        l2_count = len(session.get_l2_tasks(limit=100))
        print(f"        {name}: L1={l1_count}, L2={l2_count}")

    # 3. 演示聚合到 Coordinator（汇总各 Agent 结果）
    print("\n    [Step 3] 聚合到 Coordinator")
    coordinator_session = sessions["coordinator"]

    # 从各 Session 收集重要任务
    aggregated_count = 0
    for name in ["researcher", "writer", "reviewer"]:
        result = await controller.share_context(
            from_session_id=f"session-{name}",
            to_session_ids=["session-coordinator"],
            task_limit=2,  # 只取最重要的 2 个
        )
        aggregated_count += result.get("session-coordinator", 0)

    print(f"        聚合了 {aggregated_count} 个任务到 Coordinator")

    # 4. 演示分散（Coordinator 分发任务）
    print("\n    [Step 4] 从 Coordinator 分散任务")
    summary_task = Task(
        action="broadcast.summary",
        parameters={
            "content": "团队工作摘要: 研究、写作、审核均已完成初步工作",
            "metadata": {"type": "summary", "broadcast": True},
        },
    )
    coordinator_session.add_task(summary_task)

    # 广播到所有其他 Session
    result = await controller.share_context(
        from_session_id="session-coordinator",
        to_session_ids=[
            "session-researcher",
            "session-writer",
            "session-reviewer",
        ],
        task_limit=1,
    )
    print("        广播摘要到所有 Agent:")
    for sid, count in result.items():
        print(f"          → {sid}: {count} 个任务")

    # 5. 显示最终状态
    print("\n    [最终状态]")
    for name, session in sessions.items():
        l1 = len(session.get_l1_tasks(limit=100))
        l2 = len(session.get_l2_tasks(limit=100))
        print(f"        {name}: L1={l1}, L2={l2}")


# ==================== RAG 集成 ====================

async def demo_rag_integration(team: dict[str, Any], kb):
    """演示 RAG 知识库与 Context 集成"""
    print("\n" + "-" * 50)
    print("[7] RAG 知识库集成演示")
    print("-" * 50)

    from loom.context import ContextOrchestrator
    from loom.context.sources import L1RecentSource, RAGKnowledgeSource
    from loom.memory import EstimateCounter

    sessions = team["sessions"]
    agents = team["agents"]

    # 1. 创建 RAG 上下文源
    print("\n    [Step 1] 创建 RAG 上下文源")
    rag_source = RAGKnowledgeSource(
        knowledge_base=kb,
        relevance_threshold=0.3,
    )
    print("        RAGKnowledgeSource (阈值: 0.3)")

    # 2. 为 Researcher 创建上下文编排器
    print("\n    [Step 2] 为 Researcher 创建上下文编排器")
    researcher_session = sessions["researcher"]
    token_counter = EstimateCounter()

    sources = [
        L1RecentSource(researcher_session.memory, researcher_session.session_id),
        rag_source,
    ]

    orchestrator = ContextOrchestrator(
        token_counter=token_counter,
        sources=sources,
        model_context_window=8000,
        output_reserve_ratio=0.25,
    )
    print(f"        上下文源: {[s.source_name for s in sources]}")

    # 3. 构建上下文
    print("\n    [Step 3] 构建上下文")
    messages = await orchestrator.build_context(
        query="AI Agent 的记忆系统如何设计？",
        system_prompt="你是一个 AI 研究专家，基于知识库回答问题。",
        min_relevance=0.3,
    )

    print(f"        构建了 {len(messages)} 条消息:")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"][:60].replace("\n", " ").strip()
        print(f"          [{i+1}] {role}: {content}...")

    # 4. 演示 Agent 使用 RAG
    print("\n    [Step 4] Agent 使用 RAG 知识库")
    researcher_agent = agents["researcher"]
    if hasattr(researcher_agent, "knowledge_base") and researcher_agent.knowledge_base:
        results = await researcher_agent.knowledge_base.query("记忆层级", limit=2)
        print(f"        Agent 查询知识库，获得 {len(results)} 个结果:")
        for r in results:
            preview = r.content[:40].replace("\n", " ").strip()
            print(f"          - {preview}... (相关度: {r.relevance:.2f})")
    else:
        print("        Agent 未配置知识库")

    # 5. 显示预算信息
    print("\n    [Step 5] 上下文预算信息")
    budget_info = orchestrator.get_budget_info("你是一个 AI 研究专家。")
    print(f"        总预算: {budget_info['total']} tokens")
    print(f"        可用预算: {budget_info['available']} tokens")


# ==================== 完整协作流程 ====================

async def demo_full_collaboration(team: dict[str, Any]):
    """演示完整的多 Agent 协作流程（基于真实 LLM）"""
    print("\n" + "-" * 50)
    print("[8] 完整协作流程演示")
    print("-" * 50)

    from loom.api import Task

    agents = team["agents"]
    sessions = team["sessions"]
    controller = team["controller"]
    llm = team["llm"]

    # 检查是否使用真实 LLM
    is_real_llm = not llm.__class__.__name__.startswith("Mock")
    print(f"\n    LLM 类型: {'真实 LLM' if is_real_llm else 'Mock LLM'}")

    # 定义协作任务
    task_topic = "AI Agent 记忆系统的最佳实践"
    print(f"    协作任务: {task_topic}")

    # Phase 1: Coordinator 分配任务
    print("\n    [Phase 1] Coordinator 分配任务")
    agents["coordinator"]
    coordinator_session = sessions["coordinator"]

    delegation_task = Task(
        action="coordinator.delegate",
        parameters={
            "topic": task_topic,
            "assignments": {
                "researcher": "研究记忆系统的设计模式和最佳实践",
                "writer": "撰写技术文档",
                "reviewer": "审核内容质量",
            },
        },
    )
    coordinator_session.add_task(delegation_task)
    print("        任务已分配给团队成员")

    # Phase 2: Researcher 执行研究
    print("\n    [Phase 2] Researcher 执行研究")
    researcher = agents["researcher"]
    researcher_session = sessions["researcher"]

    if is_real_llm:
        # 使用真实 LLM 进行研究
        try:
            response = await researcher.run(
                "请简要分析 AI Agent 记忆系统的设计要点（50字以内）"
            )
            research_content = response.content if hasattr(response, "content") else str(response)
            print(f"        研究结果: {research_content[:100]}...")
        except Exception as e:
            research_content = "研究完成（模拟）: 记忆系统应采用分层架构"
            print(f"        LLM 调用失败，使用模拟结果: {e}")
    else:
        research_content = "研究完成（模拟）: 记忆系统应采用 L1-L4 分层架构，支持自动提升和压缩"
        print(f"        研究结果: {research_content}")

    # 保存研究结果
    research_task = Task(
        action="research.complete",
        parameters={"content": research_content, "status": "completed"},
    )
    researcher_session.add_task(research_task)

    # 共享到 Writer
    await controller.share_context(
        from_session_id="session-researcher",
        to_session_ids=["session-writer"],
        task_limit=3,
    )
    print("        研究结果已共享给 Writer")

    # Phase 3: Writer 撰写内容
    print("\n    [Phase 3] Writer 撰写内容")
    writer = agents["writer"]
    writer_session = sessions["writer"]

    if is_real_llm:
        try:
            response = await writer.run(
                f"基于以下研究结果，撰写一段简短的技术说明（30字以内）：{research_content[:100]}"
            )
            draft_content = response.content if hasattr(response, "content") else str(response)
            print(f"        草稿: {draft_content[:100]}...")
        except Exception as e:
            draft_content = "技术文档草稿（模拟）: AI Agent 记忆系统采用分层设计..."
            print(f"        LLM 调用失败，使用模拟结果: {e}")
    else:
        draft_content = "技术文档草稿（模拟）: AI Agent 记忆系统采用 L1-L4 分层设计，实现高效的上下文管理"
        print(f"        草稿: {draft_content}")

    # 保存草稿
    draft_task = Task(
        action="draft.complete",
        parameters={"content": draft_content, "version": 1},
    )
    writer_session.add_task(draft_task)

    # 共享到 Reviewer
    await controller.share_context(
        from_session_id="session-writer",
        to_session_ids=["session-reviewer"],
        task_limit=3,
    )
    print("        草稿已共享给 Reviewer")

    # Phase 4: Reviewer 审核
    print("\n    [Phase 4] Reviewer 审核内容")
    reviewer = agents["reviewer"]
    reviewer_session = sessions["reviewer"]

    if is_real_llm:
        try:
            response = await reviewer.run(
                f"请简要评价以下内容的质量（20字以内）：{draft_content[:100]}"
            )
            review_content = response.content if hasattr(response, "content") else str(response)
            print(f"        审核意见: {review_content[:100]}...")
        except Exception as e:
            review_content = "审核通过（模拟）: 内容结构清晰，技术准确"
            print(f"        LLM 调用失败，使用模拟结果: {e}")
    else:
        review_content = "审核通过（模拟）: 内容结构清晰，技术描述准确，建议补充示例代码"
        print(f"        审核意见: {review_content}")

    # 保存审核结果
    review_task = Task(
        action="review.complete",
        parameters={"content": review_content, "approved": True},
    )
    reviewer_session.add_task(review_task)

    # Phase 5: 汇总到 Coordinator
    print("\n    [Phase 5] 汇总结果到 Coordinator")
    for name in ["researcher", "writer", "reviewer"]:
        await controller.share_context(
            from_session_id=f"session-{name}",
            to_session_ids=["session-coordinator"],
            task_limit=2,
        )

    # 最终统计
    print("\n    [协作完成] 最终统计:")
    total_tasks = 0
    for name, session in sessions.items():
        count = len(session.get_l1_tasks(limit=100))
        total_tasks += count
        print(f"        {name}: {count} 个任务")
    print(f"        总计: {total_tasks} 个任务")

    # 显示协作流程图
    print("\n    [协作流程]")
    print("        ┌─────────────┐")
    print("        │ Coordinator │")
    print("        └──────┬──────┘")
    print("               │ 分配任务")
    print("        ┌──────▼──────┐")
    print("        │  Researcher │")
    print("        └──────┬──────┘")
    print("               │ 研究结果")
    print("        ┌──────▼──────┐")
    print("        │    Writer   │")
    print("        └──────┬──────┘")
    print("               │ 草稿")
    print("        ┌──────▼──────┐")
    print("        │   Reviewer  │")
    print("        └──────┬──────┘")
    print("               │ 审核结果")
    print("        ┌──────▼──────┐")
    print("        │ Coordinator │")
    print("        └─────────────┘")


if __name__ == "__main__":
    asyncio.run(main())
