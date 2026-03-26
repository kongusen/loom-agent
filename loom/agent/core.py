"""Agent — the core execution loop. Composition over inheritance."""

from __future__ import annotations

import json
import logging
import uuid
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from ..config import AgentConfig
from ..context import CompressionScorer, ContextOrchestrator, HeartbeatLoop, PartitionManager
from ..events import EventBus
from ..evolution import EvolutionEngine
from ..memory import MemoryManager
from ..memory.tokenizers import EstimatorTokenizer
from ..scene import SceneManager
from ..skills import SkillContextManager, SkillRegistry
from ..tools import ToolRegistry
from ..types import (
    AgentEvent,
    AssistantMessage,
    DoneEvent,
    LLMProvider,
    MemoryEntry,
    Message,
    SystemMessage,
    ToolCall,
    ToolContext,
    UserMessage,
)
from .constraint_validator import ConstraintValidator
from .interceptor import InterceptorChain, InterceptorContext
from .resource_guard import ResourceGuard
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

        # 公理一：上下文工程组件
        self.tokenizer = EstimatorTokenizer()
        self.partition_mgr = PartitionManager(window=128000, tokenizer=self.tokenizer)
        self.skill_mgr = SkillContextManager(SkillRegistry(), self.tokenizer)
        self.compressor = CompressionScorer(embedding=None)
        self.heartbeat = HeartbeatLoop(
            self.partition_mgr, self.memory, self.skill_mgr, self.compressor
        )
        self._goal = ""
        self.knowledge_provider = None  # 可选的 KnowledgeProvider

        # 公理二：场景包系统
        self.scene_mgr = SceneManager()

        # 公理四：自我进化
        self.evolution = EvolutionEngine()
        self._execution_trace: list[str] = []

        # P0: Harness 约束系统
        self.constraint_validator = ConstraintValidator(self.scene_mgr)
        self.resource_guard = ResourceGuard(
            max_tokens=self.config.max_tokens or 100000, max_time_sec=300
        )

        # P2: 历史缓存优化
        self._history_cache: dict[str, Any] = {}
        self._history_dirty = True

    def on(self, event_type: str, handler: Callable) -> None:
        self.event_bus.on(event_type, handler)

    async def run(self, input_text: str, signal: Any = None) -> DoneEvent:
        last_event = DoneEvent(content="")
        async for event in self.stream(input_text, signal=signal):
            if isinstance(event, DoneEvent):
                last_event = event
        return last_event

    async def stream(self, input_text: str, signal: Any = None) -> AsyncGenerator[AgentEvent, None]:
        # P0: 启动资源守卫
        self.resource_guard.start()

        self._goal = input_text  # 保存目标用于压缩
        await self.memory.add_message(UserMessage(content=input_text))

        # P2: 标记历史为脏
        self._history_dirty = True

        # 公理一：检查腐烂系数
        if self.partition_mgr.should_heartbeat():
            logger.info(f"Heartbeat triggered: ρ={self.partition_mgr.compute_decay():.3f}")
            await self._trigger_heartbeat()
        elif self.partition_mgr.should_compress():
            logger.info(f"Compression triggered: ρ={self.partition_mgr.compute_decay():.3f}")
            await self._trigger_compression()

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

            # P0: 自动回顾蒸馏
            await self._auto_retrospect(input_text, done_content)

    async def _emit(self, event: AgentEvent) -> AgentEvent:
        await self.event_bus.emit(event)
        return event

    async def _execute_tool(self, tc: ToolCall) -> str:
        # P0: 前置约束验证
        valid, error_msg = self.constraint_validator.validate_before_call(tc)
        if not valid:
            logger.warning(f"Constraint violation: {error_msg}")
            return f"Error: {error_msg}"

        # P0: 资源配额检查
        within_quota, quota_msg = self.resource_guard.check_quota()
        if not within_quota:
            logger.error(f"Resource quota exceeded: {quota_msg}")
            return f"Error: {quota_msg}"

        # 记录执行轨迹
        self._execution_trace.append(tc.name)

        if tc.name == "delegate" and self.on_delegate:
            try:
                args = json.loads(tc.arguments)
                return await self.on_delegate(args.get("task", ""), args.get("domain", ""))
            except Exception as e:
                return json.dumps({"error": str(e)})
        ctx = ToolContext(agent_id=self.id)
        return await self.tools.execute(tc, ctx)

    async def _build_messages(self) -> list[Message]:
        # P2: 增量构建 - 避免重复计算
        cached_messages = self._history_cache.get("messages")
        if not self._history_dirty and isinstance(cached_messages, list):
            return cached_messages

        # 公理一：更新分区
        self.partition_mgr.update_partition("system", self.config.system_prompt)

        # 构建历史
        history = self.memory.get_history()
        history_text = "\n".join(
            f"{m.role}: {m.content if isinstance(m.content, str) else str(m.content)}"
            for m in history
        )
        self.partition_mgr.update_partition("history", history_text)

        # 构建消息列表
        messages: list[Message] = [SystemMessage(content=self.config.system_prompt)]

        # 添加记忆 + 知识上下文
        last = history[-1].content if history else ""
        query = last if isinstance(last, str) else str(last)
        budget = self.partition_mgr.get_available_budget("memory")

        # L2/L3 记忆
        memory_entries = await self.memory.extract_for(query, budget // 2)

        # Knowledge 检索
        knowledge_frags: list = []
        if self.knowledge_provider:
            knowledge_frags = await self.knowledge_provider.provide(query, budget // 2)

        # 合并
        combined = self._merge_context(memory_entries, knowledge_frags, budget)
        if combined:
            mem_text = "\n".join(item["content"] for item in combined)
            self.partition_mgr.update_partition("memory", mem_text)
            messages.append(SystemMessage(content=f"[Context]\n{mem_text}"))

        messages.extend(history)

        # 拦截器
        if self.interceptors._interceptors:
            ictx = InterceptorContext(messages=messages)
            await self.interceptors.run(ictx)
            messages = ictx.messages

        # P2: 缓存结果
        self._history_cache["messages"] = messages
        self._history_dirty = False

        return messages

    async def _trigger_heartbeat(self) -> None:
        """触发心跳续写（Ralph Loop）"""
        new_context = await self.heartbeat.trigger(self._goal)
        # 更新分区
        for name, content in new_context.items():
            self.partition_mgr.update_partition(name, content)

    async def _trigger_compression(self) -> None:
        """触发历史压缩"""
        history = self.memory.get_history()
        scored = await self.compressor.score_history(history, self._goal)
        scored.sort(key=lambda x: x[1], reverse=True)
        keep_count = max(1, int(len(scored) * 0.4))
        # 保留高分消息（简化实现：直接更新 L1）
        compressed = [msg for msg, _ in scored[:keep_count]]
        self.memory.l1._messages = deque(
            (
                msg,
                self.memory.tokenizer.count(
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                ),
            )
            for msg in compressed
        )
        self.memory.l1.current_tokens = sum(tokens for _, tokens in self.memory.l1._messages)

    def _merge_context(self, memory_entries: list, knowledge_frags: list, budget: int) -> list:
        """合并记忆和知识，按相关度排序"""
        items = []
        for e in memory_entries:
            items.append({"content": e.content, "score": e.importance, "tokens": e.tokens})
        for f in knowledge_frags:
            items.append({"content": f.content, "score": f.relevance, "tokens": f.tokens})
        items.sort(key=lambda x: x["score"], reverse=True)
        result, used = [], 0
        for item in items:
            if used + item["tokens"] > budget:
                break
            result.append(item)
            used += item["tokens"]
        return result

    async def spawn(
        self, _goal: str, slice_type: str = "minimal", memory_chunks: list | None = None
    ) -> Agent:
        """派生 Sub-Agent（E4: E_spawn）"""
        sub_agent = Agent(
            provider=self.provider,
            config=self.config,
            memory=MemoryManager(),
            tools=self.tools,
        )
        # 共享 M_f（L3）
        sub_agent.memory.l3 = self.memory.l3
        # Modular 切片：注入记忆
        if slice_type == "modular" and memory_chunks:
            for chunk in memory_chunks:
                await sub_agent.memory.l2.store(chunk)
        return sub_agent

    async def _handle_write_memory(self, content: str, importance: float = 0.7) -> str:
        """E1: 写记忆工具处理器"""
        entry = MemoryEntry(
            content=content, tokens=self.tokenizer.count(content), importance=importance
        )
        await self.memory.l3.store(entry)
        return f"Memory stored: {content[:50]}..."

    async def _handle_activate_skill(self, skill_name: str) -> str:
        """E2: 激活技能工具处理器"""
        budget = self.partition_mgr.get_available_budget("skill")
        success = self.skill_mgr.activate(skill_name, budget)
        if success:
            return f"Skill '{skill_name}' activated"
        return f"Failed to activate '{skill_name}' (budget exceeded or not found)"

    async def _handle_deactivate_skill(self, skill_name: str) -> str:
        """E2: 卸载技能工具处理器"""
        self.skill_mgr.deactivate(skill_name)
        return f"Skill '{skill_name}' deactivated"

    async def _handle_switch_scene(self, scene_id: str) -> str:
        """E3: 场景切换工具处理器"""
        try:
            tools = self.scene_mgr.switch(scene_id)
            return f"Scene switched to '{scene_id}' with {len(tools)} tools"
        except ValueError as e:
            return f"Scene switch failed: {e}"

    async def _auto_retrospect(self, task: str, result: str) -> None:
        """P0: 自动回顾蒸馏"""
        from ..types.evolution import TaskResult as EvolutionTaskResult

        success = bool(result and "error" not in result.lower())
        task_result = EvolutionTaskResult(
            task=task, success=success, trace=self._execution_trace, metadata={}
        )
        await self.evolution.e1_retrospect(task_result)
        self._execution_trace = []

        # P1: 自动技能结晶
        skills = await self.evolution.e2_crystallize()
        if skills:
            for skill in skills:
                self.skill_mgr.registry.register(skill)
                logger.info(f"Auto-crystallized skill: {skill.name}")

    def _check_constraints(self, tool_call: ToolCall, constraints: dict) -> bool:
        """P0/P1: 约束检查 + 工具白名单"""
        # P1: 工具白名单检查
        if not self.scene_mgr.is_tool_allowed(tool_call.name):
            return False

        # P0: 约束检查
        if constraints.get("network") is False and tool_call.name in ["web_search", "web_fetch"]:
            return False
        if constraints.get("write") is False and tool_call.name in ["write_file", "bash"]:
            return False
        return True
