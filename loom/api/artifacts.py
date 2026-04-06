"""Artifact storage for Loom runtime"""

from typing import Optional
from .models import Artifact


class ArtifactStore:
    """Artifact storage"""

    def __init__(self):
        self._artifacts: dict[str, Artifact] = {}
        self._by_run: dict[str, list[str]] = {}

    def store(self, artifact: Artifact) -> None:
        """Store artifact"""
        self._artifacts[artifact.artifact_id] = artifact

        if artifact.run_id not in self._by_run:
            self._by_run[artifact.run_id] = []
        if artifact.artifact_id not in self._by_run[artifact.run_id]:
            self._by_run[artifact.run_id].append(artifact.artifact_id)

    def get(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID"""
        return self._artifacts.get(artifact_id)

    def list_by_run(self, run_id: str) -> list[Artifact]:
        """List artifacts by run ID"""
        artifact_ids = self._by_run.get(run_id, [])
        return [self._artifacts[aid] for aid in artifact_ids if aid in self._artifacts]

    def delete(self, artifact_id: str) -> None:
        """Delete artifact"""
        if artifact_id in self._artifacts:
            artifact = self._artifacts[artifact_id]
            del self._artifacts[artifact_id]

            if artifact.run_id in self._by_run:
                self._by_run[artifact.run_id].remove(artifact_id)
