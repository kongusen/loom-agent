"""
Unit tests for loom.crew.roles module

Tests cover:
- Role dataclass creation and validation
- Role method functionality (allows_tool, has_capability, to_dict, from_dict)
- RoleRegistry operations (register, get, update, remove, etc.)
- Built-in roles availability and correctness
"""

import pytest
from loom.crew.roles import Role, RoleRegistry, BUILTIN_ROLES


class TestRole:
    """Tests for Role dataclass"""

    def test_role_creation_minimal(self):
        """Test creating role with minimal required fields"""
        role = Role(
            name="test_role",
            description="Test role",
            goal="Test goal"
        )

        assert role.name == "test_role"
        assert role.description == "Test role"
        assert role.goal == "Test goal"
        assert role.backstory == ""
        assert role.tools == []
        assert role.capabilities == []
        assert role.max_iterations == 20
        assert role.model_name is None
        assert role.delegation is False
        assert role.metadata == {}

    def test_role_creation_full(self):
        """Test creating role with all fields"""
        role = Role(
            name="full_role",
            description="Full test role",
            goal="Complete test",
            backstory="Test backstory",
            tools=["tool1", "tool2"],
            capabilities=["cap1", "cap2"],
            max_iterations=30,
            model_name="gpt-4",
            delegation=True,
            metadata={"key": "value"}
        )

        assert role.name == "full_role"
        assert role.description == "Full test role"
        assert role.goal == "Complete test"
        assert role.backstory == "Test backstory"
        assert role.tools == ["tool1", "tool2"]
        assert role.capabilities == ["cap1", "cap2"]
        assert role.max_iterations == 30
        assert role.model_name == "gpt-4"
        assert role.delegation is True
        assert role.metadata == {"key": "value"}

    def test_role_creation_empty_name_raises(self):
        """Test that empty name raises ValueError"""
        with pytest.raises(ValueError, match="name cannot be empty"):
            Role(
                name="",
                description="Test",
                goal="Test goal"
            )

    def test_role_creation_empty_goal_raises(self):
        """Test that empty goal raises ValueError"""
        with pytest.raises(ValueError, match="must have a goal"):
            Role(
                name="test",
                description="Test",
                goal=""
            )

    def test_allows_tool_empty_tools(self):
        """Test allows_tool with no tools configured"""
        role = Role(name="test", description="Test", goal="Test", tools=[])
        assert role.allows_tool("any_tool") is False

    def test_allows_tool_wildcard(self):
        """Test allows_tool with wildcard (all tools allowed)"""
        role = Role(name="test", description="Test", goal="Test", tools=["*"])
        assert role.allows_tool("any_tool") is True
        assert role.allows_tool("another_tool") is True

    def test_allows_tool_specific_tools(self):
        """Test allows_tool with specific tool list"""
        role = Role(
            name="test",
            description="Test",
            goal="Test",
            tools=["read_file", "write_file"]
        )
        assert role.allows_tool("read_file") is True
        assert role.allows_tool("write_file") is True
        assert role.allows_tool("bash") is False

    def test_has_capability(self):
        """Test has_capability method"""
        role = Role(
            name="test",
            description="Test",
            goal="Test",
            capabilities=["coding", "testing"]
        )
        assert role.has_capability("coding") is True
        assert role.has_capability("testing") is True
        assert role.has_capability("research") is False

    def test_to_dict(self):
        """Test serialization to dict"""
        role = Role(
            name="test",
            description="Test role",
            goal="Test goal",
            backstory="Test backstory",
            tools=["tool1"],
            capabilities=["cap1"],
            max_iterations=25,
            model_name="gpt-4",
            delegation=True,
            metadata={"key": "value"}
        )

        data = role.to_dict()

        assert data["name"] == "test"
        assert data["description"] == "Test role"
        assert data["goal"] == "Test goal"
        assert data["backstory"] == "Test backstory"
        assert data["tools"] == ["tool1"]
        assert data["capabilities"] == ["cap1"]
        assert data["max_iterations"] == 25
        assert data["model_name"] == "gpt-4"
        assert data["delegation"] is True
        assert data["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """Test deserialization from dict"""
        data = {
            "name": "test",
            "description": "Test role",
            "goal": "Test goal",
            "backstory": "Test backstory",
            "tools": ["tool1"],
            "capabilities": ["cap1"],
            "max_iterations": 25,
            "model_name": "gpt-4",
            "delegation": True,
            "metadata": {"key": "value"}
        }

        role = Role.from_dict(data)

        assert role.name == "test"
        assert role.description == "Test role"
        assert role.goal == "Test goal"
        assert role.backstory == "Test backstory"
        assert role.tools == ["tool1"]
        assert role.capabilities == ["cap1"]
        assert role.max_iterations == 25
        assert role.model_name == "gpt-4"
        assert role.delegation is True
        assert role.metadata == {"key": "value"}

    def test_from_dict_minimal(self):
        """Test deserialization with minimal data"""
        data = {
            "name": "test",
            "description": "Test role",
            "goal": "Test goal"
        }

        role = Role.from_dict(data)

        assert role.name == "test"
        assert role.description == "Test role"
        assert role.goal == "Test goal"
        assert role.backstory == ""
        assert role.tools == []
        assert role.capabilities == []
        assert role.max_iterations == 20
        assert role.model_name is None
        assert role.delegation is False
        assert role.metadata == {}

    def test_repr(self):
        """Test __repr__ method"""
        role = Role(
            name="test",
            description="Test",
            goal="Test",
            capabilities=["cap1", "cap2"],
            tools=["tool1", "tool2", "tool3"],
            delegation=True
        )

        repr_str = repr(role)

        assert "Role" in repr_str
        assert "test" in repr_str
        assert "['cap1', 'cap2']" in repr_str
        assert "tools=3" in repr_str
        assert "delegation=True" in repr_str


class TestRoleRegistry:
    """Tests for RoleRegistry class"""

    def setup_method(self):
        """Clear registry before each test"""
        RoleRegistry.clear()

    def teardown_method(self):
        """Restore built-in roles after each test"""
        from loom.crew.roles import register_builtin_roles
        register_builtin_roles()

    def test_register_role(self):
        """Test registering a role"""
        role = Role(name="test", description="Test", goal="Test")
        RoleRegistry.register(role)

        assert RoleRegistry.has_role("test") is True
        retrieved = RoleRegistry.get("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_register_duplicate_raises(self):
        """Test that registering duplicate role raises ValueError"""
        role1 = Role(name="test", description="Test 1", goal="Test 1")
        role2 = Role(name="test", description="Test 2", goal="Test 2")

        RoleRegistry.register(role1)

        with pytest.raises(ValueError, match="already registered"):
            RoleRegistry.register(role2)

    def test_update_role(self):
        """Test updating an existing role"""
        role1 = Role(name="test", description="Test 1", goal="Test 1")
        role2 = Role(name="test", description="Test 2", goal="Test 2")

        RoleRegistry.register(role1)
        RoleRegistry.update(role2)

        retrieved = RoleRegistry.get("test")
        assert retrieved.description == "Test 2"
        assert retrieved.goal == "Test 2"

    def test_update_new_role(self):
        """Test updating a non-existent role (should register it)"""
        role = Role(name="new", description="New", goal="New")
        RoleRegistry.update(role)

        assert RoleRegistry.has_role("new") is True

    def test_get_nonexistent_role(self):
        """Test getting a role that doesn't exist"""
        result = RoleRegistry.get("nonexistent")
        assert result is None

    def test_has_role(self):
        """Test has_role method"""
        role = Role(name="test", description="Test", goal="Test")
        RoleRegistry.register(role)

        assert RoleRegistry.has_role("test") is True
        assert RoleRegistry.has_role("nonexistent") is False

    def test_list_roles(self):
        """Test list_roles method"""
        role1 = Role(name="role1", description="Role 1", goal="Goal 1")
        role2 = Role(name="role2", description="Role 2", goal="Goal 2")

        RoleRegistry.register(role1)
        RoleRegistry.register(role2)

        roles = RoleRegistry.list_roles()

        assert len(roles) == 2
        role_names = {r.name for r in roles}
        assert "role1" in role_names
        assert "role2" in role_names

    def test_list_role_names(self):
        """Test list_role_names method"""
        role1 = Role(name="role1", description="Role 1", goal="Goal 1")
        role2 = Role(name="role2", description="Role 2", goal="Goal 2")

        RoleRegistry.register(role1)
        RoleRegistry.register(role2)

        names = RoleRegistry.list_role_names()

        assert len(names) == 2
        assert "role1" in names
        assert "role2" in names

    def test_remove_role(self):
        """Test removing a role"""
        role = Role(name="test", description="Test", goal="Test")
        RoleRegistry.register(role)

        assert RoleRegistry.has_role("test") is True

        removed = RoleRegistry.remove("test")

        assert removed is True
        assert RoleRegistry.has_role("test") is False

    def test_remove_nonexistent_role(self):
        """Test removing a role that doesn't exist"""
        removed = RoleRegistry.remove("nonexistent")
        assert removed is False

    def test_clear_registry(self):
        """Test clearing the registry"""
        role1 = Role(name="role1", description="Role 1", goal="Goal 1")
        role2 = Role(name="role2", description="Role 2", goal="Goal 2")

        RoleRegistry.register(role1)
        RoleRegistry.register(role2)

        assert len(RoleRegistry.list_roles()) == 2

        RoleRegistry.clear()

        assert len(RoleRegistry.list_roles()) == 0

    def test_find_by_capability(self):
        """Test finding roles by capability"""
        role1 = Role(
            name="role1",
            description="Role 1",
            goal="Goal 1",
            capabilities=["coding", "testing"]
        )
        role2 = Role(
            name="role2",
            description="Role 2",
            goal="Goal 2",
            capabilities=["research", "analysis"]
        )
        role3 = Role(
            name="role3",
            description="Role 3",
            goal="Goal 3",
            capabilities=["coding", "research"]
        )

        RoleRegistry.register(role1)
        RoleRegistry.register(role2)
        RoleRegistry.register(role3)

        coding_roles = RoleRegistry.find_by_capability("coding")
        assert len(coding_roles) == 2
        coding_names = {r.name for r in coding_roles}
        assert "role1" in coding_names
        assert "role3" in coding_names

        research_roles = RoleRegistry.find_by_capability("research")
        assert len(research_roles) == 2
        research_names = {r.name for r in research_roles}
        assert "role2" in research_names
        assert "role3" in research_names

        testing_roles = RoleRegistry.find_by_capability("testing")
        assert len(testing_roles) == 1
        assert testing_roles[0].name == "role1"


class TestBuiltinRoles:
    """Tests for built-in roles"""

    def test_builtin_roles_dict_exists(self):
        """Test that BUILTIN_ROLES dict is defined"""
        assert BUILTIN_ROLES is not None
        assert isinstance(BUILTIN_ROLES, dict)

    def test_builtin_roles_count(self):
        """Test that we have expected built-in roles"""
        expected_roles = [
            "manager",
            "researcher",
            "developer",
            "qa_engineer",
            "security_auditor",
            "tech_writer"
        ]

        for role_name in expected_roles:
            assert role_name in BUILTIN_ROLES, f"Missing built-in role: {role_name}"

    def test_manager_role(self):
        """Test manager role configuration"""
        manager = BUILTIN_ROLES["manager"]

        assert manager.name == "manager"
        assert manager.delegation is True
        assert "delegate" in manager.tools or "task" in manager.tools
        assert "coordination" in manager.capabilities or "planning" in manager.capabilities

    def test_researcher_role(self):
        """Test researcher role configuration"""
        researcher = BUILTIN_ROLES["researcher"]

        assert researcher.name == "researcher"
        assert "read_file" in researcher.tools or "grep" in researcher.tools
        assert "research" in researcher.capabilities or "information_gathering" in researcher.capabilities

    def test_developer_role(self):
        """Test developer role configuration"""
        developer = BUILTIN_ROLES["developer"]

        assert developer.name == "developer"
        assert "write_file" in developer.tools or "edit_file" in developer.tools
        assert "coding" in developer.capabilities

    def test_qa_engineer_role(self):
        """Test QA engineer role configuration"""
        qa = BUILTIN_ROLES["qa_engineer"]

        assert qa.name == "qa_engineer"
        assert "bash" in qa.tools or "read_file" in qa.tools
        assert "testing" in qa.capabilities or "quality_assurance" in qa.capabilities

    def test_security_auditor_role(self):
        """Test security auditor role configuration"""
        auditor = BUILTIN_ROLES["security_auditor"]

        assert auditor.name == "security_auditor"
        assert "read_file" in auditor.tools or "grep" in auditor.tools
        assert "security_analysis" in auditor.capabilities

    def test_tech_writer_role(self):
        """Test tech writer role configuration"""
        writer = BUILTIN_ROLES["tech_writer"]

        assert writer.name == "tech_writer"
        assert "write_file" in writer.tools or "read_file" in writer.tools
        assert "documentation" in writer.capabilities or "technical_writing" in writer.capabilities

    def test_builtin_roles_auto_registered(self):
        """Test that built-in roles are auto-registered"""
        # Built-in roles should be registered on module import
        for role_name in BUILTIN_ROLES.keys():
            assert RoleRegistry.has_role(role_name), f"Built-in role not registered: {role_name}"

    def test_builtin_roles_retrievable(self):
        """Test that built-in roles can be retrieved from registry"""
        for role_name, role_def in BUILTIN_ROLES.items():
            retrieved = RoleRegistry.get(role_name)
            assert retrieved is not None, f"Cannot retrieve built-in role: {role_name}"
            assert retrieved.name == role_def.name
            assert retrieved.goal == role_def.goal


class TestRoleIntegration:
    """Integration tests for Role and RoleRegistry working together"""

    def setup_method(self):
        """Setup for integration tests"""
        RoleRegistry.clear()

    def teardown_method(self):
        """Cleanup after integration tests"""
        from loom.crew.roles import register_builtin_roles
        register_builtin_roles()

    def test_role_lifecycle(self):
        """Test complete role lifecycle: create, register, retrieve, update, remove"""
        # Create
        role = Role(
            name="lifecycle_test",
            description="Test role",
            goal="Test goal",
            tools=["tool1"]
        )

        # Register
        RoleRegistry.register(role)
        assert RoleRegistry.has_role("lifecycle_test")

        # Retrieve
        retrieved = RoleRegistry.get("lifecycle_test")
        assert retrieved.name == "lifecycle_test"
        assert retrieved.tools == ["tool1"]

        # Update
        updated_role = Role(
            name="lifecycle_test",
            description="Updated test role",
            goal="Updated goal",
            tools=["tool1", "tool2"]
        )
        RoleRegistry.update(updated_role)

        # Verify update
        retrieved_updated = RoleRegistry.get("lifecycle_test")
        assert retrieved_updated.description == "Updated test role"
        assert retrieved_updated.tools == ["tool1", "tool2"]

        # Remove
        RoleRegistry.remove("lifecycle_test")
        assert not RoleRegistry.has_role("lifecycle_test")

    def test_role_serialization_roundtrip(self):
        """Test role serialization and deserialization preserves data"""
        original = Role(
            name="roundtrip_test",
            description="Test role",
            goal="Test goal",
            backstory="Test backstory",
            tools=["tool1", "tool2"],
            capabilities=["cap1", "cap2"],
            max_iterations=25,
            model_name="gpt-4",
            delegation=True,
            metadata={"key": "value"}
        )

        # Serialize
        data = original.to_dict()

        # Deserialize
        reconstructed = Role.from_dict(data)

        # Verify all fields match
        assert reconstructed.name == original.name
        assert reconstructed.description == original.description
        assert reconstructed.goal == original.goal
        assert reconstructed.backstory == original.backstory
        assert reconstructed.tools == original.tools
        assert reconstructed.capabilities == original.capabilities
        assert reconstructed.max_iterations == original.max_iterations
        assert reconstructed.model_name == original.model_name
        assert reconstructed.delegation == original.delegation
        assert reconstructed.metadata == original.metadata
