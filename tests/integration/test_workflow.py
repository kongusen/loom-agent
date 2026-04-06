"""Integration tests"""

import pytest
from loom.api import (
    AgentRuntime,
    AgentProfile,
    AgentConfig,
    LLMConfig,
    RunState,
)


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test complete workflow"""
        # Create config
        config = AgentConfig(
            name="test",
            llm=LLMConfig(model="gpt-4")
        )

        # Create profile
        profile = AgentProfile(
            id="test",
            name="Test",
            config=config
        )

        # Create runtime
        runtime = AgentRuntime(profile=profile)

        # Create session
        session = runtime.create_session()
        assert session.id

        # Create task
        task = session.create_task(goal="Test goal")
        assert task.id

        # Start run
        run = task.start()
        assert run.state == RunState.QUEUED

        # Wait for completion
        result = await run.wait()
        assert result.state == RunState.COMPLETED
