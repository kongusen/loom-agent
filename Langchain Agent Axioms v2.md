# Agent 公理系统 v2.1

> 副标题：Agent runtime 的控制论宪法
>
> v2.1 的目标不是再补几个工程经验，而是把 v2.0 从“设计宣言”推进到“带失效域、可验证终止、共享状态一致性约束”的硬理论。

---

## v2.1 的立场变化

v2.0 最强的地方有三点：

1. `C_working` 是 Agent 的一等公民，而不是散落在 history 里的隐性状态。
2. `early_stop` 不是失败信号，而是能力边界声明。
3. Harness `Ψ` 是舞台，不是演员；它设置硬边界，但不代替 LLM 做语义判断。

v2.1 保留这三点，但做三个关键收紧：

1. **把“公理”和“策略”分开。**
   `ρ`、`δ_min`、压缩打分、`d_max(σ)` 这类参数不再伪装成公理，它们属于策略层。
2. **把“完成”从自我感觉改成可验证谓词。**
   `goal_reached` 不能只由 LLM 自评给出，必须有 `V` 提供的终止证据。
3. **把共享 `M_f` 从存储介质改成一致性契约。**
   多 Agent 一旦共享文件系统，就必须先定义冲突、顺序、可见性和审计语义。

---

## 核心主张

> **Agent 不是一段续写，而是一个在硬边界内运行、对外部世界施加动作、并对自身状态承担可验证责任的受约束控制系统。**

因此，本系统不再只描述“它由哪些部件构成”，而要约束：

1. 什么状态是必须保持的。
2. 什么状态变化是合法的。
3. 什么条件下可以宣称任务完成。
4. 多个 Agent 共享状态时，什么读写是可接受的。

---

## 三层结构

### 第一层：本体层（Ontology）

```
A = ⟨C, M, L, S, Ψ, V, Γ⟩
```

| 符号 | 名称 | 作用 |
|---|---|---|
| `C` | Context | 有界感知窗口；Agent 的唯一直接观察界面 |
| `M` | Memory | `M = (M_s, M_f, M_w)`；短时状态 / 外部持久化 / 模型权重 |
| `L` | Loop | 状态转移系统，负责 `Reason → Act → Observe → Decide` |
| `S` | Skill | 可被调度的能力代数，不是平铺工具列表 |
| `Ψ` | Harness | 硬边界、权限和否决权的持有者 |
| `V` | Verifier | 终止、阶段完成、约束满足的外部验证接口 |
| `Γ` | Consistency Contract | 多 Agent 共享 `M_f` 时的一致性语义 |

### 第二层：不变量层（Invariants）

本层给出系统成立所需的最小不变量。

### 第三层：策略层（Policy）

本层只描述实现上的可调参数，例如：

```
ρ_warn, δ_min, ε, d_max(σ), compression_score, priority_map
```

它们重要，但不是公理。它们可以替换、学习、任务化，且不改变系统本体。

---

## 唯一公理

> **唯一公理：**
>
> Agent runtime 是一个带硬边界、可外部化状态、可验证终止、可审计共享记忆的一致控制系统：
>
> ```
> A = ⟨C, M, L, S, Ψ, V, Γ⟩
> ```

为了让这条公理真正可操作，它必须展开为 6 条不变量。

---

## 六条不变量

### I1. 有界感知不变量

```
|C_t| ≤ W_max
```

Agent 在时刻 `t` 的直接感知只能发生在 `C_t` 内。任何未进入 `C_t` 的状态，对当前决策等价于不存在。

**推论：**
`renew` 不是优化技巧，而是由有界感知必然导出的保持连续性的操作。

### I2. 状态可外部化不变量

若某状态对后续决策必要，则它必须满足：

```
critical(x) = true  =>  serializable(x) = true  =>  storable_in(M_f)
```

至少以下状态必须可外部化：

1. 当前目标 `goal`
2. 当前计划 `plan`
3. 当前边界状态 `boundary_state`
4. 最近验证结果 `verification_state`
5. 子任务拓扑 `task_graph`

**推论：**
没有外部化能力，就不存在严格意义上的“跨窗口连续 Agent”。

### I3. 转移显式化不变量

每一步循环都必须产生显式可审计转移：

```
x_t --L--> x_{t+1}
```

其中至少记录：

```
τ_t = ⟨reason_summary, act, effect, observation, decision, verifier_result⟩
```

任何影响未来决策的隐式状态变化，如果没有记录到 `τ_t` 或 `M_f`，都视为理论外行为。

### I4. 硬边界优先不变量

Harness `Ψ` 对物理、权限、安全和拓扑边界拥有最终否决权。

```
violate_hard_boundary(x_t, Ψ) => veto
```

这里的 `veto` 可以是：

1. 强制 `renew`
2. 强制交控
3. 强制终止
4. 强制拒绝执行某个动作

但 `Ψ` 不负责替模型做中间语义判断。

### I5. 可验证终止不变量

任务完成不能由 LLM 自评单独成立，必须满足：

```
goal_reached(x_t) := ∃ v ∈ V_terminal, verdict(v, x_t) = pass
```

LLM 的 `goal_progress` 仅是内部信号，不是终止证明。

**推论：**
`terminate` 是一个验证事件，而不是一个心理状态。

### I6. 共享记忆一致性不变量

若多个 Agent 共享 `M_f`，则所有共享写入必须满足一致性契约 `Γ`：

```
write(e, M_f) is valid  <=>  satisfies(e, Γ)
```

`Γ` 至少定义：

1. 写入粒度
2. 可见性时机
3. 顺序语义
4. 冲突检测
5. 审计保留

没有 `Γ`，则多 Agent 共享 `M_f` 只是偶然可用，而不是理论内合法行为。

---

## 运行时状态

定义时刻 `t` 的运行时状态为：

```
x_t = ⟨goal, C_t, w_t, m_t, b_t, d_t, q_t, status_t⟩
```

| 字段 | 含义 |
|---|---|
| `goal` | 当前顶层目标 |
| `C_t` | 当前上下文窗口 |
| `w_t` | 工作状态 `C_working` 的结构化视图 |
| `m_t` | 已外部化的持久记忆索引 |
| `b_t` | 边界状态集合 |
| `d_t` | 当前任务分解深度 |
| `q_t` | 验证状态与待验证队列 |
| `status_t` | `running / suspended / waiting / terminated / handed_off` |

其中：

```
w_t = ⟨plan, dashboard, pending_checks, recent_failures, task_graph_ref⟩
```

v2.1 对 `C_working` 的收紧如下：

> **`C_working` 不是无限保留，而是固定 schema + 固定预算 + 可覆写槽位。**

因此，“永不压缩”应理解为：

1. 它的逻辑字段不能缺席。
2. 它的槽位内容可以覆写和摘要化。
3. 它不能无限膨胀成新的 `C_history`。

---

## Loop 的形式化

```
L = (Reason → Act → Observe → Decide)^*
```

其中 `Decide` 取代 v2.0 的 `Δ`，因为这一阶段本质上是在当前状态和验证结果上选择下一状态转移。

### 单步语义

```
Reason:   π_t = plan(x_t)
Act:      e_t = execute(π_t.action, S, Ψ)
Observe:  o_t = observe(e_t)
Verify:   r_t = verify(o_t, V)
Decide:   x_{t+1} = decide(x_t, o_t, r_t, Ψ)
```

### 合法转移集合

```
Decide(x_t) ∈ {
  continue,
  renew,
  decompose,
  wait,
  handoff,
  terminate
}
```

### 终止条件

```
terminate 仅当：
  1. verdict(pass) 成立；或
  2. Ψ 基于硬边界做强制终止。
```

### 挂起条件

```
wait / handoff 仅当：
  1. 缺失外部输入；
  2. 缺失权限；
  3. 缺失工具；
  4. 到达结构边界且不可再合法分解。
```

---

## 边界条件模型

v2.0 的 `early_stop` 很重要，但语义还不够细。v2.1 将边界条件显式分类。

### 边界集合

```
B = {B_phys, B_topo, B_perm, B_safe, B_cap, B_epi, B_time}
```

| 边界 | 含义 | 典型触发 |
|---|---|---|
| `B_phys` | 物理边界 | `ρ = 1.0`、token 用尽、资源耗尽 |
| `B_topo` | 拓扑边界 | `depth = d_max` |
| `B_perm` | 权限边界 | 无文件/网络/系统权限 |
| `B_safe` | 安全边界 | 违反安全策略或约束 |
| `B_cap` | 能力边界 | 缺少必要技能或工具 |
| `B_epi` | 认识边界 | 无法形成可验证判断，证据不足 |
| `B_time` | 时间边界 | deadline、超时、预算到期 |

### early_stop 的严格语义

```
early_stop(x_t) := ∃ B_i ∈ B, triggered(B_i, x_t) ∧ ¬goal_reached(x_t)
```

因此 `early_stop` 不等于“做失败了”，而等于：

> 当前状态已触到某类边界，继续原路径推进不再合法或不再经济。

### 边界响应映射

```
response(B_phys) = renew | terminate
response(B_topo) = handoff
response(B_perm) = wait | handoff
response(B_safe) = veto
response(B_cap)  = decompose | handoff
response(B_epi)  = verify_more | handoff
response(B_time) = summarize_and_handoff | terminate
```

这意味着“拆解”只是 `early_stop` 的一个分支，而不是统一答案。

---

## 可验证性模型

v2.0 最大的理论缺口，是把 `goal_progress` 和 `goal_reached` 靠得太近。v2.1 强制拆开。

### 两种不同的量

```
self_estimate(x_t) ∈ [0, 1] or free_text
verdict(x_t) ∈ {pass, fail, unknown}
```

前者属于内部控制信号，后者属于外部验证信号。

### 验证接口

```
V = {v_1, v_2, ..., v_n}
```

每个验证器是一个判定函数：

```
v_i : X -> {pass, fail, unknown}
```

常见类型：

1. **结果验证器**：输出是否满足目标。
2. **阶段验证器**：某个子目标是否完成。
3. **约束验证器**：是否违反场景/权限/安全约束。
4. **一致性验证器**：共享状态是否冲突。

### 终止原则

```
LLM_claim_done(x_t) ∧ verdict = unknown   =>  不可 terminate
LLM_claim_done(x_t) ∧ verdict = fail      =>  不可 terminate
LLM_claim_done(x_t) ∧ verdict = pass      =>  可 terminate
```

### 最弱验证原则

若任务类型暂时没有强验证器，则系统至少要输出：

```
certificate_t = ⟨claim, evidence, unresolved_risks⟩
```

即使无法强证真，也必须能把“我为什么认为已经完成”转化成结构化证据，而不是一句主观判断。

---

## 一致性模型

v2.0 把 `M_f` 当成三条定理的共同基础设施，这是对的；但只要进入多 Agent，就不能只说“共享”，必须定义共享语义。

### 一致性契约

```
Γ = ⟨namespace, log, order, visibility, conflict, compaction⟩
```

### v2.1 的最小一致性要求

#### Γ1. 追加优先

共享写入的原语不是“原地覆盖”，而是：

```
append(event)
```

状态视图通过日志物化得到，而不是直接共享可变单元。

#### Γ2. 事件元数据完备

每个共享事件至少包含：

```
e = ⟨id, agent_id, parent_id, topic, payload, seq, ts, version, kind⟩
```

其中：

1. `seq` 保证单 Agent 内部单调顺序。
2. `parent_id` 记录因果来源。
3. `version` 用于物化视图时的冲突检测。

#### Γ3. 单 Agent 单调读

对同一 Agent 而言，后续读取不能看见比自己先前读取更旧的共享视图。

#### Γ4. 跨 Agent 最终可见

跨 Agent 不要求强同步，但要求：

```
append(e) succeeded  =>  eventually visible(e)
```

#### Γ5. 冲突显式化

若两个事件同时修改同一物化键：

```
conflict(k, v1, v2) => {merge, reject, escalate}
```

冲突必须进入日志并可审计，不能静默覆盖。

### 理论后果

因此，多 Agent 模型的基础设施不是“共享文件夹”，而是：

> **带事件日志、版本和冲突语义的外部化工作记忆。**

---

## Skill 与 Scene 的重述

v2.0 的 `Σ` 很有价值，但它更像能力代数而不是独立定理。v2.1 将其放回 `S` 的结构里。

### Skill 不是工具表，而是约束化能力单元

```
σ = ⟨id, tools, constraints, memory_scope, verifier_set⟩
```

### 组合规则

```
σ_a ⊕ σ_b = ⟨
  tools_a ∪ tools_b,
  constraints_a ∩ constraints_b,
  memory_scope_a ∪ memory_scope_b,
  verifier_a ∪ verifier_b
⟩
```

这里保留 v2.0 最重要的思想：

> 约束收窄通常提升可靠性，因为它减少无效搜索空间。

但 v2.1 补上一条：

> 约束收窄只有在验证器覆盖不下降时才成立；否则它可能只是把错误隐藏掉。

---

## 从“定理”改成“派生命题”

v2.0 里的“定理”更接近工程推论。v2.1 改称“派生命题”，并标注前提。

### 命题 P1：可续存性

由 `I1 + I2` 可得：

```
bounded(C) ∧ externalizable(critical_state)
=> renewable(runtime)
```

即：只要感知有界且关键状态可外部化，runtime 就可以跨窗口续存。

### 命题 P2：可验证终止

由 `I3 + I5` 可得：

```
auditable_transition ∧ verifier_available
=> terminal_claims are checkable
```

即：终止不是主观声称，而是可检查断言。

### 命题 P3：边界驱动分解

由 `I4` 与边界分类可得：

```
early_stop ≠ failure
early_stop = boundary_trigger
```

因此分解、交控、等待、拒绝，都是边界响应，不应混成单一失败恢复逻辑。

### 命题 P4：多 Agent 一致协作

由 `I2 + I6` 可得：

```
shared_memory ∧ consistency_contract
=> multi_agent collaboration is auditable
```

若没有 `Γ`，则多 Agent 只是并发访问同一磁盘，不构成理论上的协作系统。

### 命题 P5：可审计进化

由 `I2 + I3 + I5 + I6` 可得：

```
evolution is admissible only if its cause, evidence, and effect are all auditable
```

也就是说，Evolve 不是“改得更聪明了”，而是“改动有触发原因、验证结果和回滚依据”。

---

## 自我进化的收紧

v2.0 的 `E1-E4` 很有启发性，但还欠缺“何时允许写入系统”的合法性条件。v2.1 补上准入门槛。

```
Evolve(A, ΔA) is admissible iff:
  1. trigger_evidence exists
  2. expected_gain is stated
  3. verifier exists
  4. rollback path exists
```

### 四种进化机制

| 机制 | 合法触发 | 需要的验证 |
|---|---|---|
| `E1` 回顾蒸馏 | 重复模式被记录 | 下次任务命中率提升 |
| `E2` 模式结晶 | 高频成功链路稳定出现 | 新 Skill 的通过率不低于旧路径 |
| `E3` 约束固化 | 明确失败根因重复出现 | 新约束减少错误且不过度压制能力 |
| `E4` 阿米巴分裂 | 某类子任务长期高负载 | 新拓扑提升吞吐或成功率 |

### E3 的棘轮修正

v2.0 已指出“约束只增不减”的风险。v2.1 进一步规定：

```
constraint κ is valid only within scope σ and review_window T
```

也就是说，约束默认不是永恒真理，而是：

1. 有适用域 `σ`
2. 有复审周期 `T`
3. 有失效与撤销条件

否则 E3 很容易把系统训成一个越来越胆小的执行器。

---

## 失效域

一个理论要更硬，必须同时说明它在哪些地方会失效。

本系统在以下条件下不保证上述命题成立：

1. `C_working` 不是结构化状态，而是自由文本堆积。
2. `V` 缺席，或验证器长期返回 `unknown` 且无证据输出。
3. `M_f` 存在静默覆盖，且没有事件日志。
4. `Ψ` 在运行时频繁替 LLM 做中间语义判断。
5. `S` 没有被约束化，只是大工具池直连。
6. 进化写入无审计、无回滚、无作用域。

满足任一条时，本系统退化为“工程风格建议集”，而不是“控制论宪法”。

---

## 对实现的约束解释

为了避免理论和实现再次脱节，v2.1 明确区分：

### 属于公理层的

1. `C` 必须有界。
2. 关键状态必须可外部化。
3. 转移必须可审计。
4. 终止必须可验证。
5. 共享写入必须满足一致性契约。

### 属于策略层的

1. 何时主动 `renew`
2. `ρ_warn` 取多少
3. `d_max` 是常数还是 `d_max(σ)`
4. `ΔH` 如何近似
5. 压缩函数如何设计
6. 优先级函数 `f` 如何实现

这意味着：

> `ΔH` 不是公理，只是通信价值的一个候选代理量。  
> `goal_progress` 不是完成证明，只是控制信号。  
> `d_max` 不是宇宙常数，只是拓扑预算。  

---

## 总结

v2.1 将 Agent runtime 定义为：

> **一个在有界上下文中运行、通过可外部化状态保持连续、通过验证器声明完成、通过一致性契约共享记忆、并由 Harness 持有硬边界否决权的控制系统。**

因此，系统的核心不再是“模型是否足够聪明”，而是以下五点是否成立：

1. 状态是否完整
2. 转移是否显式
3. 完成是否可证
4. 边界是否清楚
5. 共享是否一致

只要这五点不成立，再强的模型也只是把不确定性藏进 prompt；只有这五点成立，Agent 才开始拥有理论上的可控性。

---

## 下一步待证明的问题

1. **最小验证充分性：** 对开放任务而言，什么样的 `V` 才足够支撑 `terminate`？
2. **边界到策略的最优映射：** `B_cap` 触发时，何时该 `decompose`，何时该 `handoff`？
3. **一致性与吞吐的折中：** `Γ` 多强才不会把多 Agent 吞吐压垮？
4. **进化准入的统计判据：** `E2/E3/E4` 的“足够证据”门槛如何定义？
5. **Scene 组合的完备性：** `σ_a ⊕ σ_b` 是否总能保持验证器闭包？

*Agent 公理系统 v2.1 · 完*
