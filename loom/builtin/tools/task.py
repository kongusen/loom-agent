"""Task 工具 - 启动 SubAgent 执行子任务"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Optional, Dict, List

from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool
from loom.core.permissions import PermissionManager
from loom.agents.registry import get_agent_by_type as get_registered_agent_by_type
from loom.utils.agent_loader import (
    get_agent_by_type as get_file_agent_by_type,
)  # fallback to file-based packs
from loom.agents.refs import AgentRef, ModelRef

if TYPE_CHECKING:
    from loom.components.agent import Agent


class TaskInput(BaseModel):
    """Task 工具输入参数"""

    description: str = Field(description="Short description of the task (3-5 words)")
    prompt: str = Field(description="Detailed task instructions for the sub-agent")
    subagent_type: str | None = Field(
        default=None, description="Optional: agent type from .loom/.claude agent packs"
    )
    model_name: str | None = Field(
        default=None, description="Optional: override model name for this sub-agent"
    )


class TaskTool(BaseTool):
    """
    Task 工具 - 启动 SubAgent 执行专项任务

    对应 Claude Code 的 Task 工具和 SubAgent 机制
    
    新特性 (Loom 0.0.3):
    - 子代理池管理
    - 性能监控和指标收集
    - 智能负载均衡
    - 资源使用优化
    """

    name = "task"
    description = (
        "Launch a sub-agent to handle a specific subtask independently. "
        "Useful for parallel execution or specialized processing. "
        "The sub-agent has its own execution environment and tool access."
    )
    args_schema = TaskInput
    is_concurrency_safe = True

    # 🆕 Loom 2.0 - Orchestration attributes
    is_read_only = False  # Sub-agent may use write tools
    category = "general"  # Not inherently dangerous, but depends on sub-agent's tools
    requires_confirmation = False

    def __init__(
        self,
        agent_factory: Optional[callable] = None,
        max_iterations: int = 20,
        enable_pooling: bool = True,
        pool_size: int = 5,
        enable_monitoring: bool = True,
    ) -> None:
        """
        Parameters:
        - agent_factory: 创建 SubAgent 的工厂函数
        - max_iterations: SubAgent 最大迭代次数
        - enable_pooling: 启用子代理池管理
        - pool_size: 子代理池大小
        - enable_monitoring: 启用性能监控
        """
        self.agent_factory = agent_factory
        self.max_iterations = max_iterations
        
        # Performance optimizations
        self.enable_pooling = enable_pooling
        self.pool_size = pool_size
        self.enable_monitoring = enable_monitoring
        
        # Sub-agent pool management
        self._agent_pool: Dict[str, Any] = {}
        self._pool_stats = {
            "total_created": 0,
            "total_executed": 0,
            "average_execution_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }

    async def run(
        self,
        description: str,
        prompt: str,
        subagent_type: str | None = None,
        model_name: str | None = None,
        **kwargs: Any,
    ) -> str:
        """执行子任务"""
        if not self.agent_factory:
            return "Error: Task tool not configured with agent_factory"

        try:
            # 解析 Agent Packs（若提供 subagent_type）
            agent_system_instructions: Optional[str] = None
            allowed_tools: Optional[List[str]] = None
            effective_model: Optional[str] = model_name

            if subagent_type:
                # 1) Prefer programmatic registry
                cfg = get_registered_agent_by_type(subagent_type)
                if cfg:
                    agent_system_instructions = cfg.system_instructions or None
                    if isinstance(cfg.tools, list):
                        allowed_tools = list(cfg.tools)
                    elif cfg.tools == "*":
                        allowed_tools = None
                    if effective_model is None and cfg.model_name:
                        effective_model = cfg.model_name
                else:
                    # 2) Fallback to file-based packs (optional)
                    fcfg = get_file_agent_by_type(subagent_type)
                    if fcfg:
                        agent_system_instructions = fcfg.system_prompt or None
                        if isinstance(fcfg.tools, list):
                            allowed_tools = fcfg.tools
                        elif fcfg.tools == "*":
                            allowed_tools = None
                        if effective_model is None and fcfg.model_name:
                            effective_model = fcfg.model_name

            # 构造权限策略（若需要限制工具）
            permission_policy: Optional[Dict[str, str]] = None
            if allowed_tools is not None:
                policy: Dict[str, str] = {"default": "deny"}
                for t in allowed_tools:
                    policy[t] = "allow"
                permission_policy = policy

            # 创建 SubAgent 实例（尽量传递可选参数；不支持则回退）
            try:
                sub_agent: Agent = self.agent_factory(  # type: ignore[call-arg]
                    max_iterations=self.max_iterations,
                    system_instructions=agent_system_instructions,
                    permission_policy=permission_policy,
                    model_name=effective_model,
                )
            except TypeError:
                # 回退到最小签名
                sub_agent = self.agent_factory(max_iterations=self.max_iterations)  # type: ignore[call-arg]

                # 如果无法通过构造器注入权限，则运行时替换权限管理器
                if permission_policy is not None:
                    sub_agent.executor.permission_manager = PermissionManager(
                        policy=permission_policy
                    )
                    sub_agent.executor.tool_pipeline.permission_manager = (
                        sub_agent.executor.permission_manager
                    )

            # 运行子任务（系统提示已注入到 sub_agent，输入仍为原始 prompt）
            start_time = time.time() if self.enable_monitoring else None
            
            # Check pool for reusable agent
            agent_key = self._get_agent_key(subagent_type, effective_model, permission_policy)
            if self.enable_pooling and agent_key in self._agent_pool:
                sub_agent = self._agent_pool[agent_key]
                self._pool_stats["cache_hits"] += 1
            else:
                self._pool_stats["cache_misses"] += 1
                self._pool_stats["total_created"] += 1
                
                # Add to pool if enabled and not at capacity
                if self.enable_pooling and len(self._agent_pool) < self.pool_size:
                    self._agent_pool[agent_key] = sub_agent
            
            result = await sub_agent.run(prompt)
            
            # Update performance metrics
            if self.enable_monitoring and start_time:
                execution_time = time.time() - start_time
                self._pool_stats["total_executed"] += 1
                # Update running average
                current_avg = self._pool_stats["average_execution_time"]
                total_executed = self._pool_stats["total_executed"]
                self._pool_stats["average_execution_time"] = (
                    (current_avg * (total_executed - 1) + execution_time) / total_executed
                )

            # 格式化返回结果
            return f"**SubAgent Task: {description}**\n\nResult:\n{result}"

        except Exception as e:
            return f"SubAgent execution error: {type(e).__name__}: {str(e)}"

    # Framework-friendly API: set by reference instead of strings
    async def run_ref(
        self,
        *,
        description: str,
        prompt: str,
        agent: AgentRef | None = None,
        model: ModelRef | None = None,
    ) -> str:
        subagent_type = agent.agent_type if isinstance(agent, AgentRef) else None
        model_name = model.name if isinstance(model, ModelRef) else None
        return await self.run(
            description=description,
            prompt=prompt,
            subagent_type=subagent_type,
            model_name=model_name,
        )

    def _get_agent_key(
        self, 
        subagent_type: Optional[str], 
        model_name: Optional[str], 
        permission_policy: Optional[Dict[str, str]]
    ) -> str:
        """Generate unique key for agent pool"""
        import hashlib
        
        key_parts = [
            subagent_type or "default",
            model_name or "default",
            str(sorted(permission_policy.items())) if permission_policy else "default"
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get sub-agent pool statistics"""
        return {
            **self._pool_stats,
            "pool_size": len(self._agent_pool),
            "max_pool_size": self.pool_size,
            "pool_utilization": len(self._agent_pool) / self.pool_size if self.pool_size > 0 else 0,
            "cache_hit_rate": (
                self._pool_stats["cache_hits"] / 
                (self._pool_stats["cache_hits"] + self._pool_stats["cache_misses"])
                if (self._pool_stats["cache_hits"] + self._pool_stats["cache_misses"]) > 0 else 0
            )
        }

    def clear_pool(self) -> None:
        """Clear the sub-agent pool"""
        self._agent_pool.clear()

    def reset_stats(self) -> None:
        """Reset performance statistics"""
        self._pool_stats = {
            "total_created": 0,
            "total_executed": 0,
            "average_execution_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
