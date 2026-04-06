"""Skill system - 参考 Claude Code skills

Skill 特性：
1. Markdown 格式，支持 frontmatter 元数据
2. 按需加载（lazy loading）
3. 支持参数替换
4. 支持 allowedTools 限制
5. 支持 whenToUse 匹配
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Skill:
    """Skill definition"""
    name: str
    description: str
    content: str  # Markdown content

    # Frontmatter fields
    when_to_use: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    argument_hint: str | None = None
    model: str | None = None
    user_invocable: bool = True

    # Metadata
    source: str = "user"  # user | plugin | bundled
    file_path: str | None = None

    def matches_task(self, task: str) -> bool:
        """Check if skill matches task description"""
        if not self.when_to_use:
            return False
        task_lower = task.lower()
        keywords = [kw.strip() for kw in self.when_to_use.lower().split(',')]
        return any(kw in task_lower for kw in keywords)


class SkillRegistry:
    """Skill registry with lazy loading"""

    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self._loaders: dict[str, Callable[[], Skill]] = {}

    def register(self, skill: Skill):
        """Register a skill"""
        self.skills[skill.name] = skill

    def register_lazy(self, name: str, loader: Callable[[], Skill]):
        """Register a lazy-loaded skill"""
        self._loaders[name] = loader

    def unregister(self, name: str):
        """Remove a skill or lazy loader."""
        self.skills.pop(name, None)
        self._loaders.pop(name, None)

    def get(self, name: str) -> Skill | None:
        """Get skill by name (lazy load if needed)"""
        if name in self.skills:
            return self.skills[name]

        if name in self._loaders:
            skill = self._loaders[name]()
            self.skills[name] = skill
            del self._loaders[name]
            return skill

        return None

    def match_task(self, task: str) -> list[Skill]:
        """Find skills matching task"""
        matched = []
        for name in list(self.skills.keys()) + list(self._loaders.keys()):
            skill = self.get(name)
            if skill and skill.matches_task(task):
                matched.append(skill)
        return matched

    def list_skills(self) -> list[str]:
        """List all skill names"""
        return list(self.skills.keys()) + list(self._loaders.keys())


class SkillLoader:
    """Load skills from filesystem"""

    @staticmethod
    def parse_frontmatter(content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown (simple parser, no external deps)"""
        if not content.startswith('---\n'):
            return {}, content

        parts = content.split('---\n', 2)
        if len(parts) < 3:
            return {}, content

        # Simple YAML parser for basic key: value and key: [list] syntax
        frontmatter = {}
        for line in parts[1].split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Handle lists: [item1, item2] or comma-separated
            if value.startswith('[') and value.endswith(']'):
                items = value[1:-1].split(',')
                frontmatter[key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
            # Handle booleans
            elif value.lower() in ('true', 'false'):
                frontmatter[key] = value.lower() == 'true'
            # Handle numbers
            elif value.isdigit():
                frontmatter[key] = int(value)
            # Handle strings (remove quotes if present)
            else:
                frontmatter[key] = value.strip('"').strip("'")

        body = parts[2]
        return frontmatter, body

    @staticmethod
    def load_from_file(path: Path) -> Skill:
        """Load skill from markdown file"""
        content = path.read_text(encoding='utf-8')
        frontmatter, body = SkillLoader.parse_frontmatter(content)

        name = frontmatter.get('name', path.stem)
        description = frontmatter.get('description', '')

        return Skill(
            name=name,
            description=description,
            content=body,
            when_to_use=frontmatter.get('whenToUse'),
            allowed_tools=frontmatter.get('allowedTools', []),
            argument_hint=frontmatter.get('argumentHint'),
            model=frontmatter.get('model'),
            user_invocable=frontmatter.get('userInvocable', True),
            source='user',
            file_path=str(path),
        )

    @staticmethod
    def load_from_directory(directory: Path, registry: SkillRegistry):
        """Load all skills from directory (lazy)"""
        if not directory.exists():
            return

        for skill_file in directory.glob('**/*.md'):
            # Skip README files
            if skill_file.name.upper() == 'README.MD':
                continue

            skill_name = skill_file.stem
            # Register lazy loader
            registry.register_lazy(
                skill_name,
                lambda p=skill_file: SkillLoader.load_from_file(p)
            )
