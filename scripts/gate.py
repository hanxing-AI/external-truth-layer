#!/usr/bin/env python3
"""
gate.py — Two-tier verification gate for AI agent outputs.

Design principles:
  1. Verification leverage comes from comparing against objective references,
     NOT from "a second model's second opinion."
  2. Errors are triaged by type — never let "verified" overstep into domains
     it can't actually judge.

Two tiers:
  Level 1 (Deterministic): output_check.py — no model needed, checks
      format/compliance/factual-grounding. Reliable for "Type 1 errors"
      (sloppiness, formatting, banned words, stale model names) even with
      weak models.
  Level 2 (Cross-family): Calls a different model family as verifier.
      Key: the verifier is forced to ONLY judge against provided reference
      materials. If it can't verify, it must ESCALATE — never pretend it can
      judge domain correctness (that's a correlated blind spot).

Three verdicts (strict):
  GO       — Every key claim is supported by reference materials, no conflicts.
  NO-GO    — A claim directly contradicts reference materials, or hits a ban.
  ESCALATE — A claim can't be verified against references. "Can't tell" is
             NEVER NO-GO or silent GO — it's ESCALATE. Pretending to judge is
             worse than being wrong.

Usage:
  python3 gate.py --draft draft.md
  python3 gate.py --draft draft.md --refs "reference text"
  python3 gate.py --draft draft.md --refs-file spec.md --skip-model   # Level 1 only
  python3 gate.py --draft-text "..." --refs "..." --json

Environment:
  VERIFIER_API_KEY  — API key for the cross-family verifier model
  VERIFIER_BASE_URL — Base URL (default: https://api.deepseek.com)
  VERIFIER_MODEL    — Model name (default: deepseek-chat)

Exit codes: 0=GO / 2=NO-GO / 1=ESCALATE / 3=error
"""
import sys, os, json, argparse, subprocess, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))


def read_env(key, default=""):
    """Read from environment, with optional fallback to .env file."""
    val = os.environ.get(key, "")
    if val:
        return val
    # Try .env file in home directory or current directory
    for envp in [os.path.expanduser("~/.env"), os.path.join(os.getcwd(), ".env")]:
        try:
            for line in open(envp, encoding="utf-8"):
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            pass
    return default


def deterministic_layer(text):
    """Level 1: run output_check.py, return (verdict, findings)."""
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "output_check.py"), "--json", "--text", text],
        capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"verdict": "ERROR", "findings": [{"severity": "ERROR", "type": "det", "message": r.stderr[:200]}]}


VERIFIER_SYSTEM = """You are an independent output verifier. You are NOT the same model family as the generator. Your job is not to rewrite or praise — it is to calmly adjudicate.

Three verdicts (strict, never mix):
- GO: Every key claim in the output can be found supported in the [Reference Materials], with no contradiction.
- NO-GO: The output contains a claim that [directly contradicts] the Reference Materials, or hits an explicit ban. Only use NO-GO when you catch a clear conflict.
- ESCALATE: The output contains a claim that [the Reference Materials don't cover and you cannot verify]. "Can't tell true/false" is NEVER NO-GO — if you can't verify, output ESCALATE for human/stronger-model review.

Rules:
1. You may ONLY judge against the [Reference Materials]. What can be verified there, verify; what can't, output ESCALATE. Never use your own knowledge to adjudicate, and never issue NO-GO just because you can't verify.
2. When "deep domain correctness" judgment is needed (facts, logic, professional conclusions) and the Reference Materials don't cover it, ALWAYS ESCALATE. Never GO just because it "looks right." For the most dangerous class of errors, pretending to judge is worse than being wrong.
3. Output ONLY one JSON: {"verdict": "GO|NO-GO|ESCALATE", "reasons": ["specific reasons, pointing to which reference item"], "escalate_items": ["specific items needing human review"]}"""


def cross_family_layer(text, refs):
    """Level 2: cross-family model GO/NO-GO/ESCALATE."""
    api_key = read_env("VERIFIER_API_KEY")
    base_url = read_env("VERIFIER_BASE_URL", "https://api.deepseek.com")
    model = read_env("VERIFIER_MODEL", "deepseek-chat")

    if not api_key:
        return {"verdict": "ESCALATE",
                "reasons": ["VERIFIER_API_KEY not configured — cannot independently verify"],
                "escalate_items": ["Entire output needs human review"]}

    user = f"""[Reference Materials] (the ONLY source of truth):
{refs if refs.strip() else '(No reference materials provided — anything involving facts/domain correctness should ESCALATE)'}

[Output to verify]:
{text}

Adjudicate per the rules. Output JSON only."""

    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": VERIFIER_SYSTEM},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }).encode()

    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read())
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        return {"verdict": "ESCALATE",
                "reasons": [f"Cross-family verifier call failed: {e}"],
                "escalate_items": ["Entire output needs human review"]}


def main():
    ap = argparse.ArgumentParser(description="Two-tier verification gate")
    ap.add_argument("--draft", help="File path of draft to verify")
    ap.add_argument("--draft-text", help="Draft text directly")
    ap.add_argument("--refs", default="", help="Reference material text")
    ap.add_argument("--refs-file", help="Reference material file path")
    ap.add_argument("--skip-model", action="store_true", help="Skip Level 2 (deterministic only)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.draft_text:
        text = args.draft_text
    elif args.draft:
        text = open(args.draft, encoding="utf-8").read()
    else:
        text = sys.stdin.read()

    refs = args.refs
    if args.refs_file:
        refs += "\n" + open(args.refs_file, encoding="utf-8").read()

    det = deterministic_layer(text)
    result = {"level1_deterministic": det}

    if det["verdict"] == "NO-GO":
        final, code = "NO-GO", 2
    elif args.skip_model:
        final = det["verdict"] if det["verdict"] != "GO" else "GO"
        code = 1 if det["verdict"] == "FLAG" else 0
    else:
        model_res = cross_family_layer(text, refs)
        result["level2_cross_family"] = model_res
        mv = model_res.get("verdict", "ESCALATE")
        if mv == "NO-GO":
            final, code = "NO-GO", 2
        elif mv == "ESCALATE":
            final, code = "ESCALATE", 1
        elif det["verdict"] == "FLAG":
            final, code = "FLAG", 1
        else:
            final, code = "GO", 0

    result["final_verdict"] = final

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        icon = {"GO": "✅ GO", "FLAG": "⚠️  FLAG",
                "ESCALATE": "🔺 ESCALATE (needs human/stronger model)",
                "NO-GO": "⛔ NO-GO"}.get(final, final)
        print(f"Gate verdict: {icon}\n")
        print("── Level 1: Deterministic ──")
        print(f"  {det['verdict']}")
        for f in det.get("findings", []):
            print(f"    [{f['type']}] {f['message']}")
        if "level2_cross_family" in result:
            m = result["level2_cross_family"]
            print("── Level 2: Cross-family verifier ──")
            print(f"  {m.get('verdict')}")
            for r in m.get("reasons", []):
                print(f"    · {r}")
            for e in m.get("escalate_items", []):
                print(f"    🔺 Escalate: {e}")
    sys.exit(code)


if __name__ == "__main__":
    main()
