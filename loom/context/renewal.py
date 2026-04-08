"""Context renewal - 上下文磁盘换页

触发条件：
1. 主动：LLM 判断需要 renew
2. 强制：ρ >= 1.0（物理约束）

Renewal 流程：
1. snapshot(C_working.dashboard) → M_f['working_state']
2. snapshot(C_working.plan) → M_f['plan_state']
3. snapshot(C_working.event_surface) → M_f['event_state']
4. snapshot(C_working.knowledge_surface) → M_f['knowledge_state']
5. compress(C_history) - score(h) = K(h) · rel(h,goal) · e^(-λ·age(h))
6. 重建 new_C = C_system ⊕ C_memory ⊕ C_skill ⊕ summary ⊕ working_state
7. resume(new_C, original_goal) - goal 永远随 renew 传递
"""

from copy import deepcopy

from ..memory import PersistentMemory
from ..types import Dashboard, EventSurface, KnowledgeSurface
from .compression import ContextCompressor
from .partitions import ContextPartitions


class ContextRenewer:
    """Handle context renewal when overflow"""

    def __init__(self):
        self.compressor = ContextCompressor()
        self.persistent = PersistentMemory()

    def renew(self, partitions: ContextPartitions, goal: str) -> ContextPartitions:
        """Renew context by compressing and rebuilding"""
        # 1. Snapshot dashboard
        working_state = {
            'rho': partitions.working.rho,
            'token_budget': partitions.working.token_budget,
            'goal_progress': partitions.working.goal_progress,
            'error_count': partitions.working.error_count,
            'depth': partitions.working.depth,
            'last_hb_ts': partitions.working.last_hb_ts,
            'interrupt_requested': partitions.working.interrupt_requested,
            'scratchpad': partitions.working.scratchpad,
        }
        self.persistent.save('working_state', working_state)

        # 2. Snapshot plan
        plan_state = {
            'plan': partitions.working.plan,
            'goal': goal
        }
        self.persistent.save('plan_state', plan_state)

        # 3. Snapshot event_surface (必须跨 renew 保留)
        event_state = {
            'pending_events': partitions.working.event_surface.pending_events,
            'active_risks': partitions.working.event_surface.active_risks,
            'recent_event_decisions': partitions.working.event_surface.recent_event_decisions[-5:],  # 只保留最近5条
        }
        self.persistent.save('event_state', event_state)

        # 4. Snapshot knowledge_surface
        knowledge_state = {
            'active_questions': partitions.working.knowledge_surface.active_questions,
            'evidence_packs': partitions.working.knowledge_surface.evidence_packs,
            'citations': partitions.working.knowledge_surface.citations,
        }
        self.persistent.save('knowledge_state', knowledge_state)

        # 5. Compress history
        compressed_history = self.compressor.auto_compact(
            partitions.history,
            goal
        )

        # 6. Rebuild new context
        new_partitions = ContextPartitions()
        new_partitions.system = list(partitions.system)  # 永不压缩
        new_partitions.working = self._restore_dashboard(
            working_state,
            plan_state,
            event_state,
            knowledge_state,
        )
        new_partitions.memory = list(partitions.memory)  # 保留
        new_partitions.skill = list(partitions.skill)  # 保留
        new_partitions.history = list(compressed_history)  # 压缩后

        return new_partitions

    def _restore_dashboard(
        self,
        working_state: dict,
        plan_state: dict,
        event_state: dict,
        knowledge_state: dict,
    ) -> Dashboard:
        """Rebuild dashboard from snapshots so renew returns a clean working state."""
        return Dashboard(
            rho=working_state.get('rho', 0.0),
            token_budget=working_state.get('token_budget', 0),
            goal_progress=working_state.get('goal_progress', ''),
            error_count=working_state.get('error_count', 0),
            depth=working_state.get('depth', 0),
            last_hb_ts=working_state.get('last_hb_ts', ''),
            interrupt_requested=working_state.get('interrupt_requested', False),
            plan=deepcopy(plan_state.get('plan', [])),
            event_surface=EventSurface(
                pending_events=deepcopy(event_state.get('pending_events', [])),
                active_risks=deepcopy(event_state.get('active_risks', [])),
                recent_event_decisions=deepcopy(event_state.get('recent_event_decisions', [])),
            ),
            knowledge_surface=KnowledgeSurface(
                active_questions=deepcopy(knowledge_state.get('active_questions', [])),
                evidence_packs=deepcopy(knowledge_state.get('evidence_packs', [])),
                citations=deepcopy(knowledge_state.get('citations', [])),
            ),
            scratchpad=working_state.get('scratchpad', ''),
        )
