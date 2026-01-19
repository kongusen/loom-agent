"""
工具配置 (Tool Configuration)

提供工具相关的配置选项。

基于 Phase 4 配置系统
"""

from loom.config.base import LoomBaseConfig


class ToolConfig(LoomBaseConfig):
    """
    工具配置

    管理工具的注册和使用
    """

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
