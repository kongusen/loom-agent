# XPASS 测试分析与 Mock 替代方案

## 概述

XPASS 表示测试被标记为 `@pytest.mark.xfail`（预期失败），但实际上通过了。这些测试通常依赖外部服务（如真实 API），导致：
- 需要 API Key
- 运行不稳定（网络、超时）
- 成本问题
- CI/CD 环境配置复杂

本文档分析所有 XPASS 测试，并提供使用 Mock 替代的方案。

---

## 发现的 XPASS 测试

### 1. 分形架构测试（已处理 ✅）

**文件**: `tests/integration/test_fractal_real_api.py`

#### 测试列表

| 测试方法 | 依赖项 | 状态 | Mock 版本 |
|---------|--------|------|----------|
| `test_fractal_delegation_with_memory_flow` | OpenAI API | ✅ XPASS | ✅ `test_fractal_delegation_with_memory_flow_mock` |
| `test_multi_level_fractal_delegation` | OpenAI API | ✅ XPASS | ✅ `test_multi_level_fractal_delegation_mock` |

#### 依赖项分析

- **外部依赖**: OpenAI API (`OPENAI_API_KEY`)
- **问题**: 
  - 需要 API Key
  - 可能超时
  - 产生费用
  - 结果不稳定（LLM 输出可能变化）

#### Mock 替代方案

已创建 `TestFractalMockAPI` 类，使用 `MockLLMProvider`：

```python
from loom.providers.llm.mock import MockLLMProvider

llm_provider = MockLLMProvider(
    responses=[
        {"type": "text", "content": "..."},
        {"type": "tool_call", "name": "delegate_task", "arguments": {...}},
        # ...
    ]
)
```

**优势**:
- ✅ 无需 API Key
- ✅ 运行速度快
- ✅ 结果稳定
- ✅ 零成本
- ✅ 可离线运行

**使用方式**:
```bash
# Mock 版本（推荐用于 CI/CD）
pytest tests/integration/test_fractal_real_api.py::TestFractalMockAPI -v

# 真实 API 版本（用于端到端验证）
pytest tests/integration/test_fractal_real_api.py::TestFractalRealAPI -v
```

---

### 2. Sandbox Print 支持测试

**文件**: `tests/unit/test_tools/test_sandbox.py`

#### 测试详情

```python
@pytest.mark.xfail(reason="Print support requires complex RestrictedPython configuration", strict=False)
async def test_execute_python_with_print(self, sandbox):
    """Test using print in sandboxed code"""
```

#### 依赖项分析

- **外部依赖**: RestrictedPython 的 print 支持配置
- **问题**: 
  - 不是外部 API，而是功能限制
  - RestrictedPython 对 print 的支持需要复杂配置
  - 这是框架限制，不是测试问题

#### Mock 替代方案

**不建议使用 Mock**，因为：
1. 这是功能限制，不是外部依赖
2. 测试的是沙盒执行能力，需要真实执行环境
3. `strict=False` 表示允许通过，只是标记为已知限制

**建议**:
- 保持 `xfail` 标记，但添加更详细的说明
- 如果功能已实现，移除 `xfail` 标记
- 如果功能确实无法实现，保持现状

---

## 其他可能依赖外部服务的测试

### 3. 真实 API 集成测试

**文件**: `tests/integration/test_llm_provider.py`, `test_embedding_provider.py`, `test_e2e_real_api.py`

这些测试使用 `@requires_real_api` 装饰器，**不是 xfail**，而是 `skipif`：
- 如果没有 API Key，测试会被跳过（SKIPPED）
- 如果有 API Key，测试会运行
- 这是正确的设计，不需要 Mock 替代

**建议**: 保持现状，这些是真正的集成测试。

---

## Mock 替代策略总结

### 何时使用 Mock

✅ **应该使用 Mock**:
1. 测试框架逻辑，而非外部服务集成
2. 需要快速、稳定的测试结果
3. CI/CD 环境（避免 API Key 管理）
4. 开发阶段快速迭代
5. 测试外部服务的行为模拟

❌ **不应该使用 Mock**:
1. 真正的集成测试（验证与外部服务的集成）
2. 端到端测试（E2E）
3. 功能限制测试（如 sandbox print）

### Mock 实现模式

#### 1. 预设响应序列

```python
llm_provider = MockLLMProvider(
    responses=[
        {"type": "text", "content": "响应1"},
        {"type": "tool_call", "name": "tool_name", "arguments": {...}},
        {"type": "text", "content": "响应2"},
        # ...
    ]
)
```

**注意**: 由于父节点和子节点共享同一个 provider，响应序列需要按所有 Agent 的调用顺序设计。

#### 2. 关键词匹配（默认行为）

```python
llm_provider = MockLLMProvider()  # 使用默认关键词匹配
```

#### 3. 自定义 Mock Provider

对于复杂场景，可以创建自定义 Mock Provider：

```python
class CustomMockLLMProvider(MockLLMProvider):
    async def chat(self, messages, **kwargs):
        # 自定义逻辑
        return LLMResponse(content="...")
```

---

## 测试组织建议

### 文件结构

```
tests/
├── unit/                    # 单元测试（使用 Mock）
│   └── test_*.py
├── integration/
│   ├── test_*_real_api.py   # 真实 API 测试（需要 API Key）
│   └── test_*_mock.py       # Mock 版本测试（无需 API Key）
└── fixtures/
    └── mock_providers.py    # Mock Provider 定义
```

### 命名约定

- **真实 API 测试**: `test_*_real_api.py` 或 `Test*RealAPI`
- **Mock 测试**: `test_*_mock.py` 或 `Test*MockAPI`
- **共享测试类**: 在同一文件中使用不同的测试类

### 运行策略

```bash
# 开发阶段：运行 Mock 测试（快速）
pytest tests/unit tests/integration -k "mock" -v

# CI/CD：运行所有 Mock 测试
pytest tests/unit tests/integration -k "mock" -v --cov

# 发布前：运行真实 API 测试（验证集成）
ENABLE_REAL_API_TESTS=true pytest tests/integration -k "real_api" -v
```

---

## 实施检查清单

- [x] ✅ `test_fractal_delegation_with_memory_flow` - 已创建 Mock 版本
- [x] ✅ `test_multi_level_fractal_delegation` - 已创建 Mock 版本
- [ ] ⚠️ `test_execute_python_with_print` - 功能限制，保持 xfail
- [ ] ✅ 其他真实 API 测试 - 使用 `@requires_real_api`，设计正确

---

## 相关文档

- `tests/integration/FRACTAL_TEST_MOCK.md` - 分形测试 Mock 版本详细说明
- `tests/README_API_TESTING.md` - 真实 API 测试指南
- `loom/providers/llm/mock.py` - MockLLMProvider 实现

---

## 总结

1. **分形架构测试**: ✅ 已创建 Mock 版本，可以替代真实 API 测试
2. **Sandbox Print 测试**: ⚠️ 功能限制，保持 xfail，不需要 Mock
3. **其他集成测试**: ✅ 使用 `@requires_real_api`，设计正确

**建议**:
- 开发阶段使用 Mock 版本
- CI/CD 使用 Mock 版本
- 发布前运行真实 API 版本进行端到端验证
