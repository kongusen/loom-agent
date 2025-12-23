# Contributing to Loom Agent

Thank you for your interest in contributing to Loom Agent! 🎉

## Quick Links

- **User Guide (English)**: [docs/index.md](docs/index.md)
- **User Guide (Chinese)**: [docs/zh/index.md](docs/zh/index.md)
- **Issues**: [GitHub Issues](https://github.com/kongusen/loom-agent/issues)

## How to Contribute

1.  **Fork the repository** on GitHub.
2.  **Clone your fork**:
    ```bash
    git clone https://github.com/YOUR_USERNAME/loom-agent.git
    cd loom-agent
    ```
3.  **Install dependencies**:
    ```bash
    pip install poetry
    poetry install --with dev
    ```
4.  **Create a branch**: `git checkout -b feature/your-feature-name`
5.  **Make your changes** and add tests.
6.  **Run tests**:
    ```bash
    poetry run pytest
    ```
7.  **Submit a Pull Request**.

## Code Style

- We use `black` for formatting.
- We use `mypy` for type checking.
- We use `pydantic` heavily for data models.

## Documentation

If you are updating documentation, please try to keep both English (`docs/`) and Chinese (`docs/zh/`) sections in sync if possible. If not, just update the English one and open an issue for translation.
