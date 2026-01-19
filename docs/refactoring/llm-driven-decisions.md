# LLM-Driven Decision Making Refactoring

## 核心原则

**"所有价值都在RL过的模型里，不在你那上万行的抽象里"**

框架提供能力，LLM做决策（token阈值除外）。

## 重构概览

本次重构将框架中的硬编码决策逻辑转换为LLM主动决策，遵循以下原则：

1. **框架职责**：提供基础设施和能力（存储、检索、执行）
2. **LLM职责**：做出所有智能决策（查询什么、存储什么、如何处理）
3. **硬限制**：Token限制、时间限制、成本限制由框架强制执行

## 已完成的重构

### 1. 上下文管理系统 (Context Management)

#### 问题识别

**文件**: `loom/memory/task_context.py`

**硬编码决策**:
- Line 143-144: 框架决定从L2和L1各取一半的任务
- Line 186-190: 框架决定只查询"node.thinking"事件
- Line 255-256: 框架决定按创建时间排序
- Line 302-311: 框架决定保留最近的消息，丢弃旧消息

#### 解决方案

**创建的工具**: `loom/tools/context_tools.py`

提供8个上下文查询工具，让LLM主动决定查询什么：

**Memory查询工具**:
- `query_l1_memory(limit)` - 查询L1最近任务
- `query_l2_memory(limit)` - 查询L2重要任务
- `query_l3_memory(limit)` - 查询L3任务摘要
- `query_l4_memory(query, limit)` - L4语义搜索

**Event查询工具**:
- `query_events_by_action(action, node_filter, limit)` - 按动作类型查询
- `query_events_by_node(node_id, action_filter, limit)` - 按节点查询
- `query_recent_events(limit, action_filter, node_filter)` - 查询最近事件
- `query_thinking_process(node_id, task_id, limit)` - 查询思考过程

**重构后的行为**:
- `TaskContextManager.build_context()` 优化为自动包含L1 + LLM主动查询L2/L3/L4
- **L1自动包含**：最近10个任务自动添加到上下文（保证速度）
- **L2/L3/L4按需查询**：LLM通过工具主动查询，以压缩陈述句形式返回
- **逐级压缩策略**：
  - L1: 完整对话消息（自动包含）
  - L2: 中等压缩 - "执行了[action]操作，参数[params]，结果[result]"
  - L3: 高度压缩 - "[action]: [简短描述]"
  - L4: 极简压缩 - "[action]完成/执行"
- Token限制仍由框架强制执行（硬限制）

### 2. 记忆管理系统 (Memory Management)

#### 问题识别

**文件**: `loom/memory/core.py`

**硬编码决策**:
- Line 77: 默认将任务存储到L1（框架决定）
- Line 413, 434: 90%阈值触发提升（框架决定何时提升）
- Line 453: 重要性>0.6的任务提升到L2（框架决定重要性阈值）
- Line 469: 移除20%最不重要的任务（框架决定移除比例）
- Line 466: 按重要性降序排序（框架决定排序策略）

#### 解决方案

**创建的工具**: `loom/tools/memory_management_tools.py`

提供3个记忆管理工具，让LLM主动管理记忆层级：

**记忆状态工具**:
- `get_memory_stats()` - 获取各层记忆使用情况，让LLM了解记忆压力

**任务提升工具**:
- `promote_task_to_l2(task_id, reason)` - 将任务从L1提升到L2，LLM决定哪些任务重要

**任务摘要工具**:
- `create_task_summary(task_id, summary, importance, tags)` - 创建任务摘要存储到L3，LLM决定如何总结

**重构后的行为**:
- 框架仍然将新任务默认存储到L1（合理的默认行为）
- LLM通过`get_memory_stats()`了解记忆使用情况
- LLM决定哪些任务应该提升到L2（重要任务）
- LLM决定如何总结任务到L3（压缩存储）
- 移除自动提升逻辑（promote_tasks方法不再自动调用）

## 已分析但无需重构的部分

### 3. 技能加载系统 (_load_relevant_skills)

**文件**: `loom/orchestration/agent.py:547`

**分析结果**: ✅ 已经是LLM驱动

**现有实现**:
- 使用`SkillActivator`和LLM判断哪些技能相关
- LLM决定加载哪些技能，框架只提供基础设施
- 符合"框架提供能力，LLM做决策"的原则

**结论**: 无需修改，已经符合设计原则

### 4. 临时消息过滤 (_filter_ephemeral_messages)

**文件**: `loom/orchestration/agent.py:432`

**分析结果**: ✅ 框架优化，类似Token限制

**现有实现**:
- 过滤重复的临时工具输出（如多次`ls`调用）
- 只保留最近N次输出，防止上下文污染
- 类似于Token限制的资源管理优化

**结论**: 无需修改，属于框架资源管理优化（类似"token阈值除外"）

## 重构总结

### 创建的新文件

1. **loom/tools/context_tools.py** (682行)
   - 8个上下文查询工具
   - ContextToolExecutor执行器
   - 让LLM主动查询记忆和事件

2. **loom/tools/memory_management_tools.py** (334行)
   - 3个记忆管理工具
   - MemoryManagementToolExecutor执行器
   - 让LLM主动管理记忆层级

3. **docs/refactoring/llm-driven-decisions.md** (本文档)
   - 重构文档和集成指南

### 修改的文件

1. **loom/memory/task_context.py**
   - 简化`build_context()`方法
   - 移除自动上下文收集逻辑
   - 保留Token限制强制执行

### 设计原则对照

| 组件 | 旧方式 | 新方式 |
|------|--------|--------|
| L1上下文 | 框架自动收集 | ✅ 框架自动包含（性能优化） |
| L2/L3/L4查询 | 框架自动收集完整数据 | LLM按需查询压缩陈述句 |
| 压缩策略 | 框架硬编码压缩规则 | 逐级压缩（L2→L3→L4） |
| 记忆层级 | 框架自动提升（90%阈值，0.6重要性） | LLM决定何时提升哪些任务 |
| 任务摘要 | 框架自动生成摘要 | LLM决定如何总结任务 |
| 技能加载 | ✅ 已经是LLM驱动 | 保持不变 |
| Token限制 | ✅ 框架强制执行 | 保持不变（硬限制） |
| 临时消息 | ✅ 框架优化 | 保持不变（资源管理） |

## 集成指南

### 如何使用新工具

#### 1. 在Agent中注册上下文查询工具

```python
from loom.tools.context_tools import create_all_context_tools, ContextToolExecutor
from loom.orchestration.agent import Agent

# 创建Agent
agent = Agent(
    agent_id="my-agent",
    llm_provider=llm,
    memory=memory,
    event_bus=event_bus,
)

# 创建上下文工具执行器
context_executor = ContextToolExecutor(memory=memory, event_bus=event_bus)

# 注册上下文查询工具
context_tools = create_all_context_tools()
for tool in context_tools:
    agent.register_tool(tool, context_executor.execute)
```

#### 2. 在Agent中注册记忆管理工具

```python
from loom.tools.memory_management_tools import (
    create_all_memory_management_tools,
    MemoryManagementToolExecutor
)

# 创建记忆管理工具执行器
memory_executor = MemoryManagementToolExecutor(memory=memory)

# 注册记忆管理工具
memory_tools = create_all_memory_management_tools()
for tool in memory_tools:
    agent.register_tool(tool, memory_executor.execute)
```

#### 3. 更新系统提示词

为了让LLM有效使用这些工具，需要在系统提示词中添加指导：

```python
system_prompt = """
You are an intelligent agent with access to memory and event query tools.

**Context Management**:
- Use query_l1_memory() to see recent tasks
- Use query_l2_memory() to see important tasks
- Use query_l3_memory() to see task summaries
- Use query_l4_memory(query) for semantic search
- Use query_events_by_action() to see specific event types
- Use query_thinking_process() to see what you or others have been thinking

**Memory Management**:
- Use get_memory_stats() to check memory usage
- Use promote_task_to_l2(task_id) to mark important tasks
- Use create_task_summary(task_id, summary) to compress old tasks

**Guidelines**:
- Query context as needed, don't assume you have all information
- Promote important tasks to L2 to keep them in working memory
- Create summaries for completed tasks to save memory
- Check memory stats periodically to avoid running out of space
"""
```

## 下一步工作

### 必须完成的集成任务

1. **更新Agent初始化逻辑**
   - 在Agent构造函数中自动注册上下文查询工具
   - 在Agent构造函数中自动注册记忆管理工具
   - 更新默认系统提示词，包含工具使用指导

2. **移除旧的自动提升逻辑**
   - 在Agent中移除对`memory.promote_tasks()`的自动调用
   - 让LLM通过工具主动管理记忆

3. **更新测试**
   - 创建上下文查询工具的单元测试
   - 创建记忆管理工具的单元测试
   - 创建集成测试验证LLM驱动的决策

4. **更新文档**
   - 更新用户指南，说明新的LLM驱动方式
   - 更新API文档，说明新工具的使用方法

### 可选的优化任务

1. **性能优化**
   - 缓存频繁查询的上下文
   - 优化工具执行性能

2. **监控和调试**
   - 添加工具调用日志
   - 添加LLM决策追踪

3. **更多LLM驱动的能力**
   - 分析其他可能的硬编码决策
   - 继续将决策权交给LLM

## 结论

本次重构成功实现了"框架提供能力，LLM做决策"的核心原则：

### 关键成果

1. **创建了11个新工具**，让LLM主动控制上下文查询和记忆管理
2. **简化了TaskContextManager**，移除了硬编码的上下文收集逻辑
3. **保留了合理的框架优化**（Token限制、临时消息过滤）
4. **识别了已经符合原则的部分**（技能加载系统）

### 设计哲学

**框架的职责**：
- 提供基础设施（存储、检索、执行）
- 强制执行硬限制（Token、时间、成本）
- 优化资源使用（临时消息过滤）

**LLM的职责**：
- 决定查询什么上下文
- 决定哪些任务重要
- 决定如何总结任务
- 决定何时清理记忆

### 价值体现

> "所有价值都在RL过的模型里，不在你那上万行的抽象里"

通过这次重构，我们将决策权从框架的硬编码逻辑转移到了经过RL训练的LLM模型，让模型的智能真正发挥作用。框架不再试图"聪明"地做决策，而是专注于提供可靠的基础设施和工具，让LLM自主决策。

---

**文档版本**: v0.3.9
**创建日期**: 2026-01-19
**作者**: Claude Code (Anthropic)
