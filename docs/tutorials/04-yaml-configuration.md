# 教程 4：使用 YAML 配置

> **学习目标**：学会使用 YAML 文件配置 Agent 和 Crew，实现声明式管理

## 为什么使用 YAML 配置？

YAML 配置提供了声明式的方式来管理 Agent 系统：

- **可读性强**：清晰的结构，易于理解和维护
- **版本控制**：配置文件可以纳入 Git 管理
- **环境分离**：开发、测试、生产环境使用不同配置
- **团队协作**：非程序员也能修改配置

## 基本配置结构

创建一个 `loom.yaml` 文件：

```yaml
version: "1.0"

# 控制配置（可选）
control:
  budget: 5000      # Token 预算
  depth: 10         # 最大深度

# 定义 Agents
agents:
  - name: my-agent
    role: "通用助手"

# 定义 Crews（可选）
crews:
  - name: my-team
    agents:
      - my-agent
```

## 加载配置文件

使用 `LoomApp.from_config()` 加载配置：

```python
from loom.api.main import LoomApp

# 加载配置文件
app, agents, crews = LoomApp.from_config("loom.yaml")

# 获取 Agent
my_agent = agents["my-agent"]

# 运行任务
result = await app.run(my_agent, "你好")
print(result)
```

## 使用预构建 Agent

配置文件支持使用预构建的 Agent 类型：

```yaml
agents:
  # 使用 CoderAgent
  - name: coder
    type: CoderAgent
    config:
      base_dir: ./src

  # 使用 AnalystAgent
  - name: analyst
    type: AnalystAgent
```

**可用的预构建类型**：
- `CoderAgent`：具有文件操作能力的编码 Agent
- `AnalystAgent`：具有计算能力的分析 Agent

## 使用自定义 Agent（带 Skills）

你也可以通过 `role` 和 `skills` 配置自定义 Agent：

```yaml
agents:
  # 自定义计算助手
  - name: calculator-agent
    role: "计算助手"
    skills:
      - calculator

  # 自定义文件助手
  - name: file-agent
    role: "文件助手"
    skills:
      - filesystem
    config:
      base_dir: ./data
```

**可用的 Skills**：
- `calculator`：数学计算能力
- `filesystem`：文件读写能力

## 配置 Crew

在配置文件中定义团队：

```yaml
agents:
  - name: writer
    role: "内容创作者"

  - name: reviewer
    role: "审稿人"

crews:
  - name: writing-team
    agents:
      - writer
      - reviewer
```

使用配置的 Crew：

```python
from loom.api.main import LoomApp

app, agents, crews = LoomApp.from_config("loom.yaml")

# 获取 Crew
team = crews["writing-team"]

# 运行任务
result = await app.run(team, "写一篇关于 Python 的文章")
print(result)
```

## 完整示例

这是一个完整的配置文件示例：

```yaml
version: "1.0"

control:
  budget: 5000
  depth: 10

agents:
  # 预构建 Agent
  - name: coder
    type: CoderAgent
    config:
      base_dir: ./src

  - name: analyst
    type: AnalystAgent

  # 自定义 Agent
  - name: calculator-agent
    role: "计算助手"
    skills:
      - calculator

crews:
  - name: dev-team
    agents:
      - coder
      - analyst
```

使用这个配置：

```python
from loom.api.main import LoomApp

# 加载配置
app, agents, crews = LoomApp.from_config("loom.yaml")

# 使用单个 Agent
coder = agents["coder"]
result = await app.run(coder, "创建一个 hello.py 文件")

# 使用 Crew
team = crews["dev-team"]
result = await app.run(team, "分析并优化代码")
```

## 下一步

🎉 恭喜！你已经完成了所有核心教程。

**继续学习：**
- 📖 [操作指南](../guides/) - 解决具体问题
- 💡 [概念文档](../concepts/) - 深入理解原理
- 📚 [API 参考](../reference/) - 查阅完整 API
