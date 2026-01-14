# 如何使用统一处理机制解决问题

> **问题导向** - 学会使用统一处理机制解决不同类型的问题

## 概述

loom-agent 采用**统一的ReAct循环处理机制**，所有查询都通过相同的处理流程，根据查询特征自动调整上下文大小和策略。

### 统一处理流程

从 v0.3.7 开始，loom-agent 使用统一的处理流程：

- **统一ReAct循环**：所有查询都通过相同的处理流程
- **动态上下文调整**：根据查询特征自动调整上下文大小
- **查询特征分析**：基于查询长度、代码检测、多步骤识别等特征
- **可配置策略**：支持自定义上下文配置和处理策略

## 配置方式

### 方式 1：使用 CognitiveConfig（推荐）

最简单的方式是使用预设模式：

```python
from loom.kernel.core.bus import UniversalEventBus
from loom.kernel.core import Dispatcher
from loom.node.agent import AgentNode
from loom.config.cognitive import CognitiveConfig
from loom.llm import OpenAIProvider

# 创建基础设施
bus = UniversalEventBus()
dispatcher = Dispatcher(bus=bus)
provider = OpenAIProvider(api_key="your-api-key")

# 快速模式 - 偏向较小上下文
fast_agent = AgentNode(
    node_id="fast-assistant",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.fast_mode()
)

# 深度模式 - 偏向完整上下文
deep_agent = AgentNode(
    node_id="analyst",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.deep_mode()
)

# 平衡模式 - 默认配置
balanced_agent = AgentNode(
    node_id="assistant",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.balanced_mode()
)
```

**预设模式对比**：

| 模式 | 上下文大小 | 适用场景 |
|------|-----------|---------|
| fast_mode | 小（500 tokens） | 简单对话、快速响应 |
| balanced_mode | 中（4000 tokens） | 通用任务（默认） |
| deep_mode | 大（8000 tokens） | 复杂分析、深度推理 |

**注意**：所有模式都使用统一的ReAct循环处理，区别主要在于上下文大小配置。

## 使用场景

### 场景 1：简单对话

**适用**：闲聊、简单问答、快速响应

```python
# 使用快速模式
agent = AgentNode(
    node_id="chatbot",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.fast_mode()
)
```

**特点**：快速、流畅、低延迟

### 场景 2：复杂分析

**适用**：数据分析、问题诊断、多角度思考

```python
# 使用深度模式
agent = AgentNode(
    node_id="analyst",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.deep_mode()
)
```

**工作流程**：
1. 查询通过统一的ReAct循环处理
2. 根据查询特征自动使用完整上下文（8000+ tokens）
3. 深度分析和推理
4. 返回详细结果

### 场景 3：自定义配置

**适用**：需要特定配置的场景

```python
# 创建自定义配置
config = CognitiveConfig.default()

# 调整上下文参数
config.curation_max_tokens = 6000  # 上下文最大 token 数
config.context_max_tokens = 12000  # 总上下文限制

# 调整 Memory 参数
config.memory_max_l1_size = 30  # L1 缓冲区大小
config.memory_auto_vectorize_l4 = True  # 自动向量化 L4

agent = AgentNode(
    node_id="custom-agent",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=config
)
```


## 最佳实践

### 1. 选择合适的模式

| 任务类型 | 推荐配置 |
|---------|---------|
| 简单对话 | fast_mode() |
| 快速问答 | fast_mode() |
| 数据分析 | deep_mode() |
| 问题诊断 | deep_mode() |
| 通用任务 | balanced_mode() |

### 2. 自定义配置参数

根据业务需求调整配置：

```python
config = CognitiveConfig.default()

# 调整上下文大小
config.curation_max_tokens = 6000  # 策展后的最大 token 数
config.context_max_tokens = 12000  # 总上下文限制

# 调整 Memory 参数
config.memory_max_l1_size = 30  # L1 缓冲区大小
config.memory_auto_vectorize_l4 = True  # 自动向量化 L4
```

### 3. 选择合适的预设模式

根据任务类型选择合适的预设模式：

```python
# 快速响应优先
config = CognitiveConfig.fast_mode()

# 深度分析优先
config = CognitiveConfig.deep_mode()

# 平衡模式（默认）
config = CognitiveConfig.balanced_mode()
```

## 常见问题

**Q: 如何查看上下文大小？**

A: 系统会根据查询特征自动调整上下文大小，可以通过日志或监控查看。

**Q: 可以强制使用特定上下文大小吗？**

A: 可以通过配置影响上下文大小：
- 使用 `fast_mode()` 配置较小的上下文窗口
- 使用 `deep_mode()` 配置完整的上下文窗口
- 所有查询仍通过统一的ReAct循环处理

**Q: 处理流程是如何工作的？**

A: 所有查询都通过统一的ReAct循环处理。系统使用 `QueryFeatureExtractor` 提取查询特征（代码检测、多步骤识别、工具需求等），然后根据特征动态调整上下文大小和处理策略。

## 总结

统一处理架构提供了灵活的问题解决方式：

1. **统一流程**：所有查询都通过ReAct循环处理
2. **动态调整**：根据查询特征自动调整上下文大小
3. **预设模式**：快速配置常见场景（fast/balanced/deep）
4. **自定义配置**：精确控制上下文和记忆参数

## 相关文档

- [配置 Agent](agents/configuring-agents.md) - Agent 配置详解
- [架构设计](../concepts/architecture.md) - 了解双系统架构
- [Memory 系统](../concepts/memory_system.md) - Memory 系统说明
