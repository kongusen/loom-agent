"""Context manager - C: Agent's perception interface

核心主张：C 是 Agent 的唯一感知界面。管理 C 就是管理 Agent 的认知。
"""

from ..utils import count_messages_tokens
from .compression import ContextCompressor
from .dashboard import DashboardManager
from .partitions import ContextPartitions
from .renewal import ContextRenewer


class ContextManager:
    """Manage context with five partitions and compression."""

    def __init__(self, max_tokens: int = 200000):
        self.max_tokens = max_tokens
        self.partitions = ContextPartitions()
        self.dashboard = DashboardManager(self.partitions.working)
        self.compressor = ContextCompressor()
        self.renewer = ContextRenewer()
        self.current_goal = ""

    @property
    def rho(self) -> float:
        """Calculate context pressure ρ = token_count / max_tokens."""
        token_count = count_messages_tokens(self.partitions.get_all_messages())
        return token_count / self.max_tokens

    def should_renew(self) -> bool:
        """Check if context needs renewal (ρ >= 1.0)."""
        return self.rho >= 1.0

    def renew(self):
        """Renew context while keeping dashboard bound to live working state."""
        self.partitions = self.renewer.renew(self.partitions, self.current_goal)
        self.dashboard.bind(self.partitions.working)
        self.dashboard.update_rho(self.rho)

    def should_compress(self) -> str | None:
        """Check if compression is needed."""
        return self.compressor.should_compress(self.rho)

    def compress(self, strategy: str):
        """Execute compression strategy on history only."""
        if strategy == 'snip':
            self.partitions.history = self.compressor.snip_compact(self.partitions.history)
        elif strategy == 'micro':
            self.partitions.history = self.compressor.micro_compact(self.partitions.history)
        elif strategy == 'collapse':
            self.partitions.history = self.compressor.context_collapse(
                self.partitions.history,
                self.current_goal,
            )
        elif strategy == 'auto':
            self.partitions.history = self.compressor.auto_compact(
                self.partitions.history,
                self.current_goal,
            )

        self.dashboard.update_rho(self.rho)
