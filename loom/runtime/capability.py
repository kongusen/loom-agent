"""Runtime capability contracts."""

from __future__ import annotations

import builtins
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .._config.tools import Toolset, ToolSpec


class CapabilitySource(str, Enum):
    """Where a runtime capability comes from."""

    BUILTIN = "builtin"
    TOOLSET = "toolset"
    MCP = "mcp"
    SKILL = "skill"
    PLUGIN = "plugin"
    CUSTOM = "custom"


@dataclass(slots=True)
class CapabilitySpec:
    """One user-facing capability declaration.

    A capability is a source of agent abilities.  In the first SDK layer it
    compiles into existing ``ToolSpec`` entries when tools are available, while
    keeping source metadata for MCP, skills, plugins, and future discovery.
    """

    name: str
    source: CapabilitySource
    description: str = ""
    tools: list[ToolSpec | Toolset] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_tools(self) -> list[ToolSpec]:
        """Compile the executable portion of this capability to tool specs."""
        return _flatten_tool_entries(self.tools)


class RuntimeCapabilityProvider(Protocol):
    """Protocol for objects that provide capabilities to a runtime."""

    def capabilities(self) -> Iterable[CapabilitySpec]:
        ...


class Capability:
    """Factories for first-class Loom runtime capabilities."""

    @staticmethod
    def of(
        name: str,
        *entries: ToolSpec | Toolset,
        source: CapabilitySource = CapabilitySource.CUSTOM,
        description: str = "",
        metadata: dict[str, Any] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> CapabilitySpec:
        """Create a custom capability from explicit tools and metadata."""
        return CapabilitySpec(
            name=name,
            source=source,
            description=description,
            tools=list(entries),
            metadata=dict(metadata or {}),
            extensions=dict(extensions or {}),
        )

    @staticmethod
    def files(
        *,
        read_only: bool = True,
        name: str = "files",
    ) -> CapabilitySpec:
        """Create a file-system capability backed by the built-in file toolset."""
        toolset = Toolset.files(read_only=read_only, name=name)
        return CapabilitySpec(
            name=name,
            source=CapabilitySource.BUILTIN,
            description=toolset.description,
            tools=[toolset],
            metadata={"builtin": "files", "read_only": read_only},
        )

    @staticmethod
    def web(*, name: str = "web") -> CapabilitySpec:
        """Create a web research capability backed by the built-in web toolset."""
        toolset = Toolset.web(name=name)
        return CapabilitySpec(
            name=name,
            source=CapabilitySource.BUILTIN,
            description=toolset.description,
            tools=[toolset],
            metadata={"builtin": "web"},
        )

    @staticmethod
    def shell(
        *,
        require_approval: bool = True,
        name: str = "shell",
    ) -> CapabilitySpec:
        """Create a shell capability backed by the built-in shell toolset."""
        toolset = Toolset.shell(name=name)
        if not require_approval:
            toolset = replace(
                toolset,
                tools=[
                    replace(tool, requires_permission=False)
                    for tool in toolset.tools
                ],
            )
        return CapabilitySpec(
            name=name,
            source=CapabilitySource.BUILTIN,
            description=toolset.description,
            tools=[toolset],
            metadata={"builtin": "shell", "require_approval": require_approval},
        )

    @staticmethod
    def mcp(name: str | None = None, **config: Any) -> CapabilitySpec:
        """Create an MCP capability declaration.

        This first layer exposes Loom's generic MCP bridge tools and preserves
        server metadata for later registration/discovery layers.
        """
        server_name = name or "default"
        capability_name = "mcp" if name is None else f"mcp:{name}"
        toolset = Toolset.mcp(name=capability_name)
        return CapabilitySpec(
            name=capability_name,
            source=CapabilitySource.MCP,
            description=toolset.description,
            tools=[toolset],
            metadata={"server": server_name, "config": dict(config)},
        )

    @staticmethod
    def skill(name: str, **config: Any) -> CapabilitySpec:
        """Declare a skill capability without loading a skill marketplace."""
        return CapabilitySpec(
            name=f"skill:{name}",
            source=CapabilitySource.SKILL,
            description=str(config.pop("description", "")),
            metadata={"skill": name, "config": dict(config)},
        )


class CapabilityRegistry:
    """Small explicit registry for runtime capability declarations."""

    def __init__(self, capabilities: Iterable[CapabilitySpec] | None = None) -> None:
        self._capabilities: dict[str, CapabilitySpec] = {}
        for capability in capabilities or []:
            self.register(capability)

    def register(self, capability: CapabilitySpec) -> None:
        """Register or replace one capability declaration."""
        self._capabilities[capability.name] = _normalize_capability(capability)

    def register_provider(self, provider: RuntimeCapabilityProvider) -> None:
        """Register every capability returned by a provider."""
        capabilities = provider.capabilities()
        for capability in capabilities:
            self.register(capability)

    def get(self, name: str) -> CapabilitySpec | None:
        """Return a capability by name."""
        return self._capabilities.get(name)

    def list(self) -> builtins.list[CapabilitySpec]:
        """Return capabilities in registration order."""
        return list(self._capabilities.values())

    def list_capabilities(self) -> builtins.list[CapabilitySpec]:
        """Return capabilities in registration order."""
        return self.list()

    def compile_tools(self) -> builtins.list[ToolSpec]:
        """Compile all registered executable capability tools."""
        tools: builtins.list[ToolSpec] = []
        for capability in self._capabilities.values():
            tools.extend(capability.to_tools())
        return tools


def activate_capabilities(
    capabilities: Iterable[CapabilitySpec],
    ecosystem_manager: Any,
) -> list[str]:
    """Activate explicit capability declarations into an ecosystem manager.

    Activation is intentionally explicit and local to the provided manager.  It
    does not scan user directories, discover plugins, or load marketplaces.
    """
    activated: list[str] = []
    for capability in capabilities:
        if activate_capability(capability, ecosystem_manager):
            activated.append(capability.name)
    return activated


def activate_capability(capability: CapabilitySpec, ecosystem_manager: Any) -> bool:
    """Activate one explicit capability declaration into an ecosystem manager."""
    normalized = _normalize_capability(capability)
    if normalized.source == CapabilitySource.MCP:
        return _activate_mcp_capability(normalized, ecosystem_manager)
    if normalized.source == CapabilitySource.SKILL:
        return _activate_skill_capability(normalized, ecosystem_manager)
    return False


def _normalize_capability(capability: CapabilitySpec) -> CapabilitySpec:
    if not isinstance(capability, CapabilitySpec):
        raise TypeError(
            f"capability must be CapabilitySpec, got {type(capability).__name__}"
        )
    source = capability.source
    if not isinstance(source, CapabilitySource):
        source = CapabilitySource(source)
    return replace(
        capability,
        source=source,
        tools=list(capability.tools),
        metadata=dict(capability.metadata),
        extensions=dict(capability.extensions),
    )


def _flatten_tool_entries(entries: Iterable[ToolSpec | Toolset]) -> list[ToolSpec]:
    tools: list[ToolSpec] = []
    for entry in entries:
        if isinstance(entry, ToolSpec):
            tools.append(entry)
        elif isinstance(entry, Toolset):
            tools.extend(entry.tools)
        else:
            raise TypeError(
                "capability tools must be ToolSpec or Toolset, "
                f"got {type(entry).__name__}"
            )
    return tools


def _activate_mcp_capability(capability: CapabilitySpec, ecosystem_manager: Any) -> bool:
    from ..ecosystem.activation import Capability as EcosystemCapability

    server_name = str(capability.metadata.get("server") or capability.name.removeprefix("mcp:"))
    raw_config = dict(capability.metadata.get("config") or {})
    config = _mcp_server_config(raw_config, capability)

    ecosystem_manager.mcp_bridge.register_server(
        server_name,
        config,
        scope=str(raw_config.get("scope", "agent")),
    )
    if _should_connect_mcp_server(raw_config, config):
        ecosystem_manager.mcp_bridge.connect(server_name)

    ecosystem_manager.capability_registry.register(
        EcosystemCapability(
            name=capability.name,
            description=capability.description or f"MCP server: {server_name}",
            tools=[server_name],
            activation="manual",
            keywords=[server_name, capability.name],
        )
    )
    ecosystem_manager.capability_registry.activate(capability.name)
    return True


def _mcp_server_config(raw_config: dict[str, Any], capability: CapabilitySpec) -> Any:
    from ..ecosystem.mcp import MCPServerConfig, MCPTransportType

    transport = raw_config.get("type", raw_config.get("transport", "stdio"))
    if isinstance(transport, MCPTransportType):
        transport_type = transport
    else:
        transport_type = MCPTransportType(str(transport))

    auto_approve = raw_config.get("auto_approve", raw_config.get("autoApprove"))
    return MCPServerConfig(
        type=transport_type,
        command=_optional_str(raw_config.get("command")),
        args=_string_list(raw_config.get("args")),
        env=_string_dict(raw_config.get("env")),
        url=_optional_str(raw_config.get("url")),
        headers=_string_dict(raw_config.get("headers")),
        disabled=bool(raw_config.get("disabled", False)),
        auto_approve=_string_list(auto_approve),
        instructions=str(raw_config.get("instructions", capability.description or "")),
        mock_tools=_dict_list(raw_config.get("mock_tools", raw_config.get("mockTools"))),
        mock_resources=_dict_list(
            raw_config.get("mock_resources", raw_config.get("mockResources"))
        ),
        mock_tool_results=dict(
            raw_config.get("mock_tool_results", raw_config.get("mockToolResults")) or {}
        ),
    )


def _should_connect_mcp_server(raw_config: dict[str, Any], config: Any) -> bool:
    if config.disabled:
        return False
    explicit = raw_config.get("connect")
    if explicit is not None:
        return bool(explicit)
    return bool(
        config.command
        or config.mock_tools
        or config.mock_resources
        or config.mock_tool_results
    )


def _activate_skill_capability(capability: CapabilitySpec, ecosystem_manager: Any) -> bool:
    from ..ecosystem.activation import Capability as EcosystemCapability
    from ..ecosystem.skill import Skill, SkillLoader

    skill_name = str(capability.metadata.get("skill") or capability.name.removeprefix("skill:"))
    raw_config = dict(capability.metadata.get("config") or {})

    raw_path = raw_config.get("path")
    if raw_path is not None:
        path = Path(str(raw_path)).expanduser()
        if path.is_dir():
            SkillLoader.load_from_directory(path, ecosystem_manager.skill_registry)
        elif path.is_file():
            ecosystem_manager.skill_registry.register(SkillLoader.load_from_file(path))

    raw_content = raw_config.get("content")
    if raw_content is not None:
        ecosystem_manager.skill_registry.register(
            Skill(
                name=skill_name,
                description=capability.description,
                content=str(raw_content),
                when_to_use=_optional_str(
                    raw_config.get("when_to_use", raw_config.get("whenToUse"))
                ),
                allowed_tools=_string_list(
                    raw_config.get("allowed_tools", raw_config.get("allowedTools"))
                ),
                argument_hint=_optional_str(
                    raw_config.get("argument_hint", raw_config.get("argumentHint"))
                ),
                model=_optional_str(raw_config.get("model")),
                user_invocable=bool(raw_config.get("user_invocable", True)),
                effort=_optional_int(raw_config.get("effort")),
                agent=_optional_str(raw_config.get("agent")),
                context=str(raw_config.get("context", "inline")),
                paths=_optional_string_list(raw_config.get("paths")),
                version=_optional_str(raw_config.get("version")),
                source="agent",
            )
        )

    ecosystem_manager.capability_registry.register(
        EcosystemCapability(
            name=capability.name,
            description=capability.description or f"Skill: {skill_name}",
            tools=_string_list(raw_config.get("allowed_tools", raw_config.get("allowedTools"))),
            activation="manual",
            keywords=[skill_name, capability.name],
        )
    )
    ecosystem_manager.capability_registry.activate(capability.name)
    return True


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def _optional_string_list(value: Any) -> list[str] | None:
    if value is None:
        return None
    return _string_list(value)


def _string_dict(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    return {str(key): str(item) for key, item in dict(value).items()}


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    return [dict(item) for item in value]


__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CapabilitySource",
    "CapabilitySpec",
    "RuntimeCapabilityProvider",
    "activate_capabilities",
    "activate_capability",
]
