"""
Project State Object (PSO) Implementation.
"""

from typing import Any, Dict, List
from loom.protocol.memory_operations import ProjectStateObject

class SimplePSO(ProjectStateObject):
    def __init__(self):
        self.state: Dict[str, Any] = {
            "goals": [],
            "completed_tasks": [],
            "current_context": "",
            "variables": {}
        }
        
    async def update(self, events: List[Dict[str, Any]]) -> None:
        """
        Update state based on heuristic interpretation of events.
        """
        for event in events:
            role = event.get("role")
            content = event.get("content", "")
            
            if role == "user" and ("task" in content.lower() or "goal" in content.lower()):
                self.state["goals"].append(content)
            elif role == "tool" and "result" in str(content).lower():
                self.state["completed_tasks"].append(str(content)[:100])
                
    async def snapshot(self) -> Dict[str, Any]:
        return self.state.copy()

    def to_markdown(self) -> str:
        md = "## Project State\n"
        md += "### Goals\n"
        for g in self.state["goals"]:
            md += f"- [ ] {g}\n"
        md += "\n### Completed\n"
        for t in self.state["completed_tasks"]:
            md += f"- [x] {t}\n"
        return md
