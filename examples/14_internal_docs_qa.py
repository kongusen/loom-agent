"""14 - Internal Docs QA.

End-to-end application-style demo for grounded internal documentation answers.
Works with the public `KnowledgeQuery -> KnowledgeBundle -> RunContext` flow.
"""

import asyncio
import os

from loom import (
    AgentConfig,
    KnowledgeDocument,
    KnowledgeQuery,
    KnowledgeSource,
    ModelRef,
    RunContext,
    create_agent,
)


def resolve_model() -> ModelRef:
    provider = os.getenv("LOOM_PROVIDER", "openai" if os.getenv("OPENAI_API_KEY") else "anthropic").lower()
    model_name = os.getenv("LOOM_MODEL_NAME")
    if provider == "openai":
        return ModelRef.openai(
            model_name or os.getenv("OPENAI_MODEL") or "gpt-4.1",
            api_base=os.getenv("OPENAI_BASE_URL"),
            api_key_env="OPENAI_API_KEY",
        )
    if provider == "gemini":
        return ModelRef.gemini(model_name or "gemini-2.5-pro")
    if provider == "qwen":
        return ModelRef.qwen(model_name or "qwen-max")
    if provider == "ollama":
        return ModelRef.ollama(model_name or "llama3", api_base=os.getenv("OLLAMA_BASE_URL"))
    return ModelRef.anthropic(model_name or "claude-sonnet-4")


async def main():
    agent = create_agent(
        AgentConfig(
            model=resolve_model(),
            instructions="Answer internal documentation questions from the supplied evidence only.",
            knowledge=[
                KnowledgeSource.inline(
                    "handbook",
                    [
                        KnowledgeDocument(
                            title="Deploy Policy",
                            content="Production deploys require approval from the release owner.",
                        ),
                        KnowledgeDocument(
                            title="Incident Policy",
                            content="Primary on-call engineers must acknowledge incidents within 10 minutes.",
                        ),
                    ],
                    description="Internal company handbook",
                )
            ],
        )
    )

    question = "Who can approve a production deploy?"
    knowledge = agent.resolve_knowledge(
        KnowledgeQuery(
            text=question,
            goal="Answer deploy approval question",
            top_k=2,
        )
    )

    result = await agent.run(
        "Answer the internal documentation question.",
        context=RunContext(
            inputs={"user_question": question},
            knowledge=knowledge,
        ),
    )

    print("=== Internal Docs QA ===")
    print(f"Question:  {question}")
    print(f"Evidence:  {len(knowledge.items)} items / {len(knowledge.citations)} citations")
    print(f"Answer:    {result.output}")


asyncio.run(main())
