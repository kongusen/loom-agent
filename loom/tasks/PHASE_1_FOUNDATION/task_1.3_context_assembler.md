# Task 1.3: 修复 RAG Context Bug - 创建 ContextAssembler

**状态**: ⏳ 待开始
**优先级**: P0
**预计时间**: 1-2 天
**依赖**: Task 1.2 (流式 API) ✅

---

## 📋 任务概述

### 目标

创建 `ContextAssembler` 组件，修复 RAG 上下文被系统提示覆盖的 Bug，实现基于优先级的智能上下文组装。

### 为什么需要这个任务？

**当前问题 (Loom 1.0)**:
```python
# loom/core/agent_executor.py:664-671
def _inject_system_prompt(self, history: List[Message], system_prompt: str) -> List[Message]:
    """注入或更新系统提示消息"""
    # 如果第一条是系统消息，则替换；否则在开头插入
    if history and history[0].role == "system":
        history[0] = Message(role="system", content=system_prompt)  # ❌ 覆盖了 RAG 上下文！
    else:
        history.insert(0, Message(role="system", content=system_prompt))
    return history
```

**问题**:
1. RAG 检索的文档上下文被注入到 `history` 中作为 system 消息
2. `_inject_system_prompt` 直接覆盖第一个 system 消息
3. 导致 RAG 上下文丢失，LLM 无法看到检索的文档

**期望结果 (Loom 2.0)**:
```python
# 使用 ContextAssembler 智能组装
assembler = ContextAssembler(max_tokens=4000)
assembler.add_component("base_instructions", base_prompt, priority=100)
assembler.add_component("tool_schema", tool_definitions, priority=80)
assembler.add_component("retrieved_docs", rag_context, priority=90)  # 高优先级，不被覆盖
assembler.add_component("examples", few_shot_examples, priority=50)

final_system_prompt = assembler.assemble()  # 智能合并，保证 RAG 上下文存在
```

---

## 📐 详细步骤

### Step 1: 创建 ContextAssembler

**文件**: `loom/core/context_assembly.py` (新建)

**核心类设计**:
```python
from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import IntEnum


class ComponentPriority(IntEnum):
    """组件优先级枚举"""
    CRITICAL = 100     # 基础指令（必须包含）
    HIGH = 90          # RAG 上下文、重要配置
    MEDIUM = 70        # 工具定义
    LOW = 50           # 示例、额外提示
    OPTIONAL = 30      # 可选内容


@dataclass
class ContextComponent:
    """上下文组件"""
    name: str
    content: str
    priority: int
    token_count: int
    truncatable: bool = True


class ContextAssembler:
    """
    智能上下文组装器。

    功能:
    - 按优先级组装多个组件
    - Token 预算管理
    - 智能截断低优先级组件
    - 保证高优先级组件完整性
    """

    def __init__(
        self,
        max_tokens: int = 16000,
        token_counter: Optional[callable] = None
    ):
        """
        Args:
            max_tokens: 最大 token 预算
            token_counter: Token 计数函数（默认使用简单估算）
        """
        self.max_tokens = max_tokens
        self.token_counter = token_counter or self._estimate_tokens
        self.components: List[ContextComponent] = []

    def add_component(
        self,
        name: str,
        content: str,
        priority: int,
        truncatable: bool = True
    ):
        """
        添加上下文组件。

        Args:
            name: 组件名称（如 "base_instructions", "retrieved_docs"）
            content: 组件内容
            priority: 优先级（0-100，越高越重要）
            truncatable: 是否可截断
        """
        if not content:
            return

        token_count = self.token_counter(content)
        component = ContextComponent(
            name=name,
            content=content,
            priority=priority,
            token_count=token_count,
            truncatable=truncatable
        )
        self.components.append(component)

    def assemble(self) -> str:
        """
        组装最终上下文。

        策略:
        1. 按优先级降序排序
        2. 依次添加组件直到超出预算
        3. 对可截断组件进行智能截断
        4. 合并所有组件

        Returns:
            组装后的上下文字符串
        """
        # 按优先级排序
        sorted_components = sorted(
            self.components,
            key=lambda c: c.priority,
            reverse=True
        )

        # 计算当前总 Token
        total_tokens = sum(c.token_count for c in sorted_components)

        # 如果超出预算，进行截断
        if total_tokens > self.max_tokens:
            sorted_components = self._truncate_components(sorted_components)

        # 合并组件
        sections = []
        for component in sorted_components:
            sections.append(f"# {component.name.upper()}\n{component.content}")

        return "\n\n".join(sections)

    def _truncate_components(
        self,
        components: List[ContextComponent]
    ) -> List[ContextComponent]:
        """
        智能截断组件以满足 token 预算。

        策略:
        1. 保留所有 truncatable=False 的组件
        2. 按优先级降序处理可截断组件
        3. 为每个组件分配 token 配额
        """
        budget_remaining = self.max_tokens
        result = []

        # 首先添加所有不可截断组件
        for comp in components:
            if not comp.truncatable:
                if comp.token_count <= budget_remaining:
                    result.append(comp)
                    budget_remaining -= comp.token_count
                else:
                    # 不可截断但超出预算，跳过（或抛出警告）
                    print(f"Warning: Component '{comp.name}' is too large and cannot be truncated")

        # 然后添加可截断组件
        truncatable = [c for c in components if c.truncatable]

        for comp in truncatable:
            if comp.token_count <= budget_remaining:
                # 完整添加
                result.append(comp)
                budget_remaining -= comp.token_count
            elif budget_remaining > 100:  # 至少保留 100 tokens
                # 截断添加
                truncated_content = self._truncate_content(
                    comp.content,
                    budget_remaining
                )
                truncated_comp = ContextComponent(
                    name=comp.name,
                    content=truncated_content,
                    priority=comp.priority,
                    token_count=budget_remaining,
                    truncatable=comp.truncatable
                )
                result.append(truncated_comp)
                budget_remaining = 0
                break

        return result

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """
        截断内容以适应 token 限制。

        策略: 简单按字符比例截断
        """
        ratio = max_tokens / self.token_counter(content)
        target_chars = int(len(content) * ratio * 0.95)  # 保守估计

        if target_chars < len(content):
            return content[:target_chars] + "\n... (truncated)"
        return content

    def _estimate_tokens(self, text: str) -> int:
        """
        简单估算 token 数量。

        粗略估算: 1 token ≈ 4 字符（英文）
        """
        return len(text) // 4

    def get_summary(self) -> Dict:
        """返回组装摘要（用于调试）"""
        total_tokens = sum(c.token_count for c in self.components)
        return {
            "components": [
                {
                    "name": c.name,
                    "priority": c.priority,
                    "tokens": c.token_count,
                    "truncatable": c.truncatable
                }
                for c in sorted(self.components, key=lambda x: x.priority, reverse=True)
            ],
            "total_tokens": total_tokens,
            "budget": self.max_tokens,
            "overflow": total_tokens - self.max_tokens if total_tokens > self.max_tokens else 0
        }
```

---

### Step 2: 修改 AgentExecutor

**文件**: `loom/core/agent_executor.py`

**修改点**:

1. **导入 ContextAssembler**:
```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority
```

2. **删除 `_inject_system_prompt` 方法**:
```python
# 删除这个方法（第 664-671 行）
def _inject_system_prompt(self, history: List[Message], system_prompt: str) -> List[Message]:
    ...
```

3. **修改 `execute_stream()` 中的上下文组装逻辑**:
```python
# 在 execute_stream() 中 (约第 440 行)

# Step 4: 使用 ContextAssembler 组装系统提示
assembler = ContextAssembler(max_tokens=self.max_context_tokens)

# 添加基础指令
base_instructions = self.system_instructions or ""
if base_instructions:
    assembler.add_component(
        name="base_instructions",
        content=base_instructions,
        priority=ComponentPriority.CRITICAL,
        truncatable=False
    )

# 添加 RAG 上下文（如果有）
if retrieved_docs:
    doc_context = self.context_retriever.format_documents(retrieved_docs)
    assembler.add_component(
        name="retrieved_context",
        content=doc_context,
        priority=ComponentPriority.HIGH,
        truncatable=True
    )

# 添加工具定义
if self.tools:
    tools_spec = self._serialize_tools()
    tools_prompt = build_tools_prompt(tools_spec)
    assembler.add_component(
        name="tool_definitions",
        content=tools_prompt,
        priority=ComponentPriority.MEDIUM,
        truncatable=False
    )

# 组装最终系统提示
final_system_prompt = assembler.assemble()

# 注入到 history
if history and history[0].role == "system":
    history[0] = Message(role="system", content=final_system_prompt)
else:
    history.insert(0, Message(role="system", content=final_system_prompt))
```

4. **添加调试事件**:
```python
# 在组装后发出事件
summary = assembler.get_summary()
yield AgentEvent(
    type=AgentEventType.CONTEXT_ASSEMBLED,
    metadata={
        "total_tokens": summary["total_tokens"],
        "components": len(summary["components"]),
        "overflow": summary["overflow"]
    }
)
```

---

### Step 3: 添加新的事件类型（可选）

**文件**: `loom/core/events.py`

如果需要更详细的上下文组装可观测性，可以添加：

```python
class AgentEventType(Enum):
    # ... 现有事件 ...

    # Context Assembly Events (可选)
    CONTEXT_ASSEMBLED = "context_assembled"
```

---

## 🧪 测试要求

### 单元测试

**文件**: `tests/unit/test_context_assembler.py` (新建)

测试用例：

1. **基本组装**
```python
def test_basic_assembly():
    """测试基本组装功能"""
    assembler = ContextAssembler(max_tokens=1000)
    assembler.add_component("part1", "Hello", priority=100)
    assembler.add_component("part2", "World", priority=90)

    result = assembler.assemble()

    assert "part1" in result.upper()
    assert "Hello" in result
    assert "World" in result
```

2. **优先级排序**
```python
def test_priority_ordering():
    """测试优先级排序"""
    assembler = ContextAssembler(max_tokens=10000)
    assembler.add_component("low", "Low priority", priority=10)
    assembler.add_component("high", "High priority", priority=100)
    assembler.add_component("mid", "Mid priority", priority=50)

    result = assembler.assemble()

    # 高优先级应该在前
    high_pos = result.find("High priority")
    mid_pos = result.find("Mid priority")
    low_pos = result.find("Low priority")

    assert high_pos < mid_pos < low_pos
```

3. **Token 预算管理**
```python
def test_token_budget():
    """测试 token 预算限制"""
    assembler = ContextAssembler(max_tokens=100)

    # 添加超出预算的内容
    assembler.add_component("large", "x" * 1000, priority=50, truncatable=True)
    assembler.add_component("critical", "Important", priority=100, truncatable=False)

    result = assembler.assemble()
    summary = assembler.get_summary()

    # 关键内容应该保留
    assert "Important" in result
    # 总 token 应该在预算内
    assert summary["total_tokens"] <= 100
```

4. **不可截断组件**
```python
def test_non_truncatable_components():
    """测试不可截断组件保护"""
    assembler = ContextAssembler(max_tokens=500)

    assembler.add_component("critical", "Critical content", priority=100, truncatable=False)
    assembler.add_component("optional", "x" * 10000, priority=50, truncatable=True)

    result = assembler.assemble()

    # 关键内容必须完整
    assert "Critical content" in result
    assert result.count("Critical content") == 1  # 没有被截断
```

5. **RAG 上下文保护**
```python
def test_rag_context_preserved():
    """测试 RAG 上下文被正确保留"""
    assembler = ContextAssembler(max_tokens=2000)

    assembler.add_component(
        "base_instructions",
        "You are a helpful assistant.",
        priority=ComponentPriority.CRITICAL,
        truncatable=False
    )

    assembler.add_component(
        "retrieved_docs",
        "Document 1: Important info\nDocument 2: More info",
        priority=ComponentPriority.HIGH,
        truncatable=True
    )

    result = assembler.assemble()

    # RAG 上下文应该存在
    assert "Document 1" in result
    assert "Important info" in result
```

### 集成测试

**文件**: `tests/integration/test_rag_context_fix.py` (新建)

测试真实场景：

```python
@pytest.mark.asyncio
async def test_rag_context_not_overwritten():
    """测试 RAG 上下文不被系统提示覆盖"""
    # 创建带 RAG 的 agent
    from loom.rag import MockRetriever

    retriever = MockRetriever(docs=[
        {"content": "Python is a programming language", "score": 0.9}
    ])

    agent = Agent(
        llm=mock_llm,
        context_retriever=retriever,
        system_instructions="You are helpful"
    )

    collector = EventCollector()
    async for event in agent.execute("What is Python?"):
        collector.add(event)

    # 验证 RAG 上下文在 LLM 调用中存在
    # (需要检查发送给 LLM 的消息)
    # 这个测试可能需要 mock LLM 来验证
```

---

## ✅ 验收标准

| 标准 | 要求 | 检查 |
|------|------|------|
| ContextAssembler 实现 | 完整功能 | [ ] |
| 优先级排序 | 正确排序组件 | [ ] |
| Token 预算管理 | 不超出限制 | [ ] |
| RAG 上下文保留 | 不被覆盖 | [ ] |
| 删除旧方法 | `_inject_system_prompt` 已删除 | [ ] |
| 测试覆盖率 | ≥ 80% | [ ] |
| 所有测试通过 | 单元 + 集成测试 | [ ] |
| 向后兼容 | 不破坏现有功能 | [ ] |

---

## 📋 实施检查清单

### 代码实现
- [ ] 创建 `loom/core/context_assembly.py`
  - [ ] `ComponentPriority` 枚举
  - [ ] `ContextComponent` 数据类
  - [ ] `ContextAssembler` 类
    - [ ] `add_component()` 方法
    - [ ] `assemble()` 方法
    - [ ] `_truncate_components()` 方法
    - [ ] `get_summary()` 方法

- [ ] 修改 `loom/core/agent_executor.py`
  - [ ] 导入 `ContextAssembler`
  - [ ] 删除 `_inject_system_prompt()` 方法
  - [ ] 修改 `execute_stream()` 使用 ContextAssembler
  - [ ] 添加 CONTEXT_ASSEMBLED 事件（可选）

### 测试
- [ ] 创建 `tests/unit/test_context_assembler.py`
  - [ ] 5+ 单元测试
  - [ ] 覆盖所有核心功能

- [ ] 创建 `tests/integration/test_rag_context_fix.py`
  - [ ] End-to-end RAG 测试
  - [ ] 验证上下文不被覆盖

- [ ] 运行所有测试
  ```bash
  pytest tests/unit/test_context_assembler.py -v
  pytest tests/integration/test_rag_context_fix.py -v
  pytest tests/ -v  # 确保没有破坏现有功能
  ```

### 文档
- [ ] 创建 `examples/rag_context_example.py`
  - [ ] 演示 RAG 集成
  - [ ] 展示上下文组装

- [ ] 更新 `docs/api_reference.md`
  - [ ] 添加 ContextAssembler API 文档

- [ ] 创建 `docs/TASK_1.3_COMPLETION_SUMMARY.md`

### 完成
- [ ] 所有测试通过
- [ ] 代码审查
- [ ] 更新 `LOOM_2.0_DEVELOPMENT_PLAN.md`
- [ ] 更新 `loom/tasks/README.md`

---

## 🔗 参考资源

- [Task 1.1: AgentEvent 模型](task_1.1_agent_events.md)
- [Task 1.2: 流式 API](task_1.2_streaming_api.md)
- [原始 Bug 报告](../../../LOOM_2.0_DEVELOPMENT_PLAN.md#原始问题)

---

## 📝 注意事项

### 关键决策

1. **优先级系统**: 使用 0-100 整数，而非枚举
   - 灵活性更高
   - 允许精细调整

2. **Token 计数**: 使用简单估算
   - 精确计数需要 tokenizer（依赖特定模型）
   - 简单估算足够满足需求

3. **截断策略**: 保守截断低优先级组件
   - 保证关键信息完整
   - 避免语义破坏

### 潜在问题

1. **Token 估算不准确**: 可能导致超出实际限制
   - 解决：添加 10% buffer

2. **组件顺序**: 某些 LLM 对 prompt 顺序敏感
   - 解决：提供自定义排序选项（后续优化）

3. **性能**: 大量组件时性能可能下降
   - 解决：当前规模足够，后续可优化

---

**创建日期**: 2025-10-25
**预计开始**: 2025-10-25
**预计完成**: 2025-10-26
