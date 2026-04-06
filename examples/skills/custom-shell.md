---
name: custom-shell
description: Demonstrate custom shell configuration
whenToUse: shell, custom, environment
allowedTools: []
userInvocable: true
effort: 2
agent: general-purpose
context: inline
version: 1.0.0
shell:
  command: /bin/bash
  args: ["-c"]
  env:
    CUSTOM_VAR: "Hello from custom shell"
  timeout: 10
---

# Custom Shell Configuration

This skill demonstrates Sprint 3 features:
- **Shell Configuration**: Custom shell with environment variables
- **Token Estimation**: Progressive loading optimization

## Shell Commands with Custom Environment

**Echo Custom Variable**: !`echo $CUSTOM_VAR`

**Current Directory**: !`pwd`

**List Files**: !`ls -la | head -5`

## Token Estimation

This skill's frontmatter is estimated at ~50 tokens, while full content is ~200 tokens.

Progressive loading allows the system to:
1. Load only frontmatter for discovery (low cost)
2. Load full content only when invoked (on-demand)

---

**Note**: Shell commands run with custom environment variables defined in frontmatter.
