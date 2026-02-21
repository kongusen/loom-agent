"""
工具配置 (Tool Configuration)

提供工具相关的配置选项。

基于 Phase 4 配置系统

v0.5.1: 扩展为聚合配置，支持渐进式披露
"""

from pathlib import Path
from typing import Any

from pydantic import Field

from loom.config.base import LoomBaseConfig


class ToolConfig(LoomBaseConfig):
    """
    工具配置（聚合）

    v0.5.1: 扩展为聚合配置，支持渐进式披露

    聚合以下Agent.create()参数：
    - tools: 工具定义列表
    - skills: 技能ID列表
    - skills_dir: 技能目录路径
    - skill_loaders: 技能加载器列表

    运行时配置：
    - tool_timeout, max_tool_calls, etc.
    """

    # ==================== 聚合参数（来自Agent.create） ====================

    tools: list[dict[str, Any]] | None = Field(
        default=None,
        description="工具定义列表（OpenAI格式）",
    )

    skills: list[str] | None = Field(
        default=None,
        description="技能ID列表",
    )

    skills_dir: str | Path | list[str | Path] | None = Field(
        default=None,
        description="技能目录路径（SKILL.md格式）",
    )

    skill_loaders: list[Any] | None = Field(
        default=None,
        description="自定义技能加载器列表",
    )

    # ==================== 运行时配置 ====================

    enabled: bool = True
    """是否启用工具系统"""

    auto_register: bool = True
    """是否自动注册工具"""

    tool_timeout: int = 30
    """单个工具的默认超时时间（秒）"""

    max_tool_calls: int = 10
    """单次对话中允许的最大工具调用次数"""

    require_confirmation: bool = False
    """是否需要用户确认才能执行工具"""

    allowed_tools: list[str] | None = None
    """允许使用的工具列表（None 表示允许所有）"""

    blocked_tools: list[str] | None = None
    """禁止使用的工具列表"""

    enable_tool_cache: bool = True
    """是否启用工具结果缓存"""

    cache_ttl: int = 300
    """缓存过期时间（秒）"""
