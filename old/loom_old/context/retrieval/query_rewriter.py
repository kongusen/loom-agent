"""
QueryRewriter - 轻量级查询增强

纯文本处理，不调用 LLM。
从对话上下文中提取关键词，与原始查询拼接，提升检索召回率。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RewriteResult:
    """查询重写结果"""

    original: str
    rewritten: str
    keywords: list[str] = field(default_factory=list)


class QueryRewriter:
    """
    查询重写器

    策略：
    1. 从最近 N 条对话消息中提取高频实词
    2. 过滤停用词和短词
    3. 将 top-K 关键词追加到原始查询
    """

    # 英文停用词（精简版）
    _EN_STOPWORDS: set[str] = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "must",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "this",
        "that",
        "these",
        "those",
        "what",
        "which",
        "who",
        "whom",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "when",
        "where",
        "how",
        "not",
        "no",
        "nor",
        "so",
        "too",
        "very",
        "just",
        "also",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "into",
        "about",
        "between",
        "through",
        "after",
        "before",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
    }

    # 中文停用词（精简版）
    _ZH_STOPWORDS: set[str] = {
        "的",
        "了",
        "在",
        "是",
        "我",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "他",
        "她",
        "它",
        "们",
        "那",
        "些",
        "什么",
        "怎么",
        "如何",
        "可以",
        "但是",
        "因为",
        "所以",
        "如果",
        "虽然",
        "还是",
        "或者",
        "以及",
        "而且",
    }

    _WORD_PATTERN = re.compile(r"[\w\u4e00-\u9fff]{2,}", re.UNICODE)

    def __init__(
        self,
        max_context_messages: int = 5,
        max_keywords: int = 6,
        min_word_length: int = 2,
        extra_stopwords: set[str] | None = None,
    ):
        self._max_context_messages = max_context_messages
        self._max_keywords = max_keywords
        self._min_word_length = min_word_length
        self._stopwords = self._EN_STOPWORDS | self._ZH_STOPWORDS
        if extra_stopwords:
            self._stopwords |= extra_stopwords

    def rewrite(
        self,
        query: str,
        context_messages: list[dict[str, str]] | None = None,
    ) -> RewriteResult:
        """
        重写查询

        Args:
            query: 原始查询
            context_messages: 最近的对话消息 [{"role": "...", "content": "..."}]

        Returns:
            RewriteResult
        """
        if not query:
            return RewriteResult(original=query, rewritten=query)

        if not context_messages:
            return RewriteResult(original=query, rewritten=query)

        # 取最近 N 条消息
        recent = context_messages[-self._max_context_messages :]

        # 提取所有词
        word_freq: dict[str, int] = {}
        query_words = {w.lower() for w in self._WORD_PATTERN.findall(query)}

        for msg in recent:
            content = msg.get("content", "")
            words = self._WORD_PATTERN.findall(content)
            for w in words:
                w_lower = w.lower()
                if (
                    len(w_lower) >= self._min_word_length
                    and w_lower not in self._stopwords
                    and w_lower not in query_words
                ):
                    word_freq[w_lower] = word_freq.get(w_lower, 0) + 1

        # 按频率排序，取 top-K
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [w for w, _ in sorted_words[: self._max_keywords]]

        if not keywords:
            return RewriteResult(original=query, rewritten=query, keywords=[])

        # 拼接：原始查询 + 关键词上下文
        enrichment = " ".join(keywords)
        rewritten = f"{query} [{enrichment}]"

        return RewriteResult(
            original=query,
            rewritten=rewritten,
            keywords=keywords,
        )
