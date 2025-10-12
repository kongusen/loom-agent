"""Multi-Agent 系统 - 支持多个 Agent 协作完成复杂任务"""

from __future__ import annotations

from typing import Dict, Optional

from loom.components.agent import Agent
from loom.interfaces.llm import BaseLLM


class MultiAgentSystem:
    """
    Multi-Agent 协作系统

    支持:
    - 多个专业 Agent 协同工作
    - 协调器 LLM 进行任务分解和结果汇总
    - Agent 间通信与数据传递
    """

    def __init__(
        self,
        agents: Dict[str, Agent],
        coordinator: Optional[BaseLLM] = None,
    ) -> None:
        self.agents = agents
        self.coordinator = coordinator

    async def run(self, task: str) -> str:
        """
        执行多 Agent 任务

        工作流程:
        1. 协调器分解任务 (如果有)
        2. 分配子任务给不同 Agent
        3. 汇总结果
        """
        if not self.coordinator:
            # 简单模式:顺序执行所有 Agent
            results = {}
            for name, agent in self.agents.items():
                result = await agent.run(f"As {name}, help with: {task}")
                results[name] = result

            return self._format_results(results)

        # 协调模式:使用协调器分解任务
        subtasks = await self._decompose_task(task)

        results = {}
        for subtask in subtasks:
            agent_name = subtask.get("agent")
            subtask_desc = subtask.get("task", task)

            if agent_name and agent_name in self.agents:
                result = await self.agents[agent_name].run(subtask_desc)
                results[agent_name] = result

        # 汇总结果
        return await self._aggregate_results(task, results)

    async def _decompose_task(self, task: str) -> list[dict]:
        """使用协调器分解任务"""
        if not self.coordinator:
            return [{"agent": list(self.agents.keys())[0], "task": task}]

        agent_list = ", ".join(self.agents.keys())
        decompose_prompt = f"""You are a task coordinator for a multi-agent system.

Available agents: {agent_list}

Task: {task}

Decompose this task into subtasks and assign each to the most appropriate agent.
Return a JSON list like:
[
  {{"agent": "agent_name", "task": "subtask description"}},
  ...
]
"""

        response = await self.coordinator.generate([{"role": "user", "content": decompose_prompt}])

        # 简单解析 (实际应该用 JSON)
        import json

        try:
            subtasks = json.loads(response)
            if isinstance(subtasks, list):
                return subtasks
        except Exception:
            pass

        # 降级:单个任务
        return [{"agent": list(self.agents.keys())[0], "task": task}]

    async def _aggregate_results(self, original_task: str, results: Dict[str, str]) -> str:
        """汇总各 Agent 的结果"""
        if not self.coordinator:
            return self._format_results(results)

        results_text = "\n\n".join([f"**{name}**: {result}" for name, result in results.items()])

        aggregate_prompt = f"""You are a task coordinator for a multi-agent system.

Original task: {original_task}

Results from agents:
{results_text}

Synthesize these results into a coherent final answer.
"""

        return await self.coordinator.generate([{"role": "user", "content": aggregate_prompt}])

    def _format_results(self, results: Dict[str, str]) -> str:
        """格式化结果"""
        lines = ["## Multi-Agent Results\n"]
        for name, result in results.items():
            lines.append(f"### Agent: {name}")
            lines.append(result)
            lines.append("")
        return "\n".join(lines)
