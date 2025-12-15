"""
Artifact Store - 上下文管理和存储系统

核心模式：子agent返回摘要，详细内容写文件

包含：
- SubAgentResult: 标准化的子agent返回格式
- ArtifactStore: 完整结果的文件系统存储
- 自动压缩和按需加载
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from loom.utils.token_counter import estimate_tokens


@dataclass
class SubAgentResult:
    """
    标准化的子agent返回格式

    核心理念：
    - summary: 1000-2000 token的摘要（必须返回给coordinator）
    - artifacts: 完整结果的文件路径（可选，自动存储）
    - metadata: 执行元数据（工具使用、token统计等）

    Example:
        ```python
        # Agent执行完成后
        result = SubAgentResult(
            agent_id="researcher1",
            task_id="task1",
            summary="找到了3个相关研究报告...",  # 简短摘要
            detailed_content="[完整的10页报告内容]",  # 自动存储到文件
            success=True,
            metadata={
                "tools_used": ["web_search", "web_fetch"],
                "token_count": 15000
            }
        )

        # Coordinator只看到摘要
        print(result.summary)  # "找到了3个相关研究报告..."

        # 需要时加载完整内容
        if coordinator.needs_detail("task1"):
            full_content = result.load_artifact(artifact_store)
        ```
    """

    agent_id: str  # 执行的 agent ID
    task_id: str  # 任务 ID
    summary: str  # 摘要（1000-2000 tokens）
    success: bool = True  # 是否成功
    error: Optional[str] = None  # 错误信息
    artifacts: List[str] = field(default_factory=list)  # artifact ID 列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 执行元数据
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        """验证摘要长度"""
        # 检查摘要 token 数
        summary_tokens = estimate_tokens(self.summary)
        if summary_tokens > 3000:  # 超过3000就警告
            # 截断摘要
            self.metadata["original_summary_tokens"] = summary_tokens
            self.metadata["summary_truncated"] = True
            # 简单截断：保留前2000 tokens对应的字符
            # 粗略估计：1 token ≈ 4 characters
            max_chars = 2000 * 4
            if len(self.summary) > max_chars:
                self.summary = self.summary[:max_chars] + "\n\n[摘要被截断，完整内容见 artifacts]"

    @classmethod
    def from_execution(
        cls,
        agent_id: str,
        task_id: str,
        summary: str,
        detailed_content: Optional[str] = None,
        artifact_store: Optional[ArtifactStore] = None,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SubAgentResult:
        """
        从执行结果创建 SubAgentResult

        如果 detailed_content 超过阈值，自动存储到 ArtifactStore

        Args:
            agent_id: Agent ID
            task_id: 任务 ID
            summary: 摘要
            detailed_content: 详细内容（可选）
            artifact_store: Artifact 存储（可选）
            success: 是否成功
            error: 错误信息
            metadata: 元数据

        Returns:
            SubAgentResult
        """
        artifacts = []

        # 如果有详细内容且超过阈值，存储到 artifact store
        if detailed_content and artifact_store:
            content_tokens = estimate_tokens(detailed_content)
            if content_tokens > 5000:  # 超过5K tokens就存储
                artifact_id = artifact_store.save(
                    content=detailed_content,
                    artifact_type="execution_result",
                    agent_id=agent_id,
                    task_id=task_id,
                    metadata=metadata or {},
                )
                artifacts.append(artifact_id)

        return cls(
            agent_id=agent_id,
            task_id=task_id,
            summary=summary,
            success=success,
            error=error,
            artifacts=artifacts,
            metadata=metadata or {},
        )

    def load_artifact(
        self, artifact_store: ArtifactStore, artifact_id: Optional[str] = None
    ) -> Optional[str]:
        """
        加载完整的 artifact 内容

        Args:
            artifact_store: Artifact 存储
            artifact_id: 指定的 artifact ID（可选，默认第一个）

        Returns:
            Artifact 内容（如果存在）
        """
        if not self.artifacts:
            return None

        aid = artifact_id or self.artifacts[0]
        return artifact_store.load(aid)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "summary": self.summary,
            "success": self.success,
            "error": self.error,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SubAgentResult:
        """从字典反序列化"""
        return cls(
            agent_id=data["agent_id"],
            task_id=data["task_id"],
            summary=data["summary"],
            success=data.get("success", True),
            error=data.get("error"),
            artifacts=data.get("artifacts", []),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


class ArtifactStore:
    """
    Artifact 存储系统

    特性：
    - 文件系统存储（支持大文件）
    - 内容寻址（基于hash去重）
    - 元数据索引
    - 自动清理（可选）

    存储结构：
    ```
    artifacts/
      ├── index.json              # 元数据索引
      ├── content/
      │   ├── abc123.txt          # 实际内容
      │   ├── def456.json
      │   └── ...
      └── metadata/
          ├── abc123.meta.json    # 元数据
          └── ...
    ```

    Example:
        ```python
        store = ArtifactStore(path="./crew_artifacts")

        # 存储
        artifact_id = store.save(
            content="大段文本...",
            artifact_type="research_report",
            agent_id="researcher1",
            task_id="task1"
        )

        # 加载
        content = store.load(artifact_id)

        # 查询
        artifacts = store.search(agent_id="researcher1")
        ```
    """

    def __init__(
        self,
        path: str = "./crew_artifacts",
        auto_cleanup: bool = False,
        max_age_days: int = 7,
    ):
        """
        初始化 Artifact 存储

        Args:
            path: 存储根目录
            auto_cleanup: 是否自动清理旧文件
            max_age_days: 文件最大保留天数（仅当 auto_cleanup=True）
        """
        self.path = Path(path)
        self.auto_cleanup = auto_cleanup
        self.max_age_days = max_age_days

        # 创建目录结构
        self.content_dir = self.path / "content"
        self.metadata_dir = self.path / "metadata"
        self.content_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        # 索引文件
        self.index_file = self.path / "index.json"
        self.index = self._load_index()

        # 如果启用自动清理
        if self.auto_cleanup:
            self._cleanup_old_artifacts()

    def save(
        self,
        content: str,
        artifact_type: str,
        agent_id: str,
        task_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        存储 artifact

        Args:
            content: 内容
            artifact_type: 类型（如 "research_report", "analysis"）
            agent_id: Agent ID
            task_id: 任务 ID
            metadata: 额外元数据

        Returns:
            artifact_id: 唯一标识符
        """
        # 生成 artifact ID（基于内容 hash）
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        artifact_id = f"{task_id}_{agent_id}_{content_hash}"

        # 检查是否已存在（去重）
        if artifact_id in self.index:
            return artifact_id

        # 存储内容
        content_path = self.content_dir / f"{artifact_id}.txt"
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(content)

        # 构建元数据
        artifact_metadata = {
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "agent_id": agent_id,
            "task_id": task_id,
            "content_path": str(content_path),
            "content_size": len(content),
            "token_count": estimate_tokens(content),
            "created_at": time.time(),
            "custom_metadata": metadata or {},
        }

        # 存储元数据
        metadata_path = self.metadata_dir / f"{artifact_id}.meta.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(artifact_metadata, f, indent=2, ensure_ascii=False)

        # 更新索引
        self.index[artifact_id] = artifact_metadata
        self._save_index()

        return artifact_id

    def load(self, artifact_id: str) -> Optional[str]:
        """
        加载 artifact 内容

        Args:
            artifact_id: Artifact ID

        Returns:
            内容字符串（如果存在）
        """
        if artifact_id not in self.index:
            return None

        content_path = self.index[artifact_id]["content_path"]
        if not os.path.exists(content_path):
            return None

        with open(content_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_metadata(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """获取 artifact 元数据"""
        return self.index.get(artifact_id)

    def search(
        self,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索 artifacts

        Args:
            agent_id: 按 agent ID 过滤
            task_id: 按任务 ID 过滤
            artifact_type: 按类型过滤

        Returns:
            匹配的 artifact 元数据列表
        """
        results = []
        for artifact_id, metadata in self.index.items():
            if agent_id and metadata["agent_id"] != agent_id:
                continue
            if task_id and metadata["task_id"] != task_id:
                continue
            if artifact_type and metadata["artifact_type"] != artifact_type:
                continue
            results.append(metadata)

        return results

    def delete(self, artifact_id: str) -> bool:
        """删除 artifact"""
        if artifact_id not in self.index:
            return False

        # 删除文件
        metadata = self.index[artifact_id]
        content_path = metadata["content_path"]
        if os.path.exists(content_path):
            os.remove(content_path)

        # 删除元数据文件
        metadata_path = self.metadata_dir / f"{artifact_id}.meta.json"
        if metadata_path.exists():
            metadata_path.unlink()

        # 从索引中删除
        del self.index[artifact_id]
        self._save_index()

        return True

    def clear_all(self) -> int:
        """清空所有 artifacts（返回删除数量）"""
        count = len(self.index)

        # 删除所有文件
        for artifact_id in list(self.index.keys()):
            self.delete(artifact_id)

        return count

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        total_size = 0
        total_tokens = 0
        type_counts: Dict[str, int] = {}

        for metadata in self.index.values():
            total_size += metadata.get("content_size", 0)
            total_tokens += metadata.get("token_count", 0)
            artifact_type = metadata.get("artifact_type", "unknown")
            type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1

        return {
            "total_artifacts": len(self.index),
            "total_size_bytes": total_size,
            "total_tokens": total_tokens,
            "types": type_counts,
            "storage_path": str(self.path),
        }

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """加载索引"""
        if not self.index_file.exists():
            return {}

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_index(self):
        """保存索引"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)

    def _cleanup_old_artifacts(self):
        """清理过期的 artifacts"""
        current_time = time.time()
        max_age_seconds = self.max_age_days * 24 * 3600

        to_delete = []
        for artifact_id, metadata in self.index.items():
            created_at = metadata.get("created_at", current_time)
            age = current_time - created_at
            if age > max_age_seconds:
                to_delete.append(artifact_id)

        for artifact_id in to_delete:
            self.delete(artifact_id)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"ArtifactStore("
            f"path={self.path}, "
            f"artifacts={stats['total_artifacts']}, "
            f"total_tokens={stats['total_tokens']:,})"
        )


__all__ = ["SubAgentResult", "ArtifactStore"]
