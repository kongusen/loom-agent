import pytest
from loom.patterns.crew import Crew
from loom.core.runnable import RunnableSequence
from tests.unit.patterns.test_composition import AddOne, MultiplyByTwo

@pytest.mark.asyncio
async def test_crew_basic_execution():
    """Verify Crew executes workflow."""
    workflow = RunnableSequence([AddOne(), MultiplyByTwo()])
    crew = Crew(workflow=workflow, name="MathCrew")
    
    # (5 + 1) * 2 = 12
    result = await crew.invoke(5)
    assert result == 12

@pytest.mark.asyncio
async def test_crew_attributes():
    """Verify Crew retains attributes."""
    crew = Crew(workflow=AddOne(), name="TestCrew", memory=None)
    assert crew.name == "TestCrew"
    assert crew.workflow is not None
