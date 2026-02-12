"""
Token Counter - Token 计数器

提供统一的 token 计数接口，支持多种 LLM 的 tokenizer。

设计原则：
1. 抽象接口 - 支持多种实现
2. 缓存优化 - 使用 LRU 缓存提升性能
3. 降级策略 - 提供估算模式作为后备
"""

from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tiktoken import Encoding


class TokenCounter(ABC):
    """
    Token 计数器抽象基类

    所有 token 计数器必须实现此接口。
    """

    @abstractmethod
    def count(self, text: str) -> int:
        """
        计算文本的 token 数

        Args:
            text: 要计算的文本

        Returns:
            token 数量
        """
        pass

    @abstractmethod
    def count_messages(self, messages: list[dict]) -> int:
        """
        计算消息列表的 token 数

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]

        Returns:
            总 token 数量
        """
        pass


class EstimateCounter(TokenCounter):
    """
    估算计数器 - 使用简单的字符数估算

    规则：1 token ≈ 4 字符（英文）或 1.5 字符（中文）

    适用场景：
    - 没有对应 tokenizer 的模型
    - 不需要精确计数的场景
    - 作为其他计数器的后备
    """

    def __init__(self, chars_per_token: float = 4.0):
        """
        初始化估算计数器

        Args:
            chars_per_token: 每个 token 的平均字符数
        """
        self.chars_per_token = chars_per_token

    def count(self, text: str) -> int:
        """计算文本的 token 数（估算）"""
        if not text:
            return 0
        return max(1, int(len(text) / self.chars_per_token))

    def count_messages(self, messages: list[dict]) -> int:
        """计算消息列表的 token 数（估算）"""
        total = 0
        for msg in messages:
            # 消息格式开销：约 4 tokens
            total += 4
            # 角色
            total += self.count(msg.get("role", ""))
            # 内容
            total += self.count(msg.get("content", ""))
        return total


class TiktokenCounter(TokenCounter):
    """
    Tiktoken 计数器 - 用于 OpenAI 模型

    使用 OpenAI 的 tiktoken 库进行精确计数。

    支持的模型：
    - gpt-4, gpt-4-turbo, gpt-4o
    - gpt-3.5-turbo
    - text-embedding-ada-002
    """

    def __init__(self, model: str = "gpt-4", cache_size: int = 1024):
        """
        初始化 Tiktoken 计数器

        Args:
            model: OpenAI 模型名称
            cache_size: LRU 缓存最大条目数
        """
        self.model = model
        self._encoding: Encoding | None = None
        self._cache: OrderedDict[str, int] = OrderedDict()
        self._cache_size = cache_size
        self._load_encoding()

    def _load_encoding(self):
        """加载 tiktoken encoding"""
        try:
            import tiktoken

            try:
                self._encoding = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # 如果模型不支持，使用默认的 cl100k_base（GPT-4）
                self._encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            # tiktoken 未安装，降级到估算模式
            self._encoding = None

    def count(self, text: str) -> int:
        """计算文本的 token 数（精确，带 LRU 缓存）"""
        if not text:
            return 0

        if self._encoding is None:
            # 降级到估算模式
            return EstimateCounter().count(text)

        # Cache lookup
        cached = self._cache.get(text)
        if cached is not None:
            self._cache.move_to_end(text)
            return cached

        # Compute and cache
        result = len(self._encoding.encode(text))
        self._cache[text] = result
        if len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)
        return result

    def count_messages(self, messages: list[dict]) -> int:
        """
        计算消息列表的 token 数（精确）

        参考 OpenAI 的计算方法：
        https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        """
        if self._encoding is None:
            # 降级到估算模式
            return EstimateCounter().count_messages(messages)

        total = 3  # 每个消息列表的固定开销

        for msg in messages:
            total += 3  # 每条消息的固定开销
            total += self.count(msg.get("role", ""))
            total += self.count(msg.get("content", ""))

            # 如果有 name 字段
            if "name" in msg:
                total += self.count(msg["name"])
                total -= 1  # name 字段会减少 1 个 token

        return total

    def clear_cache(self) -> None:
        """清空 token 计数缓存"""
        self._cache.clear()

    @property
    def cache_info(self) -> dict[str, int]:
        """返回缓存统计信息"""
        return {"size": len(self._cache), "max_size": self._cache_size}


class AnthropicCounter(TokenCounter):
    """
    Anthropic 计数器 - 用于 Claude 模型

    Anthropic 使用自己的 tokenizer，规则：
    - 英文：约 3.5 字符/token
    - 中文：约 1.5 字符/token

    由于 Anthropic 没有公开的 tokenizer 库，使用估算方法。
    """

    def __init__(self):
        """初始化 Anthropic 计数器"""
        # Anthropic 的平均字符/token 比率
        self.chars_per_token = 3.5

    def count(self, text: str) -> int:
        """计算文本的 token 数（估算）"""
        if not text:
            return 0
        return max(1, int(len(text) / self.chars_per_token))

    def count_messages(self, messages: list[dict]) -> int:
        """计算消息列表的 token 数（估算）"""
        total = 0
        for msg in messages:
            # 消息格式开销
            total += 3
            # 角色
            total += self.count(msg.get("role", ""))
            # 内容
            total += self.count(msg.get("content", ""))
        return total
