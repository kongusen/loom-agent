"""团队和远程操作"""

from typing import Any


async def team_create(name: str, members: list[str]) -> dict[str, Any]:
    """创建团队"""
    return {"team_id": f"team_{name}", "name": name, "members": members}


async def team_delete(team_id: str) -> dict[str, Any]:
    """删除团队"""
    return {"team_id": team_id, "status": "deleted"}


async def remote_trigger(event: str, data: dict) -> dict[str, Any]:
    """触发远程事件"""
    return {"event": event, "data": data, "status": "triggered"}
