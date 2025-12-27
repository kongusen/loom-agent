"""
Agent Node (Fractal System)
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid

from loom.protocol.cloudevents import CloudEvent
from loom.protocol.interfaces import ReflectiveMemoryStrategy
from loom.node.base import Node
from loom.node.tool import ToolNode
from loom.kernel.dispatcher import Dispatcher
from loom.kernel.cognitive_state import (
    CognitiveState,
    ProjectionOperator,
    Thought,
    ThoughtState,
    Observable
)

from loom.interfaces.llm import LLMProvider
from loom.infra.llm import MockLLMProvider
from loom.interfaces.memory import MemoryInterface
from loom.memory.hierarchical import HierarchicalMemory


@dataclass
class ReflectionConfig:
    """
    Configuration for Memory Reflection (Human Factors Engineering).

    Framework DETECTS when reflection is needed.
    Developer CONFIGURES how reflection should behave.
    System EXECUTES the reflection according to config.
    """
    threshold: int = 20
    """Number of entries before reflection is triggered"""

    candidate_count: int = 10
    """Number of memory entries to include in reflection"""

    remove_count: int = 10
    """Number of entries to remove after consolidation"""

    prompt_template: str = "Summarize the following conversation segment into a concise knowledge entry:\n\n{history}"
    """Template for the reflection prompt. {history} will be replaced with actual history."""

    enabled: bool = True
    """Whether reflection is enabled"""


@dataclass
class ThinkingPolicy:
    """
    Policy for System 2 (Slow Thinking).
    Controls when to spawn ephemeral thought nodes.

    Implements Entropy Control (熵控制) from Cognitive Dynamics theory.

    Philosophy: Framework provides SUGGESTIONS, User has CONTROL.
    All limits can be disabled by setting to None or very large values.
    """
    enabled: bool = False
    max_thoughts: Optional[int] = None  # None = unlimited (user controls)
    max_depth: Optional[int] = None  # None = unlimited (user controls)
    total_token_budget: Optional[int] = None  # None = unlimited (user controls)
    thought_timeout: Optional[float] = None  # None = no timeout (user controls)
    trigger_words: List[str] = field(default_factory=list)  # e.g., ["analyze", "check", "deep"]
    spawn_threshold: float = 0.7  # Confidence threshold (conceptually)

    # Warning thresholds (soft limits for logging)
    warn_depth: int = 3
    warn_thoughts: int = 5
    warn_timeout: float = 10.0


class AgentNode(Node):
    """
    A Node that acts as an Intelligent Agent (MCP Client).

    Implements Cognitive Dynamics: Dual-Process streaming with controlled fractal thoughts.
    """

    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        role: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        tools: Optional[List[ToolNode]] = None,
        provider: Optional[LLMProvider] = None,
        memory: Optional[MemoryInterface] = None,
        enable_auto_reflection: bool = False,
        reflection_config: Optional[ReflectionConfig] = None,
        thinking_policy: Optional[ThinkingPolicy] = None,
        current_depth: int = 0,  # Track fractal depth for entropy control
        projection_strategy: str = "selective"  # Projection operator strategy
    ):
        super().__init__(node_id, dispatcher)
        self.role = role
        self.system_prompt = system_prompt
        self.known_tools = {t.tool_def.name: t for t in tools} if tools else {}
        self.memory = memory or HierarchicalMemory()
        self.provider = provider or MockLLMProvider()
        self.enable_auto_reflection = enable_auto_reflection
        self.reflection_config = reflection_config or ReflectionConfig()
        self.thinking_policy = thinking_policy or ThinkingPolicy()
        self.current_depth = current_depth
        self._active_thoughts: List[str] = []  # Track active thought node IDs
        self._tokens_used: int = 0  # Track token budget usage

        # Explicit Cognitive State Space (S ∈ R^N)
        self.cognitive_state = CognitiveState()

        # Explicit Projection Operator (π: S → O)
        self.projector = ProjectionOperator(strategy=projection_strategy)

    async def _spawn_thought(self, task: str) -> Optional[str]:
        """
        System 2: Spawn a new Ephemeral Node to think about a sub-task.

        Implements Configurable Entropy Control (熵控制):
        - Hard limits can be set by user (max_depth, max_thoughts, etc.)
        - Warning thresholds suggest best practices
        - User has FULL CONTROL over enforcement

        Returns the node_id of the spawned thought, or None if blocked by policy.
        """
        # 1. Policy Check: Is thinking enabled?
        if not self.thinking_policy.enabled:
            return None

        # 2. Entropy Control: Depth Limit (User configurable)
        if self.thinking_policy.max_depth is not None:
            if self.current_depth >= self.thinking_policy.max_depth:
                print(f"[Entropy Control] Depth limit reached ({self.current_depth}/{self.thinking_policy.max_depth})")
                return None

        # Warning: Approaching dangerous depth
        if self.current_depth >= self.thinking_policy.warn_depth:
            print(f"⚠️  [Warning] Deep recursion: depth={self.current_depth} (consider setting max_depth)")

        # 3. Entropy Control: Active Thought Limit (User configurable)
        if self.thinking_policy.max_thoughts is not None:
            if len(self._active_thoughts) >= self.thinking_policy.max_thoughts:
                print(f"[Entropy Control] Max concurrent thoughts reached ({len(self._active_thoughts)}/{self.thinking_policy.max_thoughts})")
                return None

        # Warning: Many active thoughts
        if len(self._active_thoughts) >= self.thinking_policy.warn_thoughts:
            print(f"⚠️  [Warning] Many active thoughts: {len(self._active_thoughts)} (consider setting max_thoughts)")

        # 4. Entropy Control: Token Budget (User configurable)
        if self.thinking_policy.total_token_budget is not None:
            if self._tokens_used >= self.thinking_policy.total_token_budget:
                print(f"[Entropy Control] Token budget exhausted ({self._tokens_used}/{self.thinking_policy.total_token_budget})")
                return None

        # 5. Trigger Analysis: Should we spawn a thought for this task?
        needs_thought = any(w in task.lower() for w in self.thinking_policy.trigger_words)
        if not needs_thought:
            return None

        # 6. Spawn Ephemeral Thought Node
        thought_id = f"thought-{str(uuid.uuid4())[:8]}"

        # Add thought to cognitive state space (S)
        thought = Thought(
            id=thought_id,
            task=task,
            state=ThoughtState.RUNNING,
            depth=self.current_depth + 1,
            metadata={"parent": self.node_id}
        )
        self.cognitive_state.add_thought(thought)

        from loom.protocol.cloudevents import EventType

        # Notify Kernel
        await self.dispatcher.dispatch(CloudEvent.create(
            source=self.source_uri,
            type=EventType.NODE_REGISTER,
            data={
                "node_id": thought_id,
                "parent": self.node_id,
                "depth": self.current_depth + 1,
                "state_dimensionality": self.cognitive_state.dimensionality()
            }
        ))

        # Create Fractal Child Node (Self-similar but depth-aware)
        thought_node = AgentNode(
            node_id=thought_id,
            dispatcher=self.dispatcher,
            role="Deep Thinker",
            system_prompt="You are a deep thinking sub-process. Analyze the following.",
            provider=self.provider,  # Inherit provider
            thinking_policy=ThinkingPolicy(enabled=False),  # Child nodes don't spawn by default
            current_depth=self.current_depth + 1  # Increment depth
        )

        # Register with dispatcher (auto-subscribes to event bus)
        await self.dispatcher.register_ephemeral(thought_node)

        # Track active thought
        self._active_thoughts.append(thought_id)

        print(f"[System 2] Thought spawned: {thought_id} (depth={self.current_depth + 1}, active={len(self._active_thoughts)}, S_dim={self.cognitive_state.dimensionality()})")

        return thought_id

    async def _perform_reflection(self) -> None:
        """
        Check and perform metabolic memory reflection.

        FIXED: Now uses developer-configured parameters instead of hardcoded values.
        Framework DETECTS, Developer CONFIGURES, System EXECUTES.

        FIXED: Uses Protocol check instead of isinstance for better abstraction.
        """
        # 0. Check if reflection is enabled
        if not self.reflection_config.enabled:
            return

        # 1. Check if memory supports reflection (Protocol-First)
        if not isinstance(self.memory, ReflectiveMemoryStrategy):
            # Memory doesn't support reflection, skip silently
            return

        # 2. Check if memory needs reflection (Framework DETECTS)
        if not self.memory.should_reflect(threshold=self.reflection_config.threshold):
            return

        # 3. Get candidates (Developer CONFIGURED count)
        candidates = self.memory.get_reflection_candidates(
            count=self.reflection_config.candidate_count
        )

        # 4. Summarize with LLM (Developer CONFIGURED prompt)
        history_text = "\n".join([f"{e.role}: {e.content}" for e in candidates])
        prompt = self.reflection_config.prompt_template.format(history=history_text)

        try:
            # We use a separate call (not affecting main context)
            response = await self.provider.chat([{"role": "user", "content": prompt}])
            summary = response.content

            # 5. Consolidate (Developer CONFIGURED remove_count)
            await self.memory.consolidate(
                summary,
                remove_count=self.reflection_config.remove_count
            )

            # 6. Emit Event
            await self.dispatcher.dispatch(CloudEvent.create(
                source=self.source_uri,
                type="agent.reflection",
                data={"summary": summary},
            ))
        except Exception as e:
            # Reflection shouldn't crash the agent
            # FIXED: Should emit event instead of just print
            error_event = CloudEvent.create(
                source=self.source_uri,
                type="agent.reflection.failed",
                data={"error": str(e)}
            )
            await self.dispatcher.dispatch(error_event)

    async def process(self, event: CloudEvent) -> Any:
        """
        Agent Loop with Memory (Dual Process Support):
        1. Receive Task -> Add to Memory
        2. System 1: Stream "Speech" (Fast Path)
        3. System 2: Spawn "Thoughts" (Slow Path) - TODO
        """
        # Hook: Auto Reflection
        if self.enable_auto_reflection:
             await self._perform_reflection()
             
        # Detect if we should use streaming (System 1)
        # For now, default to True if not explicitly disabled
        # In future, this could be dynamic based on complexity
        use_streaming = self.provider.__class__.__name__ != "MockLLMProvider" or True
        
        if use_streaming:
            return await self._execute_stream_loop(event)
        else:
            return await self._execute_loop(event)

    async def _execute_stream_loop(self, event: CloudEvent) -> Any:
        """
        System 1: Streaming Execution Loop.
        Emits 'agent.stream.chunk' events for immediate feedback.
        """
        from loom.protocol.cloudevents import EventType
        
        task = event.data.get("task", "") or event.data.get("content", "")
        max_iterations = event.data.get("max_iterations", 5)
        
        # 1. Perceive (Add to Memory)
        await self.memory.add("user", task)
        
        iterations = 0
        final_response = ""
        
        while iterations < max_iterations:
            iterations += 1
            
            # 2. Recall (Get Context)
            history = await self.memory.get_recent(limit=20)
            messages = [{"role": "system", "content": self.system_prompt}] + history
            
            # 3. Think (Stream + Dual Process)
            mcp_tools = [t.tool_def.model_dump() for t in self.known_tools.values()]
            llm_config = event.extensions.get("llm_config_override")
            
            # System 2: Spark Thought (Async/Parallel)
            # We trigger it BEFORE starting stream, or PARALLEL
            thought_id = await self._spawn_thought(task)
            thought_task = None
            if thought_id:
                # Dispatch task to thought node (fire and forget or await?)
                # For "Thinking while Speaking", it should be parallel.
                # We start a background task to await result
                import asyncio
                thought_task = asyncio.create_task(self.call(
                    target_node=f"/node/{thought_id}",
                    data={"task": f"Analyze deeply: {task}"}
                ))
            
            # Streaming Buffer
            current_content = ""

            # Start Stream (System 1)
            # UPGRADED: Now using structured StreamChunk interface
            # Supports real-time thought injection during streaming

            try:
                stream = self.provider.stream_chat(messages, tools=mcp_tools)
                thought_injected = False  # Track if thought has been injected
                tool_calls_buffer = []  # Buffer for tool calls in stream

                async for chunk in stream:
                    # Handle different chunk types
                    if chunk.type == "text":
                        text_content = str(chunk.content)
                        current_content += text_content

                        # Emit Chunk Event (System 1 Output)
                        await self.dispatcher.dispatch(CloudEvent.create(
                            source=self.source_uri,
                            type=EventType.STREAM_CHUNK,
                            data={"chunk": text_content, "index": len(current_content)},
                            traceparent=event.traceparent
                        ))

                    elif chunk.type == "tool_call":
                        # NEW: Handle tool calls in streaming mode
                        tool_call = chunk.content if isinstance(chunk.content, dict) else {}
                        tool_calls_buffer.append(tool_call)
                        print(f"[Stream Tool Call] Received: {tool_call.get('name', 'unknown')}")

                    elif chunk.type == "thought_injection":
                        # System 2 thought has been injected into the stream
                        print(f"[Real-Time Projection] Thought injected: {chunk.content}")

                    elif chunk.type == "done":
                        # Stream complete
                        break

                    # Real-time injection point: Check if thought finished while streaming
                    if thought_task and not thought_injected and thought_task.done():
                        try:
                            result = thought_task.result()
                            # Inject thought into current context (for next chunk generation)
                            # This is the theoretical π(S) → O projection happening IN REAL-TIME
                            print(f"[Real-Time Projection] Thought completed mid-stream: {result}")
                            thought_injected = True

                            # Emit injection event
                            await self.dispatcher.dispatch(CloudEvent.create(
                                source=self.source_uri,
                                type=EventType.THOUGHT_SPARK,
                                data={"spark": result, "injected_at": len(current_content)}
                            ))

                        except Exception as e:
                            print(f"[Projection Error] {e}")

                final_text = current_content

                # NEW: Process tool calls if any were received in stream
                if tool_calls_buffer:
                    # Record the assistant message with tool calls
                    await self.memory.add("assistant", final_text or "", metadata={
                        "tool_calls": tool_calls_buffer
                    })

                    # Execute each tool call
                    for tc in tool_calls_buffer:
                        tc_name = tc.get("name")
                        tc_args = tc.get("arguments", {})

                        # Emit thought event
                        await self.dispatcher.dispatch(CloudEvent.create(
                            source=self.source_uri,
                            type="agent.thought",
                            data={"thought": f"Calling {tc_name}", "tool_call": tc},
                            traceparent=event.traceparent
                        ))

                        target_tool = self.known_tools.get(tc_name)
                        if target_tool:
                            try:
                                tool_result = await self.call(
                                    target_node=target_tool.source_uri,
                                    data={"arguments": tc_args}
                                )

                                # Extract result content
                                result_content = tool_result.get("result", str(tool_result)) if isinstance(tool_result, dict) else str(tool_result)

                                # Add Result to Memory
                                await self.memory.add("tool", str(result_content), metadata={
                                    "tool_name": tc_name,
                                    "tool_call_id": tc.get("id")
                                })
                            except Exception as e:
                                err_msg = f"Tool {tc_name} failed: {str(e)}"
                                await self.memory.add("system", err_msg)
                        else:
                            err_msg = f"Tool {tc_name} not found."
                            await self.memory.add("system", err_msg)

                    # Continue loop to process tool results
                    # Important: We must clear the tool buffer so we don't re-execute
                    tool_calls_buffer = []  
                    continue

                # Fallback: If streaming produced no content (e.g., tool call scenario),
                # fall back to non-streaming mode
                if not final_text.strip():
                    print("[Stream] No content from stream, falling back to chat()")
                    return await self._execute_loop(event)

                # Async Projection with Configurable Timeout
                if thought_task and thought_id:
                    async def _project_thought():
                        try:
                            # User-configurable timeout (None = unlimited)
                            timeout = self.thinking_policy.thought_timeout

                            if timeout is not None:
                                result = await asyncio.wait_for(thought_task, timeout=timeout)
                            else:
                                # No timeout - wait indefinitely (user choice)
                                result = await thought_task

                            # Update cognitive state: mark thought as completed
                            self.cognitive_state.complete_thought(thought_id, result)

                            # PROJECTION: π(S) → O
                            # Use explicit projection operator to collapse state
                            observable = self.projector.collapse(self.cognitive_state)

                            # 1. Emit Spark Event (State Space Collapse)
                            await self.dispatcher.dispatch(CloudEvent.create(
                               source=self.source_uri,
                               type=EventType.THOUGHT_SPARK,
                               data={
                                   "spark": result,
                                   "observable": observable.content,
                                   "state_dimensionality": self.cognitive_state.dimensionality(),
                                   "projection_strategy": self.projector.strategy
                               }
                            ))

                            # 2. Memory Consolidation (Projection into Observable Manifold)
                            await self.memory.add("system", observable.content, metadata={
                                "type": "thought_spark",
                                "thought_id": thought_id,
                                "depth": self.current_depth + 1,
                                "projection_metadata": observable.metadata
                            })

                            # 3. Cleanup (Resource Release)
                            self.cognitive_state.remove_thought(thought_id)
                            self.dispatcher.cleanup_ephemeral(thought_id)
                            if thought_id in self._active_thoughts:
                                self._active_thoughts.remove(thought_id)

                            print(f"[Projection] π(S) → O: {thought_id} projected (S_dim={self.cognitive_state.dimensionality()})")

                        except asyncio.TimeoutError:
                            # Thought exceeded timeout - force cleanup
                            thought = self.cognitive_state.get_thought(thought_id)
                            if thought:
                                thought.state = ThoughtState.TIMEOUT
                            print(f"[Entropy Control] Thought {thought_id} timed out after {timeout}s")
                            self.cognitive_state.remove_thought(thought_id)
                            self.dispatcher.cleanup_ephemeral(thought_id)
                            if thought_id in self._active_thoughts:
                                self._active_thoughts.remove(thought_id)

                        except Exception as e:
                            # Unexpected failure - cleanup and log
                            thought = self.cognitive_state.get_thought(thought_id)
                            if thought:
                                thought.state = ThoughtState.FAILED
                            print(f"[Kernel] Thought {thought_id} failed projection: {e}")
                            self.cognitive_state.remove_thought(thought_id)
                            self.dispatcher.cleanup_ephemeral(thought_id)
                            if thought_id in self._active_thoughts:
                                self._active_thoughts.remove(thought_id)

                    # Fire and forget the projector
                    asyncio.create_task(_project_thought())
                
                # Check if the response looks like a tool call (naive check for now as stream interface is limited)
                # Ideally, we would parse structured output. For now, we assume System 1 is mostly chat.
                # If we want to support tools in stream, we should use a more advanced provider method.
                # Fallback: If no content, maybe retry with chat()? 
                # For this implementation, we treat streamed text as the final answer.
                
                # 4. Act (Final Answer)
                await self.memory.add("assistant", final_text)
                final_response = final_text
                break
                
            except Exception as e:
                # Fallback to non-streaming if stream fails
                print(f"Streaming failed, falling back: {e}")
                return await self._execute_loop(event)
        
        if not final_response and iterations >= max_iterations:
             final_response = "Error: Maximum iterations reached without final answer."
             await self.memory.add("system", final_response)
             
        # Hook: Check reflection after new memories added
        if self.enable_auto_reflection:
             await self._perform_reflection()

        return {"response": final_response, "iterations": iterations}

    async def _execute_loop(self, event: CloudEvent) -> Any:
        """
        Execute the standard ReAct Loop (Non-streaming).
        """
        from loom.protocol.cloudevents import EventType
        
        task = event.data.get("task", "") or event.data.get("content", "")
        max_iterations = event.data.get("max_iterations", 5)
        
        # 1. Perceive (Add to Memory)
        await self.memory.add("user", task)
        
        iterations = 0
        final_response = ""
        
        while iterations < max_iterations:
            iterations += 1
            
            # 2. Recall (Get Context)
            history = await self.memory.get_recent(limit=20)
            messages = [{"role": "system", "content": self.system_prompt}] + history
            
            # 3. Think
            mcp_tools = [t.tool_def.model_dump() for t in self.known_tools.values()]
            
            # Check for Adaptive Control Overrides (from Interceptors)
            llm_config = event.extensions.get("llm_config_override")
            
            response = await self.provider.chat(messages, tools=mcp_tools, config=llm_config)
            final_text = response.content
            
            # 4. Act (Tool Usage or Final Answer)
            if response.tool_calls:
                # Record the "thought" / call intent
                # ALWAYS store assistant message with tool_calls (even if content is empty)
                await self.memory.add("assistant", final_text or "", metadata={
                    "tool_calls": response.tool_calls
                })
                
                # Execute tools (Parallel support possible, here sequential)
                for tc in response.tool_calls:
                    tc_name = tc.get("name")
                    tc_args = tc.get("arguments")
                    
                    # Emit thought event
                    await self.dispatcher.dispatch(CloudEvent.create(
                        source=self.source_uri,
                        type="agent.thought", # Could use EventType.THOUGHT_SPARK conceptually? Keeping generic for now.
                        data={"thought": f"Calling {tc_name}", "tool_call": tc},
                        traceparent=event.traceparent
                    ))
                    
                    target_tool = self.known_tools.get(tc_name)

                    if target_tool:
                        # FIXED: Use self.call() to invoke through event bus
                        # This ensures:
                        # - Tool calls are visible in Studio
                        # - Interceptors can control tool execution
                        # - Supports distributed tool nodes
                        # - Maintains fractal uniformity
                        try:
                            tool_result = await self.call(
                                target_node=target_tool.source_uri,
                                data={"arguments": tc_args}
                            )

                            # Extract result content
                            if isinstance(tool_result, dict):
                                result_content = tool_result.get("result", str(tool_result))
                            else:
                                result_content = str(tool_result)

                            # Add Result to Memory (Observation)
                            await self.memory.add("tool", str(result_content), metadata={
                                "tool_name": tc_name,
                                "tool_call_id": tc.get("id")
                            })
                        except Exception as e:
                            # Tool call failed through event bus
                            err_msg = f"Tool {tc_name} failed: {str(e)}"
                            await self.memory.add("system", err_msg)
                    else:
                        err_msg = f"Tool {tc_name} not found."
                        await self.memory.add("system", err_msg)
                
                # Loop continues to reflect on tool results
                continue
            
            else:
                # Final Answer
                await self.memory.add("assistant", final_text)
                final_response = final_text
                break
        
        if not final_response and iterations >= max_iterations:
             final_response = "Error: Maximum iterations reached without final answer."
             await self.memory.add("system", final_response)
             
        # Hook: Check reflection after new memories added
        if self.enable_auto_reflection:
             await self._perform_reflection()

        return {"response": final_response, "iterations": iterations}

