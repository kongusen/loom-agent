"""
Pipeline Builder - Declarative API for building fractal node structures

Provides a fluent, user-friendly API for manually constructing
complex agent pipelines without auto-decomposition.
"""

from typing import List, Optional, Any, Callable, Dict
from dataclasses import dataclass
from loom.node.fractal import FractalAgentNode
from loom.config.fractal import NodeRole, FractalConfig, GrowthTrigger


@dataclass
class PipelineStep:
    """Represents a single step in the pipeline"""
    name: str
    role: NodeRole
    tools: Optional[List[Any]] = None
    prompt_template: Optional[str] = None
    node: Optional[FractalAgentNode] = None


class PipelineBuilder:
    """
    Fluent API for building fractal node pipelines

    Example:
        ```python
        pipeline = (
            PipelineBuilder("research_pipeline", llm=openai)
            .coordinator("orchestrator")
            .parallel([
                ("research_ai", "specialist", ai_tools),
                ("research_market", "specialist", market_tools),
                ("research_tech", "specialist", tech_tools)
            ])
            .aggregator("synthesizer")
            .build()
        )

        result = await pipeline.execute("Analyze AI market trends")
        ```
    """

    def __init__(
        self,
        pipeline_name: str,
        provider: Any,
        memory: Optional[Any] = None,
        fractal_config: Optional[FractalConfig] = None
    ):
        """
        Initialize pipeline builder

        Args:
            pipeline_name: Name for the root node
            provider: Language model provider
            memory: Memory system
            fractal_config: Fractal configuration (auto-growth disabled by default)
        """
        self.pipeline_name = pipeline_name
        self.provider = provider
        self.memory = memory

        # Disable auto-growth for manual pipelines
        self.fractal_config = fractal_config or FractalConfig(
            enabled=False,  # Manual control
            growth_trigger=GrowthTrigger.MANUAL
        )

        self._root: Optional[FractalAgentNode] = None
        self._current: Optional[FractalAgentNode] = None
        self._steps: List[PipelineStep] = []

    def coordinator(
        self,
        name: str,
        tools: Optional[List[Any]] = None,
        prompt: Optional[str] = None
    ) -> 'PipelineBuilder':
        """
        Add a coordinator node (task decomposer)

        Args:
            name: Node name/identifier
            tools: Tools available to this node
            prompt: Custom system prompt

        Returns:
            Self for chaining
        """
        return self._add_node(name, NodeRole.COORDINATOR, tools, prompt)

    def specialist(
        self,
        name: str,
        tools: Optional[List[Any]] = None,
        prompt: Optional[str] = None,
        domain: Optional[str] = None
    ) -> 'PipelineBuilder':
        """
        Add a specialist node (domain expert)

        Args:
            name: Node name/identifier
            tools: Specialized tools for this domain
            prompt: Custom system prompt
            domain: Domain description (added to prompt if provided)

        Returns:
            Self for chaining
        """
        if domain and not prompt:
            prompt = f"You are a specialist in {domain}. Provide expert analysis and insights."

        return self._add_node(name, NodeRole.SPECIALIST, tools, prompt)

    def executor(
        self,
        name: str,
        tools: Optional[List[Any]] = None,
        prompt: Optional[str] = None
    ) -> 'PipelineBuilder':
        """
        Add an executor node (task executor)

        Args:
            name: Node name/identifier
            tools: Tools for execution
            prompt: Custom system prompt

        Returns:
            Self for chaining
        """
        return self._add_node(name, NodeRole.EXECUTOR, tools, prompt)

    def aggregator(
        self,
        name: str,
        tools: Optional[List[Any]] = None,
        prompt: Optional[str] = None
    ) -> 'PipelineBuilder':
        """
        Add an aggregator node (result synthesizer)

        Args:
            name: Node name/identifier
            tools: Tools for aggregation
            prompt: Custom system prompt

        Returns:
            Self for chaining
        """
        if not prompt:
            prompt = "Synthesize and combine the provided information into a coherent response."

        return self._add_node(name, NodeRole.AGGREGATOR, tools, prompt)

    def parallel(
        self,
        nodes: List[tuple],
        join_with_aggregator: bool = True
    ) -> 'PipelineBuilder':
        """
        Add multiple parallel nodes

        Args:
            nodes: List of (name, role, tools) tuples
            join_with_aggregator: Automatically add aggregator after parallel nodes

        Returns:
            Self for chaining

        Example:
            ```python
            .parallel([
                ("task1", "executor", tools1),
                ("task2", "executor", tools2),
                ("task3", "executor", tools3)
            ])
            ```
        """
        if not self._current:
            raise ValueError("Cannot add parallel nodes without a parent. Add a coordinator first.")

        parent = self._current

        # Add all parallel nodes as children
        for node_spec in nodes:
            if len(node_spec) == 2:
                name, role_str = node_spec
                tools = None
            elif len(node_spec) == 3:
                name, role_str, tools = node_spec
            else:
                raise ValueError(f"Invalid node spec: {node_spec}. Expected (name, role) or (name, role, tools)")

            role = NodeRole[role_str.upper()]

            step = PipelineStep(
                name=name,
                role=role,
                tools=tools
            )

            node = self._create_node(step, parent=parent)
            parent.children.append(node)
            self._steps.append(step)

        # Add aggregator if requested
        if join_with_aggregator:
            agg_name = f"{parent.node_id}_aggregator"
            self.aggregator(agg_name)

        return self

    def chain(
        self,
        nodes: List[tuple]
    ) -> 'PipelineBuilder':
        """
        Add a chain of sequential nodes

        Args:
            nodes: List of (name, role, tools) tuples

        Returns:
            Self for chaining

        Example:
            ```python
            .chain([
                ("analyze", "executor", analysis_tools),
                ("refine", "executor", refinement_tools),
                ("finalize", "aggregator", None)
            ])
            ```
        """
        for node_spec in nodes:
            if len(node_spec) == 2:
                name, role_str = node_spec
                tools = None
            elif len(node_spec) == 3:
                name, role_str, tools = node_spec
            else:
                raise ValueError(f"Invalid node spec: {node_spec}")

            role = NodeRole[role_str.upper()]
            self._add_node(name, role, tools)

        return self

    def custom_node(
        self,
        name: str,
        role: NodeRole,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> 'PipelineBuilder':
        """
        Add a custom node with full control

        Args:
            name: Node name
            role: Node role
            config: Custom configuration
            **kwargs: Additional node parameters

        Returns:
            Self for chaining
        """
        return self._add_node(name, role, config=config, **kwargs)

    def _add_node(
        self,
        name: str,
        role: NodeRole,
        tools: Optional[List[Any]] = None,
        prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> 'PipelineBuilder':
        """Internal method to add a node"""
        step = PipelineStep(
            name=name,
            role=role,
            tools=tools,
            prompt_template=prompt
        )

        # Create node
        if self._root is None:
            # First node becomes root
            node = self._create_node(step, parent=None, **kwargs)
            self._root = node
            self._current = node
        else:
            # Add as child of current
            parent = self._current
            node = self._create_node(step, parent=parent, **kwargs)
            parent.children.append(node)
            self._current = node

        step.node = node
        self._steps.append(step)

        return self

    def _create_node(
        self,
        step: PipelineStep,
        parent: Optional[FractalAgentNode] = None,
        **kwargs
    ) -> FractalAgentNode:
        """Create a FractalAgentNode from a step"""
        depth = parent.depth + 1 if parent else 0
        node_id = f"{self.pipeline_name}.{step.name}"

        return FractalAgentNode(
            node_id=node_id,
            role=step.role,
            parent=parent,
            depth=depth,
            provider=self.provider,
            tools=step.tools or [],
            memory=self.memory,
            fractal_config=self.fractal_config,
            standalone=True,
            **kwargs
        )

    def build(self) -> FractalAgentNode:
        """
        Build and return the root node

        Returns:
            Root FractalAgentNode with complete structure
        """
        if self._root is None:
            raise ValueError("Pipeline is empty. Add at least one node.")

        # Reset current to root
        self._current = self._root

        return self._root

    def visualize(self) -> str:
        """
        Visualize the pipeline structure

        Returns:
            String representation of the pipeline
        """
        if self._root is None:
            return "Empty pipeline"

        return self._root.visualize_structure(format="tree")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get pipeline summary

        Returns:
            Dictionary with pipeline statistics
        """
        return {
            "name": self.pipeline_name,
            "total_nodes": len(self._steps),
            "max_depth": max((s.node.depth for s in self._steps if s.node), default=0),
            "roles": {
                role.value: sum(1 for s in self._steps if s.role == role)
                for role in NodeRole
            },
            "steps": [
                {
                    "name": s.name,
                    "role": s.role.value,
                    "has_tools": s.tools is not None and len(s.tools) > 0
                }
                for s in self._steps
            ]
        }


class PipelineTemplate:
    """Pre-built pipeline templates for common patterns"""

    @staticmethod
    def sequential_pipeline(
        name: str,
        provider: Any,
        steps: List[str],
        memory: Optional[Any] = None
    ) -> FractalAgentNode:
        """
        Create a simple sequential pipeline

        Args:
            name: Pipeline name
            provider: LLM provider
            steps: List of step names
            memory: Memory system

        Returns:
            Root node of sequential pipeline
        """
        builder = PipelineBuilder(name, provider, memory)

        builder.coordinator(f"{name}_coordinator")

        for step in steps:
            builder.executor(step)

        builder.aggregator(f"{name}_aggregator")

        return builder.build()

    @staticmethod
    def research_pipeline(
        name: str,
        provider: Any,
        domains: List[str],
        memory: Optional[Any] = None
    ) -> FractalAgentNode:
        """
        Create a parallel research pipeline

        Args:
            name: Pipeline name
            provider: LLM provider
            domains: List of research domains
            memory: Memory system

        Returns:
            Root node of research pipeline
        """
        builder = PipelineBuilder(name, provider, memory)

        builder.coordinator(f"{name}_coordinator")

        # Parallel specialists
        parallel_nodes = [
            (f"research_{domain}", "specialist", None)
            for domain in domains
        ]

        builder.parallel(parallel_nodes, join_with_aggregator=True)

        return builder.build()

    @staticmethod
    def iterative_refinement(
        name: str,
        provider: Any,
        iterations: int = 3,
        memory: Optional[Any] = None
    ) -> FractalAgentNode:
        """
        Create an iterative refinement pipeline

        Args:
            name: Pipeline name
            provider: LLM provider
            iterations: Number of refinement iterations
            memory: Memory system

        Returns:
            Root node of iterative pipeline
        """
        builder = PipelineBuilder(name, provider, memory)

        builder.coordinator(f"{name}_coordinator")

        # Iterative chain
        for i in range(iterations):
            builder.executor(f"iteration_{i+1}")

        builder.aggregator(f"{name}_final")

        return builder.build()


# Convenience function
def build_pipeline(
    name: str,
    provider: Any,
    memory: Optional[Any] = None
) -> PipelineBuilder:
    """
    Create a new pipeline builder

    Args:
        name: Pipeline name
        provider: LLM provider
        memory: Memory system

    Returns:
        PipelineBuilder instance

    Example:
        ```python
        pipeline = (
            build_pipeline("my_pipeline", provider)
            .coordinator("main")
            .executor("step1")
            .executor("step2")
            .aggregator("final")
            .build()
        )
        ```
    """
    return PipelineBuilder(name, provider, memory)
