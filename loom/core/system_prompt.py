"""系统提示生成模块 - 对齐 Claude Code 的动态系统提示构建机制"""

from typing import Dict, List, Optional

from loom.interfaces.tool import BaseTool


class SystemPromptBuilder:
    """动态生成系统提示，包含工具目录、风格指引与边界提醒"""

    def __init__(
        self,
        base_instructions: Optional[str] = None,
        style_guide: Optional[str] = None,
        boundary_reminders: Optional[List[str]] = None,
    ) -> None:
        self.base_instructions = base_instructions or self._default_instructions()
        self.style_guide = style_guide or self._default_style_guide()
        self.boundary_reminders = boundary_reminders or self._default_boundary_reminders()

    def build(
        self,
        tools: Dict[str, BaseTool],
        context: Optional[Dict] = None,
    ) -> str:
        """构建完整的系统提示"""
        sections = [
            self.base_instructions,
            self._build_tool_catalog(tools),
            self.style_guide,
            self._build_boundary_section(),
        ]

        if context:
            sections.insert(1, self._build_context_section(context))

        return "\n\n".join(filter(None, sections))

    def _build_tool_catalog(self, tools: Dict[str, BaseTool]) -> str:
        """生成工具目录"""
        if not tools:
            return ""

        catalog_lines = ["## Available Tools", ""]
        for tool in tools.values():
            catalog_lines.append(f"### {tool.name}")
            catalog_lines.append(f"**Description**: {getattr(tool, 'description', 'No description')}")

            # 提取参数 schema
            if hasattr(tool, "args_schema"):
                try:
                    schema = tool.args_schema.model_json_schema()
                    properties = schema.get("properties", {})
                    required = schema.get("required", [])

                    if properties:
                        catalog_lines.append("**Parameters**:")
                        for param_name, param_info in properties.items():
                            is_required = " (required)" if param_name in required else ""
                            param_type = param_info.get("type", "any")
                            param_desc = param_info.get("description", "")
                            catalog_lines.append(f"- `{param_name}` ({param_type}){is_required}: {param_desc}")
                except Exception:
                    pass

            # 并发安全性标记
            if hasattr(tool, "is_concurrency_safe"):
                safe = "✓" if tool.is_concurrency_safe else "✗"
                catalog_lines.append(f"**Concurrency Safe**: {safe}")

            catalog_lines.append("")

        return "\n".join(catalog_lines)

    def _build_context_section(self, context: Dict) -> str:
        """构建上下文信息段"""
        lines = ["## Context Information", ""]
        for key, value in context.items():
            lines.append(f"**{key}**: {value}")
        return "\n".join(lines)

    def _build_boundary_section(self) -> str:
        """构建边界提醒段"""
        if not self.boundary_reminders:
            return ""
        lines = ["## Important Reminders", ""]
        for reminder in self.boundary_reminders:
            lines.append(f"- {reminder}")
        return "\n".join(lines)

    @staticmethod
    def _default_instructions() -> str:
        return """You are an intelligent AI agent powered by the Loom framework.

Your capabilities:
- Analyze user requests and break them down into actionable steps
- Use available tools to gather information and perform actions
- Think step-by-step through complex problems
- Provide clear, concise, and accurate responses

When using tools:
1. Carefully read the tool descriptions and parameters
2. Provide all required parameters with correct types
3. Handle tool results appropriately
4. If a tool fails, try alternative approaches or inform the user

Your responses should be:
- Clear and well-structured
- Accurate and factual
- Helpful and actionable
- Honest about limitations"""

    @staticmethod
    def _default_style_guide() -> str:
        return """## Response Style

- Use markdown formatting for better readability
- Break down complex explanations into bullet points or numbered lists
- When executing multiple steps, show your reasoning process
- If uncertain, acknowledge the uncertainty
- Cite tool results when making claims based on them"""

    @staticmethod
    def _default_boundary_reminders() -> List[str]:
        return [
            "Always validate tool parameters before calling",
            "Respect tool execution timeouts and handle failures gracefully",
            "Do not make assumptions about tool results without verification",
            "If a task requires multiple steps, break it down clearly",
            "Stop and ask for clarification if the user's intent is ambiguous",
        ]


def build_system_prompt(
    tools: Dict[str, BaseTool],
    custom_instructions: Optional[str] = None,
    context: Optional[Dict] = None,
) -> str:
    """便捷函数：快速构建系统提示"""
    builder = SystemPromptBuilder(base_instructions=custom_instructions)
    return builder.build(tools, context)
