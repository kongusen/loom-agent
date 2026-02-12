"""
LLMEntityExtractor 单元测试
"""

import json
from unittest.mock import AsyncMock, Mock

import pytest

from loom.providers.knowledge.rag.builders.entity_extractor import LLMEntityExtractor
from loom.providers.knowledge.rag.config import ExtractionConfig
from loom.providers.knowledge.rag.models.chunk import TextChunk


def _make_chunk(content: str = "Test content", chunk_id: str = "chunk_1") -> TextChunk:
    return TextChunk(id=chunk_id, content=content, document_id="doc_1")


def _mock_llm(response_content: str):
    llm = Mock()
    resp = Mock()
    resp.content = response_content
    llm.chat = AsyncMock(return_value=resp)
    return llm


class TestLLMEntityExtractorInit:
    def test_default_config(self):
        llm = Mock()
        extractor = LLMEntityExtractor(llm)
        assert extractor._config.enabled is True
        assert "CONCEPT" in extractor._config.entity_types

    def test_custom_config(self):
        llm = Mock()
        cfg = ExtractionConfig(entity_types=["PERSON"], enabled=False)
        extractor = LLMEntityExtractor(llm, config=cfg)
        assert extractor._config.entity_types == ["PERSON"]
        assert extractor._config.enabled is False


class TestLLMEntityExtractorExtract:
    @pytest.mark.asyncio
    async def test_extract_entities_from_chunk(self):
        """mock LLM 返回 JSON，验证解析"""
        response = json.dumps({
            "entities": [
                {"text": "GraphRAG", "type": "CONCEPT", "description": "图增强检索"},
                {"text": "VectorStore", "type": "TOOL", "description": "向量存储"},
            ],
            "relations": [
                {
                    "source": "GraphRAG",
                    "target": "VectorStore",
                    "type": "USES",
                    "description": "GraphRAG 使用 VectorStore",
                },
            ],
        })
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm)
        chunk = _make_chunk("GraphRAG uses VectorStore for retrieval")

        entities, relations = await extractor.extract(chunk)

        assert len(entities) == 2
        assert entities[0].text == "GraphRAG"
        assert entities[0].entity_type == "CONCEPT"
        assert entities[0].chunk_ids == ["chunk_1"]
        assert entities[1].text == "VectorStore"

    @pytest.mark.asyncio
    async def test_extract_relations_from_chunk(self):
        """验证关系提取"""
        response = json.dumps({
            "entities": [
                {"text": "Agent", "type": "CONCEPT"},
                {"text": "LLM", "type": "TOOL"},
            ],
            "relations": [
                {"source": "Agent", "target": "LLM", "type": "DEPENDS_ON"},
            ],
        })
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm)

        entities, relations = await extractor.extract(_make_chunk())

        assert len(relations) == 1
        assert relations[0].relation_type == "DEPENDS_ON"
        # source_id 和 target_id 应该对应实体的 id
        entity_ids = {e.text: e.id for e in entities}
        assert relations[0].source_id == entity_ids["Agent"]
        assert relations[0].target_id == entity_ids["LLM"]

    @pytest.mark.asyncio
    async def test_extraction_config_applied(self):
        """验证 entity_types/relation_types 出现在 prompt 中"""
        cfg = ExtractionConfig(
            entity_types=["PERSON", "ORG"],
            relation_types=["WORKS_FOR"],
        )
        llm = _mock_llm(json.dumps({"entities": [], "relations": []}))
        extractor = LLMEntityExtractor(llm, config=cfg)

        await extractor.extract(_make_chunk())

        call_args = llm.chat.call_args
        prompt = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0][0]["content"]
        assert "PERSON" in prompt
        assert "ORG" in prompt
        assert "WORKS_FOR" in prompt

    @pytest.mark.asyncio
    async def test_hints_in_prompt(self):
        """验证 hints 出现在 prompt 中"""
        cfg = ExtractionConfig(hints="关注技术架构和API设计模式")
        llm = _mock_llm(json.dumps({"entities": [], "relations": []}))
        extractor = LLMEntityExtractor(llm, config=cfg)

        await extractor.extract(_make_chunk())

        call_args = llm.chat.call_args
        prompt = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0][0]["content"]
        assert "关注技术架构和API设计模式" in prompt

    @pytest.mark.asyncio
    async def test_malformed_json_returns_empty(self):
        """LLM 返回非 JSON 时容错"""
        llm = _mock_llm("This is not valid JSON at all")
        extractor = LLMEntityExtractor(llm)

        entities, relations = await extractor.extract(_make_chunk())

        assert entities == []
        assert relations == []

    @pytest.mark.asyncio
    async def test_extraction_disabled(self):
        """config.enabled=False 时跳过"""
        cfg = ExtractionConfig(enabled=False)
        llm = Mock()
        extractor = LLMEntityExtractor(llm, config=cfg)

        entities, relations = await extractor.extract(_make_chunk())

        assert entities == []
        assert relations == []
        llm.chat.assert_not_called()

    @pytest.mark.asyncio
    async def test_max_entities_respected(self):
        """超过 max 时截断"""
        many_entities = [{"text": f"Entity{i}", "type": "CONCEPT"} for i in range(20)]
        response = json.dumps({"entities": many_entities, "relations": []})
        cfg = ExtractionConfig(max_entities_per_chunk=5)
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm, config=cfg)

        entities, relations = await extractor.extract(_make_chunk())

        assert len(entities) == 5

    @pytest.mark.asyncio
    async def test_max_relations_respected(self):
        """超过 max_relations 时截断"""
        entities_data = [
            {"text": "A", "type": "CONCEPT"},
            {"text": "B", "type": "CONCEPT"},
        ]
        many_relations = [
            {"source": "A", "target": "B", "type": "USES"} for _ in range(20)
        ]
        response = json.dumps({"entities": entities_data, "relations": many_relations})
        cfg = ExtractionConfig(max_relations_per_chunk=3)
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm, config=cfg)

        entities, relations = await extractor.extract(_make_chunk())

        assert len(relations) == 3

    @pytest.mark.asyncio
    async def test_relation_with_missing_entity_skipped(self):
        """关系引用不存在的实体时跳过"""
        response = json.dumps({
            "entities": [{"text": "A", "type": "CONCEPT"}],
            "relations": [
                {"source": "A", "target": "NonExistent", "type": "USES"},
            ],
        })
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm)

        entities, relations = await extractor.extract(_make_chunk())

        assert len(entities) == 1
        assert len(relations) == 0  # 跳过了引用不存在实体的关系

    @pytest.mark.asyncio
    async def test_markdown_code_block_json(self):
        """LLM 返回 markdown code block 包裹的 JSON"""
        inner = json.dumps({
            "entities": [{"text": "Test", "type": "CONCEPT"}],
            "relations": [],
        })
        response = f"```json\n{inner}\n```"
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm)

        entities, relations = await extractor.extract(_make_chunk())

        assert len(entities) == 1
        assert entities[0].text == "Test"

    @pytest.mark.asyncio
    async def test_llm_exception_returns_empty(self):
        """LLM 调用异常时容错返回空"""
        llm = Mock()
        llm.chat = AsyncMock(side_effect=RuntimeError("API error"))
        extractor = LLMEntityExtractor(llm)

        entities, relations = await extractor.extract(_make_chunk())

        assert entities == []
        assert relations == []

    @pytest.mark.asyncio
    async def test_entity_metadata_has_description(self):
        """实体 metadata 包含 description"""
        response = json.dumps({
            "entities": [{"text": "Agent", "type": "CONCEPT", "description": "智能代理"}],
            "relations": [],
        })
        llm = _mock_llm(response)
        extractor = LLMEntityExtractor(llm)

        entities, _ = await extractor.extract(_make_chunk())

        assert entities[0].metadata["description"] == "智能代理"
