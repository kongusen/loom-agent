"""
执行配置 (Execution Configuration)

提供工具执行相关的配置选项。

基于 Phase 4 配置系统
"""

from loom.config.base import LoomBaseConfig


class ExecutionConfig(LoomBaseConfig):
    """
    执行配置

    管理工具执行的行为和限制
    """

    timeout: int = 30
    """工具执行超时时间（秒）"""

    max_retries: int = 2
    """工具执行失败时的最大重试次数"""

    retry_delay: float = 1.0
    """重试之间的延迟时间（秒）"""

    parallel_execution: bool = False
    """是否允许并行执行多个工具"""

    max_parallel_tools: int = 3
    """最大并行执行的工具数量"""

    enable_sandbox: bool = True
    """是否启用沙箱环境"""

    capture_output: bool = True
    """是否捕获工具输出"""

    log_execution: bool = True
    """是否记录工具执行日志"""
