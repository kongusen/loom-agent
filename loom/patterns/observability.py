"""
Observability & Evaluation - 可观测性和评估系统

包含：
- CrewTracer: 追踪和监控 Crew 执行
- DecisionLog: 决策日志
- CrewEvaluator: 质量评估（基于 LLM）

用于调试、优化和质量保证
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

from loom.core.base_agent import BaseAgent
from loom.core.message import Message
from loom.patterns.artifact_store import SubAgentResult
from loom.patterns.coordination import SubTask, TaskComplexity


# ===== Observability (可观测性) =====


@dataclass
class DecisionLogEntry:
    """决策日志条目"""

    timestamp: float
    log_type: str  # "task_delegation", "sub_agent_execution", "tool_usage", etc.
    content: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "type": self.log_type,
            "content": self.content,
        }


class CrewTracer:
    """
    Crew 执行追踪器

    追踪整个 crew 的执行过程，包括：
    - Coordinator 决策
    - Sub-agent 执行
    - 工具使用
    - 失败模式

    Example:
        ```python
        tracer = CrewTracer()

        # 记录决策
        tracer.log_coordinator_decision(
            complexity="complex",
            num_agents=10,
            subtasks=[...]
        )

        # 记录执行
        tracer.log_sub_agent_execution(
            agent="researcher1",
            task="研究市场",
            result=result,
            success=True
        )

        # 生成报告
        report = tracer.generate_report()
        print(report)
        ```
    """

    def __init__(self, enabled: bool = True):
        """
        初始化追踪器

        Args:
            enabled: 是否启用追踪
        """
        self.enabled = enabled
        self.decision_log: List[DecisionLogEntry] = []
        self.tool_usage_stats: Dict[str, Dict[str, int]] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def start(self):
        """开始追踪"""
        if self.enabled:
            self.start_time = time.time()

    def end(self):
        """结束追踪"""
        if self.enabled:
            self.end_time = time.time()

    def log_coordinator_decision(
        self,
        original_task: str,
        complexity: TaskComplexity,
        num_subtasks: int,
        estimated_agents: int,
        reasoning: str,
    ):
        """记录 coordinator 决策"""
        if not self.enabled:
            return

        entry = DecisionLogEntry(
            timestamp=time.time(),
            log_type="task_delegation",
            content={
                "original_task": original_task[:100],  # 截断
                "complexity": complexity.value,
                "num_subtasks": num_subtasks,
                "estimated_agents": estimated_agents,
                "reasoning": reasoning[:200],
            },
        )
        self.decision_log.append(entry)

    def log_sub_agent_execution(
        self,
        agent_id: str,
        task_id: str,
        task_description: str,
        result: SubAgentResult,
    ):
        """记录 sub-agent 执行"""
        if not self.enabled:
            return

        # 提取工具使用
        tools_used = result.metadata.get("tools_used", [])
        for tool in tools_used:
            self._record_tool_usage(agent_id, tool, result.success)

        entry = DecisionLogEntry(
            timestamp=time.time(),
            log_type="sub_agent_execution",
            content={
                "agent_id": agent_id,
                "task_id": task_id,
                "task": task_description[:100],
                "success": result.success,
                "error": result.error,
                "tools_used": tools_used,
                "summary_length": len(result.summary),
                "has_artifacts": len(result.artifacts) > 0,
            },
        )
        self.decision_log.append(entry)

    def log_error(
        self, agent_id: str, task_id: str, error: str, recovery_action: str
    ):
        """记录错误和恢复"""
        if not self.enabled:
            return

        entry = DecisionLogEntry(
            timestamp=time.time(),
            log_type="error",
            content={
                "agent_id": agent_id,
                "task_id": task_id,
                "error": error[:200],
                "recovery_action": recovery_action,
            },
        )
        self.decision_log.append(entry)

    def _record_tool_usage(self, agent_id: str, tool: str, success: bool):
        """记录工具使用统计"""
        key = f"{agent_id}:{tool}"
        if key not in self.tool_usage_stats:
            self.tool_usage_stats[key] = {"success": 0, "failure": 0}

        if success:
            self.tool_usage_stats[key]["success"] += 1
        else:
            self.tool_usage_stats[key]["failure"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.decision_log:
            return {"enabled": self.enabled, "total_events": 0}

        # 计算各种统计
        total_events = len(self.decision_log)
        event_types = {}
        for entry in self.decision_log:
            event_types[entry.log_type] = event_types.get(entry.log_type, 0) + 1

        # 成功率
        executions = [
            e for e in self.decision_log if e.log_type == "sub_agent_execution"
        ]
        successful = sum(1 for e in executions if e.content.get("success", False))
        success_rate = (successful / len(executions) * 100) if executions else 0

        # 耗时
        duration = (
            (self.end_time - self.start_time)
            if self.start_time and self.end_time
            else None
        )

        return {
            "enabled": self.enabled,
            "total_events": total_events,
            "event_types": event_types,
            "total_executions": len(executions),
            "successful_executions": successful,
            "success_rate": round(success_rate, 2),
            "duration_seconds": round(duration, 2) if duration else None,
            "tool_usage_count": len(self.tool_usage_stats),
        }

    def generate_report(self) -> str:
        """生成执行报告"""
        if not self.enabled or not self.decision_log:
            return "追踪未启用或无数据"

        stats = self.get_stats()

        report_lines = [
            "# Crew 执行报告\n",
            "## 整体统计",
            f"- 总耗时: {stats.get('duration_seconds', 'N/A')} 秒",
            f"- 总事件数: {stats['total_events']}",
            f"- Sub-agent 执行次数: {stats['total_executions']}",
            f"- 成功率: {stats['success_rate']}%",
            "",
            "## 事件类型分布",
        ]

        for event_type, count in stats["event_types"].items():
            report_lines.append(f"- {event_type}: {count}")

        # 工具使用统计
        if self.tool_usage_stats:
            report_lines.append("\n## 工具使用统计\n")
            for key, counts in self.tool_usage_stats.items():
                total = counts["success"] + counts["failure"]
                success_rate = (counts["success"] / total * 100) if total > 0 else 0
                report_lines.append(
                    f"- {key}: {total} 次（成功率 {success_rate:.1f}%）"
                )

        # 失败分析
        errors = [e for e in self.decision_log if e.log_type == "error"]
        if errors:
            report_lines.append(f"\n## 失败分析\n")
            report_lines.append(f"- 总失败次数: {len(errors)}")
            # 分组统计错误类型
            error_types: Dict[str, int] = {}
            for error_entry in errors:
                error_msg = error_entry.content.get("error", "unknown")
                error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg
                error_types[error_type] = error_types.get(error_type, 0) + 1

            for error_type, count in error_types.items():
                report_lines.append(f"  - {error_type}: {count} 次")

        return "\n".join(report_lines)

    def render_decision_tree(self) -> str:
        """
        渲染决策树（简化版）

        TODO: 实现更复杂的可视化
        """
        if not self.enabled or not self.decision_log:
            return "无决策数据"

        lines = ["决策树:\n"]

        # 找到任务分解事件
        delegations = [
            e for e in self.decision_log if e.log_type == "task_delegation"
        ]
        if delegations:
            delegation = delegations[0]
            lines.append(
                f"├─ Coordinator: 分解为 {delegation.content['num_subtasks']} 个子任务"
            )

        # 找到执行事件
        executions = [
            e for e in self.decision_log if e.log_type == "sub_agent_execution"
        ]
        for i, exec_entry in enumerate(executions):
            content = exec_entry.content
            status = "✓" if content["success"] else "✗"
            indent = "│  " if i < len(executions) - 1 else "   "
            lines.append(
                f"{indent}├─ SubAgent ({content['agent_id']}): {content['task'][:50]}... {status}"
            )

        return "\n".join(lines)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"CrewTracer("
            f"enabled={self.enabled}, "
            f"events={stats['total_events']}, "
            f"success_rate={stats.get('success_rate', 0)}%)"
        )


# ===== Evaluation (评估) =====


@dataclass
class EvalMetrics:
    """评估指标"""

    factual_accuracy: float  # 0.0-1.0
    citation_accuracy: float
    completeness: float
    source_quality: float
    tool_efficiency: float
    overall: float
    pass_: bool  # 是否通过
    feedback: str  # 详细反馈

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> EvalMetrics:
        """从 JSON 创建"""
        scores = data.get("scores", {})
        return cls(
            factual_accuracy=scores.get("factual_accuracy", 0.0),
            citation_accuracy=scores.get("citation_accuracy", 0.0),
            completeness=scores.get("completeness", 0.0),
            source_quality=scores.get("source_quality", 0.0),
            tool_efficiency=scores.get("tool_efficiency", 0.0),
            overall=data.get("overall", 0.0),
            pass_=data.get("pass", False),
            feedback=data.get("feedback", ""),
        )


class CrewEvaluator:
    """
    Crew 执行质量评估器

    使用 LLM 作为 judge 评估结果质量

    Example:
        ```python
        evaluator = CrewEvaluator(judge_model=OpenAILLM(model="gpt-4"))

        metrics = await evaluator.evaluate(
            task="分析AI芯片市场",
            result="[crew的输出结果]",
            criteria=["factual_accuracy", "completeness"]
        )

        print(f"Overall score: {metrics.overall}")
        print(f"Pass: {metrics.pass_}")
        ```
    """

    EVAL_PROMPT_TEMPLATE = """评估以下 Crew 任务的完成质量：

**任务**: {task}

**结果**: {result}

**评分标准** (0.0-1.0)：
1. **事实准确性** (factual_accuracy): 论断是否与来源相符？
2. **引用准确性** (citation_accuracy): 引用是否正确匹配来源？（如果无引用要求，可给N/A）
3. **完整性** (completeness): 是否涵盖了所有要求的方面？
4. **来源质量** (source_quality): 是否使用了权威的原始资料？
5. **工具效率** (tool_efficiency): 是否合理使用了合适的工具？（如果无工具信息，可给N/A）

请返回 JSON：
{{
    "scores": {{
        "factual_accuracy": 0.0-1.0,
        "citation_accuracy": 0.0-1.0 或 "N/A",
        "completeness": 0.0-1.0,
        "source_quality": 0.0-1.0,
        "tool_efficiency": 0.0-1.0 或 "N/A"
    }},
    "overall": 0.0-1.0,
    "pass": true/false,
    "feedback": "详细的反馈，指出优点和需要改进的地方..."
}}

只返回 JSON，不要其他内容。"""

    def __init__(self, judge_agent: BaseAgent):
        """
        初始化评估器

        Args:
            judge_agent: 用作评审的 agent（推荐使用强模型如 GPT-4 或 Claude）
        """
        self.judge_agent = judge_agent

    async def evaluate(
        self,
        task: str,
        result: str,
        criteria: Optional[List[str]] = None,
    ) -> EvalMetrics:
        """
        评估 crew 执行结果

        Args:
            task: 原始任务
            result: Crew 输出结果
            criteria: 评分标准（可选，默认全部）

        Returns:
            EvalMetrics: 评估指标
        """
        prompt = self.EVAL_PROMPT_TEMPLATE.format(task=task, result=result[:2000])

        try:
            response = await self.judge_agent.run(prompt)

            # 解析 JSON
            import json

            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            eval_data = json.loads(content)

            # 处理 N/A
            scores = eval_data.get("scores", {})
            for key, value in scores.items():
                if value == "N/A":
                    scores[key] = 0.5  # 默认中等分数

            eval_data["scores"] = scores

            return EvalMetrics.from_json(eval_data)

        except Exception as e:
            # 评估失败：返回默认指标
            return EvalMetrics(
                factual_accuracy=0.5,
                citation_accuracy=0.5,
                completeness=0.5,
                source_quality=0.5,
                tool_efficiency=0.5,
                overall=0.5,
                pass_=False,
                feedback=f"评估失败: {str(e)}",
            )

    def __repr__(self) -> str:
        return f"CrewEvaluator(judge={self.judge_agent.name})"


__all__ = [
    "DecisionLogEntry",
    "CrewTracer",
    "EvalMetrics",
    "CrewEvaluator",
]
