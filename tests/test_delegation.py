import pytest
from loom.protocol.delegation import (
    SubtaskSpecification,
    DelegationRequest,
    DelegationResult,
    DELEGATE_SUBTASKS_TOOL
)

def test_subtask_specification():
    """测试 SubtaskSpecification 数据类"""
    # 最小参数
    spec = SubtaskSpecification(description="Test task")
    assert spec.description == "Test task"
    assert spec.role is None
    assert spec.tools is None
    
    # 完整参数
    spec = SubtaskSpecification(
        description="Test task",
        role="specialist",
        tools=["tool1", "tool2"],
        max_tokens=1000,
        metadata={"key": "value"}
    )
    assert spec.role == "specialist"
    assert len(spec.tools) == 2
    assert spec.max_tokens == 1000

def test_delegation_request():
    """测试 DelegationRequest 数据类"""
    subtasks = [SubtaskSpecification(description="t1")]
    req = DelegationRequest(subtasks=subtasks)
    
    assert len(req.subtasks) == 1
    assert req.execution_mode == "parallel"  # 默认值
    assert req.synthesis_strategy == "auto"  # 默认值

def test_delegate_subtasks_tool_definition():
    """测试工具定义符合 MCP 规范"""
    tool = DELEGATE_SUBTASKS_TOOL
    assert tool.name == "delegate_subtasks"
    
    schema = tool.input_schema
    assert "subtasks" in schema["properties"]
    assert schema["required"] == ["subtasks"]
    
    subtask_props = schema["properties"]["subtasks"]["items"]["properties"]
    assert "description" in subtask_props
    assert "role" in subtask_props
