"""H_b 监控源实现"""

import hashlib
import os
from pathlib import Path
from typing import Any

import psutil


class FilesystemMonitor:
    """文件系统变化监控"""

    def __init__(self, paths: list[str], method: str = "hash", delta_h: float = 0.7):
        self.paths = [Path(p) for p in paths]
        self.method = method
        self.delta_h = delta_h
        self.cache: dict[str, str] = {}
        self._init_cache()

    def _init_cache(self):
        for path in self.paths:
            if path.exists():
                if path.is_file():
                    self.cache[str(path)] = self._hash_file(path)
                elif path.is_dir():
                    for file in path.rglob("*"):
                        if file.is_file():
                            self.cache[str(file)] = self._hash_file(file)

    def _hash_file(self, path: Path) -> str:
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        except OSError:
            return ""

    def check(self, timestamp: str) -> dict | None:
        """检查文件系统变化，返回第一个变更（更新所有缓存）"""
        changed: list[str] = []
        first_hash = ""
        for path in self.paths:
            if not path.exists():
                continue
            files = [path] if path.is_file() else list(path.rglob("*"))
            for file in files:
                if not file.is_file():
                    continue
                file_str = str(file)
                current_hash = self._hash_file(file)
                cached_hash = self.cache.get(file_str)
                if cached_hash and current_hash != cached_hash:
                    self.cache[file_str] = current_hash
                    if not changed:
                        first_hash = current_hash
                    changed.append(file_str)
                elif not cached_hash:
                    self.cache[file_str] = current_hash

        if not changed:
            return None
        return {
            "event_id": f"evt_fs_{timestamp.replace(':', '')}",
            "source": "filesystem",
            "summary": f"{len(changed)} file(s) modified: {changed[0]}{'...' if len(changed) > 1 else ''}",
            "delta_H": self.delta_h,
            "observed_at": timestamp,
            "fingerprint": first_hash,
            "paths": changed,
        }


class ProcessMonitor:
    """进程状态监控"""

    def __init__(
        self,
        pid_file: str | None = None,
        watch_pids: list[int] | None = None,
        delta_h: float = 0.8,
    ):
        self.pid_file = pid_file
        self.delta_h = delta_h
        self.tracked_pids: set[int] = set(watch_pids or [])

    def check(self, timestamp: str) -> dict | None:
        """检查进程状态"""
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                pid = int(Path(self.pid_file).read_text().strip())
                self.tracked_pids.add(pid)
            except (OSError, ValueError):
                pass

        for pid in sorted(self.tracked_pids):
            if not psutil.pid_exists(pid):
                return {
                    "event_id": f"evt_proc_{timestamp.replace(':', '')}",
                    "source": "process",
                    "summary": f"进程 {pid} 已退出",
                    "delta_H": self.delta_h,
                    "observed_at": timestamp,
                    "pid": pid,
                }

        return None


class ResourceMonitor:
    """系统资源监控"""

    def __init__(
        self,
        thresholds: dict[str, float],
        delta_h_cpu: float = 0.8,
        delta_h_memory: float = 0.9,
        delta_h_disk: float = 0.85,
    ):
        self.thresholds = thresholds
        self.delta_h_cpu = delta_h_cpu
        self.delta_h_memory = delta_h_memory
        self.delta_h_disk = delta_h_disk

    def check(self, timestamp: str) -> dict | None:
        cpu_threshold = self.thresholds.get("cpu_pct", self.thresholds.get("cpu"))
        if cpu_threshold is not None:
            cpu = psutil.cpu_percent(interval=None)
            if cpu > cpu_threshold:
                return {
                    "event_id": f"evt_cpu_{timestamp.replace(':', '')}",
                    "source": "resource",
                    "summary": f"CPU 使用率 {cpu:.1f}% 超过阈值",
                    "delta_H": self.delta_h_cpu,
                    "observed_at": timestamp,
                    "resource": "cpu",
                    "value": cpu,
                }

        memory_threshold = self.thresholds.get("memory_pct", self.thresholds.get("memory"))
        if memory_threshold is not None:
            mem = psutil.virtual_memory()
            if mem.percent > memory_threshold:
                return {
                    "event_id": f"evt_mem_{timestamp.replace(':', '')}",
                    "source": "resource",
                    "summary": f"内存使用率 {mem.percent:.1f}% 超过阈值",
                    "delta_H": self.delta_h_memory,
                    "observed_at": timestamp,
                    "resource": "memory",
                    "value": mem.percent,
                }

        disk_threshold = self.thresholds.get("disk_pct", self.thresholds.get("disk"))
        if disk_threshold is not None:
            disk = psutil.disk_usage("/")
            if disk.percent > disk_threshold:
                return {
                    "event_id": f"evt_disk_{timestamp.replace(':', '')}",
                    "source": "resource",
                    "summary": f"磁盘使用率 {disk.percent:.1f}% 超过阈值",
                    "delta_H": self.delta_h_disk,
                    "observed_at": timestamp,
                    "resource": "disk",
                    "value": disk.percent,
                }

        return None


class MFEventsMonitor:
    """M_f 事件总线监控"""

    def __init__(self, topics: list[str], event_bus: Any | None = None):
        self.topics = topics
        self.event_bus = event_bus
        self.cursor = 0

    def set_event_bus(self, event_bus: Any) -> None:
        """Attach an event bus after construction."""
        self.event_bus = event_bus

    def check(self, timestamp: str) -> dict | None:
        """检查 M_f 事件总线"""
        if self.event_bus is None:
            return None

        events = getattr(self.event_bus, "published_events", [])
        if self.cursor >= len(events):
            return None

        new_events = events[self.cursor:]
        self.cursor = len(events)

        for event in new_events:
            topic = getattr(event, "topic", None)
            if self.topics and topic not in self.topics:
                continue

            delta_h = getattr(event, "delta_h", 0.0)
            return {
                "event_id": f"evt_mf_{getattr(event, 'id', 'unknown')}",
                "source": "mf_events",
                "summary": f"Topic {topic} received from {getattr(event, 'sender', 'unknown')}",
                "delta_H": delta_h,
                "observed_at": timestamp,
                "topic": topic,
                "payload": getattr(event, "payload", {}),
            }

        return None
