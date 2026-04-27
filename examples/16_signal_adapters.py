"""16 - Runtime signal adapters.

External producers such as gateways, cron jobs, heartbeat monitors, and app
callbacks should normalize their events into RuntimeSignal. The runtime does
not distinguish those producers; AttentionPolicy decides what to do with each
signal.
"""

import asyncio

from loom import Agent, Model, SessionConfig, SignalAdapter


async def main():
    agent = Agent(
        model=Model.openai("gpt-5.1"),
        instructions="Handle pending runtime signals concisely.",
    )
    session = agent.session(SessionConfig(id="ops"))

    gateway = SignalAdapter(
        source="gateway:slack",
        type="message",
        summary=lambda event: event["text"],
        payload=lambda event: {"channel": event["channel"]},
        dedupe_key=lambda event: event["event_id"],
    )
    cron = SignalAdapter(
        source="cron",
        type="job",
        summary=lambda event: f"Run scheduled job {event['job_id']}",
        payload=lambda event: {"job_id": event["job_id"]},
    )

    gateway_decision = await session.receive(
        {
            "event_id": "evt-support-1",
            "text": "Customer asks for deployment status",
            "channel": "support",
        },
        adapter=gateway,
    )
    cron_decision = await session.receive(
        {"job_id": "deployment-health"},
        adapter=cron,
        urgency="high",
    )

    result = await session.run("Handle pending runtime signals")

    print(f"Gateway signal: {gateway_decision.action}")
    print(f"Cron signal:    {cron_decision.action}")
    print(f"Run state:      {result.state.value}")
    print(f"Output:         {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
