# Loom Agent 生产环境开发指南

**版本**: 0.0.3
**最后更新**: 2025-01-27
**目标读者**: 产品开发工程师

---

## 📋 目录

1. [核心能力概览](#核心能力概览)
2. [Context Assembly - 智能上下文管理](#context-assembly)
3. [TaskTool - 子代理系统](#tasktool)
4. [AgentEvent - 流式执行监控](#agentevent)
5. [智能 TT 递归 - 可扩展任务处理](#智能-tt-递归)
6. [统一协调机制 - 四大能力协同](#统一协调机制)
7. [完整产品示例](#完整产品示例)
8. [生产环境最佳实践](#生产环境最佳实践)

---

## 核心能力概览

Loom Agent 0.0.3 提供四大核心能力 + 统一协调机制：

### 1. **ContextAssembler** - 智能上下文组装
- 基于优先级的组件管理
- 自动 Token 预算控制
- 防止 RAG 上下文被覆盖
- 智能截断低优先级内容

### 2. **TaskTool** - 子代理执行
- 启动独立子任务
- 支持自定义 agent 类型
- 可配置工具权限
- 支持模型覆盖

### 3. **AgentEvent** - 流式事件系统
- 24 种事件类型
- 实时进度监控
- LLM 流式输出
- 工具执行追踪

### 4. **智能 TT 递归** - 可扩展任务处理
- 智能工具结果分析
- 任务类型识别和处理
- 动态递归指导生成
- 可扩展的任务处理器架构

### 5. **统一协调机制** - 四大能力协同
- 智能上下文在 TT 递归中组织复杂任务
- 跨组件的统一状态管理和性能优化
- 动态策略调整和资源分配
- 四大核心能力的深度集成

---

## Context Assembly

### 基本用法

```python
from loom.core.context_assembly import ContextAssembler, ComponentPriority

# 创建组装器（设置 token 预算）
assembler = ContextAssembler(max_tokens=8000)

# 添加基础指令（最高优先级，不可截断）
assembler.add_component(
    name="base_instructions",
    content="你是一个专业的代码审查助手。",
    priority=ComponentPriority.CRITICAL,  # 100
    truncatable=False
)

# 添加 RAG 检索内容（高优先级，可截断）
assembler.add_component(
    name="retrieved_docs",
    content=retrieved_doc_content,
    priority=ComponentPriority.HIGH,  # 90
    truncatable=True
)

# 添加工具定义（中等优先级）
assembler.add_component(
    name="tool_definitions",
    content=tool_descriptions,
    priority=ComponentPriority.MEDIUM,  # 70
    truncatable=False
)

# 添加示例（低优先级）
assembler.add_component(
    name="examples",
    content=example_content,
    priority=ComponentPriority.LOW,  # 50
    truncatable=True
)

# 组装最终 prompt
final_prompt = assembler.assemble()

# 查看组装摘要（调试用）
summary = assembler.get_summary()
print(f"Total tokens: {summary['total_tokens']}")
print(f"Components: {summary['component_count']}")
print(f"Was truncated: {summary['truncated']}")
```

### 优先级级别

```python
class ComponentPriority(IntEnum):
    CRITICAL = 100  # 必须包含：基础指令、核心配置
    HIGH = 90       # 重要内容：RAG 上下文、关键信息
    MEDIUM = 70     # 标准内容：工具定义、常规配置
    LOW = 50        # 次要内容：示例、提示
    OPTIONAL = 30   # 可选内容：额外说明
```

### 产品场景：RAG 问答系统

```python
import asyncio
from loom import Agent
from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.llm.factory import LLMFactory

async def rag_qa_system(user_query: str, retrieved_docs: list):
    """带 RAG 的问答系统"""

    # 1. 创建 LLM
    llm = LLMFactory.create_openai(
        api_key="sk-...",
        model="gpt-4"
    )

    # 2. 创建上下文组装器
    assembler = ContextAssembler(max_tokens=16000)

    # 3. 添加系统指令（最高优先级）
    assembler.add_component(
        "system_instructions",
        "你是一个基于文档的问答助手。请根据提供的文档内容回答问题。",
        ComponentPriority.CRITICAL,
        truncatable=False
    )

    # 4. 添加检索到的文档（高优先级，防止被截断）
    doc_content = "\n\n".join([
        f"【文档 {i+1}】\n{doc['content']}"
        for i, doc in enumerate(retrieved_docs)
    ])
    assembler.add_component(
        "retrieved_documents",
        f"相关文档内容：\n\n{doc_content}",
        ComponentPriority.HIGH,
        truncatable=True  # 如果太长可以截断
    )

    # 5. 添加回答指南（中等优先级）
    assembler.add_component(
        "answer_guidelines",
        "请遵循以下规则：\n1. 优先使用文档内容\n2. 引用具体段落\n3. 承认不知道的内容",
        ComponentPriority.MEDIUM,
        truncatable=True
    )

    # 6. 组装最终 system prompt
    system_prompt = assembler.assemble()

    # 7. 创建 agent 并执行
    agent = Agent(
        llm=llm,
        system_instructions=system_prompt
    )

    result = await agent.run(user_query)

    # 8. 返回结果和元信息
    summary = assembler.get_summary()
    return {
        "answer": result,
        "context_info": {
            "total_tokens": summary["total_tokens"],
            "truncated": summary["truncated"],
            "components_included": summary["component_count"]
        }
    }

# 使用示例
if __name__ == "__main__":
    docs = [
        {"content": "Loom Agent 是一个生产级的 Python Agent 框架..."},
        {"content": "ContextAssembler 提供智能上下文管理..."}
    ]

    result = asyncio.run(
        rag_qa_system("Loom Agent 的核心特性是什么？", docs)
    )

    print(result["answer"])
    print(f"\n使用 tokens: {result['context_info']['total_tokens']}")
```

---

## TaskTool

### 基本用法

```python
from loom import Agent, tool
from loom.builtin.tools import TaskTool
from loom.llm.factory import LLMFactory

# 1. 创建主 Agent
def create_agent(max_iterations=20, **kwargs):
    """Agent 工厂函数"""
    llm = LLMFactory.create_openai(
        api_key="sk-...",
        model="gpt-4"
    )
    return Agent(llm=llm, max_iterations=max_iterations, **kwargs)

# 2. 创建 TaskTool
task_tool = TaskTool(
    agent_factory=create_agent,
    max_iterations=10  # 子 agent 的最大迭代次数
)

# 3. 创建主 agent（带 TaskTool）
main_agent = create_agent(tools=[task_tool])

# 4. 使用子任务
result = await main_agent.run("""
分析这个项目的代码质量，包括：
1. 使用子任务统计代码行数
2. 使用子任务检查是否有 TODO 注释
3. 使用子任务分析函数命名规范
""")
```

### 使用 Agent Packs（预定义子代理类型）

```python
from loom.agents.registry import register_agent_spec
from loom.agents.refs import AgentSpec

# 1. 注册自定义 agent 类型
register_agent_spec(
    AgentSpec(
        agent_type="code-reviewer",
        system_instructions="""
        你是一个代码审查专家。
        请检查代码的：
        - 命名规范
        - 注释质量
        - 错误处理
        """,
        tools=["read_file", "grep"],  # 限制只能使用这些工具
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="security-auditor",
        system_instructions="""
        你是一个安全审计专家。
        请检查潜在的安全问题。
        """,
        tools=["read_file", "grep", "bash"],
        model_name="gpt-4"
    )
)

# 2. 使用预定义的 agent 类型
task_tool = TaskTool(agent_factory=create_agent)
main_agent = create_agent(tools=[task_tool])

result = await main_agent.run("""
请使用 code-reviewer 类型的子代理审查 src/main.py 文件。
然后使用 security-auditor 类型的子代理检查安全问题。
""")
```

### 产品场景：多步骤数据分析

```python
from loom import Agent
from loom.builtin.tools import TaskTool, ReadFileTool, WriteTool
from loom.llm.factory import LLMFactory
from loom.agents.registry import register_agent_spec
from loom.agents.refs import AgentSpec

# 1. 注册专业化的子代理
register_agent_spec(
    AgentSpec(
        agent_type="data-cleaner",
        system_instructions="""
        你是数据清洗专家。
        任务：读取原始数据，清洗异常值，输出清洗后的数据。
        """,
        tools=["read_file", "write_file", "python_repl"],
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="data-analyzer",
        system_instructions="""
        你是数据分析专家。
        任务：分析数据，生成统计报告。
        """,
        tools=["read_file", "python_repl", "write_file"],
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="report-writer",
        system_instructions="""
        你是报告撰写专家。
        任务：基于分析结果，生成易懂的报告。
        """,
        tools=["read_file", "write_file"],
        model_name="gpt-4"
    )
)

# 2. 创建数据分析流水线
async def data_analysis_pipeline(raw_data_path: str):
    """完整的数据分析流水线"""

    def agent_factory(max_iterations=20, **kwargs):
        llm = LLMFactory.create_openai(api_key="sk-...", model="gpt-4")
        return Agent(llm=llm, max_iterations=max_iterations, **kwargs)

    # 创建主协调器
    coordinator = agent_factory(
        tools=[
            TaskTool(agent_factory=agent_factory),
            ReadFileTool(),
            WriteTool()
        ],
        system_instructions="你是数据分析流水线的协调器。"
    )

    # 执行多步骤分析
    result = await coordinator.run(f"""
    请完成以下数据分析任务：

    1. 使用 data-cleaner 子代理清洗数据文件 {raw_data_path}
       输出到 cleaned_data.csv

    2. 使用 data-analyzer 子代理分析 cleaned_data.csv
       输出统计结果到 analysis_results.json

    3. 使用 report-writer 子代理生成最终报告
       输出到 final_report.md

    请逐步完成，并报告每一步的结果。
    """)

    return result

# 使用
result = await data_analysis_pipeline("raw_sales_data.csv")
print(result)
```

### TaskTool 高级特性

```python
# 1. 动态模型选择
result = await main_agent.run("""
使用 gpt-4 模型的子代理分析复杂逻辑。
使用 gpt-3.5-turbo 模型的子代理生成简单总结。
""")

# 2. 工具权限控制
register_agent_spec(
    AgentSpec(
        agent_type="read-only-analyzer",
        system_instructions="只读分析器",
        tools=["read_file", "grep", "glob"],  # 只允许读操作
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="writer",
        system_instructions="写入器",
        tools=["write_file"],  # 只允许写操作
        model_name="gpt-4"
    )
)

# 3. 嵌套子任务（子代理启动子代理）
register_agent_spec(
    AgentSpec(
        agent_type="project-manager",
        system_instructions="项目管理器，可以分配子任务",
        tools=["task", "read_file", "write_file"],  # 包含 task 工具
        model_name="gpt-4"
    )
)
```

---

## AgentEvent

### 基本流式执行

```python
from loom import Agent
from loom.core.events import AgentEventType, EventCollector
from loom.llm.factory import LLMFactory

async def streaming_execution():
    """流式执行示例"""

    llm = LLMFactory.create_openai(api_key="sk-...", model="gpt-4")
    agent = Agent(llm=llm, tools=my_tools)

    # 流式执行并处理事件
    async for event in agent.execute("分析这个项目"):

        # 1. LLM 输出流
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

        # 2. 工具执行开始
        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            print(f"\n[工具] 正在调用: {event.tool_call.name}")
            print(f"[工具] 参数: {event.tool_call.arguments}")

        # 3. 工具执行进度
        elif event.type == AgentEventType.TOOL_PROGRESS:
            status = event.metadata.get('status', '')
            print(f"[工具] 进度: {status}")

        # 4. 工具执行结果
        elif event.type == AgentEventType.TOOL_RESULT:
            result = event.tool_result
            print(f"[工具] 完成: {result.tool_name}")
            print(f"[工具] 耗时: {result.execution_time_ms:.1f}ms")

        # 5. 执行完成
        elif event.type == AgentEventType.AGENT_FINISH:
            print(f"\n✓ 完成: {event.content}")
```

### 事件类型完整列表

```python
# 阶段事件
PHASE_START                # 阶段开始
PHASE_END                  # 阶段结束

# 上下文事件
CONTEXT_ASSEMBLY_START     # 上下文组装开始
CONTEXT_ASSEMBLY_COMPLETE  # 上下文组装完成
COMPRESSION_APPLIED        # 历史压缩

# 检索事件（RAG）
RETRIEVAL_START            # 检索开始
RETRIEVAL_PROGRESS         # 检索进度
RETRIEVAL_COMPLETE         # 检索完成

# LLM 事件
LLM_START                  # LLM 请求开始
LLM_DELTA                  # LLM 流式输出（每个 token）
LLM_COMPLETE               # LLM 输出完成
LLM_TOOL_CALLS             # LLM 决定使用工具

# 工具事件
TOOL_EXECUTION_START       # 工具开始执行
TOOL_PROGRESS              # 工具执行进度
TOOL_RESULT                # 工具执行结果
TOOL_ERROR                 # 工具执行错误

# 迭代事件
ITERATION_START            # 新一轮迭代
MAX_ITERATIONS_REACHED     # 达到最大迭代

# 错误和恢复
ERROR                      # 错误发生
RECOVERY_ATTEMPT           # 尝试恢复
RECOVERY_SUCCESS           # 恢复成功

# 完成事件
AGENT_FINISH               # Agent 执行完成
```

### 产品场景：进度追踪 UI

```python
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class ExecutionProgress:
    """执行进度状态"""
    current_phase: str = ""
    llm_output: str = ""
    tools_executed: list = None
    total_tokens: int = 0
    errors: list = None

    def __post_init__(self):
        if self.tools_executed is None:
            self.tools_executed = []
        if self.errors is None:
            self.errors = []

class ProgressTracker:
    """进度追踪器（用于 UI 更新）"""

    def __init__(self):
        self.progress = ExecutionProgress()
        self.event_history = []

    async def track_execution(self, agent, prompt: str):
        """追踪 agent 执行并更新进度"""

        async for event in agent.execute(prompt):
            # 记录事件
            self.event_history.append(event)

            # 更新进度状态
            if event.type == AgentEventType.PHASE_START:
                self.progress.current_phase = event.phase
                await self._update_ui(f"开始阶段: {event.phase}")

            elif event.type == AgentEventType.LLM_DELTA:
                self.progress.llm_output += event.content
                await self._update_ui_stream(event.content)

            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                tool_info = {
                    "name": event.tool_call.name,
                    "status": "running",
                    "start_time": event.timestamp
                }
                self.progress.tools_executed.append(tool_info)
                await self._update_ui(f"执行工具: {event.tool_call.name}")

            elif event.type == AgentEventType.TOOL_RESULT:
                # 更新最后一个工具的状态
                if self.progress.tools_executed:
                    self.progress.tools_executed[-1]["status"] = "completed"
                    self.progress.tools_executed[-1]["duration"] = \
                        event.tool_result.execution_time_ms
                await self._update_ui(
                    f"工具完成: {event.tool_result.tool_name} "
                    f"({event.tool_result.execution_time_ms:.1f}ms)"
                )

            elif event.type == AgentEventType.ERROR:
                error_info = {
                    "message": str(event.error),
                    "timestamp": event.timestamp,
                    "recoverable": event.metadata.get('recoverable', False)
                }
                self.progress.errors.append(error_info)
                await self._update_ui(f"错误: {error_info['message']}")

            elif event.type == AgentEventType.AGENT_FINISH:
                await self._update_ui("执行完成！")
                break

        return self.progress

    async def _update_ui(self, message: str):
        """更新 UI（实际项目中可以是 WebSocket 推送）"""
        print(f"[UI 更新] {message}")

    async def _update_ui_stream(self, content: str):
        """流式更新 UI"""
        print(content, end="", flush=True)

    def get_summary(self) -> dict:
        """获取执行摘要"""
        return {
            "total_events": len(self.event_history),
            "tools_used": len(self.progress.tools_executed),
            "errors_occurred": len(self.progress.errors),
            "final_output": self.progress.llm_output,
            "phases_completed": list(set([
                e.phase for e in self.event_history
                if hasattr(e, 'phase') and e.phase
            ]))
        }

# 使用示例
async def main():
    llm = LLMFactory.create_openai(api_key="sk-...", model="gpt-4")
    agent = Agent(llm=llm, tools=my_tools)

    tracker = ProgressTracker()
    progress = await tracker.track_execution(
        agent,
        "分析项目代码并生成质量报告"
    )

    # 获取摘要
    summary = tracker.get_summary()
    print(f"\n\n执行摘要:")
    print(f"- 总事件数: {summary['total_events']}")
    print(f"- 使用工具数: {summary['tools_used']}")
    print(f"- 错误数: {summary['errors_occurred']}")

asyncio.run(main())
```

### 事件收集和分析

```python
from loom.core.events import EventCollector

async def analyze_execution():
    """分析 agent 执行过程"""

    collector = EventCollector()

    # 执行并收集所有事件
    async for event in agent.execute(prompt):
        collector.add(event)

        # 实时显示 LLM 输出
        if event.type == AgentEventType.LLM_DELTA:
            print(event.content, end="", flush=True)

    # 事后分析
    print("\n\n=== 执行分析 ===")

    # 1. 获取 LLM 完整输出
    llm_content = collector.get_llm_content()
    print(f"LLM 输出长度: {len(llm_content)} 字符")

    # 2. 获取所有工具结果
    tool_results = collector.get_tool_results()
    print(f"执行工具数: {len(tool_results)}")
    for result in tool_results:
        print(f"  - {result.tool_name}: {result.execution_time_ms:.1f}ms")

    # 3. 获取错误
    errors = collector.get_errors()
    if errors:
        print(f"错误数: {len(errors)}")
        for error in errors:
            print(f"  - {type(error).__name__}: {str(error)}")

    # 4. 筛选特定类型事件
    tool_events = collector.filter(AgentEventType.TOOL_EXECUTION_START)
    print(f"工具调用事件数: {len(tool_events)}")

    # 5. 获取最终结果
    final_response = collector.get_final_response()
    print(f"\n最终响应: {final_response}")

    return collector
```

---

## 智能 TT 递归

### 核心概念

Loom Agent 的 TT（Tail-Recursive）递归系统提供了智能的任务处理能力，能够根据工具执行结果动态调整递归策略，为开发者提供可扩展的任务处理器架构。

### 基本用法

```python
from loom.core.agent_executor import AgentExecutor, TaskHandler
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message
from typing import Dict, Any

# 1. 创建自定义任务处理器
class SQLTaskHandler(TaskHandler):
    """SQL 任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        """判断是否为 SQL 相关任务"""
        sql_keywords = ["sql", "query", "select", "database", "表", "查询", "数据库"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in sql_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成 SQL 任务的递归指导"""
        
        if result_analysis["has_errors"]:
            return f"""工具执行遇到问题。请重新尝试完成 SQL 任务：{original_task}

建议：
- 检查工具参数是否正确
- 尝试使用不同的方法获取数据
- 如果问题持续，请说明具体错误"""
        
        elif result_analysis["has_data"] and result_analysis["completeness_score"] >= 0.6:
            return f"""工具调用已完成，已获取到所需的数据信息。现在请基于这些数据生成最终的 SQL 查询语句。

重要提示：
- 不要继续调用工具
- 直接生成完整的 SQL 查询
- 确保 SQL 语法正确
- 包含适当的注释说明查询目的

原始任务：{original_task}"""
        
        elif recursion_depth >= 5:
            return f"""已达到较深的递归层级。请基于当前可用的信息生成 SQL 查询。

如果信息不足，请说明需要哪些额外信息。

原始任务：{original_task}"""
        
        else:
            return f"""继续处理 SQL 任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：使用更多工具收集相关信息，或分析已获得的数据"""

# 2. 创建 AgentExecutor 并传入自定义处理器
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    task_handlers=[SQLTaskHandler()]  # 传入自定义处理器
)

# 3. 执行任务
turn_state = TurnState.initial(max_iterations=10)
context = ExecutionContext.create()
messages = [Message(role="user", content="生成用户统计的 SQL 查询")]

async for event in executor.tt(messages, turn_state, context):
    # 处理事件...
    pass
```

### 任务处理器基类

```python
class TaskHandler:
    """
    任务处理器基类
    
    开发者可以继承此类来实现自定义的任务处理逻辑
    """
    
    def can_handle(self, task: str) -> bool:
        """
        判断是否能处理给定的任务
        
        Args:
            task: 任务描述
            
        Returns:
            bool: 是否能处理此任务
        """
        raise NotImplementedError
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """
        生成递归指导消息
        
        Args:
            original_task: 原始任务
            result_analysis: 工具结果分析
            recursion_depth: 递归深度
            
        Returns:
            str: 生成的指导消息
        """
        raise NotImplementedError
```

### 工具结果分析

框架会自动分析工具执行结果，提供以下分析信息：

```python
result_analysis = {
    "has_data": False,           # 是否包含数据
    "has_errors": False,         # 是否有错误
    "suggests_completion": False, # 是否建议完成
    "result_types": [],          # 结果类型列表
    "completeness_score": 0.0    # 完成度评分 (0.0-1.0)
}
```

### 产品场景：多领域任务处理

```python
from loom.core.agent_executor import AgentExecutor, TaskHandler
from loom.llm.factory import LLMFactory
from typing import Dict, Any

class AnalysisTaskHandler(TaskHandler):
    """分析任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        analysis_keywords = ["analyze", "analysis", "examine", "review", "分析", "检查", "评估"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in analysis_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["suggests_completion"] or result_analysis["completeness_score"] >= 0.8:
            return f"""信息收集基本完成。请基于已收集的信息完成分析任务：{original_task}

请提供：
1. 关键发现和洞察
2. 数据支持的分析结论  
3. 建议或推荐行动
4. 任何需要注意的限制或风险"""
        
        elif result_analysis["has_errors"]:
            return f"""分析过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查数据源是否可用
- 尝试不同的分析方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续分析任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多数据或使用分析工具处理已获得的信息"""

class CodeGenerationTaskHandler(TaskHandler):
    """代码生成任务处理器"""
    
    def can_handle(self, task: str) -> bool:
        generation_keywords = ["generate", "create", "build", "make", "生成", "创建", "构建", "开发"]
        task_lower = task.lower()
        return any(keyword in task_lower for keyword in generation_keywords)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        if result_analysis["completeness_score"] >= 0.7:
            return f"""信息收集完成。请基于收集到的信息生成代码完成任务：{original_task}

请提供：
- 完整的代码实现
- 必要的注释和文档
- 使用说明或示例"""
        
        elif result_analysis["has_errors"]:
            return f"""代码生成过程中遇到问题。请重新尝试完成任务：{original_task}

建议：
- 检查模板或参考代码是否可用
- 尝试不同的生成方法
- 如果问题持续，请说明具体错误"""
        
        else:
            return f"""继续代码生成任务：{original_task}

当前进度：{result_analysis['completeness_score']:.0%}
建议：收集更多参考信息或使用代码分析工具"""

class CustomTaskHandler(TaskHandler):
    """自定义任务处理器示例"""
    
    def __init__(self, task_patterns: list[str], guidance_template: str):
        """
        初始化自定义任务处理器
        
        Args:
            task_patterns: 任务匹配模式列表
            guidance_template: 指导消息模板
        """
        self.task_patterns = task_patterns
        self.guidance_template = guidance_template
    
    def can_handle(self, task: str) -> bool:
        """判断是否能处理给定任务"""
        task_lower = task.lower()
        return any(pattern.lower() in task_lower for pattern in self.task_patterns)
    
    def generate_guidance(
        self,
        original_task: str,
        result_analysis: Dict[str, Any],
        recursion_depth: int
    ) -> str:
        """生成自定义指导消息"""
        
        # 使用模板生成指导消息
        guidance = self.guidance_template.format(
            original_task=original_task,
            completeness_score=result_analysis['completeness_score'],
            has_data=result_analysis['has_data'],
            has_errors=result_analysis['has_errors'],
            recursion_depth=recursion_depth
        )
        
        return guidance

# 创建多领域任务处理系统
def create_multi_domain_system(api_key: str):
    """创建多领域任务处理系统"""
    
    llm = LLMFactory.create_openai(api_key=api_key, model="gpt-4")
    
    # 创建自定义任务处理器
    task_handlers = [
        SQLTaskHandler(),
        AnalysisTaskHandler(),
        CodeGenerationTaskHandler(),
        
        # 自定义报告生成处理器
        CustomTaskHandler(
            task_patterns=["report", "报告", "summary", "总结"],
            guidance_template="""继续生成报告任务：{original_task}

当前进度：{completeness_score:.0%}
状态：{'有数据' if has_data else '无数据'}, {'有错误' if has_errors else '无错误'}
递归深度：{recursion_depth}

建议：{'基于已有数据生成报告' if has_data else '收集更多数据'}"""
        ),
        
        # 自定义测试任务处理器
        CustomTaskHandler(
            task_patterns=["test", "测试", "testing"],
            guidance_template="""继续测试任务：{original_task}

进度：{completeness_score:.0%}
{'发现错误，需要修复' if has_errors else '测试正常进行'}
深度：{recursion_depth}

下一步：{'修复发现的问题' if has_errors else '继续执行测试'}"""
        ),
    ]
    
    # 创建执行器
    executor = AgentExecutor(
        llm=llm,
        tools=tools,
        task_handlers=task_handlers
    )
    
    return executor

# 使用示例
async def main():
    executor = create_multi_domain_system("sk-...")
    
    # 测试不同类型的任务
    test_tasks = [
        "生成用户统计的 SQL 查询",
        "分析代码质量",
        "创建 REST API",
        "生成项目报告",
        "测试系统功能"
    ]
    
    for task in test_tasks:
        print(f"\n处理任务: {task}")
        
        turn_state = TurnState.initial(max_iterations=10)
        context = ExecutionContext.create()
        messages = [Message(role="user", content=task)]
        
        async for event in executor.tt(messages, turn_state, context):
            if event.type.value == "agent_finish":
                print(f"完成: {event.content}")
                break
```

### 智能递归特性

#### 1. 自动任务类型识别
- 基于关键词匹配识别任务类型
- 支持中英文混合识别
- 可扩展的匹配模式

#### 2. 工具结果智能分析
- 自动检测数据类型、错误、完成建议
- 计算任务完成度评分
- 提供详细的结果类型分析

#### 3. 动态递归策略
- 根据工具结果质量调整策略
- 基于递归深度控制行为
- 保持原始任务上下文

#### 4. 可扩展架构
- 开发者可自定义任务处理器
- 支持模板化指导生成
- 框架自动选择匹配的处理器

### 最佳实践

```python
# ✅ 推荐：创建专门的任务处理器
class DomainSpecificHandler(TaskHandler):
    def can_handle(self, task: str) -> bool:
        # 精确的领域匹配逻辑
        return self._is_domain_task(task)
    
    def generate_guidance(self, original_task, result_analysis, recursion_depth):
        # 领域特定的指导逻辑
        return self._generate_domain_guidance(...)

# ✅ 推荐：使用模板化处理器
template_handler = CustomTaskHandler(
    task_patterns=["特定关键词"],
    guidance_template="领域特定的指导模板"
)

# ❌ 不推荐：硬编码任务类型
# 框架层不应该硬编码特定的任务类型
```

---

## 统一协调机制

### 核心概念

Loom Agent 0.0.3 的统一协调机制实现了四大核心能力的深度集成，让它们能够协同工作而非各自为战。通过智能协调器，框架能够：

1. **智能上下文在 TT 递归中组织复杂任务**
2. **动态调整策略和资源分配**
3. **统一的状态管理和性能优化**
4. **跨组件的协调和通信**

### 基本用法

```python
from loom.core.agent_executor import AgentExecutor
from loom.core.unified_coordination import UnifiedExecutionContext, IntelligentCoordinator
from loom.llm.factory import LLMFactory

# 1. 创建启用统一协调的执行器
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    enable_unified_coordination=True  # 启用统一协调
)

# 2. 执行复杂任务时，四大能力会自动协同工作
async for event in executor.tt(messages, turn_state, context):
    # ContextAssembler 会根据 TT 递归状态动态调整优先级
    # TaskTool 的子代理会复用主代理的智能上下文
    # EventProcessor 会智能过滤和批量处理事件
    # TaskHandler 会根据任务类型生成智能指导
    pass
```

### 统一执行上下文

```python
from loom.core.unified_coordination import UnifiedExecutionContext

# 创建统一执行上下文
unified_context = UnifiedExecutionContext(
    execution_id="task_001",
    enable_cross_component_optimization=True,
    enable_dynamic_strategy_adjustment=True,
    enable_unified_monitoring=True
)

# 创建执行器时传入统一上下文
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    unified_context=unified_context,
    enable_unified_coordination=True
)
```

### 智能协调器特性

#### 1. 任务类型识别和复杂度评估

```python
# 协调器会自动分析任务
task_analysis = {
    "task_type": "analysis",        # 分析、生成、SQL、测试等
    "complexity_score": 0.7,        # 0.0-1.0 复杂度评分
    "recursion_context": {          # 递归上下文
        "turn_counter": 3,
        "max_iterations": 10,
        "task_type": "analysis",
        "complexity": 0.7
    }
}
```

#### 2. 动态上下文策略调整

```python
# 基于任务类型和递归深度自动调整策略
if task_type == "analysis" and complexity > 0.7:
    # 复杂分析任务需要更多示例和指导
    assembler.adjust_priority("examples", ComponentPriority.MEDIUM)
    assembler.adjust_priority("analysis_guidelines", ComponentPriority.HIGH)

elif recursion_depth > 3:
    # 深度递归时，优先保留核心指令
    assembler.adjust_priority("base_instructions", ComponentPriority.CRITICAL)
    assembler.adjust_priority("tool_definitions", ComponentPriority.HIGH)
```

#### 3. 智能子代理策略

```python
# 基于任务复杂度决定是否使用子代理
if complexity > 0.7:
    strategy = {
        "use_sub_agents": True,
        "parallel_execution": True,
        "subagent_types": ["code-analyzer", "quality-checker"]
    }
```

### 产品场景：智能任务协调系统

```python
import asyncio
from loom.core.agent_executor import AgentExecutor
from loom.core.unified_coordination import UnifiedExecutionContext
from loom.core.turn_state import TurnState
from loom.core.execution_context import ExecutionContext
from loom.core.types import Message
from loom.llm.factory import LLMFactory

class IntelligentTaskCoordinator:
    """智能任务协调系统"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = LLMFactory.create_openai(api_key=api_key, model="gpt-4")
    
    async def coordinate_complex_task(self, task_description: str):
        """协调复杂任务执行"""
        
        # 1. 创建统一执行上下文
        unified_context = UnifiedExecutionContext(
            execution_id=f"task_{int(time.time())}",
            enable_cross_component_optimization=True,
            enable_dynamic_strategy_adjustment=True,
            enable_unified_monitoring=True
        )
        
        # 2. 创建增强的执行器
        executor = AgentExecutor(
            llm=self.llm,
            tools=tools,
            unified_context=unified_context,
            enable_unified_coordination=True
        )
        
        # 3. 执行任务
        turn_state = TurnState.initial(max_iterations=20)
        context = ExecutionContext.create()
        messages = [Message(role="user", content=task_description)]
        
        print(f"开始协调执行任务: {task_description}\n")
        
        async for event in executor.tt(messages, turn_state, context):
            # 处理事件...
            if event.type.value == "agent_finish":
                print(f"\n✓ 任务完成: {event.content}")
                
                # 获取统一性能指标
                metrics = executor.get_unified_metrics()
                print(f"\n📊 性能指标:")
                print(f"- 任务类型: {metrics['task_analysis']['task_type']}")
                print(f"- 复杂度评分: {metrics['task_analysis']['complexity_score']:.2f}")
                print(f"- 递归深度: {metrics['task_analysis']['recursion_context']['turn_counter']}")
                
                if "context_assembler" in metrics:
                    ca_metrics = metrics["context_assembler"]
                    print(f"- 上下文组件数: {ca_metrics['component_count']}")
                    print(f"- Token 使用率: {ca_metrics['budget_utilization']:.1%}")
                
                if "task_tool" in metrics:
                    tt_metrics = metrics["task_tool"]
                    print(f"- 子代理池大小: {tt_metrics['pool_size']}")
                    print(f"- 缓存命中率: {tt_metrics['cache_hit_rate']:.1%}")
                
                break
        
        return executor.get_unified_metrics()

# 使用示例
async def main():
    coordinator = IntelligentTaskCoordinator("sk-...")
    
    # 测试不同类型的复杂任务
    complex_tasks = [
        "分析项目代码质量，包括安全性、性能和可维护性",
        "生成用户行为分析报告，需要处理多个数据源",
        "创建完整的 REST API 系统，包括文档和测试",
        "优化数据库查询性能，分析慢查询并提供解决方案"
    ]
    
    for task in complex_tasks:
        print(f"\n{'='*60}")
        metrics = await coordinator.coordinate_complex_task(task)
        print(f"{'='*60}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

### 跨组件优化

#### 1. ContextAssembler 与 TT 递归集成

```python
# ContextAssembler 可以感知 TT 递归状态
def smart_add_component(name: str, content: str, priority: int, 
                       truncatable: bool = True, 
                       context_hint: Optional[str] = None):
    """智能添加上下文组件"""
    # 基于当前任务类型调整优先级
    adjusted_priority = coordinator._adjust_priority_by_context(
        priority, context_hint
    )
    
    # 基于递归状态调整可截断性
    adjusted_truncatable = coordinator._adjust_truncatability_by_recursion(
        truncatable
    )
    
    assembler.add_component(
        name, content, adjusted_priority, adjusted_truncatable
    )
```

#### 2. TaskTool 与上下文组装集成

```python
# TaskTool 的子代理可以复用主代理的智能上下文
def smart_create_subagent(subagent_type: str, 
                         context_requirements: Dict[str, Any]):
    """智能创建子代理"""
    # 基于上下文需求调整子代理配置
    adjusted_config = coordinator._adjust_subagent_config(
        subagent_type, context_requirements
    )
    
    return task_tool._create_subagent_with_config(adjusted_config)
```

#### 3. EventProcessor 与所有组件集成

```python
# EventProcessor 可以基于上下文调整处理策略
def smart_process_events(events: List, 
                         context: Dict[str, Any]):
    """智能处理事件"""
    # 基于上下文调整处理策略
    adjusted_events = coordinator._adjust_events_by_context(events, context)
    
    return processor.process_events(adjusted_events)
```

### 动态策略调整

```python
class DynamicStrategyAdjuster:
    """动态策略调整器"""
    
    def __init__(self, coordinator: IntelligentCoordinator):
        self.coordinator = coordinator
        self.strategy_history = []
    
    def adjust_strategy_based_on_performance(self, 
                                           current_metrics: Dict[str, Any],
                                           target_performance: Dict[str, Any]):
        """基于性能指标动态调整策略"""
        
        # 分析性能瓶颈
        bottlenecks = self._identify_bottlenecks(current_metrics)
        
        for bottleneck in bottlenecks:
            if bottleneck == "context_assembly_slow":
                # 调整上下文组装策略
                self.coordinator.config.context_assembler.enable_caching = True
                self.coordinator.config.context_assembler.cache_size = 200
            
            elif bottleneck == "sub_agent_creation_overhead":
                # 调整子代理池策略
                self.coordinator.config.task_tool.pool_size = 10
                self.coordinator.config.task_tool.enable_pooling = True
            
            elif bottleneck == "event_processing_latency":
                # 调整事件处理策略
                for filter_obj in self.coordinator.config.event_processor.filters:
                    filter_obj.batch_size = 20
                    filter_obj.batch_timeout = 0.05
```

### 统一协调特性

#### 1. 智能上下文组织复杂任务
- 根据任务类型、复杂度、递归深度动态调整上下文策略
- 智能优先级调整和资源分配
- 跨组件共享上下文信息

#### 2. 统一协调执行
- 四大能力协同工作，而非独立运行
- 统一的性能监控和指标收集
- 智能的资源分配和负载均衡

#### 3. 动态策略调整
- 基于实时性能指标调整策略
- 自适应优化执行参数
- 智能的故障恢复和降级

### 最佳实践

```python
# ✅ 推荐：启用统一协调机制
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    enable_unified_coordination=True
)

# ✅ 推荐：使用统一执行上下文
unified_context = UnifiedExecutionContext(
    enable_cross_component_optimization=True,
    enable_dynamic_strategy_adjustment=True,
    enable_unified_monitoring=True
)

# ✅ 推荐：监控统一性能指标
metrics = executor.get_unified_metrics()
print(f"任务类型: {metrics['task_analysis']['task_type']}")
print(f"复杂度: {metrics['task_analysis']['complexity_score']:.2f}")

# ❌ 不推荐：禁用统一协调
executor = AgentExecutor(
    llm=llm,
    tools=tools,
    enable_unified_coordination=False  # 失去四大能力协同优势
)
```

---

## 完整产品示例

### 示例 1：智能代码审查系统

```python
import asyncio
from loom import Agent
from loom.builtin.tools import TaskTool, ReadFileTool, GrepTool, GlobTool
from loom.llm.factory import LLMFactory
from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.core.events import AgentEventType, EventCollector
from loom.agents.registry import register_agent_spec
from loom.agents.refs import AgentSpec

# 1. 注册专业化代理
register_agent_spec(
    AgentSpec(
        agent_type="security-scanner",
        system_instructions="""
        你是安全扫描专家。检查常见安全问题：
        - SQL 注入风险
        - XSS 漏洞
        - 硬编码密钥
        - 不安全的依赖
        """,
        tools=["read_file", "grep", "glob"],
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="code-quality-checker",
        system_instructions="""
        你是代码质量检查专家。检查：
        - 函数复杂度
        - 命名规范
        - 代码重复
        - 文档完整性
        """,
        tools=["read_file", "grep", "glob"],
        model_name="gpt-4"
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="test-coverage-analyzer",
        system_instructions="""
        你是测试覆盖率分析专家。检查：
        - 测试文件覆盖
        - 关键函数测试
        - 边界条件测试
        """,
        tools=["read_file", "grep", "glob", "bash"],
        model_name="gpt-4"
    )
)

class CodeReviewSystem:
    """智能代码审查系统"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.llm = LLMFactory.create_openai(api_key=api_key, model="gpt-4")

    def _create_agent(self, max_iterations=20, **kwargs):
        """Agent 工厂"""
        return Agent(
            llm=self.llm,
            max_iterations=max_iterations,
            **kwargs
        )

    async def review_project(
        self,
        project_path: str,
        focus_areas: list = None
    ) -> dict:
        """审查项目代码"""

        if focus_areas is None:
            focus_areas = ["security", "quality", "tests"]

        # 1. 创建上下文组装器
        assembler = ContextAssembler(max_tokens=16000)

        # 添加系统指令
        assembler.add_component(
            "system_role",
            "你是高级代码审查协调器，负责协调各个专业审查子系统。",
            ComponentPriority.CRITICAL,
            truncatable=False
        )

        # 添加审查指南
        assembler.add_component(
            "review_guidelines",
            """
            审查流程：
            1. 使用 security-scanner 子代理进行安全扫描
            2. 使用 code-quality-checker 子代理检查代码质量
            3. 使用 test-coverage-analyzer 子代理分析测试覆盖
            4. 汇总所有结果并给出综合评估

            输出格式：
            - 为每个领域生成单独的报告
            - 标注严重问题（Critical）、警告（Warning）、建议（Suggestion）
            - 提供具体的改进建议
            """,
            ComponentPriority.HIGH,
            truncatable=False
        )

        # 添加项目上下文
        assembler.add_component(
            "project_info",
            f"项目路径: {project_path}\n审查重点: {', '.join(focus_areas)}",
            ComponentPriority.MEDIUM,
            truncatable=False
        )

        system_prompt = assembler.assemble()

        # 2. 创建主协调器
        coordinator = self._create_agent(
            system_instructions=system_prompt,
            tools=[
                TaskTool(agent_factory=self._create_agent),
                ReadFileTool(),
                GrepTool(),
                GlobTool()
            ]
        )

        # 3. 执行审查（带进度追踪）
        collector = EventCollector()
        results = {"steps": [], "errors": [], "final_report": ""}

        print("开始代码审查...\n")

        async for event in coordinator.execute(f"""
        请对项目 {project_path} 进行全面的代码审查。

        重点审查：{', '.join(focus_areas)}

        请使用以下子代理：
        - security-scanner: 安全扫描
        - code-quality-checker: 质量检查
        - test-coverage-analyzer: 测试覆盖分析

        最后生成一份综合报告。
        """):
            collector.add(event)

            if event.type == AgentEventType.LLM_DELTA:
                print(event.content, end="", flush=True)

            elif event.type == AgentEventType.TOOL_EXECUTION_START:
                step = f"执行工具: {event.tool_call.name}"
                results["steps"].append(step)
                print(f"\n[{step}]")

            elif event.type == AgentEventType.TOOL_RESULT:
                print(f" ✓ 完成 ({event.tool_result.execution_time_ms:.0f}ms)")

            elif event.type == AgentEventType.ERROR:
                results["errors"].append(str(event.error))

        results["final_report"] = collector.get_final_response()
        results["tool_count"] = len(collector.get_tool_results())
        results["event_count"] = len(collector.events)

        return results

# 使用示例
async def main():
    reviewer = CodeReviewSystem(api_key="sk-...")

    results = await reviewer.review_project(
        project_path="./src",
        focus_areas=["security", "quality", "tests"]
    )

    print("\n\n=== 审查完成 ===")
    print(f"执行步骤: {len(results['steps'])}")
    print(f"使用工具: {results['tool_count']}")
    print(f"总事件数: {results['event_count']}")

    if results["errors"]:
        print(f"错误数: {len(results['errors'])}")

    print("\n完整报告:")
    print(results["final_report"])

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 2：RAG 文档问答系统

```python
import asyncio
from loom import Agent
from loom.llm.factory import LLMFactory
from loom.core.context_assembly import ContextAssembler, ComponentPriority
from loom.core.events import AgentEventType

class RAGDocumentQA:
    """基于 RAG 的文档问答系统"""

    def __init__(self, api_key: str):
        self.llm = LLMFactory.create_openai(api_key=api_key, model="gpt-4")

    async def retrieve_documents(self, query: str) -> list:
        """
        模拟文档检索（实际项目中可接入向量数据库）
        """
        # 这里应该是实际的向量检索逻辑
        # 例如：使用 ChromaDB, Pinecone 等
        return [
            {
                "title": "Loom Agent 入门",
                "content": "Loom Agent 是一个生产级的 Python Agent 框架...",
                "score": 0.95
            },
            {
                "title": "ContextAssembler 使用指南",
                "content": "ContextAssembler 提供智能的上下文组装功能...",
                "score": 0.88
            }
        ]

    async def answer_question(
        self,
        question: str,
        max_docs: int = 5
    ) -> dict:
        """回答用户问题"""

        # 1. 检索相关文档
        print(f"检索相关文档...")
        docs = await self.retrieve_documents(question)
        docs = docs[:max_docs]  # 限制文档数量
        print(f"找到 {len(docs)} 个相关文档\n")

        # 2. 创建上下文组装器
        assembler = ContextAssembler(max_tokens=8000)

        # 系统角色（最高优先级）
        assembler.add_component(
            "system_role",
            "你是一个专业的文档问答助手。请基于提供的文档内容准确回答问题。",
            ComponentPriority.CRITICAL,
            truncatable=False
        )

        # 检索到的文档（高优先级）
        doc_content = "\n\n".join([
            f"【文档 {i+1}: {doc['title']}】（相关度: {doc['score']:.2f}）\n{doc['content']}"
            for i, doc in enumerate(docs)
        ])
        assembler.add_component(
            "retrieved_documents",
            f"相关文档内容：\n\n{doc_content}",
            ComponentPriority.HIGH,
            truncatable=True
        )

        # 回答规则（中等优先级）
        assembler.add_component(
            "answer_rules",
            """
            回答规则：
            1. 优先使用文档中的信息
            2. 如果文档中没有相关信息，明确告知用户
            3. 引用具体的文档内容时，注明文档标题
            4. 保持回答简洁准确
            """,
            ComponentPriority.MEDIUM,
            truncatable=True
        )

        system_prompt = assembler.assemble()

        # 3. 创建 agent
        agent = Agent(
            llm=self.llm,
            system_instructions=system_prompt
        )

        # 4. 流式回答（实时显示）
        answer = ""
        print("回答:")
        print("-" * 60)

        async for event in agent.execute(question):
            if event.type == AgentEventType.LLM_DELTA:
                answer += event.content
                print(event.content, end="", flush=True)

        print("\n" + "-" * 60)

        # 5. 返回结果和元信息
        context_summary = assembler.get_summary()

        return {
            "answer": answer,
            "sources": [
                {"title": doc["title"], "score": doc["score"]}
                for doc in docs
            ],
            "context_info": {
                "tokens_used": context_summary["total_tokens"],
                "docs_included": len(docs),
                "was_truncated": context_summary["truncated"]
            }
        }

# 使用示例
async def main():
    qa_system = RAGDocumentQA(api_key="sk-...")

    # 示例问题
    questions = [
        "Loom Agent 的核心特性是什么？",
        "如何使用 ContextAssembler？",
        "TaskTool 有什么用？"
    ]

    for question in questions:
        print(f"\n问题: {question}\n")
        result = await qa_system.answer_question(question)

        print(f"\n来源文档: {len(result['sources'])} 个")
        for src in result['sources']:
            print(f"  - {src['title']} (相关度: {src['score']:.2f})")

        print(f"\n上下文信息:")
        print(f"  - Tokens: {result['context_info']['tokens_used']}")
        print(f"  - 文档数: {result['context_info']['docs_included']}")
        print(f"  - 截断: {result['context_info']['was_truncated']}")

        print("\n" + "=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 生产环境最佳实践

### 1. Context Management

```python
# ✅ 推荐：使用 ContextAssembler
assembler = ContextAssembler(max_tokens=16000)
assembler.add_component("critical_info", content, ComponentPriority.CRITICAL, False)
assembler.add_component("rag_docs", docs, ComponentPriority.HIGH, True)
prompt = assembler.assemble()

# ❌ 不推荐：手动拼接字符串
prompt = f"{instructions}\n\n{docs}\n\n{tools}"  # 可能超出 token 限制
```

### 2. Error Handling

```python
async def robust_execution(agent, prompt):
    """带错误处理的执行"""
    try:
        result = ""
        async for event in agent.execute(prompt):
            if event.type == AgentEventType.ERROR:
                # 记录错误
                logger.error(f"Agent error: {event.error}")
                if not event.metadata.get('recoverable', False):
                    raise event.error

            elif event.type == AgentEventType.LLM_DELTA:
                result += event.content

            elif event.type == AgentEventType.AGENT_FINISH:
                return result

    except Exception as e:
        logger.exception("Fatal error in agent execution")
        # 返回友好的错误消息给用户
        return f"抱歉，处理过程中遇到错误: {str(e)}"
```

### 3. Token Budget Management

```python
# 根据模型调整 token 预算
MODEL_TOKEN_LIMITS = {
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-3.5-turbo": 4096,
    "gpt-3.5-turbo-16k": 16385
}

model_name = "gpt-4"
max_tokens = MODEL_TOKEN_LIMITS[model_name]

# 预留空间给输出
context_budget = int(max_tokens * 0.7)  # 70% 用于输入
output_budget = max_tokens - context_budget

assembler = ContextAssembler(
    max_tokens=context_budget,
    token_buffer=0.9  # 再留 10% buffer
)
```

### 4. SubAgent Isolation

```python
# ✅ 推荐：限制子代理权限
register_agent_spec(
    AgentSpec(
        agent_type="data-reader",
        system_instructions="只读数据分析器",
        tools=["read_file", "grep", "python_repl"],  # 明确列出允许的工具
        model_name="gpt-3.5-turbo"  # 使用成本更低的模型
    )
)

# ❌ 不推荐：给予所有权限
register_agent_spec(
    AgentSpec(
        agent_type="unrestricted-agent",
        system_instructions="万能助手",
        tools="*",  # 所有工具都可用（危险）
        model_name="gpt-4"
    )
)
```

### 5. Monitoring and Logging

```python
import structlog
from loom.core.events import EventCollector

logger = structlog.get_logger()

async def monitored_execution(agent, prompt, request_id):
    """带监控的执行"""
    collector = EventCollector()
    start_time = time.time()

    try:
        async for event in agent.execute(prompt):
            collector.add(event)

            # 记录关键事件
            if event.type == AgentEventType.TOOL_EXECUTION_START:
                logger.info(
                    "tool_started",
                    request_id=request_id,
                    tool=event.tool_call.name
                )

            elif event.type == AgentEventType.ERROR:
                logger.error(
                    "agent_error",
                    request_id=request_id,
                    error=str(event.error)
                )

        # 记录执行统计
        duration = time.time() - start_time
        logger.info(
            "execution_complete",
            request_id=request_id,
            duration_sec=duration,
            events=len(collector.events),
            tools_used=len(collector.get_tool_results())
        )

        return collector.get_final_response()

    except Exception as e:
        logger.exception(
            "execution_failed",
            request_id=request_id,
            duration_sec=time.time() - start_time
        )
        raise
```

### 6. Async Best Practices

```python
import asyncio

# ✅ 推荐：并发执行多个独立任务
async def parallel_analysis(files: list):
    """并发分析多个文件"""
    tasks = [
        analyze_file(file) for file in files
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果和异常
    successful = [r for r in results if not isinstance(r, Exception)]
    failed = [r for r in results if isinstance(r, Exception)]

    return successful, failed

# ❌ 不推荐：顺序执行
async def sequential_analysis(files: list):
    results = []
    for file in files:
        result = await analyze_file(file)  # 一个一个执行，慢
        results.append(result)
    return results
```

### 7. Cost Optimization

```python
# 根据任务复杂度选择模型
def select_model(task_complexity: str) -> str:
    """根据任务复杂度选择合适的模型"""
    if task_complexity == "simple":
        return "gpt-3.5-turbo"  # 简单任务用便宜的模型
    elif task_complexity == "medium":
        return "gpt-4"
    else:
        return "gpt-4-32k"  # 复杂任务用强大的模型

# 使用子代理时分级处理
register_agent_spec(
    AgentSpec(
        agent_type="simple-summarizer",
        system_instructions="生成简短摘要",
        tools=["read_file"],
        model_name="gpt-3.5-turbo"  # 便宜
    )
)

register_agent_spec(
    AgentSpec(
        agent_type="deep-analyzer",
        system_instructions="深度分析和推理",
        tools=["read_file", "python_repl"],
        model_name="gpt-4"  # 贵但强大
    )
)
```

---

## 总结

### 核心能力矩阵

| 能力 | 用途 | 适用场景 |
|-----|------|---------|
| **ContextAssembler** | 智能上下文管理 | RAG 系统、长上下文任务、token 优化 |
| **TaskTool** | 子代理编排 | 复杂流水线、任务分解、并行处理 |
| **AgentEvent** | 流式执行监控 | 实时 UI、进度追踪、日志分析 |
| **智能 TT 递归** | 可扩展任务处理 | 多领域任务、智能递归控制、自定义处理逻辑 |
| **统一协调机制** | 四大能力协同 | 复杂任务协调、跨组件优化、统一状态管理 |

### 快速选择指南

**我的场景是...** → **应该使用...**

- 📄 需要整合大量文档到 prompt → `ContextAssembler`
- 🔧 需要执行多步骤复杂任务 → `TaskTool` + Agent Packs
- 📊 需要实时显示执行进度 → `AgentEvent` + EventCollector
- 🎯 需要智能任务类型识别和处理 → `智能 TT 递归` + 自定义 `TaskHandler`
- 🔒 需要限制子任务权限 → `TaskTool` + 自定义 `tools` 列表
- ⚡ 需要并行执行多个子任务 → 多个 `TaskTool` 实例
- 💰 需要优化 token 成本 → `ContextAssembler` + 分级模型选择
- 🧠 需要根据工具结果动态调整策略 → `智能 TT 递归` + 结果分析
- 🎪 需要四大能力协同工作 → `统一协调机制` + `UnifiedExecutionContext`
- 🚀 需要智能上下文组织复杂任务 → `统一协调机制` + `IntelligentCoordinator`
- 📈 需要跨组件性能优化 → `统一协调机制` + 动态策略调整
- 🔄 需要统一状态管理和监控 → `统一协调机制` + 统一性能指标

---

**更新日期**: 2025-01-27
**框架版本**: Loom Agent 0.0.3
**文档维护**: 随框架更新同步更新

如有问题，请参考：
- API 文档: `docs/agent_events_guide.md`
- 示例代码: `examples/`
- 单元测试: `tests/unit/`
