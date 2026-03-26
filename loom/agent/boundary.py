"""边界检测和响应 - Axiom 2 边界条件模型"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .core import Agent

class BoundaryType(Enum):
    """边界类型（简化为 4 类）"""
    PHYSICAL = "physical"      # token/memory 耗尽
    PERMISSION = "permission"  # 缺少权限
    CAPABILITY = "capability"  # 超出能力
    TIME = "time"              # 超时


class BoundaryResponse(Enum):
    """边界响应策略"""
    RENEW = "renew"           # 压缩继续
    WAIT = "wait"             # 等待输入
    HANDOFF = "handoff"       # 转交
    DECOMPOSE = "decompose"   # 拆解
    STOP = "stop"             # 终止


class BoundaryDetector:
    """边界检测器"""

    def __init__(self, partition_mgr, resource_guard, scene_mgr):
        self.partition_mgr = partition_mgr
        self.guard = resource_guard
        self.scene_mgr = scene_mgr

    def detect(self) -> Optional[tuple[BoundaryType, dict]]:
        """检测是否触及边界"""

        # 物理边界：上下文压力
        if self.partition_mgr.compute_decay() > 0.9:
            return (BoundaryType.PHYSICAL, {"reason": "context_full", "decay": self.partition_mgr.compute_decay()})

        # 物理边界：资源配额
        within_quota, msg = self.guard.check_quota()
        if not within_quota:
            return (BoundaryType.PHYSICAL, {"reason": msg})

        # 时间边界
        if self.guard._start_time > 0:
            import time
            elapsed = time.time() - self.guard._start_time
            if elapsed > self.guard._max_time:
                return (BoundaryType.TIME, {"reason": "timeout", "elapsed": elapsed})

        return None


class BoundaryHandler:
    """边界响应处理器"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.policy = self._default_policy()

    def _default_policy(self) -> dict[BoundaryType, list[BoundaryResponse]]:
        """默认响应策略"""
        return {
            BoundaryType.PHYSICAL: [BoundaryResponse.RENEW, BoundaryResponse.STOP],
            BoundaryType.PERMISSION: [BoundaryResponse.WAIT, BoundaryResponse.HANDOFF],
            BoundaryType.CAPABILITY: [BoundaryResponse.DECOMPOSE, BoundaryResponse.HANDOFF],
            BoundaryType.TIME: [BoundaryResponse.STOP, BoundaryResponse.HANDOFF],
        }

    async def handle(self, boundary_type: BoundaryType, context: dict) -> BoundaryResponse:
        """处理边界触发"""
        responses = self.policy.get(boundary_type, [BoundaryResponse.STOP])

        # 简单策略：选择第一个可用响应
        for response in responses:
            if response == BoundaryResponse.RENEW:
                if await self._can_renew():
                    await self._do_renew()
                    return response
            elif response == BoundaryResponse.STOP:
                return response

        return BoundaryResponse.STOP

    async def _can_renew(self) -> bool:
        """检查是否可以续存"""
        return self.agent.partition_mgr.compute_decay() < 1.0

    async def _do_renew(self):
        """执行续存操作"""
        await self.agent._trigger_compression()
