"""Test context components"""

import pytest
from loom.context.manager import ContextManager
from loom.context.partitions import ContextPartitions
from loom.context.compression import ContextCompressor


class TestContextManager:
    """Test ContextManager"""

    def test_context_manager_creation(self):
        """Test ContextManager creation"""
        cm = ContextManager(max_tokens=4000)
        assert cm.max_tokens == 4000
        assert cm.rho >= 0
        assert cm.dashboard.dashboard is cm.partitions.working

    def test_should_renew(self):
        """Test should_renew logic"""
        cm = ContextManager(max_tokens=100)
        assert isinstance(cm.should_renew(), bool)


class TestContextPartitions:
    """Test ContextPartitions"""

    def test_partitions_creation(self):
        """Test ContextPartitions creation"""
        partitions = ContextPartitions()
        assert partitions.system == []
        assert partitions.memory == []
        assert partitions.history == []

    def test_get_all_messages(self):
        """Test get_all_messages"""
        partitions = ContextPartitions()
        messages = partitions.get_all_messages()
        assert isinstance(messages, list)


class TestContextCompressor:
    """Test ContextCompressor"""

    def test_compressor_creation(self):
        """Test ContextCompressor creation"""
        compressor = ContextCompressor()
        assert compressor is not None
