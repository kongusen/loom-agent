"""
Tests for Crew Node
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.node.crew import CrewNode
from loom.node.base import Node
from loom.kernel.core import Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.protocol.interfaces import NodeProtocol
from loom.memory.sanitizers import BubbleUpSanitizer


class MockAgentNode(Node):
    """Mock agent for testing."""

    def __init__(self, node_id: str, dispatcher: Dispatcher, response_value: str = "OK"):
        super().__init__(node_id, dispatcher)
        self.response_value = response_value

    async def process(self, event: CloudEvent) -> any:
        """Return mock response."""
        return {"response": self.response_value}


class TestCrewNode:
    """Test CrewNode class."""

    @pytest.fixture
    def dispatcher(self):
        """Create a dispatcher for testing."""
        from loom.kernel.core import Dispatcher, UniversalEventBus
        bus = UniversalEventBus()
        return Dispatcher(bus)

    @pytest.fixture
    def mock_agents(self, dispatcher):
        """Create mock agents."""
        agents = [
            MockAgentNode("agent1", dispatcher, "Agent1 response"),
            MockAgentNode("agent2", dispatcher, "Agent2 response"),
            MockAgentNode("agent3", dispatcher, "Agent3 response"),
        ]
        return agents

    @pytest.fixture
    def crew(self, dispatcher, mock_agents):
        """Create a crew node."""
        return CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents,
            pattern="sequential"
        )

    def test_initialization(self, dispatcher, mock_agents):
        """Test crew initialization."""
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents,
            pattern="sequential"
        )
        assert crew.node_id == "test_crew"
        assert crew.agents == mock_agents
        assert crew.pattern == "sequential"
        assert crew.sanitizer is not None

    def test_initialization_with_parallel_pattern(self, dispatcher, mock_agents):
        """Test crew initialization with parallel pattern."""
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents,
            pattern="parallel"
        )
        assert crew.pattern == "parallel"

    def test_initialization_default_sanitizer(self, dispatcher, mock_agents):
        """Test that default sanitizer is BubbleUpSanitizer."""
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents
        )
        assert isinstance(crew.sanitizer, BubbleUpSanitizer)

    def test_initialization_custom_sanitizer(self, dispatcher, mock_agents):
        """Test crew initialization with custom sanitizer."""
        custom_sanitizer = MagicMock()
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents,
            sanitizer=custom_sanitizer
        )
        assert crew.sanitizer == custom_sanitizer

    @pytest.mark.asyncio
    async def test_process_sequential_pattern(self, crew):
        """Test processing with sequential pattern."""
        event = CloudEvent.create(
            source="/test",
            type="node.request",
            data={"task": "Initial task"}
        )

        # Mock the call method to return agent responses
        crew.call = AsyncMock(side_effect=[
            {"response": "Agent1 response"},
            {"response": "Agent2 response"},
            {"response": "Agent3 response"}
        ])

        # Mock sanitizer
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized response")

        result = await crew.process(event)

        assert "final_output" in result
        assert result["final_output"] == "Agent3 response"
        assert "trace" in result
        assert len(result["trace"]) == 3

    @pytest.mark.asyncio
    async def test_process_parallel_pattern_unsupported(self, dispatcher, mock_agents):
        """Test that parallel pattern returns error."""
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=mock_agents,
            pattern="parallel"
        )

        event = CloudEvent.create(
            source="/test",
            type="node.request",
            data={"task": "Test task"}
        )

        result = await crew.process(event)
        assert "error" in result
        assert "Unsupported pattern" in result["error"]

    @pytest.mark.asyncio
    async def test_process_gets_task_from_event_data(self, crew):
        """Test that process extracts task from event data."""
        event = CloudEvent.create(
            source="/test",
            type="node.request",
            data={"task": "Test task from event"}
        )

        crew.call = AsyncMock(return_value={"response": "OK"})
        crew.sanitizer.sanitize = AsyncMock(return_value="sanitized")

        await crew.process(event)

        # Verify that call was made with the task
        assert crew.call.called

    @pytest.mark.asyncio
    async def test_process_with_empty_task(self, crew):
        """Test processing with empty task."""
        event = CloudEvent.create(
            source="/test",
            type="node.request",
            data={"task": ""}
        )

        crew.call = AsyncMock(return_value={"response": "Result"})
        crew.sanitizer.sanitize = AsyncMock(return_value="sanitized")

        result = await crew.process(event)
        assert "final_output" in result

    @pytest.mark.asyncio
    async def test_process_with_no_task_key(self, crew):
        """Test processing when event data has no 'task' key."""
        event = CloudEvent.create(
            source="/test",
            type="node.request",
            data={}
        )

        crew.call = AsyncMock(return_value={"response": "Result"})
        crew.sanitizer.sanitize = AsyncMock(return_value="sanitized")

        result = await crew.process(event)
        assert "final_output" in result

    @pytest.mark.asyncio
    async def test_execute_sequential(self, crew):
        """Test sequential execution of agents."""
        crew.call = AsyncMock(side_effect=[
            {"response": "Response 1"},
            {"response": "Response 2"},
            {"response": "Response 3"}
        ])
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        result = await crew._execute_sequential("Initial task")

        assert result["final_output"] == "Response 3"
        assert len(result["trace"]) == 3
        assert result["trace"][0]["agent"] == "agent1"
        assert result["trace"][1]["agent"] == "agent2"
        assert result["trace"][2]["agent"] == "agent3"

    @pytest.mark.asyncio
    async def test_execute_sequential_passes_output_to_next_agent(self, crew):
        """Test that output of one agent is passed to the next."""
        call_count = 0

        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Return the data.task as response
            data = args[1] if len(args) > 1 else kwargs.get("data", {})
            return {"response": f"Processed: {data.get('task', '')}"}

        crew.call = mock_call
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        result = await crew._execute_sequential("Initial")

        # Each agent should receive the previous agent's output
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_sequential_handles_agent_error(self, crew):
        """Test error handling when an agent fails."""
        crew.call = AsyncMock(side_effect=[
            {"response": "OK"},
            Exception("Agent failed"),
            {"response": "Should not reach here"}
        ])

        result = await crew._execute_sequential("Task")

        assert "error" in result
        assert "agent2" in result["error"]
        assert "trace" in result

    @pytest.mark.asyncio
    async def test_execute_sequential_with_dict_response(self, crew):
        """Test handling dict response from agent."""
        crew.call = AsyncMock(return_value={"response": "Dict response", "data": "extra"})
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        result = await crew._execute_sequential("Task")

        assert "final_output" in result
        # Should extract "response" field
        assert result["final_output"] == "Dict response"

    @pytest.mark.asyncio
    async def test_execute_sequential_with_non_dict_response(self, crew):
        """Test handling non-dict response from agent."""
        crew.call = AsyncMock(return_value="String response")
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        result = await crew._execute_sequential("Task")

        assert "final_output" in result
        assert result["final_output"] == "String response"

    @pytest.mark.asyncio
    async def test_execute_sequential_with_traceparent(self, crew):
        """Test that traceparent is passed through."""
        crew.call = AsyncMock(return_value={"response": "OK"})
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        await crew._execute_sequential("Task", traceparent="trace_123")

        # Verify traceparent was used in calls
        assert crew.call.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_sequential_calls_sanitizer(self, crew):
        """Test that sanitizer is called for each response."""
        crew.call = AsyncMock(side_effect=[
            {"response": "Response 1"},
            {"response": "Response 2"},
            {"response": "Response 3"}
        ])
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        await crew._execute_sequential("Task")

        # Sanitizer should be called 3 times
        assert crew.sanitizer.sanitize.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_sequential_sanitizer_with_token_limit(self, crew):
        """Test that sanitizer is called with token limit."""
        crew.call = AsyncMock(return_value={"response": "Long response that needs sanitizing"})
        crew.sanitizer.sanitize = AsyncMock(return_value="Short")

        await crew._execute_sequential("Task")

        # Verify sanitizer was called with token limit
        call_args = crew.sanitizer.sanitize.call_args_list[0]
        assert call_args[1].get("target_token_limit") == 100

    @pytest.mark.asyncio
    async def test_execute_sequential_trace_contains_sanitized_output(self, crew):
        """Test that trace contains both output and sanitized output."""
        crew.call = AsyncMock(return_value={"response": "Original output"})
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized output")

        result = await crew._execute_sequential("Task")

        trace_entry = result["trace"][0]
        assert "output" in trace_entry
        assert trace_entry["output"] == "Original output"
        assert "sanitized" in trace_entry
        assert trace_entry["sanitized"] == "Sanitized output"

    @pytest.mark.asyncio
    async def test_execute_sequential_with_single_agent(self, dispatcher):
        """Test sequential execution with single agent."""
        agent = MockAgentNode("agent1", dispatcher, "Single response")
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=[agent],
            pattern="sequential"
        )

        crew.call = AsyncMock(return_value={"response": "Single"})
        crew.sanitizer.sanitize = AsyncMock(return_value="Sanitized")

        result = await crew._execute_sequential("Task")

        assert result["final_output"] == "Single"
        assert len(result["trace"]) == 1

    @pytest.mark.asyncio
    async def test_execute_sequential_with_empty_agents_list(self, dispatcher):
        """Test sequential execution with no agents."""
        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=[],
            pattern="sequential"
        )

        result = await crew._execute_sequential("Task")

        assert result["final_output"] == "Task"
        assert result["trace"] == []

    @pytest.mark.asyncio
    async def test_execute_sequential_preserves_chain_results(self, crew):
        """Test that all intermediate results are preserved in trace."""
        crew.call = AsyncMock(side_effect=[
            {"response": "Step 1"},
            {"response": "Step 2"},
            {"response": "Step 3"}
        ])
        crew.sanitizer.sanitize = AsyncMock(return_value="S")

        result = await crew._execute_sequential("Start")

        assert result["trace"][0]["output"] == "Step 1"
        assert result["trace"][1]["output"] == "Step 2"
        assert result["trace"][2]["output"] == "Step 3"

    def test_crew_accepts_node_protocol(self, dispatcher):
        """Test that CrewNode can accept any NodeProtocol implementation."""
        # Create mock nodes that implement NodeProtocol
        mock_node1 = MagicMock(spec=NodeProtocol)
        mock_node1.node_id = "mock1"
        mock_node1.source_uri = "mock1"

        mock_node2 = MagicMock(spec=NodeProtocol)
        mock_node2.node_id = "mock2"
        mock_node2.source_uri = "mock2"

        crew = CrewNode(
            node_id="test_crew",
            dispatcher=dispatcher,
            agents=[mock_node1, mock_node2]
        )

        assert len(crew.agents) == 2
