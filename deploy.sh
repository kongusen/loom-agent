#!/bin/bash

# Lexicon Agent Framework 部署脚本
# 用于推送代码到远程仓库

set -e

echo "🚀 Lexicon Agent Framework 开源部署"
echo "=================================="

# 检查是否在正确的目录
if [ ! -f "pyproject.toml" ] || [ ! -d "lexicon_agent" ]; then
    echo "❌ 错误: 请在项目根目录运行此脚本"
    exit 1
fi

# 检查Git状态
echo "📋 检查Git状态..."
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  警告: 工作目录有未提交的更改"
    git status --short
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查远程仓库
if ! git remote get-url origin > /dev/null 2>&1; then
    echo "❌ 错误: 未配置远程仓库"
    echo "请先创建GitHub仓库并添加远程地址:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/lexicon-agent.git"
    exit 1
fi

# 获取远程仓库URL
REMOTE_URL=$(git remote get-url origin)
echo "📡 远程仓库: $REMOTE_URL"

# 推送到远程仓库
echo "📤 推送代码到远程仓库..."
git push -u origin main

echo "✅ 部署完成!"
echo ""
echo "🎉 Lexicon Agent Framework 已成功开源发布!"
echo "📖 仓库地址: $REMOTE_URL"
echo ""
echo "接下来您可以:"
echo "- 📝 完善仓库描述和标签"
echo "- 🌟 邀请其他开发者加入"
echo "- 📢 在社区分享您的项目"
echo "- 🐛 创建第一个Issue或讨论"
echo ""
echo "感谢您选择开源! 🙏"