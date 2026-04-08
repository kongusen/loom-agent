"""Example 12: Heartbeat and Safety Rules Integration."""

import asyncio

from loom import (
    AgentConfig,
    ModelRef,
    create_agent,
    tool,
)
from loom.config import (
    FilesystemWatchMethod,
    HeartbeatConfig,
    ResourceThresholds,
    SafetyEvaluator,
    SafetyRule,
    WatchConfig,
)


# Example 1: Basic Heartbeat Configuration
async def example_basic_heartbeat():
    """Enable heartbeat monitoring for file system changes"""
    print("\n=== Example 1: Basic Heartbeat ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a DevOps assistant monitoring the codebase",
            heartbeat=HeartbeatConfig(
                interval=5.0,
                min_entropy_delta=0.1,
                watch_sources=[
                    WatchConfig.filesystem(paths=["./src"], method=FilesystemWatchMethod.HASH)
                ],
            ),
        ),
    )

    # Heartbeat will monitor file changes in background
    result = await agent.run("Monitor the src directory for changes")
    print(f"Result: {result.output}")


# Example 2: Multiple Watch Sources
async def example_multiple_watch_sources():
    """Monitor multiple sources: filesystem, resources, processes"""
    print("\n=== Example 2: Multiple Watch Sources ===")

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a system monitoring assistant",
            heartbeat=HeartbeatConfig(
                interval=3.0,
                watch_sources=[
                    WatchConfig.filesystem(
                        paths=["./src", "./config"],
                        method=FilesystemWatchMethod.HASH,
                    ),
                    WatchConfig.resource(
                        thresholds=ResourceThresholds(cpu_pct=80.0, memory_pct=90.0),
                    ),
                    WatchConfig.process(watch_pids=[1234, 5678]),
                ],
            ),
        ),
    )

    result = await agent.run("Monitor system health")
    print(f"Result: {result.output}")


# Example 3: Basic Safety Rules
async def example_basic_safety():
    """Add safety rules to prevent dangerous operations"""
    print("\n=== Example 3: Basic Safety Rules ===")

    @tool(description="Delete a file")
    async def delete_file(path: str) -> str:
        return f"Deleted: {path}"

    @tool(description="Read a file")
    async def read_file(path: str) -> str:
        return f"Content of: {path}"

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a file management assistant",
            tools=[delete_file, read_file],
            safety_rules=[
                SafetyRule.block_tool(
                    name="no_delete",
                    reason="File deletion is forbidden",
                    tool_names=["delete_file"],
                )
            ],
        )
    )

    # This will be vetoed
    result = await agent.run("Delete the config file")
    print(f"Result: {result.output}")


# Example 4: Advanced Safety Rules
async def example_advanced_safety():
    """Complex safety rules with conditional logic"""
    print("\n=== Example 4: Advanced Safety Rules ===")

    @tool(description="Write to a file")
    async def write_file(path: str, content: str) -> str:
        return f"Wrote to {path}: {content}"

    @tool(description="Execute command")
    async def execute_command(cmd: str) -> str:
        return f"Executed: {cmd}"

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a system administrator assistant",
            tools=[write_file, execute_command],
            safety_rules=[
                SafetyRule.when_argument_startswith(
                    name="no_prod_write",
                    reason="Cannot write to production environment",
                    tool_name="write_file",
                    argument="path",
                    prefix="/prod/",
                ),
                SafetyRule.when_argument_contains_any(
                    name="no_dangerous_commands",
                    reason="Dangerous command blocked",
                    tool_name="execute_command",
                    argument="cmd",
                    values=["rm -rf", "dd if=", "mkfs"],
                ),
            ],
        )
    )

    result = await agent.run("Write config to /prod/config.yaml")
    print(f"Result: {result.output}")


# Example 5: Reusable SafetyRule objects
async def example_safety_rule_objects():
    """Use SafetyRule objects directly for reusable safety policies"""
    print("\n=== Example 5: SafetyRule Objects ===")

    @tool(description="Deploy application")
    async def deploy(env: str, version: str) -> str:
        return f"Deployed {version} to {env}"

    no_prod_deploy = SafetyRule.when_argument_equals(
        name="no_prod_deploy",
        reason="Production deployment requires manual approval",
        tool_name="deploy",
        argument="env",
        value="production",
    )

    no_old_versions = SafetyRule.when_argument_startswith(
        name="no_old_versions",
        reason="Cannot deploy v1.x versions (deprecated)",
        tool_name="deploy",
        argument="version",
        prefix="v1.",
    )

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a deployment assistant",
            tools=[deploy],
            safety_rules=[no_prod_deploy, no_old_versions],
        )
    )

    result = await agent.run("Deploy v2.0 to production")
    print(f"Result: {result.output}")


# Example 6: Combined Heartbeat + Safety
async def example_combined():
    """Use both heartbeat and safety rules together"""
    print("\n=== Example 6: Combined Heartbeat + Safety ===")

    @tool(description="Restart service")
    async def restart_service(name: str) -> str:
        return f"Restarted service: {name}"

    @tool(description="Check service status")
    async def check_status(name: str) -> str:
        return f"Status of {name}: running"

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a service monitoring and management assistant",
            tools=[restart_service, check_status],
            heartbeat=HeartbeatConfig(
                interval=5.0,
                watch_sources=[
                    WatchConfig.resource(
                        thresholds=ResourceThresholds(cpu_pct=80.0, memory_pct=90.0),
                    )
                ],
            ),
            safety_rules=[
                SafetyRule.when_argument_contains_any(
                    name="no_critical_restart",
                    reason="Critical services require manual restart approval",
                    tool_name="restart_service",
                    argument="name",
                    values=["database", "auth-service"],
                )
            ],
        )
    )

    result = await agent.run("Monitor services and restart if needed")
    print(f"Result: {result.output}")


# Example 7: Dynamic Safety Rules
async def example_dynamic_safety():
    """Add safety rules based on runtime conditions"""
    print("\n=== Example 7: Dynamic Safety Rules ===")

    @tool(description="Modify configuration")
    async def modify_config(key: str, value: str) -> str:
        return f"Set {key} = {value}"

    # Business hours check
    import datetime

    def is_business_hours() -> bool:
        now = datetime.datetime.now()
        return 9 <= now.hour < 17 and now.weekday() < 5

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a configuration management assistant",
            tools=[modify_config],
            safety_rules=[
                SafetyRule.custom(
                    name="business_hours_only",
                    reason="Configuration changes only allowed during business hours",
                    evaluator=SafetyEvaluator.callable(
                        lambda tool, args: tool == "modify_config" and not is_business_hours()
                    ),
                )
            ],
        )
    )

    result = await agent.run("Update the database connection string")
    print(f"Result: {result.output}")


# Example 8: Explicit AgentConfig Composition
async def example_explicit_composition():
    """Build the final agent in one explicit AgentConfig"""
    print("\n=== Example 8: Explicit AgentConfig Composition ===")

    @tool(description="Execute query")
    async def execute_query(sql: str) -> str:
        return f"Query result: {sql}"

    agent = create_agent(
        AgentConfig(
            model=ModelRef.anthropic("claude-sonnet-4"),
            instructions="You are a database assistant",
            tools=[execute_query],
            heartbeat=HeartbeatConfig(
                interval=10.0,
                watch_sources=[
                    WatchConfig.resource(
                        thresholds=ResourceThresholds(cpu_pct=90.0),
                    )
                ],
            ),
            safety_rules=[
                SafetyRule.when_argument_contains_any(
                    name="no_drop",
                    reason="DROP statements are forbidden",
                    tool_name="execute_query",
                    argument="sql",
                    values=["DROP"],
                )
            ],
        )
    )

    result = await agent.run("Show me all users")
    print(f"Result: {result.output}")


async def main():
    """Run all examples"""
    print("=" * 60)
    print("Heartbeat and Safety Rules Integration Examples")
    print("=" * 60)

    # Note: These examples demonstrate the API
    # Actual execution requires proper provider setup

    try:
        await example_basic_heartbeat()
    except Exception as e:
        print(f"Example 1 error (expected without API key): {e}")

    try:
        await example_multiple_watch_sources()
    except Exception as e:
        print(f"Example 2 error (expected without API key): {e}")

    try:
        await example_basic_safety()
    except Exception as e:
        print(f"Example 3 error (expected without API key): {e}")

    try:
        await example_advanced_safety()
    except Exception as e:
        print(f"Example 4 error (expected without API key): {e}")

    try:
        await example_safety_rule_objects()
    except Exception as e:
        print(f"Example 5 error (expected without API key): {e}")

    try:
        await example_combined()
    except Exception as e:
        print(f"Example 6 error (expected without API key): {e}")

    try:
        await example_dynamic_safety()
    except Exception as e:
        print(f"Example 7 error (expected without API key): {e}")

    try:
        await example_explicit_composition()
    except Exception as e:
        print(f"Example 8 error (expected without API key): {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
