"""
ResultSynthesizer Tests

测试结果合成器功能，目标覆盖率 80%+
"""

from unittest.mock import AsyncMock, Mock

import pytest

from loom.fractal.synthesizer import ResultSynthesizer


class TestResultSynthesizerConcatenate:
    """测试简单拼接策略"""

    @pytest.mark.asyncio
    async def test_synthesize_concatenate_strategy(self):
        """测试concatenate策略"""
        synthesizer = ResultSynthesizer()

        subtask_results = [{"result": "结果1"}, {"result": "结果2"}, {"result": "结果3"}]

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=subtask_results, strategy="concatenate"
        )

        assert "子任务 1 结果:" in result
        assert "结果1" in result
        assert "子任务 2 结果:" in result
        assert "结果2" in result
        assert "子任务 3 结果:" in result
        assert "结果3" in result
        assert "---" in result

    def test_concatenate_with_dict_results(self):
        """测试拼接字典结果"""
        synthesizer = ResultSynthesizer()

        subtask_results = [{"result": "第一个结果"}, {"result": "第二个结果"}]

        result = synthesizer._concatenate(subtask_results)

        assert "子任务 1 结果:" in result
        assert "第一个结果" in result
        assert "子任务 2 结果:" in result
        assert "第二个结果" in result

    def test_concatenate_without_result_key(self):
        """测试拼接没有result键的结果"""
        synthesizer = ResultSynthesizer()

        subtask_results = [{"data": "数据1"}, {"data": "数据2"}]

        result = synthesizer._concatenate(subtask_results)

        assert "子任务 1 结果:" in result
        assert "子任务 2 结果:" in result


class TestResultSynthesizerStructured:
    """测试结构化输出策略"""

    @pytest.mark.asyncio
    async def test_synthesize_structured_strategy(self):
        """测试structured策略"""
        synthesizer = ResultSynthesizer()

        subtask_results = [
            {"result": "成功结果1", "success": True},
            {"result": "成功结果2", "success": True},
        ]

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=subtask_results, strategy="structured"
        )

        assert "# 任务执行结果" in result
        assert "✅ 成功" in result
        assert "成功结果1" in result
        assert "成功结果2" in result
        assert "2 个子任务" in result

    def test_structured_with_success_and_failure(self):
        """测试结构化输出包含成功和失败"""
        synthesizer = ResultSynthesizer()

        subtask_results = [
            {"result": "成功结果", "success": True},
            {"result": "失败结果", "success": False, "error": "错误信息"},
        ]

        result = synthesizer._structured(subtask_results)

        assert "✅ 成功" in result
        assert "❌ 失败" in result
        assert "成功结果" in result
        assert "失败结果" in result
        assert "错误信息" in result
        assert "1 成功" in result
        assert "1 失败" in result

    def test_structured_all_success(self):
        """测试结构化输出全部成功"""
        synthesizer = ResultSynthesizer()

        subtask_results = [
            {"result": "结果1", "success": True},
            {"result": "结果2", "success": True},
            {"result": "结果3", "success": True},
        ]

        result = synthesizer._structured(subtask_results)

        assert "3 个子任务" in result
        assert "3 成功" in result
        assert "0 失败" in result

    def test_structured_default_success(self):
        """测试结构化输出默认为成功"""
        synthesizer = ResultSynthesizer()

        subtask_results = [
            {"result": "结果1"},  # 没有success字段，默认为True
            {"result": "结果2"},
        ]

        result = synthesizer._structured(subtask_results)

        assert "2 成功" in result
        assert "0 失败" in result


class TestResultSynthesizerLLM:
    """测试LLM合成策略"""

    @pytest.mark.asyncio
    async def test_synthesize_llm_strategy_success(self):
        """测试LLM策略成功"""
        synthesizer = ResultSynthesizer()

        # Mock provider with chat() method
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "LLM合成的结果"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        subtask_results = [{"result": "结果1"}, {"result": "结果2"}]

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=subtask_results, strategy="llm", provider=mock_provider
        )

        assert result == "LLM合成的结果"
        mock_provider.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_llm_without_provider(self):
        """测试LLM策略没有provider时降级"""
        synthesizer = ResultSynthesizer()

        subtask_results = [{"result": "结果1", "success": True}]

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=subtask_results, strategy="llm", provider=None
        )

        # 应该降级到structured
        assert "# 任务执行结果" in result
        assert "✅ 成功" in result

    @pytest.mark.asyncio
    async def test_llm_synthesize_failure_fallback(self):
        """测试LLM合成失败时降级"""
        synthesizer = ResultSynthesizer()

        # Mock provider that raises exception
        mock_provider = Mock()
        mock_provider.chat = AsyncMock(side_effect=RuntimeError("LLM错误"))

        subtask_results = [{"result": "结果1", "success": True}]

        result = await synthesizer._llm_synthesize(
            task="测试任务", results=subtask_results, provider=mock_provider, max_tokens=2000
        )

        # 应该降级到structured
        assert "# 任务执行结果" in result


class TestResultSynthesizerEdgeCases:
    """测试边界情况和异常处理"""

    @pytest.mark.asyncio
    async def test_synthesize_empty_results(self):
        """测试空结果列表"""
        synthesizer = ResultSynthesizer()

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=[], strategy="structured"
        )

        assert result == "没有子任务结果可供合成。"

    @pytest.mark.asyncio
    async def test_synthesize_unknown_strategy(self):
        """测试未知策略时降级"""
        synthesizer = ResultSynthesizer()

        subtask_results = [{"result": "结果1", "success": True}]

        result = await synthesizer.synthesize(
            task="测试任务", subtask_results=subtask_results, strategy="unknown_strategy"
        )

        # 应该降级到structured
        assert "# 任务执行结果" in result
        assert "✅ 成功" in result

    @pytest.mark.asyncio
    async def test_synthesize_exception_fallback(self):
        """测试异常时降级到concatenate"""
        from unittest.mock import patch

        synthesizer = ResultSynthesizer()

        subtask_results = [{"result": "结果1"}]

        # Mock _structured to raise exception
        with patch.object(synthesizer, "_structured", side_effect=RuntimeError("错误")):
            result = await synthesizer.synthesize(
                task="测试任务", subtask_results=subtask_results, strategy="structured"
            )

        # 应该降级到concatenate
        assert "子任务 1 结果:" in result
        assert "结果1" in result


class TestResultSynthesizerPromptBuilding:
    """测试提示词构建"""

    def test_build_synthesis_prompt(self):
        """测试构建合成提示词"""
        synthesizer = ResultSynthesizer()

        task = "完成数据分析"
        results = [
            {"result": "数据已清洗", "success": True},
            {"result": "分析失败", "success": False},
        ]

        prompt = synthesizer._build_synthesis_prompt(task, results)

        assert "完成数据分析" in prompt
        assert "数据已清洗" in prompt
        assert "分析失败" in prompt
        assert "✅ 成功" in prompt
        assert "❌ 失败" in prompt
        assert "综合答案：" in prompt

    def test_build_synthesis_prompt_all_success(self):
        """测试构建提示词全部成功"""
        synthesizer = ResultSynthesizer()

        task = "测试任务"
        results = [{"result": "结果1", "success": True}, {"result": "结果2", "success": True}]

        prompt = synthesizer._build_synthesis_prompt(task, results)

        assert "子任务 1 (✅ 成功)" in prompt
        assert "子任务 2 (✅ 成功)" in prompt
        assert "结果1" in prompt
        assert "结果2" in prompt
