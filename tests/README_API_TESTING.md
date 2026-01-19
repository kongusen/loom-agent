# 真实API测试指南

本文档说明如何配置和运行基于真实API的集成测试。

## 概述

Loom Agent提供两种测试模式：
- **单元测试**：使用mock对象，不需要真实API，快速运行
- **集成测试**：使用真实API调用，验证与外部服务的集成

## 环境配置

### 1. 创建环境变量文件

复制`.env.example`为`.env`：

```bash
cp .env.example .env
```

### 2. 配置API密钥

编辑`.env`文件，填入真实的API配置：

```bash
# OpenAI API密钥
OPENAI_API_KEY=sk-your-actual-api-key-here

# OpenAI 模型
OPENAI_MODEL=gpt-4o-mini

# OpenAI API基础URL
OPENAI_BASE_URL=https://api.openai.com/v1

# Embedding 模型
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# 启用真实API测试
ENABLE_REAL_API_TESTS=true

# 测试超时时间（秒）
API_TEST_TIMEOUT=30

# 最大重试次数
API_MAX_RETRIES=3
```

**重要提示**：
- `.env`文件已在`.gitignore`中，不会被提交到git
- 请勿将API密钥提交到版本控制系统
- 建议使用测试专用的API密钥，避免影响生产环境

## 运行测试

### 运行所有单元测试（不需要API密钥）

```bash
pytest tests/unit -v
```

### 运行所有集成测试（需要API密钥）

```bash
# 确保已配置 ENABLE_REAL_API_TESTS=true
pytest tests/integration -v
```

### 运行特定的集成测试

```bash
# 只运行LLM provider测试
pytest tests/integration/test_llm_provider.py -v

# 只运行embedding provider测试
pytest tests/integration/test_embedding_provider.py -v

# 运行特定的测试方法
pytest tests/integration/test_llm_provider.py::TestOpenAIProviderIntegration::test_chat_basic -v
```

### 跳过集成测试

如果未配置API密钥或设置`ENABLE_REAL_API_TESTS=false`，集成测试会自动跳过：

```bash
# 这些测试会被跳过
pytest tests/integration -v
# 输出: SKIPPED [1] Real API tests disabled...
```

## 可用的集成测试

### LLM Provider测试 (`test_llm_provider.py`)

测试OpenAI LLM provider的真实API调用：

- `test_chat_basic`: 基本的chat调用
- `test_chat_with_system_message`: 带系统消息的chat调用
- `test_stream_chat_basic`: 流式chat调用
- `test_chat_with_temperature`: 测试temperature参数

### Embedding Provider测试 (`test_embedding_provider.py`)

测试OpenAI embedding provider的真实API调用：

- `test_embed_single_text`: 单个文本的embedding生成
- `test_embed_chinese_text`: 中文文本的embedding生成
- `test_embed_batch`: 批量embedding生成
- `test_embed_consistency`: embedding一致性测试

## 最佳实践

### 1. 开发时使用单元测试

日常开发时，优先运行单元测试（使用mock）：
- 速度快，无需网络请求
- 无API成本
- 可离线运行

```bash
pytest tests/unit -v
```

### 2. 提交前运行集成测试

在提交代码前，运行集成测试验证真实API集成：

```bash
ENABLE_REAL_API_TESTS=true pytest tests/integration -v
```

### 3. CI/CD配置

在CI/CD环境中：
- 默认只运行单元测试
- 可选择性地在特定分支（如main）运行集成测试
- 使用secrets管理API密钥

### 4. 成本控制

真实API测试会产生费用，建议：
- 使用较小的模型（如gpt-4o-mini）
- 限制测试数据量
- 不要在CI中频繁运行集成测试
- 定期检查API使用量

## 故障排除

### 测试被跳过

**问题**：运行集成测试时显示SKIPPED

**解决方案**：
1. 检查`.env`文件是否存在
2. 确认`ENABLE_REAL_API_TESTS=true`
3. 确认`OPENAI_API_KEY`已正确配置

### API密钥无效

**问题**：测试失败，提示API密钥无效

**解决方案**：
1. 检查API密钥是否正确
2. 确认API密钥有足够的配额
3. 检查base_url是否正确

### 超时错误

**问题**：测试超时失败

**解决方案**：
1. 增加`API_TEST_TIMEOUT`值
2. 检查网络连接
3. 确认API服务可用

## 架构说明

### 测试配置模块 (`tests/api_config.py`)

提供API测试的配置管理：
- `APITestConfig`: 配置类，从环境变量加载配置
- `requires_real_api`: 装饰器，标记需要真实API的测试
- `get_openai_config()`: 获取OpenAI配置
- `get_embedding_config()`: 获取Embedding配置

### Pytest Fixtures (`tests/conftest.py`)

提供共享的测试fixtures：
- `api_test_config`: API测试配置对象
- `openai_config`: OpenAI配置字典
- `embedding_config`: Embedding配置字典

### 集成测试目录 (`tests/integration/`)

包含所有真实API集成测试：
- `test_llm_provider.py`: LLM provider测试
- `test_embedding_provider.py`: Embedding provider测试

## 如何添加新的集成测试

### 1. 创建测试文件

在`tests/integration/`目录下创建新的测试文件：

```python
"""
Your Provider 集成测试
"""

import pytest
from tests.api_config import requires_real_api

class TestYourProviderIntegration:
    """Your Provider 真实API集成测试"""

    @requires_real_api
    @pytest.mark.asyncio
    async def test_your_feature(self, openai_config):
        """测试你的功能"""
        # 使用openai_config或embedding_config fixture
        # 实现你的测试逻辑
        pass
```

### 2. 使用装饰器

使用`@requires_real_api`装饰器标记需要真实API的测试：
- 如果未启用真实API测试，测试会自动跳过
- 避免在没有API密钥时运行失败

### 3. 使用Fixtures

使用conftest.py中提供的fixtures：
- `api_test_config`: 获取完整的配置对象
- `openai_config`: 获取OpenAI配置字典
- `embedding_config`: 获取Embedding配置字典

### 4. 编写断言

编写清晰的断言验证API响应：
- 验证响应不为空
- 验证响应格式正确
- 验证响应内容符合预期

## 总结

本测试体系提供了：
- ✅ 灵活的配置管理（环境变量）
- ✅ 自动跳过机制（无API密钥时）
- ✅ 清晰的测试组织（单元测试 vs 集成测试）
- ✅ 完整的文档和示例
- ✅ 成本控制建议

遵循最简实现原则，只提供必要的功能，易于理解和维护。
