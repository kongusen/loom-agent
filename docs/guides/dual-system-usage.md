# 如何使用双系统解决问题

> **问题导向** - 学会使用 System 1 和 System 2 解决不同类型的问题

## 概述

loom-agent 的双系统架构提供了两种互补的问题解决方式：
- **System 1（快速流）**：适合快速响应、对话交互
- **System 2（深度思考）**：适合复杂推理、多步骤分析

## 基本使用

### 默认模式：仅 System 1

默认情况下，Agent 只使用 System 1（快速流式输出）：

```python
from loom.weave import create_agent, run

# 创建 Agent（默认只使用 System 1）
agent = create_agent("assistant", role="通用助手")

# 快速响应
result = run(agent, "你好，请介绍一下自己")
print(result)
```

**特点**：
- 快速响应
- 流式输出
- 适合简单对话

### 启用 System 2：深度思考模式

要启用 System 2，需要配置 `ThinkingPolicy`：

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp

# 创建 LoomApp
app = LoomApp()

# 配置 System 2
thinking_policy = ThinkingPolicy(
    enabled=True,              # 启用深度思考
    max_thoughts=3,            # 最多3个并行思考
    max_depth=2,               # 最大递归深度2层
    trigger_words=["分析", "推理", "深入"]  # 触发词
)

# 创建启用 System 2 的 Agent
agent = AgentNode(
    node_id="deep-thinker",
    dispatcher=app.dispatcher,
    role="深度分析师",
    thinking_policy=thinking_policy
)

# 运行任务
result = await app.run(agent, "请深入分析这个问题的根本原因")
```

**特点**：
- 并行启动深度思考
- 生成结构化洞察
- 适合复杂问题

## ThinkingPolicy 配置选项

### 核心配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | False | 是否启用 System 2 |
| `max_thoughts` | int | None | 最大并行思考数（None=无限制） |
| `max_depth` | int | None | 最大递归深度（None=无限制） |
| `total_token_budget` | int | None | Token 预算（None=无限制） |
| `thought_timeout` | float | None | 思考超时时间（秒） |
| `trigger_words` | List[str] | [] | 触发词列表 |
| `spawn_threshold` | float | 0.7 | 置信度阈值 |

### 警告阈值（软限制）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `warn_depth` | 3 | 深度警告阈值 |
| `warn_thoughts` | 5 | 思考数量警告阈值 |
| `warn_timeout` | 10.0 | 超时警告阈值（秒） |

## 使用场景

### 场景 1：简单对话（仅 System 1）

**适用**：闲聊、简单问答、快速响应

```python
from loom.weave import create_agent, run

agent = create_agent("chatbot", role="聊天助手")
result = run(agent, "今天天气怎么样？")
```

**特点**：快速、流畅、无需深度思考

### 场景 2：复杂分析（System 1 + System 2）

**适用**：数据分析、问题诊断、多角度思考

```python
from loom.node.agent import AgentNode, ThinkingPolicy
from loom.api.main import LoomApp

app = LoomApp()

# 启用深度思考
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=5,
    max_depth=3,
    trigger_words=["分析", "诊断", "评估"]
)

agent = AgentNode(
    node_id="analyst",
    dispatcher=app.dispatcher,
    role="数据分析师",
    thinking_policy=thinking_policy
)

result = await app.run(agent, "分析这个系统性能下降的根本原因")
```

**工作流程**：
1. System 1 快速给出初步响应
2. System 2 并行启动深度分析
3. 生成多个思考节点（如：检查日志、分析指标、对比历史）
4. 投影合并所有洞察

### 场景 3：受控深度思考（限制资源）

**适用**：需要深度思考但要控制成本

```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=2,              # 限制并行思考数
    max_depth=2,                 # 限制递归深度
    total_token_budget=5000,     # 限制 Token 使用
    thought_timeout=30.0         # 30秒超时
)

agent = AgentNode(
    node_id="budget-analyst",
    dispatcher=app.dispatcher,
    role="成本敏感的分析师",
    thinking_policy=thinking_policy
)
```

**特点**：
- 平衡深度和成本
- 避免资源过度消耗
- 适合生产环境

### 场景 4：触发词模式（智能启动）

**适用**：根据任务内容自动决定是否启用 System 2

```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    trigger_words=["分析", "推理", "深入", "评估", "诊断"],
    max_thoughts=3
)

agent = AgentNode(
    node_id="smart-agent",
    dispatcher=app.dispatcher,
    role="智能助手",
    thinking_policy=thinking_policy
)

# 包含触发词 -> 启动 System 2
await app.run(agent, "请深入分析这个问题")

# 不包含触发词 -> 仅 System 1
await app.run(agent, "你好")
```

**特点**：
- 自动识别复杂任务
- 节省不必要的计算
- 用户体验更智能

## 最佳实践

### 1. 选择合适的模式

| 任务类型 | 推荐配置 |
|---------|---------|
| 简单对话 | System 1 only |
| 快速问答 | System 1 only |
| 数据分析 | System 1 + System 2 |
| 问题诊断 | System 1 + System 2 |
| 多步推理 | System 1 + System 2 |
| 创意生成 | System 1 + System 2 |

### 2. 合理设置限制

**生产环境建议**：
```python
thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=3,           # 避免过多并行
    max_depth=2,              # 防止无限递归
    total_token_budget=10000, # 控制成本
    thought_timeout=60.0      # 避免长时间等待
)
```

### 3. 使用触发词优化

**推荐触发词**：
- 分析类：`["分析", "评估", "诊断", "检查"]`
- 推理类：`["推理", "推导", "证明", "解释"]`
- 深度类：`["深入", "详细", "全面", "彻底"]`

### 4. 监控和调试

观察 System 2 的运行状态：
```python
# 查看认知状态
print(f"活跃思考数: {len(agent.cognitive_state.active_thoughts)}")
print(f"状态空间维度: {agent.cognitive_state.dimensionality()}")

# 查看完成的思考
for thought in agent.cognitive_state.get_completed_thoughts():
    print(f"思考 {thought.id}: {thought.result}")
```

## 常见问题

### Q1: System 2 什么时候启动？

**A**: 当 `ThinkingPolicy.enabled=True` 时，System 2 会在以下情况启动：
- 任务包含触发词（如果配置了 `trigger_words`）
- 或者无条件启动（如果 `trigger_words` 为空）

### Q2: 如何查看 System 2 的输出？

**A**: System 2 的输出通过投影算子（ProjectionOperator）合并到最终结果中：
```python
# 查看投影后的洞察
observables = agent.projector.project(agent.cognitive_state)
for obs in observables:
    print(f"洞察: {obs.content}")
```

### Q3: System 1 和 System 2 会冲突吗？

**A**: 不会。两个系统并行工作：
- System 1 提供快速流式输出
- System 2 在后台深度思考
- 最终通过投影合并结果

### Q4: 如何控制成本？

**A**: 使用限制参数：
- `max_thoughts`: 限制并行思考数
- `max_depth`: 限制递归深度
- `total_token_budget`: 限制 Token 使用
- `thought_timeout`: 限制思考时间

## 总结

双系统架构提供了灵活的问题解决方式：

1. **System 1**：快速、直觉、适合简单任务
2. **System 2**：深度、理性、适合复杂任务
3. **配置灵活**：通过 ThinkingPolicy 精确控制
4. **成本可控**：多种限制参数保护资源

## 相关文档

- [架构设计](../concepts/architecture.md) - 了解双系统架构
- [认知动力学](../concepts/cognitive-dynamics.md) - 理解理论基础
- [创建 Agent](../tutorials/01-your-first-agent.md) - 基础教程
