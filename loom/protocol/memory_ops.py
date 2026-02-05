"""
记忆操作协议 (Memory Operations Protocol)

提供标准化的记忆操作接口，统一记忆系统的操作语义。

基于 A1 公理（统一接口公理）和 A4 公理（记忆层次公理）
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryOperation(StrEnum):
    """
    记忆操作类型

    定义所有支持的记忆操作
    """

    STORE = "store"  # 存储记忆
    RETRIEVE = "retrieve"  # 检索记忆
    UPDATE = "update"  # 更新记忆
    DELETE = "delete"  # 删除记忆
    SEARCH = "search"  # 搜索记忆
    COMPRESS = "compress"  # 压缩记忆


class MemoryRequest(BaseModel):
    """
    记忆操作请求

    标准化的记忆操作请求格式
    """

    operation: MemoryOperation = Field(..., description="操作类型")
    layer: str = Field(..., description="目标记忆层级 (L1/L2/L3/L4)")
    key: str | None = Field(None, description="记忆键（用于检索、更新、删除）")
    content: Any | None = Field(None, description="记忆内容（用于存储、更新）")
    query: str | None = Field(None, description="搜索查询（用于搜索操作）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        """Pydantic 配置"""

        use_enum_values = True


class MemoryResponse(BaseModel):
    """
    记忆操作响应

    标准化的记忆操作响应格式
    """

    success: bool = Field(..., description="操作是否成功")
    data: Any | None = Field(None, description="返回的数据")
    error: str | None = Field(None, description="错误信息（如果失败）")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")

    class Config:
        """Pydantic 配置"""

        arbitrary_types_allowed = True
