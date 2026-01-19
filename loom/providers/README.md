# Providers - 外部提供者

外部服务集成接口。

## 设计理念

Providers层提供与外部服务的统一集成接口，支持可插拔的提供者实现。

## 核心组件

### 1. Provider (`base.py`)
提供者基类：
- `initialize()`: 初始化提供者
- `close()`: 关闭提供者

### 2. LLMProvider (`llm.py`)
LLM提供者抽象：
- `generate()`: 生成文本
- `generate_stream()`: 流式生成

### 3. VectorStoreProvider (`vector_store.py`)
向量存储提供者抽象：
- `store()`: 存储向量
- `search()`: 相似度搜索
- `delete()`: 删除向量

## 使用示例

```python
from loom.providers import LLMProvider

class MyLLMProvider(LLMProvider):
    async def initialize(self):
        # 初始化连接
        pass

    async def generate(self, prompt, **kwargs):
        # 调用LLM API
        return "generated text"

    async def close(self):
        # 清理资源
        pass

# 使用
provider = MyLLMProvider(config={"api_key": "..."})
await provider.initialize()
result = await provider.generate("Hello")
await provider.close()
```

## 扩展

可以实现具体的提供者：
- OpenAI Provider
- Anthropic Provider
- Local LLM Provider
- Chroma Vector Store
- Pinecone Vector Store
