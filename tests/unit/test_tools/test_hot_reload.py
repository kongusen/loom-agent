"""
Tests for Skill Hot Reload

测试热更新管理器的核心功能：
- SkillVersion 版本追踪
- FileWatcher 文件监听
- HotReloadManager 变更通知
"""

import asyncio

import pytest

from loom.tools.skills.hot_reload import (
    FileWatcher,
    HotReloadManager,
    SkillChangeEvent,
    SkillVersion,
)
from loom.tools.skills.registry import SkillRegistry


class TestSkillVersion:
    """测试 SkillVersion 数据模型"""

    def test_from_file(self, tmp_path):
        """测试从文件创建版本"""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Test Skill\nSome instructions")

        version = SkillVersion.from_file("test_skill", skill_file)

        assert version.skill_id == "test_skill"
        assert version.content_hash is not None
        assert len(version.content_hash) == 16
        assert version.file_path == skill_file

    def test_hash_changes_with_content(self, tmp_path):
        """测试内容变更时 hash 变化"""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"

        skill_file.write_text("Version 1")
        v1 = SkillVersion.from_file("test_skill", skill_file)

        skill_file.write_text("Version 2")
        v2 = SkillVersion.from_file("test_skill", skill_file)

        assert v1.content_hash != v2.content_hash

    def test_same_content_same_hash(self, tmp_path):
        """测试相同内容产生相同 hash"""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("Same content")

        v1 = SkillVersion.from_file("test_skill", skill_file)
        v2 = SkillVersion.from_file("test_skill", skill_file)

        assert v1.content_hash == v2.content_hash


class TestFileWatcher:
    """测试 FileWatcher 文件监听器"""

    def test_init(self, tmp_path):
        """测试初始化"""
        watcher = FileWatcher([tmp_path], poll_interval=0.1)
        assert watcher.watch_dirs == [tmp_path]
        assert watcher.poll_interval == 0.1
        assert not watcher._running

    @pytest.mark.asyncio
    async def test_start_stop(self, tmp_path):
        """测试启动和停止"""
        watcher = FileWatcher([tmp_path], poll_interval=0.1)

        await watcher.start()
        assert watcher._running

        await watcher.stop()
        assert not watcher._running

    @pytest.mark.asyncio
    async def test_detect_file_creation(self, tmp_path):
        """测试检测文件创建"""
        changes = []

        def on_change(path, change_type):
            changes.append((path, change_type))

        watcher = FileWatcher([tmp_path], poll_interval=0.1)
        watcher.on_change = on_change
        await watcher.start()

        # 创建新 skill
        skill_dir = tmp_path / "new_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("New skill")

        await asyncio.sleep(0.2)
        await watcher.stop()

        assert len(changes) == 1
        assert changes[0][1] == "created"


class TestHotReloadManager:
    """测试 HotReloadManager"""

    @pytest.fixture
    def registry(self):
        """创建 SkillRegistry"""
        return SkillRegistry()

    def test_init(self, registry, tmp_path):
        """测试初始化"""
        manager = HotReloadManager(
            registry=registry,
            watch_dirs=[tmp_path],
        )
        assert manager.registry is registry
        assert not manager.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self, registry, tmp_path):
        """测试启动和停止"""
        manager = HotReloadManager(
            registry=registry,
            watch_dirs=[tmp_path],
            poll_interval=0.1,
        )

        await manager.start()
        assert manager.is_running

        await manager.stop()
        assert not manager.is_running

    @pytest.mark.asyncio
    async def test_callback_on_change(self, registry, tmp_path):
        """测试变更回调"""
        events = []

        def on_change(event: SkillChangeEvent):
            events.append(event)

        # 先创建 skill
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("Initial content")

        manager = HotReloadManager(
            registry=registry,
            watch_dirs=[tmp_path],
            poll_interval=0.1,
        )
        manager.on_skill_change(on_change)
        await manager.start()

        # 修改文件
        await asyncio.sleep(0.15)
        skill_file.write_text("Modified content")
        await asyncio.sleep(0.2)

        await manager.stop()

        assert len(events) >= 1
        assert events[-1].skill_id == "test_skill"
        assert events[-1].change_type == "modified"
