# Agent Forge

GAN-inspired multi-agent harness for building complete features and applications.

**Planner** (Opus 4.6) → **Contract Negotiation** (Generator ↔ Evaluator) → **Build** (Opus 4.6, full session) → **QA** (Opus 4.6 + Playwright CLI) → Fix loop (up to 3 rounds)

No sprints — Opus 4.6 sustains coherent work for hours without decomposition (validated by Anthropic's blog).

Inspired by [Anthropic's harness design blog](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## How It Works

```
USER PROMPT (1-4 sentences)
    ↓
PLANNER         Opus expands prompt into rich product SPEC.md
    ↓
CONTRACT        Generator proposes acceptance criteria (CONTRACT.md)
    ↓                ↕ iterate until agreed
EVALUATOR       Reviews contract, approves or requests changes
    ↓
GENERATOR       Opus builds EVERYTHING in one continuous session
    ↓
EVALUATOR       QAs the running app (Playwright CLI + tools)
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
