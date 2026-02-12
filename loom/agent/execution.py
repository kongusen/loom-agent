"""
ExecutionEngine - Agent 执行引擎

从 Agent.core 提取的核心执行循环。
负责 Agent 的迭代执行、工具调用、检查点管理。
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from loom.exceptions import TaskComplete
from loom.observability.metrics import LoomMetrics
from loom.runtime import Task, TaskStatus

if TYPE_CHECKING:
    from loom.agent.core import Agent

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Agent 执行引擎

    核心理念：Agent is just a for loop
    将 Agent._execute_impl 的循环逻辑提取为独立类。
    """

    def __init__(self, agent: Agent):
        self._agent = agent

    async def run(self, task: Task) -> Task:
        """
        执行任务的核心循环

        Args:
            task: 待执行的任务

        Returns:
            更新后的任务
        """
        agent = self._agent

        await agent._ensure_pending_tools_registered()
        agent.memory.add_task(task)
        await agent._ensure_shared_task_context(task)

        agent._current_task_id = task.taskId  # type: ignore[attr-defined]
        agent._current_session_id = task.sessionId  # type: ignore[attr-defined]
        agent._tracer.new_trace()

        try:
            # 记忆压缩
            if hasattr(agent, "memory_compactor") and agent.memory_compactor:
                current_context = await agent.context_orchestrator.build_context(
                    task.parameters.get("content", "")
                )
                compacted = await agent.memory_compactor.check_and_compact(
                    task,
                    current_context,
                    agent.context_orchestrator.max_tokens,
                )
                if compacted:
                    logger.info("Memory compaction triggered for task %s", task.taskId)

            # 加载 Skills
            task_content = task.parameters.get("content", "")
            activated_skills = await agent._load_relevant_skills(task_content)
            injected_instructions = activated_skills.get("injected_instructions", [])

            # 循环状态
            accumulated_messages: list[dict[str, Any]] = []
            final_content = ""
            iteration = 0

            # Checkpoint resume
            start_iteration = 0
            if agent._checkpoint_mgr:
                _cp = await agent._checkpoint_mgr.load_latest(agent.node_id, task.taskId)
                if _cp:
                    start_iteration = _cp.iteration + 1
                    if _cp.memory_snapshot and hasattr(agent.memory, "restore_snapshot"):
                        agent.memory.restore_snapshot(_cp.memory_snapshot)
                    accumulated_messages = list(_cp.tool_history or [])
                    logger.info("Resuming from checkpoint iteration %d", _cp.iteration)

            try:
                for iteration in range(start_iteration, agent.max_iterations):
                    agent._metrics.increment(LoomMetrics.ITERATIONS_TOTAL)

                    # 更新预算阶段
                    agent._adaptive_budget.update_phase(
                        current_iteration=iteration,
                        max_iterations=agent.max_iterations,
                    )

                    # 过滤 ephemeral 消息
                    filtered_messages = agent._filter_ephemeral_messages(accumulated_messages)

                    # 更新统一检索源的对话上下文
                    if agent._retrieval_source is not None:
                        agent._retrieval_source.set_context_messages(filtered_messages)

                    # 构建上下文
                    messages = await agent.context_orchestrator.build_context(
                        task.parameters.get("content", "")
                    )

                    # Skills 指令注入（仅第一次迭代）
                    if injected_instructions and iteration == 0:
                        skill_instructions = "\n\n=== Available Skills ===\n\n"
                        skill_instructions += "\n\n".join(injected_instructions)
                        messages.append({"role": "system", "content": skill_instructions})

                    if filtered_messages:
                        messages.extend(filtered_messages)

                    # LLM 调用
                    full_content = ""
                    tool_calls = []

                    async for chunk in agent.llm_provider.stream_chat(
                        messages,
                        tools=agent.all_tools if agent.all_tools else None,
                    ):
                        if chunk.type == "text":
                            content_str = (
                                str(chunk.content)
                                if isinstance(chunk.content, dict)
                                else chunk.content
                            )
                            full_content += content_str
                            await agent.publish_thinking(
                                content=content_str,
                                task_id=task.taskId,
                                metadata={"iteration": iteration},
                                session_id=task.sessionId,
                            )
                        elif chunk.type == "tool_call_complete":
                            if isinstance(chunk.content, dict):
                                tool_calls.append(chunk.content)
                            else:
                                try:
                                    tool_calls.append(json.loads(str(chunk.content)))
                                except (json.JSONDecodeError, TypeError):
                                    tool_calls.append(
                                        {"name": "", "arguments": {}, "content": str(chunk.content)}
                                    )
                        elif chunk.type == "error":
                            await agent._publish_event(
                                action="node.error",
                                parameters={"error": chunk.content},
                                task_id=task.taskId,
                            )

                    final_content = full_content

                    # 剥离 importance 标记
                    from loom.agent.core import _strip_importance_tag

                    clean_content, importance = _strip_importance_tag(full_content)
                    if importance is not None:
                        full_content = clean_content
                        final_content = clean_content
                        task.metadata["importance"] = importance
                        if agent.memory:
                            agent.memory.promote_task_to_l2(task)

                    # 无工具调用
                    if not tool_calls:
                        if agent.require_done_tool:
                            accumulated_messages.append(
                                {
                                    "role": "system",
                                    "content": (
                                        "Please call the 'done' tool to complete the task. "
                                        "IMPORTANT: First output your full response as text, "
                                        "then call done() with just a brief summary (1-2 sentences). "
                                        "Do NOT put your full response in the done() message parameter."
                                    ),
                                }
                            )
                            continue
                        else:
                            break

                    # 添加 assistant 消息
                    if tool_calls:
                        assistant_msg = {
                            "role": "assistant",
                            "content": full_content or "",
                            "tool_calls": [
                                {
                                    "id": tc.get("id", f"call_{i}"),
                                    "type": "function",
                                    "function": {
                                        "name": tc.get("name", ""),
                                        "arguments": (
                                            tc.get("arguments", "{}")
                                            if isinstance(tc.get("arguments"), str)
                                            else json.dumps(tc.get("arguments", {}))
                                        ),
                                    },
                                }
                                for i, tc in enumerate(tool_calls)
                            ],
                        }
                        accumulated_messages.append(assistant_msg)

                    # 执行工具调用
                    for tool_call in tool_calls:
                        if not isinstance(tool_call, dict):
                            continue
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("arguments", {})
                        if isinstance(tool_args, str):
                            try:
                                tool_args = json.loads(tool_args)
                            except json.JSONDecodeError:
                                tool_args = {}
                        if not isinstance(tool_args, dict):
                            tool_args = {}

                        agent._metrics.increment(LoomMetrics.TOOL_CALLS_TOTAL)

                        await agent.publish_tool_call(
                            tool_name=tool_name,
                            tool_args=tool_args,
                            task_id=task.taskId,
                            session_id=task.sessionId,
                        )

                        # done tool
                        if tool_name == "done":
                            from loom.tools.builtin.done import execute_done_tool

                            await execute_done_tool(tool_args)

                        # 元工具路由
                        if tool_name == "create_plan":
                            result = await agent._execute_plan(tool_args, task)
                        elif tool_name == "delegate_task":
                            result = await agent._auto_delegate(tool_args, task)
                        elif tool_name == "delegate_to_agent":
                            target_agent = tool_args.get("target_agent", "")
                            subtask = tool_args.get("subtask", "")
                            result = await agent._execute_delegate_task(
                                target_agent,
                                subtask,
                                task.taskId,
                                session_id=task.sessionId,
                            )
                        else:
                            result = await agent._tool_router.route(tool_name, tool_args)

                        await agent.publish_tool_result(
                            tool_name=tool_name,
                            result=result,
                            task_id=task.taskId,
                            session_id=task.sessionId,
                        )

                        accumulated_messages.append(
                            {
                                "role": "tool",
                                "content": result,
                                "tool_call_id": tool_call.get("id", ""),
                                "tool_name": tool_name,
                            }
                        )

                    # 保存检查点
                    if agent._checkpoint_mgr:
                        from loom.runtime.checkpoint import CheckpointData

                        _cp_data = CheckpointData(
                            agent_id=agent.node_id,
                            task_id=task.taskId,
                            iteration=iteration,
                            max_iterations=agent.max_iterations,
                            agent_state={"final_content": final_content},
                            memory_snapshot=(
                                agent.memory.export_snapshot()
                                if hasattr(agent.memory, "export_snapshot")
                                else {}
                            ),
                            tool_history=[
                                m for m in accumulated_messages if m.get("role") == "tool"
                            ],
                            context_metadata={"session_id": task.sessionId},
                        )
                        await agent._checkpoint_mgr.save(_cp_data)

            except TaskComplete as e:
                task.status = TaskStatus.COMPLETED
                task.result = {
                    "content": final_content or e.message,
                    "message": e.message,
                    "output": e.output,
                    "completed_explicitly": True,
                }
                await agent._self_evaluate(task)
                agent.memory.add_task(task)
                await agent.memory.promote_tasks_async()
                return task

            # 循环正常结束
            if not final_content:
                tool_outputs = [
                    m.get("content", "")
                    for m in accumulated_messages
                    if m.get("role") == "tool" and m.get("content")
                ]
                if tool_outputs:
                    final_content = "\n".join(tool_outputs)

            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": final_content,
                "completed_explicitly": False,
                "iterations": iteration + 1,
            }

            await agent._self_evaluate(task)
            agent.memory.add_task(task)
            await agent.memory.promote_tasks_async()

            return task
        finally:
            # Trace 摘要
            _trace_summary = agent._tracer.get_trace_summary()
            logger.debug(
                "Trace summary: spans=%d, duration=%.1fms, errors=%d",
                _trace_summary["span_count"],
                _trace_summary["total_duration_ms"],
                _trace_summary["error_count"],
            )

            # Metrics 导出
            if agent._metrics_exporters:
                _snapshot = agent._metrics.snapshot()
                for _mexp in agent._metrics_exporters:
                    try:
                        _mexp.export(_snapshot)
                    except Exception:
                        logger.debug("Metrics export failed", exc_info=True)

            # 清理任务上下文
            if hasattr(agent, "_current_task_id"):
                del agent._current_task_id
            if hasattr(agent, "_current_session_id"):
                del agent._current_session_id
