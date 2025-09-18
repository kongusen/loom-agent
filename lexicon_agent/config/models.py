"""
配置数据模型

定义框架的所有配置接口
"""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


# =============================================================================
# 枚举类型定义
# =============================================================================

class LLMProvider(str, Enum):
    """LLM提供者类型"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    CUSTOM = "custom"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"


class ContextStrategy(str, Enum):
    """上下文策略"""
    SIMPLE = "simple"
    HIERARCHICAL = "hierarchical"
    COMPRESSED = "compressed"
    ADAPTIVE = "adaptive"


class ToolExecutionMode(str, Enum):
    """工具执行模式"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"


class OrchestrationStrategy(str, Enum):
    """编排策略"""
    SINGLE = "single"
    MULTI_AGENT = "multi_agent"
    PIPELINE = "pipeline"
    REACTIVE = "reactive"


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# =============================================================================
# LLM配置
# =============================================================================

class LLMConfig(BaseModel):
    """LLM配置"""
    
    # 基础配置
    provider: LLMProvider = LLMProvider.CUSTOM
    model: str = Field(default="gpt-3.5-turbo", description="模型名称")
    api_key: Optional[str] = Field(default=None, description="API密钥")
    api_base: Optional[str] = Field(default=None, description="API基础URL")
    
    # 请求配置
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: Optional[int] = Field(default=None, ge=1, description="最大token数")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Top-p采样")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="存在惩罚")
    
    # 高级配置
    timeout: int = Field(default=60, ge=1, description="请求超时时间(秒)")
    max_retries: int = Field(default=3, ge=0, description="最大重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试延迟(秒)")
    
    # 流式配置
    stream: bool = Field(default=True, description="是否启用流式响应")
    stream_buffer_size: int = Field(default=1024, ge=1, description="流式缓冲区大小")
    
    # 工具调用配置
    enable_function_calling: bool = Field(default=True, description="是否启用函数调用")
    function_call_timeout: int = Field(default=30, ge=1, description="函数调用超时时间")
    
    # 缓存配置
    enable_cache: bool = Field(default=True, description="是否启用响应缓存")
    cache_ttl: int = Field(default=3600, ge=0, description="缓存TTL(秒)")
    
    # 自定义配置
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="自定义请求头")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="自定义参数")
    
    @validator('api_base')
    def validate_api_base(cls, v, values):
        """验证API基础URL"""
        if values.get('provider') == LLMProvider.CUSTOM and not v:
            raise ValueError("Custom provider requires api_base")
        return v


# =============================================================================
# 上下文配置  
# =============================================================================

class ContextConfig(BaseModel):
    """上下文配置"""
    
    # 策略配置
    strategy: ContextStrategy = ContextStrategy.ADAPTIVE
    
    # 容量配置
    max_context_length: int = Field(default=8000, ge=100, description="最大上下文长度")
    max_turns: int = Field(default=100, ge=1, description="最大对话轮数")
    max_memory_mb: int = Field(default=512, ge=64, description="最大内存使用(MB)")
    
    # 压缩配置
    enable_compression: bool = Field(default=True, description="是否启用上下文压缩")
    compression_ratio: float = Field(default=0.5, ge=0.1, le=0.9, description="压缩比例")
    compression_strategy: str = Field(default="importance", description="压缩策略")
    
    # 检索配置
    enable_retrieval: bool = Field(default=True, description="是否启用上下文检索")
    retrieval_top_k: int = Field(default=5, ge=1, description="检索Top-K")
    retrieval_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="检索阈值")
    
    # 缓存配置
    enable_context_cache: bool = Field(default=True, description="是否启用上下文缓存")
    cache_policy: str = Field(default="lru", description="缓存策略")
    cache_size: int = Field(default=1000, ge=10, description="缓存大小")
    
    # 优化配置
    enable_optimization: bool = Field(default=True, description="是否启用上下文优化")
    optimization_interval: int = Field(default=10, ge=1, description="优化间隔(轮)")
    
    # 自定义配置
    custom_processors: List[str] = Field(default_factory=list, description="自定义处理器")
    custom_rules: Dict[str, Any] = Field(default_factory=dict, description="自定义规则")


# =============================================================================
# 工具配置
# =============================================================================

class ToolConfig(BaseModel):
    """工具配置"""
    
    # 执行配置
    execution_mode: ToolExecutionMode = ToolExecutionMode.ADAPTIVE
    max_concurrent_tools: int = Field(default=3, ge=1, description="最大并发工具数")
    tool_timeout: int = Field(default=30, ge=1, description="工具超时时间(秒)")
    
    # 安全配置
    enable_safety_check: bool = Field(default=True, description="是否启用安全检查")
    safety_level: str = Field(default="strict", description="安全级别")
    allowed_tool_patterns: List[str] = Field(default_factory=list, description="允许的工具模式")
    blocked_tool_patterns: List[str] = Field(default_factory=list, description="阻止的工具模式")
    
    # 重试配置
    max_retries: int = Field(default=2, ge=0, description="最大重试次数")
    retry_delay: float = Field(default=1.0, ge=0.0, description="重试延迟(秒)")
    
    # 监控配置
    enable_monitoring: bool = Field(default=True, description="是否启用工具监控")
    log_tool_calls: bool = Field(default=True, description="是否记录工具调用")
    
    # 工具注册
    enabled_tools: List[str] = Field(
        default=["file_system", "web_search", "code_execution", "knowledge_base"],
        description="启用的工具列表"
    )
    disabled_tools: List[str] = Field(default_factory=list, description="禁用的工具列表")
    
    # 自定义工具配置
    custom_tools: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict, 
        description="自定义工具配置"
    )


# =============================================================================
# 编排配置
# =============================================================================

class OrchestrationConfig(BaseModel):
    """编排配置"""
    
    # 策略配置
    strategy: OrchestrationStrategy = OrchestrationStrategy.PIPELINE
    
    # Agent配置
    max_agents: int = Field(default=5, ge=1, description="最大Agent数量")
    agent_timeout: int = Field(default=60, ge=1, description="Agent超时时间(秒)")
    
    # 协调配置
    enable_coordination: bool = Field(default=True, description="是否启用Agent协调")
    coordination_strategy: str = Field(default="round_robin", description="协调策略")
    
    # 负载均衡
    enable_load_balancing: bool = Field(default=True, description="是否启用负载均衡")
    load_balance_strategy: str = Field(default="least_busy", description="负载均衡策略")
    
    # 故障处理
    enable_failover: bool = Field(default=True, description="是否启用故障转移")
    failover_threshold: int = Field(default=3, ge=1, description="故障转移阈值")
    
    # 自定义配置
    custom_strategies: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="自定义编排策略"
    )


# =============================================================================
# 性能配置
# =============================================================================

class PerformanceConfig(BaseModel):
    """性能配置"""
    
    # 监控配置
    enable_monitoring: bool = Field(default=True, description="是否启用性能监控")
    metrics_collection_interval: float = Field(default=1.0, ge=0.1, description="指标收集间隔(秒)")
    
    # 优化配置
    enable_auto_optimization: bool = Field(default=True, description="是否启用自动优化")
    optimization_interval: int = Field(default=300, ge=60, description="优化间隔(秒)")
    
    # 资源限制
    max_memory_usage_mb: int = Field(default=1024, ge=128, description="最大内存使用(MB)")
    max_cpu_usage_percent: int = Field(default=80, ge=10, le=100, description="最大CPU使用率(%)")
    
    # 响应时间配置
    target_response_time_ms: int = Field(default=1000, ge=100, description="目标响应时间(毫秒)")
    max_response_time_ms: int = Field(default=5000, ge=1000, description="最大响应时间(毫秒)")
    
    # 吞吐量配置
    target_throughput_rps: int = Field(default=10, ge=1, description="目标吞吐量(请求/秒)")
    max_concurrent_requests: int = Field(default=100, ge=1, description="最大并发请求数")
    
    # 缓存配置
    enable_result_cache: bool = Field(default=True, description="是否启用结果缓存")
    cache_size_mb: int = Field(default=256, ge=32, description="缓存大小(MB)")


# =============================================================================
# 安全配置
# =============================================================================

class SecurityConfig(BaseModel):
    """安全配置"""
    
    # 认证配置
    enable_authentication: bool = Field(default=False, description="是否启用认证")
    auth_method: str = Field(default="api_key", description="认证方法")
    
    # 授权配置
    enable_authorization: bool = Field(default=False, description="是否启用授权")
    permission_model: str = Field(default="rbac", description="权限模型")
    
    # 输入验证
    enable_input_validation: bool = Field(default=True, description="是否启用输入验证")
    max_input_length: int = Field(default=10000, ge=100, description="最大输入长度")
    
    # 输出过滤
    enable_output_filtering: bool = Field(default=True, description="是否启用输出过滤")
    sensitive_data_patterns: List[str] = Field(
        default_factory=lambda: ["password", "token", "key", "secret"],
        description="敏感数据模式"
    )
    
    # 速率限制
    enable_rate_limiting: bool = Field(default=True, description="是否启用速率限制")
    rate_limit_requests_per_minute: int = Field(default=60, ge=1, description="每分钟请求限制")
    
    # 审计日志
    enable_audit_log: bool = Field(default=True, description="是否启用审计日志")
    audit_log_level: str = Field(default="info", description="审计日志级别")


# =============================================================================
# 主配置模型
# =============================================================================

class LexiconAgentConfig(BaseModel):
    """Lexicon Agent 主配置"""
    
    # 基础配置
    agent_id: str = Field(default="lexicon_agent_default", description="Agent标识")
    version: str = Field(default="2.0.0", description="配置版本")
    
    # 日志配置
    log_level: LogLevel = LogLevel.INFO
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    log_file: Optional[str] = Field(default=None, description="日志文件路径")
    
    # 模块配置
    llm: LLMConfig = Field(default_factory=LLMConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    tools: ToolConfig = Field(default_factory=ToolConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # 环境配置
    environment: str = Field(default="development", description="运行环境")
    debug: bool = Field(default=False, description="是否启用调试模式")
    
    # 自定义配置
    custom: Dict[str, Any] = Field(default_factory=dict, description="自定义配置")
    
    class Config:
        """Pydantic配置"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # 禁止额外字段
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LexiconAgentConfig":
        """从字典创建配置"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "LexiconAgentConfig":
        """从JSON字符串创建配置"""
        return cls.model_validate_json(json_str)


# =============================================================================
# 配置模板
# =============================================================================

def create_default_config() -> LexiconAgentConfig:
    """创建默认配置"""
    return LexiconAgentConfig()


def create_development_config() -> LexiconAgentConfig:
    """创建开发环境配置"""
    config = LexiconAgentConfig()
    config.environment = "development"
    config.debug = True
    config.log_level = LogLevel.DEBUG
    config.performance.enable_monitoring = True
    config.security.enable_authentication = False
    return config


def create_production_config() -> LexiconAgentConfig:
    """创建生产环境配置"""
    config = LexiconAgentConfig()
    config.environment = "production"
    config.debug = False
    config.log_level = LogLevel.INFO
    config.performance.enable_auto_optimization = True
    config.security.enable_authentication = True
    config.security.enable_rate_limiting = True
    return config


def create_minimal_config() -> LexiconAgentConfig:
    """创建最小配置"""
    return LexiconAgentConfig(
        llm=LLMConfig(
            provider=LLMProvider.CUSTOM,
            model="gpt-3.5-turbo"
        ),
        context=ContextConfig(
            strategy=ContextStrategy.SIMPLE,
            max_context_length=4000
        ),
        tools=ToolConfig(
            execution_mode=ToolExecutionMode.SEQUENTIAL,
            enabled_tools=["file_system"]
        )
    )