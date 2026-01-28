"""
Result Synthesizer - 结果合成器

基于A3公理（分形自相似公理）：
实现子任务结果的智能合成。

简化原则：
1. 移除provider管理逻辑（由调用者负责）
2. 移除配置类（过度设计）
3. 保留核心合成策略
4. 保留降级方案
5. 集成质量指标评估
"""

import logging
from typing import TYPE_CHECKING, Any

from loom.fractal.budget import QualityEvaluator, QualityMetrics

if TYPE_CHECKING:
    from loom.providers.llm.interface import LLMProvider

logger = logging.getLogger(__name__)


class ResultSynthesizer:
    """
    结果合成器

    支持3种合成策略：
    1. concatenate: 简单拼接
    2. structured: 结构化输出
    3. llm: LLM智能合成（需要provider）
    """

    async def synthesize(
        self,
        task: str,
        subtask_results: list[dict[str, Any]],
        strategy: str = "structured",
        provider: "LLMProvider | None" = None,
        max_tokens: int = 2000,
    ) -> str:
        """
        合成子任务结果

        Args:
            task: 原始任务描述
            subtask_results: 子任务结果列表
            strategy: 合成策略 (concatenate|structured|llm)
            provider: LLM provider（仅llm策略需要）
            max_tokens: LLM合成的最大token数

        Returns:
            合成后的结果字符串
        """
        if not subtask_results:
            return "没有子任务结果可供合成。"

        logger.info(f"开始合成 {len(subtask_results)} 个子任务结果，策略: {strategy}")

        try:
            if strategy == "concatenate":
                return self._concatenate(subtask_results)
            elif strategy == "structured":
                return self._structured(subtask_results)
            elif strategy == "llm":
                if not provider:
                    logger.warning("LLM策略需要provider，降级到structured")
                    return self._structured(subtask_results)
                return await self._llm_synthesize(task, subtask_results, provider, max_tokens)
            else:
                logger.warning(f"未知的合成策略: {strategy}，使用structured")
                return self._structured(subtask_results)
        except Exception as e:
            logger.error(f"合成失败: {e}，降级到concatenate")
            return self._concatenate(subtask_results)

    def _concatenate(self, subtask_results: list[dict[str, Any]]) -> str:
        """
        简单拼接策略

        将所有子任务结果按顺序拼接，用分隔符分开。

        Args:
            subtask_results: 子任务结果列表

        Returns:
            拼接后的结果
        """
        parts = []
        for i, result in enumerate(subtask_results, 1):
            result_text = result.get("result", str(result))
            parts.append(f"子任务 {i} 结果:\n{result_text}")

        return "\n\n---\n\n".join(parts)

    def _structured(self, subtask_results: list[dict[str, Any]]) -> str:
        """
        结构化输出策略

        生成带有状态指示器和组织结构的输出。

        Args:
            subtask_results: 子任务结果列表

        Returns:
            结构化的结果
        """
        lines = ["# 任务执行结果\n"]

        success_count = 0
        failure_count = 0

        for i, result in enumerate(subtask_results, 1):
            # 判断成功/失败
            is_success = result.get("success", True)
            if is_success:
                success_count += 1
                status = "✅ 成功"
            else:
                failure_count += 1
                status = "❌ 失败"

            # 提取结果
            result_text = result.get("result", str(result))
            error = result.get("error")

            lines.append(f"## 子任务 {i} - {status}\n")
            if error:
                lines.append(f"**错误**: {error}\n")
            lines.append(f"{result_text}\n")

        # 添加摘要
        total = len(subtask_results)
        lines.insert(
            1, f"**总计**: {total} 个子任务 | ✅ {success_count} 成功 | ❌ {failure_count} 失败\n"
        )

        return "\n".join(lines)

    async def _llm_synthesize(
        self,
        task: str,
        results: list[dict[str, Any]],
        provider: "LLMProvider",
        max_tokens: int,
    ) -> str:
        """
        使用LLM合成

        Args:
            task: 原始任务描述
            results: 子任务结果列表
            provider: LLM provider
            max_tokens: 最大token数

        Returns:
            LLM合成的结果
        """
        # 构建合成提示词
        prompt = self._build_synthesis_prompt(task, results)

        # 调用LLM
        try:
            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens
            )
            return response.content.strip()
        except Exception as e:
            logger.error(f"LLM合成失败: {e}，降级到structured")
            return self._structured(results)

    def _build_synthesis_prompt(self, task: str, results: list[dict[str, Any]]) -> str:
        """
        构建合成提示词

        Args:
            task: 原始任务描述
            results: 子任务结果列表

        Returns:
            合成提示词
        """
        # 构建子任务结果部分
        results_text = []
        for i, result in enumerate(results, 1):
            result_content = result.get("result", str(result))
            success = result.get("success", True)
            status = "✅ 成功" if success else "❌ 失败"

            results_text.append(f"子任务 {i} ({status}):\n{result_content}")

        results_section = "\n\n".join(results_text)

        # 构建完整提示词
        prompt = f"""请将以下子任务的结果合成为一个连贯、完整的答案。

原始任务：
{task}

子任务结果：
{results_section}

请提供一个综合性的答案，要求：
1. 整合所有成功的子任务结果
2. 保持逻辑连贯和流畅
3. 如果有失败的子任务，简要说明但不影响整体答案
4. 直接给出答案，不需要额外的解释或元信息

综合答案："""

        return prompt

    async def synthesize_with_quality(
        self,
        task: str,
        subtask_results: list[dict[str, Any]],
        strategy: str = "structured",
        provider: "LLMProvider | None" = None,
        max_tokens: int = 2000,
        parent_context: str = "",
    ) -> tuple[str, list[QualityMetrics]]:
        """
        合成子任务结果并评估质量

        Args:
            task: 原始任务描述
            subtask_results: 子任务结果列表
            strategy: 合成策略
            provider: LLM provider（用于合成和质量评估）
            max_tokens: 最大token数
            parent_context: 父节点上下文

        Returns:
            (合成结果, 质量指标列表)
        """
        # 1. 创建评估器（有provider则用LLM评估）
        evaluator = QualityEvaluator(provider=provider)
        quality_metrics = []

        for result in subtask_results:
            subtask_desc = result.get("subtask", "")
            metrics = await evaluator.evaluate(subtask_desc, result, parent_context)
            quality_metrics.append(metrics)
            result["_quality_metrics"] = metrics

        # 2. 执行合成
        synthesized = await self.synthesize(
            task, subtask_results, strategy, provider, max_tokens
        )

        # 3. 记录质量统计
        avg_score = sum(m.overall_score for m in quality_metrics) / len(quality_metrics) if quality_metrics else 0
        logger.info(f"合成完成，平均质量分数: {avg_score:.2f}")

        return synthesized, quality_metrics

    def _structured_with_quality(
        self, subtask_results: list[dict[str, Any]]
    ) -> str:
        """带质量指标的结构化输出"""
        lines = ["# 任务执行结果\n"]

        success_count = 0
        failure_count = 0
        total_score = 0.0

        for i, result in enumerate(subtask_results, 1):
            is_success = result.get("success", True)
            metrics: QualityMetrics | None = result.get("_quality_metrics")

            if is_success:
                success_count += 1
                status = "✅ 成功"
            else:
                failure_count += 1
                status = "❌ 失败"

            result_text = result.get("result", str(result))
            error = result.get("error")

            lines.append(f"## 子任务 {i} - {status}\n")

            # 添加质量指标
            if metrics:
                total_score += metrics.overall_score
                lines.append(
                    f"**质量**: 置信度={metrics.confidence:.2f}, "
                    f"覆盖度={metrics.coverage:.2f}, "
                    f"新颖度={metrics.novelty:.2f}\n"
                )

            if error:
                lines.append(f"**错误**: {error}\n")
            lines.append(f"{result_text}\n")

        # 添加摘要
        total = len(subtask_results)
        avg_score = total_score / total if total > 0 else 0
        lines.insert(
            1,
            f"**总计**: {total} 个子任务 | ✅ {success_count} 成功 | "
            f"❌ {failure_count} 失败 | 平均质量: {avg_score:.2f}\n"
        )

        return "\n".join(lines)
