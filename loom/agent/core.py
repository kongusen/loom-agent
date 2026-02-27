"""Agent — the core execution loop. Composition over inheritance."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from ..config import AgentConfig
from ..context import ContextOrchestrator
from ..events import EventBus
from ..memory import MemoryManager
from ..tools import ToolRegistry
from ..types import (
    AgentEvent,
    AssistantMessage,
    DoneEvent,
    LLMProvider,
    Message,
    SystemMessage,
    ToolCall,
    ToolContext,
    UserMessage,
)
from .interceptor import InterceptorChain, InterceptorContext
from .strategy import LoopContext, LoopStrategy, ToolUseStrategy

logger = logging.getLogger(__name__)

DelegateHandler = Callable[[str, str], Awaitable[str]]


class Agent:
    """Minimal agent: provider + memory + tools + context → stream events."""

    def __init__(
        self,
        provider: LLMProvider,
        config: AgentConfig | None = None,
        name: str | None = None,
        memory: MemoryManager | None = None,
        tools: ToolRegistry | None = None,
        context: ContextOrchestrator | None = None,
        event_bus: EventBus | None = None,
        interceptors: InterceptorChain | None = None,
        strategy: LoopStrategy | None = None,
    ) -> None:
        self.id = uuid.uuid4().hex[:8]
        self.name = name or f"agent-{self.id}"
        self.config = config or AgentConfig()
        self.provider = provider
        self.memory = memory or MemoryManager()
        self.tools = tools or ToolRegistry()
        self.context = context or ContextOrchestrator()
        self.event_bus = event_bus or EventBus()
        self.interceptors = interceptors or InterceptorChain()
        self.strategy = strategy or ToolUseStrategy()
        self.on_delegate: DelegateHandler | None = None

    def on(self, event_type: str, handler: Callable) -> None:
        self.event_bus.on(event_type, handler)

    async def run(self, input_text: str, signal: Any = None) -> DoneEvent:
        last_event = DoneEvent(content="")
        async for event in self.stream(input_text, signal=signal):
            if isinstance(event, DoneEvent):
                last_event = event
        return last_event

    async def stream(self, input_text: str, signal: Any = None) -> AsyncGenerator[AgentEvent, None]:
        await self.memory.add_message(UserMessage(content=input_text))
        messages = await self._build_messages()

        ctx = LoopContext(
            messages=messages,
            provider=self.provider,
            tools=self.tools.list(),
            tool_registry=self.tools,
            max_steps=self.config.max_steps,
            streaming=self.config.stream,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            agent_id=self.id,
            interceptors=self.interceptors,
            events=self.event_bus,
            signal=signal,
            tool_context=self.config.tool_context,
        )

        done_content: str | None = None
        async for event in self.strategy.execute(ctx):
            if isinstance(event, DoneEvent):
                done_content = event.content
            yield await self._emit(event)

        if done_content is not None:
            await self.memory.add_message(AssistantMessage(content=done_content))

    async def _emit(self, event: AgentEvent) -> AgentEvent:
        await self.event_bus.emit(event)
        return event

    async def _execute_tool(self, tc: ToolCall) -> str:
        if tc.name == "delegate" and self.on_delegate:
            try:
                args = json.loads(tc.arguments)
                return await self.on_delegate(args.get("task", ""), args.get("domain", ""))
            except Exception as e:
                return json.dumps({"error": str(e)})
        ctx = ToolContext(agent_id=self.id)
        return await self.tools.execute(tc, ctx)

    async def _build_messages(self) -> list[Message]:
        messages: list[Message] = [SystemMessage(content=self.config.system_prompt)]
        computed = self.context.compute_budget(self.config.system_prompt)
        budget = (
            computed.available if computed.available < float("inf") else self.config.token_budget
        )
        last = self.memory.get_history()[-1].content if self.memory.get_history() else ""
        query = last if isinstance(last, str) else str(last)
        fragments = await self.context.gather(query=query, budget=budget)
        if fragments:
            ctx_text = "\n".join(f"[{f.source}] {f.content}" for f in fragments)
            messages.append(SystemMessage(content=ctx_text))
        # L2/L3: inject long-term memories that fell out of the sliding window
        recalled = await self.memory.extract_for(query, budget=budget // 4)
        if recalled:
            mem_text = "\n".join(e.content for e in recalled)
            messages.append(SystemMessage(content=f"[Recalled context]\n{mem_text}"))
        messages.extend(self.memory.get_history())
        # Run interceptor chain
        if self.interceptors._interceptors:
            ictx = InterceptorContext(messages=messages)
            await self.interceptors.run(ictx)
            messages = ictx.messages
        return messages
