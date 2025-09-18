# Lexicon Agent Framework 使用指南

## 框架概述

Lexicon Agent Framework 是一个功能强大的多智能体协作框架，专为构建复杂的智能系统而设计。该框架提供了完整的智能体编排、上下文管理、工具调用和流式处理能力。

### 核心特性

🤖 **多智能体编排**：支持多个智能体的协调和协作
🧠 **智能上下文管理**：自动管理和优化上下文信息
🔧 **丰富的工具系统**：内置文件操作、知识库、代码执行等工具
🌊 **流式数据处理**：支持实时数据流处理和响应
🔒 **安全机制**：内置安全检查和权限控制
⚡ **高性能**：异步架构，支持并发处理
🔌 **可扩展性**：模块化设计，易于扩展和定制

## 快速开始

### 1. 基础导入

```python
import asyncio
from lexicon_agent.types import Agent, SessionState, ContextRequirements
from lexicon_agent.core.tools.registry import ToolRegistry
from lexicon_agent.core.orchestration.engine import OrchestrationEngine, UserInput, OrchestrationContext
```

### 2. 创建智能体

```python
# 创建智能体
agent = Agent(
    agent_id="my_agent_001",
    name="数据分析智能体",
    specialization="data_analysis",
    capabilities=["data_analysis", "file_operations", "reporting"],
    status="available",
    configuration={"max_concurrent_tasks": 3}
)
```

### 3. 初始化工具系统

```python
# 获取工具注册表
tool_registry = ToolRegistry()

# 查看可用工具
available_tools = tool_registry.list_tools()
print(f"可用工具: {available_tools}")

# 使用文件系统工具
fs_tool = tool_registry.get_tool("file_system")
result = await fs_tool.execute({
    "action": "read",
    "path": "data.txt"
})
```

### 4. 编排执行

```python
# 创建编排引擎
engine = OrchestrationEngine()

# 用户输入
user_input = UserInput(
    message="请分析数据文件并生成报告",
    context={"task_type": "data_analysis"}
)

# 创建编排上下文
context = OrchestrationContext(
    user_input=user_input,
    available_agents=[agent],
    session_context={"project": "sales_analysis"}
)

# 执行编排
result = await engine.orchestrate(user_input, [agent], context)
```

## 核心组件详解

### 1. 智能体系统 (Agent System)

#### 智能体定义

智能体是框架的核心执行单元，每个智能体具有特定的能力和专业化领域：

```python
from lexicon_agent.types import Agent

agent = Agent(
    agent_id="unique_id",           # 唯一标识符
    name="智能体名称",              # 显示名称
    specialization="domain",        # 专业化领域
    capabilities=[                  # 能力列表
        "data_analysis",
        "code_generation",
        "file_operations"
    ],
    status="available",             # 状态：available/busy/offline
    configuration={                 # 配置参数
        "max_tasks": 5,
        "timeout": 30
    }
)
```

#### 智能体管理

```python
from lexicon_agent.core.agent.controller import AgentController
from lexicon_agent.core.context import ContextRetrievalEngine, ContextProcessor, ContextManager

# 初始化依赖组件
context_engine = ContextRetrievalEngine()
context_processor = ContextProcessor()
context_manager = ContextManager()

# 创建智能体控制器
controller = AgentController(
    context_engine=context_engine,
    context_processor=context_processor,
    context_manager=context_manager
)

# 注册智能体
await controller.register_agent(agent)

# 生成响应流
async for event in controller.generate_response(user_input, session_context):
    if event.type == "response_delta":
        print(event.data["content"], end="")
```

### 2. 上下文管理 (Context Management)

#### 会话状态管理

```python
from lexicon_agent.types import SessionState

session_state = SessionState(
    session_id="session_001",
    context_memory={                # 上下文记忆
        "user_preferences": {"format": "json"},
        "previous_results": []
    },
    conversation_history=[          # 对话历史
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ],
    environment_state={             # 环境状态
        "working_directory": "/path/to/work",
        "available_resources": ["cpu", "memory"]
    }
)
```

#### 上下文检索

```python
from lexicon_agent.types import ContextRequirements
from lexicon_agent.core.context.management import ContextManager

# 定义上下文需求
requirements = ContextRequirements(
    strategies=["semantic_search", "rule_based"],
    max_tokens=2000,
    priorities=["relevance", "recency"]
)

# 管理上下文
context_manager = ContextManager()
managed_context = await context_manager.manage_context(
    session_state, 
    requirements
)
```

### 3. 工具系统 (Tool System)

#### 内置工具

框架提供多种内置工具：

**文件系统工具**
```python
fs_tool = tool_registry.get_tool("file_system")

# 读取文件
result = await fs_tool.execute({
    "action": "read",
    "path": "document.txt"
})

# 写入文件
result = await fs_tool.execute({
    "action": "write",
    "path": "output.txt",
    "content": "Hello, World!"
})

# 列出目录
result = await fs_tool.execute({
    "action": "list",
    "path": "/path/to/directory"
})
```

**知识库工具**
```python
kb_tool = tool_registry.get_tool("knowledge_base")

# 创建知识库
await kb_tool.execute({
    "action": "create",
    "kb_name": "my_knowledge_base",
    "description": "项目文档知识库"
})

# 添加文档
await kb_tool.execute({
    "action": "add",
    "kb_name": "my_knowledge_base",
    "title": "API文档",
    "text": "这是API使用说明...",
    "metadata": {"category": "documentation"}
})

# 搜索文档
result = await kb_tool.execute({
    "action": "search",
    "kb_name": "my_knowledge_base",
    "query": "API使用方法",
    "limit": 5
})
```

**代码解释器工具**
```python
code_tool = tool_registry.get_tool("code_interpreter")

# 执行Python代码
result = await code_tool.execute({
    "language": "python",
    "code": """
def hello_world():
    return "Hello, World!"

print(hello_world())
    """,
    "timeout": 10
})
```

#### 自定义工具

```python
from lexicon_agent.core.tools.registry import BaseTool
from lexicon_agent.types import ToolSafetyLevel

class CustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="custom_tool",
            description="自定义工具示例"
        )
    
    async def execute(self, input_data: dict) -> dict:
        # 实现工具逻辑
        return {
            "result": "Custom tool executed successfully",
            "input_received": input_data,
            "success": True
        }
    
    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "parameter": {"type": "string"}
            },
            "required": ["parameter"]
        }
    
    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.SAFE

# 注册自定义工具
custom_tool = CustomTool()
tool_registry.register_tool(custom_tool)
```

### 4. 流式处理 (Streaming)

#### 创建和管理流

```python
from lexicon_agent.core.streaming.processor import StreamingProcessor

processor = StreamingProcessor()

# 创建流
stream_id = "data_stream_001"
success = await processor.create_stream(stream_id, "json")

# 处理流数据
async for chunk in processor.process_stream(stream_id, data_iterator):
    print(f"处理块: {chunk.data}")

# 清理流
await processor._finalize_stream(stream_id, processor.processors["json"])
```

#### 流式管道

```python
from lexicon_agent.core.streaming.pipeline import StreamingPipeline

pipeline = StreamingPipeline()

# 创建处理管道
await pipeline.create_pipeline(
    pipeline_id="analysis_pipeline",
    stages=[
        {"name": "data_input", "processor": "json"},
        {"name": "analysis", "processor": "text"},
        {"name": "output", "processor": "event"}
    ]
)

# 执行管道
async for result in pipeline.execute_pipeline("analysis_pipeline", input_data):
    print(f"管道输出: {result}")
```

### 5. 编排引擎 (Orchestration)

#### 基础编排

```python
from lexicon_agent.core.orchestration.engine import OrchestrationEngine, UserInput, OrchestrationContext

engine = OrchestrationEngine()

# 创建用户输入
user_input = UserInput(
    message="请分析销售数据并生成月度报告，包括趋势分析和预测",
    context={"department": "sales", "period": "monthly"}
)

# 创建编排上下文
context = OrchestrationContext(
    user_input=user_input,
    available_agents=[data_agent, report_agent],
    session_context={"user_id": "user123"},
    constraints={"max_execution_time": 300}
)

# 执行编排
result = await engine.orchestrate(user_input, available_agents, context)
```

#### 工具编排

```python
from lexicon_agent.types import ToolCall, ManagedContext

# 准备工具调用
tool_calls = [
    ToolCall(
        tool_name="file_system",
        call_id="read_data",
        parameters={"action": "read", "path": "sales_data.csv"}
    ),
    ToolCall(
        tool_name="code_interpreter", 
        call_id="analyze_data",
        parameters={
            "language": "python",
            "code": "import pandas as pd; df = pd.read_csv('sales_data.csv'); print(df.describe())"
        }
    )
]

# 创建管理上下文
managed_context = ManagedContext(
    session_id="analysis_session",
    constraints={"memory_limit": "1GB"},
    metadata={"task": "data_analysis"}
)

# 执行工具编排
async for event in engine.orchestrate_tools(tool_calls, managed_context):
    print(f"工具执行事件: {event}")
```

## 高级功能

### 1. LLM 集成

框架支持多种LLM API的集成：

```python
import os
import aiohttp

class LLMIntegration:
    def __init__(self):
        self.api_key = os.getenv('LLM_API_KEY')
        self.base_url = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('LLM_MODEL', 'gpt-3.5-turbo')
    
    async def generate_response(self, prompt: str) -> dict:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
            
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                return await response.json()

# 使用示例
llm = LLMIntegration()
response = await llm.generate_response("解释量子计算的基本原理")
```

### 2. 配置管理

```python
from lexicon_agent.config import ConfigurationManager

# 加载配置
config_manager = ConfigurationManager()
await config_manager.load_configuration("config.yaml")

# 获取配置
db_config = config_manager.get_config_section("database")
llm_config = config_manager.get_config_section("llm")

# 动态更新配置
await config_manager.update_config("llm.model", "gpt-4")
```

### 3. 性能监控

```python
# 获取系统指标
metrics = await engine.get_orchestration_status()
print(f"活跃流程: {metrics['active_flows']}")
print(f"性能指标: {metrics['performance_metrics']}")

# 工具使用统计
tool_metrics = tool_registry.get_registry_statistics()
print(f"工具成功率: {tool_metrics['overall_success_rate']}")
```

## 部署和运行

### 1. 安装依赖

```bash
pip install aiohttp pydantic python-dotenv
```

### 2. 环境配置

创建 `.env` 文件：

```env
# LLM API配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 数据库配置（可选）
DATABASE_URL=sqlite:///lexicon.db

# 日志级别
LOG_LEVEL=INFO
```

### 3. 基础应用示例

```python
import asyncio
from lexicon_agent.main import main

async def run_application():
    """运行Lexicon Agent应用"""
    
    # 初始化组件
    tool_registry = ToolRegistry()
    engine = OrchestrationEngine()
    
    # 创建智能体
    assistant_agent = Agent(
        agent_id="assistant_001",
        name="通用助手",
        specialization="general",
        capabilities=["file_operations", "data_analysis", "code_generation"],
        status="available"
    )
    
    # 注册智能体和启动服务
    available_agents = [assistant_agent]
    
    # 主循环
    while True:
        user_message = input("请输入您的需求 (输入 'quit' 退出): ")
        if user_message.lower() == 'quit':
            break
        
        # 创建用户输入
        user_input = UserInput(message=user_message)
        
        # 创建编排上下文
        context = OrchestrationContext(
            user_input=user_input,
            available_agents=available_agents
        )
        
        # 执行编排
        result = await engine.orchestrate(user_input, available_agents, context)
        
        # 输出结果
        print(f"助手回复: {result.primary_result}")
        print(f"参与智能体: {len(result.participating_agents)}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(run_application())
```

## 最佳实践

### 1. 智能体设计

- **单一职责**：每个智能体专注于特定领域
- **能力明确**：清晰定义智能体的能力边界
- **状态管理**：及时更新智能体状态

### 2. 上下文管理

- **适量上下文**：避免上下文过载
- **定期清理**：清理过期的上下文信息
- **优先级管理**：合理设置上下文优先级

### 3. 工具使用

- **安全第一**：始终考虑工具的安全级别
- **错误处理**：实现完善的错误处理机制
- **性能监控**：监控工具执行性能

### 4. 流式处理

- **资源管理**：及时清理不用的流
- **并发控制**：合理控制并发流数量
- **错误恢复**：实现流处理错误恢复

## 故障排除

### 常见问题

1. **智能体注册失败**
   - 检查智能体ID是否唯一
   - 验证必需字段是否完整

2. **工具执行错误**
   - 检查输入参数格式
   - 验证工具权限设置

3. **上下文管理问题**
   - 检查上下文大小限制
   - 验证上下文格式正确性

4. **流式处理异常**
   - 检查流ID是否冲突
   - 验证处理器类型匹配

### 调试技巧

```python
import logging

# 启用调试日志
logging.basicConfig(level=logging.DEBUG)

# 查看组件状态
print("工具状态:", tool_registry.get_registry_statistics())
print("编排状态:", await engine.get_orchestration_status())
```

## 扩展开发

### 1. 自定义智能体

```python
class SpecializedAgent(Agent):
    def __init__(self, domain_config):
        super().__init__(
            agent_id=f"specialized_{domain_config['domain']}",
            name=f"{domain_config['domain']}专家",
            specialization=domain_config['domain'],
            capabilities=domain_config['capabilities']
        )
        self.domain_config = domain_config
    
    async def specialized_operation(self, task):
        # 实现专业化操作
        pass
```

### 2. 自定义编排策略

```python
from lexicon_agent.core.orchestration.strategies import OrchestrationStrategy

class CustomStrategy(OrchestrationStrategy):
    async def determine_agent_count(self, task_requirements):
        # 自定义智能体数量逻辑
        return min(3, task_requirements.get("complexity", 1))
    
    async def create_execution_plan(self, agents, context):
        # 自定义执行计划
        return {
            "strategy": "custom",
            "steps": ["analyze", "execute", "verify"],
            "parallel_execution": True
        }
```

## 总结

Lexicon Agent Framework 提供了构建复杂智能系统所需的完整基础设施。通过合理使用框架的各个组件，您可以快速构建出功能强大、可扩展的多智能体应用系统。

框架的模块化设计确保了高度的灵活性和可扩展性，同时内置的安全机制和性能优化保证了系统的稳定性和效率。

开始使用框架时，建议从简单的单智能体场景开始，逐步扩展到复杂的多智能体协作系统。