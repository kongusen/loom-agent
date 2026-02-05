"""
PlannerMixin - 规划逻辑

处理任务规划、步骤执行、结果聚合等功能。

从 core.py 拆分，遵循单一职责原则。
"""

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from loom.exceptions import TaskComplete
from loom.protocol import Task, TaskStatus

if TYPE_CHECKING:
    from .core import Agent


def create_plan_tool() -> dict[str, Any]:
    """创建 create_plan 元工具定义"""
    return {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": (
                "Create execution plan for complex tasks. "
                "Use when: task requires 3+ independent steps. "
                "Avoid when: single-step tasks, already executing plan step."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "Goal to achieve"},
                    "steps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of execution steps",
                    },
                    "reasoning": {
                        "type": "string",
                        "description": "Why this plan is needed",
                    },
                },
                "required": ["goal", "steps"],
            },
        },
    }


class PlannerMixin:
    """
    规划处理混入类

    提供规划相关的所有功能：
    - 执行规划
    - 步骤分解
    - 结果聚合
    """

    # 类型提示（由 Agent 类提供）
    node_id: str
    llm_provider: Any
    memory: Any
    system_prompt: str
    _root_context_id: str | None
    _recursive_depth: int

    async def _execute_plan(
        self,
        plan_args: dict[str, Any],
        parent_task: Task,
    ) -> str:
        """
        执行规划 - 实现Planning范式

        将复杂任务分解为多个子任务，使用分形架构执行。
        """
        goal = plan_args.get("goal", "")
        steps = plan_args.get("steps", [])
        reasoning = plan_args.get("reasoning", "")

        if not steps:
            return "Error: No steps provided in plan"

        # 发布规划事件
        await self._publish_event(
            action="node.planning",
            parameters={
                "goal": goal,
                "steps": steps,
                "reasoning": reasoning,
                "step_count": len(steps),
            },
            task_id=parent_task.taskId,
            session_id=parent_task.sessionId,
        )

        # 写入计划到 SHARED 作用域
        from loom.fractal.memory import MemoryScope

        plan_content = f"[Parent Plan] Goal: {goal}\n"
        if reasoning:
            plan_content += f"Reasoning: {reasoning}\n"
        plan_content += f"Steps ({len(steps)}):\n"
        for idx, step in enumerate(steps, 1):
            plan_content += f"  {idx}. {step}\n"

        plan_entry_id = f"plan:{parent_task.taskId}"
        await self.memory.write(plan_entry_id, plan_content, scope=MemoryScope.SHARED)

        # 准备上下文
        parent_context_id = await self._ensure_shared_task_context(parent_task)
        root_context_id = parent_task.parameters.get("root_context_id") or self._root_context_id
        context_hints = [cid for cid in [root_context_id, parent_context_id] if cid]

        # 执行每个步骤
        results = []
        parent_plan_summary = self._build_plan_summary(goal, reasoning, steps)

        for idx, step in enumerate(steps):
            subtask = Task(
                task_id=f"{parent_task.taskId}-step-{idx+1}-{uuid4()}",
                action="execute",
                parameters={
                    "content": step,
                    "parent_task_id": parent_task.taskId,
                    "step_index": idx + 1,
                    "total_steps": len(steps),
                    "is_plan_step": True,
                    "parent_plan": parent_plan_summary,
                    "root_context_id": root_context_id,
                },
                session_id=parent_task.sessionId,
            )

            child_node = await self._create_child_node(
                subtask=subtask,
                context_hints=context_hints,
            )

            result = await child_node.execute_task(subtask)
            await self._sync_memory_from_child(child_node)

            if result.status == TaskStatus.COMPLETED:
                step_result = (
                    result.result.get("content", str(result.result))
                    if isinstance(result.result, dict)
                    else str(result.result)
                )
                results.append(f"Step {idx+1}: {step_result}")
            else:
                results.append(f"Step {idx+1}: Failed - {result.error or 'Unknown error'}")

        # 聚合结果
        final_answer = await self._synthesize_plan_results(
            goal, parent_task.parameters.get("content", goal), results
        )

        raise TaskComplete(message=final_answer)

    def _build_plan_summary(
        self, goal: str, reasoning: str, steps: list[str]
    ) -> str:
        """构建计划摘要"""
        summary = f"Goal: {goal}\n"
        if reasoning:
            summary += f"Reasoning: {reasoning}\n"
        summary += f"Steps ({len(steps)}):\n"
        for idx, step in enumerate(steps, 1):
            summary += f"  {idx}. {step}\n"
        return summary

    async def _synthesize_plan_results(
        self, goal: str, original_question: str, results: list[str]
    ) -> str:
        """使用 LLM 综合生成最终答案"""
        steps_context = "\n".join(results)

        synthesis_prompt = f"""You have executed a plan to answer the user's question. Now provide a direct, comprehensive answer based on the execution results.

User's Original Question: {original_question}

Plan Execution Results:
{steps_context}

IMPORTANT:
- Provide a DIRECT answer to the user's question
- Do NOT describe the plan or say "I created a plan"
- Synthesize insights from the execution results
- MUST respond in the same language as the user's original question"""

        try:
            response = await self.llm_provider.chat(
                messages=[{"role": "user", "content": synthesis_prompt}],
                max_tokens=1000,
            )
            return response.content
        except Exception:
            return f"Plan '{goal}' completed:\n" + steps_context
