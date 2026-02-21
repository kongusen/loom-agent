"""
Result Synthesizer - 结果合成器

基于A3公理（分形自相似公理）：
实现子任务结果的智能合成。

简化原则：
1. 移除provider管理逻辑（由调用者负责）
2. 移除配置类（过度设计）
3. 保留核心合成策略
4. 保留降级方案

Phase 5: 移除质量指标评估（预算系统的一部分）
"""

import logging
from typing import TYPE_CHECKING, Any

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
