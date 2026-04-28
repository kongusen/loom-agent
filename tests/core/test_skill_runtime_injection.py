"""Runtime injection coverage for skill capabilities."""

from __future__ import annotations

import pytest

from loom import (
    Agent,
    Capability,
    Model,
    Runtime,
    RuntimeTask,
    SkillInjection,
    SkillInjectionPolicy,
)
from loom.providers.base import CompletionRequest, CompletionResponse, LLMProvider


class CapturingProvider(LLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.requests: list[CompletionRequest] = []

    async def _complete_request(self, request: CompletionRequest) -> CompletionResponse:
        self.requests.append(request)
        return CompletionResponse(content="ok")


@pytest.mark.asyncio
async def test_matching_skill_capability_is_injected_into_runtime_context() -> None:
    provider = CapturingProvider()
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.skill(
                "repo-review",
                description="Review repository changes.",
                content="# Review\nPrefer small diffs and test evidence.",
                when_to_use="review,diff",
            ),
            Capability.skill(
                "deploy",
                description="Deploy production changes.",
                content="# Deploy\nUse release controls.",
                when_to_use="deploy,release",
            ),
        ],
    )
    agent._provider = provider
    agent._provider_resolved = True

    result = await agent.run("Review this diff")

    contents = [str(message["content"]) for message in provider.requests[0].messages]
    skill_block = "\n".join(contents)
    assert result.output == "ok"
    assert "## Available Skills/Tools" in skill_block
    assert "Skill: repo-review" in skill_block
    assert "Prefer small diffs and test evidence." in skill_block
    assert "Use release controls." not in skill_block


@pytest.mark.asyncio
async def test_runtime_task_metadata_can_explicitly_select_skill() -> None:
    provider = CapturingProvider()
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.skill(
                "repo-review",
                content="# Review\nUse explicit review guidance.",
                when_to_use="review",
            )
        ],
    )
    agent._provider = provider
    agent._provider_resolved = True

    await agent.run(
        RuntimeTask(
            goal="Summarize the repository",
            metadata={"skills": ["repo-review"]},
        )
    )

    contents = [str(message["content"]) for message in provider.requests[0].messages]
    assert any("Use explicit review guidance." in content for content in contents)


@pytest.mark.asyncio
async def test_skill_injection_policy_limits_skill_context_budget() -> None:
    provider = CapturingProvider()
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.skill(
                "large-skill",
                content="# Large\n" + ("token " * 200),
                when_to_use="large",
            )
        ],
        runtime=Runtime.sdk(
            skill_injection=SkillInjection.matching(max_tokens=12),
        ),
    )
    agent._provider = provider
    agent._provider_resolved = True

    await agent.run("Use the large skill")

    contents = [str(message["content"]) for message in provider.requests[0].messages]
    assert any("Skill: large-skill" in content for content in contents)
    assert not any(("token " * 50).strip() in content for content in contents)


@pytest.mark.asyncio
async def test_unmatched_skill_does_not_pollute_later_runs_in_same_session() -> None:
    provider = CapturingProvider()
    agent = Agent(
        model=Model.openai("gpt-test"),
        capabilities=[
            Capability.skill(
                "repo-review",
                content="# Review\nOnly use this for reviews.",
                when_to_use="review",
            )
        ],
    )
    agent._provider = provider
    agent._provider_resolved = True

    session = agent.session()
    await session.run("Review this diff")
    await session.run("Write a short project summary")

    first_contents = [str(message["content"]) for message in provider.requests[0].messages]
    second_contents = [str(message["content"]) for message in provider.requests[1].messages]
    assert any("Only use this for reviews." in content for content in first_contents)
    assert not any("Only use this for reviews." in content for content in second_contents)


def test_skill_injection_policy_is_skill_injection_alias() -> None:
    assert SkillInjectionPolicy is SkillInjection
