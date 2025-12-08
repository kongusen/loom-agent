"""
Execution Visualizer: Command-Line Flame Graph for tt Recursion

This module provides CLI-based visualization of loom-agent execution.
Unlike LangGraph's flow charts, we use a timeline/flame graph approach
that better represents recursive depth and temporal progression.

Design Philosophy:
- LangGraph: Spatial visualization (nodes in a graph)
- loom-agent: Temporal visualization (timeline with depth)

Why Flame Graph?
- Naturally represents recursive calls (depth)
- Shows time progression (X-axis)
- Easy to spot bottlenecks
- Familiar to developers (profiling tools)

Example Output:
    Execution Timeline (Thread: user-123)
    ════════════════════════════════════════════════════════════
    Depth 0 │ ████ Context ████ LLM ██████████ Tool: search █████
    Depth 1 │           ████ Context ████ LLM ██████ Tool: analyze
    Depth 2 │                     ████ Context ████ LLM ████ FINISH
    ════════════════════════════════════════════════════════════
            0s        2s        4s        6s        8s       10s

    Legend:
    🟦 Context Assembly  🟪 LLM Call  🟧 Tool Execution  🟩 Complete

Example:
    ```python
    from loom.visualization import ExecutionVisualizer

    # Create visualizer
    viz = ExecutionVisualizer()

    # Visualize from events
    events = await journal.replay(thread_id="user-123")
    viz.visualize_events(events)

    # Or visualize in real-time
    async for event in agent.execute(prompt):
        viz.add_event(event)

    viz.render()
    ```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.tree import Tree
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .events import AgentEvent, AgentEventType


class PhaseType(Enum):
    """Execution phases for visualization."""
    CONTEXT = "context"
    LLM = "llm"
    TOOL = "tool"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ExecutionSegment:
    """
    A segment of execution (one phase).

    Attributes:
        phase: Type of phase
        start_time: Start timestamp
        end_time: End timestamp (None if ongoing)
        depth: Recursion depth
        label: Display label
        metadata: Additional data
    """
    phase: PhaseType
    start_time: float
    end_time: Optional[float]
    depth: int
    label: str
    metadata: Dict[str, Any]

    @property
    def duration(self) -> float:
        """Get duration in seconds."""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time


class ExecutionVisualizer:
    """
    Visualizes agent execution as a flame graph / timeline.

    Features:
    - Timeline view (horizontal bars per depth)
    - Tree view (hierarchical structure)
    - Summary statistics
    - Phase breakdown
    - Real-time updates

    Example:
        ```python
        viz = ExecutionVisualizer()

        # From events
        events = await journal.replay(thread_id="user-123")
        viz.visualize_events(events)

        # Or real-time
        async for event in agent.execute(prompt):
            viz.add_event(event)

        # Render
        viz.render()
        ```
    """

    def __init__(self):
        """Initialize visualizer."""
        if not RICH_AVAILABLE:
            raise ImportError(
                "ExecutionVisualizer requires the 'rich' package. "
                "Install it with: pip install rich"
            )

        self.console = Console()
        self.segments: List[ExecutionSegment] = []
        self.current_segments: Dict[int, ExecutionSegment] = {}  # depth -> segment
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.iterations: Dict[int, Dict[str, Any]] = {}  # depth -> iteration info

    def add_event(self, event: AgentEvent):
        """
        Add an event to the visualization.

        This can be called in real-time during execution.

        Args:
            event: Event to add
        """
        if self.start_time is None:
            self.start_time = event.timestamp

        depth = event.iteration or 0

        # Handle different event types
        if event.type == AgentEventType.ITERATION_START:
            # New iteration
            self.iterations[depth] = {
                "start_time": event.timestamp,
                "events": []
            }

        elif event.type == AgentEventType.CONTEXT_ASSEMBLY_START:
            # Start context phase
            segment = ExecutionSegment(
                phase=PhaseType.CONTEXT,
                start_time=event.timestamp,
                end_time=None,
                depth=depth,
                label="Context",
                metadata=event.metadata
            )
            self.current_segments[depth] = segment

        elif event.type == AgentEventType.CONTEXT_ASSEMBLY_COMPLETE:
            # End context phase
            if depth in self.current_segments:
                segment = self.current_segments[depth]
                segment.end_time = event.timestamp
                self.segments.append(segment)
                del self.current_segments[depth]

        elif event.type == AgentEventType.LLM_START:
            # Start LLM phase
            segment = ExecutionSegment(
                phase=PhaseType.LLM,
                start_time=event.timestamp,
                end_time=None,
                depth=depth,
                label="LLM",
                metadata=event.metadata
            )
            self.current_segments[depth] = segment

        elif event.type == AgentEventType.LLM_COMPLETE:
            # End LLM phase
            if depth in self.current_segments:
                segment = self.current_segments[depth]
                segment.end_time = event.timestamp
                self.segments.append(segment)
                del self.current_segments[depth]

        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            # Start tool phase
            tool_name = event.tool_call.name if event.tool_call else "unknown"
            segment = ExecutionSegment(
                phase=PhaseType.TOOL,
                start_time=event.timestamp,
                end_time=None,
                depth=depth,
                label=f"Tool: {tool_name}",
                metadata={"tool_name": tool_name}
            )
            self.current_segments[depth] = segment

        elif event.type == AgentEventType.TOOL_RESULT:
            # End tool phase
            if depth in self.current_segments:
                segment = self.current_segments[depth]
                segment.end_time = event.timestamp
                self.segments.append(segment)
                del self.current_segments[depth]

        elif event.type == AgentEventType.AGENT_FINISH:
            # Execution complete
            self.end_time = event.timestamp

        elif event.type in (AgentEventType.ERROR, AgentEventType.TOOL_ERROR):
            # Error occurred
            segment = ExecutionSegment(
                phase=PhaseType.ERROR,
                start_time=event.timestamp,
                end_time=event.timestamp,
                depth=depth,
                label=f"Error: {str(event.error)[:30]}",
                metadata={"error": str(event.error)}
            )
            self.segments.append(segment)

    def visualize_events(self, events: List[AgentEvent]):
        """
        Visualize a complete list of events.

        Args:
            events: List of events in chronological order
        """
        for event in events:
            self.add_event(event)

    def render(self, mode: str = "timeline"):
        """
        Render the visualization.

        Args:
            mode: Visualization mode ("timeline", "tree", "summary")
        """
        if mode == "timeline":
            self.render_timeline()
        elif mode == "tree":
            self.render_tree()
        elif mode == "summary":
            self.render_summary()
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'timeline', 'tree', or 'summary'")

    def render_timeline(self):
        """
        Render timeline visualization (flame graph style).

        Shows execution phases across time for each recursion depth.
        """
        if not self.segments:
            self.console.print("[yellow]No execution data to visualize[/yellow]")
            return

        # Calculate total duration
        if self.start_time and self.end_time:
            total_duration = self.end_time - self.start_time
        elif self.start_time:
            total_duration = time.time() - self.start_time
        else:
            total_duration = 0

        # Group segments by depth
        depth_segments: Dict[int, List[ExecutionSegment]] = {}
        max_depth = 0

        for segment in self.segments:
            if segment.depth not in depth_segments:
                depth_segments[segment.depth] = []
            depth_segments[segment.depth].append(segment)
            max_depth = max(max_depth, segment.depth)

        # Render title
        self.console.print()
        self.console.print(Panel(
            f"[bold]Execution Timeline[/bold]\n"
            f"Duration: {total_duration:.2f}s | Max Depth: {max_depth} | Segments: {len(self.segments)}",
            style="cyan"
        ))

        # Render timeline for each depth
        timeline_width = 80
        for depth in range(max_depth + 1):
            segments = depth_segments.get(depth, [])

            # Build timeline string
            timeline = [" "] * timeline_width

            for segment in segments:
                if total_duration == 0:
                    continue

                # Calculate position and width
                start_pos = int((segment.start_time - self.start_time) / total_duration * timeline_width)
                end_pos = int((segment.end_time or time.time() - self.start_time) / total_duration * timeline_width)

                start_pos = max(0, min(start_pos, timeline_width - 1))
                end_pos = max(start_pos + 1, min(end_pos, timeline_width))

                # Color based on phase
                if segment.phase == PhaseType.CONTEXT:
                    char = "█"
                    color = "blue"
                elif segment.phase == PhaseType.LLM:
                    char = "█"
                    color = "magenta"
                elif segment.phase == PhaseType.TOOL:
                    char = "█"
                    color = "yellow"
                elif segment.phase == PhaseType.ERROR:
                    char = "X"
                    color = "red"
                else:
                    char = "█"
                    color = "white"

                # Fill timeline
                for i in range(start_pos, end_pos):
                    timeline[i] = char

            # Render row
            timeline_str = "".join(timeline)
            self.console.print(f"Depth {depth} │ [{color}]{timeline_str}[/{color}]")

        # Render time markers
        time_markers = []
        for i in range(0, timeline_width, 20):
            t = (i / timeline_width) * total_duration
            time_markers.append(f"{t:.1f}s")

        marker_line = "         " + "".join(
            f"{m:>20}" for m in time_markers
        )
        self.console.print(marker_line)

        # Legend
        self.console.print()
        self.console.print("Legend:")
        self.console.print("  [blue]█[/blue] Context Assembly  "
                          "[magenta]█[/magenta] LLM Call  "
                          "[yellow]█[/yellow] Tool Execution  "
                          "[red]X[/red] Error")
        self.console.print()

    def render_tree(self):
        """
        Render tree visualization (hierarchical view).

        Shows execution as a tree structure with recursive calls.
        """
        tree = Tree("[bold cyan]Execution Tree[/bold cyan]")

        # Group segments by depth
        depth_segments: Dict[int, List[ExecutionSegment]] = {}
        for segment in self.segments:
            if segment.depth not in depth_segments:
                depth_segments[segment.depth] = []
            depth_segments[segment.depth].append(segment)

        # Build tree recursively
        def build_subtree(parent_node, depth):
            segments = depth_segments.get(depth, [])

            for segment in segments:
                # Color based on phase
                if segment.phase == PhaseType.CONTEXT:
                    color = "blue"
                    icon = "🔧"
                elif segment.phase == PhaseType.LLM:
                    color = "magenta"
                    icon = "🤖"
                elif segment.phase == PhaseType.TOOL:
                    color = "yellow"
                    icon = "🔨"
                elif segment.phase == PhaseType.ERROR:
                    color = "red"
                    icon = "❌"
                else:
                    color = "white"
                    icon = "•"

                duration_str = f"{segment.duration:.2f}s" if segment.duration > 0 else "..."
                node_label = f"{icon} [{color}]{segment.label}[/{color}] ({duration_str})"

                child_node = parent_node.add(node_label)

                # Check if there are children at next depth
                if depth + 1 in depth_segments:
                    build_subtree(child_node, depth + 1)

        # Start from depth 0
        build_subtree(tree, 0)

        self.console.print()
        self.console.print(tree)
        self.console.print()

    def render_summary(self):
        """
        Render summary statistics.

        Shows aggregated metrics about execution.
        """
        if not self.segments:
            self.console.print("[yellow]No execution data to visualize[/yellow]")
            return

        # Calculate statistics
        total_duration = (self.end_time or time.time()) - self.start_time if self.start_time else 0

        phase_durations: Dict[PhaseType, float] = {
            PhaseType.CONTEXT: 0.0,
            PhaseType.LLM: 0.0,
            PhaseType.TOOL: 0.0,
            PhaseType.ERROR: 0.0
        }

        phase_counts: Dict[PhaseType, int] = {
            PhaseType.CONTEXT: 0,
            PhaseType.LLM: 0,
            PhaseType.TOOL: 0,
            PhaseType.ERROR: 0
        }

        max_depth = 0
        tool_breakdown: Dict[str, int] = {}

        for segment in self.segments:
            phase_durations[segment.phase] += segment.duration
            phase_counts[segment.phase] += 1
            max_depth = max(max_depth, segment.depth)

            if segment.phase == PhaseType.TOOL:
                tool_name = segment.metadata.get("tool_name", "unknown")
                tool_breakdown[tool_name] = tool_breakdown.get(tool_name, 0) + 1

        # Render summary
        self.console.print()
        self.console.print(Panel(
            "[bold]Execution Summary[/bold]",
            style="cyan"
        ))

        # Create table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Duration", f"{total_duration:.2f}s")
        table.add_row("Max Recursion Depth", str(max_depth))
        table.add_row("Total Segments", str(len(self.segments)))
        table.add_row("", "")

        # Phase breakdown
        for phase, count in phase_counts.items():
            if count > 0:
                duration = phase_durations[phase]
                percent = (duration / total_duration * 100) if total_duration > 0 else 0
                table.add_row(
                    f"{phase.value.title()} Phases",
                    f"{count}x ({duration:.2f}s, {percent:.1f}%)"
                )

        self.console.print(table)

        # Tool breakdown
        if tool_breakdown:
            self.console.print()
            self.console.print("[bold]Tool Usage:[/bold]")
            for tool_name, count in sorted(tool_breakdown.items(), key=lambda x: x[1], reverse=True):
                self.console.print(f"  • {tool_name}: {count}x")

        self.console.print()


def visualize_execution_from_events(
    events: List[AgentEvent],
    mode: str = "timeline"
):
    """
    Convenience function to visualize execution from events.

    Args:
        events: List of events
        mode: Visualization mode ("timeline", "tree", "summary")

    Example:
        ```python
        from loom.visualization import visualize_execution_from_events

        events = await journal.replay(thread_id="user-123")
        visualize_execution_from_events(events, mode="timeline")
        ```
    """
    viz = ExecutionVisualizer()
    viz.visualize_events(events)
    viz.render(mode=mode)


def visualize_execution_live(event_stream):
    """
    Visualize execution in real-time from an async event stream.

    Args:
        event_stream: Async iterator of events

    Example:
        ```python
        from loom.visualization import visualize_execution_live

        async def main():
            await visualize_execution_live(agent.execute(prompt))

        asyncio.run(main())
        ```
    """
    viz = ExecutionVisualizer()

    async def process_events():
        async for event in event_stream:
            viz.add_event(event)

            # Optionally render partial updates
            # (could be resource-intensive)

        # Final render
        viz.render(mode="timeline")

    import asyncio
    asyncio.run(process_events())
