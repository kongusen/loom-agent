"""Scene Manager for Axiom 2."""

from __future__ import annotations

import logging

from ..types.scene import ScenePackage

logger = logging.getLogger(__name__)


class SceneManager:
    """场景包管理器 - 管理 Σ 场景库"""

    def __init__(self) -> None:
        self.scenes: dict[str, ScenePackage] = {}
        self.current: ScenePackage | None = None

    def register(self, scene: ScenePackage) -> None:
        """注册场景包到 Σ"""
        self.scenes[scene.id] = scene
        logger.info(f"Scene registered: {scene.id} with {len(scene.tools)} tools")

    def switch(self, scene_id: str) -> list[str]:
        """E3: 场景切换 - 返回新场景的工具名称列表"""
        if scene_id not in self.scenes:
            raise ValueError(f"Scene '{scene_id}' not found")

        old_scene = self.current
        self.current = self.scenes[scene_id]

        logger.info(f"Scene switched: {old_scene.id if old_scene else 'None'} → {scene_id}")
        logger.info(f"Available tools: {self.current.tools}")
        return self.current.tools

    def is_tool_allowed(self, tool_name: str) -> bool:
        """P1: 检查工具是否在当前场景中"""
        if not self.current:
            return True
        return tool_name in self.current.tools

    def compose(self, scene_ids: list[str]) -> ScenePackage:
        """场景组合 σ_a ⊕ σ_b"""
        if not scene_ids:
            raise ValueError("Need at least one scene to compose")

        result = self.scenes[scene_ids[0]]
        for sid in scene_ids[1:]:
            result = result + self.scenes[sid]

        return result

    def get_tools(self) -> list[str]:
        """获取当前场景的工具名称列表"""
        return self.current.tools if self.current else []
