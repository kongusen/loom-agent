# P2 问题修复计划

**优先级**: P2 - 高级能力问题
**目标**: 增强框架的高级特性和完整性

---

## P2 问题概览

根据 IMPLEMENTATION_GAPS.md，P2 包含 10 个高级能力问题（#11-#20）。

---

## P2 问题列表

### 11. MCP 集成有两个重复实现

**文件**: `loom/ecosystem/mcp.py`

**问题**:
- 基础 MCP bridge 已实现
- 但实际连接和工具执行仍使用 mock 数据
- 需要实现真实的 MCP 协议通信

**优先级**: 中 - 影响外部工具集成

---

### 12. Evolution Strategies 完全是占位符

**文件**: `loom/evolution/strategies.py`

**问题**:
- ToolLearningStrategy 只有 pass
- PolicyOptimizationStrategy 只有 pass
- Evolution 系统结构存在但无行为

**优先级**: 低 - 高级特性，不影响基础功能

---

### 13. Heartbeat 监控集成不完整

**文件**: `loom/runtime/monitors.py`

**问题**:
- MFEventsMonitor 实现了但需要手动设置 event_bus
- Heartbeat 和 Dashboard 的集成不够深入
- 未深度集成到运行循环

**优先级**: 中 - 影响运行时监控

---

### 14. Context Renewal 保留了状态但未完全恢复语义

**文件**: `loom/context/renewal.py`

**问题**:
- 实现了基础的 context renewal
- 但语义恢复不完整
- 压缩后的信息可能丢失重要上下文

**优先级**: 中 - 影响长时间运行的任务

---

### 15. Dashboard 状态存储但未用于决策

**文件**: `loom/context/dashboard.py`

**问题**:
- Dashboard 记录了丰富的状态
- 但 DecisionEngine 只使用了部分信息
- 未充分利用 Dashboard 数据

**优先级**: 低 - DecisionEngine 已经可用

---

### 16. Plugin 生态系统加载但未完全连接

**文件**: `loom/ecosystem/plugin.py`

**问题**:
- Plugin 加载机制存在
- 但与 Agent 的集成不完整
- 缺少 plugin 生命周期管理

**优先级**: 低 - 扩展性特性

---

### 17. Safety Hooks 实现基础但缺少丰富的上下文

**文件**: `loom/safety/hooks.py`

**问题**:
- Hook 系统存在但上下文信息有限
- 无法访问完整的 Agent 状态
- 决策能力受限

**优先级**: 中 - 影响安全性

---

### 18. Permission 系统有重复的类定义

**文件**: 多个文件

**问题**:
- Permission 相关类在多处定义
- 可能导致不一致
- 需要统一

**优先级**: 低 - 代码质量问题

---

### 19. Capability Loader 实现简单

**文件**: `loom/capabilities/loader.py`

**问题**:
- 只支持基础的 capability 加载
- 缺少依赖解析
- 缺少版本管理

**优先级**: 低 - 基础功能已可用

---

### 20. VetoAuthority 实现过于简单

**文件**: `loom/safety/veto.py`

**问题**:
- 只有简单的 veto 逻辑
- 缺少复杂的决策机制
- 缺少审计日志

**优先级**: 中 - 影响安全性

---

## 修复优先级排序

基于影响和复杂度，建议修复顺序：

### 高优先级（影响核心功能）

1. **Heartbeat 监控集成** - 影响运行时监控和中断处理
2. **Safety Hooks 上下文增强** - 影响安全性
3. **VetoAuthority 增强** - 影响安全性

### 中优先级（增强可用性）

4. **Context Renewal 语义恢复** - 影响长时间运行
5. **MCP 集成真实实现** - 影响外部工具集成

### 低优先级（高级特性）

6. **Evolution Strategies 实现** - 高级学习特性
7. **Dashboard 决策集成** - 优化决策质量
8. **Plugin 生态系统连接** - 扩展性
9. **Permission 系统统一** - 代码质量
10. **Capability Loader 增强** - 扩展性

---

## 本次会话目标

建议先修复高优先级的 3 个问题：

1. Heartbeat 监控集成
2. Safety Hooks 上下文增强
3. VetoAuthority 增强

预计时间：2-3 小时

---

## 成功标准

每个修复需要：
- ✅ 实现完整功能
- ✅ 创建测试文件
- ✅ 所有测试通过
- ✅ 创建文档
