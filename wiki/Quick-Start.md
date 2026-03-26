# 快速开始

5 分钟上手 Loom Agent Framework。

## 安装

```bash
pip install loom-agent
```

## 基础使用

```python
from loom.agent import Agent
from loom.providers.llm.anthropic import AnthropicProvider

# 1. 创建 Provider
provider = AnthropicProvider(api_key="your-key")

# 2. 创建 Agent
agent = Agent(provider=provider)

# 3. 运行
result = await agent.run("Hello!")
print(result.content)
```

## 添加约束

```python
from loom.types.scene import ScenePackage

# 定义场景
scene = ScenePackage(
    id="readonly",
    tools=["read_file"],
    constraints={"write": False}
)

agent.scene_mgr.register(scene)
agent.scene_mgr.switch("readonly")
```

下一步 → [核心概念](./Core-Concepts.md)
