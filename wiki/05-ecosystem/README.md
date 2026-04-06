# Ecosystem

Loom's capability layer: Skills, Plugins, and MCP servers.

## Three Extension Points

| Type | Purpose | Load time |
|---|---|---|
| **Skills** | Reusable task workflows with tool constraints | On demand |
| **Plugins** | Bundles of MCP servers + hooks | At startup |
| **MCP** | External tool servers via stdio JSON-RPC | On connect |

## Pages

- [Skills](skills.md)
- [Plugins](plugins.md)
- [MCP Integration](mcp.md)

**Code:** `loom/ecosystem/`
