"""Benchmark runner — unified entry point, outputs JSON report.

Usage:
    python -m benchmarks.runner              # run all, print JSON
    python -m benchmarks.runner --pretty     # pretty-print
    python -m benchmarks.runner -o report.json  # save to file
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks import perf, logic, mechanism


async def run_all():
    t0 = time.monotonic()

    print("Running performance benchmarks...", file=sys.stderr)
    perf_results = await perf.run_all()

    print("Running logic tests...", file=sys.stderr)
    logic_results = await logic.run_all()

    print("Running mechanism tests...", file=sys.stderr)
    mech_results = await mechanism.run_all()

    elapsed = time.monotonic() - t0

    logic_passed = sum(1 for r in logic_results if r.passed)
    mech_passed = sum(1 for r in mech_results if r.passed)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_duration_ms": round(elapsed * 1000, 1),
        "summary": {
            "perf_benchmarks": len(perf_results),
            "logic_tests": f"{logic_passed}/{len(logic_results)}",
            "mechanism_tests": f"{mech_passed}/{len(mech_results)}",
            "all_passed": logic_passed == len(logic_results) and mech_passed == len(mech_results),
        },
        "performance": [r.to_dict() for r in perf_results],
        "logic": [r.to_dict() for r in logic_results],
        "mechanism": [r.to_dict() for r in mech_results],
    }


def main():
    args = sys.argv[1:]
    pretty = "--pretty" in args
    out_file = None
    if "-o" in args:
        idx = args.index("-o")
        if idx + 1 < len(args):
            out_file = args[idx + 1]

    report = asyncio.run(run_all())
    text = json.dumps(report, indent=2 if pretty else None, ensure_ascii=False)

    if out_file:
        Path(out_file).write_text(text)
        print(f"Report saved to {out_file}", file=sys.stderr)
    else:
        print(text)

    if not report["summary"]["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
