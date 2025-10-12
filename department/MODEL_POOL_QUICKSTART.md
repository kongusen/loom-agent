# 模型池快速入门

> 注意：本文件仍包含对 legacy `lexicon_agent` 模块的引用，现已移除。请参考 `loom.llm.pool.ModelPool` 与 `loom.LLMCapabilities` 进行迁移。

## 5分钟上手模型池

### 步骤1：安装和导入

```python
from lexicon_agent.core.model_pool import ModelPool, ModelCapabilities
from lexicon_agent.core.agent import AgentController, StreamingGenerator
```

### 步骤2：创建模型池并添加模型

```python
# 创建模型池
pool = ModelPool()

# 添加默认模型（快速且便宜）
pool.add(
    alias="default",
    provider="openai",
    model_name="gpt-3.5-turbo",
    capabilities=ModelCapabilities(
        supports_tools=True,
        context_window=4096,
        cost_per_1k_tokens=0.002
    ),
    api_key="your-openai-api-key"
)

# 添加视觉模型
pool.add(
    alias="vision",
    provider="openai",
    model_name="gpt-4-vision",
    capabilities=ModelCapabilities(
        supports_vision=True,
        context_window=8192,
        cost_per_1k_tokens=0.04
    ),
    api_key="your-openai-api-key"
)

# 添加大上下文模型
pool.add(
    alias="large-context",
    provider="anthropic",
    model_name="claude-3-opus",
    capabilities=ModelCapabilities(
        context_window=200000,
        cost_per_1k_tokens=0.015
    ),
    api_key="your-anthropic-api-key"
)
```

### 步骤3：使用Agent（自动模型选择）

```python
# 创建带模型池的StreamingGenerator
streaming_generator = StreamingGenerator(model_pool=pool)

# 创建Agent
agent = AgentController(
    context_engine=your_context_engine,
    context_processor=your_context_processor,
    context_manager=your_context_manager,
    streaming_generator=streaming_generator
)

# 运行Agent - 框架会自动选择合适的模型！
async for event in agent.stream_run(
    user_message="请分析这张图片的内容",
    session_context=your_session_context
):
    if event.type == AgentEventType.RESPONSE_DELTA:
        print(event.content, end="", flush=True)
```

**就是这么简单！** Agent会自动：
1. 检测到消息中有"图片"关键词
2. 推断需要 `supports_vision=True`
3. 选择 `vision` 模型
4. 使用选中的模型处理请求

## 常见场景

### 场景1：手动指定需求

```python
# 如果你想显式控制模型选择
await agent.stream_run(
    user_message="分析这个大文档",
    session_context=context,
    model_requirements={
        "min_context_window": 50000  # 明确要求大上下文
    }
)
```

### 场景2：使用本地模型

```python
pool.add(
    alias="local",
    provider="local",
    model_name="llama-3-70b",
    capabilities=ModelCapabilities(
        supports_tools=True,
        context_window=8192,
        cost_per_1k_tokens=0.0  # 本地模型无成本
    ),
    base_url="http://localhost:8000"
)
```

### 场景3：添加自定义能力

```python
pool.add(
    alias="sql-expert",
    provider="custom",
    model_name="my-sql-model",
    capabilities=ModelCapabilities(
        custom_capabilities={
            "specialized_for": "sql",
            "supported_databases": ["postgresql", "mysql"]
        }
    )
)

# 使用时
model = pool.select({
    "specialized_for": "sql"
})
```

### 场景4：自定义选择策略

```python
from lexicon_agent.core.model_pool import ModelSelector

class CostAwareSelector(ModelSelector):
    """总是选择满足要求的最便宜模型"""
    def select_model(self, available_models, requirements, context):
        capable = [m for m in available_models
                   if m.capabilities.meets_requirements(requirements)]
        return min(capable, key=lambda m: m.capabilities.cost_per_1k_tokens)

# 使用自定义选择器
pool = ModelPool(selector=CostAwareSelector())
```

## 自动推断规则

框架会根据以下特征自动推断需求：

| 特征 | 推断的需求 | 选择的模型类型 |
|------|-----------|--------------|
| 消息包含"图片"、"image" | `supports_vision=True` | 视觉模型 |
| 有可用工具 | `supports_tools=True` | 支持工具的模型 |
| 上下文 > 50KB | `min_context_window=32000` | 大上下文模型 |
| 上下文 > 20KB | `min_context_window=16000` | 中等上下文模型 |

## 查询和管理

```python
# 查看所有模型
models = pool.list_models()
for model in models:
    print(f"{model['alias']}: {model['model_name']}")

# 获取特定模型
model = pool.get("vision")

# 设置默认模型
pool.set_default("fast-model")

# 移除模型
pool.remove("old-model")

# 检查模型数量
print(f"模型池中有 {len(pool)} 个模型")
```

## 调试和监控

```python
# 手动测试模型选择
requirements = {
    "supports_vision": True,
    "min_context_window": 8000
}
selected = pool.select(requirements)
print(f"选择的模型: {selected.alias}")

# 查看模型能力
model = pool.get("vision")
print(f"支持视觉: {model.capabilities.supports_vision}")
print(f"上下文窗口: {model.capabilities.context_window}")
print(f"成本: ${model.capabilities.cost_per_1k_tokens}/1k tokens")
```

## 完整示例

```python
import asyncio
from lexicon_agent.core.model_pool import ModelPool, ModelCapabilities
from lexicon_agent.core.agent import AgentController, StreamingGenerator
from lexicon_agent.core.context import (
    ContextRetrievalEngine,
    ContextProcessor,
    ContextManager
)

async def main():
    # 1. 创建模型池
    pool = ModelPool()

    # 2. 配置模型
    pool.add("default", "openai", "gpt-3.5-turbo",
             capabilities=ModelCapabilities(supports_tools=True))
    pool.add("vision", "openai", "gpt-4-vision",
             capabilities=ModelCapabilities(supports_vision=True))
    pool.add("large", "anthropic", "claude-3-opus",
             capabilities=ModelCapabilities(context_window=200000))

    # 3. 创建组件
    context_engine = ContextRetrievalEngine(...)
    context_processor = ContextProcessor(...)
    context_manager = ContextManager(...)
    streaming_generator = StreamingGenerator(model_pool=pool)

    # 4. 创建Agent
    agent = AgentController(
        context_engine=context_engine,
        context_processor=context_processor,
        context_manager=context_manager,
        streaming_generator=streaming_generator
    )

    # 5. 运行Agent - 自动选择模型！
    session_context = SessionContext(...)

    # 测试1：普通对话 → 使用default
    print("\n测试1：普通对话")
    async for event in agent.stream_run(
        user_message="你好，今天天气怎么样？",
        session_context=session_context
    ):
        if event.type == AgentEventType.RESPONSE_DELTA:
            print(event.content, end="")

    # 测试2：图片分析 → 使用vision
    print("\n\n测试2：图片分析")
    async for event in agent.stream_run(
        user_message="请分析这张图片中的物体",
        session_context=session_context
    ):
        if event.type == AgentEventType.RESPONSE_DELTA:
            print(event.content, end="")

    # 测试3：长文档 → 使用large
    print("\n\n测试3：长文档分析")
    large_document = "..." * 100000  # 大文档
    async for event in agent.stream_run(
        user_message=f"请总结这份文档：{large_document}",
        session_context=session_context
    ):
        if event.type == AgentEventType.RESPONSE_DELTA:
            print(event.content, end="")

if __name__ == "__main__":
    asyncio.run(main())
```

## 下一步

- 阅读 [MODEL_POOL_DESIGN.md](MODEL_POOL_DESIGN.md) 了解详细设计
- 查看 [examples/model_pool_example.py](examples/model_pool_example.py) 了解更多示例
- 实现自定义选择器以满足你的特定需求

## 常见问题

### Q: 我必须配置多个模型吗？

A: 不，你可以只配置一个模型作为default：

```python
pool = ModelPool()
pool.add("default", "openai", "gpt-4",
         capabilities=ModelCapabilities())
```

### Q: 如何禁用自动选择？

A: 使用旧接口，直接传入llm_provider：

```python
# 这样会跳过模型池，直接使用提供的provider
streaming_generator = StreamingGenerator(llm_provider=my_provider)
```

### Q: 自动推断的需求不准确怎么办？

A: 显式指定requirements：

```python
await agent.stream_run(
    user_message="...",
    session_context=context,
    model_requirements={
        "supports_vision": True,  # 显式指定
        "min_context_window": 50000
    }
)
```

### Q: 可以动态添加/删除模型吗？

A: 可以：

```python
# 运行时添加
pool.add("new-model", ...)

# 运行时删除
pool.remove("old-model")

# 立即生效，下次请求会使用新的模型池
```

### Q: 如何追踪哪个模型被使用了？

A: 查看event的metadata：

```python
async for event in agent.stream_run(...):
    if event.type == AgentEventType.LLM_STREAMING:
        print(f"使用的模型: {event.metadata.get('model_alias')}")
```

## 技巧和最佳实践

### 技巧1：链式配置

```python
pool = ModelPool().add(
    "fast", "openai", "gpt-3.5-turbo", ...
).add(
    "vision", "openai", "gpt-4-vision", ...
).add(
    "large", "anthropic", "claude-3-opus", ...
)
```

### 技巧2：环境变量配置

```python
import os

pool.add(
    "default",
    provider="openai",
    model_name=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo"),
    api_key=os.getenv("OPENAI_API_KEY")
)
```

### 技巧3：成本追踪

```python
class CostTrackingSelector(ModelSelector):
    def __init__(self):
        self.total_cost = 0

    def select_model(self, models, requirements, context):
        selected = super().select_model(models, requirements, context)
        # 记录预期成本
        tokens = context.get("estimated_tokens", 1000)
        self.total_cost += selected.capabilities.cost_per_1k_tokens * tokens / 1000
        return selected
```

## 获取帮助

- 查看示例代码: `examples/model_pool_example.py`
- 阅读完整文档: `MODEL_POOL_DESIGN.md`
- 提交Issue: [GitHub Issues](https://github.com/...)

---

**记住：框架的目标是让你自由，而不是限制你！**
