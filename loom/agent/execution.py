"""
ExecutionEngine - Agent 执行引擎

从 Agent.core 提取的核心执行循环。
负责 Agent 的迭代执行、工具调用、检查点管理。

v0.6: 消息直接写入 L1 滑动窗口，不再使用 accumulated_messages。
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


def _extract_response_from_l1(memory: Any) -> str:
    """Extract the response from L1 assistant messages.

    Scans L1 message history in reverse to find assistant text content.
    Skips tool-call-only assistant messages (no text content).
    """
    items = memory.get_message_items()
    # Collect assistant text from the last contiguous assistant turn
    parts: list[str] = []
    for item in reversed(items):
        if item.role == "assistant" and item.content:
            parts.append(str(item.content))
        elif item.role == "assistant":
            continue  # tool-call-only assistant message, skip
        else:
            if parts:
                break  # hit a non-assistant message after collecting, stop
    parts.reverse()
    return "\n".join(parts)


class ExecutionEngine:
    """
    Agent 执行引擎

    核心理念：Agent is just a for loop

    v0.6 变更：
    - 消息直接写入 L1 滑动窗口（memory.add_message）
    - 移除 accumulated_messages，L1 即对话历史
    - L1 驱逐自动触发 L2/L3 管线
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

            # 将用户输入写入 L1 滑动窗口
            agent.memory.add_message(
                "user",
                task_content,
                metadata={"task_id": task.taskId, "session_id": task.sessionId},
            )

            # 循环状态
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
                    logger.info("Resuming from checkpoint iteration %d", _cp.iteration)

            try:
                for iteration in range(start_iteration, agent.max_iterations):
                    agent._metrics.increment(LoomMetrics.ITERATIONS_TOTAL)

                    # 更新预算阶段
                    agent._adaptive_budget.update_phase(
                        current_iteration=iteration,
                        max_iterations=agent.max_iterations,
                    )

                    # 获取 L1 对话历史
                    l1_messages = agent.memory.get_context_messages()

                    # 过滤 ephemeral 消息
                    filtered_messages = agent._filter_ephemeral_messages(l1_messages)

                    # 更新统一检索源的对话上下文
                    if agent._retrieval_source is not None:
                        agent._retrieval_source.set_context_messages(filtered_messages)

                    # 构建上下文（system prompt + L2/L3 + other sources）
                    messages = await agent.context_orchestrator.build_context(
                        task.parameters.get("content", "")
                    )

                    # Skills 指令注入（仅第一次迭代）
                    if injected_instructions and iteration == 0:
                        skill_instructions = "\n\n=== Available Skills ===\n\n"
                        skill_instructions += "\n\n".join(injected_instructions)
                        messages.append({"role": "system", "content": skill_instructions})

                    # 追加 L1 对话历史
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

                    # 构建 importance metadata（传入 L1，驱逐时流入 L2）
                    _imp_meta = {"importance": importance} if importance is not None else {}

                    # 无工具调用
                    if not tool_calls:
                        if agent.require_done_tool:
                            # Record assistant text to L1, then remind to call done
                            if full_content:
                                agent.memory.add_message("assistant", full_content, metadata=_imp_meta)
                            agent.memory.add_message(
                                "system",
                                "Please call the 'done' tool to signal task completion.",
                                metadata={"ephemeral": True},
                            )
                            continue
                        else:
                            # 记录 assistant 最终回复到 L1
                            agent.memory.add_message("assistant", full_content, metadata=_imp_meta)
                            break

                    # 有工具调用 — 记录 assistant 消息到 L1
                    formatted_tool_calls = [
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
                    ]
                    agent.memory.add_message(
                        "assistant",
                        full_content or "",
                        tool_calls=formatted_tool_calls,
                        metadata=_imp_meta,
                    )

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

                        # 记录工具结果到 L1
                        agent.memory.add_message(
                            "tool",
                            result,
                            tool_call_id=tool_call.get("id", ""),
                            tool_name=tool_name,
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
                            tool_history=[],  # L1 已包含完整历史
                            context_metadata={"session_id": task.sessionId},
                        )
                        await agent._checkpoint_mgr.save(_cp_data)

            except TaskComplete as e:
                task.status = TaskStatus.COMPLETED
                # Response comes from L1 assistant messages, not done.message
                response = _extract_response_from_l1(agent.memory)
                task.result = {
                    "content": response or e.message or "",
                    "message": e.message,
                    "output": e.output,
                    "completed_explicitly": True,
                }
                await agent._self_evaluate(task)
                return task

            # 循环正常结束 — extract response from L1
            response = _extract_response_from_l1(agent.memory)
            if not response:
                # Fallback: tool outputs from L1
                items = agent.memory.get_message_items()
                tool_outputs = [
                    str(item.content)
                    for item in items
                    if item.role == "tool" and item.content
                ]
                if tool_outputs:
                    response = "\n".join(tool_outputs[-5:])

            task.status = TaskStatus.COMPLETED
            task.result = {
                "content": response or "",
                "completed_explicitly": False,
                "iterations": iteration + 1,
            }

            await agent._self_evaluate(task)

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
