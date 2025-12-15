"""
Coordination - 智能任务协调和分解机制

包含：
- SmartCoordinator: 智能任务分解器
- ComplexityAnalyzer: 任务复杂度分析器
- TaskDecomposition: 任务分解结果

基于 Anthropic 的 Multi-Agent 最佳实践。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any

from loom.core.base_agent import BaseAgent
from loom.core.message import Message
from loom.interfaces.llm import BaseLLM


class TaskComplexity(str, Enum):
    """任务复杂度等级"""

    SIMPLE = "simple"  # 1 agent, 3-10 tool calls
    MEDIUM = "medium"  # 2-4 agents, 10-15 tool calls each
    COMPLEX = "complex"  # 10+ agents, detailed division of labor


@dataclass
class SubTask:
    """子任务定义"""

    id: str
    agent: str  # agent name
    task: str  # 详细任务描述
    depends_on: List[str] = field(default_factory=list)  # 依赖的任务 ID
    output_format: Optional[str] = None  # 输出格式要求
    tool_guide: Optional[str] = None  # 工具使用指南
    resource_scope: Optional[str] = None  # 资源范围
    boundaries: Optional[str] = None  # 任务边界
    quality_standards: Optional[str] = None  # 质量标准
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于 JSON）"""
        return {
            "id": self.id,
            "agent": self.agent,
            "task": self.task,
            "depends_on": self.depends_on,
            "output_format": self.output_format,
            "tool_guide": self.tool_guide,
            "resource_scope": self.resource_scope,
            "boundaries": self.boundaries,
            "quality_standards": self.quality_standards,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubTask:
        """从字典反序列化"""
        return cls(
            id=data["id"],
            agent=data["agent"],
            task=data["task"],
            depends_on=data.get("depends_on", []),
            output_format=data.get("output_format"),
            tool_guide=data.get("tool_guide"),
            resource_scope=data.get("resource_scope"),
            boundaries=data.get("boundaries"),
            quality_standards=data.get("quality_standards"),
        )


@dataclass
class TaskDecomposition:
    """任务分解结果"""

    complexity: TaskComplexity
    subtasks: List[SubTask]
    reasoning: str  # 分解理由
    estimated_agents: int  # 预估需要的 agent 数量
    metadata: Dict[str, Any] = field(default_factory=dict)


class ComplexityAnalyzer:
    """
    任务复杂度分析器

    自动判断任务复杂度并推荐 agent 数量。

    判断依据：
    - SIMPLE: 单一事实查询、直接比较
    - MEDIUM: 多维度对比、需要 2-4 个数据源
    - COMPLEX: 开放性研究、需要深度分析
    """

    # 复杂度分析提示模板
    ANALYSIS_TEMPLATE = """分析以下任务的复杂度：

任务: {task}

复杂度分类规则：

1. **简单 (SIMPLE)** - 1个agent，3-10次工具调用：
   特征：
   - 单一事实查询（"特斯拉股价"，"谁是现任CEO"）
   - 直接信息检索（"Python官方文档地址"）
   - 简单计算或转换

2. **中等 (MEDIUM)** - 2-4个agent，每个10-15次调用：
   特征：
   - 多维度对比（"比较特斯拉vs比亚迪的市场策略"）
   - 需要综合2-4个数据源
   - 中等规模分析（"分析2024年电动车销量趋势"）

3. **复杂 (COMPLEX)** - 10+个agent，明确分工：
   特征：
   - 开放性研究（"分析全球电动车市场的竞争格局和未来趋势"）
   - 需要深度多角度分析
   - 涉及多个领域或维度
   - 需要综合大量数据源

请分析上述任务并返回 JSON：
{{
    "complexity": "simple|medium|complex",
    "reasoning": "详细说明为什么是这个复杂度...",
    "estimated_agents": <数字>,
    "estimated_tool_calls": <数字>,
    "key_challenges": ["挑战1", "挑战2"]
}}

只返回 JSON，不要其他内容。"""

    def __init__(self, llm: BaseLLM):
        """
        初始化复杂度分析器

        Args:
            llm: 用于分析的语言模型
        """
        self.llm = llm

    async def analyze(self, task: str) -> TaskComplexity:
        """
        分析任务复杂度

        Args:
            task: 任务描述

        Returns:
            TaskComplexity: 复杂度等级
        """
        prompt = self.ANALYSIS_TEMPLATE.format(task=task)
        messages = [Message(role="user", content=prompt)]

        # 调用 LLM 分析
        response = await self.llm.generate(messages)

        # 解析结果
        try:
            # 提取 JSON
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            result = json.loads(content)
            complexity_str = result.get("complexity", "medium")

            # 转换为枚举
            if complexity_str == "simple":
                return TaskComplexity.SIMPLE
            elif complexity_str == "complex":
                return TaskComplexity.COMPLEX
            else:
                return TaskComplexity.MEDIUM

        except Exception:
            # 解析失败，默认中等复杂度
            return TaskComplexity.MEDIUM

    async def analyze_detailed(self, task: str) -> Dict[str, Any]:
        """
        详细分析任务复杂度（返回完整信息）

        Args:
            task: 任务描述

        Returns:
            完整的分析结果字典
        """
        prompt = self.ANALYSIS_TEMPLATE.format(task=task)
        messages = [Message(role="user", content=prompt)]

        response = await self.llm.generate(messages)

        try:
            content = response.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            return json.loads(content)
        except Exception:
            # 解析失败，返回默认值
            return {
                "complexity": "medium",
                "reasoning": "分析失败，使用默认复杂度",
                "estimated_agents": 3,
                "estimated_tool_calls": 30,
                "key_challenges": [],
            }


class SmartCoordinator:
    """
    智能任务协调器

    特性：
    - 使用详细的任务分解模板（防止模糊指令）
    - 自动去重检测
    - 复杂度评估
    - 自动缩放 agent 数量

    基于 Anthropic 的 Multi-Agent 最佳实践。
    """

    # 详细的任务分解提示模板
    DELEGATION_TEMPLATE = """你是一个任务协调专家，负责将复杂任务分解为详细的子任务。

## 可用的 Agents：
{agent_info}

## 主任务：
{task}

## 任务复杂度评估：
- 复杂度: {complexity}
- 推荐 agent 数量: {estimated_agents}
- 分析理由: {reasoning}

## 任务分解要求：

每个子任务必须包含以下 6 个要素（避免模糊指令）：

1. **明确目标** (task): 具体要回答什么问题或完成什么工作
2. **输出格式** (output_format): 返回 JSON/Markdown/列表等，包含哪些字段
3. **工具指南** (tool_guide): 优先使用哪些工具，为什么，如何使用
4. **资源范围** (resource_scope): 搜索时间范围、地理范围、数据源等
5. **任务边界** (boundaries): 不要做什么，避免与其他子 agent 重复
6. **质量标准** (quality_standards): 来源可靠性、数据新鲜度要求

## 错误示例：
❌ "研究半导体短缺" （太模糊）

## 正确示例：
✅ {{
    "id": "task1",
    "agent": "market_researcher",
    "task": "研究2024年汽车行业的半导体短缺情况，找出受影响最大的3家车企及其产量损失",
    "output_format": "JSON格式，包含 [{{'company': '公司名', 'loss_percentage': 数字, 'source': '数据来源URL'}}]",
    "tool_guide": "优先使用 web_search 找行业报告（如Gartner、IHS），避免用 news_search（太碎片）。搜索关键词：'automotive semiconductor shortage 2024 production loss'",
    "resource_scope": "仅2024年数据，聚焦美国和欧洲市场，使用权威行业报告",
    "boundaries": "不要研究芯片制造商（由task2负责），不要分析历史趋势（由task3负责）",
    "quality_standards": "必须引用权威来源（财报、行业协会报告），数据发布时间不超过3个月",
    "depends_on": []
}}

## 依赖关系规则：
- 如果任务B需要任务A的结果，则 B.depends_on = ["task_a_id"]
- 无依赖的任务可以并行执行
- 避免循环依赖

## 去重要求：
- 检查是否有重复或重叠的子任务
- 确保每个子任务有明确的边界
- 避免多个 agent 做相同的工作

请将主任务分解为 {estimated_agents} 个左右的子任务，返回 JSON 数组：

[
  {{
    "id": "task1",
    "agent": "agent_name",
    "task": "详细任务描述",
    "output_format": "输出格式",
    "tool_guide": "工具使用指南",
    "resource_scope": "资源范围",
    "boundaries": "任务边界",
    "quality_standards": "质量标准",
    "depends_on": []
  }},
  ...
]

只返回 JSON 数组，不要markdown代码块，不要其他解释。"""

    def __init__(
        self,
        base_agent: BaseAgent,
        complexity_analyzer: Optional[ComplexityAnalyzer] = None,
        detect_duplicate_tasks: bool = True,
        auto_scale_agents: bool = True,
    ):
        """
        初始化智能协调器

        Args:
            base_agent: 用作协调器的 agent
            complexity_analyzer: 复杂度分析器（可选）
            detect_duplicate_tasks: 是否检测重复任务
            auto_scale_agents: 是否自动缩放 agent 数量
        """
        self.base_agent = base_agent
        self.complexity_analyzer = complexity_analyzer
        self.detect_duplicate_tasks = detect_duplicate_tasks
        self.auto_scale_agents = auto_scale_agents

    async def decompose_task(
        self,
        task: str,
        available_agents: List[BaseAgent],
    ) -> TaskDecomposition:
        """
        智能分解任务

        Args:
            task: 主任务描述
            available_agents: 可用的 agent 列表

        Returns:
            TaskDecomposition: 任务分解结果
        """
        # 1. 分析任务复杂度
        if self.complexity_analyzer and self.auto_scale_agents:
            analysis = await self.complexity_analyzer.analyze_detailed(task)
            complexity = TaskComplexity(analysis.get("complexity", "medium"))
            estimated_agents = analysis.get("estimated_agents", len(available_agents))
            reasoning = analysis.get("reasoning", "")
        else:
            complexity = TaskComplexity.MEDIUM
            estimated_agents = len(available_agents)
            reasoning = "未进行复杂度分析"

        # 2. 构建 agent 信息
        agent_info = self._format_agent_info(available_agents)

        # 3. 使用详细模板生成子任务
        prompt = self.DELEGATION_TEMPLATE.format(
            agent_info=agent_info,
            task=task,
            complexity=complexity.value,
            estimated_agents=min(estimated_agents, len(available_agents)),
            reasoning=reasoning,
        )

        # 4. 调用协调器 LLM
        response = await self.base_agent.run(prompt)

        # 5. 解析子任务
        subtasks = self._parse_subtasks(response)

        # 6. 去重检测（如果启用）
        if self.detect_duplicate_tasks and subtasks:
            subtasks = self._deduplicate_tasks(subtasks)

        # 7. 返回分解结果
        return TaskDecomposition(
            complexity=complexity,
            subtasks=subtasks,
            reasoning=reasoning,
            estimated_agents=estimated_agents,
            metadata={
                "original_task": task,
                "available_agents": len(available_agents),
            },
        )

    def _format_agent_info(self, agents: List[BaseAgent]) -> str:
        """格式化 agent 信息"""
        lines = []
        for agent in agents:
            # 获取 agent 的系统提示或描述
            system_prompt = getattr(agent, "system_prompt", None)
            if system_prompt:
                desc = system_prompt[:100]  # 截取前100字符
            else:
                desc = "General purpose agent"

            # 获取工具列表
            tools = getattr(agent, "tools", [])
            if tools:
                tool_names = ", ".join([t.name for t in tools])
                lines.append(f"- **{agent.name}**: {desc} (工具: {tool_names})")
            else:
                lines.append(f"- **{agent.name}**: {desc}")

        return "\n".join(lines)

    def _parse_subtasks(self, response: str) -> List[SubTask]:
        """
        解析子任务 JSON

        Args:
            response: LLM 返回的响应

        Returns:
            SubTask 列表
        """
        try:
            # 提取 JSON（可能被包裹在 markdown 中）
            content = response.strip()

            # 移除 markdown 代码块
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            # 解析 JSON
            data = json.loads(content)

            if not isinstance(data, list):
                return []

            # 转换为 SubTask 对象
            subtasks = []
            for item in data:
                if all(key in item for key in ["id", "agent", "task"]):
                    subtask = SubTask(
                        id=item["id"],
                        agent=item["agent"],
                        task=item["task"],
                        depends_on=item.get("depends_on", []),
                        output_format=item.get("output_format"),
                        tool_guide=item.get("tool_guide"),
                        resource_scope=item.get("resource_scope"),
                        boundaries=item.get("boundaries"),
                        quality_standards=item.get("quality_standards"),
                    )
                    subtasks.append(subtask)

            return subtasks

        except Exception as e:
            # 解析失败
            return []

    def _deduplicate_tasks(self, subtasks: List[SubTask]) -> List[SubTask]:
        """
        检测并去除重复任务

        使用多层策略：
        1. 完全相同的描述 → 直接去重
        2. 高度相似的描述（85%+相似度）→ 合并
        3. 相同Agent+相似任务 → 去重
        """
        if not subtasks or len(subtasks) <= 1:
            return subtasks

        unique_subtasks = []
        seen_exact = set()  # 完全相同的任务

        for subtask in subtasks:
            # 层级1：完全相同检查
            task_key = (subtask.agent, subtask.task.lower().strip())
            if task_key in seen_exact:
                continue  # 跳过重复任务

            # 层级2：相似度检查（与已有任务对比）
            is_duplicate = False
            for existing in unique_subtasks:
                # 只对比同一个 Agent 的任务
                if existing.agent == subtask.agent:
                    similarity = self._calculate_similarity(
                        existing.task, subtask.task
                    )
                    # 相似度 > 85% 认为是重复
                    if similarity > 0.85:
                        is_duplicate = True
                        break

            if not is_duplicate:
                seen_exact.add(task_key)
                unique_subtasks.append(subtask)

        removed_count = len(subtasks) - len(unique_subtasks)
        if removed_count > 0:
            print(f"[去重检测] 移除了 {removed_count} 个重复任务")

        return unique_subtasks

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（简化版）

        使用 Jaccard 相似度（基于词集合）

        Returns:
            0.0-1.0 的相似度分数
        """
        # 转换为小写并分词
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Jaccard 相似度 = 交集 / 并集
        if not words1 and not words2:
            return 1.0  # 都为空视为完全相同
        if not words1 or not words2:
            return 0.0  # 一个为空视为完全不同

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"SmartCoordinator("
            f"coordinator={self.base_agent.name}, "
            f"auto_scale={self.auto_scale_agents}, "
            f"detect_duplicates={self.detect_duplicate_tasks})"
        )


__all__ = [
    "TaskComplexity",
    "SubTask",
    "TaskDecomposition",
    "ComplexityAnalyzer",
    "SmartCoordinator",
]
