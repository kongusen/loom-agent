"""测试 P1 Harness 反馈回路优化."""

import pytest

from loom.cluster.reward import RewardBus
from loom.evolution.engine import EvolutionEngine
from loom.types import AgentNode, CapabilityProfile
from loom.types.evolution import Pattern

# ── RewardBus 步骤级反馈测试 ──


def test_reward_bus_step_evaluation():
    """测试步骤级即时反馈."""
    bus = RewardBus()
    node = AgentNode(
        id="test",
        depth=0,
        capabilities=CapabilityProfile(tools=[]),
    )

    # 成功的工具调用
    step_result = {"tool_success": True, "output_tokens": 100, "input_tokens": 50}
    score = bus.evaluate_step(node, step_result)

    assert score > 0
    assert hasattr(node.capabilities, "step_score")
    assert node.capabilities.step_score > 0


def test_reward_bus_step_efficiency():
    """测试 Token 效率计算."""
    bus = RewardBus()
    node = AgentNode(
        id="test",
        depth=0,
        capabilities=CapabilityProfile(tools=[]),
    )

    # 高效率
    step_result = {"tool_success": True, "output_tokens": 200, "input_tokens": 100}
    score1 = bus.evaluate_step(node, step_result)

    # 低效率
    step_result = {"tool_success": True, "output_tokens": 10, "input_tokens": 100}
    score2 = bus.evaluate_step(node, step_result)

    assert score1 > score2


# ── EvolutionEngine 预测性结晶测试 ──


@pytest.mark.asyncio
async def test_evolution_adaptive_crystallize():
    """测试预测性技能结晶."""
    engine = EvolutionEngine(theta_crystal=3, tau_skill=0.8)

    # 添加高置信度模式（频率低但成功率高）
    engine.patterns["high_conf"] = Pattern(
        name="high_conf", frequency=2, success_rate=0.95, steps=["step1", "step2"]
    )

    # 添加低置信度模式（频率高但成功率低）
    engine.patterns["low_conf"] = Pattern(
        name="low_conf", frequency=5, success_rate=0.7, steps=["step1"]
    )

    # 自适应结晶
    skills = await engine.e2_crystallize_adaptive()

    # 高置信度模式应该被结晶（即使频率 < 3）
    assert len(skills) > 0
    assert any("high_conf" in s.name for s in skills)


@pytest.mark.asyncio
async def test_evolution_adaptive_threshold():
    """测试动态阈值计算."""
    engine = EvolutionEngine(theta_crystal=3, tau_skill=0.8)

    # 低频高质量模式
    engine.patterns["quality"] = Pattern(
        name="quality", frequency=2, success_rate=1.0, steps=["step1"]
    )

    skills = await engine.e2_crystallize_adaptive()

    # 应该通过动态阈值结晶
    assert len(skills) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
