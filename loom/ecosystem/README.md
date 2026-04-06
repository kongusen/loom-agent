# Loom Ecosystem - Skill, Plugin, MCP

基于 Claude Code 架构的生态系统实现

## 架构概览

```
loom/ecosystem/
├── skill.py          # Skill 系统（可复用提示词）
├── plugin.py         # Plugin 系统（扩展包）
├── mcp.py           # MCP 集成（Model Context Protocol）
└── integration.py   # 生态整合
```

## 1. Skill 系统

### 特性
- Markdown 格式，支持 YAML frontmatter
- 按需加载（lazy loading）
- 任务匹配（whenToUse）
- 工具限制（allowedTools）

### 示例

```markdown
---
name: code-review
description: Review code systematically
whenToUse: review code, check quality
allowedTools: [read_file, grep]
---

# Code Review

Review the code for:
1. Best practices
2. Security issues
3. Performance
```

### 使用

```python
from loom.ecosystem.skill import SkillRegistry, SkillLoader

registry = SkillRegistry()
SkillLoader.load_from_directory(Path("skills/"), registry)

# 任务匹配
matched = registry.match_task("I need to review code")
skill = registry.get("code-review")
```

## 2. Plugin 系统

### 特性
- plugin.json manifest
- 可包含 skills、MCP servers、hooks
- 依赖管理
- 启用/禁用控制

### plugin.json 格式

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "skills": ["skills/"],
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server"]
    }
  }
}
```

### 使用

```python
from loom.ecosystem.plugin import PluginLoader

loader = PluginLoader()
plugin = loader.load_plugin(Path("my-plugin/"))
```

## 3. MCP 集成

### 特性
- 多种传输协议（stdio/sse/http/ws）
- 环境变量替换
- 作用域隔离
- Instructions 注入到 system prompt

### 配置示例

```python
from loom.ecosystem.mcp import MCPBridge, MCPServerConfig, MCPTransportType

bridge = MCPBridge()
config = MCPServerConfig(
    type=MCPTransportType.STDIO,
    command="uvx",
    args=["mcp-server-git"],
    env={"GIT_ROOT": "${CLAUDE_PLUGIN_ROOT}"}
)
bridge.register_server("git", config)
```

## 4. 生态整合

### EcosystemManager

统一管理 Skill、Plugin、MCP：

```python
from loom.ecosystem.integration import EcosystemManager

manager = EcosystemManager()

# 加载用户 skills
manager.load_user_skills(Path("~/.loom/skills"))

# 加载 plugins（自动加载其中的 skills 和 MCP servers）
manager.load_plugins(Path("~/.loom/plugins"))

# 获取 system prompt 注入
additions = manager.get_system_prompt_additions()
```

## 参考 Claude Code 的设计

### 1. Skill 加载机制
- 懒加载：只在需要时加载 skill 内容
- 文件监听：自动检测 skill 文件变化
- 去重：通过 realpath 避免重复加载

### 2. Plugin 架构
- Manifest 验证
- 组件隔离（skills/commands/hooks/mcp）
- 错误收集和报告

### 3. MCP 集成
- 环境变量替换（${VAR}, ${CLAUDE_PLUGIN_ROOT}）
- 作用域命名（plugin:name:server）
- Instructions 双重价值（工具注册 + 行为说明）

## 运行示例

```bash
cd loom/examples
python demo_ecosystem.py
```

## 核心优化点

1. **按需注入**：只有匹配任务的 skill 才注入 context
2. **懒加载**：skill 内容只在调用时加载
3. **作用域隔离**：plugin 提供的 MCP server 有独立命名空间
4. **环境变量**：支持 ${CLAUDE_PLUGIN_ROOT} 等变量替换
5. **Instructions 注入**：MCP server 的 instructions 自动注入 system prompt
