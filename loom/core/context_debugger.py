"""
Context Debugger: Make Context Management Transparent

This module provides debugging and introspection tools for loom-agent's
intelligent context management system.

Problem Statement:
    Users常问："为什么 LLM 忘记了我刚才读的文件？"
    "为什么 RAG 文档没生效？"
    "Token 超限了，哪些内容被丢弃了？"

Solution:
    ContextDebugger 让这些决策变得透明和可追溯。

This is loom-agent's UNIQUE ADVANTAGE over LangGraph:
    - LangGraph: State is just a dict, no visibility into why things change
    - loom-agent: Context Fabric with explainable priority-based assembly

Example:
    ```python
    debugger = ContextDebugger()

    # Attach to agent
    agent = agent(
        llm=llm,
        tools=tools,
        context_debugger=debugger
    )

    # After execution
    print(debugger.explain_iteration(5))
    # Output:
    # 📊 Context Assembly Report (Iteration 5)
    # Token Budget: 7500/8000 (93.8%)
    #
    # ✅ Included Components:
    #   - system_instructions (500 tokens, priority=100, critical)
    #   - rag_docs (2000 tokens, priority=90, truncated=True)
    #   - tool_definitions (3000 tokens, priority=70)
    #
    # ❌ Excluded Components:
    #   - file_content.py (2500 tokens, priority=70)
    #     Reason: Token limit exceeded, lower priority than RAG docs
    ```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

from .execution_frame import ExecutionFrame


@dataclass
class ComponentDecision:
    """
    Records a decision made during context assembly.

    Attributes:
        component_name: Name of the context component
        priority: Priority level (0-100)
        token_count: Number of tokens
        action: What happened (included, truncated, excluded)
        reason: Why this decision was made
        truncated_from: Original token count if truncated
    """
    component_name: str
    priority: int
    token_count: int
    action: str  # "included", "truncated", "excluded"
    reason: str
    truncated_from: Optional[int] = None


@dataclass
class ContextAssemblyLog:
    """
    Complete log of one context assembly operation.

    Attributes:
        iteration: Iteration number
        frame_id: Frame ID
        timestamp: When assembly occurred
        token_budget: Maximum tokens allowed
        tokens_used: Actual tokens used
        decisions: List of component decisions
        compression_applied: Whether compression was triggered
        metadata: Additional assembly metadata
    """
    iteration: int
    frame_id: str
    timestamp: float
    token_budget: int
    tokens_used: int
    decisions: List[ComponentDecision] = field(default_factory=list)
    compression_applied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def token_usage_percent(self) -> float:
        """Calculate token usage percentage."""
        if self.token_budget == 0:
            return 0.0
        return (self.tokens_used / self.token_budget) * 100

    @property
    def included_components(self) -> List[ComponentDecision]:
        """Get components that were included."""
        return [d for d in self.decisions if d.action in ("included", "truncated")]

    @property
    def excluded_components(self) -> List[ComponentDecision]:
        """Get components that were excluded."""
        return [d for d in self.decisions if d.action == "excluded"]


class ContextDebugger:
    """
    Debugger for context assembly decisions.

    This class records and explains context assembly decisions,
    making the "why" behind context management transparent.

    Features:
    - Record every context assembly decision
    - Explain why components were included/excluded
    - Track component across iterations
    - Export debug reports
    - Generate visualizations

    Example:
        ```python
        debugger = ContextDebugger()

        # During execution, record decisions
        debugger.record_assembly(
            iteration=5,
            frame_id="abc123",
            token_budget=8000,
            tokens_used=7500,
            decisions=[
                ComponentDecision(
                    component_name="system_instructions",
                    priority=100,
                    token_count=500,
                    action="included",
                    reason="Critical component, always included"
                ),
                ComponentDecision(
                    component_name="file_content.py",
                    priority=70,
                    token_count=2500,
                    action="excluded",
                    reason="Token limit exceeded"
                )
            ]
        )

        # Later, explain what happened
        print(debugger.explain_iteration(5))
        ```
    """

    def __init__(self, enable_auto_export: bool = False, export_path: Optional[Path] = None):
        """
        Initialize context debugger.

        Args:
            enable_auto_export: Auto-export logs to file after each assembly
            export_path: Path to export logs (default: ./context_debug.jsonl)
        """
        self.logs: List[ContextAssemblyLog] = []
        self.enable_auto_export = enable_auto_export
        self.export_path = export_path or Path("./context_debug.jsonl")

    def record_assembly(
        self,
        iteration: int,
        frame_id: str,
        token_budget: int,
        tokens_used: int,
        decisions: List[ComponentDecision],
        compression_applied: bool = False,
        timestamp: Optional[float] = None,
        **metadata
    ):
        """
        Record a context assembly operation.

        Args:
            iteration: Iteration number
            frame_id: Frame ID
            token_budget: Maximum tokens allowed
            tokens_used: Actual tokens used
            decisions: List of component decisions
            compression_applied: Whether compression was applied
            timestamp: Timestamp (defaults to now)
            **metadata: Additional metadata
        """
        import time

        log = ContextAssemblyLog(
            iteration=iteration,
            frame_id=frame_id,
            timestamp=timestamp or time.time(),
            token_budget=token_budget,
            tokens_used=tokens_used,
            decisions=decisions,
            compression_applied=compression_applied,
            metadata=metadata
        )

        self.logs.append(log)

        # Auto-export if enabled
        if self.enable_auto_export:
            self._export_log(log)

    def record_from_frame(self, frame: ExecutionFrame):
        """
        Record context assembly from an ExecutionFrame.

        This is a convenience method that extracts context_metadata
        from a frame and records it.

        Args:
            frame: ExecutionFrame with context_metadata
        """
        metadata = frame.context_metadata

        if not metadata:
            return  # No context metadata available

        # Extract decisions from metadata
        decisions = []

        # Included components
        for comp in metadata.get("components_included", []):
            decisions.append(ComponentDecision(
                component_name=comp["name"],
                priority=comp.get("priority", 50),
                token_count=comp.get("token_count", 0),
                action="truncated" if comp.get("truncated", False) else "included",
                reason=comp.get("reason", "Included by priority"),
                truncated_from=comp.get("original_tokens") if comp.get("truncated") else None
            ))

        # Excluded components
        for comp in metadata.get("components_excluded", []):
            decisions.append(ComponentDecision(
                component_name=comp["name"],
                priority=comp.get("priority", 50),
                token_count=comp.get("token_count", 0),
                action="excluded",
                reason=comp.get("reason", "Excluded due to priority or token limit")
            ))

        self.record_assembly(
            iteration=frame.depth,
            frame_id=frame.frame_id,
            token_budget=metadata.get("token_budget", 0),
            tokens_used=metadata.get("tokens_used", 0),
            decisions=decisions,
            compression_applied=metadata.get("compression_applied", False),
            **{k: v for k, v in metadata.items() if k not in (
                "components_included", "components_excluded",
                "token_budget", "tokens_used", "compression_applied"
            )}
        )

    # ===== Query Methods =====

    def get_log(self, iteration: int) -> Optional[ContextAssemblyLog]:
        """
        Get log for a specific iteration.

        Args:
            iteration: Iteration number

        Returns:
            ContextAssemblyLog or None if not found
        """
        for log in self.logs:
            if log.iteration == iteration:
                return log
        return None

    def get_logs_for_frame(self, frame_id: str) -> List[ContextAssemblyLog]:
        """Get all logs for a specific frame."""
        return [log for log in self.logs if log.frame_id == frame_id]

    def track_component(self, component_name: str) -> List[Dict[str, Any]]:
        """
        Track a component across all iterations.

        Args:
            component_name: Component to track

        Returns:
            List of dicts with iteration, action, reason for each occurrence

        Example:
            ```python
            timeline = debugger.track_component("file_content.py")
            # [
            #     {"iteration": 0, "action": "included", "tokens": 2500},
            #     {"iteration": 3, "action": "truncated", "tokens": 1000},
            #     {"iteration": 5, "action": "excluded", "reason": "Token limit"}
            # ]
            ```
        """
        timeline = []

        for log in self.logs:
            for decision in log.decisions:
                if decision.component_name == component_name:
                    timeline.append({
                        "iteration": log.iteration,
                        "action": decision.action,
                        "tokens": decision.token_count,
                        "priority": decision.priority,
                        "reason": decision.reason,
                        "truncated_from": decision.truncated_from
                    })

        return timeline

    # ===== Explanation Methods =====

    def explain_iteration(self, iteration: int) -> str:
        """
        Generate human-readable explanation of context assembly for an iteration.

        Args:
            iteration: Iteration number

        Returns:
            Formatted string report

        Example output:
            📊 Context Assembly Report (Iteration 5)
            Token Budget: 7500/8000 (93.8%)

            ✅ Included Components:
              - system_instructions (500 tokens, priority=100, critical)
              - rag_docs (2000 tokens, priority=90, truncated from 3000)
              - tool_definitions (3000 tokens, priority=70)

            ❌ Excluded Components:
              - file_content.py (2500 tokens, priority=70)
                Reason: Token limit exceeded, lower priority than RAG docs
        """
        log = self.get_log(iteration)

        if not log:
            return f"No context assembly log found for iteration {iteration}"

        lines = [
            f"📊 Context Assembly Report (Iteration {iteration})",
            f"Frame ID: {log.frame_id[:12]}...",
            f"Token Budget: {log.tokens_used}/{log.token_budget} ({log.token_usage_percent:.1f}%)",
        ]

        if log.compression_applied:
            lines.append("⚠️  Context compression was applied")

        lines.append("")

        # Included components
        included = log.included_components
        if included:
            lines.append("✅ Included Components:")
            for decision in sorted(included, key=lambda d: d.priority, reverse=True):
                truncated_note = ""
                if decision.action == "truncated" and decision.truncated_from:
                    truncated_note = f", truncated from {decision.truncated_from}"

                lines.append(
                    f"  - {decision.component_name} "
                    f"({decision.token_count} tokens, "
                    f"priority={decision.priority}{truncated_note})"
                )

        # Excluded components
        excluded = log.excluded_components
        if excluded:
            lines.append("")
            lines.append("❌ Excluded Components:")
            for decision in excluded:
                lines.append(
                    f"  - {decision.component_name} "
                    f"({decision.token_count} tokens, priority={decision.priority})"
                )
                lines.append(f"    Reason: {decision.reason}")

        return "\n".join(lines)

    def explain_component(self, component_name: str) -> str:
        """
        Explain what happened to a specific component across all iterations.

        Args:
            component_name: Component to explain

        Returns:
            Formatted string report
        """
        timeline = self.track_component(component_name)

        if not timeline:
            return f"Component '{component_name}' was never used"

        lines = [
            f"📦 Component Timeline: {component_name}",
            f"Total occurrences: {len(timeline)}",
            ""
        ]

        for entry in timeline:
            action_emoji = {
                "included": "✅",
                "truncated": "✂️ ",
                "excluded": "❌"
            }.get(entry["action"], "❓")

            truncated_note = ""
            if entry.get("truncated_from"):
                truncated_note = f" (from {entry['truncated_from']} tokens)"

            lines.append(
                f"{action_emoji} Iteration {entry['iteration']}: "
                f"{entry['action'].upper()} - "
                f"{entry['tokens']} tokens, priority={entry['priority']}{truncated_note}"
            )

            if entry.get("reason"):
                lines.append(f"   {entry['reason']}")

        return "\n".join(lines)

    def why_excluded(self, component_name: str, iteration: int) -> str:
        """
        Explain why a component was excluded in a specific iteration.

        Args:
            component_name: Component name
            iteration: Iteration number

        Returns:
            Explanation string
        """
        log = self.get_log(iteration)

        if not log:
            return f"No log found for iteration {iteration}"

        for decision in log.decisions:
            if decision.component_name == component_name:
                if decision.action == "excluded":
                    return (
                        f"'{component_name}' was excluded in iteration {iteration}:\n"
                        f"  Priority: {decision.priority}\n"
                        f"  Token count: {decision.token_count}\n"
                        f"  Reason: {decision.reason}"
                    )
                else:
                    return f"'{component_name}' was NOT excluded (action: {decision.action})"

        return f"'{component_name}' was not found in iteration {iteration}"

    # ===== Export Methods =====

    def _export_log(self, log: ContextAssemblyLog):
        """Export a single log to file (JSON Lines format)."""
        with self.export_path.open("a") as f:
            log_data = {
                "iteration": log.iteration,
                "frame_id": log.frame_id,
                "timestamp": log.timestamp,
                "token_budget": log.token_budget,
                "tokens_used": log.tokens_used,
                "token_usage_percent": log.token_usage_percent,
                "compression_applied": log.compression_applied,
                "decisions": [
                    {
                        "component": d.component_name,
                        "priority": d.priority,
                        "tokens": d.token_count,
                        "action": d.action,
                        "reason": d.reason,
                        "truncated_from": d.truncated_from
                    }
                    for d in log.decisions
                ],
                "metadata": log.metadata
            }
            f.write(json.dumps(log_data) + "\n")

    def export_all(self, path: Optional[Path] = None):
        """
        Export all logs to file.

        Args:
            path: Export path (defaults to self.export_path)
        """
        export_path = path or self.export_path

        with export_path.open("w") as f:
            for log in self.logs:
                log_data = {
                    "iteration": log.iteration,
                    "frame_id": log.frame_id,
                    "timestamp": log.timestamp,
                    "token_budget": log.token_budget,
                    "tokens_used": log.tokens_used,
                    "decisions": [
                        {
                            "component": d.component_name,
                            "priority": d.priority,
                            "tokens": d.token_count,
                            "action": d.action,
                            "reason": d.reason
                        }
                        for d in log.decisions
                    ]
                }
                f.write(json.dumps(log_data) + "\n")

    def generate_summary(self) -> str:
        """
        Generate summary report across all iterations.

        Returns:
            Formatted summary report
        """
        if not self.logs:
            return "No context assembly logs recorded"

        total_iterations = len(self.logs)
        total_compressions = sum(1 for log in self.logs if log.compression_applied)
        avg_token_usage = sum(log.token_usage_percent for log in self.logs) / total_iterations

        # Component statistics
        component_stats: Dict[str, Dict[str, int]] = {}
        for log in self.logs:
            for decision in log.decisions:
                if decision.component_name not in component_stats:
                    component_stats[decision.component_name] = {
                        "included": 0,
                        "truncated": 0,
                        "excluded": 0
                    }
                component_stats[decision.component_name][decision.action] += 1

        lines = [
            "📊 Context Management Summary",
            f"Total iterations: {total_iterations}",
            f"Compressions applied: {total_compressions} ({total_compressions/total_iterations*100:.1f}%)",
            f"Average token usage: {avg_token_usage:.1f}%",
            "",
            "Component Statistics:",
        ]

        for comp_name, stats in sorted(component_stats.items()):
            total = sum(stats.values())
            lines.append(
                f"  - {comp_name}: "
                f"included={stats['included']}/{total}, "
                f"truncated={stats['truncated']}/{total}, "
                f"excluded={stats['excluded']}/{total}"
            )

        return "\n".join(lines)
