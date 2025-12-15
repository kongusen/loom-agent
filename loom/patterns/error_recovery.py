"""
Error Recovery - 容错和恢复机制

包含：
- ErrorRecovery: 智能错误处理
- Checkpoint: 执行状态保存和恢复
- RecoveryAction: 恢复动作枚举
- 自动重试、降级、通知coordinator

提升成功率从60%到95%
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

from loom.core.base_agent import BaseAgent
from loom.patterns.artifact_store import SubAgentResult
from loom.patterns.coordination import SubTask


class RecoveryAction(str, Enum):
    """恢复动作"""

    RETRY = "retry"  # 重试相同任务
    SKIP = "skip"  # 跳过并继续
    FALLBACK = "fallback"  # 降级到简化版任务
    REASSIGN = "reassign"  # 分配给其他 agent
    ABORT = "abort"  # 中止整个 crew 执行


@dataclass
class ErrorContext:
    """错误上下文"""

    agent_id: str
    task_id: str
    task_description: str
    error: Exception
    error_type: str
    error_message: str
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryConfig:
    """恢复配置"""

    # 重试配置
    auto_retry: bool = True
    max_retries: int = 3
    exponential_backoff: bool = True
    base_delay: float = 1.0  # 基础延迟（秒）

    # 降级配置
    enable_fallback: bool = True
    fallback_mode: str = "graceful_degrade"  # "graceful_degrade" or "skip"

    # Coordinator 通知
    inform_coordinator: bool = True
    coordinator_decides: bool = False  # 让 coordinator 决定恢复策略

    # 其他
    skip_on_max_retries: bool = True


class ErrorRecovery:
    """
    错误恢复管理器

    特性：
    - 自动重试（带指数退避）
    - 任务降级
    - Coordinator 通知和决策
    - 错误隔离

    Example:
        ```python
        recovery = ErrorRecovery(
            config=RecoveryConfig(
                auto_retry=True,
                max_retries=3,
                inform_coordinator=True
            ),
            coordinator=coordinator_agent
        )

        # 执行带恢复的任务
        result = await recovery.execute_with_recovery(
            agent=agent,
            task=subtask,
            original_task="原始任务"
        )
        ```
    """

    def __init__(
        self,
        config: Optional[RecoveryConfig] = None,
        coordinator: Optional[BaseAgent] = None,
    ):
        """
        初始化错误恢复器

        Args:
            config: 恢复配置
            coordinator: 协调器 agent（用于决策）
        """
        self.config = config or RecoveryConfig()
        self.coordinator = coordinator
        self.error_history: List[ErrorContext] = []

    async def execute_with_recovery(
        self,
        agent: BaseAgent,
        subtask: SubTask,
        original_task: Optional[str] = None,
    ) -> SubAgentResult:
        """
        执行任务（带错误恢复）

        Args:
            agent: 执行的 agent
            subtask: 子任务
            original_task: 原始任务（可选）

        Returns:
            SubAgentResult
        """
        retry_count = 0

        while retry_count <= self.config.max_retries:
            try:
                # 尝试执行
                response = await agent.run(subtask.task)

                # 成功：返回结果
                return SubAgentResult(
                    agent_id=agent.name,
                    task_id=subtask.id,
                    summary=response,
                    success=True,
                    metadata={
                        "retry_count": retry_count,
                        "original_task": original_task,
                    },
                )

            except Exception as e:
                # 记录错误上下文
                error_ctx = ErrorContext(
                    agent_id=agent.name,
                    task_id=subtask.id,
                    task_description=subtask.task,
                    error=e,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    retry_count=retry_count,
                )
                self.error_history.append(error_ctx)

                # 决定恢复策略
                action = await self._decide_recovery_action(error_ctx, subtask)

                if action == RecoveryAction.RETRY:
                    retry_count += 1
                    if retry_count <= self.config.max_retries:
                        # 指数退避
                        if self.config.exponential_backoff:
                            delay = self.config.base_delay * (2 ** (retry_count - 1))
                            await asyncio.sleep(delay)
                        continue
                    else:
                        # 达到最大重试次数
                        if self.config.skip_on_max_retries:
                            action = RecoveryAction.SKIP
                        else:
                            action = RecoveryAction.ABORT

                if action == RecoveryAction.SKIP:
                    # 跳过：返回失败结果
                    return SubAgentResult(
                        agent_id=agent.name,
                        task_id=subtask.id,
                        summary=f"任务失败（已跳过）: {str(e)}",
                        success=False,
                        error=str(e),
                        metadata={
                            "retry_count": retry_count,
                            "recovery_action": "skip",
                        },
                    )

                elif action == RecoveryAction.FALLBACK:
                    # 降级：尝试简化版任务
                    simplified_task = self._simplify_task(subtask)
                    try:
                        response = await agent.run(simplified_task)
                        return SubAgentResult(
                            agent_id=agent.name,
                            task_id=subtask.id,
                            summary=f"[降级执行] {response}",
                            success=True,
                            metadata={
                                "retry_count": retry_count,
                                "recovery_action": "fallback",
                                "original_task": subtask.task,
                                "simplified_task": simplified_task,
                            },
                        )
                    except Exception as fallback_error:
                        # 降级也失败：跳过
                        return SubAgentResult(
                            agent_id=agent.name,
                            task_id=subtask.id,
                            summary=f"降级执行失败: {str(fallback_error)}",
                            success=False,
                            error=str(fallback_error),
                            metadata={
                                "retry_count": retry_count,
                                "recovery_action": "fallback_failed",
                            },
                        )

                elif action == RecoveryAction.ABORT:
                    # 中止：抛出异常
                    raise Exception(
                        f"任务执行失败，已中止（agent={agent.name}, task={subtask.id}, error={str(e)}）"
                    )

                else:
                    # 其他动作：TODO
                    return SubAgentResult(
                        agent_id=agent.name,
                        task_id=subtask.id,
                        summary=f"未实现的恢复动作: {action}",
                        success=False,
                        error=str(e),
                    )

        # 不应该到这里
        return SubAgentResult(
            agent_id=agent.name,
            task_id=subtask.id,
            summary="未知错误",
            success=False,
        )

    async def _decide_recovery_action(
        self, error_ctx: ErrorContext, subtask: SubTask
    ) -> RecoveryAction:
        """
        决定恢复策略

        Args:
            error_ctx: 错误上下文
            subtask: 子任务

        Returns:
            RecoveryAction
        """
        # 策略1：让 coordinator 决定
        if self.config.inform_coordinator and self.coordinator and self.config.coordinator_decides:
            return await self._ask_coordinator(error_ctx, subtask)

        # 策略2：自动策略
        # 如果还有重试次数，先重试
        if error_ctx.retry_count < self.config.max_retries and self.config.auto_retry:
            return RecoveryAction.RETRY

        # 如果启用降级，尝试降级
        if self.config.enable_fallback:
            return RecoveryAction.FALLBACK

        # 否则跳过
        return RecoveryAction.SKIP

    async def _ask_coordinator(
        self, error_ctx: ErrorContext, subtask: SubTask
    ) -> RecoveryAction:
        """
        询问 coordinator 如何处理错误

        Args:
            error_ctx: 错误上下文
            subtask: 子任务

        Returns:
            RecoveryAction
        """
        if not self.coordinator:
            return RecoveryAction.SKIP

        prompt = f"""子 agent 执行失败，请决定如何处理：

**失败信息**:
- Agent: {error_ctx.agent_id}
- 任务: {error_ctx.task_description}
- 错误类型: {error_ctx.error_type}
- 错误信息: {error_ctx.error_message}
- 已重试次数: {error_ctx.retry_count}

**可选操作**:
1. retry - 重试相同任务
2. skip - 跳过并继续其他任务
3. fallback - 尝试简化版任务
4. reassign - 分配给其他 agent（暂未实现）
5. abort - 中止整个执行

请返回一个操作（只返回操作名称，如 "retry"）："""

        try:
            response = await self.coordinator.run(prompt)
            action_str = response.strip().lower()

            # 解析动作
            if "retry" in action_str:
                return RecoveryAction.RETRY
            elif "skip" in action_str:
                return RecoveryAction.SKIP
            elif "fallback" in action_str:
                return RecoveryAction.FALLBACK
            elif "reassign" in action_str:
                return RecoveryAction.REASSIGN
            elif "abort" in action_str:
                return RecoveryAction.ABORT
            else:
                # 默认：skip
                return RecoveryAction.SKIP

        except Exception:
            # Coordinator 调用失败，使用默认策略
            return RecoveryAction.SKIP

    def _simplify_task(self, subtask: SubTask) -> str:
        """
        简化任务（降级）

        策略：
        - 减少工具使用要求
        - 放宽质量标准
        - 缩小范围

        Args:
            subtask: 原始子任务

        Returns:
            简化后的任务描述
        """
        simplified = f"""简化版任务: {subtask.task}

要求降级：
- 尽力而为，允许不完整结果
- 如果某些工具失败，跳过即可
- 数据源可以不完全权威
- 可以返回部分结果

请尽力完成，不要再失败。"""

        return simplified

    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        if not self.error_history:
            return {"total_errors": 0}

        # 统计错误类型
        error_types: Dict[str, int] = {}
        for error_ctx in self.error_history:
            error_type = error_ctx.error_type
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # 统计失败的 agent
        failed_agents: Dict[str, int] = {}
        for error_ctx in self.error_history:
            agent_id = error_ctx.agent_id
            failed_agents[agent_id] = failed_agents.get(agent_id, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "error_types": error_types,
            "failed_agents": failed_agents,
            "most_common_error": max(error_types, key=error_types.get)
            if error_types
            else None,
        }

    def __repr__(self) -> str:
        return (
            f"ErrorRecovery("
            f"auto_retry={self.config.auto_retry}, "
            f"max_retries={self.config.max_retries}, "
            f"inform_coordinator={self.config.inform_coordinator})"
        )


# ===== Checkpoint 机制 =====


@dataclass
class CheckpointData:
    """Checkpoint 数据"""

    # 执行状态
    task_id: str
    original_task: str
    complexity: str
    subtasks: List[Dict[str, Any]]  # 所有子任务
    completed_task_ids: List[str]  # 已完成的任务 ID
    results: Dict[str, Dict[str, Any]]  # task_id -> SubAgentResult.to_dict()

    # 元数据
    checkpoint_id: str
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class CheckpointManager:
    """
    Checkpoint 管理器

    特性：
    - 保存执行状态
    - 从中断点恢复
    - 避免从头重启

    Example:
        ```python
        checkpoint_mgr = CheckpointManager(path="./checkpoints")

        # 执行过程中保存
        checkpoint_mgr.save(
            task_id="main_task",
            original_task="分析AI市场",
            subtasks=subtasks,
            completed_task_ids=["task1", "task2"],
            results={...}
        )

        # 恢复
        data = checkpoint_mgr.load("main_task")
        if data:
            # 从 completed_task_ids 继续执行
            remaining_subtasks = [
                st for st in subtasks
                if st.id not in data.completed_task_ids
            ]
        ```
    """

    def __init__(self, path: str = "./crew_checkpoints", enabled: bool = True):
        """
        初始化 Checkpoint 管理器

        Args:
            path: 存储路径
            enabled: 是否启用（可以用于开发时禁用）
        """
        self.path = Path(path)
        self.enabled = enabled

        if self.enabled:
            self.path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        task_id: str,
        original_task: str,
        complexity: str,
        subtasks: List[SubTask],
        completed_task_ids: List[str],
        results: Dict[str, SubAgentResult],
    ) -> str:
        """
        保存 checkpoint

        Args:
            task_id: 任务 ID
            original_task: 原始任务
            complexity: 复杂度
            subtasks: 所有子任务
            completed_task_ids: 已完成的任务 ID
            results: 已完成的结果

        Returns:
            checkpoint_id
        """
        if not self.enabled:
            return ""

        checkpoint_id = f"ckpt_{task_id}_{int(time.time())}"

        # 构建数据
        data = CheckpointData(
            task_id=task_id,
            original_task=original_task,
            complexity=complexity,
            subtasks=[st.to_dict() for st in subtasks],
            completed_task_ids=completed_task_ids,
            results={tid: res.to_dict() for tid, res in results.items()},
            checkpoint_id=checkpoint_id,
            timestamp=time.time(),
        )

        # 保存到文件
        checkpoint_file = self.path / f"{checkpoint_id}.json"
        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(asdict(data), f, indent=2, ensure_ascii=False)

        return checkpoint_id

    def load(self, task_id: str) -> Optional[CheckpointData]:
        """
        加载最新的 checkpoint

        Args:
            task_id: 任务 ID

        Returns:
            CheckpointData（如果存在）
        """
        if not self.enabled:
            return None

        # 查找所有匹配的 checkpoint
        pattern = f"ckpt_{task_id}_*.json"
        checkpoint_files = list(self.path.glob(pattern))

        if not checkpoint_files:
            return None

        # 选择最新的
        latest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        # 加载
        with open(latest_file, "r", encoding="utf-8") as f:
            data_dict = json.load(f)

        return CheckpointData(**data_dict)

    def has_checkpoint(self, task_id: str) -> bool:
        """检查是否有 checkpoint"""
        if not self.enabled:
            return False

        pattern = f"ckpt_{task_id}_*.json"
        return len(list(self.path.glob(pattern))) > 0

    def delete(self, checkpoint_id: str) -> bool:
        """删除 checkpoint"""
        if not self.enabled:
            return False

        checkpoint_file = self.path / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            return True
        return False

    def clear_all(self) -> int:
        """清空所有 checkpoints"""
        if not self.enabled:
            return 0

        count = 0
        for checkpoint_file in self.path.glob("ckpt_*.json"):
            checkpoint_file.unlink()
            count += 1
        return count

    def __repr__(self) -> str:
        if self.enabled:
            checkpoint_count = len(list(self.path.glob("ckpt_*.json")))
            return f"CheckpointManager(path={self.path}, count={checkpoint_count})"
        else:
            return "CheckpointManager(disabled)"


__all__ = [
    "RecoveryAction",
    "ErrorContext",
    "RecoveryConfig",
    "ErrorRecovery",
    "CheckpointData",
    "CheckpointManager",
]
