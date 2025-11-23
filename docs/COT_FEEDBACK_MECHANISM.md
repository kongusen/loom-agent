# Loom 框架 CoT 反馈机制梳理

## 概述

Loom 框架实现了一套完整的 **Chain of Thought (CoT) 反馈机制**，在递归执行过程中为 LLM 提供智能指导，帮助其更好地完成任务。该机制通过多层反馈系统，在工具执行后分析结果，生成指导消息，引导 LLM 的下一步行动。

## 核心组件架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentExecutor.tt()                        │
│              (Tail-Recursive Control Loop)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Phase 0: Recursion Control          │
        │   - RecursionMonitor                  │
        │   - Termination Detection             │
        │   - Warning Generation                 │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Phase 4: Tool Execution              │
        │   - ToolOrchestrator                   │
        │   - Tool Results Collection            │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Phase 5: Feedback Generation        │
        │   - Tool Result Analysis               │
        │   - Recursion Guidance Generation      │
        │   - Recursion Depth Hints              │
        └───────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   Recursive Call (tt)                  │
        │   - Messages with Guidance             │
        └───────────────────────────────────────┘
```

## 反馈机制层次

### 1. 递归控制反馈层 (Recursion Control Feedback)

**位置**: `loom/core/recursion_control.py`

**功能**: 在递归执行前检测终止条件和循环模式，生成终止或警告消息。

#### 1.1 终止检测 (`RecursionMonitor.check_termination`)

检测四种终止条件：

1. **最大迭代次数** (`MAX_ITERATIONS`)
   - 硬性限制，防止无限递归
   - 触发时生成终止消息

2. **重复工具调用** (`DUPLICATE_TOOLS`)
   - 检测连续 N 次调用同一工具
   - 默认阈值：3 次
   - 表示可能陷入循环

3. **循环模式检测** (`LOOP_DETECTED`)
   - 检测输出中的重复模式
   - 窗口大小：5 次迭代
   - 识别行为循环

4. **错误率阈值** (`ERROR_THRESHOLD`)
   - 计算错误率：`error_count / iteration`
   - 默认阈值：0.5 (50%)
   - 超过阈值时终止

#### 1.2 终止消息生成 (`build_termination_message`)

根据终止原因生成相应的指导消息：

```python
TerminationReason.DUPLICATE_TOOLS:
    "⚠️ Detected repeated tool calls. Please proceed with available information."

TerminationReason.LOOP_DETECTED:
    "⚠️ Detected execution loop. Please break the pattern and complete the task."

TerminationReason.MAX_ITERATIONS:
    "⚠️ Maximum iterations reached. Please provide the best answer with current information."

TerminationReason.ERROR_THRESHOLD:
    "⚠️ Too many errors occurred. Please complete the task with current information."
```

#### 1.3 早期警告 (`should_add_warning`)

在接近限制时提供早期警告（默认阈值：80%）：

- **接近迭代限制**: 提醒剩余迭代次数
- **工具调用重复**: 警告工具调用模式

**示例**:
```python
"⚠️ Approaching iteration limit (5 remaining). Please work towards completing the task."
"⚠️ You've called 'search' multiple times. Consider trying a different approach or completing the task."
```

### 2. 工具结果分析层 (Tool Result Analysis)

**位置**: `loom/core/agent_executor.py::_analyze_tool_results`

**功能**: 分析工具执行结果，评估任务完成度和结果质量。

#### 2.1 分析维度

```python
{
    "has_data": bool,              # 是否包含数据
    "has_errors": bool,            # 是否包含错误
    "suggests_completion": bool,   # 是否建议完成任务
    "result_types": List[str],     # 结果类型列表
    "completeness_score": float    # 完成度评分 (0.0-1.0)
}
```

#### 2.2 关键词检测

**数据类型检测**:
- 关键词: `"data"`, `"found"`, `"retrieved"`, `"table"`, `"schema"`, `"获取到"`, `"表结构"`
- 影响: `completeness_score += 0.3`

**错误检测**:
- 关键词: `"error"`, `"failed"`, `"exception"`, `"not found"`
- 标记: `has_errors = True`

**完成建议检测**:
- 关键词: `"complete"`, `"finished"`, `"done"`, `"ready"`
- 影响: `completeness_score += 0.5`

**分析结果检测**:
- 关键词: `"analysis"`, `"summary"`, `"conclusion"`, `"insights"`
- 影响: `completeness_score += 0.4`

### 3. 递归指导生成层 (Recursion Guidance Generation)

**位置**: `loom/core/agent_executor.py::_generate_recursion_guidance`

**功能**: 基于工具结果分析和任务上下文，生成下一轮递归的指导消息。

#### 3.1 指导生成流程

```
工具结果分析
    ↓
原始任务提取
    ↓
任务处理器匹配 (TaskHandler)
    ↓
生成指导消息
    ↓
注入到下一轮消息中 (system message)
```

#### 3.2 任务处理器机制 (`TaskHandler`)

**基类定义**:
```python
class TaskHandler:
    def can_handle(self, task: str) -> bool:
        """判断是否能处理给定的任务"""
        
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成递归指导消息"""
```

**匹配逻辑**:
1. 遍历所有注册的 `TaskHandler`
2. 调用 `can_handle()` 检查是否匹配
3. 使用第一个匹配的处理器生成指导
4. 如果没有匹配，使用默认指导生成器

#### 3.3 默认指导生成 (`_generate_default_guidance`)

根据结果分析生成三种类型的指导：

**1. 完成建议场景** (`suggests_completion` 或 `recursion_depth >= 6`):
```python
"""工具调用已完成。请基于返回的结果完成任务：{original_task}

请提供完整、准确的最终答案。"""
```

**2. 错误场景** (`has_errors`):
```python
"""工具执行遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查工具参数是否正确
- 尝试使用不同的工具或方法
- 如果问题持续，请说明具体错误"""
```

**3. 继续执行场景** (默认):
```python
"""继续处理任务：{original_task}

当前进度：{completeness_score:.0%}
建议：使用更多工具收集信息或分析已获得的结果"""
```

### 4. 递归深度提示层 (Recursion Depth Hints)

**位置**: `loom/core/agent_executor.py::_build_recursion_hint`

**功能**: 在深度递归时（深度 > 3）提供进度提示，帮助 LLM 了解执行状态。

#### 4.1 提示内容

```python
"""🔄 Recursion Status:
- Depth: {current_depth}/{max_depth} ({progress:.0f}% of maximum)
- Remaining iterations: {remaining}

Please review the tool results above and make meaningful progress towards completing the task.
Avoid calling the same tool repeatedly with the same arguments unless necessary.
If you have enough information, please provide your final answer."""
```

#### 4.2 触发条件

- 递归深度 > 3
- 在准备递归消息时自动添加

### 5. 统一协调反馈层 (Unified Coordination Feedback)

**位置**: `loom/core/unified_coordination.py::IntelligentCoordinator`

**功能**: 通过智能协调器提供高级反馈和策略调整。

#### 5.1 任务类型分析

**任务分类**:
- `analysis`: 分析任务
- `generation`: 生成任务
- `sql`: SQL 查询任务
- `testing`: 测试任务
- `reporting`: 报告任务
- `general`: 通用任务

#### 5.2 复杂度计算

```python
complexity = 0.0
complexity += min(len(task_content) / 1000, 0.3)  # 内容长度因子
complexity += min(keyword_count * 0.1, 0.3)         # 关键词因子
complexity += recursion_factor * 0.4                 # 递归深度因子
```

#### 5.3 动态策略调整

基于任务类型和复杂度调整上下文优先级：

- **复杂分析任务**: 提高示例和指导优先级
- **SQL 任务**: 提高表结构和查询示例优先级
- **深度递归**: 优先保留核心指令，降低示例优先级

## 反馈消息注入流程

### 消息准备流程 (`_prepare_recursive_messages`)

```python
# 1. 添加 assistant 消息（包含 tool_calls）
assistant_msg = Message(
    role="assistant",
    content=assistant_content,
    metadata={"tool_calls": tool_calls}
)

# 2. 添加工具结果消息
for result in tool_results:
    tool_msg = Message(
        role="tool",
        content=result.content,
        tool_call_id=result.tool_call_id
    )

# 3. 生成并注入指导消息（系统消息）
guidance_message = self._generate_recursion_guidance(...)
if guidance_message:
    next_messages.append(Message(role="system", content=guidance_message))

# 4. 深度递归时添加进度提示
if turn_state.turn_counter > 3:
    hint = Message(role="system", content=hint_content)
    next_messages.append(hint)
```

### 消息顺序要求

遵循 OpenAI API 规范：
1. `assistant` 消息（包含 `tool_calls`）必须在最前
2. `tool` 消息紧跟在对应的 `assistant` 消息后
3. `system` 消息（指导信息）在 `tool` 消息之后
4. 不能破坏消息链的连续性

## 反馈机制执行时序

```
┌─────────────────────────────────────────────────────────────┐
│ Turn N: 执行阶段                                              │
├─────────────────────────────────────────────────────────────┤
│ 1. RecursionMonitor 检查终止条件                             │
│    ├─ 检测循环/错误/限制                                      │
│    └─ 生成终止/警告消息 (system message)                      │
│                                                              │
│ 2. 执行工具调用                                               │
│    ├─ ToolOrchestrator.execute_batch()                       │
│    └─ 收集工具结果 (ToolResult[])                             │
│                                                              │
│ 3. 分析工具结果                                               │
│    ├─ _analyze_tool_results()                                │
│    └─ 生成 result_analysis                                    │
│                                                              │
│ 4. 生成递归指导                                               │
│    ├─ _extract_original_task()                               │
│    ├─ TaskHandler 匹配                                        │
│    ├─ _generate_recursion_guidance()                         │
│    └─ 生成指导消息                                            │
│                                                              │
│ 5. 准备递归消息                                               │
│    ├─ assistant 消息 (tool_calls)                             │
│    ├─ tool 消息 (results)                                     │
│    ├─ system 消息 (guidance)                                  │
│    └─ system 消息 (depth hint, if depth > 3)                  │
│                                                              │
│ 6. 递归调用 tt()                                              │
│    └─ 传入准备好的消息                                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Turn N+1: 接收反馈                                           │
├─────────────────────────────────────────────────────────────┤
│ LLM 接收包含以下信息的消息：                                   │
│ 1. 工具执行结果                                               │
│ 2. 任务完成度分析                                             │
│ 3. 递归指导建议                                               │
│ 4. 执行进度提示                                               │
│                                                              │
│ LLM 基于反馈决定下一步行动：                                   │
│ - 继续调用工具                                                │
│ - 分析已有结果                                                │
│ - 生成最终答案                                                │
└─────────────────────────────────────────────────────────────┘
```

## 自定义扩展

### 实现自定义 TaskHandler

```python
from loom.core.agent_executor import TaskHandler
from typing import Dict, Any

class CustomTaskHandler(TaskHandler):
    def can_handle(self, task: str) -> bool:
        # 定义任务匹配逻辑
        return "custom_keyword" in task.lower()
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        # 生成领域特定的指导消息
        if result_analysis["has_data"]:
            return f"数据已获取，请分析：{original_task}"
        else:
            return f"继续收集数据：{original_task}"

# 使用
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    task_handlers=[CustomTaskHandler()]
)
```

### 配置递归监控参数

```python
from loom.core.recursion_control import RecursionMonitor

monitor = RecursionMonitor(
    max_iterations=100,           # 最大迭代次数
    duplicate_threshold=5,        # 重复工具调用阈值
    loop_detection_window=10,     # 循环检测窗口
    error_threshold=0.3           # 错误率阈值
)

executor = AgentExecutor(
    llm=llm,
    tools=tools,
    recursion_monitor=monitor
)
```

## 关键设计原则

### 1. 渐进式反馈
- **早期警告**: 在接近限制时提供警告，而非直接终止
- **分层指导**: 从终止检测到深度提示，多层次反馈

### 2. 上下文感知
- **任务类型识别**: 根据任务类型调整反馈策略
- **结果质量分析**: 基于工具结果质量生成相应指导

### 3. 可扩展性
- **TaskHandler 机制**: 支持领域特定的指导生成
- **统一协调**: 通过 IntelligentCoordinator 统一管理

### 4. 消息格式合规
- **API 规范**: 严格遵循 OpenAI API 消息格式要求
- **消息顺序**: 保证消息链的连续性和正确性

## 性能优化

### 1. 批量事件处理
- 通过 `EventProcessor` 批量处理事件
- 减少事件处理开销

### 2. 上下文缓存
- `ContextAssembler` 支持组件缓存
- 减少重复组装开销

### 3. 智能过滤
- `EventFilter` 过滤不必要的事件
- 降低事件流处理负担

## 总结

Loom 框架的 CoT 反馈机制通过五个层次的反馈系统，在递归执行过程中为 LLM 提供智能指导：

1. **递归控制反馈**: 检测终止条件和循环，生成终止/警告消息
2. **工具结果分析**: 分析工具执行结果，评估任务完成度
3. **递归指导生成**: 基于分析结果生成任务特定的指导消息
4. **递归深度提示**: 在深度递归时提供进度提示
5. **统一协调反馈**: 通过智能协调器提供高级策略调整

该机制具有高度的可扩展性，支持开发者通过 `TaskHandler` 实现领域特定的反馈逻辑，同时保证了消息格式的合规性和执行的高效性。

