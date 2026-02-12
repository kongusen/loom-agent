"""
Checkpoint - Agent 检查点与恢复

为长时间运行的 Agent 任务提供断点续跑能力。

设计思路：
- 基于 StateStore 抽象，支持内存/文件/远程存储
- 每次迭代结束时自动保存检查点
- 恢复时从最近的检查点继续执行
- 检查点包含：迭代进度、记忆快照、任务状态
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.runtime.state_store import StateStore

logger = logging.getLogger(__name__)


class CheckpointStatus(Enum):
    CREATED = "created"
    VALID = "valid"
    CORRUPTED = "corrupted"
    EXPIRED = "expired"


@dataclass
class CheckpointData:
    """检查点数据"""

    agent_id: str
    task_id: str
    iteration: int
    max_iterations: int
    timestamp: float = field(default_factory=time.time)
    status: str = CheckpointStatus.CREATED.value

    # Agent 运行状态
    agent_state: dict[str, Any] = field(default_factory=dict)

    # 记忆快照（L1/L2 的序列化数据）
    memory_snapshot: dict[str, Any] = field(default_factory=dict)

    # 工具执行历史摘要
    tool_history: list[dict[str, Any]] = field(default_factory=list)

    # 上下文元数据
    context_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointData:
        status = data.pop("status", CheckpointStatus.CREATED.value)
        cp = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        cp.status = status
        return cp


class CheckpointManager:
    """
    检查点管理器

    负责检查点的创建、保存、加载和清理。

    用法：
        store = MemoryStateStore()
        mgr = CheckpointManager(store)

        # 保存检查点
        await mgr.save(CheckpointData(
            agent_id="agent-1", task_id="task-1",
            iteration=5, max_iterations=30,
        ))

        # 恢复最近的检查点
        cp = await mgr.load_latest("agent-1", "task-1")
        if cp:
            print(f"从迭代 {cp.iteration} 恢复")

        # 清理过期检查点
        await mgr.cleanup("agent-1", keep_last=3)
    """

    KEY_PREFIX = "checkpoint"

    def __init__(
        self,
        store: StateStore,
        max_checkpoints: int = 10,
        auto_validate: bool = True,
    ):
        """
        Args:
            store: 状态存储后端
            max_checkpoints: 每个 agent+task 最多保留的检查点数
            auto_validate: 加载时是否自动验证
        """
        self._store = store
        self._max_checkpoints = max_checkpoints
        self._auto_validate = auto_validate

    def _key(self, agent_id: str, task_id: str, iteration: int) -> str:
        return f"{self.KEY_PREFIX}:{agent_id}:{task_id}:{iteration:06d}"

    def _prefix(self, agent_id: str, task_id: str = "") -> str:
        if task_id:
            return f"{self.KEY_PREFIX}:{agent_id}:{task_id}:"
        return f"{self.KEY_PREFIX}:{agent_id}:"

    async def save(self, checkpoint: CheckpointData) -> None:
        """保存检查点"""
        checkpoint.status = CheckpointStatus.VALID.value
        key = self._key(checkpoint.agent_id, checkpoint.task_id, checkpoint.iteration)
        await self._store.save(key, checkpoint.to_dict())
        logger.debug(
            "Checkpoint saved: %s iteration=%d", key, checkpoint.iteration,
        )
        # 自动清理超出限制的旧检查点
        await self.cleanup(
            checkpoint.agent_id, checkpoint.task_id,
            keep_last=self._max_checkpoints,
        )

    async def load_latest(
        self, agent_id: str, task_id: str,
    ) -> CheckpointData | None:
        """加载最近的有效检查点"""
        keys = await self._store.list_keys(self._prefix(agent_id, task_id))
        if not keys:
            return None

        # 按 key 排序（iteration 部分是零填充的，天然有序）
        keys.sort(reverse=True)

        for key in keys:
            data = await self._store.get(key)
            if data is None:
                continue
            try:
                cp = CheckpointData.from_dict(dict(data))
            except (KeyError, TypeError):
                logger.warning("Corrupted checkpoint: %s", key)
                continue

            if self._auto_validate and not self._validate(cp):
                continue
            return cp

        return None

    async def load(
        self, agent_id: str, task_id: str, iteration: int,
    ) -> CheckpointData | None:
        """加载指定迭代的检查点"""
        key = self._key(agent_id, task_id, iteration)
        data = await self._store.get(key)
        if data is None:
            return None
        try:
            return CheckpointData.from_dict(dict(data))
        except (KeyError, TypeError):
            logger.warning("Corrupted checkpoint: %s", key)
            return None

    async def cleanup(
        self, agent_id: str, task_id: str, keep_last: int = 3,
    ) -> int:
        """
        清理旧检查点，只保留最近 N 个

        Returns:
            删除的检查点数量
        """
        keys = await self._store.list_keys(self._prefix(agent_id, task_id))
        if len(keys) <= keep_last:
            return 0

        keys.sort()
        to_delete = keys[: len(keys) - keep_last]
        for key in to_delete:
            await self._store.delete(key)

        if to_delete:
            logger.debug("Cleaned up %d old checkpoints", len(to_delete))
        return len(to_delete)

    async def delete_all(self, agent_id: str, task_id: str) -> int:
        """删除某个 agent+task 的所有检查点"""
        keys = await self._store.list_keys(self._prefix(agent_id, task_id))
        for key in keys:
            await self._store.delete(key)
        return len(keys)

    async def list_checkpoints(
        self, agent_id: str, task_id: str,
    ) -> list[int]:
        """列出所有检查点的迭代号"""
        keys = await self._store.list_keys(self._prefix(agent_id, task_id))
        iterations = []
        for key in keys:
            parts = key.rsplit(":", 1)
            if len(parts) == 2:
                try:
                    iterations.append(int(parts[1]))
                except ValueError:
                    continue
        iterations.sort()
        return iterations

    @staticmethod
    def _validate(cp: CheckpointData) -> bool:
        """验证检查点数据完整性"""
        if not cp.agent_id or not cp.task_id:
            return False
        if cp.iteration < 0:
            return False
        return cp.status != CheckpointStatus.CORRUPTED.value
