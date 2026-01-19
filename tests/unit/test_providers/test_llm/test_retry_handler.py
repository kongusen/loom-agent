"""
Retry Handler Unit Tests

测试重试处理器的核心功能
"""

import asyncio

import pytest

from loom.providers.llm.retry_handler import (
    RetryConfig,
    calculate_delay,
    retry_async,
    should_retry,
)


class TestRetryConfig:
    """测试RetryConfig配置类"""

    def test_init_default(self):
        """测试默认参数初始化"""
        config = RetryConfig()

        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.retry_on_timeout is True
        assert config.retry_on_rate_limit is True

    def test_init_custom(self):
        """测试自定义参数初始化"""
        config = RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            retry_on_timeout=False,
            retry_on_rate_limit=False,
        )

        assert config.max_retries == 5
        assert config.initial_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.retry_on_timeout is False
        assert config.retry_on_rate_limit is False


class TestCalculateDelay:
    """测试calculate_delay函数"""

    def test_calculate_delay_first_attempt(self):
        """测试第一次重试的延迟"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0)
        delay = calculate_delay(0, config)

        assert delay == 1.0

    def test_calculate_delay_exponential_backoff(self):
        """测试指数退避"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=60.0)

        assert calculate_delay(0, config) == 1.0  # 1 * 2^0 = 1
        assert calculate_delay(1, config) == 2.0  # 1 * 2^1 = 2
        assert calculate_delay(2, config) == 4.0  # 1 * 2^2 = 4
        assert calculate_delay(3, config) == 8.0  # 1 * 2^3 = 8

    def test_calculate_delay_max_limit(self):
        """测试最大延迟限制"""
        config = RetryConfig(initial_delay=1.0, exponential_base=2.0, max_delay=5.0)

        # 2^10 = 1024, 但应该被限制在5.0
        delay = calculate_delay(10, config)
        assert delay == 5.0


class TestShouldRetry:
    """测试should_retry函数"""

    def test_should_retry_timeout_error(self):
        """测试超时错误应该重试"""
        config = RetryConfig(retry_on_timeout=True)
        error = TimeoutError()

        assert should_retry(error, config) is True

    def test_should_not_retry_timeout_when_disabled(self):
        """测试禁用超时重试时不重试"""
        config = RetryConfig(retry_on_timeout=False)
        error = TimeoutError()

        assert should_retry(error, config) is False

    def test_should_not_retry_generic_error(self):
        """测试普通错误不应该重试"""
        config = RetryConfig()
        error = ValueError("Generic error")

        assert should_retry(error, config) is False


class TestRetryAsync:
    """测试retry_async函数"""

    @pytest.mark.asyncio
    async def test_retry_async_success_first_attempt(self):
        """测试第一次尝试就成功"""
        call_count = 0

        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await retry_async(successful_func)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_async_success_after_retries(self):
        """测试重试后成功"""
        call_count = 0

        async def eventually_successful_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Timeout")
            return "success"

        config = RetryConfig(max_retries=3, initial_delay=0.01)
        result = await retry_async(eventually_successful_func, config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_async_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0

        async def always_failing_func():
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Timeout")

        config = RetryConfig(max_retries=2, initial_delay=0.01)

        with pytest.raises(asyncio.TimeoutError):
            await retry_async(always_failing_func, config)

        assert call_count == 3  # 初始尝试 + 2次重试

    @pytest.mark.asyncio
    async def test_retry_async_non_retryable_error(self):
        """测试不可重试的错误"""
        call_count = 0

        async def non_retryable_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        config = RetryConfig(max_retries=3)

        with pytest.raises(ValueError):
            await retry_async(non_retryable_func, config)

        assert call_count == 1  # 只尝试一次
