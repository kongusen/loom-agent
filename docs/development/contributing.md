# Contributing to Loom Agent

感谢你对Loom Agent的贡献兴趣！

---

## 快速开始

### 1. Fork和Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/loom-agent.git
cd loom-agent
```

### 2. 设置开发环境

参见 [development-setup.md](development-setup.md)

### 3. 创建分支

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

---

## 开发流程

### 代码规范

- **Python版本**: 3.11+
- **代码风格**: 使用Black和isort
- **类型提示**: 使用完整类型提示
- **文档字符串**: 所有公共API必须有docstring

### 运行格式化工具

```bash
# 格式化代码
black loom/ tests/
isort loom/ tests/

# 类型检查
mypy loom/
```

### 提交代码前检查

```bash
# 运行所有检查
./scripts/check_ready.sh

# 或手动运行
black --check loom/ tests/
isort --check loom/ tests/
mypy loom/
pytest -v
```

---

## 测试

### 运行测试

```bash
# 所有测试
poetry run pytest -v

# 特定测试文件
poetry run pytest tests/unit/test_agent.py -v

# 带覆盖率
poetry run pytest --cov=loom --cov-report=html
```

### 编写测试

- **单元测试**: `tests/unit/` - 测试单个函数/类
- **集成测试**: `tests/integration/` - 测试组件交互
- **契约测试**: `tests/contract/` - 测试接口契约

示例：

```python
# tests/unit/test_new_feature.py
import pytest
from loom.new_feature import NewFeature

@pytest.mark.asyncio
async def test_new_feature():
    feature = NewFeature()
    result = await feature.run()
    assert result == expected_value
```

---

## 提交规范

### Commit Message格式

使用语义化提交信息：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型** (type):
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更改
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 添加测试
- `chore`: 构建/工具变更

**示例**:

```
feat(agent): add streaming support

Add streaming API for real-time output from agents.
This allows users to receive partial results as they
are generated.

Closes #123
```

```
fix(memory): resolve memory leak in persistent storage

The persistent memory was not properly closing database
connections, causing memory leaks in long-running agents.

Fixes #456
```

---

## Pull Request流程

### 1. 更新你的分支

```bash
git fetch upstream
git rebase upstream/main
```

### 2. 推送到你的Fork

```bash
git push origin feature/your-feature-name
```

### 3. 创建Pull Request

访问GitHub并创建PR，确保：

- [ ] 标题清晰描述变更
- [ ] 描述说明为什么需要这个变更
- [ ] 引用相关的Issue
- [ ] 所有测试通过
- [ ] 代码已格式化
- [ ] 添加了必要的文档

### 4. Code Review

- 响应review意见
- 根据反馈修改代码
- 保持commit历史清晰

### 5. 合并

维护者会合并你的PR

---

## 贡献类型

### 报告Bug

使用GitHub Issues报告bug，包含：

- 清晰的标题
- 详细的描述
- 复现步骤
- 预期行为vs实际行为
- Python版本、操作系统等环境信息
- 最小可复现示例代码

### 功能请求

使用GitHub Issues提出功能请求，包含：

- 功能描述
- 使用场景
- 预期API示例
- 为什么这个功能有用

### 改进文档

文档改进总是受欢迎的：

- 修正错别字
- 改进示例代码
- 添加缺失的文档
- 改善文档结构

### 添加示例

在 `docs/user/examples/` 添加示例：

- 完整的代码示例
- 清晰的注释
- 实际使用场景
- 预期输出

---

## 代码审查标准

维护者会检查：

1. **功能性**
   - 代码是否解决了问题
   - 是否引入新的bug
   - 边缘情况处理

2. **代码质量**
   - 遵循项目代码风格
   - 有适当的类型提示
   - 有清晰的文档字符串
   - 命名清晰易懂

3. **测试**
   - 有充分的测试覆盖
   - 测试用例清晰
   - 测试通过

4. **文档**
   - 更新了相关文档
   - API变更有文档说明
   - 示例代码正确

5. **向后兼容**
   - 不破坏现有API
   - 如需破坏性变更，有明确说明

---

## 开发环境建议

### IDE配置

推荐使用：
- **VS Code** + Python扩展
- **PyCharm Professional**

### 有用的工具

```bash
# 安装pre-commit hooks
pre-commit install

# 自动运行检查
pre-commit run --all-files
```

### 调试技巧

```python
# 使用structlog查看详细日志
import structlog
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(10))

# 在代码中添加断点
import pdb; pdb.set_trace()
```

---

## 社区准则

### 行为准则

- 尊重所有贡献者
- 保持专业和建设性的讨论
- 欢迎新人和问题
- 专注于对项目最有利的事情

### 沟通渠道

- **GitHub Issues**: Bug报告、功能请求
- **GitHub Discussions**: 一般讨论、问题
- **Pull Requests**: 代码review

---

## 获取帮助

遇到问题？

1. 查看 [development-setup.md](development-setup.md)
2. 搜索已有的Issues
3. 在GitHub Discussions提问
4. 联系维护者

---

## 认可贡献者

所有贡献者都会在：
- README.md的Contributors部分
- 发布说明中（重要贡献）

---

## License

通过贡献代码，你同意你的贡献将使用MIT License。

---

**感谢你的贡献！** 🎉
