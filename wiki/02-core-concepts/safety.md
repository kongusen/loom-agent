# Safety & Control (Harness Ψ)

The Harness is the stage, not the actor. It sets boundaries and holds veto power — but never replaces the model's decisions.

## Three-Tier Protection

```
Tool call request
      │
      ▼
Layer 1: Speculative Classifier  (risk pre-assessment)
      │
      ▼
Layer 2: Hook Policy Layer       (PreToolUse hooks → allow/ask/deny)
      │
      ▼
Layer 3: Permission Decision     (rules + user interaction)
      │
      ▼
   Execute or Block
```

## PermissionManager ✅

```python
from loom.safety import PermissionManager

pm = PermissionManager(mode="DEFAULT")  # DEFAULT | PLAN | AUTO
pm.grant("shell", "run_command", requires_approval=True)
decision = pm.evaluate("shell", "run_command", context)
```

## HookManager ✅

```python
from loom.safety import HookManager

hooks = HookManager()
hooks.register("pre_tool_use", lambda ctx: "allow")
outcome = hooks.evaluate("pre_tool_use", context, agent_context)
```

## VetoAuthority ✅

Ψ's safety valve — can block any tool call. Use sparingly.

```python
from loom.safety import VetoAuthority, VetoRule

veto = VetoAuthority()
veto.add_rule(VetoRule(
    name="no-rm-rf",
    predicate=lambda tool, args: "rm -rf" in args.get("command", ""),
    reason="Destructive command blocked",
))
vetoed, reason = veto.check_tool("run_command", {"command": "rm -rf /"})
```

**What Harness can do vs. cannot do:**

| ✅ Can | ❌ Cannot |
|---|---|
| Set initial system context | Override model's reasoning mid-run |
| Provide tools and skill packages | Set arbitrary semantic thresholds |
| Set physical constraints (ρ, d_max) | Make semantic decisions for the model |
| Configure heartbeat strategy | Let H_b respond on behalf of the model |
| Hold veto power (safety valve) | — |

**Code:** `loom/safety/`
