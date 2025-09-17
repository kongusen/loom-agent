"""
上下文管理器

通过解决基本约束、实施复杂的内存层次结构和开发压缩技术高效组织和利用上下文信息
受Claude Code的弱引用机制启发
"""

import asyncio
import weakref
import json
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ...types import (
    ProcessedContext, ManagedContext, SessionState,
    WeakValueDictionary, CachedResult, CacheStrategy
)


@dataclass
class SessionConstraints:
    """会话约束"""
    max_memory_mb: int = 512
    max_context_items: int = 1000
    cache_policy: str = "adaptive"
    compression_level: int = 1
    memory_strategy: str = "balanced"


@dataclass
class MemoryAllocation:
    """内存分配"""
    tier: str  # hot, warm, cold
    allocated_size: int = 0
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = time.time()


@dataclass
class AllocationStrategy:
    """分配策略"""
    priority: str = "medium"  # high, medium, low
    access_pattern: str = "unknown"  # frequent, occasional, rare
    retention_policy: str = "normal"  # persistent, normal, temporary


class ConstraintResolver:
    """约束解决器"""
    
    def __init__(self):
        self.constraint_rules = {
            "memory_pressure": self._handle_memory_pressure,
            "token_limit": self._handle_token_limit,
            "quality_threshold": self._handle_quality_threshold,
            "time_constraint": self._handle_time_constraint
        }
    
    async def resolve(self, processed_context: ProcessedContext,
                     session_constraints: SessionConstraints) -> Dict[str, Any]:
        """解决约束冲突"""
        
        # 分析当前约束状态
        constraint_analysis = self._analyze_constraints(processed_context, session_constraints)
        
        # 应用约束解决规则
        resolved_constraints = {}
        for constraint_type, violation in constraint_analysis.items():
            if violation["violated"]:
                resolution = await self.constraint_rules[constraint_type](
                    violation, session_constraints
                )
                resolved_constraints[constraint_type] = resolution
            else:
                resolved_constraints[constraint_type] = {"action": "none", "status": "satisfied"}
        
        return {
            "constraint_analysis": constraint_analysis,
            "resolutions": resolved_constraints,
            "memory_strategy": self._determine_memory_strategy(resolved_constraints),
            "compression_level": self._determine_compression_level(resolved_constraints),
            "cache_policy": self._determine_cache_policy(resolved_constraints)
        }
    
    def _analyze_constraints(self, context: ProcessedContext, 
                           constraints: SessionConstraints) -> Dict[str, Dict[str, Any]]:
        """分析约束状态"""
        
        # 估算内存使用
        content_size = len(json.dumps(context.content))
        estimated_memory = content_size / (1024 * 1024)  # MB
        
        # 估算项目数量
        item_count = self._count_context_items(context.content)
        
        # 分析质量分数
        avg_quality = self._calculate_average_quality(context)
        
        return {
            "memory_pressure": {
                "violated": estimated_memory > constraints.max_memory_mb,
                "current": estimated_memory,
                "limit": constraints.max_memory_mb,
                "severity": max(0, (estimated_memory - constraints.max_memory_mb) / constraints.max_memory_mb)
            },
            "token_limit": {
                "violated": item_count > constraints.max_context_items,
                "current": item_count,
                "limit": constraints.max_context_items,
                "severity": max(0, (item_count - constraints.max_context_items) / constraints.max_context_items)
            },
            "quality_threshold": {
                "violated": avg_quality < 0.5,
                "current": avg_quality,
                "threshold": 0.5,
                "severity": max(0, (0.5 - avg_quality) / 0.5)
            },
            "time_constraint": {
                "violated": False,  # 简化实现
                "current": 0,
                "limit": 1000,
                "severity": 0
            }
        }
    
    def _count_context_items(self, context: Dict[str, Any]) -> int:
        """计算上下文项目数量"""
        
        def count_items(obj):
            if isinstance(obj, dict):
                return sum(count_items(v) for v in obj.values()) + len(obj)
            elif isinstance(obj, list):
                return sum(count_items(item) for item in obj) + len(obj)
            else:
                return 1
        
        return count_items(context)
    
    def _calculate_average_quality(self, context: ProcessedContext) -> float:
        """计算平均质量分数"""
        
        if not context.optimization_trace:
            return 0.8  # 默认值
        
        quality_scores = []
        for trace in context.optimization_trace:
            if "quality_after" in trace:
                scores = trace["quality_after"].values()
                quality_scores.extend(scores)
        
        return sum(quality_scores) / len(quality_scores) if quality_scores else 0.8
    
    async def _handle_memory_pressure(self, violation: Dict[str, Any], 
                                    constraints: SessionConstraints) -> Dict[str, Any]:
        """处理内存压力"""
        
        severity = violation["severity"]
        
        if severity > 0.5:  # 严重内存压力
            return {
                "action": "aggressive_compression",
                "compression_ratio": 0.3,
                "cache_eviction": True,
                "priority": "high"
            }
        elif severity > 0.2:  # 中等内存压力
            return {
                "action": "moderate_compression",
                "compression_ratio": 0.6,
                "cache_eviction": False,
                "priority": "medium"
            }
        else:  # 轻微内存压力
            return {
                "action": "light_compression",
                "compression_ratio": 0.8,
                "cache_eviction": False,
                "priority": "low"
            }
    
    async def _handle_token_limit(self, violation: Dict[str, Any], 
                                constraints: SessionConstraints) -> Dict[str, Any]:
        """处理token限制"""
        
        severity = violation["severity"]
        
        return {
            "action": "truncate_content",
            "target_reduction": min(0.5, severity),
            "preserve_important": True,
            "priority": "high" if severity > 0.3 else "medium"
        }
    
    async def _handle_quality_threshold(self, violation: Dict[str, Any], 
                                      constraints: SessionConstraints) -> Dict[str, Any]:
        """处理质量阈值"""
        
        return {
            "action": "quality_enhancement",
            "target_quality": 0.7,
            "enhancement_methods": ["content_enrichment", "relevance_filtering"],
            "priority": "medium"
        }
    
    async def _handle_time_constraint(self, violation: Dict[str, Any], 
                                    constraints: SessionConstraints) -> Dict[str, Any]:
        """处理时间约束"""
        
        return {
            "action": "optimize_processing",
            "target_time": 1.0,
            "optimization_methods": ["parallel_processing", "caching"],
            "priority": "high"
        }
    
    def _determine_memory_strategy(self, resolutions: Dict[str, Dict[str, Any]]) -> str:
        """确定内存策略"""
        
        memory_resolution = resolutions.get("memory_pressure", {})
        
        if memory_resolution.get("priority") == "high":
            return "aggressive"
        elif memory_resolution.get("priority") == "medium":
            return "balanced"
        else:
            return "conservative"
    
    def _determine_compression_level(self, resolutions: Dict[str, Dict[str, Any]]) -> int:
        """确定压缩级别"""
        
        memory_resolution = resolutions.get("memory_pressure", {})
        token_resolution = resolutions.get("token_limit", {})
        
        memory_priority = memory_resolution.get("priority", "low")
        token_priority = token_resolution.get("priority", "low")
        
        if memory_priority == "high" or token_priority == "high":
            return 3  # 最高压缩
        elif memory_priority == "medium" or token_priority == "medium":
            return 2  # 中等压缩
        else:
            return 1  # 轻度压缩
    
    def _determine_cache_policy(self, resolutions: Dict[str, Dict[str, Any]]) -> str:
        """确定缓存策略"""
        
        memory_resolution = resolutions.get("memory_pressure", {})
        
        if memory_resolution.get("cache_eviction"):
            return "aggressive_eviction"
        else:
            return "adaptive"


class MemoryHierarchy:
    """多层内存管理，类似Claude Code的弱引用系统"""
    
    def __init__(self):
        self.hot_memory: Dict[str, Any] = {}  # 频繁访问的上下文
        self.warm_memory = WeakValueDictionary()  # 中等频率访问
        self.cold_storage: Dict[str, bytes] = {}  # 长期存储（压缩）
        self.gc_registry = weakref.finalize
        
        # 访问统计
        self.access_stats: Dict[str, MemoryAllocation] = {}
        
        # 清理任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    async def allocate(self, context: ProcessedContext, 
                      allocation_strategy: AllocationStrategy) -> MemoryAllocation:
        """分配内存层次"""
        
        context_id = self._generate_context_id(context)
        
        allocation = MemoryAllocation()
        
        # 根据访问模式和重要性分配到不同层次
        if allocation_strategy.priority == 'high':
            self.hot_memory[context_id] = context
            allocation.tier = 'hot'
            allocation.allocated_size = len(json.dumps(context.content))
        elif allocation_strategy.priority == 'medium':
            # 使用弱引用存储
            self.warm_memory[context_id] = context
            allocation.tier = 'warm'
            allocation.allocated_size = len(json.dumps(context.content))
        else:
            # 压缩存储
            compressed_data = await self._compress_context(context)
            self.cold_storage[context_id] = compressed_data
            allocation.tier = 'cold'
            allocation.allocated_size = len(compressed_data)
        
        # 记录分配信息
        self.access_stats[context_id] = allocation
        
        # 注册清理回调
        if allocation_strategy.retention_policy != "persistent":
            self.gc_registry(context, self._cleanup_callback, context_id)
        
        return allocation
    
    async def retrieve(self, context_id: str) -> Optional[ProcessedContext]:
        """从内存层次中检索上下文"""
        
        # 更新访问统计
        if context_id in self.access_stats:
            self.access_stats[context_id].update_access()
        
        # 按层次检索
        if context_id in self.hot_memory:
            return self.hot_memory[context_id]
        
        if context_id in self.warm_memory:
            context = self.warm_memory[context_id]
            if context is not None:
                # 如果访问频繁，提升到热内存
                if self.access_stats[context_id].access_count > 5:
                    self.hot_memory[context_id] = context
                    del self.warm_memory[context_id]
                return context
        
        if context_id in self.cold_storage:
            compressed_data = self.cold_storage[context_id]
            context = await self._decompress_context(compressed_data)
            
            # 根据访问频率决定是否提升
            if self.access_stats[context_id].access_count > 2:
                self.warm_memory[context_id] = context
                del self.cold_storage[context_id]
            
            return context
        
        return None
    
    async def evict(self, context_id: str) -> bool:
        """从内存中移除上下文"""
        
        evicted = False
        
        if context_id in self.hot_memory:
            del self.hot_memory[context_id]
            evicted = True
        
        if context_id in self.warm_memory:
            del self.warm_memory[context_id]
            evicted = True
        
        if context_id in self.cold_storage:
            del self.cold_storage[context_id]
            evicted = True
        
        if context_id in self.access_stats:
            del self.access_stats[context_id]
        
        return evicted
    
    async def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        
        hot_size = sum(len(json.dumps(obj.content if hasattr(obj, 'content') else obj)) 
                      for obj in self.hot_memory.values())
        warm_size = sum(len(json.dumps(obj.content if hasattr(obj, 'content') else obj)) 
                       for obj in self.warm_memory._data.values() 
                       if obj is not None and not callable(obj))
        cold_size = sum(len(data) for data in self.cold_storage.values())
        
        return {
            "hot_memory": {
                "items": len(self.hot_memory),
                "size_bytes": hot_size
            },
            "warm_memory": {
                "items": len(self.warm_memory._data),
                "size_bytes": warm_size
            },
            "cold_storage": {
                "items": len(self.cold_storage),
                "size_bytes": cold_size
            },
            "total_items": len(self.access_stats),
            "total_size_bytes": hot_size + warm_size + cold_size
        }
    
    def _generate_context_id(self, context: ProcessedContext) -> str:
        """生成上下文ID"""
        content_hash = hashlib.md5(
            json.dumps(context.content, sort_keys=True).encode()
        ).hexdigest()
        return f"ctx_{content_hash[:16]}_{int(time.time())}"
    
    async def _compress_context(self, context: ProcessedContext) -> bytes:
        """压缩上下文（简化实现）"""
        import gzip
        
        data = json.dumps({
            "content": context.content,
            "metadata": context.processing_metadata
        }).encode('utf-8')
        
        return gzip.compress(data)
    
    async def _decompress_context(self, compressed_data: bytes) -> ProcessedContext:
        """解压上下文"""
        import gzip
        
        decompressed = gzip.decompress(compressed_data)
        data = json.loads(decompressed.decode('utf-8'))
        
        return ProcessedContext(
            content=data["content"],
            processing_metadata=data["metadata"]
        )
    
    def _cleanup_callback(self, context_id: str):
        """清理回调"""
        asyncio.create_task(self.evict(context_id))
    
    def _start_cleanup_task(self):
        """启动定期清理任务"""
        
        async def cleanup_routine():
            while True:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._perform_cleanup()
        
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(cleanup_routine())
    
    async def _perform_cleanup(self):
        """执行定期清理"""
        
        current_time = time.time()
        cleanup_threshold = 3600  # 1小时未访问
        
        # 清理长时间未访问的项目
        to_evict = []
        for context_id, allocation in self.access_stats.items():
            if current_time - allocation.last_access > cleanup_threshold:
                if allocation.tier in ["warm", "cold"]:  # 保留热内存
                    to_evict.append(context_id)
        
        for context_id in to_evict:
            await self.evict(context_id)


class CompressionEngine:
    """压缩引擎"""
    
    def __init__(self):
        self.compression_methods = {
            1: self._light_compression,
            2: self._moderate_compression,
            3: self._aggressive_compression
        }
        self.decompression_cache: Dict[str, Any] = {}
    
    async def compress(self, context: ProcessedContext, 
                      compression_level: int,
                      preserve_semantics: bool = True) -> ProcessedContext:
        """压缩上下文"""
        
        if compression_level not in self.compression_methods:
            compression_level = 1
        
        compression_method = self.compression_methods[compression_level]
        
        compressed_content = await compression_method(
            context.content, preserve_semantics
        )
        
        # 计算压缩比
        original_size = len(json.dumps(context.content))
        compressed_size = len(json.dumps(compressed_content))
        compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
        
        # 更新元数据
        updated_metadata = context.processing_metadata.copy()
        updated_metadata.update({
            "compression_applied": True,
            "compression_level": compression_level,
            "compression_ratio": compression_ratio,
            "original_size": original_size,
            "compressed_size": compressed_size
        })
        
        return ProcessedContext(
            content=compressed_content,
            processing_metadata=updated_metadata,
            optimization_trace=context.optimization_trace
        )
    
    async def _light_compression(self, content: Dict[str, Any], 
                               preserve_semantics: bool) -> Dict[str, Any]:
        """轻度压缩"""
        
        compressed = {}
        
        for key, value in content.items():
            if isinstance(value, str):
                # 简单的空白字符压缩
                compressed_value = ' '.join(value.split())
                if len(compressed_value) < len(value) * 0.9:  # 至少减少10%
                    compressed[key] = compressed_value
                else:
                    compressed[key] = value
            elif isinstance(value, (list, dict)):
                # 递归压缩
                if isinstance(value, dict):
                    compressed[key] = await self._light_compression(value, preserve_semantics)
                else:
                    compressed[key] = value  # 列表暂不压缩
            else:
                compressed[key] = value
        
        return compressed
    
    async def _moderate_compression(self, content: Dict[str, Any], 
                                  preserve_semantics: bool) -> Dict[str, Any]:
        """中度压缩"""
        
        compressed = {}
        
        for key, value in content.items():
            if isinstance(value, str) and len(value) > 200:
                # 保留前后部分，中间用省略号
                if preserve_semantics:
                    compressed_value = value[:100] + "..." + value[-50:]
                else:
                    compressed_value = value[:150] + "..."
                compressed[key] = compressed_value
            elif isinstance(value, dict):
                # 递归压缩，但跳过一些不重要的键
                important_keys = ["content", "result", "main", "summary"]
                filtered_value = {
                    k: v for k, v in value.items()
                    if k in important_keys or len(str(v)) < 100
                }
                compressed[key] = await self._moderate_compression(filtered_value, preserve_semantics)
            elif isinstance(value, list) and len(value) > 10:
                # 截断长列表
                compressed[key] = value[:5] + [{"truncated": len(value) - 5}] + value[-5:]
            else:
                compressed[key] = value
        
        return compressed
    
    async def _aggressive_compression(self, content: Dict[str, Any], 
                                    preserve_semantics: bool) -> Dict[str, Any]:
        """激进压缩"""
        
        compressed = {}
        
        # 只保留最重要的键
        important_keys = ["content", "result", "summary", "main"]
        
        for key, value in content.items():
            if key in important_keys or len(str(value)) < 50:
                if isinstance(value, str) and len(value) > 100:
                    # 大幅截断文本
                    if preserve_semantics:
                        # 尝试保留句子结构
                        sentences = value.split('.')
                        if len(sentences) > 2:
                            compressed_value = sentences[0] + "." + sentences[-1]
                        else:
                            compressed_value = value[:50] + "..."
                    else:
                        compressed_value = value[:80] + "..."
                    compressed[key] = compressed_value
                elif isinstance(value, dict):
                    # 递归激进压缩
                    compressed[key] = await self._aggressive_compression(value, preserve_semantics)
                elif isinstance(value, list) and len(value) > 3:
                    # 大幅截断列表
                    compressed[key] = value[:2] + [{"truncated": len(value) - 2}]
                else:
                    compressed[key] = value
        
        return compressed


class ContextCache:
    """上下文缓存"""
    
    def __init__(self):
        self.cache_tiers = {
            "hot": {},  # 内存缓存
            "warm": WeakValueDictionary(),  # 弱引用缓存
            "cold": {}  # 持久缓存
        }
        self.cache_policies = {
            "adaptive": self._adaptive_policy,
            "aggressive_eviction": self._aggressive_eviction_policy,
            "conservative": self._conservative_policy
        }
        self.access_tracker: Dict[str, List[float]] = defaultdict(list)
    
    async def store(self, context: ProcessedContext, 
                   cache_policy: str) -> str:
        """存储上下文到缓存"""
        
        cache_key = self._generate_cache_key(context)
        
        # 根据策略选择缓存层
        tier = await self._select_cache_tier(context, cache_policy)
        
        # 存储到相应层
        if tier == "hot":
            self.cache_tiers["hot"][cache_key] = context
        elif tier == "warm":
            self.cache_tiers["warm"][cache_key] = context
        else:  # cold
            compressed_context = await self._compress_for_cold_storage(context)
            self.cache_tiers["cold"][cache_key] = compressed_context
        
        # 记录访问
        self.access_tracker[cache_key].append(time.time())
        
        return cache_key
    
    async def retrieve(self, cache_key: str) -> Optional[ProcessedContext]:
        """从缓存检索上下文"""
        
        # 按层级检索
        for tier_name, tier_cache in self.cache_tiers.items():
            if cache_key in tier_cache:
                context = tier_cache[cache_key]
                
                # 如果是冷存储，需要解压
                if tier_name == "cold":
                    context = await self._decompress_from_cold_storage(context)
                
                # 记录访问
                self.access_tracker[cache_key].append(time.time())
                
                # 根据访问频率可能提升缓存层级
                await self._maybe_promote_cache_tier(cache_key, tier_name)
                
                return context
        
        return None
    
    async def evict(self, cache_key: str) -> bool:
        """从缓存中移除"""
        
        evicted = False
        
        for tier_cache in self.cache_tiers.values():
            if cache_key in tier_cache:
                del tier_cache[cache_key]
                evicted = True
        
        if cache_key in self.access_tracker:
            del self.access_tracker[cache_key]
        
        return evicted
    
    async def _select_cache_tier(self, context: ProcessedContext, 
                               policy: str) -> str:
        """选择缓存层级"""
        
        if policy in self.cache_policies:
            return await self.cache_policies[policy](context)
        else:
            return await self._adaptive_policy(context)
    
    async def _adaptive_policy(self, context: ProcessedContext) -> str:
        """自适应缓存策略"""
        
        # 基于内容大小和质量决定缓存层级
        content_size = len(json.dumps(context.content))
        
        # 获取质量分数
        quality_score = 0.8  # 默认值
        if context.optimization_trace:
            latest_trace = context.optimization_trace[-1]
            if "quality_after" in latest_trace:
                quality_scores = list(latest_trace["quality_after"].values())
                quality_score = sum(quality_scores) / len(quality_scores)
        
        if content_size < 10000 and quality_score > 0.8:
            return "hot"
        elif content_size < 50000 and quality_score > 0.6:
            return "warm"
        else:
            return "cold"
    
    async def _aggressive_eviction_policy(self, context: ProcessedContext) -> str:
        """激进淘汰策略"""
        
        # 优先使用弱引用和冷存储
        content_size = len(json.dumps(context.content))
        
        if content_size < 5000:
            return "warm"
        else:
            return "cold"
    
    async def _conservative_policy(self, context: ProcessedContext) -> str:
        """保守策略"""
        
        # 优先使用热缓存
        return "hot"
    
    async def _maybe_promote_cache_tier(self, cache_key: str, current_tier: str):
        """可能提升缓存层级"""
        
        access_times = self.access_tracker[cache_key]
        
        # 如果最近访问频繁，提升层级
        recent_accesses = [t for t in access_times if time.time() - t < 3600]  # 1小时内
        
        if len(recent_accesses) > 3:  # 1小时内访问超过3次
            if current_tier == "cold":
                # 从冷存储提升到温缓存
                context = self.cache_tiers["cold"][cache_key]
                decompressed = await self._decompress_from_cold_storage(context)
                self.cache_tiers["warm"][cache_key] = decompressed
                del self.cache_tiers["cold"][cache_key]
            elif current_tier == "warm" and len(recent_accesses) > 5:
                # 从温缓存提升到热缓存
                context = self.cache_tiers["warm"][cache_key]
                self.cache_tiers["hot"][cache_key] = context
                del self.cache_tiers["warm"][cache_key]
    
    def _generate_cache_key(self, context: ProcessedContext) -> str:
        """生成缓存键"""
        
        content_hash = hashlib.md5(
            json.dumps(context.content, sort_keys=True).encode()
        ).hexdigest()
        
        return f"cache_{content_hash[:16]}"
    
    async def _compress_for_cold_storage(self, context: ProcessedContext) -> bytes:
        """为冷存储压缩"""
        import gzip
        
        data = json.dumps({
            "content": context.content,
            "metadata": context.processing_metadata,
            "trace": context.optimization_trace
        }).encode('utf-8')
        
        return gzip.compress(data)
    
    async def _decompress_from_cold_storage(self, compressed_data: bytes) -> ProcessedContext:
        """从冷存储解压"""
        import gzip
        
        decompressed = gzip.decompress(compressed_data)
        data = json.loads(decompressed.decode('utf-8'))
        
        return ProcessedContext(
            content=data["content"],
            processing_metadata=data["metadata"],
            optimization_trace=data.get("trace", [])
        )


class ContextManager:
    """上下文管理器主类"""
    
    def __init__(self):
        self.constraint_resolver = ConstraintResolver()
        self.memory_hierarchy = MemoryHierarchy()
        self.compression_engine = CompressionEngine()
        self.context_cache = ContextCache()
        
        # 性能指标
        self.management_metrics = {
            "contexts_managed": 0,
            "average_compression_ratio": 0.0,
            "cache_hit_rate": 0.0,
            "memory_efficiency": 0.0
        }
    
    async def manage_context(self, processed_context: ProcessedContext,
                           session_constraints: SessionConstraints) -> ManagedContext:
        """管理上下文的主入口方法"""
        
        start_time = time.time()
        
        # 1. 基本约束解决
        resolved_constraints = await self.constraint_resolver.resolve(
            processed_context, session_constraints
        )
        
        # 2. 内存层次结构管理
        allocation_strategy = AllocationStrategy(
            priority=self._determine_priority(processed_context, resolved_constraints),
            access_pattern=self._predict_access_pattern(processed_context),
            retention_policy=self._determine_retention_policy(session_constraints)
        )
        
        memory_allocation = await self.memory_hierarchy.allocate(
            processed_context, allocation_strategy
        )
        
        # 3. 智能压缩
        compression_level = resolved_constraints["compression_level"]
        compressed_context = await self.compression_engine.compress(
            processed_context,
            compression_level=compression_level,
            preserve_semantics=True
        )
        
        # 4. 上下文缓存管理
        cache_policy = resolved_constraints["cache_policy"]
        cache_entry = await self.context_cache.store(
            compressed_context, cache_policy
        )
        
        # 5. 生成管理元数据
        management_time = time.time() - start_time
        management_metadata = self._generate_management_metadata(
            resolved_constraints, memory_allocation, management_time
        )
        
        # 6. 更新性能指标
        self._update_metrics(compressed_context, cache_entry)
        
        return ManagedContext(
            active_context=compressed_context,
            memory_footprint={
                "allocation": memory_allocation,
                "memory_stats": await self.memory_hierarchy.get_memory_stats()
            },
            cache_reference=cache_entry,
            management_metadata=management_metadata
        )
    
    async def recover_context(self, context_id: str, 
                            corruption_type: str) -> Optional[ProcessedContext]:
        """恢复损坏的上下文"""
        
        recovery_methods = {
            "memory_corruption": self._recover_from_memory,
            "cache_corruption": self._recover_from_cache,
            "compression_error": self._recover_from_compression_error
        }
        
        if corruption_type in recovery_methods:
            return await recovery_methods[corruption_type](context_id)
        
        return None
    
    async def _recover_from_memory(self, context_id: str) -> Optional[ProcessedContext]:
        """从内存损坏中恢复"""
        
        # 尝试从不同内存层级恢复
        context = await self.memory_hierarchy.retrieve(context_id)
        if context:
            return context
        
        # 尝试从缓存恢复
        cache_key = f"cache_{context_id}"
        return await self.context_cache.retrieve(cache_key)
    
    async def _recover_from_cache(self, context_id: str) -> Optional[ProcessedContext]:
        """从缓存损坏中恢复"""
        
        # 尝试从内存层级恢复
        return await self.memory_hierarchy.retrieve(context_id)
    
    async def _recover_from_compression_error(self, context_id: str) -> Optional[ProcessedContext]:
        """从压缩错误中恢复"""
        
        # 尝试从原始内存恢复（未压缩版本）
        context = await self.memory_hierarchy.retrieve(context_id)
        if context and not context.processing_metadata.get("compression_applied"):
            return context
        
        return None
    
    def _determine_priority(self, context: ProcessedContext, 
                          constraints: Dict[str, Any]) -> str:
        """确定优先级"""
        
        # 基于约束解决结果确定优先级
        memory_resolution = constraints["resolutions"].get("memory_pressure", {})
        quality_resolution = constraints["resolutions"].get("quality_threshold", {})
        
        if memory_resolution.get("priority") == "high":
            return "low"  # 内存压力大时降低优先级
        elif quality_resolution.get("action") == "quality_enhancement":
            return "high"  # 需要质量提升时提高优先级
        else:
            return "medium"
    
    def _predict_access_pattern(self, context: ProcessedContext) -> str:
        """预测访问模式"""
        
        # 简化实现：基于内容特征预测
        content_size = len(json.dumps(context.content))
        
        if content_size < 10000:
            return "frequent"  # 小内容可能频繁访问
        elif content_size < 50000:
            return "occasional"
        else:
            return "rare"  # 大内容访问较少
    
    def _determine_retention_policy(self, constraints: SessionConstraints) -> str:
        """确定保留策略"""
        
        if constraints.cache_policy == "aggressive_eviction":
            return "temporary"
        elif constraints.memory_strategy == "conservative":
            return "persistent"
        else:
            return "normal"
    
    def _generate_management_metadata(self, constraints: Dict[str, Any],
                                    allocation: MemoryAllocation,
                                    management_time: float) -> Dict[str, Any]:
        """生成管理元数据"""
        
        return {
            "management_time": management_time,
            "constraints_resolved": len(constraints["resolutions"]),
            "memory_tier": allocation.tier,
            "allocated_size": allocation.allocated_size,
            "compression_applied": constraints["compression_level"] > 1,
            "cache_policy": constraints["cache_policy"],
            "management_version": "2.0.0",
            "constraint_violations": [
                k for k, v in constraints["constraint_analysis"].items()
                if v["violated"]
            ]
        }
    
    def _update_metrics(self, context: ProcessedContext, cache_key: str):
        """更新管理指标"""
        
        self.management_metrics["contexts_managed"] += 1
        
        # 更新压缩比
        if context.processing_metadata.get("compression_applied"):
            compression_ratio = context.processing_metadata.get("compression_ratio", 1.0)
            current_avg = self.management_metrics["average_compression_ratio"]
            total_managed = self.management_metrics["contexts_managed"]
            
            self.management_metrics["average_compression_ratio"] = (
                (current_avg * (total_managed - 1) + compression_ratio) / total_managed
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.management_metrics.copy()
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        
        memory_stats = await self.memory_hierarchy.get_memory_stats()
        
        return {
            "memory_hierarchy": memory_stats,
            "management_metrics": self.get_performance_metrics(),
            "cache_status": {
                "hot_items": len(self.context_cache.cache_tiers["hot"]),
                "warm_items": len(self.context_cache.cache_tiers["warm"]._data),
                "cold_items": len(self.context_cache.cache_tiers["cold"])
            },
            "system_health": self._calculate_system_health(memory_stats)
        }
    
    def _calculate_system_health(self, memory_stats: Dict[str, Any]) -> str:
        """计算系统健康状态"""
        
        total_size = memory_stats["total_size_bytes"]
        total_items = memory_stats["total_items"]
        
        # 简化的健康评估
        if total_size > 100 * 1024 * 1024:  # > 100MB
            return "warning"
        elif total_items > 1000:
            return "warning"
        else:
            return "healthy"