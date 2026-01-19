"""
Tests for Custom LLM Provider
"""

import pytest

from loom.providers.llm.custom import CustomProvider


class TestCustomProviderAttributes:
    """Test suite for CustomProvider attributes"""

    def test_provider_name_attribute(self):
        """Test PROVIDER_NAME attribute"""
        assert CustomProvider.PROVIDER_NAME == "Custom"

    def test_default_base_url_attribute(self):
        """Test DEFAULT_BASE_URL attribute"""
        assert CustomProvider.DEFAULT_BASE_URL == "http://localhost:1234/v1"

    def test_default_model_attribute(self):
        """Test DEFAULT_MODEL attribute"""
        assert CustomProvider.DEFAULT_MODEL == "local-model"

    def test_api_key_env_var_attribute(self):
        """Test API_KEY_ENV_VAR attribute"""
        assert CustomProvider.API_KEY_ENV_VAR is None

    def test_custom_provider_inherits_from_openai_compatible(self):
        """Test CustomProvider inherits from OpenAICompatibleProvider"""
        from loom.providers.llm.openai_compatible import OpenAICompatibleProvider

        assert issubclass(CustomProvider, OpenAICompatibleProvider)
