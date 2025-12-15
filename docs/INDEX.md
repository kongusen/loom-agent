# 📑 Loom Agent 文档索引

本文档提供了所有文档的完整列表，方便快速查找。

**最后更新**: 2024-12-15  
**版本**: v0.1.9

---

## 📂 文档分类索引

### 🚀 快速开始 (getting-started/)

| 文档 | 描述 | 链接 |
|------|------|------|
| 安装指南 | 安装和配置 Loom Agent | [installation.md](./getting-started/installation.md) |
| 5分钟快速开始 | 快速上手指南 | [quickstart.md](./getting-started/quickstart.md) |
| 创建第一个 Agent | 创建你的第一个 Agent | [first-agent.md](./getting-started/first-agent.md) |

### 📖 使用指南 (guides/)

#### Patterns (guides/patterns/)

| 文档 | 描述 | 链接 |
|------|------|------|
| Crew 多代理协作 | Crew 模式使用指南 | [crew.md](./guides/patterns/crew.md) |

#### Skills (guides/skills/)

| 文档 | 描述 | 链接 |
|------|------|------|
| Skills 概述 | Skills 系统介绍 | [overview.md](./guides/skills/overview.md) |
| 创建 Skills | 如何创建自定义 Skills | [creating-skills.md](./guides/skills/creating-skills.md) |
| 内置 Skills | 内置 Skills 列表 | [builtin-skills.md](./guides/skills/builtin-skills.md) |
| Skills 快速参考 | Skills API 速查表 | [quick-reference.md](./guides/skills/quick-reference.md) |

#### Integrations (guides/integrations/)

| 文档 | 描述 | 链接 |
|------|------|------|
| LLM 支持指南 | 主流 LLM 集成指南 | [llm-support.md](./guides/integrations/llm-support.md) |
| 自定义 BaseURL | 自定义 API BaseURL 配置 | [CUSTOM_BASEURL.md](./guides/integrations/CUSTOM_BASEURL.md) |

#### Advanced (guides/advanced/)

| 文档 | 描述 | 链接 |
|------|------|------|
| 分层记忆与 RAG | HierarchicalMemory 和 RAG 使用指南 | [hierarchical_memory_rag.md](./guides/advanced/hierarchical_memory_rag.md) |
| Context Assembler 指南 | Context Assembler 使用指南 | [CONTEXT_ASSEMBLER_GUIDE.md](./guides/advanced/CONTEXT_ASSEMBLER_GUIDE.md) |
| Context Assembler 最终形态 | Context Assembler 架构详解 | [CONTEXT_ASSEMBLER_FINAL_FORM.md](./guides/advanced/CONTEXT_ASSEMBLER_FINAL_FORM.md) |
| Crew 智能路由指南 | Crew 路由模式使用指南 | [CREW_ROUTING_GUIDE.md](./guides/advanced/CREW_ROUTING_GUIDE.md) |
| 递归控制模式指南 | ReflectionLoop、TreeOfThoughts 等 | [RECURSIVE_CONTROL_GUIDE.md](./guides/advanced/RECURSIVE_CONTROL_GUIDE.md) |
| ReAct 模式指南 | ReAct 推理模式使用指南 | [REACT_MODE_GUIDE.md](./guides/advanced/REACT_MODE_GUIDE.md) |

### 🔌 API 参考 (api/)

| 文档 | 描述 | 链接 |
|------|------|------|
| API 文档索引 | API 文档总览 | [README.md](./api/README.md) |
| Agents API | Agent 相关 API | [agents.md](./api/agents.md) |
| Patterns API | 模式相关 API | [patterns.md](./api/patterns.md) |
| Tools API | 工具相关 API | [tools.md](./api/tools.md) |
| Core API | 核心 API | [core.md](./api/core.md) |

### 🏛️ 架构文档 (architecture/)

| 文档 | 描述 | 链接 |
|------|------|------|
| 架构概述 | 整体架构设计 | [overview.md](./architecture/overview.md) |

### 🔄 迁移指南 (migration/)

| 文档 | 描述 | 链接 |
|------|------|------|
| v0.1.5 迁移指南 | 迁移到 v0.1.5 | [v0.1.5.md](./migration/v0.1.5.md) |
| v0.1.6 迁移指南 | 迁移到 v0.1.6 | [v0.1.6.md](./migration/v0.1.6.md) |

### 🛠️ 开发文档

开发相关文档请参考根目录的 CHANGELOG.md 和 CONTRIBUTING.md。

### 💡 示例代码 (examples/)

| 目录 | 描述 | 链接 |
|------|------|------|
| 完整示例 | 完整项目示例 | [complete/](./examples/complete/) |
| 集成示例 | 第三方集成示例 | [integrations/](./examples/integrations/) |

---

## 🔍 按主题查找

### 入门学习
1. [安装指南](./getting-started/installation.md)
2. [5分钟快速开始](./getting-started/quickstart.md)
3. [创建第一个 Agent](./getting-started/first-agent.md)

### 核心功能
- **Skills 系统**: [Skills 概述](./guides/skills/overview.md) → [创建 Skills](./guides/skills/creating-skills.md)
- **Crew 协作**: [Crew 指南](./guides/patterns/crew.md) → [Crew 路由](./guides/advanced/CREW_ROUTING_GUIDE.md)
- **工具系统**: [Tools API](./api/tools.md)

### 高级功能
- **递归控制**: [递归控制指南](./guides/advanced/RECURSIVE_CONTROL_GUIDE.md)
- **ReAct 模式**: [ReAct 模式指南](./guides/advanced/REACT_MODE_GUIDE.md)
- **记忆系统**: [分层记忆与 RAG](./guides/advanced/hierarchical_memory_rag.md)
- **上下文组装**: [Context Assembler 指南](./guides/advanced/CONTEXT_ASSEMBLER_GUIDE.md)

### 集成与配置
- **LLM 集成**: [LLM 支持指南](./guides/integrations/llm-support.md)
- **自定义配置**: [自定义 BaseURL](./guides/integrations/CUSTOM_BASEURL.md)

### 架构与开发
- **架构理解**: [架构概述](./architecture/overview.md)
- **开发指南**: [贡献指南](../CONTRIBUTING.md)

---

## 📊 文档统计

- **总文档数**: 25+ 个文档
- **快速开始**: 3 个文档
- **使用指南**: 12+ 个文档
- **API 参考**: 5 个文档
- **架构文档**: 1 个文档
- **迁移指南**: 2 个文档

---

## 🔗 相关资源

- [主 README](../README.md)
- [变更日志](../CHANGELOG.md)
- [贡献指南](../CONTRIBUTING.md)
- [GitHub 仓库](https://github.com/kongusen/loom-agent)

---

**需要帮助？** 查看 [文档中心](./README.md)

