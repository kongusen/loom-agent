# Contributing to Loom Agent

Thank you for your interest in contributing to Loom Agent! 🎉

## Quick Links

- **Documentation Home**: [docs/README.md](docs/README.md)
- **Axiomatic Framework**: [docs/concepts/axiomatic-framework.md](docs/concepts/axiomatic-framework.md)
- **Getting Started**: [docs/usage/getting-started.md](docs/usage/getting-started.md)
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

We follow a structured documentation system organized by purpose:

- **`docs/concepts/`**: Theoretical foundations and axiomatic framework
- **`docs/usage/`**: User guides and API references
- **`docs/framework/`**: Core architecture documentation
- **`docs/features/`**: Feature-specific documentation
- **`docs/patterns/`**: Design patterns and best practices
- **`docs/optimization/`**: Performance optimization guides

When updating documentation:
1. Place new docs in the appropriate category
2. Update the main [docs/README.md](docs/README.md) navigation if adding new sections
3. Ensure code examples are tested and working
4. Use clear, concise language suitable for both beginners and advanced users
