"""Built-in tools: done and delegate."""

from __future__ import annotations

from pydantic import BaseModel

from ..types import ToolDefinition, ToolContext
from .schema import PydanticSchema


class DoneParams(BaseModel):
    result: str


async def _done_execute(params: DoneParams, ctx: ToolContext) -> str:
    return params.result


done_tool = ToolDefinition(
    name="done",
    description="Signal task completion with a final result.",
    parameters=PydanticSchema(DoneParams),
    execute=_done_execute,
)


class DelegateParams(BaseModel):
    task: str
    domain: str = ""


async def _delegate_execute(params: DelegateParams, ctx: ToolContext) -> str:
    # Actual delegation handled by agent loop — this is a signal tool
    return f"Delegating: {params.task}"


delegate_tool = ToolDefinition(
    name="delegate",
    description="Delegate a subtask to another agent in the cluster.",
    parameters=PydanticSchema(DelegateParams),
    execute=_delegate_execute,
)
