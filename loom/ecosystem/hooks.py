"""Skill hooks system - lifecycle management"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class SkillHooks:
    """Skill lifecycle hooks"""
    on_load: Callable[[], Any] | None = None      # 加载时执行
    on_invoke: Callable[[], Any] | None = None    # 调用前执行
    on_complete: Callable[[Any], Any] | None = None  # 完成后执行
    on_error: Callable[[Exception], Any] | None = None  # 错误时执行


class HookExecutor:
    """Execute skill hooks"""

    @staticmethod
    async def execute_hook(hook: Callable | None, *args, **kwargs) -> Any:
        """Execute a single hook

        Args:
            hook: Hook function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Hook result or None if hook is None
        """
        if hook is None:
            return None

        try:
            if asyncio.iscoroutinefunction(hook):
                return await hook(*args, **kwargs)
            else:
                return hook(*args, **kwargs)
        except Exception as e:
            print(f"Hook execution failed: {e}")
            return None

    @staticmethod
    async def execute_on_load(hooks: SkillHooks | None, skill_name: str) -> Any:
        """Execute onLoad hook"""
        if hooks and hooks.on_load:
            print(f"[Hook] onLoad: {skill_name}")
            return await HookExecutor.execute_hook(hooks.on_load)
        return None

    @staticmethod
    async def execute_on_invoke(hooks: SkillHooks | None, skill_name: str, args: str) -> Any:
        """Execute onInvoke hook"""
        if hooks and hooks.on_invoke:
            print(f"[Hook] onInvoke: {skill_name} with args={args}")
            return await HookExecutor.execute_hook(hooks.on_invoke)
        return None

    @staticmethod
    async def execute_on_complete(hooks: SkillHooks | None, skill_name: str, result: Any) -> Any:
        """Execute onComplete hook"""
        if hooks and hooks.on_complete:
            print(f"[Hook] onComplete: {skill_name}")
            return await HookExecutor.execute_hook(hooks.on_complete, result)
        return None

    @staticmethod
    async def execute_on_error(hooks: SkillHooks | None, skill_name: str, error: Exception) -> Any:
        """Execute onError hook"""
        if hooks and hooks.on_error:
            print(f"[Hook] onError: {skill_name} - {error}")
            return await HookExecutor.execute_hook(hooks.on_error, error)
        return None


def parse_hooks_from_frontmatter(frontmatter: dict) -> SkillHooks | None:
    """Parse hooks from skill frontmatter

    Args:
        frontmatter: Parsed YAML frontmatter

    Returns:
        SkillHooks object or None if no hooks defined

    Example frontmatter:
        hooks:
          onLoad: print("Loading skill")
          onInvoke: print("Invoking skill")
          onComplete: print("Skill completed")
          onError: print("Skill failed")
    """
    if 'hooks' not in frontmatter:
        return None

    hooks_data = frontmatter['hooks']
    if not isinstance(hooks_data, dict):
        return None

    # For now, we store hook definitions as strings
    # In a full implementation, these would be compiled/evaluated
    return SkillHooks(
        on_load=hooks_data.get('onLoad'),
        on_invoke=hooks_data.get('onInvoke'),
        on_complete=hooks_data.get('onComplete'),
        on_error=hooks_data.get('onError'),
    )
