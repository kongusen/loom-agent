"""模型池管理系统

框架级的多模型管理机制，允许用户：
1. 配置多个 LLM 模型
2. 为每个模型设置别名和能力
3. Agent 根据任务需求自动选择合适的模型
"""

from __future__ import annotations

from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from loom.interfaces.llm import BaseLLM
from .config import LLMCapabilities


@dataclass
class ModelEntry:
    name: str
    llm: BaseLLM
    capabilities: LLMCapabilities
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ModelPool:
    def __init__(self, default_model: Optional[str] = None):
        self._models: Dict[str, ModelEntry] = {}
        self._default_model = default_model

    def add(
        self,
        name: str,
        llm: BaseLLM,
        capabilities: Optional[LLMCapabilities] = None,
        **metadata
    ) -> None:
        if capabilities is None:
            if hasattr(llm, 'capabilities'):
                capabilities = llm.capabilities  # type: ignore[attr-defined]
            else:
                capabilities = LLMCapabilities()

        entry = ModelEntry(
            name=name,
            llm=llm,
            capabilities=capabilities,
            metadata=metadata
        )

        self._models[name] = entry
        if len(self._models) == 1 and self._default_model is None:
            self._default_model = name

    def get(self, name: str) -> Optional[BaseLLM]:
        entry = self._models.get(name)
        return entry.llm if entry else None

    def get_default(self) -> Optional[BaseLLM]:
        if self._default_model:
            return self.get(self._default_model)
        return None

    def set_default(self, name: str) -> None:
        if name not in self._models:
            raise ValueError(f"Model '{name}' not found in pool")
        self._default_model = name

    def select_by_capabilities(
        self,
        required_capabilities: LLMCapabilities,
        prefer_default: bool = False
    ) -> Optional[BaseLLM]:
        if prefer_default and self._default_model:
            default_entry = self._models[self._default_model]
            if self._capabilities_match(default_entry.capabilities, required_capabilities):
                return default_entry.llm

        for entry in self._models.values():
            if self._capabilities_match(entry.capabilities, required_capabilities):
                return entry.llm
        return None

    def select(
        self,
        selector: Callable[[Dict[str, ModelEntry]], Optional[str]] = None,
        **requirements
    ) -> Optional[BaseLLM]:
        if selector:
            selected_name = selector(self._models)
            return self.get(selected_name) if selected_name else None

        if requirements:
            required_caps = LLMCapabilities(**requirements)
            return self.select_by_capabilities(required_caps)
        return self.get_default()

    def list_models(self) -> Dict[str, ModelEntry]:
        return dict(self._models)

    def remove(self, name: str) -> None:
        if name in self._models:
            del self._models[name]
            if self._default_model == name:
                self._default_model = next(iter(self._models), None)

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, name: str) -> bool:
        return name in self._models

    @staticmethod
    def _capabilities_match(
        model_caps: LLMCapabilities,
        required_caps: LLMCapabilities
    ) -> bool:
        if required_caps.supports_tools and not model_caps.supports_tools:
            return False
        if required_caps.supports_vision and not model_caps.supports_vision:
            return False
        if required_caps.supports_json_mode and not model_caps.supports_json_mode:
            return False
        if required_caps.max_tokens > model_caps.max_tokens:
            return False
        if required_caps.context_window > model_caps.context_window:
            return False
        return True


class CapabilityBasedSelector:
    def __init__(
        self,
        prefer_default: bool = True,
        fallback_to_default: bool = True
    ):
        self.prefer_default = prefer_default
        self.fallback_to_default = fallback_to_default

    def select(
        self,
        pool: ModelPool,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseLLM]:
        if not task_context:
            return pool.get_default()

        required_caps = self._infer_capabilities(task_context)
        selected = pool.select_by_capabilities(
            required_caps,
            prefer_default=self.prefer_default
        )
        if selected is None and self.fallback_to_default:
            selected = pool.get_default()
        return selected

    def _infer_capabilities(
        self,
        task_context: Dict[str, Any]
    ) -> LLMCapabilities:
        return LLMCapabilities(
            supports_vision=task_context.get("has_image", False),
            supports_tools=task_context.get("needs_tools", False),
            context_window=task_context.get("context_size", 8192),
            max_tokens=task_context.get("max_output", 4096)
        )

