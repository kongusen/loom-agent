# 配置 Agent

> **问题导向** - 学会配置 Agent 的各种选项和参数

## AgentNode 配置参数

### 基本参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `node_id` | str | Agent 唯一标识符 |
| `dispatcher` | Dispatcher | 事件调度器 |
| `role` | str | Agent 角色描述 |
| `system_prompt` | str | 系统提示词 |
| `provider` | LLMProvider | LLM 提供商 |

### 认知配置参数（推荐）

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `cognitive_config` | CognitiveConfig | None | **统一认知配置**（推荐使用） |

### 高级参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `tools` | List[ToolNode] | [] | 可用工具列表 |
| `execution_config` | ExecutionConfig | ExecutionConfig.default() | 执行配置 |
| `thinking_policy` | ThinkingPolicy | ThinkingPolicy() | 思考策略 |
| `enable_auto_reflection` | bool | False | 自动反思 |
| `projection_strategy` | str | "selective" | 投影策略 |
| `fractal_config` | FractalConfig | None | Fractal 架构配置 |

## 配置示例

### 基础配置

```python
from loom.kernel.core.bus import UniversalEventBus
from loom.kernel.core import Dispatcher
from loom.node.agent import AgentNode
from loom.llm import OpenAIProvider

# 创建事件总线和调度器
bus = UniversalEventBus()
dispatcher = Dispatcher(bus=bus)

# 创建 LLM 提供商
provider = OpenAIProvider(api_key="your-api-key")

# 创建 Agent（使用默认配置）
agent = AgentNode(
    node_id="assistant",
    dispatcher=dispatcher,
    role="通用助手",
    system_prompt="你是一个友好的AI助手",
    provider=provider
)
```

### 使用 CognitiveConfig（推荐）

**快速模式** - 适合简单查询，快速响应：

```python
from loom.config.cognitive import CognitiveConfig

# 使用快速模式预设
fast_config = CognitiveConfig.fast_mode()

agent = AgentNode(
    node_id="fast-assistant",
    dispatcher=dispatcher,
    role="快速助手",
    system_prompt="你是一个快速响应的助手",
    provider=provider,
    cognitive_config=fast_config
)
```

**深度模式** - 适合复杂任务，深度分析：

```python
# 使用深度模式预设
deep_config = CognitiveConfig.deep_mode()

agent = AgentNode(
    node_id="analyst",
    dispatcher=dispatcher,
    role="分析师",
    system_prompt="你是一个深度分析专家",
    provider=provider,
    cognitive_config=deep_config
)
```

**平衡模式** - 默认配置，适合大多数场景：

```python
# 使用平衡模式（默认）
balanced_config = CognitiveConfig.balanced_mode()

agent = AgentNode(
    node_id="assistant",
    dispatcher=dispatcher,
    cognitive_config=balanced_config
)
```

### 自定义配置

如果预设模式不满足需求，可以自定义配置：

```python
# 创建自定义配置
custom_config = CognitiveConfig.default()

# 调整路由参数
custom_config.router_max_s1_length = 50  # System 1 最大查询长度
custom_config.router_s1_confidence_threshold = 0.75  # 置信度阈值

# 调整上下文参数
custom_config.curation_max_tokens = 6000  # 上下文最大 token 数
custom_config.context_max_tokens = 12000  # 总上下文限制

# 调整 Memory 参数
custom_config.memory_max_l1_size = 30  # L1 缓冲区大小
custom_config.memory_auto_vectorize_l4 = True  # 自动向量化 L4

agent = AgentNode(
    node_id="custom-agent",
    dispatcher=dispatcher,
    provider=provider,
    cognitive_config=custom_config
)
```

### 配置参数说明

**路由配置**:
- `router_max_s1_length`: System 1 处理的最大查询长度（词数）
- `router_s1_confidence_threshold`: System 1 置信度阈值（0-1）
- `router_enable_heuristics`: 是否启用启发式路由

**上下文配置**:
- `curation_max_tokens`: 策展后的最大 token 数
- `context_max_tokens`: 总上下文限制
- `context_strategy`: 上下文策略（"auto", "system1", "system2"）

**Memory 配置**:
- `memory_max_l1_size`: L1 缓冲区大小
- `memory_auto_vectorize_l4`: 是否自动向量化 L4 全局知识
- `memory_enable_auto_compression`: 是否启用自动压缩



## 相关文档

- [创建 Agent](creating-agents.md) - Agent 创建方法
- [双系统使用](../dual-system-usage.md) - System 1/2 详细说明
- [配置 LLM](../configuration/llm-providers.md) - 配置 LLM 提供商
- [Memory 系统](../../concepts/memory_system.md) - Memory 系统架构
- [架构概念](../../concepts/architecture.md) - 整体架构说明

## 最佳实践

1. **使用预设模式**: 优先使用 `fast_mode()`, `balanced_mode()`, `deep_mode()` 预设
2. **按需自定义**: 只在预设模式不满足需求时才自定义配置
3. **测试配置**: 使用 `CognitiveConfig.for_testing()` 进行单元测试
4. **性能优化**: 使用 `CognitiveConfig.for_performance()` 优化性能
5. **准确性优先**: 使用 `CognitiveConfig.for_accuracy()` 提升准确性
