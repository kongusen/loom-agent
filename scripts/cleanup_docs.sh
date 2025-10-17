#!/bin/bash
# 清理临时文档和构建产物

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}📁 Loom Agent - 文档清理脚本${NC}"
echo ""

# 确认
echo "此脚本将删除以下文件："
echo ""
echo "临时文档："
echo "  - *_STATUS.md *_REPORT.md *_COMPLETE.md *_FEATURES.md"
echo "  - DELIVERABLES.md PROJECT_STATUS.md"
echo "  - PRE_RELEASE_*.md READY_TO_*.md RELEASE_STEPS_*.md"
echo "  - QUICK_PUBLISH.md DOCUMENTATION_INDEX.md V4_FINAL_SUMMARY.md"
echo ""
echo "已迁移的原始文档："
echo "  - USER_GUIDE.md API_REFERENCE.md PYPI_PUBLISHING_GUIDE.md RELEASE_v0.0.1.md"
echo ""
echo "构建产物："
echo "  - dist/ build/ *.egg-info/"
echo ""

read -p "确认删除这些文件？(y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 已取消${NC}"
    exit 0
fi

echo ""
echo -e "${GREEN}🗑️  开始清理...${NC}"
echo ""

# 删除临时状态和报告文档
echo "清理临时文档..."
rm -f *_STATUS.md *_REPORT.md *_COMPLETE.md *_FEATURES.md 2>/dev/null || true
rm -f DELIVERABLES.md PROJECT_STATUS.md 2>/dev/null || true
rm -f PRE_RELEASE_*.md READY_TO_*.md RELEASE_STEPS_*.md 2>/dev/null || true
rm -f QUICK_PUBLISH.md DOCUMENTATION_INDEX.md V4_FINAL_SUMMARY.md 2>/dev/null || true

# 删除根目录中已迁移的文档
echo "删除已迁移的原始文档..."
rm -f USER_GUIDE.md API_REFERENCE.md PYPI_PUBLISHING_GUIDE.md RELEASE_v0.0.1.md 2>/dev/null || true

# 清理构建产物
echo "清理构建产物..."
rm -rf dist/ build/ *.egg-info/ 2>/dev/null || true

# 清理Python缓存
echo "清理Python缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# 清理测试虚拟环境
echo "清理测试环境..."
rm -rf test-* testpypi-* verify-* 2>/dev/null || true

echo ""
echo -e "${GREEN}✅ 清理完成！${NC}"
echo ""
echo "保留的文档："
echo "  ✓ README.md"
echo "  ✓ CHANGELOG.md"
echo "  ✓ LICENSE"
echo "  ✓ docs/ (用户和开发者文档)"
echo "  ✓ releases/ (发布说明)"
echo ""
echo "下一步："
echo "  1. 查看 docs/ 目录确认文档组织"
echo "  2. 运行 git status 查看变更"
echo "  3. 提交文档重组: git add docs/ releases/ .gitignore README.md"
echo ""
