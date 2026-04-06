---
name: debug-assistant
description: Help debug code issues systematically
whenToUse: debug, debugging, fix bug, error, issue, problem
allowedTools:
  - read_file
  - grep
  - bash
argumentHint: <file_path or error_message>
---

# Debug Assistant

I'll help you debug the issue systematically.

## Steps:

1. **Understand the problem**
   - What's the expected behavior?
   - What's the actual behavior?
   - Error messages or stack traces?

2. **Gather context**
   - Read relevant files
   - Check recent changes
   - Review logs

3. **Identify root cause**
   - Trace execution flow
   - Check assumptions
   - Isolate the issue

4. **Propose solution**
   - Fix the bug
   - Add tests
   - Prevent regression

Let's start debugging!
