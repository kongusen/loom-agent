from typing import Any, Dict, Type, Optional, Callable, get_type_hints, Union
from abc import ABC, abstractmethod
import inspect
from pydantic import BaseModel, create_model
from loom.core.runnable import Runnable, RunnableConfig

class BaseTool(Runnable[Dict[str, Any], str]):
    """
    Base class for Tools.

    Philosophy:
    - Tool is also a Runnable
    - Input: Dict (tool arguments)
    - Output: str (tool result)
    """

    name: str
    description: str
    args_schema: Type[BaseModel]  # Pydantic schema

    # Orchestration hints
    is_read_only: bool = False
    category: str = "general"
    requires_confirmation: bool = False

    @abstractmethod
    async def invoke(
        self,
        input: Dict[str, Any],
        config: Optional[RunnableConfig] = None,
        **kwargs
    ) -> str:
        """Execute the tool."""
        ...

    def get_openai_schema(self) -> Dict[str, Any]:
        """Generate OpenAI Function Calling format schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema()
            }
        }


class FunctionTool(BaseTool):
    """
    Wraps a plain Python function as a Tool.

    Example:
        def search_web(query: str, max_results: int = 10) -> str:
            '''Search the web'''
            return f"Results for {query}"

        tool = FunctionTool.from_function(search_web)
    """

    def __init__(self, func: Callable, name: str = None, description: str = None):
        self.func = func
        self.name = name or func.__name__
        self.description = description or (func.__doc__ or "").strip()

        # Automatically generate Pydantic schema
        self.args_schema = self._create_schema_from_function(func)

    @staticmethod
    def _create_schema_from_function(func: Callable) -> Type[BaseModel]:
        """Generate schema via inspection."""
        sig = inspect.signature(func)
        hints = get_type_hints(func)

        fields = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            
            param_type = hints.get(param_name, Any)
            default = param.default if param.default != inspect.Parameter.empty else ...
            fields[param_name] = (param_type, default)

        return create_model(f"{func.__name__}_Schema", **fields)

    async def invoke(self, input: Dict[str, Any], config=None, **kwargs) -> str:
        # Validate arguments
        validated = self.args_schema(**input)

        # Execute function
        result = self.func(**validated.model_dump())

        # Async support
        if inspect.iscoroutine(result):
            result = await result

        return str(result)

    @classmethod
    def from_function(cls, func: Callable) -> "FunctionTool":
        """Factory method."""
        return cls(func)
