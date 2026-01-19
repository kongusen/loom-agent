"""
内容清理器 (Content Sanitizer)

清理和规范化记忆内容，保证记忆质量。

功能：
- 移除敏感信息（邮箱、电话、API密钥等）
- 清理格式问题（多余空白、换行等）
- 规范化内容
- 验证内容有效性

基于 A4 公理：记忆层次公理
"""

import re
from re import Pattern


class ContentSanitizer:
    """
    内容清理器

    提供内容清理和验证功能
    """

    def __init__(self):
        """初始化清理器，加载清理模式"""
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> dict[str, Pattern[str]]:
        """
        加载清理模式

        Returns:
            模式字典，键为模式名称，值为编译后的正则表达式
        """
        return {
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "phone": re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
            "api_key": re.compile(r"\b[A-Za-z0-9]{32,}\b"),
            "url": re.compile(r"https?://[^\s]+"),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        }

    def sanitize(self, content: str, mask_sensitive: bool = True) -> str:
        """
        清理内容

        Args:
            content: 要清理的内容
            mask_sensitive: 是否掩码敏感信息，默认 True

        Returns:
            清理后的内容
        """
        if not content or not isinstance(content, str):
            return str(content) if content else ""

        # 1. 移除多余空白
        content = re.sub(r"\s+", " ", content).strip()

        # 2. 掩码敏感信息
        if mask_sensitive:
            for pattern_name, pattern in self.patterns.items():
                content = pattern.sub(f"[{pattern_name.upper()}]", content)

        # 3. 规范化换行
        content = content.replace("\r\n", "\n")

        # 4. 移除控制字符（保留换行和制表符）
        content = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", content)

        return content

    def validate(self, content: str) -> bool:
        """
        验证内容是否有效

        Args:
            content: 要验证的内容

        Returns:
            True 表示内容有效
        """
        if not content:
            return False

        if not isinstance(content, str):
            return False

        # 检查内容长度
        if len(content.strip()) == 0:
            return False

        # 检查是否全是空白字符
        if content.isspace():
            return False

        # 检查是否包含有效字符
        if not any(c.isalnum() for c in content):
            return False

        return True
