#!/usr/bin/env python3
"""
precheck.py — Feedforward guidance (run BEFORE generating output).

A good harness has two mechanisms: feedforward (guide before generation) and
feedback (correct after generation). output_check.py and gate.py are feedback.
This script is feedforward — it scans a task description before the model
starts working, and flags known risk patterns so the model can avoid them
proactively.

This is NOT a model call. It's pure pattern matching against rules.yaml —
the same rules file used by output_check.py, but applied to the task prompt
instead of the output.

Usage:
  python3 precheck.py --task "Write an article mentioning next Wednesday's deadline"
  python3 precheck.py --task-file task.txt
  echo "task description" | python3 precheck.py
  python3 precheck.py --json --task "..."

Exit codes: 0=no risks detected / 1=risks flagged (advisory, never blocks)
"""
import sys, os, re, json, argparse

RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.yaml")


def load_rules():
    try:
        import yaml
    except ImportError:
        print("Requires pyyaml: pip install pyyaml", file=sys.stderr)
        sys.exit(3)
    with open(RULES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def scan_task(task_text, rules):
    """Scan task description for known risk patterns. Returns advisory warnings."""
    warnings = []
    low = task_text.lower()

    # 1. Date/weekday risk — if task mentions dates or weekdays, remind to use datecheck.py
    weekday_pats = rules.get("weekday_claim", {}).get("patterns", [])
    if any(re.search(p, task_text) for p in weekday_pats):
        warnings.append({
            "risk": "weekday-claim",
            "message": "Task mentions a weekday. Run datecheck.py to compute it deterministically before writing.",
        })
    if re.search(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', task_text):
        warnings.append({
            "risk": "date-reference",
            "message": "Task references a specific date. Verify weekday and time distance with datecheck.py.",
        })

    # 2. Volatile facts risk — if task asks about models/versions/prices
    volatile_triggers = rules.get("volatile_facts", {}).get("needs_disclaimer_when", [])
    if any(t in task_text for t in volatile_triggers) and re.search(r'模型|版本|价格|model|version|price', task_text, re.IGNORECASE):
        warnings.append({
            "risk": "volatile-facts",
            "message": "Task involves model names, versions, or prices. Don't rely on training memory — verify or add 'check official docs' disclaimer.",
        })

    # 3. Lethal trifecta risk — if task involves all three categories
    trifecta_rule = rules.get("lethal_trifecta", {})
    if trifecta_rule.get("enabled"):
        cats = {
            "private data": trifecta_rule.get("private_data_patterns", []),
            "untrusted content": trifecta_rule.get("untrusted_content_patterns", []),
            "external send": trifecta_rule.get("external_send_patterns", []),
        }
        hits = {}
        for label, patterns in cats.items():
            for pat in patterns:
                if re.search(pat, task_text, re.IGNORECASE):
                    hits[label] = pat
                    break
        if len(hits) >= 2:
            severity = "high" if len(hits) == 3 else "medium"
            warnings.append({
                "risk": "lethal-trifecta",
                "severity": severity,
                "message": f"Task involves {len(hits)}/3 risk categories ({list(hits.keys())}). Be extra careful with data handling.",
            })

    # 4. File path risk — if task mentions saving/writing files
    path_triggers = rules.get("file_path", {}).get("triggers", [])
    if any(t in task_text for t in path_triggers):
        warnings.append({
            "risk": "file-path",
            "message": "Task involves saving files. Ensure output goes to a designated project directory.",
        })

    # 5. Traditional Chinese context — if task is about classical/historical content
    if re.search(r'古典|古文|历史|三國|水浒|红楼|classical|historical', task_text, re.IGNORECASE):
        tc_rule = rules.get("traditional_chinese", {})
        if tc_rule.get("enabled"):
            warnings.append({
                "risk": "traditional-chinese-context",
                "message": "Task involves classical/historical content. Watch for accidental Traditional Chinese characters in output.",
            })

    return warnings


def main():
    ap = argparse.ArgumentParser(description="Feedforward pre-check for known risk patterns")
    ap.add_argument("--task", help="Task description text")
    ap.add_argument("--task-file", help="File containing task description")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.task is not None:
        text = args.task
    elif args.task_file:
        with open(args.task_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    rules = load_rules()
    warnings = scan_task(text, rules)

    if args.json:
        print(json.dumps({"warnings": warnings, "count": len(warnings)}, ensure_ascii=False, indent=2))
    else:
        if not warnings:
            print("✅ No known risk patterns detected in task description.")
            print("   (This does not mean the task is safe — only that no known patterns matched.)")
        else:
            print(f"⚠️  {len(warnings)} risk pattern(s) detected:\n")
            for w in warnings:
                sev = w.get("severity", "advisory")
                print(f"  [{w['risk']}] ({sev})")
                print(f"    {w['message']}\n")

    sys.exit(0)  # Always exit 0 — this is advisory, never blocks


if __name__ == "__main__":
    main()
