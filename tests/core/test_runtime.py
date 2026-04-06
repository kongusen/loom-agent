"""Test runtime components"""

import pytest
from loom.runtime.heartbeat import Heartbeat, HeartbeatConfig, WatchSource


class TestHeartbeat:
    """Test Heartbeat"""

    def test_heartbeat_config_defaults(self):
        """Test HeartbeatConfig defaults"""
        config = HeartbeatConfig()
        assert config.T_hb == 5.0
        assert config.delta_hb == 0.1
        assert config.watch_sources == []
        assert config.interrupt_policy["low"] == "queue"

    def test_heartbeat_config_custom(self):
        """Test HeartbeatConfig custom values"""
        sources = [WatchSource(type="filesystem", config={"paths": ["/tmp"]})]
        config = HeartbeatConfig(T_hb=1.0, delta_hb=0.2, watch_sources=sources)
        assert config.T_hb == 1.0
        assert config.delta_hb == 0.2
        assert len(config.watch_sources) == 1

    def test_heartbeat_creation(self):
        """Test Heartbeat creation"""
        config = HeartbeatConfig()
        hb = Heartbeat(config)
        assert hb.config == config
        assert hb.running is False
        assert hb.thread is None

    def test_classify_urgency(self):
        """Test urgency classification"""
        config = HeartbeatConfig()
        hb = Heartbeat(config)

        assert hb._classify_urgency({"delta_H": 0.9}) == "critical"
        assert hb._classify_urgency({"delta_H": 0.6}) == "high"
        assert hb._classify_urgency({"delta_H": 0.3}) == "low"

    def test_watch_source(self):
        """Test WatchSource"""
        source = WatchSource(type="filesystem", config={"paths": ["/tmp"]})
        assert source.type == "filesystem"
        assert source.config["paths"] == ["/tmp"]
