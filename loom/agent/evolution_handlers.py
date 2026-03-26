"""Evolution handlers for E1/E2 tools (Axiom 4)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..types import MemoryEntry

if TYPE_CHECKING:
    from ..agent.core import Agent
    from ..types import ToolContext


async def write_memory_handler(params: dict[str, Any], ctx: ToolContext, agent: Agent) -> str:
    """E1: 写入长期记忆"""
    content = params.get("content", "")
    importance = params.get("importance", 0.7)

    if not content:
        return '{"error": "content is required"}'

    # 创建记忆条目
    entry = MemoryEntry(
        content=content,
        importance=importance,
        tokens=agent.tokenizer.count(content),
        metadata={"source": "agent_tool", "timestamp": time.time()}
    )

    # 写入 L2（长期记忆）
    await agent.memory.l2.store(entry)

    # 如果重要度很高，同时写入 L3
    if importance >= 0.9:
        await agent.memory.l3.store(entry)

    return f'{{"status": "success", "importance": {importance}}}'


async def activate_skill_handler(params: dict[str, Any], ctx: ToolContext, agent: Agent) -> str:
    """E2: 激活技能"""
    skill_name = params.get("skill_name", "")

    if not skill_name:
        return '{"error": "skill_name is required"}'

    # 检查技能是否存在
    skill = agent.skill_mgr.registry.get(skill_name)
    if not skill:
        available = [s.name for s in agent.skill_mgr.registry.all()]
        return f'{{"error": "Skill not found", "available": {available}}}'

    # 检查预算
    budget = agent.partition_mgr.get_available_budget("skill")
    skill_tokens = agent.tokenizer.count(skill.instructions)

    if skill_tokens > budget:
        return f'{{"error": "Insufficient budget", "needed": {skill_tokens}, "available": {budget}}}'

    # 激活技能
    activated = agent.skill_mgr.activate(skill_name, budget)
    if not activated:
        return f'{{"error": "Failed to activate skill"}}'

    # 更新 C_skill 分区
    skill_context = agent.skill_mgr.get_context()
    agent.partition_mgr.update_partition("skill", skill_context)

    return f'{{"status": "success", "skill": "{skill_name}", "tokens": {skill_tokens}}}'


async def deactivate_skill_handler(params: dict[str, Any], ctx: ToolContext, agent: Agent) -> str:
    """E2: 停用技能"""
    skill_name = params.get("skill_name", "")

    if not skill_name:
        return '{"error": "skill_name is required"}'

    # 停用技能
    agent.skill_mgr.deactivate(skill_name)

    # 更新 C_skill 分区
    skill_context = agent.skill_mgr.get_context()
    agent.partition_mgr.update_partition("skill", skill_context)

    return f'{{"status": "success", "skill": "{skill_name}"}}'
