# Loom v0.7.0 完整接入方案 - 架构分析

## 执行摘要

当前 v0.6.6 存在"半接线"状态：核心机制已实现，但未完全集成到主执行路径。v0.7.0 将删除所有向后兼容代码，构建完全基于四公理的统一架构。

---

## 一、四公理当前状态诊断

### 公理一：上下文工程（Context Engineering）

**已实现组件：**
- ✅ PartitionManager：5分区模型（system/working/memory/skill/history）
- ✅ HeartbeatLoop：Ralph Loop 心跳续写
- ✅ CompressionScorer：三层评分压缩
- ✅ SkillContextManager：技能预算化管理

**半接线问题：**
1. **分区未完全使用**：`_build_messages()` 只用了 system/memory/history，忽略 working/skill
2. **旧路径并存**：ContextOrchestrator 仍存在但不在主路径
3. **working 分区无业务写入**：heartbeat 依赖的 working 分区在主循环中无持续更新
4. **skill 分区未拼接**：skill_mgr.get_context() 未进入最终 prompt

**根本原因：**
`Agent._build_messages()` 没有调用 `partition_mgr.get_context()` 统一组装，而是手工拼接部分分区。

---

### 公理二：场景包系统（Scene Package System）

**已实现组件：**
- ✅ SceneManager：场景加载与切换
- ✅ ConstraintValidator：场景约束验证（P0）
- ✅ Scene 类型定义

**半接线问题：**
1. **约束未卡主路径**：工具执行绕过 ConstraintValidator
2. **场景切换无自动触发**：需手动调用 `scene_mgr.activate_scene()`
3. **场景上下文未注入**：场景的 system_prompt_additions 未自动合并到 C_system

**根本原因：**
ConstraintValidator 和 SceneManager 是独立组件，未集成到 ToolRegistry.execute() 和 partition 更新流程。

---

### 公理三：信息增益门控（Information Gain Gating）

**已实现组件：**
- ✅ InformationGainCalculator：ΔH 计算
- ✅ EventBus.publish_with_gain()：带门控的发布

**半接线问题：**
1. **主事件流未使用门控**：Agent 内部仍用 `event_bus.emit()` 而非 `publish_with_gain()`
2. **工具输出未过滤**：工具结果直接返回，无信息增益评估
3. **LLM 输出未门控**：流式输出无 ΔH 检查

**根本原因：**
`publish_with_gain()` 是可选钩子，不是默认路径。

---

### 公理四：自我进化（Self-Evolution）

**已实现组件：**
- ✅ EvolutionEngine：E1/E2 结晶化
- ✅ RewardBus：EMA 能力追踪
- ✅ AmoebaLoop：6阶段自组织

**半接线问题：**
1. **agent_tools 未接线**：write_memory/activate_skill/deactivate_skill 是占位实现
2. **进化未自动触发**：EvolutionEngine 存在但无调用点
3. **RewardBus 未集成**：Agent 主循环无 reward 评估

**根本原因：**
E1/E2 工具定义存在，但 execute 函数是 `_not_implemented`，未绑定到 Agent 的实际 handler。

---

## 二、向后兼容代码清单（待删除）

### 2.1 旧上下文系统
```
loom/context/orchestrator.py  # 完全替换为 PartitionManager
loom/context/source.py         # 废弃
loom/context/sources/          # 整个目录删除
```

### 2.2 旧技能系统
```
loom/skills/provider.py        # 替换为 SkillContextManager
loom/skills/catalog_provider.py # 删除
```

### 2.3 未使用的类型
```
loom/types/context.py 中的 ContextSource/ContextFragment  # 删除
```

---

## 三、完整接入的核心变更

### 3.1 公理一：统一分区组装

**变更点：**
`Agent._build_messages()` 必须：
1. 调用 `partition_mgr.get_context()` 获取完整上下文
2. 删除手工拼接逻辑
3. 在每个执行步骤后更新 working 分区
4. 自动触发 compress/heartbeat

**新流程：**
```
每轮开始 → 更新 working 分区（当前任务状态）
         → 检查 ρ → 触发 compress/heartbeat
         → partition_mgr.get_context() → 构建 messages
         → LLM 调用
         → 更新 history 分区
```

### 3.2 公理二：约束前置验证

**变更点：**
`ToolRegistry.execute()` 必须：
1. 调用 `constraint_validator.validate()` 前置检查
2. 验证失败直接返回错误，不执行工具
3. 场景切换自动更新 C_system

**新流程：**
```
工具调用 → ConstraintValidator.validate()
        → 失败 → 返回约束错误
        → 成功 → 执行工具 → 返回结果
```

### 3.3 公理三：全链路门控

**变更点：**
1. Agent 内部所有 `emit()` 替换为 `publish_with_gain()`
2. 工具输出经过 ΔH 评估后再返回
3. LLM 流式输出累积 ΔH，低增益时截断

**新流程：**
```
事件产生 → 计算 ΔH → 门控判断 → 发布/丢弃
工具输出 → 计算 ΔH → 过滤冗余 → 返回精简结果
```

### 3.4 公理四：E1/E2 工具接线

**变更点：**
1. 实现 `write_memory_handler()` 绑定到 Agent.memory
2. 实现 `activate_skill_handler()` 绑定到 Agent.skill_mgr
3. 自动注册这些工具到 ToolRegistry
4. 在任务结束时触发 EvolutionEngine

**新流程：**
```
Agent 初始化 → 自动注册 E1/E2 工具
工具调用 → 路由到 Agent handler → 更新内部状态
任务结束 → RewardBus.evaluate() → EvolutionEngine.crystallize()
```

---

## 四、删除策略

### 4.1 不兼容变更
- 删除 ContextOrchestrator 及所有 ContextSource 子类
- 删除 SkillProvider/SkillCatalogProvider
- Agent 构造函数移除 `context` 参数

### 4.2 迁移路径
用户需要：
1. 移除所有自定义 ContextSource
2. 改用 PartitionManager 直接更新分区
3. 技能加载改用 SkillRegistry + SkillContextManager

---

## 五、实施阶段

### Phase 1: 公理一完整接入（核心）
- 重写 `_build_messages()` 使用 partition_mgr
- 实现 working 分区自动更新
- 删除 ContextOrchestrator

### Phase 2: 公理二约束前置
- ToolRegistry.execute() 集成 ConstraintValidator
- 场景切换自动更新 C_system

### Phase 3: 公理三门控全覆盖
- 替换所有 emit() 为 publish_with_gain()
- 工具输出 ΔH 过滤

### Phase 4: 公理四进化闭环
- 实现 E1/E2 工具 handler
- 集成 RewardBus 和 EvolutionEngine

### Phase 5: 清理向后兼容代码
- 删除所有标记为废弃的模块
- 更新类型定义

---

## 六、风险与缓解

### 风险1：破坏现有用户代码
**缓解**：提供详细迁移指南，标记为 v0.7.0 breaking change

### 风险2：性能回退
**缓解**：保留 P2 优化（缓存、增量计算）

### 风险3：复杂度增加
**缓解**：提供默认配置，高级用户可定制

---

## 七、成功标准

v0.7.0 完成标志：
1. ✅ Agent 主循环完全基于 PartitionManager
2. ✅ 所有工具调用经过 ConstraintValidator
3. ✅ 所有事件经过信息增益门控
4. ✅ E1/E2 工具完全可用
5. ✅ 无向后兼容代码残留
6. ✅ 所有测试通过

---

**下一步：分段实施方案**
