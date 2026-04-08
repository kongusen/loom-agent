"""H_b heartbeat - 独立感知层，与 L* 并行运行"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WatchSource:
    """监控源配置"""
    type: str  # filesystem, process, mf_events, resource, external_signal
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class HeartbeatConfig:
    """H_b 配置 - 由 Ψ 在构建时设定"""
    T_hb: float = 5.0  # 心跳间隔（秒）
    delta_hb: float = 0.1  # 最小信息熵增量
    watch_sources: list[WatchSource] = field(default_factory=list)
    interrupt_policy: dict[str, str] = field(default_factory=lambda: {
        "low": "queue",
        "high": "request",
        "critical": "force"
    })


class Heartbeat:
    """H_b 独立心跳感知层"""

    def __init__(self, config: HeartbeatConfig):
        self.config = config
        self.running = False
        self.thread: threading.Thread | None = None
        self.event_callback: Callable | None = None
        # Monitor caches with type annotations
        self._fs_monitors: dict[str, Any] = {}
        self._proc_monitors: dict[str, Any] = {}
        self._res_monitors: dict[str, Any] = {}
        self._mf_monitors: dict[str, Any] = {}

    def start(self, event_callback: Callable):
        """启动心跳线程"""
        self.event_callback = event_callback
        self.running = True
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止心跳"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _heartbeat_loop(self):
        """心跳主循环"""
        while self.running:
            timestamp = datetime.now().isoformat()

            # 检查所有监控源
            for source in self.config.watch_sources:
                event = self._check_source(source, timestamp)
                if event and event.get("delta_H", 0) > self.config.delta_hb:
                    # 分类紧迫度并注入事件
                    urgency = self._classify_urgency(event)
                    self.process_event(event, urgency)

            time.sleep(self.config.T_hb)

    def _check_source(self, source: WatchSource, timestamp: str) -> dict | None:
        """检查单个监控源"""
        from .monitors import FilesystemMonitor, MFEventsMonitor, ProcessMonitor, ResourceMonitor

        if source.type == "filesystem":
            key = str(source.config)
            if key not in self._fs_monitors:
                self._fs_monitors[key] = FilesystemMonitor(
                    source.config.get("paths", []),
                    source.config.get("method", "hash")
                )
            result = self._fs_monitors[key].check(timestamp)
            return result if isinstance(result, dict) or result is None else None

        elif source.type == "process":
            key = str(source.config)
            if key not in self._proc_monitors:
                self._proc_monitors[key] = ProcessMonitor(
                    source.config.get("pid_file"),
                    source.config.get("watch_pids", []),
                )
            result = self._proc_monitors[key].check(timestamp)
            return result if isinstance(result, dict) or result is None else None

        elif source.type == "resource":
            key = str(source.config)
            if key not in self._res_monitors:
                self._res_monitors[key] = ResourceMonitor(source.config.get("thresholds", {}))
            result = self._res_monitors[key].check(timestamp)
            return result if isinstance(result, dict) or result is None else None

        elif source.type == "mf_events":
            key = str(source.config)
            if key not in self._mf_monitors:
                self._mf_monitors[key] = MFEventsMonitor(
                    source.config.get("topics", []),
                    event_bus=source.config.get("event_bus"),
                )
            result = self._mf_monitors[key].check(timestamp)
            return result if isinstance(result, dict) or result is None else None

        return None

    def _classify_urgency(self, event: dict) -> str:
        """分类事件紧迫度"""
        delta_H = event.get("delta_H", 0)
        if delta_H > 0.8:
            return "critical"
        elif delta_H > 0.5:
            return "high"
        else:
            return "low"

    def process_event(self, event: dict, urgency: str, dashboard_manager: Any | None = None) -> dict:
        """Standardize one heartbeat event and dispatch it."""
        event["urgency"] = urgency

        if dashboard_manager is not None:
            dashboard_manager.ingest_heartbeat_event(event, urgency)

        if self.event_callback:
            self.event_callback(event, urgency)

        return event

    def dashboard_callback(self, dashboard_manager: Any) -> Callable:
        """Create a callback that projects events into a dashboard manager."""

        def _callback(event: dict, urgency: str):
            self.process_event(event, urgency, dashboard_manager=dashboard_manager)

        return _callback
