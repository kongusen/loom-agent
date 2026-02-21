"""
22_mechanism_validation.py - 框架机制综合验证

基于真实 API 测试 8 大核心机制：
1. 多轮对话
2. 记忆升维 L1→L2→L3
3. 动态工具创建
4. Skill 动态加载
5. Done 工具信号语义
6. Session 注入 + Chatbot 输出
7. 知识图谱 (Knowledge Graph)
8. 多Skill自主选择 + 工具绑定
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# 确保使用本地源码而非 site-packages 中的旧版本
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

from loom.agent import Agent
from loom.config.llm import LLMConfig
from loom.events.session import Session
from loom.memory.store import InMemoryStore
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.providers.knowledge.rag.graph_rag import GraphRAGKnowledgeBase
from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation
from loom.providers.knowledge.rag.retrievers.graph import GraphRetriever
from loom.providers.knowledge.rag.retrievers.vector import VectorRetriever
from loom.providers.knowledge.rag.stores.chunk_store import InMemoryChunkStore
from loom.providers.knowledge.rag.stores.entity_store import InMemoryEntityStore
from loom.providers.knowledge.rag.stores.relation_store import InMemoryRelationStore
from loom.providers.knowledge.rag.strategies.hybrid import HybridStrategy
from loom.providers.llm import OpenAIProvider
from loom.tools.skills.activator import SkillActivator
from loom.tools.skills.filesystem_loader import FilesystemSkillLoader

load_dotenv(Path(__file__).parent.parent.parent / ".env")


# ==================== Helpers ====================


def inspect_memory(agent, label=""):
    """打印 Agent 三层记忆状态（含实际内容、重要性门控、TTL）"""
    mem = agent.memory.memory  # LoomMemory
    l1_items = mem.get_message_items()
    l2_entries = mem.get_working_memory()
    l3_pending = mem._pending_l3_records

    # 显示门控和 TTL 配置
    threshold = mem._l2_importance_threshold
    ttl = mem._l2._ttl_seconds
    ttl_str = f"{ttl}s" if ttl is not None else "off"
    print(f"    [{label}] gate={threshold}, ttl={ttl_str}")

    print(f"    [{label}] L1: {len(l1_items)} msgs ({mem._l1.token_usage()} tok)")
    for item in l1_items:
        role = getattr(item, "role", "?")
        content = getattr(item, "content", str(item))
        imp = item.metadata.get("importance") if hasattr(item, "metadata") else None
        imp_str = f" imp={imp}" if imp is not None else ""
        print(f"      L1 | {role}{imp_str}: {content}")

    print(f"    [{label}] L2: {len(l2_entries)} entries ({mem._l2.token_usage()} tok)")
    for entry in l2_entries:
        etype = getattr(entry, "entry_type", "?")
        imp = getattr(entry, "importance", "?")
        exp = getattr(entry, "expires_at", None)
        exp_str = f" exp={exp:%H:%M:%S}" if exp else ""
        content = getattr(entry, "content", str(entry))
        print(f"      L2 | [{etype} imp={imp}{exp_str}] {content}")

    print(f"    [{label}] L3 pending: {len(l3_pending)} records")
    for record in l3_pending:
        imp = getattr(record, "importance", "?")
        tags = getattr(record, "tags", [])
        content = getattr(record, "content", str(record))
        print(f"      L3 | [imp={imp} tags={tags}] {content}")


def setup_llm():
    """创建 LLM Provider"""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("请设置 OPENAI_API_KEY 环境变量")
    config = LLMConfig(provider="openai", model=model, api_key=api_key, base_url=base_url)
    return OpenAIProvider(config)


def setup_embedding():
    """创建 Embedding Provider（记忆和知识体系共享）"""
    return OpenAIEmbeddingProvider(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )


# ==================== Test Functions ====================


async def test_multi_turn_and_memory(llm, embedding_provider):
    """测试 1+2: 多轮对话 + 记忆升维 L1→L2→L3"""
    l3_store = InMemoryStore()

    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个知识助手，用简短的中文回答问题（不超过两句话）。",
        node_id="memory-test",
        max_iterations=3,
        require_done_tool=False,
        memory_config={
            "l1_token_budget": 500,
            "l2_token_budget": 200,
            "l2_importance_threshold": 0.0,  # 门控关闭，确保驱逐内容全部进入 L2
            "l2_ttl_seconds": 86400,          # 24h TTL
        },
        embedding_provider=embedding_provider,
    )
    # 挂载 L3 持久存储
    agent.memory.memory.set_memory_store(l3_store)

    questions = [
        "什么是机器学习？",
        "深度学习和机器学习有什么区别？",
        "Transformer架构的核心是什么？",
        "GPT和BERT的区别是什么？",
        "大语言模型的训练需要什么？",
        "什么是注意力机制？",
        "CNN和RNN各自的优势是什么？",
    ]

    for i, q in enumerate(questions):
        print(f"  Q{i + 1}: {q}")
        result = await agent.run(q)
        print(f"  A{i + 1}: {result}")
        print()
        inspect_memory(agent, f"Turn {i + 1}")

        # 每轮检查是否有 L3 pending，有则 flush 到 L3 store
        mem = agent.memory.memory
        if mem._pending_l3_records:
            flushed = await mem.flush_pending()
            print(f"    >>> Flushed {flushed} records to L3 store")
        print()

    mem = agent.memory.memory
    l2_count = len(mem.get_working_memory())
    l3_store_count = len(l3_store._records)
    print(f"  ✓ Memory escalation verified: L2={l2_count}, L3 store={l3_store_count}")

    # --- L2 回忆测试 ---
    # Q1 "什么是机器学习？" 应已从 L1 驱逐到 L2（或更高层）
    recall_q = "我们最开始讨论的机器学习有哪三种主要类型？请列出来。"
    print("\n  === L2 记忆回忆测试 ===")
    print("  L1 当前内容（不含早期对话）:")
    for item in mem.get_message_items():
        role = getattr(item, "role", "?")
        content = getattr(item, "content", str(item))
        print(f"    L1 | {role}: {content[:80]}...")
    print("  L2 中保存的对话:")
    for entry in mem.get_working_memory():
        content = getattr(entry, "content", str(entry))
        print(f"    L2 | {content[:80]}...")
    print("  L3 store 中保存的记录:")
    for _rid, record in l3_store._records.items():
        print(f"    L3 | [imp={record.importance}] {record.content[:80]}...")
    print()
    print(f"  Recall Q: {recall_q}")
    recall_result = await agent.run(recall_q)
    print(f"  Recall A: {recall_result}")
    print()
    inspect_memory(agent, "After L2 Recall")

    ml_keywords = ["监督", "无监督", "强化", "半监督"]
    found_types = [kw for kw in ml_keywords if kw in recall_result]
    print(f"  Found ML types: {found_types}")
    assert len(found_types) >= 2, f"Agent should recall ML types from memory, only found: {found_types}"
    print("  ✓ L2 memory recall verified")

    # --- L3 回忆测试 ---
    # L2 中相同 importance 的条目无法互相驱逐，因此使用 end_session()
    # 这是生产环境中 session 结束时将 L2 持久化到 L3 的标准流程
    print("\n  === L3 持久记忆回忆测试 ===")
    print("  调用 end_session() 将 L2 全部持久化到 L3...")
    persisted = await mem.end_session()
    print(f"  end_session() 持久化了 {persisted} 条记录到 L3 store")

    l3_store_count = len(l3_store._records)
    assert l3_store_count > 0, "Expected L3 store to have records after end_session()"

    # 验证 L3 记录包含 embedding（embedding-first 检索的前提）
    has_embeddings = any(r.embedding is not None for r in l3_store._records.values())
    embedding_count = sum(1 for r in l3_store._records.values() if r.embedding is not None)
    print(f"  L3 records with embeddings: {embedding_count}/{l3_store_count}")
    assert has_embeddings, "L3 records should have embeddings when embedding_provider is configured"

    # end_session() 会清空 L1 和 L2，此时知识只存在于 L3
    l1_after = len(mem.get_message_items())
    l2_after = len(mem.get_working_memory())
    print(f"  end_session() 后: L1={l1_after} msgs, L2={l2_after} entries, L3 store={l3_store_count}")
    assert l1_after == 0 and l2_after == 0, "L1 and L2 should be empty after end_session()"

    l3_contents = [r.content for r in l3_store._records.values()]
    print("  L3 store 中保存的记录:")
    for c in l3_contents:
        print(f"    L3 | {c[:100]}...")

    # 此时 L1/L2 为空，agent 只能从 L3 检索知识
    l3_recall_q = "回忆一下我们之前讨论的话题，机器学习的定义是什么？它有哪些主要类型？"
    print(f"\n  L3 Recall Q: {l3_recall_q}")
    l3_recall_result = await agent.run(l3_recall_q)
    print(f"  L3 Recall A: {l3_recall_result}")
    print()
    inspect_memory(agent, "After L3 Recall")

    # 验证：回答应包含机器学习的核心概念（来自 L3 持久记忆）
    has_ml_def = "机器学习" in l3_recall_result
    has_core = any(kw in l3_recall_result for kw in ["数据", "训练", "模型", "预测", "模式", "算法", "监督", "学习"])
    print(f"  Contains 机器学习: {has_ml_def}")
    print(f"  Contains 核心概念: {has_core}")
    assert has_ml_def and has_core, "Agent should recall ML definition from L3 persistent memory"
    print("  ✓ L3 persistent memory recall verified — agent retrieved knowledge from L3 store")


async def test_dynamic_tool(llm):
    """测试 3: 动态工具创建"""
    agent = Agent.create(
        llm=llm,
        system_prompt=(
            "你是一个工具创建专家。你可以使用 create_tool 来创建新工具。\n"
            "当用户要求创建工具时，先用 create_tool 创建，然后调用新工具。"
        ),
        node_id="dynamic-tool-test",
        max_iterations=6,
        require_done_tool=False,
    )
    result = await agent.run(
        "请创建一个名为 word_count 的工具，功能是统计文本中的单词数量。"
        "参数为 text (string)，实现用 len(text.split()) 计算。"
        "创建后用它统计 'hello world foo bar baz' 有几个单词。"
    )
    print(f"  Result: {result}")
    print("  ✓ Dynamic tool test completed")


async def test_skill_loading(llm):
    """测试 4: Skill 动态加载"""
    skills_dir = Path(__file__).parent / "skills"
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个AI助手。",
        skills_dir=skills_dir,
        skills=["summarizer"],
        node_id="skill-test",
        max_iterations=3,
        require_done_tool=False,
    )

    # 验证 skill_registry 已加载 summarizer
    has_registry = agent.skill_registry is not None
    has_activator = agent.skill_activator is not None
    print(f"  Skill registry loaded: {has_registry}")
    print(f"  Skill activator ready: {has_activator}")

    # 验证 skill 在 config 中启用
    enabled = list(agent.config.enabled_skills) if agent.config else []
    print(f"  Enabled skills: {enabled}")

    long_text = (
        "人工智能是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。"
        "研究领域包括机器人、语言识别、图像识别、自然语言处理和专家系统等。"
        "人工智能从诞生以来，理论和技术日益成熟，应用领域也不断扩大。"
    )
    # 执行时 SkillActivator 会自动匹配并注入 skill instructions
    result = await agent.run(f"请帮我总结以下文本：{long_text}")
    print(f"  Result: {result}")
    assert has_registry and has_activator, "Skill registry and activator should be initialized"
    assert "summarizer" in enabled, "summarizer should be in enabled skills"
    print("  ✓ Skill loading verified")


async def test_done_semantics(llm):
    """测试 5: Done 工具信号语义"""
    agent = Agent.create(
        llm=llm,
        system_prompt="你是一个数学助手。先用文字回答问题，然后调用 done 工具表示完成。",
        node_id="done-test",
        require_done_tool=True,
        max_iterations=3,
    )
    result = await agent.run("1+1等于几？")
    print(f"  Result: '{result}'")

    # 新语义：response 从 L1 assistant 消息提取，不是 done.message
    has_answer = "2" in result
    not_just_signal = result != "Task completed" and len(result) > 5
    print(f"  Contains answer '2': {has_answer}")
    print(f"  Not just signal text: {not_just_signal}")
    assert has_answer, "Response should contain the actual answer from L1"
    print("  ✓ Done tool signal semantics verified")


async def test_session_and_memory(llm, embedding_provider):
    """测试 6: Session 记忆机制 — 三大场景验证

    A. 同一 Session 5 轮回忆（L1 滑动窗口保持）
    B. 不同 L1，共享 L2/L3（工作记忆跨对话窗口）
    C. 跨 Session 记忆连续（L3 持久记忆 + Embedding 向量检索）
    """
    from loom.memory.core import LoomMemory

    l3_store = InMemoryStore()

    # ============================================================
    # Scenario A: 同一 Session 内 5 轮回忆
    # 验证: L1 滑动窗口足够大时，agent 能回忆 5 轮前的独特信息
    # ============================================================
    print("\n  === Scenario A: 同一 Session 5 轮回忆 ===")

    session_a = Session(
        session_id="recall-session",
        l1_token_budget=4000,
        l2_token_budget=2000,
    )

    agent_a = Agent.create(
        llm=llm,
        system_prompt="你是一个记忆助手，用简短中文回答。记住用户告诉你的所有信息。",
        node_id="recall-agent",
        session=session_a,
        max_iterations=3,
        require_done_tool=False,
    )

    # Turn 1: 给出独特信息
    unique_code = "Loom2024Alpha"
    r1 = await agent_a.run(f"请记住我的项目代号是 {unique_code}，这很重要。")
    print(f"  Turn 1 (记住): {r1[:80]}...")

    # Turns 2-5: 无关对话（制造干扰）
    fillers = [
        "今天天气怎么样？",
        "推荐一本好书。",
        "Python和Java哪个更适合初学者？",
        "什么是云计算？",
    ]
    for i, q in enumerate(fillers, 2):
        r = await agent_a.run(q)
        print(f"  Turn {i}: {q} → {r[:60]}...")

    # Turn 6: 回忆独特信息
    recall_r = await agent_a.run("我之前告诉你的项目代号是什么？请准确回答。")
    print(f"  Turn 6 (回忆): {recall_r}")

    assert unique_code in recall_r, (
        f"Agent should recall '{unique_code}' from L1, got: {recall_r}"
    )
    print("  ✓ Scenario A: 5-turn L1 recall verified")

    # ============================================================
    # Scenario B: 不同 L1，共享 L2/L3
    # 验证: Agent1 对话后 L1→L2 驱逐，清空 L1，Agent2 通过 L2 回忆
    # ============================================================
    print("\n  === Scenario B: 不同 L1，共享 L2/L3 ===")

    shared_memory = LoomMemory(
        node_id="shared-mem",
        l1_token_budget=300,  # 小 L1，强制快速驱逐到 L2
        l2_token_budget=4000,
        l2_importance_threshold=0.0,  # 门控关闭，确保驱逐内容进入 L2
        embedding_provider=embedding_provider,
    )
    shared_memory.set_memory_store(l3_store)

    # Agent B1: 使用共享 memory 进行对话
    session_b1 = Session(
        session_id="shared-s1",
        l1_token_budget=300,
        l2_token_budget=4000,
    )
    session_b1._memory = shared_memory

    agent_b1 = Agent.create(
        llm=llm,
        system_prompt="你是一个知识助手，用简短中文回答。",
        node_id="shared-agent-1",
        session=session_b1,
        max_iterations=3,
        require_done_tool=False,
        embedding_provider=embedding_provider,
    )

    # Agent B1 多轮对话，触发 L1→L2 驱逐
    b1_questions = [
        "量子计算的基本原理是什么？",
        "量子比特和经典比特有什么区别？",
        "量子纠缠是什么现象？",
    ]
    for q in b1_questions:
        r = await agent_b1.run(q)
        print(f"  B1: {q} → {r[:60]}...")

    # 检查 L2 是否有驱逐内容
    l2_entries = shared_memory.get_working_memory()
    print(f"  Shared L2 entries after B1: {len(l2_entries)}")
    for entry in l2_entries:
        print(f"    L2 | {entry.content[:80]}...")
    assert len(l2_entries) > 0, "L2 should have evicted content from B1 conversations"

    # 清空 L1（模拟「不同的 L1」— 新对话窗口）
    shared_memory._l1.clear()
    print("  L1 cleared (simulating new conversation window)")

    # Agent B2: 同一个 shared_memory（L1 已清空，L2/L3 保留）
    session_b2 = Session(
        session_id="shared-s2",
        l1_token_budget=300,
        l2_token_budget=4000,
    )
    session_b2._memory = shared_memory

    agent_b2 = Agent.create(
        llm=llm,
        system_prompt="你是一个知识助手，用简短中文回答。根据已有的记忆信息回答问题。",
        node_id="shared-agent-2",
        session=session_b2,
        max_iterations=3,
        require_done_tool=False,
        embedding_provider=embedding_provider,
    )

    # Agent B2 应该能通过 L2 回忆 Agent B1 的对话内容
    b2_recall = await agent_b2.run("之前讨论过量子计算，量子比特有什么特点？")
    print(f"  B2 recall: {b2_recall}")

    has_quantum = any(kw in b2_recall for kw in ["量子", "叠加", "纠缠", "qubit", "比特"])
    print(f"  Contains quantum concepts: {has_quantum}")
    assert has_quantum, (
        f"Agent B2 should recall quantum concepts from shared L2, got: {b2_recall}"
    )
    print("  ✓ Scenario B: Shared L2/L3 with different L1 verified")

    # ============================================================
    # Scenario C: 跨 Session 记忆连续（L3 持久记忆）
    # 验证: Session1 对话 → end_session() 持久化 → Session2 通过 L3 回忆
    # 模拟用户在不同时间的两次会话，基于记忆连续回答
    # ============================================================
    print("\n  === Scenario C: 跨 Session 记忆连续 ===")

    # 使用独立的 L3 store（避免 Scenario B 的残留数据干扰）
    l3_store_c = InMemoryStore()

    # --- Session 1: 对话并持久化 ---
    memory_c1 = LoomMemory(
        node_id="cross-s1",
        l1_token_budget=500,
        l2_token_budget=2000,
        l2_importance_threshold=0.0,  # 门控关闭，确保 end_session() 持久化全部内容
        embedding_provider=embedding_provider,
    )
    memory_c1.set_memory_store(l3_store_c)

    session_c1 = Session(
        session_id="cross-session-1",
        l1_token_budget=500,
        l2_token_budget=2000,
    )
    session_c1._memory = memory_c1

    agent_c1 = Agent.create(
        llm=llm,
        system_prompt="你是一个项目管理助手，用简短中文回答。",
        node_id="cross-agent-1",
        session=session_c1,
        max_iterations=3,
        require_done_tool=False,
        embedding_provider=embedding_provider,
    )

    # Session 1 对话（包含独特项目信息）
    unique_project = "Phoenix"
    c1_turns = [
        f"我们的新项目叫 {unique_project}，目标是构建下一代AI平台。",
        f"{unique_project} 项目的技术栈是 Python + Rust + React。",
        f"{unique_project} 项目的截止日期是2025年6月。",
    ]
    for q in c1_turns:
        r = await agent_c1.run(q)
        print(f"  C1: {q[:50]}... → {r[:60]}...")

    # 结束 Session 1 → L2 持久化到 L3
    persisted = await memory_c1.end_session()
    print(f"  Session 1 ended: persisted {persisted} records to L3")

    l3_count = len(l3_store_c._records)
    print(f"  L3 store records: {l3_count}")
    assert l3_count > 0, "L3 should have records after end_session()"

    # 验证 L3 记录包含 embedding
    emb_count = sum(1 for r in l3_store_c._records.values() if r.embedding is not None)
    print(f"  L3 records with embeddings: {emb_count}/{l3_count}")

    # 打印 L3 内容
    for _rid, record in l3_store_c._records.items():
        print(f"    L3 | [imp={record.importance}] {record.content[:80]}...")

    # --- Session 2: 全新 L1/L2，同一 L3 store ---
    memory_c2 = LoomMemory(
        node_id="cross-s2",
        l1_token_budget=2000,
        l2_token_budget=4000,
        l2_importance_threshold=0.0,  # 与 Session 1 一致
        embedding_provider=embedding_provider,
    )
    memory_c2.set_memory_store(l3_store_c)  # 同一个 L3

    session_c2 = Session(
        session_id="cross-session-2",
        l1_token_budget=2000,
        l2_token_budget=4000,
    )
    session_c2._memory = memory_c2

    agent_c2 = Agent.create(
        llm=llm,
        system_prompt=(
            "你是一个项目管理助手，用简短中文回答。"
            "你可以使用 query 工具搜索历史记忆来回答用户的问题。"
        ),
        node_id="cross-agent-2",
        session=session_c2,
        max_iterations=5,
        require_done_tool=False,
        embedding_provider=embedding_provider,
    )

    # Session 2 Agent 通过 L3 回忆 Session 1 的内容
    c2_recall = await agent_c2.run(
        "我们之前讨论的项目叫什么名字？用了什么技术栈？"
    )
    print(f"  C2 recall: {c2_recall}")

    has_project = unique_project in c2_recall
    has_tech = any(kw in c2_recall for kw in ["Python", "Rust", "React"])
    print(f"  Contains project name '{unique_project}': {has_project}")
    print(f"  Contains tech stack: {has_tech}")
    assert has_project, (
        f"Agent C2 should recall project '{unique_project}' from L3, got: {c2_recall}"
    )
    print("  ✓ Scenario C: Cross-session memory continuity verified")


async def test_knowledge_graph(llm, embedding_provider):
    """测试 7: 知识图谱 (Knowledge Graph) + Embedding 向量检索"""

    # === Step 1: 构建图 ===
    entity_store = InMemoryEntityStore()
    relation_store = InMemoryRelationStore()
    chunk_store = InMemoryChunkStore()

    # 14 个实体
    entities_data = [
        ("ml", "机器学习", "FIELD", "通过数据和算法让计算机自动学习的AI分支"),
        ("dl", "深度学习", "FIELD", "使用多层神经网络的机器学习子领域"),
        ("sl", "监督学习", "METHOD", "使用带标签数据训练模型"),
        ("ul", "无监督学习", "METHOD", "在无标签数据中发现模式"),
        ("rl", "强化学习", "METHOD", "通过环境交互和奖励信号学习"),
        ("nn", "神经网络", "CONCEPT", "模拟生物神经元的计算模型"),
        ("cnn", "CNN", "MODEL", "卷积神经网络，擅长图像处理"),
        ("rnn", "RNN", "MODEL", "循环神经网络，擅长序列数据"),
        ("transformer", "Transformer", "MODEL", "基于自注意力的架构"),
        ("bert", "BERT", "MODEL", "双向编码器，擅长语言理解"),
        ("gpt", "GPT", "MODEL", "生成式预训练，擅长文本生成"),
        ("attention", "注意力机制", "CONCEPT", "动态权重分配的核心技术"),
        ("nlp", "自然语言处理", "FIELD", "处理和理解人类语言的技术领域"),
        ("cv", "计算机视觉", "FIELD", "处理和理解图像视频的技术领域"),
    ]

    # 为每个实体创建 Entity 和对应的 TextChunk
    chunk_descriptions = {
        "ml": "机器学习是人工智能的核心分支，通过数据驱动的方法让计算机自动学习规律。主要类型包括监督学习、无监督学习和强化学习。",
        "dl": "深度学习是机器学习的子领域，使用多层神经网络自动提取特征，在图像识别、语音识别等领域取得突破。",
        "sl": "监督学习使用带标签的训练数据，学习输入到输出的映射关系，常用于分类和回归任务。",
        "ul": "无监督学习在没有标签的数据中发现隐藏的模式和结构，常用于聚类、降维和异常检测。",
        "rl": "强化学习通过智能体与环境的交互，根据奖励信号学习最优策略，应用于游戏AI和机器人控制。",
        "nn": "神经网络是模拟生物神经元连接的计算模型，由输入层、隐藏层和输出层组成，是深度学习的基础。",
        "cnn": "CNN（卷积神经网络）通过卷积层提取空间特征，具有平移不变性和参数共享特点，广泛应用于计算机视觉。",
        "rnn": "RNN（循环神经网络）通过隐藏状态记忆序列信息，适合处理时间序列和自然语言等变长序列数据。",
        "transformer": "Transformer基于自注意力机制，支持并行计算，由编码器-解码器结构组成，革新了NLP领域。BERT和GPT都基于Transformer。",
        "bert": "BERT（双向编码器表示）使用Transformer编码器，通过遮蔽语言模型进行预训练，擅长语言理解任务如分类和问答。",
        "gpt": "GPT（生成式预训练Transformer）使用Transformer解码器，通过自回归方式生成文本，擅长文本生成和对话。",
        "attention": "注意力机制通过Query-Key-Value计算动态权重，让模型选择性关注输入的重要部分，是Transformer的核心组件。",
        "nlp": "自然语言处理是AI的重要分支，涵盖文本分类、机器翻译、问答系统等任务，Transformer架构带来了革命性进展。",
        "cv": "计算机视觉处理和理解图像视频数据，核心任务包括图像分类、目标检测和语义分割，CNN是其主要模型。",
    }

    # 批量生成 chunk embeddings（记忆和知识体系共享同一个 embedding_provider）
    chunk_contents = [chunk_descriptions[eid] for eid, _, _, _ in entities_data]
    chunk_embeddings = await embedding_provider.embed_batch(chunk_contents)
    print(f"  Generated {len(chunk_embeddings)} chunk embeddings (dim={len(chunk_embeddings[0])})")

    for i, (eid, text, etype, desc) in enumerate(entities_data):
        chunk_id = f"chunk_{eid}"
        entity = Entity(
            id=eid, text=text, entity_type=etype,
            description=desc, chunk_ids=[chunk_id],
        )
        await entity_store.add(entity)

        chunk = TextChunk(
            id=chunk_id, content=chunk_descriptions[eid],
            document_id="ai_knowledge", entity_ids=[eid],
            keywords=[text],
            embedding=chunk_embeddings[i],
        )
        await chunk_store.add(chunk)

    # 15 条关系
    relations_data = [
        ("r01", "dl", "ml", "子领域", "深度学习是机器学习的子领域"),
        ("r02", "sl", "ml", "类型", "监督学习是机器学习的一种类型"),
        ("r03", "ul", "ml", "类型", "无监督学习是机器学习的一种类型"),
        ("r04", "rl", "ml", "类型", "强化学习是机器学习的一种类型"),
        ("r05", "dl", "nn", "基于", "深度学习基于多层神经网络"),
        ("r06", "cnn", "dl", "属于", "CNN属于深度学习模型"),
        ("r07", "rnn", "dl", "属于", "RNN属于深度学习模型"),
        ("r08", "transformer", "dl", "属于", "Transformer属于深度学习模型"),
        ("r09", "bert", "transformer", "基于", "BERT基于Transformer编码器"),
        ("r10", "gpt", "transformer", "基于", "GPT基于Transformer解码器"),
        ("r11", "attention", "transformer", "核心组件", "注意力机制是Transformer的核心"),
        ("r12", "cnn", "cv", "应用于", "CNN广泛应用于计算机视觉"),
        ("r13", "rnn", "nlp", "应用于", "RNN应用于自然语言处理"),
        ("r14", "transformer", "nlp", "革新", "Transformer革新了自然语言处理"),
        ("r15", "bert", "nlp", "应用于", "BERT应用于自然语言理解任务"),
    ]

    for rid, src, tgt, rtype, desc in relations_data:
        relation = Relation(
            id=rid, source_id=src, target_id=tgt,
            relation_type=rtype, description=desc,
        )
        await relation_store.add(relation)

    print(f"  Graph built: {len(entities_data)} entities, {len(relations_data)} relations")

    # === Step 2: 打印图结构 ===
    print("\n  === 知识图谱结构 ===")
    type_groups = {}
    for eid, text, etype, _desc in entities_data:
        type_groups.setdefault(etype, []).append((eid, text))
    for etype, items in type_groups.items():
        names = ", ".join(f"{text}({eid})" for eid, text in items)
        print(f"    [{etype}] {names}")

    print("\n  === 关系 ===")
    for _rid, src, tgt, rtype, _desc in relations_data:
        src_name = next(t for e, t, _, _ in entities_data if e == src)
        tgt_name = next(t for e, t, _, _ in entities_data if e == tgt)
        print(f"    {src_name} --{rtype}--> {tgt_name}")

    # === Step 3: N-hop 遍历 ===
    print("\n  === 从 Transformer 出发 2-hop BFS 遍历 ===")
    hop_relations = await relation_store.get_n_hop("transformer", n=2, direction="both")
    visited_ids = {"transformer"}
    for rel in hop_relations:
        visited_ids.add(rel.source_id)
        visited_ids.add(rel.target_id)

    visited_entities = await entity_store.get_by_ids(list(visited_ids))
    print(f"    发现 {len(visited_entities)} 个关联实体:")
    for e in visited_entities:
        print(f"      - {e.text} ({e.entity_type})")
    print(f"    经过 {len(hop_relations)} 条关系:")
    for rel in hop_relations:
        src_e = await entity_store.get(rel.source_id)
        tgt_e = await entity_store.get(rel.target_id)
        src_name = src_e.text if src_e else rel.source_id
        tgt_name = tgt_e.text if tgt_e else rel.target_id
        print(f"      {src_name} --{rel.relation_type}--> {tgt_name}")

    # 验证遍历结果
    visited_names = {e.text for e in visited_entities}
    expected = {"BERT", "GPT", "注意力机制", "深度学习"}
    found = expected & visited_names
    print(f"    Expected entities found: {found}")
    assert len(found) >= 3, f"2-hop from Transformer should find BERT/GPT/注意力机制/深度学习, got: {found}"
    print("  ✓ N-hop traversal verified")

    # === Step 4: GraphRetriever + VectorRetriever 查询 ===
    # 注意: InMemoryEntityStore.search() 检查 query 是否为实体文本的子串
    # 因此查询词需要匹配实体名称（如 "Transformer"）
    print("\n  === GraphRetriever 查询: 'Transformer' ===")
    graph_retriever = GraphRetriever(entity_store, relation_store, chunk_store)
    entities, relations, chunks = await graph_retriever.retrieve(
        "Transformer", n_hop=2, limit=10
    )
    print(f"    Entities: {len(entities)}")
    for e in entities:
        print(f"      - {e.text} ({e.entity_type})")
    print(f"    Relations: {len(relations)}")
    for r in relations:
        print(f"      - {r.source_id} --{r.relation_type}--> {r.target_id}")
    print(f"    Chunks: {len(chunks)}")
    for c in chunks:
        print(f"      - [{c.id}] {c.content[:60]}...")

    assert len(entities) > 0, "GraphRetriever should find entities for 'Transformer'"
    assert len(chunks) > 0, "GraphRetriever should return chunks"
    print("  ✓ GraphRetriever query verified")

    # === Step 4b: VectorRetriever 语义检索 ===
    print("\n  === VectorRetriever 语义检索: '注意力是如何工作的' ===")
    vector_retriever = VectorRetriever(chunk_store, embedding_provider)
    vector_results = await vector_retriever.retrieve("注意力是如何工作的", limit=5)
    print(f"    Vector results: {len(vector_results)}")
    for chunk, score in vector_results:
        print(f"      - [{chunk.id}] score={score:.4f} {chunk.content[:60]}...")

    assert len(vector_results) > 0, "VectorRetriever should find chunks by semantic similarity"
    # 注意力机制相关的 chunk 应排在前列
    top_chunk_ids = [c.id for c, _ in vector_results[:3]]
    assert "chunk_attention" in top_chunk_ids, (
        f"'注意力机制' chunk should be in top-3 vector results, got: {top_chunk_ids}"
    )
    print("  ✓ VectorRetriever semantic search verified")

    # === Step 5: HybridStrategy 混合检索 + Agent 问答 ===
    print("\n  === Agent + HybridStrategy 混合检索问答 ===")
    strategy = HybridStrategy(
        graph_retriever=graph_retriever,
        vector_retriever=vector_retriever,
        n_hop=2,
        graph_weight=0.5,
        vector_weight=0.5,
    )
    knowledge_base = GraphRAGKnowledgeBase(
        strategy=strategy,
        chunk_store=chunk_store,
        name="ai_knowledge_graph",
        description="AI/ML 领域知识图谱",
    )

    agent = Agent.create(
        llm=llm,
        system_prompt=(
            "你是一个AI知识专家。根据提供的知识图谱信息，用简洁的中文回答问题。"
            "请基于知识库中的结构化信息来回答。"
        ),
        node_id="kg-test",
        knowledge_base=knowledge_base,
        max_iterations=3,
        require_done_tool=False,
    )

    question = "BERT和GPT有什么区别？它们和Transformer是什么关系？"
    print(f"  Q: {question}")
    result = await agent.run(question)
    print(f"  A: {result}")

    # 验证回答包含关键信息
    has_bert = "BERT" in result
    has_gpt = "GPT" in result
    has_transformer = "Transformer" in result or "transformer" in result
    has_diff = any(kw in result for kw in ["编码器", "解码器", "理解", "生成", "双向", "自回归"])
    print(f"  Contains BERT: {has_bert}")
    print(f"  Contains GPT: {has_gpt}")
    print(f"  Contains Transformer: {has_transformer}")
    print(f"  Contains distinction: {has_diff}")
    assert has_bert and has_gpt, "Answer should mention both BERT and GPT"
    assert has_transformer, "Answer should mention Transformer"
    print("  ✓ Knowledge graph + HybridStrategy + Agent integration verified")


async def test_multi_skill_and_tool_binding(llm):
    """测试 8: 多Skill自主选择 + 工具绑定"""
    skills_dir = Path(__file__).parent / "skills"

    # === Step 1: 加载所有 Skill ===
    loader = FilesystemSkillLoader(skills_dir)
    all_skill_defs = await loader.list_skills()  # returns list[SkillDefinition]
    all_metadata = await loader.list_skill_metadata()  # returns list[dict]
    skill_by_id = {s.skill_id: s for s in all_skill_defs}
    print(f"  Loaded {len(all_skill_defs)} skills from filesystem:")
    for skill in all_skill_defs:
        tools_str = ", ".join(skill.required_tools) if skill.required_tools else "(none)"
        print(f"    - {skill.name} [{skill.skill_id}] required_tools=[{tools_str}]")
    assert len(all_skill_defs) >= 4, f"Expected at least 4 skills, got {len(all_skill_defs)}"
    print("  ✓ Skill filesystem loading verified")

    # === Step 2: 自主选择测试 ===
    print("\n  === Skill 自主选择 (token matching) ===")
    activator = SkillActivator(llm)

    test_cases = [
        ("请帮我总结这段文本的要点", "summarizer"),
        ("翻译这段话成英文", "translator"),
        ("计算这个数学题 x^2 + 3x = 0", "math-solver"),
        ("审查这段代码的质量", "code-review"),
    ]

    selection_passed = 0
    for task_desc, expected_skill in test_cases:
        relevant = await activator.find_relevant_skills(task_desc, all_metadata)
        top_match = relevant[0] if relevant else "(none)"
        is_match = expected_skill in relevant[:2]  # 允许在前2名
        status = "✓" if is_match else "✗"
        print(f"    {status} '{task_desc}' → top={top_match}, expected={expected_skill}, found_in_top2={is_match}")
        if is_match:
            selection_passed += 1

    assert selection_passed >= 3, f"Expected at least 3/4 correct selections, got {selection_passed}/4"
    print(f"  ✓ Autonomous skill selection verified ({selection_passed}/4)")

    # === Step 3: 工具绑定验证 ===
    print("\n  === 工具绑定验证 ===")

    # 3a: 无 required_tools 的 skill → 应成功激活
    summarizer = skill_by_id["summarizer"]
    result_ok = await activator.activate(summarizer)
    print(f"    summarizer (no required_tools): success={result_ok.success}")
    assert result_ok.success, "Summarizer should activate without tool requirements"

    # 3b: 有 required_tools 但无 tool_manager → 应成功（不检查）
    math_solver = skill_by_id["math-solver"]
    result_no_tm = await activator.activate(math_solver, tool_manager=None)
    print(f"    math-solver (no tool_manager): success={result_no_tm.success}")
    assert result_no_tm.success, "Should succeed when no tool_manager to validate against"

    # 3c: 有 required_tools + 有 tool_manager 但工具缺失 → 应失败
    class MockToolManager:
        def list_tools(self):
            return ["search", "read_file"]  # 不包含 calculate/plot_graph

    result_missing = await activator.activate(math_solver, tool_manager=MockToolManager())
    print(f"    math-solver (tools missing): success={result_missing.success}, "
          f"missing={result_missing.missing_tools}")
    assert not result_missing.success, "Should fail when required tools are missing"
    assert "calculate" in result_missing.missing_tools, "Should report 'calculate' as missing"

    # 3d: 有 required_tools + tool_manager 且工具齐全 → 应成功
    class FullToolManager:
        def list_tools(self):
            return ["calculate", "plot_graph", "search"]

    result_full = await activator.activate(math_solver, tool_manager=FullToolManager())
    print(f"    math-solver (tools present): success={result_full.success}")
    assert result_full.success, "Should succeed when all required tools are available"
    print("  ✓ Tool binding validation verified")

    # === Step 4: 激活内容注入验证 ===
    print("\n  === 激活内容注入 ===")
    translator = skill_by_id["translator"]
    result_inject = await activator.activate(translator)
    has_instructions = "翻译" in result_inject.content
    print(f"    Activation content contains instructions: {has_instructions}")
    print(f"    Content preview: {result_inject.content[:80]}...")
    assert has_instructions, "Activated skill should contain instruction content"
    print("  ✓ Skill instruction injection verified")


# ==================== Main ====================


async def main():
    llm = setup_llm()
    embedding = setup_embedding()

    print("=" * 60)
    print("  Loom Agent 机制综合验证 Demo")
    print("=" * 60)

    # (name, test_fn, extra_args) — embedding_provider 由记忆和知识体系共享
    tests = [
        ("1+2. 多轮对话 + 记忆升维", test_multi_turn_and_memory, (embedding,)),
        ("3. 动态工具创建", test_dynamic_tool, ()),
        ("4. Skill 动态加载", test_skill_loading, ()),
        ("5. Done 工具信号语义", test_done_semantics, ()),
        ("6. Session 记忆机制", test_session_and_memory, (embedding,)),
        ("7. 知识图谱 (Knowledge Graph)", test_knowledge_graph, (embedding,)),
        ("8. 多Skill自主选择 + 工具绑定", test_multi_skill_and_tool_binding, ()),
    ]

    passed = 0
    failed = 0
    for name, test_fn, extra_args in tests:
        print(f"\n{'─' * 50}")
        print(f"  {name}")
        print(f"{'─' * 50}")
        try:
            await test_fn(llm, *extra_args)
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ✗ FAILED: {e}")
            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
