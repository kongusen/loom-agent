"""Q1: LLM Self-Perception Reliability

问题: LLM 在 goal_progress 上的自评是否可靠？长任务末期是否会系统性高估完成度？
观测现象: 模型在任务未完成时给出高完成度描述
实验设计: 多阶段任务，对比模型自评与客观完成度
证据要求: transcript、checklist、goal_progress 时间序列、偏差统计
"""

from loom.agent.runtime import AgentRuntime
from loom.types.state import WorkingState

# 实验：构造多阶段任务，跟踪自评偏差
async def experiment_self_perception():
    runtime = AgentRuntime()

    # 定义可验证的子里程碑
    milestones = [
        {"id": 1, "desc": "读取配置文件", "objective_complete": False},
        {"id": 2, "desc": "解析数据结构", "objective_complete": False},
        {"id": 3, "desc": "生成输出文件", "objective_complete": False},
        {"id": 4, "desc": "验证结果正确性", "objective_complete": False},
    ]

    evidence = []

    async for step in runtime.run("完成数据处理任务"):
        # 收集模型自评
        self_reported = step.working_state.dashboard.goal_progress

        # 客观验证完成度
        objective_progress = sum(m["objective_complete"] for m in milestones) / len(milestones)

        # 记录偏差
        bias = self_reported - objective_progress
        evidence.append({
            "step": step.step_num,
            "self_reported": self_reported,
            "objective": objective_progress,
            "bias": bias
        })

    return evidence

# 分析偏差趋势
def analyze_bias(evidence):
    late_stage = [e for e in evidence if e["objective"] > 0.7]
    return sum(e["bias"] for e in late_stage) / len(late_stage) if late_stage else 0
