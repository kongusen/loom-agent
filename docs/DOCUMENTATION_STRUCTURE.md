# Loom Agent Documentation Structure

## 文档组织原则

1. **用户文档** (`docs/user/`) - 面向使用Loom Agent的开发者
2. **开发者文档** (`docs/development/`) - 面向贡献代码的开发者
3. **根目录** - 只保留必要的核心文档

---

## 目录结构

```
loom-agent/
├── README.md                          # 项目介绍、快速开始
├── LICENSE                            # MIT许可证
├── CHANGELOG.md                       # 版本变更历史
├── docs/
│   ├── user/                         # 用户文档
│   │   ├── getting-started.md        # 快速开始指南
│   │   ├── user-guide.md             # 完整用户手册
│   │   ├── api-reference.md          # API参考文档
│   │   └── examples/                 # 示例代码
│   │       ├── basic-agent.md
│   │       ├── custom-tools.md
│   │       └── rag-patterns.md
│   └── development/                  # 开发者文档
│       ├── contributing.md           # 贡献指南
│       ├── development-setup.md      # 开发环境设置
│       ├── testing.md                # 测试指南
│       └── publishing.md             # 发布流程
└── releases/                         # 发布说明（历史记录）
    └── v0.0.1.md                     # v0.0.1发布说明
```

---

## 文档分类

### 用户文档 (docs/user/)

面向使用Loom Agent的开发者：

- **getting-started.md** - 5分钟快速上手
- **user-guide.md** - 完整使用教程
- **api-reference.md** - 详细API文档
- **examples/** - 实际代码示例

### 开发者文档 (docs/development/)

面向贡献代码的开发者：

- **contributing.md** - 如何贡献代码
- **development-setup.md** - 开发环境配置
- **testing.md** - 如何运行测试
- **publishing.md** - 如何发布新版本

### 根目录文档

- **README.md** - 项目概述、安装、基本示例
- **CHANGELOG.md** - 所有版本的变更记录
- **LICENSE** - MIT许可证

### 发布说明 (releases/)

每个版本的发布说明（用于GitHub Release）：

- **v0.0.1.md** - 首次发布
- **v0.1.0.md** - 未来版本
- ...

---

## 不上传到Git的文件

这些文件应该被.gitignore排除：

### 开发过程文档
- `specs/` - 规格说明（开发过程文件）
- `.claude/` - Claude Code配置
- `.codex/` - Codex配置
- `.specify/` - Specify配置

### 临时文档
- `*_STATUS.md` - 状态文档
- `*_REPORT.md` - 报告文档
- `DELIVERABLES.md` - 交付物清单
- `IMPLEMENTATION_*.md` - 实现记录
- `PROJECT_STATUS.md` - 项目状态
- `PRE_RELEASE_*.md` - 发布前检查
- `READY_TO_*.md` - 准备文档

### 构建产物
- `dist/` - 构建的包
- `*.egg-info/` - Python包信息
- `__pycache__/` - Python缓存
- `.pytest_cache/` - Pytest缓存

---

## 文档维护

### 添加新用户文档

1. 在 `docs/user/` 创建新文档
2. 更新 `docs/user/getting-started.md` 的目录
3. 在 `README.md` 添加链接（如果是重要文档）

### 添加新开发者文档

1. 在 `docs/development/` 创建新文档
2. 更新 `docs/development/contributing.md` 的链接
3. 确保文档清晰、有代码示例

### 发布新版本

1. 更新 `CHANGELOG.md`
2. 创建 `releases/vX.Y.Z.md`
3. 更新 `pyproject.toml` 版本号
4. 构建和发布到PyPI
5. 创建GitHub Release（使用releases/vX.Y.Z.md）

---

## 文档编写规范

### Markdown格式

- 使用标准Markdown格式
- 代码块指定语言（python, bash, json等）
- 使用相对路径链接其他文档

### 代码示例

- 提供完整可运行的示例
- 添加必要的注释
- 包含预期输出

### 链接

- 用户文档之间使用相对路径
- 链接到源代码使用GitHub链接
- 外部链接使用完整URL

---

## 迁移计划

从当前结构迁移到新结构：

1. **创建目录结构** ✓
2. **移动用户文档** → 下一步
3. **移动开发者文档** → 下一步
4. **更新.gitignore** → 下一步
5. **更新README.md链接** → 下一步
6. **删除临时文档** → 最后
