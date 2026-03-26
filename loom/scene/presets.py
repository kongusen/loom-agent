"""Preset scene packages."""

from ..types.scene import ScenePackage


def create_code_scene() -> ScenePackage:
    """σ_code: bash, git, file ops"""
    return ScenePackage(
        id="code",
        tools=["bash", "read_file", "write_file", "git"],
        constraints={"network": False, "write_outside_repo": False},
        memory_scope=["./"],
    )


def create_research_scene() -> ScenePackage:
    """σ_research: web_search, web_fetch, read"""
    return ScenePackage(
        id="research",
        tools=["web_search", "web_fetch", "read_file"],
        constraints={"write": False, "network_write": False},
        memory_scope=[],
    )
