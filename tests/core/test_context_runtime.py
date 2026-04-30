"""Tests for runtime context coordination extraction."""

from loom.runtime.context_runtime import ContextRuntime


class _Working:
    def __init__(self) -> None:
        self.goal_progress = ""
        self.scratchpad = ""
        self.knowledge_surface = type("KS", (), {"evidence_packs": []})()


class _Partitions:
    def __init__(self) -> None:
        self.system = []
        self.memory = []
        self.skill = []
        self.history = []
        self.working = _Working()

    def get_all_messages(self):
        return list(self.system + self.memory + self.history)


class _Dashboard:
    def __init__(self) -> None:
        self.questions = []
        self.dashboard = type("D", (), {"knowledge_surface": type("KS", (), {"evidence_packs": []})()})()

    def add_question(self, q):
        self.questions.append(q)

    def add_evidence(self, evidence):
        self.dashboard.knowledge_surface.evidence_packs.append(evidence)


class _Ctx:
    def __init__(self) -> None:
        self.partitions = _Partitions()
        self.dashboard = _Dashboard()
        self._knowledge_sources = []


def test_context_runtime_initialize_context_populates_partitions() -> None:
    ctx = _Ctx()
    runtime = ContextRuntime(
        context_manager=ctx,
        ecosystem_manager=None,
        skill_injection_policy=None,
        emit=lambda *_a, **_k: None,
    )

    runtime.initialize_context("ship", "follow policy", {"repo": "loom"})

    assert str(ctx.partitions.system[0].content) == "follow policy"
    assert ctx.partitions.working.goal_progress == "Goal: ship"
    assert ctx.partitions.working.scratchpad == "ship"
    assert "repo: loom" in str(ctx.partitions.memory[0].content)


def test_context_runtime_build_messages_appends_goal_user_message() -> None:
    ctx = _Ctx()
    runtime = ContextRuntime(
        context_manager=ctx,
        ecosystem_manager=None,
        skill_injection_policy=None,
        emit=lambda *_a, **_k: None,
    )

    messages = runtime.build_messages("answer me")

    assert messages[-1].role == "user"
    assert str(messages[-1].content) == "answer me"
