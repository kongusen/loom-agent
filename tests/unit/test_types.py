"""Unit tests for types, config, errors, session."""

from loom.types import (
    AgentNode,
    AssistantMessage,
    Bid,
    CapabilityProfile,
    CompletionParams,
    CompletionResult,
    ContextFragment,
    DoneEvent,
    ErrorEvent,
    RetrieverOptions,
    RewardRecord,
    SkillActivation,
    SkillTrigger,
    StepEndEvent,
    StepStartEvent,
    StreamChunk,
    SubTask,
    SystemMessage,
    TaskAd,
    TextDeltaEvent,
    TokenUsage,
    ToolCall,
    ToolContext,
    ToolMessage,
    ToolResult,
    UserMessage,
)


class TestMessages:
    def test_system_message(self):
        m = SystemMessage(content="hello")
        assert m.role == "system"
        assert m.content == "hello"

    def test_user_message(self):
        m = UserMessage(content="hi")
        assert m.role == "user"

    def test_assistant_message_with_tool_calls(self):
        tc = ToolCall(id="tc1", name="search", arguments='{"q":"x"}')
        m = AssistantMessage(content="", tool_calls=[tc])
        assert len(m.tool_calls) == 1
        assert m.tool_calls[0].name == "search"

    def test_tool_message(self):
        m = ToolMessage(content="result", tool_call_id="tc1")
        assert m.role == "tool"


class TestTokenUsage:
    def test_defaults(self):
        u = TokenUsage()
        assert u.total_tokens == 0

    def test_values(self):
        u = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        assert u.total_tokens == 30


class TestCompletionTypes:
    def test_completion_params(self):
        p = CompletionParams(messages=[UserMessage(content="hi")])
        assert p.max_tokens == 4096
        assert p.temperature == 0.7

    def test_completion_result(self):
        r = CompletionResult(content="ok")
        assert r.finish_reason == "stop"
        assert r.usage.total_tokens == 0

    def test_stream_chunk(self):
        c = StreamChunk(text="hello")
        assert c.text == "hello"
        assert c.finish_reason is None


class TestEvents:
    def test_text_delta(self):
        e = TextDeltaEvent(text="hi")
        assert e.type == "text_delta"

    def test_done_event(self):
        e = DoneEvent(content="done", steps=3)
        assert e.usage.total_tokens == 0

    def test_error_event(self):
        e = ErrorEvent(error="fail", recoverable=True)
        assert e.recoverable is True

    def test_step_events(self):
        s = StepStartEvent(step=1)
        assert s.type == "step_start"
        e = StepEndEvent(step=1, reason="complete")
        assert e.reason == "complete"


class TestClusterTypes:
    def test_agent_node_defaults(self):
        n = AgentNode()
        assert n.status == "idle"
        assert n.depth == 0
        assert len(n.id) == 8

    def test_capability_profile(self):
        c = CapabilityProfile(scores={"code": 0.9}, tools=["search"])
        assert c.scores["code"] == 0.9

    def test_task_ad(self):
        t = TaskAd(domain="code", description="test")
        assert t.estimated_complexity == 0.5

    def test_bid(self):
        b = Bid(agent_id="a1", task_id="t1", score=0.8)
        assert b.score == 0.8

    def test_subtask(self):
        s = SubTask(description="sub", domain="code")
        assert s.estimated_complexity == 0.3

    def test_reward_record(self):
        r = RewardRecord(task_id="t1", reward=0.7, domain="code")
        assert r.reward == 0.7


class TestToolTypes:
    def test_tool_context(self):
        ctx = ToolContext(agent_id="a1", session_id="s1", tenant_id="t1")
        assert ctx.signal is None

    def test_tool_result(self):
        r = ToolResult(tool_call_id="tc1", tool_name="search", success=True, result="found")
        assert r.success is True


class TestContextTypes:
    def test_context_fragment(self):
        f = ContextFragment(source="memory", content="data", tokens=10, relevance=0.8)
        assert f.relevance == 0.8

    def test_retriever_options(self):
        o = RetrieverOptions()
        assert o.limit == 10


class TestSkillTypes:
    def test_skill_trigger_defaults(self):
        t = SkillTrigger()
        assert t.type == "keyword"
        assert t.threshold == 0.7
        assert t.evaluator is None

    def test_skill_trigger_custom(self):
        t = SkillTrigger(type="custom", evaluator=lambda x: 0.5)
        assert t.evaluator is not None

    def test_skill_activation(self):
        a = SkillActivation(score=0.9, reason="test")
        assert a.score == 0.9
