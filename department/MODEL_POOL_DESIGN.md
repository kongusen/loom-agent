# 模型池设计文档

> 注意：本文件部分示例来源于 legacy `lexicon_agent`，该模块已移除。Loom 对应实现为 `loom.llm.pool.ModelPool` 与 `loom.llm.config.LLMCapabilities`，接口命名略有差异，迁移时请以 Loom 实际 API 为准。

## 概述

基于现有 Lexicon Agent 架构的多模型管理系统，提供框架级的模型选择和切换能力。

## 设计原则

### 1. 框架 vs 应用

**这是一个框架，不是应用**

- **框架提供**: 机制、接口、默认实现
- **用户决定**: 配置、策略、扩展

### 2. 职责分离

```python
# 框架职责
- 模型池管理（添加、删除、查询）
- 能力匹配机制（requirements → model）
- 选择器接口（可扩展）
- 与 AgentController 集成

# 用户职责
- 配置具体模型（OpenAI, Anthropic, Local, etc.）
- 定义模型能力（supports_vision, max_tokens, etc.）
- （可选）自定义选择策略
```

## 核心组件

### 1. ModelCapabilities - 模型能力描述

```python
@dataclass
class ModelCapabilities:
    # 标准能力（框架定义）
    supports_tools: bool = False
    supports_vision: bool = False
    supports_streaming: bool = True
    max_tokens: int = 4096
    context_window: int = 4096

    # 性能指标
    avg_latency_ms: float = 1000.0
    cost_per_1k_tokens: float = 0.01

    # 自定义能力（用户扩展）
    custom_capabilities: Dict[str, Any] = field(default_factory=dict)
```

**设计亮点：**
- 框架定义常见能力字段
- 用户可以通过 `custom_capabilities` 自由扩展
- 不限制用户只能使用预定义的能力

### 2. ModelConfig - 模型配置

```python
@dataclass
class ModelConfig:
    alias: str              # 用户定义的别名
    provider: str           # 提供商（openai, anthropic, local, etc.）
    model_name: str         # 模型名称
    api_key: Optional[str]
    base_url: Optional[str]
    capabilities: ModelCapabilities
    extra_config: Dict[str, Any]
```

**设计亮点：**
- 用户完全自由命名（alias）
- 支持任意提供商（不硬编码）
- 支持本地模型（base_url）

### 3. ModelSelector - 选择器接口

```python
class ModelSelector(ABC):
    @abstractmethod
    def select_model(
        self,
        available_models: List[ModelConfig],
        requirements: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[ModelConfig]:
        """根据需求选择模型"""
        pass
```

**框架提供默认实现：**
- `CapabilityBasedSelector` - 基于能力匹配

**用户可以自定义：**
```python
class CostAwareSelector(ModelSelector):
    """总是选择最便宜的模型"""
    def select_model(self, ...):
        return min(models, key=lambda m: m.capabilities.cost_per_1k_tokens)

class LatencyAwareSelector(ModelSelector):
    """总是选择最快的模型"""
    def select_model(self, ...):
        return min(models, key=lambda m: m.capabilities.avg_latency_ms)
```

### 4. ModelPool - 模型池

```python
class ModelPool:
    def __init__(self, selector: ModelSelector, default_alias: str)

    # 模型管理
    def add(alias, provider, model_name, capabilities, ...) -> ModelPool
    def get(alias) -> ModelConfig
    def remove(alias) -> bool

    # 模型选择
    def select(requirements, context) -> ModelConfig
    def get_default() -> ModelConfig

    # 查询
    def list_models() -> List[Dict]
```

## 集成架构

### 与现有系统的集成

```
AgentController (六阶段流程)
    ↓
StreamingGenerator (LLM交互)
    ↓
ModelPool (模型管理) ← 新增
    ↓
LLMProvider (实际调用)
```

### 修改点

**1. StreamingGenerator 初始化**

```python
# 旧接口（向后兼容）
StreamingGenerator(llm_provider=provider)

# 新接口（支持模型池）
StreamingGenerator(model_pool=pool)
```

**2. 自动模型选择**

```python
async def stream_response(
    self,
    user_message: str,
    context: ManagedContext,
    available_tools: List[str],
    model_requirements: Optional[Dict[str, Any]] = None  # ← 新增
) -> AsyncIterator[Dict[str, Any]]:
    # 1. 选择合适的模型
    llm_provider = await self._select_provider(...)

    # 2. 使用选中的模型生成响应
    async for chunk in llm_provider.generate_stream(...):
        yield chunk
```

**3. 自动推断需求**

```python
def _infer_requirements(self, user_message, available_tools, context):
    """框架根据任务特征自动推断需求"""
    requirements = {}

    # 需要工具？
    if available_tools:
        requirements["supports_tools"] = True

    # 需要视觉？
    if "图片" in user_message or "image" in user_message:
        requirements["supports_vision"] = True

    # 需要大上下文？
    if len(context) > 50000:
        requirements["min_context_window"] = 32000

    return requirements
```

## 使用示例

### 示例1：基础配置

```python
from lexicon_agent.core.model_pool import ModelPool, ModelCapabilities

# 创建模型池
pool = ModelPool()

# 添加模型
pool.add(
    alias="default",
    provider="openai",
    model_name="gpt-3.5-turbo",
    capabilities=ModelCapabilities(
        supports_tools=True,
        max_tokens=4096,
        context_window=4096,
        cost_per_1k_tokens=0.002
    ),
    api_key="your-key"
)

pool.add(
    alias="vision",
    provider="openai",
    model_name="gpt-4-vision",
    capabilities=ModelCapabilities(
        supports_vision=True,  # 支持视觉
        max_tokens=4096,
        context_window=8192,
        cost_per_1k_tokens=0.04
    )
)

pool.add(
    alias="large-context",
    provider="anthropic",
    model_name="claude-3-opus",
    capabilities=ModelCapabilities(
        context_window=200000,  # 大上下文
        cost_per_1k_tokens=0.015
    )
)
```

### 示例2：自动选择

```python
# 场景1：普通任务
model = pool.select({})
# → 选择 default (成本最低)

# 场景2：需要视觉
model = pool.select({"supports_vision": True})
# → 选择 vision

# 场景3：需要大上下文
model = pool.select({"min_context_window": 50000})
# → 选择 large-context
```

### 示例3：与Agent集成

```python
from lexicon_agent.core.agent import AgentController, StreamingGenerator

# 创建带模型池的生成器
streaming_generator = StreamingGenerator(model_pool=pool)

# 创建Agent（六阶段流程）
agent = AgentController(
    context_engine=...,
    context_processor=...,
    context_manager=...,
    streaming_generator=streaming_generator  # ← 使用模型池
)

# Agent 运行时会自动选择合适的模型
async for event in agent.stream_run(
    user_message="请分析这张图片",  # → 自动选择vision模型
    session_context=...
):
    print(event)
```

### 示例4：自定义选择器

```python
from lexicon_agent.core.model_pool import ModelSelector

class MyCustomSelector(ModelSelector):
    def select_model(self, available_models, requirements, context):
        # 自定义选择逻辑
        # 例如：根据时间段选择不同的模型
        import datetime
        hour = datetime.datetime.now().hour

        if 9 <= hour <= 17:  # 工作时间
            # 优先选择快速模型
            return min(models, key=lambda m: m.capabilities.avg_latency_ms)
        else:  # 非工作时间
            # 优先选择便宜模型
            return min(models, key=lambda m: m.capabilities.cost_per_1k_tokens)

# 使用自定义选择器
pool = ModelPool(selector=MyCustomSelector())
```

### 示例5：框架灵活性

```python
# 用户可以定义任意能力

# 本地模型
pool.add(
    "local-llama",
    provider="local",
    model_name="llama-3-70b",
    capabilities=ModelCapabilities(
        custom_capabilities={
            "runs_locally": True,
            "supports_chinese": True,
            "gpu_required": True
        }
    ),
    base_url="http://localhost:8000"
)

# 专用模型
pool.add(
    "sql-expert",
    provider="custom",
    model_name="my-sql-model",
    capabilities=ModelCapabilities(
        custom_capabilities={
            "specialized_for": "sql_generation",
            "accuracy": 0.95,
            "supports_dialects": ["postgresql", "mysql"]
        }
    )
)

# 选择时使用自定义能力
model = pool.select({
    "specialized_for": "sql_generation"
})
# → 选择 sql-expert
```

## 扩展点

### 1. Provider工厂

```python
# TODO: 实现provider工厂
class ProviderFactory:
    @staticmethod
    def create_provider(model_config: ModelConfig) -> LLMProvider:
        if model_config.provider == "openai":
            return OpenAIProvider(...)
        elif model_config.provider == "anthropic":
            return AnthropicProvider(...)
        elif model_config.provider == "local":
            return LocalProvider(...)
        else:
            raise ValueError(f"Unknown provider: {model_config.provider}")
```

### 2. 动态能力检测

```python
# TODO: 自动检测模型能力
class CapabilityDetector:
    @staticmethod
    async def detect(provider: LLMProvider) -> ModelCapabilities:
        """自动检测模型支持的能力"""
        pass
```

### 3. 模型预热

```python
# TODO: 预热机制
class ModelPool:
    async def warmup(self, alias: str):
        """预先加载模型，减少首次调用延迟"""
        pass
```

### 4. 性能追踪

```python
# TODO: 追踪每个模型的实际性能
class ModelPool:
    def get_performance_stats(self, alias: str) -> Dict[str, Any]:
        """获取模型的实际使用统计"""
        return {
            "avg_latency": ...,
            "success_rate": ...,
            "total_tokens": ...,
            "total_cost": ...
        }
```

## 设计优势

### 1. 框架级设计

✅ **机制而非策略**
- 框架提供能力匹配机制
- 用户决定选择策略

✅ **灵活而非限制**
- 不限制模型提供商
- 不限制能力类型
- 不限制选择逻辑

### 2. 架构集成

✅ **无缝集成**
- 与现有 AgentController 兼容
- 向后兼容旧接口
- 渐进式迁移

✅ **六阶段协同**
```
Phase 1: 上下文检索 → 评估上下文大小
Phase 2: 上下文处理 → 计算token需求
Phase 3: LLM流式响应 → 选择合适模型 ← 这里！
Phase 4: 工具编排 → 使用支持工具的模型
Phase 5: 结果聚合 → 记录模型使用
Phase 6: 递归控制 → 可以切换模型
```

### 3. 智能选择

✅ **自动推断**
- 根据任务特征推断需求
- 用户无需显式指定

✅ **显式控制**
- 用户可以覆盖自动推断
- 精确控制模型选择

### 4. 可扩展性

✅ **自定义选择器**
```python
class MySelector(ModelSelector): ...
```

✅ **自定义能力**
```python
custom_capabilities={"my_feature": True}
```

✅ **自定义提供商**
```python
provider="my_custom_provider"
```

## 最佳实践

### 1. 模型配置

```python
# ✅ 好的做法
pool.add(
    "fast-cheap",          # 清晰的别名
    provider="openai",
    model_name="gpt-3.5-turbo",
    capabilities=ModelCapabilities(
        # 明确标注能力
        supports_tools=True,
        context_window=4096,
        # 准确的性能指标
        avg_latency_ms=800,
        cost_per_1k_tokens=0.002
    )
)

# ❌ 不好的做法
pool.add(
    "model1",              # 不清晰的别名
    provider="openai",
    model_name="gpt-3.5-turbo",
    capabilities=ModelCapabilities()  # 没有配置能力
)
```

### 2. 需求定义

```python
# ✅ 好的做法
requirements = {
    "supports_vision": True,      # 明确需要视觉
    "min_context_window": 8000    # 明确上下文需求
}

# ❌ 不好的做法
requirements = {
    "model_name": "gpt-4-vision"  # 不应该指定具体模型
}
```

### 3. 选择器实现

```python
# ✅ 好的做法
class MySelector(ModelSelector):
    def select_model(self, available_models, requirements, context):
        # 1. 先过滤满足能力的模型
        capable = [m for m in available_models
                   if m.capabilities.meets_requirements(requirements)]

        # 2. 再应用自定义逻辑
        return self._custom_logic(capable, context)

# ❌ 不好的做法
class MySelector(ModelSelector):
    def select_model(self, available_models, requirements, context):
        # 忽略requirements，直接选择
        return available_models[0]
```

## 未来改进

### 短期（v1.1）

- [ ] 实现 ProviderFactory
- [ ] 支持异步能力检测
- [ ] 添加模型使用统计

### 中期（v1.2）

- [ ] 模型预热机制
- [ ] 自动故障转移
- [ ] A/B测试支持

### 长期（v2.0）

- [ ] 模型池持久化
- [ ] 分布式模型池
- [ ] 智能成本优化

## 总结

这是一个**真正的框架设计**：

1. **框架提供机制**：模型池管理 + 能力匹配 + 选择接口
2. **用户完全自由**：配置模型 + 定义能力 + 自定义策略
3. **智能自动化**：自动推断需求 + 自动选择模型
4. **完美集成**：与现有六阶段架构无缝集成
5. **高度可扩展**：支持任意提供商、能力、选择器

**核心理念：框架不应该限制用户，而应该赋能用户。**
