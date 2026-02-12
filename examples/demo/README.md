# Loom Agent Demo

本示例展示 Loom Agent 的核心能力。

## 目录结构

```
demo/
├── README.md
├── 01_basic_agent.py        # 基础 Agent 使用
├── 02_custom_tools.py       # 自定义工具
├── 03_skills_system.py      # Skills 系统
├── 04_disabled_tools.py     # 禁用内置工具
├── 05_event_bus.py          # 事件总线
├── 06_agent_builder.py      # 链式构建
├── 07_memory_scope.py       # 记忆作用域
├── 08_sandbox_tools.py      # 沙盒工具
├── 09_multi_agent.py        # 多 Agent 协作
├── 10_knowledge_rag.py      # 知识库 RAG
├── 11_streaming_output.py   # 流式输出
├── 12_task_delegation.py    # 任务委派
├── 13_parallel_execution.py # 并行执行
├── 14_workflow_pipeline.py  # 工作流管道
├── 15_memory_hierarchy.py   # 记忆层级与跨Session共享
├── 16_interceptors.py       # 拦截器示例
├── 17_memory_rag_autowiring.py # Memory+RAG+Knowledge 自动接线
├── 18_adaptive_budget.py    # Context 动态预算与任务阶段
├── 19_tracing_metrics.py    # Tracing 与 Metrics 可观测性
├── 20_checkpoint.py         # Checkpoint 检查点与恢复
└── skills/
    └── code-review/
        └── SKILL.md
```

## 运行示例

```bash
# 设置环境变量
export OPENAI_API_KEY="your-key"

# 运行基础示例
python 01_basic_agent.py

# 运行自定义工具示例
python 02_custom_tools.py
```

## 功能演示

| 示例 | 功能 |
|------|------|
| 01 | Agent 基础创建和运行 |
| 02 | FunctionToMCP 工具转换 |
| 03 | Skills 加载和激活 |
| 04 | disabled_tools 配置 |
| 05 | EventBus 事件通信 |
| 06 | Agent.builder() 链式 API |
| 07 | MemoryScope 记忆作用域 |
| 08 | Sandbox 沙盒工具 |
| 09 | 多 Agent 共享 EventBus |
| 10 | 知识库 RAG 查询 |
| 11 | FractalStreamAPI 分形流式观测 |
| 12 | 父子 Agent 任务委派 |
| 13 | ParallelExecutor 并行执行 |
| 14 | 工作流管道与结果合成 |
| 15 | 记忆层级 L1-L4 与跨Session共享 |
| 16 | 拦截器：日志、性能监控、指标收集 |
| 17 | Memory+RAG+Knowledge 自动接线 |
| 18 | Context 动态预算与 TaskPhase 阶段策略 |
| 19 | LoomTracer 追踪 + LoomMetrics 指标 |
| 20 | Checkpoint 检查点与断点续跑 |
