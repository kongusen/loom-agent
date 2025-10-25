# Loom Agent 生产环境开发指南

**版本**: 0.0.2
**最后更新**: 2025-10-25
**目标读者**: 产品开发工程师

---

## 📋 目录

1. [核心能力概览](#核心能力概览)
2. [Context Assembly - 智能上下文管理](#context-assembly)
3. [TaskTool - 子代理系统](#tasktool)
4. [AgentEvent - 流式执行监控](#agentevent)
5. [完整产品示例](#完整产品示例)
6. [生产环境最佳实践](#生产环境最佳实践)

---

## 核心能力概览

Loom Agent 0.0.2 提供三大核心能力：

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

### 快速选择指南

**我的场景是...** → **应该使用...**

- 📄 需要整合大量文档到 prompt → `ContextAssembler`
- 🔧 需要执行多步骤复杂任务 → `TaskTool` + Agent Packs
- 📊 需要实时显示执行进度 → `AgentEvent` + EventCollector
- 🔒 需要限制子任务权限 → `TaskTool` + 自定义 `tools` 列表
- ⚡ 需要并行执行多个子任务 → 多个 `TaskTool` 实例
- 💰 需要优化 token 成本 → `ContextAssembler` + 分级模型选择

---

**更新日期**: 2025-10-25
**框架版本**: Loom Agent 0.0.2
**文档维护**: 随框架更新同步更新

如有问题，请参考：
- API 文档: `docs/agent_events_guide.md`
- 示例代码: `examples/`
- 单元测试: `tests/unit/`
