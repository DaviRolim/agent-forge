# Agent Forge

GAN-inspired multi-agent harness for building complete features and applications.

**Planner** (Opus 4.6) → **Contract Negotiation** (Generator ↔ Evaluator) → **Build** (Sonnet 4.6) → **QA** (Opus 4.6 + Playwright) → Fix loop (up to 3 rounds)

Inspired by [Anthropic's harness design blog](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## How It Works

```
USER PROMPT (1-4 sentences)
    ↓
PLANNER         Opus expands prompt into rich product SPEC.md
    ↓
CONTRACT        Generator proposes acceptance criteria
    ↓                ↕ iterate until agreed
EVALUATOR       Reviews contract, approves or requests changes
    ↓
BUILDER         Sonnet implements against the contract
    ↓
EVALUATOR       QAs the running app (Playwright + CLI)
    ↓
                If FAIL → fix → re-evaluate (max 3 rounds)
    ↓
DONE            All criteria pass
```

All agents run via Claude CLI (`claude --print -p`) in the TARGET project directory.
Uses your Claude Max subscription — no API key costs.

## Usage

```bash
python3 forge.py "Redesign the checkout flow with a progress indicator" \
  --dir /path/to/target/project \
  --verbose
```

## Requirements

- Python 3.12+
- Claude CLI (`claude`) authenticated with Claude Max
- Target project accessible on disk
