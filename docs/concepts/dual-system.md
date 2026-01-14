# 统一处理架构 (Unified Processing Architecture)

Loom 采用**统一的ReAct循环处理机制**，所有查询都通过相同的处理流程，根据查询特征自适应调整上下文大小和策略。

## 统一处理流程

所有查询都通过统一的ReAct循环处理：

```
用户输入 → 添加到记忆 → ReAct循环
                              ↓
                    ┌─────────┴─────────┐
                    ↓                   ↓
              上下文组装          工具调用
            (动态调整大小)      (按需执行)
                    ↓                   ↓
               LLM调用 ←──────────────┘
                    ↓
              流式输出/完整响应
```

## 查询特征分析

Loom 使用**查询特征提取器 (QueryFeatureExtractor)** 分析查询特征，用于动态调整上下文策略。

### 特征提取

系统通过以下方式分析查询：

1.  **查询特征提取**：使用 `QueryFeatureExtractor` 提取查询特征。
2.  **复杂度评分**：分析 Tokens 数量、意图深度。
3.  **模式匹配**：检测是否包含代码、数学公式或复杂的指令关键词（如 "计划"、"比较"、"分析"）。
4.  **工具需求检测**：检测查询是否需要工具调用（v0.3.7+）。

### 上下文策略调整

根据查询特征，系统会动态调整：
- **上下文大小**：简单查询使用较小上下文，复杂查询使用完整上下文
- **处理深度**：根据查询复杂度决定是否需要多轮工具调用和深度推理
- **输出方式**：支持流式输出和完整响应

## 使用案例

所有查询都通过统一流程处理，但会根据特征自动调整策略：

*   **简单查询**（自动使用较小上下文）:
    *   "即使给我讲个笑话。"
    *   "在这个上下文中 'Loom' 是什么意思？"
*   **复杂查询**（自动使用完整上下文和深度推理）:
    *   "写一个 Python 脚本来抓取这个网站。"
    *   "分析过去 5 年的市场趋势。"
    *   "制定一个旅行计划。"

## 认知配置

你可以通过 `CognitiveSystemConfig` 配置处理行为：

```python
from loom.config.cognitive import CognitiveSystemConfig

# 使用预设模式（影响上下文大小和处理策略）
config = CognitiveSystemConfig.fast_mode()      # 偏向快速响应（较小上下文）
config = CognitiveSystemConfig.balanced_mode() # 平衡模式（默认）
config = CognitiveSystemConfig.deep_mode()      # 偏向深度分析（完整上下文）

# 自定义配置
config = CognitiveSystemConfig.default()
config.curation_max_tokens = 6000  # 调整上下文大小
config.context_max_tokens = 12000
```

**注意**：这些配置主要影响上下文大小和处理策略，所有查询仍通过统一的ReAct循环处理。
