"""
Tests for loom/config/context.py - BudgetConfig and ContextConfig with field validators.
"""

import pytest

from loom.config.context import BudgetConfig, ContextConfig
from loom.config.memory import MemoryConfig
from loom.memory.compaction import CompactionConfig
from loom.providers.knowledge.base import KnowledgeBaseProvider
from loom.runtime.session_lane import SessionIsolationMode

# Resolve forward references so pydantic can fully validate the models.
# MemoryConfig has a TYPE_CHECKING forward ref to KnowledgeBaseProvider,
# and ContextConfig has one to CompactionConfig.
MemoryConfig.model_rebuild(
    _types_namespace={"KnowledgeBaseProvider": KnowledgeBaseProvider}
)
ContextConfig.model_rebuild(
    _types_namespace={"CompactionConfig": CompactionConfig}
)


# ============ BudgetConfig ============


class TestBudgetConfig:
    def test_defaults(self):
        bc = BudgetConfig()
        assert bc.l1_ratio == 0.25
        assert bc.l2_ratio == 0.20
        assert bc.l3_l4_ratio == 0.30
        assert bc.rag_ratio == 0.15
        assert bc.inherited_ratio == 0.10

    def test_custom_values(self):
        bc = BudgetConfig(
            l1_ratio=0.40,
            l2_ratio=0.10,
            l3_l4_ratio=0.20,
            rag_ratio=0.20,
            inherited_ratio=0.10,
        )
        assert bc.l1_ratio == 0.40
        assert bc.l2_ratio == 0.10
        assert bc.l3_l4_ratio == 0.20
        assert bc.rag_ratio == 0.20
        assert bc.inherited_ratio == 0.10

    def test_partial_override(self):
        bc = BudgetConfig(l1_ratio=0.50)
        assert bc.l1_ratio == 0.50
        # remaining fields keep defaults
        assert bc.l2_ratio == 0.20
        assert bc.l3_l4_ratio == 0.30


# ============ ContextConfig defaults ============


class TestContextConfigDefaults:
    def test_all_defaults(self):
        cfg = ContextConfig()
        assert cfg.memory is None
        assert cfg.budget is None
        assert cfg.compaction is None
        assert cfg.session_isolation == SessionIsolationMode.STRICT


# ============ _coerce_memory ============


class TestCoerceMemory:
    def test_none_passthrough(self):
        cfg = ContextConfig(memory=None)
        assert cfg.memory is None

    def test_memory_config_instance(self):
        mc = MemoryConfig()
        cfg = ContextConfig(memory=mc)
        assert cfg.memory is mc

    def test_dict_coerced_to_memory_config(self):
        cfg = ContextConfig(memory={"enable_compression": False})
        assert isinstance(cfg.memory, MemoryConfig)
        assert cfg.memory.enable_compression is False

    def test_empty_dict_coerced(self):
        cfg = ContextConfig(memory={})
        assert isinstance(cfg.memory, MemoryConfig)

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(memory=42)

    def test_invalid_type_string_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(memory="bad")


# ============ _coerce_budget ============


class TestCoerceBudget:
    def test_none_passthrough(self):
        cfg = ContextConfig(budget=None)
        assert cfg.budget is None

    def test_budget_config_instance(self):
        bc = BudgetConfig(l1_ratio=0.50)
        cfg = ContextConfig(budget=bc)
        assert cfg.budget is bc
        assert cfg.budget.l1_ratio == 0.50

    def test_dict_coerced_to_budget_config(self):
        cfg = ContextConfig(budget={"l1_ratio": 0.60, "l2_ratio": 0.10})
        assert isinstance(cfg.budget, BudgetConfig)
        assert cfg.budget.l1_ratio == 0.60
        assert cfg.budget.l2_ratio == 0.10
        # unset fields keep defaults
        assert cfg.budget.rag_ratio == 0.15

    def test_empty_dict_coerced(self):
        cfg = ContextConfig(budget={})
        assert isinstance(cfg.budget, BudgetConfig)
        assert cfg.budget.l1_ratio == 0.25

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(budget=123)

    def test_invalid_type_list_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(budget=[1, 2, 3])


# ============ _coerce_compaction ============


class TestCoerceCompaction:
    def test_none_passthrough(self):
        cfg = ContextConfig(compaction=None)
        assert cfg.compaction is None

    def test_compaction_config_instance(self):
        cc = CompactionConfig(enabled=False, threshold=0.90)
        cfg = ContextConfig(compaction=cc)
        assert cfg.compaction is cc
        assert cfg.compaction.enabled is False
        assert cfg.compaction.threshold == 0.90

    def test_dict_coerced_to_compaction_config(self):
        cfg = ContextConfig(compaction={"enabled": True, "threshold": 0.75})
        assert isinstance(cfg.compaction, CompactionConfig)
        assert cfg.compaction.enabled is True
        assert cfg.compaction.threshold == 0.75

    def test_empty_dict_coerced(self):
        cfg = ContextConfig(compaction={})
        assert isinstance(cfg.compaction, CompactionConfig)
        # defaults from CompactionConfig
        assert cfg.compaction.enabled is True
        assert cfg.compaction.strategy == "silent"

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(compaction=99)

    def test_invalid_type_string_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(compaction="none")


# ============ _coerce_session_isolation ============


class TestCoerceSessionIsolation:
    def test_enum_instance(self):
        cfg = ContextConfig(session_isolation=SessionIsolationMode.ADVISORY)
        assert cfg.session_isolation == SessionIsolationMode.ADVISORY

    def test_string_strict(self):
        cfg = ContextConfig(session_isolation="strict")
        assert cfg.session_isolation == SessionIsolationMode.STRICT

    def test_string_advisory(self):
        cfg = ContextConfig(session_isolation="advisory")
        assert cfg.session_isolation == SessionIsolationMode.ADVISORY

    def test_string_none_mode(self):
        cfg = ContextConfig(session_isolation="none")
        assert cfg.session_isolation == SessionIsolationMode.NONE

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            ContextConfig(session_isolation=42)

    def test_invalid_string_raises(self):
        with pytest.raises((TypeError, ValueError)):
            ContextConfig(session_isolation="invalid_mode")


# ============ Combined construction ============


class TestContextConfigCombined:
    def test_all_fields_from_dicts(self):
        cfg = ContextConfig(
            memory={"enable_compression": True},
            budget={"l1_ratio": 0.30},
            compaction={"enabled": False},
            session_isolation="advisory",
        )
        assert isinstance(cfg.memory, MemoryConfig)
        assert isinstance(cfg.budget, BudgetConfig)
        assert isinstance(cfg.compaction, CompactionConfig)
        assert cfg.session_isolation == SessionIsolationMode.ADVISORY
        assert cfg.budget.l1_ratio == 0.30
        assert cfg.compaction.enabled is False

    def test_all_fields_from_instances(self):
        mc = MemoryConfig()
        bc = BudgetConfig()
        cc = CompactionConfig()
        cfg = ContextConfig(
            memory=mc,
            budget=bc,
            compaction=cc,
            session_isolation=SessionIsolationMode.NONE,
        )
        assert cfg.memory is mc
        assert cfg.budget is bc
        assert cfg.compaction is cc
        assert cfg.session_isolation == SessionIsolationMode.NONE
