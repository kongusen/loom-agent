# Anthropic and Gemini Structured Output Guide

## Overview

Anthropic (Claude) and Google Gemini now support structured output, ensuring models return valid JSON format data through different implementation methods.

---

## Anthropic (Claude) Structured Output

### Implementation

Claude implements structured output by adding JSON format instructions to the system prompt.

### 1. Declarative Configuration (JSON Object)

```python
from loom.llm.providers import AnthropicProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

# Configure structured output
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

# Call
response = await provider.chat(
    messages=[
        {"role": "user", "content": "List 3 programming languages and their features"}
    ]
)

print(response.content)  # Returns JSON format
```

### 2. Schema Configuration

```python
from loom.config.llm import LLMConfig, StructuredOutputConfig

# Define JSON Schema
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

# Configure
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_schema",
        schema=language_schema,
        schema_name="ProgrammingLanguages"
    )
)

provider = AnthropicProvider(api_key="sk-ant-...", config=config)

# Call
response = await provider.chat(
    messages=[
        {"role": "user", "content": "List 3 programming languages"}
    ]
)

# Response will follow schema structure
import json
data = json.loads(response.content)
print(data["languages"])
```

---

## Google Gemini Structured Output

### Implementation

Gemini natively supports structured output via `response_mime_type` and `response_schema` parameters.

### 1. Declarative Configuration (JSON Object)

```python
from loom.llm.providers import GeminiProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

# Configure structured output
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

# Call
response = await provider.chat(
    messages=[
        {"role": "user", "content": "Introduce main features of Python"}
    ]
)

print(response.content)  # Returns JSON format
```

### 2. Schema Configuration

```python
from loom.config.llm import LLMConfig, StructuredOutputConfig

# Define JSON Schema
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

# Configure
config = LLMConfig(
    structured_output=StructuredOutputConfig(
        enabled=True,
        format="json_schema",
        schema=user_schema,
        schema_name="UserProfile"
    )
)

provider = GeminiProvider(api_key="...", config=config)

# Call
response = await provider.chat(
    messages=[
        {"role": "user", "content": "Create a user profile for a software engineer"}
    ]
)

# Response strictly follows schema
import json
user_data = json.loads(response.content)
print(f"Name: {user_data['name']}, Age: {user_data['age']}")
```

---

## Streaming Output Support

Both providers support streaming structured output:

```python
# Anthropic Streaming
async for chunk in provider.stream_chat(messages):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "done":
        print("\nDone")

# Gemini Streaming
async for chunk in provider.stream_chat(messages):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "done":
        print("\nDone")
```

---

## Comparison Summary

| Feature | Anthropic (Claude) | Google Gemini |
|---------|-------------------|---------------|
| Implementation | System Prompt Guidance | Native API Parameters |
| JSON Object | ✅ Supported | ✅ Supported |
| JSON Schema | ✅ Supported (via prompt) | ✅ Native Support |
| Strict Mode | ⚠️ Depends on model understanding | ✅ API Level Guarantee |
| Streaming | ✅ Supported | ✅ Supported |

---

## Best Practices

1. **Choose the Format**:
   - Simple scenarios: Use `json_object` format
   - Complex structures: Use `json_schema` format

2. **Schema Design**:
   - Keep schema simple and clear
   - Use `required` fields to ensure necessary attributes
   - Add `description` to improve accuracy

3. **Error Handling**:
   ```python
   import json

   try:
       data = json.loads(response.content)
   except json.JSONDecodeError as e:
       print(f"JSON Parse Error: {e}")
       # Handle error
   ```

4. **Prompt Optimization**:
   - Clearly state the required data structure in user messages
   - Provide example output format
   - Use clear field names

---

## Complete Example

```python
import asyncio
from loom.llm.providers import AnthropicProvider, GeminiProvider
from loom.config.llm import LLMConfig, StructuredOutputConfig

async def main():
    # Define schema
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

    # Configure
    config = LLMConfig(
        structured_output=StructuredOutputConfig(
            enabled=True,
            format="json_schema",
            schema=recipe_schema,
            schema_name="Recipe"
        )
    )

    # Test Anthropic
    claude = AnthropicProvider(api_key="sk-ant-...", config=config)
    response = await claude.chat(
        messages=[{"role": "user", "content": "Give me a simple pasta recipe"}]
    )
    print("Claude:", response.content)

    # Test Gemini
    gemini = GeminiProvider(api_key="...", config=config)
    response = await gemini.chat(
        messages=[{"role": "user", "content": "Give me a simple pasta recipe"}]
    )
    print("Gemini:", response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

All providers now support full structured output functionality!
