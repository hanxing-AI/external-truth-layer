---
name: external-truth-layer
description: >-
  Replace "weak model checking weak model" with deterministic code, external
  references, and cross-family verification. Core insight: a model verifying
  itself is ineffective for capability errors because blind spots are correlated.
  Solution: compare against objective references, triage errors by type, and
  use a different model family as verifier to decorrelate blind spots.
  Includes feedforward pre-check, date calculator, fact lookup, format compliance
  checker, two-tier GO/NO-GO/ESCALATE verification gate, and failure pattern
  collection for self-improvement.
when_to_use: |-
  Any scenario requiring "verify / check / confirm" — date claims, fact
  references, pre-publish compliance, irreversible action decisions. Especially
  when you know the current model isn't strong, or when you feel "probably fine
  but should check" — that feeling is the signal to use this.
triggers: |-
  Before generating → precheck.py (feedforward guidance)
  Date/weekday claims → datecheck.py
  Static fact lookup → factlookup.sh
  Pre-publish format check → output_check.py
  Irreversible/external output → gate.py
  After repeated failures → collect_failures.py (weakness mining)
---

# External Truth Layer

> Replace "weak model checking weak model" with code + external references + cross-family models.

## The Core Problem

**A weak model verifying itself is ineffective against capability errors.**
The generator and verifier share the same blind spots (same brain), so they
wave each other through. Real verification requires two things:
1. **Compare against external references** (fact bases, tests, specs, rules) → deterministic judgment
2. **Triage by error type + use a different model family as verifier** → decorrelate blind spots

## Two Types of Control

Drawing from Birgitta Böckeler's harness engineering framework, this toolkit
implements two types of control:

| Type | What it means | This toolkit's implementation |
|------|--------------|-------------------------------|
| **Computational controls** | Non-black-and-white checks with objective answers (linter, unit test, pattern match) | Level 1 of gate.py, output_check.py, datecheck.py, precheck.py |
| **Inferential controls** | Checks that involve probability and judgment (another model as judge) | Level 2 of gate.py (cross-family verifier) |

The key insight: computational controls are reliable even with weak models
because the answer is deterministic. Inferential controls add value only when
the verifier is from a different model family (decorrelated blind spots).
Mixing both — and knowing which is which — is what makes the gate effective.

## Two Directions of Control

| Direction | When it runs | Purpose | This toolkit |
|-----------|-------------|---------|--------------|
| **Feedforward** | Before generation | Guide the model away from known risk patterns | precheck.py |
| **Feedback** | After generation | Catch errors the model already made | output_check.py, gate.py |

A complete harness needs both. Feedforward prevents errors proactively;
feedback catches what slips through.

## Tool Chain

All scripts live in `scripts/` alongside this SKILL.md.

### 1. precheck.py — Feedforward Pre-Check

**When to run**: BEFORE starting work on a task, scan the task description
for known risk patterns.

```bash
python3 scripts/precheck.py --task "Write about next Wednesday's deadline and the latest GPT model"
# Output: ⚠️ 2 risk patterns detected: weekday-claim, volatile-facts
```

This is advisory only — it never blocks. It alerts the model to risks it
should watch for during generation, using the same rules.yaml as output_check.py.

### 2. datecheck.py — Deterministic Date Calculation

**When to run**: whenever you write "Wednesday", "X months ago", "X days from now".

```bash
python3 scripts/datecheck.py 2026-07-08
# Output: 2026-07-08 is 周三, 4 days from now

python3 scripts/datecheck.py --today
python3 scripts/datecheck.py --since 2026-06-26
python3 scripts/datecheck.py --next-weekday 3        # 3=Wednesday
```

**Rule**: dates are computed by code, never by inference.

### 3. factlookup.sh — Fact Base Search

**When to run**: when answering questions about stored facts (names, configs, project details).

```bash
export FACT_DIR=~/my-fact-base
bash scripts/factlookup.sh "keyword"
bash scripts/factlookup.sh --list     # list all fact files
bash scripts/factlookup.sh --index    # print index file
```

### 4. output_check.py — Format Compliance Checker

**When to run**: before publishing or delivering any content.

```bash
python3 scripts/output_check.py --text "your content..."
python3 scripts/output_check.py --file draft.md
echo "text" | python3 scripts/output_check.py --json
```

Rules are in `scripts/rules.yaml` — **customize them with your own rules**.
Includes checks for: traditional Chinese, forbidden words, file path safety,
volatile facts (stale model names), weekday claims, time distance claims,
and lethal trifecta (dangerous capability combinations).

### 5. gate.py — Two-Tier Verification Gate

**When to run**: for irreversible or external outputs (publishing, config changes, releases).

```bash
python3 scripts/gate.py --draft draft.md --refs "reference materials..."
python3 scripts/gate.py --draft draft.md --refs-file spec.md
python3 scripts/gate.py --draft draft.md --skip-model   # Level 1 only
```

**Two tiers**:
- **Level 1 (Computational)**: Deterministic (no model) — scans for known error patterns
- **Level 2 (Inferential)**: Cross-family model — uses a different model family
  to adjudicate against reference materials

**Three verdicts** (strict):
- **GO** = Every claim is supported by references, no conflicts → pass
- **NO-GO** = A claim contradicts references, or hits a ban → block
- **ESCALATE** = References don't cover this, can't verify → escalate to human/stronger model

**The key insight "ESCALATE"**: "Can't verify" is ALWAYS ESCALATE, never NO-GO
and never silent GO. This prevents the most dangerous error — pretending to
judge is worse than being wrong.

### 6. collect_failures.py — Failure Pattern Collection (Self-Harness)

**When to run**: periodically, to detect your most common failure patterns
and improve rules.yaml over time.

```bash
python3 scripts/collect_failures.py --log gate_history.jsonl
python3 scripts/collect_failures.py --log gate_history.jsonl --top 5
```

Inspired by the Self-Harness framework (weakness mining → proposal → validation).
This script does the mining half: it collects gate.py run results, tallies
which rules are most frequently violated, and outputs a ranked report with
recommendations. It does NOT auto-modify rules.yaml — it gives you data to
decide what to strengthen.

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
- **pyyaml** — for output_check.py, gate.py, precheck.py (`pip install pyyaml`)
- **opencc-python-reimplemented** — optional, for Traditional Chinese detection (`pip install opencc-python-reimplemented`)

## How to Customize

1. **Edit `scripts/rules.yaml`** — replace sample rules with your own. Each rule
   should anchor to an objective, verifiable standard.
2. **Set environment variables** — point `FACT_DIR` to your knowledge base,
   set `VERIFIER_*` to a model from a different family than your primary model.
3. **Add your own fact base** — create markdown files with structured facts
   that `factlookup.sh` can search.
4. **Collect failures regularly** — run `collect_failures.py` on your gate.py
   history to find your most common patterns, then strengthen rules.yaml.

## Relationship to Other Systems

This skill is model-agnostic and framework-agnostic. It works with:
- Hermes Agent (as a skill in `~/.hermes/skills/`)
- Claude (as Custom Instructions or Project Knowledge)
- ChatGPT / GPT (as Custom GPT instructions + Knowledge files)
- Cursor / any AI IDE (as `.cursorrules` or custom instructions)
- Any system that can run shell scripts

The core methodology — "use deterministic code instead of model self-checks,
triage errors by type, cross-family verification, feedforward + feedback" — is universal.
