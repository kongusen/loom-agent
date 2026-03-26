"""PartitionManager — 管理 5 个上下文分区（公理一）"""

from __future__ import annotations

from ..types import ContextPartition, Tokenizer


class PartitionManager:
    """管理 C_system/working/memory/skill/history 五个分区"""

    def __init__(self, window: int, tokenizer: Tokenizer):
        self.window = window
        self.tokenizer = tokenizer
        self.partitions: dict[str, ContextPartition] = {
            "system": ContextPartition("system", "", 0, 5, False, False),
            "working": ContextPartition("working", "", 0, 4, True, False),
            "memory": ContextPartition("memory", "", 0, 3, False, True),
            "skill": ContextPartition("skill", "", 0, 2, False, True),
            "history": ContextPartition("history", "", 0, 1, False, True),
        }

    def update_partition(self, name: str, content: str) -> None:
        """更新分区内容并重新计算 token"""
        if name in self.partitions:
            self.partitions[name].content = content
            self.partitions[name].tokens = self.tokenizer.count(content)

    def append_to_history(self, content: str, tokens: int) -> None:
        """增量追加到 history，避免重新计算"""
        p = self.partitions["history"]
        p.content += content
        p.tokens += tokens

    def compute_decay(self) -> float:
        """计算腐烂系数 ρ = |C_history| / W_max"""
        return self.partitions["history"].tokens / self.window if self.window > 0 else 0.0

    def get_total_tokens(self) -> int:
        """获取当前总 token 数"""
        return sum(p.tokens for p in self.partitions.values())

    def should_compress(self) -> bool:
        """判断是否需要压缩：0.60 ≤ ρ < 0.85"""
        rho = self.compute_decay()
        return 0.60 <= rho < 0.85

    def should_heartbeat(self) -> bool:
        """判断是否需要心跳续写：ρ ≥ 0.85"""
        return self.compute_decay() >= 0.85

    def get_available_budget(self, for_partition: str) -> int:
        """计算指定分区的可用预算"""
        used = sum(p.tokens for name, p in self.partitions.items() if name != for_partition)
        return max(0, self.window - used)

    def get_context(self) -> str:
        """按优先级组装完整上下文"""
        parts = []
        for name in ["system", "working", "memory", "skill", "history"]:
            if self.partitions[name].content:
                parts.append(self.partitions[name].content)
        return "\n\n".join(parts)
