"""
Loom Capabilities - 统一的能力管理系统

基于优化方案（OPTIMIZATION_PLAN.md）第2.4节：CapabilityRegistry 门面设计

核心原则：
1. 门面模式 - 不创建新系统，复用现有组件
2. 统一发现 - 提供统一的能力发现接口
3. 依赖验证 - 验证 Skill 的工具依赖（新增功能）

职责：
- 统一管理 Tools 和 Skills
- 提供能力发现接口
- 验证依赖关系
- 内部复用 SandboxToolManager + SkillRegistry + SkillActivator
"""

from .registry import CapabilityRegistry, CapabilitySet, ValidationResult

__all__ = [
    "CapabilityRegistry",
    "CapabilitySet",
    "ValidationResult",
]
