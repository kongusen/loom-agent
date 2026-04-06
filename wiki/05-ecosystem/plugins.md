# Plugins

Plugins bundle MCP servers and hooks into a single installable unit.

## Plugin Structure

```
my-plugin/
├── plugin.yaml       # metadata + MCP server configs
├── hooks/            # pre/post tool use hooks
└── skills/           # skill markdown files
```

## Loading a Plugin

```python
from loom.ecosystem.plugin import PluginLoader

loader = PluginLoader()
plugin = loader.load_plugin("./my-plugin", source="local")
loader.enable_plugin("my-plugin")
loader.apply_to_agent("my-plugin", agent)
```

**Code:** `loom/ecosystem/plugin.py`
