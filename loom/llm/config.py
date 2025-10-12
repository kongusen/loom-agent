"""LLM 统一配置系统

提供统一的接口来配置各种 LLM 提供商，支持：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- Cohere
- Azure OpenAI
- Ollama (本地模型)
- 自定义模型
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum


class LLMProvider(str, Enum):
    """LLM 提供商枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class LLMCapabilities(BaseModel):
    """模型能力描述"""
    supports_tools: bool = Field(default=False, description="是否支持工具调用/Function Calling")
    supports_vision: bool = Field(default=False, description="是否支持视觉输入")
    supports_streaming: bool = Field(default=True, description="是否支持流式输出")
    supports_json_mode: bool = Field(default=False, description="是否支持 JSON 模式")
    supports_system_message: bool = Field(default=True, description="是否支持系统消息")
    max_tokens: int = Field(default=4096, description="最大输出 token 数")
    context_window: int = Field(default=8192, description="上下文窗口大小")


class LLMConfig(BaseModel):
    """统一的 LLM 配置

    示例:
        # OpenAI
        config = LLMConfig.openai(api_key="sk-...", model="gpt-4")

        # Anthropic
        config = LLMConfig.anthropic(api_key="sk-ant-...", model="claude-3-5-sonnet-20241022")

        # Ollama 本地模型
        config = LLMConfig.ollama(model="llama3", base_url="http://localhost:11434")

        # 自定义模型
        config = LLMConfig.custom(
            model_name="my-model",
            base_url="https://my-api.com",
            api_key="..."
        )
    """

    # 基本配置
    provider: LLMProvider = Field(description="LLM 提供商")
    model_name: str = Field(description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API Key（如果需要）")
    base_url: Optional[str] = Field(default=None, description="API 基础 URL（用于代理或自定义端点）")

    # 生成参数
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数，控制随机性")
    max_tokens: Optional[int] = Field(default=None, description="最大输出 token 数")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="核采样参数")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")

    # 可靠性配置
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试延迟（秒）")
    timeout: float = Field(default=60.0, ge=0.0, description="请求超时时间（秒）")

    # 额外参数（特定提供商的特殊参数）
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外的提供商特定参数")

    # 模型能力（可选，用于自动检测）
    capabilities: Optional[LLMCapabilities] = Field(default=None, description="模型能力，不指定则自动检测")

    class Config:
        use_enum_values = True

    # ==================== 快速配置方法 ====================

    @classmethod
    def openai(
        cls,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.OPENAI,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=base_url,
            **kwargs
        )

    @classmethod
    def anthropic(
        cls,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.ANTHROPIC,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
            **kwargs
        )

    @classmethod
    def ollama(
        cls,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.OLLAMA,
            model_name=model,
            base_url=base_url,
            temperature=temperature,
            api_key=None,
            **kwargs
        )

    @classmethod
    def azure_openai(
        cls,
        api_key: str,
        deployment_name: str,
        endpoint: str,
        api_version: str = "2024-02-15-preview",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.AZURE_OPENAI,
            model_name=deployment_name,
            api_key=api_key,
            base_url=endpoint,
            temperature=temperature,
            extra_params={"api_version": api_version},
            **kwargs
        )

    @classmethod
    def google(
        cls,
        api_key: str,
        model: str = "gemini-pro",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.GOOGLE,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )

    @classmethod
    def cohere(
        cls,
        api_key: str,
        model: str = "command-r-plus",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.COHERE,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )

    @classmethod
    def custom(
        cls,
        model_name: str,
        base_url: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        capabilities: Optional[LLMCapabilities] = None,
        **kwargs
    ) -> "LLMConfig":
        return cls(
            provider=LLMProvider.CUSTOM,
            model_name=model_name,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            capabilities=capabilities,
            **kwargs
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        return cls(**data)

    def __repr__(self) -> str:
        return f"LLMConfig(provider={self.provider}, model={self.model_name})"

