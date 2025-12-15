"""
Loom Interfaces - 协议定义

定义核心接口（使用 Python Protocol）：
- BaseLLM: LLM 接口
- BaseTool: 工具接口
- BaseMemory: Memory 接口
- BaseCompressor: 压缩器接口
- BaseEmbedding: Embedding 接口
- BaseRetriever: 检索器接口
- BaseVectorStore: 向量存储接口
- EventProducer: 事件生产者接口
"""

from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.interfaces.memory import BaseMemory
from loom.interfaces.compressor import BaseCompressor
from loom.interfaces.embedding import BaseEmbedding
from loom.interfaces.retriever import BaseRetriever
from loom.interfaces.vector_store import BaseVectorStore
from loom.interfaces.event_producer import EventProducer

__all__ = [
    "BaseLLM",
    "BaseTool",
    "BaseMemory",
    "BaseCompressor",
    "BaseEmbedding",
    "BaseRetriever",
    "BaseVectorStore",
    "EventProducer",
]
