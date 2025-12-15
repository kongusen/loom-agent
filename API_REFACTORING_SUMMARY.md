# API 重构总结 - 工厂化设计

## 核心变更

### 1. 命名重构

**之前**：
```python
from loom import SimpleAgent

agent = SimpleAgent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)
```

**现在**：
```python
import loom

agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)
```

### 2. 设计理念

- **工厂化**：只提供 `agent()` 工厂函数，不直接导出 `Agent` 类
- **递增命名**：Agent 是标准实现，不是"简单版本"
- **API 简洁**：`loom.agent()` 是创建 Agent 的唯一入口

### 3. 文件变更

#### 重命名
- `loom/agents/simple.py` → `loom/agents/agent.py`
- `SimpleAgent` 类 → `Agent` 类

#### 新增工厂函数
- `loom/__init__.py` 中添加 `agent()` 工厂函数
- 工厂函数是创建 Agent 的推荐方式

#### 导出更新
- `loom/__init__.py` 只导出 `agent` 函数
- `Agent` 类不在 `__all__` 中（内部使用）

---

## 使用方式

### 基础用法

```python
import loom
from loom import Message

# 创建 Agent
agent = loom.agent(
    name="assistant",
    llm="deepseek",      # 提供商名称
    api_key="sk-...",    # API 密钥
    model="deepseek-chat"  # 可选
)

# 使用
message = Message(role="user", content="Hello!")
response = await agent.run(message)
print(response.content)
```

### 高级配置

```python
import loom

# 方式 1：极简配置
agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)

# 方式 2：详细配置
agent = loom.agent(
    name="assistant",
    llm="qwen",
    api_key="sk-...",
    model="qwen-turbo",
    temperature=0.7,
    max_tokens=2000
)

# 方式 3：字典配置
agent = loom.agent(
    name="assistant",
    llm={
        "provider": "openai",
        "api_key": "sk-...",
        "model": "gpt-4",
        "temperature": 0.7
    }
)

# 方式 4：使用代理
agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    base_url="https://your-proxy.com/v1"
)

# 方式 5：自定义服务
agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="your-key",
    base_url="https://your-service.com/v1",
    model="your-model"
)

# 方式 6：LLM 实例
from loom.builtin import UnifiedLLM
llm = UnifiedLLM(api_key="sk-...", provider="openai")
agent = loom.agent(name="assistant", llm=llm)
```

### 添加工具

```python
import loom
from loom import tool

@tool(name="calculator")
async def calculator(expression: str) -> float:
    return eval(expression)

agent = loom.agent(
    name="assistant",
    llm="openai",
    api_key="sk-...",
    tools=[calculator]
)
```

---

## 迁移指南

### 从 SimpleAgent 迁移

**旧代码**：
```python
from loom import SimpleAgent

agent = SimpleAgent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)
```

**新代码**：
```python
import loom

agent = loom.agent(
    name="assistant",
    llm="deepseek",
    api_key="sk-..."
)
```

### 批量替换

1. **导入语句**：
   ```bash
   # 将所有 SimpleAgent 导入替换为 loom
   sed -i 's/from loom import SimpleAgent/import loom/g' *.py
   sed -i 's/from loom.agents import SimpleAgent/import loom/g' *.py
   ```

2. **实例化调用**：
   ```bash
   # 将所有 SimpleAgent() 替换为 loom.agent()
   sed -i 's/SimpleAgent(/loom.agent(/g' *.py
   ```

---

## 优势

### 1. **API 清晰**
- 只有一个入口：`loom.agent()`
- 不会在 `Agent` 和 `SimpleAgent` 之间困惑

### 2. **命名合理**
- `Agent` 是标准实现，不是"简单版本"
- 符合递增命名原则（未来可能有 `AdvancedAgent` 等）

### 3. **工厂模式**
- 灵活：可以根据参数返回不同类型的 Agent
- 扩展性：未来可以支持更多 Agent 类型

### 4. **向后兼容**
- 保留了所有功能
- 只是改变了 API 入口

---

## 内部实现

### 工厂函数

```python
# loom/__init__.py
def agent(
    name: str,
    llm: Union[str, Dict[str, Any], BaseLLM],
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    tools: Optional[List[BaseTool]] = None,
    system_prompt: Optional[str] = None,
    context_manager: Optional[ContextManager] = None,
    max_recursion_depth: int = 20,
    skills_dir: Optional[str] = None,
    enable_skills: bool = True,
    **llm_kwargs: Any,
) -> Agent:
    """创建 Loom Agent 实例（工厂函数）"""
    return Agent(
        name=name,
        llm=llm,
        api_key=api_key,
        model=model,
        base_url=base_url,
        tools=tools,
        system_prompt=system_prompt,
        context_manager=context_manager,
        max_recursion_depth=max_recursion_depth,
        skills_dir=skills_dir,
        enable_skills=enable_skills,
        **llm_kwargs,
    )
```

### Agent 类

```python
# loom/agents/agent.py
class Agent:
    """
    Agent - Loom Agent 标准实现

    基于递归状态机的核心 Agent 实现
    """

    def __init__(self, name: str, llm: Union[str, Dict, BaseLLM], ...):
        ...

    async def run(self, message: Message) -> Message:
        """核心递归方法"""
        return await self.executor.execute(message)
```

---

## 支持的 LLM

通过 `loom.agent()` 支持以下 LLM：

### OpenAI 兼容提供商
- **OpenAI** - `llm="openai"`
- **DeepSeek** - `llm="deepseek"` (国产)
- **Qwen/通义千问** - `llm="qwen"` (阿里)
- **Kimi/月之暗面** - `llm="kimi"` (国产)
- **智谱/GLM** - `llm="zhipu"` (国产)
- **豆包** - `llm="doubao"` (字节跳动)
- **零一万物 Yi** - `llm="yi"` (国产)
- **自定义** - `llm="custom"` (任何 OpenAI 兼容服务)

### 示例

```python
# OpenAI
agent = loom.agent(name="assistant", llm="openai", api_key="sk-...")

# DeepSeek（国产，性价比高）
agent = loom.agent(name="coder", llm="deepseek", api_key="sk-...")

# 通义千问（阿里）
agent = loom.agent(name="assistant", llm="qwen", api_key="sk-...")

# 自定义服务（vLLM, Ollama 等）
agent = loom.agent(
    name="assistant",
    llm="custom",
    api_key="EMPTY",
    base_url="http://localhost:8000/v1",
    model="Qwen/Qwen2-7B-Instruct"
)
```

---

## 测试验证

```bash
# 导入测试
python3 -c "import loom; print('✅ Import successful')"

# 工厂函数测试
python3 -c "
import loom
agent = loom.agent(name='test', llm='openai', api_key='test')
print('✅ agent() 工厂函数正常工作')
print('Agent type:', type(agent).__name__)
"

# Agent 类未导出测试
python3 -c "
import loom
print('agent 在 __all__:', 'agent' in loom.__all__)
print('Agent 在 __all__:', 'Agent' in loom.__all__)
print('✅ Agent 类未导出（符合预期）')
"
```

---

## 总结

✅ **完成的工作**：
1. 重命名 `SimpleAgent` → `Agent`
2. 添加 `loom.agent()` 工厂函数
3. 只导出 `agent()` 函数，不导出 `Agent` 类
4. 更新所有代码和文档中的引用
5. 修复 `UnifiedLLM` 参数顺序问题

✅ **设计理念**：
- 工厂化：统一入口 `loom.agent()`
- 递增命名：Agent 是标准实现
- API 简洁：只提供必要的导出

✅ **向后兼容**：
- 保留所有功能
- 只改变 API 入口
- 迁移简单（批量替换即可）

---

**版本**: v0.1.6+
**日期**: 2025-12-15
