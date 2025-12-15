"""
递归控制模式 - 高级 Agent 推理能力

基于吴恩达的 Agent 四大范式，实现：
1. Reflection（反思）- 自我评估和改进
2. Planning（规划）- CoT、ToT、Plan-and-Execute
3. Recursive Control（递归控制）- 灵活的控制流

支持的思维模式：
- Chain-of-Thought (CoT) - 思维链
- Tree-of-Thoughts (ToT) - 思维树
- ReAct - 推理+行动
- Self-Consistency - 自洽性
- Reflection - 反思循环
- Plan-and-Execute - 规划-执行
"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field

from loom.core.message import Message
from loom.core.base_agent import BaseAgent


# ============================================================================
# 思维模式枚举
# ============================================================================


class ThinkingMode(str, Enum):
    """
    思维模式枚举

    定义不同的推理和控制模式
    """
    # 基础模式
    DIRECT = "direct"  # 直接响应（默认）
    REACT = "react"  # 推理+行动（已实现）

    # 高级规划模式
    CHAIN_OF_THOUGHT = "cot"  # 思维链：逐步推理
    TREE_OF_THOUGHTS = "tot"  # 思维树：探索多条路径
    PLAN_AND_EXECUTE = "plan_execute"  # 先规划后执行

    # 质量改进模式
    REFLECTION = "reflection"  # 反思：自我评估和改进
    SELF_CONSISTENCY = "self_consistency"  # 自洽性：多次生成+投票

    # 混合模式
    ADAPTIVE = "adaptive"  # 自适应：根据任务选择模式


# ============================================================================
# 思维节点（用于 ToT）
# ============================================================================


@dataclass
class ThoughtNode:
    """
    思维节点 - Tree of Thoughts 的基本单元

    每个节点代表一个推理步骤或决策点
    """
    content: str  # 思维内容
    score: float = 0.0  # 评分（0-1）
    depth: int = 0  # 深度
    parent: Optional[ThoughtNode] = None  # 父节点
    children: List[ThoughtNode] = field(default_factory=list)  # 子节点
    is_terminal: bool = False  # 是否为终端节点
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据

    def add_child(self, child: ThoughtNode) -> None:
        """添加子节点"""
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)

    def get_path(self) -> List[ThoughtNode]:
        """获取从根节点到当前节点的路径"""
        path = []
        node = self
        while node is not None:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def get_path_content(self) -> str:
        """获取路径的文本表示"""
        path = self.get_path()
        return " → ".join([node.content for node in path])


# ============================================================================
# 反思循环
# ============================================================================


class ReflectionLoop:
    """
    反思循环 - Reflection Pattern

    Agent 自我评估和改进输出：
    1. 生成初始响应
    2. 评估响应质量
    3. 根据评估改进
    4. 重复直到满意或达到上限

    Example:
        ```python
        loop = ReflectionLoop(
            agent=agent,
            max_iterations=3,
            improvement_threshold=0.8
        )

        result = await loop.run(message)
        ```
    """

    def __init__(
        self,
        agent: BaseAgent,
        max_iterations: int = 3,
        improvement_threshold: float = 0.8,
        evaluator: Optional[Callable] = None,
    ):
        """
        初始化反思循环

        Args:
            agent: Agent 实例
            max_iterations: 最大迭代次数
            improvement_threshold: 改进阈值（0-1）
            evaluator: 自定义评估函数 (response: str) -> float
        """
        self.agent = agent
        self.max_iterations = max_iterations
        self.improvement_threshold = improvement_threshold
        self.evaluator = evaluator or self._default_evaluator

        self.iterations_history: List[Dict[str, Any]] = []

    async def run(self, message: Message) -> Message:
        """
        执行反思循环

        Args:
            message: 输入消息

        Returns:
            改进后的响应消息
        """
        current_message = message
        best_response = None
        best_score = 0.0

        for iteration in range(self.max_iterations):
            # 1. 生成响应
            response = await self.agent.run(current_message)

            # 2. 评估响应
            score = await self.evaluator(response.content)

            # 3. 记录历史
            self.iterations_history.append({
                "iteration": iteration,
                "response": response.content,
                "score": score,
            })

            # 4. 更新最佳响应
            if score > best_score:
                best_score = score
                best_response = response

            # 5. 检查是否满足阈值
            if score >= self.improvement_threshold:
                break

            # 6. 生成改进提示
            if iteration < self.max_iterations - 1:
                feedback = await self._generate_feedback(response.content, score)
                current_message = Message(
                    role="user",
                    content=f"Previous response:\n{response.content}\n\nFeedback:\n{feedback}\n\nPlease improve your response based on the feedback."
                )

        return best_response or response

    async def _default_evaluator(self, response: str) -> float:
        """
        默认评估器（使用 Agent 自我评估）

        Args:
            response: 响应内容

        Returns:
            评分（0-1）
        """
        eval_message = Message(
            role="user",
            content=f"""Evaluate the following response on a scale of 0-1:

Response: {response}

Provide only a numeric score between 0 and 1, where:
- 0.0-0.3: Poor quality
- 0.3-0.6: Acceptable quality
- 0.6-0.8: Good quality
- 0.8-1.0: Excellent quality

Score:"""
        )

        eval_response = await self.agent.run(eval_message)

        # 提取分数
        try:
            score = float(eval_response.content.strip())
            return max(0.0, min(1.0, score))
        except ValueError:
            return 0.5  # 默认中等分数

    async def _generate_feedback(self, response: str, score: float) -> str:
        """
        生成改进反馈

        Args:
            response: 当前响应
            score: 评分

        Returns:
            改进建议
        """
        feedback_message = Message(
            role="user",
            content=f"""The previous response scored {score:.2f}/1.0.

Response: {response}

Provide specific feedback on how to improve this response. Focus on:
1. Accuracy and completeness
2. Clarity and structure
3. Relevance to the task
4. Any missing information

Feedback:"""
        )

        feedback_response = await self.agent.run(feedback_message)
        return feedback_response.content


# ============================================================================
# 思维树（Tree of Thoughts）
# ============================================================================


class TreeOfThoughts:
    """
    思维树 - Tree of Thoughts Pattern

    探索多条推理路径，评估和选择最佳路径：
    1. 生成多个候选思维步骤
    2. 评估每个步骤的质量
    3. 选择最有前景的路径继续探索
    4. 重复直到找到解决方案

    Example:
        ```python
        tot = TreeOfThoughts(
            agent=agent,
            branching_factor=3,
            max_depth=5,
            selection_strategy="best_first"
        )

        result = await tot.run(message)
        ```
    """

    def __init__(
        self,
        agent: BaseAgent,
        branching_factor: int = 3,
        max_depth: int = 5,
        selection_strategy: str = "best_first",
        evaluator: Optional[Callable] = None,
    ):
        """
        初始化思维树

        Args:
            agent: Agent 实例
            branching_factor: 每个节点的分支数
            max_depth: 最大深度
            selection_strategy: 选择策略（"best_first", "beam_search", "dfs"）
            evaluator: 评估函数 (thought: str) -> float
        """
        self.agent = agent
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self.selection_strategy = selection_strategy
        self.evaluator = evaluator or self._default_evaluator

        self.root: Optional[ThoughtNode] = None
        self.explored_nodes: List[ThoughtNode] = []

    async def run(self, message: Message) -> Message:
        """
        执行思维树搜索

        Args:
            message: 输入消息

        Returns:
            最佳路径的响应
        """
        # 1. 创建根节点
        self.root = ThoughtNode(content=message.content, depth=0)
        self.explored_nodes = [self.root]

        # 2. 搜索最佳路径
        if self.selection_strategy == "best_first":
            best_node = await self._best_first_search()
        elif self.selection_strategy == "beam_search":
            best_node = await self._beam_search()
        elif self.selection_strategy == "dfs":
            best_node = await self._depth_first_search()
        else:
            raise ValueError(f"Unknown selection strategy: {self.selection_strategy}")

        # 3. 生成最终响应
        path_content = best_node.get_path_content()
        final_message = Message(
            role="user",
            content=f"Based on the reasoning path:\n{path_content}\n\nProvide the final answer:"
        )

        return await self.agent.run(final_message)

    async def _best_first_search(self) -> ThoughtNode:
        """最佳优先搜索"""
        current_node = self.root

        for depth in range(self.max_depth):
            # 生成子节点
            children = await self._generate_children(current_node)

            if not children:
                break

            # 评估所有子节点
            for child in children:
                child.score = await self.evaluator(child.content)
                current_node.add_child(child)
                self.explored_nodes.append(child)

            # 选择最佳子节点
            best_child = max(children, key=lambda n: n.score)

            # 检查是否为终端节点
            if best_child.is_terminal or best_child.score >= 0.9:
                return best_child

            current_node = best_child

        return current_node

    async def _beam_search(self, beam_width: int = 3) -> ThoughtNode:
        """束搜索"""
        current_beam = [self.root]

        for depth in range(self.max_depth):
            all_candidates = []

            # 为每个节点生成子节点
            for node in current_beam:
                children = await self._generate_children(node)

                for child in children:
                    child.score = await self.evaluator(child.content)
                    node.add_child(child)
                    self.explored_nodes.append(child)
                    all_candidates.append(child)

            if not all_candidates:
                break

            # 选择 top-k 候选
            all_candidates.sort(key=lambda n: n.score, reverse=True)
            current_beam = all_candidates[:beam_width]

            # 检查是否有终端节点
            for node in current_beam:
                if node.is_terminal or node.score >= 0.9:
                    return node

        # 返回最佳节点
        return max(current_beam, key=lambda n: n.score)

    async def _depth_first_search(self) -> ThoughtNode:
        """深度优先搜索"""
        best_node = self.root
        best_score = 0.0

        async def dfs(node: ThoughtNode, depth: int) -> None:
            nonlocal best_node, best_score

            if depth >= self.max_depth:
                return

            # 生成子节点
            children = await self._generate_children(node)

            for child in children:
                child.score = await self.evaluator(child.content)
                node.add_child(child)
                self.explored_nodes.append(child)

                if child.score > best_score:
                    best_score = child.score
                    best_node = child

                if child.is_terminal or child.score >= 0.9:
                    return

                await dfs(child, depth + 1)

        await dfs(self.root, 0)
        return best_node

    async def _generate_children(self, node: ThoughtNode) -> List[ThoughtNode]:
        """
        生成子节点（下一步思维）

        Args:
            node: 当前节点

        Returns:
            子节点列表
        """
        prompt = f"""Current thought: {node.content}

Generate {self.branching_factor} different next steps or reasoning paths to continue.
Each step should be a distinct approach to solving the problem.

Provide {self.branching_factor} brief next steps (one per line):"""

        message = Message(role="user", content=prompt)
        response = await self.agent.run(message)

        # 解析响应为多个子节点
        lines = response.content.strip().split('\n')
        children = []

        for line in lines[:self.branching_factor]:
            line = line.strip()
            if line and not line.startswith('#'):
                # 移除编号前缀（如 "1. ", "- "）
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                line = re.sub(r'^[-*]\s*', '', line)

                child = ThoughtNode(content=line)
                children.append(child)

        return children

    async def _default_evaluator(self, thought: str) -> float:
        """
        默认评估器

        Args:
            thought: 思维内容

        Returns:
            评分（0-1）
        """
        eval_message = Message(
            role="user",
            content=f"""Evaluate the quality and promise of this reasoning step on a scale of 0-1:

Thought: {thought}

Consider:
- Is it logical and coherent?
- Does it move toward a solution?
- Is it a promising direction?

Provide only a numeric score (0-1). Score:"""
        )

        eval_response = await self.agent.run(eval_message)

        try:
            score = float(eval_response.content.strip())
            return max(0.0, min(1.0, score))
        except ValueError:
            return 0.5


# ============================================================================
# 规划-执行模式
# ============================================================================


@dataclass
class Plan:
    """执行计划"""
    steps: List[str]  # 计划步骤
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """执行结果"""
    step: str  # 步骤描述
    result: str  # 执行结果
    success: bool = True  # 是否成功
    metadata: Dict[str, Any] = field(default_factory=dict)


class PlanExecutor:
    """
    规划-执行器 - Plan-and-Execute Pattern

    先制定完整计划，再逐步执行：
    1. 分析任务，制定计划
    2. 逐步执行每个步骤
    3. 监控执行，必要时调整计划
    4. 汇总结果

    Example:
        ```python
        executor = PlanExecutor(
            agent=agent,
            allow_replan=True
        )

        result = await executor.run(message)
        ```
    """

    def __init__(
        self,
        agent: BaseAgent,
        allow_replan: bool = True,
        max_replans: int = 2,
    ):
        """
        初始化规划执行器

        Args:
            agent: Agent 实例
            allow_replan: 是否允许重新规划
            max_replans: 最大重新规划次数
        """
        self.agent = agent
        self.allow_replan = allow_replan
        self.max_replans = max_replans

        self.current_plan: Optional[Plan] = None
        self.execution_results: List[ExecutionResult] = []
        self.replan_count = 0

    async def run(self, message: Message) -> Message:
        """
        执行规划-执行循环

        Args:
            message: 输入消息

        Returns:
            最终响应
        """
        # 1. 制定计划
        self.current_plan = await self._create_plan(message.content)

        # 2. 执行计划
        for i, step in enumerate(self.current_plan.steps):
            # 执行步骤
            result = await self._execute_step(step, i)
            self.execution_results.append(result)

            # 检查是否成功
            if not result.success:
                # 失败处理
                if self.allow_replan and self.replan_count < self.max_replans:
                    # 重新规划
                    self.current_plan = await self._replan(
                        message.content,
                        failed_step=step,
                        error=result.result
                    )
                    self.replan_count += 1
                    continue
                else:
                    # 无法恢复
                    break

        # 3. 汇总结果
        return await self._summarize_results(message.content)

    async def _create_plan(self, task: str) -> Plan:
        """
        创建执行计划

        Args:
            task: 任务描述

        Returns:
            执行计划
        """
        plan_message = Message(
            role="user",
            content=f"""Create a step-by-step plan to accomplish this task:

Task: {task}

Provide a numbered list of concrete steps. Each step should be:
- Specific and actionable
- In logical order
- Clear about what needs to be done

Plan:"""
        )

        response = await self.agent.run(plan_message)

        # 解析计划
        lines = response.content.strip().split('\n')
        steps = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 移除编号
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                line = re.sub(r'^[-*]\s*', '', line)
                if line:
                    steps.append(line)

        return Plan(steps=steps)

    async def _execute_step(self, step: str, step_index: int) -> ExecutionResult:
        """
        执行单个步骤

        Args:
            step: 步骤描述
            step_index: 步骤索引

        Returns:
            执行结果
        """
        # 构建执行上下文
        context = self._build_execution_context(step_index)

        execute_message = Message(
            role="user",
            content=f"""Execute this step:

Step: {step}

Context:
{context}

Provide the result of executing this step:"""
        )

        try:
            response = await self.agent.run(execute_message)
            return ExecutionResult(
                step=step,
                result=response.content,
                success=True
            )
        except Exception as e:
            return ExecutionResult(
                step=step,
                result=str(e),
                success=False
            )

    async def _replan(
        self,
        task: str,
        failed_step: str,
        error: str
    ) -> Plan:
        """
        重新规划

        Args:
            task: 原始任务
            failed_step: 失败的步骤
            error: 错误信息

        Returns:
            新的执行计划
        """
        replan_message = Message(
            role="user",
            content=f"""The following step failed:

Step: {failed_step}
Error: {error}

Original task: {task}

Create a new plan that accounts for this failure. Provide alternative steps or workarounds.

New plan:"""
        )

        response = await self.agent.run(replan_message)

        # 解析新计划
        lines = response.content.strip().split('\n')
        steps = []

        for line in lines:
            line = line.strip()
            if line:
                import re
                line = re.sub(r'^\d+\.\s*', '', line)
                line = re.sub(r'^[-*]\s*', '', line)
                if line:
                    steps.append(line)

        return Plan(steps=steps)

    def _build_execution_context(self, current_step_index: int) -> str:
        """构建执行上下文"""
        if not self.execution_results:
            return "No previous results."

        context_lines = []
        for i, result in enumerate(self.execution_results):
            if i < current_step_index:
                context_lines.append(f"Step {i + 1}: {result.step}")
                context_lines.append(f"Result: {result.result}\n")

        return "\n".join(context_lines) if context_lines else "No previous results."

    async def _summarize_results(self, task: str) -> Message:
        """
        汇总执行结果

        Args:
            task: 原始任务

        Returns:
            汇总消息
        """
        results_text = []
        for i, result in enumerate(self.execution_results):
            status = "✓" if result.success else "✗"
            results_text.append(f"{status} Step {i + 1}: {result.step}")
            results_text.append(f"   Result: {result.result}\n")

        summary_message = Message(
            role="user",
            content=f"""Summarize the results of executing this task:

Task: {task}

Execution results:
{chr(10).join(results_text)}

Provide a concise summary and final answer:"""
        )

        return await self.agent.run(summary_message)


# ============================================================================
# 自洽性检查
# ============================================================================


class SelfConsistency:
    """
    自洽性检查 - Self-Consistency Pattern

    生成多个候选答案，通过投票或一致性检查选择最佳答案：
    1. 生成 N 个独立的候选答案
    2. 比较答案的一致性
    3. 通过投票或相似度选择最佳答案

    Example:
        ```python
        consistency = SelfConsistency(
            agent=agent,
            num_samples=5,
            selection_method="vote"
        )

        result = await consistency.run(message)
        ```
    """

    def __init__(
        self,
        agent: BaseAgent,
        num_samples: int = 5,
        selection_method: str = "vote",  # "vote" or "similarity"
    ):
        """
        初始化自洽性检查

        Args:
            agent: Agent 实例
            num_samples: 生成的样本数
            selection_method: 选择方法（"vote", "similarity"）
        """
        self.agent = agent
        self.num_samples = num_samples
        self.selection_method = selection_method

        self.samples: List[str] = []

    async def run(self, message: Message) -> Message:
        """
        执行自洽性检查

        Args:
            message: 输入消息

        Returns:
            最一致的响应
        """
        # 1. 生成多个样本
        self.samples = await self._generate_samples(message)

        # 2. 选择最佳答案
        if self.selection_method == "vote":
            best_answer = await self._vote_selection()
        elif self.selection_method == "similarity":
            best_answer = await self._similarity_selection()
        else:
            raise ValueError(f"Unknown selection method: {self.selection_method}")

        return Message(role="assistant", content=best_answer)

    async def _generate_samples(self, message: Message) -> List[str]:
        """生成多个独立样本"""
        tasks = [self.agent.run(message) for _ in range(self.num_samples)]
        responses = await asyncio.gather(*tasks)
        return [resp.content for resp in responses]

    async def _vote_selection(self) -> str:
        """投票选择"""
        # 使用 Agent 进行投票
        vote_message = Message(
            role="user",
            content=f"""Given these {self.num_samples} answers to the same question, select the most common or best answer:

{chr(10).join([f"Answer {i+1}: {sample}" for i, sample in enumerate(self.samples)])}

Which answer is most reliable? Provide the complete selected answer:"""
        )

        result = await self.agent.run(vote_message)
        return result.content

    async def _similarity_selection(self) -> str:
        """基于相似度选择"""
        # 简化实现：选择最接近平均值的答案
        # 实际实现可以使用 embedding 计算相似度
        return self.samples[len(self.samples) // 2]


# ============================================================================
# 导出
# ============================================================================


__all__ = [
    "ThinkingMode",
    "ThoughtNode",
    "ReflectionLoop",
    "TreeOfThoughts",
    "PlanExecutor",
    "SelfConsistency",
    "Plan",
    "ExecutionResult",
]
