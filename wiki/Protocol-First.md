# 协议优先 (Protocol-First)

## 定义

**协议优先**是 Loom 的核心设计原则，所有组件必须先定义接口协议(Protocol)，然后实现具体功能。

## 核心思想

传统框架的扩展方式是继承(Inheritance)，导致：
- 紧耦合：子类依赖父类的实现细节
- 脆弱：父类变更影响所有子类
- 不灵活：多重继承复杂且容易出错

Loom 采用**协议(Protocol)**方式：
- 松耦合：只依赖接口，不依赖实现
- 稳定：协议定义后很少变更
- 灵活：一个类可以实现多个协议

## Protocol vs Inheritance

### 传统方式：继承

```python
class Agent:
    def execute(self, task):
        raise NotImplementedError

class MyAgent(Agent):  # 紧耦合
    def execute(self, task):
        # ...
```

### Loom 方式：协议

```python
from typing import Protocol

class AgentProtocol(Protocol):  # 接口定义
    def execute(self, task: Task) -> Task:
        ...

class MyAgent:  # 松耦合，不继承
    def execute(self, task: Task) -> Task:
        # 只需实现协议方法
```

## 核心协议

### Agent 协议

```python
class NodeProtocol(Protocol):
    """节点协议：所有组件的基础接口"""

    node_id: str
    node_type: str

    async def execute_task(self, task: Task) -> Task:
        """执行任务"""
        ...
```

### LLM 协议

```python
class LLMProvider(Protocol):
    """LLM 提供者协议"""

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None
    ) -> AsyncIterator[Chunk]:
        """流式对话"""
        ...
```

### Memory 协议

```python
class MemoryLayer(Protocol):
    """记忆层协议"""

    async def add(self, item: Task) -> None:
        """添加记忆"""
        ...

    async def retrieve(
        self,
        query: Any,
        limit: int = 10
    ) -> list[Task]:
        """检索记忆"""
        ...
```

## 优势

### 1. 可替换性

```python
# 轻松替换 LLM 提供者
llm1 = OpenAIProvider(api_key="...")
llm2 = AnthropicProvider(api_key="...")

# 两者都实现了 LLMProvider 协议，可以直接互换
agent = Agent(llm_provider=llm1)
agent.llm_provider = llm2  # 无缝切换
```

### 2. 多实现共存

```python
# 同一个协议的多个实现
class InMemoryLLM(LLMProvider): ...
class OpenAILLM(LLMProvider): ...
class AnthropicLLM(LLMProvider): ...

# 根据场景选择
if testing:
    llm = InMemoryLLM()
elif production:
    llm = OpenAILLM(api_key="...")
```

### 3. 类型安全

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # 类型检查时使用协议
    from loom.protocol import LLMProvider

def create_agent(llm: LLMProvider):  # 类型提示
    return Agent(llm_provider=llm)

# mypy 会检查传入的对象是否符合协议
create_agent(OpenAIProvider())  # ✓ 通过
create_agent("not an llm")       # ✗ 类型错误
```

## 协议发现

Loom 使用 `Protocol` 的鸭子类型：

```python
class MyCustomLLM:
    """不需要显式声明实现 LLMProvider"""

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None
    ) -> AsyncIterator[Chunk]:
        """只要实现了这个方法，就符合协议"""
        yield Chunk(type="text", content="...")

# 可以直接使用
agent = Agent(llm_provider=MyCustomLLM())  # ✓
```

## 相关概念

- → [公理系统](Axiomatic-System) (A1: 统一接口公理)
- → [分形递归](Fractal-Recursion) (协议保证可组合性)

## 参见

- 📖 [PEP 544](https://peps.python.org/pep-0544/) (Protocol 规范)
- 🔧 [API 指南]: [实现自定义协议](api/Protocol)

## 代码位置

- 协议定义: `loom/protocol/`
- 节点协议: `loom/protocol/nodes.py`
- LLM 协议: `loom/protocol/llm.py`

## 反向链接

被引用于: [公理系统](Axiomatic-System) | [分形架构](Fractal-Architecture) | [工具系统](Tool-System)
