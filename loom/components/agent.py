from __future__ import annotations

from typing import AsyncGenerator, Dict, List, Optional

from loom.core.agent_executor import AgentExecutor
from loom.core.types import StreamEvent
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.interfaces.compressor import BaseCompressor
from loom.callbacks.base import BaseCallback
from loom.callbacks.metrics import MetricsCollector
from loom.core.event_bus import EventBus


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
        event_bus: Optional[EventBus] = None,
        metrics: Optional[MetricsCollector] = None,
    ) -> None:
        tools_map = {t.name: t for t in (tools or [])}
        self.executor = AgentExecutor(
            llm=llm,
            tools=tools_map,
            memory=memory,
            compressor=compressor,
            context_retriever=context_retriever,
            event_bus=event_bus,
            max_iterations=max_iterations,
            max_context_tokens=max_context_tokens,
            metrics=metrics,
            permission_manager=None,
            system_instructions=system_instructions,
            callbacks=callbacks,
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

    async def run(self, input: str) -> str:
        return await self.executor.execute(input)

    async def stream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        async for ev in self.executor.stream(input):
            yield ev

    # LangChain 风格的别名，便于迁移/调用
    async def ainvoke(self, input: str) -> str:
        return await self.run(input)

    async def astream(self, input: str) -> AsyncGenerator[StreamEvent, None]:
        async for ev in self.stream(input):
            yield ev

    def get_metrics(self) -> Dict:
        """返回当前指标摘要。"""
        return self.executor.metrics.summary()
