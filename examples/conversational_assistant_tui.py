"""
对话助手 TUI Demo - 基于Textual的交互式界面

特性：
- 实时对话交互
- 可观测的思考过程
- 智能RAG知识库
- 工具和Skill集成
- 流式输出

运行：
  OPENAI_API_KEY=... python examples/conversational_assistant_tui.py

快捷键：
  - Tab: 切换面板
  - Ctrl+C: 退出
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from loom.agent import Agent
from loom.tools.registry import ToolRegistry
from loom.config.llm import LLMConfig
from loom.events import EventBus
from loom.protocol import Task
from loom.providers.knowledge.base import KnowledgeBaseProvider, KnowledgeItem
from loom.providers.llm.openai import OpenAIProvider

# ==================== 数据结构 ====================


@dataclass
class ParadigmStats:
    """范式统计 - 跟踪各种AI能力的使用"""

    reflection_events: int = 0
    tool_calls: int = 0
    planning_events: int = 0
    collaboration_events: int = 0
    context_queries: int = 0
    tool_creation_events: int = 0
    created_tools: list[str] = field(default_factory=list)


@dataclass
class ConversationState:
    """对话状态（增强版 - 综合两个demo的优势）"""

    # ===== 原有字段（conversational_assistant_tui.py）=====
    # 对话历史
    messages: list[dict[str, str]] = field(default_factory=list)

    # 知识库查询记录
    knowledge_queries: int = 0

    # 当前回合使用的知识项
    current_knowledge_items: list[dict] = field(default_factory=list)

    # 统计信息
    total_messages: int = 0
    total_tokens: int = 0

    # ===== 新增字段（参考cli_stream_demo_v4.py）=====
    # 分形agent跟踪
    current_thinking: dict[str, str] = field(default_factory=dict)  # base_task_id -> content
    thinking_order: list[str] = field(default_factory=list)  # 思考顺序
    node_depth: dict[str, int] = field(default_factory=dict)  # 节点深度
    task_nodes: dict[str, str] = field(default_factory=dict)  # task_id -> node_id
    parent_map: dict[str, str | None] = field(default_factory=dict)  # 父子关系
    task_names: dict[str, str] = field(default_factory=dict)  # 任务名称

    # 流式显示
    pending_sentences: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (task_id, node_id, chunk)

    # 工具调用跟踪（增强版）
    tool_calls: list[tuple[str, str, str, dict]] = field(
        default_factory=list
    )  # (task_id, node_id, tool, args)
    tool_results: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # (task_id, node_id, tool, result)

    # 规划事件
    plans: list[tuple[str, str, dict]] = field(default_factory=list)  # (task_id, node_id, plan)

    # 运行状态
    nodes_used: set[str] = field(default_factory=set)
    tasks_seen: set[str] = field(default_factory=set)
    running_nodes: set[str] = field(default_factory=set)
    running_tasks: set[str] = field(default_factory=set)
    max_depth: int = 0

    # 范式统计
    paradigms: ParadigmStats = field(default_factory=ParadigmStats)

    # 显示模式
    continuous_mode: bool = True  # 连续模式：合并子agent输出
    current_paradigm: str = "Idle"
    is_processing: bool = False


# ==================== 辅助函数 ====================


def shorten_id(full_id: str, length: int = 8) -> str:
    """缩短长ID以便显示"""
    if len(full_id) <= length:
        return full_id
    parts = full_id.split("-")
    if len(parts) > 1:
        return parts[-1][:length]
    return full_id[:length]


# ==================== 知识库 ====================


class ConversationalKnowledgeBase(KnowledgeBaseProvider):
    """对话知识库"""

    def __init__(self):
        self.knowledge_data = [
            {
                "id": "kb_python_001",
                "content": "Python异步编程基于事件循环和协程，使用async/await语法。",
                "source": "Python指南",
                "tags": ["python", "async"],
            },
            {
                "id": "kb_llm_001",
                "content": "大语言模型通过Transformer架构学习语言规律。",
                "source": "LLM概览",
                "tags": ["llm", "ai"],
            },
            {
                "id": "kb_rag_001",
                "content": "RAG结合检索和生成，提供更准确的答案。",
                "source": "RAG技术",
                "tags": ["rag", "retrieval"],
            },
        ]

    async def query(self, query: str, limit: int = 3) -> list[KnowledgeItem]:
        """查询知识库"""
        query_lower = query.lower()
        results = []

        for item in self.knowledge_data:
            relevance = 0.0
            if query_lower in item["content"].lower():
                relevance = 0.9
            elif any(query_lower in tag for tag in item["tags"]):
                relevance = 0.8

            if relevance > 0:
                results.append(
                    KnowledgeItem(
                        id=item["id"],
                        content=item["content"],
                        source=item["source"],
                        relevance=relevance,
                    )
                )

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:limit]

    async def get_by_id(self, knowledge_id: str) -> KnowledgeItem | None:
        """根据ID获取知识项"""
        for item in self.knowledge_data:
            if item["id"] == knowledge_id:
                return KnowledgeItem(
                    id=item["id"],
                    content=item["content"],
                    source=item["source"],
                    relevance=1.0,
                )
        return None


# ==================== 工具定义 ====================


# 工具实现函数
async def calculator(expression: str) -> str:
    """
    计算器工具实现

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        # 使用 eval 计算表达式（注意：生产环境应使用更安全的方法）
        result = eval(expression, {"__builtins__": {}}, {})
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


async def search_knowledge(query: str) -> str:
    """
    搜索知识库工具实现

    Args:
        query: 搜索查询

    Returns:
        搜索结果
    """
    # 注意：这个函数会在 main() 中被重新定义，以访问 knowledge_base
    return "知识库搜索功能需要在初始化后使用"


def create_calculator_tool():
    """计算器工具"""
    return {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "执行数学计算",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "数学表达式"}},
                "required": ["expression"],
            },
        },
    }


def create_search_tool():
    """搜索工具"""
    return {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "搜索知识库中的相关信息",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "搜索查询"}},
                "required": ["query"],
            },
        },
    }


# ==================== 事件处理器 ====================


class EventProcessor:
    """事件处理器 - 处理Agent事件并更新TUI（增强版 - 综合两个demo）"""

    def __init__(self, app: "ConversationalAssistantApp", session_id: str):
        self.app = app
        self.session_id = session_id
        self.state = app.state  # 直接引用app的state

        # 原有字段（保留兼容性）
        self.current_stage = None
        self.knowledge_items = []
        self.streaming_response = ""
        self.is_streaming = False

    def _base_task_id(self, event_task_id: str) -> str:
        """提取基础task ID"""
        if ":event:" in event_task_id:
            return event_task_id.split(":event:", 1)[0]
        return event_task_id

    def _infer_parent(self, task_id: str) -> str | None:
        """推断父task ID"""
        for marker in ("-child-", "-step-"):
            if marker in task_id:
                return task_id.split(marker, 1)[0]
        return None

    def _calculate_depth(self, task_id: str) -> int:
        """计算任务在层级中的深度"""
        depth = 0
        current = task_id
        while current in self.state.parent_map and self.state.parent_map[current] is not None:
            depth += 1
            parent = self.state.parent_map[current]
            assert parent is not None
            current = parent
            if depth > 10:  # 防止无限循环
                break
        return depth

    async def on_event(self, task: Task) -> Task:
        """处理事件（增强版 - 添加分形agent跟踪）"""
        # 安全检查：确保 parameters 不为 None
        if task.parameters is None:
            return task

        # Session过滤
        if task.session_id != self.session_id:
            return task

        # 提取节点信息
        node_id = task.parameters.get("node_id", "unknown")
        if node_id:
            self.state.nodes_used.add(node_id)

        # 提取base_task_id并跟踪
        base_task_id = self._base_task_id(task.task_id)
        if base_task_id not in self.state.tasks_seen:
            self.state.tasks_seen.add(base_task_id)
            self.state.parent_map[base_task_id] = self._infer_parent(base_task_id)
            self.state.task_names[base_task_id] = shorten_id(base_task_id)
            depth = self._calculate_depth(base_task_id)
            self.state.node_depth[base_task_id] = depth
            if depth > self.state.max_depth:
                self.state.max_depth = depth

        if base_task_id not in self.state.task_nodes and node_id:
            self.state.task_nodes[base_task_id] = node_id

        # 路由到具体的事件处理器
        action = task.action
        if action == "node.thinking":
            await self._handle_thinking(task, base_task_id, node_id)
        elif action == "node.tool_call":
            await self._handle_tool_call(task, base_task_id, node_id)
        elif action == "node.tool_result":
            await self._handle_tool_result(task, base_task_id, node_id)
        elif action == "node.planning":
            await self._handle_planning(task, base_task_id, node_id)
        elif action == "node.knowledge_query":
            await self._handle_knowledge_query(task, base_task_id, node_id)
        elif action == "node.knowledge_result":
            await self._handle_knowledge_result(task, base_task_id, node_id)
        elif action == "node.response":
            await self._handle_response(task, base_task_id, node_id)
        elif action in {"node.start", "node.complete"}:
            await self._handle_lifecycle(task, base_task_id)

        return task

    async def _handle_thinking(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理思考事件 - 累积内容并支持流式显示"""
        content = task.parameters.get("content", "")
        stage = task.parameters.get("stage", None)

        if not content:
            return

        # 累积思考内容（按task_id分组）
        if base_task_id not in self.state.current_thinking:
            self.state.current_thinking[base_task_id] = ""
            self.state.thinking_order.append(base_task_id)

        self.state.current_thinking[base_task_id] += content

        # 添加到pending_sentences用于流式显示
        self.state.pending_sentences.append((base_task_id, node_id, content))

        # 更新范式统计
        self.state.current_paradigm = "Reflection"
        self.state.paradigms.reflection_events += 1

        # 显示逻辑：根据continuous_mode决定如何显示
        if self.state.continuous_mode:
            # 连续模式：在聊天窗口中流式显示，不显示节点ID
            if stage and stage != self.current_stage:
                self.current_stage = stage
                if stage == "generating":
                    self.is_streaming = True
                    self.streaming_response = ""
                    await self.app.start_streaming_response()

            if self.is_streaming:
                self.streaming_response += content
                await self.app.update_streaming_response(content)
            else:
                # 在思考面板显示
                await self.app.update_thinking(content)
        else:
            # 详细模式：显示节点信息
            if stage and stage != self.current_stage:
                self.current_stage = stage
                await self.app.show_thinking_stage(stage)

            await self.app.update_thinking(content)

    async def _handle_tool_call(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理工具调用事件"""
        tool_name = task.parameters.get("tool_name", "")
        tool_args = task.parameters.get("tool_args", {})

        self.state.tool_calls.append((base_task_id, node_id, tool_name, tool_args))

        # 更新范式统计
        if tool_name == "create_plan":
            self.state.paradigms.planning_events += 1
            self.state.current_paradigm = "Planning"
        elif tool_name == "delegate_task":
            self.state.paradigms.collaboration_events += 1
            self.state.current_paradigm = "Collaboration"
        elif tool_name == "create_tool":
            self.state.paradigms.tool_creation_events += 1
            self.state.current_paradigm = "Tool Creation"
            created_tool = tool_args.get("tool_name", "")
            if created_tool:
                self.state.paradigms.created_tools.append(created_tool)
        elif tool_name.startswith("query_"):
            self.state.paradigms.context_queries += 1
            self.state.current_paradigm = "Context Query"
        else:
            self.state.paradigms.tool_calls += 1
            self.state.current_paradigm = "Tool Use"

        # 显示工具调用
        await self.app.add_tool_call(tool_name, tool_args)

    async def _handle_tool_result(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理工具结果事件"""
        tool_name = task.parameters.get("tool_name", "")
        result = task.parameters.get("result", "")
        result_str = result if isinstance(result, str) else str(result)

        self.state.tool_results.append((base_task_id, node_id, tool_name, result_str))

        # 显示工具结果（可选，避免过多输出）
        # await self.app.add_tool_result(tool_name, result_str)

    async def _handle_planning(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理规划事件"""
        plan = {
            "goal": task.parameters.get("goal", ""),
            "steps": task.parameters.get("steps", []),
            "reasoning": task.parameters.get("reasoning", ""),
            "step_count": task.parameters.get("step_count", 0),
        }
        self.state.plans.append((base_task_id, node_id, plan))
        self.state.current_paradigm = "Planning"

        # 在思考面板显示规划
        await self.app.show_planning(plan)

    async def _handle_knowledge_query(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理知识库查询事件"""
        query = task.parameters.get("query", "")
        await self.app.show_knowledge_query(query)

    async def _handle_knowledge_result(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理知识库查询结果事件"""
        items = task.parameters.get("items", [])
        self.knowledge_items = items
        self.state.current_knowledge_items = items
        await self.app.show_knowledge_results(items)

    async def _handle_response(self, task: Task, base_task_id: str, node_id: str) -> None:
        """处理最终响应事件"""
        response = task.parameters.get("content", "")

        # 如果有流式响应，使用累积的内容
        if self.is_streaming and self.streaming_response:
            response = self.streaming_response
            await self.app.finish_streaming_response()
        else:
            # 非流式响应，直接显示
            await self.app.add_response(response)

        # 重置状态
        self.current_stage = None
        self.knowledge_items = []
        self.streaming_response = ""
        self.is_streaming = False

    async def _handle_lifecycle(self, task: Task, base_task_id: str) -> None:
        """处理生命周期事件"""
        if task.action == "node.start":
            self.state.running_tasks.add(base_task_id)
        else:
            self.state.running_tasks.discard(base_task_id)


# ==================== TUI 组件 ====================


class ChatWindow(RichLog):
    """聊天窗口"""

    def __init__(self):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self.border_title = "💬 对话"


class ThinkingPanel(RichLog):
    """思考面板"""

    def __init__(self):
        super().__init__(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=True,
        )
        self.border_title = "💭 思考过程"


class StatsPanel(Static):
    """统计面板（增强版 - 显示范式统计和分形agent信息）"""

    def __init__(self, state: ConversationState):
        super().__init__()
        self.border_title = "📊 统计"
        self.state = state

    def update_display(self):
        """更新统计显示"""
        self.update(self._render_stats())

    def _render_stats(self) -> str:
        """渲染统计信息（增强版）"""
        # 基础统计
        basic_stats = f"""[bold cyan]对话统计[/bold cyan]
消息数: {self.state.total_messages}
工具调用: {len(self.state.tool_calls)}
知识查询: {self.state.knowledge_queries}
"""

        # 分形Agent统计
        fractal_stats = f"""
[bold green]分形Agent[/bold green]
节点数: {len(self.state.nodes_used)}
任务数: {len(self.state.tasks_seen)}
最大深度: {self.state.max_depth}
当前范式: {self.state.current_paradigm}
"""

        # 范式统计
        paradigm_stats = f"""
[bold magenta]范式统计[/bold magenta]
反思事件: {self.state.paradigms.reflection_events}
规划事件: {self.state.paradigms.planning_events}
协作事件: {self.state.paradigms.collaboration_events}
工具创建: {self.state.paradigms.tool_creation_events}
上下文查询: {self.state.paradigms.context_queries}
"""

        return basic_stats + fractal_stats + paradigm_stats


# ==================== 主应用 ====================


class ConversationalAssistantApp(App):
    """对话助手 TUI 应用"""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #left-panel {
        width: 2fr;
        layout: vertical;
    }

    #right-panel {
        width: 1fr;
        layout: vertical;
    }

    ChatWindow {
        height: 1fr;
        border: solid green;
    }

    ThinkingPanel {
        height: 1fr;
        border: solid yellow;
    }

    StatsPanel {
        height: 10;
        border: solid cyan;
    }

    Input {
        dock: bottom;
    }
    """

    def __init__(self, agent: Any, session_id: str):
        super().__init__()
        self.agent = agent
        self.session_id = session_id
        self.state = ConversationState()
        self.chat_window = None
        self.thinking_panel = None
        self.stats_panel = None
        self.event_queue: asyncio.Queue = asyncio.Queue()

    def compose(self) -> ComposeResult:
        """组合UI"""
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="left-panel"):
                self.chat_window = ChatWindow()
                yield self.chat_window
            with Vertical(id="right-panel"):
                self.thinking_panel = ThinkingPanel()
                yield self.thinking_panel
                self.stats_panel = StatsPanel(self.state)
                yield self.stats_panel
        yield Input(placeholder="输入消息... (输入 'quit' 退出)")
        yield Footer()

    async def on_mount(self):
        """应用启动时"""
        self.chat_window.write("[bold green]🤖 对话助手已启动[/bold green]")
        self.chat_window.write("[dim]特性: 智能RAG | 工具调用 | Skill集成 | 可观测思考[/dim]")
        self.chat_window.write("")

    async def on_input_submitted(self, event: Input.Submitted):
        """处理用户输入"""
        user_input = event.value.strip()
        if not user_input:
            return

        # 清空输入框
        event.input.value = ""

        # 检查退出命令
        if user_input.lower() in ["quit", "exit", "退出"]:
            self.exit()
            return

        # 显示用户消息
        self.chat_window.write(f"[bold cyan]👤 你:[/bold cyan] {user_input}")
        self.chat_window.write("")

        # 清空思考面板
        self.thinking_panel.clear()

        # 处理消息
        await self._process_message(user_input)

    async def update_thinking(self, content: str):
        """更新思考面板"""
        self.thinking_panel.write(content, end="")

    async def show_thinking_stage(self, stage: str):
        """显示思考阶段"""
        stage_names = {
            "understanding": "🤔 理解问题",
            "retrieving": "📚 检索知识",
            "analyzing": "🔍 分析推理",
            "generating": "✍️ 生成回答",
        }
        stage_display = stage_names.get(stage, f"💭 {stage}")
        self.thinking_panel.write(f"\n\n[bold magenta]{'='*40}[/bold magenta]")
        self.thinking_panel.write(f"\n[bold magenta]{stage_display}[/bold magenta]")
        self.thinking_panel.write(f"\n[bold magenta]{'='*40}[/bold magenta]\n")

    async def show_knowledge_query(self, query: str):
        """显示知识库查询"""
        self.state.knowledge_queries += 1
        self.thinking_panel.write(f"\n[bold yellow]📚 查询知识库:[/bold yellow] [dim]{query}[/dim]")
        self._update_stats()

    async def show_knowledge_results(self, items: list):
        """显示知识库查询结果"""
        if items:
            self.thinking_panel.write(
                f"\n[bold yellow]✓ 检索到 {len(items)} 条相关知识:[/bold yellow]"
            )
            for i, item in enumerate(items, 1):
                relevance = item.get("relevance", 0.0)
                source = item.get("source", "未知来源")
                content_preview = item.get("content", "")[:60] + "..."
                self.thinking_panel.write(
                    f"\n  {i}. [dim]({relevance:.2f})[/dim] {source}: {content_preview}"
                )
        else:
            self.thinking_panel.write("\n[dim]未找到相关知识[/dim]")

    async def show_planning(self, plan: dict):
        """显示规划事件"""
        goal = plan.get("goal", "")
        steps = plan.get("steps", [])
        reasoning = plan.get("reasoning", "")

        self.thinking_panel.write("\n[bold cyan]📋 规划:[/bold cyan]")
        if goal:
            self.thinking_panel.write(f"  目标: {goal}")
        if reasoning:
            self.thinking_panel.write(f"  推理: {reasoning}")
        if steps:
            self.thinking_panel.write(f"  步骤 ({len(steps)}):")
            for i, step in enumerate(steps, 1):
                self.thinking_panel.write(f"    {i}. {step}")

    async def add_tool_call(self, tool_name: str, tool_args: dict = None):
        """添加工具调用记录"""
        self.state.tool_calls.append((tool_name, tool_args or {}))
        args_str = ""
        if tool_args:
            args_preview = str(tool_args)[:50]
            args_str = (
                f" [dim]({args_preview}...)[/dim]"
                if len(str(tool_args)) > 50
                else f" [dim]({args_preview})[/dim]"
            )
        self.thinking_panel.write(f"\n[bold green]🔧 调用工具: {tool_name}{args_str}[/bold green]")
        self._update_stats()

    async def increment_knowledge_queries(self):
        """增加知识库查询计数（保留兼容性）"""
        self.state.knowledge_queries += 1
        self._update_stats()

    async def add_response(self, response: str):
        """添加助手响应（优化版 - 显示知识来源）"""
        self.chat_window.write(f"[bold green]🤖 助手:[/bold green] {response}")

        # 如果使用了知识库，显示知识来源
        if self.state.current_knowledge_items:
            sources = set()
            for item in self.state.current_knowledge_items:
                source = item.get("source", "未知来源")
                sources.add(source)

            if sources:
                sources_str = ", ".join(sources)
                self.chat_window.write(f"[dim]📚 参考来源: {sources_str}[/dim]")

        self.chat_window.write("")
        self.state.total_messages += 1
        # 清空当前知识项，准备下一轮
        self.state.current_knowledge_items = []
        self._update_stats()

    async def start_streaming_response(self):
        """开始流式响应（打字机效果）"""
        self.chat_window.write("[bold green]🤖 助手:[/bold green] ", end="")

    async def update_streaming_response(self, content: str):
        """更新流式响应（逐字符显示）"""
        self.chat_window.write(content, end="")

    async def finish_streaming_response(self):
        """完成流式响应"""
        # 如果使用了知识库，显示知识来源
        if self.state.current_knowledge_items:
            sources = set()
            for item in self.state.current_knowledge_items:
                source = item.get("source", "未知来源")
                sources.add(source)

            if sources:
                sources_str = ", ".join(sources)
                self.chat_window.write(f"\n[dim]📚 参考来源: {sources_str}[/dim]")

        self.chat_window.write("")
        self.state.total_messages += 1
        # 清空当前知识项，准备下一轮
        self.state.current_knowledge_items = []
        self._update_stats()

    def _update_stats(self):
        """更新统计面板"""
        self.stats_panel.update_display()

    async def process_events(self) -> None:
        """处理事件队列并实现流式显示（参考demo_v4）"""
        displayed_chunks = 0
        displayed_tool_calls = 0
        current_node_buffer: dict[str, str] = {}
        last_display_time = 0.0

        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                if event is None:  # 停止信号
                    break

                # 处理事件（更新state）
                # EventProcessor会更新self.state

                import time

                current_time = time.time()

                # 处理新的思考内容
                if len(self.state.pending_sentences) > displayed_chunks:
                    new_chunks = self.state.pending_sentences[displayed_chunks:]
                    for base_task_id, _, chunk in new_chunks:
                        if base_task_id not in current_node_buffer:
                            current_node_buffer[base_task_id] = ""
                        current_node_buffer[base_task_id] += chunk
                    displayed_chunks = len(self.state.pending_sentences)

                # 每0.3秒批量显示
                if current_time - last_display_time > 0.3 and current_node_buffer:
                    for base_task_id, content in list(current_node_buffer.items()):
                        if content:
                            await self.update_streaming_response(content)
                            current_node_buffer[base_task_id] = ""
                    last_display_time = current_time

                # 处理工具调用
                if len(self.state.tool_calls) > displayed_tool_calls:
                    new_calls = self.state.tool_calls[displayed_tool_calls:]
                    for _, _, tool_name, tool_args in new_calls:
                        await self.add_tool_call(tool_name, tool_args)
                    displayed_tool_calls = len(self.state.tool_calls)

            except TimeoutError:
                continue

    def _build_context_summary(self) -> str:
        """构建对话上下文摘要"""
        if not self.state.messages:
            return "这是对话的开始。"

        # 获取最近的对话
        recent_messages = self.state.messages[-6:]  # 最近3轮对话

        # 构建上下文摘要
        context_parts = []
        context_parts.append(f"对话轮次: {len(self.state.messages) // 2}")

        # 提取最近讨论的主题
        if len(recent_messages) >= 2:
            last_user_msg = recent_messages[-2]["content"] if len(recent_messages) >= 2 else ""
            if last_user_msg:
                context_parts.append(f"上一个问题: {last_user_msg[:50]}...")

        return " | ".join(context_parts)

    async def _process_message(self, user_input: str):
        """处理用户消息（优化版 - 支持流式显示）"""
        try:
            # 构建上下文摘要
            context_summary = self._build_context_summary()

            # 创建任务（增强上下文）
            task = Task(
                task_id=f"chat-{self.state.total_messages}",
                action="chat",
                parameters={
                    "content": user_input,
                    "history": self.state.messages[-10:],
                    "context_summary": context_summary,
                    "conversation_turn": len(self.state.messages) // 2 + 1,
                },
                session_id=self.session_id,
            )

            # 启动事件处理器（后台任务）
            event_processor_task = asyncio.create_task(self.process_events())

            # 开始流式响应
            await self.start_streaming_response()

            # 执行任务（后台）
            agent_task = asyncio.create_task(self.agent.execute_task(task))

            # 等待任务完成
            result = await agent_task

            # 停止事件处理器
            await self.event_queue.put(None)
            await event_processor_task

            # 完成流式响应
            await self.finish_streaming_response()

            # 提取响应内容
            if result.result and isinstance(result.result, dict):
                response = result.result.get("content", "抱歉，我无法回答这个问题。")
            else:
                response = str(result.result) if result.result else "抱歉，我无法回答这个问题。"

            # 添加到对话历史
            self.state.messages.append({"role": "user", "content": user_input})
            self.state.messages.append({"role": "assistant", "content": response})

            # 更新统计
            self._update_stats()

        except Exception as e:
            self.chat_window.write(f"[bold red]❌ 错误: {e}[/bold red]")
            self.chat_window.write("")


# ==================== 主函数 ====================


async def main():
    """主函数"""
    # 1. 创建EventBus
    event_bus = EventBus()

    # 2. 配置LLM
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ 错误: 请设置 OPENAI_API_KEY 环境变量")
        return

    llm_config = LLMConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        temperature=0.7,
    )
    llm = OpenAIProvider(llm_config)
    print("✓ LLM已配置")

    # 3. 配置知识库
    knowledge_base = ConversationalKnowledgeBase()
    print(f"✓ 知识库已配置 ({len(knowledge_base.knowledge_data)} 条知识)")

    # 4. 创建ToolRegistry并注册工具实现
    tool_registry = ToolRegistry()

    # 注册 calculator 工具
    tool_registry.register_function(calculator)

    # 创建 search_knowledge 的闭包，使其能访问 knowledge_base
    async def search_knowledge_impl(query: str) -> str:
        """搜索知识库"""
        try:
            results = await knowledge_base.query(query, limit=3)
            if not results:
                return f"未找到与 '{query}' 相关的知识"

            response = f"找到 {len(results)} 条相关知识：\n\n"
            for i, item in enumerate(results, 1):
                response += f"{i}. {item.content}\n"
                response += f"   来源: {item.source} (相关度: {item.relevance:.2f})\n\n"
            return response
        except Exception as e:
            return f"搜索错误: {str(e)}"

    tool_registry.register_function(search_knowledge_impl, name="search_knowledge")
    print("✓ 工具已注册 (calculator, search_knowledge)")

    # 5. 创建工具定义列表
    tools = [
        create_calculator_tool(),
        create_search_tool(),
    ]

    # 6. 集成Skills（暂时禁用，等待 tool_registry 实现）
    print("✓ Skill集成已跳过（等待 tool_registry 实现）")

    # 7. 创建Agent
    system_prompt = """你是一个友好、专业的AI对话助手。

你的特点：
- 语义连贯，表达清晰自然
- 善于分析复杂问题，提供深入见解
- 能够利用知识库提供准确信息
- 思考过程透明可见
- 可以调用工具和Skills来增强能力
- 可以创建子Agent来处理复杂的子任务

**上下文感知能力：**
- 仔细阅读对话历史，理解之前讨论的主题和上下文
- 当用户使用"它"、"这个"、"那个"、"刚才"等指代词时，根据上下文理解其含义
- 在回答时自然地引用之前的对话内容，保持对话连贯性
- 如果用户的问题与之前的话题相关，明确指出这种关联
- 记住用户的偏好和之前提到的信息

**工具和Skill使用：**
- 当用户需要代码审查时，使用code_review工具
- 当用户需要深度分析时，可以使用deep_analysis skill

**分形Agent能力（使用delegate_task工具）：**
当遇到以下情况时，使用delegate_task工具创建子Agent：
- 任务可以分解为多个独立的子任务（如：设计系统的多个模块）
- 需要深度分析或专业处理（如：代码审查、架构设计、数据分析）
- 任务涉及多个领域的专业知识（如：前端+后端+数据库设计）

使用方式：
delegate_task(
    subtask_description="具体的子任务描述",
    required_capabilities=["需要的能力列表"]
)

示例场景：
- 用户："设计一个完整的用户认证系统"
  → 使用delegate_task分别处理：数据库设计、API设计、前端界面、安全策略
- 用户："分析这段代码的性能问题"
  → 使用delegate_task创建专门的代码分析子Agent

请用自然、流畅的语言回答用户问题，让对话像与真人交流一样自然。"""

    agent = Agent.from_llm(
        llm=llm,
        node_id="conversational-assistant",
        system_prompt=system_prompt,
        tools=tools,
        event_bus=event_bus,
        knowledge_base=knowledge_base,
        knowledge_max_items=3,
        knowledge_relevance_threshold=0.75,
        require_done_tool=False,
        tool_registry=tool_registry,
    )
    print(f"✓ Agent已创建: {agent.node_id}")

    # 9. 创建TUI应用并设置事件处理器
    session_id = str(uuid4())
    tui_app = ConversationalAssistantApp(agent, session_id)

    # 创建事件处理器（用于处理事件并更新state）
    event_processor = EventProcessor(tui_app, session_id)

    # 注册事件处理器：将事件放入队列，由process_events()批量处理
    async def handle_event(task: Task) -> Task:
        # 先让EventProcessor处理事件（更新state）
        await event_processor.on_event(task)
        # 然后放入队列供UI显示
        await tui_app.event_queue.put(task)
        return task

    event_bus.register_handler("*", handle_event)
    print("✓ 事件处理器已配置")

    # 10. 运行TUI应用
    print("\n启动对话助手 TUI...")
    print("=" * 60)
    await tui_app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
