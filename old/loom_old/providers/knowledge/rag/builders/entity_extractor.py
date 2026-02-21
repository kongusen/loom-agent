"""
实体抽取器
"""

import json
import logging
import uuid
from abc import ABC, abstractmethod

from loom.providers.knowledge.rag.models.chunk import TextChunk
from loom.providers.knowledge.rag.models.entity import Entity
from loom.providers.knowledge.rag.models.relation import Relation

logger = logging.getLogger(__name__)


class EntityExtractor(ABC):
    """实体抽取器抽象接口"""

    @abstractmethod
    async def extract(
        self,
        chunk: TextChunk,
    ) -> tuple[list[Entity], list[Relation]]:
        """
        从文本块中抽取实体和关系

        Args:
            chunk: 文本块

        Returns:
            (entities, relations) 元组
        """
        pass


class LLMEntityExtractor(EntityExtractor):
    """
    LLM 驱动的实体/关系提取器

    使用 Agent 的 LLM provider，通过结构化 prompt 提取实体和关系。
    用户通过 ExtractionConfig 配置提取方向（Skill 模式）。
    """

    def __init__(
        self,
        llm_provider,
        config=None,
    ):
        """
        Args:
            llm_provider: LLMProvider 实例（从 Agent 共享）
            config: ExtractionConfig 提取配置
        """
        from loom.providers.knowledge.rag.config import ExtractionConfig

        self._llm = llm_provider
        self._config = config or ExtractionConfig()

    async def extract(
        self,
        chunk: TextChunk,
    ) -> tuple[list[Entity], list[Relation]]:
        """使用 LLM 提取实体和关系"""
        if not self._config.enabled:
            return [], []

        prompt = self._build_extraction_prompt(chunk)
        try:
            response = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2000,
            )
            return self._parse_response(response.content, chunk)
        except Exception:
            logger.warning("LLM entity extraction failed for chunk %s", chunk.id, exc_info=True)
            return [], []

    def _build_extraction_prompt(self, chunk: TextChunk) -> str:
        """构建提取 prompt"""
        cfg = self._config

        entity_types_str = ", ".join(cfg.entity_types)
        relation_types_str = ", ".join(cfg.relation_types)

        hints_section = ""
        if cfg.hints:
            hints_section = f"\n领域提示：{cfg.hints}\n"

        return f"""从以下文本中提取实体和关系。

允许的实体类型：{entity_types_str}
允许的关系类型：{relation_types_str}
{hints_section}
约束：
- 最多提取 {cfg.max_entities_per_chunk} 个实体
- 最多提取 {cfg.max_relations_per_chunk} 个关系
- 关系的 source 和 target 必须是提取出的实体 text

请严格按以下 JSON 格式输出，不要输出其他内容：
{{"entities": [{{"text": "实体名", "type": "实体类型", "description": "简短描述"}}], "relations": [{{"source": "源实体名", "target": "目标实体名", "type": "关系类型", "description": "简短描述"}}]}}

文本：
{chunk.content}"""

    def _parse_response(
        self, content: str, chunk: TextChunk
    ) -> tuple[list[Entity], list[Relation]]:
        """解析 LLM 输出的 JSON 为 Entity/Relation 对象"""
        try:
            # 尝试提取 JSON（LLM 可能包裹在 markdown code block 中）
            text = content.strip()
            if text.startswith("```"):
                # 去掉 ```json ... ``` 包裹
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            logger.debug("Failed to parse LLM extraction response as JSON")
            return [], []

        entities = []
        raw_entities = data.get("entities", [])
        for item in raw_entities[: self._config.max_entities_per_chunk]:
            if not isinstance(item, dict) or "text" not in item:
                continue
            entity_id = f"entity_{uuid.uuid4().hex[:8]}"
            entities.append(
                Entity(
                    id=entity_id,
                    text=item["text"],
                    entity_type=item.get("type", "CONCEPT"),
                    chunk_ids=[chunk.id],
                    metadata={"description": item.get("description", "")},
                )
            )

        # 构建 text → entity_id 映射，用于关系解析
        text_to_id = {e.text: e.id for e in entities}

        relations = []
        raw_relations = data.get("relations", [])
        for item in raw_relations[: self._config.max_relations_per_chunk]:
            if not isinstance(item, dict):
                continue
            source_text = item.get("source", "")
            target_text = item.get("target", "")
            source_id = text_to_id.get(source_text)
            target_id = text_to_id.get(target_text)
            if not source_id or not target_id:
                continue  # 跳过引用不存在实体的关系
            relations.append(
                Relation(
                    id=f"rel_{uuid.uuid4().hex[:8]}",
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=item.get("type", "RELATED_TO"),
                    metadata={"description": item.get("description", "")},
                )
            )

        return entities, relations
