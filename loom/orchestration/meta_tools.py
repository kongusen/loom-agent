"""
Meta-tools for Agent orchestration

Meta-tools are special tools that enable agents to perform high-level
orchestration tasks like delegation, planning, and reflection.
"""

from typing import Any


def create_delegate_task_tool() -> dict[str, Any]:
    """
    Create the delegate_task meta-tool definition

    This tool allows agents to delegate subtasks to child agents,
    enabling hierarchical task decomposition and parallel execution.

    Returns:
        Tool definition dict compatible with LLM tool calling
    """
    return {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": (
                "Delegate a subtask to a specialized child agent. "
                "Use this when a task can be broken down into independent subtasks "
                "or when specialized expertise is needed. "
                "The child agent will have access to relevant context from the parent."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subtask_description": {
                        "type": "string",
                        "description": "Clear description of the subtask to delegate",
                    },
                    "required_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of capabilities needed (e.g., 'code_analysis', 'data_processing')",
                    },
                    "context_hints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory IDs that should be passed to the child agent",
                    },
                },
                "required": ["subtask_description"],
            },
        },
    }


async def execute_delegate_task(
    agent: Any,  # Agent instance
    args: dict[str, Any],
    parent_task: Any,  # Task instance
) -> Any:
    """
    Execute the delegate_task meta-tool

    This is called by the Agent when the LLM invokes the delegate_task tool.

    Args:
        agent: The parent Agent instance
        args: Tool arguments from LLM
        parent_task: The current task being executed

    Returns:
        Result from the child agent
    """
    # Delegate to Agent._auto_delegate method
    return await agent._auto_delegate(args, parent_task)
