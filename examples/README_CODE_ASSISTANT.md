# Loom Code Assistant Demo

这个示例展示了Loom框架的核心能力，通过构建一个类似Claude Code的代码助手。

## 核心能力展示

### 1. 四层记忆系统（L1-L4）
- **L1 工作记忆**: 最近10条对话，自动包含在上下文中
- **L2 会话记忆**: 重要的会话事件（50条），24小时保留
- **L3 情节记忆**: 跨会话事件（200条），7天保留
- **L4 语义记忆**: 长期知识（1000条），永久保留

### 2. 工具系统
- `read_file`: 读取文件内容
- `list_files`: 列出目录中的文件
- `search_code`: 在代码中搜索关键词
- `analyze_code_structure`: 分析代码结构（类、函数、导入）

### 3. 多轮对话
- 保持上下文理解
- 记住之前的分析结果
- 自动引用历史信息

### 4. 自主决策
- Agent自动选择合适的工具
- 智能规划任务执行
- 持续反思和优化

## 使用方法

### 1. 配置环境

首先，确保已经安装了依赖：

```bash
poetry install
```

### 2. 配置API密钥

复制`.env.example`为`.env`并填入你的OpenAI API密钥：

```bash
cp .env.example .env
```

编辑`.env`文件：

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 运行示例

```bash
python examples/code_assistant_demo.py
```

## 演示内容

### 演示1: 基本使用
- 列出目录中的Python文件
- 分析代码文件的结构

### 演示2: 记忆系统
- 第1轮：搜索Agent类的位置
- 第2轮：基于记忆读取和分析文件
- 第3轮：测试记忆保持能力

### 演示3: 代码搜索
- 在代码库中搜索关键词
- 找到相关代码位置

### 演示4: 统计信息
- 显示Agent执行统计
- 显示记忆系统状态

## 预期输出

```
======================================================================
Loom Code Assistant Demo
展示Loom框架的核心能力
======================================================================

正在创建代码助手...
✓ 代码助手创建成功: code-assistant
✓ 工具数量: 8
✓ 记忆系统: 已启用（L1-L4四层记忆）

======================================================================
演示 1: 基本使用 - 文件读取和代码分析
======================================================================

[任务1] 列出examples目录的Python文件
状态: completed
结果: 文件列表 (examples/*.py):
  - autonomous_agent_demo.py
  - code_assistant_demo.py
  - ...

[任务2] 分析autonomous_agent_demo.py的代码结构
状态: completed
结果: 代码结构分析 (examples/autonomous_agent_demo.py):

导入 (5):
  L7: import asyncio
  L8: from loom.orchestration.agent import Agent
  ...

类 (1):
  L14: class MockLLMProvider(LLMProvider):
  ...

函数 (3):
  L16: async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
  L20: async def stream_chat(self, messages: list[dict], **kwargs):
  ...

======================================================================
演示 2: 记忆系统 - 多轮对话与上下文保持
======================================================================

[第1轮] 询问Agent类的位置
结果: 我找到了Agent类的定义，它位于loom/orchestration/agent.py文件中...

[第2轮] 基于记忆继续询问（测试L1工作记忆）
结果: 根据刚才的搜索结果，我来读取loom/orchestration/agent.py文件...

[第3轮] 测试记忆保持
结果: 我们刚才分析了Agent类，它位于loom/orchestration/agent.py文件中。主要方法包括...

======================================================================
演示 3: 代码搜索 - 在代码库中查找关键词
======================================================================

[任务] 搜索'LoomMemory'关键词
状态: completed
结果: 搜索结果 (关键词: LoomMemory):

loom/memory/core.py:15: class LoomMemory:
loom/memory/core.py:20:     def __init__(self, config: MemoryConfig):
...

======================================================================
演示 4: Agent统计信息
======================================================================

执行统计:
  - 总执行次数: 6
  - 成功次数: 6
  - 失败次数: 0
  - 成功率: 100.0%

记忆系统:
  - L1 (工作记忆): 10 项
  - L2 (会话记忆): 3 项
  - L3 (情节记忆): 0 项
  - L4 (语义记忆): 0 项

======================================================================
演示完成！
======================================================================

核心能力展示:
✓ 工具系统 - 文件读取、代码搜索、结构分析
✓ 记忆系统 - L1-L4四层记忆，自动迁移和压缩
✓ 多轮对话 - 保持上下文，记住之前的分析
✓ 自主决策 - Agent自动选择合适的工具
```

## 技术亮点

### 1. 记忆系统的自动迁移
- 频繁访问的任务自动从L1提升到L2
- 重要事件自动从L2提升到L3
- 长期知识自动从L3提升到L4

### 2. 工具的智能选择
- Agent根据任务自动选择合适的工具
- 无需手动指定工具调用
- 支持工具链式调用

### 3. 上下文的智能管理
- L1自动包含在每次LLM调用中
- L2-L4通过搜索工具按需访问
- 自动压缩和优化上下文

## 扩展建议

### 1. 添加更多工具
```python
async def write_file(file_path: str, content: str) -> str:
    """写入文件"""
    # 实现文件写入逻辑
    pass

async def run_tests(test_path: str) -> str:
    """运行测试"""
    # 实现测试运行逻辑
    pass
```

### 2. 集成外部知识库
```python
from loom.providers.knowledge import VectorKnowledgeBase

# 创建知识库
kb = VectorKnowledgeBase(embedding_provider, vector_store)

# 添加代码知识
await kb.add_item(KnowledgeItem(
    id="kb_1",
    content="Loom框架使用四层记忆系统...",
    source="Documentation"
))

# 配置到Agent
memory_config = MemoryConfig(knowledge_base=kb)
```

### 3. 启用向量搜索
```python
from loom.providers.embedding.openai import OpenAIEmbeddingProvider
from loom.memory.vector_store import InMemoryVectorStore

# 配置embedding
embedding_provider = OpenAIEmbeddingProvider(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="text-embedding-3-small"
)

vector_store = InMemoryVectorStore()

# 配置到记忆系统
memory_config = MemoryConfig(
    embedding_provider=embedding_provider,
    vector_store=vector_store,
    enable_l4_vector_search=True
)
```

## 相关文档

- [Memory System](../docs/features/memory-system.md)
- [Tool System](../docs/features/tool-system.md)
- [Context Management](../docs/framework/context-management.md)
- [API Reference](../docs/usage/api-reference.md)

## 常见问题

### Q: 为什么需要四层记忆？
A: 四层记忆模拟人类认知架构，实现了从短期到长期的自然过渡，避免了上下文溢出和信息丢失。

### Q: 工具是如何被选择的？
A: Agent通过LLM的tool calling能力自动选择工具，无需手动指定。

### Q: 如何自定义工具？
A: 参考`create_code_tools()`函数，定义async函数并注册到ToolRegistry即可。

### Q: 记忆系统会占用多少内存？
A: 默认配置下，L1-L4总共约1260条记录，每条记录约1KB，总计约1.2MB。

## 许可证

MIT License
