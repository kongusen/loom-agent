"""测试 Scene 组合的约束收窄"""

import pytest

from loom.types.scene import ScenePackage


class TestSceneComposition:
    """验证场景组合时约束正确收窄"""

    def test_boolean_constraints_use_and_logic(self):
        """布尔约束：两者都允许才允许"""
        scene1 = ScenePackage(
            id="s1",
            tools=["read"],
            constraints={"network": True, "write": True}
        )
        scene2 = ScenePackage(
            id="s2",
            tools=["write"],
            constraints={"network": False, "write": True}
        )

        combined = scene1 + scene2

        # network: True AND False = False (更严格)
        assert combined.constraints["network"] is False
        # write: True AND True = True
        assert combined.constraints["write"] is True

    def test_numeric_constraints_use_min(self):
        """数值约束：取更小的限制"""
        scene1 = ScenePackage(
            id="s1",
            tools=["read"],
            constraints={"max_tokens": 1000, "timeout": 30}
        )
        scene2 = ScenePackage(
            id="s2",
            tools=["write"],
            constraints={"max_tokens": 500, "timeout": 60}
        )

        combined = scene1 + scene2

        # 取更小的限制
        assert combined.constraints["max_tokens"] == 500
        assert combined.constraints["timeout"] == 30

    def test_list_constraints_use_intersection(self):
        """列表约束：取交集"""
        scene1 = ScenePackage(
            id="s1",
            tools=["read"],
            constraints={"allowed_domains": ["a.com", "b.com", "c.com"]}
        )
        scene2 = ScenePackage(
            id="s2",
            tools=["write"],
            constraints={"allowed_domains": ["b.com", "c.com", "d.com"]}
        )

        combined = scene1 + scene2

        # 取交集
        assert set(combined.constraints["allowed_domains"]) == {"b.com", "c.com"}

    def test_tools_use_union(self):
        """工具列表：取并集"""
        scene1 = ScenePackage(id="s1", tools=["read", "write"])
        scene2 = ScenePackage(id="s2", tools=["write", "bash"])

        combined = scene1 + scene2

        # 工具取并集
        assert set(combined.tools) == {"read", "write", "bash"}

    def test_one_sided_constraints(self):
        """单侧约束：保留存在的约束"""
        scene1 = ScenePackage(
            id="s1",
            tools=["read"],
            constraints={"network": True}
        )
        scene2 = ScenePackage(
            id="s2",
            tools=["write"],
            constraints={"write": False}
        )

        combined = scene1 + scene2

        # 两个约束都保留
        assert combined.constraints["network"] is True
        assert combined.constraints["write"] is False
