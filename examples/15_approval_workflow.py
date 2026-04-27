"""15 - Approval Workflow.

End-to-end application-style demo for a staged approval flow.
Works with the public `Agent -> Session -> RunContext` API.
"""

import asyncio
import os

from loom import Agent, Model, RunContext, SessionConfig


def resolve_model():
    provider = os.getenv("LOOM_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "anthropic").lower()
    model_name = os.getenv("LOOM_MODEL_NAME")
    if provider == "openai":
        return Model.openai(
            model_name or os.getenv("OPENAI_MODEL") or "gpt-4.1",
            api_base=os.getenv("OPENAI_BASE_URL"),
            api_key_env="OPENAI_API_KEY",
        )
    if provider == "gemini":
        return Model.gemini(model_name or "gemini-2.5-pro")
    if provider == "qwen":
        return Model.qwen(model_name or "qwen-max")
    if provider == "ollama":
        return Model.ollama(model_name or "llama3", api_base=os.getenv("OLLAMA_BASE_URL"))
    return Model.anthropic(model_name or "claude-sonnet-4")


async def main():
    agent = Agent(
        model=resolve_model(),
        instructions=(
            "Prepare operational changes, summarize risk, "
            "and treat approval as an explicit runtime input."
        ),
    )

    session = agent.session(
        SessionConfig(
            id="approval-demo",
            metadata={"workflow": "production-deploy"},
        )
    )

    draft = await session.run("Prepare a production deployment plan for version 2.3.0")
    review = await session.run(
        "Summarize the risk and identify the missing approval step.",
        context=RunContext(
            inputs={
                "draft_plan": draft.output,
                "target_environment": "production",
            }
        ),
    )
    approved = await session.run(
        "Produce the final approved action summary.",
        context=RunContext(
            inputs={
                "draft_plan": draft.output,
                "review_summary": review.output,
                "approval_state": "approved",
                "approved_by": "release-owner",
            }
        ),
    )

    print("=== Approval Workflow ===")
    print(f"Draft:    {draft.output}")
    print(f"Review:   {review.output}")
    print(f"Approved: {approved.output}")
    print(f"Runs:     {len(session.list_runs())}")


asyncio.run(main())
