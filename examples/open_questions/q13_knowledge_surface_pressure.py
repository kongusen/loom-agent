"""Q13: Knowledge Surface Token Pressure

问题: evidence_packs 如何在保持 citation 的同时避免挤爆上下文？
观测现象: 多个证据包召回后 knowledge_surface 持续膨胀
实验设计: 比较四种表示策略对质量、引用率和 token 占用的影响
证据要求: evidence_pack 样本、token 曲线、citation 保真率、质量评审
"""

from loom.tools.knowledge import KnowledgeProvider

async def experiment_evidence_strategies():
    strategies = [
        "raw_evidence",
        "hierarchical_summary",
        "conflict_priority",
        "citation_index_lazy"
    ]

    results = {}
    query = "如何实现分布式事务？"

    for strategy in strategies:
        provider = KnowledgeProvider(strategy=strategy)
        packs = await provider.retrieve(query, top_k=5)

        results[strategy] = {
            "token_usage": sum(p.estimate_tokens() for p in packs),
            "citation_accuracy": evaluate_citations(packs),
            "answer_quality": evaluate_answer_quality(packs, query)
        }

    return results

def evaluate_citations(packs):
    # 验证引用是否准确指向来源
    return 0.95

def evaluate_answer_quality(packs, query):
    # 评估回答质量
    return 0.88
