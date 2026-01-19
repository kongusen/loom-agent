"""
Content Sanitizer Unit Tests

测试内容清理器的功能
"""

import pytest

from loom.memory.sanitizers import ContentSanitizer


class TestContentSanitizerInit:
    """测试 ContentSanitizer 初始化"""

    def test_init(self):
        """测试初始化"""
        sanitizer = ContentSanitizer()

        assert sanitizer.patterns is not None
        assert "email" in sanitizer.patterns
        assert "phone" in sanitizer.patterns
        assert "api_key" in sanitizer.patterns

    def test_load_patterns(self):
        """测试加载模式"""
        sanitizer = ContentSanitizer()

        patterns = sanitizer._load_patterns()

        assert isinstance(patterns, dict)
        assert len(patterns) > 0


class TestContentSanitizerSanitize:
    """测试内容清理功能"""

    def test_sanitize_basic(self):
        """测试基本清理"""
        sanitizer = ContentSanitizer()

        content = "  Hello   World  "
        result = sanitizer.sanitize(content)

        assert result == "Hello World"

    def test_sanitize_email(self):
        """测试清理邮箱"""
        sanitizer = ContentSanitizer()

        content = "Contact me at test@example.com"
        result = sanitizer.sanitize(content, mask_sensitive=True)

        assert "[EMAIL]" in result
        assert "test@example.com" not in result

    def test_sanitize_phone(self):
        """测试清理电话"""
        sanitizer = ContentSanitizer()

        content = "Call me at 123-456-7890"
        result = sanitizer.sanitize(content, mask_sensitive=True)

        assert "[PHONE]" in result
        assert "123-456-7890" not in result

    def test_sanitize_api_key(self):
        """测试清理API密钥"""
        sanitizer = ContentSanitizer()

        content = "API key: abcdefghijklmnopqrstuvwxyz123456"
        result = sanitizer.sanitize(content, mask_sensitive=True)

        assert "[API_KEY]" in result

    def test_sanitize_url(self):
        """测试清理URL"""
        sanitizer = ContentSanitizer()

        content = "Visit https://example.com for more info"
        result = sanitizer.sanitize(content, mask_sensitive=True)

        assert "[URL]" in result
        assert "https://example.com" not in result

    def test_sanitize_credit_card(self):
        """测试清理信用卡号"""
        sanitizer = ContentSanitizer()

        content = "Card: 1234-5678-9012-3456"
        result = sanitizer.sanitize(content, mask_sensitive=True)

        assert "[CREDIT_CARD]" in result

    def test_sanitize_without_masking(self):
        """测试不掩码敏感信息"""
        sanitizer = ContentSanitizer()

        content = "Email: test@example.com Phone: 123-456-7890"
        result = sanitizer.sanitize(content, mask_sensitive=False)

        assert "test@example.com" in result
        assert "123-456-7890" in result

    def test_sanitize_normalize_newlines(self):
        """测试规范化换行"""
        sanitizer = ContentSanitizer()

        content = "Line1\r\nLine2\rLine3\nLine4"
        result = sanitizer.sanitize(content)

        # sanitize 会将所有空白字符（包括换行）替换为单个空格
        assert "\r\n" not in result
        assert "\r" not in result
        # 注意：sanitize 会将所有空白替换为单个空格，所以换行也会被替换
        assert "Line1" in result
        assert "Line2" in result

    def test_sanitize_remove_control_chars(self):
        """测试移除控制字符"""
        sanitizer = ContentSanitizer()

        content = "Hello\x00World\x01Test"
        result = sanitizer.sanitize(content)

        assert "\x00" not in result
        assert "\x01" not in result
        assert "Hello" in result
        assert "World" in result

    def test_sanitize_empty_string(self):
        """测试清理空字符串"""
        sanitizer = ContentSanitizer()

        result = sanitizer.sanitize("")

        assert result == ""

    def test_sanitize_none(self):
        """测试清理 None"""
        sanitizer = ContentSanitizer()

        result = sanitizer.sanitize(None)

        assert result == ""

    def test_sanitize_non_string(self):
        """测试清理非字符串类型"""
        sanitizer = ContentSanitizer()

        result = sanitizer.sanitize(123)

        assert result == "123"


class TestContentSanitizerValidate:
    """测试内容验证功能"""

    def test_validate_valid_content(self):
        """测试验证有效内容"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate("Hello World") is True
        assert sanitizer.validate("Test123") is True
        assert sanitizer.validate("Content with numbers 123") is True

    def test_validate_empty_string(self):
        """测试验证空字符串"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate("") is False

    def test_validate_none(self):
        """测试验证 None"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate(None) is False

    def test_validate_whitespace_only(self):
        """测试验证只有空白字符"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate("   ") is False
        assert sanitizer.validate("\n\t") is False
        assert sanitizer.validate(" \t\n\r") is False
        assert sanitizer.validate("     ") is False

    def test_validate_no_alphanumeric(self):
        """测试验证没有字母数字字符"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate("!@#$%^&*()") is False
        assert sanitizer.validate("---") is False

    def test_validate_non_string(self):
        """测试验证非字符串类型"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate(123) is False
        assert sanitizer.validate([]) is False
        assert sanitizer.validate({}) is False

    def test_validate_with_alphanumeric(self):
        """测试验证包含字母数字的内容"""
        sanitizer = ContentSanitizer()

        assert sanitizer.validate("Hello!") is True
        assert sanitizer.validate("123!@#") is True
        assert sanitizer.validate("Test-123") is True
