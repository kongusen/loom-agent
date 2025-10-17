from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from loom.core.steering_control import SteeringControl
from loom.core.tool_pipeline import ToolExecutionPipeline
from loom.core.types import Message, StreamEvent, ToolCall
from loom.core.system_prompt import build_system_prompt
from loom.interfaces.compressor import BaseCompressor
from loom.interfaces.llm import BaseLLM
from loom.interfaces.memory import BaseMemory
from loom.interfaces.tool import BaseTool
from loom.core.permissions import PermissionManager
from loom.callbacks.metrics import MetricsCollector
import time
from loom.utils.token_counter import count_messages_tokens
from loom.callbacks.base import BaseCallback
from loom.core.errors import ExecutionAbortedError

# RAG support
try:
    from loom.core.context_retriever import ContextRetriever
except ImportError:
    ContextRetriever = None  # type: ignore


class AgentExecutor:
    """Agent 执行器：封装主循环，连接 LLM、内存、工具流水线与事件流。"""

    def __init__(
        self,
        llm: BaseLLM,
        tools: Dict[str, BaseTool] | None = None,
        memory: BaseMemory | None = None,
        compressor: BaseCompressor | None = None,
        context_retriever: Optional["ContextRetriever"] = None,  # 🆕 RAG support
        steering_control: SteeringControl | None = None,
        max_iterations: int = 50,
        max_context_tokens: int = 16000,
        permission_manager: PermissionManager | None = None,
        metrics: MetricsCollector | None = None,
        system_instructions: Optional[str] = None,
        callbacks: Optional[List[BaseCallback]] = None,
        enable_steering: bool = False,  # 🆕 US1: Real-time steering
    ) -> None:
        self.llm = llm
        self.tools = tools or {}
        self.memory = memory
        self.compressor = compressor
        self.context_retriever = context_retriever  # 🆕 RAG support
        self.steering_control = steering_control or SteeringControl()
        self.max_iterations = max_iterations
        self.max_context_tokens = max_context_tokens
        self.metrics = metrics or MetricsCollector()
        self.permission_manager = permission_manager or PermissionManager(policy={"default": "allow"})
        self.system_instructions = system_instructions
        self.callbacks = callbacks or []
        self.enable_steering = enable_steering  # 🆕 US1
        self.tool_pipeline = ToolExecutionPipeline(
            self.tools, permission_manager=self.permission_manager, metrics=self.metrics
        )

    async def _emit(self, event_type: str, payload: Dict) -> None:
        if not self.callbacks:
            return
        enriched = dict(payload)
        enriched.setdefault("ts", time.time())
        enriched.setdefault("type", event_type)
        for cb in self.callbacks:
            try:
                await cb.on_event(event_type, enriched)
            except Exception:
                # best-effort; don't fail agent execution on callback errors
                pass

    async def execute(
        self,
        user_input: str,
        cancel_token: Optional[asyncio.Event] = None,  # 🆕 US1: Cancellation support
        correlation_id: Optional[str] = None,  # 🆕 US1: Request tracing
    ) -> str:
        """非流式执行，包含工具调用的 ReAct 循环（最小实现）。

        Args:
            user_input: User query/instruction
            cancel_token: Optional Event to signal cancellation (US1)
            correlation_id: Optional correlation ID for request tracing (US1)

        Returns:
            Final agent response (or partial results if cancelled)
        """
        # Generate correlation_id if not provided
        if correlation_id is None:
            correlation_id = str(uuid4())

        await self._emit("request_start", {
            "input": user_input,
            "source": "execute",
            "iteration": 0,
            "correlation_id": correlation_id,  # 🆕 US1
        })

        # Check cancellation before starting
        if cancel_token and cancel_token.is_set():
            await self._emit("agent_finish", {
                "content": "Request cancelled before execution",
                "source": "execute",
                "correlation_id": correlation_id,
            })
            return "Request cancelled before execution"

        history = await self._load_history()

        # 🆕 Step 1: RAG - 自动检索相关文档（如果配置了 context_retriever）
        retrieved_docs = []
        if self.context_retriever:
            retrieved_docs = await self.context_retriever.retrieve_for_query(user_input)
            if retrieved_docs:
                # 注入检索到的文档上下文
                if self.context_retriever.inject_as == "system":
                    doc_context = self.context_retriever.format_documents(retrieved_docs)
                    history.append(Message(
                        role="system",
                        content=doc_context,
                        metadata={"type": "retrieved_context", "doc_count": len(retrieved_docs)}
                    ))
                # 记录检索指标
                self.metrics.metrics.retrievals = getattr(self.metrics.metrics, "retrievals", 0) + 1
                await self._emit("retrieval_complete", {"doc_count": len(retrieved_docs), "source": "execute"})

        # Step 2: 添加用户消息
        history.append(Message(role="user", content=user_input))

        # Step 3: 压缩检查
        history = await self._maybe_compress(history)

        # Step 4: 动态生成系统提示
        context = {"retrieved_docs_count": len(retrieved_docs)} if retrieved_docs else None
        system_prompt = build_system_prompt(self.tools, self.system_instructions, context)
        history = self._inject_system_prompt(history, system_prompt)

        if not self.llm.supports_tools or not self.tools:
            try:
                # Create LLM task that can be cancelled
                llm_task = asyncio.create_task(self.llm.generate([m.__dict__ for m in history]))

                # Poll for cancellation while waiting for LLM
                while not llm_task.done():
                    if cancel_token and cancel_token.is_set():
                        llm_task.cancel()
                        try:
                            await llm_task
                        except asyncio.CancelledError:
                            pass
                        partial_result = "Execution interrupted during LLM call"
                        await self._emit("agent_finish", {
                            "content": partial_result,
                            "source": "execute",
                            "correlation_id": correlation_id,
                            "interrupted": True,
                        })
                        return partial_result
                    await asyncio.sleep(0.1)  # Check every 100ms

                text = await llm_task
            except asyncio.CancelledError:
                partial_result = "Execution interrupted during LLM call"
                await self._emit("agent_finish", {
                    "content": partial_result,
                    "source": "execute",
                    "correlation_id": correlation_id,
                    "interrupted": True,
                })
                return partial_result
            except Exception as e:
                self.metrics.metrics.total_errors += 1
                await self._emit("error", {"stage": "llm_generate", "message": str(e)})
                raise
            self.metrics.metrics.llm_calls += 1
            if self.memory:
                await self.memory.add_message(Message(role="assistant", content=text))
            await self._emit("agent_finish", {"content": text, "source": "execute"})
            return text

        tools_spec = self._serialize_tools()
        iterations = 0
        final_text = ""
        while iterations < self.max_iterations:
            # 🆕 US1: Check cancellation before each iteration
            if cancel_token and cancel_token.is_set():
                partial_result = f"Execution interrupted after {iterations} iterations. Partial progress: {final_text or '(in progress)'}"
                await self._emit("agent_finish", {
                    "content": partial_result,
                    "source": "execute",
                    "correlation_id": correlation_id,
                    "interrupted": True,
                    "iterations_completed": iterations,
                })
                return partial_result

            try:
                resp = await self.llm.generate_with_tools([m.__dict__ for m in history], tools_spec)
            except Exception as e:
                self.metrics.metrics.total_errors += 1
                await self._emit("error", {
                    "stage": "llm_generate_with_tools",
                    "message": str(e),
                    "source": "execute",
                    "iteration": iterations,
                    "correlation_id": correlation_id,  # 🆕 US1
                })
                raise
            self.metrics.metrics.llm_calls += 1
            tool_calls = resp.get("tool_calls") or []
            content = resp.get("content") or ""

            if tool_calls:
                # 广播工具调用开始（非流式路径）
                try:
                    meta = [
                        {"id": str(tc.get("id", "")), "name": str(tc.get("name", ""))}
                        for tc in tool_calls
                    ]
                    await self._emit("tool_calls_start", {"tool_calls": meta, "source": "execute", "iteration": iterations})
                except Exception:
                    pass
                # 执行工具并把结果写回消息
                try:
                    for tr in await self._execute_tool_batch(tool_calls):
                        tool_msg = Message(role="tool", content=tr.content, tool_call_id=tr.tool_call_id)
                        history.append(tool_msg)
                        if self.memory:
                            await self.memory.add_message(tool_msg)
                        await self._emit("tool_result", {"tool_call_id": tr.tool_call_id, "content": tr.content, "source": "execute", "iteration": iterations})
                except Exception as e:
                    self.metrics.metrics.total_errors += 1
                    await self._emit("error", {"stage": "tool_execute", "message": str(e), "source": "execute", "iteration": iterations})
                    raise
                iterations += 1
                self.metrics.metrics.total_iterations += 1
                history = await self._maybe_compress(history)
                continue

            # 无工具调用：认为生成最终答案
            final_text = content
            if self.memory:
                await self.memory.add_message(Message(role="assistant", content=final_text))
            await self._emit("agent_finish", {
                "content": final_text,
                "source": "execute",
                "correlation_id": correlation_id,  # 🆕 US1
            })
            break

        return final_text

    async def stream(self, user_input: str) -> AsyncGenerator[StreamEvent, None]:
        """流式执行：输出 text_delta/agent_finish 事件。后续可接入 tool_calls。"""
        yield StreamEvent(type="request_start")
        await self._emit("request_start", {"input": user_input, "source": "stream", "iteration": 0})
        history = await self._load_history()

        # 🆕 RAG - 自动检索文档
        retrieved_docs = []
        if self.context_retriever:
            retrieved_docs = await self.context_retriever.retrieve_for_query(user_input)
            if retrieved_docs:
                if self.context_retriever.inject_as == "system":
                    doc_context = self.context_retriever.format_documents(retrieved_docs)
                    history.append(Message(
                        role="system",
                        content=doc_context,
                        metadata={"type": "retrieved_context", "doc_count": len(retrieved_docs)}
                    ))
                self.metrics.metrics.retrievals = getattr(self.metrics.metrics, "retrievals", 0) + 1
                # 🆕 广播检索事件
                yield StreamEvent(type="retrieval_complete", metadata={"doc_count": len(retrieved_docs)})
                await self._emit("retrieval_complete", {"doc_count": len(retrieved_docs), "source": "stream"})

        history.append(Message(role="user", content=user_input))

        # 压缩检查
        compressed = await self._maybe_compress(history)
        if compressed is not history:
            history = compressed
            yield StreamEvent(type="compression_applied")

        # 动态生成系统提示
        context = {"retrieved_docs_count": len(retrieved_docs)} if retrieved_docs else None
        system_prompt = build_system_prompt(self.tools, self.system_instructions, context)
        history = self._inject_system_prompt(history, system_prompt)

        if not self.llm.supports_tools or not self.tools:
            try:
                async for delta in self.llm.stream([m.__dict__ for m in history]):
                    yield StreamEvent(type="text_delta", content=delta)
            except Exception as e:
                self.metrics.metrics.total_errors += 1
                await self._emit("error", {"stage": "llm_stream", "message": str(e), "source": "stream"})
                raise
            yield StreamEvent(type="agent_finish")
            return

        tools_spec = self._serialize_tools()
        iterations = 0
        while iterations < self.max_iterations:
            try:
                resp = await self.llm.generate_with_tools([m.__dict__ for m in history], tools_spec)
            except Exception as e:
                self.metrics.metrics.total_errors += 1
                await self._emit("error", {"stage": "llm_generate_with_tools", "message": str(e), "source": "stream", "iteration": iterations})
                raise
            self.metrics.metrics.llm_calls += 1
            tool_calls = resp.get("tool_calls") or []
            content = resp.get("content") or ""

            if tool_calls:
                # 广播工具调用开始
                tc_models = [self._to_tool_call(tc) for tc in tool_calls]
                yield StreamEvent(type="tool_calls_start", tool_calls=tc_models)
                await self._emit(
                    "tool_calls_start",
                    {"tool_calls": [{"id": t.id, "name": t.name} for t in tc_models], "source": "stream", "iteration": iterations},
                )
                # 执行工具
                try:
                    async for tr in self._execute_tool_calls_async(tc_models):
                        yield StreamEvent(type="tool_result", result=tr)
                        await self._emit("tool_result", {"tool_call_id": tr.tool_call_id, "content": tr.content, "source": "stream", "iteration": iterations})
                        tool_msg = Message(role="tool", content=tr.content, tool_call_id=tr.tool_call_id)
                        history.append(tool_msg)
                        if self.memory:
                            await self.memory.add_message(tool_msg)
                except Exception as e:
                    self.metrics.metrics.total_errors += 1
                    await self._emit("error", {"stage": "tool_execute", "message": str(e), "source": "stream", "iteration": iterations})
                    raise
                iterations += 1
                self.metrics.metrics.total_iterations += 1
                # 每轮结束后做压缩检查
                history = await self._maybe_compress(history)
                continue

            # 无工具调用：输出最终文本并结束
            if content:
                yield StreamEvent(type="text_delta", content=content)
            yield StreamEvent(type="agent_finish")
            await self._emit("agent_finish", {"content": content})
            if self.memory and content:
                await self.memory.add_message(Message(role="assistant", content=content))
            break

    async def _load_history(self) -> List[Message]:
        if not self.memory:
            return []
        return await self.memory.get_messages()

    async def _maybe_compress(self, history: List[Message]) -> List[Message]:
        """Check if compression needed and apply if threshold reached.

        US2: Automatic compression at 92% threshold with 8-segment summarization.
        """
        if not self.compressor:
            return history

        tokens_before = count_messages_tokens(history)

        # Check if compression should be triggered (92% threshold)
        if self.compressor.should_compress(tokens_before, self.max_context_tokens):
            # Attempt compression
            try:
                compressed_messages, metadata = await self.compressor.compress(history)

                # Update metrics
                self.metrics.metrics.compressions = getattr(self.metrics.metrics, "compressions", 0) + 1
                if metadata.key_topics == ["fallback"]:
                    self.metrics.metrics.compression_fallbacks = getattr(self.metrics.metrics, "compression_fallbacks", 0) + 1

                # Emit compression event with metadata
                await self._emit(
                    "compression_applied",
                    {
                        "before_tokens": metadata.original_tokens,
                        "after_tokens": metadata.compressed_tokens,
                        "compression_ratio": metadata.compression_ratio,
                        "original_message_count": metadata.original_message_count,
                        "compressed_message_count": metadata.compressed_message_count,
                        "key_topics": metadata.key_topics,
                        "fallback_used": metadata.key_topics == ["fallback"],
                    },
                )

                return compressed_messages

            except Exception as e:
                # Compression failed - continue without compression
                self.metrics.metrics.total_errors += 1
                await self._emit("error", {
                    "stage": "compression",
                    "message": str(e),
                })
                return history

        return history

    def _serialize_tools(self) -> List[Dict]:
        tools_spec: List[Dict] = []
        for t in self.tools.values():
            schema = {}
            try:
                schema = t.args_schema.model_json_schema()  # type: ignore[attr-defined]
            except Exception:
                schema = {"type": "object", "properties": {}}
            tools_spec.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": getattr(t, "description", ""),
                        "parameters": schema,
                    },
                }
            )
        return tools_spec

    def _to_tool_call(self, raw: Dict) -> ToolCall:
        # 允许 Rule/Mock LLM 输出简单 dict
        return ToolCall(id=str(raw.get("id", "call_0")), name=raw["name"], arguments=raw.get("arguments", {}))

    async def _execute_tool_batch(self, tool_calls_raw: List[Dict]) -> List[ToolResult]:
        tc_models = [self._to_tool_call(tc) for tc in tool_calls_raw]
        results: List[ToolResult] = []
        async for tr in self._execute_tool_calls_async(tc_models):
            results.append(tr)
        return results

    async def _execute_tool_calls_async(self, tool_calls: List[ToolCall]):
        async for tr in self.tool_pipeline.execute_calls(tool_calls):
            yield tr

    def _inject_system_prompt(self, history: List[Message], system_prompt: str) -> List[Message]:
        """注入或更新系统提示消息"""
        # 如果第一条是系统消息，则替换；否则在开头插入
        if history and history[0].role == "system":
            history[0] = Message(role="system", content=system_prompt)
        else:
            history.insert(0, Message(role="system", content=system_prompt))
        return history
