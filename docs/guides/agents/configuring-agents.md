# 配置 Agent

> **问题导向** - 学会配置 Agent 的各种选项和参数

## AgentNode 配置参数

### 基本参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | str | Agent 唯一标识符 |
| `role` | str | Agent 角色描述 |
| `system_prompt` | str | 系统提示词 |
| `provider` | LLMProvider | LLM 提供商 |

### 高级参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tools` | List[ToolNode] | [] | 可用工具列表 |
| `memory` | MemoryInterface | HierarchicalMemory() | 记忆系统 |
| `thinking_policy` | ThinkingPolicy | ThinkingPolicy() | System 2 配置 |
| `enable_auto_reflection` | bool | False | 自动反思 |
| `projection_strategy` | str | "selective" | 投影策略 |

## 配置示例

### 基础配置

```python
from loom.node.agent import AgentNode
from loom.api.main import LoomApp

app = LoomApp()

agent = AgentNode(
    node_id="assistant",
    dispatcher=app.dispatcher,
    role="通用助手",
    system_prompt="你是一个友好的AI助手"
)
```

### 配置 System 2（深度思考）

```python
from loom.node.agent import ThinkingPolicy

thinking_policy = ThinkingPolicy(
    enabled=True,
    max_thoughts=3,
    max_depth=2,
    trigger_words=["分析", "推理"]
)

agent = AgentNode(
    node_id="analyst",
    dispatcher=app.dispatcher,
    role="分析师",
    thinking_policy=thinking_policy
)
```

### 配置记忆系统

```python
from loom.builtin.memory import HierarchicalMemory

memory = HierarchicalMemory(
    max_short_term=10,
    max_long_term=100
)

agent = AgentNode(
    node_id="assistant",
    dispatcher=app.dispatcher,
    role="助手",
    memory=memory
)
```

## 相关文档

- [创建 Agent](creating-agents.md) - Agent 创建方法
- [双系统使用](../dual-system-usage.md) - 配置 System 1 和 System 2
- [配置 LLM](../configuration/llm-providers.md) - 配置 LLM 提供商
