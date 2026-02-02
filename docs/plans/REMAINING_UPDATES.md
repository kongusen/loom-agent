# 待更新清单（Phase 1–4 收尾与后续）

本文档汇总当前已规划阶段中尚未完成或可选的更新项，便于按需收尾。

---

## 一、Phase 3 收尾（可选）

| 项 | 说明 | 位置 |
|----|------|------|
| **迁移指南入口** | README 或 docs 首页增加「升级到 v0.5」/「迁移指南」链接，便于用户从首页跳转到迁移文档 | `README.md`、`README_EN.md` 或 `docs/README.md` / `docs/usage/` 目录说明 |
| **API 文档索引** | 若存在 docs 总目录或 usage 索引页，增加 `migration-v0.5.md` 的入口 | `docs/usage/` 下索引或 `docs/README.md` |

---

## 二、Phase 4 规划与决策

| 项 | 说明 |
|----|------|
| **Phase 4 计划** | 已创建：`docs/plans/2026-02-02-phase4-naming-camelcase.md`。目标：公开 API 统一为驼峰命名（camelCase）。 |
| **是否实施** | 需团队决策：**选项 A** 全量驼峰（破坏性）、**选项 B** 仅参数别名（兼容）、**选项 C** 不实施（保持 PEP 8 snake_case）。 |
| **若实施** | 按 Phase 4 计划执行 Task 1–5；完成后更新 CHANGELOG 与迁移指南（如 v0.5 → v0.6 命名变更）。 |
| **若不实施** | 在研究报告或计划中注明「命名规范维持 snake_case」，可跳过 Phase 4 进入 Phase 5/6。 |

---

## 三、文档与发布（按需）

| 项 | 说明 |
|----|------|
| **CHANGELOG** | 每个 Phase 或版本发布前，在 `CHANGELOG.md` 中补充对应变更（破坏性、新增 API、迁移说明）。 |
| **AGENTS.md / README 版本号** | 若发布 v0.5.0，将 AGENTS.md、README 等处的版本号从 v0.4.4 更新为 v0.5.0。 |
| **OPTIMIZATION_SKILLS_TOOLS.md** | 若尚未在文末增加「Phase 2 实施状态」小节，可补充 P0/P1/P2 勾选（可选）。 |

---

## 四、后续阶段

| 阶段 | 说明 | 计划/完成度文档 |
|------|------|------------------|
| **Phase 5** | LLM 自主决策优化（预算软限制、Router 弃用/移除、重要性去硬编码） | 计划：`2026-02-02-phase5-llm-autonomy.md`；完成度：`phase5-completion-checklist.md` |
| **Phase 6** | 测试与文档收尾（集成/端到端测试、覆盖率、API 文档、迁移指南、示例） | `docs/plans/2026-02-02-phase6-testing-docs.md` ✅ 已创建（含完成度标准） |

---

## 五、快速检查命令（可选）

```bash
# 检查是否还有 LoomApp / AgentConfig 残留（应为 0 或仅文档中的「旧代码」示例）
grep -r "LoomApp\|app\.create_agent\|from loom\.api\.models" --include="*.py" loom/ tests/ examples/

# 检查迁移指南是否被引用（可选：在 README 或 docs 中增加链接后再次检查）
grep -r "migration-v0\.5\|迁移.*v0\.5\|升级.*v0\.5" --include="*.md" README.md docs/
```

---

*最后更新：随 Phase 4 计划创建时一并整理。*
