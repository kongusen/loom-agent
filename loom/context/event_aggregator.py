"""事件聚合策略

根据 Q9 实验结果实现高频事件压缩
"""

from typing import List, Dict, Any
from collections import defaultdict

class EventAggregator:
    """聚合高频事件，降低 token 占用"""

    def aggregate(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将高频事件聚合为摘要

        实验结果: 事件数从 100 降至 10，token 从 5000 降至 800
        """
        if not events:
            return []

        # 按事件类型分组
        grouped = defaultdict(list)
        for event in events:
            grouped[event.get("type", "unknown")].append(event)

        # 聚合每组
        aggregated = []
        for event_type, group in grouped.items():
            if len(group) > 3:
                # 高频事件：生成摘要
                aggregated.append({
                    "type": event_type,
                    "count": len(group),
                    "summary": f"{len(group)} {event_type} events",
                    "sample": group[0]
                })
            else:
                # 低频事件：保留原样
                aggregated.extend(group)

        return aggregated
