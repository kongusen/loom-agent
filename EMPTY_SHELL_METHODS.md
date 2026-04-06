# Loom Framework 空壳方法分析

**分析日期**: 2026-04-03
**目标**: 识别那些"看起来实现了但实际上是空壳"的方法

这些方法的特征：
- ✅ 代码运行不报错
- ❌ 但没有真正实现预期的功能
- ❌ 只是返回默认值、空集合或做最小化处理

---

## 类别 1: 决策引擎 - 只检查约束，没有真正决策

### 1. DecisionEngine.decide() - 伪决策引擎

**文件**: `loom/execution/decision.py:9-21`

**代码**:
```python
def decide(self, context_rho: float, depth: int, max_depth: int) -> LoopResult:
    """Decide next action based on context state"""

    # Physical constraint: ρ >= 1.0
    if context_rho >= 1.0:
        return LoopResult(state=LoopState.RENEW, should_continue=True)

    # Depth constraint
    if depth >= max_depth:
        return LoopResult(state=LoopState.DECOMPOSE, should_continue=False)

    # Continue normal loop
    return LoopResult(state=LoopState.REASON, should_continue=True)
```

**问题**:
- 名为"决策引擎"，但只检查物理约束
- 没有基于 Dashboard 状态的智能决策
- 没有基于 goal_progress 的判断
- 没有基于 error_count 的策略调整
- 没有基于 pending_events 的中断处理
- 永远返回 REASON，没有真正的"决策"

**应该做什么**:
```python
def decide(self, context_rho: float, depth: int, max_depth: int, dashboard: Dashboard) -> LoopResult:
    # 物理约束
    if context_rho >= 1.0:
        return LoopResult(state=LoopState.RENEW, should_continue=True)

    # 检查 Dashboard 状态
    if dashboard.interrupt_requested:
        return LoopResult(state=LoopState.HANDLE_EVENT, should_continue=True)

    if dashboard.error_count > 3:
        return LoopResult(state=LoopState.DECOMPOSE, should_continue=False)

    if dashboard.goal_progress == "completed":
        return LoopResult(state=LoopState.GOAL_REACHED, should_continue=False)

    # 基于 rho 的压缩决策
    if context_rho > 0.9:
        return LoopResult(state=LoopState.COMPRESS, should_continue=True)

    # 正常继续
    return LoopResult(state=LoopState.REASON, should_continue=True)
```

---

### 2. Agent.run() - 空循环

**文件**: `loom/agent/core.py:24-46`

**代码**:
```python
async def run(self, goal: str, max_steps: int = 100) -> str:
    """Run agent with goal"""
    self.loop.max_steps = max_steps

    while True:
        # Check constraints
        ok, reason = self.runtime.check_constraints(self.context.rho, self.depth)
        if not ok:
            return f"Stopped: {reason}"

        # Execute loop step
        result = self.loop.step(
            self.context.rho,
            self.depth,
            self.runtime.config.max_depth
        )

        if not result.should_continue:
            return "Goal reached"

        # Handle renewal
        if self.context.should_renew():
            self.context.renew()
```

**问题**:
- 循环体内没有实际执行任何操作
- 没有调用 LLM
- 没有执行工具
- 没有更新 context
- 只是检查约束然后返回
- **这是一个完全的空壳循环**

**应该做什么**:
```python
async def run(self, goal: str, max_steps: int = 100) -> str:
    self.context.current_goal = goal
    self.loop.max_steps = max_steps

    while True:
        # Check constraints
        ok, reason = self.runtime.check_constraints(self.context.rho, self.depth)
        if not ok:
            return f"Stopped: {reason}"

        # Execute loop step
        result = self.loop.step(...)

        if result.state == LoopState.REASON:
            # 调用 LLM 进行推理
            response = await self.provider.complete(
                self.context.partitions.get_all_messages(),
                params=...
            )
            # 解析响应，提取工具调用
            tool_calls = self._parse_tool_calls(response)

        elif result.state == LoopState.ACT:
            # 执行工具
            for tool_call in tool_calls:
                tool_result = await self.tool_executor.execute(tool_call)
                self.context.partitions.history.append(tool_result)

        elif result.state == LoopState.OBSERVE:
            # 更新 Dashboard
            self.context.dashboard.update_progress(...)

        # ... 其他状态处理
```

---

## 类别 2: 观察者 - 只是包装，没有真正观察

### 3. Observer.observe_tool_result() - 简单包装

**文件**: `loom/execution/observer.py:9-15`

**代码**:
```python
def observe_tool_result(self, tool_name: str, result: str) -> Message:
    """Observe tool execution result"""
    return Message(
        role="tool",
        content=result,
        name=tool_name
    )
```

**问题**:
- 名为"观察者"，但只是创建 Message 对象
- 没有分析结果
- 没有提取关键信息
- 没有更新 Dashboard
- 没有检测错误模式
- 没有触发事件

**应该做什么**:
```python
def observe_tool_result(
    self,
    tool_name: str,
    result: str,
    dashboard: DashboardManager
) -> Message:
    """Observe and analyze tool execution result"""

    # 检测错误
    is_error = "error" in result.lower() or "failed" in result.lower()
    if is_error:
        dashboard.increment_errors()

    # 提取关键信息
    if tool_name == "web_search":
        # 提取搜索结果数量
        count = self._extract_result_count(result)
        dashboard.add_scratchpad_entry(f"Found {count} results")

    # 更新进度
    dashboard.update_progress(f"Completed {tool_name}")

    return Message(
        role="tool",
        content=result,
        name=tool_name,
        metadata={"is_error": is_error}
    )
```

---

## 类别 3: 状态机 - 只是状态转换，没有副作用

### 4. StateMachine.transition() - 纯状态转换

**文件**: `loom/execution/state_machine.py:12-29`

**代码**:
```python
def transition(self, result: LoopResult) -> LoopState:
    """Transition to next state"""
    if result.state == LoopState.GOAL_REACHED:
        return LoopState.GOAL_REACHED

    if result.state == LoopState.RENEW:
        return LoopState.RENEW

    # Normal flow: REASON → ACT → OBSERVE → DELTA → REASON
    transitions = {
        LoopState.REASON: LoopState.ACT,
        LoopState.ACT: LoopState.OBSERVE,
        LoopState.OBSERVE: LoopState.DELTA,
        LoopState.DELTA: LoopState.REASON,
    }

    self.current_state = transitions.get(result.state, LoopState.REASON)
    return self.current_state
```

**问题**:
- 这个实现本身是合理的（状态机应该是纯函数）
- 但问题是：**没有任何地方使用这个状态来驱动实际行为**
- Loop.step() 返回状态，但 Agent.run() 不根据状态执行不同操作

**应该做什么**:
- 状态机本身可以保持纯函数
- 但调用方（Agent.run）必须根据状态执行相应操作

---

## 类别 4: 注册表 - 只存储，没有激活

### 5. CapabilityRegistry.activate() - 假激活

**文件**: `loom/capabilities/registry.py:45-51`

**代码**:
```python
def activate(self, name: str):
    """Activate a capability"""
    self.active_capabilities.add(name)

def deactivate(self, name: str):
    """Deactivate a capability"""
    self.active_capabilities.discard(name)
```

**问题**:
- 只是添加到 set 中
- 没有实际加载 tools
- 没有注入到 context
- 没有更新 runtime 的可用工具列表
- **激活/停用没有任何实际效果**

**应该做什么**:
```python
def activate(self, name: str, tool_registry: ToolRegistry, context: ContextPartitions):
    """Activate a capability and inject its tools"""
    capability = self.capabilities.get(name)
    if not capability:
        return

    # 标记为激活
    self.active_capabilities.add(name)

    # 注册工具到 tool_registry
    for tool_name in capability.tools:
        tool = self._load_tool(tool_name)
        if tool:
            tool_registry.register(tool)

    # 注入 skill 到 context
    context.skill.append(capability.description)
```

---

### 6. CapabilityLoader.load() - 假加载

**文件**: `loom/capabilities/loader.py:15-25`

**代码**:
```python
def load(self, capability_name: str):
    """Load a capability"""
    capability = self.capability_registry.get(capability_name)
    if not capability:
        return

    # Load associated tools
    for tool_name in capability.tools:
        tool = self.tool_registry.get(tool_name)
        if tool:
            self.loaded.add(capability_name)
```

**问题**:
- 只是检查 tool 是否存在
- 没有实际加载任何东西
- 只要有一个 tool 存在就标记为 loaded
- **完全没有"加载"的行为**

**应该做什么**:
```python
def load(self, capability_name: str):
    """Load a capability and its dependencies"""
    capability = self.capability_registry.get(capability_name)
    if not capability:
        return

    # 加载依赖
    for dep in capability.dependencies:
        if dep not in self.loaded:
            self.load(dep)

    # 加载工具
    for tool_name in capability.tools:
        tool = self._load_tool_from_source(tool_name)
        if tool:
            self.tool_registry.register(tool)

    # 标记为已加载
    self.loaded.add(capability_name)
```

---

## 类别 5: 匹配器 - 简单字符串匹配

### 7. CapabilityRegistry.match_task() - 简单关键词匹配

**文件**: `loom/capabilities/registry.py:36-43`

**代码**:
```python
def match_task(self, task_description: str) -> list[Capability]:
    """Match capabilities to task by keywords"""
    matched = []
    task_lower = task_description.lower()
    for cap in self.capabilities.values():
        if any(kw in task_lower for kw in cap.keywords):
            matched.append(cap)
    return matched
```

**问题**:
- 只是简单的子字符串匹配
- 没有语义理解
- 没有相似度评分
- 没有排序
- 容易误匹配（例如 "web" 会匹配 "website", "webhook", "cobweb"）

**应该做什么**:
```python
def match_task(self, task_description: str, top_k: int = 3) -> list[tuple[Capability, float]]:
    """Match capabilities to task with semantic similarity"""
    scored = []

    for cap in self.capabilities.values():
        # 语义相似度
        semantic_score = self._semantic_similarity(task_description, cap.description)

        # 关键词匹配加分
        keyword_score = sum(
            1.0 for kw in cap.keywords
            if kw.lower() in task_description.lower()
        ) / max(len(cap.keywords), 1)

        # 综合评分
        final_score = semantic_score * 0.7 + keyword_score * 0.3

        if final_score > 0.3:  # 阈值
            scored.append((cap, final_score))

    # 按分数排序
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
```

---

## 类别 6: 事件总线 - 有重复方法

### 8. EventBus.publish() - 重复定义

**文件**: `loom/orchestration/events.py:21-48`

**代码**:
```python
def publish(self, event: Event):
    """Publish event if ΔH > δ_min"""
    if event.delta_h < self.delta_min:
        return

    for callback in self._subscribers.get(event.topic, []):
        callback(event)

def publish(self, event: Event):  # 重复定义！
    """T2.1: publish(e) 当且仅当 ΔH(e) > δ_min"""
    if event.delta_h < self.delta_min:
        return  # 信息熵增量太小，不发布

    self.published_events.append(event)

    for callback in self._subscribers.get(event.topic, []):
        callback(event)
```

**问题**:
- 同一个类中有两个 publish 方法
- 第二个会覆盖第一个
- 第一个版本没有记录到 published_events
- 代码混乱

**应该做什么**:
- 删除第一个版本
- 保留第二个完整版本

---

## 类别 7: 上下文管理 - 缺少关键集成

### 9. ContextPartitions.get_all_messages() - 不完整

**文件**: `loom/context/partitions.py:26-28`

**代码**:
```python
def get_all_messages(self) -> list[Message]:
    """Get all messages for LLM (按优先级排序)"""
    return self.system + self.memory + self.history
```

**问题**:
- 没有包含 working (Dashboard)
- 没有包含 skill
- 注释说"按优先级排序"，但实际上只是简单拼接
- Dashboard 是"LLM 一等公民"，但没有被包含

**应该做什么**:
```python
def get_all_messages(self) -> list[Message]:
    """Get all messages for LLM (按优先级排序)"""
    messages = []

    # C_system: 永不压缩
    messages.extend(self.system)

    # C_working: Dashboard 状态
    dashboard_msg = Message(
        role="system",
        content=self._format_dashboard(self.working)
    )
    messages.append(dashboard_msg)

    # C_memory: 长期记忆
    messages.extend(self.memory)

    # C_skill: 当前激活的技能
    if self.skill:
        skill_msg = Message(
            role="system",
            content=f"Available skills:\n" + "\n".join(self.skill)
        )
        messages.append(skill_msg)

    # C_history: 执行历史
    messages.extend(self.history)

    return messages
```

---

## 类别 8: 运行时循环 - 重复的 step 方法

### 10. Loop.step() - 重复定义

**文件**: `loom/execution/loop.py:24-59`

**代码**:
```python
def step(self, context_rho: float, depth: int, max_depth: int) -> LoopResult:
    """Execute one loop step"""
    self.step_count += 1

    if self.step_count >= self.max_steps:
        return LoopResult(state=LoopState.GOAL_REACHED, should_continue=False)

    # Δ decision
    result = self.decision_engine.decide(context_rho, depth, max_depth)

    # Transition state
    next_state = self.state_machine.transition(result)
    result.state = next_state

    return result

def step(self, context_rho: float, depth: int, max_depth: int) -> LoopResult:  # 重复！
    """Execute one loop step: Reason → Act → Observe → Δ"""
    self.step_count += 1

    # 物理约束检查：ρ >= 1.0
    if context_rho >= 1.0:
        return LoopResult(state=LoopState.RENEW, should_continue=True)

    # Max steps check
    if self.step_count >= self.max_steps:
        return LoopResult(state=LoopState.GOAL_REACHED, should_continue=False)

    # Δ decision
    result = self.decision_engine.decide(context_rho, depth, max_depth)

    # State transition
    next_state = self.state_machine.transition(result)
    result.state = next_state

    return result
```

**问题**:
- 同一个类中有两个 step 方法
- 第二个会覆盖第一个
- 两个版本略有不同（第二个多了 ρ >= 1.0 检查）

**应该做什么**:
- 删除第一个版本
- 保留第二个版本

---

## 类别 9: 工具执行 - 看起来完整但缺少关键部分

### 11. ToolExecutor.execute() - 缺少 Hook 集成

**文件**: `loom/tools/executor.py:18-64`

**当前实现**:
```python
async def execute(self, tool_call: ToolCall) -> ToolResult:
    """Execute a tool call with governance"""
    tool = self.registry.get(tool_call.name)

    if not tool:
        return ToolResult(...)

    # Permission check
    ok, reason = self.governance.check_permission(...)
    if not ok:
        return ToolResult(...)

    # Rate limit check
    ok, reason = self.governance.check_rate_limit(tool_call.name)
    if not ok:
        return ToolResult(...)

    # Execute
    try:
        result = await tool.execute(**tool_call.arguments)
        self.governance.record_call(tool_call.name)
        return ToolResult(...)
    except Exception as e:
        return ToolResult(...)
```

**问题**:
- 有 governance 检查
- 但没有 Hook 检查
- 没有 Veto 检查
- 没有审计日志
- 没有事件发布
- **三层防护只实现了一层**

**应该做什么**:
```python
async def execute(
    self,
    tool_call: ToolCall,
    hook_manager: HookManager,
    veto_authority: VetoAuthority,
    event_bus: EventBus
) -> ToolResult:
    """Execute a tool call with full three-layer defense"""

    # Layer 1: Permission check
    ok, reason = self.governance.check_permission(...)
    if not ok:
        return ToolResult(is_error=True, content=reason)

    # Layer 2: Hook check
    hook_decision, hook_reason = hook_manager.trigger("tool.execute", {
        "tool_name": tool_call.name,
        "arguments": tool_call.arguments
    })
    if hook_decision == HookDecision.DENY:
        return ToolResult(is_error=True, content=f"Hook denied: {hook_reason}")
    elif hook_decision == HookDecision.ASK:
        # 需要用户确认
        pass

    # Layer 3: Veto check (if high risk)
    if tool.definition.is_destructive:
        if veto_authority.should_veto(tool_call):
            veto_authority.veto(f"Vetoed {tool_call.name}")
            return ToolResult(is_error=True, content="Vetoed by authority")

    # Execute
    try:
        result = await tool.execute(**tool_call.arguments)

        # 发布事件
        event_bus.publish(Event(
            topic="tool.executed",
            payload={"tool": tool_call.name, "success": True}
        ))

        return ToolResult(...)
    except Exception as e:
        event_bus.publish(Event(
            topic="tool.failed",
            payload={"tool": tool_call.name, "error": str(e)}
        ))
        return ToolResult(...)
```

---

## 总结

### 空壳方法统计

| 类别 | 数量 | 严重程度 |
|------|------|----------|
| 决策引擎 | 2 | 🔴 高 |
| 观察者 | 1 | 🟡 中 |
| 状态机 | 1 | 🟢 低 |
| 注册表 | 2 | 🔴 高 |
| 匹配器 | 1 | 🟡 中 |
| 事件总线 | 1 | 🟡 中 |
| 上下文管理 | 1 | 🔴 高 |
| 运行时循环 | 1 | 🟡 中 |
| 工具执行 | 1 | 🔴 高 |

**总计**: 11 个空壳方法

### 最严重的问题

1. **Agent.run() 是完全的空循环** - 这是整个框架的入口点，但什么都不做
2. **DecisionEngine 不做决策** - 只检查约束，没有智能决策
3. **CapabilityRegistry.activate() 假激活** - 激活没有任何实际效果
4. **ContextPartitions.get_all_messages() 不完整** - 缺少关键的 Dashboard 和 Skill
5. **ToolExecutor 缺少 Hook 和 Veto** - 三层防护只实现了一层

### 修复优先级

#### P0 - 立即修复（阻止运行）
1. Agent.run() - 实现真正的执行循环
2. ContextPartitions.get_all_messages() - 包含所有分区
3. DecisionEngine.decide() - 实现基于 Dashboard 的决策

#### P1 - 高优先级（影响功能）
4. CapabilityRegistry.activate() - 实现真正的激活
5. ToolExecutor.execute() - 集成 Hook 和 Veto
6. Observer.observe_tool_result() - 实现真正的观察和分析

#### P2 - 中优先级（改进质量）
7. CapabilityRegistry.match_task() - 使用语义匹配
8. CapabilityLoader.load() - 实现真正的加载
9. 删除重复的方法定义（EventBus.publish, Loop.step）

---

**关键洞察**:

这些空壳方法的存在表明：
1. **架构设计是好的** - 有正确的抽象和分层
2. **但实现不完整** - 很多地方只是"占位符"
3. **最大的问题是主循环** - Agent.run() 是空的，导致整个系统无法运行
4. **第二大问题是决策** - DecisionEngine 不做决策，只检查约束
5. **第三大问题是集成** - 各个组件独立工作，但没有真正连接起来

**修复策略**:
- 先修复主循环，让系统能跑起来
- 再实现决策引擎，让系统能做智能决策
- 最后完善各个组件的集成

