"""Capability registry - 按需注入原则

✗ 错误做法：启动时把所有 Skill 塞进 C
✓ 正确做法：只有匹配到当前任务的 Skill 才注入
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..tools.registry import ToolRegistry
    from ..context.partitions import ContextPartitions


@dataclass
class Capability:
    """Capability definition with metadata"""
    name: str
    description: str
    tools: list[str]
    activation: str = "manual"  # manual | auto
    keywords: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)


class CapabilityRegistry:
    """Manage capability registration with on-demand injection"""

    def __init__(self):
        self.capabilities: dict[str, Capability] = {}
        self.active_capabilities: set[str] = set()

    def register(self, capability: Capability):
        """Register a capability"""
        self.capabilities[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        """Get capability by name"""
        return self.capabilities.get(name)

    def match_task(self, task_description: str) -> list[Capability]:
        """Match capabilities to task by keywords"""
        matched = []
        task_lower = task_description.lower()
        for cap in self.capabilities.values():
            if any(kw in task_lower for kw in cap.keywords):
                matched.append(cap)
        return matched

    def activate(
        self,
        name: str,
        tool_registry: "ToolRegistry | None" = None,
        context: "ContextPartitions | None" = None
    ) -> bool:
        """Activate a capability and inject its tools

        Args:
            name: Capability name to activate
            tool_registry: Tool registry to register tools to (optional)
            context: Context partitions to inject skill description (optional)

        Returns:
            True if activated successfully, False otherwise
        """
        # Get capability
        capability = self.capabilities.get(name)
        if not capability:
            return False

        # Already active
        if name in self.active_capabilities:
            return True

        # Mark as active
        self.active_capabilities.add(name)

        # Register tools if tool_registry provided
        if tool_registry:
            from ..tools.builtin import get_builtin_tool

            for tool_name in capability.tools:
                # Try to get builtin tool
                tool = get_builtin_tool(tool_name)
                if tool:
                    tool_registry.register(tool)

        # Inject skill description to context if provided
        if context:
            # Format skill description
            skill_desc = self._format_skill_description(capability)
            if skill_desc and skill_desc not in context.skill:
                context.skill.append(skill_desc)

        return True

    def deactivate(
        self,
        name: str,
        tool_registry: "ToolRegistry | None" = None,
        context: "ContextPartitions | None" = None
    ) -> bool:
        """Deactivate a capability and remove its tools

        Args:
            name: Capability name to deactivate
            tool_registry: Tool registry to unregister tools from (optional)
            context: Context partitions to remove skill description (optional)

        Returns:
            True if deactivated successfully, False otherwise
        """
        # Get capability
        capability = self.capabilities.get(name)
        if not capability:
            return False

        # Not active
        if name not in self.active_capabilities:
            return True

        # Mark as inactive
        self.active_capabilities.discard(name)

        # Unregister tools if tool_registry provided
        if tool_registry:
            for tool_name in capability.tools:
                tool_registry.unregister(tool_name)

        # Remove skill description from context if provided
        if context:
            skill_desc = self._format_skill_description(capability)
            if skill_desc in context.skill:
                context.skill.remove(skill_desc)

        return True

    def _format_skill_description(self, capability: Capability) -> str:
        """Format capability as skill description for LLM

        Args:
            capability: Capability to format

        Returns:
            Formatted skill description
        """
        parts = [f"**{capability.name}**: {capability.description}"]

        if capability.tools:
            parts.append(f"  Tools: {', '.join(capability.tools)}")

        return "\n".join(parts)

    def list_capabilities(self) -> list[Capability]:
        """List all capabilities"""
        return list(self.capabilities.values())

    def list_active(self) -> list[Capability]:
        """List active capabilities"""
        return [
            cap for cap in self.capabilities.values()
            if cap.name in self.active_capabilities
        ]

