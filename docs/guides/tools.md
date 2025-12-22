# Tool System Guide

Tools are the primary way Agents interact with the external world. Loom converts Python functions into tool schemas that LLMs can understand and invoke.

## 1. Defining Tools

The `@tool` decorator is the standard way to define tools.

### Basic Tool
```python
from loom.builtin import tool

@tool
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

### Complex Arguments (Pydantic)
Loom supports complex types naturally.

```python
from typing import List

@tool
async def send_email(recipients: List[str], subject: str, body: str):
    """
    Send an email to multiple recipients.
    
    Args:
        recipients: List of email addresses
        subject: Email subject
        body: Plain text body
    """
    # Implementation...
```

## 2. Best Practices

### Type Hints are Mandatory
The tool generator uses type hints to build the JSON schema.
- ✅ `def func(x: int)`
- ❌ `def func(x)` -> Logic will fail or generate "any" type which confuses LLMs.

### Docstrings Matter
The LLM reads the docstring to understand:
1. **What** the tool does (Summary).
2. **When** to use it.
3. **What** each argument means (Args section).

**Format**: Google-style or NumPy-style docstrings are recommended.

## 3. Concurrency
Tools are executed asynchronously by the `RecursiveEngine`.
If you pass `RunnableConfig(max_concurrency=N)`, the engine will limit parallel execution.

```python
agent.invoke("...", config={"max_concurrency": 5})
```
