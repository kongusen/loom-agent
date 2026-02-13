"""
Tests for context/budget.py and context/compactor.py
"""

from unittest.mock import MagicMock

import pytest

from loom.context.block import ContextBlock
from loom.context.budget import (
    DEFAULT_ALLOCATION_RATIOS,
    LEGACY_ALLOCATION_RATIOS,
    PHASE_ALLOCATION_TEMPLATES,
    AdaptiveBudgetManager,
    BudgetAllocation,
    BudgetManager,
    TaskPhase,
    TokenBudget,
)
from loom.context.compactor import CompactionLevel, ContextCompactor

# ============ TokenBudget ============


class TestTokenBudget:
    def test_basic(self):
        b = TokenBudget(total=10000, reserved_output=2500, system_prompt=500)
        assert b.available == 7000
        assert b.used == 500
        assert b.remaining == 7000

    def test_available_never_negative(self):
        b = TokenBudget(total=100, reserved_output=80, system_prompt=50)
        assert b.available == 0

    def test_zero_reserved(self):
        b = TokenBudget(total=10000)
        assert b.available == 10000
        assert b.reserved_output == 0
        assert b.system_prompt == 0


# ============ BudgetAllocation ============


class TestBudgetAllocation:
    def test_get_existing(self):
        ba = BudgetAllocation(allocations={"L1": 100, "L2": 200})
        assert ba.get("L1") == 100

    def test_get_missing(self):
        ba = BudgetAllocation(allocations={"L1": 100})
        assert ba.get("L3") == 0

    def test_total_allocated(self):
        ba = BudgetAllocation(allocations={"L1": 100, "L2": 200, "L3": 50})
        assert ba.total_allocated == 350

    def test_empty(self):
        ba = BudgetAllocation()
        assert ba.total_allocated == 0
        assert ba.get("any") == 0


# ============ TaskPhase ============


class TestTaskPhase:
    def test_early(self):
        assert TaskPhase.from_progress(0, 10) == TaskPhase.EARLY
        assert TaskPhase.from_progress(2, 10) == TaskPhase.EARLY

    def test_middle(self):
        assert TaskPhase.from_progress(5, 10) == TaskPhase.MIDDLE

    def test_late(self):
        assert TaskPhase.from_progress(8, 10) == TaskPhase.LATE
        assert TaskPhase.from_progress(10, 10) == TaskPhase.LATE

    def test_zero_max(self):
        assert TaskPhase.from_progress(0, 0) == TaskPhase.MIDDLE

    def test_negative_max(self):
        assert TaskPhase.from_progress(5, -1) == TaskPhase.MIDDLE


# ============ BudgetManager ============


class TestBudgetManager:
    @pytest.fixture
    def counter(self):
        c = MagicMock()
        c.count_messages.return_value = 100
        return c

    def test_init_defaults(self, counter):
        mgr = BudgetManager(counter, model_context_window=128000)
        assert mgr.model_context_window == 128000
        assert mgr.output_reserve_ratio == 0.25
        total = sum(mgr.allocation_ratios.values())
        assert abs(total - 1.0) < 0.01

    def test_create_budget_no_prompt(self, counter):
        mgr = BudgetManager(counter, model_context_window=10000)
        budget = mgr.create_budget()
        assert budget.total == 10000
        assert budget.reserved_output == 2500
        assert budget.system_prompt == 0

    def test_create_budget_with_prompt(self, counter):
        counter.count_messages.return_value = 200
        mgr = BudgetManager(counter, model_context_window=10000)
        budget = mgr.create_budget("You are a helpful assistant.")
        assert budget.system_prompt == 200

    def test_allocate(self, counter):
        mgr = BudgetManager(counter, model_context_window=10000)
        budget = TokenBudget(total=10000, reserved_output=2500)
        allocation = mgr.allocate(budget)
        assert allocation.total_allocated > 0
        assert allocation.total_allocated <= budget.available

    def test_allocate_for_sources(self, counter):
        mgr = BudgetManager(counter, model_context_window=10000)
        budget = TokenBudget(total=10000, reserved_output=2500)
        allocation = mgr.allocate_for_sources(budget, ["L1_recent", "L2_important"])
        assert allocation.get("L1_recent") > 0
        assert allocation.get("L2_important") > 0
        assert allocation.get("tools") == 0

    def test_allocate_for_unknown_sources(self, counter):
        mgr = BudgetManager(counter, model_context_window=10000)
        budget = TokenBudget(total=10000, reserved_output=2500)
        allocation = mgr.allocate_for_sources(budget, ["unknown_source"])
        assert allocation.get("unknown_source") > 0

    def test_normalize_ratios_zero_total(self, counter):
        mgr = BudgetManager(counter, model_context_window=10000)
        result = mgr._normalize_ratios({"a": 0, "b": 0})
        assert result == DEFAULT_ALLOCATION_RATIOS

    def test_custom_ratios(self, counter):
        custom = {"A": 0.5, "B": 0.5}
        mgr = BudgetManager(counter, model_context_window=10000, allocation_ratios=custom)
        assert abs(mgr.allocation_ratios["A"] - 0.5) < 0.01
        assert abs(mgr.allocation_ratios["B"] - 0.5) < 0.01


# ============ AdaptiveBudgetManager ============


class TestAdaptiveBudgetManager:
    @pytest.fixture
    def counter(self):
        c = MagicMock()
        c.count_messages.return_value = 100
        return c

    def test_init_default_phase(self, counter):
        mgr = AdaptiveBudgetManager(counter, model_context_window=128000)
        assert mgr.current_phase == TaskPhase.EARLY

    def test_update_phase_early(self, counter):
        mgr = AdaptiveBudgetManager(counter, model_context_window=128000)
        phase = mgr.update_phase(1, 10)
        assert phase == TaskPhase.EARLY

    def test_update_phase_middle(self, counter):
        mgr = AdaptiveBudgetManager(counter, model_context_window=128000)
        phase = mgr.update_phase(5, 10)
        assert phase == TaskPhase.MIDDLE

    def test_update_phase_late(self, counter):
        mgr = AdaptiveBudgetManager(counter, model_context_window=128000)
        phase = mgr.update_phase(8, 10)
        assert phase == TaskPhase.LATE

    def test_phase_changes_allocation_ratios(self, counter):
        mgr = AdaptiveBudgetManager(counter, model_context_window=128000)
        mgr.update_phase(1, 10)  # early
        early_ratios = mgr.allocation_ratios.copy()
        mgr.update_phase(8, 10)  # late
        late_ratios = mgr.allocation_ratios.copy()
        # INHERITED should be higher in late phase
        assert late_ratios.get("INHERITED", 0) > early_ratios.get("INHERITED", 0)

    def test_custom_phase_templates(self, counter):
        custom = {
            TaskPhase.EARLY: {"A": 0.5, "B": 0.5},
            TaskPhase.MIDDLE: {"A": 0.3, "B": 0.7},
            TaskPhase.LATE: {"A": 0.1, "B": 0.9},
        }
        mgr = AdaptiveBudgetManager(
            counter, model_context_window=128000, phase_templates=custom
        )
        mgr.update_phase(8, 10)
        assert abs(mgr.allocation_ratios["B"] - 0.9) < 0.01


# ============ Constants ============


class TestBudgetConstants:
    def test_default_ratios_sum_to_one(self):
        total = sum(DEFAULT_ALLOCATION_RATIOS.values())
        assert abs(total - 1.0) < 0.01

    def test_legacy_ratios_sum_to_one(self):
        total = sum(LEGACY_ALLOCATION_RATIOS.values())
        assert abs(total - 1.0) < 0.01

    def test_phase_templates_exist(self):
        assert TaskPhase.EARLY in PHASE_ALLOCATION_TEMPLATES
        assert TaskPhase.MIDDLE in PHASE_ALLOCATION_TEMPLATES
        assert TaskPhase.LATE in PHASE_ALLOCATION_TEMPLATES


# ============ CompactionLevel ============


class TestCompactionLevel:
    def test_enum_values(self):
        assert CompactionLevel.NONE.value == 0
        assert CompactionLevel.LIGHT.value == 1
        assert CompactionLevel.MEDIUM.value == 2
        assert CompactionLevel.AGGRESSIVE.value == 3

    def test_ordering(self):
        assert CompactionLevel.NONE.value < CompactionLevel.LIGHT.value
        assert CompactionLevel.LIGHT.value < CompactionLevel.MEDIUM.value
        assert CompactionLevel.MEDIUM.value < CompactionLevel.AGGRESSIVE.value


# ============ ContextCompactor ============


def _make_block(content="test", tokens=100, priority=0.5, compressible=True, source="L1"):
    return ContextBlock(
        content=content,
        role="system",
        token_count=tokens,
        priority=priority,
        source=source,
        compressible=compressible,
    )


class TestContextCompactorInit:
    def test_init(self):
        counter = MagicMock()
        cc = ContextCompactor(counter)
        assert cc.token_counter is counter
        assert cc.summarizer is None

    def test_init_with_summarizer(self):
        counter = MagicMock()
        summarizer = MagicMock()
        cc = ContextCompactor(counter, summarizer=summarizer)
        assert cc.summarizer is summarizer


class TestGetCompactionLevel:
    @pytest.fixture
    def compactor(self):
        return ContextCompactor(MagicMock())

    def test_none_level(self, compactor):
        assert compactor.get_compaction_level(500, 1000) == CompactionLevel.NONE

    def test_light_level(self, compactor):
        assert compactor.get_compaction_level(750, 1000) == CompactionLevel.LIGHT

    def test_medium_level(self, compactor):
        assert compactor.get_compaction_level(900, 1000) == CompactionLevel.MEDIUM

    def test_aggressive_level(self, compactor):
        assert compactor.get_compaction_level(960, 1000) == CompactionLevel.AGGRESSIVE

    def test_zero_budget(self, compactor):
        assert compactor.get_compaction_level(100, 0) == CompactionLevel.AGGRESSIVE

    def test_negative_budget(self, compactor):
        assert compactor.get_compaction_level(100, -1) == CompactionLevel.AGGRESSIVE


class TestCompactorCompact:
    @pytest.fixture
    def counter(self):
        c = MagicMock()
        c.count_messages.return_value = 50
        return c

    async def test_empty_blocks(self, counter):
        cc = ContextCompactor(counter)
        result = await cc.compact([], 1000)
        assert result == []

    async def test_within_budget_no_change(self, counter):
        cc = ContextCompactor(counter)
        blocks = [_make_block(tokens=100), _make_block(tokens=100)]
        result = await cc.compact(blocks, 500)
        assert len(result) == 2

    async def test_over_budget_drops_low_priority(self, counter):
        cc = ContextCompactor(counter)
        b_high = _make_block(tokens=100, priority=0.9, compressible=False)
        b_low = _make_block(tokens=100, priority=0.1, compressible=False)
        # Budget only fits one block
        result = await cc.compact([b_low, b_high], 100)
        assert len(result) == 1
        assert result[0].priority == 0.9

    async def test_non_compressible_preserved(self, counter):
        cc = ContextCompactor(counter)
        b1 = _make_block(tokens=50, priority=0.9, compressible=False)
        b2 = _make_block(tokens=50, priority=0.5, compressible=True)
        result = await cc.compact([b1, b2], 80)
        # Non-compressible high-priority block should be kept
        assert any(b.priority == 0.9 for b in result)


class TestFitToBudget:
    def test_fits_all(self):
        cc = ContextCompactor(MagicMock())
        blocks = [_make_block(tokens=50), _make_block(tokens=50)]
        result = cc._fit_to_budget(blocks, 200)
        assert len(result) == 2

    def test_partial_fit(self):
        cc = ContextCompactor(MagicMock())
        blocks = [_make_block(tokens=60), _make_block(tokens=60)]
        result = cc._fit_to_budget(blocks, 100)
        assert len(result) == 1

    def test_nothing_fits(self):
        cc = ContextCompactor(MagicMock())
        blocks = [_make_block(tokens=200)]
        result = cc._fit_to_budget(blocks, 50)
        assert len(result) == 0


class TestLightCompact:
    def test_removes_extra_blank_lines(self):
        counter = MagicMock()
        counter.count_messages.return_value = 10
        cc = ContextCompactor(counter)
        block = _make_block(content="line1\n\n\n\nline2", tokens=100)
        result = cc._light_compact(block, 50)
        assert result is not None
        assert "\n\n\n" not in result.content

    def test_returns_none_when_truncation_fails(self):
        counter = MagicMock()
        counter.count_messages.return_value = 999  # always over budget
        cc = ContextCompactor(counter)
        block = _make_block(content="x", tokens=100)
        result = cc._light_compact(block, 5)
        assert result is None


class TestTruncateToBudget:
    def test_zero_budget(self):
        cc = ContextCompactor(MagicMock())
        block = _make_block(content="hello")
        result = cc._truncate_to_budget(block, "hello", 0)
        assert result is None

    def test_truncation_works(self):
        counter = MagicMock()
        # Return token count proportional to content length
        counter.count_messages.side_effect = lambda msgs: len(msgs[0]["content"])
        cc = ContextCompactor(counter)
        block = _make_block(content="a" * 100, tokens=100)
        result = cc._truncate_to_budget(block, "a" * 100, 50)
        assert result is not None
        assert result.token_count <= 50


class TestMediumCompact:
    async def test_with_summarizer(self):
        counter = MagicMock()
        counter.count_messages.return_value = 20
        # Make it awaitable

        async def async_summarizer(text):
            return "summary"

        cc = ContextCompactor(counter, summarizer=async_summarizer)
        block = _make_block(content="long content " * 50, tokens=200)
        result = await cc._medium_compact(block, 50)
        assert result is not None
        assert result.content == "summary"

    async def test_without_summarizer_falls_back(self):
        counter = MagicMock()
        counter.count_messages.return_value = 10
        cc = ContextCompactor(counter, summarizer=None)
        block = _make_block(content="line1\n\n\n\nline2", tokens=200)
        result = await cc._medium_compact(block, 50)
        assert result is not None

    async def test_summarizer_error_falls_back(self):
        counter = MagicMock()
        counter.count_messages.return_value = 10

        async def bad_summarizer(text):
            raise RuntimeError("fail")

        cc = ContextCompactor(counter, summarizer=bad_summarizer)
        block = _make_block(content="content", tokens=200)
        result = await cc._medium_compact(block, 50)
        # Should fall back to light compact
        assert result is not None


class TestAggressiveCompact:
    async def test_aggressive_tries_medium_first(self):
        counter = MagicMock()
        counter.count_messages.return_value = 10

        async def summarizer(text):
            return "short"

        cc = ContextCompactor(counter, summarizer=summarizer)
        block = _make_block(content="very long content " * 100, tokens=500)
        result = await cc._aggressive_compact(block, 50)
        assert result is not None


# ============ ContextBlock ============


class TestContextBlock:
    def test_basic_creation(self):
        b = ContextBlock(
            content="hello", role="system", token_count=5, priority=0.5, source="L1"
        )
        assert b.content == "hello"
        assert b.compressible is True

    def test_negative_tokens_raises(self):
        with pytest.raises(ValueError):
            ContextBlock(content="x", role="system", token_count=-1, priority=0.5, source="L1")

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError):
            ContextBlock(content="x", role="system", token_count=1, priority=1.5, source="L1")

    def test_to_message(self):
        b = _make_block(content="hello")
        msg = b.to_message()
        assert msg == {"role": "system", "content": "hello"}

    def test_with_priority(self):
        b = _make_block(priority=0.5)
        b2 = b.with_priority(0.9)
        assert b2.priority == 0.9
        assert b.priority == 0.5  # original unchanged

    def test_with_content(self):
        b = _make_block(content="old", tokens=100)
        b2 = b.with_content("new", 50)
        assert b2.content == "new"
        assert b2.token_count == 50
        assert b.content == "old"  # original unchanged
