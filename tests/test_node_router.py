"""
Tests for Router Node

Tests the AttentionRouter class which routes tasks to appropriate nodes.
"""

import pytest
from unittest.mock import Mock, AsyncMock

from loom.node.router import AttentionRouter
from loom.kernel.core.dispatcher import Dispatcher
from loom.protocol.cloudevents import CloudEvent
from loom.llm import LLMProvider, StreamChunk
from loom.protocol.interfaces import NodeProtocol


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, node_id: str, role: str, process_result=None):
        self.node_id = node_id
        self.role = role
        self.source_uri = f"/node/{node_id}"
        self.process_result = process_result or {"output": f"Handled by {node_id}"}

    async def process(self, event):
        return self.process_result


class TestAttentionRouter:
    """Test AttentionRouter functionality."""

    @pytest.fixture
    async def dispatcher(self):
        """Create a Dispatcher with a test bus."""
        from loom.kernel.core.bus import UniversalEventBus
        bus = UniversalEventBus()
        await bus.connect()
        dispatcher = Dispatcher(bus)
        yield dispatcher
        await bus.disconnect()

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = Mock(spec=LLMProvider)
        return provider

    def test_initialization(self, dispatcher, mock_provider):
        """Test router initialization."""
        agents = [
            MockAgent("agent1", "Role 1"),
            MockAgent("agent2", "Role 2")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        assert router.node_id == "router"
        assert len(router.agents) == 2
        assert "agent1" in router.agents
        assert "agent2" in router.agents
        assert router.registry == {
            "agent1": "Role 1",
            "agent2": "Role 2"
        }

    def test_initialization_with_empty_agents(self, dispatcher, mock_provider):
        """Test router with no agents."""
        router = AttentionRouter("router", dispatcher, [], mock_provider)
        assert len(router.agents) == 0
        assert router.registry == {}

    @pytest.mark.asyncio
    async def test_process_with_no_task(self, dispatcher, mock_provider):
        """Test processing when no task is provided."""
        agents = [MockAgent("agent1", "Role 1")]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={}
        )

        result = await router.process(event)
        assert result == {"error": "No task provided"}

    @pytest.mark.asyncio
    async def test_process_successful_routing(self, dispatcher, mock_provider):
        """Test successful routing to an agent."""
        agents = [
            MockAgent("coder", "Code expert"),
            MockAgent("writer", "Writing expert")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        # Mock LLM response
        mock_response = Mock()
        mock_response.content = "coder"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Mock the call to agent
        original_call = router.call
        call_results = []

        async def mock_call(target, data):
            call_results.append((target, data))
            return agents[0].process_result

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "Write a Python function"}
        )

        result = await router.process(event)

        assert result["routed_to"] == "coder"
        assert "result" in result
        assert mock_provider.chat.called

        # Restore
        router.call = original_call

    @pytest.mark.asyncio
    async def test_process_with_fuzzy_match(self, dispatcher, mock_provider):
        """Test routing with fuzzy matching in LLM response."""
        agents = [
            MockAgent("agent_a", "Role A"),
            MockAgent("agent_b", "Role B")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        # Mock LLM response with extra text
        mock_response = Mock()
        mock_response.content = "I select agent_a for this task"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Mock the call to agent
        async def mock_call(target, data):
            return agents[0].process_result

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "test task"}
        )

        result = await router.process(event)

        assert result["routed_to"] == "agent_a"

    @pytest.mark.asyncio
    async def test_process_with_invalid_selection(self, dispatcher, mock_provider):
        """Test routing when LLM selects invalid agent."""
        agents = [MockAgent("agent1", "Role 1")]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        # Mock LLM response with non-existent agent
        mock_response = Mock()
        mock_response.content = "nonexistent_agent"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "test task"}
        )

        result = await router.process(event)

        assert "error" in result
        assert "nonexistent_agent" in result["error"]

    @pytest.mark.asyncio
    async def test_process_with_whitespace_selection(self, dispatcher, mock_provider):
        """Test routing when LLM response has whitespace."""
        agents = [
            MockAgent("agent1", "Role 1"),
            MockAgent("agent2", "Role 2")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        # Mock LLM response with whitespace
        mock_response = Mock()
        mock_response.content = "  agent1  "
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Mock the call to agent
        async def mock_call(target, data):
            return agents[0].process_result

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "test task"}
        )

        result = await router.process(event)

        assert result["routed_to"] == "agent1"

    @pytest.mark.asyncio
    async def test_registry_construction(self, dispatcher, mock_provider):
        """Test that registry is correctly constructed."""
        agents = [
            MockAgent("agent_1", "Expert in Python"),
            MockAgent("agent_2", "Expert in JavaScript"),
            MockAgent("agent_3", "Expert in Go")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        expected_registry = {
            "agent_1": "Expert in Python",
            "agent_2": "Expert in JavaScript",
            "agent_3": "Expert in Go"
        }
        assert router.registry == expected_registry

    @pytest.mark.asyncio
    async def test_prompt_includes_all_agents(self, dispatcher, mock_provider):
        """Test that the routing prompt includes all agents."""
        agents = [
            MockAgent("agent1", "Role 1"),
            MockAgent("agent2", "Role 2"),
            MockAgent("agent3", "Role 3")
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        mock_response = Mock()
        mock_response.content = "agent1"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Mock the call to agent
        async def mock_call(target, data):
            return {}

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "test task"}
        )

        await router.process(event)

        # Verify chat was called
        assert mock_provider.chat.called
        call_args = mock_provider.chat.call_args
        messages = call_args[0][0]

        # Check that prompt contains agent info
        prompt = messages[0]["content"]
        assert "agent1" in prompt
        assert "agent2" in prompt
        assert "agent3" in prompt
        assert "Role 1" in prompt
        assert "Role 2" in prompt
        assert "Role 3" in prompt

    @pytest.mark.asyncio
    async def test_routes_to_correct_agent(self, dispatcher, mock_provider):
        """Test that router actually calls the selected agent."""
        agents = [
            MockAgent("agent1", "Role 1", process_result={"output": "Result 1"}),
            MockAgent("agent2", "Role 2", process_result={"output": "Result 2"})
        ]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        # Mock LLM to select agent2
        mock_response = Mock()
        mock_response.content = "agent2"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Track which agent was called
        called_agent = []

        async def mock_call(target, data):
            called_agent.append(target)
            return agents[1].process_result

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "test task"}
        )

        result = await router.process(event)

        assert len(called_agent) == 1
        assert called_agent[0] == "/node/agent2"
        assert result["result"] == {"output": "Result 2"}

    @pytest.mark.asyncio
    async def test_process_passes_task_to_agent(self, dispatcher, mock_provider):
        """Test that router passes the task to the selected agent."""
        agents = [MockAgent("agent1", "Role 1")]
        router = AttentionRouter("router", dispatcher, agents, mock_provider)

        mock_response = Mock()
        mock_response.content = "agent1"
        mock_provider.chat = AsyncMock(return_value=mock_response)

        # Capture data passed to agent
        passed_data = []

        async def mock_call(target, data):
            passed_data.append(data)
            return {"output": "done"}

        router.call = mock_call

        event = CloudEvent.create(
            source="/caller",
            type="node.request",
            data={"task": "Write code"}
        )

        await router.process(event)

        assert len(passed_data) == 1
        assert passed_data[0]["task"] == "Write code"

    @pytest.mark.asyncio
    async def test_with_crew_nodes(self, dispatcher, mock_provider):
        """Test that router can handle CrewNode instances."""
        # Create mock crew nodes
        crew1 = Mock(spec=NodeProtocol)
        crew1.node_id = "crew1"
        crew1.role = "Data analysis crew"
        crew1.source_uri = "/node/crew1"

        crew2 = Mock(spec=NodeProtocol)
        crew2.node_id = "crew2"
        crew2.role = "Writing crew"
        crew2.source_uri = "/node/crew2"

        router = AttentionRouter("router", dispatcher, [crew1, crew2], mock_provider)

        assert "crew1" in router.agents
        assert "crew2" in router.agents
        assert router.registry["crew1"] == "Data analysis crew"
        assert router.registry["crew2"] == "Writing crew"
