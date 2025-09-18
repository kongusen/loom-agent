"""
配置验证器

验证配置的有效性和一致性
"""

from typing import List, Dict, Any
from dataclasses import dataclass
from pydantic import ValidationError

from .models import LexiconAgentConfig, LLMProvider


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def validate(self, config: LexiconAgentConfig) -> ValidationResult:
        """
        验证配置
        
        Args:
            config: 配置对象
            
        Returns:
            ValidationResult: 验证结果
        """
        errors = []
        warnings = []
        
        try:
            # Pydantic 内置验证
            config.model_dump()
        except ValidationError as e:
            errors.extend([str(error) for error in e.errors()])
        
        # 自定义验证规则
        errors.extend(self._validate_llm_config(config))
        errors.extend(self._validate_context_config(config))
        errors.extend(self._validate_tool_config(config))
        errors.extend(self._validate_performance_config(config))
        errors.extend(self._validate_security_config(config))
        
        # 警告检查
        warnings.extend(self._check_warnings(config))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _validate_llm_config(self, config: LexiconAgentConfig) -> List[str]:
        """验证LLM配置"""
        errors = []
        llm_config = config.llm
        
        # 检查必需的配置（如果有API密钥或API base，说明是实际使用，需要验证）
        if llm_config.provider == LLMProvider.CUSTOM:
            if llm_config.api_key or llm_config.api_base:  # 只在有具体配置时验证
                if not llm_config.api_base:
                    errors.append("Custom LLM provider requires api_base")
                if not llm_config.model:
                    errors.append("Custom LLM provider requires model")
        
        # 检查OpenAI配置（如果指定了模型，说明是实际使用，需要验证）
        if llm_config.provider == LLMProvider.OPENAI:
            if llm_config.model and llm_config.model != "gpt-3.5-turbo":  # 只在实际配置时验证
                if not llm_config.api_key:
                    errors.append("OpenAI provider requires api_key")
        
        # 检查Azure OpenAI配置
        if llm_config.provider == LLMProvider.AZURE_OPENAI:
            if not llm_config.api_key:
                errors.append("Azure OpenAI provider requires api_key")
            if not llm_config.api_base:
                errors.append("Azure OpenAI provider requires api_base")
        
        # 检查参数范围
        if llm_config.temperature < 0 or llm_config.temperature > 2:
            errors.append("Temperature must be between 0 and 2")
        
        if llm_config.max_tokens is not None and llm_config.max_tokens < 1:
            errors.append("max_tokens must be positive")
        
        if llm_config.timeout < 1:
            errors.append("timeout must be at least 1 second")
        
        return errors
    
    def _validate_context_config(self, config: LexiconAgentConfig) -> List[str]:
        """验证上下文配置"""
        errors = []
        context_config = config.context
        
        # 检查容量配置
        if context_config.max_context_length < 100:
            errors.append("max_context_length must be at least 100")
        
        if context_config.max_turns < 1:
            errors.append("max_turns must be at least 1")
        
        if context_config.max_memory_mb < 64:
            errors.append("max_memory_mb must be at least 64MB")
        
        # 检查压缩配置
        if context_config.compression_ratio < 0.1 or context_config.compression_ratio > 0.9:
            errors.append("compression_ratio must be between 0.1 and 0.9")
        
        # 检查检索配置
        if context_config.retrieval_top_k < 1:
            errors.append("retrieval_top_k must be at least 1")
        
        if context_config.retrieval_threshold < 0 or context_config.retrieval_threshold > 1:
            errors.append("retrieval_threshold must be between 0 and 1")
        
        return errors
    
    def _validate_tool_config(self, config: LexiconAgentConfig) -> List[str]:
        """验证工具配置"""
        errors = []
        tool_config = config.tools
        
        # 检查并发配置
        if tool_config.max_concurrent_tools < 1:
            errors.append("max_concurrent_tools must be at least 1")
        
        if tool_config.tool_timeout < 1:
            errors.append("tool_timeout must be at least 1 second")
        
        # 检查重试配置
        if tool_config.max_retries < 0:
            errors.append("max_retries must be non-negative")
        
        if tool_config.retry_delay < 0:
            errors.append("retry_delay must be non-negative")
        
        # 检查工具列表冲突
        enabled_set = set(tool_config.enabled_tools)
        disabled_set = set(tool_config.disabled_tools)
        conflict = enabled_set.intersection(disabled_set)
        
        if conflict:
            errors.append(f"Tools cannot be both enabled and disabled: {list(conflict)}")
        
        return errors
    
    def _validate_performance_config(self, config: LexiconAgentConfig) -> List[str]:
        """验证性能配置"""
        errors = []
        perf_config = config.performance
        
        # 检查时间配置
        if perf_config.metrics_collection_interval < 0.1:
            errors.append("metrics_collection_interval must be at least 0.1 seconds")
        
        if perf_config.optimization_interval < 60:
            errors.append("optimization_interval must be at least 60 seconds")
        
        # 检查资源限制
        if perf_config.max_memory_usage_mb < 128:
            errors.append("max_memory_usage_mb must be at least 128MB")
        
        if perf_config.max_cpu_usage_percent < 10 or perf_config.max_cpu_usage_percent > 100:
            errors.append("max_cpu_usage_percent must be between 10 and 100")
        
        # 检查响应时间配置
        if perf_config.target_response_time_ms >= perf_config.max_response_time_ms:
            errors.append("target_response_time_ms must be less than max_response_time_ms")
        
        # 检查吞吐量配置
        if perf_config.target_throughput_rps < 1:
            errors.append("target_throughput_rps must be at least 1")
        
        if perf_config.max_concurrent_requests < 1:
            errors.append("max_concurrent_requests must be at least 1")
        
        return errors
    
    def _validate_security_config(self, config: LexiconAgentConfig) -> List[str]:
        """验证安全配置"""
        errors = []
        security_config = config.security
        
        # 检查输入验证
        if security_config.max_input_length < 100:
            errors.append("max_input_length must be at least 100")
        
        # 检查速率限制
        if security_config.rate_limit_requests_per_minute < 1:
            errors.append("rate_limit_requests_per_minute must be at least 1")
        
        # 检查认证和授权的一致性
        if security_config.enable_authorization and not security_config.enable_authentication:
            errors.append("Authorization requires authentication to be enabled")
        
        return errors
    
    def _check_warnings(self, config: LexiconAgentConfig) -> List[str]:
        """检查配置警告"""
        warnings = []
        
        # 检查生产环境配置
        if config.environment == "production":
            if config.debug:
                warnings.append("Debug mode is enabled in production environment")
            
            if config.log_level.value == "DEBUG":
                warnings.append("Debug log level in production may impact performance")
            
            if not config.security.enable_authentication:
                warnings.append("Authentication is disabled in production environment")
            
            if not config.security.enable_rate_limiting:
                warnings.append("Rate limiting is disabled in production environment")
        
        # 检查性能配置
        if config.performance.max_concurrent_requests > 1000:
            warnings.append("Very high max_concurrent_requests may cause resource issues")
        
        if config.context.max_context_length > 32000:
            warnings.append("Very large max_context_length may impact performance")
        
        # 检查工具安全
        if not config.tools.enable_safety_check:
            warnings.append("Tool safety check is disabled, which may be risky")
        
        # 检查LLM配置
        if config.llm.temperature > 1.5:
            warnings.append("High temperature may cause unpredictable responses")
        
        if config.llm.max_retries > 5:
            warnings.append("High retry count may cause long delays")
        
        return warnings
    
    def validate_llm_connectivity(self, config: LexiconAgentConfig) -> ValidationResult:
        """验证LLM连接性（可选的运行时验证）"""
        errors = []
        warnings = []
        
        # 这里可以添加实际的连接测试
        # 例如：发送测试请求到LLM API
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )