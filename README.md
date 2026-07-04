# External Truth Layer

A verification toolkit for AI agents that replaces "weak model checking weak model" with deterministic code, external references, and cross-family model verification.

Works with any AI system that can run shell scripts — Claude, ChatGPT, Gemini, DeepSeek, Hermes Agent, Cursor, custom GPTs, and more.

## The Problem It Solves

AI models verifying themselves is like a student grading their own homework: the same blind spots that caused the error also prevent catching it. "Does this look right?" asked to the same brain that wrote it gets you a confident "yes" regardless of whether it's actually correct.

This is especially dangerous for:

- **Date/weekday claims** — LLMs generate "Wednesday" via semantic pattern-matching, not calendar arithmetic
- **Factual references** — LLMs hallucinate or rely on outdated training data
- **Compliance checks** — LLMs miss banned words or format violations they themselves introduced
- **Pre-publish validation** — "Looks good to me" from the same model that wrote it is not verification

## The Solution

Four tools that shift verification from "model judgment" to "deterministic code + external references":

| Tool | What it does | Needs a model? |
|------|-------------|----------------|
| `precheck.py` | Scans task description for known risk patterns BEFORE generation (feedforward) | No |
| `datecheck.py` | Computes weekdays and time distances using Python datetime | No |
| `factlookup.sh` | Searches a local fact/knowledge base via grep | No |
| `output_check.py` | Checks format compliance (traditional chars, banned words, stale model names, weekday claims, lethal trifecta) | No |
| `gate.py` | Two-tier verification gate: deterministic Level 1 + cross-family model Level 2 | Level 2 only |
| `collect_failures.py` | Collects gate.py run history, tallies most common failure patterns, recommends rule improvements | No |

### The Three Verdicts (gate.py)

- **GO** — Every claim is supported by reference materials. Pass.
- **NO-GO** — A claim directly contradicts references, or hits a ban. Block.
- **ESCALATE** — References don't cover this, can't verify. **"Can't verify" is never NO-GO and never silent GO** — it goes to human review. Pretending to judge is worse than being wrong.

## Installation

### Prerequisites

- Python 3
- pyyaml (`pip install pyyaml`)
- opencc-python-reimplemented (optional, for Chinese traditional/simplified detection: `pip install opencc-python-reimplemented`)

### Use with Hermes Agent

```bash
mkdir -p ~/.hermes/skills/hermes/external-truth-layer
cd ~/.hermes/skills/hermes/external-truth-layer
git clone https://github.com/hanxing-AI/external-truth-layer.git .
```

### Use with Claude (Projects / Custom Instructions)

Copy the contents of `SKILL.md` into your Project's Custom Instructions.
Upload `scripts/` as Knowledge files.

### Use with ChatGPT (Custom GPT)

Paste `SKILL.md` into your GPT's Instructions. Upload `scripts/` as Knowledge files.

### Use with Cursor / Cline / other AI IDEs

Copy `SKILL.md` into `.cursorrules` or `.cline_custom_instructions.md`.
Place `scripts/` in your project directory.

### Use with any system supporting system prompts

`SKILL.md` is a system prompt. `scripts/` are tools the agent can call.

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `FACT_DIR` | Fact base directory for factlookup.sh | `~/.local/fact-base` |
| `FACT_INDEX` | Index file path | `$FACT_DIR/index.md` |
| `VERIFIER_API_KEY` | API key for gate.py Level 2 cross-family verifier | (none) |
| `VERIFIER_BASE_URL` | Verifier API base URL | `https://api.deepseek.com` |
| `VERIFIER_MODEL` | Verifier model name | `deepseek-chat` |

### Customizing rules.yaml

The `scripts/rules.yaml` file ships with sample rules. **You should replace
them with your own.** Each rule should anchor to an objective, verifiable
standard — not subjective quality judgment.

Key principle: only include rules that can be checked against objective
references (format, compliance, factual grounding, consistency). "Deep domain
correctness" (is the article well-written? is the logic sound?) goes to human
review or a stronger model, not to this checker.

### Choosing a cross-family verifier

The whole point of Level 2 is decorrelation. If your primary model is from
family A, your verifier should be from family B:

| Primary model family | Suggested verifier |
|----------------------|-------------------|
| Anthropic (Claude) | DeepSeek, Qwen, or GPT |
| OpenAI (GPT) | DeepSeek, Claude, or Qwen |
| DeepSeek | Claude or GPT |
| Google (Gemini) | DeepSeek or Claude |
| Local model | Any cloud model from a different family |

## File Structure

```
external-truth-layer/
├── SKILL.md                ← Main skill file (load this)
├── README.md               ← You are here
├── LICENSE                 ← MIT
├── .gitignore
└── scripts/
    ├── precheck.py         ← Feedforward pre-check (run before generation)
    ├── datecheck.py        ← Deterministic date/weekday calculator
    ├── factlookup.sh       ← Fact base grep wrapper
    ├── output_check.py     ← Format compliance checker
    ├── gate.py             ← Two-tier verification gate
    ├── collect_failures.py ← Failure pattern collection (self-improvement)
    └── rules.yaml          ← Rules for all checkers (customize this!)
```

## Quick Start

```bash
# Pre-check a task for known risks (before generation)
python3 scripts/precheck.py --task "Write about next Wednesday and the latest model prices"

# Check a date
python3 scripts/datecheck.py 2026-07-04

# Check content before publishing
python3 scripts/output_check.py --file my-article.md

# Full two-tier gate with reference materials
python3 scripts/gate.py --draft my-article.md --refs "known facts and constraints..."

# Gate with deterministic layer only (no model needed)
python3 scripts/gate.py --draft my-article.md --skip-model

# Analyze your most common failure patterns
python3 scripts/collect_failures.py --log gate_history.jsonl
```

## Why This Matters

The core insight — **weak models verifying weak models is ineffective for capability errors** — applies regardless of model strength. Even a strong model has blind spots when checking its own output. The solution isn't "try harder" or "think more carefully"; it's structural: shift verification to code and external references that don't share the model's blind spots.

This toolkit is particularly valuable when:
- Running on a weaker/local model and wanting stronger-model-quality verification
- Publishing content where errors are costly (public posts, config changes, releases)
- Working with dates, facts, or compliance requirements where deterministic checks exist

## Further Reading

This toolkit is part of a broader conversation about "harness engineering" —
the scaffolding around an AI model that determines whether it succeeds or
fails on real tasks. Key resources:

- **Anthropic, "Building Effective Agents"** — distinguishing workflows from agents, and when to use each
- **LangChain / Vivek Trivedy, "The Anatomy of an Agent Harness"** — the five primitives of a harness (filesystem, code execution, sandbox, memory, context management)
- **Addy Osmani, "Agent Harness Engineering"** — the "Agent = Model + Harness" formula: "A decent model with a great harness beats a great model with a bad harness"
- **Birgitta Böckeler (martinfowler.com)** — computational vs inferential controls, feedforward vs feedback, the "cybernetic governor" metaphor
- **awesome-harness-engineering (GitHub)** — curated collection of harness engineering resources covering tools, patterns, evaluation, memory, permissions, and observability
- **Self-Harness (Shanghai AI Lab)** — agents that detect their own failure patterns and propose harness improvements autonomously

## Acknowledgments

The core methodology was developed through practical iteration with AI agent
systems, informed by the insight that verification leverage comes from
comparing against objective references rather than soliciting a second opinion
from the same type of brain.

## License

MIT — use it, modify it, ship it, just keep the copyright notice.

## Contributing

Fork it, customize `rules.yaml` for your use case, and share your improvements.
The most valuable contributions are new rule patterns for `rules.yaml` that
catch common AI output failures.
