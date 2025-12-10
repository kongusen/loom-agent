# loom-agent v0.1.0 发布指南

**发布日期**: 2024-12-10
**目标版本**: v0.1.0

---

## 📋 发布前检查清单

### 1. 代码质量检查

- [ ] 所有测试通过
  ```bash
  pytest tests/
  ```

- [ ] 代码格式检查
  ```bash
  black loom/ tests/
  isort loom/ tests/
  ```

- [ ] 类型检查（可选）
  ```bash
  mypy loom/
  ```

### 2. 版本更新检查

- [x] `pyproject.toml` 版本已更新为 `0.1.0`
- [x] `CHANGELOG.md` 已添加 v0.1.0 发布说明
- [x] `README.md` roadmap 已更新
- [x] `README_EN.md` roadmap 已更新

### 3. 文档完整性检查

- [x] 中文 README.md 完整
- [x] 英文 README_EN.md 完整
- [x] CHANGELOG.md 包含详细的变更说明
- [x] 示例代码可运行
- [x] API 文档准确

---

## 🚀 发布步骤

### 步骤 1: 环境准备

#### 1.1 确保 Poetry 已安装

```bash
poetry --version
```

如果未安装：
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### 1.2 确保有 PyPI 访问权限

检查 PyPI token 是否配置：
```bash
poetry config pypi-token.pypi --list
```

如果未配置，设置 PyPI token：
```bash
poetry config pypi-token.pypi <your-pypi-token>
```

获取 PyPI token: https://pypi.org/manage/account/token/

---

### 步骤 2: 本地验证

#### 2.1 运行所有测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行 Crew 系统测试
pytest tests/unit/crew/ -v

# 运行插件系统测试
pytest tests/unit/plugins/ -v
```

**预期结果**: 141 个测试全部通过

#### 2.2 本地构建测试

```bash
# 清理旧的构建文件
rm -rf dist/ build/ *.egg-info

# 构建包
poetry build
```

**预期输出**:
```
Building loom-agent (0.1.0)
  - Building sdist
  - Built loom-agent-0.1.0.tar.gz
  - Building wheel
  - Built loom_agent-0.1.0-py3-none-any.whl
```

#### 2.3 本地安装测试

```bash
# 创建临时虚拟环境
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# 从本地 wheel 安装
pip install dist/loom_agent-0.1.0-py3-none-any.whl

# 测试导入
python -c "import loom; print(loom.__version__)"

# 测试 Crew 系统
python -c "from loom.crew import Crew; print('Crew OK')"

# 测试插件系统
python -c "from loom.plugins import ToolPluginManager; print('Plugins OK')"

# 退出测试环境
deactivate
rm -rf test_env
```

---

### 步骤 3: Git 提交和打标签

#### 3.1 提交所有变更

```bash
# 检查状态
git status

# 添加所有变更
git add .

# 创建提交
git commit -m "Release v0.1.0 - Multi-Agent Collaboration & Tool Plugin Ecosystem

- Add Crew multi-agent collaboration system
- Add Tool plugin ecosystem
- Add bilingual documentation (Chinese + English)
- Update version to 0.1.0
- Update CHANGELOG.md with v0.1.0 release notes
"

# 推送到远程
git push origin main
```

#### 3.2 创建 Git 标签

```bash
# 创建带注释的标签
git tag -a v0.1.0 -m "v0.1.0 - Multi-Agent Collaboration & Tool Plugin Ecosystem

Major Features:
- Crew multi-agent collaboration system (2,000+ lines)
- Tool plugin ecosystem (1,200+ lines)
- Bilingual documentation (3,000+ lines)
- 141 comprehensive tests (100% pass rate)

See CHANGELOG.md for full details.
"

# 推送标签到远程
git push origin v0.1.0
```

---

### 步骤 4: 发布到 PyPI

#### 4.1 发布到 TestPyPI（可选但推荐）

```bash
# 配置 TestPyPI token
poetry config repositories.testpypi https://test.pypi.org/legacy/
poetry config pypi-token.testpypi <your-testpypi-token>

# 发布到 TestPyPI
poetry publish -r testpypi

# 从 TestPyPI 安装测试
pip install --index-url https://test.pypi.org/simple/ loom-agent==0.1.0
```

#### 4.2 发布到 PyPI（正式发布）

```bash
# 确保已构建最新版本
poetry build

# 发布到 PyPI
poetry publish
```

**预期输出**:
```
Publishing loom-agent (0.1.0) to PyPI
 - Uploading loom-agent-0.1.0.tar.gz 100%
 - Uploading loom_agent-0.1.0-py3-none-any.whl 100%
```

#### 4.3 验证 PyPI 发布

等待 1-2 分钟后：

```bash
# 检查 PyPI 页面
# https://pypi.org/project/loom-agent/0.1.0/

# 在新环境中安装
pip install loom-agent==0.1.0

# 验证版本
python -c "import loom; print(loom.__version__)"  # 应输出: 0.1.0

# 验证 Crew 系统
python -c "from loom.crew import Crew; print('Crew system available')"

# 验证插件系统
python -c "from loom.plugins import ToolPluginManager; print('Plugin system available')"
```

---

### 步骤 5: 创建 GitHub Release

#### 5.1 通过 GitHub Web 界面创建

1. 访问: https://github.com/kongusen/loom-agent/releases/new
2. **Tag**: 选择 `v0.1.0`
3. **Release title**: `v0.1.0 - Multi-Agent Collaboration & Tool Plugin Ecosystem`
4. **Description**: 复制 `GITHUB_RELEASE_v0_1_0.md` 的内容
5. **Assets**: 自动从 PyPI 链接，或手动上传：
   - `dist/loom-agent-0.1.0.tar.gz`
   - `dist/loom_agent-0.1.0-py3-none-any.whl`
6. 点击 **Publish release**

#### 5.2 通过 GitHub CLI 创建（可选）

```bash
# 安装 GitHub CLI
# macOS: brew install gh
# Windows: choco install gh

# 登录
gh auth login

# 创建 release
gh release create v0.1.0 \
  --title "v0.1.0 - Multi-Agent Collaboration & Tool Plugin Ecosystem" \
  --notes-file GITHUB_RELEASE_v0_1_0.md \
  dist/loom-agent-0.1.0.tar.gz \
  dist/loom_agent-0.1.0-py3-none-any.whl
```

---

### 步骤 6: 发布后验证

#### 6.1 验证 PyPI

- [ ] PyPI 页面显示正确: https://pypi.org/project/loom-agent/
- [ ] 版本号为 0.1.0
- [ ] 描述和文档链接正确
- [ ] 可以通过 pip 安装

#### 6.2 验证 GitHub Release

- [ ] GitHub Release 页面显示: https://github.com/kongusen/loom-agent/releases/tag/v0.1.0
- [ ] Release notes 完整
- [ ] 资产文件可下载

#### 6.3 验证文档

- [ ] README.md 显示正确
- [ ] README_EN.md 显示正确
- [ ] CHANGELOG.md 包含 v0.1.0
- [ ] 所有文档链接有效

#### 6.4 功能验证

```bash
# 创建新的测试环境
python -m venv verify_env
source verify_env/bin/activate

# 从 PyPI 安装
pip install loom-agent==0.1.0

# 测试基本功能
python << EOF
import asyncio
from loom import agent

async def test():
    # 测试基本 agent
    my_agent = agent(
        provider="openai",
        model="gpt-4",
        system_instructions="Test"
    )
    print("✓ Basic agent creation OK")

    # 测试 Crew 系统
    from loom.crew import Crew, Role
    roles = [Role(name="test", goal="test", backstory="test")]
    crew = Crew(roles=roles, llm=None)
    print("✓ Crew system OK")

    # 测试插件系统
    from loom.plugins import ToolPluginManager
    manager = ToolPluginManager()
    print("✓ Plugin system OK")

asyncio.run(test())
EOF

# 清理
deactivate
rm -rf verify_env
```

---

### 步骤 7: 社交媒体和社区通知

#### 7.1 发布公告

在以下渠道发布公告：

- [ ] **GitHub Discussions**: 创建 "v0.1.0 Released" 主题
- [ ] **Twitter/X**: 发布发布推文
- [ ] **Reddit**: 在 r/Python, r/MachineLearning 发布
- [ ] **Hacker News**: 提交 Show HN
- [ ] **Discord/Slack**: 在相关社区发布

#### 7.2 公告模板

**标题**: 🎉 loom-agent v0.1.0 Released - Multi-Agent Collaboration & Tool Plugins

**内容**:
```
We're excited to announce loom-agent v0.1.0! 🚀

This major release introduces:
✅ Crew multi-agent collaboration (like CrewAI/AutoGen)
✅ Tool plugin ecosystem for extensibility
✅ Complete bilingual documentation
✅ 141 comprehensive tests

Key advantages over other frameworks:
- Event Sourcing for complete audit trails
- Crash Recovery from any breakpoint
- HITL (Human-in-the-Loop) with lifecycle hooks
- Context Debugging to understand LLM decisions

Install: pip install loom-agent==0.1.0
GitHub: https://github.com/kongusen/loom-agent
Docs: https://github.com/kongusen/loom-agent#readme

#AI #LLM #Python #MultiAgent #OpenSource
```

---

## 🔄 回滚策略

如果发布后发现严重问题：

### 回滚 PyPI（不推荐）

PyPI 不允许删除已发布的版本，只能：

1. **发布补丁版本** (推荐)
   ```bash
   # 修复问题后发布 v0.1.1
   poetry version patch
   poetry build
   poetry publish
   ```

2. **标记版本为 yanked**
   ```bash
   # 通过 PyPI web 界面标记版本
   # 用户可以安装，但 pip 默认不会选择该版本
   ```

### 回滚 GitHub Release

```bash
# 删除 GitHub Release
gh release delete v0.1.0

# 删除 Git 标签
git tag -d v0.1.0
git push origin :refs/tags/v0.1.0
```

---

## 📝 发布后任务

- [ ] 监控 GitHub Issues 的反馈
- [ ] 回复社区问题
- [ ] 收集用户反馈
- [ ] 规划 v0.2.0 功能
- [ ] 更新文档（如有遗漏）

---

## 🆘 常见问题

### Q1: Poetry publish 失败

**问题**: `HTTP 403: Invalid or non-existent authentication`

**解决**:
```bash
# 重新配置 PyPI token
poetry config pypi-token.pypi <your-new-token>
```

### Q2: 版本号冲突

**问题**: `File already exists`

**解决**:
- PyPI 不允许重新上传同版本
- 必须增加版本号（如 0.1.1）

### Q3: 测试失败

**问题**: 某些测试在 CI/CD 失败

**解决**:
```bash
# 本地运行所有测试
pytest tests/ -v

# 检查特定失败测试
pytest tests/unit/crew/test_xxx.py -v -s
```

---

## 📞 联系方式

如有问题，请联系：
- **GitHub Issues**: https://github.com/kongusen/loom-agent/issues
- **Email**: wanghaishan0210@gmail.com

---

**发布清单最后检查**:

- [x] 版本号更新
- [x] CHANGELOG 更新
- [x] README 更新
- [x] 测试通过
- [ ] 本地构建成功
- [ ] Git 标签创建
- [ ] PyPI 发布
- [ ] GitHub Release
- [ ] 验证完成
- [ ] 社区通知

**祝发布顺利！** 🎉
