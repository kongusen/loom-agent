"""
Context Compression Engine
"""
import datetime
from typing import TYPE_CHECKING, Any, Protocol

import tiktoken

from loom.memory.types import MemoryQuery, MemoryStatus, MemoryTier, MemoryType, MemoryUnit

if TYPE_CHECKING:
    from loom.memory.core import LoomMemory


class LLMProvider(Protocol):
    """Protocol for LLM providers used in compression."""
    async def chat(self, messages: list[dict[str, str]], **kwargs) -> Any:
        ...

class ContextCompressor:
    """
    Compresses conversation history by:
    1. Summarizing old message chains.
    2. Removing redundant tool call/result pairs if successful.
    3. Preserving critical facts (L4/L3).
    """

    @staticmethod
    def compress_history(
        units: list[MemoryUnit],
        keep_last_n: int = 4
    ) -> list[MemoryUnit]:
        """
        Compress a list of memory units.
        Args:
            units: Sorted list of memory units (Chronological).
            keep_last_n: Number of recent interaction turns to keep uncompressed.
        """
        if not units:
            return []

        # 1. Separate Immutable vs Compressible
        # Immutable: System prompts (handled outside), L4 Facts, Snippets
        # Compressible: L1 Messages, Thoughts, Tool Calls/Results

        immutable = []
        compressible = []

        for u in units:
            if u.tier == MemoryTier.L4_GLOBAL or u.type == MemoryType.FACT:
                immutable.append(u)
            else:
                compressible.append(u)

        # 2. Identify Compression Region
        # We want to keep the last N items (or turns) intact.
        if len(compressible) <= keep_last_n:
            return units # precise order might need reconstruction if we split lists.
            # Actually, if we just return units, we are fine.

        if keep_last_n > 0:
            to_compress = compressible[:-keep_last_n]
            kept_recent = compressible[-keep_last_n:]
        else:
            to_compress = compressible
            kept_recent = []

        # 3. Apply Compression Strategies
        compressed_segment = ContextCompressor._compress_segment(to_compress)

        # 4. Reassemble
        # Order: Immutable Facts -> Compressed Summary -> Recent History
        # Note: Original time order should ideally be preserved.
        # But summaries act as a "checkpoint" content.

        result = immutable + compressed_segment + kept_recent

        # Re-sort by time to be safe?
        # Summaries should have timestamp of the LATEST item they summarize.
        result.sort(key=lambda u: u.created_at)

        return result

    @staticmethod
    def _compress_segment(segment: list[MemoryUnit]) -> list[MemoryUnit]:
        """
        Compress a segment of memory units into a summary or simplified form.
        """
        if not segment:
            return []

        summary_text = ""
        tool_counts = {}

        # Iterate and build efficient representation
        for u in segment:
            if u.type == MemoryType.MESSAGE:
                role = u.metadata.get("role", "unknown")
                summary_text += f"{role}: {str(u.content)[:50]}...\n"

            elif u.type == MemoryType.THOUGHT:
                # Discard old thoughts or minimize
                pass

            elif u.type == MemoryType.TOOL_CALL:
                # Count usage
                calls = u.content if isinstance(u.content, list) else [u.content]
                for c in calls:
                    # Content might be the name itself if string, or dict
                    name = "unknown"
                    if isinstance(c, dict):
                        name = c.get("name", "unknown")
                    elif isinstance(c, str):
                        name = "unknown" # Content might be raw string of args?
                        # In agent.py we store list of dicts.

                    # If u.content is just a dict (single call)
                    if isinstance(u.content, dict):
                         name = u.content.get("name", "unknown")
                    elif isinstance(u.content, list):
                         pass # handled by iteration above if c is dict

                    # Better robustness
                    if isinstance(c, dict):
                        name = c.get("name", "unknown")

                    tool_counts[name] = tool_counts.get(name, 0) + 1

        # Create Summary Unit
        summary_content = "Previous Context Summary:\n"
        if summary_text:
            summary_content += summary_text
        if tool_counts:
            summary_content += "Tools used: " + ", ".join([f"{k} ({v})" for k,v in tool_counts.items()])

        summary_unit = MemoryUnit(
            content=summary_content,
            tier=MemoryTier.L2_WORKING, # Summary lives in Working Memory? Or L3?
            type=MemoryType.SUMMARY,
            created_at=segment[-1].created_at, # Timestamp of last item
            importance=0.5
        )

        return [summary_unit]


class MemoryCompressor:
    """
    Advanced memory compression with LLM-based summarization and fact extraction.
    Implements token-threshold-based compression triggers.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        l1_to_l3_threshold: int = 30,
        l3_to_l4_threshold: int = 50,
        token_threshold: int = 4000,
        enable_llm_summarization: bool = True
    ):
        """
        Initialize the memory compressor.

        Args:
            llm_provider: Optional LLM provider for intelligent summarization
            l1_to_l3_threshold: Number of L1 units before compression
            l3_to_l4_threshold: Number of L3 units before fact extraction
            token_threshold: Token count threshold for triggering compression
            enable_llm_summarization: Whether to use LLM for summarization
        """
        self.llm_provider = llm_provider
        self.l1_to_l3_threshold = l1_to_l3_threshold
        self.l3_to_l4_threshold = l3_to_l4_threshold
        self.token_threshold = token_threshold
        self.enable_llm_summarization = enable_llm_summarization

        # Initialize tokenizer for token counting
        try:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoder = None

    def _count_tokens(self, units: list[MemoryUnit]) -> int:
        """Count total tokens in memory units."""
        if not self.encoder:
            # Fallback: rough estimation
            return sum(len(str(u.content)) // 4 for u in units)

        total = 0
        for unit in units:
            content_str = str(unit.content)
            total += len(self.encoder.encode(content_str))
        return total

    async def compress_l1_to_l3(
        self,
        memory: "LoomMemory",
        session_id: str = "default"
    ) -> str | None:
        """
        Compress L1 raw IO buffer to L3 session summary.

        Args:
            memory: LoomMemory instance
            session_id: Session identifier for grouping

        Returns:
            ID of created summary unit, or None if no compression needed
        """
        # Query L1 messages
        l1_query = MemoryQuery(
            tiers=[MemoryTier.L1_RAW_IO],
            types=[MemoryType.MESSAGE, MemoryType.THOUGHT, MemoryType.TOOL_CALL, MemoryType.TOOL_RESULT]
        )
        l1_messages = await memory.query(l1_query)

        # Check if compression is needed
        if len(l1_messages) < self.l1_to_l3_threshold:
            return None

        # Check token count
        token_count = self._count_tokens(l1_messages)
        if token_count < self.token_threshold:
            return None

        # Perform compression
        if self.enable_llm_summarization and self.llm_provider:
            summary_text = await self._summarize_with_llm(l1_messages)
        else:
            summary_text = self._simple_summary(l1_messages)

        # Create L3 summary unit
        summary_unit = MemoryUnit(
            content=summary_text,
            tier=MemoryTier.L3_SESSION,
            type=MemoryType.SUMMARY,
            importance=0.7,
            metadata={
                "session_id": session_id,
                "compressed_count": len(l1_messages),
                "original_tokens": token_count
            }
        )

        summary_id = await memory.add(summary_unit)

        # Mark compressed units as SUMMARIZED
        for unit in l1_messages:
            unit.status = MemoryStatus.SUMMARIZED

        return summary_id

    async def extract_facts_to_l4(
        self,
        memory: "LoomMemory"
    ) -> list[str]:
        """
        Extract facts from L2/L3 and promote to L4 global knowledge.

        Args:
            memory: LoomMemory instance

        Returns:
            List of IDs of created fact units
        """
        # Query L2 and L3 for potential facts
        query = MemoryQuery(
            tiers=[MemoryTier.L2_WORKING, MemoryTier.L3_SESSION],
            types=[MemoryType.MESSAGE, MemoryType.SUMMARY, MemoryType.CONTEXT]
        )
        candidates = await memory.query(query)

        if len(candidates) < self.l3_to_l4_threshold:
            return []

        # Extract facts
        if self.enable_llm_summarization and self.llm_provider:
            facts = await self._extract_facts_with_llm(candidates)
        else:
            facts = self._extract_facts_simple(candidates)

        # Create L4 fact units
        fact_ids = []
        for fact_text in facts:
            fact_unit = MemoryUnit(
                content=fact_text,
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=0.9,
                metadata={"extracted_from": "L2/L3"}
            )
            fact_id = await memory.add(fact_unit)
            fact_ids.append(fact_id)

        return fact_ids

    async def _summarize_with_llm(self, units: list[MemoryUnit]) -> str:
        """Use LLM to create intelligent summary."""
        # Build context from units
        context_parts = []
        for unit in units[:20]:  # Limit to avoid token overflow
            if unit.type == MemoryType.MESSAGE:
                context_parts.append(str(unit.content))
            elif unit.type == MemoryType.TOOL_CALL:
                context_parts.append(f"Tool: {unit.content}")
            elif unit.type == MemoryType.TOOL_RESULT:
                context_parts.append(f"Result: {str(unit.content)[:100]}")

        context_text = "\n".join(context_parts)

        # Create summarization prompt
        messages = [
            {
                "role": "system",
                "content": "You are a memory compression assistant. Summarize the conversation history concisely, preserving key information."
            },
            {
                "role": "user",
                "content": f"Summarize this conversation:\n\n{context_text}"
            }
        ]

        try:
            response = await self.llm_provider.chat(messages, max_tokens=200)
            return getattr(response, "content", str(response))
        except Exception:
            # Fallback to simple summary
            return self._simple_summary(units)

    def _simple_summary(self, units: list[MemoryUnit]) -> str:
        """Create rule-based summary."""
        message_count = sum(1 for u in units if u.type == MemoryType.MESSAGE)
        tool_count = sum(1 for u in units if u.type == MemoryType.TOOL_CALL)

        summary = f"Compressed {len(units)} memory units: "
        summary += f"{message_count} messages, {tool_count} tool calls."

        return summary

    async def _extract_facts_with_llm(self, units: list[MemoryUnit]) -> list[str]:
        """Use LLM to extract facts from memory units."""
        # Build context from units
        context_parts = []
        for unit in units[:30]:  # Limit to avoid token overflow
            context_parts.append(str(unit.content)[:200])

        context_text = "\n".join(context_parts)

        # Create fact extraction prompt
        messages = [
            {
                "role": "system",
                "content": "You are a knowledge extraction assistant. Extract key facts from the conversation. Return each fact on a new line."
            },
            {
                "role": "user",
                "content": f"Extract key facts from this conversation:\n\n{context_text}"
            }
        ]

        try:
            response = await self.llm_provider.chat(messages, max_tokens=300)
            content = getattr(response, "content", str(response))
            # Split by newlines and filter empty lines
            facts = [f.strip() for f in content.split("\n") if f.strip()]
            return facts[:10]  # Limit to top 10 facts
        except Exception:
            # Fallback to simple extraction
            return self._extract_facts_simple(units)

    def _extract_facts_simple(self, units: list[MemoryUnit]) -> list[str]:
        """Extract facts using simple heuristics."""
        facts = []

        # Look for high-importance units
        for unit in units:
            if unit.importance > 0.8 and unit.type in [MemoryType.MESSAGE, MemoryType.CONTEXT]:
                content_str = str(unit.content)[:100]
                if len(content_str) > 20:  # Skip very short content
                    facts.append(content_str)

        return facts[:5]  # Limit to top 5 facts


class L4Compressor:
    """L4知识库压缩器

    使用DBSCAN聚类和LLM总结来压缩相似的facts，保持L4在合理规模。

    Attributes:
        llm: LLM提供者，用于总结clusters
        embedding: Embedding提供者，用于计算相似度
        threshold: 触发压缩的facts数量阈值
        similarity_threshold: 聚类相似度阈值（0-1）
        min_cluster_size: 最小聚类大小，小于此值的cluster不压缩
    """

    def __init__(
        self,
        llm_provider: Any,
        embedding_provider: Any,
        threshold: int = 150,
        similarity_threshold: float = 0.75,
        min_cluster_size: int = 3
    ):
        self.llm = llm_provider
        self.embedding = embedding_provider
        self.threshold = threshold
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size

    async def should_compress(self, l4_facts: list[MemoryUnit]) -> bool:
        """判断是否需要压缩

        Args:
            l4_facts: L4层的所有facts

        Returns:
            是否需要压缩
        """
        return len(l4_facts) > self.threshold

    async def compress(
        self,
        l4_facts: list[MemoryUnit]
    ) -> list[MemoryUnit]:
        """压缩L4 facts

        Args:
            l4_facts: L4层的所有facts

        Returns:
            压缩后的facts列表
        """
        # 1. 聚类相似的facts
        clusters = await self._cluster_facts(l4_facts)

        # 2. 压缩每个cluster
        compressed = []
        for cluster in clusters:
            if len(cluster) >= self.min_cluster_size:
                # 只压缩包含min_cluster_size个以上的cluster
                summary_fact = await self._summarize_cluster(cluster)
                compressed.append(summary_fact)
            else:
                # 保留小cluster的原始facts
                compressed.extend(cluster)

        return compressed

    async def _cluster_facts(
        self,
        facts: list[MemoryUnit]
    ) -> list[list[MemoryUnit]]:
        """聚类相似的facts（自实现，不依赖sklearn）

        使用基于相似度阈值的简单聚类算法：
        1. 计算所有facts之间的余弦相似度
        2. 使用并查集合并相似度超过阈值的facts
        3. 返回聚类结果

        Args:
            facts: 待聚类的facts列表

        Returns:
            聚类后的facts列表，每个元素是一个cluster
        """
        try:
            import numpy as np
        except ImportError:
            # 如果numpy不可用，返回单个cluster
            return [facts]

        if len(facts) < 2:
            return [facts]

        # 获取所有embeddings
        embeddings = []
        for fact in facts:
            if fact.embedding:
                embeddings.append(fact.embedding)
            else:
                # 实时计算
                emb = await self.embedding.embed_text(str(fact.content))
                embeddings.append(emb)

        # 转换为numpy数组并归一化
        embeddings_array = np.array(embeddings, dtype=np.float64)

        # L2归一化
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # 避免除以零
        embeddings_normalized = embeddings_array / norms

        # 检查是否有无效值
        if np.any(np.isnan(embeddings_normalized)) or np.any(np.isinf(embeddings_normalized)):
            return [facts]

        # 计算余弦相似度矩阵
        similarity_matrix = np.dot(embeddings_normalized, embeddings_normalized.T)
        similarity_matrix = np.clip(similarity_matrix, -1.0, 1.0)

        # 使用并查集进行聚类
        clusters = self._union_find_clustering(
            facts,
            similarity_matrix,
            self.similarity_threshold
        )

        return clusters

    def _union_find_clustering(
        self,
        facts: list[MemoryUnit],
        similarity_matrix,
        threshold: float
    ) -> list[list[MemoryUnit]]:
        """使用并查集进行聚类

        Args:
            facts: facts列表
            similarity_matrix: 相似度矩阵
            threshold: 相似度阈值

        Returns:
            聚类结果
        """
        n = len(facts)

        # 初始化并查集
        parent = list(range(n))
        rank = [0] * n

        def find(x):
            """查找根节点（带路径压缩）"""
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            """合并两个集合（按秩合并）"""
            root_x = find(x)
            root_y = find(y)

            if root_x == root_y:
                return

            if rank[root_x] < rank[root_y]:
                parent[root_x] = root_y
            elif rank[root_x] > rank[root_y]:
                parent[root_y] = root_x
            else:
                parent[root_y] = root_x
                rank[root_x] += 1

        # 遍历相似度矩阵，合并相似的facts
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i][j] >= threshold:
                    union(i, j)

        # 组织成clusters
        clusters_dict = {}
        for i in range(n):
            root = find(i)
            if root not in clusters_dict:
                clusters_dict[root] = []
            clusters_dict[root].append(facts[i])

        return list(clusters_dict.values())

    async def _summarize_cluster(
        self,
        cluster: list[MemoryUnit]
    ) -> MemoryUnit:
        """使用LLM总结一个cluster

        Args:
            cluster: 待总结的facts cluster

        Returns:
            总结后的单个fact
        """
        # 构建prompt
        facts_text = "\n".join([
            f"{i+1}. {fact.content}"
            for i, fact in enumerate(cluster)
        ])

        prompt = f"""Summarize these related facts into a single concise fact.
Keep the key information, remove redundancy.

Facts:
{facts_text}

Concise summary (1-2 sentences):"""

        # 调用LLM
        try:
            response = await self.llm.complete(
                prompt,
                max_tokens=150,
                temperature=0.3  # 低温度，更确定性
            )
            summary = getattr(response, "content", str(response))
        except Exception:
            # 降级：使用第一个fact作为代表
            summary = str(cluster[0].content)

        # 创建新的fact
        return MemoryUnit(
            content=summary.strip(),
            tier=MemoryTier.L4_GLOBAL,
            type=MemoryType.FACT,
            importance=max(f.importance for f in cluster),  # 保留最高重要性
            metadata={
                "compressed_from": len(cluster),
                "original_ids": [f.id for f in cluster],
                "compressed_at": datetime.datetime.now().isoformat()
            }
        )
