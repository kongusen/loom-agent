# P1 问题修复计划

**优先级**: P1 - 高优先级（框架可用性问题）
**目标**: 让框架更加完整和可用

---

## P1 问题列表

### 1. CapabilityRegistry.activate() - 假激活 → 真实激活

**文件**: `loom/capabilities/registry.py`

**问题**:
- 只是添加到 set 中，没有实际效果
- 没有加载 tools
- 没有注入到 context
- 没有更新 runtime 的可用工具列表

**优先级**: 高 - 能力系统是框架的核心特性

---

### 2. Web 工具完全是 Mock 实现

**文件**: `loom/tools/builtin/web.py`

**问题**:
- web_fetch 和 web_search 都是 mock
- 工具声称有能力但实际不工作
- 用户无法使用 web 相关功能

**优先级**: 高 - Web 工具是常用功能

---

### 3. 知识检索使用词法相似度而非真正的嵌入

**文件**: `loom/tools/knowledge.py`

**问题**:
- 使用简单的 token overlap 计算相似度
- 无法理解语义
- 与 "RAG as Evidence" 的定位不符

**优先级**: 中 - 影响检索质量

---

### 4. Context Compression 的 micro_compact 未实现

**文件**: `loom/context/compression.py`

**问题**:
- 四层压缩机制中的一层缺失
- 无法缓存工具结果

**优先级**: 中 - 影响 token 效率

---

### 5. 工具治理的权限检查不够细粒度

**文件**: `loom/tools/governance.py`

**问题**:
- 只有简单的 allow/deny 逻辑
- 缺少基于参数的细粒度控制
- 缺少基于上下文的动态决策

**优先级**: 中 - 影响安全性

---

### 6. Observer 只是包装器

**文件**: `loom/execution/observer.py`

**问题**:
- 只是简单包装 ToolExecutor
- 没有实际的观察和记录功能

**优先级**: 低 - 不影响核心功能

---

## 修复顺序

基于影响和复杂度，建议修复顺序：

1. **Web 工具** - 最常用，实现相对简单
2. **CapabilityRegistry.activate()** - 核心特性，需要重构
3. **micro_compact** - 相对独立，实现简单
4. **知识检索 embedding** - 需要集成外部库
5. **工具治理细粒度控制** - 需要设计策略系统
6. **Observer 增强** - 优先级较低

---

## 本次会话目标

修复前 3 个问题：
1. Web 工具实现
2. CapabilityRegistry.activate() 真实激活
3. micro_compact 实现

---

## 预计时间

- Web 工具: 30-45 分钟
- CapabilityRegistry: 30-45 分钟
- micro_compact: 15-30 分钟

总计: 1.5-2 小时
