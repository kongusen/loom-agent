"""Compile agent tool/capability declarations into runtime tool specs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .._config.tools import ToolSpec
from .capability import CapabilitySpec


@dataclass(slots=True)
class CompiledCapabilities:
    """Internal compilation result for declared tools and capabilities."""

    tool_specs: list[ToolSpec]
    activated_capabilities: list[CapabilitySpec]
    metadata: dict[str, Any] = field(default_factory=dict)


class CapabilityCompiler:
    """Compile user declarations into one governed executable tool list."""

    def compile(
        self,
        tools: list[ToolSpec],
        capabilities: list[CapabilitySpec],
    ) -> CompiledCapabilities:
        compiled_tools: list[ToolSpec] = list(tools)
        capability_tool_count = 0
        seen_names: set[str] = set()

        for tool in compiled_tools:
            if tool.name in seen_names:
                raise ValueError(f"Duplicate tool name {tool.name!r} from explicit tools")
            seen_names.add(tool.name)

        for capability in capabilities:
            capability_tools = capability.to_tools()
            for tool in capability_tools:
                if tool.name in seen_names:
                    raise ValueError(
                        f"Duplicate tool name {tool.name!r} from capability {capability.name!r}"
                    )
                seen_names.add(tool.name)
            compiled_tools.extend(capability_tools)
            capability_tool_count += len(capability_tools)

        return CompiledCapabilities(
            tool_specs=compiled_tools,
            activated_capabilities=list(capabilities),
            metadata={
                "declared_tool_count": len(tools),
                "capability_count": len(capabilities),
                "capability_tool_count": capability_tool_count,
                "total_tool_count": len(compiled_tools),
            },
        )
