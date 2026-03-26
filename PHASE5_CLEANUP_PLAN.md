# Phase 5: 清理向后兼容代码实施方案

## 目标
删除所有旧实现，确保 v0.7.0 是完全基于四公理的纯净架构。

---

## 5.1 删除文件清单

### 上下文系统旧代码
```bash
# 完全删除
rm loom/context/orchestrator.py
rm loom/context/source.py
rm -rf loom/context/sources/

# 保留的文件
# loom/context/partition.py      ✓ 保留
# loom/context/heartbeat.py      ✓ 保留
# loom/context/compression.py    ✓ 保留
```

### 技能系统旧代码
```bash
# 删除旧 provider
rm loom/skills/provider.py
rm loom/skills/catalog_provider.py

# 保留的文件
# loom/skills/loader.py          ✓ 保留
# loom/skills/registry.py        ✓ 保留
# loom/skills/context_manager.py ✓ 保留
```

---

## 5.2 类型定义清理

### loom/types/context.py
```python
# 删除以下类型
# - ContextSource (基类)
# - ContextFragment
# - ContextBlock (如果未被使用)

# 保留
# - ContextPartition ✓
# - ContextConfig ✓
```

### loom/types/__init__.py
```python
# 移除导出
# from .context import ContextSource, ContextFragment  # 删除

# 保留
from .context import ContextPartition, ContextConfig
```

---

## 5.3 Agent API 清理

### 删除构造参数
```python
# loom/agent/core.py

# 之前
def __init__(
    self,
    provider: LLMProvider,
    context: ContextOrchestrator | None = None,  # 删除
    ...
):
    self.context = context or ContextOrchestrator()  # 删除

# 之后
def __init__(
    self,
    provider: LLMProvider,
    config: AgentConfig | None = None,
    name: str | None = None,
    memory: MemoryManager | None = None,
    tools: ToolRegistry | None = None,
    event_bus: EventBus | None = None,
    interceptors: InterceptorChain | None = None,
    strategy: LoopStrategy | None = None,
    gating_config: GatingConfig | None = None,  # 新增
):
    # ... 只保留新架构组件
```

---

## 5.4 导入清理

### 全局搜索并删除
```bash
# 搜索所有引用旧类的地方
grep -r "ContextOrchestrator" loom/
grep -r "ContextSource" loom/
grep -r "SkillProvider" loom/
grep -r "SkillCatalogProvider" loom/

# 删除这些导入和使用
```

---

## 5.5 测试清理

### 删除旧测试
```bash
# 删除测试旧 API 的文件
rm tests/unit/test_context_orchestrator.py
rm tests/unit/test_context_sources.py
rm tests/unit/test_skill_provider.py
```

### 更新集成测试
```python
# tests/integration/test_agent.py

# 删除旧 API 测试
# def test_agent_with_custom_context(): ...  # 删除

# 添加新 API 测试
async def test_agent_partition_system():
    """验证 Agent 使用 PartitionManager"""
    agent = Agent(provider=MockProvider())

    assert agent.partition_mgr is not None
    assert len(agent.partition_mgr.partitions) == 5
```

---

## 5.6 文档更新

### README.md
```markdown
# 删除旧示例
## ~~Custom Context Sources~~  # 删除

# 添加新示例
## Context Partitions

Loom v0.7.0 uses a 5-partition context system:

```python
agent = Agent(provider=provider)

# Partitions are managed automatically
# - system: Base prompt + scene additions
# - working: Current task state
# - memory: L2/L3 retrieval
# - skill: Activated skills
# - history: L1 conversation

# Customize partition budget
agent.partition_mgr.window = 200000
```
```

### MIGRATION.md (新建)
```markdown
# Migration Guide: v0.6.x → v0.7.0

## Breaking Changes

### 1. Context System
**Removed:** `ContextOrchestrator`, `ContextSource`
**Replaced by:** `PartitionManager` (automatic)

Before:
```python
from loom.context import ContextOrchestrator, MemoryContextSource
context = ContextOrchestrator()
context.add_source(MemoryContextSource(memory))
agent = Agent(provider=provider, context=context)
```

After:
```python
# No manual context setup needed
agent = Agent(provider=provider)
# Partitions managed automatically
```

### 2. Skill System
**Removed:** `SkillProvider`, `SkillCatalogProvider`
**Replaced by:** `SkillContextManager` (automatic)

Before:
```python
from loom.skills import SkillProvider
skill_provider = SkillProvider(registry)
agent = Agent(provider=provider)
# Manual skill injection
```

After:
```python
agent = Agent(provider=provider)
# Skills auto-registered as E2 tools
# Use activate_skill/deactivate_skill tools
```

### 3. Event Publishing
**Changed:** All events now use information gain gating

Before:
```python
await agent.event_bus.emit(event)
```

After:
```python
# Automatic gating in Agent internals
# Configure thresholds:
agent.gating_config.event_threshold = 0.2
```
```

---

## 5.7 版本标记

### pyproject.toml
```toml
[tool.poetry]
name = "loom-agent"
version = "0.7.0"  # 更新版本
description = "Agent framework with 4-axiom architecture"

[tool.poetry.dependencies]
# 确保依赖版本正确
```

### CHANGELOG.md
```markdown
# Changelog

## [0.7.0] - 2026-03-26

### Breaking Changes
- **Removed** `ContextOrchestrator` and all `ContextSource` classes
- **Removed** `SkillProvider` and `SkillCatalogProvider`
- **Removed** `Agent.context` parameter
- **Changed** All events now use information gain gating by default

### Added
- **Axiom 1**: Complete partition-based context system
- **Axiom 2**: Constraint validation on all tool calls
- **Axiom 3**: Information gain gating across all outputs
- **Axiom 4**: E1/E2 evolution tools fully functional

### Migration
See MIGRATION.md for detailed upgrade guide.
```

---

## 5.8 实施检查清单

- [ ] 删除所有旧上下文文件
- [ ] 删除所有旧技能 provider 文件
- [ ] 清理类型定义
- [ ] 删除 Agent.context 参数
- [ ] 搜索并删除所有旧 API 引用
- [ ] 删除旧测试文件
- [ ] 更新集成测试
- [ ] 更新 README.md
- [ ] 创建 MIGRATION.md
- [ ] 更新 CHANGELOG.md
- [ ] 更新版本号到 0.7.0
- [ ] 运行完整测试套件
- [ ] 验证无向后兼容代码残留

---

**下一步：总体实施时间表**
