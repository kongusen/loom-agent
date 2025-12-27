"""
Loom 标准技能库

提供预构建的常用技能。
"""

from loom.stdlib.skills.base import Skill
from loom.stdlib.skills.calculator import CalculatorSkill
from loom.stdlib.skills.filesystem import FileSystemSkill

__all__ = [
    "Skill",
    "CalculatorSkill",
    "FileSystemSkill",
]
