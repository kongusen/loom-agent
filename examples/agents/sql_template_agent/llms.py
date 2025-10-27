"""LLM 工厂：默认使用 test_new_features.GPT4oMiniLLM。"""

from __future__ import annotations

import os
from typing import Optional

from loom.interfaces.llm import BaseLLM


def create_llm(
    *,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "gpt-4o-mini",
) -> BaseLLM:
    """创建支持工具调用的 LLM 实例。

    默认复用 test_new_features.py 中的 GPT4oMiniLLM 定义，允许通过环境变量
    `LOOM_XIAOAI_BASE_URL` 和 `LOOM_XIAOAI_API_KEY` 覆盖。
    """
    try:
        from test_new_features import GPT4oMiniLLM
    except ImportError as exc:  # pragma: no cover - 仅在文件缺失时触发
        raise RuntimeError(
            "未找到 GPT4oMiniLLM，请确认 test_new_features.py 保存在仓库根目录。"
        ) from exc

    llm = GPT4oMiniLLM()
    if base_url or os.getenv("LOOM_XIAOAI_BASE_URL"):
        llm.base_url = base_url or os.getenv("LOOM_XIAOAI_BASE_URL")
    if api_key or os.getenv("LOOM_XIAOAI_API_KEY"):
        llm.api_key = api_key or os.getenv("LOOM_XIAOAI_API_KEY")
    if model:
        llm.model = model

    return llm

