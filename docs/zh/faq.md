# 常见问题 (FAQ)

### 我可以在没有 LLM 的情况下使用 Loom 吗？
是的，理论上可以。`Node` 的逻辑可以是纯确定性的 Python 代码。但是，`AgentNode` 是专门为 LLM 驱动的交互设计的。你可以混合使用：用代码实现 ToolNode，用 LLM 驱动 AgentNode。

### 如何防止无限循环？
1.  在 Agent 中设置 `max_iterations`（最大迭代次数）。
2.  使用 `BudgetInterceptor` 来强制终止超过 Token 限制的任务。

### 新陈代谢记忆 (Metabolic Memory) 与 RAG 有什么区别？
RAG 像一个搜索引擎（被动检索）。新陈代谢记忆像一个消化系统（主动代谢），随着时间的推移，它会压缩、清洗并将信息整合成一个结构化的项目状态 (PSO)。

### Loom 适合生产环境吗？
Loom 的核心协议（Protocols）是稳定的。内置的节点实现处于 Beta 阶段。在部署之前，我们建议对您的 Agent 进行全面的测试。
