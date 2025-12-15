"""
Loom v0.1.6 - 导入测试

测试新架构的所有导入是否正常工作
"""


def test_core_imports():
    """测试核心模块导入"""
    print("Testing core imports...")

    from loom.core import (
        Message,
        BaseAgent,
        create_agent,
        AgentExecutor,
        ContextManager,
        create_context_manager,
        LoomError,
        AgentError,
        ExecutionError,
    )

    print("✓ Core imports successful")


def test_agent_imports():
    """测试 Agent 导入"""
    print("Testing agent imports...")

    import loom

    print("✓ Agent imports successful")


def test_builtin_imports():
    """测试内置模块导入"""
    print("Testing builtin imports...")

    from loom.builtin import (
        OpenAILLM,
        tool,
        ToolBuilder,
        InMemoryMemory,
        PersistentMemory,
        StructuredCompressor,
        CompressionConfig,
    )

    print("✓ Builtin imports successful")


def test_patterns_imports():
    """测试模式导入"""
    print("Testing patterns imports...")

    from loom.patterns import (
        Crew,
        CrewRole,
        sequential_crew,
        parallel_crew,
        coordinated_crew,
        SmartCoordinator,
        ParallelExecutor,
        ErrorRecovery,
        CrewTracer,
        CrewPresets,
    )

    print("✓ Patterns imports successful")


def test_interfaces_imports():
    """测试接口导入"""
    print("Testing interfaces imports...")

    from loom.interfaces import (
        BaseLLM,
        BaseTool,
        BaseMemory,
        BaseCompressor,
    )

    print("✓ Interfaces imports successful")


def test_top_level_imports():
    """测试顶级导入"""
    print("Testing top-level imports...")

    from loom import (
        SimpleAgent,
        Message,
        tool,
        ToolBuilder,
        OpenAILLM,
        Crew,
        CrewRole,
    )

    print("✓ Top-level imports successful")


def test_tool_decorator():
    """测试 @tool 装饰器"""
    print("Testing @tool decorator...")

    from loom import tool

    @tool(name="test_tool", description="A test tool")
    def test_func(x: int) -> int:
        """Test function"""
        return x * 2

    # 检查工具属性
    assert hasattr(test_func, "name")
    assert hasattr(test_func, "description")
    assert hasattr(test_func, "execute")
    assert hasattr(test_func, "to_schema")

    assert test_func.name == "test_tool"
    assert test_func.description == "A test tool"

    # 检查 schema
    schema = test_func.to_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"
    assert "parameters" in schema["function"]

    print("✓ @tool decorator works correctly")


def test_message():
    """测试 Message"""
    print("Testing Message...")

    from loom import Message

    # 创建消息
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

    # 测试 with_history
    msg2 = Message(role="assistant", content="Hi")
    msg3 = msg2.with_history([msg, msg2])
    assert hasattr(msg3, "history")
    assert len(msg3.history) == 2

    print("✓ Message works correctly")


def test_context_manager():
    """测试 ContextManager"""
    print("Testing ContextManager...")

    from loom.core import ContextManager, create_context_manager

    # 创建默认 ContextManager
    cm = ContextManager()
    assert cm.max_context_tokens == 100000
    assert cm.compressor is None
    assert cm.memory is None

    # 使用工厂函数
    cm2 = create_context_manager(max_context_tokens=50000)
    assert cm2.max_context_tokens == 50000

    print("✓ ContextManager works correctly")


def main():
    """运行所有测试"""
    print("=" * 80)
    print("Loom v0.1.6 - Import Test")
    print("=" * 80)
    print()

    tests = [
        test_core_imports,
        test_agent_imports,
        test_builtin_imports,
        test_patterns_imports,
        test_interfaces_imports,
        test_top_level_imports,
        test_tool_decorator,
        test_message,
        test_context_manager,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        print()

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)

    if failed == 0:
        print("\n🎉 All tests passed! The new architecture is working correctly.")
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the errors above.")


if __name__ == "__main__":
    main()
