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
