"""
配置模型

使用 Pydantic 定义 YAML 配置的数据结构。
"""

from typing import Any

from pydantic import BaseModel, Field

from loom.config.fractal import FractalConfig


class ControlConfig(BaseModel):
    """控制配置"""
    budget: int | None = Field(None, description="Token 预算")
    depth: int | None = Field(None, description="最大深度")
    hitl: list[str] | None = Field(None, description="人工介入模式")


class AgentConfig(BaseModel):
    """Agent 配置"""
    name: str = Field(..., description="Agent 名称")
    type: str | None = Field(None, description="预构建 Agent 类型")
    role: str | None = Field(None, description="自定义角色")
    skills: list[str] | None = Field(None, description="技能列表")
    config: dict[str, Any] | None = Field(None, description="额外配置")
    fractal: FractalConfig | None = Field(None, description="分型配置")


class CrewConfig(BaseModel):
    """Crew 配置"""
    name: str = Field(..., description="Crew 名称")
    type: str | None = Field(None, description="预构建 Crew 类型")
    agents: list[str] = Field(..., description="Agent 名称列表")
    config: dict[str, Any] | None = Field(None, description="额外配置")


class LoomConfig(BaseModel):
    """完整的 Loom 配置"""
    version: str = Field("1.0", description="配置版本")
    control: ControlConfig | None = Field(None, description="控制配置")
    agents: list[AgentConfig] | None = Field(None, description="Agent 列表")
    crews: list[CrewConfig] | None = Field(None, description="Crew 列表")
