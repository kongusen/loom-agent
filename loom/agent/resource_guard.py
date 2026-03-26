"""Resource guard — hard limits for token/time quotas (Harness P0)."""

from __future__ import annotations

import time


class ResourceGuard:
    """资源配额守卫 - 防止资源耗尽."""

    def __init__(self, max_tokens: int = 100000, max_time_sec: int = 300) -> None:
        self._max_tokens = max_tokens
        self._max_time = max_time_sec
        self._used_tokens = 0
        self._start_time = 0.0

    def start(self) -> None:
        """开始计时."""
        self._start_time = time.time()
        self._used_tokens = 0

    def check_quota(self, estimated_tokens: int = 0) -> tuple[bool, str]:
        """检查是否超配额.

        Returns:
            (is_within_quota, error_message)
        """
        # Token 配额检查
        if self._used_tokens + estimated_tokens > self._max_tokens:
            return (
                False,
                f"Token quota exceeded: {self._used_tokens + estimated_tokens}/{self._max_tokens}",
            )

        # 时间配额检查
        if self._start_time > 0:
            elapsed = time.time() - self._start_time
            if elapsed > self._max_time:
                return False, f"Time quota exceeded: {elapsed:.1f}s/{self._max_time}s"

        return True, ""

    def consume(self, tokens: int) -> None:
        """消耗 token."""
        self._used_tokens += tokens

    def get_remaining_tokens(self) -> int:
        """获取剩余 token."""
        return max(0, self._max_tokens - self._used_tokens)

    def get_remaining_time(self) -> float:
        """获取剩余时间（秒）."""
        if self._start_time == 0:
            return self._max_time
        elapsed = time.time() - self._start_time
        return max(0.0, self._max_time - elapsed)

    def reset(self) -> None:
        """重置配额."""
        self._used_tokens = 0
        self._start_time = 0.0
