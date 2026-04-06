"""Test artifact store"""

import pytest
from loom.api import ArtifactStore, Artifact


class TestArtifactStore:
    """Test ArtifactStore"""

    def test_store_artifact(self):
        """Test store artifact"""
        store = ArtifactStore()
        artifact = Artifact(run_id="run_001", kind="patch", title="Fix")
        store.store(artifact)

        retrieved = store.get(artifact.artifact_id)
        assert retrieved is not None
        assert retrieved.title == "Fix"

    def test_list_by_run(self):
        """Test list by run"""
        store = ArtifactStore()
        a1 = Artifact(run_id="run_001", kind="patch", title="A1")
        a2 = Artifact(run_id="run_001", kind="report", title="A2")
        store.store(a1)
        store.store(a2)

        artifacts = store.list_by_run("run_001")
        assert len(artifacts) == 2

    def test_delete_artifact(self):
        """Test delete artifact"""
        store = ArtifactStore()
        artifact = Artifact(run_id="run_001", kind="text", title="Test")
        store.store(artifact)
        store.delete(artifact.artifact_id)

        retrieved = store.get(artifact.artifact_id)
        assert retrieved is None
