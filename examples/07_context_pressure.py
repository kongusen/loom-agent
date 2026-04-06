"""07 - Context Pressure and Compression

Shows how Loom's five compression levels trigger at different ρ (rho) values.

  ρ > 0.70 → Snip Compact    (truncate long messages)
  ρ > 0.80 → Micro Compact   (cache tool results)
  ρ > 0.90 → Context Collapse (fold inactive regions)
  ρ > 0.95 → Auto Compact    (full compression)
  API 413  → Reactive Compact (emergency: auto + snip at 500 chars)

Run:
    python examples/07_context_pressure.py
"""

from loom.context.compression import ContextCompressor
from loom.types import Message


def make_messages(n: int, length: int = 3000) -> list[Message]:
    return [Message(role="user" if i % 2 == 0 else "assistant", content="x" * length) for i in range(n)]


def main():
    compressor = ContextCompressor()
    messages = make_messages(10)
    total_chars = sum(len(m.content) for m in messages)
    print(f"Original: {len(messages)} messages, {total_chars} chars\n")

    levels = [
        (0.65, "none"),
        (0.75, "snip"),
        (0.85, "micro"),
        (0.92, "collapse"),
        (0.96, "auto"),
    ]

    for rho, expected in levels:
        triggered = compressor.should_compress(rho)
        print(f"  ρ={rho:.2f} → triggers: {triggered or 'none':10s}  (expected: {expected})")

    print("\n=== Snip Compact (ρ=0.75) ===")
    snipped = compressor.snip_compact(messages, max_length=500)
    print(f"  After snip: {sum(len(m.content) for m in snipped)} chars")

    print("\n=== Context Collapse (ρ=0.92) ===")
    collapsed = compressor.context_collapse(messages, goal="summarize project")
    print(f"  After collapse: {len(collapsed)} messages (kept first {compressor.collapse_keep_first} + last {compressor.collapse_keep_last})")

    print("\n=== Reactive Compact (API 413) ===")
    reactive = compressor.reactive_compact(messages, goal="summarize project")
    print(f"  After reactive: {len(reactive)} messages, {sum(len(m.content) for m in reactive)} chars")


main()
