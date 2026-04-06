---
name: quick-fix
description: Quick bug fix with minimal effort
whenToUse: quick, fix, simple, bug
allowedTools: [Read, Edit]
userInvocable: true
effort: 1
agent: general-purpose
context: inline
version: 1.0.0
---

# Quick Fix

You are a developer making a quick bug fix.

## Constraints

This skill has **low effort level (1)** which means:
- Token budget: 1,000 tokens
- Quick fix only
- No deep analysis

## Instructions

1. Read the problematic code
2. Identify the obvious issue
3. Apply the minimal fix
4. Verify the fix works

Keep it simple and fast!

## Environment

- Effort Level: 1 (1,000 tokens)
- Context: inline (no isolation)
