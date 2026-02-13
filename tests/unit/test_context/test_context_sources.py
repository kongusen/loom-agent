"""
Tests for loom/context/sources/ - ToolSource, SkillSource, RAGKnowledgeSource, L3PersistentSource
"""

from unittest.mock import AsyncMock, MagicMock

from loom.context.block import ContextBlock
from loom.context.sources.memory import L3PersistentSource
from loom.context.sources.rag import RAGKnowledgeSource
from loom.context.sources.skill import SkillSource
from loom.context.sources.tool import ToolSource


def _mock_token_counter(tokens_per_call: int = 10):
    counter = MagicMock()
    counter.count_messages = MagicMock(return_value=tokens_per_call)
    return counter


# ==================== ToolSource ====================


class TestToolSourceInit:
    def test_defaults(self):
        src = ToolSource()
        assert src.source_name == "tools"
        assert src._tool_manager is None
        assert src._tool_registry is None

    def test_with_manager(self):
        mgr = MagicMock()
        src = ToolSource(tool_manager=mgr)
        assert src._tool_manager is mgr


class TestToolSourceGetDefinitions:
    def test_empty_when_no_sources(self):
        src = ToolSource()
        assert src._get_tool_definitions() == []

    def test_from_tool_manager(self):
        tool = MagicMock()
        tool.name = "bash"
        tool.description = "Run commands"
        tool.input_schema = {"type": "object"}
        mgr = MagicMock()
        mgr.list_tools.return_value = [tool]
        src = ToolSource(tool_manager=mgr)
        defs = src._get_tool_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "bash"

    def test_from_tool_registry(self):
        defn = MagicMock()
        defn.name = "search"
        defn.description = "Search files"
        defn.input_schema = {}
        registry = MagicMock()
        registry.definitions = [defn]
        src = ToolSource(tool_registry=registry)
        defs = src._get_tool_definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "search"

    def test_manager_exception_swallowed(self):
        mgr = MagicMock()
        mgr.list_tools.side_effect = RuntimeError("fail")
        src = ToolSource(tool_manager=mgr)
        assert src._get_tool_definitions() == []


class TestToolSourceToolToContent:
    def test_basic(self):
        src = ToolSource()
        content = src._tool_to_content({"name": "bash", "description": "Run cmd", "input_schema": {}})
        assert "Tool: bash" in content
        assert "Description: Run cmd" in content

    def test_with_params(self):
        src = ToolSource()
        content = src._tool_to_content({
            "name": "search",
            "description": "Search",
            "input_schema": {
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}
            },
        })
        assert "query: string" in content
        assert "limit: integer" in content

    def test_empty_tool(self):
        src = ToolSource()
        content = src._tool_to_content({})
        assert "Tool: unknown" in content


class TestToolSourceIsRelevant:
    def test_empty_query_always_relevant(self):
        src = ToolSource()
        is_rel, score = src._is_relevant({"name": "bash"}, "", 0.5)
        assert is_rel is True

    def test_matching_keyword(self):
        src = ToolSource()
        is_rel, score = src._is_relevant(
            {"name": "file_search", "description": "Search files on disk"},
            "search files",
            0.5,
        )
        assert is_rel is True
        assert score >= 0.5

    def test_no_match(self):
        src = ToolSource()
        is_rel, score = src._is_relevant(
            {"name": "bash", "description": "Run shell commands"},
            "database query optimization",
            0.8,
        )
        # With high threshold and no keyword overlap, should be not relevant
        assert is_rel is False or score < 0.8


class TestToolSourceCollect:
    async def test_empty_tools(self):
        src = ToolSource()
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_collects_tools(self):
        tool = MagicMock()
        tool.name = "bash"
        tool.description = "Run commands"
        tool.input_schema = {}
        mgr = MagicMock()
        mgr.list_tools.return_value = [tool]
        src = ToolSource(tool_manager=mgr)
        blocks = await src.collect("run commands", 1000, _mock_token_counter())
        assert len(blocks) >= 1
        assert isinstance(blocks[0], ContextBlock)
        assert blocks[0].source == "tools"

    async def test_respects_budget(self):
        tools = []
        for i in range(5):
            t = MagicMock()
            t.name = f"tool_{i}"
            t.description = f"Tool {i} description"
            t.input_schema = {}
            tools.append(t)
        mgr = MagicMock()
        mgr.list_tools.return_value = tools
        src = ToolSource(tool_manager=mgr)
        # Budget of 25 tokens, each tool costs 10 → max 2 tools
        blocks = await src.collect("", 25, _mock_token_counter(10))
        assert len(blocks) <= 2

    async def test_filters_irrelevant(self):
        tool = MagicMock()
        tool.name = "xyz_obscure"
        tool.description = "Does something obscure"
        tool.input_schema = {}
        mgr = MagicMock()
        mgr.list_tools.return_value = [tool]
        src = ToolSource(tool_manager=mgr)
        blocks = await src.collect("database query", 1000, _mock_token_counter(), min_relevance=0.9)
        # With very high threshold, obscure tool should be filtered
        assert len(blocks) == 0


# ==================== SkillSource ====================


class TestSkillSourceInit:
    def test_defaults(self):
        src = SkillSource()
        assert src.source_name == "skills"
        assert src._active_skill_ids == []

    def test_with_active_skills(self):
        src = SkillSource(active_skill_ids=["s1", "s2"])
        assert src._active_skill_ids == ["s1", "s2"]


class TestSkillSourceActivation:
    def test_activate(self):
        src = SkillSource()
        src.activate_skill("s1")
        assert "s1" in src._active_skill_ids

    def test_activate_idempotent(self):
        src = SkillSource()
        src.activate_skill("s1")
        src.activate_skill("s1")
        assert src._active_skill_ids.count("s1") == 1

    def test_deactivate(self):
        src = SkillSource(active_skill_ids=["s1", "s2"])
        src.deactivate_skill("s1")
        assert "s1" not in src._active_skill_ids
        assert "s2" in src._active_skill_ids

    def test_deactivate_missing_noop(self):
        src = SkillSource()
        src.deactivate_skill("nonexistent")  # should not raise

    def test_set_active_skills(self):
        src = SkillSource(active_skill_ids=["old"])
        src.set_active_skills(["new1", "new2"])
        assert src._active_skill_ids == ["new1", "new2"]


class TestSkillSourceGetContent:
    async def test_no_registry(self):
        src = SkillSource()
        result = await src._get_skill_content("s1")
        assert result is None

    async def test_sync_get_skill(self):
        skill_def = MagicMock()
        skill_def.instructions = "Do X then Y"
        del skill_def.get_full_instructions  # ensure it falls to instructions
        registry = MagicMock()
        registry.get_skill = MagicMock(return_value=skill_def)
        src = SkillSource(skill_registry=registry)
        result = await src._get_skill_content("s1")
        assert result == "Do X then Y"

    async def test_async_get_skill(self):
        skill_def = MagicMock()
        skill_def.get_full_instructions = MagicMock(return_value="Full instructions here")
        registry = MagicMock()
        registry.get_skill = AsyncMock(return_value=skill_def)
        src = SkillSource(skill_registry=registry)
        result = await src._get_skill_content("s1")
        assert result == "Full instructions here"

    async def test_skill_not_found(self):
        registry = MagicMock()
        registry.get_skill = MagicMock(return_value=None)
        src = SkillSource(skill_registry=registry)
        result = await src._get_skill_content("missing")
        assert result is None

    async def test_exception_returns_none(self):
        registry = MagicMock()
        registry.get_skill = MagicMock(side_effect=RuntimeError("fail"))
        src = SkillSource(skill_registry=registry)
        result = await src._get_skill_content("s1")
        assert result is None


class TestSkillSourceCollect:
    async def test_no_active_skills(self):
        src = SkillSource()
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_collects_active_skills(self):
        skill_def = MagicMock()
        skill_def.instructions = "Skill content"
        del skill_def.get_full_instructions
        registry = MagicMock()
        registry.get_skill = MagicMock(return_value=skill_def)
        src = SkillSource(skill_registry=registry, active_skill_ids=["s1"])
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert len(blocks) == 1
        assert blocks[0].source == "skills"
        assert blocks[0].priority == 0.85

    async def test_respects_budget(self):
        skill_def = MagicMock()
        skill_def.instructions = "Content"
        del skill_def.get_full_instructions
        registry = MagicMock()
        registry.get_skill = MagicMock(return_value=skill_def)
        src = SkillSource(skill_registry=registry, active_skill_ids=["s1", "s2", "s3"])
        # Budget 15, each skill costs 10 → max 1
        blocks = await src.collect("query", 15, _mock_token_counter(10))
        assert len(blocks) == 1

    async def test_skips_none_content(self):
        registry = MagicMock()
        registry.get_skill = MagicMock(return_value=None)
        src = SkillSource(skill_registry=registry, active_skill_ids=["s1"])
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []


# ==================== RAGKnowledgeSource ====================


class TestRAGKnowledgeSourceInit:
    def test_defaults(self):
        kb = MagicMock()
        src = RAGKnowledgeSource(knowledge_base=kb)
        assert src.source_name == "RAG_knowledge"
        assert src.relevance_threshold == 0.7


class TestRAGKnowledgeSourceCollect:
    async def test_empty_query(self):
        kb = MagicMock()
        src = RAGKnowledgeSource(knowledge_base=kb)
        blocks = await src.collect("", 1000, _mock_token_counter())
        assert blocks == []

    async def test_query_returns_items(self):
        item = MagicMock()
        item.relevance = 0.9
        item.source = "docs"
        item.content = "Important knowledge"
        item.id = "k1"
        kb = MagicMock()
        kb.query = AsyncMock(return_value=[item])
        src = RAGKnowledgeSource(knowledge_base=kb, relevance_threshold=0.5)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert len(blocks) == 1
        assert "[Knowledge: docs]" in blocks[0].content
        assert blocks[0].priority == 0.9

    async def test_filters_low_relevance(self):
        item = MagicMock()
        item.relevance = 0.3
        item.source = "docs"
        item.content = "Low relevance"
        item.id = "k1"
        kb = MagicMock()
        kb.query = AsyncMock(return_value=[item])
        src = RAGKnowledgeSource(knowledge_base=kb, relevance_threshold=0.7)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_uses_stricter_threshold(self):
        item = MagicMock()
        item.relevance = 0.6
        item.source = "docs"
        item.content = "Medium relevance"
        item.id = "k1"
        kb = MagicMock()
        kb.query = AsyncMock(return_value=[item])
        # relevance_threshold=0.7 > min_relevance=0.5 → uses 0.7
        src = RAGKnowledgeSource(knowledge_base=kb, relevance_threshold=0.7)
        blocks = await src.collect("query", 1000, _mock_token_counter(), min_relevance=0.5)
        assert blocks == []

    async def test_query_exception_returns_empty(self):
        kb = MagicMock()
        kb.query = AsyncMock(side_effect=RuntimeError("fail"))
        src = RAGKnowledgeSource(knowledge_base=kb)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_respects_budget(self):
        items = []
        for i in range(5):
            item = MagicMock()
            item.relevance = 0.9
            item.source = "docs"
            item.content = f"Item {i}"
            item.id = f"k{i}"
            items.append(item)
        kb = MagicMock()
        kb.query = AsyncMock(return_value=items)
        src = RAGKnowledgeSource(knowledge_base=kb, relevance_threshold=0.5)
        blocks = await src.collect("query", 25, _mock_token_counter(10))
        assert len(blocks) <= 2

    async def test_empty_results(self):
        kb = MagicMock()
        kb.query = AsyncMock(return_value=[])
        src = RAGKnowledgeSource(knowledge_base=kb)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []


# ==================== L3PersistentSource (now L3PersistentSource) ====================


class TestL3PersistentSourceInit:
    def test_basic(self):
        mem = MagicMock()
        src = L3PersistentSource(memory=mem)
        assert src.source_name == "L3_persistent"
        assert src.session_id is None

    def test_with_session(self):
        mem = MagicMock()
        src = L3PersistentSource(memory=mem, session_id="sess1")
        assert src.session_id == "sess1"


class TestL3PersistentSourceCollect:
    async def test_empty_query(self):
        mem = MagicMock()
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("", 1000, _mock_token_counter())
        assert blocks == []

    async def test_no_l3_store(self):
        mem = MagicMock()
        mem.l3 = None
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_search_returns_results(self):
        record = MagicMock()
        record.content = "Relevant fact"
        record.importance = 0.85
        record.record_id = "r1"
        record.tags = []
        record.session_id = None
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(return_value=[record])
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert len(blocks) == 1
        assert "[Persistent Memory]" in blocks[0].content
        assert blocks[0].priority == 0.85

    async def test_filters_low_importance(self):
        record = MagicMock()
        record.content = "Low importance"
        record.importance = 0.2
        record.record_id = "r1"
        record.tags = []
        record.session_id = None
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(return_value=[record])
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter(), min_relevance=0.5)
        assert blocks == []

    async def test_search_exception_returns_empty(self):
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(side_effect=RuntimeError("fail"))
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_skips_empty_content(self):
        record = MagicMock()
        record.content = ""
        record.importance = 0.9
        record.record_id = "r1"
        record.tags = []
        record.session_id = None
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(return_value=[record])
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert blocks == []

    async def test_respects_budget(self):
        records = []
        for i in range(5):
            r = MagicMock()
            r.content = f"Fact {i}"
            r.importance = 0.9
            r.record_id = f"r{i}"
            r.tags = []
            r.session_id = None
            records.append(r)
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(return_value=records)
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 25, _mock_token_counter(10))
        assert len(blocks) <= 2

    async def test_priority_clamped(self):
        record = MagicMock()
        record.content = "High"
        record.importance = 1.5  # above 1.0
        record.record_id = "r1"
        record.tags = []
        record.session_id = None
        mem = MagicMock()
        mem.l3 = MagicMock()
        mem.search_persistent = AsyncMock(return_value=[record])
        src = L3PersistentSource(memory=mem)
        blocks = await src.collect("query", 1000, _mock_token_counter())
        assert len(blocks) == 1
        assert blocks[0].priority == 1.0
