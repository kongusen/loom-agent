"""Skill system - 参考 Claude Code skills

Skill 特性：
1. Markdown 格式，支持 frontmatter 元数据
2. 按需加载（lazy loading）
3. 支持参数替换
4. 支持 allowedTools 限制
5. 支持 whenToUse 匹配
6. Agent 框架特性：effort, agent, context, paths
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Import hooks system
if TYPE_CHECKING:
    from .hooks import SkillHooks, parse_hooks_from_frontmatter
else:
    try:
        from .hooks import SkillHooks, parse_hooks_from_frontmatter
    except ImportError:
        SkillHooks = None  # type: ignore
        parse_hooks_from_frontmatter = None  # type: ignore


@dataclass
class ShellConfig:
    """Shell configuration for inline execution"""
    command: str = "/bin/bash"
    args: list[str] = field(default_factory=lambda: ["-c"])
    env: dict[str, str] = field(default_factory=dict)
    timeout: int = 30  # seconds


def get_effort_token_limit(effort: int | None) -> int:
    """Convert effort level to token limit

    Args:
        effort: Effort level (1-5) or None

    Returns:
        Token limit for the effort level
    """
    if effort is None:
        return 4000  # Default

    effort_map = {
        1: 1000,    # 简单任务
        2: 2000,    # 中等任务
        3: 4000,    # 复杂任务（默认）
        4: 8000,    # 困难任务
        5: 16000,   # 极其复杂任务
    }
    return effort_map.get(effort, 4000)


def estimate_skill_tokens(skill: 'Skill', load_content: bool = False) -> int:
    """Estimate token consumption for a skill

    Args:
        skill: Skill object
        load_content: Whether to load full content (default: only frontmatter)

    Returns:
        Estimated token count
    """
    if not load_content:
        # Only estimate frontmatter
        text = f"{skill.name} {skill.description}"
        if skill.when_to_use:
            text += f" {skill.when_to_use}"
        if skill.argument_hint:
            text += f" {skill.argument_hint}"
        # Rough estimation: ~1.3 tokens per word
        return int(len(text.split()) * 1.3)
    else:
        # Estimate full content
        full_text = f"{skill.name} {skill.description} {skill.content}"
        return int(len(full_text.split()) * 1.3)


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

    # Agent framework features (P0)
    effort: int | None = None  # 1-5, controls token budget
    agent: str | None = None  # general-purpose, code-expert, debug-assistant
    context: str = "inline"  # inline | fork | isolated

    # Advanced features (P1)
    paths: list[str] | None = None  # [src/**, tests/**] - path restrictions
    version: str | None = None  # 1.0.0 - version control
    hooks: 'SkillHooks | None' = None  # Lifecycle hooks

    # Sprint 3 features (P2)
    shell: 'ShellConfig | None' = None  # Shell configuration

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
        # Also supports nested objects with indentation
        frontmatter: dict[str, Any] = {}
        lines = parts[1].split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped or stripped.startswith('#'):
                i += 1
                continue

            if ':' not in stripped:
                i += 1
                continue

            # Get indentation level
            indent = len(line) - len(line.lstrip())

            key, value = stripped.split(':', 1)
            key = key.strip()
            value = value.strip()

            # Check if this is a nested object (value is empty and next line is indented)
            if not value and i + 1 < len(lines):
                next_line = lines[i + 1]
                next_indent = len(next_line) - len(next_line.lstrip())

                if next_indent > indent:
                    # Parse nested object
                    nested: dict[str, Any] = {}
                    i += 1

                    while i < len(lines):
                        nested_line = lines[i]
                        nested_stripped = nested_line.strip()
                        nested_indent = len(nested_line) - len(nested_line.lstrip())

                        if nested_indent <= indent:
                            # Back to parent level
                            break

                        if not nested_stripped or nested_stripped.startswith('#'):
                            i += 1
                            continue

                        if ':' in nested_stripped:
                            nested_key, nested_value = nested_stripped.split(':', 1)
                            nested_key = nested_key.strip()
                            nested_value = nested_value.strip()

                            # Parse nested value types
                            if not nested_value and i + 1 < len(lines):
                                # Check for deeper nesting (e.g., env: with sub-keys)
                                deeper_line = lines[i + 1]
                                deeper_indent = len(deeper_line) - len(deeper_line.lstrip())

                                if deeper_indent > nested_indent:
                                    # Parse deeper nested object
                                    deeper_nested: dict[str, Any] = {}
                                    i += 1

                                    while i < len(lines):
                                        deeper_line = lines[i]
                                        deeper_stripped = deeper_line.strip()
                                        deeper_indent_level = len(deeper_line) - len(deeper_line.lstrip())

                                        if deeper_indent_level <= nested_indent:
                                            # Back to parent level
                                            break

                                        if not deeper_stripped or deeper_stripped.startswith('#'):
                                            i += 1
                                            continue

                                        if ':' in deeper_stripped:
                                            deeper_key, deeper_value = deeper_stripped.split(':', 1)
                                            deeper_key = deeper_key.strip()
                                            deeper_value = deeper_value.strip()

                                            # Parse deeper value types
                                            if deeper_value.startswith('[') and deeper_value.endswith(']'):
                                                items = deeper_value[1:-1].split(',')
                                                deeper_nested[deeper_key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                                            elif deeper_value.lower() in ('true', 'false'):
                                                deeper_nested[deeper_key] = deeper_value.lower() == 'true'
                                            elif deeper_value.isdigit():
                                                deeper_nested[deeper_key] = int(deeper_value)
                                            else:
                                                deeper_nested[deeper_key] = deeper_value.strip('"').strip("'")

                                        i += 1

                                    nested[nested_key] = deeper_nested
                                    continue

                            if nested_value.startswith('[') and nested_value.endswith(']'):
                                # List
                                items = nested_value[1:-1].split(',')
                                nested[nested_key] = [item.strip().strip('"').strip("'") for item in items if item.strip()]
                            elif nested_value.lower() in ('true', 'false'):
                                # Boolean
                                nested[nested_key] = nested_value.lower() == 'true'
                            elif nested_value.isdigit():
                                # Integer
                                nested[nested_key] = int(nested_value)
                            else:
                                # String
                                nested[nested_key] = nested_value.strip('"').strip("'")

                        i += 1

                    frontmatter[key] = nested
                    continue

            # Handle lists: [item1, item2]
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

            i += 1

        body = parts[2]
        return frontmatter, body

    @staticmethod
    def load_from_file(path: Path) -> Skill:
        """Load skill from markdown file"""
        content = path.read_text(encoding='utf-8')
        frontmatter, body = SkillLoader.parse_frontmatter(content)

        name = frontmatter.get('name', path.stem)
        description = frontmatter.get('description', '')

        # Parse hooks if available
        hooks = None
        if parse_hooks_from_frontmatter is not None:
            hooks = parse_hooks_from_frontmatter(frontmatter)

        # Parse shell config if available
        shell = None
        if 'shell' in frontmatter and isinstance(frontmatter['shell'], dict):
            shell_data = frontmatter['shell']
            shell = ShellConfig(
                command=shell_data.get('command', '/bin/bash'),
                args=shell_data.get('args', ['-c']),
                env=shell_data.get('env', {}),
                timeout=shell_data.get('timeout', 30),
            )

        return Skill(
            name=name,
            description=description,
            content=body,
            when_to_use=frontmatter.get('whenToUse'),
            allowed_tools=frontmatter.get('allowedTools', []),
            argument_hint=frontmatter.get('argumentHint'),
            model=frontmatter.get('model'),
            user_invocable=frontmatter.get('userInvocable', True),
            # Agent framework features
            effort=frontmatter.get('effort'),
            agent=frontmatter.get('agent'),
            context=frontmatter.get('context', 'inline'),
            paths=frontmatter.get('paths'),
            version=frontmatter.get('version'),
            hooks=hooks,
            shell=shell,
            # Metadata
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
                lambda p=skill_file: SkillLoader.load_from_file(p)  # type: ignore[misc]
            )
