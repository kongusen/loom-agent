"""
Agent Node (Fractal System)
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import uuid
import json

from loom.protocol.cloudevents import CloudEvent, EventType
from loom.node.base import Node
from loom.node.tool import ToolNode
from loom.kernel.core import Dispatcher, CognitiveState, ProjectionOperator, Thought, ThoughtState

from loom.llm import LLMProvider, MockLLMProvider

# New Memory System
from loom.memory.core import LoomMemory
from loom.memory.context import ContextAssembler, ContextManager
from loom.memory.types import (
    MemoryUnit, MemoryTier, MemoryType,
    ContextProjection
)
from loom.config.memory import ContextConfig, CurationConfig
from loom.tools.registry import ToolRegistry

# System 1/2 Components
from loom.cognition.router import QueryClassifier, AdaptiveRouter, SystemType, RoutingDecision
from loom.config.router import RouterConfig
from loom.config.cognitive import CognitiveConfig
from loom.cognition.confidence import ConfidenceEstimator
from loom.memory.system_strategies import System1Strategy, System2Strategy

# Utilities
from loom.utils.normalization import DataNormalizer
from loom.utils.formatting import ErrorFormatter

# Configuration
from loom.config.execution import ExecutionConfig
from loom.config.models import AgentConfig as AgentMetaConfig
from loom.config.fractal import FractalConfig


from loom.kernel.core import ToolExecutor

@dataclass
class ReflectionConfig:
    enabled: bool = False
    interval: int = 5 

    
@dataclass
class ThinkingPolicy:
    enabled: bool = False 


class AgentNode(Node):
    """
    Agent Node V3 with System 1/2 Architecture.
    
    Features:
    - LoomMemory Integration (L1-L4)
    - Dual Context Managers (System 1 / System 2)
    - Metacognitive Routing (Adaptive)
    - Fractal Inheritance
    """

    def __init__(
        self,
        node_id: str,
        dispatcher: Dispatcher,
        role: str = "Assistant",
        system_prompt: str = "You are a helpful assistant.",
        tools: Optional[List[ToolNode]] = None,
        provider: Optional[LLMProvider] = None,
        cognitive_config: Optional[CognitiveConfig] = None,
        execution_config: Optional[ExecutionConfig] = None,
        context_projection: Optional[ContextProjection] = None,
        enable_auto_reflection: bool = False,
        reflection_config: Optional[ReflectionConfig] = None,
        thinking_policy: Optional[ThinkingPolicy] = None,
        current_depth: int = 0,
        projection_strategy: str = "selective",
        fractal_config: Optional['FractalConfig'] = None
    ):
        super().__init__(node_id, dispatcher)
        self.role = role
        self.system_prompt = system_prompt

        # Fractal configuration (inlined from FractalMixin)
        self._fractal_config: Optional[FractalConfig] = None
        if fractal_config:
            self.set_fractal_config(fractal_config)


        # execution config
        self.execution_config = execution_config or ExecutionConfig.default()

        # Unified Cognitive Configuration
        self.cognitive_config = cognitive_config or CognitiveConfig.default()

        # Tools
        # We maintain support for legacy known_tools while also using registry
        self.known_tools: Dict[str, ToolNode] = {t.tool_def.name: t for t in tools} if tools else {}
        self.tool_registry = ToolRegistry()

        # Initialize Orchestrator and Synthesizer for explicit delegation
        # Use get_fractal_config() from mixin
        f_config = self.get_fractal_config()
        if f_config and f_config.enable_explicit_delegation:
            from loom.kernel.fractal import FractalOrchestrator, OrchestratorConfig
            from loom.kernel.fractal import Synthesizer as ResultSynthesizer
            from loom.kernel.fractal import SynthesisStrategy as SynthesisConfig

            orchestrator_config = OrchestratorConfig(
                allow_recursive_delegation=f_config.allow_recursive_delegation,
                max_recursive_depth=f_config.max_recursive_depth,
                tool_blacklist=f_config.child_tool_blacklist,
                default_child_token_budget=f_config.default_child_token_budget,
                max_concurrent_children=f_config.max_concurrent_children
            )

            synthesis_config = SynthesisConfig(
                synthesis_model=f_config.synthesis_model,
                synthesis_model_override=f_config.synthesis_model_override,
                max_synthesis_tokens=f_config.synthesis_max_tokens
            )

            self.orchestrator = FractalOrchestrator(
                parent_node=self,
                config=orchestrator_config
            )
            self.synthesizer = ResultSynthesizer(
                provider=provider or MockLLMProvider(),
                config=synthesis_config
            )
        else:
            self.orchestrator = None
            self.synthesizer = None

        # Register internal tools
        self._register_internal_tools()

        self.provider = provider or MockLLMProvider()

        # --- Memory & Context System ---
        self.memory = LoomMemory(node_id=node_id)

        # Dual Context Managers (from unified config)
        self.s1_config = self.cognitive_config.get_s1_context_config()
        self.s1_assembler = ContextAssembler(config=self.s1_config)
        self.s1_context = ContextManager(node_id, self.memory, self.s1_assembler)

        self.s2_config = self.cognitive_config.get_s2_context_config()
        self.s2_assembler = ContextAssembler(config=self.s2_config)
        self.s2_context = ContextManager(node_id, self.memory, self.s2_assembler)

        # Default to S2 context for backward compatibility
        self.context = self.s2_context

        # --- Cognitive Routing (from unified config) ---
        self.router_config = self.cognitive_config.get_router_config()
        self.classifier = QueryClassifier(config=self.router_config)
        self.router = AdaptiveRouter(self.classifier, config=self.router_config)
        self.confidence_estimator = ConfidenceEstimator()

        # Apply Projection (Fractal Inheritance)
        if context_projection:
             self._apply_projection(context_projection)

        # Register Internal Context Tools
        self._register_internal_tools()
        
        # --- Cognitive Control ---
        self.enable_auto_reflection = enable_auto_reflection
        self.reflection_config = reflection_config or ReflectionConfig()
        self.thinking_policy = thinking_policy or ThinkingPolicy()
        self.current_depth = current_depth
        self._active_thoughts: List[str] = []
        self._tokens_used: int = 0
        
        self.cognitive_state = CognitiveState()
        self.projector = ProjectionOperator(strategy=projection_strategy)

        # Parallel Execution Engine
        self.executor = ToolExecutor(config=self.execution_config)

    def _apply_projection(self, projection: ContextProjection):
        """Ingest projected context from parent."""
        units = projection.to_memory_units()
        for unit in units:
            self.memory.add(unit)

    def _register_internal_tools(self):
        """Register memory management tools."""
        
        async def load_context(resource_id: str) -> str:
            """
            Load full content of a resource snippet into working memory.
            Args:
                resource_id: The ID of the snippet to expand.
            """
            return self.context.load_resource(resource_id)
            
        async def save_to_longterm(content: str, importance: float = 0.8) -> str:
            """
            Save important information to long-term memory (Global).
            Args:
                content: The text to save.
                importance: 0.0 to 1.0 importance score.
            """
            await self.memory.add(MemoryUnit(
                content=content,
                tier=MemoryTier.L4_GLOBAL,
                type=MemoryType.FACT,
                importance=importance
            ))
            return "✅ Saved to long-term memory."

        self.tool_registry.register_function(load_context)
        self.tool_registry.register_function(save_to_longterm)

        # Register delegation tool if orchestrator is available
        if self.orchestrator is not None:
            async def delegate_subtasks(
                subtasks: List[Dict[str, Any]],
                execution_mode: str = "parallel",
                synthesis_strategy: str = "auto",
                reasoning: str = None
            ) -> str:
                """
                将复杂任务分解为子任务并委托给专门的子代理执行。

                Args:
                    subtasks: 子任务列表，每个包含 description (必需), role, tools, max_tokens
                    execution_mode: 执行模式 (parallel|sequential|adaptive)
                    synthesis_strategy: 合成策略 (auto|concatenate|structured)
                    reasoning: 分解理由

                Returns:
                    合成后的结果
                """
                try:
                    from loom.protocol.delegation import DelegationRequest, SubtaskSpecification

                    # 解析子任务
                    parsed_subtasks = [
                        SubtaskSpecification(**st) for st in subtasks
                    ]

                    # 创建请求
                    request = DelegationRequest(
                        subtasks=parsed_subtasks,
                        execution_mode=execution_mode,
                        synthesis_strategy=synthesis_strategy,
                        reasoning=reasoning
                    )

                    # 执行委托
                    result = await self.orchestrator.delegate(request)

                    if result.success:
                        return result.synthesized_result
                    else:
                        return f"委托失败: {result.metadata.get('error', 'Unknown error')}"

                except Exception as e:
                    return f"委托工具错误: {str(e)}"

            # 注册工具
            self.tool_registry.register_function(delegate_subtasks)

    async def _spawn_thought(self, task: str) -> Optional[str]:
        """
        System 2: Spawn a new Ephemeral Node to think about a sub-task.
        """
        if not self.thinking_policy.enabled:
            return None

        # [Entropy Checks Omitted for Brevity - Keeping Core Logic] 
        
        thought_id = f"thought-{str(uuid.uuid4())[:8]}"
        thought = Thought(
            id=thought_id,
            task=task,
            state=ThoughtState.RUNNING,
            depth=self.current_depth + 1,
            metadata={"parent": self.node_id}
        )
        self.cognitive_state.add_thought(thought)

        await self.dispatcher.dispatch(CloudEvent.create(
            source=self.source_uri,
            type=EventType.NODE_REGISTER,
            data={
                "node_id": thought_id,
                "parent": self.node_id,
                "depth": self.current_depth + 1
            }
        ))
        
        # Create Fractal Child Node with Projection
        # Project current context to child
        projection = self.memory.create_projection(instruction=task)

        thought_node = AgentNode(
            node_id=thought_id,
            dispatcher=self.dispatcher,
            role="Deep Thinker",
            system_prompt="You are a deep thinking sub-process. Analyze the following.",
            provider=self.provider,
            context_config=self.context_config, # Inherit configs
            context_projection=projection,      # Inherit context
            thinking_policy=ThinkingPolicy(enabled=False), 
            current_depth=self.current_depth + 1
        )

        await self.dispatcher.register_ephemeral(thought_node)
        self._active_thoughts.append(thought_id)
        return thought_id

    async def _perform_reflection(self) -> None:
        """Check and perform metabolic memory reflection."""
        # TODO: Implement LoomMemory-specific reflection
        # For now, LoomMemory manages its own promotion via tiers.
        # We can implement a cleanup/summary strategy later.
        pass

    async def process(self, event: CloudEvent) -> Any:
        """
        Agent Loop with System 1/2 Routing.
        """
        if event.type != "node.request":
            return None
            
        data = event.data or {}
        task = data.get("content") or data.get("task") or str(data)
        
        # 0. Perceive (Add to Memory)
        await self.memory.add(MemoryUnit(
            content=str(task),
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        ))

        # 1. Routing Decision
        # Check context requirements (e.g. if tools are strictly needed)
        context_info = {"requires_tools": "tool" in str(task).lower()} 
        decision = self.router.route(str(task), context_info)
        
        # Emulate thinking/classification event? Optional but good for debug
        # print(f"[{self.node_id}] Routing: {decision.system} (conf={decision.confidence:.2f})")

        # 2. Execute based on System
        if decision.system == SystemType.SYSTEM_1:
             return await self._execute_system1(task, decision)
        
        # Default to System 2 (or Adaptive fallback which we implement as S2 for now)
        return await self._execute_system2(task, decision, event)

    async def _execute_system1(self, task: str, decision: RoutingDecision, event: Optional[CloudEvent] = None) -> Any:
        """Fast Path: Single Turn, Minimal Context with Confidence Evaluation."""
        # 1. Build Prompt (Fast Strategy)
        messages = await self.s1_context.build_prompt(task, "Answer directly and concisely.")

        # 2. Call LLM (No tools passed to enforce reflex)
        try:
            response = await self.provider.chat(messages)
        except Exception as e:
            return f"System 1 Error: {e}"

        content = getattr(response, "content", "") if not isinstance(response, dict) else response.get("content", "")

        # 3. Evaluate Confidence
        confidence_result = self.confidence_estimator.estimate(
            query=task,
            response=content
        )

        # 4. Check if we should fallback to System 2
        if self.router.should_fallback(confidence_result.score):
            # Record switch
            self.classifier.record_switch()

            # Fallback to System 2
            if event:
                return await self._execute_system2(task, decision, event)
            else:
                # If no event, return with low confidence indicator
                return {
                    "response": content,
                    "system": "SYSTEM_1_UNCERTAIN",
                    "confidence": confidence_result.score,
                    "reasoning": confidence_result.reasoning,
                    "should_retry_s2": True
                }

        # 5. Record & Return (Confident S1 response)
        self.memory.add(MemoryUnit(
            content=content,
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.THOUGHT
        ))

        result = {
            "response": content,
            "system": "SYSTEM_1",
            "confidence": confidence_result.score,
            "reasoning": confidence_result.reasoning
        }
        return result

    async def _execute_system2(self, task: str, decision: RoutingDecision, event: CloudEvent) -> Any:
        """Slow Path: ReAct Loop, Full Context."""
        # This wraps the original _execute_loop logic
        return await self._execute_loop(event)

    async def _execute_loop(self, event: CloudEvent) -> Any:
        """Standard ReAct Loop using ContextManager."""
        
        data = event.data or {}
        task = data.get("content") or data.get("task") or str(data)
        system_prompt = data.get("system_prompt") or self.system_prompt
        max_iterations = data.get("max_iterations", 10)

        # 1. Perceive (Add to Memory)
        await self.memory.add(MemoryUnit(
            content=str(task),
            tier=MemoryTier.L1_RAW_IO,
            type=MemoryType.MESSAGE
        ))
        
        iterations = 0
        final_response = ""
        
        while iterations < max_iterations:
            iterations += 1
            
            # 2. Recall (Context Assembly)
            messages = await self.context.build_prompt(
                task=str(task),
                system_prompt=system_prompt
            )

            # 3. Think
            # Combine external known_tools (MCP) and internal tools
            internal_definitions = self.tool_registry.definitions
            external_definitions = [t.tool_def for t in self.known_tools.values()]
            
            # Convert internal definitions to dicts (model_dump) if needed by provider
            # Assuming provider expects dicts or objects. 
            # loom.protocol.mcp.MCPToolDefinition likely has model_dump
            all_tools_dumps = [d.model_dump() for d in internal_definitions + external_definitions]

            try:
                response = await self.provider.chat(messages, tools=all_tools_dumps)
            except Exception as e:
                return f"Error calling LLM: {str(e)}"
            
            # Extract content
            if isinstance(response, dict):
                content = response.get("content", "")
                tool_calls = response.get("tool_calls", [])
            else:
                content = getattr(response, "content", "")
                tool_calls = getattr(response, "tool_calls", [])

            # 4. Act
            if content:
                await self.memory.add(MemoryUnit(
                    content=str(content), 
                    tier=MemoryTier.L1_RAW_IO, 
                    type=MemoryType.THOUGHT
                ))
            
            if tool_calls:
                # Record intent (All calls in one block)
                await self.memory.add(MemoryUnit(
                    content=tool_calls, 
                    tier=MemoryTier.L1_RAW_IO, 
                    type=MemoryType.TOOL_CALL
                ))

                # 1. Parse and Prepare
                parsed_calls = []
                for tc in tool_calls:
                    name = tc.get("name")
                    args = tc.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except: pass
                    
                    if not isinstance(args, dict):
                         args = {"args": args}
                    
                    parsed_calls.append({"name": name, "arguments": args})

                    # Emit Tool Call Event (Bus-Awareness) - Immediate feedback
                    await self.dispatcher.dispatch(CloudEvent.create(
                        source=self.source_uri,
                        type="agent.tool.call",
                        data={"minion": self.node_id, "tool": name, "arguments": args},
                        traceparent=event.traceparent
                    ))

                # 2. Define Execution Wrapper (for Event Emission)
                async def monitored_execution(name: str, args: Dict) -> Any:
                    # Execute
                    result_val = await self._execute_any_tool(name, args)
                    
                    # Emit Result Event immediately (for streaming/UI)
                    await self.dispatcher.dispatch(CloudEvent.create(
                        source=self.source_uri,
                        type="agent.tool.result",
                        data={"minion": self.node_id, "tool": name, "result": str(result_val)},
                        traceparent=event.traceparent
                    ))
                    return result_val

                # 3. Parallel Execution
                # results will be a list of ToolExecutionResult objects, in order
                results = await self.executor.execute_batch(parsed_calls, monitored_execution)

                # 4. Update Memory (Sequential & Deterministic)
                for res in results:
                    await self.memory.add(MemoryUnit(
                        content=str(res.result),
                        tier=MemoryTier.L1_RAW_IO,
                        type=MemoryType.TOOL_RESULT,
                        metadata={"tool_name": res.name, "error": res.error}
                    ))

                continue # Loop again
            
            final_response = content
            break

        return final_response

    async def _execute_stream_loop(self, event: CloudEvent) -> Any:
        """
        Streaming Loop with ContextManager.
        (Simplified implementation logic for brevity, matches structure of _execute_loop)
        """
        # For now, fallback to blocking loop as streaming requires updating
        # how we stream context updates. 
        # But to satisfy the AgentNode contract, we wrap _execute_loop
        result = await self._execute_loop(event)
        
        # If result is string, wrap in expected format if needed by caller, 
        # but _execute_loop returns string.
        # Original processed returned dict {"response": ...}
        return {"response": result, "iterations": 1}

    async def _execute_any_tool(self, name: str, args: Dict) -> Any:
        """Execute either internal or external tool."""
        try:
            # 1. Internal
            internal_func = self.tool_registry.get_callable(name)
            result = None
            if internal_func:
                if callable(internal_func):
                    result = await internal_func(**args)
                else:
                    result = str(internal_func)
            else:
                # 2. External (Legacy ToolNode)
                tool_node = self.known_tools.get(name)
                if tool_node:
                    # Use call() for distributed / event-bus execution
                    res = await self.call(
                        target_node=tool_node.source_uri,
                        data={"arguments": args}
                    )
                    if isinstance(res, dict):
                        result = res.get("result", str(res))
                    else:
                        result = str(res)
                else:
                    return f"Tool {name} not found."

            # Normalize Result
            return DataNormalizer.normalize_to_size(
                result,
                max_depth=self.execution_config.normalization.max_depth,
                max_bytes=self.execution_config.normalization.max_bytes,
                string_limit=self.execution_config.normalization.truncate_strings
            )

        except Exception as e:
            # Actionable Error Formatting (Optional Check)
            if not self.execution_config.error_handling.rich_formatting:
               # Fallback to simple string if rich formatting disabled
               return f"Tool Error: {str(e)}"
               
            # TODO: Pass error_handling config to ErrorFormatter if we add config support there
            return ErrorFormatter.format_tool_error(e, name)

    # ============================================================================
    # Fractal Configuration Management (inlined from FractalMixin)
    # ============================================================================

    def get_fractal_config(self) -> Optional[FractalConfig]:
        """Get current fractal configuration"""
        return self._fractal_config

    def set_fractal_config(self, config: FractalConfig):
        """Set fractal configuration"""
        if config:
            config.validate()
        self._fractal_config = config
