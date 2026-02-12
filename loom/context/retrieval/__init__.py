"""
Unified Retrieval Pipeline - 统一检索管道

将 L4 语义检索和 RAG 知识库检索统一为一条管道：
Query → QueryRewriter → Parallel Retrieval → Reranker → RetrievalInjector → ContextBlocks

核心组件：
- QueryRewriter: 轻量级查询增强（关键词提取 + 上下文拼接）
- RetrievalCandidate: 统一候选项（包装 MemoryUnit / KnowledgeItem）
- Reranker: 跨源重排序 + 去重
- RetrievalInjector: 预算感知注入（高分 → L2 优先级，低分 → 背景优先级）
- UnifiedRetrievalSource: ContextSource 实现，替代 L4SemanticSource + RAGKnowledgeSource
"""

from loom.context.retrieval.candidates import CandidateOrigin, RetrievalCandidate
from loom.context.retrieval.injector import RetrievalInjector
from loom.context.retrieval.query_rewriter import QueryRewriter
from loom.context.retrieval.source import UnifiedRetrievalSource
from loom.context.retrieval.reranker import Reranker

__all__ = [
    "QueryRewriter",
    "RetrievalCandidate",
    "CandidateOrigin",
    "Reranker",
    "RetrievalInjector",
    "UnifiedRetrievalSource",
]
