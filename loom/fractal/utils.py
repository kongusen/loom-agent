"""
分形工具集 (Fractal Utilities)

基于递归状态机设计的分形决策工具。

核心功能：
- 任务复杂度评估
- 分形分解决策

基于 A3 公理：分形自相似公理
运行时递归 = 节点递归，不需要手动实现递归逻辑。
"""

from loom.config import FractalConfig, GrowthTrigger


def estimate_task_complexity(task: str) -> float:
    """
    估算任务复杂度 (0-1)

    基于以下启发式规则：
    - 任务描述长度
    - 连接词数量 (and, or, then 等)
    - 步骤指示词 (step, phase, first 等)

    Args:
        task: 任务描述字符串

    Returns:
        复杂度分数，范围 0.0-1.0
    """
    task_lower = task.lower()

    # 长度分数
    length_score = min(1.0, len(task) / 1000)

    # 连接词计数
    conjunctions = ["and", "or", "then", "after", "before", "while"]
    conjunction_count = sum(task_lower.count(c) for c in conjunctions)
    conjunction_score = min(1.0, conjunction_count / 5)

    # 步骤指示词
    step_keywords = ["step", "phase", "first", "second", "finally", "component"]
    step_count = sum(task_lower.count(k) for k in step_keywords)
    step_score = min(1.0, step_count / 3)

    # 加权平均
    return length_score * 0.3 + conjunction_score * 0.4 + step_score * 0.3


def should_use_fractal(task: str, config: FractalConfig) -> bool:
    """
    判断是否应该使用分形分解

    基于任务复杂度和配置决定是否使用分形分解。
    符合分形自相似原则:判断只依赖任务本身,不依赖外部路由决策。

    Args:
        task: 任务描述
        config: 分形配置

    Returns:
        True 表示应该使用分形分解
    """
    if not config or not config.enabled:
        return False

    trigger = config.growth_trigger

    # 永不使用分形
    if trigger == GrowthTrigger.NEVER:
        return False

    # 总是使用分形
    if trigger == GrowthTrigger.ALWAYS:
        return True

    # 仅手动触发（不自动触发）
    if trigger == GrowthTrigger.MANUAL:
        return False

    # 基于复杂度触发
    if trigger == GrowthTrigger.COMPLEXITY:
        complexity = estimate_task_complexity(task)
        return complexity > config.complexity_threshold

    return False
