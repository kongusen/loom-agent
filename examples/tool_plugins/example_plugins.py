"""
Example tool plugins for demonstration purposes.

This module contains example plugins showing how to create custom tools:
- WeatherTool: Mock weather lookup tool
- CurrencyConverterTool: Currency conversion tool
- SentimentAnalysisTool: Text sentiment analysis tool
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from loom.interfaces.tool import BaseTool
from loom.plugins import ToolPluginMetadata, ToolPlugin


# ============================================================================
# Example 1: Weather Tool Plugin
# ============================================================================

WEATHER_PLUGIN_METADATA = ToolPluginMetadata(
    name="weather-tool-plugin",
    version="1.0.0",
    author="Loom Team <team@loom.ai>",
    description="Mock weather lookup tool for demonstration",
    license="MIT",
    tags=["weather", "data", "demo"],
    dependencies=[],
)


class WeatherToolInput(BaseModel):
    """Input schema for weather tool"""

    location: str = Field(..., description="City name or location")
    units: str = Field("celsius", description="Temperature units (celsius/fahrenheit)")


class WeatherTool(BaseTool):
    """
    Mock weather lookup tool.

    This is a demonstration tool that returns mock weather data.
    In a real implementation, this would call an actual weather API.
    """

    name = "weather"
    description = "Get current weather for a location (mock data)"
    args_schema = WeatherToolInput
    is_read_only = True
    category = "network"

    async def run(self, location: str, units: str = "celsius", **kwargs) -> str:
        """
        Get weather for location.

        Args:
            location: City name
            units: Temperature units

        Returns:
            str: Weather description
        """
        # Mock weather data
        mock_temp = 22 if units == "celsius" else 72
        mock_condition = "Partly cloudy"

        return f"""**Weather for {location}**

Temperature: {mock_temp}°{units[0].upper()}
Condition: {mock_condition}
Humidity: 65%
Wind: 10 km/h NW

_Note: This is mock data for demonstration_
"""


# Create weather plugin
weather_plugin = ToolPlugin(
    tool_class=WeatherTool,
    metadata=WEATHER_PLUGIN_METADATA
)


# ============================================================================
# Example 2: Currency Converter Plugin
# ============================================================================

CURRENCY_PLUGIN_METADATA = ToolPluginMetadata(
    name="currency-converter-plugin",
    version="1.0.0",
    author="Loom Team <team@loom.ai>",
    description="Currency conversion tool with mock exchange rates",
    license="MIT",
    tags=["finance", "currency", "demo"],
    dependencies=[],
)


class CurrencyConverterInput(BaseModel):
    """Input schema for currency converter"""

    amount: float = Field(..., description="Amount to convert", gt=0)
    from_currency: str = Field(..., description="Source currency code (e.g., USD)")
    to_currency: str = Field(..., description="Target currency code (e.g., EUR)")


class CurrencyConverterTool(BaseTool):
    """
    Currency conversion tool.

    Uses mock exchange rates for demonstration.
    """

    name = "currency_converter"
    description = "Convert between currencies (mock rates)"
    args_schema = CurrencyConverterInput
    is_read_only = True
    category = "general"

    # Mock exchange rates (to USD)
    MOCK_RATES = {
        "USD": 1.0,
        "EUR": 0.85,
        "GBP": 0.73,
        "JPY": 110.0,
        "CNY": 6.5,
    }

    async def run(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        **kwargs
    ) -> str:
        """
        Convert currency.

        Args:
            amount: Amount to convert
            from_currency: Source currency
            to_currency: Target currency

        Returns:
            str: Conversion result
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Check currency support
        if from_currency not in self.MOCK_RATES:
            return f"Error: Unsupported currency '{from_currency}'"
        if to_currency not in self.MOCK_RATES:
            return f"Error: Unsupported currency '{to_currency}'"

        # Convert through USD
        usd_amount = amount / self.MOCK_RATES[from_currency]
        result = usd_amount * self.MOCK_RATES[to_currency]

        return f"""**Currency Conversion**

{amount:.2f} {from_currency} = {result:.2f} {to_currency}

Exchange rate: 1 {from_currency} = {self.MOCK_RATES[to_currency] / self.MOCK_RATES[from_currency]:.4f} {to_currency}

_Note: Using mock exchange rates for demonstration_
"""


# Create currency plugin
currency_plugin = ToolPlugin(
    tool_class=CurrencyConverterTool,
    metadata=CURRENCY_PLUGIN_METADATA
)


# ============================================================================
# Example 3: Sentiment Analysis Plugin
# ============================================================================

SENTIMENT_PLUGIN_METADATA = ToolPluginMetadata(
    name="sentiment-analysis-plugin",
    version="1.0.0",
    author="Loom Team <team@loom.ai>",
    description="Simple sentiment analysis tool",
    license="MIT",
    tags=["nlp", "text", "analysis", "demo"],
    dependencies=[],
)


class SentimentAnalysisInput(BaseModel):
    """Input schema for sentiment analysis"""

    text: str = Field(..., description="Text to analyze")


class SentimentAnalysisTool(BaseTool):
    """
    Simple sentiment analysis tool.

    Uses basic keyword matching for demonstration.
    """

    name = "sentiment_analysis"
    description = "Analyze sentiment of text (basic keyword matching)"
    args_schema = SentimentAnalysisInput
    is_read_only = True
    category = "general"

    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "love", "happy", "joy", "best", "awesome", "perfect"
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "worst", "hate", "sad",
        "angry", "disappointed", "poor", "difficult", "problem"
    }

    async def run(self, text: str, **kwargs) -> str:
        """
        Analyze sentiment.

        Args:
            text: Text to analyze

        Returns:
            str: Sentiment analysis result
        """
        text_lower = text.lower()
        words = text_lower.split()

        # Count positive/negative words
        positive_count = sum(1 for word in words if word in self.POSITIVE_WORDS)
        negative_count = sum(1 for word in words if word in self.NEGATIVE_WORDS)

        # Determine sentiment
        if positive_count > negative_count:
            sentiment = "Positive"
            emoji = "😊"
        elif negative_count > positive_count:
            sentiment = "Negative"
            emoji = "😞"
        else:
            sentiment = "Neutral"
            emoji = "😐"

        # Calculate score
        total = positive_count + negative_count
        if total > 0:
            score = (positive_count - negative_count) / total
        else:
            score = 0.0

        return f"""**Sentiment Analysis** {emoji}

Text: "{text[:100]}{'...' if len(text) > 100 else ''}"

Sentiment: {sentiment}
Score: {score:.2f} (range: -1.0 to +1.0)

Positive words: {positive_count}
Negative words: {negative_count}

_Note: Using basic keyword matching for demonstration_
"""


# Create sentiment plugin
sentiment_plugin = ToolPlugin(
    tool_class=SentimentAnalysisTool,
    metadata=SENTIMENT_PLUGIN_METADATA
)


# ============================================================================
# Export all example plugins
# ============================================================================

EXAMPLE_PLUGINS = [
    weather_plugin,
    currency_plugin,
    sentiment_plugin,
]

__all__ = [
    "EXAMPLE_PLUGINS",
    "weather_plugin",
    "currency_plugin",
    "sentiment_plugin",
    "WeatherTool",
    "CurrencyConverterTool",
    "SentimentAnalysisTool",
]
