"""ClusterProvider — injects cluster state into agent context."""

from __future__ import annotations

from ..types import ContextFragment, ContextSource


class ClusterProvider:
    source = ContextSource.CLUSTER

    def __init__(self, cluster, agent_id: str) -> None:
        self._cluster = cluster
        self._agent_id = agent_id

    async def provide(self, _query: str, budget: int) -> list[ContextFragment]:
        frags: list[ContextFragment] = []
        node = self._cluster.get_node(self._agent_id)
        if not node:
            return frags

        caps = ", ".join(
            f"{d}: {s:.2f}"
            for d, s in sorted(node.capabilities.scores.items(), key=lambda x: -x[1])
        )
        cap_text = (
            f"My capabilities: {caps}. Success rate: {node.capabilities.success_rate * 100:.0f}%"
        )
        frags.append(
            ContextFragment(
                source=ContextSource.CLUSTER,
                content=cap_text,
                tokens=len(cap_text) // 4,
                relevance=0.8,
            )
        )

        peers = [n for n in self._cluster.nodes if n.id != self._agent_id]
        if peers:
            peer_text = f"Cluster: {len(peers)} peers. " + ", ".join(
                f"{p.id}({p.status})" for p in peers[:5]
            )
            frags.append(
                ContextFragment(
                    source=ContextSource.CLUSTER,
                    content=peer_text,
                    tokens=len(peer_text) // 4,
                    relevance=0.5,
                )
            )

        total = 0
        return [f for f in frags if (total := total + f.tokens) <= budget]
