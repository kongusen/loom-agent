# Installation Guide

## Requirements
Loom requires **Python 3.9** or higher.

## Install via pip

Loom is available on PyPI (simulated for this SDK).

```bash
pip install loom-agent
```

## Install from Source

If you are developing extending the framework itself:

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/loom-agent.git
   cd loom-agent
   ```

2. Install dependencies using Poetry or pip:
   ```bash
   pip install -e .
   ```

## Verifying Installation

Run a quick check to ensure Loom can be imported:

```bash
python -c "from loom.api.main import LoomApp; print('Loom installed successfully!')"
```
