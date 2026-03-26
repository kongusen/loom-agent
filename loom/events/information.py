"""Information gain calculator for Axiom 3."""

from __future__ import annotations

import math


class InformationGainCalculator:
    """计算事件的信息增益 ΔH(e)"""

    def __init__(self, delta_min: float = 0.1, epsilon: int = 1000) -> None:
        self.delta_min = delta_min  # 发布门控阈值
        self.epsilon = epsilon  # 压缩阈值（token 数）

    def calculate_delta_h(self, payload: str, context: str = "") -> float:
        """计算信息增益 ΔH(e) = H(Ω) - H(Ω|e)"""
        if not payload:
            return 0.0

        # 简化实现：基于 payload 长度和唯一性
        payload_entropy = self._entropy(payload)
        context_entropy = self._entropy(context) if context else 0.0

        # ΔH = 新信息熵 - 已知信息熵
        delta_h = max(0.0, payload_entropy - context_entropy * 0.5)
        return delta_h

    def _entropy(self, text: str) -> float:
        """计算文本熵（简化版）"""
        if not text:
            return 0.0

        # 字符频率分布
        freq: dict[str, int] = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1

        # Shannon 熵
        entropy = 0.0
        total = len(text)
        for count in freq.values():
            p = count / total
            entropy -= p * math.log2(p)

        return entropy

    def should_publish(self, delta_h: float) -> bool:
        """公理 3.1: 发布门控"""
        return delta_h > self.delta_min

    def should_compress(self, payload: str) -> bool:
        """公理 3.2: 压缩门控"""
        return len(payload) > self.epsilon

    def compress_payload(self, payload: str) -> str:
        """压缩 payload（简化实现）"""
        if len(payload) <= self.epsilon:
            return payload

        # 简单截断保留关键信息
        return payload[: self.epsilon] + "..."

    def calculate_priority(self, delta_h: float) -> int:
        """根据 ΔH 计算优先级"""
        return int(delta_h * 10)
