# Lexicon Agent Framework

> 🤖 A powerful multi-agent orchestration framework for building intelligent systems

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Async](https://img.shields.io/badge/Async-Native-orange.svg)]()

## 🚀 Key Features

- **🤖 Multi-Agent Orchestration**: Coordinate multiple specialized agents working together
- **🧠 Intelligent Context Management**: Automatic context optimization and memory management  
- **🔧 Rich Tool Ecosystem**: Built-in tools for file operations, knowledge bases, code execution
- **🌊 Streaming Processing**: Real-time data processing and response streaming
- **🔒 Security First**: Built-in security checks and permission controls
- **⚡ High Performance**: Asynchronous architecture with concurrent processing
- **🔌 Extensible**: Modular design for easy customization and extension
- **🌐 LLM Integration**: Support for multiple LLM providers (OpenAI, Anthropic, etc.)

## 🏗️ Architecture

```
lexicon_agent/
├── core/
│   ├── agent/           # Agent management and control
│   ├── context/         # Context processing and management
│   ├── orchestration/   # Multi-agent orchestration
│   ├── streaming/       # Streaming data processing
│   └── tools/           # Tool registry and execution
├── config/              # Configuration management
├── infrastructure/      # Infrastructure components
├── api/                 # API interfaces (CLI, REST, WebSocket)
└── types.py            # Core type definitions
```

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/your-org/lexicon-agent.git
cd lexicon-agent

# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e .
```

## 🏃‍♂️ Quick Start

### Basic Usage

```python
import asyncio
from lexicon_agent.types import Agent
from lexicon_agent.core.tools.registry import ToolRegistry
from lexicon_agent.core.orchestration.engine import OrchestrationEngine, UserInput, OrchestrationContext

async def main():
    # Create an agent
    agent = Agent(
        agent_id="assistant_001",
        name="General Assistant",
        specialization="general",
        capabilities=["file_operations", "data_analysis"],
        status="available"
    )
    
    # Initialize tools and orchestration
    tool_registry = ToolRegistry()
    engine = OrchestrationEngine()
    
    # Create user input
    user_input = UserInput(
        message="Analyze the sales data and create a summary report"
    )
    
    # Create orchestration context
    context = OrchestrationContext(
        user_input=user_input,
        available_agents=[agent]
    )
    
    # Execute orchestration
    result = await engine.orchestrate(user_input, [agent], context)
    print(f"Result: {result.primary_result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Tool Usage Example

```python
from lexicon_agent.core.tools.registry import ToolRegistry

# Get tool registry
tool_registry = ToolRegistry()

# Use file system tool
fs_tool = tool_registry.get_tool("file_system")
result = await fs_tool.execute({
    "action": "read",
    "path": "data.txt"
})

# Use knowledge base tool  
kb_tool = tool_registry.get_tool("knowledge_base")
await kb_tool.execute({
    "action": "create",
    "kb_name": "project_docs",
    "description": "Project documentation"
})
```

## 🔧 Core Components

### Agents
- **Agent Controller**: Manages agent lifecycle and coordination
- **Agent Registry**: Agent discovery and capability matching
- **Specialization**: Domain-specific agent behaviors

### Context Management  
- **Context Retrieval**: Intelligent context gathering
- **Context Processing**: Context optimization and compression
- **Memory Management**: Persistent and session memory

### Tool System
- **Tool Registry**: Centralized tool management
- **Tool Executor**: Safe tool execution with monitoring
- **Tool Scheduler**: Intelligent tool scheduling and orchestration

### Orchestration
- **Orchestration Engine**: Multi-agent workflow coordination
- **Strategy System**: Pluggable orchestration strategies
- **Event Coordination**: Inter-agent communication

### Streaming
- **Stream Processor**: Real-time data processing
- **Stream Pipeline**: Multi-stage processing pipelines
- **Stream Optimizer**: Performance optimization

## 🛠️ Built-in Tools

| Tool | Description | Safety Level |
|------|-------------|--------------|
| **File System** | File operations (read, write, list) | Cautious |
| **Knowledge Base** | Document storage and search | Safe |
| **Code Interpreter** | Code execution (Python, JS, Bash) | Exclusive |
| **Web Search** | Web information retrieval | Safe |

## 🌐 LLM Integration

The framework supports multiple LLM providers:

```python
# Environment configuration
export LLM_API_KEY="your-api-key"
export LLM_BASE_URL="https://api.openai.com/v1"  
export LLM_MODEL="gpt-3.5-turbo"

# Supported providers:
# - OpenAI (GPT-3.5, GPT-4)
# - Anthropic (Claude-3)
# - Azure OpenAI
# - Local models (Ollama, etc.)
```

## 📚 Documentation

- **[Framework Guide](FRAMEWORK_GUIDE.md)** - Comprehensive usage guide
- **[API Reference](lexicon_agent/)** - Detailed API documentation
- **[Examples](examples/)** - Usage examples and tutorials

## 🔒 Security

The framework implements multiple security layers:

- **Path Traversal Protection**: Prevents unauthorized file access
- **Code Execution Sandboxing**: Safe code execution environment
- **Permission-based Access**: Granular permission controls
- **Input Validation**: Comprehensive input sanitization

## 📊 Performance

- **Concurrent Agent Support**: 100+ agents simultaneously
- **Tool Execution**: Sub-second response times
- **Memory Efficiency**: Optimized context management
- **Streaming Throughput**: 1000+ events/second

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for details.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by modern multi-agent systems research
- Built with Python's async/await ecosystem
- Designed for production scalability

---

**Built with ❤️ for the AI community**