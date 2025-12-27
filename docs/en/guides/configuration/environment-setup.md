# Environment Setup

> **Problem-Oriented** - Learn to configure loom-agent development and production environments

## Python Environment

### System Requirements

- Python 3.11+
- pip or poetry

### Creating Virtual Environment

```bash
# Using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Using conda
conda create -n loom python=3.11
conda activate loom
```

## Installing Dependencies

### Basic Installation

```bash
pip install loom-agent
```

### Full Installation (includes all features)

```bash
pip install loom-agent[all]
```

### On-demand Installation

```bash
# OpenAI support
pip install loom-agent[llm]

# Anthropic support
pip install loom-agent[anthropic]

# Visualization tools
pip install loom-agent[studio]
```

## Environment Variable Configuration

### Creating .env File

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_API_KEY=sk-ant-...
```

### Loading Environment Variables

```python
from dotenv import load_dotenv
load_dotenv()
```

## Verify Installation

```python
import loom
print(f"loom-agent version: {loom.__version__}")

# Test basic functionality
from loom.weave import create_agent, run
agent = create_agent("test", role="Test")
print("✓ Installation successful")
```

## Related Documentation

- [Configuring LLM Providers](llm-providers.md) - Configure LLM providers
- [Production Deployment](../deployment/production-deployment.md) - Production environment deployment

