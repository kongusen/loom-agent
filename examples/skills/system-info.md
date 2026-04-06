---
name: system-info
description: Display system information with hooks and shell execution
whenToUse: system, info, environment
allowedTools: []
userInvocable: true
effort: 2
agent: general-purpose
context: inline
version: 1.0.0
hooks:
  onLoad: Loading system info skill
  onInvoke: Gathering system information
  onComplete: System info collected
  onError: Failed to gather system info
---

# System Information

This skill demonstrates:
- **Hooks**: Lifecycle management
- **Shell inline execution**: !`command` syntax

## System Details

**Current Directory**: !`pwd`

**User**: !`whoami`

**Date**: !`date`

**Git Branch**: !`git branch --show-current 2>/dev/null || echo "Not a git repo"`

**Python Version**: !`python3 --version`

## Environment

- Skill Directory: ${CLAUDE_SKILL_DIR}
- Session ID: ${CLAUDE_SESSION_ID}
- Effort Level: 2 (2,000 tokens)

---

**Note**: Shell commands are executed inline and replaced with their output.
