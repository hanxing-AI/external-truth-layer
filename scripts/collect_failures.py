#!/usr/bin/env python3
"""
collect_failures.py — Failure pattern collection (inspired by Self-Harness).

Self-Harness principle: an agent should detect its own failure patterns
(Weakness Mining) and propose targeted improvements. This script does the
detection half — it collects historical gate.py run results, tallies which
rules are most frequently violated, and outputs a ranked report.

It does NOT auto-modify rules.yaml (too dangerous). It gives you data to
decide what to add or strengthen.

Usage:
  # Collect from a log file of gate.py --json outputs
  python3 collect_failures.py --log gate_history.jsonl

  # Collect from a directory of gate run JSON files
  python3 collect_failures.py --dir runs/

  # Pipe a single gate.py --json output
  gate.py --json --draft draft.md | python3 collect_failures.py --stdin

  # Show top N patterns
  python3 collect_failures.py --log gate_history.jsonl --top 5

Exit codes: 0=success / 3=error
"""
import sys, os, json, argparse
from collections import Counter, defaultdict
from datetime import datetime


def load_runs_from_jsonl(filepath):
    """Load gate.py --json outputs from a JSONL file (one JSON per line)."""
    runs = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return runs


def load_runs_from_dir(dirpath):
    """Load gate.py --json outputs from a directory of .json files."""
    runs = []
    for fname in sorted(os.listdir(dirpath)):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(dirpath, fname), encoding="utf-8") as f:
                    runs.append(json.load(f))
            except (json.JSONDecodeError, IOError):
                continue
    return runs


def load_from_stdin():
    """Load a single gate.py --json output from stdin."""
    try:
        return [json.loads(sys.stdin.read())]
    except json.JSONDecodeError:
        return []


def extract_findings(runs):
    """Extract all findings from gate.py run results."""
    all_findings = []
    final_verdicts = Counter()

    for run in runs:
        # Final verdict
        fv = run.get("final_verdict", "UNKNOWN")
        final_verdicts[fv] += 1

        # Level 1 findings
        det = run.get("level1_deterministic", {})
        for f in det.get("findings", []):
            all_findings.append({
                "level": "L1-deterministic",
                "type": f.get("type", "unknown"),
                "severity": f.get("severity", "unknown"),
                "message": f.get("message", ""),
            })

        # Level 2 findings
        l2 = run.get("level2_cross_family", {})
        if l2:
            for reason in l2.get("reasons", []):
                all_findings.append({
                    "level": "L2-cross-family",
                    "type": "model-reason",
                    "severity": l2.get("verdict", "unknown"),
                    "message": reason,
                })
            for item in l2.get("escalate_items", []):
                all_findings.append({
                    "level": "L2-cross-family",
                    "type": "escalate-item",
                    "severity": "ESCALATE",
                    "message": item,
                })

    return all_findings, final_verdicts


def analyze(all_findings, final_verdicts, top_n=10):
    """Analyze findings and produce a ranked report."""
    # Count by type
    by_type = Counter()
    by_severity = Counter()
    type_messages = defaultdict(set)

    for f in all_findings:
        by_type[f["type"]] += 1
        by_severity[f["severity"]] += 1
        # Keep unique message snippets per type (first 60 chars)
        type_messages[f["type"]].add(f["message"][:60])

    # Build report
    lines = []
    lines.append("=" * 60)
    lines.append("Failure Pattern Report — Self-Harness Weakness Mining")
    lines.append("=" * 60)
    lines.append("")

    # Verdict summary
    total_runs = sum(final_verdicts.values())
    lines.append(f"Total runs analyzed: {total_runs}")
    lines.append("Verdict distribution:")
    for v, count in final_verdicts.most_common():
        pct = count / total_runs * 100 if total_runs else 0
        lines.append(f"  {v:12s}  {count:3d}  ({pct:.0f}%)")
    lines.append("")

    # Top failure types
    lines.append(f"Top {top_n} failure patterns (by type):")
    lines.append("-" * 60)
    for rank, (ftype, count) in enumerate(by_type.most_common(top_n), 1):
        lines.append(f"  {rank}. [{ftype}] × {count}")
        # Show sample messages
        samples = list(type_messages[ftype])[:2]
        for s in samples:
            lines.append(f"     e.g. \"{s}...\"")
    lines.append("")

    # Severity distribution
    lines.append("Severity distribution of findings:")
    for sev, count in by_severity.most_common():
        lines.append(f"  {sev:12s}  {count}")
    lines.append("")

    # Recommendations
    lines.append("Recommendations:")
    lines.append("-" * 60)
    if by_type:
        top_type = by_type.most_common(1)[0]
        lines.append(f"  1. Most frequent: '{top_type[0]}' ({top_type[1]} times).")
        lines.append(f"     Consider strengthening the corresponding rule in rules.yaml.")
    if final_verdicts.get("ESCALATE", 0) > 0:
        esc_count = final_verdicts["ESCALATE"]
        lines.append(f"  2. {esc_count} run(s) ended in ESCALATE.")
        lines.append("     These are areas where reference materials don't cover the claims.")
        lines.append("     Consider adding reference materials for those domains.")
    if final_verdicts.get("NO-GO", 0) > 0:
        nogo_count = final_verdicts["NO-GO"]
        lines.append(f"  3. {nogo_count} run(s) ended in NO-GO.")
        lines.append("     These are hard blocks. Consider if the rules are too strict")
        lines.append("     or if the model needs better pre-generation guidance (precheck.py).")
    if not by_type:
        lines.append("  No findings recorded. Either all runs passed cleanly,")
        lines.append("  or no gate.py history was found.")
    lines.append("")

    lines.append("Note: This script does NOT auto-modify rules.yaml.")
    lines.append("      Review the patterns above and manually update rules as needed.")
    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Collect and analyze failure patterns from gate.py runs")
    ap.add_argument("--log", help="JSONL file of gate.py --json outputs")
    ap.add_argument("--dir", help="Directory of gate.py --json output files")
    ap.add_argument("--stdin", action="store_true", help="Read single run from stdin")
    ap.add_argument("--top", type=int, default=10, help="Show top N patterns (default: 10)")
    ap.add_argument("--json", action="store_true", help="Output as JSON instead of text")
    args = ap.parse_args()

    runs = []
    if args.log:
        runs = load_runs_from_jsonl(args.log)
    elif args.dir:
        runs = load_runs_from_dir(args.dir)
    elif args.stdin:
        runs = load_from_stdin()
    elif not sys.stdin.isatty():
        runs = load_from_stdin()
    else:
        ap.print_help()
        sys.exit(1)

    if not runs:
        print("No valid gate.py runs found.", file=sys.stderr)
        sys.exit(3)

    all_findings, final_verdicts = extract_findings(runs)

    if args.json:
        result = {
            "total_runs": len(runs),
            "verdict_distribution": dict(final_verdicts),
            "findings_by_type": dict(Counter(f["type"] for f in all_findings)),
            "findings_by_severity": dict(Counter(f["severity"] for f in all_findings)),
            "total_findings": len(all_findings),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        report = analyze(all_findings, final_verdicts, args.top)
        print(report)

    sys.exit(0)


if __name__ == "__main__":
    main()
