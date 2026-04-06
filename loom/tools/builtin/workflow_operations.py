"""工作流和计划工具"""

from typing import Any


async def enter_plan_mode() -> dict[str, Any]:
    """进入计划模式"""
    return {"mode": "plan", "status": "entered"}


async def exit_plan_mode() -> dict[str, Any]:
    """退出计划模式"""
    return {"mode": "normal", "status": "exited"}


async def enter_worktree(name: str | None = None) -> dict[str, Any]:
    """进入 worktree"""
    return {"worktree": name or "default", "status": "entered"}


async def exit_worktree() -> dict[str, Any]:
    """退出 worktree"""
    return {"status": "exited"}
