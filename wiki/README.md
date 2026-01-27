# Loom Agent Wiki 文档

这是 Loom Agent 框架的 Deepwiki 风格文档，基于 v0.4.3 版本。

## 📁 文档结构

```
wiki/
├── Home.md                      # 首页（框架概览）
├── Getting-Started.md            # 快速开始指南
│
├── concepts/                     # 核心概念文档
│   ├── Axiomatic-System.md      # 公理系统
│   ├── Protocol-First.md        # 协议优先
│   ├── Event-Sovereignty.md     # 事件主权
│   ├── Fractal-Recursion.md     # 分形递归
│   ├── Fractal-Architecture.md  # 分形架构
│   ├── Fractal-Node.md          # 分形节点
│   ├── Composite-Node.md        # 组合节点
│   ├── Execution-Strategy.md    # 执行策略
│   ├── Metabolic-Memory.md      # 代谢记忆
│   ├── Memory-Layers.md         # 记忆分层
│   ├── Memory-Scope.md          # 记忆作用域
│   ├── Context-Management.md    # 上下文管理
│   ├── Event-Bus.md             # 事件总线
│   ├── CloudEvents.md           # CloudEvents 标准
│   ├── Event-Interceptor.md     # 事件拦截器
│   ├── Observability.md         # 可观测性
│   ├── Four-Paradigms.md        # 四范式工作
│   ├── Autonomous-Capabilities.md # 自主能力
│   ├── Tool-System.md           # 工具系统
│   └── Skills.md                # Skills 系统
│
├── api/                          # API 文档
│   ├── API-Agent.md             # Agent API
│   └── API-Memory.md            # Memory API
│
├── examples/                     # 示例代码
│   ├── Quick-Start.md           # 快速开始示例
│   └── Research-Team.md         # 研究小组示例
│
└── design/                       # 设计文档（待添加）
    ├── Axiomatic-System.md
    ├── Fractal-Architecture.md
    └── Memory-System.md
```

## 🚀 设置 GitHub Wiki

### 方式 1: 使用脚本（推荐）

```bash
./scripts/setup-wiki.sh
```

### 方式 2: 手动设置

```bash
# 1. 克隆 Wiki 仓库
git clone https://github.com/kongusen/loom-agent.wiki.git wiki_repo

# 2. 复制文件
cp -r wiki/* wiki_repo/

# 3. 提交并推送
cd wiki_repo
git add .
git commit -m "docs: 添加 Deepwiki 风格文档"
git push
```

## 📖 文档特色

### Deepwiki 风格

- **知识图谱化**: 每个概念页面都有双向链接
- **分层导航**: 概念 → API → 示例，从浅到深
- **概念映射**: 以概念为中心组织内容
- **上下文感知**: 相关概念、参见、反向链接

### 页面结构

每个概念页面包含：

```markdown
# 概念名称

## 定义
一句话定义

## 核心思想
详细解释

## 关键特性
- 特性 1
- 特性 2

## 相关概念
- → [概念A](Concept-A)
- → [概念B](Concept-B)

## 参见
- 📖 [设计文档](design/xxx)
- 🔧 [API 指南](api/xxx)
- 💡 [示例代码](examples/xxx)

## 代码位置
- `loom/path/to/module.py`

## 反向链接
被引用于: [其他概念](Other-Concept)
```

## 🔄 更新文档

### 修改现有页面

```bash
# 1. 编辑文件
vim wiki/Axiomatic-System.md

# 2. 推送到 GitHub Wiki
./scripts/setup-wiki.sh
```

### 添加新页面

```bash
# 1. 创建新页面
vim wiki/New-Concept.md

# 2. 在相关页面添加链接
vim wiki/Related-Concept.md

# 3. 推送
./scripts/setup-wiki.sh
```

## 📚 文档原则

### YAGNI (You Aren't Gonna Need It)

- 只编写必要的文档
- 避免过度解释
- 代码自解释优于文档

### 一致性

- 统一的命名约定
- 统一的页面结构
- 统一的链接格式

### 准确性

- 文档与代码同步
- 基于 v0.4.3 版本
- 定期审查和更新

## 🔗 外部资源

- **GitHub 仓库**: https://github.com/kongusen/loom-agent
- **PyPI 包**: https://pypi.org/project/loom-agent
- **DeepWiki**: https://deepwiki.com/kongusen/loom-agent

## 📝 版本

- **当前版本**: v0.4.3
- **最后更新**: 2025-01-27
