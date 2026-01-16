"""
Retry Handler for LLM API Calls

提供智能重试机制，处理：
- 速率限制 (Rate Limit)
- 临时网络错误
- 超时
"""

import asyncio
import logging
from collections.abc import Callable
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retry_on_timeout: bool = True,
        retry_on_rate_limit: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retry_on_timeout = retry_on_timeout
        self.retry_on_rate_limit = retry_on_rate_limit


def should_retry(exception: Exception, config: RetryConfig) -> bool:
    """判断是否应该重试"""

    # 超时错误
    if isinstance(exception, asyncio.TimeoutError):
        return config.retry_on_timeout

    # OpenAI 特定错误
    try:
        from openai import APIConnectionError, APITimeoutError, RateLimitError

        if isinstance(exception, RateLimitError):
            return config.retry_on_rate_limit

        if isinstance(exception, APITimeoutError | APIConnectionError):
            return True

    except ImportError:
        pass

    # 其他错误不重试
    return False


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """计算重试延迟（指数退避）"""
    delay = config.initial_delay * (config.exponential_base ** attempt)
    return min(delay, config.max_delay)


async def retry_async(
    func: Callable[..., T],
    config: RetryConfig | None = None,
    *args,
    **kwargs
) -> T:
    """
    异步函数重试包装器

    Args:
        func: 要重试的异步函数
        config: 重试配置
        *args, **kwargs: 传递给函数的参数

    Returns:
        函数执行结果

    Raises:
        最后一次尝试的异常
    """
    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except Exception as e:
            last_exception = e

            # 最后一次尝试，直接抛出异常
            if attempt == config.max_retries:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_retries} retries: {str(e)}"
                )
                raise

            # 判断是否应该重试
            if not should_retry(e, config):
                logger.warning(
                    f"Function {func.__name__} failed with non-retryable error: {str(e)}"
                )
                raise

            # 计算延迟并等待
            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Function {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}), "
                f"retrying in {delay:.2f}s: {str(e)}"
            )
            await asyncio.sleep(delay)

    # 理论上不会到达这里
    raise last_exception
