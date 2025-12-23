"""
State Patch Protocol (JSON Patch / CRDT-like)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict

class PatchOperation(str, Enum):
    """JSON Patch Operations (RFC 6902)"""
    ADD = "add"
    REMOVE = "remove"
    REPLACE = "replace"
    MOVE = "move"
    COPY = "copy"
    TEST = "test"

class StatePatch(BaseModel):
    """
    Represents a single operation to modify the state.
    """
    op: PatchOperation
    path: str # JSON Pointer, e.g., "/memory/short_term/0"
    value: Optional[Any] = None
    from_path: Optional[str] = Field(None, alias="from") # For move/copy
    
    model_config = ConfigDict(populate_by_name=True)

def apply_patch(state: Union[Dict, List], patch: StatePatch) -> None:
    """
    Apply a single patch to the state (In-Place).
    Simplified implementation supporting ADD, REPLACE, REMOVE.
    """
    
    # Parse path
    tokens = [t for t in patch.path.split('/') if t]
    if not tokens:
        return # Root modification not supported directly on container usually
        
    target = state
    parent = None
    key = None
    
    # Navigate to target
    for i, token in enumerate(tokens):
        is_last = (i == len(tokens) - 1)
        
        # Handle list index
        if isinstance(target, list):
            try:
                idx = int(token)
                key = idx
            except ValueError:
                if token == "-":
                    key = len(target) # Append
                else:
                    raise ValueError(f"Invalid list index: {token}")
        else:
            key = token
            
        if not is_last:
            if isinstance(target, dict):
                target = target.setdefault(key, {})
            elif isinstance(target, list):
                if key < len(target):
                    target = target[key]
                else:
                    raise IndexError(f"List index out of range: {key}")
            parent = target
            
    # Apply operation
    if patch.op == PatchOperation.ADD:
        if isinstance(target, list):
            if isinstance(key, int):
                target.insert(key, patch.value)
        elif isinstance(target, dict):
            target[key] = patch.value
            
    elif patch.op == PatchOperation.REPLACE:
        if isinstance(target, list):
             target[key] = patch.value
        elif isinstance(target, dict):
             target[key] = patch.value
             
    elif patch.op == PatchOperation.REMOVE:
        if isinstance(target, list):
             target.pop(key)
        elif isinstance(target, dict):
             target.pop(key, None)
             
    # TODO: Implement MOVE, COPY, TEST
