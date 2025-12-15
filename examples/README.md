# Loom Agent Examples

这个目录包含 Loom Agent 框架的集成示例和使用示例。

## 核心理念

Loom Agent 的核心框架**只依赖 Python 和 Pydantic**，不包含任何第三方服务的集成。所有集成（LLM 提供商、工具、Skills 等）都在这个 `examples/` 目录中作为**示例**提供，你可以根据需要复制和修改。

## 目录结构

```
examples/
├── integrations/       # 第三方服务集成示例
│   ├── openai_llm.py          # OpenAI LLM 集成
│   ├── compression.py         # 上下文压缩器
│   └── anthropic_llm.py       # (待添加) Anthropic LLM 集成
├── skills/            # 预设 Skills 示例
│   ├── pdf_analyzer/          # PDF 分析
│   ├── web_research/          # Web 研究
│   └── data_processor/        # 数据处理
├── tools/             # 工具示例
│   ├── calculator.py          # (待添加) 计算器工具
│   └── web_search.py          # (待添加) Web 搜索工具
├── agents/            # Agent 示例
│   ├── chatbot.py             # (待添加) 简单聊天机器人
│   └── research_agent.py      # (待添加) 研究型 Agent
└── crew/              # 多 Agent 协作示例
    └── research_team.py       # (待添加) 研究团队
```

## 快速开始

### 1. 核心框架（无需任何依赖）

核心框架只需要 Python 和 Pydantic：

```python
import loom, Message, tool

# 定义工具（无需外部依赖）
@tool(name="calculator")
async def calculator(expression: str) -> float:
    """计算数学表达式"""
    return eval(expression)

# 创建 Agent 需要一个 LLM，但核心框架不提供
# 你需要使用 examples 中的集成，或自己实现 BaseLLM Protocol
```

### 2. 使用 OpenAI LLM 集成

如果你想使用 OpenAI：

**步骤 1**：安装 OpenAI SDK

```bash
pip install openai
```

**步骤 2**：使用集成示例

```python
import loom, Message, tool
from examples.integrations.openai_llm import OpenAILLM

# 定义工具
@tool(name="calculator")
async def calculator(expression: str) -> float:
    return eval(expression)

# 创建 LLM
llm = OpenAILLM(api_key="sk-...")

# 创建 Agent
agent = loom.agent(
    name="assistant",
    llm=llm,
    tools=[calculator]
)

# 使用
message = Message(role="user", content="What's 2+2?")
response = await agent.run(message)
print(response.content)
```

### 3. 使用压缩器

如果你想使用上下文压缩：

```python
import loom, create_context_manager
from examples.integrations.openai_llm import OpenAILLM
from examples.integrations.compression import StructuredCompressor, CompressionConfig

# 创建压缩器
compressor = StructuredCompressor(
    config=CompressionConfig(threshold=0.9),
    keep_recent=6
)

# 创建带压缩的上下文管理器
context_mgr = create_context_manager(
    max_history=100,
    compressor=compressor
)

# 创建 Agent
llm = OpenAILLM(api_key="sk-...")
agent = loom.agent(
    name="assistant",
    llm=llm,
    context_manager=context_mgr
)
```

### 4. 使用预设 Skills

预设 Skills 也是示例，你可以复制到你的项目中使用：

```python
import loom
from examples.integrations.openai_llm import OpenAILLM

# 创建 Agent，指向 examples/skills 目录
agent = loom.agent(
    name="assistant",
    llm=OpenAILLM(api_key="sk-..."),
    enable_skills=True,
    skills_dir="./examples/skills"
)

# 列出可用的 Skills
skills = agent.list_skills()
for skill in skills:
    print(f"- {skill.metadata.name}: {skill.metadata.description}")
```

## 集成示例详解

### OpenAI LLM (`integrations/openai_llm.py`)

OpenAI LLM 集成示例，展示如何实现 `BaseLLM` Protocol。

**依赖**：
```bash
pip install openai
```

**特点**：
- 支持所有 OpenAI 模型（GPT-4, GPT-3.5, O1 等）
- 支持工具调用 (function calling)
- 支持 JSON 模式 (structured output)
- 支持流式生成

**用法**：
```python
from examples.integrations.openai_llm import OpenAILLM

llm = OpenAILLM(
    api_key="sk-...",
    model="gpt-4",
    temperature=0.7
)
```

### 压缩器 (`integrations/compression.py`)

简化版 8 段式结构化压缩器，不依赖 LLM。

**依赖**：无

**特点**：
- 基于规则的压缩，无需 LLM
- 8 段式结构化摘要
- 自动保留近端消息窗口

**用法**：
```python
from examples.integrations.compression import StructuredCompressor, CompressionConfig

compressor = StructuredCompressor(
    config=CompressionConfig(threshold=0.9),
    keep_recent=6
)
```

### 预设 Skills (`skills/`)

三个预设 Skills 示例：

#### 1. PDF Analyzer (`skills/pdf_analyzer/`)

PDF 文档分析 Skill。

**依赖**：
```bash
pip install pypdf2 pdfplumber
```

**功能**：
- 提取文本
- 提取表格
- 提取元数据

#### 2. Web Research (`skills/web_research/`)

Web 研究 Skill。

**依赖**：
```bash
pip install requests beautifulsoup4 selenium
```

**功能**：
- 搜索查询
- 网页抓取
- 动态内容处理

#### 3. Data Processor (`skills/data_processor/`)

数据处理 Skill。

**依赖**：
```bash
pip install pandas openpyxl
```

**功能**：
- CSV/Excel/JSON 处理
- 数据聚合
- 数据验证

## 如何创建自己的集成

### 1. 实现 LLM 集成

要集成其他 LLM 提供商（如 Anthropic, Cohere 等），实现 `BaseLLM` Protocol：

```python
from loom.interfaces import BaseLLM
from typing import AsyncGenerator, Dict, Any, List, Optional

class MyLLM:
    """实现 BaseLLM Protocol"""

    @property
    def model_name(self) -> str:
        """返回模型名称"""
        return "my-model"

    async def stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式生成接口

        Yields:
            事件字典，类型包括：
            - {"type": "content_delta", "content": "..."}
            - {"type": "tool_calls", "tool_calls": [...]}
            - {"type": "finish", "finish_reason": "stop"}
        """
        # 实现你的流式生成逻辑
        yield {"type": "content_delta", "content": "Hello"}
        yield {"type": "finish", "finish_reason": "stop"}
```

参考 `examples/integrations/openai_llm.py` 获取完整示例。

### 2. 实现 Compressor 集成

实现 `BaseCompressor` Protocol：

```python
from loom.interfaces import BaseCompressor
from loom.core import Message
from typing import List

class MyCompressor:
    """实现 BaseCompressor Protocol"""

    async def compress(self, messages: List[Message]) -> List[Message]:
        """压缩消息历史"""
        # 实现你的压缩逻辑
        return messages[-10:]  # 简单保留最近 10 条

    def should_compress(self, token_count: int, max_tokens: int) -> bool:
        """检查是否需要压缩"""
        return token_count > max_tokens * 0.8
```

参考 `examples/integrations/compression.py` 获取完整示例。

### 3. 创建自定义 Skill

创建 Skill 目录结构：

```
my_skill/
├── skill.yaml          # Skill 元数据
├── SKILL.md           # 详细文档
└── resources/         # 资源文件
    └── examples.json
```

参考 `examples/skills/` 中的示例。

## 为什么这样设计？

### 核心框架的设计原则

1. **专注核心机制**：框架只关注 Agent 的核心机制（递归状态机、消息协议、上下文管理、事件系统），不关注具体集成。

2. **极简依赖**：只依赖 Python 和 Pydantic，用户可以在任何环境中使用，无需安装大量不需要的包。

3. **灵活集成**：通过 Protocol（鸭子类型），用户可以轻松集成任何 LLM、工具、Memory 实现，无需继承特定基类。

4. **示例即文档**：Examples 目录提供完整的集成示例，用户可以直接复制使用或参考修改。

### 与其他框架的对比

| 框架 | 核心依赖 | LLM 集成 | 设计理念 |
|------|---------|---------|---------|
| **Loom Agent** | Python + Pydantic | 示例提供 | 核心机制 + 集成示例 |
| LangChain | 10+ 必需包 | 内置 | 大而全的工具箱 |
| AutoGen | OpenAI SDK 必需 | 内置 | Microsoft 生态 |
| CrewAI | 5+ 必需包 | 内置 | 多 Agent 预设 |

### 好处

1. **更小的安装体积**：核心框架只有 2 个依赖，安装速度快。

2. **更自由的选择**：你可以选择任何 LLM 提供商、任何工具，不受框架限制。

3. **更清晰的架构**：核心机制和集成实现分离，代码更清晰易懂。

4. **更容易维护**：框架核心不会因为某个集成的变化而需要更新。

5. **更适合生产环境**：你只需要安装你实际使用的依赖，减少供应链风险。

## 常见问题

### Q: 为什么不把 OpenAI LLM 放在核心框架中？

A: 因为不是所有用户都使用 OpenAI。有的用户使用 Anthropic, Cohere, 本地模型，或自己的 LLM 服务。把 OpenAI 放在核心会强制所有用户安装 `openai` 包，即使他们不需要。

### Q: 我可以把 examples 中的代码用在生产环境吗？

A: 当然可以！Examples 中的代码都是生产级别的，经过充分测试。你可以直接复制到你的项目中使用，或者根据需要修改。

### Q: 如何贡献新的集成示例？

A: 欢迎贡献！请参考现有示例的格式，创建 Pull Request。我们特别欢迎：
- 新的 LLM 提供商集成（Anthropic, Cohere, 等）
- 新的 Skill 示例
- 新的工具示例
- 新的 Agent 使用场景

### Q: 为什么 Skills 也是示例？

A: 因为 Skills 通常依赖特定的外部库。例如 `pdf_analyzer` 依赖 `pypdf2`, `web_research` 依赖 `selenium`。我们不希望强制用户安装这些库，除非他们真的需要这些功能。

### Q: 我需要实现所有 Protocol 方法吗？

A: 不需要。Python 的 Protocol 是基于鸭子类型的，只要你实现了必需的方法（如 `BaseLLM.stream()`），就可以工作。IDE 会提示你需要实现哪些方法。

## 相关资源

- [核心文档](../docs/README.md)
- [API 参考](../docs/api/README.md)
- [架构设计](../docs/architecture/overview.md)
- [快速开始](../docs/getting-started/quickstart.md)

## 许可证

与 Loom Agent 框架相同，采用 MIT 许可证。
