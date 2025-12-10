"""
Loom Agent Crew System - Complete Demo

This example demonstrates the full capabilities of the loom-agent Crew system
for multi-agent collaboration, including:

1. Role-based agent specialization
2. Task orchestration with dependencies
3. Multiple execution modes (SEQUENTIAL, PARALLEL, CONDITIONAL, HIERARCHICAL)
4. Agent communication via MessageBus and SharedState
5. Task delegation using DelegateTool
6. Complex condition logic with ConditionBuilder

Run this example with:
    python examples/crew_demo.py
"""

import asyncio
from typing import Dict, Any

from loom.crew import (
    Crew,
    Role,
    Task,
    OrchestrationPlan,
    OrchestrationMode,
    ConditionBuilder,
    BUILTIN_ROLES,
)
from loom.llm.factory import LLMFactory


# ============================================================================
# Scenario 1: Code Review Workflow (SEQUENTIAL Mode)
# ============================================================================


async def scenario_1_code_review():
    """
    Scenario: Multi-agent code review workflow

    Flow:
    1. Researcher analyzes codebase structure
    2. Security Auditor performs security review
    3. Tech Writer documents findings

    Mode: SEQUENTIAL (tasks execute in order)
    """
    print("\n" + "="*80)
    print("SCENARIO 1: Code Review Workflow (Sequential)")
    print("="*80)

    # Create LLM (replace with your API key)
    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    # Define roles
    roles = [
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["security_auditor"],
        BUILTIN_ROLES["tech_writer"],
    ]

    # Create crew
    crew = Crew(roles=roles, llm=llm)

    # Define tasks with dependencies
    tasks = [
        Task(
            id="analyze_structure",
            description="Analyze codebase structure",
            prompt="""Analyze the authentication module structure in src/auth.py:

1. Identify key components and classes
2. Map data flow and dependencies
3. Note any architectural patterns used

Output your findings in a structured format.""",
            assigned_role="researcher",
            output_key="structure_analysis"
        ),
        Task(
            id="security_review",
            description="Security vulnerability assessment",
            prompt="""Based on the structure analysis, perform a security review:

1. Check for common vulnerabilities (OWASP Top 10)
2. Review authentication and authorization logic
3. Identify potential security risks
4. Provide recommendations

Use the structure analysis to guide your review.""",
            assigned_role="security_auditor",
            dependencies=["analyze_structure"],
            output_key="security_findings"
        ),
        Task(
            id="document_findings",
            description="Document review findings",
            prompt="""Create comprehensive documentation of the code review:

1. Summary of architecture (from structure analysis)
2. Security findings and recommendations
3. Action items for developers

Format as markdown documentation.""",
            assigned_role="tech_writer",
            dependencies=["analyze_structure", "security_review"]
        ),
    ]

    # Create and execute plan
    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.SEQUENTIAL
    )

    print("\n🚀 Executing code review workflow...")
    results = await crew.kickoff(plan)

    print("\n📊 Results:")
    for task_id, result in results.items():
        print(f"\n{task_id}:")
        print(f"  {result[:200]}...")  # First 200 chars

    print("\n✅ Scenario 1 complete!")


# ============================================================================
# Scenario 2: Feature Implementation (PARALLEL Mode)
# ============================================================================


async def scenario_2_parallel_feature():
    """
    Scenario: Parallel feature implementation

    Flow:
    1. Research and implementation happen in parallel
    2. Testing waits for both to complete

    Mode: PARALLEL (independent tasks execute concurrently)
    """
    print("\n" + "="*80)
    print("SCENARIO 2: Feature Implementation (Parallel)")
    print("="*80)

    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    roles = [
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["developer"],
        BUILTIN_ROLES["qa_engineer"],
    ]

    crew = Crew(roles=roles, llm=llm)

    tasks = [
        # Independent tasks (can run in parallel)
        Task(
            id="research_api",
            description="Research API design patterns",
            prompt="Research REST API best practices for user authentication endpoints",
            assigned_role="researcher",
            output_key="api_research"
        ),
        Task(
            id="implement_endpoint",
            description="Implement authentication endpoint",
            prompt="Implement /api/v1/auth/login endpoint with JWT token generation",
            assigned_role="developer",
            output_key="implementation"
        ),
        # Dependent task (waits for both above)
        Task(
            id="write_tests",
            description="Write API tests",
            prompt="Write comprehensive tests for the authentication endpoint",
            assigned_role="qa_engineer",
            dependencies=["research_api", "implement_endpoint"]
        ),
    ]

    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.PARALLEL,
        max_parallel=3  # Max 3 concurrent tasks
    )

    print("\n🚀 Executing parallel feature implementation...")
    results = await crew.kickoff(plan)

    print("\n📊 Results:")
    print(f"  Total tasks: {len(results)}")
    print(f"  Research and implementation ran in parallel")
    print(f"  Tests ran after both completed")

    print("\n✅ Scenario 2 complete!")


# ============================================================================
# Scenario 3: Conditional Workflow (CONDITIONAL Mode)
# ============================================================================


async def scenario_3_conditional_workflow():
    """
    Scenario: Conditional task execution based on runtime state

    Flow:
    1. Initial code analysis
    2. Security review (only if issues found)
    3. Refactoring (only if security issues exist)
    4. Documentation update (always runs)

    Mode: CONDITIONAL (tasks execute based on conditions)
    """
    print("\n" + "="*80)
    print("SCENARIO 3: Conditional Workflow")
    print("="*80)

    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    roles = [
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["security_auditor"],
        BUILTIN_ROLES["developer"],
        BUILTIN_ROLES["tech_writer"],
    ]

    crew = Crew(roles=roles, llm=llm)

    tasks = [
        Task(
            id="initial_scan",
            description="Initial code scan",
            prompt="Perform initial code quality scan and identify potential issues",
            assigned_role="researcher",
            output_key="scan_results"
        ),
        Task(
            id="security_deep_dive",
            description="Deep security analysis",
            prompt="Perform detailed security analysis of flagged code sections",
            assigned_role="security_auditor",
            # Only run if scan found issues
            condition=ConditionBuilder.and_all([
                ConditionBuilder.key_exists("scan_results"),
                ConditionBuilder.not_(
                    lambda ctx: "no issues" in ctx.get("scan_results", "").lower()
                )
            ]),
            dependencies=["initial_scan"],
            output_key="security_analysis"
        ),
        Task(
            id="refactor_code",
            description="Refactor vulnerable code",
            prompt="Refactor code to address security vulnerabilities",
            assigned_role="developer",
            # Only run if security analysis was performed
            condition=ConditionBuilder.key_exists("security_analysis"),
            dependencies=["security_deep_dive"],
        ),
        Task(
            id="update_docs",
            description="Update documentation",
            prompt="Update documentation based on code review findings",
            assigned_role="tech_writer",
            # Always runs
            dependencies=["initial_scan"]
        ),
    ]

    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.CONDITIONAL
    )

    print("\n🚀 Executing conditional workflow...")
    results = await crew.kickoff(plan)

    print("\n📊 Results:")
    stats = plan.shared_context.get("_conditional_stats", {})
    print(f"  Total tasks: {stats.get('total_tasks', 0)}")
    print(f"  Executed: {stats.get('executed', 0)}")
    print(f"  Skipped: {stats.get('skipped', 0)}")
    print(f"  Skipped tasks: {stats.get('skipped_task_ids', [])}")

    print("\n✅ Scenario 3 complete!")


# ============================================================================
# Scenario 4: Hierarchical Coordination (HIERARCHICAL Mode)
# ============================================================================


async def scenario_4_hierarchical_coordination():
    """
    Scenario: Manager-coordinated team workflow

    Flow:
    Manager receives overall goal and coordinates team members using
    the delegate tool to assign subtasks to appropriate roles.

    Mode: HIERARCHICAL (manager coordinates all tasks)
    """
    print("\n" + "="*80)
    print("SCENARIO 4: Hierarchical Coordination")
    print("="*80)

    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    # Include manager role
    roles = [
        BUILTIN_ROLES["manager"],
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["developer"],
        BUILTIN_ROLES["qa_engineer"],
    ]

    crew = Crew(roles=roles, llm=llm)

    # Define high-level tasks for manager to coordinate
    tasks = [
        Task(
            id="gather_requirements",
            description="Gather feature requirements",
            prompt="Research best practices for implementing user profile feature",
            assigned_role="researcher",
        ),
        Task(
            id="implement_feature",
            description="Implement user profile feature",
            prompt="Implement user profile CRUD endpoints",
            assigned_role="developer",
            dependencies=["gather_requirements"]
        ),
        Task(
            id="test_feature",
            description="Test user profile feature",
            prompt="Write and run tests for user profile endpoints",
            assigned_role="qa_engineer",
            dependencies=["implement_feature"]
        ),
    ]

    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.HIERARCHICAL
    )

    print("\n🚀 Manager coordinating team workflow...")
    print("   Manager will delegate tasks to team members")
    results = await crew.kickoff(plan)

    print("\n📊 Results:")
    manager_result = results.get("_manager_coordination", {})
    print(f"  Status: {manager_result.get('status')}")
    print(f"  Coordinated tasks: {manager_result.get('coordinated_tasks')}")
    print(f"\n  Manager summary:")
    print(f"  {manager_result.get('result', '')[:300]}...")

    print("\n✅ Scenario 4 complete!")


# ============================================================================
# Scenario 5: Inter-Agent Communication
# ============================================================================


async def scenario_5_agent_communication():
    """
    Scenario: Agents communicate via MessageBus and SharedState

    Demonstrates:
    - SharedState for storing/retrieving shared data
    - MessageBus for agent-to-agent messaging
    - Real-time coordination
    """
    print("\n" + "="*80)
    print("SCENARIO 5: Inter-Agent Communication")
    print("="*80)

    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    roles = [
        BUILTIN_ROLES["researcher"],
        BUILTIN_ROLES["developer"],
    ]

    crew = Crew(roles=roles, llm=llm)

    # Set initial shared state
    await crew.shared_state.set("project_phase", "planning")
    await crew.shared_state.set("quality_threshold", 0.8)

    print("\n📡 Initial shared state:")
    print(f"  project_phase: {await crew.shared_state.get('project_phase')}")
    print(f"  quality_threshold: {await crew.shared_state.get('quality_threshold')}")

    tasks = [
        Task(
            id="research_tech",
            description="Research technology stack",
            prompt="""Research appropriate technology stack for the project.

Check shared state for project phase and update with your recommendation.""",
            assigned_role="researcher",
            output_key="tech_research"
        ),
        Task(
            id="prototype",
            description="Create prototype",
            prompt="""Create a prototype based on research findings.

Use the tech recommendation from shared state.""",
            assigned_role="developer",
            dependencies=["research_tech"]
        ),
    ]

    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.SEQUENTIAL
    )

    print("\n🚀 Executing with shared state...")
    results = await crew.kickoff(plan)

    print("\n📊 Final shared state:")
    print(f"  All keys: {await crew.shared_state.keys()}")

    print("\n📈 MessageBus stats:")
    stats = crew.message_bus.get_stats()
    print(f"  Total messages: {stats.get('total_messages', 0)}")
    print(f"  Active threads: {stats.get('active_threads', 0)}")

    print("\n✅ Scenario 5 complete!")


# ============================================================================
# Scenario 6: Custom Roles and Complex Conditions
# ============================================================================


async def scenario_6_custom_roles():
    """
    Scenario: Custom roles with complex conditional logic

    Demonstrates:
    - Creating custom roles
    - Complex condition combinations
    - Role capability matching
    """
    print("\n" + "="*80)
    print("SCENARIO 6: Custom Roles & Complex Conditions")
    print("="*80)

    llm = LLMFactory.create_openai(api_key="your-openai-api-key")

    # Define custom roles
    data_analyst = Role(
        name="data_analyst",
        description="Data analysis specialist",
        goal="Analyze data and extract insights",
        backstory="Expert in data analysis with strong statistical background",
        tools=["read_file", "python_repl", "calculator"],
        capabilities=["data_analysis", "statistics", "visualization"]
    )

    ml_engineer = Role(
        name="ml_engineer",
        description="Machine learning engineer",
        goal="Build and train ML models",
        backstory="ML expert with experience in model development",
        tools=["python_repl", "read_file", "write_file"],
        capabilities=["machine_learning", "model_training", "data_preprocessing"]
    )

    roles = [data_analyst, ml_engineer, BUILTIN_ROLES["tech_writer"]]

    crew = Crew(roles=roles, llm=llm)

    # Complex conditional tasks
    tasks = [
        Task(
            id="analyze_data",
            description="Analyze dataset",
            prompt="Perform exploratory data analysis on customer dataset",
            assigned_role="data_analyst",
            output_key="data_insights"
        ),
        Task(
            id="train_model",
            description="Train ML model",
            prompt="Train a classification model based on data analysis",
            assigned_role="ml_engineer",
            # Complex condition: run if data quality is good AND insights exist
            condition=ConditionBuilder.and_all([
                ConditionBuilder.key_exists("data_insights"),
                ConditionBuilder.or_any([
                    ConditionBuilder.key_equals("data_quality", "high"),
                    ConditionBuilder.key_equals("data_quality", "medium")
                ])
            ]),
            dependencies=["analyze_data"],
            output_key="model_results"
        ),
        Task(
            id="document_model",
            description="Document ML model",
            prompt="Create documentation for the trained model",
            assigned_role="tech_writer",
            # Only if model was trained
            condition=ConditionBuilder.key_exists("model_results"),
            dependencies=["train_model"]
        ),
    ]

    # Simulate data quality in shared context
    plan = OrchestrationPlan(
        tasks=tasks,
        mode=OrchestrationMode.CONDITIONAL,
        shared_context={"data_quality": "high"}  # This will allow model training
    )

    print("\n🚀 Executing with custom roles and conditions...")
    results = await crew.kickoff(plan)

    print("\n📊 Results:")
    stats = plan.shared_context.get("_conditional_stats", {})
    print(f"  Executed: {stats.get('executed', 0)} tasks")
    print(f"  Skipped: {stats.get('skipped', 0)} tasks")

    print("\n👥 Crew stats:")
    crew_stats = crew.get_stats()
    print(f"  Total members: {crew_stats['total_members']}")
    print(f"  Roles: {crew_stats['roles']}")

    print("\n✅ Scenario 6 complete!")


# ============================================================================
# Main Demo Runner
# ============================================================================


async def main():
    """Run all demo scenarios"""
    print("\n" + "="*80)
    print("🎬 Loom Agent Crew System - Complete Demo")
    print("="*80)
    print("\nThis demo showcases all features of the Crew system:")
    print("  1. Code Review Workflow (Sequential)")
    print("  2. Feature Implementation (Parallel)")
    print("  3. Conditional Workflow")
    print("  4. Hierarchical Coordination")
    print("  5. Inter-Agent Communication")
    print("  6. Custom Roles & Complex Conditions")

    print("\n⚠️  Note: This demo requires an OpenAI API key.")
    print("    Set your API key in the code or use environment variables.")

    # Run scenarios
    scenarios = [
        ("Scenario 1", scenario_1_code_review),
        ("Scenario 2", scenario_2_parallel_feature),
        ("Scenario 3", scenario_3_conditional_workflow),
        ("Scenario 4", scenario_4_hierarchical_coordination),
        ("Scenario 5", scenario_5_agent_communication),
        ("Scenario 6", scenario_6_custom_roles),
    ]

    for name, scenario_func in scenarios:
        try:
            await scenario_func()
        except Exception as e:
            print(f"\n❌ {name} failed: {e}")
            print("   (This is expected if no API key is configured)")

    print("\n" + "="*80)
    print("🎉 Demo Complete!")
    print("="*80)
    print("\nNext steps:")
    print("  - Review the code to understand each scenario")
    print("  - Modify scenarios for your use cases")
    print("  - Create your own custom roles and workflows")
    print("  - Explore the API documentation for advanced features")


if __name__ == "__main__":
    asyncio.run(main())
