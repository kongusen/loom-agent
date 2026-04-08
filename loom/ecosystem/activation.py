"""Runtime activation helpers for ecosystem components.

This module is intentionally internal to the ecosystem package. It models how
loaded ecosystem components are activated into the current runtime rather than
defining a separate top-level extension system.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context.partitions import ContextPartitions
    from ..tools.registry import ToolRegistry


@dataclass
class Capability:
    """Runtime activation unit derived from ecosystem components."""

    name: str
    description: str
    tools: list[str]
    activation: str = "manual"  # manual | auto
    keywords: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)


class CapabilityRegistry:
    """Manage capability activation with on-demand runtime injection."""

    def __init__(self):
        self.capabilities: dict[str, Capability] = {}
        self.active_capabilities: set[str] = set()

    def register(self, capability: Capability) -> None:
        """Register one activation unit."""
        self.capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        """Get capability by name."""
        return self.capabilities.get(name)

    def match_task(self, task_description: str) -> list[Capability]:
        """Match capabilities to a task description by keyword."""
        matched = []
        task_lower = task_description.lower()
        for capability in self.capabilities.values():
            if any(keyword in task_lower for keyword in capability.keywords):
                matched.append(capability)
        return matched

    def activate(
        self,
        name: str,
        tool_registry: "ToolRegistry | None" = None,
        context: "ContextPartitions | None" = None,
    ) -> bool:
        """Activate a capability and inject its runtime effects."""
        capability = self.capabilities.get(name)
        if capability is None:
            return False

        if name in self.active_capabilities:
            return True

        self.active_capabilities.add(name)

        if tool_registry:
            from ..tools.builtin import get_builtin_tool

            for tool_name in capability.tools:
                tool = get_builtin_tool(tool_name)
                if tool:
                    tool_registry.register(tool)

        if context:
            skill_desc = self._format_skill_description(capability)
            if skill_desc and skill_desc not in context.skill:
                context.skill.append(skill_desc)

        return True

    def deactivate(
        self,
        name: str,
        tool_registry: "ToolRegistry | None" = None,
        context: "ContextPartitions | None" = None,
    ) -> bool:
        """Deactivate a capability and remove injected runtime effects."""
        capability = self.capabilities.get(name)
        if capability is None:
            return False

        if name not in self.active_capabilities:
            return True

        self.active_capabilities.discard(name)

        if tool_registry:
            for tool_name in capability.tools:
                tool_registry.unregister(tool_name)

        if context:
            skill_desc = self._format_skill_description(capability)
            if skill_desc in context.skill:
                context.skill.remove(skill_desc)

        return True

    def list_capabilities(self) -> list[Capability]:
        """List all registered capabilities."""
        return list(self.capabilities.values())

    def list_active(self) -> list[Capability]:
        """List currently active capabilities."""
        return [
            capability
            for capability in self.capabilities.values()
            if capability.name in self.active_capabilities
        ]

    def _format_skill_description(self, capability: Capability) -> str:
        """Render a capability as skill context text."""
        parts = [f"**{capability.name}**: {capability.description}"]
        if capability.tools:
            parts.append(f"  Tools: {', '.join(capability.tools)}")
        return "\n".join(parts)


class CapabilityLoader:
    """Thin helper that progressively activates registered capabilities."""

    def __init__(self, capability_registry: CapabilityRegistry, tool_registry: "ToolRegistry"):
        self.capability_registry = capability_registry
        self.tool_registry = tool_registry
        self.loaded: set[str] = set()

    def load(self, capability_name: str) -> bool:
        """Load a capability and activate its tools."""
        if capability_name in self.loaded:
            return True

        capability = self.capability_registry.get(capability_name)
        if capability is None:
            return False

        for dependency in getattr(capability, "dependencies", []):
            self.load(dependency)

        self.capability_registry.activate(capability_name, self.tool_registry)
        self.loaded.add(capability_name)
        return True

    def unload(self, capability_name: str) -> bool:
        """Unload a capability and deactivate its tools."""
        if capability_name not in self.loaded:
            return False

        self.capability_registry.deactivate(capability_name, self.tool_registry)
        self.loaded.discard(capability_name)
        return True

    def is_loaded(self, capability_name: str) -> bool:
        """Check whether a capability has already been loaded."""
        return capability_name in self.loaded


__all__ = ["Capability", "CapabilityRegistry", "CapabilityLoader"]
