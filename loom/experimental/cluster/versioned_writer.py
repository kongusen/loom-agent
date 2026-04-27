"""版本化写入机制

根据 Q3 实验结果解决 DAG 拓扑写冲突
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WriteVersion:
    """写入版本"""

    agent_id: str
    content: Any
    timestamp: datetime = field(default_factory=datetime.now)
    version: int = 1


class VersionedWriter:
    """版本化写入"""

    def __init__(self):
        self.versions: dict[str, list[WriteVersion]] = {}

    def write(self, key: str, content: Any, agent_id: str):
        """版本化写入

        实验结果: 0 冲突, 3 版本
        """
        if key not in self.versions:
            self.versions[key] = []

        version = WriteVersion(
            agent_id=agent_id, content=content, version=len(self.versions[key]) + 1
        )
        self.versions[key].append(version)

    def read_latest(self, key: str) -> Any:
        """读取最新版本"""
        if key not in self.versions or not self.versions[key]:
            return None
        return self.versions[key][-1].content

    def merge_all(self, key: str) -> Any:
        """合并所有版本"""
        if key not in self.versions:
            return None

        contents = [v.content for v in self.versions[key]]
        return {"merged": contents, "version_count": len(contents)}
