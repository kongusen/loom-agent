"""Skill 工具 - 完整实现"""

from pathlib import Path
from typing import Any


async def skill_invoke(skill: str, args: str = "") -> dict[str, Any]:
    """调用 Skill

    Args:
        skill: Skill 名称（支持 /skill 或 skill 格式）
        args: 可选参数（字符串或 key=value 格式）

    Returns:
        包含 skill 内容和元数据的字典
    """
    import os

    from loom.ecosystem.hooks import HookExecutor
    from loom.ecosystem.shell_exec import execute_inline_shell, has_inline_shell_commands

    # 移除前导斜杠（兼容 /skill 格式）
    skill_name = skill.lstrip("/")

    # 获取或创建全局注册表
    registry = _get_or_create_registry()

    # 查找 skill
    skill_obj = registry.get(skill_name)

    if not skill_obj:
        return {
            "success": False,
            "skill": skill_name,
            "args": args,
            "error": f"Skill '{skill_name}' not found",
            "available_skills": registry.list_skills(),
        }

    try:
        # Execute onLoad hook
        if skill_obj.hooks:
            await HookExecutor.execute_on_load(skill_obj.hooks, skill_name)

        # Execute onInvoke hook
        if skill_obj.hooks:
            await HookExecutor.execute_on_invoke(skill_obj.hooks, skill_name, args)

        # 获取内容（懒加载）
        content = skill_obj.content

        # 环境变量替换（符合 Claude Code 规范）
        if skill_obj.file_path:
            skill_dir = os.path.dirname(skill_obj.file_path)
            content = content.replace("${CLAUDE_SKILL_DIR}", skill_dir)

        # Session ID 替换（简化版本）
        import uuid

        session_id = str(uuid.uuid4())[:8]
        content = content.replace("${CLAUDE_SESSION_ID}", session_id)

        # 参数替换
        if args:
            # 支持两种格式：
            # 1. 简单字符串：直接替换 $ARGUMENTS
            # 2. key=value 格式：替换 ${key}
            if "=" in args:
                # 命名参数格式：name=John email=john@example.com
                arg_dict = {}
                for pair in args.split():
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        arg_dict[key.strip()] = value.strip()
                        # 替换 ${key} 格式
                        content = content.replace(f"${{{key.strip()}}}", value.strip())
            else:
                # 简单参数格式：直接替换 $ARGUMENTS
                content = content.replace("$ARGUMENTS", args)
                content = content.replace("${ARGUMENTS}", args)

        # Shell 内联执行（如果包含 !`command`）
        if has_inline_shell_commands(content):
            content = await execute_inline_shell(content, skill_obj.shell)

        result = {
            "success": True,
            "skill": skill_name,
            "args": args,
            "content": content,
            "description": skill_obj.description,
            "allowed_tools": skill_obj.allowed_tools,
            "model": skill_obj.model,
            "user_invocable": skill_obj.user_invocable,
            "source": skill_obj.source,
            # Agent framework features
            "effort": skill_obj.effort,
            "effort_token_limit": _get_effort_token_limit(skill_obj.effort),
            "agent": skill_obj.agent,
            "context": skill_obj.context,
            "paths": skill_obj.paths,
            "version": skill_obj.version,
            "has_hooks": skill_obj.hooks is not None,
            "has_shell_config": skill_obj.shell is not None,
        }

        # Execute onComplete hook
        if skill_obj.hooks:
            await HookExecutor.execute_on_complete(skill_obj.hooks, skill_name, result)

        return result

    except Exception as e:
        # Execute onError hook
        if skill_obj.hooks:
            await HookExecutor.execute_on_error(skill_obj.hooks, skill_name, e)

        return {
            "success": False,
            "skill": skill_name,
            "args": args,
            "error": str(e),
        }


def _get_effort_token_limit(effort: int | None) -> int:
    """Get token limit for effort level"""
    from loom.ecosystem.skill import get_effort_token_limit

    return get_effort_token_limit(effort)


async def skill_discover() -> dict[str, Any]:
    """发现可用 Skills

    Returns:
        包含所有可用 skills 的列表
    """
    from loom.ecosystem.skill import estimate_skill_tokens

    # 获取或创建全局注册表
    registry = _get_or_create_registry()

    # 获取所有 skills
    skills = []
    for skill_name in registry.list_skills():
        skill_obj = registry.get(skill_name)
        if skill_obj:
            skills.append(
                {
                    "name": skill_obj.name,
                    "description": skill_obj.description,
                    "when_to_use": skill_obj.when_to_use,
                    "user_invocable": skill_obj.user_invocable,
                    "source": skill_obj.source,
                    "allowed_tools": skill_obj.allowed_tools,
                    "model": skill_obj.model,
                    # Agent framework features
                    "effort": skill_obj.effort,
                    "agent": skill_obj.agent,
                    "context": skill_obj.context,
                    "paths": skill_obj.paths,
                    "version": skill_obj.version,
                    # Token estimation (frontmatter only)
                    "estimated_tokens": estimate_skill_tokens(skill_obj, load_content=False),
                }
            )

    return {"success": True, "skills": skills, "count": len(skills)}


# 全局注册表缓存
_global_registry = None


def _get_or_create_registry():
    """获取或创建全局 skill 注册表"""
    global _global_registry

    if _global_registry is None:
        from loom.ecosystem.skill import SkillLoader, SkillRegistry

        _global_registry = SkillRegistry()

        # 从默认位置加载 skills
        search_paths = [
            Path.cwd() / "skills",
            Path.cwd() / "examples" / "skills",
            Path.home() / ".loom" / "skills",
        ]

        for path in search_paths:
            if path.exists():
                SkillLoader.load_from_directory(path, _global_registry)

    return _global_registry
