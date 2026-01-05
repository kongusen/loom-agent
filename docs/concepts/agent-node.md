# Agent 模式与节点机制 (Agent Patterns & Node Mechanism)

Loom 将所有活跃组件统一在 **Node (节点)** 的概念下。无论是简单的工具、复杂的 Agent，还是 Agent 团队，它们都是通过标准协议通信的 Node。

## 节点协议 (The Node Protocol)

Loom 中的每个组件都实现了 `NodeProtocol`。这确保了系统的任何部分都可以与任何其他部分通信，而无需了解其内部实现。

```python
class NodeProtocol(Protocol):
    node_id: str
    
    async def process(self, event: CloudEvent) -> CloudEvent:
        """Process an incoming event and return a response."""
        ...
```

### 分形递归 (Fractal Recursion)

由于 Agent 和工作流 (Crews) 共享相同的 `Node` 接口，它们可以无限组合。

*   **Agent A** 可以调用 **Agent B**。
*   **Agent B** 可以调用 **Crew C** (包含 Agent D, E, F)。
*   **Agent D** 可以调用 **Agent A** (通过深度限制处理循环)。

这种**分形架构 (Fractal Architecture)** 允许你用简单、自相似的积木构建复杂的系统。

## Agent 架构

`AgentNode` 是 Node 的一种具体实现，它拥有**认知 (Cognition)** 能力。

### 内部结构
1.  **摄入 (Ingest)**: 接收 `CloudEvent`。
2.  **认知 (Cognition)**:
    *   检索上下文 (Memory)。
    *   决定模式 (System 1/2)。
    *   生成计划 (如果是 System 2)。
3.  **执行 (Fractal Orchestrator)**:
    *   执行工具。
    *   委托子任务给其他 Node。
4.  **合成 (Synthesize)**: 制定最终响应。

## Agent 模式

Loom 无缝支持多种 Agent 模式：

### 1. ReAct (Reasoning + Acting)
标准模式，Agent 进行推理，选择工具，观察输出，然后重复。这是 `AgentNode` 在 System 2 模式下的默认行为。

### 2. Planning (Plan-and-Solve)
Agent 先生成多步计划，然后逐步执行。
*   **实现**: 通过 `PlannerSkill` 或 System 2 的隐式能力实现。

### 3. Crew / Swarm (团队/蜂群)
一组协同工作的 Agent。
*   **SequentialCrew**: Agent 链式传递任务 (A -> B -> C)。
*   **HierarchicalCrew**: 领导 Agent 委托任务给工 Agent。

在 Loom 中，`Crew` 只是另一个 `Node`。对于调用者来说，它看起来就像一个单一的 Agent。

## 递归与委托 (Recursion & Delegation)

Loom v0.3.6 引入了 **无限递归**。一个 Agent 可以决定将子任务 **委托 (Delegate)** 给另一个 Node。

```python
# 用户问: "研究 X 并写一份报告。"

# Agent A (经理)
#  -> 委托 "研究 X" 给 Agent B (研究员)
#       -> Agent B 搜索网络，总结。
#       -> Agent B 返回摘要。
#  -> 委托 "写报告" 给 Agent C (作家)
#       -> Agent C以此摘要为基础，撰写文本。
#       -> Agent C 返回文本。
#  -> Agent A 返回最终报告给用户。
```

这由 `FractalOrchestrator` 处理，它管理调用栈并确保上下文在层级之间正确传递（必要时进行压缩）。
