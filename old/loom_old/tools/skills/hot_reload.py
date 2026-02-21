"""
Skill Hot Reload - 热更新管理器

支持 Skills 的实时更新：
1. 文件监听 - 检测 SKILL.md 变更
2. 版本追踪 - 基于内容 hash
3. 事件通知 - 通知已激活的 Agent
"""

import asyncio
import contextlib
import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from loom.events import EventBus

    from .registry import SkillRegistry


@dataclass
class SkillVersion:
    """Skill 版本信息"""

    skill_id: str
    content_hash: str  # SHA256 of SKILL.md
    loaded_at: datetime
    file_path: Path | None = None

    @classmethod
    def from_file(cls, skill_id: str, file_path: Path) -> "SkillVersion":
        """从文件创建版本信息"""
        content = file_path.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return cls(
            skill_id=skill_id,
            content_hash=content_hash,
            loaded_at=datetime.now(),
            file_path=file_path,
        )


@dataclass
class SkillChangeEvent:
    """Skill 变更事件"""

    skill_id: str
    change_type: str  # "created" | "modified" | "deleted"
    old_version: SkillVersion | None
    new_version: SkillVersion | None
    timestamp: datetime = field(default_factory=datetime.now)


class FileWatcher:
    """
    文件监听器 - 轮询模式

    使用轮询而非 watchdog，减少依赖且跨平台兼容。
    """

    def __init__(
        self,
        watch_dirs: list[Path],
        poll_interval: float = 1.0,
        file_pattern: str = "SKILL.md",
    ):
        self.watch_dirs = [Path(d) for d in watch_dirs]
        self.poll_interval = poll_interval
        self.file_pattern = file_pattern
        self._file_mtimes: dict[Path, float] = {}
        self._running = False
        self._task: asyncio.Task | None = None
        self.on_change: Callable[[Path, str], None] | None = None

    async def start(self) -> None:
        """启动文件监听"""
        if self._running:
            return
        self._running = True
        self._scan_initial()
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) -> None:
        """停止文件监听"""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    def _scan_initial(self) -> None:
        """初始扫描，记录所有文件的修改时间"""
        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            for skill_dir in watch_dir.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / self.file_pattern
                    if skill_file.exists():
                        self._file_mtimes[skill_file] = skill_file.stat().st_mtime

    async def _poll_loop(self) -> None:
        """轮询循环"""
        while self._running:
            await asyncio.sleep(self.poll_interval)
            await self._check_changes()

    async def _check_changes(self) -> None:
        """检查文件变更"""
        current_files: set[Path] = set()

        for watch_dir in self.watch_dirs:
            if not watch_dir.exists():
                continue
            for skill_dir in watch_dir.iterdir():
                if not skill_dir.is_dir():
                    continue
                skill_file = skill_dir / self.file_pattern
                if not skill_file.exists():
                    continue

                current_files.add(skill_file)
                mtime = skill_file.stat().st_mtime
                old_mtime = self._file_mtimes.get(skill_file)

                if old_mtime is None:
                    # 新文件
                    self._file_mtimes[skill_file] = mtime
                    if self.on_change:
                        self.on_change(skill_file, "created")
                elif mtime > old_mtime:
                    # 文件修改
                    self._file_mtimes[skill_file] = mtime
                    if self.on_change:
                        self.on_change(skill_file, "modified")

        # 检查删除的文件
        deleted = set(self._file_mtimes.keys()) - current_files
        for skill_file in deleted:
            del self._file_mtimes[skill_file]
            if self.on_change:
                self.on_change(skill_file, "deleted")


class HotReloadManager:
    """
    热更新管理器

    协调文件监听、版本追踪和事件通知。
    """

    def __init__(
        self,
        registry: "SkillRegistry",
        event_bus: "EventBus | None" = None,
        watch_dirs: list[Path] | None = None,
        poll_interval: float = 1.0,
    ):
        self.registry = registry
        self.event_bus = event_bus
        self.watch_dirs = watch_dirs or []
        self._versions: dict[str, SkillVersion] = {}
        self._watcher: FileWatcher | None = None
        self._poll_interval = poll_interval
        self._running = False
        self._callbacks: list[Callable[[SkillChangeEvent], Any]] = []

    async def start(self) -> None:
        """启动热更新监听"""
        if self._running:
            return
        if not self.watch_dirs:
            return

        self._running = True
        self._watcher = FileWatcher(
            watch_dirs=self.watch_dirs,
            poll_interval=self._poll_interval,
        )
        self._watcher.on_change = self._handle_file_change
        await self._watcher.start()

    async def stop(self) -> None:
        """停止热更新监听"""
        self._running = False
        if self._watcher:
            await self._watcher.stop()
            self._watcher = None

    def on_skill_change(self, callback: Callable[[SkillChangeEvent], Any]) -> None:
        """注册变更回调"""
        self._callbacks.append(callback)

    def _handle_file_change(self, file_path: Path, change_type: str) -> None:
        """处理文件变更（同步入口，内部调度异步）"""
        asyncio.create_task(self._process_change(file_path, change_type))

    async def _process_change(self, file_path: Path, change_type: str) -> None:
        """处理文件变更（异步）"""
        skill_id = file_path.parent.name
        old_version = self._versions.get(skill_id)
        new_version: SkillVersion | None = None

        if change_type == "deleted":
            # 删除版本记录
            if skill_id in self._versions:
                del self._versions[skill_id]
        else:
            # 创建新版本
            new_version = SkillVersion.from_file(skill_id, file_path)

            # 检查内容是否真的变了
            if old_version and old_version.content_hash == new_version.content_hash:
                return  # 内容未变，忽略

            self._versions[skill_id] = new_version

        # 清除 registry 缓存
        self.registry.clear_cache()

        # 构建变更事件
        event = SkillChangeEvent(
            skill_id=skill_id,
            change_type=change_type,
            old_version=old_version,
            new_version=new_version,
        )

        # 通知回调
        for callback in self._callbacks:
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Callback error: {e}")

        # 发布事件总线
        if self.event_bus:
            from loom.runtime.task import Task

            task = Task(
                action="skill.changed",
                parameters={
                    "skill_id": skill_id,
                    "change_type": change_type,
                    "old_hash": old_version.content_hash if old_version else None,
                    "new_hash": new_version.content_hash if new_version else None,
                },
            )
            await self.event_bus.publish(task, wait_result=False)

    def get_version(self, skill_id: str) -> SkillVersion | None:
        """获取 Skill 当前版本"""
        return self._versions.get(skill_id)

    def get_all_versions(self) -> dict[str, SkillVersion]:
        """获取所有版本信息"""
        return self._versions.copy()

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running
