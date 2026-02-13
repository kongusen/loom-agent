"""
API Module Init Tests

测试loom.api模块的导入和导出
"""


def test_api_module_imports():
    """测试API模块可以正确导入"""
    from loom.api import (
        ChangeType,
        FractalEvent,
        FractalStreamAPI,
        OutputStrategy,
        StreamAPI,
        VersionAPI,
        VersionInfo,
        get_version,
        get_version_info,
    )

    assert FractalEvent is not None
    assert FractalStreamAPI is not None
    assert OutputStrategy is not None
    assert StreamAPI is not None
    assert VersionAPI is not None
    assert VersionInfo is not None
    assert ChangeType is not None
    assert get_version is not None
    assert get_version_info is not None


def test_api_module_version():
    """测试API模块版本"""
    import loom.api

    assert hasattr(loom.api, "__version__")
    assert isinstance(loom.api.__version__, str)
    assert len(loom.api.__version__) > 0


def test_api_module_all():
    """测试__all__导出列表"""
    import loom.api

    assert hasattr(loom.api, "__all__")
    assert isinstance(loom.api.__all__, list)
    assert len(loom.api.__all__) > 0
