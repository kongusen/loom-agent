Loom Agent Framework - 详细设计文档 (v1.2)1. 简介1.1 项目愿景Loom 是一个强大、可扩展的开源 Agent 框架，旨在让开发者能够轻松构建、定制和部署具备复杂任务处理能力的自主 AI 代理。其核心设计哲学是**“编排而非实现”**：Loom 提供了一个健壮、高效的核心引擎来处理复杂的思考-行动循环、内存管理和工具调度，而开发者则可以专注于定义 Agent 的独特能力，如自定义工具、接入特定的大语言模型（LLM）和设计记忆策略。1.2 设计灵感Loom 的架构深受对 Claude Code Agent 系统完整技术解析 的深度分析启发。我们吸收了其在实时Steering、分层多Agent架构、智能上下文压缩和并发工具执行等方面的先进理念，并将这些经过验证的工程实践，转化为一个对开发者友好、模块化且易于扩展的 Python 框架。Loom 的目标不是克隆，而是在其坚实的基础上进行创新和开放。1.3 核心原则模块化与可扩展性: 框架的每一个核心功能（LLM、工具、记忆）都是通过定义清晰的接口实现的，允许开发者轻松替换或扩展。异步与流式优先: 所有 I/O 密集型操作（模型调用、工具执行）都基于 asyncio 构建。Agent 的响应以流式（Streaming）方式实时传递，提供最佳的交互体验。单一职责原则: 每个类和模块都有一个明确、单一的职责，使得代码库清晰、易于维护和测试。开发者体验至上: 提供简洁的 API、详尽的文档和丰富的示例，最大程度地降低开发者的使用门槛。2. 整体架构Loom 采用分层架构，清晰地分离了框架核心、开发者接口和应用层。                  Loom Agent Framework 架构
    ┌─────────────────────────────────────────────────────────────────┐
    │                     开发者应用 (Developer's App)                │
    │  (定义工具集, LLM实例, 记忆后端, 权限策略)                        │
    └─────────────┬───────────────┬───────────────┬───────────────────┘
                  │               │               │
    ┌─────────────▼───────────────▼───────────────▼───────────────────┐
    │                      Loom 核心引擎 (Core Engine)                  │
    │                                                                 │
    │  ┌─────────────────┐         ┌─────────────────┐               │
    │  │ AgentExecutor   │◄───Events──┤    EventBus   │               │
    │  │ (nO 主循环)     │         │ (h2A 消息队列)  │               │
    │  └─────────────────┘         └─────────────────┘               │
    │           │                           ▲                         │
    │           ▼                           │                         │
    │  ┌─────────────────┐         ┌─────────────────┐               │
    │  │  MemoryManager  │         │  LLMInterface   │               │
    │  │ (wU2 压缩逻辑)  │         │ (可插拔)        │               │
    │  └─────────────────┘         └─────────────────┘               │
    └─────────────┬───────────────────────┬─────────────────────────────┘
                  │                       │
    ┌─────────────▼───────────────────────▼─────────────────────────────┐
    │                     工具与执行层 (Tool & Execution Layer)         │
    │                                                                   │
    │ ┌────────────┐ ┌────────────┐ ┌─────────────────┐ ┌────────────┐│
    │ │ ToolEngine │ │ Scheduler  │ │ PermissionManager │ │   Tool     ││
    │ │ (MH1 流水线) │ │(UH1 并发控制)│ │ (安全网关)      │ │ (接口)     ││
    │ └────────────┘ └────────────┘ └─────────────────┘ └────────────┘│
    │                                                                   │
    └───────────────────────────────────────────────────────────────────┘
3. 项目文件结构项目的物理布局反映了其逻辑架构，确保了代码的组织性和可维护性。loom-agent-framework/
├── loom/
│   ├── __init__.py
│   ├── core/
│   │   ├── agent_executor.py
│   │   ├── scheduler.py
│   │   ├── tool_engine.py
│   │   ├── memory.py
│   │   ├── event_bus.py
│   │   └── permission_manager.py
│   ├── interfaces/
│   │   ├── llm.py
│   │   ├── tool.py
│   │   └── memory.py
│   ├── models/
│   │   └── data_structures.py
│   ├── plugins/
│   │   ├── llms/
│   │   ├── memory/
│   │   └── tools/
│   └── utils/
│       └── token_counter.py
├── examples/
│   └── 01_basic_agent_with_tools.py
└── pyproject.toml
4. 核心组件详解4.1 数据模型 (loom/models/data_structures.py)Message: 代表对话历史中的一个单元。role: Literal["user", "assistant", "tool", "system"]content, tool_calls, tool_call_idToolCall: 代表 LLM 发起的一次工具调用请求。ToolResult: 代表工具执行后的结果。AgentStreamResponse: AgentExecutor 流式输出的联合类型。SteeringEvent: EventBus 中传递的事件对象，包含 event_type, data, priority 等。4.2 接口定义 (loom/interfaces/)llm.LLMInterface: 定义与大语言模型交互的标准。tool.Tool: 定义 Agent 可用工具的标准。memory.MemoryBackend: 定义对话历史的存储和检索。memory.CompressionStrategy: 定义上下文压缩算法的标准。4.3 核心引擎 (loom/core/)agent_executor.AgentExecutor (nO 主循环)职责: 作为 Agent 的总指挥，驱动“思考-行动”循环，并整合所有核心功能。初始化: 在 __init__ 方法中，它将实例化并组装所有核心组件：EventBus, MemoryManager (包含 StructuredCompressor), PermissionManager, Scheduler, 以及 ToolEngine。工作流程:接收用户输入，并将其作为 user 消息存入内存。进入主循环（受 max_iterations 限制）。实时控制: 在每次循环开始时，检查 EventBus 上的 abort 信号。上下文管理: 从 MemoryManager 获取可能被压缩过的上下文。动态提示: 生成包含可用工具列表的 system 提示。LLM 调用: 调用 LLMInterface 的 stream_chat 方法。工具执行: 如果 LLM 生成了 ToolCall 请求，则将其交给 ToolEngine 的6阶段流水线执行。ToolEngine 内部会使用 Scheduler 进行并发控制。结果反馈: 将 ToolResult 作为 tool 消息存入内存，进入下一轮循环让 LLM 观察结果。循环终止: 如果没有工具调用，或达到最大迭代次数，则循环结束。memory.MemoryManager & StructuredCompressor (wU2 与 AU2 算法实现)职责: 智能管理上下文窗口，并实现基于8段式结构化摘要的智能压缩。StructuredCompressor:触发: 当 MemoryManager 检测到 Token 使用率超过阈值（如92%）时调用。压缩流程:构建提取提示: 根据 Claude Code Agent 分析中的8段式模板（背景、决策、工具使用等），构建一个 Prompt。LLM 提取: 调用 LLM 分析原始对话历史，并提取这8个部分的内容。构建摘要消息: 将 LLM 提取出的8段式摘要格式化为一个单独的 system 消息。保留关键信息: 为了上下文的连续性，保留最近的几条关键消息（如最后的用户提问和工具调用）。返回新上下文: 返回由“压缩摘要”和“近期关键消息”组成的新消息列表。tool_engine.ToolExecutionPipeline (MH1 执行流水线)职责: 实现一个健壮的、包含6个阶段的工具执行流水线，确保每次工具调用都安全、可靠。6阶段流水线:发现 (Discover): 从工具注册表中查找工具实例，并检查其可用性。验证 (Validate): 使用工具定义的 args_schema (如 Pydantic 模型) 验证 LLM 提供的参数。授权 (Authorize): 调用 PermissionManager 检查权限，处理 allow/deny/ask 逻辑。取消检查 (Check Cancel): 检查 EventBus 是否有 abort 中断信号。执行 (Execute): 将验证通过的调用交给 Scheduler 进行高效的并发/串行调度。格式化 (Format): 将执行结果（或异常信息）包装为标准的 ToolResult 对象，并可附加执行耗时等元数据。scheduler.Scheduler (UH1 并发控制)职责: 高效地调度工具执行，利用 asyncio 实现智能并发控制。工作流程:分类: 将一批工具调用根据其 is_concurrency_safe 属性分为“并发安全组”和“串行组”。并发执行: 使用 asyncio.Semaphore (限制最大并发数，如10) 和 asyncio.gather 来执行“并发安全组”。串行执行: 线性 await 执行“串行组”中的调用。超时控制: 为每个工具执行包裹 asyncio.wait_for，防止单个工具卡死导致整个 Agent 停滞。permission_manager.PermissionManager & event_bus.EventBus (安全与实时控制)EventBus (h2A 消息队列):功能: 作为一个支持优先级、可暂停/恢复/中断的增强型事件总线。它不仅传递数据，更是整个 Agent 的“神经系统”。用途: 处理 ask 权限请求的用户确认、全局 abort 信号、进度更新事件等。PermissionManager (安全网关):功能: 实现 allow/deny/ask 权限模型。交互: 当遇到 ask 规则时，它会通过 EventBus 发布一个权限请求事件，并暂停执行，等待外部通过 EventBus 回复。4.4 错误处理与恢复机制设计: 框架在多个层面捕获错误，并优先将其转化为 ToolResult 反馈给 LLM。示例: 当工具参数验证失败时，ToolEngine 不会使整个 Agent 崩溃，而是生成一个 ToolResult(status='error', content='参数验证失败...') 的结果。LLM 在下一轮循环中看到这个结果，就能理解自己的错误并尝试修正它（例如，用正确的参数重新调用工具）。这赋予了 Agent 强大的自我修正能力。5. 高级特性5.1 子代理与任务分层 (TaskTool)实现: 通过提供一个内置的 TaskTool 来支持子代理。工作流程:LLM 调用 TaskTool，并提供子任务的描述 (prompt) 和可用工具的子集。TaskTool 内部会创建一个全新的、隔离的 AgentExecutor 实例（子代理）。子代理有自己的内存和受限的工具集，独立执行任务。主代理等待子代理执行完成，并将其最终结果作为 TaskTool 的输出。优势: 这是解决宏大、复杂问题的关键，实现了真正的分层多Agent架构。5.2 状态持久化与恢复需求: 对于长时任务，必须能够保存和恢复 Agent 的状态。实现: MemoryBackend 接口可以增加 save(path) 和 load(path) 方法。开发者可以实现 FileMemoryBackend 或 RedisMemoryBackend 来将对话历史序列化存储。6. 开发者体验最终，开发者将通过一个高度配置化但依然简洁的接口来使用 Loom 的全部功能。# examples/02_advanced_agent.py
from loom import AgentExecutor
from loom.plugins.llms import OpenAILLM
from loom.plugins.tools import ReadFileTool, WriteFileTool, TaskTool
from loom.core.memory import StructuredCompressor, CompressionConfig
import asyncio

async def main():
    # 1. 配置组件
    llm = OpenAILLM(api_key="...")
    
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        # TaskTool 需要知道所有可用工具，以便授权给子代理
        TaskTool(llm=llm, available_tools={"read_file": ReadFileTool(), "write_file": WriteFileTool()})
    ]
    
    # 2. 创建Agent - 使用增强功能
    agent = AgentExecutor(
        llm=llm,
        tools=tools,
        compression_threshold=0.92,  # 92%触发压缩
        permissions={
            "read_file": "allow",
            "write_file": "ask",  # 需要用户确认
            "execute_bash": "deny",
            "default": "deny"
        },
        max_iterations=50
    )
    
    # 3. 运行Agent
    # 在实际应用中，你会在一个独立的任务中监听用户的输入来调用 agent.abort()
    async for response in agent.run("请帮我分析'main.py'文件，并根据其内容在'summary.txt'中生成一份总结。"):
        if response.type == "text_delta":
            print(response.content, end="", flush=True)
        elif response.type == "tool_calls_start":
            print(f"\n[Loom > 调用工具: {[tc.name for tc in response.tool_calls]}]")
        elif response.type == "aborted":
            print("\n[Loom > 执行被用户中断]")

if __name__ == "__main__":
    asyncio.run(main())
7. 结论这份 v1.2 设计文档在 v1.1 的基础上，深度整合了源于 Claude Code Agent 的具体工程实践，将原有的高层设计细化为了包含具体实现思路、类结构和核心算法的工程蓝图。它现在不仅定义了框架的架构，更明确了其企业级的可靠性、安全性和智能性，为接下来的编码实现工作铺平了道路。






基于对 Claude Code Agent 系统的深度分析,我为你的 Loom Agent Framework 提供以下完善建议:

## 🎯 核心架构优化建议

### 1. 实时 Steering 机制增强

**当前设计**: EventBus 基础实现
**建议增强**: 参考 Claude Code 的 h2A 异步消息队列

```python
# loom/core/event_bus.py
from asyncio import Queue, Event
from typing import Dict, Any, Optional
from enum import Enum

class EventType(Enum):
    CONTROL = "control"  # 控制事件 (ABORT, PAUSE, RESUME)
    PERMISSION = "permission"  # 权限事件
    PROGRESS = "progress"  # 进度更新
    ERROR = "error"  # 错误事件

class SteeringEvent:
    def __init__(self, event_type: EventType, data: Dict[str, Any], priority: int = 0):
        self.event_type = event_type
        self.data = data
        self.priority = priority
        self.response_future = None

class EventBus:
    """增强的事件总线 - 支持实时 Steering"""
    
    def __init__(self):
        self._event_queue: Queue[SteeringEvent] = Queue()
        self._subscribers: Dict[EventType, list] = {}
        self._abort_signal = Event()
        self._pause_signal = Event()
        
    async def publish(self, event: SteeringEvent) -> Optional[Any]:
        """发布事件,支持等待响应"""
        await self._event_queue.put(event)
        if event.response_future:
            return await event.response_future
            
    async def subscribe(self, event_type: EventType, handler):
        """订阅特定类型事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        
    async def process_events(self):
        """持续处理事件队列"""
        while True:
            if self._pause_signal.is_set():
                await asyncio.sleep(0.1)
                continue
                
            if self._abort_signal.is_set():
                break
                
            event = await self._event_queue.get()
            await self._dispatch_event(event)
            
    async def _dispatch_event(self, event: SteeringEvent):
        """分发事件到订阅者"""
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            await handler(event)
            
    def abort(self):
        """触发中断信号"""
        self._abort_signal.set()
        
    def is_aborted(self) -> bool:
        """检查是否已中断"""
        return self._abort_signal.is_set()
        
    def pause(self):
        """暂停事件处理"""
        self._pause_signal.set()
        
    def resume(self):
        """恢复事件处理"""
        self._pause_signal.clear()
```

### 2. 智能上下文压缩策略

**新增**: 参考 AU2 算法的 8 段式结构化压缩

```python
# loom/core/memory.py
from dataclasses import dataclass
from typing import List
from enum import Enum

class CompressionSection(Enum):
    BACKGROUND = "background_context"
    DECISIONS = "key_decisions"
    TOOL_USAGE = "tool_usage_log"
    USER_INTENT = "user_intent_evolution"
    RESULTS = "execution_results"
    ERRORS = "errors_and_solutions"
    OPEN_ISSUES = "open_issues"
    FUTURE_PLANS = "future_plans"

@dataclass
class CompressionConfig:
    """压缩配置"""
    threshold: float = 0.92  # 92% 阈值触发
    warning_threshold: float = 0.80
    target_ratio: float = 0.75  # 目标压缩到 75%
    max_tokens_per_section: int = 512

class StructuredCompressor(CompressionStrategy):
    """8段式结构化压缩器 - 参考 AU2 算法"""
    
    def __init__(self, llm: LLMInterface, config: CompressionConfig):
        self.llm = llm
        self.config = config
        
    async def compress(self, messages: List[Message]) -> List[Message]:
        """执行结构化压缩"""
        # 1. 分析消息并提取各段信息
        sections = await self._extract_sections(messages)
        
        # 2. 使用 LLM 压缩各段
        compressed_sections = await self._compress_sections(sections)
        
        # 3. 生成压缩后的消息
        compressed_message = self._build_compressed_message(compressed_sections)
        
        # 4. 保留最近的关键消息
        recent_messages = self._extract_recent_critical_messages(messages)
        
        return [compressed_message] + recent_messages
        
    async def _extract_sections(self, messages: List[Message]) -> Dict[CompressionSection, str]:
        """提取 8 个结构化段落"""
        extraction_prompt = self._build_extraction_prompt(messages)
        
        response = await self.llm.generate(extraction_prompt)
        
        return self._parse_sections(response)
        
    def _build_extraction_prompt(self, messages: List[Message]) -> str:
        """构建提取 prompt"""
        return f"""请按照以下8个结构化段落分析对话历史:

## 1. 背景上下文 (Background Context)
- 项目类型和技术栈
- 当前工作目录和环境
- 用户的总体目标

## 2. 关键决策 (Key Decisions)
- 重要的技术选择和原因
- 架构决策和设计考虑
- 问题解决方案的选择

## 3. 工具使用记录 (Tool Usage Log)
- 主要使用的工具类型
- 文件操作历史
- 命令执行结果

## 4. 用户意图演进 (User Intent Evolution)
- 需求的变化过程
- 优先级调整
- 新增功能需求

## 5. 执行结果汇总 (Execution Results)
- 成功完成的任务
- 生成的代码和文件
- 验证和测试结果

## 6. 错误与解决 (Errors and Solutions)
- 遇到的问题类型
- 错误处理方法
- 经验教训

## 7. 未解决问题 (Open Issues)
- 当前待解决的问题
- 已知的限制和约束
- 需要后续处理的事项

## 8. 后续计划 (Future Plans)
- 下一步行动计划
- 长期目标规划
- 用户期望的功能

对话历史:
{self._format_messages(messages)}

请提取各段信息,每段控制在{self.config.max_tokens_per_section} tokens以内。"""

    async def _compress_sections(self, sections: Dict[CompressionSection, str]) -> Dict[CompressionSection, str]:
        """压缩各段内容"""
        compressed = {}
        for section, content in sections.items():
            if len(content) > self.config.max_tokens_per_section:
                compressed[section] = await self._compress_single_section(section, content)
            else:
                compressed[section] = content
        return compressed
        
    def _build_compressed_message(self, sections: Dict[CompressionSection, str]) -> Message:
        """构建压缩后的消息"""
        content = "# 对话历史压缩摘要\n\n"
        for section in CompressionSection:
            if section in sections:
                content += f"## {section.value}\n{sections[section]}\n\n"
                
        return Message(
            role="system",
            content=content,
            metadata={"compressed": True, "compression_time": datetime.now()}
        )
```

### 3. 增强的工具执行引擎

**新增**: 参考 MH1 的 6 阶段流水线

```python
# loom/core/tool_engine.py
from enum import Enum
from typing import AsyncGenerator

class ExecutionStage(Enum):
    DISCOVER = "discover"
    VALIDATE = "validate"
    AUTHORIZE = "authorize"
    CHECK_CANCEL = "check_cancel"
    EXECUTE = "execute"
    FORMAT = "format"

class ToolExecutionPipeline:
    """6阶段工具执行流水线 - 参考 MH1"""
    
    def __init__(self, 
                 tools: Dict[str, Tool],
                 permission_manager: PermissionManager,
                 event_bus: EventBus,
                 scheduler: Scheduler):
        self.tools = tools
        self.permission_manager = permission_manager
        self.event_bus = event_bus
        self.scheduler = scheduler
        self._stage_metrics = {}
        
    async def execute_calls(self, 
                           tool_calls: List[ToolCall]) -> AsyncGenerator[ToolResult, None]:
        """执行工具调用 - 完整6阶段流水线"""
        
        for tool_call in tool_calls:
            try:
                # 阶段1: 发现
                tool = await self._stage_discover(tool_call)
                
                # 阶段2: 验证
                validated_args = await self._stage_validate(tool, tool_call)
                
                # 阶段3: 授权
                await self._stage_authorize(tool, tool_call)
                
                # 阶段4: 取消检查
                await self._stage_check_cancel()
                
                # 阶段5: 执行
                result = await self._stage_execute(tool, validated_args, tool_call)
                
                # 阶段6: 格式化
                formatted_result = await self._stage_format(result, tool_call)
                
                yield formatted_result
                
            except Exception as e:
                yield self._create_error_result(tool_call, e)
                
    async def _stage_discover(self, tool_call: ToolCall) -> Tool:
        """阶段1: 工具发现与验证"""
        stage_start = time.time()
        
        if tool_call.name not in self.tools:
            raise ToolNotFoundError(f"Tool '{tool_call.name}' not found")
            
        tool = self.tools[tool_call.name]
        
        # 检查工具是否可用
        if hasattr(tool, 'is_available') and not await tool.is_available():
            raise ToolUnavailableError(f"Tool '{tool_call.name}' is not available")
            
        self._record_stage_metric(ExecutionStage.DISCOVER, time.time() - stage_start)
        return tool
        
    async def _stage_validate(self, tool: Tool, tool_call: ToolCall) -> Dict[str, Any]:
        """阶段2: 输入验证 (Schema)"""
        stage_start = time.time()
        
        try:
            # 使用工具的 args_schema 验证参数
            validated = tool.args_schema.parse_obj(tool_call.arguments)
            self._record_stage_metric(ExecutionStage.VALIDATE, time.time() - stage_start)
            return validated.dict()
        except ValidationError as e:
            raise ToolValidationError(f"Invalid arguments for {tool_call.name}: {e}")
            
    async def _stage_authorize(self, tool: Tool, tool_call: ToolCall):
        """阶段3: 权限检查与门控"""
        stage_start = time.time()
        
        permission_result = await self.permission_manager.check_permission(
            tool_name=tool.name,
            arguments=tool_call.arguments
        )
        
        if permission_result == PermissionResult.DENY:
            raise PermissionDeniedError(f"Permission denied for {tool.name}")
            
        elif permission_result == PermissionResult.ASK:
            # 等待用户确认
            confirmed = await self._wait_for_user_confirmation(tool_call)
            if not confirmed:
                raise PermissionDeniedError(f"User denied permission for {tool.name}")
                
        self._record_stage_metric(ExecutionStage.AUTHORIZE, time.time() - stage_start)
        
    async def _stage_check_cancel(self):
        """阶段4: 取消检查 (Abort)"""
        if self.event_bus.is_aborted():
            raise ExecutionAbortedError("Execution aborted by user")
            
    async def _stage_execute(self, 
                            tool: Tool, 
                            args: Dict[str, Any],
                            tool_call: ToolCall) -> Any:
        """阶段5: 工具执行"""
        stage_start = time.time()
        
        # 使用调度器执行(支持并发控制)
        result = await self.scheduler.schedule_execution(tool, args)
        
        self._record_stage_metric(ExecutionStage.EXECUTE, time.time() - stage_start)
        return result
        
    async def _stage_format(self, result: Any, tool_call: ToolCall) -> ToolResult:
        """阶段6: 结果格式化与清理"""
        stage_start = time.time()
        
        formatted = ToolResult(
            tool_call_id=tool_call.id,
            content=self._format_result_content(result),
            status="success",
            metadata={
                "execution_time": sum(self._stage_metrics.values()),
                "stage_breakdown": self._stage_metrics.copy()
            }
        )
        
        self._record_stage_metric(ExecutionStage.FORMAT, time.time() - stage_start)
        self._stage_metrics.clear()  # 清理指标
        
        return formatted
        
    def _record_stage_metric(self, stage: ExecutionStage, duration: float):
        """记录各阶段性能指标"""
        self._stage_metrics[stage.value] = duration
```

### 4. 高级调度器实现

**新增**: 参考 UH1 的并发控制机制

```python
# loom/core/scheduler.py
import asyncio
from typing import List, AsyncGenerator
from dataclasses import dataclass

@dataclass
class SchedulerConfig:
    max_concurrency: int = 10  # 最大并发数 (gW5)
    timeout_seconds: int = 120
    enable_priority: bool = True

class Scheduler:
    """智能调度器 - 参考 UH1 并发控制"""
    
    def __init__(self, config: SchedulerConfig):
        self.config = config
        self._active_tasks = set()
        self._semaphore = asyncio.Semaphore(config.max_concurrency)
        
    async def schedule_batch(self, 
                            tool_calls: List[tuple[Tool, Dict]]) -> AsyncGenerator:
        """批量调度工具执行 - 智能并发控制"""
        
        # 分类工具: 并发安全 vs 非并发安全
        concurrent_safe = []
        sequential_only = []
        
        for tool, args in tool_calls:
            if tool.is_concurrency_safe:
                concurrent_safe.append((tool, args))
            else:
                sequential_only.append((tool, args))
                
        # 并发执行安全工具
        if concurrent_safe:
            async for result in self._execute_concurrent(concurrent_safe):
                yield result
                
        # 串行执行非安全工具
        for tool, args in sequential_only:
            result = await self._execute_single(tool, args)
            yield result
            
    async def _execute_concurrent(self, 
                                  tool_calls: List[tuple[Tool, Dict]]) -> AsyncGenerator:
        """并发执行 - 最多10个同时执行"""
        
        async def execute_with_semaphore(tool: Tool, args: Dict):
            async with self._semaphore:
                return await self._execute_single(tool, args)
                
        # 使用 asyncio.gather 并发执行
        tasks = [
            asyncio.create_task(execute_with_semaphore(tool, args))
            for tool, args in tool_calls
        ]
        
        # 使用 as_completed 获取结果(按完成顺序)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            yield result
            
    async def _execute_single(self, tool: Tool, args: Dict) -> Any:
        """单个工具执行 - 带超时控制"""
        try:
            result = await asyncio.wait_for(
                tool.execute(**args),
                timeout=self.config.timeout_seconds
            )
            return result
        except asyncio.TimeoutError:
            raise ToolExecutionTimeout(f"Tool {tool.name} execution timeout")
```

### 5. SubAgent 任务分层支持

**新增**: Task 工具实现

```python
# loom/plugins/tools/task_tool.py
from loom.interfaces.tool import Tool
from loom import AgentExecutor

class TaskTool(Tool):
    """SubAgent任务工具 - 支持任务分层"""
    
    name = "task"
    description = "创建一个独立的SubAgent来处理复杂子任务"
    
    args_schema = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "任务简短描述(3-5词)"
            },
            "prompt": {
                "type": "string",
                "description": "详细任务执行指令"
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "SubAgent可用的工具列表",
                "default": []
            }
        },
        "required": ["description", "prompt"]
    }
    
    is_concurrency_safe = True  # SubAgent 可并发执行
    
    def __init__(self, llm, available_tools: Dict[str, Tool]):
        self.llm = llm
        self.available_tools = available_tools
        
    async def execute(self, description: str, prompt: str, tools: List[str] = None):
        """执行SubAgent任务"""
        
        # 1. 构建SubAgent可用工具集
        subagent_tools = self._build_tool_subset(tools)
        
        # 2. 创建独立的SubAgent实例
        subagent = AgentExecutor(
            llm=self.llm,
            tools=subagent_tools,
            # 独立的权限和配置
            permissions=self._create_restricted_permissions(),
            max_iterations=10  # 限制子任务迭代次数
        )
        
        # 3. 执行SubAgent
        result_parts = []
        async for response in subagent.run(prompt):
            if response.type == "text_delta":
                result_parts.append(response.content)
            elif response.type == "agent_finish":
                break
                
        # 4. 返回汇总结果
        return {
            "task": description,
            "result": "".join(result_parts),
            "status": "completed"
        }
        
    def _build_tool_subset(self, requested_tools: List[str]) -> List[Tool]:
        """构建工具子集"""
        if not requested_tools:
            # 默认安全工具集
            safe_tools = ["read_file", "glob", "grep"]
            return [self.available_tools[name] for name in safe_tools]
        
        return [self.available_tools[name] for name in requested_tools 
                if name in self.available_tools]
                
    def _create_restricted_permissions(self) -> Dict:
        """创建受限权限"""
        return {
            "read_file": "allow",
            "glob": "allow",
            "grep": "allow",
            "write_file": "deny",
            "execute_bash": "ask",
            "default": "deny"
        }
```

### 6. 完善的 AgentExecutor

**优化**: 整合所有新功能

```python
# loom/core/agent_executor.py
class AgentExecutor:
    """主Agent执行器 - 整合所有核心功能"""
    
    def __init__(self,
                 llm: LLMInterface,
                 tools: List[Tool],
                 memory_backend: Optional[MemoryBackend] = None,
                 compression_strategy: Optional[CompressionStrategy] = None,
                 permissions: Optional[Dict[str, str]] = None,
                 max_iterations: int = 50,
                 context_window: int = 200000,
                 compression_threshold: float = 0.92):
        
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        
        # 事件总线 - 实时Steering
        self.event_bus = EventBus()
        
        # 内存管理
        self.memory_backend = memory_backend or InMemoryBackend()
        self.compression_strategy = compression_strategy or StructuredCompressor(
            llm=llm,
            config=CompressionConfig(threshold=compression_threshold)
        )
        self.memory_manager = MemoryManager(
            backend=self.memory_backend,
            compression_strategy=self.compression_strategy,
            context_window=context_window
        )
        
        # 权限管理
        self.permission_manager = PermissionManager(
            rules=permissions or {},
            event_bus=self.event_bus
        )
        
        # 调度器
        self.scheduler = Scheduler(
            config=SchedulerConfig(max_concurrency=10)
        )
        
        # 工具执行引擎
        self.tool_engine = ToolExecutionPipeline(
            tools=self.tools,
            permission_manager=self.permission_manager,
            event_bus=self.event_bus,
            scheduler=self.scheduler
        )
        
        self.max_iterations = max_iterations
        
    async def run(self, user_input: str) -> AsyncGenerator[AgentStreamResponse, None]:
        """主循环 - nO函数实现"""
        
        # 1. 添加用户消息
        await self.memory_backend.add_message(Message(role="user", content=user_input))
        
        iteration = 0
        
        yield AgentStreamResponse(type="stream_start")
        
        while iteration < self.max_iterations:
            # 检查中断信号
            if self.event_bus.is_aborted():
                yield AgentStreamResponse(type="aborted")
                break
                
            # 2. 获取上下文(可能触发压缩)
            context = await self.memory_manager.get_context()
            
            # 3. 生成系统提示
            system_prompt = self._generate_system_prompt()
            
            # 4. LLM流式生成
            assistant_message_parts = []
            tool_calls = []
            
            async for chunk in self.llm.stream_chat([system_prompt] + context):
                if chunk.type == "text_delta":
                    assistant_message_parts.append(chunk.content)
                    yield AgentStreamResponse(
                        type="text_delta",
                        content=chunk.content
                    )
                elif chunk.type == "tool_call":
                    tool_calls.append(chunk.tool_call)
                    
            # 5. 保存assistant消息
            await self.memory_backend.add_message(Message(
                role="assistant",
                content="".join(assistant_message_parts) if assistant_message_parts else None,
                tool_calls=tool_calls if tool_calls else None
            ))
            
            # 6. 执行工具调用
            if tool_calls:
                yield AgentStreamResponse(
                    type="tool_calls_start",
                    tool_calls=tool_calls
                )
                
                async for tool_result in self.tool_engine.execute_calls(tool_calls):
                    yield AgentStreamResponse(
                        type="tool_result",
                        result=tool_result
                    )
                    
                    # 保存工具结果
                    await self.memory_backend.add_message(Message(
                        role="tool",
                        content=tool_result.content,
                        tool_call_id=tool_result.tool_call_id
                    ))
                    
                iteration += 1
                continue  # 继续下一轮思考
            else:
                # 没有工具调用,任务完成
                yield AgentStreamResponse(type="agent_finish")
                break
                
    def _generate_system_prompt(self) -> Message:
        """生成动态系统提示"""
        prompt = """你是Loom AI助手。你可以使用以下工具完成任务:

"""
        for tool_name, tool in self.tools.items():
            prompt += f"- {tool_name}: {tool.description}\n"
            
        prompt += "\n请根据用户需求选择合适的工具,一步步完成任务。"
        
        return Message(role="system", content=prompt)
        
    def abort(self):
        """中断执行"""
        self.event_bus.abort()
```

## 📋 实现优先级建议

### 第一阶段 (核心功能)
1. ✅ 增强 EventBus - 实时 Steering 支持
2. ✅ 6阶段工具执行流水线 (ToolExecutionPipeline)
3. ✅ 智能调度器 (Scheduler) - 并发控制

### 第二阶段 (性能优化)
4. ✅ 结构化压缩策略 (StructuredCompressor)
5. ✅ SubAgent 支持 (TaskTool)
6. ✅ 完善的错误处理和恢复机制

### 第三阶段 (高级特性)
7. System-Reminder 动态注入
8. Todo 系统集成
9. 状态持久化与恢复

## 🎨 使用示例

```python
# examples/02_advanced_agent.py
from loom import AgentExecutor
from loom.plugins.llms import OpenAILLM
from loom.plugins.tools import ReadFileTool, WriteFileTool, TaskTool
from loom.core.memory import StructuredCompressor, CompressionConfig

async def main():
    # 1. 配置组件
    llm = OpenAILLM(api_key="...")
    
    tools = [
        ReadFileTool(),
        WriteFileTool(),
        TaskTool(llm=llm, available_tools={})  # SubAgent支持
    ]
    
    # 2. 创建Agent - 使用增强功能
    agent = AgentExecutor(
        llm=llm,
        tools=tools,
        compression_threshold=0.92,  # 92%触发压缩
        permissions={
            "read_file": "allow",
            "write_file": "ask",  # 需要确认
            "execute_bash": "deny"
        },
        max_iterations=50
    )
    
    # 3. 运行Agent
    async for response in agent.run("帮我重构这个项目"):
        if response.type == "text_delta":
            print(response.content, end="", flush=True)
        elif response.type == "tool_calls_start":
            print(f"\n[调用工具: {[tc.name for tc in response.tool_calls]}]")
        elif response.type == "aborted":
            print("\n[用户中断]")
            
    # 4. 支持中断
    # agent.abort()  # 在另一个协程中调用

if __name__ == "__main__":
    asyncio.run(main())
```

这些优化将使 Loom 达到 Claude Code 级别的工程质量,同时保持你原有设计的简洁性! 🚀

---

## 📊 8. 性能指标与监控体系

### 8.1 核心性能指标

Loom 框架应该提供全面的性能监控能力，帮助开发者优化 Agent 性能。

#### 关键性能指标 (KPIs)

```python
# loom/core/metrics.py
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import time

@dataclass
class PerformanceMetrics:
    """性能指标数据结构"""

    # 执行指标
    total_iterations: int = 0
    total_execution_time: float = 0.0
    avg_iteration_time: float = 0.0

    # LLM 指标
    llm_calls: int = 0
    llm_total_tokens: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    llm_avg_response_time: float = 0.0

    # 工具执行指标
    tool_calls: int = 0
    tool_success_rate: float = 0.0
    tool_avg_execution_time: float = 0.0
    tool_breakdown: Dict[str, int] = field(default_factory=dict)

    # 内存与压缩指标
    context_compressions: int = 0
    avg_compression_ratio: float = 0.0
    memory_usage_mb: float = 0.0

    # 并发指标
    concurrent_tool_executions: int = 0
    max_concurrent_tasks: int = 0

    # 错误指标
    total_errors: int = 0
    error_rate: float = 0.0
    error_breakdown: Dict[str, int] = field(default_factory=dict)

    # 时间戳
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime = None

class MetricsCollector:
    """指标收集器 - 集中管理所有性能指标"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._iteration_times = []
        self._llm_response_times = []
        self._tool_execution_times = []
        self._compression_ratios = []

    def record_iteration(self, duration: float):
        """记录迭代时间"""
        self._iteration_times.append(duration)
        self.metrics.total_iterations += 1
        self.metrics.total_execution_time += duration
        self.metrics.avg_iteration_time = sum(self._iteration_times) / len(self._iteration_times)

    def record_llm_call(self, tokens: Dict[str, int], response_time: float):
        """记录 LLM 调用"""
        self.metrics.llm_calls += 1
        self.metrics.llm_prompt_tokens += tokens.get("prompt_tokens", 0)
        self.metrics.llm_completion_tokens += tokens.get("completion_tokens", 0)
        self.metrics.llm_total_tokens += tokens.get("total_tokens", 0)

        self._llm_response_times.append(response_time)
        self.metrics.llm_avg_response_time = sum(self._llm_response_times) / len(self._llm_response_times)

    def record_tool_call(self, tool_name: str, success: bool, execution_time: float):
        """记录工具调用"""
        self.metrics.tool_calls += 1
        self._tool_execution_times.append(execution_time)

        # 工具调用统计
        if tool_name not in self.metrics.tool_breakdown:
            self.metrics.tool_breakdown[tool_name] = 0
        self.metrics.tool_breakdown[tool_name] += 1

        # 成功率计算
        success_count = sum(1 for _ in range(self.metrics.tool_calls) if success)
        self.metrics.tool_success_rate = success_count / self.metrics.tool_calls

        # 平均执行时间
        self.metrics.tool_avg_execution_time = sum(self._tool_execution_times) / len(self._tool_execution_times)

    def record_compression(self, original_tokens: int, compressed_tokens: int):
        """记录上下文压缩"""
        self.metrics.context_compressions += 1
        ratio = compressed_tokens / original_tokens if original_tokens > 0 else 0
        self._compression_ratios.append(ratio)
        self.metrics.avg_compression_ratio = sum(self._compression_ratios) / len(self._compression_ratios)

    def record_error(self, error_type: str):
        """记录错误"""
        self.metrics.total_errors += 1

        if error_type not in self.metrics.error_breakdown:
            self.metrics.error_breakdown[error_type] = 0
        self.metrics.error_breakdown[error_type] += 1

        # 错误率计算
        total_operations = self.metrics.tool_calls + self.metrics.llm_calls
        self.metrics.error_rate = self.metrics.total_errors / total_operations if total_operations > 0 else 0

    def get_summary(self) -> Dict:
        """生成性能摘要报告"""
        self.metrics.end_time = datetime.now()

        return {
            "execution": {
                "total_time": self.metrics.total_execution_time,
                "iterations": self.metrics.total_iterations,
                "avg_iteration_time": self.metrics.avg_iteration_time
            },
            "llm": {
                "calls": self.metrics.llm_calls,
                "total_tokens": self.metrics.llm_total_tokens,
                "avg_response_time": self.metrics.llm_avg_response_time
            },
            "tools": {
                "calls": self.metrics.tool_calls,
                "success_rate": f"{self.metrics.tool_success_rate * 100:.2f}%",
                "avg_execution_time": self.metrics.tool_avg_execution_time,
                "breakdown": self.metrics.tool_breakdown
            },
            "compression": {
                "compressions": self.metrics.context_compressions,
                "avg_ratio": f"{self.metrics.avg_compression_ratio * 100:.2f}%"
            },
            "errors": {
                "total": self.metrics.total_errors,
                "error_rate": f"{self.metrics.error_rate * 100:.2f}%",
                "breakdown": self.metrics.error_breakdown
            }
        }
```

### 8.2 实时监控与日志

```python
# loom/core/monitoring.py
import logging
from typing import Optional
from contextlib import asynccontextmanager

class AgentMonitor:
    """Agent 运行时监控器"""

    def __init__(self,
                 metrics_collector: MetricsCollector,
                 enable_logging: bool = True,
                 log_level: str = "INFO"):
        self.metrics = metrics_collector
        self.logger = self._setup_logger(enable_logging, log_level)

    def _setup_logger(self, enable: bool, level: str) -> logging.Logger:
        """配置日志记录器"""
        logger = logging.getLogger("loom.agent")
        logger.setLevel(getattr(logging, level))

        if enable:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    @asynccontextmanager
    async def track_iteration(self, iteration_num: int):
        """跟踪单次迭代"""
        start = time.time()
        self.logger.info(f"[Iteration {iteration_num}] Starting...")

        try:
            yield
            duration = time.time() - start
            self.metrics.record_iteration(duration)
            self.logger.info(f"[Iteration {iteration_num}] Completed in {duration:.2f}s")
        except Exception as e:
            self.logger.error(f"[Iteration {iteration_num}] Failed: {e}")
            raise

    @asynccontextmanager
    async def track_tool_execution(self, tool_name: str):
        """跟踪工具执行"""
        start = time.time()
        self.logger.debug(f"[Tool: {tool_name}] Executing...")

        success = True
        try:
            yield
            duration = time.time() - start
            self.logger.debug(f"[Tool: {tool_name}] Success in {duration:.2f}s")
        except Exception as e:
            success = False
            duration = time.time() - start
            self.logger.error(f"[Tool: {tool_name}] Failed: {e}")
            raise
        finally:
            self.metrics.record_tool_call(tool_name, success, duration)

    def log_compression(self, original_tokens: int, compressed_tokens: int):
        """记录压缩事件"""
        ratio = (compressed_tokens / original_tokens) * 100
        self.logger.info(
            f"[Compression] {original_tokens} → {compressed_tokens} tokens ({ratio:.1f}%)"
        )
        self.metrics.record_compression(original_tokens, compressed_tokens)
```

### 8.3 性能优化建议

基于监控数据，框架应提供自动优化建议：

```python
# loom/utils/optimizer.py
class PerformanceOptimizer:
    """性能优化建议生成器"""

    def analyze(self, metrics: PerformanceMetrics) -> List[str]:
        """分析性能指标并生成优化建议"""
        suggestions = []

        # LLM Token 使用分析
        if metrics.llm_total_tokens > 150000:
            suggestions.append(
                "⚠️  LLM Token 使用量较高，建议降低压缩阈值 (当前可能 > 0.92)"
            )

        # 工具执行分析
        if metrics.tool_success_rate < 0.8:
            suggestions.append(
                f"⚠️  工具成功率偏低 ({metrics.tool_success_rate*100:.1f}%)，"
                "检查工具参数验证和错误处理"
            )

        # 压缩效率分析
        if metrics.avg_compression_ratio < 0.5:
            suggestions.append(
                f"✅ 压缩效率良好 (压缩至 {metrics.avg_compression_ratio*100:.1f}%)"
            )
        elif metrics.avg_compression_ratio > 0.8:
            suggestions.append(
                "⚠️  压缩效率较低，考虑优化压缩提示或更换压缩策略"
            )

        # 错误率分析
        if metrics.error_rate > 0.1:
            top_error = max(metrics.error_breakdown.items(), key=lambda x: x[1])
            suggestions.append(
                f"⚠️  错误率较高 ({metrics.error_rate*100:.1f}%)，"
                f"主要错误类型: {top_error[0]}"
            )

        # 并发利用率分析
        if metrics.concurrent_tool_executions > 0:
            suggestions.append(
                f"✅ 并发执行 {metrics.concurrent_tool_executions} 次，性能良好"
            )
        else:
            suggestions.append(
                "💡 未使用并发执行，考虑标记工具为 concurrency_safe=True"
            )

        return suggestions
```

---

## 🛡️ 9. 错误处理与边界案例

### 9.1 分层错误处理架构

Loom 采用多层次错误处理策略，确保系统的健壮性。

```python
# loom/core/exceptions.py
class LoomException(Exception):
    """Loom 框架基础异常"""
    def __init__(self, message: str, recoverable: bool = False, context: Dict = None):
        super().__init__(message)
        self.recoverable = recoverable
        self.context = context or {}

# 工具执行异常
class ToolException(LoomException):
    """工具执行相关异常"""
    pass

class ToolNotFoundError(ToolException):
    """工具未找到"""
    def __init__(self, tool_name: str):
        super().__init__(
            f"Tool '{tool_name}' not found in registry",
            recoverable=True,
            context={"tool_name": tool_name}
        )

class ToolValidationError(ToolException):
    """工具参数验证失败"""
    def __init__(self, tool_name: str, validation_errors: List):
        super().__init__(
            f"Invalid arguments for tool '{tool_name}'",
            recoverable=True,
            context={"tool_name": tool_name, "errors": validation_errors}
        )

class ToolExecutionTimeout(ToolException):
    """工具执行超时"""
    def __init__(self, tool_name: str, timeout: int):
        super().__init__(
            f"Tool '{tool_name}' execution timeout after {timeout}s",
            recoverable=True,
            context={"tool_name": tool_name, "timeout": timeout}
        )

# 权限异常
class PermissionDeniedError(LoomException):
    """权限被拒绝"""
    def __init__(self, tool_name: str, reason: str = None):
        super().__init__(
            f"Permission denied for tool '{tool_name}'" + (f": {reason}" if reason else ""),
            recoverable=False,
            context={"tool_name": tool_name, "reason": reason}
        )

# LLM 异常
class LLMException(LoomException):
    """LLM 相关异常"""
    pass

class LLMRateLimitError(LLMException):
    """LLM API 速率限制"""
    def __init__(self, retry_after: int = None):
        super().__init__(
            f"LLM API rate limit exceeded" + (f", retry after {retry_after}s" if retry_after else ""),
            recoverable=True,
            context={"retry_after": retry_after}
        )

class LLMContextLengthError(LLMException):
    """上下文长度超限"""
    def __init__(self, current_tokens: int, max_tokens: int):
        super().__init__(
            f"Context length {current_tokens} exceeds maximum {max_tokens}",
            recoverable=True,
            context={"current_tokens": current_tokens, "max_tokens": max_tokens}
        )

# 内存异常
class MemoryException(LoomException):
    """内存管理异常"""
    pass

class CompressionFailedError(MemoryException):
    """压缩失败"""
    def __init__(self, reason: str):
        super().__init__(
            f"Context compression failed: {reason}",
            recoverable=True,
            context={"reason": reason}
        )

# 执行控制异常
class ExecutionAbortedError(LoomException):
    """执行被中断"""
    def __init__(self, reason: str = "User aborted"):
        super().__init__(reason, recoverable=False, context={"reason": reason})
```

### 9.2 错误恢复策略

```python
# loom/core/error_recovery.py
from typing import Callable, Any
import asyncio

class ErrorRecoveryStrategy:
    """错误恢复策略"""

    @staticmethod
    async def retry_with_exponential_backoff(
        func: Callable,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0
    ) -> Any:
        """指数退避重试"""
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                return await func()
            except LLMRateLimitError as e:
                if attempt == max_retries - 1:
                    raise

                wait_time = e.context.get("retry_after", delay)
                await asyncio.sleep(min(wait_time, max_delay))
                delay *= 2

    @staticmethod
    async def fallback_on_error(
        primary_func: Callable,
        fallback_func: Callable,
        recoverable_only: bool = True
    ) -> Any:
        """主备降级策略"""
        try:
            return await primary_func()
        except LoomException as e:
            if recoverable_only and not e.recoverable:
                raise
            return await fallback_func()

    @staticmethod
    def convert_to_tool_result(exception: Exception, tool_call: ToolCall) -> ToolResult:
        """将异常转换为工具结果 - 关键自愈机制"""
        if isinstance(exception, ToolValidationError):
            return ToolResult(
                tool_call_id=tool_call.id,
                status="error",
                content=f"参数验证失败: {exception.context.get('errors', str(exception))}\n"
                        f"请检查参数类型和格式，然后重试。",
                metadata={"error_type": "validation", "recoverable": True}
            )
        elif isinstance(exception, ToolExecutionTimeout):
            return ToolResult(
                tool_call_id=tool_call.id,
                status="error",
                content=f"工具执行超时 ({exception.context['timeout']}s)\n"
                        f"建议: 简化任务或分解为更小的子任务",
                metadata={"error_type": "timeout", "recoverable": True}
            )
        elif isinstance(exception, PermissionDeniedError):
            return ToolResult(
                tool_call_id=tool_call.id,
                status="error",
                content=f"权限被拒绝: {exception.context.get('reason', '未授权')}\n"
                        f"该工具需要用户明确授权或配置权限",
                metadata={"error_type": "permission", "recoverable": False}
            )
        else:
            return ToolResult(
                tool_call_id=tool_call.id,
                status="error",
                content=f"未知错误: {str(exception)}\n请尝试其他方法或报告此问题",
                metadata={"error_type": "unknown", "recoverable": False}
            )
```

### 9.3 边界案例处理

```python
# loom/core/boundary_cases.py
class BoundaryHandler:
    """边界案例处理器"""

    @staticmethod
    async def handle_empty_tool_response(result: Any, tool_name: str) -> ToolResult:
        """处理空工具响应"""
        if result is None or (isinstance(result, str) and not result.strip()):
            return ToolResult(
                content=f"⚠️  工具 '{tool_name}' 返回空结果，可能该操作无输出或执行失败",
                status="warning",
                metadata={"empty_response": True}
            )
        return result

    @staticmethod
    async def handle_max_iterations_reached(
        iteration: int,
        max_iterations: int,
        has_tool_calls: bool
    ) -> AgentStreamResponse:
        """处理达到最大迭代次数"""
        if has_tool_calls:
            message = (
                f"⚠️  已达到最大迭代次数 ({max_iterations})，但仍有未完成的工具调用。\n"
                "建议: 增加 max_iterations 或简化任务复杂度。"
            )
        else:
            message = f"✅ 任务在 {iteration} 次迭代内完成"

        return AgentStreamResponse(
            type="agent_finish",
            content=message,
            metadata={"iterations": iteration, "max_iterations": max_iterations}
        )

    @staticmethod
    async def handle_circular_tool_calls(
        tool_call_history: List[str],
        window_size: int = 5
    ) -> bool:
        """检测循环工具调用"""
        if len(tool_call_history) < window_size:
            return False

        recent_calls = tool_call_history[-window_size:]
        if len(set(recent_calls)) == 1:
            # 连续调用同一工具，可能陷入循环
            return True

        return False
```

---

## 🧪 10. 测试策略与质量保证

### 10.1 测试金字塔

Loom 采用完整的测试金字塔策略：

```
           ┌─────────────┐
           │  E2E Tests  │  ← 10% (完整场景)
           └─────────────┘
         ┌───────────────────┐
         │ Integration Tests │  ← 30% (组件协作)
         └───────────────────┘
      ┌─────────────────────────┐
      │     Unit Tests          │  ← 60% (单元逻辑)
      └─────────────────────────┘
```

### 10.2 单元测试 (Unit Tests)

```python
# tests/unit/test_tool_engine.py
import pytest
from loom.core.tool_engine import ToolExecutionPipeline, ExecutionStage
from loom.core.exceptions import ToolNotFoundError, ToolValidationError

class MockTool:
    name = "mock_tool"
    args_schema = {"type": "object", "properties": {"arg": {"type": "string"}}}
    is_concurrency_safe = True

    async def execute(self, arg: str):
        return f"Result: {arg}"

@pytest.mark.asyncio
async def test_tool_discovery_success():
    """测试工具发现 - 成功场景"""
    tools = {"mock_tool": MockTool()}
    pipeline = ToolExecutionPipeline(tools, None, None, None)

    tool_call = ToolCall(name="mock_tool", arguments={"arg": "test"})
    tool = await pipeline._stage_discover(tool_call)

    assert tool.name == "mock_tool"

@pytest.mark.asyncio
async def test_tool_discovery_not_found():
    """测试工具发现 - 工具不存在"""
    pipeline = ToolExecutionPipeline({}, None, None, None)

    tool_call = ToolCall(name="unknown_tool", arguments={})

    with pytest.raises(ToolNotFoundError) as exc_info:
        await pipeline._stage_discover(tool_call)

    assert "unknown_tool" in str(exc_info.value)

@pytest.mark.asyncio
async def test_tool_validation_success():
    """测试参数验证 - 成功场景"""
    tool = MockTool()
    pipeline = ToolExecutionPipeline({}, None, None, None)

    tool_call = ToolCall(name="mock_tool", arguments={"arg": "valid"})
    validated = await pipeline._stage_validate(tool, tool_call)

    assert validated["arg"] == "valid"

@pytest.mark.asyncio
async def test_tool_validation_failure():
    """测试参数验证 - 失败场景"""
    tool = MockTool()
    pipeline = ToolExecutionPipeline({}, None, None, None)

    tool_call = ToolCall(name="mock_tool", arguments={"wrong_arg": "value"})

    with pytest.raises(ToolValidationError):
        await pipeline._stage_validate(tool, tool_call)
```

### 10.3 集成测试 (Integration Tests)

```python
# tests/integration/test_agent_execution.py
import pytest
from loom import AgentExecutor
from loom.plugins.llms import MockLLM
from loom.plugins.tools import CalculatorTool

@pytest.mark.asyncio
async def test_agent_with_tool_execution():
    """测试 Agent 完整工具执行流程"""
    llm = MockLLM(responses=[
        {"type": "tool_call", "tool": "calculator", "args": {"expression": "2+2"}},
        {"type": "text", "content": "计算结果是 4"}
    ])

    tools = [CalculatorTool()]
    agent = AgentExecutor(llm=llm, tools=tools, max_iterations=5)

    responses = []
    async for response in agent.run("计算 2+2"):
        responses.append(response)

    # 验证流程
    assert any(r.type == "tool_calls_start" for r in responses)
    assert any(r.type == "tool_result" for r in responses)
    assert any(r.type == "agent_finish" for r in responses)

@pytest.mark.asyncio
async def test_context_compression_trigger():
    """测试上下文压缩触发"""
    llm = MockLLM()
    agent = AgentExecutor(
        llm=llm,
        tools=[],
        compression_threshold=0.01  # 极低阈值，立即触发压缩
    )

    # 添加大量消息
    for i in range(100):
        await agent.memory_backend.add_message(
            Message(role="user", content=f"Message {i}" * 100)
        )

    context = await agent.memory_manager.get_context()

    # 验证压缩发生
    assert any(msg.metadata.get("compressed") for msg in context)
```

### 10.4 端到端测试 (E2E Tests)

```python
# tests/e2e/test_complete_scenarios.py
import pytest
from loom import AgentExecutor
from loom.plugins.llms import OpenAILLM
from loom.plugins.tools import ReadFileTool, WriteFileTool, TaskTool

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_file_analysis_and_summary():
    """E2E: 文件分析与总结场景"""
    llm = OpenAILLM(api_key=os.getenv("OPENAI_API_KEY"))

    tools = [
        ReadFileTool(),
        WriteFileTool(),
        TaskTool(llm=llm, available_tools={})
    ]

    agent = AgentExecutor(
        llm=llm,
        tools=tools,
        permissions={"read_file": "allow", "write_file": "allow"},
        max_iterations=20
    )

    # 执行完整任务
    final_response = None
    async for response in agent.run(
        "读取 'data/input.txt'，分析内容，并将摘要写入 'data/summary.txt'"
    ):
        if response.type == "agent_finish":
            final_response = response

    # 验证结果
    assert final_response is not None
    assert Path("data/summary.txt").exists()

    # 验证性能指标
    metrics = agent.monitor.metrics.get_summary()
    assert metrics["tools"]["calls"] >= 2  # 至少读取和写入
    assert metrics["execution"]["iterations"] < 20
```

### 10.5 性能测试 (Performance Tests)

```python
# tests/performance/test_benchmarks.py
import pytest
import time
from loom import AgentExecutor

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_concurrent_tool_execution_performance():
    """性能测试: 并发工具执行"""
    tools = [SlowTool(delay=1.0, concurrency_safe=True) for _ in range(10)]
    agent = AgentExecutor(llm=MockLLM(), tools=tools)

    start = time.time()

    # 触发10个并发工具调用
    async for _ in agent.run("Execute all tools"):
        pass

    duration = time.time() - start

    # 并发执行应该 < 2秒 (而非串行的10秒)
    assert duration < 2.0, f"Concurrent execution too slow: {duration}s"

@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_compression_performance():
    """性能测试: 上下文压缩速度"""
    llm = MockLLM()
    compressor = StructuredCompressor(llm, CompressionConfig())

    # 生成大量消息
    messages = [
        Message(role="user", content=f"Message {i}" * 100)
        for i in range(1000)
    ]

    start = time.time()
    compressed = await compressor.compress(messages)
    duration = time.time() - start

    # 压缩应该 < 5秒
    assert duration < 5.0
    assert len(compressed) < len(messages)
```

### 10.6 CI/CD 集成

```yaml
# .github/workflows/test.yml
name: Loom Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=loom --cov-report=xml

      - name: Run integration tests
        run: |
          pytest tests/integration -v

      - name: Run E2E tests (main branch only)
        if: github.ref == 'refs/heads/main'
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/e2e -v -m e2e

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 🚀 11. 部署与生产环境考虑

### 11.1 生产级配置

```python
# loom/config/production.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProductionConfig:
    """生产环境配置"""

    # 性能配置
    max_iterations: int = 50
    context_window: int = 200000
    compression_threshold: float = 0.92
    max_concurrency: int = 10
    tool_timeout_seconds: int = 120

    # 安全配置
    enable_permission_system: bool = True
    default_permission: str = "deny"
    require_user_confirmation_for: List[str] = None

    # 可观测性
    enable_metrics: bool = True
    enable_logging: bool = True
    log_level: str = "INFO"
    metrics_export_interval: int = 60  # seconds

    # 稳定性
    enable_circuit_breaker: bool = True
    error_threshold: float = 0.5  # 50% 错误率触发熔断
    circuit_breaker_timeout: int = 60  # seconds

    # LLM 配置
    llm_rate_limit_rpm: int = 60
    llm_retry_max_attempts: int = 3
    llm_retry_exponential_base: float = 2.0

    # 内存管理
    enable_auto_compression: bool = True
    enable_state_persistence: bool = True
    state_backup_interval: int = 300  # seconds

    def __post_init__(self):
        if self.require_user_confirmation_for is None:
            self.require_user_confirmation_for = [
                "write_file",
                "delete_file",
                "execute_bash",
                "network_request"
            ]
```

### 11.2 容器化部署

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml README.md ./
COPY loom ./loom

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV LOOM_ENV=production

# 暴露端口 (如果有 API 服务)
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import loom; print('healthy')"

# 启动命令
CMD ["python", "-m", "loom.server"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  loom-agent:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOOM_ENV=production
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

volumes:
  redis-data:
  prometheus-data:
```

### 11.3 监控与告警

```python
# loom/observability/prometheus.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server

class PrometheusMetrics:
    """Prometheus 指标导出"""

    def __init__(self, port: int = 9091):
        # 计数器
        self.iterations_total = Counter(
            'loom_iterations_total',
            'Total number of agent iterations'
        )

        self.tool_calls_total = Counter(
            'loom_tool_calls_total',
            'Total number of tool calls',
            ['tool_name', 'status']
        )

        self.llm_calls_total = Counter(
            'loom_llm_calls_total',
            'Total number of LLM API calls'
        )

        # 直方图 (延迟分布)
        self.iteration_duration = Histogram(
            'loom_iteration_duration_seconds',
            'Agent iteration duration'
        )

        self.tool_execution_duration = Histogram(
            'loom_tool_execution_duration_seconds',
            'Tool execution duration',
            ['tool_name']
        )

        # 仪表盘 (当前状态)
        self.active_agents = Gauge(
            'loom_active_agents',
            'Number of currently active agents'
        )

        self.context_tokens = Gauge(
            'loom_context_tokens',
            'Current context window token count'
        )

        # 启动 HTTP 服务器
        start_http_server(port)

    def record_tool_call(self, tool_name: str, status: str, duration: float):
        """记录工具调用"""
        self.tool_calls_total.labels(tool_name=tool_name, status=status).inc()
        self.tool_execution_duration.labels(tool_name=tool_name).observe(duration)
```

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'loom-agent'
    static_configs:
      - targets: ['loom-agent:9091']
```

### 11.4 熔断与降级

```python
# loom/resilience/circuit_breaker.py
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # 正常运行
    OPEN = "open"          # 熔断开启
    HALF_OPEN = "half_open"  # 半开状态

class CircuitBreaker:
    """熔断器 - 防止级联失败"""

    def __init__(self,
                 failure_threshold: float = 0.5,
                 timeout: int = 60,
                 expected_exception: type = LoomException):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    async def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """成功回调"""
        self.success_count += 1

        if self.state == CircuitState.HALF_OPEN:
            # 半开状态下成功，关闭熔断器
            self.state = CircuitState.CLOSED
            self.failure_count = 0

    def _on_failure(self):
        """失败回调"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        total = self.failure_count + self.success_count
        if total > 0:
            failure_rate = self.failure_count / total

            if failure_rate >= self.failure_threshold:
                self.state = CircuitState.OPEN
```

### 11.5 安全加固

```python
# loom/security/sandbox.py
import ast
from typing import Set

class SecureToolValidator:
    """工具安全验证器"""

    DANGEROUS_MODULES = {
        'os', 'subprocess', 'sys', 'eval', 'exec',
        '__import__', 'open', 'file'
    }

    @classmethod
    def validate_tool_code(cls, code: str) -> bool:
        """验证工具代码是否安全"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False

        for node in ast.walk(tree):
            # 检查导入
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in cls.DANGEROUS_MODULES:
                        return False

            # 检查函数调用
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in cls.DANGEROUS_MODULES:
                        return False

        return True

    @classmethod
    def sanitize_tool_output(cls, output: str, max_length: int = 10000) -> str:
        """清理工具输出"""
        # 限制长度
        if len(output) > max_length:
            output = output[:max_length] + "\n... (truncated)"

        # 移除敏感信息模式 (API keys, tokens, etc.)
        import re
        patterns = [
            r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
            r'ghp_[a-zA-Z0-9]{36}',  # GitHub tokens
            r'Bearer [a-zA-Z0-9\-._~+/]+=*',  # Bearer tokens
        ]

        for pattern in patterns:
            output = re.sub(pattern, '[REDACTED]', output)

        return output
```

---

## 📚 12. 最佳实践与使用指南

### 12.1 工具设计最佳实践

```python
# 示例: 设计良好的工具
from loom.interfaces.tool import Tool
from pydantic import BaseModel, Field

class FileSearchArgs(BaseModel):
    """工具参数定义 - 使用 Pydantic 进行验证"""
    pattern: str = Field(..., description="搜索模式 (支持通配符)")
    directory: str = Field(".", description="搜索目录")
    max_results: int = Field(100, ge=1, le=1000, description="最大结果数")

class FileSearchTool(Tool):
    """文件搜索工具 - 最佳实践示例"""

    name = "file_search"
    description = "在指定目录中搜索文件，支持通配符模式"
    args_schema = FileSearchArgs
    is_concurrency_safe = True  # 只读操作，并发安全

    async def execute(self, pattern: str, directory: str = ".", max_results: int = 100):
        """执行文件搜索"""
        try:
            # 1. 输入验证 (已由 Pydantic 完成)

            # 2. 安全检查
            if not self._is_safe_directory(directory):
                raise PermissionDeniedError(self.name, "Directory access denied")

            # 3. 执行核心逻辑
            results = await self._search_files(pattern, directory, max_results)

            # 4. 格式化输出
            return {
                "files": results,
                "count": len(results),
                "pattern": pattern
            }

        except Exception as e:
            # 5. 错误处理
            return {"error": str(e), "files": []}

    def _is_safe_directory(self, directory: str) -> bool:
        """安全目录检查"""
        dangerous_paths = ['/etc', '/sys', '/proc', '~/.ssh']
        return not any(directory.startswith(p) for p in dangerous_paths)
```

### 12.2 Agent 配置模板

```python
# examples/configs/production_agent.py
from loom import AgentExecutor
from loom.plugins.llms import OpenAILLM
from loom.plugins.tools import *
from loom.config import ProductionConfig

def create_production_agent():
    """生产级 Agent 配置"""

    # 1. 配置 LLM
    llm = OpenAILLM(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4",
        temperature=0.7,
        max_retries=3
    )

    # 2. 配置工具集
    tools = [
        # 文件操作工具
        ReadFileTool(),
        WriteFileTool(),
        GlobTool(),

        # 代码工具
        GrepTool(),
        PythonREPLTool(),

        # Sub-Agent 支持
        TaskTool(
            llm=llm,
            available_tools={
                "read_file": ReadFileTool(),
                "grep": GrepTool(),
            }
        ),
    ]

    # 3. 配置权限
    permissions = {
        "read_file": "allow",
        "glob": "allow",
        "grep": "allow",
        "write_file": "ask",
        "python_repl": "ask",
        "execute_bash": "deny",
        "default": "deny"
    }

    # 4. 创建 Agent
    config = ProductionConfig()
    agent = AgentExecutor(
        llm=llm,
        tools=tools,
        permissions=permissions,
        max_iterations=config.max_iterations,
        compression_threshold=config.compression_threshold,
        enable_metrics=config.enable_metrics,
        enable_logging=config.enable_logging
    )

    return agent
```

### 12.3 常见问题解决方案

#### 问题1: 上下文长度超限

```python
# 解决方案: 激进压缩 + 更早触发
agent = AgentExecutor(
    llm=llm,
    tools=tools,
    compression_threshold=0.80,  # 降低阈值，更早触发
    compression_strategy=StructuredCompressor(
        llm=llm,
        config=CompressionConfig(
            target_ratio=0.50,  # 目标压缩到 50%
            max_tokens_per_section=256  # 减少每段 token 数
        )
    )
)
```

#### 问题2: 工具执行超时

```python
# 解决方案: 增加超时时间 + 优化工具逻辑
from loom.core.scheduler import SchedulerConfig

agent = AgentExecutor(
    llm=llm,
    tools=tools,
    scheduler_config=SchedulerConfig(
        timeout_seconds=300,  # 增加到 5 分钟
        max_concurrency=5  # 减少并发以降低负载
    )
)
```

#### 问题3: LLM 循环调用工具

```python
# 解决方案: 添加循环检测
from loom.core.boundary_cases import BoundaryHandler

class AntiLoopAgentExecutor(AgentExecutor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_call_history = []

    async def run(self, user_input: str):
        async for response in super().run(user_input):
            if response.type == "tool_calls_start":
                # 检测循环
                for tc in response.tool_calls:
                    self.tool_call_history.append(tc.name)

                if BoundaryHandler.handle_circular_tool_calls(self.tool_call_history):
                    yield AgentStreamResponse(
                        type="error",
                        content="检测到循环工具调用，已中断执行"
                    )
                    break

            yield response
```

---

## 🎓 13. 总结与未来规划

### 13.1 v1.2 版本总结

Loom Agent Framework v1.2 已经是一个功能完备、工程化的 Agent 框架：

**核心能力**:
- ✅ 完整的 nO 主循环实现
- ✅ 6 阶段工具执行流水线 (MH1)
- ✅ 8 段式结构化压缩 (AU2/wU2)
- ✅ 智能并发调度 (UH1, gW5)
- ✅ 实时 Steering 控制 (h2A)
- ✅ Sub-Agent 任务分层
- ✅ 全面的错误处理与恢复
- ✅ 企业级监控与可观测性

**工程质量**:
- ✅ 完整的测试覆盖 (单元/集成/E2E)
- ✅ 生产级部署配置
- ✅ 安全加固机制
- ✅ 性能优化与熔断降级

### 13.2 未来规划 (v2.0)

#### Phase 1: 增强能力
- 🔄 多模态支持 (Vision, Audio, Video Tools)
- 🔄 流式工具执行 (工具结果实时流式返回)
- 🔄 分布式 Agent 集群
- 🔄 知识库集成 (RAG)

#### Phase 2: 生态扩展
- 🔄 工具市场 (Tool Marketplace)
- 🔄 LLM 适配器插件 (Anthropic, Gemini, Local Models)
- 🔄 可视化 Agent 编排 (Low-Code Builder)
- 🔄 Agent 协作协议 (Multi-Agent Communication)

#### Phase 3: 企业特性
- 🔄 细粒度权限控制 (RBAC)
- 🔄 审计日志与合规
- 🔄 成本追踪与预算控制
- 🔄 SLA 保证与故障隔离

---

## 📖 附录

### A. 术语表

- **nO**: Agent 主循环函数
- **h2A**: Human-to-Agent 异步消息队列 (EventBus)
- **MH1**: 6 阶段工具执行流水线
- **UH1**: 并发调度控制算法
- **wU2/AU2**: 8 段式结构化上下文压缩
- **gW5**: 最大并发数限制 (Semaphore)
- **TaskTool**: Sub-Agent 任务委托工具

### B. API 参考

详细 API 文档请访问: `docs/api/README.md`

### C. 贡献指南

欢迎贡献代码! 请查看 `CONTRIBUTING.md`

### D. 许可证

Loom 采用 MIT 许可证开源 - 详见 `LICENSE` 文件

---

**文档版本**: v1.3
**最后更新**: 2025-10
**维护者**: Loom Team

这份完善的设计文档现在已经达到生产级标准，涵盖了从架构设计到工程实践的全部关键内容! 🚀