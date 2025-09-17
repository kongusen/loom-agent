"""
上下文处理器

通过长序列处理、自我优化机制和结构化数据集成变换和优化获取的信息
受Claude Code的normalizeToSize算法启发
"""

import asyncio
import json
import time
import copy
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime

from ...types import (
    ContextPackage, ProcessedContext, 
    ContextRequirements
)


@dataclass
class ProcessingConstraints:
    """处理约束"""
    max_tokens: int = 100000
    target_size: Optional[int] = None
    preserve_structure: bool = True
    goals: List[str] = field(default_factory=lambda: ["relevance", "completeness"])
    optimization_level: int = 1  # 1-3, 3为最高优化


@dataclass
class ContextSequence:
    """上下文序列"""
    content: str
    tokens: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 1.0
    
    def __post_init__(self):
        if not self.tokens:
            # 简单的分词
            self.tokens = self.content.split()


@dataclass
class ProcessedSequence:
    """处理后的序列"""
    original_sequence: ContextSequence
    processed_content: str
    token_reduction: float = 0.0
    quality_score: float = 1.0
    processing_methods: List[str] = field(default_factory=list)
    
    @classmethod
    def from_sequence(cls, sequence: ContextSequence) -> 'ProcessedSequence':
        """从原始序列创建"""
        return cls(
            original_sequence=sequence,
            processed_content=sequence.content,
            quality_score=sequence.importance_score
        )


class LongSequenceProcessor:
    """长序列处理器，实现类似Claude Code的智能截断"""
    
    def __init__(self):
        self.tokenizer_cache: Dict[str, List[str]] = {}
        self.compression_strategies = {
            "truncate_low_importance": self._truncate_by_importance,
            "summarize_redundant": self._summarize_redundant_content,
            "preserve_structure": self._structure_aware_truncation,
            "priority_based": self._priority_based_truncation
        }
    
    async def process(self, sequences: List[ContextSequence], 
                     max_length: int, preserve_structure: bool = True) -> List[ProcessedSequence]:
        """处理长序列"""
        
        processed = []
        total_tokens = sum(len(seq.tokens) for seq in sequences)
        
        if total_tokens <= max_length:
            # 不需要处理，直接转换
            for sequence in sequences:
                processed.append(ProcessedSequence.from_sequence(sequence))
            return processed
        
        # 需要压缩
        compression_ratio = max_length / total_tokens
        
        for sequence in sequences:
            if len(sequence.tokens) <= max_length * compression_ratio:
                processed.append(ProcessedSequence.from_sequence(sequence))
                continue
            
            # 智能截断策略
            if preserve_structure:
                truncated = await self._structure_aware_truncation(sequence, int(max_length * compression_ratio))
            else:
                truncated = await self._priority_based_truncation(sequence, int(max_length * compression_ratio))
            
            processed.append(truncated)
        
        return processed
    
    async def _structure_aware_truncation(self, sequence: ContextSequence, 
                                        max_length: int) -> ProcessedSequence:
        """结构感知的截断"""
        
        content = sequence.content
        tokens = sequence.tokens
        
        if len(tokens) <= max_length:
            return ProcessedSequence.from_sequence(sequence)
        
        # 分析结构 (简化实现)
        paragraphs = content.split('\n\n')
        sentences = content.split('.')
        
        # 优先保留重要段落和句子
        important_parts = []
        current_length = 0
        
        # 按重要性排序段落
        paragraph_scores = [(p, self._calculate_importance(p)) for p in paragraphs if p.strip()]
        paragraph_scores.sort(key=lambda x: x[1], reverse=True)
        
        for paragraph, score in paragraph_scores:
            para_tokens = len(paragraph.split())
            if current_length + para_tokens <= max_length:
                important_parts.append(paragraph)
                current_length += para_tokens
            else:
                # 部分保留
                remaining_tokens = max_length - current_length
                if remaining_tokens > 10:  # 至少保留10个token
                    truncated_para = ' '.join(paragraph.split()[:remaining_tokens])
                    important_parts.append(truncated_para + "...")
                break
        
        processed_content = '\n\n'.join(important_parts)
        token_reduction = 1 - (len(processed_content.split()) / len(tokens))
        
        return ProcessedSequence(
            original_sequence=sequence,
            processed_content=processed_content,
            token_reduction=token_reduction,
            quality_score=self._calculate_quality_after_truncation(content, processed_content),
            processing_methods=["structure_aware_truncation"]
        )
    
    async def _priority_based_truncation(self, sequence: ContextSequence, 
                                       max_length: int) -> ProcessedSequence:
        """基于优先级的截断"""
        
        tokens = sequence.tokens
        content = sequence.content
        
        if len(tokens) <= max_length:
            return ProcessedSequence.from_sequence(sequence)
        
        # 简单策略：保留前面的tokens和最重要的后面tokens
        keep_front = int(max_length * 0.7)  # 保留70%在前面
        keep_back = max_length - keep_front
        
        if keep_back > 0:
            selected_tokens = tokens[:keep_front] + ["..."] + tokens[-keep_back:]
        else:
            selected_tokens = tokens[:max_length]
        
        processed_content = ' '.join(selected_tokens)
        token_reduction = 1 - (len(selected_tokens) / len(tokens))
        
        return ProcessedSequence(
            original_sequence=sequence,
            processed_content=processed_content,
            token_reduction=token_reduction,
            quality_score=sequence.importance_score * (1 - token_reduction * 0.5),
            processing_methods=["priority_based_truncation"]
        )
    
    def _calculate_importance(self, text: str) -> float:
        """计算文本重要性（简化实现）"""
        
        # 基于关键词密度和长度
        important_keywords = ["error", "important", "critical", "main", "key", "primary"]
        keyword_count = sum(1 for keyword in important_keywords if keyword.lower() in text.lower())
        
        # 长度权重（适中长度更重要）
        length_score = min(1.0, len(text.split()) / 100)
        
        # 结构权重（包含标点的文本更重要）
        structure_score = min(1.0, text.count('.') * 0.1 + text.count(':') * 0.2)
        
        return (keyword_count * 0.5 + length_score * 0.3 + structure_score * 0.2)
    
    def _calculate_quality_after_truncation(self, original: str, processed: str) -> float:
        """计算截断后的质量分数"""
        
        if not processed or not original:
            return 0.0
        
        # 长度保持率
        length_ratio = len(processed) / len(original)
        
        # 关键信息保持率（简化检查）
        original_words = set(original.lower().split())
        processed_words = set(processed.lower().split())
        
        if original_words:
            info_retention = len(processed_words.intersection(original_words)) / len(original_words)
        else:
            info_retention = 1.0
        
        return (length_ratio * 0.3 + info_retention * 0.7)


class SelfOptimizationEngine:
    """自我优化引擎"""
    
    def __init__(self):
        self.optimization_history: List[Dict[str, Any]] = []
        self.performance_thresholds = {
            "min_quality_score": 0.7,
            "max_processing_time": 5.0,
            "target_compression_ratio": 0.8
        }
    
    async def optimize(self, data: Dict[str, Any], 
                      optimization_goals: List[str],
                      feedback_loop: bool = True) -> Dict[str, Any]:
        """执行自我优化"""
        
        start_time = time.time()
        
        # 分析当前数据质量
        current_quality = self._assess_data_quality(data)
        
        # 基于目标选择优化策略
        optimization_strategy = self._select_optimization_strategy(
            optimization_goals, current_quality
        )
        
        # 执行优化
        optimized_data = await self._apply_optimization(data, optimization_strategy)
        
        # 评估优化效果
        optimization_result = self._evaluate_optimization(
            data, optimized_data, optimization_strategy
        )
        
        processing_time = time.time() - start_time
        
        # 记录优化历史
        if feedback_loop:
            self._record_optimization(optimization_strategy, optimization_result, processing_time)
        
        return optimized_data
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, float]:
        """评估数据质量"""
        
        quality_metrics = {
            "completeness": self._calculate_completeness(data),
            "relevance": self._calculate_relevance(data),
            "structure": self._calculate_structure_quality(data),
            "redundancy": self._calculate_redundancy(data)
        }
        
        return quality_metrics
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """计算完整性"""
        
        required_fields = ["assembled_content", "strategy_used", "source_contexts"]
        present_fields = sum(1 for field in required_fields if field in data)
        
        return present_fields / len(required_fields)
    
    def _calculate_relevance(self, data: Dict[str, Any]) -> float:
        """计算相关性"""
        
        # 简化实现：基于内容丰富度
        content = data.get("assembled_content", {})
        if not content:
            return 0.0
        
        content_size = len(str(content))
        
        # 标准化到0-1
        return min(1.0, content_size / 10000)
    
    def _calculate_structure_quality(self, data: Dict[str, Any]) -> float:
        """计算结构质量"""
        
        if not isinstance(data, dict):
            return 0.5
        
        # 检查嵌套深度和组织结构
        max_depth = self._calculate_max_depth(data)
        optimal_depth = 3  # 假设3层为最优
        
        depth_score = 1.0 - abs(max_depth - optimal_depth) / 5
        
        # 检查键值对的合理性
        key_quality = len([k for k in data.keys() if isinstance(k, str) and k]) / len(data)
        
        return max(0.0, (depth_score + key_quality) / 2)
    
    def _calculate_redundancy(self, data: Dict[str, Any]) -> float:
        """计算冗余度（越低越好）"""
        
        content_str = json.dumps(data, sort_keys=True)
        
        # 简单的重复检测
        words = content_str.split()
        unique_words = set(words)
        
        if not words:
            return 0.0
        
        redundancy = 1 - (len(unique_words) / len(words))
        return redundancy
    
    def _calculate_max_depth(self, data: Any, current_depth: int = 0) -> int:
        """计算最大嵌套深度"""
        
        if not isinstance(data, (dict, list)):
            return current_depth
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(
                self._calculate_max_depth(value, current_depth + 1)
                for value in data.values()
            )
        else:  # list
            if not data:
                return current_depth
            return max(
                self._calculate_max_depth(item, current_depth + 1)
                for item in data
            )
    
    def _select_optimization_strategy(self, goals: List[str], 
                                    quality: Dict[str, float]) -> Dict[str, Any]:
        """选择优化策略"""
        
        strategy = {
            "primary_focus": "balanced",
            "techniques": [],
            "target_improvements": {}
        }
        
        # 基于目标选择技术
        if "relevance" in goals and quality.get("relevance", 1.0) < 0.7:
            strategy["techniques"].append("relevance_filtering")
            strategy["target_improvements"]["relevance"] = 0.8
        
        if "completeness" in goals and quality.get("completeness", 1.0) < 0.8:
            strategy["techniques"].append("content_enrichment")
            strategy["target_improvements"]["completeness"] = 0.9
        
        if "efficiency" in goals and quality.get("redundancy", 0.0) > 0.3:
            strategy["techniques"].append("redundancy_removal")
            strategy["target_improvements"]["redundancy"] = 0.2
        
        # 如果没有特定技术，使用默认优化
        if not strategy["techniques"]:
            strategy["techniques"] = ["general_optimization"]
            strategy["primary_focus"] = "balanced"
        
        return strategy
    
    async def _apply_optimization(self, data: Dict[str, Any], 
                                strategy: Dict[str, Any]) -> Dict[str, Any]:
        """应用优化策略"""
        
        optimized_data = copy.deepcopy(data)
        
        for technique in strategy["techniques"]:
            if technique == "relevance_filtering":
                optimized_data = await self._apply_relevance_filtering(optimized_data)
            elif technique == "content_enrichment":
                optimized_data = await self._apply_content_enrichment(optimized_data)
            elif technique == "redundancy_removal":
                optimized_data = await self._apply_redundancy_removal(optimized_data)
            elif technique == "general_optimization":
                optimized_data = await self._apply_general_optimization(optimized_data)
        
        return optimized_data
    
    async def _apply_relevance_filtering(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用相关性过滤"""
        
        # 模拟相关性过滤
        await asyncio.sleep(0.1)
        
        assembled_content = data.get("assembled_content", {})
        
        if isinstance(assembled_content, dict):
            # 过滤低相关性内容
            filtered_content = {}
            for key, value in assembled_content.items():
                if self._is_relevant_content(value):
                    filtered_content[key] = value
            
            data["assembled_content"] = filtered_content
            data["optimization_applied"] = data.get("optimization_applied", []) + ["relevance_filtering"]
        
        return data
    
    async def _apply_content_enrichment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用内容丰富化"""
        
        await asyncio.sleep(0.05)
        
        # 添加元数据和结构信息
        if "metadata" not in data:
            data["metadata"] = {}
        
        data["metadata"]["enrichment_timestamp"] = time.time()
        data["metadata"]["content_summary"] = self._generate_content_summary(data)
        data["optimization_applied"] = data.get("optimization_applied", []) + ["content_enrichment"]
        
        return data
    
    async def _apply_redundancy_removal(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用冗余移除"""
        
        await asyncio.sleep(0.08)
        
        # 简化的去重逻辑
        def remove_duplicates(obj):
            if isinstance(obj, dict):
                seen_values = set()
                filtered_dict = {}
                for key, value in obj.items():
                    value_str = str(value)
                    if value_str not in seen_values:
                        seen_values.add(value_str)
                        filtered_dict[key] = remove_duplicates(value)
                return filtered_dict
            elif isinstance(obj, list):
                seen_items = set()
                filtered_list = []
                for item in obj:
                    item_str = str(item)
                    if item_str not in seen_items:
                        seen_items.add(item_str)
                        filtered_list.append(remove_duplicates(item))
                return filtered_list
            else:
                return obj
        
        optimized_data = remove_duplicates(data)
        optimized_data["optimization_applied"] = optimized_data.get("optimization_applied", []) + ["redundancy_removal"]
        
        return optimized_data
    
    async def _apply_general_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """应用通用优化"""
        
        await asyncio.sleep(0.03)
        
        # 通用优化：清理空值、标准化格式等
        def clean_data(obj):
            if isinstance(obj, dict):
                return {k: clean_data(v) for k, v in obj.items() 
                       if v is not None and v != "" and v != []}
            elif isinstance(obj, list):
                return [clean_data(item) for item in obj 
                       if item is not None and item != "" and item != []]
            else:
                return obj
        
        cleaned_data = clean_data(data)
        cleaned_data["optimization_applied"] = cleaned_data.get("optimization_applied", []) + ["general_optimization"]
        
        return cleaned_data
    
    def _is_relevant_content(self, content: Any) -> bool:
        """判断内容是否相关（简化实现）"""
        
        if not content:
            return False
        
        content_str = str(content).lower()
        
        # 过滤明显无关的内容
        irrelevant_indicators = ["lorem ipsum", "test data", "placeholder", "xxx"]
        
        return not any(indicator in content_str for indicator in irrelevant_indicators)
    
    def _generate_content_summary(self, data: Dict[str, Any]) -> str:
        """生成内容摘要"""
        
        content = data.get("assembled_content", {})
        
        if isinstance(content, dict):
            keys = list(content.keys())
            return f"Content with {len(keys)} sections: {', '.join(keys[:3])}{'...' if len(keys) > 3 else ''}"
        else:
            content_str = str(content)
            return f"Content of {len(content_str)} characters"
    
    def _evaluate_optimization(self, original: Dict[str, Any], 
                             optimized: Dict[str, Any],
                             strategy: Dict[str, Any]) -> Dict[str, Any]:
        """评估优化效果"""
        
        original_quality = self._assess_data_quality(original)
        optimized_quality = self._assess_data_quality(optimized)
        
        improvements = {}
        for metric, original_score in original_quality.items():
            optimized_score = optimized_quality.get(metric, original_score)
            improvements[metric] = optimized_score - original_score
        
        overall_improvement = sum(improvements.values()) / len(improvements)
        
        return {
            "improvements": improvements,
            "overall_improvement": overall_improvement,
            "strategy_effectiveness": self._calculate_strategy_effectiveness(
                strategy, improvements
            ),
            "quality_before": original_quality,
            "quality_after": optimized_quality
        }
    
    def _calculate_strategy_effectiveness(self, strategy: Dict[str, Any], 
                                        improvements: Dict[str, float]) -> float:
        """计算策略有效性"""
        
        target_improvements = strategy.get("target_improvements", {})
        
        if not target_improvements:
            return max(0.0, sum(improvements.values()) / len(improvements))
        
        effectiveness_scores = []
        for metric, target in target_improvements.items():
            actual_improvement = improvements.get(metric, 0)
            if target > 0:
                effectiveness = min(1.0, actual_improvement / target)
            else:
                effectiveness = 1.0 if actual_improvement >= target else 0.0
            effectiveness_scores.append(effectiveness)
        
        return sum(effectiveness_scores) / len(effectiveness_scores)
    
    def _record_optimization(self, strategy: Dict[str, Any], 
                           result: Dict[str, Any], processing_time: float):
        """记录优化历史"""
        
        self.optimization_history.append({
            "timestamp": time.time(),
            "strategy": strategy,
            "result": result,
            "processing_time": processing_time
        })
        
        # 保留最近100条记录
        if len(self.optimization_history) > 100:
            self.optimization_history = self.optimization_history[-100:]
    
    def get_trace(self) -> List[Dict[str, Any]]:
        """获取优化轨迹"""
        return self.optimization_history.copy()


class StructuredDataIntegrator:
    """结构化数据集成器"""
    
    def __init__(self):
        self.integration_patterns = {
            "hierarchical": self._integrate_hierarchical,
            "flat": self._integrate_flat,
            "graph": self._integrate_graph,
            "temporal": self._integrate_temporal
        }
    
    async def integrate(self, processed_sequences: List[ProcessedSequence],
                       data_sources: List[str]) -> Dict[str, Any]:
        """集成结构化数据"""
        
        # 分析数据结构类型
        structure_type = self._analyze_structure_type(processed_sequences)
        
        # 选择集成模式
        integration_pattern = self._select_integration_pattern(structure_type, data_sources)
        
        # 执行集成
        integrated_data = await self.integration_patterns[integration_pattern](
            processed_sequences, data_sources
        )
        
        return {
            "integrated_content": integrated_data,
            "structure_type": structure_type,
            "integration_pattern": integration_pattern,
            "source_count": len(processed_sequences),
            "data_sources": data_sources
        }
    
    def _analyze_structure_type(self, sequences: List[ProcessedSequence]) -> str:
        """分析数据结构类型"""
        
        if not sequences:
            return "empty"
        
        # 简单分析：检查内容特征
        has_hierarchy = any("section" in seq.processed_content.lower() or 
                           "chapter" in seq.processed_content.lower()
                           for seq in sequences)
        
        has_temporal = any("time" in seq.processed_content.lower() or
                          "date" in seq.processed_content.lower() or
                          "when" in seq.processed_content.lower()
                          for seq in sequences)
        
        has_relationships = any("related" in seq.processed_content.lower() or
                               "connected" in seq.processed_content.lower()
                               for seq in sequences)
        
        if has_hierarchy:
            return "hierarchical"
        elif has_temporal:
            return "temporal"
        elif has_relationships:
            return "graph"
        else:
            return "flat"
    
    def _select_integration_pattern(self, structure_type: str, 
                                   data_sources: List[str]) -> str:
        """选择集成模式"""
        
        # 基于结构类型和数据源选择模式
        if structure_type == "hierarchical":
            return "hierarchical"
        elif structure_type == "temporal":
            return "temporal"
        elif len(data_sources) > 3:
            return "graph"  # 多数据源用图模式
        else:
            return "flat"
    
    async def _integrate_hierarchical(self, sequences: List[ProcessedSequence],
                                    data_sources: List[str]) -> Dict[str, Any]:
        """分层集成"""
        
        hierarchy = {"root": {"children": [], "content": "", "metadata": {}}}
        
        for i, seq in enumerate(sequences):
            node = {
                "id": f"node_{i}",
                "content": seq.processed_content,
                "source": data_sources[i] if i < len(data_sources) else "unknown",
                "quality_score": seq.quality_score,
                "processing_methods": seq.processing_methods,
                "children": []
            }
            hierarchy["root"]["children"].append(node)
        
        return hierarchy
    
    async def _integrate_flat(self, sequences: List[ProcessedSequence],
                            data_sources: List[str]) -> Dict[str, Any]:
        """扁平集成"""
        
        flat_data = {
            "items": [],
            "metadata": {
                "total_items": len(sequences),
                "integration_method": "flat"
            }
        }
        
        for i, seq in enumerate(sequences):
            item = {
                "id": f"item_{i}",
                "content": seq.processed_content,
                "source": data_sources[i] if i < len(data_sources) else "unknown",
                "quality_score": seq.quality_score,
                "token_reduction": seq.token_reduction
            }
            flat_data["items"].append(item)
        
        return flat_data
    
    async def _integrate_graph(self, sequences: List[ProcessedSequence],
                             data_sources: List[str]) -> Dict[str, Any]:
        """图结构集成"""
        
        graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "node_count": len(sequences),
                "integration_method": "graph"
            }
        }
        
        # 创建节点
        for i, seq in enumerate(sequences):
            node = {
                "id": f"node_{i}",
                "content": seq.processed_content,
                "source": data_sources[i] if i < len(data_sources) else "unknown",
                "quality_score": seq.quality_score
            }
            graph["nodes"].append(node)
        
        # 创建简单的边（基于内容相似性）
        for i in range(len(sequences)):
            for j in range(i + 1, len(sequences)):
                similarity = self._calculate_content_similarity(
                    sequences[i].processed_content,
                    sequences[j].processed_content
                )
                if similarity > 0.3:  # 阈值
                    edge = {
                        "from": f"node_{i}",
                        "to": f"node_{j}",
                        "weight": similarity,
                        "type": "similarity"
                    }
                    graph["edges"].append(edge)
        
        return graph
    
    async def _integrate_temporal(self, sequences: List[ProcessedSequence],
                                data_sources: List[str]) -> Dict[str, Any]:
        """时序集成"""
        
        temporal_data = {
            "timeline": [],
            "metadata": {
                "total_events": len(sequences),
                "integration_method": "temporal"
            }
        }
        
        # 按质量分数排序作为时序代理
        sorted_sequences = sorted(sequences, key=lambda x: x.quality_score, reverse=True)
        
        for i, seq in enumerate(sorted_sequences):
            event = {
                "sequence": i,
                "content": seq.processed_content,
                "source": data_sources[sequences.index(seq)] if sequences.index(seq) < len(data_sources) else "unknown",
                "importance": seq.quality_score,
                "processing_info": {
                    "methods": seq.processing_methods,
                    "token_reduction": seq.token_reduction
                }
            }
            temporal_data["timeline"].append(event)
        
        return temporal_data
    
    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """计算内容相似性（简化实现）"""
        
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)


class NormalizationEngine:
    """标准化引擎，实现类似Claude Code的normalizeToSize算法"""
    
    def __init__(self):
        self.normalization_cache: Dict[str, Any] = {}
        self.max_cache_size = 1000
    
    async def normalize(self, context: Dict[str, Any], 
                       target_size: int, preserve_priority: bool = True) -> Dict[str, Any]:
        """标准化上下文到目标大小"""
        
        # 计算当前大小
        current_size = self._estimate_size(context)
        
        if current_size <= target_size:
            return context  # 不需要压缩
        
        # 生成缓存键
        cache_key = self._generate_cache_key(context, target_size, preserve_priority)
        if cache_key in self.normalization_cache:
            return self.normalization_cache[cache_key]
        
        # 执行标准化
        normalized_context = await self._normalize_to_size(
            context, target_size, preserve_priority
        )
        
        # 缓存结果
        self._cache_result(cache_key, normalized_context)
        
        return normalized_context
    
    def _estimate_size(self, obj: Any) -> int:
        """估算对象大小（字节）"""
        
        try:
            return len(json.dumps(obj, ensure_ascii=False).encode('utf-8'))
        except (TypeError, ValueError):
            # 对于不可序列化的对象，使用字符串长度估算
            return len(str(obj))
    
    async def _normalize_to_size(self, obj: Any, target_size: int, 
                               preserve_priority: bool, current_depth: int = 0) -> Any:
        """递归标准化到目标大小"""
        
        max_depth = 10  # 防止无限递归
        if current_depth > max_depth:
            return str(obj)[:target_size // 4] if target_size > 0 else ""
        
        current_size = self._estimate_size(obj)
        
        if current_size <= target_size:
            return obj
        
        if isinstance(obj, dict):
            return await self._normalize_dict(obj, target_size, preserve_priority, current_depth)
        elif isinstance(obj, list):
            return await self._normalize_list(obj, target_size, preserve_priority, current_depth)
        elif isinstance(obj, str):
            return self._normalize_string(obj, target_size)
        else:
            # 对于其他类型，转换为字符串并截断
            str_repr = str(obj)
            return str_repr[:target_size] if len(str_repr) > target_size else str_repr
    
    async def _normalize_dict(self, obj: Dict[str, Any], target_size: int,
                            preserve_priority: bool, current_depth: int) -> Dict[str, Any]:
        """标准化字典"""
        
        if not obj:
            return obj
        
        # 计算每个键值对的大小和优先级
        items_info = []
        for key, value in obj.items():
            size = self._estimate_size({key: value})
            priority = self._calculate_priority(key, value) if preserve_priority else 1.0
            items_info.append((key, value, size, priority))
        
        # 按优先级排序
        if preserve_priority:
            items_info.sort(key=lambda x: x[3], reverse=True)
        
        # 逐步添加项目直到接近目标大小
        normalized_dict = {}
        used_size = 0
        
        for key, value, size, priority in items_info:
            # 为每个项目分配空间
            remaining_items = len([item for item in items_info if item[0] not in normalized_dict])
            if remaining_items > 0:
                allocated_size = (target_size - used_size) // remaining_items
            else:
                allocated_size = target_size - used_size
            
            if allocated_size <= 0:
                break
            
            # 递归标准化值
            if size > allocated_size:
                normalized_value = await self._normalize_to_size(
                    value, allocated_size, preserve_priority, current_depth + 1
                )
            else:
                normalized_value = value
            
            normalized_dict[key] = normalized_value
            used_size += self._estimate_size({key: normalized_value})
            
            if used_size >= target_size:
                break
        
        return normalized_dict
    
    async def _normalize_list(self, obj: List[Any], target_size: int,
                            preserve_priority: bool, current_depth: int) -> List[Any]:
        """标准化列表"""
        
        if not obj:
            return obj
        
        # 计算每个项目的大小和优先级
        items_info = []
        for i, item in enumerate(obj):
            size = self._estimate_size(item)
            priority = self._calculate_list_item_priority(item, i) if preserve_priority else 1.0
            items_info.append((item, size, priority, i))
        
        # 按优先级排序
        if preserve_priority:
            items_info.sort(key=lambda x: x[2], reverse=True)
        else:
            # 保持原始顺序
            items_info.sort(key=lambda x: x[3])
        
        # 分配空间
        normalized_list = []
        used_size = 0
        
        for item, size, priority, original_index in items_info:
            remaining_items = len(items_info) - len(normalized_list)
            if remaining_items > 0:
                allocated_size = (target_size - used_size) // remaining_items
            else:
                allocated_size = target_size - used_size
            
            if allocated_size <= 0:
                break
            
            # 递归标准化项目
            if size > allocated_size:
                normalized_item = await self._normalize_to_size(
                    item, allocated_size, preserve_priority, current_depth + 1
                )
            else:
                normalized_item = item
            
            normalized_list.append(normalized_item)
            used_size += self._estimate_size(normalized_item)
            
            if used_size >= target_size:
                break
        
        return normalized_list
    
    def _normalize_string(self, obj: str, target_size: int) -> str:
        """标准化字符串"""
        
        if len(obj.encode('utf-8')) <= target_size:
            return obj
        
        # 智能截断：尝试在句子边界截断
        sentences = obj.split('.')
        
        if len(sentences) > 1:
            # 逐句添加直到超过目标大小
            result = ""
            for sentence in sentences:
                test_result = result + sentence + "."
                if len(test_result.encode('utf-8')) > target_size:
                    if result:  # 如果已经有内容，就停止
                        break
                    else:  # 如果第一句就超过，就截断第一句
                        max_chars = target_size // 2  # 估算字符数
                        return sentence[:max_chars] + "..."
                result = test_result
            
            return result.rstrip('.') + "..." if result != obj else result
        else:
            # 单句，直接截断
            max_chars = target_size // 2  # 估算字符数
            return obj[:max_chars] + "..." if len(obj) > max_chars else obj
    
    def _calculate_priority(self, key: str, value: Any) -> float:
        """计算键值对的优先级"""
        
        # 重要键的优先级更高
        important_keys = [
            "content", "result", "main", "primary", "key", "important",
            "summary", "conclusion", "analysis", "data"
        ]
        
        key_lower = key.lower()
        key_priority = 2.0 if any(imp_key in key_lower for imp_key in important_keys) else 1.0
        
        # 内容丰富度影响优先级
        value_size = self._estimate_size(value)
        size_priority = min(2.0, value_size / 1000)  # 标准化
        
        return key_priority * size_priority
    
    def _calculate_list_item_priority(self, item: Any, index: int) -> float:
        """计算列表项的优先级"""
        
        # 前面的项目优先级稍高
        position_priority = max(0.5, 2.0 - index * 0.1)
        
        # 内容丰富度
        size_priority = min(2.0, self._estimate_size(item) / 500)
        
        return position_priority * size_priority
    
    def _generate_cache_key(self, obj: Any, target_size: int, 
                           preserve_priority: bool) -> str:
        """生成缓存键"""
        
        import hashlib
        
        # 使用对象的哈希、目标大小和选项生成键
        obj_str = str(obj)[:1000]  # 限制长度
        key_data = f"{obj_str}_{target_size}_{preserve_priority}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _cache_result(self, key: str, result: Any):
        """缓存结果"""
        
        if len(self.normalization_cache) >= self.max_cache_size:
            # 删除最老的条目（简化LRU）
            oldest_key = next(iter(self.normalization_cache))
            del self.normalization_cache[oldest_key]
        
        self.normalization_cache[key] = result


class ContextProcessor:
    """上下文处理器主类"""
    
    def __init__(self):
        self.sequence_processor = LongSequenceProcessor()
        self.self_optimizer = SelfOptimizationEngine()
        self.data_integrator = StructuredDataIntegrator()
        self.normalization_engine = NormalizationEngine()
        
        # 性能指标
        self.processing_metrics = {
            "total_processed": 0,
            "average_processing_time": 0.0,
            "optimization_success_rate": 0.0
        }
    
    async def process_context(self, context_package: ContextPackage,
                            processing_constraints: ProcessingConstraints) -> ProcessedContext:
        """处理上下文的主入口方法"""
        
        start_time = time.time()
        
        # 1. 提取和预处理内容
        primary_context = context_package.primary_context
        sequences = self._extract_sequences(primary_context)
        
        # 2. 长序列智能处理
        processed_sequences = await self.sequence_processor.process(
            sequences,
            max_length=processing_constraints.max_tokens,
            preserve_structure=processing_constraints.preserve_structure
        )
        
        # 3. 结构化数据集成
        data_sources = context_package.metadata.get("retrieval_strategies_used", [])
        integrated_data = await self.data_integrator.integrate(
            processed_sequences, data_sources
        )
        
        # 4. 自我优化机制
        optimized_context = await self.self_optimizer.optimize(
            integrated_data,
            optimization_goals=processing_constraints.goals,
            feedback_loop=True
        )
        
        # 5. 上下文标准化
        if processing_constraints.target_size:
            normalized_context = await self.normalization_engine.normalize(
                optimized_context,
                target_size=processing_constraints.target_size,
                preserve_priority=True
            )
        else:
            normalized_context = optimized_context
        
        # 6. 生成处理元数据
        processing_time = time.time() - start_time
        processing_metadata = self._generate_processing_metadata(
            context_package, processed_sequences, processing_time
        )
        
        # 7. 更新性能指标
        self._update_metrics(processing_time, True)
        
        return ProcessedContext(
            content=normalized_context,
            processing_metadata=processing_metadata,
            optimization_trace=self.self_optimizer.get_trace()[-5:]  # 最近5次
        )
    
    def _extract_sequences(self, context: Dict[str, Any]) -> List[ContextSequence]:
        """从上下文中提取序列"""
        
        sequences = []
        
        def extract_from_object(obj, path="root"):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}"
                    if isinstance(value, str) and len(value) > 50:  # 足够长的文本
                        seq = ContextSequence(
                            content=value,
                            metadata={"source_path": current_path, "source_key": key}
                        )
                        sequences.append(seq)
                    elif isinstance(value, (dict, list)):
                        extract_from_object(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    current_path = f"{path}[{i}]"
                    if isinstance(item, str) and len(item) > 50:
                        seq = ContextSequence(
                            content=item,
                            metadata={"source_path": current_path, "source_index": i}
                        )
                        sequences.append(seq)
                    elif isinstance(item, (dict, list)):
                        extract_from_object(item, current_path)
            elif isinstance(obj, str) and len(obj) > 50:
                seq = ContextSequence(
                    content=obj,
                    metadata={"source_path": path}
                )
                sequences.append(seq)
        
        extract_from_object(context)
        
        # 如果没有提取到序列，将整个上下文作为一个序列
        if not sequences:
            sequences.append(ContextSequence(
                content=str(context),
                metadata={"source_path": "root", "fallback": True}
            ))
        
        return sequences
    
    def _generate_processing_metadata(self, context_package: ContextPackage,
                                    processed_sequences: List[ProcessedSequence],
                                    processing_time: float) -> Dict[str, Any]:
        """生成处理元数据"""
        
        total_original_tokens = sum(
            len(seq.original_sequence.tokens) for seq in processed_sequences
        )
        total_processed_tokens = sum(
            len(seq.processed_content.split()) for seq in processed_sequences
        )
        
        token_reduction_rate = (
            1 - (total_processed_tokens / total_original_tokens)
            if total_original_tokens > 0 else 0
        )
        
        average_quality = (
            sum(seq.quality_score for seq in processed_sequences) / len(processed_sequences)
            if processed_sequences else 0
        )
        
        return {
            "processing_time": processing_time,
            "sequence_count": len(processed_sequences),
            "token_reduction_rate": token_reduction_rate,
            "average_quality_score": average_quality,
            "original_token_count": total_original_tokens,
            "processed_token_count": total_processed_tokens,
            "processing_methods_used": list(set(
                method for seq in processed_sequences 
                for method in seq.processing_methods
            )),
            "source_package_id": context_package.package_id,
            "processor_version": "2.0.0"
        }
    
    def _update_metrics(self, processing_time: float, success: bool):
        """更新处理指标"""
        
        self.processing_metrics["total_processed"] += 1
        
        # 更新平均处理时间
        total_processed = self.processing_metrics["total_processed"]
        current_avg = self.processing_metrics["average_processing_time"]
        
        self.processing_metrics["average_processing_time"] = (
            (current_avg * (total_processed - 1) + processing_time) / total_processed
        )
        
        # 更新成功率（这里简化为都成功）
        if success:
            current_success_rate = self.processing_metrics["optimization_success_rate"]
            self.processing_metrics["optimization_success_rate"] = (
                (current_success_rate * (total_processed - 1) + 1.0) / total_processed
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.processing_metrics.copy()