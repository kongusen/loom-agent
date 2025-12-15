"""
Loom Builtin - 核心实现 + 主流 LLM 支持

核心模块（无外部依赖）：
- tools: 工具构建能力（@tool, ToolBuilder）
- memory: Memory 实现（InMemoryMemory, PersistentMemory）

LLM 支持（需要外部依赖）：
- llms: 主流 LLM 提供商支持
  - OpenAI, DeepSeek, Qwen, Kimi, 智谱, 豆包, 零一万物
  - 依赖: pip install openai

使用示例：
```python
from loom.builtin import tool, UnifiedLLM

# 工具
@tool()
async def calculator(expr: str) -> float:
    return eval(expr)

# LLM（支持多种提供商）
llm = UnifiedLLM(provider="deepseek", api_key="...")
```
"""

# Tools (核心，无依赖)
from loom.builtin.tools import tool, ToolBuilder

# Memory (核心，无依赖)
from loom.builtin.memory import InMemoryMemory, PersistentMemory

# LLMs (需要 pip install openai)
from loom.builtin.llms import (
    UnifiedLLM,
    OpenAILLM,
    DeepSeekLLM,
    QwenLLM,
    KimiLLM,
    ZhipuLLM,
    DoubaoLLM,
    YiLLM,
)

__all__ = [
    # Tools
    "tool",
    "ToolBuilder",
    # Memory
    "InMemoryMemory",
    "PersistentMemory",
    # LLMs
    "UnifiedLLM",
    "OpenAILLM",
    "DeepSeekLLM",
    "QwenLLM",
    "KimiLLM",
    "ZhipuLLM",
    "DoubaoLLM",
    "YiLLM",
]
