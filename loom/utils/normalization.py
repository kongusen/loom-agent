"""
Data Normalization Utilities
Inspired by Claude Code's normalizeToSize algorithm.
"""

import json
import sys
from typing import Any


class DataNormalizer:
    """
    Intelligently truncates and normalizes data structures to fit within size limits.
    Handles circular references and framework-specific objects.
    """

    @staticmethod
    def normalize_to_size(
        obj: Any,
        max_depth: int = 3,
        max_bytes: int = 100_000,
        string_limit: int = 20_000
    ) -> Any:
        """
        Normalize an object to fit within a size limit by iteratively reducing depth.
        """
        current_depth = max_depth
        normalized = DataNormalizer._normalize(obj, current_depth, string_limit=string_limit)

        # Iteratively reduce depth if size is too large
        while DataNormalizer._estimate_size(normalized) > max_bytes and current_depth > 0:
            current_depth -= 1
            normalized = DataNormalizer._normalize(obj, current_depth)

        return normalized

    @staticmethod
    def _normalize(
        obj: Any,
        max_depth: int,
        current_depth: int = 0,
        visited: set[int] | None = None,
        string_limit: int = 20_000
    ) -> Any:
        if visited is None:
            visited = set()

        if obj is None:
            return None

        # Primitives
        if isinstance(obj, bool | int | float | str):
            # Truncate extremely long strings immediately
            if isinstance(obj, str) and len(obj) > string_limit:
                return obj[:string_limit] + "... [TRUNCATED]"
            return obj

        # Handle Circular References
        obj_id = id(obj)
        if obj_id in visited:
            return "[Circular]"

        visited.add(obj_id)

        # Depth Check
        if current_depth >= max_depth:
            if isinstance(obj, list | tuple):
                return f"[Array({len(obj)})]"
            if hasattr(obj, '__class__'):
                 return f"[{obj.__class__.__name__}]"
            return "[Object]"

        # specific framework handling (e.g. Pydantic)
        if hasattr(obj, "model_dump") and callable(obj.model_dump):
             try:
                 # Pydantic v2
                 data = obj.model_dump()
                 return DataNormalizer._normalize(data, max_depth, current_depth, visited.copy())
             except Exception:
                 pass

        if hasattr(obj, "dict") and callable(obj.dict):
             try:
                 # Pydantic v1
                 data = obj.dict()
                 return DataNormalizer._normalize(data, max_depth, current_depth, visited.copy())
             except Exception:
                 pass

        # Dictionaries
        if isinstance(obj, dict):
             dict_result = {}
             keys = list(obj.keys())
             # Limit keys just in case
             for key in keys[:50]:
                 dict_result[str(key)] = DataNormalizer._normalize(
                     obj[key], max_depth, current_depth + 1, visited.copy()
                 )
             if len(keys) > 50:
                 dict_result["..."] = f"{len(keys) - 50} more keys"
             return dict_result

        # Lists/Tuples
        if isinstance(obj, list | tuple):
             list_result = []
             # Limit array items
             for item in obj[:50]:
                 list_result.append(DataNormalizer._normalize(
                     item, max_depth, current_depth + 1, visited.copy()
                 ))
             if len(obj) > 50:
                 list_result.append(f"... {len(obj) - 50} more items")
             return list_result

        # General Objects (__dict__)
        if hasattr(obj, "__dict__"):
            return DataNormalizer._normalize(obj.__dict__, max_depth, current_depth, visited.copy())

        # Fallback for unknown objects
        return str(obj)

    @staticmethod
    def _estimate_size(obj: Any) -> int:
        """Rough estimation of JSON size."""
        try:
            return len(json.dumps(obj, default=lambda x: str(x)))
        except Exception:
            return sys.getsizeof(obj)
