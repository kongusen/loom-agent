"""
Fractal Agent Node

Self-organizing agent nodes that can dynamically spawn children to handle
complex tasks through recursive decomposition.
"""

import asyncio
import time
import uuid
from typing import Any, Optional, cast

from loom.config.fractal import (
    FractalConfig,
    GrowthStrategy,
    NodeMetrics,
    NodeRole,
)
from loom.kernel.fractal import FractalOrchestrator, OrchestratorConfig, fractal_utils
from loom.llm import LLMProvider, MockLLMProvider
from loom.memory.core import LoomMemory
from loom.node.agent import AgentNode
from loom.protocol.delegation import TaskDecomposition


class FractalAgentNode(AgentNode):
    """
    Fractal Agent Node - Self-organizing hierarchical agent

    Extends AgentNode with the ability to:
    1. Decompose complex tasks into subtasks
    2. Spawn child nodes to handle subtasks
    3. Aggregate results from children
    4. Track and optimize structure performance
    """

    def __init__(
        self,
        # Core parameters (compatible with AgentNode)
        node_id: str,
        dispatcher: Any | None = None,
        provider: LLMProvider | None = None,
        tools: list[Any] | None = None,
        memory: LoomMemory | None = None,
        # Fractal-specific parameters
        role: NodeRole = NodeRole.COORDINATOR,
        parent: Optional["FractalAgentNode"] = None,
        depth: int = 0,
        fractal_config: FractalConfig | None = None,
        # Simplified mode (skip AgentNode init for standalone use)
        standalone: bool = True,
        # Pass through to parent
        **kwargs,
    ):
        """
        Initialize fractal agent node

        Args:
            node_id: Unique identifier for this node
            dispatcher: Event dispatcher (optional for standalone mode)
            provider: Language model provider
            tools: Available tools for this node
            memory: Memory system
            role: Role of this node in the hierarchy
            parent: Parent node (None for root)
            depth: Depth in the tree (0 for root)
            fractal_config: Fractal mode configuration
            standalone: If True, use simplified init (don't call AgentNode.__init__)
            **kwargs: Additional arguments passed to AgentNode
        """
        # Store attributes for standalone mode
        if standalone:
            # Minimal initialization without AgentNode
            self.node_id = node_id
            self.provider = provider or kwargs.get("llm") or MockLLMProvider()  # Support both names
            self.llm = self.provider  # Alias
            self.tools = tools or []
            self.memory = memory or LoomMemory(self.node_id)
            # dispatcher can be None in standalone, but AgentNode expects Dispatcher.
            # We must either create one or allow None (if typed Optional).
            # AgentNode types dispatcher as Dispatcher.
            # So we create a dummy or rely on standard bus.
            from loom.kernel.core import Dispatcher, UniversalEventBus

            self.dispatcher = dispatcher or Dispatcher(UniversalEventBus())

            # Initialize tool helper structures
            self.known_tools = (
                {t.name: t for t in self.tools} if hasattr(self.tools, "__iter__") else {}
            )
            # Mock tool registry for standalone
            self.tool_registry = type("MockRegistry", (), {"_tools": {}})()
        else:
            # Full AgentNode initialization
            from loom.kernel.core import Dispatcher
            from loom.kernel.core.bus import UniversalEventBus

            if dispatcher is None:
                bus = UniversalEventBus()
                dispatcher = Dispatcher(bus)
            super().__init__(
                node_id=node_id, dispatcher=dispatcher, provider=provider, tools=tools, **kwargs
            )
            self.llm = provider  # Alias for convenience

        # Fractal attributes
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:8]}"
        self.role = role.value
        self.parent = parent
        self.children: list[
            FractalAgentNode
        ] = []  # Kept for backward compat/inspection, but managed by Orchestrator technically?
        # Actually, Orchestrator doesn't persist children list in state, it returns them.
        # But we might want to track them for visibility.
        # For Phase 2 simplicity, let's keep self.children but populate it from Orchestrator results if needed,
        # OR just remove it and accept that structure is transient.
        # Let's keep it empty for now, or just use it to track active children for visualization?
        # The original code used it for persistence.
        # Let's comment it out or leave it empty.

        self.depth = depth

        # Configuration
        self.fractal_config = fractal_config or FractalConfig()
        if self.fractal_config.enabled:
            self.fractal_config.validate()

        # Metrics
        self.metrics = NodeMetrics()

        # Track structure changes
        self._structure_version = 0

        # Initialize Orchestrator
        if self.fractal_config.enabled:
            orchestrator_config = OrchestratorConfig(
                allow_recursive_delegation=self.fractal_config.allow_recursive_delegation,
                max_recursive_depth=self.fractal_config.max_recursive_depth,
                default_child_token_budget=self.fractal_config.default_child_token_budget,
                max_concurrent_children=self.fractal_config.max_concurrent_children,
                implicit_mode_enabled=True,  # Always enable for FractalAgentNode
            )
            self.orchestrator = FractalOrchestrator(self, orchestrator_config)

    # ============================================================================
    # Core Execution
    # ============================================================================

    async def execute(self, task: str, force_fractal: bool = False, **kwargs) -> dict[str, Any]:
        """
        Execute task with optional fractal decomposition

        Args:
            task: Task description
            force_fractal: Force fractal mode even if disabled in config
            **kwargs: Additional arguments passed to parent run()

        Returns:
            Result dictionary with keys:
                - result: Task result
                - node_id: ID of node that executed
                - structure: Structure tree (if fractal mode used)
                - metrics: Performance metrics
        """
        start_time = time.time()
        tokens_before = self._count_tokens() if hasattr(self, "_count_tokens") else 0

        try:
            # Decide whether to use fractal mode
            use_fractal = force_fractal or self._should_use_fractal_mode(task)

            if use_fractal and await self._should_decompose(task):
                # Fractal path: decompose and delegate
                result = await self._fractal_execute(task, **kwargs)
            else:
                # Direct path: execute locally
                result = await self._direct_execute(task, **kwargs)

            # Record success
            execution_time = time.time() - start_time
            tokens_used = (
                self._count_tokens() - tokens_before if hasattr(self, "_count_tokens") else 0
            )

            self.metrics.record_execution(
                success=True,
                tokens=tokens_used,
                time=execution_time,
                cost=self._estimate_cost(tokens_used),
            )

            # Return enriched result
            return {
                "result": result,
                "node_id": self.node_id,
                "execution_time": execution_time,
                "tokens_used": tokens_used,
                "structure": self.get_structure_tree() if use_fractal else None,
                "metrics": self.metrics.to_dict(),
            }

        except Exception:
            # Record failure
            execution_time = time.time() - start_time
            tokens_used = (
                self._count_tokens() - tokens_before if hasattr(self, "_count_tokens") else 0
            )

            self.metrics.record_execution(
                success=False, tokens=tokens_used, time=execution_time, cost=0.0
            )

            raise

    def _should_use_fractal_mode(self, task: str) -> bool:
        """Determine if fractal mode should be used"""
        return fractal_utils.should_use_fractal(task, self.fractal_config)

    async def _direct_execute(self, task: str, **_kwargs) -> Any:
        """Execute task directly using parent AgentNode._execute_task()"""
        # Use parent class's execution method
        # Note: _execute_task takes (task, event), ignoring kwargs for now or mapping them
        result = await self._execute_task(task)
        return result

    async def _fractal_execute(self, task: str, **_kwargs) -> dict[str, Any]:
        """Execute task using fractal decomposition via Orchestrator"""
        # 1. Decompose task
        decomposition = await self._decompose_task(task)

        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")

        # 2. Delegate via Orchestrator
        delegation_result = await self.orchestrator.process_decomposition(decomposition)

        # 3. Update local structure tracking (optional, for visualization)
        # We might want to retrieve children from result if needed, but for now just return results

        return {
            "aggregated_result": delegation_result.synthesized_result,
            "subtask_results": delegation_result.subtask_results,
            "decomposition": {
                "strategy": decomposition.strategy.value,
                "reasoning": decomposition.reasoning,
                "subtask_count": len(decomposition.subtasks),
            },
        }

    # ============================================================================
    # Task Decomposition
    # ============================================================================

    async def _should_decompose(self, task: str) -> bool:
        """Determine if task should be decomposed"""
        # Check depth limit
        if self.depth >= self.fractal_config.max_depth:
            return False

        # Check total node count
        if self._count_total_nodes() >= self.fractal_config.max_total_nodes:
            return False

        # Estimate complexity
        complexity = self._estimate_task_complexity(task)

        # Decompose if complexity exceeds threshold
        return complexity > self.fractal_config.complexity_threshold

    def _estimate_task_complexity(self, task: str) -> float:
        """Estimate task complexity (0-1) using shared utility"""
        return fractal_utils.estimate_task_complexity(task)

    async def _decompose_task(self, task: str) -> TaskDecomposition:
        """
        Decompose task into subtasks using LLM

        Args:
            task: Task to decompose

        Returns:
            TaskDecomposition with subtasks and strategy
        """
        # Determine strategy
        strategy = self._detect_growth_strategy(task)

        # Create decomposition prompt
        prompt = self._create_decomposition_prompt(task, strategy)

        # Call LLM
        # Use chat method as LLMProvider does not have generate
        response_obj = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            config={"max_tokens": 1000, "temperature": 0.3},
        )
        response = response_obj.content

        # Parse response
        subtasks, reasoning = self._parse_decomposition_response(response)

        return TaskDecomposition(
            subtasks=subtasks,
            strategy=strategy,
            reasoning=reasoning,
            estimated_complexity=self._estimate_task_complexity(task),
        )

    def _detect_growth_strategy(self, task: str) -> GrowthStrategy:
        """Detect appropriate growth strategy from task"""
        task_lower = task.lower()

        # Check keywords for each strategy
        for strategy, keywords in self.fractal_config.strategy_keywords.items():
            if any(kw in task_lower for kw in keywords):
                return strategy

        # Default strategy
        return self.fractal_config.default_strategy

    def _create_decomposition_prompt(self, task: str, strategy: GrowthStrategy) -> str:
        """Create prompt for task decomposition"""
        strategy_guidance = {
            GrowthStrategy.DECOMPOSE: "Break into sequential steps that must be done in order.",
            GrowthStrategy.SPECIALIZE: "Identify specialized domains/expertise needed.",
            GrowthStrategy.PARALLELIZE: "Split into independent tasks that can run concurrently.",
            GrowthStrategy.ITERATE: "Define iterative refinement steps.",
        }

        return f"""Decompose the following task into subtasks.

Task: {task}

Strategy: {strategy.value}
Guidance: {strategy_guidance[strategy]}

Provide your response in this format:
REASONING: <brief explanation of decomposition>

SUBTASKS:
1. <subtask 1>
2. <subtask 2>
...

Keep subtasks clear and actionable. Limit to {self.fractal_config.max_children} subtasks.
"""

    def _parse_decomposition_response(self, response: str) -> tuple[list[str], str]:
        """Parse LLM decomposition response"""
        lines = response.strip().split("\n")

        reasoning = ""
        subtasks = []
        in_subtasks = False

        for line in lines:
            line = line.strip()

            if line.startswith("REASONING:"):
                reasoning = line.replace("REASONING:", "").strip()
            elif line.startswith("SUBTASKS:"):
                in_subtasks = True
            elif in_subtasks and line:
                # Remove numbering (1., 2., etc.)
                subtask = line.lstrip("0123456789.-) ").strip()
                if subtask:
                    subtasks.append(subtask)

        # Fallback if parsing fails
        if not subtasks:
            subtasks = [response.strip()]
            reasoning = "Failed to parse decomposition, using full response as single task"

        return subtasks, reasoning

    # ============================================================================
    # Child Node Management
    # ============================================================================

    # ============================================================================
    # Child Node Management (Deprecated / Handled by Orchestrator)
    # ============================================================================

    # Methods _spawn_children, _execute_children, _aggregate_results removed.
    # Logic is now in FractalOrchestrator.

    # ============================================================================
    # Structure Introspection
    # ============================================================================

    def get_structure_tree(self) -> dict[str, Any]:
        """Get complete structure tree"""
        return {
            "node_id": self.node_id,
            "role": self.role,
            "depth": self.depth,
            "metrics": self.metrics.to_dict(),
            "children": [child.get_structure_tree() for child in self.children],
        }

    def _count_total_nodes(self) -> int:
        """Count total nodes in subtree"""
        return 1 + sum(child._count_total_nodes() for child in self.children)

    def visualize_structure(self, format: str = "tree") -> str:
        """
        Visualize node structure

        Args:
            format: "tree" or "compact"

        Returns:
            String representation
        """
        if format == "tree":
            return self._visualize_tree()
        elif format == "compact":
            return self._visualize_compact()
        else:
            raise ValueError(f"Unknown format: {format}")

    def _visualize_tree(self, prefix: str = "", is_last: bool = True) -> str:
        """Visualize as ASCII tree"""
        connector = "└─ " if is_last else "├─ "
        fitness = self.metrics.fitness_score()
        tasks = self.metrics.task_count

        result = f"{prefix}{connector}{self.node_id} "
        result += f"[{self.role}] "
        result += f"fitness={fitness:.2f} tasks={tasks}\n"

        if self.children:
            extension = "   " if is_last else "│  "
            for i, child in enumerate(self.children):
                result += child._visualize_tree(prefix + extension, i == len(self.children) - 1)

        return result

    def _visualize_compact(self) -> str:
        """Compact visualization"""
        nodes: list[str] = []
        self._collect_nodes_compact(nodes)

        result = f"📊 Structure: {len(nodes)} nodes, max depth {self.depth}\n"
        for node_info in nodes:
            result += f"  • {node_info}\n"

        return result

    def _collect_nodes_compact(self, nodes: list[str], depth: int = 0):
        """Collect nodes for compact visualization"""
        indent = "  " * depth
        fitness = self.metrics.fitness_score()
        nodes.append(f"{indent}{self.node_id} [{self.role}] f={fitness:.2f}")

        for child in self.children:
            child._collect_nodes_compact(nodes, depth + 1)

    # ============================================================================
    # Utilities
    # ============================================================================

    def _select_tools_for_child(self, _subtask: str) -> list[Any]:
        """
        Select tools for child node based on subtask
        For backward compatibility with add_child.
        """
        return self.tools if hasattr(self, "tools") else []

    async def _execute_children(self, subtasks: list[str], **kwargs) -> list[dict[str, Any]]:
        """
        Execute subtasks on child nodes
        For backward compatibility with execute_pipeline.
        """
        if len(self.children) != len(subtasks):
            raise ValueError(f"Mismatch: {len(self.children)} children, {len(subtasks)} subtasks")

        # Execute in parallel
        tasks = [
            child.execute(subtask, **kwargs)
            for child, subtask in zip(self.children, subtasks, strict=False)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Helper to process results
        processed: list[dict[str, Any]] = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                child_node = self.children[i]
                error_data: dict[str, Any] = {
                    "success": False,
                    "error": str(res),
                    "node_id": child_node.node_id if child_node else "unknown",
                }
                processed.append(error_data)
            else:
                # We assume execute returns a dict, but explicit cast helps mypy
                processed.append(cast(dict[str, Any], res))
        return processed

    def _count_tokens(self) -> int:
        """Count tokens used so far (placeholder)"""
        # This should integrate with actual token counting
        return 0

    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost based on tokens"""
        # Rough estimate: $0.01 per 1000 tokens
        return tokens * 0.01 / 1000

    # ============================================================================
    # Manual Pipeline Building API
    # ============================================================================

    def add_child(
        self, role: NodeRole = NodeRole.EXECUTOR, tools: list[Any] | None = None, **kwargs
    ) -> "FractalAgentNode":
        """
        Manually add a child node (for pipeline building)

        Args:
            role: Role for the child
            tools: Tools for the child
            **kwargs: Additional parameters

        Returns:
            The created child node
        """
        child_id = f"{self.node_id}.{len(self.children)}"

        child = FractalAgentNode(
            node_id=child_id,
            role=role,
            parent=self,
            depth=self.depth + 1,
            llm=self.llm,
            tools=tools or self._select_tools_for_child(""),
            memory=self.memory,
            fractal_config=self.fractal_config,
            **kwargs,
        )

        self.children.append(child)
        self._structure_version += 1

        return child

    def remove_child(self, child: "FractalAgentNode"):
        """Remove a child node"""
        self.children.remove(child)
        self._structure_version += 1

    async def execute_pipeline(
        self, tasks: list[str], mode: str = "sequential"
    ) -> list[dict[str, Any]]:
        """
        Execute tasks on children in specified mode

        Args:
            tasks: List of tasks (one per child)
            mode: "sequential" or "parallel"

        Returns:
            List of results
        """
        if len(tasks) != len(self.children):
            raise ValueError(f"Task count ({len(tasks)}) != child count ({len(self.children)})")

        if mode == "sequential":
            results = []
            for child, task in zip(self.children, tasks, strict=False):
                result = await child.execute(task)
                results.append(result)
            return results

        elif mode == "parallel":
            return await self._execute_children(tasks)

        else:
            raise ValueError(f"Unknown mode: {mode}")
