"""
CLI Streaming Demo V4 - Interactive TUI with Textual

Features:
- Main chat interface with all interactions
- Scrollable chat window showing thinking, tool calls, and responses
- Side panels for memory layers and stats
- Real-time updates
- Keyboard navigation

Requirements:
  pip install textual

Run:
  OPENAI_API_KEY=... OPENAI_MODEL=gpt-4o-mini python3 examples/cli_stream_demo_v4.py

Keyboard shortcuts:
  - Tab: Switch between panels
  - Arrow keys: Scroll within panel
  - Ctrl+C: Exit
"""

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, RichLog, Static

from loom.agent.core import Agent
from loom.config.llm import LLMConfig
from loom.events import EventBus
from loom.runtime import Task
from loom.providers.llm.openai import OpenAIProvider


@dataclass
class ParadigmStats:
    """Track usage of paradigms"""

    reflection_events: int = 0
    tool_calls: int = 0
    planning_events: int = 0
    collaboration_events: int = 0
    context_queries: int = 0
    tool_creation_events: int = 0
    created_tools: list[str] = field(default_factory=list)


@dataclass
class SessionState:
    """Complete session state for TUI"""

    # Current thinking - accumulated per node
    current_thinking: dict[str, str] = field(default_factory=dict)  # base_task_id -> content
    thinking_order: list[str] = field(default_factory=list)  # base_task_id order

    # Pending sentences to display (for streaming)
    pending_sentences: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (base_task_id, node_id, chunk)

    # Node depth for indentation
    node_depth: dict[str, int] = field(default_factory=dict)
    task_nodes: dict[str, str] = field(default_factory=dict)  # base_task_id -> node_id

    # Tool calls
    tool_calls: list[tuple[str, str, str, dict]] = field(
        default_factory=list
    )  # (base_task_id, node_id, tool, args)

    # Tool results
    tool_results: list[tuple[str, str, str, str]] = field(
        default_factory=list
    )  # (base_task_id, node_id, tool, result)

    # Planning events
    plans: list[tuple[str, str, dict]] = field(
        default_factory=list
    )  # (base_task_id, node_id, plan)

    # Memory layers
    l2_memory: list[str] = field(default_factory=list)
    l3_memory: list[str] = field(default_factory=list)
    l4_memory: list[str] = field(default_factory=list)
    l4_stats: str = ""

    # Fractal tree
    parent_map: dict[str, str | None] = field(default_factory=dict)
    task_names: dict[str, str] = field(default_factory=dict)

    # Stats
    nodes_used: set[str] = field(default_factory=set)
    tasks_seen: set[str] = field(default_factory=set)
    running_nodes: set[str] = field(default_factory=set)
    running_tasks: set[str] = field(default_factory=set)
    max_depth: int = 0
    paradigms: ParadigmStats = field(default_factory=ParadigmStats)

    # Current status
    current_paradigm: str = "Idle"
    is_processing: bool = False


def shorten_id(full_id: str, length: int = 8) -> str:
    """Shorten long IDs for display"""
    if len(full_id) <= length:
        return full_id
    parts = full_id.split("-")
    if len(parts) > 1:
        return parts[-1][:length]
    return full_id[:length]


class EventProcessor:
    """Process events and update session state"""

    def __init__(self, state: SessionState, session_id: str):
        self.state = state
        self.session_id = session_id

    def _base_task_id(self, event_task_id: str) -> str:
        """Extract base task ID"""
        if ":event:" in event_task_id:
            return event_task_id.split(":event:", 1)[0]
        return event_task_id

    def _infer_parent(self, task_id: str) -> str | None:
        """Infer parent task ID"""
        for marker in ("-child-", "-step-"):
            if marker in task_id:
                return task_id.split(marker, 1)[0]
        return None

    def _calculate_depth(self, task_id: str) -> int:
        """Calculate the depth of a task in the hierarchy"""
        depth = 0
        current = task_id
        while current in self.state.parent_map and self.state.parent_map[current] is not None:
            depth += 1
            parent = self.state.parent_map[current]
            assert parent is not None  # Type narrowing for mypy
            current = parent
            if depth > 10:  # Prevent infinite loops
                break
        return depth

    async def process_event(self, event_task: Task) -> None:
        """Process a single event and update state"""
        if event_task.session_id != self.session_id:
            return

        node_id = event_task.parameters.get("node_id", "unknown")
        if node_id:
            self.state.nodes_used.add(node_id)

        base_task_id = self._base_task_id(event_task.task_id)
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

        # Route to specific handlers
        if event_task.action == "node.thinking":
            await self._handle_thinking(event_task, base_task_id, node_id)
        elif event_task.action == "node.tool_call":
            await self._handle_tool_call(event_task, base_task_id, node_id)
        elif event_task.action == "node.tool_result":
            await self._handle_tool_result(event_task, base_task_id, node_id)
        elif event_task.action == "node.planning":
            await self._handle_planning(event_task, base_task_id, node_id)
        elif event_task.action in {"node.start", "node.complete"}:
            await self._handle_lifecycle(event_task, base_task_id)

    async def _handle_thinking(self, event_task: Task, base_task_id: str, node_id: str) -> None:
        """Handle thinking events - accumulate for typewriter effect"""
        content = event_task.parameters.get("content", "")
        if content:
            # Accumulate text for this node
            if base_task_id not in self.state.current_thinking:
                self.state.current_thinking[base_task_id] = ""
                self.state.thinking_order.append(base_task_id)

            self.state.current_thinking[base_task_id] += content

            # Add to pending sentences for typewriter display
            # We'll display in chunks for smooth streaming
            self.state.pending_sentences.append((base_task_id, node_id, content))

            self.state.current_paradigm = "Reflection"
            self.state.paradigms.reflection_events += 1

    async def _handle_tool_call(self, event_task: Task, base_task_id: str, node_id: str) -> None:
        """Handle tool call events"""
        tool_name = event_task.parameters.get("tool_name", "")
        tool_args = event_task.parameters.get("tool_args", {})

        self.state.tool_calls.append((base_task_id, node_id, tool_name, tool_args))

        # Update paradigm stats
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

    async def _handle_tool_result(self, event_task: Task, base_task_id: str, node_id: str) -> None:
        """Handle tool result events"""
        tool_name = event_task.parameters.get("tool_name", "")
        result = event_task.parameters.get("result", "")
        result_str = result if isinstance(result, str) else str(result)

        self.state.tool_results.append((base_task_id, node_id, tool_name, result_str))

    async def _handle_planning(self, event_task: Task, base_task_id: str, node_id: str) -> None:
        """Handle planning events"""
        plan = {
            "goal": event_task.parameters.get("goal", ""),
            "steps": event_task.parameters.get("steps", []),
            "reasoning": event_task.parameters.get("reasoning", ""),
            "step_count": event_task.parameters.get("step_count", 0),
        }
        self.state.plans.append((base_task_id, node_id, plan))
        self.state.current_paradigm = "Planning"

    async def _handle_lifecycle(self, event_task: Task, base_task_id: str) -> None:
        """Handle lifecycle events"""
        if event_task.action == "node.start":
            self.state.running_tasks.add(base_task_id)
        else:
            self.state.running_tasks.discard(base_task_id)


async def query_memory_layers(agent: Agent, state: SessionState) -> None:
    """Query memory layers and update state"""
    try:
        # L1: Recent events (all tasks)
        l1_tasks = agent.memory.get_l1_tasks(limit=10)

        # DEBUG: Print L1 info
        if not l1_tasks:
            state.l2_memory = ["[DEBUG] L1 is empty - no events received"]
            state.l3_memory = []
            state.l4_memory = []
            return

        # Filter for interesting events (thinking, tool calls, etc.)
        interesting_tasks = [
            t
            for t in l1_tasks
            if t.action
            in (
                "node.thinking",
                "node.tool_call",
                "node.tool_result",
                "node.planning",
                "execute",
                "node.complete",
            )
        ]

        if not interesting_tasks:
            state.l2_memory = [f"[DEBUG] L1 has {len(l1_tasks)} tasks but none are interesting"]
            state.l3_memory = []
            state.l4_memory = []
            return

        def summarize_task(task: Task) -> str:
            if task.action == "node.tool_call":
                return f"{task.parameters.get('tool_name', '')}"
            if task.action == "node.tool_result":
                tool_name = task.parameters.get("tool_name", "")
                result = task.parameters.get("result", "")
                result_str = result if isinstance(result, str) else str(result)
                return f"{tool_name}: {result_str[:60]}"
            if task.action == "node.planning":
                goal = task.parameters.get("goal", "")
                return f"plan: {goal[:60]}"
            return str(task.parameters.get("content", task.parameters.get("tool_name", "")))[:60]

        state.l2_memory = [
            f"[{task.action}] {summarize_task(task)}" for task in interesting_tasks[-5:]
        ]

        # L2: Important tasks (importance > 0.6)
        l2_tasks = agent.memory.get_l2_tasks(limit=5)
        state.l3_memory = [
            f"[{task.task_id[:8]}] {task.parameters.get('content', str(task.action))[:60]}"
            for task in l2_tasks
        ]

        # L3: Summaries (if any)
        l3_summaries = agent.memory.get_l3_summaries(limit=5)
        state.l4_memory = [
            f"[{summary.task_id[:8]}] {summary.action}: {summary.param_summary[:60]}"
            for summary in l3_summaries
        ]

        stats = agent.memory.get_stats()
        l4_size = stats.get("l4_size", 0)
        l4_enabled = bool(
            getattr(agent.memory, "enable_l4_vectorization", False)
            and getattr(agent.memory, "embedding_provider", None)
            and getattr(agent.memory, "_l4_vector_store", None)
        )
        if l4_enabled:
            state.l4_stats = f"vectors: {l4_size}"
        else:
            state.l4_stats = "disabled"
    except Exception as e:
        # Show error in memory panel
        state.l2_memory = [f"[ERROR] {type(e).__name__}: {str(e)[:80]}"]
        state.l3_memory = []
        state.l4_memory = []
        state.l4_stats = ""


class StatusPanel(Static):
    """Status panel showing current stats"""

    def __init__(self, state: SessionState):
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("", id="status_content")

    def update_display(self) -> None:
        """Update status display"""
        content = (
            f"[cyan]Nodes:[/cyan] {len(self.state.nodes_used)} | "
            f"[green]Tasks:[/green] {len(self.state.tasks_seen)} | "
            f"[yellow]Depth:[/yellow] {self.state.max_depth} | "
            f"[magenta]Paradigm:[/magenta] {self.state.current_paradigm}"
        )
        status_widget = self.query_one("#status_content", Static)
        status_widget.update(content)


class MemoryPanel(Static):
    """Memory layers panel"""

    def __init__(self, state: SessionState):
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("", id="memory_content")

    def update_display(self) -> None:
        """Update memory display"""
        lines = ["[bold magenta]Memory Layers[/bold magenta]\n"]

        # L1 (stored in l2_memory variable)
        lines.append("[bold]L1 (Recent Events):[/bold]")
        if self.state.l2_memory:
            for item in self.state.l2_memory[-3:]:
                lines.append(f"  • {item}")
        else:
            lines.append("  (empty)")
        lines.append("")

        # L2 (stored in l3_memory variable)
        lines.append("[bold]L2 (Important Tasks):[/bold]")
        if self.state.l3_memory:
            for item in self.state.l3_memory[-3:]:
                lines.append(f"  • {item}")
        else:
            lines.append("  (empty)")
        lines.append("")

        # L3 (stored in l4_memory variable)
        lines.append("[bold]L3 (Summaries):[/bold]")
        if self.state.l4_memory:
            for item in self.state.l4_memory[-3:]:
                lines.append(f"  • {item}")
        else:
            lines.append("  (empty)")

        lines.append("")

        # L4 (vector store stats)
        lines.append("[bold]L4 (Vector Memory):[/bold]")
        if self.state.l4_stats:
            lines.append(f"  • {self.state.l4_stats}")
        else:
            lines.append("  (empty)")

        content = "\n".join(lines)
        memory_widget = self.query_one("#memory_content", Static)
        memory_widget.update(content)


class FractalTreePanel(Static):
    """Fractal tree panel showing task hierarchy"""

    def __init__(self, state: SessionState):
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        yield Static("", id="tree_content")

    def update_display(self) -> None:
        """Update tree display"""
        lines = ["[bold green]Fractal Tree[/bold green]\n"]

        if not self.state.parent_map:
            lines.append("(no tasks yet)")
        else:
            # Build tree structure
            children: dict[str | None, list[str]] = {}
            for task_id, parent in self.state.parent_map.items():
                children.setdefault(parent, []).append(task_id)

            def format_tree(task_id: str, indent: int = 0) -> None:
                short_id = shorten_id(task_id)
                display_name = self.state.task_names.get(task_id, short_id)
                lines.append("  " * indent + f"└─ {display_name}")
                for child in children.get(task_id, []):
                    format_tree(child, indent + 1)

            # Add root tasks
            roots = children.get(None, [])
            for root in roots:
                format_tree(root)

        content = "\n".join(lines)
        tree_widget = self.query_one("#tree_content", Static)
        tree_widget.update(content)


class LoomAgentApp(App):
    """Main Textual app for Loom Agent"""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #main_container {
        width: 70%;
        height: 100%;
    }

    #sidebar {
        width: 30%;
        height: 100%;
        border-left: solid $primary;
    }

    #chat_log {
        height: 1fr;
        border: solid $primary;
        padding: 1;
    }

    #input_box {
        height: 3;
        dock: bottom;
    }

    StatusPanel {
        height: auto;
        padding: 1;
        border: solid $accent;
        margin-bottom: 1;
    }

    MemoryPanel {
        height: 1fr;
        padding: 1;
        border: solid $accent;
        overflow-y: auto;
    }

    FractalTreePanel {
        height: 1fr;
        padding: 1;
        border: solid $accent;
        overflow-y: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, agent: Agent, session_id: str):
        super().__init__()
        self.agent = agent
        self.session_id = session_id
        self.state = SessionState()
        self.processor = EventProcessor(self.state, session_id)
        self.event_queue: asyncio.Queue = asyncio.Queue()

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header()

        with Horizontal():
            # Main chat area (left)
            with Vertical(id="main_container"):
                yield RichLog(id="chat_log", highlight=True, markup=True)
                yield Input(placeholder="Type your message...", id="input_box")

            # Sidebar (right)
            with Vertical(id="sidebar"):
                yield StatusPanel(self.state)
                yield MemoryPanel(self.state)
                yield FractalTreePanel(self.state)

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts"""

        # Register event handlers ONCE at startup
        async def handle_event(event_task: Task) -> Task:
            await self.event_queue.put(event_task)
            return event_task

        for action in (
            "node.thinking",
            "node.tool_call",
            "node.tool_result",
            "node.planning",
            "node.start",
            "node.complete",
        ):
            if self.agent.event_bus:  # Type guard for mypy
                self.agent.event_bus.register_handler(action, handle_event)

        chat_log = self.query_one("#chat_log", RichLog)
        chat_log.write("[bold cyan]🚀 Loom Agent - Interactive TUI[/bold cyan]")
        chat_log.write("[dim]Type your message and press Enter. Ctrl+C to quit.[/dim]\n")

        # Focus input box
        self.query_one("#input_box", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user input submission"""
        user_input = event.value.strip()
        if not user_input:
            return

        # Clear input
        event.input.value = ""

        # Display user message in chat
        chat_log = self.query_one("#chat_log", RichLog)
        chat_log.write(f"[bold green]You>[/bold green] {user_input}\n")

        # Mark as processing
        self.state.is_processing = True

        # Process in background
        asyncio.create_task(self.process_agent_task(user_input))

    async def process_agent_task(self, user_input: str) -> None:
        """Process agent task and update chat in real-time"""
        chat_log = self.query_one("#chat_log", RichLog)

        # Create task
        task = Task(
            task_id=f"chat-{uuid4()}",
            action="execute",
            parameters={"content": user_input},
            session_id=self.session_id,
        )

        # Start event processor
        event_processor_task = asyncio.create_task(self.process_events(chat_log))

        # Execute agent as background task
        agent_task = asyncio.create_task(self.agent.execute_task(task))

        # Periodically update sidebar while agent is running
        result = None
        try:
            while not agent_task.done():
                await query_memory_layers(self.agent, self.state)
                self.update_sidebar()
                await asyncio.sleep(0.25)

            # Get result but don't display yet
            result = await agent_task

        except Exception as e:
            chat_log.write(f"[bold red]Error:[/bold red] {str(e)}\n")

        finally:
            # Stop event processor and wait for all events to be displayed
            await self.event_queue.put(None)
            await event_processor_task

            # NOW display final result after all thinking is shown
            if result and result.result:
                content = (
                    result.result.get("content", "")
                    if isinstance(result.result, dict)
                    else str(result.result)
                )
                if content:
                    chat_log.write(f"\n[bold blue]Assistant>[/bold blue] {content}\n")

            # Final update
            await query_memory_layers(self.agent, self.state)
            self.update_sidebar()

            self.state.is_processing = False

    async def process_events(self, chat_log: RichLog) -> None:
        """Process events and display with typewriter effect"""
        displayed_chunks = 0
        displayed_tool_calls = 0
        displayed_tool_results = 0
        displayed_plans = 0
        current_node_buffer: dict[str, str] = {}  # base_task_id -> accumulated chunks
        last_display_time = 0.0

        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                if event is None:  # Stop signal
                    break

                # Process event
                await self.processor.process_event(event)

                # Display thinking chunks with typewriter effect
                import time

                current_time = time.time()

                # Process new chunks
                if len(self.state.pending_sentences) > displayed_chunks:
                    new_chunks = self.state.pending_sentences[displayed_chunks:]
                    for base_task_id, _, chunk in new_chunks:
                        # Accumulate chunks for this node
                        if base_task_id not in current_node_buffer:
                            current_node_buffer[base_task_id] = ""
                        current_node_buffer[base_task_id] += chunk
                    displayed_chunks = len(self.state.pending_sentences)

                # Display accumulated content periodically (every 0.3 seconds)
                if current_time - last_display_time > 0.3 and current_node_buffer:
                    for base_task_id, content in list(current_node_buffer.items()):
                        if content:
                            if base_task_id not in self.state.node_depth:
                                self.state.node_depth[base_task_id] = (
                                    self.processor._calculate_depth(base_task_id)
                                )

                            depth = self.state.node_depth.get(base_task_id, 0)
                            indent = "  ↳ " * depth if depth > 0 else ""
                            node_id = self.state.task_nodes.get(base_task_id, base_task_id)
                            short_id = shorten_id(node_id)

                            chat_log.write(
                                f"{indent}[dim cyan]💭 [{short_id}][/dim cyan] [dim]{content}[/dim]"
                            )
                            current_node_buffer[base_task_id] = ""  # Clear buffer after display

                    last_display_time = current_time

                # Display new tool calls with hierarchy
                if len(self.state.tool_calls) > displayed_tool_calls:
                    new_tool_calls = self.state.tool_calls[displayed_tool_calls:]
                    for base_task_id, node_id, tool_name, tool_args in new_tool_calls:
                        if tool_name == "done":
                            continue

                        depth = self.state.node_depth.get(base_task_id, 0)
                        indent = "  ↳ " * depth if depth > 0 else ""
                        short_id = shorten_id(node_id)

                        if tool_name == "create_plan":
                            goal = tool_args.get("goal", "")[:50]
                            chat_log.write(
                                f"{indent}[yellow]🔧 [{short_id}] 创建计划:[/yellow] {goal}..."
                            )
                        elif tool_name.startswith("query_"):
                            chat_log.write(f"{indent}[yellow]🔧 [{short_id}] 查询记忆[/yellow]")
                        else:
                            args_str = ", ".join(f"{k}={v}" for k, v in list(tool_args.items())[:2])
                            chat_log.write(
                                f"{indent}[yellow]🔧 [{short_id}] {tool_name}:[/yellow] {args_str}"
                            )

                        displayed_tool_calls += 1

                # Display new planning events
                if len(self.state.plans) > displayed_plans:
                    new_plans = self.state.plans[displayed_plans:]
                    for base_task_id, node_id, plan in new_plans:
                        depth = self.state.node_depth.get(base_task_id, 0)
                        indent = "  ↳ " * depth if depth > 0 else ""
                        short_id = shorten_id(node_id)

                        for line in self._format_plan_lines(plan, indent, short_id):
                            chat_log.write(line)
                    displayed_plans = len(self.state.plans)

                # Display new tool results
                if len(self.state.tool_results) > displayed_tool_results:
                    new_tool_results = self.state.tool_results[displayed_tool_results:]
                    for base_task_id, node_id, tool_name, result in new_tool_results:
                        if tool_name == "done":
                            continue

                        depth = self.state.node_depth.get(base_task_id, 0)
                        indent = "  ↳ " * depth if depth > 0 else ""
                        short_id = shorten_id(node_id)

                        for line in self._format_tool_result_lines(
                            tool_name, result, indent, short_id
                        ):
                            chat_log.write(line)
                    displayed_tool_results = len(self.state.tool_results)

            except TimeoutError:
                continue

        # Display any remaining incomplete thinking at the end
        for base_task_id in self.state.thinking_order:
            if base_task_id in self.state.current_thinking:
                remaining = self.state.current_thinking[base_task_id]
                if remaining:
                    depth = self.state.node_depth.get(base_task_id, 0)
                    indent = "  ↳ " * depth if depth > 0 else ""
                    node_ref = self.state.task_nodes.get(base_task_id, base_task_id)
                    short_id = shorten_id(node_ref)
                    chat_log.write(
                        f"{indent}[dim cyan]💭 [{short_id}][/dim cyan] [dim]{remaining}[/dim]"
                    )

    def _truncate(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _format_plan_lines(self, plan: dict[str, Any], indent: str, short_id: str) -> list[str]:
        goal = plan.get("goal") or "未命名目标"
        steps = plan.get("steps", []) or []
        step_count = plan.get("step_count") or len(steps)
        reasoning = plan.get("reasoning", "")

        lines = [
            f"{indent}[bold yellow]🧭 [{short_id}] 计划[/bold yellow] {self._truncate(str(goal), 80)} "
            f"({step_count} 步)"
        ]

        if reasoning:
            lines.append(f"{indent}[dim]理由:[/dim] {self._truncate(str(reasoning), 140)}")

        for idx, step in enumerate(steps, 1):
            step_text = self._truncate(str(step), 140)
            lines.append(f"{indent}  [yellow]{idx}.[/yellow] {step_text}")

        return lines

    def _format_tool_result_lines(
        self,
        tool_name: str,
        result: str,
        indent: str,
        short_id: str,
    ) -> list[str]:
        result_text = result if isinstance(result, str) else str(result)
        lowered = result_text.strip().lower()
        is_error = lowered.startswith("error") or "错误" in result_text or "失败" in result_text
        color = "red" if is_error else "green"

        # Plan execution summary
        if tool_name == "create_plan":
            return self._format_plan_result_lines(result_text, indent, short_id, color)

        # Memory queries
        if tool_name.startswith("query_"):
            return self._format_query_result_lines(tool_name, result_text, indent, short_id, color)

        # Generic tool result
        summary = self._truncate(result_text.replace("\n", " "), 160)
        return [f"{indent}[{color}]✅ [{short_id}] 结果 {tool_name}:[/{color}] {summary}"]

    def _format_plan_result_lines(
        self,
        result_text: str,
        indent: str,
        short_id: str,
        color: str,
    ) -> list[str]:
        lines = result_text.splitlines()
        if not lines:
            return [f"{indent}[{color}]✅ [{short_id}] 计划结果:[/{color}] (empty)"]

        header = self._truncate(lines[0], 140)
        out = [f"{indent}[{color}]✅ [{short_id}] {header}[/{color}]"]

        for line in lines[1:]:
            if not line.strip():
                continue
            step_text = self._truncate(line.strip(), 160)
            out.append(f"{indent}  [dim]{step_text}[/dim]")
        return out

    def _format_query_result_lines(
        self,
        tool_name: str,
        result_text: str,
        indent: str,
        short_id: str,
        color: str,
    ) -> list[str]:
        import json

        try:
            data = json.loads(result_text)
        except Exception:
            summary = self._truncate(result_text.replace("\n", " "), 140)
            return [f"{indent}[{color}]📥 [{short_id}] {tool_name}:[/{color}] {summary}"]

        count = data.get("count")
        desc = data.get("description", "")
        header = f"{tool_name} ({count})"
        if desc:
            header = f"{header} - {desc}"
        out = [f"{indent}[{color}]📥 [{short_id}] {self._truncate(header, 140)}[/{color}]"]

        # Optional preview
        preview = None
        if "tasks" in data and data["tasks"]:
            preview = data["tasks"][0]
        elif "statements" in data and data["statements"]:
            preview = data["statements"][0]
        elif "events" in data and data["events"]:
            preview = data["events"][0]

        if isinstance(preview, dict):
            preview_text = self._truncate(str(preview), 160)
            out.append(f"{indent}  [dim]{preview_text}[/dim]")
        return out

    def update_sidebar(self) -> None:
        """Update sidebar panels"""
        try:
            status_panel = self.query_one(StatusPanel)
            status_panel.update_display()

            memory_panel = self.query_one(MemoryPanel)
            memory_panel.update_display()

            fractal_tree = self.query_one(FractalTreePanel)
            fractal_tree.update_display()
        except Exception:
            pass


async def main() -> None:
    """Main entry point"""
    # Setup LLM provider
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Missing OPENAI_API_KEY in environment.")
        return

    config = LLMConfig(
        provider="openai",
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0.7,
    )
    llm_provider = OpenAIProvider(config)

    # Setup event bus
    event_bus = EventBus()

    # Create agent using Agent.create() (recommended pattern)
    agent = Agent.create(
        llm_provider,  # First positional argument
        node_id="cli-agent",
        system_prompt=(
            "You are a helpful assistant. "
            "When the user sends a message, think about your response and then call the 'done' tool. "
            "IMPORTANT: The 'content' parameter of the done tool must contain your ACTUAL response to the user, "
            "not a description of what you did. "
            "For example, if user says '你好', call done(content='你好！很高兴见到你！有什么我可以帮助你的吗？'), "
            "NOT done(content='User greeted warmly.')."
        ),
        event_bus=event_bus,
        max_iterations=10,
        require_done_tool=True,
        memory_config={
            "max_l1_size": 40,
            "max_l2_size": 12,
            "max_l3_size": 24,
        },
    )

    # Enable L4 vector memory (uses OpenAI embeddings + in-memory vector store)
    enable_l4 = os.getenv("ENABLE_L4", "1").lower() not in ("0", "false", "no")
    if enable_l4:
        from loom.memory import InMemoryVectorStore
        from loom.providers.embedding.openai import OpenAIEmbeddingProvider

        embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        agent.memory.embedding_provider = OpenAIEmbeddingProvider(  # type: ignore[assignment]
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL"),
            model=embedding_model,
        )
        agent.memory._l4_vector_store = InMemoryVectorStore()

    # Create and run app
    session_id = f"cli-session-{uuid4()}"
    app = LoomAgentApp(agent, session_id)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
