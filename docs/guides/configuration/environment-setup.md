# 环境配置

> **问题导向** - 学会配置 loom-agent 的开发和生产环境

## Python 环境

### 系统要求

- Python 3.11+
- pip 或 poetry

### 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 使用 conda
conda create -n loom python=3.11
conda activate loom
```

## 安装依赖

### 基础安装

```bash
pip install loom-agent
```

### 完整安装（包含所有功能）

```bash
pip install loom-agent[all]
```

### 按需安装

```bash
# OpenAI 支持
pip install loom-agent[llm]

# Anthropic 支持
pip install loom-agent[anthropic]

# 可视化工具
pip install loom-agent[studio]
```

## 环境变量配置

### 创建 .env 文件

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=sk-ant-...
```

### 加载环境变量

```python
from dotenv import load_dotenv
load_dotenv()
```

## 验证安装

```python
import loom
print(f"loom-agent version: {loom.__version__}")

# 测试基本功能
from loom.weave import create_agent, run
agent = create_agent("test", role="测试")
print("✓ 安装成功")
```

## 相关文档

- [配置 LLM](llm-providers.md) - 配置 LLM 提供商
- [生产部署](../deployment/production-deployment.md) - 生产环境部署
