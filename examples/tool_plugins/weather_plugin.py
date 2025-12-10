"""
Standalone Weather Tool Plugin

This file demonstrates the structure of a standalone plugin file
that can be loaded dynamically by the ToolPluginLoader.

File structure:
1. Import required dependencies
2. Define PLUGIN_METADATA (required)
3. Define tool input schema (Pydantic model)
4. Define tool class (inheriting from BaseTool)

To use this plugin:
    ```python
    from loom.plugins import ToolPluginManager

    manager = ToolPluginManager()
    plugin = await manager.install_from_file("path/to/weather_plugin.py")

    # Use the tool
    tool = manager.get_tool("weather")
    result = await tool.run(location="San Francisco")
    ```
"""

from pydantic import BaseModel, Field
from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata


# ============================================================================
# 1. Plugin Metadata (REQUIRED)
# ============================================================================

PLUGIN_METADATA = ToolPluginMetadata(
    name="weather-lookup",
    version="1.0.0",
    author="Demo Developer <demo@example.com>",
    description="Weather lookup tool using mock data",
    homepage="https://github.com/example/weather-plugin",
    license="MIT",
    dependencies=[],  # Add required packages here (e.g., ["requests>=2.28.0"])
    loom_min_version="0.1.0",
    tags=["weather", "data", "utility"],
)


# ============================================================================
# 2. Tool Input Schema
# ============================================================================

class WeatherLookupInput(BaseModel):
    """Input parameters for weather lookup"""

    location: str = Field(
        ...,
        description="City name or location to get weather for"
    )
    units: str = Field(
        "celsius",
        description="Temperature units: celsius or fahrenheit"
    )
    detailed: bool = Field(
        False,
        description="Return detailed weather information"
    )


# ============================================================================
# 3. Tool Implementation
# ============================================================================

class WeatherLookupTool(BaseTool):
    """
    Weather lookup tool.

    This tool provides weather information for a given location.
    Currently uses mock data for demonstration purposes.
    """

    name = "weather"
    description = "Get current weather information for any location"
    args_schema = WeatherLookupInput

    # Tool attributes for orchestration
    is_read_only = True
    category = "network"
    requires_confirmation = False

    async def run(
        self,
        location: str,
        units: str = "celsius",
        detailed: bool = False,
        **kwargs
    ) -> str:
        """
        Get weather for location.

        Args:
            location: City name or location
            units: Temperature units (celsius/fahrenheit)
            detailed: Include detailed information

        Returns:
            str: Formatted weather information
        """
        # Validate units
        if units not in ["celsius", "fahrenheit"]:
            return f"Error: Invalid units '{units}'. Use 'celsius' or 'fahrenheit'."

        # Mock weather data
        temp = 22 if units == "celsius" else 72
        temp_unit = "°C" if units == "celsius" else "°F"

        result = f"""**Weather for {location}**

Temperature: {temp}{temp_unit}
Condition: Partly cloudy
"""

        if detailed:
            result += f"""Humidity: 65%
Wind: 10 km/h NW
Pressure: 1013 hPa
Visibility: 10 km
UV Index: 5 (Moderate)
"""

        result += "\n_Note: This is mock data for demonstration purposes_"

        return result


# ============================================================================
# Notes for Plugin Developers
# ============================================================================

"""
Plugin Development Guidelines:

1. **PLUGIN_METADATA is required**
   - Must be a ToolPluginMetadata instance
   - Must use lowercase-with-dashes naming (e.g., "my-plugin")
   - Must follow semantic versioning (e.g., "1.0.0")

2. **Tool class must inherit from BaseTool**
   - Must implement async run() method
   - Must define name, description, and args_schema
   - Should set is_read_only, category, requires_confirmation appropriately

3. **Input schema should use Pydantic**
   - Provides automatic validation
   - Generates OpenAPI-compatible schema
   - Use Field() for parameter descriptions

4. **Keep plugins focused**
   - One plugin = one tool (or small set of related tools)
   - Clear, specific functionality
   - Good error handling

5. **Dependencies**
   - List all required packages in PLUGIN_METADATA.dependencies
   - Use version constraints (e.g., "requests>=2.28.0")
   - Keep dependencies minimal

6. **Testing**
   - Test your tool independently
   - Test with ToolPluginLoader
   - Verify error handling

7. **Documentation**
   - Clear docstrings
   - Usage examples
   - Parameter descriptions
"""
