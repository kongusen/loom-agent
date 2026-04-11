"""Evolution engine - Theorem 3"""

from .feedback import FeedbackLoop


class EvolutionEngine:
    """Self-evolution engine"""

    def __init__(self):
        self.strategies: list = []
        self.feedback_loop: FeedbackLoop = FeedbackLoop()

    def register_strategy(self, strategy):
        """Register evolution strategy"""
        self.strategies.append(strategy)

    def subscribe_to_engine(self, engine) -> None:
        """Wire evolution feedback to an AgentEngine's event bus.

        After calling this, ``tool_result`` events emitted by the engine are
        automatically collected into the internal FeedbackLoop so evolution
        strategies receive up-to-date execution data without any direct
        coupling between the runtime engine and evolution code.
        """
        self.feedback_loop.subscribe_to_engine(engine)

    def evolve(self, agent) -> None:
        """Execute all registered evolution strategies against the agent.

        If the agent does not expose a ``feedback_loop`` attribute the
        engine's own FeedbackLoop is injected automatically, so callers
        never need to wire feedback manually when using subscribe_to_engine().
        """
        if not hasattr(agent, "feedback_loop"):
            agent.feedback_loop = self.feedback_loop
        for strategy in self.strategies:
            strategy.apply(agent)
