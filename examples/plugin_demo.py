"""
Tool Plugin System Demo

This script demonstrates all features of the loom-agent tool plugin system:
1. Creating plugins programmatically
2. Loading plugins from files
3. Plugin registration and management
4. Using plugin tools
5. Plugin lifecycle (enable/disable)
6. Plugin discovery

Run this demo:
    python examples/plugin_demo.py
"""

import asyncio
from pathlib import Path

from loom.plugins import (
    ToolPluginManager,
    ToolPluginRegistry,
    ToolPluginLoader,
    ToolPlugin,
    ToolPluginMetadata,
    PluginStatus,
)

# Import example plugins
from examples.tool_plugins.example_plugins import (
    EXAMPLE_PLUGINS,
    weather_plugin,
    currency_plugin,
    sentiment_plugin,
)


async def demo_1_basic_registration():
    """Demo 1: Basic plugin registration and usage"""
    print("=" * 70)
    print("Demo 1: Basic Plugin Registration")
    print("=" * 70)

    # Create registry
    registry = ToolPluginRegistry()

    # Register weather plugin
    registry.register(weather_plugin)
    weather_plugin.enable()

    print(f"✓ Registered plugin: {weather_plugin.metadata.name}")
    print(f"  Version: {weather_plugin.metadata.version}")
    print(f"  Author: {weather_plugin.metadata.author}")
    print(f"  Tools: {', '.join(weather_plugin.metadata.tool_names)}")

    # Get and use tool
    print("\n--- Using weather tool ---")
    weather_tool = registry.get_tool("weather")
    if weather_tool:
        result = await weather_tool.run(location="San Francisco", units="celsius")
        print(result)

    print()


async def demo_2_multiple_plugins():
    """Demo 2: Working with multiple plugins"""
    print("=" * 70)
    print("Demo 2: Multiple Plugins")
    print("=" * 70)

    registry = ToolPluginRegistry()

    # Register all example plugins
    for plugin in EXAMPLE_PLUGINS:
        registry.register(plugin)
        plugin.enable()
        print(f"✓ Registered: {plugin.metadata.name}")

    # Get statistics
    print("\n--- Registry Statistics ---")
    stats = registry.get_stats()
    print(f"Total plugins: {stats['total_plugins']}")
    print(f"Enabled plugins: {stats['enabled']}")
    print(f"Total tools: {stats['total_tools']}")
    print(f"Tags: {', '.join(stats['tags'])}")

    # Use currency converter
    print("\n--- Using currency converter ---")
    converter = registry.get_tool("currency_converter")
    if converter:
        result = await converter.run(
            amount=100.0,
            from_currency="USD",
            to_currency="EUR"
        )
        print(result)

    # Use sentiment analysis
    print("\n--- Using sentiment analysis ---")
    sentiment = registry.get_tool("sentiment_analysis")
    if sentiment:
        result = await sentiment.run(
            text="This is an amazing product! I love it and highly recommend it."
        )
        print(result)

    print()


async def demo_3_plugin_lifecycle():
    """Demo 3: Plugin lifecycle management"""
    print("=" * 70)
    print("Demo 3: Plugin Lifecycle (Enable/Disable)")
    print("=" * 70)

    registry = ToolPluginRegistry()

    # Register plugins
    registry.register(weather_plugin)
    weather_plugin.enable()
    print(f"✓ Plugin '{weather_plugin.metadata.name}' enabled")

    # Tool should work
    tool = registry.get_tool("weather")
    print(f"  Tool available: {tool is not None}")

    # Disable plugin
    print(f"\n--- Disabling plugin ---")
    registry.disable_plugin(weather_plugin.metadata.name)
    print(f"✓ Plugin '{weather_plugin.metadata.name}' disabled")

    # Tool should not be available
    tool = registry.get_tool("weather")
    print(f"  Tool available: {tool is not None}")

    # Re-enable plugin
    print(f"\n--- Re-enabling plugin ---")
    registry.enable_plugin(weather_plugin.metadata.name)
    print(f"✓ Plugin '{weather_plugin.metadata.name}' enabled")

    # Tool should work again
    tool = registry.get_tool("weather")
    print(f"  Tool available: {tool is not None}")

    print()


async def demo_4_search_and_filter():
    """Demo 4: Searching and filtering plugins"""
    print("=" * 70)
    print("Demo 4: Searching and Filtering")
    print("=" * 70)

    registry = ToolPluginRegistry()

    # Register all example plugins
    for plugin in EXAMPLE_PLUGINS:
        registry.register(plugin)
        plugin.enable()

    # Search by tag
    print("--- Plugins with 'demo' tag ---")
    demo_plugins = registry.search_by_tag("demo")
    for plugin in demo_plugins:
        print(f"  • {plugin.metadata.name} - {plugin.metadata.description}")

    print("\n--- Plugins with 'finance' tag ---")
    finance_plugins = registry.search_by_tag("finance")
    for plugin in finance_plugins:
        print(f"  • {plugin.metadata.name} - {plugin.metadata.description}")

    # Search by author
    print("\n--- Plugins by 'Loom Team' ---")
    loom_plugins = registry.search_by_author("Loom Team")
    for plugin in loom_plugins:
        print(f"  • {plugin.metadata.name} (v{plugin.metadata.version})")

    # List by status
    print("\n--- Enabled plugins ---")
    enabled = registry.list_plugins(status_filter=PluginStatus.ENABLED)
    for plugin in enabled:
        print(f"  • {plugin.metadata.name}")

    print()


async def demo_5_plugin_loader():
    """Demo 5: Loading plugins from files"""
    print("=" * 70)
    print("Demo 5: Loading Plugins from Files")
    print("=" * 70)

    # Create loader with registry
    registry = ToolPluginRegistry()
    loader = ToolPluginLoader(registry=registry)

    # Load weather plugin from file
    plugin_file = Path(__file__).parent / "tool_plugins" / "weather_plugin.py"

    print(f"Loading plugin from: {plugin_file}")

    try:
        plugin = await loader.load_from_file(plugin_file, auto_register=True)

        print(f"✓ Loaded plugin: {plugin.metadata.name}")
        print(f"  Version: {plugin.metadata.version}")
        print(f"  Author: {plugin.metadata.author}")
        print(f"  Tools: {', '.join(plugin.metadata.tool_names)}")

        # Enable and use
        plugin.enable()
        tool = registry.get_tool("weather")
        if tool:
            print("\n--- Using loaded tool ---")
            result = await tool.run(
                location="Tokyo",
                units="celsius",
                detailed=True
            )
            print(result)

    except FileNotFoundError:
        print(f"⚠ Plugin file not found: {plugin_file}")
        print("  (This is expected if running from different directory)")

    print()


async def demo_6_plugin_manager():
    """Demo 6: High-level plugin management"""
    print("=" * 70)
    print("Demo 6: Plugin Manager (High-level API)")
    print("=" * 70)

    # Create manager
    manager = ToolPluginManager()

    # Install plugins programmatically
    print("--- Installing example plugins ---")
    for plugin in EXAMPLE_PLUGINS:
        # Manually register since they're already created
        manager.registry.register(plugin)
        plugin.enable()
        print(f"✓ Installed: {plugin.metadata.name}")

    # Get statistics
    print("\n--- Manager Statistics ---")
    stats = manager.get_stats()
    print(f"Total plugins: {stats['total_plugins']}")
    print(f"Total tools: {stats['total_tools']}")

    # List installed
    print("\n--- Installed Plugins ---")
    installed = manager.list_installed(status_filter=PluginStatus.ENABLED)
    for plugin in installed:
        print(f"  • {plugin.metadata.name} v{plugin.metadata.version}")
        print(f"    Tools: {', '.join(plugin.metadata.tool_names)}")
        print(f"    Tags: {', '.join(plugin.metadata.tags)}")

    # Use tool via manager
    print("\n--- Using tool via manager ---")
    sentiment = manager.get_tool("sentiment_analysis")
    if sentiment:
        result = await sentiment.run(
            text="The service was terrible and the food was awful."
        )
        print(result)

    # Disable plugin
    print("\n--- Plugin lifecycle ---")
    print("Disabling 'weather-tool-plugin'...")
    manager.disable("weather-tool-plugin")

    stats = manager.get_stats()
    print(f"Enabled plugins: {stats['enabled']}")
    print(f"Disabled plugins: {stats['disabled']}")

    print()


async def demo_7_plugin_metadata():
    """Demo 7: Working with plugin metadata"""
    print("=" * 70)
    print("Demo 7: Plugin Metadata")
    print("=" * 70)

    # Create metadata
    metadata = ToolPluginMetadata(
        name="custom-plugin",
        version="2.1.0",
        author="John Doe <john@example.com>",
        description="A custom plugin example",
        homepage="https://github.com/johndoe/custom-plugin",
        license="Apache-2.0",
        dependencies=["requests>=2.28.0", "pydantic>=2.0.0"],
        loom_min_version="0.1.0",
        tags=["custom", "example", "utility"],
    )

    print("--- Metadata Details ---")
    print(f"Name: {metadata.name}")
    print(f"Version: {metadata.version}")
    print(f"Author: {metadata.author}")
    print(f"License: {metadata.license}")
    print(f"Tags: {', '.join(metadata.tags)}")
    print(f"Dependencies: {', '.join(metadata.dependencies)}")

    # Serialize to JSON
    print("\n--- JSON Serialization ---")
    json_str = metadata.to_json()
    print(json_str)

    # Deserialize from JSON
    print("\n--- JSON Deserialization ---")
    metadata_from_json = ToolPluginMetadata.from_json(json_str)
    print(f"✓ Loaded metadata: {metadata_from_json.name} v{metadata_from_json.version}")

    print()


async def main():
    """Run all demos"""
    print("\n")
    print("=" * 70)
    print("LOOM TOOL PLUGIN SYSTEM DEMO")
    print("=" * 70)
    print()

    # Run all demos
    await demo_1_basic_registration()
    await demo_2_multiple_plugins()
    await demo_3_plugin_lifecycle()
    await demo_4_search_and_filter()
    await demo_5_plugin_loader()
    await demo_6_plugin_manager()
    await demo_7_plugin_metadata()

    print("=" * 70)
    print("All demos completed!")
    print("=" * 70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
