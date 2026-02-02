"""
Tests for Fractal Utilities

v0.5.0: estimate_task_complexity 与 should_use_fractal 已移除，
分形决策由 LLM 通过 delegate_task 等工具自主完成。
本文件保留占位，原测试已删除。
"""

import pytest


class TestFractalUtilsRemoved:
    """占位：原 estimate_task_complexity / should_use_fractal 测试已移除"""

    def test_utils_module_exists(self):
        """fractal.utils 模块仍可导入"""
        import loom.fractal.utils as utils  # noqa: F401

        assert utils is not None
