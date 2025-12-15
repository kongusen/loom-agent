# 📚 文档体系结构说明

本文档说明了 Loom Agent 的文档组织结构和管理规范。

**最后更新**: 2024-12-15  
**版本**: v0.1.9

---

## 📂 文档目录结构

```
docs/
├── README.md                    # 📚 文档中心首页（主要入口）
├── INDEX.md                     # 📑 完整文档索引
├── DOCUMENTATION_STRUCTURE.md   # 📋 本文档（文档结构说明）
│
├── getting-started/             # 🚀 快速开始
│   ├── installation.md
│   ├── quickstart.md
│   ├── first-agent.md
│   ├── quick-reference.md
│   └── legacy-user-guide.md
│
├── guides/                      # 📖 使用指南
│   ├── agents/                  # Agent 相关
│   ├── patterns/                # 模式相关
│   ├── skills/                  # Skills 系统
│   ├── tools/                   # 工具系统
│   ├── integrations/            # 🔌 集成指南
│   │   ├── llm-support.md
│   │   └── CUSTOM_BASEURL.md
│   └── advanced/                # 🎓 高级主题
│       ├── hierarchical_memory_rag.md
│       ├── CONTEXT_ASSEMBLER_GUIDE.md
│       ├── CONTEXT_ASSEMBLER_FINAL_FORM.md
│       ├── CREW_ROUTING_GUIDE.md
│       ├── RECURSIVE_CONTROL_GUIDE.md
│       └── REACT_MODE_GUIDE.md
│
├── api/                         # 🔌 API 参考
│   ├── README.md
│   ├── agents.md
│   ├── patterns.md
│   ├── tools.md
│   └── core.md
│
├── architecture/                # 🏛️ 架构文档
│   ├── overview.md
│   ├── troubleshooting.md
│   ├── ARCHITECTURE_STATUS.md
│   ├── LLM_ARCHITECTURE_SUMMARY.md
│   ├── API_REFACTORING_SUMMARY.md
│   ├── CONTEXT_ASSEMBLER_SUMMARY.md
│   └── REFACTORING_SUMMARY.md
│
├── migration/                   # 🔄 迁移指南
│   ├── v0.1.5.md
│   └── v0.1.6.md
│
├── development/                 # 🛠️ 开发文档
│   ├── RELEASE_v0.1.8.md
│   └── RELEASE_CHECKLIST_v0.1.8.md
│
└── examples/                    # 💡 示例代码
    ├── basic/
    ├── advanced/
    ├── complete/
    └── integrations/
```

---

## 📋 文档分类说明

### 🚀 快速开始 (getting-started/)

**目标用户**: 新用户、初学者

**内容**: 
- 安装和配置
- 快速上手教程
- 基础概念介绍
- API 速查表

**原则**: 
- 简洁明了
- 循序渐进
- 包含完整示例代码

### 📖 使用指南 (guides/)

**目标用户**: 所有用户

**子分类**:

#### agents/
- Agent 相关的使用指南
- 不同 Agent 类型的说明

#### patterns/
- 模式使用指南（Crew、Pipeline 等）
- 模式组合和最佳实践

#### skills/
- Skills 系统完整指南
- 创建和使用 Skills

#### tools/
- 工具开发指南
- 工具集成方法

#### integrations/ 🔌
- **新增分类**: 集成相关指南
- LLM 提供商集成
- 自定义配置

#### advanced/ 🎓
- **新增分类**: 高级主题
- 递归控制模式
- 记忆系统深度使用
- Context Assembler
- Crew 路由
- ReAct 模式

### 🔌 API 参考 (api/)

**目标用户**: 开发者

**内容**: 
- 完整的 API 文档
- 参数说明
- 返回值说明
- 使用示例

### 🏛️ 架构文档 (architecture/)

**目标用户**: 高级用户、贡献者

**内容**:
- 架构设计说明
- 实现细节
- 故障排除
- 架构总结文档

### 🔄 迁移指南 (migration/)

**目标用户**: 升级用户

**内容**:
- 版本迁移说明
- 破坏性变更
- 升级步骤

### 🛠️ 开发文档 (development/)

**目标用户**: 维护者、贡献者

**内容**:
- 发布流程
- 开发规范
- 发布检查清单

### 💡 示例代码 (examples/)

**目标用户**: 所有用户

**内容**:
- 可运行的示例代码
- 最佳实践示例
- 集成示例

---

## 📝 文档命名规范

### 文件命名

- **小写字母 + 连字符**: `quick-start.md`, `first-agent.md`
- **描述性名称**: 文件名应清楚说明内容
- **避免缩写**: 除非是通用缩写（如 API、LLM）

### 目录命名

- **小写字母 + 连字符**: `getting-started/`, `api-reference/`
- **单数形式**: `guide/` 而非 `guides/`（但现有结构保持 `guides/`）

### 特殊文档

- **README.md**: 目录索引和导航
- **INDEX.md**: 完整文档列表
- **SUMMARY.md**: 总结性文档（架构总结等）

---

## 🔗 文档链接规范

### 相对路径

使用相对路径链接文档：

```markdown
- [快速开始](./getting-started/quickstart.md)
- [API 参考](./api/README.md)
```

### 绝对路径（从项目根目录）

在根目录文档中链接到 docs：

```markdown
- [文档中心](docs/README.md)
- [快速开始](docs/getting-started/quickstart.md)
```

### 跨目录链接

使用相对路径：

```markdown
- [架构概述](../architecture/overview.md)
- [示例代码](../examples/)
```

---

## 📊 文档维护规范

### 版本信息

每个文档应包含：

```markdown
**版本**: v0.1.9
**最后更新**: 2024-12-15
```

### 文档更新

1. **新功能**: 在相应分类下添加新文档
2. **重大变更**: 更新相关文档并添加迁移指南
3. **错误修复**: 更新故障排除文档
4. **API 变更**: 更新 API 参考文档

### 文档审查

- 确保所有链接有效
- 检查代码示例可运行
- 验证版本信息准确
- 保持格式一致

---

## 🎯 文档组织原则

### 1. 用户导向

文档按用户需求组织，而非代码结构：
- 新用户 → `getting-started/`
- 日常使用 → `guides/`
- 深度定制 → `guides/advanced/`
- 集成开发 → `guides/integrations/`

### 2. 渐进式披露

从简单到复杂：
- 快速开始 → 基础指南 → 高级主题
- 每个文档都有明确的难度级别

### 3. 易于查找

- 清晰的目录结构
- 完整的索引文档
- 交叉引用链接

### 4. 一致性

- 统一的格式风格
- 一致的命名规范
- 标准的代码示例格式

---

## 📈 文档统计

- **总文档数**: 40+ 个文档
- **快速开始**: 5 个文档
- **使用指南**: 15+ 个文档
- **API 参考**: 5 个文档
- **架构文档**: 7 个文档
- **迁移指南**: 2 个文档
- **开发文档**: 2 个文档

---

## 🔄 文档整理历史

### 2024-12-15 - 文档体系重构

**变更内容**:
1. ✅ 创建 `docs/guides/integrations/` 目录
2. ✅ 创建 `docs/guides/advanced/` 目录（已存在，补充文档）
3. ✅ 创建 `docs/development/` 目录
4. ✅ 移动根目录指南文档到 `docs/guides/advanced/`
5. ✅ 移动架构总结文档到 `docs/architecture/`
6. ✅ 移动开发文档到 `docs/development/`
7. ✅ 更新 `docs/README.md` 为完整文档索引
8. ✅ 创建 `docs/INDEX.md` 完整文档列表
9. ✅ 更新根目录 `README.md` 文档链接

**整理原则**:
- 根目录只保留核心文档（README、CHANGELOG、CONTRIBUTING、LICENSE）
- 所有使用指南统一放在 `docs/guides/`
- 架构和开发文档分类清晰
- 形成完整的文档导航体系

---

## 🔗 相关资源

- [文档中心](./README.md)
- [完整索引](./INDEX.md)
- [主 README](../README.md)
- [贡献指南](../CONTRIBUTING.md)

---

**文档维护者**: 请遵循本文档的规范，保持文档体系的一致性和可维护性。

