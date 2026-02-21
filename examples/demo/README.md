# Loom v0.6.0 Demo

15 个自包含示例，逐层展示框架核心能力。所有 demo 使用 MockProvider，无需 API Key。

## 目录

```
demo/
├── _mock.py                # 共享 MockProvider + MockEmbedder
├── 01_hello_agent.py       # Agent 基础 run/stream
├── 02_tools.py             # define_tool + ToolRegistry
├── 03_event_bus.py         # EventBus 模式匹配 + 父子传播
├── 04_interceptors.py      # InterceptorChain 中间件
├── 05_memory.py            # MemoryManager L1→L2→L3
├── 06_knowledge.py         # KnowledgeBase 混合检索
├── 07_context.py           # ContextOrchestrator 自适应预算
├── 08_skills.py            # SkillRegistry 触发激活
├── 09_cluster.py           # ClusterManager 拍卖分配
├── 10_reward.py            # RewardBus EMA + LifecycleManager
├── 11_provider.py          # BaseLLMProvider 重试 + 熔断
├── 12_runtime.py           # Runtime 编排
├── 13_amoeba.py            # AmoebaLoop 6 阶段自组织
├── 14_delegation.py        # 多 Agent 委派
└── 15_full_stack.py        # 全栈流水线
```

## 运行

```bash
cd examples/demo
python 01_hello_agent.py   # 运行单个
for f in 0*.py 1*.py; do echo "=== $f ===" && python "$f"; done  # 运行全部
```

## 功能矩阵

| # | 示例 | 核心能力 |
|---|------|----------|
| 01 | Hello Agent | Agent 创建、run()、stream() |
| 02 | Tools | define_tool、Pydantic 参数、ToolRegistry |
| 03 | EventBus | 类型事件、模式匹配、父子层级传播 |
| 04 | Interceptors | 中间件链、元数据注入、计时 |
| 05 | Memory | L1 滑动窗口、L2 工作记忆、溢出级联 |
| 06 | Knowledge | 文档摄入、向量检索、RRF 混合排序 |
| 07 | Context | 多源编排、EMA 自适应评分、预算分配 |
| 08 | Skills | 关键词/正则触发、激活/停用、技能发现 |
| 09 | Cluster | 能力画像、竞价拍卖、忙碌降权 |
| 10 | Reward | EMA 信号收敛/衰减、连败追踪、有丝分裂 |
| 11 | Provider | 指数退避重试、熔断器、自定义 Provider |
| 12 | Runtime | 集群编排、任务提交、健康检查 |
| 13 | Amoeba | 6 阶段循环：感知→匹配→扩展+执行→评估+适应 |
| 14 | Delegation | 父子 Agent、事件传播、任务路由 |
| 15 | Full Stack | Agent+Memory+Knowledge+Context+Events+Tools |
