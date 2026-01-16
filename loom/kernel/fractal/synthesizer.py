"""
Result Synthesizer

实现可配置的结果合成策略，支持使用轻量级模型进行高效的结果聚合。
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SynthesisConfig:
    """合成配置"""

    synthesis_model: str = "lightweight"
    """合成策略: lightweight|same_model|custom"""

    synthesis_model_override: str | None = None
    """自定义合成模型（当 synthesis_model='custom' 时使用）"""

    max_synthesis_tokens: int = 2000
    """合成时的最大 token 数"""

    def validate(self):
        """验证配置"""
        if self.synthesis_model not in ["lightweight", "same_model", "custom"]:
            raise ValueError(f"无效的合成策略: {self.synthesis_model}")

        if self.synthesis_model == "custom" and not self.synthesis_model_override:
            raise ValueError("使用 custom 策略时必须指定 synthesis_model_override")

        if self.max_synthesis_tokens <= 0:
            raise ValueError("max_synthesis_tokens 必须大于 0")


class ResultSynthesizer:
    """
    结果合成器

    根据配置策略合成子任务结果，支持：
    1. concatenate: 简单拼接
    2. structured: 结构化输出
    3. auto: LLM 合成（支持轻量级模型）
    """

    # 轻量级模型映射表
    LIGHTWEIGHT_MODEL_MAP = {
        "gpt-4": "gpt-3.5-turbo",
        "gpt-4-turbo": "gpt-3.5-turbo",
        "gpt-4o": "gpt-4o-mini",
        "claude-opus-3": "claude-haiku-3",
        "claude-sonnet-3.5": "claude-haiku-3",
        "claude-3-opus-20240229": "claude-3-haiku-20240307",
        "claude-3-sonnet-20240229": "claude-3-haiku-20240307",
    }

    def __init__(self, provider, config: SynthesisConfig):
        """
        初始化合成器

        Args:
            provider: LLM Provider 实例
            config: 合成配置
        """
        self.base_provider = provider
        self.config = config
        self.config.validate()

    async def synthesize(
        self,
        task: str,
        subtask_results: list[dict[str, Any]],
        strategy: str = "auto"
    ) -> str:
        """
        合成子任务结果

        Args:
            task: 原始任务描述
            subtask_results: 子任务结果列表
            strategy: 合成策略 (auto|concatenate|structured)

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
            elif strategy == "auto":
                return await self._llm_synthesize(task, subtask_results)
            else:
                raise ValueError(f"未知的合成策略: {strategy}")
        except Exception as e:
            logger.error(f"合成失败: {e}")
            # 降级到简单拼接
            return self._concatenate(subtask_results)

    def _concatenate(self, subtask_results: list[dict[str, Any]]) -> str:
        """
        简单拼接策略

        将所有子任务结果按顺序拼接，用分隔符分开。
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
        lines.insert(1, f"**总计**: {total} 个子任务 | ✅ {success_count} 成功 | ❌ {failure_count} 失败\n")

        return "\n".join(lines)

    async def _llm_synthesize(self, task: str, results: list[dict[str, Any]]) -> str:
        """
        使用 LLM 合成（支持轻量级模型）

        Args:
            task: 原始任务描述
            results: 子任务结果列表

        Returns:
            LLM 合成的结果
        """
        # 获取合成用的 Provider
        provider = self._get_synthesis_provider()

        # 构建合成提示词
        prompt = self._build_synthesis_prompt(task, results)

        # 调用 LLM
        try:
            response = await provider.generate(
                prompt,
                max_tokens=self.config.max_synthesis_tokens
            )
            return str(response).strip()
        except Exception as e:
            logger.error(f"LLM 合成失败: {e}")
            # 降级到结构化输出
            return self._structured(results)

    def _get_synthesis_provider(self):
        """
        获取合成用的 Provider

        根据配置选择合适的模型。
        """
        if self.config.synthesis_model == "lightweight":
            # 自动映射到轻量级模型
            return self._map_to_lightweight(self.base_provider)
        elif self.config.synthesis_model == "same_model":
            return self.base_provider
        elif self.config.synthesis_model == "custom":
            # 用户指定的模型
            if not self.config.synthesis_model_override:
                 raise ValueError("Custom model selected but no override provided")
            return self._create_custom_provider(self.config.synthesis_model_override)
        else:
            return self.base_provider

    def _map_to_lightweight(self, provider):
        """
        映射到轻量级模型

        Args:
            provider: 原始 Provider

        Returns:
            使用轻量级模型的 Provider
        """
        # 获取当前模型
        base_model = getattr(provider, 'model', None)
        if not base_model:
            logger.warning("无法获取 Provider 的模型信息，使用原始 Provider")
            return provider

        # 查找映射
        lightweight_model = self.LIGHTWEIGHT_MODEL_MAP.get(base_model, base_model)

        if lightweight_model == base_model:
            logger.info(f"模型 {base_model} 没有轻量级映射，使用原始模型")
            return provider

        logger.info(f"映射模型: {base_model} -> {lightweight_model}")

        # 创建新的 Provider 实例
        try:
            provider_class = provider.__class__
            # 尝试创建新实例，保留其他配置
            new_provider = provider_class(model=lightweight_model)
            return new_provider
        except Exception as e:
            logger.error(f"创建轻量级 Provider 失败: {e}")
            return provider

    def _create_custom_provider(self, model_name: str):
        """
        创建自定义模型的 Provider

        Args:
            model_name: 模型名称

        Returns:
            Provider 实例
        """
        try:
            provider_class = self.base_provider.__class__
            return provider_class(model=model_name)
        except Exception as e:
            logger.error(f"创建自定义 Provider 失败: {e}")
            return self.base_provider

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
