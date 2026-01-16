"""
LoomMemory Storage Engine
"""
import math
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING, Any

from loom.config.memory import MemoryConfig
from loom.projection.profiles import ProjectionConfig, ProjectionMode

from .embedding import EmbeddingProvider
from .factory import create_embedding_provider, create_vector_store
from .types import ContextProjection, MemoryQuery, MemoryTier, MemoryType, MemoryUnit
from .vector_store import VectorStoreProvider

if TYPE_CHECKING:
    from .compression import L4Compressor


class LoomMemory:
    """
    Tiered Memory Storage System.

    L1 (Raw IO): Circular buffer for recent raw interactions.
    L2 (Working): Task-specific working memory.
    L3 (Session): Session-scoped history.
    L4 (Global): Persistent global knowledge.
    """

    def __init__(
        self,
        node_id: str,
        max_l1_size: int = 50,
        config: MemoryConfig | None = None
    ):
        self.node_id = node_id
        self.config = config or MemoryConfig()
        # Use passed max_l1_size parameter, not config default
        self.max_l1_size = max_l1_size

        # Tiered Storage
        self._l1_buffer: list[MemoryUnit] = []           # Circular buffer
        self._l2_working: list[MemoryUnit] = []          # Working memory list
        self._l3_session: dict[str, list[MemoryUnit]] = defaultdict(list) # By session_id
        self._l4_global: list[MemoryUnit] = []           # Mock for VectorDB

        # Indexes
        self._id_index: dict[str, MemoryUnit] = {}
        self._type_index: dict[MemoryType, list[str]] = defaultdict(list)

        # Vector Store & Embedding (Pluggable)
        self.vector_store: VectorStoreProvider | None = create_vector_store(
            self.config.vector_store
        )
        self.embedding_provider: EmbeddingProvider | None = create_embedding_provider(
            self.config.embedding
        ) if self.vector_store else None

        # L4 Compressor (Optional)
        self.l4_compressor: 'L4Compressor' | None = None

    async def add(self, unit: MemoryUnit) -> str:
        """Add a memory unit to the appropriate tier."""
        # Ensure source_node is set
        unit.source_node = unit.source_node or self.node_id

        # Add to Tier
        if unit.tier == MemoryTier.L1_RAW_IO:
            self._l1_buffer.append(unit)
            if len(self._l1_buffer) > self.max_l1_size:
                self._evict_from_l1()

        elif unit.tier == MemoryTier.L2_WORKING:
            self._l2_working.append(unit)

        elif unit.tier == MemoryTier.L3_SESSION:
            session_id = unit.metadata.get("session_id", "default")
            self._l3_session[session_id].append(unit)

        elif unit.tier == MemoryTier.L4_GLOBAL:
            self._l4_global.append(unit)

            # Auto-vectorize L4 content if enabled
            if self.config.auto_vectorize_l4 and self.vector_store and self.embedding_provider:
                await self._vectorize_unit(unit)

            # Check if L4 compression is needed
            if self.l4_compressor and await self.l4_compressor.should_compress(self._l4_global):
                await self._compress_l4()

        # Update Indexes
        self._id_index[unit.id] = unit
        self._type_index[unit.type].append(unit.id)

        return unit.id

    def add_sync(self, unit: MemoryUnit) -> str:
        """Synchronously add a memory unit (for projection, skips vectorization)."""
        # Ensure source_node is set
        unit.source_node = unit.source_node or self.node_id

        # Add to Tier
        if unit.tier == MemoryTier.L1_RAW_IO:
            self._l1_buffer.append(unit)
            if len(self._l1_buffer) > self.max_l1_size:
                self._evict_from_l1()

        elif unit.tier == MemoryTier.L2_WORKING:
            self._l2_working.append(unit)

        elif unit.tier == MemoryTier.L3_SESSION:
            session_id = unit.metadata.get("session_id", "default")
            self._l3_session[session_id].append(unit)

        elif unit.tier == MemoryTier.L4_GLOBAL:
            self._l4_global.append(unit)
            # Note: Skips vectorization for sync operation

        # Update Indexes
        self._id_index[unit.id] = unit
        self._type_index[unit.type].append(unit.id)

        return unit.id

    def get(self, unit_id: str) -> MemoryUnit | None:
        """Retrieve a memory unit by ID."""
        return self._id_index.get(unit_id)

    async def query(self, q: MemoryQuery) -> list[MemoryUnit]:
        """
        Query memory units based on criteria.
        """
        results = []

        # 1. Collect from requested tiers
        target_tiers = q.tiers or [
            MemoryTier.L1_RAW_IO,
            MemoryTier.L2_WORKING,
            MemoryTier.L3_SESSION,
            MemoryTier.L4_GLOBAL
        ]

        for tier in target_tiers:
            if tier == MemoryTier.L1_RAW_IO:
                results.extend(self._l1_buffer)
            elif tier == MemoryTier.L2_WORKING:
                results.extend(self._l2_working)
            elif tier == MemoryTier.L3_SESSION:
                for session_units in self._l3_session.values():
                    results.extend(session_units)
            elif tier == MemoryTier.L4_GLOBAL:
                results.extend(self._l4_global)

        # 2. Filter by Type
        if q.types:
            results = [u for u in results if u.type in q.types]

        # 3. Filter by Node ID
        if q.node_ids:
            results = [u for u in results if u.source_node in q.node_ids]

        # 4. Filter by Time
        if q.since:
            results = [u for u in results if u.created_at >= q.since]
        if q.until:
            results = [u for u in results if u.created_at <= q.until]

        # 5. Semantic Search (L4 Only for MVP)
        if q.query_text and MemoryTier.L4_GLOBAL in target_tiers:
            # Only perform semantic search on L4 items within the result set
            l4_candidates = [u for u in results if u.tier == MemoryTier.L4_GLOBAL]
            others = [u for u in results if u.tier != MemoryTier.L4_GLOBAL]

            scored_l4 = await self._semantic_search(q.query_text, l4_candidates, q.top_k)
            # For now, just append top K L4 matches to others.
            # Ideally, we might want to filter L4 to ONLY top K.
            # Strategy: If semantic search is requested, we PRIORITIZE semantic matches.
            results = others + scored_l4

        # 6. Sort
        reverse = q.descending
        # Dynamic getattr for sort key
        results.sort(
            key=lambda u: getattr(u, q.sort_by, u.created_at),
            reverse=reverse
        )

        return results

    def promote_to_l4(self, unit_id: str):
        """Promote a memory unit to L4 Global persistence."""
        unit = self.get(unit_id)
        if not unit:
            return

        # Remove from current tier if necessary (e.g. L2)
        if unit.tier == MemoryTier.L2_WORKING and unit in self._l2_working:
            self._l2_working.remove(unit)

        # Update tier and add to L4
        unit.tier = MemoryTier.L4_GLOBAL
        if unit not in self._l4_global:
            self._l4_global.append(unit)

    def clear_working(self):
        """Clear L2 Working Memory."""
        for unit in self._l2_working:
             self._remove_from_index(unit)
        self._l2_working.clear()

    def _evict_from_l1(self):
        """
        Evict least important + least recently used item from L1 buffer.
        Uses importance-weighted LRU policy.
        """
        if not self._l1_buffer:
            return

        try:
            # Score = importance * recency_factor
            now = datetime.now()
            scored = []

            for unit in self._l1_buffer:
                age_seconds = (now - unit.created_at).total_seconds()
                # Recency factor decays over hours (1.0 at 0 hours, 0.5 at 1 hour, etc.)
                recency_factor = 1.0 / (1.0 + age_seconds / 3600)
                score = unit.importance * recency_factor
                scored.append((score, unit))

            # Sort by score (lowest first)
            scored.sort(key=lambda x: x[0])

            # Evict lowest scored item
            victim = scored[0][1]
            self._l1_buffer.remove(victim)
            self._remove_from_index(victim)
        except Exception:
            # Fallback to simple FIFO if scoring fails
            if self._l1_buffer:
                removed = self._l1_buffer.pop(0)
                self._remove_from_index(removed)

    async def create_projection(
        self,
        instruction: str,
        total_budget: int = 2000,
        mode: ProjectionMode | None = None,
        include_plan: bool = True,
        include_facts: bool = True
    ) -> ContextProjection:
        """创建上下文投影（增强版）

        Args:
            instruction: 任务指令
            total_budget: 总 token 预算（默认2000）
            mode: 投影模式（可选，不指定则自动检测）
            include_plan: 是否包含父计划
            include_facts: 是否包含相关事实

        Returns:
            上下文投影对象
        """
        # 1. 自动检测模式（如果未指定）
        if mode is None:
            mode = self._detect_mode(instruction)

        # 2. 获取配置
        config = ProjectionConfig.from_mode(mode)

        # 3. 创建投影对象
        projection = ContextProjection(
            instruction=instruction,
            lineage=[self.node_id]
        )

        # 4. 提取 VIP 内容（plan）
        if include_plan:
            plans = [u for u in self._l2_working if u.type == MemoryType.PLAN]
            if plans:
                projection.parent_plan = str(plans[-1].content)

        # 5. 提取 L4 facts（带语义相关性评分）
        if include_facts and self._l4_global:
            scored_facts = await self._score_facts(
                instruction=instruction,
                facts=self._l4_global,
                max_count=config.max_l4_facts,
                config=config
            )
            projection.relevant_facts = scored_facts

        return projection

    def get_statistics(self) -> dict[str, Any]:
        """Get current memory statistics."""
        return {
            "l1_size": len(self._l1_buffer),
            "l2_size": len(self._l2_working),
            "l3_sessions": len(self._l3_session),
            "l4_size": len(self._l4_global),
            "total_units": len(self._id_index),
            "types": {
                t.value: len(ids)
                for t, ids in self._type_index.items()
            }
        }

    def _remove_from_index(self, unit: MemoryUnit):
        """Helper to remove unit from indexes."""
        if unit.id in self._id_index:
            del self._id_index[unit.id]
        if unit.id in self._type_index[unit.type]:
            self._type_index[unit.type].remove(unit.id)

    async def _semantic_search(
        self,
        query: str,
        candidates: list[MemoryUnit],
        top_k: int
    ) -> list[MemoryUnit]:
        """
        Semantic Search using vector store if available, otherwise fallback to keyword matching.
        """
        # Use vector store if available
        if self.vector_store and self.embedding_provider:
            try:
                # Generate query embedding
                query_embedding = await self.embedding_provider.embed_text(query)

                # Search vector store
                results = await self.vector_store.search(
                    query_embedding=query_embedding,
                    top_k=top_k
                )

                # Map results back to MemoryUnits
                matched_units = []
                for result in results:
                    unit = self.get(result.id)
                    if unit and unit in candidates:
                        matched_units.append(unit)

                return matched_units
            except Exception:
                # Fallback to keyword matching on error
                pass

        # Fallback: Simple keyword matching
        scored = []
        query_lower = query.lower()

        for unit in candidates:
            score = 0.0
            content_str = str(unit.content).lower()

            if query_lower in content_str:
                score = 1.0

            final_score = score + (unit.importance * 0.1)
            scored.append((final_score, unit))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [unit for _, unit in scored[:top_k]]

    async def _vectorize_unit(self, unit: MemoryUnit):
        """
        Generate and store embedding for a memory unit.
        """
        if not self.vector_store or not self.embedding_provider:
            return

        try:
            # Generate embedding
            text = str(unit.content)
            embedding = await self.embedding_provider.embed_text(text)

            # Store in vector database
            await self.vector_store.add(
                id=unit.id,
                text=text,
                embedding=embedding,
                metadata={
                    "tier": unit.tier.name,
                    "type": unit.type.value,
                    "importance": unit.importance,
                    "source_node": unit.source_node
                }
            )

            # Store embedding in unit for future use
            unit.embedding = embedding
        except Exception:
            # Log error but don't fail the add operation
            pass

    def _detect_mode(self, instruction: str) -> ProjectionMode:
        """简单的模式检测（基于关键词匹配，支持中英文）

        Args:
            instruction: 任务指令

        Returns:
            检测到的投影模式
        """
        instruction_lower = instruction.lower()

        # 检测 DEBUG 模式（英文 + 中文关键词，各15个）
        debug_keywords = [
            # 英文 (15个)
            'error', 'fix', 'debug', 'retry', 'bug', 'exception', 'failed', 'failure',
            'crash', 'broken', 'issue', 'troubleshoot', 'diagnose', 'resolve', 'repair',
            # 中文 (15个)
            '错误', '修复', '调试', '重试', '失败', '异常', '问题', 'bug',
            '崩溃', '故障', '排查', '诊断', '解决', '修理', '出错'
        ]
        if any(kw in instruction_lower for kw in debug_keywords):
            return ProjectionMode.DEBUG

        # 检测 ANALYTICAL 模式（英文 + 中文关键词，各15个）
        analytical_keywords = [
            # 英文 (15个)
            'analyze', 'analyse', 'evaluate', 'research', 'investigate', 'study',
            'examine', 'review', 'assess', 'compare', 'measure', 'benchmark',
            'profile', 'inspect', 'survey',
            # 中文 (15个)
            '分析', '评估', '研究', '调查', '探索',
            '检验', '审查', '对比', '比较', '测量', '测试', '考察', '观察', '查看', '统计'
        ]
        if any(kw in instruction_lower for kw in analytical_keywords):
            return ProjectionMode.ANALYTICAL

        # 检测 CONTEXTUAL 模式（英文 + 中文关键词，各15个）
        contextual_keywords = [
            # 英文 (15个)
            'continue', 'context', 'previous', 'earlier', 'before', 'last',
            'resume', 'recall', 'remember', 'mentioned', 'discussed', 'talked',
            'said', 'above', 'prior',
            # 中文 (15个)
            '继续', '上下文', '之前', '刚才', '前面', '上次', '接着',
            '恢复', '回忆', '记得', '提到', '讨论过', '说过', '上面', '最近'
        ]
        if any(kw in instruction_lower for kw in contextual_keywords):
            return ProjectionMode.CONTEXTUAL

        # 检测 MINIMAL 模式（非常短的指令）
        # 检测是否包含中文字符
        def has_chinese(text):
            return any('\u4e00' <= char <= '\u9fff' for char in text)

        instruction_stripped = instruction.strip()

        if has_chinese(instruction_stripped):
            # 中文或中英混合：按字符数判断（< 8个字符）
            if len(instruction_stripped) < 8:
                return ProjectionMode.MINIMAL
        else:
            # 纯英文：按单词数判断（< 3个单词）
            word_count = len(instruction_stripped.split())
            if word_count < 3:
                return ProjectionMode.MINIMAL

        # 默认：STANDARD 模式
        return ProjectionMode.STANDARD

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度

        Args:
            vec1: 向量1
            vec2: 向量2

        Returns:
            余弦相似度 (0-1)
        """
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    async def _score_facts(
        self,
        instruction: str,
        facts: list[MemoryUnit],
        max_count: int,
        config: ProjectionConfig
    ) -> list[MemoryUnit]:
        """评分并选择 facts

        Args:
            instruction: 任务指令
            facts: 候选 facts
            max_count: 最大选择数量
            config: 投影配置

        Returns:
            评分后的 top K facts
        """
        if not facts:
            return []

        # 如果有 embedding provider，使用语义相似度
        if self.embedding_provider:
            return await self._score_facts_semantic(instruction, facts, max_count, config)
        else:
            # 降级：只按 importance 排序
            sorted_facts = sorted(
                facts,
                key=lambda f: f.importance,
                reverse=True
            )
            return sorted_facts[:max_count]

    async def _score_facts_semantic(
        self,
        instruction: str,
        facts: list[MemoryUnit],
        max_count: int,
        config: ProjectionConfig
    ) -> list[MemoryUnit]:
        """使用语义相似度评分 facts

        Args:
            instruction: 任务指令
            facts: 候选 facts
            max_count: 最大选择数量
            config: 投影配置

        Returns:
            评分后的 top K facts
        """
        if not facts or not self.embedding_provider:
            return []

        try:
            # 计算 instruction 的 embedding
            instruction_emb = await self.embedding_provider.embed_text(instruction)

            # 计算每个 fact 的分数
            scored = []
            for fact in facts:
                # 如果 fact 已有 embedding，使用它
                if fact.embedding:
                    fact_emb = fact.embedding
                else:
                    # 否则实时计算
                    fact_emb = await self.embedding_provider.embed_text(str(fact.content))

                # 计算余弦相似度
                similarity = self._cosine_similarity(instruction_emb, fact_emb)

                # 混合评分：importance + relevance
                score = (
                    config.importance_weight * fact.importance +
                    config.relevance_weight * similarity
                )
                scored.append((score, fact))

            # 排序并返回 top K
            scored.sort(key=lambda x: x[0], reverse=True)
            return [fact for _, fact in scored[:max_count]]

        except Exception:
            # 出错时降级到只按 importance 排序
            sorted_facts = sorted(
                facts,
                key=lambda f: f.importance,
                reverse=True
            )
            return sorted_facts[:max_count]

    def enable_l4_compression(
        self,
        llm_provider,
        threshold: int = 150,
        similarity_threshold: float = 0.75,
        min_cluster_size: int = 3
    ):
        """启用L4自动压缩

        Args:
            llm_provider: LLM提供者，用于总结clusters
            threshold: 触发压缩的facts数量阈值
            similarity_threshold: 聚类相似度阈值（0-1）
            min_cluster_size: 最小聚类大小
        """
        from .compression import L4Compressor

        self.l4_compressor = L4Compressor(
            llm_provider=llm_provider,
            embedding_provider=self.embedding_provider,
            threshold=threshold,
            similarity_threshold=similarity_threshold,
            min_cluster_size=min_cluster_size
        )

    async def _compress_l4(self):
        """执行L4压缩"""
        print(f"🗜️  L4压缩开始：当前{len(self._l4_global)}个facts")

        # 执行压缩
        compressed = await self.l4_compressor.compress(self._l4_global)

        # 更新索引：移除旧的facts
        for fact in self._l4_global:
            self._remove_from_index(fact)

        # 替换L4
        self._l4_global = compressed

        # 更新索引：添加新的facts
        for fact in compressed:
            self._id_index[fact.id] = fact
            self._type_index[fact.type].append(fact.id)

        print(f"✅ L4压缩完成：压缩后{len(self._l4_global)}个facts")
