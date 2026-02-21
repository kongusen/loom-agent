"""Coverage-boost tests for providers/presets.py."""

from unittest.mock import patch

from loom.providers.openai import OpenAIProvider
from loom.providers.presets import (
    create_baichuan,
    create_deepseek,
    create_doubao,
    create_moonshot,
    create_qwen,
    create_yi,
    create_zhipu,
)

_NO_PROXY = {
    "https_proxy": "",
    "HTTPS_PROXY": "",
    "http_proxy": "",
    "HTTP_PROXY": "",
    "ALL_PROXY": "",
    "all_proxy": "",
}


class TestPresets:
    @patch.dict("os.environ", _NO_PROXY)
    def test_create_deepseek(self):
        p = create_deepseek(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_qwen(self):
        p = create_qwen(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_zhipu(self):
        p = create_zhipu(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_moonshot(self):
        p = create_moonshot(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_baichuan(self):
        p = create_baichuan(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_yi(self):
        p = create_yi(api_key="test-key")
        assert isinstance(p, OpenAIProvider)

    @patch.dict("os.environ", _NO_PROXY)
    def test_create_doubao(self):
        p = create_doubao(api_key="test-key")
        assert isinstance(p, OpenAIProvider)
