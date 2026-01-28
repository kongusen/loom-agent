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

**L1: 直连 + 近期记忆**
- 容量: 10项
- 特点: 短期、高频访问
- 压缩策略: 低频项迁移

**L2: 会话工作记忆（Bus相关）**
- 容量: 50项
- 特点: 中期存储
- 压缩策略: 旧项迁移

**L3: 会话摘要**
- 容量: 200项
- 特点: 会话内长期存储
- 压缩策略: 语义摘要

**L4: 跨会话记忆**
- 容量: 1000项
- 特点: 永久存储、高度压缩
- 压缩策略: 不再压缩

### Session ID（由上层定义）

本模块支持显式 `session_id`，由上层业务定义何时开启/切换会话。  
当 `session_id` 存在时：
- L1/L2/L3 默认按 session 过滤  
- L4 为跨会话记忆，不默认过滤  

## L1-L4 迭代机制（压缩与迁移）

记忆层之间通过“重要性提升 + 容量触发压缩”进行自动迁移：

**L1 → L2（重要性提升）**
- 规则：`importance > 0.6` 的 Task 提升到 L2  
- L2 使用优先队列，仅保留高重要性任务  

**L2 → L3（会话摘要）**
- 触发：L2 使用率达到 90%  
- 策略：将最不重要的 20% 压缩为 `TaskSummary` 写入 L3  
- 结果：降低存储成本，保留会话内核心信息  

**L3 → L4（跨会话向量记忆）**
- 触发：L3 使用率达到 90%  
- 策略：将最旧的 20% 摘要向量化并存入 L4  
- 依赖：需要 embedding provider 和 vector store，否则跳过  

> 入口方法：`promote_tasks()` / `promote_tasks_async()`  

## 上下文管理机制（与 L1-L4 联动）

上下文由 `TaskContextManager` 构建，和记忆分层结合：

**预算分配（可配置）**
- `l1_ratio`：L1 预算（直连消息 + L1 近期记忆）
- `l2_ratio`：L2 预算（Bus 相关上下文）
- `l3_l4_ratio`：L3/L4 预算（摘要/跨会话检索）

**上下文来源**
- **Direct（点对点）**：EventBus `query_by_target`  
  - 进入 L1 预算，且有最小保留条数  
- **Bus（集体）**：EventBus `query_by_task` / `query_recent`  
  - 经评分排序后进入 L2 预算  
- **L3/L4**：通过工具按需查询  
  - `query_l3_memory` / `query_l4_memory`  

**Session 过滤**
- `session_id` 存在时，L1/L2/L3 和 EventBus 事件按 session 过滤  
- L4 默认不做 session 限制（跨会话），但 session_id 会被记录  

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
