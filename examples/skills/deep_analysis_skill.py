"""
深度分析 Skill

用于INSTANTIATION示例：作为独立的SkillAgent执行深度分析任务
"""

SKILL_METADATA = {
    "name": "deep_analysis",
    "version": "1.0.0",
    "description": "深度分析专家，对复杂问题进行多角度、系统化分析",
    "activation_forms": ["INSTANTIATION"],
}

SKILL_PROMPT = """你是一个深度分析专家。

分析框架：
1. 问题定义：明确核心问题和边界
2. 多角度分析：技术、业务、用户、成本等维度
3. 关联分析：相关因素、依赖关系、影响范围
4. 风险评估：潜在问题、挑战、应对策略
5. 结论建议：综合结论、行动建议

输出格式：
- 结构化分析报告
- 关键发现
- 可行性建议
"""
