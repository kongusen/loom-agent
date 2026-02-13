"""
Tests for loom/exceptions.py - 全异常体系覆盖
"""

from loom.exceptions import (
    ConfigurationError,
    ContextBuildError,
    DelegationError,
    LLMProviderError,
    LoomError,
    MaxIterationsExceeded,
    MemoryBudgetExceeded,
    MemoryError,
    PermissionDenied,
    TaskComplete,
    ToolExecutionError,
    ToolNotFoundError,
)

# ==================== LoomError ====================


class TestLoomError:
    def test_basic_message(self):
        err = LoomError("something broke")
        assert str(err) == "something broke"
        assert err.agent_id == ""
        assert err.iteration == -1
        assert err.context == {}
        assert err.suggested_fix == ""

    def test_with_all_kwargs(self):
        err = LoomError(
            "fail",
            agent_id="a1",
            iteration=3,
            context={"k": "v"},
            suggested_fix="try again",
        )
        assert err.agent_id == "a1"
        assert err.iteration == 3
        assert err.context == {"k": "v"}
        assert err.suggested_fix == "try again"

    def test_to_dict_minimal(self):
        d = LoomError("msg").to_dict()
        assert d == {"error_type": "LoomError", "message": "msg"}

    def test_to_dict_full(self):
        d = LoomError(
            "msg",
            agent_id="a",
            iteration=0,
            context={"x": 1},
            suggested_fix="fix it",
        ).to_dict()
        assert d["agent_id"] == "a"
        assert d["iteration"] == 0
        assert d["context"] == {"x": 1}
        assert d["suggested_fix"] == "fix it"

    def test_to_dict_negative_iteration_excluded(self):
        d = LoomError("msg", iteration=-1).to_dict()
        assert "iteration" not in d

    def test_is_exception(self):
        assert issubclass(LoomError, Exception)


# ==================== TaskComplete ====================


class TestTaskComplete:
    def test_basic(self):
        err = TaskComplete("done")
        assert err.message == "done"
        assert err.output is None
        assert "Task completed: done" in str(err)

    def test_with_output(self):
        err = TaskComplete("ok", output={"data": 42})
        assert err.output == {"data": 42}

    def test_inherits_loom_error(self):
        err = TaskComplete("x", agent_id="a1")
        assert err.agent_id == "a1"
        assert isinstance(err, LoomError)

    def test_to_dict(self):
        d = TaskComplete("done", agent_id="a").to_dict()
        assert d["error_type"] == "TaskComplete"
        assert "Task completed: done" in d["message"]


# ==================== PermissionDenied ====================


class TestPermissionDenied:
    def test_basic(self):
        err = PermissionDenied("bash")
        assert err.tool_name == "bash"
        assert err.reason == ""
        assert "PERMISSION_MISSING" in str(err)
        assert "'bash'" in str(err)

    def test_with_reason(self):
        err = PermissionDenied("bash", reason="not whitelisted")
        assert err.reason == "not whitelisted"
        assert "not whitelisted" in str(err)

    def test_default_suggested_fix(self):
        err = PermissionDenied("bash")
        assert "tool_policy" in err.suggested_fix
        assert "bash" in err.suggested_fix

    def test_custom_suggested_fix(self):
        err = PermissionDenied("bash", suggested_fix="custom fix")
        assert err.suggested_fix == "custom fix"


# ==================== ToolExecutionError ====================


class TestToolExecutionError:
    def test_basic(self):
        err = ToolExecutionError("search", "timeout")
        assert err.tool_name == "search"
        assert err.reason == "timeout"
        assert "search" in str(err)
        assert "timeout" in str(err)

    def test_context_includes_tool_name(self):
        err = ToolExecutionError("search", "fail")
        assert err.context["tool_name"] == "search"

    def test_default_suggested_fix(self):
        err = ToolExecutionError("search", "fail")
        assert "search" in err.suggested_fix

    def test_to_dict(self):
        d = ToolExecutionError("t", "r", agent_id="a").to_dict()
        assert d["error_type"] == "ToolExecutionError"
        assert d["agent_id"] == "a"


# ==================== ToolNotFoundError ====================


class TestToolNotFoundError:
    def test_basic(self):
        err = ToolNotFoundError("missing_tool")
        assert err.tool_name == "missing_tool"
        assert err.available == []
        assert "missing_tool" in str(err)

    def test_with_available(self):
        err = ToolNotFoundError("x", available=["a", "b", "c"])
        assert "a, b, c" in str(err)

    def test_available_truncated_to_5(self):
        tools = [f"tool_{i}" for i in range(10)]
        err = ToolNotFoundError("x", available=tools)
        msg = str(err)
        assert "tool_0" in msg
        assert "tool_4" in msg
        # tool_5 through tool_9 should NOT appear
        assert "tool_5" not in msg

    def test_suggested_fix(self):
        err = ToolNotFoundError("x")
        assert "x" in err.suggested_fix


# ==================== MemoryError / MemoryBudgetExceeded ====================


class TestMemoryErrors:
    def test_memory_error_is_loom_error(self):
        assert issubclass(MemoryError, LoomError)

    def test_budget_exceeded(self):
        err = MemoryBudgetExceeded("L1", 9000, 8000)
        assert err.tier == "L1"
        assert err.used == 9000
        assert err.limit == 8000
        assert "9000" in str(err)
        assert "8000" in str(err)

    def test_budget_exceeded_suggested_fix(self):
        err = MemoryBudgetExceeded("L2", 100, 50)
        assert "L2" in err.suggested_fix

    def test_budget_exceeded_inherits_memory_error(self):
        assert issubclass(MemoryBudgetExceeded, MemoryError)


# ==================== ContextBuildError ====================


class TestContextBuildError:
    def test_basic(self):
        err = ContextBuildError("RAG", "connection failed")
        assert err.source == "RAG"
        assert err.reason == "connection failed"
        assert "RAG" in str(err)

    def test_context_includes_source(self):
        err = ContextBuildError("L4", "timeout")
        assert err.context["source"] == "L4"

    def test_suggested_fix(self):
        err = ContextBuildError("L4", "timeout")
        assert "L4" in err.suggested_fix


# ==================== MaxIterationsExceeded ====================


class TestMaxIterationsExceeded:
    def test_basic(self):
        err = MaxIterationsExceeded(10)
        assert err.max_iterations == 10
        assert "10" in str(err)

    def test_suggested_fix(self):
        err = MaxIterationsExceeded(5)
        assert "max_iterations" in err.suggested_fix


# ==================== DelegationError ====================


class TestDelegationError:
    def test_basic(self):
        err = DelegationError("child-1", "not found")
        assert err.target_agent == "child-1"
        assert err.reason == "not found"
        assert "child-1" in str(err)

    def test_context_includes_target(self):
        err = DelegationError("child-1", "fail")
        assert err.context["target_agent"] == "child-1"

    def test_suggested_fix(self):
        err = DelegationError("child-1", "fail")
        assert "child-1" in err.suggested_fix


# ==================== LLMProviderError ====================


class TestLLMProviderError:
    def test_basic(self):
        err = LLMProviderError("openai", "rate limit")
        assert err.provider == "openai"
        assert err.reason == "rate limit"
        assert "openai" in str(err)

    def test_suggested_fix(self):
        err = LLMProviderError("anthropic", "timeout")
        assert "API key" in err.suggested_fix


# ==================== ConfigurationError ====================


class TestConfigurationError:
    def test_basic(self):
        err = ConfigurationError("max_tokens", "must be positive")
        assert err.param == "max_tokens"
        assert err.reason == "must be positive"
        assert "max_tokens" in str(err)

    def test_suggested_fix(self):
        err = ConfigurationError("model", "invalid")
        assert "model" in err.suggested_fix
