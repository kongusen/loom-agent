# Evolution Strategies

## E1 — Tool Learning ✅

Learns which tools are reliable from execution feedback.

- Tracks success rate and average score per tool
- Produces `preferred_tools` and `discouraged_tools` lists
- Configurable: `success_threshold=0.6`, `min_examples=1`

## E2 — Policy Optimization ✅

Turns policy-related feedback into concrete recommendations.

- Detects tools that are frequently blocked or risky
- Recommends `deny`, `require_approval`, or `relax` per tool
- Compares against baseline policy

## E3 — Constraint Hardening ✅

Solidifies failure root causes into permanent constraints (Ψ.constraints).

- Extracts `(tool, root_cause)` pairs from failed feedback entries
- Adds new constraints to prevent repeat failures
- **Ratchet-risk mitigation**: marks constraints as stale after `stale_after` entries with no violations — prevents capability decay from over-constraining

## E4 — Amoeba Split ✅

Detects when a task domain causes persistent `early_stop` events and recommends spawning a specialist sub-agent.

- Tracks `early_stop` ratio per domain
- Triggers recommendation when `task_ratio(domain) > split_threshold` (default 0.4)
- Requires `min_samples=3` before recommending

## Balance

| Only E2, no E3 | Gets better at tasks, but repeats the same mistakes |
|---|---|
| Only E3, no audit | Gets more cautious until capability atrophies |
| Only E4, no protocol | Single-agent chaos becomes distributed chaos |

All four strategies together keep capability, constraints, and structure evolving in balance.

**Code:** `loom/evolution/strategies.py`
