# Loom Framework 完善计划

> 从简化实现到生产级实现的详细规划

---

## 📋 目录

1. [当前简化实现分析](#当前简化实现分析)
2. [LLM 统一配置与适配](#llm-统一配置与适配)
3. [完整的错误处理](#完整的错误处理)
4. [重试与熔断机制](#重试与熔断机制)
5. [缓存系统](#缓存系统)
6. [完整的测试覆盖](#完整的测试覆盖)
7. [性能优化](#性能优化)
8. [实施优先级](#实施优先级)

---

## 1. 当前简化实现分析

### 1.1 LLM 层简化点 ⚠️

#### 问题 1: 硬编码的 OpenAI 实现
**当前实现**: `loom/builtin/llms/openai.py`
```python
class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-4", ...):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
```

**问题**:
- ❌ 每个 LLM 都需要单独实现
- ❌ 缺少统一的配置管理
- ❌ 不支持动态切换模型
- ❌ 缺少模型能力自动检测

#### 问题 2: 缺少其他主流 LLM 适配器
**当前状态**:
- ✅ OpenAI (GPT-4, GPT-3.5)
- ✅ Mock, Rule (测试用)
- ❌ Anthropic Claude
- ❌ Google Gemini
- ❌ Cohere
- ❌ 本地模型 (Ollama, vLLM)
- ❌ Azure OpenAI

#### 问题 3: 缺少 LLM 能力自动检测
**当前实现**:
```python
@property
def supports_tools(self) -> bool:
    return "gpt-4" in self._model.lower() or "gpt-3.5-turbo" in self._model.lower()
```

**问题**:
- ❌ 硬编码模型名称
- ❌ 新模型需要手动更新代码
- ❌ 无法检测其他能力（function calling, vision, etc.）

---

### 1.2 向量数据库层简化点 ⚠️

#### 问题 4: 缺少连接池管理
**当前实现**: 每次创建新连接
```python
async def initialize(self) -> None:
    self.client = QdrantClient(host=self.host, port=self.port)
```

**问题**:
- ❌ 频繁创建/销毁连接
- ❌ 无连接复用
- ❌ 无连接超时管理

#### 问题 5: 缺少批量操作优化
**当前实现**: 简单的批量上传
```python
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i + batch_size]
    self.index.upsert(vectors=batch)
```

**问题**:
- ❌ 无并发批量上传
- ❌ 无失败重试
- ❌ 无进度追踪

---

### 1.3 工具系统简化点 ⚠️

#### 问题 6: 缺少工具版本管理
**当前实现**: 工具无版本信息
```python
class Calculator(BaseTool):
    name = "calculator"
    description = "..."
```

**问题**:
- ❌ 无版本控制
- ❌ 无法管理工具升级
- ❌ 无法回滚到旧版本

#### 问题 7: 缺少工具依赖管理
**当前实现**: 工具独立运行
```python
class ReadFile(BaseTool):
    async def run(self, file_path: str) -> str:
        ...
```

**问题**:
- ❌ 无法声明依赖关系
- ❌ 无法自动安装依赖
- ❌ 无法检测缺失依赖

---

### 1.4 错误处理简化点 ⚠️

#### 问题 8: 简单的异常捕获
**当前实现**:
```python
try:
    result = await tool.run(**arguments)
except Exception as e:
    return ToolResult(status="error", content=str(e))
```

**问题**:
- ❌ 丢失异常类型信息
- ❌ 无详细堆栈跟踪
- ❌ 无错误分类（可重试/不可重试）
- ❌ 无结构化错误响应

#### 问题 9: 缺少重试机制
**当前实现**: 一次失败即返回错误

**问题**:
- ❌ 网络抖动导致失败
- ❌ 临时性错误无法恢复
- ❌ 无指数退避

---

### 1.5 缓存系统简化点 ⚠️

#### 问题 10: 完全无缓存
**当前实现**: 每次都重新调用

**问题**:
- ❌ 重复的 LLM 调用浪费 token
- ❌ 重复的向量检索浪费时间
- ❌ 无 LRU 缓存

---

## 2. LLM 统一配置与适配

### 2.1 统一的 LLM 配置系统

#### 设计目标
- ✅ 支持多种 LLM 提供商
- ✅ 统一的配置接口
- ✅ 动态模型切换
- ✅ 能力自动检测

#### 实现方案

**文件**: `loom/llm_config.py`
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum

class LLMProvider(str, Enum):
    """LLM 提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    COHERE = "cohere"
    AZURE_OPENAI = "azure_openai"
    OLLAMA = "ollama"
    CUSTOM = "custom"

class LLMCapabilities(BaseModel):
    """模型能力"""
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    max_tokens: int = 4096
    context_window: int = 8192
    supports_json_mode: bool = False
    supports_system_message: bool = True

class LLMConfig(BaseModel):
    """统一的 LLM 配置"""
    provider: LLMProvider
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

    # 生成参数
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)

    # 重试配置
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0

    # 额外参数
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    # 能力（可选，自动检测）
    capabilities: Optional[LLMCapabilities] = None

    @classmethod
    def openai(
        cls,
        api_key: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        """快速创建 OpenAI 配置"""
        return cls(
            provider=LLMProvider.OPENAI,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
            **kwargs
        )

    @classmethod
    def anthropic(
        cls,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        temperature: float = 0.7,
        **kwargs
    ) -> "LLMConfig":
        """快速创建 Anthropic 配置"""
        return cls(
            provider=LLMProvider.ANTHROPIC,
            model_name=model,
            api_key=api_key,
            temperature=temperature,
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
        """快速创建 Ollama 本地模型配置"""
        return cls(
            provider=LLMProvider.OLLAMA,
            model_name=model,
            base_url=base_url,
            temperature=temperature,
            api_key=None,  # Ollama 不需要 API Key
            **kwargs
        )

    @classmethod
    def azure_openai(
        cls,
        api_key: str,
        deployment_name: str,
        endpoint: str,
        api_version: str = "2024-02-15-preview",
        **kwargs
    ) -> "LLMConfig":
        """快速创建 Azure OpenAI 配置"""
        return cls(
            provider=LLMProvider.AZURE_OPENAI,
            model_name=deployment_name,
            api_key=api_key,
            base_url=endpoint,
            extra_params={"api_version": api_version},
            **kwargs
        )
```

---

### 2.2 LLM 工厂模式

**文件**: `loom/llm/factory.py`
```python
from loom import LLMConfig, LLMProvider
from loom.interfaces.llm import BaseLLM
from typing import Dict, Type

class LLMFactory:
    """LLM 工厂 - 根据配置创建 LLM 实例"""

    _registry: Dict[LLMProvider, Type[BaseLLM]] = {}

    @classmethod
    def register(cls, provider: LLMProvider, llm_class: Type[BaseLLM]):
        """注册 LLM 实现"""
        cls._registry[provider] = llm_class

    @classmethod
    def create(cls, config: LLMConfig) -> BaseLLM:
        """根据配置创建 LLM 实例"""
        if config.provider not in cls._registry:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

        llm_class = cls._registry[config.provider]
        return llm_class.from_config(config)

# 使用示例
config = LLMConfig.openai(api_key="sk-...", model="gpt-4")
llm = LLMFactory.create(config)
```

---

### 2.3 模型能力自动检测

**文件**: `loom/llm/registry.py`
```python
from typing import Dict
from loom import LLMCapabilities

class ModelRegistry:
    """模型能力注册表"""

    # OpenAI 模型
    OPENAI_MODELS: Dict[str, LLMCapabilities] = {
        "gpt-4": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            max_tokens=8192,
            context_window=8192,
            supports_json_mode=True,
        ),
        "gpt-4-turbo": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            max_tokens=4096,
            context_window=128000,
            supports_json_mode=True,
        ),
        "gpt-4o": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            max_tokens=16384,
            context_window=128000,
            supports_json_mode=True,
        ),
        "gpt-3.5-turbo": LLMCapabilities(
            supports_tools=True,
            supports_vision=False,
            max_tokens=4096,
            context_window=16385,
            supports_json_mode=True,
        ),
    }

    # Anthropic 模型
    ANTHROPIC_MODELS: Dict[str, LLMCapabilities] = {
        "claude-3-5-sonnet-20241022": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            max_tokens=8192,
            context_window=200000,
            supports_json_mode=False,
        ),
        "claude-3-opus-20240229": LLMCapabilities(
            supports_tools=True,
            supports_vision=True,
            max_tokens=4096,
            context_window=200000,
        ),
    }

    @classmethod
    def get_capabilities(cls, provider: str, model_name: str) -> LLMCapabilities:
        """获取模型能力"""
        if provider == "openai":
            return cls.OPENAI_MODELS.get(
                model_name,
                LLMCapabilities()  # 默认能力
            )
        elif provider == "anthropic":
            return cls.ANTHROPIC_MODELS.get(
                model_name,
                LLMCapabilities()
            )
        else:
            # 未知模型，返回保守的默认能力
            return LLMCapabilities()

    @classmethod
    def supports_tools(cls, provider: str, model_name: str) -> bool:
        """快速检查是否支持工具"""
        capabilities = cls.get_capabilities(provider, model_name)
        return capabilities.supports_tools
```

---

### 2.4 统一的 BaseLLM 接口增强

**文件**: `loom/interfaces/llm.py`（增强版）
```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any, Optional
from loom import LLMConfig, LLMCapabilities

class BaseLLM(ABC):
    """增强的 LLM 基类"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._capabilities: Optional[LLMCapabilities] = config.capabilities

    @classmethod
    def from_config(cls, config: LLMConfig) -> "BaseLLM":
        """从配置创建实例"""
        return cls(config)

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        pass

    @property
    def capabilities(self) -> LLMCapabilities:
        """模型能力"""
        if self._capabilities is None:
            # 自动检测
            from loom import ModelRegistry
            self._capabilities = ModelRegistry.get_capabilities(
                self.config.provider.value,
                self.model_name
            )
        return self._capabilities

    @property
    def supports_tools(self) -> bool:
        """是否支持工具调用"""
        return self.capabilities.supports_tools

    @property
    def supports_vision(self) -> bool:
        """是否支持视觉输入"""
        return self.capabilities.supports_vision

    @abstractmethod
    async def generate(self, messages: List[Dict]) -> str:
        """生成响应"""
        pass

    @abstractmethod
    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成"""
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict]
    ) -> Dict:
        """带工具调用的生成"""
        pass
```

---

### 2.5 完整的 Anthropic Claude 适配器

**文件**: `loom/builtin/llms/anthropic.py`
```python
from __future__ import annotations
import json
from typing import Any, AsyncGenerator, Dict, List, Optional
from loom.interfaces.llm import BaseLLM
from loom import LLMConfig

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

class AnthropicLLM(BaseLLM):
    """Anthropic Claude 适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)

        if AsyncAnthropic is None:
            raise ImportError("Please install anthropic: pip install anthropic")

        self.client = AsyncAnthropic(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout,
        )
        self._model = config.model_name

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: List[Dict]) -> str:
        """生成响应"""
        # 转换消息格式（OpenAI → Anthropic）
        system_message, anthropic_messages = self._convert_messages(messages)

        response = await self.client.messages.create(
            model=self._model,
            max_tokens=self.config.max_tokens or 4096,
            temperature=self.config.temperature,
            system=system_message,
            messages=anthropic_messages,
        )

        return response.content[0].text

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成"""
        system_message, anthropic_messages = self._convert_messages(messages)

        async with self.client.messages.stream(
            model=self._model,
            max_tokens=self.config.max_tokens or 4096,
            temperature=self.config.temperature,
            system=system_message,
            messages=anthropic_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict]
    ) -> Dict:
        """带工具调用的生成"""
        system_message, anthropic_messages = self._convert_messages(messages)

        # 转换工具格式（OpenAI → Anthropic）
        anthropic_tools = self._convert_tools(tools)

        response = await self.client.messages.create(
            model=self._model,
            max_tokens=self.config.max_tokens or 4096,
            temperature=self.config.temperature,
            system=system_message,
            messages=anthropic_messages,
            tools=anthropic_tools,
        )

        # 解析响应
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content = block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        return {
            "content": content,
            "tool_calls": tool_calls if tool_calls else None,
        }

    def _convert_messages(self, messages: List[Dict]) -> tuple[str, List[Dict]]:
        """转换消息格式：OpenAI → Anthropic"""
        system_message = ""
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_message += msg["content"] + "\n"
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        return system_message.strip(), anthropic_messages

    def _convert_tools(self, tools: List[Dict]) -> List[Dict]:
        """转换工具格式：OpenAI → Anthropic"""
        anthropic_tools = []

        for tool in tools:
            func = tool["function"]
            anthropic_tools.append({
                "name": func["name"],
                "description": func["description"],
                "input_schema": func["parameters"],
            })

        return anthropic_tools
```

---

### 2.6 Ollama 本地模型适配器

**文件**: `loom/builtin/llms/ollama.py`
```python
from __future__ import annotations
import json
from typing import Any, AsyncGenerator, Dict, List
from loom.interfaces.llm import BaseLLM
from loom import LLMConfig
import aiohttp

class OllamaLLM(BaseLLM):
    """Ollama 本地模型适配器"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._model = config.model_name
        self.base_url = config.base_url or "http://localhost:11434"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: List[Dict]) -> str:
        """生成响应"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                return result["message"]["content"]

    async def stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """流式生成"""
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": self.config.temperature,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                async for line in response.content:
                    if line:
                        data = json.loads(line.decode())
                        if "message" in data:
                            yield data["message"]["content"]

    async def generate_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict]
    ) -> Dict:
        """带工具调用的生成（Ollama 需要特殊处理）"""
        # Ollama 不原生支持工具调用，需要通过提示工程模拟
        # 这里简化实现，实际需要更复杂的逻辑

        # 将工具注入到系统消息
        tool_descriptions = self._format_tools_for_prompt(tools)

        enhanced_messages = messages.copy()
        enhanced_messages.insert(0, {
            "role": "system",
            "content": f"You have access to these tools:\n{tool_descriptions}\n\n"
                      f"To use a tool, respond with JSON: {{\"tool\": \"tool_name\", \"arguments\": {{...}}}}"
        })

        response_text = await self.generate(enhanced_messages)

        # 尝试解析工具调用
        try:
            tool_call = json.loads(response_text)
            if "tool" in tool_call:
                return {
                    "content": "",
                    "tool_calls": [{
                        "id": "call_0",
                        "name": tool_call["tool"],
                        "arguments": tool_call.get("arguments", {}),
                    }]
                }
        except json.JSONDecodeError:
            pass

        return {
            "content": response_text,
            "tool_calls": None,
        }

    def _format_tools_for_prompt(self, tools: List[Dict]) -> str:
        """将工具格式化为提示文本"""
        lines = []
        for tool in tools:
            func = tool["function"]
            lines.append(f"- {func['name']}: {func['description']}")
        return "\n".join(lines)
```

---

## 3. 完整的错误处理

### 3.1 结构化错误类型

**文件**: `loom/core/errors.py`（增强版）
```python
from enum import Enum
from typing import Optional, Dict, Any

class ErrorCategory(str, Enum):
    """错误类别"""
    # 可重试错误
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    TEMPORARY_ERROR = "temporary_error"

    # 不可重试错误
    AUTHENTICATION_ERROR = "authentication_error"
    PERMISSION_ERROR = "permission_error"
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND_ERROR = "not_found_error"

    # 系统错误
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"

class LoomError(Exception):
    """Loom 基础错误"""
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN_ERROR,
        retryable: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.retryable = retryable
        self.metadata = metadata or {}
        self.original_error = original_error

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "metadata": self.metadata,
        }

# 具体错误类型
class LLMError(LoomError):
    """LLM 相关错误"""
    pass

class LLMRateLimitError(LLMError):
    """LLM 速率限制错误"""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(
            message,
            category=ErrorCategory.RATE_LIMIT_ERROR,
            retryable=True,
            metadata={"retry_after": retry_after}
        )

class ToolExecutionError(LoomError):
    """工具执行错误"""
    pass

class RetrieverError(LoomError):
    """检索器错误"""
    pass
```

---

### 3.2 错误处理装饰器

**文件**: `loom/utils/error_handling.py`
```python
import asyncio
import functools
from typing import Callable, Optional, Type
from loom.core.errors import LoomError, ErrorCategory

def with_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_categories: Optional[set[ErrorCategory]] = None,
):
    """重试装饰器"""

    if retryable_categories is None:
        retryable_categories = {
            ErrorCategory.NETWORK_ERROR,
            ErrorCategory.TIMEOUT_ERROR,
            ErrorCategory.RATE_LIMIT_ERROR,
            ErrorCategory.TEMPORARY_ERROR,
        }

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except LoomError as e:
                    last_error = e

                    # 检查是否可重试
                    if not e.retryable or e.category not in retryable_categories:
                        raise

                    # 最后一次尝试，不再重试
                    if attempt == max_retries:
                        raise

                    # 等待后重试
                    await asyncio.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                except Exception as e:
                    # 非 LoomError，包装后抛出
                    raise LoomError(
                        str(e),
                        category=ErrorCategory.UNKNOWN_ERROR,
                        original_error=e
                    )

            raise last_error

        return wrapper
    return decorator
```

---

## 4. 重试与熔断机制

### 4.1 熔断器实现

**文件**: `loom/resilience/circuit_breaker.py`
```python
import asyncio
import time
from enum import Enum
from typing import Callable, Optional

class CircuitState(str, Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 熔断（拒绝请求）
    HALF_OPEN = "half_open"  # 半开（尝试恢复）

class CircuitBreaker:
    """熔断器"""

    def __init__(
        self,
        failure_threshold: int = 5,  # 失败阈值
        success_threshold: int = 2,  # 恢复阈值
        timeout: float = 60.0,       # 熔断超时（秒）
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None

    async def call(self, func: Callable, *args, **kwargs):
        """调用函数（带熔断保护）"""

        # 检查熔断器状态
        if self.state == CircuitState.OPEN:
            # 检查是否可以尝试恢复
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 成功
            self._on_success()
            return result

        except Exception as e:
            # 失败
            self._on_failure()
            raise

    def _on_success(self):
        """处理成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                # 恢复正常
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            # CLOSED 状态，重置失败计数
            self.failure_count = 0

    def _on_failure(self):
        """处理失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            # 触发熔断
            self.state = CircuitState.OPEN
```

---

## 5. 缓存系统

### 5.1 LLM 缓存

**文件**: `loom/caching/llm_cache.py`
```python
import hashlib
import json
from typing import Optional, Dict, Any
from functools import lru_cache

class LLMCache:
    """LLM 响应缓存"""

    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, str] = {}
        self.max_size = max_size

    def get(
        self,
        model: str,
        messages: list[Dict],
        temperature: float,
    ) -> Optional[str]:
        """获取缓存"""
        key = self._generate_key(model, messages, temperature)
        return self._cache.get(key)

    def set(
        self,
        model: str,
        messages: list[Dict],
        temperature: float,
        response: str,
    ):
        """设置缓存"""
        key = self._generate_key(model, messages, temperature)

        # LRU 淘汰
        if len(self._cache) >= self.max_size:
            # 删除最旧的一个
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = response

    def _generate_key(
        self,
        model: str,
        messages: list[Dict],
        temperature: float,
    ) -> str:
        """生成缓存键"""
        content = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }, sort_keys=True)

        return hashlib.md5(content.encode()).hexdigest()
```

---

## 6. 实施优先级

### P0 - 核心功能（必须实现）

| 任务 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| **LLM 统一配置** | P0 | 3天 | 待实现 |
| **Anthropic Claude 适配器** | P0 | 2天 | 待实现 |
| **错误分类与结构化** | P0 | 2天 | 待实现 |
| **基础重试机制** | P0 | 1天 | 待实现 |

### P1 - 重要功能（应该实现）

| 任务 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| **Ollama 本地模型** | P1 | 2天 | 待实现 |
| **模型能力注册表** | P1 | 1天 | 待实现 |
| **熔断器** | P1 | 2天 | 待实现 |
| **LLM 缓存** | P1 | 2天 | 待实现 |
| **连接池管理** | P1 | 2天 | 待实现 |

### P2 - 可选功能（可以实现）

| 任务 | 优先级 | 工作量 | 状态 |
|------|--------|--------|------|
| **Google Gemini** | P2 | 2天 | 待实现 |
| **Cohere** | P2 | 2天 | 待实现 |
| **工具版本管理** | P2 | 3天 | 待实现 |
| **批量操作优化** | P2 | 2天 | 待实现 |

---

## 7. 实施步骤

### Phase 1: LLM 层完善（第1周）

**目标**：统一 LLM 配置，支持多种模型

**任务**：
1. 创建 `loom/llm_config.py` - 统一配置
2. 创建 `loom/llm_factory.py` - 工厂模式
3. 创建 `loom/model_registry.py` - 能力注册
4. 重构 `loom/builtin/llms/openai.py` - 适配新接口
5. 实现 `loom/builtin/llms/anthropic.py` - Claude 适配器
6. 实现 `loom/builtin/llms/ollama.py` - 本地模型

**验收标准**：
- ✅ 支持 OpenAI, Anthropic, Ollama
- ✅ 统一配置接口
- ✅ 自动能力检测
- ✅ 通过单元测试

### Phase 2: 错误处理完善（第2周）

**目标**：结构化错误处理，重试与熔断

**任务**：
1. 增强 `loom/core/errors.py` - 错误分类
2. 创建 `loom/utils/error_handling.py` - 重试装饰器
3. 创建 `loom/resilience/circuit_breaker.py` - 熔断器
4. 集成到 `AgentExecutor` 和 `ToolPipeline`

**验收标准**：
- ✅ 错误分类完整
- ✅ 自动重试可配置
- ✅ 熔断器保护关键服务
- ✅ 通过集成测试

### Phase 3: 性能优化（第3周）

**目标**：缓存、连接池、批量优化

**任务**：
1. 创建 `loom/caching/llm_cache.py` - LLM 缓存
2. 创建 `loom/caching/retriever_cache.py` - 检索缓存
3. 优化向量数据库连接池
4. 批量操作并发优化

**验收标准**：
- ✅ 缓存命中率 >50%
- ✅ 响应时间降低 30%+
- ✅ 通过性能测试

---

## 8. 总结

### 当前状态
- ✅ 核心功能完整（100%）
- ⚠️ 简化实现（部分生产级功能缺失）
- ✅ 可用于原型开发
- ⚠️ 生产环境需要完善

### 完善后状态
- ✅ 生产级实现（100%）
- ✅ 多 LLM 支持
- ✅ 完整错误处理
- ✅ 性能优化
- ✅ 可用于企业生产

### 预计时间
- **Phase 1**: 1 周（LLM 层）
- **Phase 2**: 1 周（错误处理）
- **Phase 3**: 1 周（性能优化）
- **总计**: 3 周

---

**下一步行动**：从 Phase 1 开始，优先完善 LLM 统一配置和 Anthropic 适配器。
