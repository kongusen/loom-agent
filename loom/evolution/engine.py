"""Evolution engine - Theorem 3"""

from .dashboard import EvolutionDashboard, EvolutionMetrics
from .feedback import FeedbackLoop


class EvolutionEngine:
    """Self-evolution engine"""

    def __init__(self):
        self.strategies: list = []
        self.feedback_loop: FeedbackLoop = FeedbackLoop()
        self.dashboard: EvolutionDashboard = EvolutionDashboard()

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

        After applying strategies, records a snapshot of execution metrics
        to the EvolutionDashboard for trend analysis.
        """
        if not hasattr(agent, "feedback_loop"):
            agent.feedback_loop = self.feedback_loop
        for strategy in self.strategies:
            strategy.apply(agent)

        # Record execution metrics snapshot after each evolution cycle
        feedback = self.feedback_loop.get_feedback()
        if feedback:
            total = len(feedback)
            successes = sum(1 for f in feedback if f.get("success", False))
            self.dashboard.record(
                EvolutionMetrics(
                    success_rate=successes / total,
                    avg_cost=0.0,
                    skill_reuse_rate=0.0,
                    constraint_count=total,
                )
            )
