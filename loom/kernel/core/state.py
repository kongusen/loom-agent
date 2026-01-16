"""
State Management (Kernel)
"""

import copy
from typing import Any

from loom.protocol.cloudevents import CloudEvent
from loom.protocol.patch import StatePatch
from loom.protocol.patch import apply_patch as apply_dict_patch


class StateStore:
    """
    Manages the application state tree.
    Updates state by applying 'state.patch' events.
    """

    def __init__(self):
        self._root: dict[str, Any] = {}

    def apply_event(self, event: CloudEvent) -> None:
        """
        Update state if event contains patches.
        Expected event.type = "state.patch"
        Expected event.data = {"patches": [...]}
        """
        if event.type != "state.patch":
            return

        if event.data is None:
            return

        patches_data = event.data.get("patches", [])
        if not patches_data:
            return

        for p_data in patches_data:
            try:
                patch = StatePatch(**p_data)
                # Apply strictly to root
                apply_dict_patch(self._root, patch)
            except Exception as e:
                # In a real system, we might want to dead-letter queue this
                print(f"Failed to apply patch: {e}")

    def get_snapshot(self, path: str = "/") -> Any:
        """
        Get a deep copy of the state at a specific path.
        """
        if path == "/":
            return copy.deepcopy(self._root)

        tokens = [t for t in path.split('/') if t]
        current: Any = self._root

        for token in tokens:
            if current is None:
                return None

            if isinstance(current, dict):
                current = current.get(token)
            elif isinstance(current, list):
                try:
                    idx = int(token)
                    current = current[idx] if 0 <= idx < len(current) else None # type: ignore
                except ValueError:
                    current = None

            if current is None:
                return None

        return copy.deepcopy(current)

    def clear(self):
        self._root = {}
