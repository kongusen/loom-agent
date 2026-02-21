"""Unit tests for config, errors, session."""

import pytest
from loom.config import AgentConfig, ClusterConfig
from loom.errors import (
    LoomError, LLMError, LLMRateLimitError, LLMAuthError, LLMStreamInterruptedError,
    ToolError, ToolTimeoutError, ToolResultTooLargeError,
    AuctionNoWinnerError, MitosisError, ApoptosisRejectedError,
    AgentAbortError, AgentMaxStepsError,
)
from loom.session import SessionContext, get_current_session, set_session, reset_session


class TestAgentConfig:
    def test_defaults(self):
        c = AgentConfig()
        assert c.max_steps == 10
        assert c.temperature == 0.7

    def test_custom(self):
        c = AgentConfig(max_steps=5, model="gpt-4")
        assert c.max_steps == 5
        assert c.model == "gpt-4"


class TestClusterConfig:
    def test_defaults(self):
        c = ClusterConfig()
        assert c.min_nodes == 1
        assert c.max_depth == 2
        assert c.mitosis_threshold == 0.6

    def test_bid_weights(self):
        c = ClusterConfig()
        assert abs(sum(c.bid_weights.values()) - 1.0) < 0.01


class TestErrors:
    def test_loom_error(self):
        e = LoomError("TEST", "test message")
        assert e.code == "TEST"
        assert str(e) == "test message"

    def test_loom_error_wrap(self):
        orig = ValueError("bad")
        wrapped = LoomError.wrap(orig)
        assert wrapped.cause is orig

    def test_loom_error_wrap_passthrough(self):
        e = LoomError("X", "x")
        assert LoomError.wrap(e) is e

    def test_llm_rate_limit(self):
        e = LLMRateLimitError("openai", retry_after_ms=1000)
        assert e.status_code == 429
        assert e.retry_after_ms == 1000

    def test_llm_auth(self):
        e = LLMAuthError("anthropic")
        assert e.status_code == 401

    def test_llm_stream_interrupted(self):
        e = LLMStreamInterruptedError("openai", partial_content="partial")
        assert e.partial_content == "partial"

    def test_tool_timeout(self):
        e = ToolTimeoutError("search", 5000)
        assert e.timeout_ms == 5000
        assert e.tool_name == "search"

    def test_tool_result_too_large(self):
        e = ToolResultTooLargeError("fetch", 200000, 100000)
        assert e.size_bytes == 200000

    def test_auction_no_winner(self):
        e = AuctionNoWinnerError("task-1")
        assert e.task_id == "task-1"

    def test_mitosis_error(self):
        e = MitosisError("node-1", "max depth reached")
        assert e.parent_id == "node-1"

    def test_apoptosis_rejected(self):
        e = ApoptosisRejectedError("node-1", "busy")
        assert e.node_id == "node-1"

    def test_agent_abort(self):
        e = AgentAbortError()
        assert e.code == "AGENT_ABORT"

    def test_agent_max_steps(self):
        e = AgentMaxStepsError(10, "partial")
        assert e.steps == 10
        assert e.partial_content == "partial"

    def test_error_hierarchy(self):
        assert issubclass(LLMError, LoomError)
        assert issubclass(LLMRateLimitError, LLMError)
        assert issubclass(ToolError, LoomError)
        assert issubclass(ToolTimeoutError, ToolError)
