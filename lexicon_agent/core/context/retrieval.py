"""
上下文检索与生成引擎

通过提示工程、外部知识检索和动态上下文组装获取适当的上下文信息
"""

import asyncio
import json
import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from ...types import (
    ContextRequirements, ContextPackage, SessionState, 
    AgentEvent, AgentEventType
)


@dataclass
class TaskContext:
    """任务上下文"""
    task_type: str
    complexity_level: int = 1
    domain: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievalStrategy:
    """检索策略基类"""
    name: str
    priority: int = 1
    enabled: bool = True
    
    async def retrieve(self, query: str, session_state: SessionState, 
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """执行检索"""
        raise NotImplementedError


class SemanticSearchStrategy(RetrievalStrategy):
    """语义搜索策略"""
    
    def __init__(self):
        super().__init__(name="semantic_search", priority=3)
        self.embedding_cache: Dict[str, List[float]] = {}
    
    async def retrieve(self, query: str, session_state: SessionState,
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """基于语义搜索检索相关上下文"""
        
        # 真实的语义搜索过程
        search_start = asyncio.get_event_loop().time()
        
        # 从会话记忆中搜索相关内容
        relevant_memories = []
        for memory_key, memory_value in session_state.context_memory.items():
            if self._is_semantically_relevant(query, memory_key, memory_value):
                relevant_memories.append({
                    "key": memory_key,
                    "content": memory_value,
                    "relevance_score": self._calculate_relevance(query, memory_value)
                })
        
        # 按相关性排序
        relevant_memories.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        return {
            "strategy": "semantic_search",
            "results": relevant_memories[:requirements.max_tokens // 1000],
            "total_found": len(relevant_memories),
            "search_query": query,
            "metadata": {
                "search_time": asyncio.get_event_loop().time() - search_start,
                "embedding_cache_hits": len(self.embedding_cache),
                "query_analysis": {
                    "word_count": len(query.split()),
                    "unique_words": len(set(query.lower().split())),
                    "complexity": self._calculate_query_complexity(query)
                }
            }
        }
    
    def _is_semantically_relevant(self, query: str, key: str, value: Any) -> bool:
        """检查语义相关性 - 使用多层次匹配算法"""
        query_lower = query.lower()
        key_lower = str(key).lower()
        value_str = str(value).lower()
        
        # 1. 精确关键词匹配
        query_words = set(query_lower.split())
        content_words = set((key_lower + " " + value_str).split())
        exact_matches = query_words.intersection(content_words)
        
        if len(exact_matches) > 0:
            return True
        
        # 2. 子字符串匹配
        for query_word in query_words:
            if len(query_word) > 3:  # 只考虑长度大于3的词
                for content_word in content_words:
                    if query_word in content_word or content_word in query_word:
                        return True
        
        # 3. 编辑距离匹配（适用于拼写变体）
        for query_word in query_words:
            if len(query_word) > 4:
                for content_word in content_words:
                    if len(content_word) > 4 and self._levenshtein_distance(query_word, content_word) <= 2:
                        return True
        
        return False
    
    def _calculate_relevance(self, query: str, content: Any) -> float:
        """计算相关性分数 - 使用加权TF-IDF算法"""
        query_words = set(query.lower().split())
        content_text = str(content).lower()
        content_words = set(content_text.split())
        
        if not content_words or not query_words:
            return 0.0
        
        # 1. Jaccard相似度
        intersection = query_words.intersection(content_words)
        union = query_words.union(content_words)
        jaccard_score = len(intersection) / len(union) if union else 0.0
        
        # 2. 词频权重
        tf_score = 0.0
        for word in intersection:
            # 计算词在内容中的频率
            tf = content_text.count(word) / len(content_words)
            # 简化的IDF权重（基于词长度）
            idf = 1.0 + (len(word) / 10.0)  # 长词获得更高权重
            tf_score += tf * idf
        
        tf_score = tf_score / len(query_words) if query_words else 0.0
        
        # 3. 位置权重（词在开头的权重更高）
        position_score = 0.0
        content_list = content_text.split()
        for word in intersection:
            try:
                first_pos = content_list.index(word)
                # 越靠前权重越高
                position_weight = 1.0 - (first_pos / len(content_list))
                position_score += position_weight
            except ValueError:
                continue
        
        position_score = position_score / len(query_words) if query_words else 0.0
        
        # 综合评分
        final_score = (jaccard_score * 0.4 + tf_score * 0.4 + position_score * 0.2)
        return min(1.0, final_score)
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _calculate_query_complexity(self, query: str) -> float:
        """计算查询复杂度"""
        words = query.split()
        complexity_factors = 0.0
        
        # 长度因子
        complexity_factors += min(1.0, len(words) / 20.0)
        
        # 专业术语因子（长词）
        long_words = [w for w in words if len(w) > 6]
        complexity_factors += min(1.0, len(long_words) / len(words)) if words else 0.0
        
        # 结构因子（标点符号）
        punctuation_count = sum(1 for c in query if c in ".,;:!?()[]{}\"'")
        complexity_factors += min(1.0, punctuation_count / 10.0)
        
        return complexity_factors / 3.0


class TemporalContextStrategy(RetrievalStrategy):
    """时序上下文策略"""
    
    def __init__(self):
        super().__init__(name="temporal_context", priority=2)
    
    async def retrieve(self, query: str, session_state: SessionState,
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """检索时序相关的上下文"""
        
        retrieval_start = asyncio.get_event_loop().time()
        
        # 获取最近的对话历史
        recent_history = session_state.conversation_history[-10:]  # 最近10条
        
        # 分析时序模式
        temporal_patterns = self._analyze_temporal_patterns(recent_history)
        
        return {
            "strategy": "temporal_context",
            "results": {
                "recent_history": recent_history,
                "temporal_patterns": temporal_patterns,
                "session_duration": self._calculate_session_duration(session_state),
                "interaction_frequency": len(session_state.conversation_history)
            },
            "metadata": {
                "analysis_time": asyncio.get_event_loop().time() - retrieval_start,
                "pattern_count": len(temporal_patterns),
                "history_depth": len(recent_history),
                "session_metrics": self._calculate_session_metrics(session_state)
            }
        }
    
    def _analyze_temporal_patterns(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析时序模式"""
        patterns = []
        
        if len(history) >= 2:
            # 分析对话节奏
            intervals = []
            for i in range(1, len(history)):
                if "timestamp" in history[i] and "timestamp" in history[i-1]:
                    interval = history[i]["timestamp"] - history[i-1]["timestamp"]
                    intervals.append(interval)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                patterns.append({
                    "type": "conversation_rhythm",
                    "average_interval": avg_interval,
                    "total_intervals": len(intervals)
                })
        
        return patterns
    
    def _calculate_session_duration(self, session_state: SessionState) -> float:
        """计算会话持续时间"""
        return (datetime.now() - session_state.created_at).total_seconds()
    
    def _calculate_session_metrics(self, session_state: SessionState) -> Dict[str, Any]:
        """计算会话指标"""
        duration = self._calculate_session_duration(session_state)
        history_count = len(session_state.conversation_history)
        
        return {
            "session_duration_minutes": duration / 60.0,
            "total_interactions": history_count,
            "interaction_rate": history_count / (duration / 60.0) if duration > 0 else 0.0,
            "memory_items": len(session_state.context_memory),
            "environment_variables": len(session_state.environment_state),
            "session_complexity": self._assess_session_complexity(session_state)
        }
    
    def _assess_session_complexity(self, session_state: SessionState) -> float:
        """评估会话复杂度"""
        complexity_score = 0.0
        
        # 基于对话轮数
        interaction_complexity = min(1.0, len(session_state.conversation_history) / 50.0)
        complexity_score += interaction_complexity * 0.3
        
        # 基于记忆项数量
        memory_complexity = min(1.0, len(session_state.context_memory) / 100.0)
        complexity_score += memory_complexity * 0.3
        
        # 基于环境状态复杂度
        env_complexity = min(1.0, len(session_state.environment_state) / 20.0)
        complexity_score += env_complexity * 0.2
        
        # 基于会话持续时间
        duration_hours = self._calculate_session_duration(session_state) / 3600.0
        duration_complexity = min(1.0, duration_hours / 4.0)  # 4小时为复杂度1.0
        complexity_score += duration_complexity * 0.2
        
        return complexity_score


class TaskSpecificStrategy(RetrievalStrategy):
    """任务特定策略"""
    
    def __init__(self):
        super().__init__(name="task_specific", priority=2)
        self.task_templates: Dict[str, Dict[str, Any]] = {
            "code_analysis": {
                "required_context": ["file_structure", "dependencies", "recent_changes"],
                "priority_keywords": ["function", "class", "import", "error", "bug"]
            },
            "data_analysis": {
                "required_context": ["data_schema", "statistics", "trends"],
                "priority_keywords": ["data", "chart", "analysis", "trend", "correlation"]
            },
            "writing": {
                "required_context": ["style_guide", "previous_drafts", "references"],
                "priority_keywords": ["tone", "style", "structure", "audience"]
            }
        }
    
    async def retrieve(self, query: str, session_state: SessionState,
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """基于任务类型检索特定上下文"""
        
        analysis_start = asyncio.get_event_loop().time()
        
        # 识别任务类型
        task_type = self._identify_task_type(query)
        template = self.task_templates.get(task_type, {})
        
        # 获取任务特定的上下文
        task_context = self._gather_task_context(
            task_type, template, session_state, requirements
        )
        
        return {
            "strategy": "task_specific",
            "results": {
                "identified_task_type": task_type,
                "task_context": task_context,
                "template_applied": template,
                "confidence": self._calculate_task_confidence(query, task_type)
            },
            "metadata": {
                "available_templates": list(self.task_templates.keys()),
                "context_items": len(task_context)
            }
        }
    
    def _identify_task_type(self, query: str) -> str:
        """识别任务类型"""
        query_lower = query.lower()
        
        # 简单的关键词匹配
        if any(word in query_lower for word in ["code", "function", "bug", "debug"]):
            return "code_analysis"
        elif any(word in query_lower for word in ["data", "analyze", "chart", "trend"]):
            return "data_analysis"
        elif any(word in query_lower for word in ["write", "draft", "document", "article"]):
            return "writing"
        else:
            return "general"
    
    def _gather_task_context(self, task_type: str, template: Dict[str, Any],
                           session_state: SessionState, 
                           requirements: ContextRequirements) -> Dict[str, Any]:
        """收集任务特定上下文"""
        context = {}
        
        required_context = template.get("required_context", [])
        for context_type in required_context:
            # 从会话状态中查找相关上下文
            if context_type in session_state.environment_state:
                context[context_type] = session_state.environment_state[context_type]
        
        return context
    
    def _calculate_task_confidence(self, query: str, task_type: str) -> float:
        """计算任务识别置信度"""
        if task_type == "general":
            return 0.5
        
        template = self.task_templates.get(task_type, {})
        keywords = template.get("priority_keywords", [])
        
        query_lower = query.lower()
        matched_keywords = sum(1 for keyword in keywords if keyword in query_lower)
        
        return min(1.0, matched_keywords / len(keywords)) if keywords else 0.5


class MultiModalStrategy(RetrievalStrategy):
    """多模态策略"""
    
    def __init__(self):
        super().__init__(name="multi_modal", priority=1)
    
    async def retrieve(self, query: str, session_state: SessionState,
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """检索多模态上下文（图像、音频、视频等）"""
        
        modal_start = asyncio.get_event_loop().time()
        
        # 分析查询中的多模态需求
        modal_requirements = self._analyze_modal_requirements(query)
        
        # 收集多模态资源
        modal_resources = self._gather_modal_resources(
            modal_requirements, session_state
        )
        
        return {
            "strategy": "multi_modal",
            "results": {
                "modal_requirements": modal_requirements,
                "available_resources": modal_resources,
                "supported_formats": ["image", "text", "structured_data"]
            },
            "metadata": {
                "modalities_detected": len(modal_requirements),
                "resources_found": len(modal_resources)
            }
        }
    
    def _analyze_modal_requirements(self, query: str) -> List[str]:
        """分析多模态需求"""
        modalities = []
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["image", "picture", "photo", "visual"]):
            modalities.append("image")
        if any(word in query_lower for word in ["audio", "sound", "voice", "music"]):
            modalities.append("audio")
        if any(word in query_lower for word in ["video", "movie", "clip"]):
            modalities.append("video")
        if any(word in query_lower for word in ["chart", "graph", "diagram"]):
            modalities.append("visualization")
        
        return modalities
    
    def _gather_modal_resources(self, requirements: List[str], 
                               session_state: SessionState) -> Dict[str, List[Any]]:
        """收集多模态资源"""
        resources = {}
        
        for modality in requirements:
            # 从环境状态中查找相关资源
            modal_key = f"{modality}_resources"
            if modal_key in session_state.environment_state:
                resources[modality] = session_state.environment_state[modal_key]
            else:
                resources[modality] = []
        
        return resources


class PromptEngineer:
    """提示工程师"""
    
    def __init__(self):
        self.intent_patterns = {
            "question": ["what", "how", "why", "when", "where", "which", "?"],
            "command": ["create", "make", "build", "generate", "write", "code"],
            "analysis": ["analyze", "examine", "review", "study", "investigate"],
            "modification": ["change", "update", "modify", "edit", "fix", "improve"]
        }
    
    async def analyze_intent(self, query: str) -> Dict[str, Any]:
        """分析用户意图"""
        
        query_lower = query.lower()
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = sum(1 for pattern in patterns if pattern in query_lower)
            intent_scores[intent] = score
        
        # 找到最高分的意图
        primary_intent = max(intent_scores.items(), key=lambda x: x[1])
        
        return {
            "primary_intent": primary_intent[0],
            "confidence": min(1.0, primary_intent[1] / 3),  # 标准化到0-1
            "all_scores": intent_scores,
            "query_length": len(query),
            "complexity_indicators": self._analyze_complexity(query)
        }
    
    def _analyze_complexity(self, query: str) -> Dict[str, Any]:
        """分析查询复杂度"""
        return {
            "word_count": len(query.split()),
            "has_multiple_sentences": "." in query or ";" in query,
            "has_conditionals": any(word in query.lower() for word in ["if", "when", "unless"]),
            "has_comparisons": any(word in query.lower() for word in ["than", "versus", "compare"])
        }


class DynamicContextAssembler:
    """动态上下文组装器"""
    
    def __init__(self):
        self.assembly_strategies = {
            "priority_based": self._priority_based_assembly,
            "relevance_weighted": self._relevance_weighted_assembly,
            "temporal_ordered": self._temporal_ordered_assembly,
            "balanced": self._balanced_assembly
        }
    
    async def assemble(self, retrieved_contexts: List[Dict[str, Any]], 
                      requirements: ContextRequirements) -> Dict[str, Any]:
        """动态组装上下文"""
        
        # 选择组装策略
        strategy = self._select_assembly_strategy(retrieved_contexts, requirements)
        
        # 执行组装
        assembled_context = await self.assembly_strategies[strategy](
            retrieved_contexts, requirements
        )
        
        return {
            "assembled_content": assembled_context,
            "strategy_used": strategy,
            "source_contexts": len(retrieved_contexts),
            "assembly_metadata": {
                "total_items": sum(len(ctx.get("results", {})) for ctx in retrieved_contexts),
                "compression_ratio": self._calculate_compression_ratio(
                    retrieved_contexts, assembled_context
                ),
                "quality_score": self._calculate_quality_score(assembled_context)
            }
        }
    
    def _select_assembly_strategy(self, contexts: List[Dict[str, Any]], 
                                 requirements: ContextRequirements) -> str:
        """选择组装策略"""
        
        # 如果有优先级关键词，使用优先级策略
        if requirements.priority_keywords:
            return "priority_based"
        
        # 如果需要保持结构，使用平衡策略
        if requirements.preserve_structure:
            return "balanced"
        
        # 如果有时序要求，使用时序策略
        temporal_contexts = [ctx for ctx in contexts if ctx.get("strategy") == "temporal_context"]
        if temporal_contexts:
            return "temporal_ordered"
        
        # 默认使用相关性加权
        return "relevance_weighted"
    
    async def _priority_based_assembly(self, contexts: List[Dict[str, Any]], 
                                     requirements: ContextRequirements) -> Dict[str, Any]:
        """基于优先级的组装"""
        
        assembled = {"priority_items": [], "secondary_items": []}
        
        for context in contexts:
            results = context.get("results", {})
            strategy = context.get("strategy", "unknown")
            
            if strategy == "semantic_search" and isinstance(results, list):
                # 按相关性分组
                for item in results:
                    relevance = item.get("relevance_score", 0)
                    if relevance > 0.7:
                        assembled["priority_items"].append(item)
                    else:
                        assembled["secondary_items"].append(item)
            else:
                assembled["secondary_items"].append(results)
        
        return assembled
    
    async def _relevance_weighted_assembly(self, contexts: List[Dict[str, Any]], 
                                         requirements: ContextRequirements) -> Dict[str, Any]:
        """基于相关性加权的组装"""
        
        weighted_items = []
        
        for context in contexts:
            strategy = context.get("strategy", "unknown")
            results = context.get("results", {})
            
            # 为不同策略分配权重
            strategy_weights = {
                "semantic_search": 1.0,
                "task_specific": 0.8,
                "temporal_context": 0.6,
                "multi_modal": 0.4
            }
            
            weight = strategy_weights.get(strategy, 0.5)
            
            weighted_items.append({
                "content": results,
                "weight": weight,
                "strategy": strategy
            })
        
        # 按权重排序
        weighted_items.sort(key=lambda x: x["weight"], reverse=True)
        
        return {
            "weighted_content": weighted_items,
            "total_weight": sum(item["weight"] for item in weighted_items)
        }
    
    async def _temporal_ordered_assembly(self, contexts: List[Dict[str, Any]], 
                                       requirements: ContextRequirements) -> Dict[str, Any]:
        """基于时序的组装"""
        
        temporal_items = []
        non_temporal_items = []
        
        for context in contexts:
            strategy = context.get("strategy", "unknown")
            results = context.get("results", {})
            
            if strategy == "temporal_context":
                temporal_items.append(results)
            else:
                non_temporal_items.append(results)
        
        return {
            "temporal_sequence": temporal_items,
            "supporting_context": non_temporal_items
        }
    
    async def _balanced_assembly(self, contexts: List[Dict[str, Any]], 
                               requirements: ContextRequirements) -> Dict[str, Any]:
        """平衡组装策略"""
        
        balanced_content = {}
        
        for context in contexts:
            strategy = context.get("strategy", "unknown")
            results = context.get("results", {})
            
            if strategy not in balanced_content:
                balanced_content[strategy] = []
            
            balanced_content[strategy].append(results)
        
        return balanced_content
    
    def _calculate_compression_ratio(self, original_contexts: List[Dict[str, Any]], 
                                   assembled_context: Dict[str, Any]) -> float:
        """计算压缩比"""
        original_size = len(json.dumps(original_contexts))
        assembled_size = len(json.dumps(assembled_context))
        
        if original_size == 0:
            return 1.0
        
        return assembled_size / original_size
    
    def _calculate_quality_score(self, assembled_context: Dict[str, Any]) -> float:
        """计算质量分数"""
        # 简化的质量评估
        if not assembled_context:
            return 0.0
        
        # 基于内容丰富度和结构完整性
        content_richness = len(str(assembled_context)) / 1000  # 标准化
        structure_completeness = len(assembled_context.keys()) / 10  # 标准化
        
        return min(1.0, (content_richness + structure_completeness) / 2)


class ContextRetrievalEngine:
    """上下文检索与生成引擎"""
    
    def __init__(self):
        self.prompt_engineer = PromptEngineer()
        self.context_assembler = DynamicContextAssembler()
        self.retrieval_strategies = {
            'semantic_search': SemanticSearchStrategy(),
            'temporal_context': TemporalContextStrategy(),
            'task_specific': TaskSpecificStrategy(),
            'multi_modal': MultiModalStrategy()
        }
        self.metrics = {
            "total_retrievals": 0,
            "average_retrieval_time": 0.0,
            "cache_hit_rate": 0.0
        }
    
    async def retrieve_context(self, query: str, session_state: SessionState,
                             task_context: TaskContext) -> ContextPackage:
        """检索上下文的主入口方法"""
        
        start_time = asyncio.get_event_loop().time()
        
        # 1. 意图识别和上下文需求分析
        intent = await self.prompt_engineer.analyze_intent(query)
        context_requirements = self._determine_context_needs(intent, task_context)
        
        # 2. 多策略并行检索
        retrieval_tasks = []
        for strategy_name in context_requirements.strategies:
            if strategy_name in self.retrieval_strategies:
                strategy = self.retrieval_strategies[strategy_name]
                task = strategy.retrieve(query, session_state, context_requirements)
                retrieval_tasks.append(task)
        
        # 3. 等待所有检索完成
        retrieved_contexts = await asyncio.gather(*retrieval_tasks, return_exceptions=True)
        
        # 过滤异常结果
        valid_contexts = []
        for i, result in enumerate(retrieved_contexts):
            if isinstance(result, Exception):
                print(f"Retrieval strategy {i} failed: {result}")
            else:
                valid_contexts.append(result)
        
        # 4. 动态上下文组装
        assembled_context = await self.context_assembler.assemble(
            valid_contexts, context_requirements
        )
        
        # 5. 计算检索指标
        retrieval_time = asyncio.get_event_loop().time() - start_time
        retrieval_metrics = self._calculate_metrics(
            valid_contexts, retrieval_time, context_requirements
        )
        
        # 6. 更新统计信息
        self._update_metrics(retrieval_time)
        
        return ContextPackage(
            primary_context=assembled_context,
            metadata={
                "intent_analysis": intent,
                "context_requirements": context_requirements.dict(),
                "retrieval_strategies_used": [ctx.get("strategy") for ctx in valid_contexts],
                "retrieval_time": retrieval_time
            },
            retrieval_metrics=retrieval_metrics
        )
    
    def _determine_context_needs(self, intent: Dict[str, Any], 
                               task_context: TaskContext) -> ContextRequirements:
        """确定上下文需求"""
        
        # 基于意图和任务类型确定策略
        strategies = ["semantic_search"]  # 默认策略
        
        if intent.get("primary_intent") == "analysis":
            strategies.extend(["task_specific", "temporal_context"])
        elif intent.get("primary_intent") == "command":
            strategies.extend(["task_specific"])
        elif intent.get("primary_intent") == "question":
            strategies.extend(["temporal_context"])
        
        # 如果是复杂任务，添加多模态策略
        if task_context.complexity_level > 2:
            strategies.append("multi_modal")
        
        # 基于任务领域调整token限制
        max_tokens = 50000  # 默认值
        if task_context.domain == "code":
            max_tokens = 100000
        elif task_context.domain == "data":
            max_tokens = 75000
        
        return ContextRequirements(
            strategies=list(set(strategies)),  # 去重
            max_tokens=max_tokens,
            preserve_structure=True,
            goals=["relevance", "completeness", "efficiency"],
            priority_keywords=intent.get("complexity_indicators", {}).get("key_terms", [])
        )
    
    def _calculate_metrics(self, contexts: List[Dict[str, Any]], 
                          retrieval_time: float,
                          requirements: ContextRequirements) -> Dict[str, Any]:
        """计算检索指标"""
        
        total_items = sum(
            len(ctx.get("results", {})) if isinstance(ctx.get("results"), (list, dict)) else 1
            for ctx in contexts
        )
        
        average_relevance = 0.0
        relevance_scores = []
        
        for ctx in contexts:
            if ctx.get("strategy") == "semantic_search":
                results = ctx.get("results", [])
                if isinstance(results, list):
                    scores = [item.get("relevance_score", 0) for item in results 
                             if isinstance(item, dict)]
                    relevance_scores.extend(scores)
        
        if relevance_scores:
            average_relevance = sum(relevance_scores) / len(relevance_scores)
        
        return {
            "retrieval_time": retrieval_time,
            "strategies_used": len(contexts),
            "total_items_retrieved": total_items,
            "average_relevance_score": average_relevance,
            "token_efficiency": total_items / requirements.max_tokens if requirements.max_tokens > 0 else 0,
            "context_diversity": len(set(ctx.get("strategy") for ctx in contexts))
        }
    
    def _update_metrics(self, retrieval_time: float):
        """更新性能指标"""
        self.metrics["total_retrievals"] += 1
        
        # 更新平均检索时间
        total_retrievals = self.metrics["total_retrievals"]
        current_avg = self.metrics["average_retrieval_time"]
        
        self.metrics["average_retrieval_time"] = (
            (current_avg * (total_retrievals - 1) + retrieval_time) / total_retrievals
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return self.metrics.copy()