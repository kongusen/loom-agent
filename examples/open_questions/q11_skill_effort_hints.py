"""Q11: Skill Effort Hints Quantification

问题: Skill frontmatter 中的 effort: high 应如何转化为资源分配决策？
观测现象: effort hint 与实际资源差异不稳定
实验设计: 配置不同 effort hints，比较执行时长、token 消耗、工具调用深度
证据要求: Skill 配置、资源日志、执行统计、质量对比
"""

from loom.tools.registry import SkillRegistry

async def experiment_effort_hints():
    registry = SkillRegistry()

    # 同类任务，不同 effort 配置
    configs = [
        {"name": "task_low", "effort": "low", "timeout": 30, "token_budget": 1000},
        {"name": "task_medium", "effort": "medium", "timeout": 60, "token_budget": 3000},
        {"name": "task_high", "effort": "high", "timeout": 120, "token_budget": 8000},
    ]

    results = []
    for config in configs:
        skill = registry.load_skill(config["name"])

        metrics = await skill.execute_with_tracking()
        results.append({
            "effort": config["effort"],
            "duration": metrics.duration,
            "tokens": metrics.token_count,
            "tool_calls": metrics.tool_depth,
            "quality": metrics.result_quality
        })

    return results
