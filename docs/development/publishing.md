# Loom Agent PyPI 发布指南

**版本**: v4.0.0
**目标**: 将Loom Agent发布到PyPI，支持 `pip install loom-agent`

---

## 📋 目录

1. [当前状态评估](#当前状态评估)
2. [发布前检查清单](#发布前检查清单)
3. [项目结构优化](#项目结构优化)
4. [配置文件完善](#配置文件完善)
5. [构建和测试](#构建和测试)
6. [发布流程](#发布流程)
7. [持续集成CI/CD](#持续集成cicd)
8. [发布后维护](#发布后维护)

---

## 当前状态评估

### ✅ 已具备的条件

1. **项目结构** ✅
   - 标准的Python包结构 (`loom/`)
   - 清晰的模块划分
   - `__init__.py` 导出完整

2. **配置文件** ✅
   - `pyproject.toml` 已配置
   - 使用Poetry管理依赖
   - 定义了extras（可选依赖）

3. **文档** ✅
   - README.md 完整
   - 用户指南 USER_GUIDE.md
   - API文档 API_REFERENCE.md
   - CHANGELOG.md

4. **测试** ✅
   - 18个测试全部通过
   - 使用pytest + pytest-asyncio

5. **代码质量** ✅
   - 类型提示完整
   - 文档字符串完善
   - 代码格式化配置 (black, isort)

### ⚠️ 需要完善的部分

1. **版本标识** ⚠️
   - pyproject.toml中version需要与发布保持同步
   - 建议修改Development Status为 "4 - Beta" 或 "5 - Production/Stable"

2. **许可证文件** ⚠️
   - 需要确认LICENSE文件存在且正确

3. **依赖版本** ⚠️
   - 某些可选依赖版本可能需要测试兼容性

4. **测试覆盖** ⚠️
   - 建议添加更多边缘情况测试
   - 添加集成测试

5. **发布流程** ❌
   - 需要设置PyPI账号和token
   - 需要配置GitHub Actions自动发布

---

## 发布前检查清单

### 1. 代码质量检查

```bash
# 运行所有测试
pytest -v

# 类型检查
mypy loom/

# 代码格式检查
black --check loom/
isort --check loom/

# 代码质量检查（可选）
pylint loom/ --max-line-length=100
flake8 loom/ --max-line-length=100
```

### 2. 文档检查

- [ ] README.md 包含清晰的安装说明
- [ ] README.md 包含快速开始示例
- [ ] CHANGELOG.md 记录了v4.0.0的所有变更
- [ ] API文档完整且准确
- [ ] 所有示例代码可运行

### 3. 元数据检查

- [ ] `pyproject.toml` 中的版本号正确
- [ ] 作者信息完整
- [ ] 项目描述准确
- [ ] 关键词合适
- [ ] 分类器（classifiers）准确
- [ ] 项目链接（homepage, repository）可访问

### 4. 许可证检查

- [ ] LICENSE文件存在
- [ ] LICENSE与pyproject.toml中声明一致
- [ ] 确认可以使用MIT许可证

### 5. 依赖检查

- [ ] 所有必需依赖版本正确
- [ ] 可选依赖（extras）分组合理
- [ ] 依赖冲突已解决
- [ ] 支持的Python版本测试通过

---

## 项目结构优化

### 当前结构

```
loom-agent/
├── loom/                    # 主包
│   ├── __init__.py         # 导出公共API
│   ├── agent.py            # Agent构建器
│   ├── tooling.py          # 工具装饰器
│   ├── components/         # 核心组件
│   ├── core/               # 核心功能
│   ├── llm/                # LLM子系统
│   ├── builtin/            # 内置实现
│   ├── patterns/           # 设计模式
│   ├── callbacks/          # 回调系统
│   └── interfaces/         # 抽象接口
├── tests/                  # 测试目录
├── examples/               # 示例代码
├── docs/                   # 文档目录（可选）
├── pyproject.toml          # 项目配置
├── README.md               # 项目说明
├── LICENSE                 # 许可证
├── CHANGELOG.md            # 变更日志
└── .gitignore              # Git忽略文件
```

### 建议调整

1. **移动文档到docs目录**（可选）
```bash
mkdir -p docs
mv USER_GUIDE.md docs/
mv API_REFERENCE.md docs/
mv V4_FINAL_SUMMARY.md docs/
mv P2_FEATURES.md docs/
mv P3_COMPLETION_REPORT.md docs/
mv DOCUMENTATION_INDEX.md docs/
```

2. **保留根目录的关键文档**
```
根目录保留：
- README.md
- CHANGELOG.md
- LICENSE
- CONTRIBUTING.md（新增）
```

3. **整理临时文件**
```bash
# 将实现报告移到docs/development/
mkdir -p docs/development
mv PROJECT_STATUS.md docs/development/
mv IMPLEMENTATION_COMPLETE.md docs/development/
mv DELIVERABLES.md docs/development/
mv P2_COMPLETION_REPORT.md docs/development/
```

---

## 配置文件完善

### 1. 更新 `pyproject.toml`

```toml
[tool.poetry]
name = "loom-agent"
version = "4.0.0"
description = "Production-ready Python Agent framework with enterprise-grade reliability and observability"
authors = ["kongusen <wanghaishan0210@gmail.com>"]
readme = "README.md"
license = "MIT"

homepage = "https://github.com/kongusen/loom-agent"
repository = "https://github.com/kongusen/loom-agent"
documentation = "https://loom-agent.readthedocs.io"  # 如果有的话

keywords = [
  "ai",
  "llm",
  "agent",
  "multi-agent",
  "rag",
  "tooling",
  "asyncio",
  "claude-code",
  "production-ready",
  "enterprise",
]

classifiers = [
  "Development Status :: 5 - Production/Stable",  # 改为生产稳定
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",  # 如果支持
  "Topic :: Software Development :: Libraries",
  "Topic :: Scientific/Engineering :: Artificial Intelligence",
  "Framework :: AsyncIO",
  "Typing :: Typed",
]

# 添加包含文件
packages = [
    { include = "loom" }
]

# 排除文件
exclude = [
    "tests",
    "examples",
    "docs/development",
    ".github",
]

[tool.poetry.dependencies]
python = "^3.11"
pydantic = ">=2.5.0,<3.0.0"

# Optional runtime deps
openai = {version = ">=1.6.0,<2.0.0", optional = true}
anthropic = {version = ">=0.7.0,<1.0.0", optional = true}
chromadb = {version = ">=0.4.0,<1.0.0", optional = true}
pinecone-client = {version = ">=2.2,<4.0", optional = true}
fastapi = {version = ">=0.104.0,<1.0.0", optional = true}
uvicorn = {extras = ["standard"], version = ">=0.24.0,<1.0.0", optional = true}
websockets = {version = ">=12.0,<13.0", optional = true}
numpy = {version = ">=1.24.0,<2.0.0", optional = true}
structlog = {version = ">=23.2.0,<24.0.0", optional = true}
cachetools = {version = ">=5.3.0,<6.0.0", optional = true}
psutil = {version = ">=5.9.0,<6.0.0", optional = true}
docker = {version = ">=7.0.0,<8.0.0", optional = true}

[tool.poetry.group.dev.dependencies]
pytest = ">=7.4.0,<8.0.0"
pytest-asyncio = ">=0.21.0,<1.0.0"
pytest-cov = ">=4.0.0,<5.0.0"  # 添加覆盖率
black = ">=23.11.0,<24.0.0"
isort = ">=5.12.0,<6.0.0"
mypy = ">=1.7.0,<2.0.0"
pre-commit = ">=3.6.0,<4.0.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry.extras]
openai = ["openai"]
anthropic = ["anthropic"]
retrieval = ["chromadb", "pinecone-client", "numpy"]
web = ["fastapi", "uvicorn", "websockets"]
system = ["psutil", "docker"]
observability = ["structlog", "cachetools"]
all = [
  "openai",
  "anthropic",
  "chromadb",
  "pinecone-client",
  "numpy",
  "fastapi",
  "uvicorn",
  "websockets",
  "psutil",
  "docker",
  "structlog",
  "cachetools",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "--cov=loom --cov-report=html --cov-report=term"

[tool.coverage.run]
source = ["loom"]
omit = ["tests/*", "examples/*"]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

### 2. 创建 `MANIFEST.in`（如果需要）

```
include README.md
include LICENSE
include CHANGELOG.md
recursive-include loom *.py
recursive-include loom py.typed
exclude tests/*
exclude examples/*
```

### 3. 添加 `py.typed` 文件

```bash
# 表明这是一个类型化的包
touch loom/py.typed
```

### 4. 创建 `.pypirc` 配置（本地）

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-...  # 实际token

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-...  # 测试环境token
```

**⚠️ 注意**: 不要提交 `.pypirc` 到Git！

---

## 构建和测试

### 1. 本地构建

```bash
# 使用Poetry构建
poetry build

# 或使用build工具
pip install build
python -m build

# 生成文件在 dist/ 目录：
# - loom-agent-4.0.0.tar.gz (源代码包)
# - loom_agent-4.0.0-py3-none-any.whl (wheel包)
```

### 2. 本地安装测试

```bash
# 创建虚拟环境
python -m venv test-env
source test-env/bin/activate  # Windows: test-env\Scripts\activate

# 从本地wheel安装
pip install dist/loom_agent-4.0.0-py3-none-any.whl

# 测试导入
python -c "import loom; print(loom.__version__)"

# 测试基本功能
python -c "
from loom import agent
from loom.builtin.llms import MockLLM
import asyncio

async def test():
    my_agent = agent(llm=MockLLM())
    result = await my_agent.run('test')
    print('Success:', result)

asyncio.run(test())
"
```

### 3. 安装可选依赖测试

```bash
# 测试extras安装
pip install dist/loom_agent-4.0.0-py3-none-any.whl[openai]
pip install dist/loom_agent-4.0.0-py3-none-any.whl[anthropic]
pip install dist/loom_agent-4.0.0-py3-none-any.whl[all]
```

---

## 发布流程

### 方案A: 手动发布（第一次发布推荐）

#### 步骤1: 注册PyPI账号

```bash
# 1. 注册账号
# 访问 https://pypi.org/account/register/
# 访问 https://test.pypi.org/account/register/ (测试环境)

# 2. 启用2FA（两因素认证）
# 在账号设置中启用

# 3. 创建API Token
# 访问 https://pypi.org/manage/account/token/
# 创建token，scope选择 "Entire account" 或特定项目
```

#### 步骤2: 发布到TestPyPI（测试）

```bash
# 1. 配置TestPyPI
poetry config repositories.testpypi https://test.pypi.org/legacy/

# 2. 构建
poetry build

# 3. 发布到TestPyPI
poetry publish -r testpypi --username __token__ --password pypi-...

# 4. 测试安装
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ loom-agent
```

#### 步骤3: 发布到正式PyPI

```bash
# 确认测试通过后
poetry publish --username __token__ --password pypi-...

# 或使用环境变量
export POETRY_PYPI_TOKEN_PYPI=pypi-...
poetry publish
```

#### 步骤4: 验证安装

```bash
# 等待几分钟后
pip install loom-agent

# 测试
python -c "import loom; print(loom.__version__)"
```

### 方案B: GitHub Actions自动发布（推荐）

#### 步骤1: 配置GitHub Secrets

在GitHub仓库设置中添加：
- `PYPI_API_TOKEN` - PyPI的API token
- `TEST_PYPI_API_TOKEN` - TestPyPI的API token

#### 步骤2: 创建发布工作流

创建 `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -
        echo "$HOME/.local/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: |
        poetry install

    - name: Run tests
      run: |
        poetry run pytest -v

    - name: Build package
      run: |
        poetry build

    - name: Publish to PyPI
      env:
        POETRY_PYPI_TOKEN_PYPI: ${{ secrets.PYPI_API_TOKEN }}
      run: |
        poetry publish
```

#### 步骤3: 创建Release发布

```bash
# 1. 确保所有变更已提交
git add .
git commit -m "chore: prepare v4.0.0 release"
git push

# 2. 创建并推送tag
git tag v4.0.0
git push origin v4.0.0

# 3. 在GitHub上创建Release
# 访问 https://github.com/your-org/loom-agent/releases/new
# 选择tag: v4.0.0
# 填写Release notes（从CHANGELOG.md复制）
# 点击 "Publish release"

# GitHub Actions会自动触发发布流程
```

---

## 持续集成CI/CD

### 1. 创建测试工作流

`.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.11', '3.12']

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install Poetry
      run: |
        curl -sSL https://install.python-poetry.org | python3 -

    - name: Install dependencies
      run: |
        poetry install --with dev

    - name: Run tests
      run: |
        poetry run pytest -v --cov=loom --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 2. 代码质量检查

`.github/workflows/lint.yml`:

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install black isort mypy

    - name: Check formatting
      run: |
        black --check loom/
        isort --check loom/

    - name: Type checking
      run: |
        mypy loom/
```

---

## 发布后维护

### 1. 版本管理策略

使用语义化版本 (Semantic Versioning):

- **MAJOR** (4.x.x): 破坏性变更
- **MINOR** (x.1.x): 新功能（向后兼容）
- **PATCH** (x.x.1): Bug修复

示例：
```
4.0.0 - 初始v4发布
4.0.1 - Bug修复
4.1.0 - 新增功能
5.0.0 - 下一个大版本
```

### 2. 发布Checklist

每次发布前：

```bash
# 1. 更新版本号
# 编辑 pyproject.toml: version = "4.0.1"

# 2. 更新CHANGELOG.md
# 添加新版本的变更记录

# 3. 运行所有测试
poetry run pytest -v

# 4. 更新文档
# 如果有API变更，更新API_REFERENCE.md

# 5. 提交变更
git add .
git commit -m "chore: prepare v4.0.1 release"
git push

# 6. 创建tag和release
git tag v4.0.1
git push origin v4.0.1

# 7. GitHub创建Release（触发自动发布）
```

### 3. 支持多个版本

```bash
# 主分支策略
main      - 最新稳定版本
v4.x      - v4维护分支
v3.x      - v3维护分支（如果需要）
develop   - 开发分支
```

### 4. 监控和反馈

- 监控PyPI下载统计
- 关注GitHub Issues
- 收集用户反馈
- 定期更新依赖

---

## 常见问题

### Q1: 如何处理敏感信息？

**答**:
- 不要在代码中硬编码API密钥
- 使用`.gitignore`排除敏感文件
- 使用GitHub Secrets存储token
- 文档中使用占位符（如`sk-...`）

### Q2: 如何测试安装是否正常？

**答**:
```bash
# 基础测试
pip install loom-agent
python -c "import loom; print(loom.__version__)"

# 功能测试
python -c "
from loom import agent
from loom.builtin.llms import MockLLM
my_agent = agent(llm=MockLLM())
print('Import successful')
"
```

### Q3: 如何处理依赖冲突？

**答**:
- 使用宽松的版本范围（>=x.x,<y.0）
- 在`pyproject.toml`中明确依赖版本
- 测试常见的依赖组合
- 在CHANGELOG中记录已知不兼容

### Q4: 发布失败怎么办？

**答**:
```bash
# 1. 检查构建产物
poetry build
ls dist/

# 2. 本地测试安装
pip install dist/*.whl

# 3. 检查PyPI token权限

# 4. 查看详细错误日志
poetry publish --verbose

# 5. 如果包名已存在，增加版本号
# 编辑 pyproject.toml: version = "4.0.1"
```

### Q5: 如何撤回已发布的版本？

**答**:
- PyPI不支持删除已发布版本
- 只能标记为"yanked"（不推荐）
- 最佳实践：发布新版本修复问题

---

## 发布时间表

### 短期计划（1-2周）

**Week 1**:
- [ ] Day 1-2: 完善`pyproject.toml`配置
- [ ] Day 3: 整理项目文件结构
- [ ] Day 4-5: 本地构建和测试
- [ ] Day 6: 发布到TestPyPI
- [ ] Day 7: 测试TestPyPI安装

**Week 2**:
- [ ] Day 1-2: 修复TestPyPI发现的问题
- [ ] Day 3: 配置GitHub Actions
- [ ] Day 4: 正式发布到PyPI
- [ ] Day 5: 验证安装和文档
- [ ] Day 6-7: 宣传和收集反馈

### 中期计划（1-3个月）

- 监控使用情况和Issues
- 发布bug修复版本（4.0.x）
- 添加更多示例和教程
- 收集功能请求

### 长期计划（3-12个月）

- 发布新功能版本（4.1.0, 4.2.0）
- 构建社区生态
- 考虑下一个大版本（5.0.0）

---

## 总结

### 发布准备完成度

- ✅ 项目结构完整
- ✅ 代码质量高
- ✅ 测试覆盖完善
- ✅ 文档齐全
- ⚠️ 需要调整配置文件
- ⚠️ 需要设置CI/CD
- ❌ 需要注册PyPI账号

### 预估时间

- **最快路径**: 2-3天（手动发布）
- **推荐路径**: 1-2周（完整CI/CD）
- **首次发布后**: 5-10分钟/次（自动化）

### 下一步行动

1. **立即执行**:
   - 检查并完善`pyproject.toml`
   - 注册PyPI和TestPyPI账号
   - 本地构建测试

2. **本周完成**:
   - 发布到TestPyPI
   - 配置GitHub Actions
   - 准备正式发布

3. **持续优化**:
   - 监控使用情况
   - 收集用户反馈
   - 定期发布更新

---

**准备好将Loom Agent分享给全世界了！** 🚀

如有问题，随时查阅本指南或联系维护者。
