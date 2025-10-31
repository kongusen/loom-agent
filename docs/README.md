# Loom Agent Framework Documentation

> Production-ready Python Agent framework with enterprise-grade reliability and observability

Version: 0.0.5

---

## 📚 Documentation Index

### Getting Started

- **[Quick Start](QUICKSTART.md)** - Get started with Loom in 5 minutes
- **[User Guide](LOOM_USER_GUIDE.md)** - Complete guide for using Loom
- **[Quick Reference](QUICK_REFERENCE.md)** - Cheat sheet for common operations

### Core Concepts

- **[Framework Guide](LOOM_FRAMEWORK_GUIDE.md)** - Understanding the Loom framework architecture
- **[Agent Events Guide](agent_events_guide.md)** - Working with agent lifecycle events
- **[Agent Permissions](AGENT_PERMISSIONS.md)** - Managing agent permissions and security

### Features & Capabilities

#### RAG & Retrieval
- **[RAG Guide](LOOM_RAG_GUIDE.md)** - Retrieval-Augmented Generation with Loom
- **[Embedding Retriever Guide](EMBEDDING_RETRIEVER_GUIDE.md)** - Semantic search using embeddings
- **[Vector Store Setup](VECTOR_STORE_SETUP_GUIDE.md)** - Setting up vector stores (FAISS, Milvus, Qdrant)

#### Tools & Extensions
- **[Tools Guide](TOOLS_GUIDE.md)** - Creating and using tools with agents
- **[Agent Packs API](AGENT_PACKS_API.md)** - Building and using agent packs

#### Integrations
- **[MCP Integration](LOOM_MCP_INTEGRATION.md)** - Model Context Protocol integration

### Production & Deployment

- **[Production Guide](PRODUCTION_GUIDE.md)** - Best practices for production deployment
  - Monitoring and observability
  - Error handling and resilience
  - Performance optimization
  - Security considerations

### Advanced Topics

See the `user/` directory for additional advanced documentation:
- [API Reference](user/api-reference.md)
- [Advanced User Guide](user/user-guide.md)
- [Getting Started (Alternative)](user/getting-started.md)

---

## 🚀 Quick Links

### Installation

```bash
pip install loom-agent
```

### Basic Example

```python
from loom import agent

# Create an agent
my_agent = agent(
    provider="openai",
    model="gpt-4o",
    tools=[my_tool]
)

# Use the agent
result = await my_agent.ainvoke("Your query here")
```

### Common Use Cases

1. **[Building a RAG System](LOOM_RAG_GUIDE.md)** - Semantic search and question answering
2. **[Creating Tools](TOOLS_GUIDE.md)** - Extend agent capabilities with custom tools
3. **[Agent Events](agent_events_guide.md)** - Monitor and react to agent behavior
4. **[Production Deployment](PRODUCTION_GUIDE.md)** - Deploy agents to production

---

## 📖 Document Organization

- **`docs/`** - User-facing documentation (this directory)
- **`docs_dev/`** - Development and design documents (not in git)
- **`examples/`** - Code examples and tutorials

---

## 🔗 Additional Resources

- [GitHub Repository](https://github.com/kongusen/loom-agent)
- [PyPI Package](https://pypi.org/project/loom-agent/)
- [Issue Tracker](https://github.com/kongusen/loom-agent/issues)

---

## 📝 Contributing to Documentation

If you find errors or want to improve the documentation:

1. Check if the document you want to edit is in `docs/` (user documentation)
2. Submit a pull request with your changes
3. Ensure your changes follow the existing documentation style

---

**Last Updated**: October 2024 | **Version**: 0.0.5
