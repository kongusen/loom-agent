# Loom Framework - 基于公理系统的架构

> **版本**: v0.4.0-alpha
> **理论基础**: 六大公理系统

## 架构设计理念

本框架完全基于[公理系统文档](../axiomatic-framework.md)设计，每个顶层目录对应一个公理。

## 目录结构（公理驱动）

```
loom/
├── protocol/        # A1: 统一接口公理 - 所有节点实现相同协议
├── events/          # A2: 事件主权公理 - 所有通信都是事件
├── fractal/         # A3: 分形自相似公理 - 递归组合能力
├── memory/          # A4: 记忆层次公理 - L1→L2→L3→L4层次
├── orchestration/   # A5: 认知调度公理 - 编排交互涌现认知
│                    # A6: 四范式工作公理 - 已集成到Agent基础能力中
├── runtime/         # 运行时支持（事件总线、拦截器等）
├── providers/       # 外部提供者（LLM、向量数据库等）
├── tools/           # 工具系统（MCP协议支持等）
└── api/             # 统一对外API
```

## 依赖关系

```
protocol (A1) - 基础协议定义
    ↓
events (A2) - 事件系统
    ↓
runtime - 运行时支持
    ↓
├─ fractal (A3) - 分形组合
├─ memory (A4) - 记忆系统
├─ orchestration (A5) - 编排调度（包含A6四范式能力）
└─ tools - 工具系统
    ↓
api - 统一对外接口
```

## 设计原则

1. **公理驱动**：每个模块严格遵循对应的公理
2. **层次清晰**：明确的依赖关系，避免循环依赖
3. **职责单一**：每个模块只负责一个公理相关的功能
4. **易于理解**：从结构就能理解框架的核心理念

## 实现顺序

按照依赖关系，实现顺序为：
1. protocol (A1) - 定义NodeProtocol等核心协议
2. events (A2) - 实现CloudEvent和事件总线
3. runtime - 实现运行时支持
4. fractal/memory/orchestration/tools - 并行实现各层
5. api - 最后实现统一API

**注**: 公理A6（四范式工作公理）已集成到orchestration/agent.py中的Agent类，作为基础能力提供：
- `Agent.reflect()` - 反思能力
- `Agent.use_tool()` - 工具使用能力
- `Agent.plan()` - 规划能力
- `Agent.delegate()` - 多智能体协作能力

## 与旧版本的区别

| 方面 | 旧版本 | 新版本 |
|------|--------|--------|
| 组织原则 | 功能混杂 | 公理驱动 |
| 目录结构 | core/kernel不清晰 | 六大公理对应 |
| API组织 | 分散导入 | 统一入口 |
| 理论基础 | 隐式 | 显式（公理系统） |
