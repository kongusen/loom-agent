# 安装指南

**版本**: v0.1.9
**最后更新**: 2024-12-15

---

## 📦 系统要求

- **Python**: 3.11+ (推荐 3.11 或 3.12)
- **操作系统**: Linux, macOS, Windows
- **内存**: 至少 4GB RAM
- **磁盘**: 至少 500MB 可用空间

---

## 🚀 快速安装

### 基础安装

```bash
pip install loom-agent
```

这将安装 Loom 的核心功能。核心框架仅依赖 Python 3.11+ 和 Pydantic，其他功能均为可选依赖。

---

## 🔧 可选集成

Loom 采用 Protocol-based 设计，所有集成均为可选。根据需要安装：

### LLM 集成

```bash
# OpenAI SDK（用于 OpenAI 集成示例）
pip install openai

# 其他 LLM - 只需实现 BaseLLM Protocol 即可
# Loom 不强制绑定任何 LLM provider
```

### 向量数据库（用于 HierarchicalMemory + RAG）

```bash
# ChromaDB（向量存储）
pip install chromadb

# FAISS（向量加速，可选）
pip install faiss-cpu  # 或 faiss-gpu
```

### 开发工具

```bash
# 测试和开发
pip install pytest pytest-asyncio

# 代码格式化
pip install black isort
```

---

## 📥 从源码安装

适合开发者或想要使用最新功能的用户。

### 1. 克隆仓库

```bash
git clone https://github.com/kongusen/loom-agent.git
cd loom-agent
```

### 2. 安装依赖

```bash
# 使用 pip
pip install -e ".[dev]"

# 或使用 poetry
poetry install
```

### 3. 验证安装

```bash
python -c "import loom; print(loom.__version__)"
# 输出: 0.1.9
```

---

## 🔑 配置 API Keys

Loom 是 Protocol-based 框架，不绑定特定 LLM。配置方式取决于你选择的 LLM：

### OpenAI 示例

```bash
export OPENAI_API_KEY="sk-..."
```

```python
# 使用 OpenAI SDK（需单独安装）
from openai import AsyncOpenAI

client = AsyncOpenAI()  # 自动从环境变量读取

# 实现 BaseLLM Protocol
# 参见 examples/integrations/openai_llm.py
```

### 自定义 LLM

```python
from loom.interfaces import BaseLLM

class MyCustomLLM:
    """实现 BaseLLM Protocol 即可"""
    async def stream(self, messages, tools=None):
        # 你的实现：可以是 OpenAI、Claude、本地模型等
        yield {"type": "content_delta", "content": "..."}
```

---

## ✅ 验证安装

创建一个测试文件 `test_loom.py`：

```python
import asyncio
from loom.core.message import Message

async def test_installation():
    """测试 Loom 核心功能"""
    print("✓ Loom 导入成功")

    # 测试 Message 不可变架构（v0.1.9 核心特性）
    msg1 = Message(role="user", content="Hello")
    msg2 = msg1.reply("Hi there!")

    print(f"✓ Message 创建成功: {msg1.id}")
    print(f"✓ Message 不可变: msg1.id != msg2.id = {msg1.id != msg2.id}")

    # 测试 history 追溯（v0.1.9 新特性）
    from loom.core.message import get_message_history
    history = get_message_history(msg2)
    print(f"✓ History 追溯正常: {len(history)} 条消息")

    # 测试序列化（v0.1.9 零数据丢失）
    data = msg2.to_dict(include_history=True)
    restored = Message.from_dict(data)
    restored_history = get_message_history(restored)
    print(f"✓ 序列化零丢失: {len(restored_history)} 条消息恢复")

    print("\n✅ Loom Agent v0.1.9 核心功能验证成功！")

if __name__ == "__main__":
    asyncio.run(test_installation())
```

运行测试：

```bash
python test_loom.py
```

预期输出：

```
✓ Loom 导入成功
✓ Message 创建成功: <uuid>
✓ Message 不可变: msg1.id != msg2.id = True
✓ History 追溯正常: 2 条消息
✓ 序列化零丢失: 2 条消息恢复

✅ Loom Agent v0.1.9 核心功能验证成功！
```

---

## 🐛 常见问题

### 问题 1: Python 版本过低

**错误**: `SyntaxError` 或 `ImportError`

**原因**: Loom 需要 Python 3.11+。

**解决方案**:
```bash
# 检查 Python 版本
python --version

# 必须是 Python 3.11 或更高版本
python3.11 -m pip install loom-agent
```

### 问题 2: 权限错误 (Permission denied)

**解决方案**: 使用虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装 Loom
pip install loom-agent
```

### 问题 3: `ModuleNotFoundError: No module named 'openai'`

**原因**: 使用 OpenAI 集成示例但未安装 OpenAI SDK。

**解决方案**:
```bash
# Loom 不强制依赖 OpenAI
# 如果需要使用 OpenAI 集成示例，单独安装：
pip install openai
```

---

## 🎓 下一步

- [创建你的第一个 Agent](./first-agent.md)
- [5分钟快速开始](./quickstart.md)
- [API 参考](../api/)
- [示例代码](../examples/)

---

## 💡 推荐工具

- **IDE**: VS Code, PyCharm
- **Python 版本管理**: pyenv
- **虚拟环境**: venv, conda
- **包管理**: pip, poetry
- **API 测试**: httpie, postman

---

## 📚 相关资源

- [官方文档](https://github.com/kongusen/loom-agent#readme)
- [GitHub 仓库](https://github.com/kongusen/loom-agent)
- [PyPI 页面](https://pypi.org/project/loom-agent/)
- [变更日志](../../CHANGELOG.md)
