# GitHub Wiki 设置指南

本文档说明如何将本地 Wiki 文档推送到 GitHub Wiki。

## 📋 前提条件

- GitHub 仓库访问权限
- Git 配置正确

## 🚀 快速开始

### 方式 1: 使用手动命令

```bash
# 1. 克隆 GitHub Wiki 仓库
git clone https://github.com/kongusen/loom-agent.wiki.git wiki_repo

# 2. 复制 Wiki 文件
cp -r wiki/* wiki_repo/

# 3. 进入 Wiki 目录
cd wiki_repo

# 4. 查看状态
git status

# 5. 提交更改
git add .
git commit -m "docs: 添加 Deepwiki 风格文档"

# 6. 推送到 GitHub
git push

# 7. 清理（可选）
cd ..
rm -rf wiki_repo
```

### 方式 2: 使用脚本（如果 scripts 不在 .gitignore 中）

```bash
# 创建设置脚本
cat > setup-wiki.sh << 'EOF'
#!/bin/bash
REPO="kongusen/loom-agent"
WIKI_URL="https://github.com/${REPO}.wiki.git"

# 克隆 Wiki 仓库
if [ -d "wiki_repo" ]; then
    cd wiki_repo
    git pull
    cd ..
else
    git clone "${WIKI_URL}" wiki_repo
fi

# 复制文件
cp -r wiki/* wiki_repo/

# 提交并推送
cd wiki_repo
git add .
git commit -m "docs: 更新 Wiki 文档" || echo "没有新更改"
git push
EOF

# 添加执行权限
chmod +x setup-wiki.sh

# 运行脚本
./setup-wiki.sh
```

## 📁 Wiki 文件结构

```
wiki/
├── Home.md                    # 首页（重命名为 Home.md）
├── Getting-Started.md          # 快速开始
├── API-Agent.md               # Agent API
├── API-Memory.md              # Memory API
├── Axiomatic-System.md        # 公理系统
├── Fractal-Architecture.md    # 分形架构
├── Metabolic-Memory.md        # 代谢记忆
├── Event-Bus.md               # 事件总线
├── Four-Paradigms.md          # 四范式工作
├── examples/
│   ├── Quick-Start.md
│   └── Research-Team.md
└── ... (更多概念页面)
```

## 🔄 更新 Wiki

### 修改现有页面

```bash
# 1. 编辑本地文件
vim wiki/Axiomatic-System.md

# 2. 推送到 GitHub Wiki
git clone https://github.com/kongusen/loom-agent.wiki.git wiki_repo
cp wiki/Axiomatic-System.md wiki_repo/
cd wiki_repo
git add Axiomatic-System.md
git commit -m "docs: 更新公理系统文档"
git push
```

### 添加新页面

```bash
# 1. 创建新页面
vim wiki/New-Concept.md

# 2. 在相关页面添加链接
vim wiki/Related-Concept.md

# 3. 推送
cp wiki/New-Concept.md wiki_repo/
cp wiki/Related-Concept.md wiki_repo/
cd wiki_repo
git add .
git commit -m "docs: 添加新概念文档"
git push
```

## 🌐 访问 Wiki

推送成功后，访问：
- **GitHub Wiki**: https://github.com/kongusen/loom-agent/wiki

## 📝 注意事项

### GitHub Wiki 的特性

1. **首页**: `Home.md` 会自动成为 Wiki 首页
2. **命名**: 使用 Pascal-Case 命名（如 `Axiomatic-System`）
3. **链接**: GitHub Wiki 支持 Markdown 链接格式
4. **历史**: 完整的 Git 历史记录
5. **协作**: 支持多人协作编辑

### 链接格式

```markdown
<!-- 内部链接 -->
[公理系统](Axiomatic-System)

<!-- 外部链接 -->
[GitHub](https://github.com/kongusen/loom-agent)

<!-- 带标题的链接 -->
[公理系统](Axiomatic-System#五条公理)
```

### 文件命名约定

- 概念页面: `Pascal-Case.md` (如 `Fractal-Architecture.md`)
- API 文档: `API-*.md` (如 `API-Agent.md`)
- 示例代码: `examples/*.md` (如 `examples/Quick-Start.md`)
- 设计文档: `design/*.md` (如 `design/Axiomatic-System.md`)

## ✅ 验证

推送后，检查以下内容：

1. ✅ 所有页面都正确显示
2. ✅ 内部链接正常工作
3. ✅ 代码块正确格式化
4. ✅ 表格正确渲染
5. ✅ 目录结构清晰

## 🛠️ 故障排除

### 问题 1: Wiki 仓库不存在

**解决方案**:
1. 访问 https://github.com/kongusen/loom-agent/wiki
2. 点击 "Add a new page"
3. 这会自动创建 Wiki 仓库

### 问题 2: 推送失败

**解决方案**:
```bash
# 检查远程 URL
cd wiki_repo
git remote -v

# 如果 URL 不正确，更新它
git remote set-url origin https://github.com/kongusen/loom-agent.wiki.git

# 重新推送
git push
```

### 问题 3: 链接不工作

**解决方案**:
- 确保文件名大小写正确
- 检查文件是否在 Wiki 仓库中
- 使用相对路径，不要使用绝对路径

## 📚 相关资源

- [GitHub Wiki 官方文档](https://docs.github.com/en/wiki)
- [Markdown 基础语法](https://www.markdownguide.org/basic-syntax/)
- [Loom DeepWiki](https://deepwiki.com/kongusen/loom-agent)

## 🎯 下一步

- 添加更多示例代码
- 补充设计文档
- 添加故障排除指南
- 翻译成英文版本
