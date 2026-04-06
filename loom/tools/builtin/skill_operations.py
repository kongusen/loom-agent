"""Skill 工具"""

from typing import Any


async def skill_invoke(skill: str, args: str = "") -> dict[str, Any]:
    """调用 Skill"""
    return {
        "skill": skill,
        "args": args,
        "result": None,
        "message": "Skill system not implemented"
    }


async def skill_discover() -> dict[str, Any]:
    """发现可用 Skills"""
    return {
        "skills": [],
        "message": "Skill discovery not implemented"
    }
