# A4: 记忆层次公理 (Memory Hierarchy Axiom)

> **公理陈述**: Memory = L1 ⊂ L2 ⊂ L3 ⊂ L4

## 设计理念

A4层实现四层记忆系统，支持有损压缩和自动迁移。
每层之间通过压缩机制实现信息的层次化存储。

## 核心组件

### 1. MemoryLayer (`layer.py`)
记忆层抽象基类：
- `store()`: 存储记忆
- `retrieve()`: 检索记忆
- `compress()`: 压缩记忆（准备迁移）

### 2. 四层记忆系统 (`hierarchy.py`)

**L1: 工作记忆**
- 容量: 10项
- 特点: 短期、高频访问
- 压缩策略: 低频项迁移

**L2: 会话记忆**
- 容量: 50项
- 特点: 中期存储
- 压缩策略: 旧项迁移

**L3: 情节记忆**
- 容量: 200项
- 特点: 长期存储
- 压缩策略: 语义摘要

**L4: 语义记忆**
- 容量: 1000项
- 特点: 永久存储、高度压缩
- 压缩策略: 不再压缩

### 3. MemoryHierarchy
四层记忆管理器：
- 统一存储接口
- 跨层检索
- 自动层间迁移

## 与公理系统的关系

- **A4（记忆层次）**: L1 ⊂ L2 ⊂ L3 ⊂ L4
- **有损压缩**: Li → Li+1 保持语义，减少细节
- **自动迁移**: 容量满时触发压缩和迁移

## 使用示例

```python
from loom.memory import MemoryHierarchy

# 创建记忆系统
memory = MemoryHierarchy()

# 存储记忆
memory_id = await memory.store("重要信息")

# 检索记忆
results = await memory.retrieve("重要")
```
