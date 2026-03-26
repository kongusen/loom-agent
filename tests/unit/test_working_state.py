"""测试 WorkingState"""

import pytest

from loom.memory.tokenizers import EstimatorTokenizer
from loom.types.working import WorkingState


class TestWorkingState:
    """验证 WorkingState 预算化结构"""

    def test_to_text_with_all_fields(self):
        """测试所有字段转换为文本"""
        tokenizer = EstimatorTokenizer()
        state = WorkingState(
            budget=2000,
            goal="Complete task",
            plan="Step 1, Step 2",
            next_action="Execute step 1"
        )

        text = state.to_text(tokenizer)

        assert "<goal>Complete task</goal>" in text
        assert "<plan>Step 1, Step 2</plan>" in text
        assert "<next_action>Execute step 1</next_action>" in text

    def test_to_text_respects_budget(self):
        """测试预算限制"""
        tokenizer = EstimatorTokenizer()
        state = WorkingState(
            budget=50,  # 很小的预算
            goal="A" * 1000,  # 很长的内容
        )

        text = state.to_text(tokenizer)
        tokens = tokenizer.count(text)

        # 应该被截断（允许小误差）
        assert tokens <= 55

    def test_from_text_parses_fields(self):
        """测试从文本解析字段"""
        text = "<goal>Test goal</goal>\n<plan>Test plan</plan>"
        state = WorkingState.from_text(text)

        assert state.goal == "Test goal"
        assert state.plan == "Test plan"

    def test_overflow_field(self):
        """测试 overflow 字段"""
        tokenizer = EstimatorTokenizer()
        state = WorkingState(
            budget=2000,
            overflow="Extra content here"
        )

        text = state.to_text(tokenizer)

        assert "<overflow>Extra content here</overflow>" in text
