"""
Version API - 版本信息管理

提供框架版本信息、变更日志和兼容性检查。
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """变更类型"""
    FEATURE = "feature"      # 新功能
    FIX = "fix"              # 修复
    BREAKING = "breaking"    # 破坏性变更
    DEPRECATION = "deprecation"  # 废弃
    PERFORMANCE = "performance"  # 性能优化
    DOCS = "docs"            # 文档


@dataclass
class ChangeLogEntry:
    """变更日志条目"""
    type: ChangeType
    description: str
    component: str = ""
    issue_id: str = ""


@dataclass
class VersionInfo:
    """版本信息"""
    major: int
    minor: int
    patch: int
    release_date: date | None = None
    codename: str = ""
    changes: list[ChangeLogEntry] = field(default_factory=list)

    @property
    def version_string(self) -> str:
        """版本字符串"""
        return f"{self.major}.{self.minor}.{self.patch}"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version_string,
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "release_date": self.release_date.isoformat() if self.release_date else None,
            "codename": self.codename,
            "changes": [
                {
                    "type": c.type.value,
                    "description": c.description,
                    "component": c.component,
                }
                for c in self.changes
            ],
        }


# 版本历史
VERSION_HISTORY: list[VersionInfo] = [
    VersionInfo(
        major=0, minor=5, patch=3,
        release_date=date(2025, 2, 7),
        codename="Fractal Stream",
        changes=[
            ChangeLogEntry(ChangeType.FEATURE, "FractalStreamAPI 分形流式观测", "loom.api"),
            ChangeLogEntry(ChangeType.FEATURE, "OutputStrategy 输出策略", "loom.api"),
            ChangeLogEntry(ChangeType.FEATURE, "FractalEvent 层级事件", "loom.api"),
            ChangeLogEntry(ChangeType.FEATURE, "Version API 版本管理", "loom.api"),
            ChangeLogEntry(ChangeType.DOCS, "Demo 11-14 高级示例", "examples"),
        ],
    ),
    VersionInfo(
        major=0, minor=5, patch=2,
        release_date=date(2025, 2, 5),
        codename="Tools Refactor",
        changes=[
            ChangeLogEntry(ChangeType.FEATURE, "Tools模块重构", "loom.tools"),
            ChangeLogEntry(ChangeType.FEATURE, "Skills热更新系统", "loom.skills"),
            ChangeLogEntry(ChangeType.FIX, "pip packaging配置修复", "packaging"),
        ],
    ),
    VersionInfo(
        major=0, minor=5, patch=1,
        release_date=date(2025, 2, 3),
        codename="Observability",
        changes=[
            ChangeLogEntry(ChangeType.FEATURE, "隐藏变量暴露", "loom.agent"),
            ChangeLogEntry(ChangeType.FEATURE, "可观测性改进", "loom.events"),
        ],
    ),
]


class VersionAPI:
    """版本管理API"""

    @staticmethod
    def get_current() -> VersionInfo:
        """获取当前版本"""
        return VERSION_HISTORY[0]

    @staticmethod
    def get_version_string() -> str:
        """获取版本字符串"""
        return VERSION_HISTORY[0].version_string

    @staticmethod
    def get_history() -> list[VersionInfo]:
        """获取版本历史"""
        return VERSION_HISTORY

    @staticmethod
    def get_changelog(version: str | None = None) -> list[ChangeLogEntry]:
        """获取变更日志"""
        if version is None:
            return VERSION_HISTORY[0].changes
        for v in VERSION_HISTORY:
            if v.version_string == version:
                return v.changes
        return []

    @staticmethod
    def check_compatibility(required: str) -> bool:
        """检查版本兼容性（语义化版本）"""
        current = VERSION_HISTORY[0]
        parts = required.split(".")
        req_major = int(parts[0])
        req_minor = int(parts[1]) if len(parts) > 1 else 0

        # 主版本必须匹配，次版本当前>=要求
        return current.major == req_major and current.minor >= req_minor


# 便捷函数
def get_version() -> str:
    """获取当前版本字符串"""
    return VersionAPI.get_version_string()


def get_version_info() -> dict[str, Any]:
    """获取当前版本详细信息"""
    return VersionAPI.get_current().to_dict()
