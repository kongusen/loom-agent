"""Configuration contracts for the public Loom API."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolAccessPolicy:
    """Stable tool access controls."""

    allow: list[str] = field(default_factory=list)
    deny: list[str] = field(default_factory=list)
    read_only_only: bool = False
    allow_destructive: bool = False


@dataclass(slots=True)
class ToolRateLimitPolicy:
    """Stable tool rate-limit controls."""

    max_calls_per_minute: int = 60


@dataclass(slots=True)
class ToolPolicy:
    """Tool governance settings exposed on the public API."""

    access: ToolAccessPolicy = field(default_factory=ToolAccessPolicy)
    rate_limits: ToolRateLimitPolicy = field(default_factory=ToolRateLimitPolicy)
    extensions: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ToolParameterSpec:
    """Stable tool parameter schema."""

    name: str
    type: str
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass(slots=True)
class ToolHandler:
    """Adapter for local callable-backed tool execution."""

    func: Callable[..., Any]
    mode: str = "callable"
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def callable(
        cls,
        func: Callable[..., Any],
        *,
        extensions: dict[str, Any] | None = None,
    ) -> ToolHandler:
        return cls(func=func, mode="callable", extensions=dict(extensions or {}))

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        return self.func(*args, **kwargs)


@dataclass(slots=True)
class ToolSpec:
    """Stable public tool declaration."""

    name: str
    description: str = ""
    parameters: list[ToolParameterSpec] = field(default_factory=list)
    read_only: bool = False
    destructive: bool = False
    concurrency_safe: bool = False
    requires_permission: bool = True
    handler: ToolHandler | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_function(
        cls,
        func: Callable[..., Any],
        *,
        name: str | None = None,
        description: str | None = None,
        read_only: bool = False,
        destructive: bool = False,
        concurrency_safe: bool = False,
        requires_permission: bool | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> ToolSpec:
        permission_required = requires_permission if requires_permission is not None else not read_only
        return cls(
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            parameters=_build_tool_parameter_specs(inspect.signature(func)),
            read_only=read_only,
            destructive=destructive,
            concurrency_safe=concurrency_safe,
            requires_permission=permission_required,
            handler=ToolHandler.callable(func),
            extensions=dict(extensions or {}),
        )

    def to_input_schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter in self.parameters:
            schema: dict[str, Any] = {"type": parameter.type}
            if parameter.description:
                schema["description"] = parameter.description
            if parameter.default is not None:
                schema["default"] = parameter.default
            properties[parameter.name] = schema
            if parameter.required:
                required.append(parameter.name)
        return {"type": "object", "properties": properties, "required": required}

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self.handler is None:
            raise RuntimeError(f"Tool '{self.name}' does not have a local handler")
        return self.handler.invoke(*args, **kwargs)


@dataclass(slots=True)
class Toolset:
    """Composable group of tools for the public API.

    Toolsets are a user-facing convenience only.  Agent normalization flattens
    them into plain ``ToolSpec`` entries before runtime execution.
    """

    name: str
    tools: list[ToolSpec] = field(default_factory=list)
    description: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def of(
        cls,
        *entries: ToolSpec | Toolset,
        name: str = "custom",
        description: str = "",
        extensions: dict[str, Any] | None = None,
    ) -> Toolset:
        """Create a toolset from tools and/or other toolsets."""
        return cls(
            name=name,
            description=description,
            tools=_flatten_toolset_entries(entries),
            extensions=dict(extensions or {}),
        )

    @classmethod
    def files(
        cls,
        *,
        read_only: bool = True,
        name: str = "files",
    ) -> Toolset:
        """Create a file-system toolset.

        ``read_only=True`` exposes Read, Glob, and Grep.  ``read_only=False``
        also exposes Write and Edit.
        """
        from ..tools.builtin.file_tool import EDIT_TOOL, GLOB_TOOL, GREP_TOOL, READ_TOOL, WRITE_TOOL

        tools = [READ_TOOL, GLOB_TOOL, GREP_TOOL]
        if not read_only:
            tools.extend([WRITE_TOOL, EDIT_TOOL])
        return cls(
            name=name,
            description="File system tools",
            tools=[_tool_spec_from_runtime_tool(tool) for tool in tools],
            extensions={"builtin": "files", "read_only": read_only},
        )

    @classmethod
    def web(cls, *, name: str = "web") -> Toolset:
        """Create a web research toolset."""
        from ..tools.builtin.shell_web_tool import WEB_FETCH_TOOL, WEB_SEARCH_TOOL

        return cls(
            name=name,
            description="Web fetch and search tools",
            tools=[
                _tool_spec_from_runtime_tool(WEB_FETCH_TOOL),
                _tool_spec_from_runtime_tool(WEB_SEARCH_TOOL),
            ],
            extensions={"builtin": "web"},
        )

    @classmethod
    def shell(cls, *, name: str = "shell") -> Toolset:
        """Create a shell execution toolset."""
        from ..tools.builtin.shell_web_tool import BASH_TOOL

        return cls(
            name=name,
            description="Shell execution tools",
            tools=[_tool_spec_from_runtime_tool(BASH_TOOL)],
            extensions={"builtin": "shell"},
        )

    @classmethod
    def mcp(cls, *, name: str = "mcp") -> Toolset:
        """Create a generic MCP resource/tool bridge toolset."""
        from ..tools.builtin.mcp_tool import MCP_CALL_TOOL, MCP_LIST_TOOL, MCP_READ_TOOL

        return cls(
            name=name,
            description="MCP resource and tool bridge",
            tools=[
                _tool_spec_from_runtime_tool(MCP_LIST_TOOL),
                _tool_spec_from_runtime_tool(MCP_READ_TOOL),
                _tool_spec_from_runtime_tool(MCP_CALL_TOOL),
            ],
            extensions={"builtin": "mcp"},
        )

    def include(self, *entries: ToolSpec | Toolset) -> Toolset:
        """Return a new toolset with additional tools appended."""
        return Toolset(
            name=self.name,
            description=self.description,
            tools=[*self.tools, *_flatten_toolset_entries(entries)],
            extensions=dict(self.extensions),
        )

    def __iter__(self):
        return iter(self.tools)

    def __len__(self) -> int:
        return len(self.tools)


def _flatten_toolset_entries(entries: tuple[ToolSpec | Toolset, ...]) -> list[ToolSpec]:
    tools: list[ToolSpec] = []
    for entry in entries:
        if isinstance(entry, ToolSpec):
            tools.append(entry)
        elif isinstance(entry, Toolset):
            tools.extend(entry.tools)
        else:
            raise TypeError(f"toolset entries must be ToolSpec or Toolset, got {type(entry).__name__}")
    return tools


def _tool_spec_from_runtime_tool(tool: Any) -> ToolSpec:
    definition = tool.definition
    read_only = bool(definition.is_read_only)
    return ToolSpec(
        name=str(definition.name),
        description=str(definition.description),
        parameters=[
            ToolParameterSpec(
                name=str(parameter.name),
                type=str(parameter.type),
                description=str(parameter.description),
                required=bool(parameter.required),
                default=parameter.default,
            )
            for parameter in definition.parameters
        ],
        read_only=read_only,
        destructive=bool(definition.is_destructive),
        concurrency_safe=bool(definition.is_concurrency_safe),
        requires_permission=not read_only,
        handler=ToolHandler.callable(tool.handler),
        extensions={"builtin_tool": str(definition.name)},
    )


def _build_tool_parameter_specs(sig: inspect.Signature) -> list[ToolParameterSpec]:
    parameters: list[ToolParameterSpec] = []
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        json_type = "string"
        if param.annotation is int:
            json_type = "integer"
        elif param.annotation is float:
            json_type = "number"
        elif param.annotation is bool:
            json_type = "boolean"

        default = None if param.default == inspect.Parameter.empty else param.default
        parameters.append(
            ToolParameterSpec(
                name=param_name,
                type=json_type,
                required=param.default == inspect.Parameter.empty,
                default=default,
            )
        )
    return parameters
