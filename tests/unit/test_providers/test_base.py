"""
Tests for Provider Base
"""

from unittest.mock import AsyncMock

import pytest

from loom.providers.base import Provider


class TestProvider:
    """Test suite for Provider base class"""

    def test_provider_is_abstract(self):
        """Test Provider cannot be instantiated directly"""
        with pytest.raises(TypeError):
            Provider()

    def test_provider_init_with_config(self):
        """Test Provider initialization with config"""

        class TestProvider(Provider):
            async def initialize(self):
                pass

            async def close(self):
                pass

        config = {"key": "value", "number": 42}
        provider = TestProvider(config)

        assert provider.config == config

    def test_provider_init_without_config(self):
        """Test Provider initialization without config"""

        class TestProvider(Provider):
            async def initialize(self):
                pass

            async def close(self):
                pass

        provider = TestProvider()

        assert provider.config == {}

    def test_provider_init_with_none_config(self):
        """Test Provider initialization with None config"""

        class TestProvider(Provider):
            async def initialize(self):
                pass

            async def close(self):
                pass

        provider = TestProvider(None)

        assert provider.config == {}

    @pytest.mark.asyncio
    async def test_provider_initialize_implementation(self):
        """Test Provider initialize method"""

        class TestProvider(Provider):
            def __init__(self, config=None):
                super().__init__(config)
                self.initialized = False

            async def initialize(self):
                self.initialized = True

            async def close(self):
                pass

        provider = TestProvider()
        await provider.initialize()

        assert provider.initialized is True

    @pytest.mark.asyncio
    async def test_provider_close_implementation(self):
        """Test Provider close method"""

        class TestProvider(Provider):
            def __init__(self, config=None):
                super().__init__(config)
                self.closed = False

            async def initialize(self):
                pass

            async def close(self):
                self.closed = True

        provider = TestProvider()
        await provider.close()

        assert provider.closed is True

    @pytest.mark.asyncio
    async def test_provider_full_lifecycle(self):
        """Test Provider full lifecycle"""

        class TestProvider(Provider):
            def __init__(self, config=None):
                super().__init__(config)
                self.state = "created"

            async def initialize(self):
                self.state = "initialized"

            async def close(self):
                self.state = "closed"

        provider = TestProvider()
        assert provider.state == "created"

        await provider.initialize()
        assert provider.state == "initialized"

        await provider.close()
        assert provider.state == "closed"

    def test_provider_config_mutation(self):
        """Test that provider config can be mutated"""

        class TestProvider(Provider):
            async def initialize(self):
                pass

            async def close(self):
                pass

        provider = TestProvider({"key": "value"})
        provider.config["new_key"] = "new_value"

        assert provider.config["new_key"] == "new_value"
