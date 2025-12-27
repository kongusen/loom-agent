"""
配置模型

使用 Pydantic 定义 YAML 配置的数据结构。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ControlConfig(BaseModel):
    """控制配置"""
    budget: Optional[int] = Field(None, description="Token 预算")
    depth: Optional[int] = Field(None, description="最大深度")
    hitl: Optional[List[str]] = Field(None, description="人工介入模式")


class AgentConfig(BaseModel):
    """Agent 配置"""
    name: str = Field(..., description="Agent 名称")
    type: Optional[str] = Field(None, description="预构建 Agent 类型")
    role: Optional[str] = Field(None, description="自定义角色")
    skills: Optional[List[str]] = Field(None, description="技能列表")
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")


class CrewConfig(BaseModel):
    """Crew 配置"""
    name: str = Field(..., description="Crew 名称")
    type: Optional[str] = Field(None, description="预构建 Crew 类型")
    agents: List[str] = Field(..., description="Agent 名称列表")
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")


class LoomConfig(BaseModel):
    """完整的 Loom 配置"""
    version: str = Field("1.0", description="配置版本")
    control: Optional[ControlConfig] = Field(None, description="控制配置")
    agents: Optional[List[AgentConfig]] = Field(None, description="Agent 列表")
    crews: Optional[List[CrewConfig]] = Field(None, description="Crew 列表")
