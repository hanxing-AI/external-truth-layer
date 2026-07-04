---
name: external-truth-layer
description: >-
  Replace "weak model checking weak model" with deterministic code, external
  references, and cross-family verification. Core insight: a model verifying
  itself is ineffective for capability errors because blind spots are correlated.
  Solution: compare against objective references, triage errors by type, and
  use a different model family as verifier to decorrelate blind spots.
  Includes date calculator, fact lookup, format compliance checker, and a
  two-tier GO/NO-GO/ESCALATE verification gate.
when_to_use: |-
  Any scenario requiring "verify / check / confirm" — date claims, fact
  references, pre-publish compliance, irreversible action decisions. Especially
  when you know the current model isn't strong, or when you feel "probably fine
  but should check" — that feeling is the signal to use this.
triggers: |-
  Date/weekday claims → datecheck.py
  Static fact lookup → factlookup.sh
  Pre-publish format check → output_check.py
  Irreversible/external output → gate.py
---

# External Truth Layer

> Replace "weak model checking weak model" with code + external references + cross-family models.

## The Core Problem

**A weak model verifying itself is ineffective against capability errors.**
The generator and verifier share the same blind spots (same brain), so they
wave each other through. Real verification requires two things:
1. **Compare against external references** (fact bases, tests, specs, rules) → deterministic judgment
2. **Triage by error type + use a different model family as verifier** → decorrelate blind spots

## Tool Chain

All scripts live in `scripts/` alongside this SKILL.md.

### 1. datecheck.py — Deterministic Date Calculation

**When to run**: whenever you write "Wednesday", "X months ago", "X days from now".

```bash
python3 scripts/datecheck.py 2026-07-08
# Output: 2026-07-08 is 周三, 4 days from now

python3 scripts/datecheck.py --today
python3 scripts/datecheck.py --since 2026-06-26
python3 scripts/datecheck.py --next-weekday 3        # 3=Wednesday
```

**Rule**: dates are computed by code, never by inference. Never say "Wednesday"
or "a few months ago" based on reasoning.

### 2. factlookup.sh — Fact Base Search

**When to run**: when answering questions about stored facts (names, configs, project details).

```bash
# Set your fact directory (default: ~/.local/fact-base)
export FACT_DIR=~/my-fact-base

bash scripts/factlookup.sh "keyword"
bash scripts/factlookup.sh --list     # list all fact files
bash scripts/factlookup.sh --index    # print index file
```

**Why**: many agent frameworks store facts in hidden directories that built-in
search tools skip. This wraps grep to reliably find them.

### 3. output_check.py — Format Compliance Checker

**When to run**: before publishing or delivering any content.

```bash
python3 scripts/output_check.py --text "your content..."
python3 scripts/output_check.py --file draft.md
echo "text" | python3 scripts/output_check.py --json
```

Rules are in `scripts/rules.yaml` — **customize them with your own rules**.
Each rule anchors to an objective, verifiable standard.

### 4. gate.py — Two-Tier Verification Gate

**When to run**: for irreversible or external outputs (publishing, config changes, releases).

```bash
python3 scripts/gate.py --draft draft.md --refs "reference materials..."
python3 scripts/gate.py --draft draft.md --refs-file spec.md
python3 scripts/gate.py --draft draft.md --skip-model   # Level 1 only
```

**Two tiers**:
- **Level 1**: Deterministic (no model) — scans for known error patterns
  (date claims without verification, fact references without sources,
  traditional/simplified mixing, stale model names, banned words)
- **Level 2**: Cross-family model — uses a different model family
  (configurable via `VERIFIER_API_KEY`, `VERIFIER_BASE_URL`, `VERIFIER_MODEL`
  environment variables) to adjudicate against reference materials

**Three verdicts** (strict):
- **GO** = Every claim is supported by references, no conflicts → pass
- **NO-GO** = A claim contradicts references, or hits a ban → block
- **ESCALATE** = References don't cover this, can't verify → escalate to human/stronger model

**The key insight "ESCALATE"**: "Can't verify" is ALWAYS ESCALATE, never NO-GO
and never silent GO. This prevents the most dangerous error — pretending to
judge is worse than being wrong.

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `FACT_DIR` | Fact base directory for factlookup.sh | `~/.local/fact-base` |
| `FACT_INDEX` | Index file path | `$FACT_DIR/index.md` |
| `VERIFIER_API_KEY` | API key for cross-family verifier (gate.py Level 2) | (none) |
| `VERIFIER_BASE_URL` | Verifier API base URL | `https://api.deepseek.com` |
| `VERIFIER_MODEL` | Verifier model name | `deepseek-chat` |

## Dependencies

- **Python 3** (all scripts)
- **pyyaml** — for output_check.py and gate.py (`pip install pyyaml`)
- **opencc-python-reimplemented** — optional, for Traditional Chinese detection (`pip install opencc-python-reimplemented`)

## How to Customize

1. **Edit `scripts/rules.yaml`** — replace sample rules with your own. Each rule
   should anchor to an objective, verifiable standard.
2. **Set environment variables** — point `FACT_DIR` to your knowledge base,
   set `VERIFIER_*` to a model from a different family than your primary model.
3. **Add your own fact base** — create markdown files with structured facts
   that `factlookup.sh` can search.

## Relationship to Other Systems

This skill is model-agnostic and framework-agnostic. It works with:
- Hermes Agent (as a skill in `~/.hermes/skills/`)
- Claude (as Custom Instructions or Project Knowledge)
- ChatGPT / GPT (as Custom GPT instructions + Knowledge files)
- Cursor / any AI IDE (as `.cursorrules` or custom instructions)
- Any system that can run shell scripts

The core methodology — "use deterministic code instead of model self-checks,
triage errors by type, cross-family verification" — is universal.
