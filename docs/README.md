# Loom Agent 文档

> 基于认知动力学的事件驱动 Agent 框架

## 🚀 快速开始

**5 分钟上手：**

```python
from loom.weave import create_agent, run

agent = create_agent("助手", role="通用助手")
result = run(agent, "你好，请介绍一下自己")
```

👉 [完整快速开始指南](getting-started/quickstart.md)

---

## 📚 文档导航

本文档基于 [Diátaxis](https://diataxis.fr/) 框架组织，分为四个部分：

### 📖 [教程 (Tutorials)](tutorials/)
**学习导向** - 循序渐进地学习 loom-agent

- [创建你的第一个 Agent](tutorials/01-your-first-agent.md)
- [添加技能到 Agent](tutorials/02-adding-skills.md)
- [构建 Agent 团队](tutorials/03-building-teams.md)
- [使用 YAML 配置](tutorials/04-yaml-configuration.md)

### 🛠️ [操作指南 (How-to Guides)](guides/)
**问题导向** - 解决具体问题

- [Agents](guides/agents/) - 创建和配置 Agent
- [分形节点](guides/fractal-nodes.md) - 构建自组织 Agent 结构
- [记忆优化](guides/memory-optimization.md) - 记忆系统优化和最佳实践
- [双系统使用](guides/dual-system-usage.md) - System 1/2 配置指南
- [LLM 流式调用](guides/llm-streaming.md) - 处理流式工具调用
- [结构化输出](guides/structured-output.md) - Claude/Gemini JSON 输出指南
- [Skills](guides/skills/) - 开发自定义技能
- [Configuration](guides/configuration/) - 配置和部署
- [Deployment](guides/deployment/) - 生产环境部署

### 💡 [概念 (Concepts)](concepts/)
**理解导向** - 深入理解核心概念

- [架构设计](concepts/architecture.md)
- [认知动力学](concepts/cognitive-dynamics.md)
- [设计哲学](concepts/design-philosophy.md)
- [记忆系统](concepts/memory_system.md)
- [双系统思维](concepts/dual-system.md)
- [Agent 节点](concepts/agent-node.md)
- [协议设计](concepts/protocol.md)

### 📚 [API 参考 (Reference)](reference/)
**信息导向** - 完整的 API 文档

- [loom.weave API](reference/api/weave.md)
- [loom.stdlib API](reference/api/stdlib.md)
- [配置参考](reference/api/config.md)
- [示例代码](reference/examples/)

---

## 🎯 根据你的需求选择

**我是新手，想快速上手：**
→ 从 [快速开始](getting-started/quickstart.md) 开始

**我想系统学习：**
→ 按顺序阅读 [教程](tutorials/)

**我遇到了具体问题：**
→ 查看 [操作指南](guides/)

**我想深入理解原理：**
→ 阅读 [概念文档](concepts/)

**我需要查 API：**
→ 查阅 [API 参考](reference/)

---

## 🔬 技术文档

深入的技术设计和实现文档：

- [BGE Embedding 优化](bge_embedding_optimization.md) - ONNX + Int8 量化优化
- [L4 压缩设计](l4_compression_design.md) - 知识库自动压缩机制
- [投影策略设计](projection_strategy_design.md) - 上下文投影完整方案
- [投影优化分析](projection_optimization_analysis.md) - 投影系统分析
- [通用框架投影](projection_for_general_framework.md) - 通用框架投影建议
