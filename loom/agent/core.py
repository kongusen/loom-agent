"""Agent — the core execution loop. Composition over inheritance."""

from __future__ import annotations

import json
import logging
import uuid
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any

from ..config import AgentConfig
from ..context import CompressionScorer, HeartbeatLoop, PartitionManager
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

        # 阶段 4: WorkingState 结构化
        from ..types.working import WorkingState
        self.working_state = WorkingState(budget=2000)

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

        # 阶段 3: 边界检测和响应
        from .boundary import BoundaryDetector, BoundaryHandler
        self.boundary_detector = BoundaryDetector(
            self.partition_mgr, self.resource_guard, self.scene_mgr
        )
        self.boundary_handler = BoundaryHandler(self)

        # 公理四：自动注册 E1/E2 工具
        self._register_evolution_tools()

    def _register_evolution_tools(self) -> None:
        """自动注册进化工具"""
        from ..tools.agent_tools import create_memory_tools, create_skill_tools

        # E1: 记忆工具
        for tool in create_memory_tools(self):
            self.tools.register(tool)

        # E2: 技能工具
        for tool in create_skill_tools(self):
            self.tools.register(tool)

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
            agent=self,
            constraint_validator=self.constraint_validator,
            resource_guard=self.resource_guard,
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

    async def _emit_with_gain(self, event: AgentEvent, payload: str = "") -> AgentEvent:
        """公理三：带信息增益门控的事件发布"""
        context = self.partition_mgr.get_context()
        published = await self.event_bus.publish_with_gain(
            event,
            payload=payload or str(event),
            context=context
        )
        if not published:
            logger.debug(f"Event filtered by gain gating: {type(event).__name__}")
        return event

    async def _execute_tool(self, tc: ToolCall) -> str:
        # P0: 资源配额检查
        within_quota, quota_msg = self.resource_guard.check_quota()
        if not within_quota:
            logger.error(f"Resource quota exceeded: {quota_msg}")
            return f"Error: {quota_msg}"

        # 执行工具（约束验证在 ToolRegistry 中）
        if tc.name == "delegate" and self.on_delegate:
            try:
                args = json.loads(tc.arguments)
                result = await self.on_delegate(args.get("task", ""), args.get("domain", ""))
            except Exception as e:
                result = json.dumps({"error": str(e)})
        else:
            ctx = ToolContext(agent_id=self.id)
            result = await self.tools.execute(tc, ctx, constraint_validator=self.constraint_validator)

        # 记录执行轨迹
        self._execution_trace.append(f"{tc.name}({tc.arguments[:50]}) → {result[:100]}")

        # 公理三：过滤工具输出
        filtered_result = await self._filter_tool_output(tc.name, result)

        # 更新 working 分区
        working_content = self._build_working_state()
        self.partition_mgr.update_partition("working", working_content)

        return filtered_result

    async def _filter_tool_output(self, tool_name: str, raw_output: str) -> str:
        """公理三：过滤工具输出的冗余信息"""
        context = self.partition_mgr.get_context()
        delta_h = self.event_bus.info_calc.calculate_delta_h(raw_output, context)

        # 低增益：截断
        if delta_h < 0.1:
            return f"[Tool {tool_name} executed, output redundant]"

        # 中等增益：总结
        if delta_h < 0.3:
            return self._summarize_output(raw_output, max_tokens=200)

        # 高增益：完整保留
        return raw_output

    def _summarize_output(self, text: str, max_tokens: int) -> str:
        """总结输出（简单截断）"""
        truncated = self.tokenizer.truncate(text, max_tokens)
        if len(truncated) < len(text):
            return truncated + "\n[... output truncated for brevity]"
        return text

    async def _build_messages(self) -> list[Message]:
        """基于 PartitionManager 构建完整上下文（公理一完整接入）"""
        # P2: 增量构建 - 避免重复计算
        cached_messages = self._history_cache.get("messages")
        if not self._history_dirty and isinstance(cached_messages, list):
            return cached_messages

        # 1. 更新所有分区
        await self._update_all_partitions()

        # 2. 检查是否需要压缩/心跳（已在 stream() 中处理，这里跳过）

        # 3. 统一组装（替换手工拼接）
        messages = self._context_to_messages()

        # 4. 拦截器（保留）
        if self.interceptors._interceptors:
            ictx = InterceptorContext(messages=messages)
            await self.interceptors.run(ictx)
            messages = ictx.messages

        # P2: 缓存结果
        self._history_cache["messages"] = messages
        self._history_dirty = False

        return messages

    async def _update_all_partitions(self) -> None:
        """更新所有 5 个分区"""
        # C_system: 基础 prompt
        system_content = self.config.system_prompt
        self.partition_mgr.update_partition("system", system_content)

        # C_working: 当前任务状态
        working_content = self._build_working_state()
        self.partition_mgr.update_partition("working", working_content)

        # C_memory: L2/L3 检索 + knowledge
        query = self._get_current_query()
        budget = self.partition_mgr.get_available_budget("memory")
        memory_entries = await self.memory.extract_for(query, budget // 2)

        knowledge_frags = []
        if self.knowledge_provider:
            knowledge_frags = await self.knowledge_provider.provide(query, budget // 2)

        combined = self._merge_context(memory_entries, knowledge_frags, budget)
        memory_text = "\n".join(item["content"] for item in combined)
        self.partition_mgr.update_partition("memory", memory_text)

        # C_skill: 激活的技能
        skill_context = self.skill_mgr.get_context()
        self.partition_mgr.update_partition("skill", skill_context)

        # C_history: L1 历史
        history = self.memory.get_history()
        history_text = "\n".join(
            f"{m.role}: {m.content if isinstance(m.content, str) else str(m.content)}"
            for m in history
        )
        self.partition_mgr.update_partition("history", history_text)

    def _build_working_state(self) -> str:
        """构建 working 分区内容"""
        # 更新 WorkingState
        self.working_state.goal = self._goal

        # 最近动作放入 overflow
        recent = self._execution_trace[-3:] if self._execution_trace else []
        if recent:
            self.working_state.overflow = "\n".join(recent)

        # 转换为文本（自动截断）
        return self.working_state.to_text(self.tokenizer)

    def _get_current_query(self) -> str:
        """获取当前查询（用于检索）"""
        history = self.memory.get_history()
        if not history:
            return self._goal or ""
        last = history[-1].content
        return last if isinstance(last, str) else str(last)

    def _context_to_messages(self) -> list[Message]:
        """将完整上下文转换为 Message 列表"""
        messages = []

        # 前 4 个分区合并为 SystemMessage
        context_parts = []
        for name in ["system", "working", "memory", "skill"]:
            content = self.partition_mgr.partitions[name].content
            if content:
                context_parts.append(f"[{name.upper()}]\n{content}")

        if context_parts:
            messages.append(SystemMessage(content="\n\n".join(context_parts)))

        # history 保持原有结构
        history = self.memory.get_history()
        messages.extend(history)

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
