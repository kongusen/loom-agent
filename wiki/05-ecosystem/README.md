# Ecosystem

Loom's ecosystem layer extends what an `Agent` can do after the core runtime is already in place.

## Position In The Stack

```text
Agent + Runtime + Capability
    ├── tools
    ├── knowledge
    └── ecosystem extensions
          ├── skills
          ├── plugins
          └── MCP
```

## Extension Surfaces

| Type | Purpose | Typical role |
|---|---|---|
| Skills | reusable task workflows | developer-authored capability packs |
| Plugins | packaged extension bundles | product/platform integration |
| MCP | external tool servers | remote or local tool interoperability |

## Notes

- These are extension layers, not replacements for the main public `Agent` API.
- Application code should start from `Agent`, `Runtime`, and `Capability`.
- Ecosystem features are typically attached through `Capability`, explicit tools, configuration, or runtime assembly.

## Pages

- [Skills](skills.md)
- [Plugins](plugins.md)
- [MCP Integration](mcp.md)

## Code

- `loom/ecosystem/skill.py`
- `loom/ecosystem/plugin.py`
- `loom/ecosystem/mcp.py`
