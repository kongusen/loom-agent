"""
Base Configuration - 基础配置类

提供所有配置类的基类，统一配置接口和验证规则。

设计原则：
1. 类型安全 - 使用 Pydantic 提供完整的类型检查
2. 验证完善 - 自动验证配置值的有效性
3. 易于序列化 - 支持字典和 JSON 格式转换
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class LoomBaseConfig(BaseModel):
    """
    Loom 配置基类

    所有配置类都应该继承此类，以获得统一的配置接口。

    特性：
    - 禁止额外字段（extra="forbid"）
    - 赋值时验证（validate_assignment=True）
    - 使用枚举值（use_enum_values=True）
    - 支持字典序列化/反序列化
    """

    model_config = ConfigDict(
        extra="forbid",  # 禁止额外字段，提高安全性
        validate_assignment=True,  # 赋值时验证
        use_enum_values=True,  # 使用枚举值而不是枚举对象
        arbitrary_types_allowed=True,  # 允许任意类型（用于自定义类）
    )

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            配置的字典表示，排除 None 值
        """
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoomBaseConfig":
        """
        从字典创建配置对象

        Args:
            data: 配置字典

        Returns:
            配置对象
        """
        return cls(**data)

    def to_json(self) -> str:
        """
        转换为 JSON 字符串

        Returns:
            JSON 格式的配置
        """
        return self.model_dump_json(exclude_none=True, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "LoomBaseConfig":
        """
        从 JSON 字符串创建配置对象

        Args:
            json_str: JSON 字符串

        Returns:
            配置对象
        """
        return cls.model_validate_json(json_str)
