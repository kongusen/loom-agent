# Phase 1: 公理一完整接入实施方案

## 目标
将 Agent 主循环从"手工拼接上下文"升级为"完全基于 PartitionManager 的分区系统"。

---

## 1.1 核心变更：重写 Agent._build_messages()

### 当前问题
```python
# loom/agent/core.py:185-237
async def _build_messages(self) -> list[Message]:
    # 手工拼接：只用了 system/memory/history
    messages = [SystemMessage(content=self.config.system_prompt)]
    # ... 手工构建 memory context
    messages.extend(history)
    return messages
```

**问题：**
1. 未使用 `partition_mgr.get_context()`
2. working/skill 分区被忽略
3. 分区更新和消息构建分离

### 新实现
```python
async def _build_messages(self) -> list[Message]:
    """基于 PartitionManager 构建完整上下文"""

    # 1. 更新所有分区
    await self._update_all_partitions()

    # 2. 检查是否需要压缩/心跳
    if self.partition_mgr.should_heartbeat():
        await self._trigger_heartbeat()
    elif self.partition_mgr.should_compress():
        await self._trigger_compression()

    # 3. 统一组装（替换手工拼接）
    full_context = self.partition_mgr.get_context()

    # 4. 转换为 Message 列表
    messages = self._context_to_messages(full_context)

    # 5. 拦截器（保留）
    if self.interceptors._interceptors:
        ictx = InterceptorContext(messages=messages)
        await self.interceptors.run(ictx)
        messages = ictx.messages

    return messages
```

---

## 1.2 新增：_update_all_partitions()

```python
async def _update_all_partitions(self) -> None:
    """更新所有 5 个分区"""

    # C_system: 基础 prompt + 场景增强
    system_content = self.config.system_prompt
    if self.scene_mgr.current_scene:
        system_content += "\n\n" + self.scene_mgr.current_scene.system_prompt_additions
    self.partition_mgr.update_partition("system", system_content)

    # C_working: 当前任务状态（新增）
    working_content = self._build_working_state()
    self.partition_mgr.update_partition("working", working_content)

    # C_memory: L2/L3 检索
    query = self._get_current_query()
    budget = self.partition_mgr.get_available_budget("memory")
    memory_entries = await self.memory.extract_for(query, budget // 2)

    # C_memory: 合并 knowledge
    knowledge_frags = []
    if self.knowledge_provider:
        knowledge_frags = await self.knowledge_provider.provide(query, budget // 2)

    combined = self._merge_context(memory_entries, knowledge_frags, budget)
    memory_text = "\n".join(item["content"] for item in combined)
    self.partition_mgr.update_partition("memory", memory_text)

    # C_skill: 激活的技能
    skill_budget = self.partition_mgr.get_available_budget("skill")
    skill_context = self.skill_mgr.get_context(skill_budget)
    self.partition_mgr.update_partition("skill", skill_context)

    # C_history: L1 历史
    history = self.memory.get_history()
    history_text = "\n".join(
        f"{m.role}: {m.content if isinstance(m.content, str) else str(m.content)}"
        for m in history
    )
    self.partition_mgr.update_partition("history", history_text)
```

---

## 1.3 新增：_build_working_state()

```python
def _build_working_state(self) -> str:
    """构建 working 分区内容（当前任务状态）"""
    parts = []

    # 当前目标
    if self._goal:
        parts.append(f"<current_goal>{self._goal}</current_goal>")

    # 最近工具调用（最多 3 个）
    recent_tools = self._execution_trace[-3:] if self._execution_trace else []
    if recent_tools:
        parts.append("<recent_actions>")
        parts.extend(recent_tools)
        parts.append("</recent_actions>")

    # 待处理的工具结果（如果有）
    if hasattr(self, '_pending_tool_results'):
        parts.append("<pending_results>")
        parts.extend(self._pending_tool_results)
        parts.append("</pending_results>")

    return "\n".join(parts)
```

---

## 1.4 新增：_context_to_messages()

```python
def _context_to_messages(self, full_context: str) -> list[Message]:
    """将完整上下文转换为 Message 列表"""

    # 策略：将 5 个分区合并为一个 system message + history
    # system/working/memory/skill → SystemMessage
    # history → 保持原有 Message 结构

    messages = []

    # 提取 system/working/memory/skill（前 4 个分区）
    context_parts = []
    for name in ["system", "working", "memory", "skill"]:
        content = self.partition_mgr.partitions[name].content
        if content:
            context_parts.append(f"[{name.upper()}]\n{content}")

    if context_parts:
        messages.append(SystemMessage(content="\n\n".join(context_parts)))

    # history 保持原有结构
    history = self.memory.get_history()
    messages.extend(history)

    return messages
```

---

## 1.5 修改：run() 方法集成

```python
async def run(self, user_input: str, goal: str = "") -> AsyncGenerator[AgentEvent, None]:
    """主执行循环"""
    self._goal = goal or user_input  # 设置目标

    # 添加用户消息
    user_msg = UserMessage(content=user_input)
    self.memory.add_message(user_msg)
    self._history_dirty = True

    # 更新 working 分区（立即反映新任务）
    working_content = self._build_working_state()
    self.partition_mgr.update_partition("working", working_content)

    # 构建消息（内部会检查 compress/heartbeat）
    messages = await self._build_messages()

    # ... 后续 LLM 调用逻辑不变
```

---

## 1.6 修改：工具执行后更新 working

```python
async def _execute_tool(self, tc: ToolCall) -> str:
    """执行工具并更新 working 分区"""

    # 执行工具
    result = await self.tools.execute(tc, ctx)

    # 记录到 execution_trace
    self._execution_trace.append(f"{tc.name}({tc.arguments}) → {result[:100]}")

    # 立即更新 working 分区
    working_content = self._build_working_state()
    self.partition_mgr.update_partition("working", working_content)

    return result
```

---

## 1.7 删除旧代码

### 删除文件
```bash
rm loom/context/orchestrator.py
rm loom/context/source.py
rm -rf loom/context/sources/
```

### 删除类型定义
```python
# loom/types/context.py
# 删除：
# - ContextSource
# - ContextFragment
# - ContextBlock（如果未被其他地方使用）
```

### 修改 Agent.__init__()
```python
# 删除参数
def __init__(
    self,
    provider: LLMProvider,
    config: AgentConfig | None = None,
    name: str | None = None,
    memory: MemoryManager | None = None,
    tools: ToolRegistry | None = None,
    # context: ContextOrchestrator | None = None,  # 删除
    event_bus: EventBus | None = None,
    interceptors: InterceptorChain | None = None,
    strategy: LoopStrategy | None = None,
) -> None:
    # ...
    # self.context = context or ContextOrchestrator()  # 删除
```

---

## 1.8 测试验证

### 单元测试
```python
# tests/unit/test_partition_integration.py

async def test_build_messages_uses_all_partitions():
    """验证 _build_messages 使用所有 5 个分区"""
    agent = Agent(provider=MockProvider())
    agent._goal = "test goal"

    messages = await agent._build_messages()

    # 验证 system message 包含所有分区内容
    system_msg = messages[0]
    assert "[SYSTEM]" in system_msg.content
    assert "[WORKING]" in system_msg.content
    assert "[MEMORY]" in system_msg.content
    assert "[SKILL]" in system_msg.content

async def test_working_partition_updates_on_tool_execution():
    """验证工具执行后 working 分区更新"""
    agent = Agent(provider=MockProvider())

    # 执行工具
    await agent._execute_tool(ToolCall(name="test", arguments="{}"))

    # 验证 working 分区包含工具记录
    working = agent.partition_mgr.partitions["working"].content
    assert "test" in working

async def test_heartbeat_triggers_at_threshold():
    """验证 ρ ≥ 0.85 时触发 heartbeat"""
    agent = Agent(provider=MockProvider())

    # 模拟 history 增长到阈值
    agent.partition_mgr.partitions["history"].tokens = int(128000 * 0.86)

    # 构建消息应触发 heartbeat
    await agent._build_messages()

    # 验证 heartbeat 被调用（通过 mock 或日志）
```

---

## 1.9 迁移指南

### 用户需要做的变更

**之前（v0.6.x）：**
```python
from loom.context import ContextOrchestrator, MemoryContextSource

context = ContextOrchestrator()
context.add_source(MemoryContextSource(memory))

agent = Agent(provider=provider, context=context)
```

**之后（v0.7.0）：**
```python
# PartitionManager 自动管理，无需手动配置
agent = Agent(provider=provider)

# 如需自定义分区预算
agent.partition_mgr.window = 200000  # 调整窗口大小
```

---

## 1.10 实施检查清单

- [ ] 实现 `_update_all_partitions()`
- [ ] 实现 `_build_working_state()`
- [ ] 实现 `_context_to_messages()`
- [ ] 重写 `_build_messages()` 使用 partition_mgr
- [ ] 修改 `run()` 设置 goal 并更新 working
- [ ] 修改 `_execute_tool()` 更新 working
- [ ] 删除 ContextOrchestrator 相关代码
- [ ] 删除 Agent 的 context 参数
- [ ] 编写单元测试
- [ ] 更新文档和迁移指南
- [ ] 验证所有现有测试通过

---

**下一步：Phase 2 公理二约束前置方案**
