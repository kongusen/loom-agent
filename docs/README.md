# 📚 Loom Agent 文档中心

**版本**: v0.1.9  
**最后更新**: 2024-12-15

欢迎来到 Loom Agent 文档中心！这里是所有文档的入口和导航中心。

---

## 🚀 快速导航

<table>
<tr>
<td width="50%">

### 🎯 新用户入门
- [安装指南](./getting-started/installation.md)
- [5分钟快速开始](./getting-started/quickstart.md)
- [创建第一个 Agent](./getting-started/first-agent.md)

</td>
<td width="50%">

### 📖 核心概念
- [Skills 系统](./guides/skills/overview.md)
- [Crew 多代理协作](./guides/patterns/crew.md)
- [Tools API](./api/tools.md)

</td>
</tr>
<tr>
<td>

### 🔌 API 参考
- [Agents API](./api/agents.md)
- [Patterns API](./api/patterns.md)
- [Tools API](./api/tools.md)
- [Core API](./api/core.md)

</td>
<td>

### 💡 示例代码
- [完整示例](./examples/complete/)
- [集成示例](./examples/integrations/)

</td>
</tr>
</table>

---

## 📂 完整文档结构

```
docs/
├── getting-started/          # 🚀 快速开始
│   ├── installation.md          # 安装指南
│   ├── quickstart.md            # 5分钟快速开始
│   └── first-agent.md           # 创建第一个 Agent
│
├── guides/                   # 📖 使用指南
│   ├── patterns/                # 模式
│   │   └── crew.md                  # Crew 多代理协作
│   │
│   ├── skills/                  # Skills 系统
│   │   ├── overview.md              # Skills 概述
│   │   ├── creating-skills.md       # 创建 Skills
│   │   ├── builtin-skills.md        # 内置 Skills
│   │   └── quick-reference.md        # Skills 快速参考
│   │
│   ├── integrations/            # 🔌 集成指南
│   │   ├── llm-support.md          # LLM 支持指南
│   │   └── CUSTOM_BASEURL.md        # 自定义 BaseURL
│   │
│   └── advanced/                # 🎓 高级主题
│       ├── hierarchical_memory_rag.md    # 分层记忆与 RAG
│       ├── CONTEXT_ASSEMBLER_GUIDE.md     # Context Assembler 指南
│       ├── CONTEXT_ASSEMBLER_FINAL_FORM.md # Context Assembler 最终形态
│       ├── CREW_ROUTING_GUIDE.md         # Crew 智能路由指南
│       ├── RECURSIVE_CONTROL_GUIDE.md    # 递归控制模式指南
│       └── REACT_MODE_GUIDE.md           # ReAct 模式指南
│
├── api/                      # 🔌 API 参考
│   ├── agents.md                 # Agents API
│   ├── patterns.md               # Patterns API
│   ├── tools.md                  # Tools API
│   ├── core.md                   # Core API
│   └── README.md                 # API 文档索引
│
├── architecture/            # 🏛️ 架构文档
│   └── overview.md              # 架构概述
│
├── migration/               # 🔄 迁移指南
│   ├── v0.1.5.md               # 迁移到 v0.1.5
│   └── v0.1.6.md               # 迁移到 v0.1.6
│
└── examples/               # 💡 示例代码
    ├── complete/               # 完整示例
    └── integrations/           # 集成示例
```

---

## 🎯 按需求查找

### 我想...

#### 🆕 开始使用 Loom
→ [安装指南](./getting-started/installation.md) → [5分钟快速开始](./getting-started/quickstart.md)

#### 📝 创建一个简单的 Agent
→ [创建第一个 Agent](./getting-started/first-agent.md)

#### 🔧 给 Agent 添加工具
→ [Tools API](./api/tools.md)

#### 🤝 实现多 Agent 协作
→ [Crew 协作指南](./guides/patterns/crew.md) → [Crew 智能路由](./guides/advanced/CREW_ROUTING_GUIDE.md)

#### 🧠 使用高级推理模式
→ [递归控制模式](./guides/advanced/RECURSIVE_CONTROL_GUIDE.md) → [ReAct 模式](./guides/advanced/REACT_MODE_GUIDE.md)

#### 📦 使用 Skills 系统
→ [Skills 概述](./guides/skills/overview.md) → [创建 Skills](./guides/skills/creating-skills.md)

#### 🔌 集成不同的 LLM
→ [LLM 支持指南](./guides/integrations/llm-support.md) → [自定义 BaseURL](./guides/integrations/CUSTOM_BASEURL.md)

#### 🧠 配置记忆系统
→ [分层记忆与 RAG](./guides/advanced/hierarchical_memory_rag.md) → [Context Assembler](./guides/advanced/CONTEXT_ASSEMBLER_GUIDE.md)

#### 📊 监控 Agent 执行
→ [架构概述](./architecture/overview.md)

#### 🏗️ 理解架构设计
→ [架构概述](./architecture/overview.md)

#### 🔍 查找特定 API
→ [完整 API 文档](./api/)

#### 💡 查看示例代码
→ [示例库](./examples/) → [完整示例](./examples/complete/)

#### 🐛 解决问题
→ [GitHub Issues](https://github.com/kongusen/loom-agent/issues)

#### 🛠️ 参与开发
→ [贡献指南](../CONTRIBUTING.md)

---

## 🌟 v0.1.9 亮点

Loom Agent v0.1.9 带来了架构清理和记忆系统优化：

### 架构改进
- ✅ **Message 架构修复**: 零数据丢失的序列化/反序列化
- ✅ **类型安全**: 100% 冻结数据类合规
- ✅ **工具结果结构化**: 保留类型信息的序列化

### 记忆系统优化
- 🧠 **智能晋升**: LLM 摘要 + 过滤 trivial 内容
- ⚡ **异步向量化**: 后台任务队列，10x 吞吐量提升
- 🔍 **调试模式**: Ephemeral Memory 完整状态导出

### 完整测试覆盖
- ✅ **65 个单元测试**: 全部通过
- ✅ **类型检查**: 100% 类型安全

详见 [CHANGELOG](../CHANGELOG.md)

---

## 📚 学习路径

### 初学者路径 (1-2 周)

```mermaid
graph LR
    A[安装] --> B[5分钟快速开始]
    B --> C[创建第一个 Agent]
    C --> D[添加工具]
    D --> E[多轮对话]
    E --> F[简单项目实践]
```

1. **第 1-2 天**: [安装](./getting-started/installation.md) + [快速开始](./getting-started/quickstart.md)
2. **第 3-4 天**: [创建 Agent](./getting-started/first-agent.md)
3. **第 5-7 天**: [Tools API](./api/tools.md) + [完整示例](./examples/complete/)
4. **第 8-10 天**: [Skills 系统](./guides/skills/overview.md) + 实践项目
5. **第 11-14 天**: [Crew 协作](./guides/patterns/crew.md) + 综合应用

### 进阶路径 (2-4 周)

1. **第 1 周**: [Crew 协作](./guides/patterns/crew.md) + [递归控制](./guides/advanced/RECURSIVE_CONTROL_GUIDE.md)
2. **第 2 周**: [分层记忆](./guides/advanced/hierarchical_memory_rag.md) + [Context Assembler](./guides/advanced/CONTEXT_ASSEMBLER_GUIDE.md)
3. **第 3 周**: [架构理解](./architecture/overview.md) + [高级示例](./examples/advanced/)
4. **第 4 周**: [集成示例](./examples/integrations/) + 生产环境部署

### 专家路径 (持续)

- 深入源码阅读
- 贡献开源项目
- 分享最佳实践
- 参与社区讨论

---

## 🔗 快速链接

### 核心资源
- [GitHub 仓库](https://github.com/kongusen/loom-agent)
- [PyPI 页面](https://pypi.org/project/loom-agent/)
- [变更日志](../CHANGELOG.md)
- [贡献指南](../CONTRIBUTING.md)

### 社区
- [GitHub Issues](https://github.com/kongusen/loom-agent/issues) - 报告问题
- [GitHub Discussions](https://github.com/kongusen/loom-agent/discussions) - 讨论交流
- [示例库](./examples/) - 分享你的示例

### 相关项目
- Skills 目录: [../skills/](../skills/)
- 示例代码: [../examples/](../examples/)

---

## 📖 文档约定

### 代码块格式

```python
# ✅ 完整可运行的示例
import asyncio
from loom import Message, agent
from examples.integrations.openai_llm import OpenAILLM

async def main():
    my_agent = agent(
        name="example",
        llm=OpenAILLM(api_key="...")
    )
    # ...

asyncio.run(main())
```

### 标注说明

- 🚀 新功能
- ⚡ 性能提升
- 🔧 改进
- 🐛 修复
- ⚠️ 注意事项
- 💡 提示
- 📝 示例

---

## 🤝 贡献文档

发现文档问题或想要改进？

1. **报告问题**: 在 [GitHub Issues](https://github.com/kongusen/loom-agent/issues) 提交
2. **提交修改**: Fork 项目，修改后提交 PR
3. **分享示例**: 在 [examples/](./examples/) 添加你的示例

详见 [贡献指南](../CONTRIBUTING.md)

---

## 📮 获取帮助

### 文档相关
- 查看 [API 参考](./api/)
- 浏览 [示例代码](./examples/)

### 技术支持
- 搜索 [GitHub Issues](https://github.com/kongusen/loom-agent/issues)
- 发起 [GitHub Discussion](https://github.com/kongusen/loom-agent/discussions)

---

## 🗺️ 文档路线图

### 即将推出
- [ ] 视频教程系列
- [ ] 交互式在线示例
- [ ] 更多语言版本
- [ ] 社区最佳实践集

### 计划中
- [ ] 性能优化指南
- [ ] 安全性最佳实践
- [ ] 生产环境部署指南
- [ ] 测试策略文档

---

**开始你的 Loom Agent 之旅！** 🎉

从 [安装指南](./getting-started/installation.md) 或 [5分钟快速开始](./getting-started/quickstart.md) 开始。
