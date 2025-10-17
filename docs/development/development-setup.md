# Development Setup

Loom Agent开发环境设置指南

---

## 系统要求

- **Python**: 3.11 或更高版本
- **Poetry**: 1.7+ (Python包管理工具)
- **Git**: 2.0+
- **操作系统**: Linux, macOS, Windows

---

## 快速设置

### 1. 克隆仓库

```bash
git clone https://github.com/kongusen/loom-agent.git
cd loom-agent
```

### 2. 安装Poetry

```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# 或使用pip
pip install poetry
```

验证安装：

```bash
poetry --version
# 应输出: Poetry (version 2.2.1) 或更高版本
```

### 3. 安装依赖

```bash
# 安装所有依赖（包括开发依赖）
poetry install --with dev

# 安装所有可选依赖
poetry install --with dev --extras all
```

### 4. 激活虚拟环境

```bash
# 方式1: 使用poetry shell
poetry shell

# 方式2: 使用poetry run
poetry run python your_script.py
```

---

## 开发工具

### 代码格式化

```bash
# Black - 代码格式化
poetry run black loom/ tests/

# isort - 导入排序
poetry run isort loom/ tests/

# 检查（不修改）
poetry run black --check loom/ tests/
poetry run isort --check loom/ tests/
```

### 类型检查

```bash
# mypy - 静态类型检查
poetry run mypy loom/
```

### Pre-commit Hooks

安装pre-commit hooks自动运行检查：

```bash
# 安装hooks
poetry run pre-commit install

# 手动运行所有检查
poetry run pre-commit run --all-files
```

---

## 运行测试

### 基础测试

```bash
# 运行所有测试
poetry run pytest

# 详细输出
poetry run pytest -v

# 运行特定测试文件
poetry run pytest tests/unit/test_agent.py

# 运行特定测试函数
poetry run pytest tests/unit/test_agent.py::test_agent_creation
```

### 测试覆盖率

```bash
# 生成覆盖率报告
poetry run pytest --cov=loom --cov-report=html --cov-report=term

# 查看HTML报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### 测试类型

```bash
# 单元测试
poetry run pytest tests/unit/ -v

# 集成测试
poetry run pytest tests/integration/ -v

# 契约测试
poetry run pytest tests/contract/ -v
```

### 测试选项

```bash
# 并行运行测试（需要pytest-xdist）
poetry run pytest -n auto

# 只运行失败的测试
poetry run pytest --lf

# 详细输出（显示print语句）
poetry run pytest -v -s

# 跳过慢速测试
poetry run pytest -m "not slow"
```

---

## 项目结构

```
loom-agent/
├── loom/                      # 主要代码
│   ├── __init__.py           # 包初始化，导出公共API
│   ├── agent.py              # Agent核心实现
│   ├── agents/               # Agent注册表和引用
│   ├── builtin/              # 内置实现
│   │   ├── llms/            # LLM实现（OpenAI, Anthropic等）
│   │   ├── memory/          # 内存实现
│   │   ├── tools/           # 内置工具
│   │   ├── compression/     # 压缩策略
│   │   ├── embeddings/      # 嵌入模型
│   │   └── retriever/       # 检索器
│   ├── callbacks/            # 回调系统
│   ├── components/           # 核心组件
│   ├── core/                 # 核心抽象和接口
│   ├── interfaces/           # 接口定义
│   ├── llm/                  # LLM管理
│   ├── mcp/                  # MCP协议支持
│   └── observability/        # 可观测性（日志、指标）
├── tests/                    # 测试代码
│   ├── unit/                # 单元测试
│   ├── integration/         # 集成测试
│   └── contract/            # 契约测试
├── docs/                     # 文档
│   ├── user/                # 用户文档
│   └── development/         # 开发者文档
├── scripts/                  # 实用脚本
├── pyproject.toml           # Poetry配置和项目元数据
└── README.md                # 项目介绍
```

---

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发代码

```python
# 在loom/下添加你的代码
# 确保有类型提示和文档字符串

class YourNewFeature:
    """
    Your feature description.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Example:
        >>> feature = YourNewFeature()
        >>> feature.run()
    """
    def __init__(self, param1: str, param2: int):
        self.param1 = param1
        self.param2 = param2

    async def run(self) -> str:
        """Run the feature."""
        return f"Result: {self.param1} {self.param2}"
```

### 3. 编写测试

```python
# tests/unit/test_your_feature.py
import pytest
from loom.your_feature import YourNewFeature

@pytest.mark.asyncio
async def test_your_feature():
    feature = YourNewFeature("test", 42)
    result = await feature.run()
    assert result == "Result: test 42"
```

### 4. 运行检查

```bash
# 格式化
black loom/ tests/
isort loom/ tests/

# 类型检查
mypy loom/

# 测试
pytest -v

# 或使用检查脚本
./scripts/check_ready.sh
```

### 5. 提交

```bash
git add .
git commit -m "feat(component): add your feature"
git push origin feature/your-feature-name
```

### 6. 创建Pull Request

在GitHub上创建PR，等待review。

---

## IDE配置

### VS Code

推荐的 `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

推荐扩展：
- Python
- Pylance
- Python Test Explorer
- GitLens

### PyCharm

1. 配置Python解释器：
   - File → Settings → Project → Python Interpreter
   - 选择Poetry环境

2. 启用格式化：
   - File → Settings → Tools → Black
   - 勾选 "On save"

3. 配置测试：
   - File → Settings → Tools → Python Integrated Tools
   - Default test runner: pytest

---

## 调试

### VS Code调试配置

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Pytest",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "${file}"],
      "console": "integratedTerminal"
    }
  ]
}
```

### 调试技巧

```python
# 使用pdb
import pdb; pdb.set_trace()

# 使用breakpoint() (Python 3.7+)
breakpoint()

# 使用structlog查看日志
import structlog
logger = structlog.get_logger()
logger.debug("debug message", variable=value)
```

---

## 常见问题

### Poetry相关

**Q: Poetry安装慢怎么办？**

```bash
# 使用国内镜像
poetry config repositories.pypi https://mirrors.aliyun.com/pypi/simple/
```

**Q: 如何更新依赖？**

```bash
# 更新所有依赖
poetry update

# 更新特定依赖
poetry update package-name
```

**Q: 如何添加新依赖？**

```bash
# 添加运行时依赖
poetry add package-name

# 添加开发依赖
poetry add --group dev package-name

# 添加可选依赖
poetry add --optional package-name
```

### 测试相关

**Q: 测试失败怎么办？**

```bash
# 查看详细错误
poetry run pytest -v -s

# 只运行失败的测试
poetry run pytest --lf

# 进入pdb调试
poetry run pytest --pdb
```

**Q: 如何测试异步代码？**

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

### 代码质量

**Q: 如何修复类型错误？**

```bash
# 运行mypy查看错误
poetry run mypy loom/

# 查看特定文件
poetry run mypy loom/your_file.py

# 忽略特定错误（不推荐）
# type: ignore
```

---

## 有用的命令

```bash
# 查看项目信息
poetry show --tree

# 查看已安装的包
poetry show

# 导出requirements.txt
poetry export -f requirements.txt --output requirements.txt

# 清理缓存
poetry cache clear pypi --all

# 构建包
poetry build

# 发布到PyPI（仅维护者）
poetry publish
```

---

## 下一步

- 阅读 [contributing.md](contributing.md) 了解贡献指南
- 查看 [testing.md](testing.md) 了解测试详情
- 参考 [publishing.md](publishing.md) 了解发布流程

---

**准备好开始开发了？查看 [contributing.md](contributing.md)！**
