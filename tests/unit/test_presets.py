"""Coverage-boost tests for providers/presets.py."""

from loom.providers.presets import (
    create_deepseek, create_qwen, create_zhipu,
    create_moonshot, create_baichuan, create_yi, create_doubao,
)
from loom.providers.openai import OpenAIProvider


class TestPresets:
    def test_create_deepseek(self):
        p = create_deepseek(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_qwen(self):
        p = create_qwen(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_zhipu(self):
        p = create_zhipu(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_moonshot(self):
        p = create_moonshot(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_baichuan(self):
        p = create_baichuan(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_yi(self):
        p = create_yi(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    def test_create_doubao(self):
        p = create_doubao(api_key="test-key")
        assert isinstance(p, OpenAIProvider)
