"""WorkingState - 预算化的灵活工作状态"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class WorkingState:
    """工作状态 - 预算化的灵活结构"""

    budget: int = 2000  # token 预算

    # 推荐 schema（非强制）
    goal: Optional[str] = None
    plan: Optional[str] = None
    progress: Optional[dict[str, Any]] = None
    blockers: Optional[list[str]] = None
    next_action: Optional[str] = None

    # 自由内容（计入预算）
    overflow: str = ""

    def to_text(self, tokenizer) -> str:
        """转换为文本（受预算限制）"""
        parts = []

        if self.goal:
            parts.append(f"<goal>{self.goal}</goal>")

        if self.plan:
            parts.append(f"<plan>{self.plan}</plan>")

        if self.progress:
            parts.append(f"<progress>{self.progress}</progress>")

        if self.blockers:
            parts.append(f"<blockers>{', '.join(self.blockers)}</blockers>")

        if self.next_action:
            parts.append(f"<next_action>{self.next_action}</next_action>")

        if self.overflow:
            parts.append(f"<overflow>{self.overflow}</overflow>")

        text = "\n".join(parts)

        # 截断到预算
        return tokenizer.truncate(text, self.budget)

    @classmethod
    def from_text(cls, text: str) -> WorkingState:
        """从文本解析（尽力而为）"""
        import re

        state = cls()

        # 尝试提取结构化字段
        if match := re.search(r"<goal>(.*?)</goal>", text, re.DOTALL):
            state.goal = match.group(1).strip()

        if match := re.search(r"<plan>(.*?)</plan>", text, re.DOTALL):
            state.plan = match.group(1).strip()

        if match := re.search(r"<next_action>(.*?)</next_action>", text, re.DOTALL):
            state.next_action = match.group(1).strip()

        # 剩余内容放入 overflow
        structured = re.sub(r"<\w+>.*?</\w+>", "", text, flags=re.DOTALL)
        state.overflow = structured.strip()

        return state
