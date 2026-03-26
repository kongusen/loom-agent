# Agent 公理系统 v2.2

> 副标题：务实的 Agent Runtime 架构原则
>
> v2.2 的目标：在理论严谨性和工程可操作性之间找到平衡点。承认 LLM 的概率本质，提供渐进式的能力增强路径。

---

## v2.2 的立场

v2.1 的问题不在于方向错误，而在于：
1. 把"理想状态"当成"最小要求"
2. 假设所有任务都可预知和验证
3. 为单机 Agent 引入分布式系统的复杂度

v2.2 的修正：
1. **分层能力模型** - 从 L0 (最小可用) 到 L3 (完全验证)
2. **承认不确定性** - LLM 是概率模型，不强求确定性保证
3. **渐进式增强** - 每层都可独立运行，上层是可选增强

---

## 核心主张

> **Agent Runtime 是一个在有界上下文中运行、通过显式状态管理保持连续性、支持渐进式验证和协作的概率控制系统。**

关键词：
- **有界上下文** - 必需（I1）
- **显式状态** - 必需（I2）
- **渐进式验证** - 可选增强
- **概率控制** - 承认 LLM 本质

---

## 四层能力模型

### L0: 最小可用 Agent
**必需组件**: `⟨C, M_s, L⟩`
- `C`: 有界上下文窗口
- `M_s`: 短期记忆（对话历史）
- `L`: 基础循环 (Reason → Act → Observe)

**保证**: 可以完成单轮对话任务

### L1: 可续存 Agent
**新增**: `M_f` (外部持久化)
- 关键状态可序列化
- 支持跨会话恢复
- 基础压缩策略

**保证**: 可以处理长对话和多会话任务

### L2: 受约束 Agent
**新增**: `⟨S, Ψ⟩`
- `S`: 技能/场景系统
- `Ψ`: 边界和约束

**保证**: 可以在受限环境中安全运行

### L3: 可验证 Agent
**新增**: `⟨V, Γ⟩`
- `V`: 验证器（可选）
- `Γ`: 一致性契约（多 Agent 时）

**保证**: 可以提供完成证据和协作保证

---

## 六条不变量（重述）

### I1. 有界感知不变量 [L0 必需]

```
|C_t| ≤ W_max
```

**含义**: Agent 的直接感知受窗口限制。

**推论**:
- `renew` 是必然操作，不是优化
- 超出窗口的状态必须外部化或丢弃

**实现要求**:
- 必须有 token 计数机制
- 必须有窗口预算管理

### I2. 状态显式化不变量 [L0 必需]

```
影响未来决策的状态必须显式记录
```

**含义**: 隐式状态变化会导致不可预测行为。

**最小要求**:
- 对话历史必须保留
- 工具调用和结果必须记录

**L1 增强**:
- 关键状态可外部化
- 支持状态恢复

**实现要求**:
- 结构化的状态表示
- 清晰的状态更新接口

### I3. 转移可追踪不变量 [L1 推荐]

```
每步循环产生可审计的转移记录
```

**含义**: 可以回溯 Agent 的决策过程。

**最小记录**:
```
τ_t = ⟨action, observation, decision⟩
```

**L2 增强**:
```
τ_t = ⟨reason, action, effect, boundary_check, decision⟩
```

**实现要求**:
- 执行轨迹日志
- 可选的详细程度控制

### I4. 边界响应不变量 [L2 必需]

```
触及边界时必须有明确的响应策略
```

**含义**: 不能让 Agent 在边界处"卡住"或"乱猜"。

**边界分类** (简化为 4 类):
1. **物理边界** (B_phys): token 耗尽、资源不足
2. **权限边界** (B_perm): 缺少权限或工具
3. **能力边界** (B_cap): 任务超出能力范围
4. **时间边界** (B_time): 超时或预算耗尽

**响应策略**:
```
B_phys → renew | compress | terminate
B_perm → wait | request | handoff
B_cap  → decompose | handoff | early_stop
B_time → summarize | handoff | terminate
```

**实现要求**:
- 边界检测机制
- 可配置的响应策略

### I5. 完成可信度不变量 [L3 可选]

```
任务完成应提供可信度指标，而非二元断言
```

**含义**: 承认 LLM 的概率本质，不强求绝对验证。

**三级可信度**:
1. **自评** (self_estimate): LLM 的主观判断
2. **证据** (evidence): 可观察的完成信号
3. **验证** (verified): 外部验证器确认

**实现要求**:
- L0/L1: 只需 self_estimate
- L2: 建议提供 evidence
- L3: 可选的 verifier 接口

### I6. 共享最小冲突不变量 [L3 可选]

```
多 Agent 共享状态时，优先避免冲突而非强制一致性
```

**含义**: 用简单机制避免大部分冲突，而非构建完整的分布式系统。

**最小实现** (L1):
- Append-only 日志
- 每个 Agent 有独立命名空间

**L2 增强**:
- 事件带 agent_id 和 timestamp
- 读取时过滤可见范围

**L3 完整**:
- 冲突检测
- 合并策略
- 审计日志

**实现要求**:
- L1: 简单的 append-only store
- L2: 事件元数据
- L3: 冲突处理逻辑

---

## 运行时状态模型

### 最小状态 (L0)

```python
x_t = {
    "goal": str,           # 当前目标
    "context": Context,    # 上下文窗口
    "history": List[Msg],  # 对话历史
    "status": Status       # running | done | error
}
```

### 扩展状态 (L1)

```python
x_t = {
    ...L0,
    "working": WorkingState,  # 工作状态
    "memory_refs": List[str], # 外部记忆引用
    "trace": List[Step]       # 执行轨迹
}
```

### 完整状态 (L2)

```python
x_t = {
    ...L1,
    "scene": str,              # 当前场景
    "boundaries": BoundarySet, # 边界状态
    "constraints": Dict        # 活跃约束
}
```

---

## C_working 的务实设计

### 问题重述

v2.1 要求固定 schema，但这与任务多样性冲突。

### v2.2 方案：预算化的灵活结构

```python
C_working = {
    "budget": int,        # 固定预算（如 2000 tokens）
    "schema": {           # 推荐结构（非强制）
        "goal": str,
        "plan": Optional[str],
        "progress": Optional[Dict],
        "blockers": Optional[List[str]],
        "next_action": Optional[str]
    },
    "overflow": str       # 超出 schema 的自由内容
}
```

**原则**:
1. 预算是硬约束
2. Schema 是软建议
3. 允许 overflow 但计入预算

**实现**:
- 提供 schema 模板
- LLM 可以选择使用或忽略
- 超出预算时强制压缩

---

## Loop 的渐进式形式化

### L0: 基础循环

```
loop:
    reason = llm.generate(context)
    if reason.has_tool_call:
        result = execute_tool(reason.tool_call)
        context.append(result)
    else:
        return reason.content
```

### L1: 带状态管理

```
loop:
    reason = llm.generate(context)
    update_working_state(reason)

    if reason.has_tool_call:
        result = execute_tool(reason.tool_call)
        context.append(result)
        trace.append((reason, result))
    else:
        save_state(memory)
        return reason.content
```

### L2: 带边界检查

```
loop:
    if check_boundaries() == triggered:
        return handle_boundary()

    reason = llm.generate(context)
    update_working_state(reason)

    if reason.has_tool_call:
        if not check_constraints(reason.tool_call):
            return constraint_violation()
        result = execute_tool(reason.tool_call)
        context.append(result)
        trace.append((reason, result))
    else:
        save_state(memory)
        return reason.content
```

### L3: 带验证

```
loop:
    if check_boundaries() == triggered:
        return handle_boundary()

    reason = llm.generate(context)
    update_working_state(reason)

    if reason.has_tool_call:
        if not check_constraints(reason.tool_call):
            return constraint_violation()
        result = execute_tool(reason.tool_call)
        context.append(result)
        trace.append((reason, result))
    else:
        if verifier_available():
            verdict = verify(reason.content, goal)
            if verdict == "pass":
                return reason.content
            else:
                context.append(f"Verification failed: {verdict}")
                continue
        else:
            return reason.content
```

---

## 边界条件的务实处理

### 简化的边界模型

不再区分 7 种边界，而是 4 大类 + 响应策略：

```python
class Boundary:
    PHYSICAL = "physical"   # token/memory/time 耗尽
    PERMISSION = "permission"  # 缺少权限/工具
    CAPABILITY = "capability"  # 任务超出能力
    TIME = "time"           # 超时/deadline

class Response:
    RENEW = "renew"         # 压缩上下文继续
    WAIT = "wait"           # 等待外部输入
    HANDOFF = "handoff"     # 转交给其他 Agent/人类
    DECOMPOSE = "decompose" # 拆解任务
    STOP = "stop"           # 提前终止
```

### 响应映射（可配置）

```python
default_boundary_policy = {
    Boundary.PHYSICAL: [Response.RENEW, Response.STOP],
    Boundary.PERMISSION: [Response.WAIT, Response.HANDOFF],
    Boundary.CAPABILITY: [Response.DECOMPOSE, Response.HANDOFF],
    Boundary.TIME: [Response.STOP, Response.HANDOFF]
}
```

### 实现要点

1. **检测优先于响应** - 先准确识别边界类型
2. **策略可配置** - 不同场景不同策略
3. **LLM 参与决策** - 边界检测后，让 LLM 选择响应

---

## 验证器的渐进式设计

### L0/L1: 无验证器

```python
def is_done(response):
    return "done" in response.lower() or no_tool_calls(response)
```

### L2: 证据收集

```python
def is_done(response, goal, trace):
    if no_tool_calls(response):
        evidence = extract_evidence(response, trace)
        return {
            "done": True,
            "confidence": "self_estimate",
            "evidence": evidence
        }
    return {"done": False}
```

### L3: 外部验证

```python
def is_done(response, goal, trace, verifier=None):
    if no_tool_calls(response):
        evidence = extract_evidence(response, trace)

        if verifier:
            verdict = verifier.check(goal, response, evidence)
            return {
                "done": verdict == "pass",
                "confidence": "verified",
                "evidence": evidence,
                "verdict": verdict
            }

        return {
            "done": True,
            "confidence": "self_estimate",
            "evidence": evidence
        }
    return {"done": False}
```

### 验证器接口

```python
class Verifier(Protocol):
    def check(self, goal: str, result: str, evidence: Dict) -> Verdict:
        """
        Returns:
            "pass": 目标达成
            "fail": 目标未达成
            "unknown": 无法判断
        """
        ...
```

**常见验证器类型**:
1. **规则验证器** - 检查输出格式、必需字段
2. **测试验证器** - 运行测试用例
3. **人类验证器** - 请求人类确认
4. **LLM 验证器** - 用另一个 LLM 评估

---

## 共享记忆的渐进式设计

### L1: 最简共享（独立命名空间）

```python
class SharedMemory:
    def __init__(self):
        self.store = {}  # {agent_id: {key: value}}

    def write(self, agent_id: str, key: str, value: Any):
        if agent_id not in self.store:
            self.store[agent_id] = {}
        self.store[agent_id][key] = value

    def read(self, agent_id: str, key: str):
        return self.store.get(agent_id, {}).get(key)
```

**特点**:
- 零冲突（每个 Agent 独立空间）
- 无协作（Agent 间不可见）

### L2: Append-only 事件日志

```python
class Event:
    id: str
    agent_id: str
    timestamp: float
    kind: str  # "memory" | "task" | "result"
    payload: Dict

class EventLog:
    def append(self, event: Event):
        self.events.append(event)

    def read(self, agent_id: str = None, kind: str = None):
        filtered = self.events
        if agent_id:
            filtered = [e for e in filtered if e.agent_id == agent_id]
        if kind:
            filtered = [e for e in filtered if e.kind == kind]
        return filtered
```

**特点**:
- 可见性可控（通过过滤）
- 无冲突（只追加）
- 可审计（完整历史）

### L3: 带冲突检测

```python
class VersionedEvent(Event):
    parent_id: Optional[str]  # 因果关系
    version: int              # 版本号

class ConflictDetector:
    def check(self, event: VersionedEvent) -> Optional[Conflict]:
        # 检查是否有其他 Agent 修改了相同资源
        ...

    def resolve(self, conflict: Conflict, strategy: str):
        # "last_write_wins" | "merge" | "manual"
        ...
```

**特点**:
- 检测冲突
- 可配置解决策略
- 保留冲突历史

---

## 实现路线图

### 阶段 1: L0 → L1 (可续存)

**目标**: 支持长对话和跨会话

**核心任务**:
1. 实现 `M_f` (外部持久化)
2. 实现 `WorkingState` 管理
3. 实现基础压缩策略
4. 实现执行轨迹记录

**验收标准**:
- 可以恢复中断的对话
- 可以处理超过窗口的长对话

### 阶段 2: L1 → L2 (受约束)

**目标**: 安全可控的 Agent

**核心任务**:
1. 实现 Scene/Skill 系统
2. 实现边界检测
3. 实现约束验证
4. 实现边界响应策略

**验收标准**:
- 可以限制 Agent 的工具访问
- 触及边界时有明确响应
- 约束违规会被拦截

### 阶段 3: L2 → L3 (可验证)

**目标**: 可信的多 Agent 协作

**核心任务**:
1. 实现 Verifier 接口
2. 实现证据收集
3. 实现事件日志
4. 实现冲突检测（可选）

**验收标准**:
- 可以提供完成证据
- 多 Agent 写入可审计
- 冲突可检测和解决

---

## 失效域（明确边界）

本理论在以下情况下**不适用**或**需要修改**:

### 1. 极短对话场景
如果任务可以在单轮完成，L1/L2/L3 都是过度设计。

**建议**: 只用 L0

### 2. 纯创意任务
如果任务是开放式创作（写诗、头脑风暴），过度约束会限制创造力。

**建议**: 只用 L0 或 L1，不要用 L2 的约束

### 3. 高度动态环境
如果外部环境快速变化，持久化状态可能过时。

**建议**: 缩短状态有效期，增加重新感知频率

### 4. 单 Agent 场景
如果永远只有一个 Agent，L3 的共享机制是浪费。

**建议**: 只实现到 L2

### 5. 完全可信环境
如果 Agent 运行在沙箱中且无敏感操作，L2 的约束可能过度。

**建议**: 简化约束检查

---

## 与 v2.1 的对比

| 维度 | v2.1 | v2.2 |
|------|------|------|
| 验证器 | 必需 | L3 可选 |
| 一致性 | 强一致性 | 渐进式（L1→L3）|
| C_working | 固定 schema | 预算化灵活结构 |
| 边界分类 | 7 种 | 4 种 |
| 状态外部化 | 所有关键状态 | 按需外部化 |
| 完成判定 | 必须外部验证 | 三级可信度 |
| 理论定位 | 控制论宪法 | 务实架构原则 |

---

## 总结

v2.2 的核心思想：

1. **承认现实** - LLM 是概率模型，不强求确定性
2. **渐进增强** - 从最简实现到完整特性的清晰路径
3. **可选复杂度** - 每层都可独立运行
4. **务实优先** - 理论服务于工程，而非相反

**一句话**:
> Agent Runtime 应该像 HTTP 协议一样 - 最简版本人人能实现，完整版本提供强大保证，中间有清晰的升级路径。

---

*Agent 公理系统 v2.2 · 完*
