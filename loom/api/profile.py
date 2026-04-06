"""Agent profile configuration"""

import ast
from dataclasses import dataclass, field
from pathlib import Path

from .config import AgentConfig, LLMConfig, PolicyConfig, ToolConfig


@dataclass
class AgentProfile:
    """Agent capability profile"""
    id: str
    name: str
    config: AgentConfig
    skills: list[str] = field(default_factory=list)
    knowledge_sources: list[str] = field(default_factory=list)

    @classmethod
    def from_preset(cls, preset: str) -> "AgentProfile":
        """Create from preset"""
        presets = {
            "default": cls(
                id="default",
                name="Default Agent",
                config=AgentConfig(name="default")
            ),
            "coding": cls(
                id="coding",
                name="Coding Assistant",
                config=AgentConfig(
                    name="coding",
                    system_prompt="You are a helpful coding assistant."
                ),
                skills=["coding-core", "test-runner"]
            ),
        }
        return presets.get(preset, presets["default"])

    @classmethod
    def from_yaml(cls, path: str) -> "AgentProfile":
        """Load from YAML file"""
        data = _parse_yaml_file(path)

        config_data = data.get("config", {})
        config = AgentConfig(
            name=config_data.get("name", data.get("id", "default")),
            llm=LLMConfig(**config_data.get("llm", {})),
            tools=ToolConfig(**config_data.get("tools", {})),
            policy=PolicyConfig(**config_data.get("policy", {})),
            system_prompt=config_data.get("system_prompt", ""),
        )

        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            config=config,
            skills=data.get("skills", []),
            knowledge_sources=data.get("knowledge_sources", []),
        )


def _parse_yaml_file(path: str) -> dict:
    """Parse a minimal YAML subset without external dependencies."""
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(path)

    lines = _prepare_yaml_lines(source.read_text())
    if not lines:
        return {}

    parsed, index = _parse_block(lines, 0, 0)
    if index != len(lines):
        raise ValueError(f"Unexpected trailing YAML content in {path}")
    if not isinstance(parsed, dict):
        raise ValueError("Profile YAML root must be a mapping")
    return parsed


def _prepare_yaml_lines(text: str) -> list[tuple[int, str]]:
    """Prepare YAML lines as (indent, content) tuples."""
    prepared: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        prepared.append((indent, raw_line[indent:]))
    return prepared


def _parse_block(
    lines: list[tuple[int, str]],
    start: int,
    indent: int,
) -> tuple[dict | list, int]:
    """Parse either a mapping or a list block."""
    if start >= len(lines):
        return {}, start

    current_indent, content = lines[start]
    if current_indent != indent:
        raise ValueError(f"Invalid indentation near '{content}'")

    if content.startswith("- "):
        return _parse_list(lines, start, indent)
    return _parse_mapping(lines, start, indent)


def _parse_mapping(
    lines: list[tuple[int, str]],
    start: int,
    indent: int,
) -> tuple[dict, int]:
    """Parse a YAML mapping block."""
    result: dict = {}
    index = start
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise ValueError(f"Unexpected indentation near '{content}'")
        if content.startswith("- "):
            break

        key, sep, raw_value = content.partition(":")
        if not sep:
            raise ValueError(f"Invalid mapping line '{content}'")

        key = key.strip()
        value_text = raw_value.strip()
        index += 1

        if value_text:
            result[key] = _parse_scalar(value_text)
            continue

        if index < len(lines) and lines[index][0] > indent:
            nested_indent = lines[index][0]
            value, index = _parse_block(lines, index, nested_indent)
            result[key] = value
        else:
            result[key] = {}

    return result, index


def _parse_list(
    lines: list[tuple[int, str]],
    start: int,
    indent: int,
) -> tuple[list, int]:
    """Parse a YAML list block."""
    result: list = []
    index = start
    while index < len(lines):
        line_indent, content = lines[index]
        if line_indent < indent:
            break
        if line_indent != indent or not content.startswith("- "):
            break

        item_text = content[2:].strip()
        index += 1

        if item_text:
            result.append(_parse_scalar(item_text))
            continue

        if index < len(lines) and lines[index][0] > indent:
            nested_indent = lines[index][0]
            value, index = _parse_block(lines, index, nested_indent)
            result.append(value)
        else:
            result.append(None)

    return result, index


def _parse_scalar(value: str):
    """Parse YAML scalar values."""
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none"}:
        return None

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    if value.startswith("[") or value.startswith("{"):
        return ast.literal_eval(value)

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value
