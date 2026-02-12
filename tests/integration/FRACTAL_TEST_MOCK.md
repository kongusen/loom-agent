# 分形架构测试 - Mock 版本说明

## 概述

`test_fractal_real_api.py` 中的测试原本依赖真实的 OpenAI API，现在提供了使用 `MockLLMProvider` 的版本，无需 API key 即可运行。

## 为什么使用 Mock？

1. **无需 API Key**：不需要配置 `OPENAI_API_KEY` 环境变量
2. **运行速度快**：无需网络请求，测试执行更快
3. **结果可预测**：预设的响应序列使测试结果稳定
4. **成本为零**：不会产生 API 调用费用
5. **离线运行**：可以在没有网络的环境中运行

## MockLLMProvider 工作原理

`MockLLMProvider` 使用 `call_count` 跟踪调用次数，按照预设的响应序列返回结果：

```python
llm_provider = MockLLMProvider(
    responses=[
        {"type": "text", "content": "响应1"},
        {"type": "tool_call", "name": "delegate_task", "arguments": {...}},
        {"type": "text", "content": "响应2"},
        # ...
    ]
)
```

## 注意事项

### 1. 共享 Provider 实例

父节点和子节点共享同一个 `llm_provider` 实例，这意味着：
- 响应序列需要按照**所有 Agent 的调用顺序**设计
- `call_count` 在所有 Agent 之间共享

### 2. 响应序列设计

设计响应序列时，需要考虑：
- 父节点的每次 LLM 调用
- 子节点的每次 LLM 调用
- 工具调用的结果处理

示例序列：
```
1. 父节点：思考任务
2. 父节点：委派子任务1
3. 子节点1：执行子任务
4. 子节点1：完成子任务
5. 父节点：委派子任务2
6. 子节点2：执行子任务
7. 子节点2：完成子任务
8. 父节点：总结结果
9. 父节点：完成整个任务
```

### 3. 测试验证

Mock 版本的测试验证点与真实 API 版本相同：
- ✅ 任务完成状态
- ✅ Memory 数据流（L1/L2）
- ✅ EventBus 订阅机制
- ✅ Context 构建
- ✅ 分形委派事件

## 使用方式

### 运行 Mock 版本测试

```bash
# 运行单个测试
pytest tests/integration/test_fractal_real_api.py::TestFractalMockAPI::test_fractal_delegation_with_memory_flow_mock -v

# 运行整个 Mock 测试类
pytest tests/integration/test_fractal_real_api.py::TestFractalMockAPI -v
```

### 运行真实 API 版本测试

```bash
# 需要设置 OPENAI_API_KEY 环境变量
export OPENAI_API_KEY=your_key_here
pytest tests/integration/test_fractal_real_api.py::TestFractalRealAPI -v
```

## 测试对比

| 特性 | Mock 版本 | 真实 API 版本 |
|------|----------|--------------|
| 需要 API Key | ❌ | ✅ |
| 运行速度 | 快 | 慢（网络延迟） |
| 结果稳定性 | 高（预设响应） | 中（LLM 输出可能变化） |
| 成本 | 免费 | 需要 API 费用 |
| 测试覆盖 | 框架逻辑 | 端到端集成 |

## 建议

1. **开发阶段**：使用 Mock 版本进行快速迭代
2. **CI/CD**：使用 Mock 版本确保测试稳定
3. **发布前**：运行真实 API 版本进行端到端验证
4. **调试**：使用 Mock 版本更容易复现问题

## 相关文件

- `loom/providers/llm/mock.py` - MockLLMProvider 实现
- `tests/integration/test_fractal_real_api.py` - 测试文件
- `tests/integration/test_four_paradigms.py` - 其他使用 Mock 的示例
