"""
执行引擎 - 递归状态机的核心

职责：
1. 递归执行管理
2. 工具调用协调
3. LLM 交互
4. Context 管理集成
"""

from __future__ import annotations
from typing import List, Optional, Any, Dict, Tuple
import asyncio
import json

from loom.core.message import Message, get_message_history, build_history_chain
from loom.core.context import ContextManager
from loom.core.errors import (
    ExecutionError,
    ToolError,
    RecursionError as LoomRecursionError,
    LLMError,
)
from loom.core.events import (
    AgentEvent,
    AgentEventType,
    create_agent_start_event,
    create_agent_end_event,
    create_agent_error_event,
    create_llm_start_event,
    create_llm_end_event,
    create_tool_start_event,
    create_tool_end_event,
)
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool
from loom.interfaces.event_producer import EventProducer


# ===== 工具结果序列化（v0.1.9 新增）=====


def serialize_tool_result(result: Any) -> Tuple[str, Dict[str, Any]]:
    """
    序列化工具结果并保留类型信息（v0.1.9 新增）

    将工具返回值序列化为字符串，同时在 metadata 中保留结构化类型信息，
    确保 LLM 能够理解和解析复杂的工具结果。

    Args:
        result: 工具返回值（任意类型）

    Returns:
        (content_str, metadata_dict) 元组：
        - content_str: 序列化后的字符串内容
        - metadata_dict: 包含类型和格式信息的元数据

    Supported Types:
        - dict, list: JSON 序列化（保留结构）
        - str: 纯文本
        - None: 空字符串
        - Exception: 结构化错误对象
        - 其他: repr() 降级

    Example:
        >>> result = {"name": "Alice", "age": 30}
        >>> content, meta = serialize_tool_result(result)
        >>> content  # '{"name": "Alice", "age": 30}'
        >>> meta     # {"content_type": "application/json", ...}
    """
    metadata: Dict[str, Any] = {}

    if isinstance(result, dict) or isinstance(result, list):
        # 结构化数据：JSON 序列化
        try:
            content = json.dumps(result, ensure_ascii=False, indent=2)
            metadata["content_type"] = "application/json"
            metadata["result_type"] = type(result).__name__
        except (TypeError, ValueError) as e:
            # 降级：无法序列化的对象使用 repr()
            content = repr(result)
            metadata["content_type"] = "text/plain"
            metadata["result_type"] = type(result).__name__
            metadata["serialization_error"] = str(e)

    elif isinstance(result, str):
        # 纯文本
        content = result
        metadata["content_type"] = "text/plain"
        metadata["result_type"] = "str"

    elif result is None:
        # 空结果
        content = ""
        metadata["content_type"] = "text/plain"
        metadata["result_type"] = "NoneType"

    elif isinstance(result, Exception):
        # 异常对象：结构化错误表示
        content = json.dumps(
            {
                "error": type(result).__name__,
                "message": str(result),
                "args": result.args,
            },
            ensure_ascii=False,
            indent=2,
        )
        metadata["content_type"] = "application/json"
        metadata["result_type"] = "Exception"
        metadata["error"] = True

    else:
        # 降级：其他类型使用 repr()
        content = repr(result)
        metadata["content_type"] = "text/plain"
        metadata["result_type"] = type(result).__name__

    return content, metadata


class AgentExecutor:
    """
    Agent 执行引擎

    核心特性：
    - 递归调用管理
    - 自动工具调用
    - Context 自动管理
    - 错误处理

    这是 Agent 的内部实现，用户通常不需要直接使用这个类。
    """

    def __init__(
        self,
        agent_name: str,
        llm: BaseLLM,
        tools: Optional[List[BaseTool]] = None,
        context_manager: Optional[ContextManager] = None,
        max_recursion_depth: int = 20,
        system_prompt: Optional[str] = None,
        event_handler: Optional[EventProducer] = None,
    ):
        """
        初始化执行引擎

        Args:
            agent_name: Agent 名称
            llm: LLM 实例
            tools: 工具列表
            context_manager: Context 管理器
            max_recursion_depth: 最大递归深度
            system_prompt: 系统提示词
            event_handler: 事件处理器（可选）
        """
        self.agent_name = agent_name
        self.llm = llm
        self.tools = tools or []
        self.context_manager = context_manager or ContextManager()
        self.max_recursion_depth = max_recursion_depth
        self.system_prompt = system_prompt
        self.event_handler = event_handler

        # 递归状态
        self.current_depth = 0

        # 统计信息
        self.stats = {
            "total_llm_calls": 0,
            "total_tool_calls": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_errors": 0,
        }

    async def execute(self, message: Message) -> Message:
        """
        执行一轮 Agent 推理

        流程：
        1. 检查递归深度
        2. 准备 Context（压缩、重建）
        3. LLM 推理
        4. 处理工具调用
        5. 递归执行（如果需要）
        6. 返回结果

        Args:
            message: 输入消息

        Returns:
            响应消息

        Raises:
            ExecutionError: 执行错误
            RecursionError: 递归深度超限
        """
        # 发出 agent_start 事件
        if self.event_handler:
            await self._emit_event(
                create_agent_start_event(
                    agent_name=self.agent_name,
                    data={"input": message.content[:100], "depth": self.current_depth},
                )
            )

        # 1. 检查递归深度
        self.current_depth += 1
        if self.current_depth > self.max_recursion_depth:
            error = LoomRecursionError(
                f"Max recursion depth exceeded",
                current_depth=self.current_depth,
                max_depth=self.max_recursion_depth,
            )
            # 发出错误事件
            if self.event_handler:
                await self._emit_event(
                    create_agent_error_event(
                        agent_name=self.agent_name, error=error, data={"depth": self.current_depth}
                    )
                )
            self.stats["total_errors"] += 1
            raise error

        try:
            # 2. 添加 system prompt（如果需要）
            if self.system_prompt and not self._has_system_prompt(message):
                message = self._add_system_prompt(message)

            # 3. 准备 Context
            prepared_message = await self.context_manager.prepare(message)

            # 4. LLM 推理
            response = await self._call_llm(prepared_message)
            self.stats["total_llm_calls"] += 1

            # 5. 检查是否需要工具调用
            if self._has_tool_calls(response):
                # 执行工具
                tool_results = await self._execute_tools(response.tool_calls)
                self.stats["total_tool_calls"] += len(response.tool_calls)

                # 构建新 Message（包含工具结果）
                new_message = self._build_tool_results_message(
                    prepared_message, response, tool_results
                )

                # 6. 递归调用 - 关键！
                return await self.execute(new_message)

            # 7. 返回最终结果
            # 发出 agent_end 事件
            if self.event_handler:
                await self._emit_event(
                    create_agent_end_event(
                        agent_name=self.agent_name,
                        data={
                            "output": response.content[:100],
                            "depth": self.current_depth,
                            "llm_calls": self.stats["total_llm_calls"],
                            "tool_calls": self.stats["total_tool_calls"],
                        },
                    )
                )

            return response

        except LoomRecursionError:
            # 递归错误直接抛出
            raise

        except Exception as e:
            self.stats["total_errors"] += 1
            # 发出错误事件
            if self.event_handler:
                await self._emit_event(
                    create_agent_error_event(
                        agent_name=self.agent_name,
                        error=e,
                        data={"depth": self.current_depth, "error_type": type(e).__name__},
                    )
                )
            raise ExecutionError(
                f"Execution failed: {str(e)}",
                agent_name=self.agent_name,
                details={"error_type": type(e).__name__},
            ) from e

        finally:
            self.current_depth -= 1

    def _has_system_prompt(self, message: Message) -> bool:
        """检查是否已有 system prompt（v0.1.9: 使用安全提取）"""
        history = get_message_history(message)
        return any(m.role == "system" for m in history)

    def _add_system_prompt(self, message: Message) -> Message:
        """添加 system prompt（v0.1.9: 使用安全提取）"""
        system_message = Message(
            role="system", content=self.system_prompt, name=self.agent_name
        )

        # 如果有历史，添加到历史最前面
        history = get_message_history(message)
        if len(history) > 1 or (len(history) == 1 and history[0] != message):
            # 已有历史记录（不只是 [message]）
            new_history = [system_message] + message.history
            return message.with_history(new_history)
        else:
            # 无历史或只有自己，创建新历史
            return message.with_history([system_message, message])

    async def _call_llm(self, message: Message) -> Message:
        """
        调用 LLM

        Args:
            message: 输入消息

        Returns:
            LLM 响应消息

        Raises:
            LLMError: LLM 调用失败
        """
        # 发出 llm_start 事件
        if self.event_handler:
            await self._emit_event(
                create_llm_start_event(
                    llm_name=getattr(self.llm, "model_name", "unknown"),
                    data={"agent_name": self.agent_name},
                )
            )

        try:
            # 转换为 LLM 格式
            llm_messages = self._to_llm_messages(message)

            # 调用 LLM（stream 方式）
            content_parts = []
            tool_calls = None  # v0.1.9: 改为 None（而非空列表）

            async for event in self.llm.stream(
                messages=llm_messages,
                tools=self._get_tool_schemas() if self.tools else None,
            ):
                if event["type"] == "content_delta":
                    content_parts.append(event["content"])
                elif event["type"] == "tool_calls":
                    tool_calls = event["tool_calls"]

            # 构建响应 Message（v0.1.9: 不可变构造，所有字段通过构造函数传递）
            response = Message(
                role="assistant",
                content="".join(content_parts),
                name=self.agent_name,
                tool_calls=tool_calls,  # v0.1.9: 构造时传递，不事后赋值
            )

            # 发出 llm_end 事件
            if self.event_handler:
                await self._emit_event(
                    create_llm_end_event(
                        llm_name=getattr(self.llm, "model_name", "unknown"),
                        data={
                            "agent_name": self.agent_name,
                            "has_tool_calls": bool(tool_calls),
                            "num_tool_calls": len(tool_calls) if tool_calls else 0,
                        },
                    )
                )

            return response

        except Exception as e:
            raise LLMError(
                f"LLM call failed: {str(e)}",
                llm_name=getattr(self.llm, "model_name", "unknown"),
            ) from e

    def _to_llm_messages(self, message: Message) -> List[Dict]:
        """将 Message 转换为 LLM 格式（v0.1.9: 使用安全提取）"""
        history = get_message_history(message)

        llm_messages = []
        for m in history:
            llm_msg = {"role": m.role, "content": m.content}

            # 添加可选字段
            if hasattr(m, "name") and m.name:
                llm_msg["name"] = m.name

            if hasattr(m, "tool_calls") and m.tool_calls:
                llm_msg["tool_calls"] = m.tool_calls

            if hasattr(m, "tool_call_id") and m.tool_call_id:
                llm_msg["tool_call_id"] = m.tool_call_id

            llm_messages.append(llm_msg)

        return llm_messages

    def _has_tool_calls(self, message: Message) -> bool:
        """检查消息是否包含工具调用"""
        return hasattr(message, "tool_calls") and message.tool_calls

    async def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        执行工具调用（并行执行以提升性能）

        Args:
            tool_calls: 工具调用列表

        Returns:
            工具结果列表
        """
        async def execute_single_tool(tc: Dict) -> Dict:
            """
            执行单个工具调用（带 Ephemeral Memory 支持）

            流程：
            1. 添加到 ephemeral memory（工具调用中间状态）
            2. 执行工具
            3. 清理 ephemeral memory
            """
            tool_id = tc["id"]
            tool_name = tc["name"]
            tool_args = tc.get("arguments", {})

            # Ephemeral Memory key
            ephemeral_key = f"tool_{tool_id}"

            # 获取 memory（如果有）
            memory = getattr(self.context_manager, "memory", None)

            # 1. 记录工具调用开始到 Ephemeral Memory
            if memory and hasattr(memory, "add_ephemeral"):
                try:
                    await memory.add_ephemeral(
                        key=ephemeral_key,
                        content=f"Calling {tool_name} with args: {tool_args}",
                        metadata={
                            "tool_name": tool_name,
                            "tool_call_id": tool_id,
                            "status": "in_progress",
                        },
                    )
                except Exception as e:
                    # Ephemeral memory failure should not block execution
                    logger.debug(f"Failed to add ephemeral memory: {e}")

            # 发出 tool_start 事件
            if self.event_handler:
                await self._emit_event(
                    create_tool_start_event(
                        tool_name=tool_name,
                        data={
                            "agent_name": self.agent_name,
                            "tool_call_id": tool_id,
                            "arguments": tool_args,
                        },
                    )
                )

            # 查找工具
            tool = self._find_tool(tool_name)
            if not tool:
                result = {
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": f"Error: Tool '{tool_name}' not found. Available tools: {[t.name for t in self.tools]}",
                }

                # 清理 Ephemeral Memory（错误时也要清理）
                if memory and hasattr(memory, "clear_ephemeral"):
                    try:
                        await memory.clear_ephemeral(key=ephemeral_key)
                    except Exception:
                        pass

                # 发出 tool_end 事件（错误）
                if self.event_handler:
                    await self._emit_event(
                        create_tool_end_event(
                            tool_name=tool_name,
                            data={
                                "agent_name": self.agent_name,
                                "tool_call_id": tool_id,
                                "success": False,
                                "error": "Tool not found",
                            },
                        )
                    )
                return result

            # 2. 执行工具
            try:
                tool_result = await tool.execute(**tool_args)

                # v0.1.9: 结构化序列化工具结果
                content, result_metadata = serialize_tool_result(tool_result)

                result = {
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": content,
                    "metadata": result_metadata,  # v0.1.9: 保留类型信息
                }

                # 3. 清理 Ephemeral Memory（成功时）
                if memory and hasattr(memory, "clear_ephemeral"):
                    try:
                        await memory.clear_ephemeral(key=ephemeral_key)
                    except Exception as e:
                        logger.debug(f"Failed to clear ephemeral memory: {e}")

                # 发出 tool_end 事件（成功）
                if self.event_handler:
                    await self._emit_event(
                        create_tool_end_event(
                            tool_name=tool_name,
                            data={
                                "agent_name": self.agent_name,
                                "tool_call_id": tool_id,
                                "success": True,
                            },
                        )
                    )
                return result

            except Exception as e:
                # v0.1.9: 结构化序列化异常
                content, error_metadata = serialize_tool_result(e)

                result = {
                    "tool_call_id": tool_id,
                    "role": "tool",
                    "name": tool_name,
                    "content": content,
                    "metadata": error_metadata,  # v0.1.9: 结构化错误信息
                }

                # 清理 Ephemeral Memory（错误时也要清理）
                if memory and hasattr(memory, "clear_ephemeral"):
                    try:
                        await memory.clear_ephemeral(key=ephemeral_key)
                    except Exception:
                        pass

                # 发出 tool_end 事件（错误）
                if self.event_handler:
                    await self._emit_event(
                        create_tool_end_event(
                            tool_name=tool_name,
                            data={
                                "agent_name": self.agent_name,
                                "tool_call_id": tool_id,
                                "success": False,
                                "error": str(e),
                            },
                        )
                    )
                return result

        # 并行执行所有工具调用
        results = await asyncio.gather(*[execute_single_tool(tc) for tc in tool_calls])

        return list(results)

    def _find_tool(self, name: str) -> Optional[BaseTool]:
        """查找工具"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None

    def _get_tool_schemas(self) -> List[Dict]:
        """获取工具的 schema"""
        return [tool.to_schema() for tool in self.tools]

    def _build_tool_results_message(
        self, original_message: Message, assistant_message: Message, tool_results: List[Dict]
    ) -> Message:
        """
        构建包含工具结果的新消息

        Args:
            original_message: 原始消息
            assistant_message: Assistant 消息（包含 tool_calls）
            tool_results: 工具结果

        Returns:
            新消息（包含完整历史）
        """
        # v0.1.9: 使用安全提取和不可变链条构建
        history = get_message_history(original_message)

        # 添加 assistant 消息
        history = build_history_chain(history, assistant_message)

        # 添加工具结果消息
        for result in tool_results:
            tool_message = Message(
                role="tool",
                content=result["content"],
                name=result.get("name"),
                tool_call_id=result.get("tool_call_id"),
                metadata=result.get("metadata", {}),  # v0.1.9: 保留结构化元数据
                parent_id=assistant_message.id,  # 链接到 assistant 消息
            )
            history = build_history_chain(history, tool_message)

        # 创建新消息（最后一个是工具结果）
        last_tool_result = history[-1]
        return last_tool_result.with_history(history)

    def reset(self) -> None:
        """重置执行状态"""
        self.current_depth = 0
        self.stats = {
            "total_llm_calls": 0,
            "total_tool_calls": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_errors": 0,
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            "agent_name": self.agent_name,
            "current_depth": self.current_depth,
            "max_depth": self.max_recursion_depth,
            "num_tools": len(self.tools),
            "context_stats": self.context_manager.get_stats(),
            # 新增统计
            "total_llm_calls": self.stats["total_llm_calls"],
            "total_tool_calls": self.stats["total_tool_calls"],
            "total_tokens_input": self.stats["total_tokens_input"],
            "total_tokens_output": self.stats["total_tokens_output"],
            "total_errors": self.stats["total_errors"],
        }

    async def _emit_event(self, event: AgentEvent) -> None:
        """
        发出事件

        Args:
            event: 事件对象
        """
        if self.event_handler:
            await self.event_handler.emit(event)
