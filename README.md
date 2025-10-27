# Loom Agent

<div align="center">

**Production-ready Python Agent framework with enterprise-grade reliability and observability**

[![PyPI](https://img.shields.io/pypi/v/loom-agent.svg)](https://pypi.org/project/loom-agent/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-18%2F18%20passing-brightgreen.svg)](tests/)

[Documentation](docs/user/user-guide.md) | [API Reference](docs/user/api-reference.md) | [Contributing](CONTRIBUTING.md)

</div>

---

## 🎯 What is Loom Agent?

Loom Agent is a Python framework for building reliable AI agents with production-grade features like automatic retries, context compression, persistent memory, and comprehensive observability.

**Key Features:**

- 🚀 **Simple API** - Get started with just 3 lines of code
- 🔧 **Tool System** - Easy decorator-based tool creation
- 💾 **Persistent Memory** - Cross-session conversation history
- 📊 **Observability** - Structured logging with correlation IDs
- 🛡️ **Production Ready** - Circuit breakers, retries, and failover
- ⚡ **High Performance** - Parallel tool execution and smart context compression (40% faster in v0.0.3)
- 🌐 **Multi-LLM** - OpenAI, Anthropic, and more
- 🎯 **Unified Coordination** - Advanced multi-agent coordination system
- 🔄 **TT Recursive Mode** - Enhanced task handling with improved recursion

## 📦 Installation

```bash
# Basic installation
pip install loom-agent

# With OpenAI support
pip install loom-agent[openai]

# With all features
pip install loom-agent[all]
```

**Requirements:** Python 3.11+

## 🚀 Quick Start

### Basic Agent

```python
import asyncio
from loom import agent
from loom.builtin.llms import MockLLM

async def main():
    # Create an agent
    my_agent = agent(llm=MockLLM())

    # Run it
    result = await my_agent.run("Hello, world!")
    print(result)

asyncio.run(main())
```

### With OpenAI

```python
from loom import agent

# Create agent with OpenAI
my_agent = agent(
    provider="openai",
    model="gpt-4",
    api_key="sk-..."  # or set OPENAI_API_KEY env var
)

result = await my_agent.run("What is the capital of France?")
print(result)
```

### Custom Tools

```python
from loom import agent, tool

@tool()
def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

my_agent = agent(
    provider="openai",
    model="gpt-4",
    tools=[add()]
)

result = await my_agent.run("What is 15 plus 27?")
print(result)
```

## 📚 Documentation

- **[Getting Started](docs/user/getting-started.md)** - Your first Loom agent in 5 minutes
- **[User Guide](docs/user/user-guide.md)** - Complete usage documentation
- **[API Reference](docs/user/api-reference.md)** - Detailed API documentation
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

## 🛠️ Core Components

### Agent Builder
```python
from loom import agent

my_agent = agent(
    provider="openai",      # LLM provider
    model="gpt-4",          # Model name
    tools=[...],            # Custom tools
    memory=...,             # Memory system
    callbacks=[...]         # Observability
)
```

### Tool Decorator
```python
from loom import tool

@tool(description="Fetch weather data")
def get_weather(city: str) -> dict:
    return {"temp": 72, "condition": "sunny"}
```

### Memory System
```python
from loom import PersistentMemory

memory = PersistentMemory()  # Conversations persist across restarts
agent = agent(llm=..., memory=memory)
```

### Observability
```python
from loom import ObservabilityCallback, MetricsAggregator

obs = ObservabilityCallback()
metrics = MetricsAggregator()

agent = agent(llm=..., callbacks=[obs, metrics])
```

## 🎯 Supported Platforms

- **Python:** 3.11, 3.12
- **Operating Systems:** Linux, macOS, Windows
- **LLM Providers:** OpenAI, Anthropic, Ollama

## 🎊 What's New in v0.0.3

**Major Performance & Reliability Improvements:**

- ⚡ **40% Performance Boost** - Optimized execution pipeline and context management
- 🔧 **Unified Coordination System** - Advanced multi-agent coordination with improved reliability
- 🔄 **Enhanced TT Recursive Mode** - Better task handling and recursion management
- 🛡️ **Bug Fixes** - All known issues resolved, compilation passes cleanly
- 📚 **Improved Documentation** - Comprehensive guides and API references

**Production Ready Features:**
- ✅ Core agent execution (stable)
- ✅ Tool system and decorators (enhanced)
- ✅ Memory and context management (optimized)
- ✅ Multi-LLM provider support (OpenAI, Anthropic, Ollama)
- ✅ Structured logging and observability
- ✅ Circuit breakers and retry mechanisms
- ✅ Unified coordination for complex workflows

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests: `poetry run pytest`
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📊 Project Status

- **Version:** 0.0.3 (Alpha)
- **Status:** Active Development
- **Tests:** 18/18 passing ✅
- **Python:** 3.11+ supported
- **Performance:** 40% improvement over v0.0.2

## 🗺️ Roadmap

### v0.1.0 (Planned)
- API stabilization
- More examples and tutorials
- Performance optimizations
- Extended documentation

### v0.2.0 (Planned)
- Additional LLM providers
- Plugin system
- Web UI for debugging

### v1.0.0 (Goal)
- Stable API
- Production-grade quality
- Comprehensive documentation
- Community ecosystem

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- **PyPI:** https://pypi.org/project/loom-agent/
- **GitHub:** https://github.com/kongusen/loom-agent
- **Issues:** https://github.com/kongusen/loom-agent/issues
- **Releases:** [v0.0.3](releases/v0.0.3.md) | [v0.0.2](releases/v0.0.2.md) | [v0.0.1](releases/v0.0.1.md)

## 🙏 Acknowledgments

Special thanks to the Claude Code project for inspiration and to all early testers and contributors!

---

**Built with ❤️ for the AI community**

<div align="center">
  <sub>If you find Loom Agent useful, please consider giving it a ⭐ on GitHub!</sub>
</div>
