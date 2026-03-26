# Loom v0.7.0 实施时间表

## 总览

**目标版本**: v0.7.0
**类型**: Breaking Change Release
**预计工作量**: 5-7 天（单人全职）
**风险等级**: 高（完全重构核心架构）

---

## 实施顺序（严格按序）

### Day 1-2: Phase 1 - 公理一完整接入
**优先级**: P0（核心依赖）
**工作量**: 2 天

#### 任务清单
1. 实现 `_update_all_partitions()` - 2h
2. 实现 `_build_working_state()` - 1h
3. 实现 `_context_to_messages()` - 1h
4. 重写 `_build_messages()` - 2h
5. 修改 `run()` 集成 working 更新 - 1h
6. 修改 `_execute_tool()` 更新 working - 1h
7. 编写单元测试（10+ 测试） - 3h
8. 删除 ContextOrchestrator 相关代码 - 2h
9. 修复所有导入错误 - 2h

**验收标准**:
- ✅ 所有 5 个分区在 prompt 中可见
- ✅ working 分区实时更新
- ✅ heartbeat/compress 自动触发
- ✅ 无 ContextOrchestrator 残留

---

### Day 3: Phase 2 - 公理二约束前置
**优先级**: P1（安全保障）
**工作量**: 1 天

#### 任务清单
1. 修改 `ToolRegistry.execute()` 集成 validator - 1h
2. 修改 `Agent._execute_tool()` 传递 validator - 0.5h
3. SceneManager 添加回调机制 - 1h
4. Agent 注册场景切换回调 - 0.5h
5. 增强 ConstraintValidator 动态约束 - 1.5h
6. ResourceGuard 集成到主循环 - 1h
7. 编写约束测试（5+ 测试） - 2h

**验收标准**:
- ✅ 所有工具调用经过约束验证
- ✅ 场景切换自动更新 C_system
- ✅ ResourceGuard 阻止超预算执行

---

### Day 4: Phase 3 - 公理三门控全覆盖
**优先级**: P1（性能优化）
**工作量**: 1 天

#### 任务清单
1. 实现 `_emit_with_gain()` - 1h
2. 替换所有 `emit()` 调用 - 1.5h
3. 实现 `_filter_tool_output()` - 1h
4. 实现 StreamGatingBuffer - 2h
5. 集成流式门控到 `run()` - 1.5h
6. 添加 GatingConfig - 0.5h
7. 编写门控测试（5+ 测试） - 2h

**验收标准**:
- ✅ 所有事件经过 ΔH 门控
- ✅ 工具输出冗余被过滤
- ✅ 流式输出累积门控生效

---

### Day 5-6: Phase 4 - 公理四进化闭环
**优先级**: P1（核心功能）
**工作量**: 2 天

#### 任务清单
1. 创建 evolution_handlers.py - 0.5h
2. 实现 write_memory_handler - 1h
3. 实现 activate_skill_handler - 1h
4. 实现 deactivate_skill_handler - 0.5h
5. 修改 agent_tools.py 绑定 handler - 1h
6. Agent 自动注册工具 - 0.5h
7. 集成 RewardBus 到 run() - 2h
8. 实现 _maybe_trigger_evolution - 1.5h
9. 实现 E1/E2 结晶化逻辑 - 3h
10. 编写进化测试（8+ 测试） - 3h

**验收标准**:
- ✅ E1/E2 工具完全可用
- ✅ RewardBus 自动评估
- ✅ 低 reward 触发进化

---

### Day 7: Phase 5 - 清理与发布
**优先级**: P0（质量保证）
**工作量**: 1 天

#### 任务清单
1. 删除所有旧文件 - 1h
2. 清理类型定义 - 0.5h
3. 搜索并删除旧 API 引用 - 1h
4. 删除旧测试 - 0.5h
5. 更新集成测试 - 1h
6. 更新 README.md - 1h
7. 创建 MIGRATION.md - 1.5h
8. 更新 CHANGELOG.md - 0.5h
9. 运行完整测试套件 - 1h
10. 修复所有测试失败 - 2h

**验收标准**:
- ✅ 无向后兼容代码残留
- ✅ 所有测试通过
- ✅ 文档完整

---

## 风险管理

### 高风险点
1. **Phase 1 重写 _build_messages**
   - 风险：破坏现有 prompt 构建逻辑
   - 缓解：先写测试，逐步迁移

2. **Phase 4 进化逻辑复杂**
   - 风险：E1/E2 结晶化可能不稳定
   - 缓解：先实现简单版本，后续迭代

3. **Phase 5 删除代码**
   - 风险：误删关键代码
   - 缓解：先 git commit，确保可回滚

### 回滚策略
- 每个 Phase 完成后立即 commit
- 使用 feature branch: `feature/v0.7.0-full-integration`
- 保留 v0.6.6 tag 作为回滚点

---

## 测试策略

### 单元测试覆盖
- Phase 1: 10+ 测试（分区系统）
- Phase 2: 5+ 测试（约束验证）
- Phase 3: 5+ 测试（门控机制）
- Phase 4: 8+ 测试（进化工具）
- **总计**: 28+ 新测试

### 集成测试
- 端到端 Agent 执行流程
- 多轮对话场景
- 工具调用链
- 场景切换
- 技能激活/停用

### 性能测试
- Token 计算性能（P2 优化）
- 分区更新延迟
- 门控计算开销

---

## 发布检查清单

### 代码质量
- [ ] Ruff linting 通过
- [ ] Mypy 类型检查通过
- [ ] 测试覆盖率 > 80%
- [ ] 无 TODO/FIXME 残留

### 文档
- [ ] README.md 更新
- [ ] MIGRATION.md 完整
- [ ] CHANGELOG.md 详细
- [ ] API 文档生成

### 版本管理
- [ ] 版本号更新到 0.7.0
- [ ] Git tag 创建
- [ ] Release notes 编写

### 社区沟通
- [ ] 发布公告草稿
- [ ] Breaking changes 说明
- [ ] 迁移示例代码

---

## 成功指标

### 技术指标
1. ✅ 所有 4 个公理完全集成
2. ✅ 无向后兼容代码
3. ✅ 测试覆盖率 > 80%
4. ✅ 性能无回退（P2 优化保留）

### 架构指标
1. ✅ Agent 主循环完全基于 PartitionManager
2. ✅ 所有工具调用经过约束验证
3. ✅ 所有输出经过信息增益门控
4. ✅ E1/E2 工具完全可用

### 用户体验指标
1. ✅ 迁移路径清晰
2. ✅ 文档完整易懂
3. ✅ 示例代码可运行

---

## 下一步行动

**立即开始**: Phase 1 - 公理一完整接入

**第一个 PR**:
```bash
git checkout -b feature/v0.7.0-phase1-axiom1
# 实现 Phase 1 所有任务
git commit -m "feat: Phase 1 - Axiom 1 complete partition integration"
```

**建议工作流**:
1. 每个 Phase 一个独立 branch
2. Phase 完成后 merge 到 feature/v0.7.0
3. 所有 Phase 完成后 merge 到 main
4. 创建 v0.7.0 tag 和 release
