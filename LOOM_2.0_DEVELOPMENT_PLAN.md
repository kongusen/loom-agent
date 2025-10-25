# Loom 2.0 开发计划

**版本**: v2.0.0-alpha
**开始日期**: 2025-10-25
**当前状态**: 阶段 1 进行中 (Task 1.1 已完成)
**预计完成**: 2025-11-20 (约 4 周)

---

## 📋 目录

1. [项目愿景](#项目愿景)
2. [架构概览](#架构概览)
3. [核心改进点](#核心改进点)
4. [迭代路线图](#迭代路线图)
5. [当前进度](#当前进度)
6. [下一步行动](#下一步行动)
7. [参考文档](#参考文档)

---

## 项目愿景

### 为什么需要 Loom 2.0？

Loom 1.0 存在以下关键问题：

1. ❌ **RAG Context Bug**: 检索上下文在 `_inject_system_prompt` 中被覆盖
2. ❌ **工具并行执行不安全**: 无差别并行，不区分只读/写入工具
3. ❌ **非流式体验**: `execute()` 返回字符串，无实时进度
4. ❌ **Prompt 工程薄弱**: 工具提示过于简单，缺少详细指导
5. ❌ **单层安全检查**: 只有简单的权限管理，无路径验证

### Loom 2.0 的目标

受 **Claude Code** 启发，Loom 2.0 将实现：

✅ **全链路流式架构** - 从 LLM 到工具到 UI，所有组件都流式
✅ **智能工具编排** - 只读工具并行，写入工具顺序
✅ **动态上下文组装** - 基于优先级和 Token 预算组装
✅ **多层安全机制** - 权限 → 类别 → 路径 → 沙盒
✅ **丰富的 Prompt 工程** - 详细指导 + 反模式 + 奖励系统

---

## 架构概览

### Loom 1.0 vs 2.0 对比

```
┌─────────────────── Loom 1.0 ───────────────────┐
│                                                 │
│  Agent.run() → str  [非流式]                   │
│      ↓                                          │
│  AgentExecutor.execute() → str                 │
│      ├─ LLM.generate()                         │
│      ├─ ToolPipeline [无差别并行]              │
│      └─ ContextRetriever [注入 Bug]            │
│                                                 │
└─────────────────────────────────────────────────┘

┌─────────────────── Loom 2.0 ───────────────────┐
│                                                 │
│  Agent.execute() → AsyncGenerator[AgentEvent]  │
│      ↓                                          │
│  AgentExecutor.tt() [递归控制循环]             │
│      ├─ ContextAssembler [动态组装]            │
│      ├─ ToolOrchestrator [智能并行/顺序]       │
│      ├─ SecurityValidator [多层验证]           │
│      └─ ErrorRecoveryController [智能重试]     │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 职责 | 优先级 |
|------|------|--------|
| **AgentEvent** | 统一事件模型 | P0 ✅ 完成 |
| **ContextAssembler** | 动态上下文组装 | P0 |
| **ToolOrchestrator** | 智能工具编排 | P0 |
| **SecurityValidator** | 多层安全验证 | P1 |
| **PromptEngine** | Prompt 工程 | P1 |
| **ErrorRecoveryController** | 错误恢复 | P2 |
| **MemoryManager** | 内存优化 | P2 |

---

## 核心改进点

### 改进 1: 全链路流式架构 ⭐⭐⭐

**当前问题**:
```python
# Loom 1.0
result = await agent.run(prompt)  # 等待完成，无进度
print(result)
```

**2.0 解决方案**:
```python
# Loom 2.0
async for event in agent.execute(prompt):
    if event.type == AgentEventType.LLM_DELTA:
        print(event.content, end="")  # 实时流式输出
    elif event.type == AgentEventType.TOOL_PROGRESS:
        print(f"\n[{event.metadata['tool_name']}] {event.metadata['status']}")
```

**关键文件**:
- ✅ `loom/core/events.py` - 已完成
- `loom/components/agent.py` - 待修改
- `loom/core/agent_executor.py` - 待重构

---

### 改进 2: 智能工具编排 ⭐⭐⭐

**当前问题**:
```python
# Loom 1.0 - 无差别并行
await asyncio.gather(*[tool.execute() for tool in tools])
# 问题: EditTool 和 ReadTool 并发 → 竞态条件
```

**2.0 解决方案**:
```python
# Loom 2.0 - 智能分类
read_only = [GrepTool, ReadTool]  # 并行执行
write_tools = [EditTool]           # 顺序执行

# 先并行执行只读
await orchestrator.execute_parallel(read_only)
# 再顺序执行写入
await orchestrator.execute_sequential(write_tools)
```

**关键文件**:
- `loom/core/tool_orchestrator.py` - 待创建
- `loom/interfaces/tool.py` - 待修改（添加 `is_read_only`）

---

### 改进 3: 修复 RAG Context Bug ⭐⭐⭐

**当前问题**:
```python
# loom/core/agent_executor.py:443-450
def _inject_system_prompt(self, history, system_prompt):
    if history and history[0].role == "system":
        history[0] = Message(role="system", content=system_prompt)  # ❌ 覆盖！
```

**Bug 场景**:
1. 第一次对话，history 为空
2. RAG 检索到文档，添加 `Message(role="system", content=retrieved_docs)`
3. 调用 `_inject_system_prompt`，**RAG 上下文被覆盖**

**2.0 解决方案**:
```python
# ContextAssembler 动态组装
system_prompt = assembler.assemble({
    "base_instructions": "You are an agent...",
    "retrieved_context": doc_context,  # 独立块
    "git_context": git_info,
    "tool_specifications": tools_prompt
}, token_budget=16000, model="gpt-4")

# 结果：RAG 上下文作为独立 ## Retrieved Context 块
```

**关键文件**:
- `loom/core/context_assembly.py` - 待创建
- `loom/core/agent_executor.py` - 待修改（删除 `_inject_system_prompt`）

---

### 改进 4: 提示工程升级 ⭐⭐

**当前问题**:
```python
# 工具提示过于简单
description = "Execute shell commands"
```

**2.0 解决方案**:
```python
# 详细的工具指导（受 Claude Code 启发）
BashTool_Prompt = """
## RULE 0 (MOST IMPORTANT): Error Interpretation
If a command fails with "Permission denied", this may indicate
sandbox limitations, not command errors. Retry with sandbox=false.

## RULE 1: Forbidden Commands
NEVER use these via BashTool:
- grep (use GrepTool instead)
- find (use GlobTool instead)

**Violation penalty: -$1000**

## RULE 2: Sandbox Decision Tree
Use sandbox=True for: ✓ read operations
Use sandbox=False for: ✗ write operations, network
"""
```

**关键文件**:
- `loom/prompts/tool_instructions.py` - 待创建
- `loom/prompts/templates/` - 待创建（工具模板目录）

---

### 改进 5: 多层安全机制 ⭐⭐

**当前问题**:
```python
# 只有简单的权限检查
if permission_manager.check(tool):
    await tool.execute()
```

**2.0 解决方案**:
```python
# 4 层安全检查
security_decision = await validator.check_tool_execution(tool, input, context)
# Layer 1: Permission Rules
# Layer 2: Tool Category (destructive/network/general)
# Layer 3: Path Security (检查是否在允许目录内)
# Layer 4: Sandbox Support
```

**关键文件**:
- `loom/security/multi_layer_validator.py` - 待创建
- `loom/security/path_validator.py` - 待创建

---

## 迭代路线图

### 总览

```
阶段 1: 基础架构 (2-3 周) → 阶段 2: 核心功能 (3-4 周) → 阶段 3: 高级优化 (2-3 周)
    ↓                           ↓                           ↓
Task 1.1 ✅                 Task 2.1                    Task 3.1
Task 1.2                    Task 2.2                    Task 3.2
Task 1.3                    Task 2.3                    Task 3.3
                            Task 2.4
```

---

### 阶段 1: 基础架构改造 (2-3 周)

**目标**: 引入流式架构，修复核心 Bug

#### Task 1.1: 创建 AgentEvent 模型 ✅ 完成

**状态**: ✅ 完成于 2025-10-25
**时间**: 1 天

**交付物**:
- ✅ `loom/core/events.py` - AgentEvent 模型
- ✅ `loom/interfaces/event_producer.py` - EventProducer Protocol
- ✅ `tests/unit/test_agent_events.py` - 31 个测试（全部通过）
- ✅ `docs/agent_events_guide.md` - 使用文档
- ✅ `examples/agent_events_demo.py` - 演示代码

**验收标准**:
- ✅ AgentEvent 模型定义完整（24 种事件类型）
- ✅ 单元测试覆盖率 > 80% (实际 100%)
- ✅ 文档齐全

---

#### Task 1.2: 重构 Agent.execute() 为流式接口 ✅ 完成

**状态**: ✅ 完成于 2025-10-25
**实际时间**: 3 小时
**优先级**: P0

**目标**: 将 `Agent.execute()` 改为返回 `AsyncGenerator[AgentEvent, None]`

**步骤**:

1. **修改 `loom/components/agent.py`**:
   ```python
   # 新接口
   async def execute(self, input: str) -> AsyncGenerator[AgentEvent, None]:
       """统一流式接口"""
       async for event in self.executor.tt(
           messages=[Message(role="user", content=input)],
           turn_state=TurnState(turn_counter=0)
       ):
           yield event

   # 向后兼容
   async def run(self, input: str) -> str:
       """Legacy API - still works"""
       final_content = ""
       async for event in self.execute(input):
           if event.type == AgentEventType.AGENT_FINISH:
               return event.content or final_content
           elif event.type == AgentEventType.LLM_DELTA:
               final_content += event.content
       return final_content
   ```

2. **修改 `AgentExecutor.execute()` 为产生事件**:
   ```python
   async def execute(self, user_input: str) -> AsyncGenerator[AgentEvent, None]:
       # 当前: return final_response (str)
       # 改为: yield AgentEvent(...)

       # Phase 1: Context
       yield AgentEvent.phase_start("context_assembly")
       # ...

       # Phase 2: LLM
       yield AgentEvent(type=AgentEventType.LLM_START)
       async for chunk in self.llm.stream(...):
           yield AgentEvent.llm_delta(chunk)

       # Phase 3: Tools
       for tool_call in tool_calls:
           yield AgentEvent(type=AgentEventType.TOOL_EXECUTION_START, tool_call=tool_call)
           # ...
   ```

3. **更新测试**:
   - 修改 `tests/integration/test_agent.py`
   - 确保向后兼容性（`run()` 方法仍可用）

**验收标准**:
- [x] `Agent.execute()` 返回 `AsyncGenerator[AgentEvent, None]`
- [x] `Agent.run()` 仍然工作（向后兼容）
- [x] 所有现有测试通过
- [x] 新增流式测试（23 个测试）

**交付物**:
- ✅ `loom/components/agent.py` - 新增 execute() 方法
- ✅ `loom/core/agent_executor.py` - 新增 execute_stream() 方法
- ✅ `tests/unit/test_streaming_api.py` - 23 个测试
- ✅ `tests/integration/test_agent_streaming.py` - 集成测试
- ✅ `examples/streaming_example.py` - 示例代码
- ✅ `docs/TASK_1.2_COMPLETION_SUMMARY.md` - 完成总结

---

#### Task 1.3: 修复 RAG Context Bug ✅ 完成

**状态**: ✅ 完成于 2025-10-25
**实际时间**: 3 小时
**优先级**: P0

**目标**: 修复 RAG 上下文被覆盖的 Bug

**步骤**:

1. **创建 `ContextAssembler`**:
   ```python
   # loom/core/context_assembly.py
   class ContextAssembler:
       def assemble(self, components: Dict[str, str], budget: int) -> str:
           # 1. 收集所有组件并计算 Token
           # 2. 按优先级排序
           # 3. 智能截断
           # 4. 合并（RAG 上下文作为独立块）
   ```

2. **修改 `AgentExecutor`**:
   ```python
   # 删除 _inject_system_prompt 方法
   # 改用 ContextAssembler

   async def execute(self, user_input: str):
       # 收集所有组件
       components = {
           "base_instructions": self.system_prompt_builder.build(),
           "retrieved_context": doc_context if doc_context else None,
           "git_context": git_info,
           "tool_specifications": self._build_tool_specs()
       }

       # 动态组装
       system_prompt = await self.context_assembler.assemble(
           components,
           token_budget=self._get_token_budget(),
           model=self.llm.model_name
       )
   ```

3. **测试 RAG 不被覆盖**:
   ```python
   # tests/unit/test_rag_context_fix.py
   async def test_rag_context_not_overwritten():
       # 模拟第一次对话
       # 检索到文档
       # 验证系统提示中包含 RAG 上下文
   ```

**验收标准**:
- [x] RAG 上下文不被覆盖
- [x] 系统提示包含独立的 `## RETRIEVED CONTEXT` 块
- [x] Token 预算机制生效
- [x] 通过 RAG 集成测试（22 个测试）

**交付物**:
- ✅ `loom/core/context_assembly.py` - 新增 ContextAssembler 类（350 行）
- ✅ `loom/core/agent_executor.py` - 修改所有三个执行方法，删除 `_inject_system_prompt`
- ✅ `tests/unit/test_context_assembler.py` - 22 个测试
- ✅ `docs/TASK_1.3_COMPLETION_SUMMARY.md` - 完成总结

---

### 阶段 2: 核心功能增强 (3-4 周)

**目标**: 实现智能工具编排、多层安全、Prompt 工程

#### Task 2.1: 实现 ToolOrchestrator ✅ 完成

**状态**: ✅ 完成于 2025-10-25
**实际时间**: 4 小时
**优先级**: P0

**目标**: 智能区分只读/写入工具，并行/顺序执行

**步骤**:

1. **修改 `BaseTool` 接口**:
   ```python
   # loom/interfaces/tool.py
   class BaseTool(ABC):
       name: str
       description: str
       args_schema: Type[BaseModel]

       # 🆕 新增
       is_read_only: bool = False
       category: str = "general"  # "general", "destructive", "network"
   ```

2. **为内置工具添加属性**:
   ```python
   class ReadTool(BaseTool):
       is_read_only = True

   class GrepTool(BaseTool):
       is_read_only = True

   class EditTool(BaseTool):
       is_read_only = False
       category = "destructive"
   ```

3. **创建 `ToolOrchestrator`**:
   ```python
   # loom/core/tool_orchestrator.py
   class ToolOrchestrator:
       def categorize_tools(self, tool_calls: List[ToolCall]):
           read_only = [tc for tc in tool_calls if self.tools[tc.name].is_read_only]
           write_tools = [tc for tc in tool_calls if not self.tools[tc.name].is_read_only]
           return read_only, write_tools

       async def execute_batch(self, tool_calls: List[ToolCall]):
           read_only, write_tools = self.categorize_tools(tool_calls)

           # 并行执行只读
           if read_only:
               async for result in self.execute_parallel(read_only):
                   yield result

           # 顺序执行写入
           for tc in write_tools:
               async for result in self._execute_one(tc):
                   yield result
   ```

4. **集成到 `AgentExecutor`**:
   ```python
   # loom/core/agent_executor.py
   self.tool_orchestrator = ToolOrchestrator(
       tools=self.tools,
       security_validator=self.security_validator
   )

   # 使用
   async for result in self.tool_orchestrator.execute_batch(tool_calls):
       yield AgentEvent.tool_result(result)
   ```

**验收标准**:
- [ ] 只读工具并行执行
- [ ] 写入工具顺序执行
- [ ] 通过并发安全测试
- [ ] 性能测试（并行 vs 顺序）

**关键文件**:
- `loom/core/tool_orchestrator.py` - 新增
- `loom/interfaces/tool.py` - 修改
- `loom/builtin/tools/*.py` - 修改（添加 `is_read_only`）
- `tests/unit/test_tool_orchestrator.py` - 新增

---

#### Task 2.2: 实现 SecurityValidator ✅ 完成

**状态**: ✅ 完成于 2025-10-25
**实际时间**: 4 小时
**优先级**: P1

**目标**: 实现多层安全验证系统，提供 4 层独立安全检查

**步骤**:
1. ✅ 创建 Security Models (RiskLevel, SecurityDecision, PathSecurityResult)
2. ✅ 实现 PathSecurityValidator (路径遍历检测、系统路径保护)
3. ✅ 实现 SecurityValidator (4 层安全检查)
4. ✅ 集成到 ToolOrchestrator
5. ✅ 编写 26 个单元测试（全部通过）

**验收标准**:
- [x] 4 层安全检查独立运行
- [x] 路径遍历攻击被阻止
- [x] 系统路径访问被拒绝
- [x] 风险级别评估正确
- [x] 审计日志记录所有决策
- [x] 通过 26 个单元测试

**交付物**:
- ✅ `loom/security/models.py` - 安全模型
- ✅ `loom/security/path_validator.py` - 路径验证器
- ✅ `loom/security/validator.py` - 多层验证器
- ✅ `loom/security/__init__.py` - 模块导出
- ✅ `loom/core/tool_orchestrator.py` - 集成
- ✅ `tests/unit/test_security_validator.py` - 26 个测试
- ✅ `docs/TASK_2.2_COMPLETION_SUMMARY.md` - 完成总结

**关键文件**:
- `loom/security/validator.py` (~400 行) - 核心安全验证器
- `loom/security/path_validator.py` (~150 行) - 路径安全
- `tests/unit/test_security_validator.py` - 26 个测试

---

#### Task 2.3: 实现 ContextAssembler

**状态**: ⏳ 待开始（如果 Task 1.3 未完成）
**预计时间**: 2 天
**优先级**: P0

**说明**: 如果在 Task 1.3 已实现，则跳过。

---

#### Task 2.4: Prompt 工程升级

**状态**: ⏳ 待开始
**预计时间**: 3-4 天
**优先级**: P1

**步骤**:
1. 创建工具提示模板
2. 为每个工具添加详细指导
3. 添加反模式和奖励系统

**关键文件**:
- `loom/prompts/tool_instructions.py` - 新增
- `loom/prompts/templates/` - 新增目录

---

### 阶段 3: 高级优化 (2-3 周)

**目标**: 性能优化、错误恢复、可选高级特性

#### Task 3.1: 内存优化

**状态**: ⏳ 待开始
**预计时间**: 2 天
**优先级**: P2

**关键文件**:
- `loom/memory/weak_ref_cache.py` - 新增

---

#### Task 3.2: 错误恢复机制

**状态**: ⏳ 待开始
**预计时间**: 2-3 天
**优先级**: P2

**关键文件**:
- `loom/core/error_recovery.py` - 新增

---

#### Task 3.3: tt 递归模式（可选）

**状态**: ⏳ 待开始
**预计时间**: 3-5 天
**优先级**: P2（可选）

**说明**: 将 `AgentExecutor.execute()` 重构为尾递归模式（类似 Claude Code 的 `tt` 函数）

---

## 当前进度

### 已完成任务

| 任务 | 状态 | 完成日期 | 交付物 |
|------|------|----------|--------|
| Task 1.1: AgentEvent 模型 | ✅ 完成 | 2025-10-25 | 6 个文件，31 个测试 |
| Task 1.2: 流式 API 重构 | ✅ 完成 | 2025-10-25 | 5 个文件，23 个测试 |
| Task 1.3: 修复 RAG Bug | ✅ 完成 | 2025-10-25 | 4 个文件，22 个测试 |
| Task 2.1: ToolOrchestrator | ✅ 完成 | 2025-10-25 | 3 个文件，19 个测试 |
| Task 2.2: SecurityValidator | ✅ 完成 | 2025-10-25 | 6 个文件，26 个测试 |

### 进行中任务

| 任务 | 状态 | 预计完成 | 进度 |
|------|------|----------|------|
| - | - | - | - |

### 待开始任务

| 任务 | 优先级 | 预计时间 | 说明 |
|------|--------|----------|------|
| Task 2.4: Prompt 工程 | P1 | 3-4 天 | 详细工具指导 + 反模式 + 奖励系统 |
| Task 3.1: 内存优化 | P2 | 2 天 | WeakRef + Streaming |
| Task 3.2: 错误恢复 | P2 | 2-3 天 | 智能重试机制 |
| Task 3.3: tt 递归（可选） | P2 | 3-5 天 | 尾递归控制循环 |

**阶段 1 完成状态**: ✅ 3/3 任务完成（100%）
**阶段 2 进度**: ✅ 2/3 任务完成（67%）
**总测试数**: 121 个测试（Loom 2.0），100% 通过

---

## 下一步行动

### 立即行动项

**当前状态**: ✅ 阶段 1 完成 (100%)，✅ 阶段 2 进行中 (67%)

**推荐下一步**: 完成阶段 2 最后一个任务或进入阶段 3

1. **Task 2.4**: Prompt 工程升级（推荐优先）⭐
   - **优先级**: P1
   - **预计时间**: 3-4 天
   - **价值**: 提升 LLM 工具使用质量，减少工具使用错误
   - **依赖**: 无
   - **交付物**:
     - `loom/prompts/tool_instructions.py` - 详细工具指导
     - `loom/prompts/templates/` - 工具模板目录
     - 反模式警告系统
     - 奖励系统（Prompt-based）
   - **参考**: `cc分析/Prompt Engineering.md`

2. **Task 3.1**: 内存优化
   - **优先级**: P2
   - **预计时间**: 2 天
   - **价值**: 减少内存占用，支持长会话
   - **依赖**: 无

3. **Task 3.2**: 错误恢复机制
   - **优先级**: P2
   - **预计时间**: 2-3 天
   - **价值**: 智能分类和重试，提升鲁棒性
   - **依赖**: 无

### 每日检查清单

开发新任务时，请检查：

- [ ] 更新本文档的"当前进度"部分
- [ ] 标记已完成任务为 ✅
- [ ] 更新"进行中任务"表格
- [ ] 完成后创建 `TASK_X.X_COMPLETION_SUMMARY.md`
- [ ] 运行所有测试：`pytest tests/ -v`
- [ ] 更新 `CHANGELOG.md`（如果有）

---

## 参考文档

### 已完成的文档

1. ✅ **完整架构设计**
   - 位置：见之前的对话历史
   - 内容：类图、时序图、接口定义

2. ✅ **Task 1.1 完成总结**
   - 文件：`docs/TASK_1.1_COMPLETION_SUMMARY.md`
   - 内容：交付物、测试结果、验收标准

3. ✅ **AgentEvent 使用指南**
   - 文件：`docs/agent_events_guide.md`
   - 内容：24 种事件类型、16 种使用模式

### Claude Code 参考

位于 `cc分析/` 目录：

1. `Architecture:The Engine Romm.md` - 架构分析
2. `Control Flow.md` - 控制流程
3. `Novel Components.md` - 创新组件
4. `Prompt Engineering.md` - Prompt 工程
5. `Tools.md` - 工具设计
6. `An LLM's Perspective.md` - LLM 视角

### 关键设计原则

从 Claude Code 学到的 10 大设计理念：

1. **AsyncGenerator 全链路** - 所有组件流式
2. **单一递归控制循环** - tt 尾递归模式
3. **提示工程驱动** - 通过 Prompt 控制行为
4. **智能并行执行** - 只读并行，写入顺序
5. **动态上下文组装** - 基于优先级和 Token 预算
6. **多层安全机制** - 4 层安全检查
7. **内存优化** - WeakRef + Streaming
8. **Sub-Agent 分层** - 递归 Agent 调用（可选）
9. **流式 JSON 解析** - 实时解析不完整 JSON（可选）
10. **错误恢复** - 智能分类和重试

---

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 破坏向后兼容性 | 🟡 中 | 保留 `run()` 方法，渐进式迁移 |
| ToolOrchestrator 并发 Bug | 🟠 高 | 充分测试，先禁用并行 fallback |
| Token 预算超限 | 🟡 中 | ContextAssembler 智能截断 |
| 性能下降 | 🟢 低 | 流式架构应该更快 |
| 测试覆盖不足 | 🟡 中 | 每个任务要求 >80% 覆盖率 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2025-10-25 | 初始版本，完成 Task 1.1 |

---

## 联系与反馈

**开发者**: Claude Code + 用户
**项目仓库**: `/Users/shan/work/uploads/loom-agent`
**问题追踪**: 在开发过程中更新本文档的"当前进度"部分

---

**最后更新**: 2025-10-25
**下次审查**: Task 1.2 完成后
