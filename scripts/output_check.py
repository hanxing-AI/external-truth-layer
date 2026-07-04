#!/usr/bin/env python3
"""
output_check.py — Deterministic output checker (external truth layer).

Core insight: weak models checking weak models is ineffective for capability
errors (blind spots are correlated). This checker only does what can be
verified against objective references — format, compliance, factual grounding,
consistency. These "Type 1" errors are easier to verify than to generate,
and have objective baselines, so even a weak model can rely on this layer.

It does NOT judge: article quality, logical coherence, domain correctness.
Those go to human review or a stronger model — this checker explicitly does
not overstep its authority.

Usage:
  echo "text" | python3 output_check.py
  python3 output_check.py --text "text"
  python3 output_check.py --file draft.md
  python3 output_check.py --json --text "..."     # machine-readable for gate.py

Exit codes: 0=all-pass(GO) / 2=has-NO-GO(block) / 1=only-FLAG(warn)
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


def check_traditional(text, rule):
    """Detect Traditional Chinese characters using opencc t2s conversion."""
    findings = []
    try:
        from opencc import OpenCC
        t2s = OpenCC("t2s")
        simplified = t2s.convert(text)
        trad_chars = sorted({o for o, s in zip(text, simplified) if o != s})
        if trad_chars:
            findings.append((rule["severity"], "traditional-chinese",
                             f"Traditional chars detected: {''.join(trad_chars[:20])}"
                             + ("..." if len(trad_chars) > 20 else "")
                             + f" — {rule.get('note', '')}"))
    except ImportError:
        findings.append(("FLAG", "traditional-chinese", "opencc not installed, skipping"))
    return findings


def check_forbidden(text, rule):
    findings = []
    for w in rule.get("words", []):
        if w in text:
            findings.append((rule["severity"], "forbidden-word", f"Blocked word: '{w}'"))
    for w in rule.get("custom_terms", []):
        if w in text:
            findings.append((rule["severity"], "custom-blocked", f"Custom blocked term: '{w}'"))
    return findings


def check_file_path(text, rule):
    findings = []
    if not any(t in text for t in rule.get("triggers", [])):
        return findings
    for hint in rule.get("suspicious_path_hints", []):
        if hint in text:
            findings.append((rule["severity"], "file-path",
                             f"Possible save to non-standard location ('{hint}') — {rule.get('note', '')}"))
    return findings


def check_volatile(text, rule):
    findings = []
    low = text.lower()
    for name in rule.get("stale_names", []):
        if name.lower() in low:
            findings.append((rule["severity"], "volatile-fact",
                             f"Possibly outdated name '{name}' ({rule.get('current_hint', '')})"))
    trigger_words = rule.get("needs_disclaimer_when", [])
    has_disclaimer = any(d in text for d in ["verify", "check official", "may be outdated", "以官网", "需核实", "为准"])
    if any(t in text for t in trigger_words) and not has_disclaimer:
        if re.search(r"model|version|price|ranking|模型|版本|价格|定价|榜单", text):
            findings.append(("FLAG", "volatile-fact",
                             "Uses 'latest/current' for model/version/price without disclaimer"))
    return findings


def check_pattern_rule(text, rule, label):
    findings = []
    for pat in rule.get("patterns", []):
        if re.search(pat, text):
            findings.append((rule["severity"], label,
                             f"Pattern matched '{pat}' — {rule.get('note', '')} (verify if checked)"))
            break
    return findings


def check_lethal_trifecta(text, rule):
    """Check if output simultaneously touches all three risk categories."""
    import re as _re
    cats = {
        "private data": rule.get("private_data_patterns", []),
        "untrusted content": rule.get("untrusted_content_patterns", []),
        "external send": rule.get("external_send_patterns", []),
    }
    hits = {}
    for label, patterns in cats.items():
        for pat in patterns:
            if _re.search(pat, text, _re.IGNORECASE):
                hits[label] = pat
                break
    if len(hits) == 3:
        return [(rule["severity"], "lethal-trifecta",
                 f"All three risk categories present: {dict(hits)} — {rule.get('note', '')}")]
    return []


def run_checks(text):
    rules = load_rules()
    findings = []
    dispatch = {
        "traditional_chinese": lambda r: check_traditional(text, r),
        "forbidden_words":     lambda r: check_forbidden(text, r),
        "file_path":           lambda r: check_file_path(text, r),
        "volatile_facts":      lambda r: check_volatile(text, r),
        "weekday_claim":       lambda r: check_pattern_rule(text, r, "weekday-claim"),
        "time_distance":       lambda r: check_pattern_rule(text, r, "time-distance"),
        "lethal_trifecta":     lambda r: check_lethal_trifecta(text, r),
    }
    for key, fn in dispatch.items():
        rule = rules.get(key)
        if rule and rule.get("enabled"):
            findings.extend(fn(rule))
    return findings


def verdict(findings):
    if any(sev == "NO-GO" for sev, _, _ in findings):
        return "NO-GO", 2
    if findings:
        return "FLAG", 1
    return "GO", 0


def main():
    ap = argparse.ArgumentParser(description="Deterministic output checker")
    ap.add_argument("--text")
    ap.add_argument("--file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.text is not None:
        text = args.text
    elif args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    findings = run_checks(text)
    v, code = verdict(findings)

    if args.json:
        print(json.dumps({
            "verdict": v,
            "findings": [{"severity": s, "type": t, "message": m} for s, t, m in findings],
        }, ensure_ascii=False, indent=2))
    else:
        icon = {"GO": "✅ GO", "FLAG": "⚠️  FLAG", "NO-GO": "⛔ NO-GO"}[v]
        print(f"{icon} — Deterministic check (format/compliance only, not content quality)")
        if not findings:
            print("  No rule violations. (Note: does not mean content is correct)")
        for s, t, m in findings:
            mark = {"NO-GO": "⛔", "FLAG": "⚠️ "}[s]
            print(f"  {mark} [{t}] {m}")
    sys.exit(code)


if __name__ == "__main__":
    main()
