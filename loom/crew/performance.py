"""
Performance monitoring and optimization utilities for Crew system.

This module provides performance tracking, agent pooling, and optimization
tools for the multi-agent Crew system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from collections import defaultdict


@dataclass
class TaskExecutionMetrics:
    """Metrics for a single task execution"""

    task_id: str
    role: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

    def finish(self, success: bool = True, error: Optional[str] = None):
        """Mark task as finished and calculate duration"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = success
        self.error = error


@dataclass
class AgentPoolStats:
    """Statistics for agent pool usage"""

    agent_creates: int = 0
    agent_reuses: int = 0
    total_executions: int = 0
    total_duration: float = 0.0
    errors: int = 0

    def get_reuse_rate(self) -> float:
        """Calculate agent reuse rate"""
        total = self.agent_creates + self.agent_reuses
        return self.agent_reuses / total if total > 0 else 0.0

    def get_average_duration(self) -> float:
        """Calculate average execution duration"""
        return (
            self.total_duration / self.total_executions
            if self.total_executions > 0
            else 0.0
        )


class PerformanceMonitor:
    """
    Performance monitoring for Crew operations.

    Tracks execution metrics, agent pool usage, and performance statistics
    across all Crew operations.

    Example:
        ```python
        monitor = PerformanceMonitor()

        # Start tracking task
        monitor.start_task("task1", "researcher")

        # ... execute task ...

        # Finish tracking
        monitor.finish_task("task1", success=True)

        # Get statistics
        stats = monitor.get_stats()
        print(f"Total tasks: {stats['total_tasks']}")
        print(f"Average duration: {stats['average_duration']:.2f}s")
        ```
    """

    def __init__(self):
        # Task execution tracking
        self._active_tasks: Dict[str, TaskExecutionMetrics] = {}
        self._completed_tasks: List[TaskExecutionMetrics] = []

        # Agent pool statistics
        self._agent_stats: Dict[str, AgentPoolStats] = defaultdict(AgentPoolStats)

        # Overall statistics
        self._orchestration_count = 0
        self._total_orchestration_time = 0.0

    def start_task(self, task_id: str, role: str) -> None:
        """
        Start tracking a task execution.

        Args:
            task_id: Unique task identifier
            role: Role executing the task
        """
        metrics = TaskExecutionMetrics(
            task_id=task_id,
            role=role,
            start_time=time.time()
        )
        self._active_tasks[task_id] = metrics

    def finish_task(
        self,
        task_id: str,
        success: bool = True,
        error: Optional[str] = None
    ) -> None:
        """
        Finish tracking a task execution.

        Args:
            task_id: Task identifier
            success: Whether task succeeded
            error: Error message if failed
        """
        if task_id not in self._active_tasks:
            return

        metrics = self._active_tasks.pop(task_id)
        metrics.finish(success=success, error=error)
        self._completed_tasks.append(metrics)

        # Update agent stats
        role_stats = self._agent_stats[metrics.role]
        role_stats.total_executions += 1
        if metrics.duration:
            role_stats.total_duration += metrics.duration
        if not success:
            role_stats.errors += 1

    def record_agent_create(self, role: str) -> None:
        """
        Record agent creation.

        Args:
            role: Role name
        """
        self._agent_stats[role].agent_creates += 1

    def record_agent_reuse(self, role: str) -> None:
        """
        Record agent reuse from pool.

        Args:
            role: Role name
        """
        self._agent_stats[role].agent_reuses += 1

    def start_orchestration(self) -> str:
        """
        Start tracking an orchestration.

        Returns:
            str: Orchestration ID
        """
        self._orchestration_count += 1
        orchestration_id = f"orch_{self._orchestration_count}"
        return orchestration_id

    def finish_orchestration(self, duration: float) -> None:
        """
        Finish tracking an orchestration.

        Args:
            duration: Orchestration duration in seconds
        """
        self._total_orchestration_time += duration

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.

        Returns:
            Dict: Performance statistics including:
                - total_tasks: Total tasks executed
                - successful_tasks: Successfully completed tasks
                - failed_tasks: Failed tasks
                - average_duration: Average task duration
                - total_duration: Total execution time
                - agent_stats: Per-agent statistics
                - orchestration_stats: Orchestration statistics
        """
        total_tasks = len(self._completed_tasks)
        successful_tasks = sum(1 for t in self._completed_tasks if t.success)
        failed_tasks = total_tasks - successful_tasks

        total_duration = sum(
            t.duration for t in self._completed_tasks if t.duration
        )
        avg_duration = total_duration / total_tasks if total_tasks > 0 else 0.0

        # Per-role statistics
        role_stats = {}
        for role, stats in self._agent_stats.items():
            role_stats[role] = {
                "creates": stats.agent_creates,
                "reuses": stats.agent_reuses,
                "reuse_rate": stats.get_reuse_rate(),
                "executions": stats.total_executions,
                "average_duration": stats.get_average_duration(),
                "errors": stats.errors,
            }

        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "average_duration": avg_duration,
            "total_duration": total_duration,
            "agent_stats": role_stats,
            "orchestration_stats": {
                "total_orchestrations": self._orchestration_count,
                "total_time": self._total_orchestration_time,
                "average_time": (
                    self._total_orchestration_time / self._orchestration_count
                    if self._orchestration_count > 0
                    else 0.0
                ),
            },
        }

    def get_task_history(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get task execution history.

        Args:
            role: Optional role filter

        Returns:
            List[Dict]: Task execution history
        """
        tasks = self._completed_tasks
        if role:
            tasks = [t for t in tasks if t.role == role]

        return [
            {
                "task_id": t.task_id,
                "role": t.role,
                "duration": t.duration,
                "success": t.success,
                "error": t.error,
            }
            for t in tasks
        ]

    def reset(self) -> None:
        """Reset all statistics"""
        self._active_tasks.clear()
        self._completed_tasks.clear()
        self._agent_stats.clear()
        self._orchestration_count = 0
        self._total_orchestration_time = 0.0

    def get_summary(self) -> str:
        """
        Get human-readable summary of performance.

        Returns:
            str: Formatted performance summary
        """
        stats = self.get_stats()

        lines = [
            "Performance Summary",
            "=" * 50,
            f"Total Tasks: {stats['total_tasks']}",
            f"  Successful: {stats['successful_tasks']}",
            f"  Failed: {stats['failed_tasks']}",
            f"Average Duration: {stats['average_duration']:.2f}s",
            f"Total Duration: {stats['total_duration']:.2f}s",
            "",
            "Agent Statistics:",
        ]

        for role, role_stats in stats['agent_stats'].items():
            lines.append(f"  {role}:")
            lines.append(f"    Creates: {role_stats['creates']}")
            lines.append(f"    Reuses: {role_stats['reuses']}")
            lines.append(f"    Reuse Rate: {role_stats['reuse_rate']:.1%}")
            lines.append(f"    Avg Duration: {role_stats['average_duration']:.2f}s")

        orch_stats = stats['orchestration_stats']
        lines.extend([
            "",
            "Orchestration Statistics:",
            f"  Total: {orch_stats['total_orchestrations']}",
            f"  Total Time: {orch_stats['total_time']:.2f}s",
            f"  Avg Time: {orch_stats['average_time']:.2f}s",
        ])

        return "\n".join(lines)
