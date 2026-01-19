"""
Tests for Agent Card Protocol
"""


from loom.protocol.agent_card import AgentCapability, AgentCard


class TestAgentCapability:
    """Test suite for AgentCapability enum"""

    def test_reflection_value(self):
        """Test REFLECTION capability value"""
        assert AgentCapability.REFLECTION == "reflection"
        assert AgentCapability.REFLECTION.value == "reflection"

    def test_tool_use_value(self):
        """Test TOOL_USE capability value"""
        assert AgentCapability.TOOL_USE == "tool_use"
        assert AgentCapability.TOOL_USE.value == "tool_use"

    def test_planning_value(self):
        """Test PLANNING capability value"""
        assert AgentCapability.PLANNING == "planning"
        assert AgentCapability.PLANNING.value == "planning"

    def test_multi_agent_value(self):
        """Test MULTI_AGENT capability value"""
        assert AgentCapability.MULTI_AGENT == "multi_agent"
        assert AgentCapability.MULTI_AGENT.value == "multi_agent"

    def test_agent_capability_is_string_enum(self):
        """Test AgentCapability is a string enum"""
        # String enum allows direct comparison with string values
        assert AgentCapability.REFLECTION == "reflection"
        assert AgentCapability.TOOL_USE == "tool_use"


class TestAgentCard:
    """Test suite for AgentCard"""

    def test_agent_card_creation(self):
        """Test creating AgentCard with required fields"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
        )

        assert card.agent_id == "test_agent"
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.version == "1.0.0"
        assert card.capabilities == []
        assert card.metadata == {}

    def test_agent_card_with_version(self):
        """Test AgentCard with custom version"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            version="2.0.0",
        )

        assert card.version == "2.0.0"

    def test_agent_card_with_capabilities(self):
        """Test AgentCard with capabilities"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            capabilities=[AgentCapability.TOOL_USE, AgentCapability.PLANNING],
        )

        assert len(card.capabilities) == 2
        assert AgentCapability.TOOL_USE in card.capabilities
        assert AgentCapability.PLANNING in card.capabilities

    def test_agent_card_with_metadata(self):
        """Test AgentCard with custom metadata"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            metadata={"key": "value", "number": 42},
        )

        assert card.metadata == {"key": "value", "number": 42}

    def test_agent_card_all_fields(self):
        """Test AgentCard with all fields"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            version="1.5.0",
            capabilities=[AgentCapability.REFLECTION, AgentCapability.MULTI_AGENT],
            metadata={"creator": "test"},
        )

        assert card.agent_id == "test_agent"
        assert card.name == "Test Agent"
        assert card.version == "1.5.0"
        assert len(card.capabilities) == 2
        assert card.metadata["creator"] == "test"

    def test_to_dict(self):
        """Test to_dict method"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            version="1.2.0",
            capabilities=[AgentCapability.TOOL_USE],
            metadata={"key": "value"},
        )

        result = card.to_dict()

        assert result["agentId"] == "test_agent"
        assert result["name"] == "Test Agent"
        assert result["description"] == "A test agent"
        assert result["version"] == "1.2.0"
        assert result["capabilities"] == ["tool_use"]
        assert result["metadata"] == {"key": "value"}

    def test_to_dict_with_default_values(self):
        """Test to_dict with default version and empty capabilities"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
        )

        result = card.to_dict()

        assert result["version"] == "1.0.0"
        assert result["capabilities"] == []
        assert result["metadata"] == {}

    def test_to_dict_with_multiple_capabilities(self):
        """Test to_dict with multiple capabilities"""
        card = AgentCard(
            agent_id="test_agent",
            name="Test Agent",
            description="A test agent",
            capabilities=[
                AgentCapability.REFLECTION,
                AgentCapability.TOOL_USE,
                AgentCapability.PLANNING,
                AgentCapability.MULTI_AGENT,
            ],
        )

        result = card.to_dict()

        assert set(result["capabilities"]) == {
            "reflection",
            "tool_use",
            "planning",
            "multi_agent",
        }

    def test_from_dict(self):
        """Test from_dict class method"""
        data = {
            "agentId": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
            "version": "2.0.0",
            "capabilities": ["tool_use", "planning"],
            "metadata": {"key": "value"},
        }

        card = AgentCard.from_dict(data)

        assert card.agent_id == "test_agent"
        assert card.name == "Test Agent"
        assert card.description == "A test agent"
        assert card.version == "2.0.0"
        assert len(card.capabilities) == 2
        assert AgentCapability.TOOL_USE in card.capabilities
        assert AgentCapability.PLANNING in card.capabilities
        assert card.metadata == {"key": "value"}

    def test_from_dict_with_minimal_fields(self):
        """Test from_dict with only required fields"""
        data = {
            "agentId": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
        }

        card = AgentCard.from_dict(data)

        assert card.agent_id == "test_agent"
        assert card.version == "1.0.0"
        assert card.capabilities == []
        assert card.metadata == {}

    def test_from_dict_without_capabilities(self):
        """Test from_dict without capabilities key"""
        data = {
            "agentId": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
        }

        card = AgentCard.from_dict(data)

        assert card.capabilities == []

    def test_from_dict_without_metadata(self):
        """Test from_dict without metadata key"""
        data = {
            "agentId": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
        }

        card = AgentCard.from_dict(data)

        assert card.metadata == {}

    def test_from_dict_preserves_extra_fields(self):
        """Test from_dict preserves extra fields in metadata"""
        data = {
            "agentId": "test_agent",
            "name": "Test Agent",
            "description": "A test agent",
            "capabilities": ["reflection"],
            "extraField": "extra_value",
        }

        card = AgentCard.from_dict(data)

        # Extra field should not be in the AgentCard
        assert not hasattr(card, "extraField")
