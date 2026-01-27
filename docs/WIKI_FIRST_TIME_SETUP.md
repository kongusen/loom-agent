# GitHub Wiki 首次设置指南

## 问题

当 GitHub 仓库的 Wiki 从未使用过时，`.wiki` 仓库不存在，导致自动化同步失败。

错误信息：
```
fatal: repository 'https://github.com/kongusen/loom-agent.wiki/' not found
```

## 解决方案：手动初始化 Wiki

### 步骤 1：访问 Wiki 页面

在浏览器中打开：
https://github.com/kongusen/loom-agent/wiki

### 步骤 2：创建第一个页面

1. 点击右上角的 **"Add a new page"** 或 **"Create first page"** 按钮
2. 页面标题输入：`Home`
3. 内容输入（可以是简单的介绍）：

```markdown
# Loom Agent Framework

**The Controlled Fractal Agent Framework**

Documentation will be automatically synced from the main repository.

For full documentation, see: https://github.com/kongusen/loom-agent
```

4. 点击 **"Save page"** 按钮

### 步骤 3：验证 Wiki 仓库创建成功

访问：
https://github.com/kongusen/loom-agent/wiki/Home

如果看到刚才创建的页面，说明 Wiki 仓库已成功初始化！

### 步骤 4：重新触发同步

有两种方式重新触发 Wiki 同步：

#### 方式 A：使用 GitHub Actions（推荐）

1. 访问：https://github.com/kongusen/loom-agent/actions
2. 点击左侧的 **"Sync Wiki"** workflow
3. 点击右侧的 **"Run workflow"** 按钮
4. 选择分支 `main`
5. 点击 **"Run workflow"** 确认

#### 方式 B：推送空提交

```bash
git commit --allow-empty -m "chore: trigger wiki sync"
git push
```

### 步骤 5：验证同步结果

访问 GitHub Wiki：
https://github.com/kongusen/loom-agent/wiki

应该能看到所有 26 个自动同步的页面：
- Home
- Axiomatic-System
- Fractal-Architecture
- Metabolic-Memory
- Event-Bus
- Four-Paradigms
- ...（等）

## 后续更新

一旦 Wiki 仓库初始化完成，后续的更新会自动同步：

### 自动触发

- 推送到 `main` 分支且修改了 `wiki/` 目录
- 推送新的版本标签（如 `v0.4.3`）
- 手动触发 workflow

### 手动触发

1. 访问：https://github.com/kongusen/loom-agent/actions/workflows/sync-wiki.yml
2. 点击 **"Run workflow"** 按钮

## 故障排除

### 问题 1：同步后看不到新页面

**原因**：可能 GitHub 缓存还没刷新

**解决**：等待 1-2 分钟，然后刷新页面

### 问题 2：某些页面链接不工作

**原因**：文件名大小写或路径不正确

**解决**：
- 检查 `wiki/` 目录中的文件名
- 确保使用 Pascal-Case 命名（如 `Axiomatic-System.md`）
- 检查链接格式是否正确

### 问题 3：workflow 运行但 Wiki 没有更新

**原因**：可能是因为没有检测到更改

**解决**：
```bash
# 检查 workflow 日志
# https://github.com/kongusen/loom-agent/actions/workflows/sync-wiki.yml

# 如果显示 "没有检测到更改"，说明文件内容相同
# 这是正常的，不需要处理
```

## 相关文档

- [Wiki 设置指南](WIKI_SETUP.md)
- [Deepwiki 迁移总结](DEEPWIKY_MIGRATION.md)

## 需要帮助？

如果遇到其他问题：
1. 检查 GitHub Actions 日志
2. 查看 Wiki 文件是否正确
3. 确认 workflow 权限设置正确
