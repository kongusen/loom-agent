# 安装指南

## 通过 pip 安装

Loom 托管在 PyPI 上，可以通过 pip 直接安装：

```bash
pip install loom-agent
```

## 验证安装

安装完成后，你可以通过导入来验证是否成功：

```python
import loom
print(f"Loom version: {loom.__version__}")
```

## 依赖项

Loom 的核心非常轻量，主要依赖：
- `pydantic`: 用于数据验证和模型定义。
- `structlog`: 用于结构化日志。

如果你需要使用特定的 LLM 提供商（如 OpenAI），你需要单独安装适配器库：
```bash
pip install openai
```
