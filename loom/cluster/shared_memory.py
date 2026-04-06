"""M_f 文件系统共享"""

from pathlib import Path
import json


class SharedMemory:
    """M_f 共享内存"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write(self, key: str, value: dict):
        """写入共享数据"""
        file_path = self.base_path / f"{key}.json"
        file_path.write_text(json.dumps(value))

    def read(self, key: str) -> dict | None:
        """读取共享数据"""
        file_path = self.base_path / f"{key}.json"
        if file_path.exists():
            return json.loads(file_path.read_text())
        return None

    def delete(self, key: str):
        """删除共享数据"""
        file_path = self.base_path / f"{key}.json"
        if file_path.exists():
            file_path.unlink()
