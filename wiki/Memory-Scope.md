# 记忆作用域 (Memory Scope)

## 定义

**记忆作用域**定义了记忆的可见性和生命周期。

## 四种作用域

| 作用域 | 可见性 | 可写性 | 生命周期 |
|--------|--------|--------|----------|
| **PRIVATE** | 仅当前节点 | 读写 | 节点销毁时清除 |
| **SHARED** | 父子节点 | 读写 | 向上同步到父节点 |
| **INHERITED** | 从父节点继承 | 只读 | 无法修改 |
| **GLOBAL** | 全局可见 | 读写 | 永久保存 |

## 使用示例

```python
from loom.fractal.memory import FractalMemory, MemoryScope

memory = FractalMemory(node_id="agent")

# PRIVATE: 仅自己可见
await memory.write(
    entry_id="private-thought",
    content="我的私人想法",
    scope=MemoryScope.PRIVATE
)

# SHARED: 父子节点共享
await memory.write(
    entry_id="shared-knowledge",
    content="共享的知识",
    scope=MemoryScope.SHARED
)

# INHERITED: 自动继承父节点的 GLOBAL 记忆
inherited = await memory.read(
    entry_id="global-config",
    search_scopes=[MemoryScope.INHERITED]
)

# GLOBAL: 全局可见
await memory.write(
    entry_id="global-config",
    content="全局配置",
    scope=MemoryScope.GLOBAL
)
```

## 记忆流动

```
父节点
  ├─ PRIVATE (仅父节点)
  ├─ SHARED (父子共享)
  └─ GLOBAL (全局可见)
       ↓ 继承
子节点
  ├─ PRIVATE (仅子节点)
  ├─ SHARED (同步到父节点)
  └─ INHERITED (只读，来自父节点)
```

## 相关概念

- → [代谢记忆](Metabolic-Memory)
- → [记忆分层](Memory-Layers)

## 代码位置

- `loom/fractal/memory.py`

## 反向链接

被引用于: [代谢记忆](Metabolic-Memory) | [分形节点](Fractal-Node)
