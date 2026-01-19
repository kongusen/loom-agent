"""
API测试配置

提供真实API测试所需的配置和工具函数。
遵循最简实现原则：只提供必要的配置管理。
"""

import os
from pathlib import Path

import pytest


def _load_env_file() -> None:
    """
    加载.env文件到环境变量

    遵循最简实现原则：手动解析.env文件，无需额外依赖。
    """
    # 查找.env文件（在项目根目录）
    current_dir = Path(__file__).parent.parent  # tests/ -> project root
    env_file = current_dir / ".env"

    if not env_file.exists():
        return

    # 解析.env文件
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue

            # 解析 KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # 只在环境变量不存在时设置（环境变量优先）
                if key and key not in os.environ:
                    os.environ[key] = value


# 在模块加载时加载.env文件
_load_env_file()


class APITestConfig:
    """API测试配置管理"""

    def __init__(self):
        """从环境变量加载配置"""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.enable_real_tests = os.getenv("ENABLE_REAL_API_TESTS", "false").lower() == "true"
        self.timeout = int(os.getenv("API_TEST_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("API_MAX_RETRIES", "3"))

    @property
    def has_api_key(self) -> bool:
        """检查是否配置了API密钥"""
        return bool(self.api_key and self.api_key != "your-api-key-here")

    @property
    def should_run_real_tests(self) -> bool:
        """判断是否应该运行真实API测试"""
        return self.enable_real_tests and self.has_api_key


# 全局配置实例
api_config = APITestConfig()


def requires_real_api(func):
    """
    装饰器：标记需要真实API的测试

    如果未启用真实API测试，将跳过该测试。
    """
    return pytest.mark.skipif(
        not api_config.should_run_real_tests,
        reason="Real API tests disabled. Set ENABLE_REAL_API_TESTS=true to enable.",
    )(func)


def get_openai_config() -> dict:
    """
    获取OpenAI配置字典

    Returns:
        包含API配置的字典
    """
    return {
        "api_key": api_config.api_key,
        "model": api_config.model,
        "base_url": api_config.base_url,
        "timeout": api_config.timeout,
        "max_retries": api_config.max_retries,
    }


def get_embedding_config() -> dict:
    """
    获取Embedding配置字典

    Returns:
        包含Embedding配置的字典
    """
    return {
        "api_key": api_config.api_key,
        "model": api_config.embedding_model,
        "base_url": api_config.base_url,
        "timeout": api_config.timeout,
    }
