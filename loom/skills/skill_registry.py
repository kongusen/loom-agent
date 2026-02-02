"""
Skill Registry - 运行时 Skill 入口（兼容层）

v0.5.0: 两套 SkillRegistry 已合并为 loom.skills.registry.SkillRegistry。
本模块仅保留 skill_market 单例与向后兼容导入。
"""

from .registry import SkillRegistry

# 全局 Skills 市场实例（统一 SkillRegistry，支持 register_skill + Loaders）
skill_market = SkillRegistry()
