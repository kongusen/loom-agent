# 如何使用双系统解决问题

> **问题导向** - 学会使用 System 1 和 System 2 解决不同类型的问题

## 概述

loom-agent 的双系统架构提供了两种互补的问题解决方式：
- **System 1（快速响应）**：适合简单查询、快速对话
- **System 2（深度推理）**：适合复杂分析、多步骤任务

### 自动路由机制

从 v0.4 开始，loom-agent 引入了**自动路由机制**，可以根据查询复杂度自动选择合适的系统：

- **智能分类**：基于查询长度、代码检测、多步骤识别等特征
- **置信度评估**：System 1 响应会被评估置信度，低置信度自动回退到 System 2
- **可配置规则**：支持自定义路由规则和阈值

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

# 快速模式 - 偏向 System 1
fast_agent = AgentNode(
    node_id="fast-assistant",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.fast_mode()
)

# 深度模式 - 偏向 System 2
deep_agent = AgentNode(
    node_id="analyst",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.deep_mode()
)

# 平衡模式 - 自动路由（默认）
balanced_agent = AgentNode(
    node_id="assistant",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=CognitiveConfig.balanced_mode()
)
```

**预设模式对比**：

| 模式 | System 1 阈值 | 上下文大小 | 适用场景 |
|------|--------------|-----------|---------|
| fast_mode | 低（0.6） | 小（500 tokens） | 简单对话、快速响应 |
| balanced_mode | 中（0.8） | 中（4000 tokens） | 通用任务 |
| deep_mode | 高（0.9） | 大（8000 tokens） | 复杂分析、深度推理 |

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
1. 查询被路由到 System 2
2. 使用完整上下文（8000+ tokens）
3. 深度分析和推理
4. 返回详细结果

### 场景 3：自定义路由规则

**适用**：需要特定路由逻辑的场景

```python
from loom.config.router import RouterRule

# 创建自定义配置
config = CognitiveConfig.default()

# 添加自定义规则
config.router_rules.append(RouterRule(
    name="code_analysis",
    keywords=["代码", "bug", "调试"],
    target_system="SYSTEM_2"
))

config.router_rules.append(RouterRule(
    name="greeting",
    keywords=["你好", "hi", "hello"],
    target_system="SYSTEM_1"
))

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

### 2. 自定义路由规则

根据业务需求添加特定规则：

```python
config = CognitiveConfig.default()

# 技术问题 -> System 2
config.router_rules.append(RouterRule(
    name="technical",
    keywords=["代码", "bug", "性能", "架构"],
    target_system="SYSTEM_2"
))

# 简单问候 -> System 1
config.router_rules.append(RouterRule(
    name="greeting",
    regex_patterns=[r"^(你好|hi|hello)"],
    target_system="SYSTEM_1"
))
```

### 3. 调整置信度阈值

根据准确性要求调整：

```python
config = CognitiveConfig.default()

# 高准确性要求 - 更容易回退到 System 2
config.router_s1_confidence_threshold = 0.9

# 快速响应优先 - 更多使用 System 1
config.router_s1_confidence_threshold = 0.6
```

## 常见问题

**Q: 如何查看使用了哪个系统？**

A: 检查响应中的 `system` 字段：
```python
result = await agent.process(event)
print(f"使用系统: {result.get('system')}")  # SYSTEM_1 或 SYSTEM_2
```

**Q: 可以强制使用特定系统吗？**

A: 可以通过调整阈值实现：
- 强制 System 1: `router_s1_confidence_threshold = 0.0`
- 强制 System 2: `router_s1_confidence_threshold = 1.0`

**Q: 路由规则的优先级？**

A: 规则按添加顺序匹配，第一个匹配的规则生效。

## 总结

双系统架构提供了灵活的问题解决方式：

1. **自动路由**：智能选择合适的系统
2. **预设模式**：快速配置常见场景
3. **自定义规则**：精确控制路由逻辑
4. **置信度评估**：自动回退机制

## 相关文档

- [配置 Agent](agents/configuring-agents.md) - Agent 配置详解
- [架构设计](../concepts/architecture.md) - 了解双系统架构
- [Memory 系统](../concepts/memory_system.md) - Memory 系统说明
