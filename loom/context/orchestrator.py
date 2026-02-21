"""Context orchestrator — gather fragments from providers within token budget."""

from __future__ import annotations

import asyncio
from ..types import ContextFragment, ContextProvider, ContextSource, TokenBudget, BudgetRatios


class ContextOrchestrator:
    """Adaptive budget allocation via EMA-scored source relevance."""

    def __init__(
        self,
        context_window: int = 128_000,
        output_reserve_ratio: float = 0.25,
        ratios: BudgetRatios | None = None,
        adaptive_alpha: float = 0.3,
    ) -> None:
        self._providers: list[ContextProvider] = []
        self._scores: dict[ContextSource, float] = {}
        self._alpha = adaptive_alpha
        self._context_window = context_window
        self._output_reserve_ratio = output_reserve_ratio
        if ratios:
            self._scores.update(ratios)

    def register(self, provider: ContextProvider) -> None:
        self._providers.append(provider)
        if provider.source not in self._scores:
            self._scores[provider.source] = 1.0

    async def gather(self, query: str, budget: int) -> list[ContextFragment]:
        if not self._providers:
            return []

        # Proportional budget allocation from adaptive scores
        total_score = sum(self._scores.get(p.source, 1.0) for p in self._providers) or 1
        coros = [
            p.provide(query, int(budget * self._scores.get(p.source, 1.0) / total_score))
            for p in self._providers
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)

        all_frags: list[ContextFragment] = []
        for r in results:
            if isinstance(r, list):
                all_frags.extend(r)

        all_frags.sort(key=lambda f: f.relevance, reverse=True)
        selected, used = [], 0
        for f in all_frags:
            if used + f.tokens > budget:
                continue
            selected.append(f)
            used += f.tokens

        self._update_scores(selected)
        return selected

    def compute_budget(self, system_prompt: str | None = None) -> TokenBudget:
        sys_tokens = len((system_prompt or "").split()) * 2  # rough estimate
        reserved = int(self._context_window * self._output_reserve_ratio)
        available = self._context_window - reserved - sys_tokens
        return TokenBudget(
            total=self._context_window,
            reserved_output=reserved,
            system_prompt_tokens=sys_tokens,
            available=max(available, 0),
        )

    @property
    def ratios(self) -> dict[str, float]:
        total = sum(self._scores.values()) or 1
        return {s.value if hasattr(s, 'value') else str(s): v / total for s, v in self._scores.items()}

    def _update_scores(self, selected: list[ContextFragment]) -> None:
        by_source: dict[ContextSource, list[float]] = {}
        for f in selected:
            by_source.setdefault(f.source, []).append(f.relevance)
        for source, old in self._scores.items():
            rels = by_source.get(source)
            avg = sum(rels) / len(rels) if rels else 0.0
            self._scores[source] = (1 - self._alpha) * old + self._alpha * avg
