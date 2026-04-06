"""Skill 工具 - 完整实现"""

from typing import Any
from pathlib import Path


async def skill_invoke(skill: str, args: str = "") -> dict[str, Any]:
    """调用 Skill

    Args:
        skill: Skill 名称（支持 /skill 或 skill 格式）
        args: 可选参数（字符串或 key=value 格式）

    Returns:
        包含 skill 内容和元数据的字典
    """
    from loom.ecosystem.skill import SkillRegistry, SkillLoader
    import os

    # 移除前导斜杠（兼容 /skill 格式）
    skill_name = skill.lstrip('/')

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
            "available_skills": registry.list_skills()
        }

    # 获取内容（懒加载）
    content = skill_obj.content

    # 环境变量替换（符合 Claude Code 规范）
    if skill_obj.file_path:
        skill_dir = os.path.dirname(skill_obj.file_path)
        content = content.replace('${CLAUDE_SKILL_DIR}', skill_dir)

    # Session ID 替换（简化版本）
    import uuid
    session_id = str(uuid.uuid4())[:8]
    content = content.replace('${CLAUDE_SESSION_ID}', session_id)

    # 参数替换
    if args:
        # 支持两种格式：
        # 1. 简单字符串：直接替换 $ARGUMENTS
        # 2. key=value 格式：替换 ${key}
        if '=' in args:
            # 命名参数格式：name=John email=john@example.com
            arg_dict = {}
            for pair in args.split():
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    arg_dict[key.strip()] = value.strip()
                    # 替换 ${key} 格式
                    content = content.replace(f'${{{key.strip()}}}', value.strip())
        else:
            # 简单参数格式：直接替换 $ARGUMENTS
            content = content.replace('$ARGUMENTS', args)
            content = content.replace('${ARGUMENTS}', args)

    return {
        "success": True,
        "skill": skill_name,
        "args": args,
        "content": content,
        "description": skill_obj.description,
        "allowed_tools": skill_obj.allowed_tools,
        "model": skill_obj.model,
        "user_invocable": skill_obj.user_invocable,
        "source": skill_obj.source,
    }


async def skill_discover() -> dict[str, Any]:
    """发现可用 Skills

    Returns:
        包含所有可用 skills 的列表
    """
    from loom.ecosystem.skill import SkillRegistry, SkillLoader

    # 获取或创建全局注册表
    registry = _get_or_create_registry()

    # 获取所有 skills
    skills = []
    for skill_name in registry.list_skills():
        skill_obj = registry.get(skill_name)
        if skill_obj:
            skills.append({
                "name": skill_obj.name,
                "description": skill_obj.description,
                "when_to_use": skill_obj.when_to_use,
                "user_invocable": skill_obj.user_invocable,
                "source": skill_obj.source,
                "allowed_tools": skill_obj.allowed_tools,
                "model": skill_obj.model,
            })

    return {
        "success": True,
        "skills": skills,
        "count": len(skills)
    }


# 全局注册表缓存
_global_registry = None


def _get_or_create_registry():
    """获取或创建全局 skill 注册表"""
    global _global_registry

    if _global_registry is None:
        from loom.ecosystem.skill import SkillRegistry, SkillLoader

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
