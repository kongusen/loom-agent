from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional

from loom.core.agent_executor import AgentExecutor
from loom.core.types import StreamEvent
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.interfaces.compressor import BaseCompressor
from loom.callbacks.base import BaseCallback
from loom.callbacks.metrics import MetricsCollector
from loom.core.steering_control import SteeringControl


class Agent:
    """高层 Agent 组件：对外暴露 run/stream，内部委托 AgentExecutor。"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: List[BaseTool] | None = None,
        memory: Optional[BaseMemory] = None,
        compressor: Optional[BaseCompressor] = None,
        max_iterations: int = 50,
        max_context_tokens: int = 16000,
        permission_policy: Optional[Dict[str, str]] = None,
        ask_handler=None,
        safe_mode: bool = False,
        permission_store=None,
        # Advanced options
        context_retriever=None,
        system_instructions: Optional[str] = None,
        callbacks: Optional[List[BaseCallback]] = None,
        steering_control: Optional[SteeringControl] = None,
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        # v4.0.0: Auto-instantiate CompressionManager (always enabled)
        if compressor is None:
            from loom.core.compression_manager import CompressionManager
            compressor = CompressionManager(
                llm=llm,
                max_retries=3,
                compression_threshold=0.92,
                target_reduction=0.75,
                sliding_window_size=20,
            )

        tools_map = {t.name: t for t in (tools or [])}
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools_map,
            memory=memory,
            compressor=compressor,
            context_retriever=context_retriever,
            steering_control=steering_control,
            max_iterations=max_iterations,
            max_context_tokens=max_context_tokens,
            metrics=metrics,
            permission_manager=None,
            system_instructions=system_instructions,
            callbacks=callbacks,
            enable_steering=True,  # v4.0.0: Always enabled
        )

        # 始终构造 PermissionManager（以便支持 safe_mode/持久化）；保持默认语义
        from loom.core.permissions import PermissionManager

        pm = PermissionManager(
            policy=permission_policy or {},
            default="allow",  # 保持默认放行语义
            ask_handler=ask_handler,
            safe_mode=safe_mode,
            permission_store=permission_store,
        )
        self.executor.permission_manager = pm
        self.executor.tool_pipeline.permission_manager = pm

    async def run(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,  # 🆕 US1
        correlation_id: Optional[str] = None,  # 🆕 US1
    ) -> str:
        return await self.executor.execute(input, cancel_token=cancel_token, correlation_id=correlation_id)

    async def stream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        async for ev in self.executor.stream(input):
            yield ev

    # LangChain 风格的别名，便于迁移/调用
    async def ainvoke(
        self,
        input: str,
        cancel_token: Optional[asyncio.Event] = None,  # 🆕 US1
        correlation_id: Optional[str] = None,  # 🆕 US1
    ) -> str:
        return await self.run(input, cancel_token=cancel_token, correlation_id=correlation_id)

    async def astream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        async for ev in self.stream(input):
            yield ev

    def get_metrics(self) -> Dict:
        """返回当前指标摘要。"""
        return self.executor.metrics.summary()
