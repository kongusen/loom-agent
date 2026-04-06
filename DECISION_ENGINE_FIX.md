# DecisionEngine.decide() 修复总结

**修复日期**: 2026-04-03
**优先级**: P0 - 最高优先级（让系统能做智能决策）

---

## 问题描述

`DecisionEngine.decide()` 名为"决策引擎"，但原实现**只是检查物理约束**：

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
- ❌ 永远返回 REASON，没有真正的"决策"
- ❌ 不考虑 Dashboard 状态（interrupt_requested, error_count, goal_progress）
- ❌ 不响应 pending events 或 active risks
- ❌ 不检查目标完成状态
- ❌ 不基于错误数量调整策略
- ❌ 系统无法"智能"地响应运行时状态

**影响**:
- 即使 Dashboard 显示 interrupt_requested，系统也不会响应
- 即使错误数量很高，系统也不会调整策略
- 即使目标已完成，系统也不会停止
- 即使有高优先级事件，系统也不会注意
- 决策引擎名不副实

---

## 修复内容

### 1. 扩展 decide() 方法签名

添加 `dashboard` 参数以接收运行时状态：

```python
def decide(
    self,
    context_rho: float,
    depth: int,
    max_depth: int,
    dashboard: Dashboard | None = None  # 新增
) -> LoopResult:
```

### 2. 实现智能决策逻辑

按优先级实现 8 层决策逻辑：

```python
# 1. Physical constraint: ρ >= 1.0 → must renew
if context_rho >= 1.0:
    return LoopResult(
        state=LoopState.RENEW,
        should_continue=True,
        reason="Context pressure exceeded threshold"
    )

# 2. Depth constraint → must decompose
if depth >= max_depth:
    return LoopResult(
        state=LoopState.DECOMPOSE,
        should_continue=False,
        reason="Maximum depth reached"
    )

# 3. Interrupt requested (from heartbeat or high-urgency events)
if dashboard.interrupt_requested:
    if dashboard.event_surface.active_risks:
        return LoopResult(
            state=LoopState.REASON,
            should_continue=True,
            reason=f"Interrupt: {len(dashboard.event_surface.active_risks)} active risks need attention"
        )

# 4. Goal completion check
if dashboard.goal_progress in {"completed", "success", "done"}:
    return LoopResult(
        state=LoopState.GOAL_REACHED,
        should_continue=False,
        reason=f"Goal marked as {dashboard.goal_progress}"
    )

# 5. Error threshold - too many errors suggest we're struggling
if dashboard.error_count >= 5:
    return LoopResult(
        state=LoopState.DECOMPOSE,
        should_continue=False,
        reason=f"Error count too high ({dashboard.error_count}) - consider decomposition"
    )
elif dashboard.error_count >= 3:
    return LoopResult(
        state=LoopState.REASON,
        should_continue=True,
        reason=f"Error count elevated ({dashboard.error_count}) - LLM should adjust strategy"
    )

# 6. Pending events - if there are many pending events
if len(dashboard.event_surface.pending_events) >= 3:
    return LoopResult(
        state=LoopState.REASON,
        should_continue=True,
        reason=f"{len(dashboard.event_surface.pending_events)} pending events - LLM should address"
    )

# 7. Context pressure warning - approaching renewal threshold
if context_rho >= 0.8:
    return LoopResult(
        state=LoopState.REASON,
        should_continue=True,
        reason=f"Context pressure high (ρ={context_rho:.2f}) - approaching renewal"
    )

# 8. Normal operation - continue loop
return LoopResult(
    state=LoopState.REASON,
    should_continue=True,
    reason="Normal operation"
)
```

### 3. 添加 reason 字段到 LoopResult

扩展 LoopResult 以包含决策原因：

```python
@dataclass
class LoopResult:
    """L* loop execution result"""
    state: LoopState
    output: Any = None
    should_continue: bool = True
    error: str | None = None
    reason: str | None = None  # 新增：决策原因
```

### 4. 集成到 Agent.run()

在 Agent 类中：

1. 添加 DecisionEngine 实例：
```python
def __init__(self, ...):
    # ...
    self.decision_engine = DecisionEngine()
```

2. 在 DELTA 阶段调用决策引擎：
```python
elif result.state == LoopState.DELTA:
    # Delta phase: use DecisionEngine for intelligent decision
    decision = self.decision_engine.decide(
        context_rho=self.context.rho,
        depth=self.depth,
        max_depth=self.runtime.config.max_depth,
        dashboard=self.context.dashboard.dashboard
    )

    # Log decision reason to scratchpad if significant
    if decision.reason and decision.reason != "Normal operation":
        current_scratchpad = self.context.dashboard.dashboard.scratchpad
        if current_scratchpad:
            self.context.dashboard.set_scratchpad(
                f"{current_scratchpad}\n[Δ] {decision.reason}"
            )
        else:
            self.context.dashboard.set_scratchpad(f"[Δ] {decision.reason}")

    # Handle decision
    if decision.state == LoopState.GOAL_REACHED:
        return self._extract_final_answer()
    elif decision.state == LoopState.RENEW:
        self.context.renew()
        self.loop.advance_state()
    elif decision.state == LoopState.DECOMPOSE:
        return f"Task requires decomposition: {decision.reason}"
    else:
        self.loop.advance_state()
```

---

## 决策优先级

DecisionEngine 按以下优先级做决策：

| 优先级 | 条件 | 决策 | 原因 |
|--------|------|------|------|
| 1 | ρ >= 1.0 | RENEW | 物理约束：必须压缩 |
| 2 | depth >= max_depth | DECOMPOSE | 物理约束：必须分解 |
| 3 | interrupt_requested + active_risks | REASON | 高优先级事件需要立即处理 |
| 4 | goal_progress = "completed" | GOAL_REACHED | 目标已完成 |
| 5 | error_count >= 5 | DECOMPOSE | 错误太多，建议分解任务 |
| 6 | error_count >= 3 | REASON | 错误较多，LLM 应调整策略 |
| 7 | pending_events >= 3 | REASON | 多个待处理事件 |
| 8 | ρ >= 0.8 | REASON | 接近压缩阈值，提醒 LLM |
| 9 | 其他 | REASON | 正常操作 |

---

## 测试结果

创建了测试文件 `test_decision_engine_fix.py`，验证 10 种决策场景：

```
======================================================================
DecisionEngine.decide() Test
======================================================================

1. Test: High context pressure (ρ >= 1.0)
   Decision: renew
   Reason: Context pressure exceeded threshold
   ✅ Correct: RENEW triggered

2. Test: Maximum depth reached
   Decision: decompose
   Reason: Maximum depth reached
   ✅ Correct: DECOMPOSE triggered

3. Test: Interrupt requested with active risks
   Decision: reason
   Reason: Interrupt: 1 active risks need attention
   ✅ Correct: REASON with risk awareness

4. Test: Goal marked as completed
   Decision: goal_reached
   Reason: Goal marked as completed
   ✅ Correct: GOAL_REACHED

5. Test: Critical error count (>= 5)
   Decision: decompose
   Reason: Error count too high (6) - consider decomposition
   ✅ Correct: DECOMPOSE due to errors

6. Test: Elevated error count (3-4)
   Decision: reason
   Reason: Error count elevated (3) - LLM should adjust strategy
   ✅ Correct: REASON with error awareness

7. Test: Multiple pending events
   Decision: reason
   Reason: 3 pending events - LLM should address
   ✅ Correct: REASON to address events

8. Test: High context pressure (0.8 <= ρ < 1.0)
   Decision: reason
   Reason: Context pressure high (ρ=0.85) - approaching renewal
   ✅ Correct: REASON with pressure awareness

9. Test: Normal operation (no issues)
   Decision: reason
   Reason: Normal operation
   ✅ Correct: REASON (normal operation)

10. Test: No dashboard provided (fallback)
   Decision: reason
   Reason: No dashboard - continue normal loop
   ✅ Correct: REASON (fallback mode)

======================================================================
✅ All 10 decision scenarios tested successfully!
```

---

## 影响范围

### 修改的文件

1. **loom/execution/decision.py** - 完全重写 decide() 方法
2. **loom/types/results.py** - 添加 reason 字段到 LoopResult
3. **loom/agent/core.py** - 集成 DecisionEngine 到 Agent.run()

### 新增的导入

```python
# In loom/execution/decision.py
from ..types import LoopState, LoopResult, Dashboard

# In loom/agent/core.py
from ..execution.decision import DecisionEngine
```

### 行为变化

**修复前**:
- DecisionEngine 只检查物理约束
- 永远返回 REASON（除非 ρ >= 1.0 或 depth >= max_depth）
- 不考虑 Dashboard 状态
- 系统无法智能响应运行时变化

**修复后**:
- DecisionEngine 基于 Dashboard 做智能决策
- 响应中断请求和高优先级事件
- 检测目标完成状态
- 基于错误数量调整策略
- 注意待处理事件
- 提前警告高 context pressure
- 决策原因记录到 scratchpad

---

## 关键改进

### 1. 真正的智能决策

DecisionEngine 现在是一个真正的"决策引擎"：
- ✅ 基于 Dashboard 状态做决策
- ✅ 考虑多个因素（错误、事件、进度、压力）
- ✅ 按优先级排序决策逻辑
- ✅ 提供决策原因（可追溯）

### 2. 响应运行时状态

系统现在可以智能响应：
- ✅ 中断请求（interrupt_requested）
- ✅ 高优先级事件（active_risks）
- ✅ 目标完成（goal_progress）
- ✅ 错误累积（error_count）
- ✅ 待处理事件（pending_events）
- ✅ Context 压力（rho）

### 3. 决策透明度

每个决策都有明确的原因：
- ✅ reason 字段记录决策依据
- ✅ 重要决策记录到 scratchpad
- ✅ 便于调试和理解系统行为

### 4. 渐进式响应

错误处理采用渐进式策略：
- error_count < 3: 正常操作
- error_count >= 3: 警告，LLM 应调整策略
- error_count >= 5: 建议分解任务

---

## 决策流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    DecisionEngine.decide()                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  ρ >= 1.0?       │──Yes──> RENEW
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ depth >= max?    │──Yes──> DECOMPOSE
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ Dashboard?       │──No───> REASON (fallback)
                    └──────────────────┘
                              │ Yes
                              ▼
                    ┌──────────────────┐
                    │ Interrupt?       │──Yes──> REASON (handle risks)
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ Goal completed?  │──Yes──> GOAL_REACHED
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ error_count >= 5?│──Yes──> DECOMPOSE
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ error_count >= 3?│──Yes──> REASON (adjust)
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ events >= 3?     │──Yes──> REASON (address)
                    └──────────────────┘
                              │ No
                              ▼
                    ┌──────────────────┐
                    │ ρ >= 0.8?        │──Yes──> REASON (warning)
                    └──────────────────┘
                              │ No
                              ▼
                         REASON (normal)
```

---

## 使用示例

### 场景 1: 正常操作

```python
dashboard = Dashboard()
dashboard.rho = 0.3
dashboard.error_count = 0
dashboard.goal_progress = "in_progress"

decision = engine.decide(
    context_rho=0.3,
    depth=1,
    max_depth=5,
    dashboard=dashboard
)

# Result: LoopResult(state=REASON, reason="Normal operation")
```

### 场景 2: 高错误率

```python
dashboard = Dashboard()
dashboard.error_count = 6

decision = engine.decide(
    context_rho=0.3,
    depth=1,
    max_depth=5,
    dashboard=dashboard
)

# Result: LoopResult(state=DECOMPOSE, reason="Error count too high (6) - consider decomposition")
```

### 场景 3: 中断请求

```python
dashboard = Dashboard()
dashboard.interrupt_requested = True
dashboard.event_surface.active_risks.append({
    "event_id": "risk_001",
    "summary": "Critical system error",
    "urgency": "high"
})

decision = engine.decide(
    context_rho=0.3,
    depth=1,
    max_depth=5,
    dashboard=dashboard
)

# Result: LoopResult(state=REASON, reason="Interrupt: 1 active risks need attention")
```

---

## 后续工作

虽然 DecisionEngine 现在是智能的，但还有改进空间：

### 立即需要（P0）

1. ✅ ~~Agent.run()~~ - 已完成
2. ✅ ~~ContextPartitions.get_all_messages()~~ - 已完成
3. ✅ ~~DecisionEngine.decide()~~ - 已完成
4. ⏭️ Gemini Provider - 决定是实现、标记还是移除

### 高优先级（P1）

5. **决策历史记录** - 记录决策历史以便分析
6. **自适应阈值** - 根据任务类型调整阈值
7. **决策指标** - 统计决策分布和效果

### 中优先级（P2）

8. **机器学习决策** - 基于历史数据优化决策
9. **多目标优化** - 平衡多个决策因素
10. **决策可视化** - Dashboard 显示决策历史

---

## 关键洞察

1. **决策是智能的核心** - DecisionEngine 让系统从"机械执行"变为"智能响应"
2. **Dashboard 是决策依据** - 没有 Dashboard，决策就是盲目的
3. **优先级很重要** - 决策逻辑的顺序决定了系统的行为
4. **透明度提升可调试性** - reason 字段让决策可追溯
5. **渐进式响应更稳健** - 不是一遇到问题就放弃，而是逐步升级响应

---

## 成功标准

- ✅ DecisionEngine 基于 Dashboard 做决策
- ✅ 响应中断请求和高优先级事件
- ✅ 检测目标完成状态
- ✅ 基于错误数量调整策略
- ✅ 注意待处理事件
- ✅ 提前警告高 context pressure
- ✅ 每个决策都有明确原因
- ✅ 测试覆盖 10 种场景
- ✅ 所有测试通过

**DecisionEngine 现在是一个真正的智能决策引擎！**
