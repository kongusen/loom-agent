"""
Rich Visualization Handler - 基于 Rich 的终端可视化

提供实时、美观的 Agent 执行追踪面板。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Any, Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.tree import Tree
from rich.table import Table
from rich.text import Text
from rich.json import JSON
from rich.syntax import Syntax
from rich.progress import SpinnerColumn, Progress, TextColumn, BarColumn
from rich.layout import Layout

from loom.core.events import AgentEvent, AgentEventType
from loom.interfaces.event_producer import EventProducer


class RichTraceHandler(EventProducer):
    """
    Rich 可视化追踪处理器
    
    实时展示：
    1. Agent 递归调用树
    2. 工具调用详情
    3. 流式输出
    4. 耗时和 Token 统计
    """

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.live: Optional[Live] = None
        self.root_tree: Optional[Tree] = None
        self.current_nodes: Dict[str, Tree] = {}  # agent_name -> Tree Node
        self.agent_depths: Dict[str, int] = {}    # agent_name -> depth
        self.active_agents: set = set()
        
        # 统计面板
        self.stats = {
            "start_time": datetime.now(),
            "llm_calls": 0,
            "tool_calls": 0,
            "errors": 0
        }

    def start(self):
        """开始可视化"""
        self.root_tree = Tree("🤖 [bold blue]Loom Agent Execution[/bold blue]")
        self.live = Live(self._render_layout(), console=self.console, refresh_per_second=10)
        self.live.start()

    def stop(self):
        """停止可视化"""
        if self.live:
            self.live.stop()
            self.live = None
        
        # 打印最终统计
        self._print_summary()

    def _render_layout(self) -> Layout:
        """渲染整体布局"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Header
        duration = datetime.now() - self.stats["start_time"]
        header_text = (
            f" [bold]Loom Studio[/bold] | "
            f"🕒 Duration: {str(duration).split('.')[0]} | "
            f"🤖 Active Agents: {len(self.active_agents)}"
        )
        layout["header"].update(Panel(header_text, style="white on blue"))
        
        # Body (Tree)
        if self.root_tree:
            layout["body"].update(Panel(self.root_tree, title="Execution Trace", border_style="blue"))
        
        # Footer (Stats)
        stats_text = (
            f"🧠 LLM Calls: {self.stats['llm_calls']} | "
            f"🛠️ Tool Calls: {self.stats['tool_calls']} | "
            f"❌ Errors: {self.stats['errors']}"
        )
        layout["footer"].update(Panel(stats_text, style="white on black"))
        
        return layout

    async def emit(self, event: AgentEvent) -> None:
        """处理事件"""
        if not self.live and event.type == AgentEventType.AGENT_START:
            self.start()

        try:
            handler_map = {
                AgentEventType.AGENT_START: self._handle_agent_start,
                AgentEventType.AGENT_END: self._handle_agent_end,
                AgentEventType.AGENT_ERROR: self._handle_agent_error,
                AgentEventType.LLM_START: self._handle_llm_start,
                AgentEventType.LLM_END: self._handle_llm_end,
                AgentEventType.TOOL_START: self._handle_tool_start,
                AgentEventType.TOOL_END: self._handle_tool_end,
                AgentEventType.TOOL_ERROR: self._handle_tool_error,
            }

            handler = handler_map.get(event.type)
            if handler:
                handler(event)
            
            # 刷新界面
            if self.live:
                self.live.update(self._render_layout())
                
        except Exception as e:
            # 避免可视化错误影响主流程
            pass

    def _get_current_node(self, agent_name: str) -> Tree:
        """获取当前 Agent 的树节点，如果不存在则添加到 Root"""
        if not agent_name:
            return self.root_tree
            
        return self.current_nodes.get(agent_name, self.root_tree)

    # ===== Event Handlers =====

    def _handle_agent_start(self, event: AgentEvent):
        name = event.agent_name or "Unknown"
        self.active_agents.add(name)
        
        # 根据 Agent 名字和 Context 推断父子关系有点复杂
        # 这里简化：如果是顶层 Agent，挂载到 Root，否则挂载到上一个 Active Agent（假设单线程）
        # 正确做法应该依靠 event 中的 parent_id，但目前 Event 结构里没有，
        # 我们暂时直接挂在 root 下，或者如果 root 下已经有节点，就在那个节点下创建分支
        
        parent = self.root_tree
        # 简单的层级推断：如果有其他 Active Agent，假设当前 Agent 是其子任务
        # 注意：这在并行执行时可能不准确，需要 TraceID 支持
        # TODO: v0.2.1 Add TraceID to Events
        
        node = parent.add(f"👤 [bold green]Agent: {name}[/bold green]")
        self.current_nodes[name] = node
        
        # 显示输入
        input_data = event.data.get("input", "")
        if input_data:
            node.add(Text(f"Input: {input_data[:200]}...", style="dim"))

    def _handle_agent_end(self, event: AgentEvent):
        name = event.agent_name
        if name in self.active_agents:
            self.active_agents.remove(name)
            
        node = self.current_nodes.get(name)
        if node:
            output = event.data.get("output", "")
            node.add(f"✅ [bold]Output[/bold]: {output[:200]}...")
            
            # 如果是顶层 Agent 结束，可选停止 Live
            if not self.active_agents:
                # self.stop()  # 实际上最好手动控制 stop，或者等待主程序退出
                pass

    def _handle_agent_error(self, event: AgentEvent):
        name = event.agent_name
        self.stats["errors"] += 1
        node = self.current_nodes.get(name, self.root_tree)
        error_msg = event.data.get("error", "Unknown Error")
        node.add(f"❌ [bold red]Error[/bold red]: {error_msg}")

    def _handle_llm_start(self, event: AgentEvent):
        # LLM 调用通常是 Agent 的一部分，不需要单独节点，或者作为叶子
        pass

    def _handle_llm_end(self, event: AgentEvent):
        self.stats["llm_calls"] += 1
        # 可以显示 Token 消耗

    def _handle_tool_start(self, event: AgentEvent):
        name = event.agent_name
        node = self.current_nodes.get(name, self.root_tree)
        
        tool_name = event.data.get("tool_name")
        args = event.data.get("args")
        
        tool_node = node.add(f"🛠️ [bold yellow]Tool: {tool_name}[/bold yellow]")
        tool_node.add(JSON(json.dumps(args, ensure_ascii=False)))
        
        # 临时保存 tool node 以便后面 update 结果（需要 ID 支持，这里简化）
        # v0.2.1: Add ToolCallID to events for matching

    def _handle_tool_end(self, event: AgentEvent):
        self.stats["tool_calls"] += 1
        # 由于我们没有 ID 匹配，这里只能简单地在当前 Agent 节点下追加结果
        # 更好的做法是在 Start 时保存 Node 引用
        name = event.agent_name
        node = self.current_nodes.get(name, self.root_tree)
        
        # 尝试找到最后一个 Tool 节点（不太可靠，但凑合）
        # 实际应该在 ToolStart 把 Node 存起来 map[tool_call_id] = node
        
        result = event.data.get("result", "")
        if len(result) > 500:
            result = result[:500] + "..."
            
        node.add(f"   ↳ 📄 [dim]Result: {result}[/dim]")

    def _handle_tool_error(self, event: AgentEvent):
        self.stats["errors"] += 1
        name = event.agent_name
        node = self.current_nodes.get(name, self.root_tree)
        error = event.data.get("error", "")
        node.add(f"   ↳ 💥 [bold red]Tool Error: {error}[/bold red]")

    def _print_summary(self):
        """打印最终摘要"""
        table = Table(title="Execution Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Duration", str(datetime.now() - self.stats["start_time"]))
        table.add_row("Total LLM Calls", str(self.stats["llm_calls"]))
        table.add_row("Total Tool Calls", str(self.stats["tool_calls"]))
        table.add_row("Errors", str(self.stats["errors"]))
        
        self.console.print(table)
