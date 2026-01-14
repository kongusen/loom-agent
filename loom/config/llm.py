"""
LLM Configuration System

系统化的 LLM 配置体系，支持：
- 基础连接配置
- 生成参数配置
- 流式输出配置
- 结构化输出配置
- 工具调用配置
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ConnectionConfig(BaseModel):
    """连接配置"""
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="API Base URL")
    timeout: float = Field(60.0, description="请求超时时间（秒）")
    max_retries: int = Field(3, description="最大重试次数")
    organization: Optional[str] = Field(None, description="组织 ID（OpenAI）")


class GenerationConfig(BaseModel):
    """生成参数配置"""
    model: str = Field("gpt-4", description="模型名称")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top P 采样")
    max_tokens: Optional[int] = Field(None, description="最大生成 Token 数")
    stop: Optional[List[str]] = Field(None, description="停止序列")
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="存在惩罚")
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="频率惩罚")
    n: int = Field(1, description="生成数量")
    seed: Optional[int] = Field(None, description="随机种子（可复现）")
    user: Optional[str] = Field(None, description="用户标识（追踪）")


class StreamConfig(BaseModel):
    """流式输出配置"""
    enabled: bool = Field(True, description="是否启用流式输出")
    chunk_size: int = Field(1, description="流式块大小")
    buffer_size: int = Field(0, description="缓冲区大小（0=无缓冲）")
    include_usage: bool = Field(False, description="是否包含 Token 使用统计")


class StructuredOutputConfig(BaseModel):
    """
    结构化输出配置

    支持两种配置方式：

    1. 声明式配置（Declarative）：
        StructuredOutputConfig(
            enabled=True,
            format="json_object"
        )

    2. Schema 方式配置（Schema-based）：
        StructuredOutputConfig(
            enabled=True,
            format="json_schema",
            schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"}
                },
                "required": ["name"]
            },
            schema_name="UserInfo"
        )
    """
    enabled: bool = Field(False, description="是否启用结构化输出")
    format: Literal["json", "json_object", "json_schema", "text"] = Field(
        "text",
        description="输出格式：json_object（声明式）或 json_schema（Schema方式）"
    )
    json_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema 定义（用于 json_schema 格式）"
    )
    schema_name: Optional[str] = Field(
        None,
        description="Schema 名称（用于 json_schema 格式）"
    )
    strict: bool = Field(True, description="严格模式（OpenAI Structured Outputs）")

    def to_openai_format(self) -> Optional[Dict[str, Any]]:
        """
        转换为 OpenAI response_format 格式

        Returns:
            OpenAI 格式的 response_format 参数
        """
        if not self.enabled:
            return None

        if self.format == "json_object":
            # 声明式配置
            return {"type": "json_object"}

        elif self.format == "json_schema":
            # Schema 方式配置
            if not self.json_schema:
                raise ValueError("json_schema format requires schema to be provided")

            return {
                "type": "json_schema",
                "json_schema": {
                    "name": self.schema_name or "response",
                    "schema": self.json_schema,
                    "strict": self.strict
                }
            }

        elif self.format == "json":
            # 兼容旧格式
            return {"type": "json_object"}

        return None


class ToolConfig(BaseModel):
    """工具调用配置"""
    tool_choice: Literal["auto", "none", "required"] = Field(
        "auto",
        description="工具选择策略"
    )
    parallel_tool_calls: bool = Field(True, description="是否允许并行工具调用")
    tool_timeout: float = Field(30.0, description="工具调用超时（秒）")


class AdvancedConfig(BaseModel):
    """高级配置"""
    logprobs: bool = Field(False, description="是否返回 log probabilities")
    top_logprobs: Optional[int] = Field(None, description="返回 top N logprobs")
    logit_bias: Optional[Dict[str, float]] = Field(
        None,
        description="Token 偏置"
    )


class LLMConfig(BaseModel):
    """
    完整的 LLM 配置体系

    Example:
        # 基础配置
        config = LLMConfig(
            connection=ConnectionConfig(api_key="sk-..."),
            generation=GenerationConfig(model="gpt-4", temperature=0.7)
        )

        # 流式输出配置
        config = LLMConfig(
            stream=StreamConfig(enabled=True, buffer_size=10)
        )

        # 结构化输出配置
        config = LLMConfig(
            structured_output=StructuredOutputConfig(
                enabled=True,
                format="json_object",
                schema={"type": "object", "properties": {...}}
            )
        )
    """
    connection: ConnectionConfig = Field(
        default_factory=ConnectionConfig,
        description="连接配置"
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="生成参数配置"
    )
    stream: StreamConfig = Field(
        default_factory=StreamConfig,
        description="流式输出配置"
    )
    structured_output: StructuredOutputConfig = Field(
        default_factory=StructuredOutputConfig,
        description="结构化输出配置"
    )
    tool: ToolConfig = Field(
        default_factory=ToolConfig,
        description="工具调用配置"
    )
    advanced: AdvancedConfig = Field(
        default_factory=AdvancedConfig,
        description="高级配置"
    )

    def to_openai_kwargs(self) -> Dict[str, Any]:
        """转换为 OpenAI API 参数"""
        kwargs = {
            "model": self.generation.model,
            "temperature": self.generation.temperature,
            "top_p": self.generation.top_p,
        }

        if self.generation.max_tokens:
            kwargs["max_tokens"] = self.generation.max_tokens
        if self.generation.stop:
            kwargs["stop"] = self.generation.stop
        if self.generation.presence_penalty != 0.0:
            kwargs["presence_penalty"] = self.generation.presence_penalty
        if self.generation.frequency_penalty != 0.0:
            kwargs["frequency_penalty"] = self.generation.frequency_penalty
        if self.generation.n != 1:
            kwargs["n"] = self.generation.n
        if self.generation.seed:
            kwargs["seed"] = self.generation.seed
        if self.generation.user:
            kwargs["user"] = self.generation.user

        # 流式配置
        if self.stream.enabled:
            kwargs["stream"] = True
            if self.stream.include_usage:
                kwargs["stream_options"] = {"include_usage": True}

        # 结构化输出配置
        if self.structured_output.enabled:
            if self.structured_output.format == "json_object":
                kwargs["response_format"] = {"type": "json_object"}
            elif self.structured_output.json_schema:
                kwargs["response_format"] = {
                    "type": "json_schema",
                    "json_schema": self.structured_output.json_schema
                }

        # 高级配置
        if self.advanced.logprobs:
            kwargs["logprobs"] = True
            if self.advanced.top_logprobs:
                kwargs["top_logprobs"] = self.advanced.top_logprobs
        if self.advanced.logit_bias:
            kwargs["logit_bias"] = self.advanced.logit_bias

        return kwargs
