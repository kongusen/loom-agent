# Anthropic 和 Gemini 结构化输出使用指南

## 概述

Anthropic (Claude) 和 Google Gemini 现已支持结构化输出，通过不同的实现方式确保模型返回有效的 JSON 格式数据。

---

## Anthropic (Claude) 结构化输出

### 实现方式

Claude 通过在 system prompt 中添加 JSON 格式指令来实现结构化输出。

### 1. 声明式配置（JSON Object）

```python
from loom.llm.providers import AnthropicProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

# 配置结构化输出
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)

provider = AnthropicProvider(
    api_key="sk-ant-...",
    config=config
)

# 调用
response = await provider.chat(
    messages=[
        {"role": "user", "content": "列出3种编程语言及其特点"}
    ]
)

print(response.content)  # 返回 JSON 格式
```

### 2. Schema 方式配置

```python
from loom.config.llm import LLMConfig, StructuredOutputConfig

# 定义 JSON Schema
language_schema = {
    "type": "object",
    "properties": {
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "paradigm": {"type": "string"},
                    "year": {"type": "integer"}
                },
                "required": ["name", "paradigm"]
            }
        }
    },
    "required": ["languages"]
}

# 配置
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_schema",
        schema=language_schema,
        schema_name="ProgrammingLanguages"
    )
)

provider = AnthropicProvider(api_key="sk-ant-...", config=config)

# 调用
response = await provider.chat(
    messages=[
        {"role": "user", "content": "列出3种编程语言"}
    ]
)

# 响应会遵循 schema 结构
import json
data = json.loads(response.content)
print(data["languages"])
```

---

## Google Gemini 结构化输出

### 实现方式

Gemini 通过 `response_mime_type` 和 `response_schema` 参数原生支持结构化输出。

### 1. 声明式配置（JSON Object）

```python
from loom.llm.providers import GeminiProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

# 配置结构化输出
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_object"
    )
)

provider = GeminiProvider(
    api_key="...",
    config=config
)

# 调用
response = await provider.chat(
    messages=[
        {"role": "user", "content": "介绍Python的主要特点"}
    ]
)

print(response.content)  # 返回 JSON 格式
```

### 2. Schema 方式配置

```python
from loom.config.llm import LLMConfig, StructuredOutputConfig

# 定义 JSON Schema
user_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "skills": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["name", "age"]
}

# 配置
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_schema",
        schema=user_schema,
        schema_name="UserProfile"
    )
)

provider = GeminiProvider(api_key="...", config=config)

# 调用
response = await provider.chat(
    messages=[
        {"role": "user", "content": "创建一个软件工程师的用户资料"}
    ]
)

# 响应严格遵循 schema
import json
user_data = json.loads(response.content)
print(f"Name: {user_data['name']}, Age: {user_data['age']}")
```

---

## 流式输出支持

两个 provider 都支持流式结构化输出：

```python
# Anthropic 流式
async for chunk in provider.stream_chat(messages):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "done":
        print("\n完成")

# Gemini 流式
async for chunk in provider.stream_chat(messages):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "done":
        print("\n完成")
```

---

## 对比总结

| 特性 | Anthropic (Claude) | Google Gemini |
|------|-------------------|---------------|
| 实现方式 | System Prompt 引导 | 原生 API 参数 |
| JSON Object | ✅ 支持 | ✅ 支持 |
| JSON Schema | ✅ 支持（通过 prompt） | ✅ 原生支持 |
| 严格模式 | ⚠️ 依赖模型理解 | ✅ API 级别保证 |
| 流式支持 | ✅ 支持 | ✅ 支持 |

---

## 最佳实践

1. **选择合适的格式**：
   - 简单场景：使用 `json_object` 格式
   - 复杂结构：使用 `json_schema` 格式

2. **Schema 设计**：
   - 保持 schema 简洁明确
   - 使用 `required` 字段确保必需属性
   - 添加 `description` 提高准确性

3. **错误处理**：
   ```python
   import json

   try:
       data = json.loads(response.content)
   except json.JSONDecodeError as e:
       print(f"JSON 解析失败: {e}")
       # 处理错误
   ```

4. **提示词优化**：
   - 在用户消息中明确说明需要的数据结构
   - 提供示例输出格式
   - 使用清晰的字段名称

---

## 完整示例

```python
import asyncio
from loom.llm.providers import AnthropicProvider, GeminiProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

async def main():
    # 定义 schema
    recipe_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "ingredients": {
                "type": "array",
                "items": {"type": "string"}
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"}
            },
            "cooking_time": {"type": "integer"}
        },
        "required": ["name", "ingredients", "steps"]
    }

    # 配置
    config = LLMConfig(
        structured_output=StructuredOutputConfig(
            enabled=True,
            format="json_schema",
            schema=recipe_schema,
            schema_name="Recipe"
        )
    )

    # 测试 Anthropic
    claude = AnthropicProvider(api_key="sk-ant-...", config=config)
    response = await claude.chat(
        messages=[{"role": "user", "content": "给我一个简单的意大利面食谱"}]
    )
    print("Claude:", response.content)

    # 测试 Gemini
    gemini = GeminiProvider(api_key="...", config=config)
    response = await gemini.chat(
        messages=[{"role": "user", "content": "给我一个简单的意大利面食谱"}]
    )
    print("Gemini:", response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

所有 provider 现已支持完整的结构化输出功能！
