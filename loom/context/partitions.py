"""Context partitions - C = C_system ⊕ C_memory ⊕ C_skill ⊕ C_history ⊕ C_working

保护优先级：C_system > C_working > C_memory > C_skill > C_history
"""

from dataclasses import dataclass, field

from ..types import Dashboard, Message


@dataclass
class ContextPartitions:
    """Five-partition context structure

    C_system: Ψ注入，永不压缩，只读
    C_working: Dashboard仪表盘，永不压缩，LLM一等公民
    C_memory: AGENTS.md等，间接可写
    C_skill: 工具声明，动态换入/换出
    C_history: 执行历史，可压缩，优先级最低
    """
    system: list[Message] = field(default_factory=list)
    working: Dashboard = field(default_factory=Dashboard)
    memory: list[Message] = field(default_factory=list)
    skill: list[str] = field(default_factory=list)
    history: list[Message] = field(default_factory=list)

    def get_all_messages(self) -> list[Message]:
        """Get all messages for LLM (按优先级排序)

        Priority order: C_system > C_working > C_memory > C_skill > C_history
        """
        messages = []

        # 1. C_system: 永不压缩，最高优先级
        messages.extend(self.system)

        # 2. C_working: Dashboard 状态 - LLM 一等公民
        dashboard_msg = self._format_dashboard()
        if dashboard_msg:
            messages.append(dashboard_msg)

        # 3. C_memory: 长期记忆
        messages.extend(self.memory)

        # 4. C_skill: 当前激活的技能/工具
        skill_msg = self._format_skills()
        if skill_msg:
            messages.append(skill_msg)

        # 5. C_history: 执行历史（可压缩）
        messages.extend(self.history)

        return messages

    def _format_dashboard(self) -> Message | None:
        """Format Dashboard into a system message for LLM"""
        if not self.working:
            return None

        sections = []

        # 核心指标
        sections.append("## Dashboard")
        sections.append(f"- Context Pressure (ρ): {self.working.rho:.2f}")
        sections.append(f"- Token Budget: {self.working.token_budget}")
        sections.append(f"- Goal Progress: {self.working.goal_progress}")
        sections.append(f"- Error Count: {self.working.error_count}")
        sections.append(f"- Depth: {self.working.depth}")

        # 中断请求
        if self.working.interrupt_requested:
            sections.append("\n⚠️ **INTERRUPT REQUESTED**")

        # Plan
        if self.working.plan:
            sections.append("\n## Current Plan")
            for i, step in enumerate(self.working.plan, 1):
                sections.append(f"{i}. {step}")

        # Event Surface
        if self.working.event_surface.pending_events:
            sections.append("\n## Pending Events")
            for event in self.working.event_surface.pending_events:
                summary = event.get("summary", "Unknown event")
                urgency = event.get("urgency", "normal")
                sections.append(f"- [{urgency}] {summary}")

        if self.working.event_surface.active_risks:
            sections.append("\n## Active Risks")
            for risk in self.working.event_surface.active_risks:
                summary = risk.get("summary", "Unknown risk")
                urgency = risk.get("urgency", "unknown")
                sections.append(f"- [{urgency}] {summary}")

        # Knowledge Surface
        if self.working.knowledge_surface.active_questions:
            sections.append("\n## Active Questions")
            for question in self.working.knowledge_surface.active_questions:
                sections.append(f"- {question}")

        if self.working.knowledge_surface.citations:
            sections.append("\n## Knowledge Citations")
            for citation in self.working.knowledge_surface.citations[:5]:  # 最多显示5个
                sections.append(f"- {citation}")

        # Scratchpad
        if self.working.scratchpad:
            sections.append("\n## Scratchpad")
            sections.append(self.working.scratchpad)

        content = "\n".join(sections)
        return Message(role="system", content=content)

    def _format_skills(self) -> Message | None:
        """Format skills into a system message for LLM"""
        if not self.skill:
            return None

        sections = []
        sections.append("## Available Skills/Tools")
        sections.append("\nYou have access to the following capabilities:")

        for skill in self.skill:
            sections.append(f"\n{skill}")

        content = "\n".join(sections)
        return Message(role="system", content=content)

    def get_compressible_messages(self) -> list[Message]:
        """Get compressible messages (只有 history)"""
        return self.history
