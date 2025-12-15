#!/bin/bash
# Loom Agent v0.1.8 发布脚本
# 执行方式: chmod +x release_v0.1.8.sh && ./release_v0.1.8.sh

set -e  # 遇到错误立即退出

echo "========================================="
echo "Loom Agent v0.1.8 Release Script"
echo "========================================="
echo ""

# 1. 添加所有新文件和修改
echo "[1/6] Adding all changes..."
git add .

# 2. 提交更改
echo "[2/6] Committing changes..."
git commit -m "$(cat <<'EOF'
Release v0.1.8 - HierarchicalMemory + RAG Integration

### 🧠 Major Features

- **HierarchicalMemory System**: 4-tier memory architecture
  - Ephemeral → Working → Session → Long-term
  - Automatic promotion mechanism
  - Semantic retrieval with RAG
  - Tool memory management (Ephemeral)

- **Vector Store Infrastructure**:
  - InMemoryVectorStore (NumPy + FAISS)
  - OpenAIEmbedding (3 models support)
  - Graceful degradation

- **Context System Integration**:
  - RAG results auto-injected as ESSENTIAL (90) priority
  - Fixed critical "Lost in the Middle" issue
  - 3-tier Session History priority (70/50/30)

- **AgentExecutor Tool Memory**:
  - Complete Ephemeral Memory lifecycle
  - Automatic cleanup on all exit paths

- **Event System**:
  - 6 new RAG event types

### 📚 Documentation

- Complete RAG guide (1,100+ lines)
- ContextAssembler visualization doc
- 6 progressive examples (650+ lines)
- v0.1.9 improvement plan

### 🔧 Critical Fixes

- **RAG Priority Issue**: Elevated RAG to ESSENTIAL (90)
  - Ensures "golden position" (Primacy Effect)
  - Prevents Lost in the Middle phenomenon
  - Knowledge-First principle enforced

### 📊 Stats

- New code: ~1,500 lines
- Modified code: ~150 lines
- Documentation: ~1,750 lines
- Total: ~3,400 lines

### 🎯 Architecture Improvements

- Clear 4-tier memory hierarchy
- Transparent RAG pipeline
- Observable tool memory
- Modular component design
- Zero-magic, explicit fallbacks

### 🔗 Key Files

- loom/builtin/memory/hierarchical_memory.py (~650 lines)
- loom/builtin/vector_store/in_memory_vector_store.py (~350 lines)
- loom/builtin/embeddings/openai_embedding.py (~150 lines)
- loom/core/context_assembler.py (RAG priority fix)
- docs/CONTEXT_ASSEMBLER_FINAL_FORM.md
- docs/guides/advanced/hierarchical_memory_rag.md
- examples/hierarchical_memory_rag_example.py

100% backward compatible. All changes additive.
EOF
)"

# 3. 创建标签
echo "[3/6] Creating Git tag v0.1.8..."
git tag -a v0.1.8 -m "$(cat <<'EOF'
Loom Agent v0.1.8 - HierarchicalMemory + RAG Integration

Revolutionary hierarchical memory system with RAG semantic retrieval.

Key Features:
- 4-tier memory architecture (Ephemeral/Working/Session/Long-term)
- Vector search with InMemoryVectorStore (NumPy + FAISS)
- OpenAI Embedding integration
- Automatic memory promotion
- Tool memory (Ephemeral) management
- RAG results in "golden position" (Primacy Effect)
- 100% backward compatible

Documentation:
- docs/guides/advanced/hierarchical_memory_rag.md
- docs/CONTEXT_ASSEMBLER_FINAL_FORM.md
- examples/hierarchical_memory_rag_example.py

Release Notes: RELEASE_v0.1.8.md
CHANGELOG: CHANGELOG.md
EOF
)"

# 4. 推送更改到远程
echo "[4/6] Pushing changes to remote..."
git push origin main

# 5. 推送标签
echo "[5/6] Pushing tag to remote..."
git push origin v0.1.8

# 6. 显示发布信息
echo "[6/6] Release complete!"
echo ""
echo "========================================="
echo "✅ v0.1.8 Release Summary"
echo "========================================="
echo ""
echo "Tag: v0.1.8"
echo "Branch: main"
echo "Date: $(date +'%Y-%m-%d %H:%M:%S')"
echo ""
echo "Next Steps:"
echo "1. Create GitHub Release: https://github.com/kongusen/loom-agent/releases/new"
echo "   - Tag: v0.1.8"
echo "   - Title: Loom Agent v0.1.8 - HierarchicalMemory + RAG Integration"
echo "   - Description: Copy from RELEASE_v0.1.8.md"
echo ""
echo "2. Publish to PyPI:"
echo "   poetry build"
echo "   poetry publish"
echo ""
echo "3. Announce:"
echo "   - Update README badges"
echo "   - Post on social media"
echo "   - Notify community"
echo ""
echo "========================================="
echo "🎉 Congratulations!"
echo "========================================="
