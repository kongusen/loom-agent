"""Tool schema — Pydantic-based parameter validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PydanticSchema:
    """ToolSchema implementation backed by a Pydantic model."""

    def __init__(self, model: type[BaseModel]) -> None:
        self._model = model

    def parse(self, raw: Any) -> Any:
        if isinstance(raw, str):
            return self._model.model_validate_json(raw)
        return self._model.model_validate(raw)

    def to_json_schema(self) -> dict:
        return self._model.model_json_schema()


class DictSchema:
    """ToolSchema backed by a raw JSON Schema dict — for MCP tools."""

    def __init__(self, schema: dict[str, Any]) -> None:
        self._schema = schema

    def parse(self, raw: Any) -> Any:
        return raw if isinstance(raw, dict) else {}

    def to_json_schema(self) -> dict:
        return self._schema
