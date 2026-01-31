"""
A5: 认知调度公理 (Cognitive Orchestration Axiom)

公理陈述：Cognition = Orchestration(N1, N2, ..., Nk)

本模块实现不同的编排模式，通过节点间的协作涌现认知。

导出内容：
- Workflow: 工作流抽象基类
- SequentialWorkflow: 固定流程工作流
- AgentWorkflow: 动态流程工作流
- Orchestrator: 编排器抽象基类
- RouterOrchestrator: 路由编排器（智能路由）
- CrewOrchestrator: 团队编排器（多节点协作）
- PipelineBuilder: 流水线构建器（顺序/并行/条件执行）
"""

# Orchestration-specific imports
from loom.orchestration.agent_workflow import AgentWorkflow
from loom.orchestration.base import Orchestrator
from loom.orchestration.crew import CrewOrchestrator
from loom.orchestration.pipeline_builder import PipelineBuilder
from loom.orchestration.router import RouterOrchestrator
from loom.orchestration.sequential_workflow import SequentialWorkflow
from loom.orchestration.workflow import Workflow

__all__ = [
    "Workflow",
    "SequentialWorkflow",
    "AgentWorkflow",
    "Orchestrator",
    "RouterOrchestrator",
    "CrewOrchestrator",
    "PipelineBuilder",
]
