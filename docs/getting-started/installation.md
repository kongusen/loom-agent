# 安装指南

**版本**: v0.1.6
**最后更新**: 2025-12-14

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

这将安装 Loom 的核心功能，但不包含任何 LLM provider 依赖。

### 带 OpenAI 支持

```bash
pip install "loom-agent[openai]"
```

### 带 Anthropic (Claude) 支持

```bash
pip install "loom-agent[anthropic]"
```

### 完整安装（所有功能）

```bash
pip install "loom-agent[all]"
```

包含所有可选依赖：OpenAI、Anthropic、向量数据库、Web 框架等。

---

## 🔧 可选依赖

Loom 支持多种可选功能，可以按需安装：

### LLM Providers

```bash
# OpenAI (GPT-3.5, GPT-4)
pip install "loom-agent[openai]"

# Anthropic (Claude)
pip install "loom-agent[anthropic]"
```

### 向量数据库（用于 RAG）

```bash
# ChromaDB
pip install "loom-agent[chromadb]"

# Pinecone
pip install "loom-agent[pinecone]"
```

### Web 框架集成

```bash
# FastAPI + Uvicorn
pip install "loom-agent[fastapi]"
```

### 组合安装

```bash
# OpenAI + FastAPI
pip install "loom-agent[openai,fastapi]"

# 开发环境（包含测试工具）
pip install "loom-agent[dev]"
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
# 输出: 0.1.6
```

---

## 🔑 配置 API Keys

Loom 支持通过环境变量配置 API keys：

### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

### Anthropic (Claude)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 在 Python 中配置

```python
from loom.builtin import OpenAILLM

# 方式 1: 直接传递
llm = OpenAILLM(api_key="sk-...")

# 方式 2: 使用环境变量（推荐）
# 设置 OPENAI_API_KEY 环境变量后：
llm = OpenAILLM()  # 自动从环境变量读取
```

---

## ✅ 验证安装

创建一个测试文件 `test_loom.py`：

```python
import asyncio
from loom import Message, SimpleAgent
from loom.builtin import OpenAILLM

async def test_installation():
    """测试 Loom 安装"""
    print(f"✓ Loom 导入成功")

    # 创建一个简单的 Agent
    agent = loom.agent(
        name="test-agent",
        llm=OpenAILLM(api_key="test-key")  # 使用测试 key
    )
    print(f"✓ Agent 创建成功: {agent.name}")

    # 获取统计信息
    stats = agent.get_stats()
    print(f"✓ 统计功能正常: {stats}")

    print("\n✅ Loom Agent v0.1.6 安装成功！")

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
✓ Agent 创建成功: test-agent
✓ 统计功能正常: {'num_tools': 0, 'max_iterations': 50, ...}

✅ Loom Agent v0.1.6 安装成功！
```

---

## 🐛 常见问题

### 问题 1: `ModuleNotFoundError: No module named 'openai'`

**原因**: 未安装 OpenAI 依赖。

**解决方案**:
```bash
pip install "loom-agent[openai]"
```

### 问题 2: Python 版本过低

**错误**: `SyntaxError` 或 `ImportError`

**原因**: Loom 需要 Python 3.11+。

**解决方案**:
```bash
# 检查 Python 版本
python --version

# 安装 Python 3.11+ 后
python3.11 -m pip install loom-agent
```

### 问题 3: 权限错误 (Permission denied)

**解决方案**: 使用虚拟环境或添加 `--user` 标志
```bash
# 使用虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

pip install loom-agent

# 或使用 --user
pip install --user loom-agent
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
