"""
LLM 配置 (LLM Configuration)

提供 LLM 相关的配置选项，统一 LLM 配置管理。

基于 Phase 4 配置系统
"""

from loom.config.base import LoomBaseConfig


class LLMConfig(LoomBaseConfig):
    """
    LLM 配置

    统一管理 LLM 提供者的配置
    """

    provider: str = "openai"
    """LLM 提供者名称 (openai, anthropic, deepseek, etc.)"""

    model: str = "gpt-4"
    """模型名称"""

    api_key: str | None = None
    """API 密钥（可选，也可以从环境变量读取）"""

    base_url: str | None = None
    """API 基础 URL（可选，用于自定义端点）"""

    temperature: float = 0.7
    """温度参数 (0.0-2.0)"""

    max_tokens: int | None = None
    """最大 token 数（可选）"""

    timeout: int = 60
    """请求超时时间（秒）"""

    max_retries: int = 3
    """最大重试次数"""

    stream: bool = False
    """是否使用流式响应"""
