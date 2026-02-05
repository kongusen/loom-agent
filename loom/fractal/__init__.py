"""
A3: 分形自相似公理 (Fractal Self-Similarity Axiom)

公理陈述：∀node ∈ System: structure(node) ≅ structure(System)

基于递归状态机设计：运行时递归 = 节点递归

本模块提供分形能力的核心组件：
- NodeContainer: 节点容器（支持递归组合）
- ResultSynthesizer: 结果合成器（智能合成子任务结果）
- ParallelExecutor: 并行执行器（多Agent并行执行和SSE汇聚）

Phase 5: 预算控制系统已移除，只保留核心分形组件。

设计理念：
利用 Claude Code 的原生递归能力，而不是手动实现递归逻辑。
分形分解通过 LLM 推理和 Task tool 递归调用实现。
"""

from loom.fractal.container import NodeContainer
from loom.fractal.parallel_executor import ParallelExecutor, ParallelResult, ParallelTask
from loom.fractal.synthesizer import ResultSynthesizer

__all__ = [
    "NodeContainer",
    "ResultSynthesizer",
    "ParallelExecutor",
    "ParallelTask",
    "ParallelResult",
]

