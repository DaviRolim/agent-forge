# Agent Forge

GAN-inspired multi-agent harness for building complete features and applications.

**Planner** (Opus) → **Contract Negotiation** (Generator ↔ Evaluator) → **Confidence Gate** (Sonnet) → **Build** (Opus) → **QA** (Sonnet) → Fix loop (up to 3 rounds)

No sprints — Opus sustains coherent work for hours without decomposition (validated by Anthropic's blog).

Inspired by [Anthropic's harness design blog](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## How It Works

```
USER PROMPT (1-4 sentences)
    ↓
INTAKE          Writes TASK.md + concise CONTEXT.md (project summary, not full tree)
    ↓
PLANNER         Opus expands prompt into rich product SPEC.md (read-only tools)
    ↓
CONTRACT        Generator proposes acceptance criteria (CONTRACT.md)
    ↓                ↕ iterate until agreed
EVALUATOR       Reviews contract, approves or requests changes (read-only tools)
    ↓
GENERATOR       Opus builds EVERYTHING in one continuous session (full tool access)
    ↓
CONFIDENCE      Sonnet quick-checks: does CHANGES.md cover all ACs? (retry if <6/10)
    ↓
EVALUATOR       QAs the running app — 4 phases: ORIENT → GATHER → EXECUTE → PRUNE
    ↓
                If FAIL → fix → re-evaluate (max 3 rounds)
    ↓
DONE            All criteria pass (auto-approve if all scores ≥ threshold)
```

All agents run via Claude CLI (`claude --print -p`) in the TARGET project directory.
Uses your Claude Max subscription — no API key costs.

## Usage

```bash
# Basic usage
python3 forge.py "Redesign the checkout flow with a progress indicator" \
  --dir /path/to/target/project \
  --verbose

# From a task file
python3 forge.py --task-file task.md --dir /path/to/project

# Resume from checkpoint (skip completed stages)
python3 forge.py "Build X" --dir /path/to/project --resume

# Force all agents to use Opus (override model tiering)
python3 forge.py "Build X" --dir /path/to/project --all-opus
```

## Features

### Model Tiering (v2)
By default, each agent uses the most cost-effective model for its role:

| Agent | Model | Rationale |
|-------|-------|-----------|
| Planner | Opus | Creative expansion needs best model |
| Generator | Opus | Complex implementation needs best model |
| Evaluator (contract) | Sonnet | Structured review — cheaper |
| Evaluator (QA) | Sonnet | Following a checklist — cheaper |
| Confidence Gate | Sonnet | Binary go/no-go — cheap |

Use `--all-opus` to force every agent to Opus.

### Least-Privilege Tool Subsets (v2)
Each agent only gets the tools it needs:
- **Planner:** Read, ListFiles, Search, Glob (read-only)
- **Evaluator (contract):** Read, ListFiles, Search, Glob (read-only)
- **Evaluator (QA):** Read, ListFiles, Search, Glob, Bash (can run servers/tests, can't write code)
- **Generator:** Full access (bypassPermissions)

### Deferred Context (v2)
Instead of dumping the entire file tree into CONTEXT.md (token-expensive on large repos), Forge writes a concise project summary:
- Project name (detected from package.json, Cargo.toml, etc.)
- Stack detection
- Key config files
- Agents are told to use Read/Search/Glob to explore as needed

### Confidence Gate (v2)
After the Generator builds, a cheap Sonnet call checks whether CHANGES.md covers all acceptance criteria. If confidence < 6/10, the Generator gets one retry with the missing items listed. Saves expensive QA rounds on obviously incomplete builds.

### Structured QA Scores (v2)
The Evaluator writes `artifacts/QA_SCORES.json` alongside QA_REPORT.md:
```json
{
  "product_depth": 7,
  "functionality": 8,
  "visual_design": 6,
  "code_quality": 7,
  "verdict": "APPROVE",
  "ac_results": {"AC-1": "PASS", "AC-2": "FAIL"}
}
```
Auto-approves if ALL scores meet thresholds, even without "VERDICT: APPROVE" text.

### Git Context Injection (v2)
Generator and Evaluator prompts are automatically prefixed with `git status` and `git diff --stat`, so agents always know the current repo state.

### Phase-Based QA (v2)
The QA evaluator follows four explicit phases:
1. **ORIENT** — Read contract, spec, and changes
2. **GATHER** — Start dev server, test every page, collect evidence
3. **EXECUTE** — Grade each criterion with collected evidence
4. **PRUNE** — Remove noise, write structured verdict + QA_SCORES.json

### Manifest-Based Observability (v2)
Every stage writes a JSON manifest to `artifacts/manifests/`:
```json
{"stage": "PLANNER", "status": "complete", "duration_s": 45, "model": "opus", "round": 1, "timestamp": "..."}
```
A summary manifest (`SUMMARY.json`) is written at the end with total duration and per-stage breakdown.

### Prompt Caching Boundary (v2)
All prompts use `__FORGE_DYNAMIC_BOUNDARY__` to separate static instructions from dynamic context, enabling future prompt caching optimizations.

### Auto-Compaction Awareness (v2)
Generator prompts include instructions to summarize progress if context grows large, preventing restarts from scratch during long sessions.

## Artifacts

After a run, `artifacts/` contains:
- `TASK.md` — Original user prompt
- `CONTEXT.md` — Project summary
- `SPEC.md` — Product specification (Planner output)
- `CONTRACT.md` — Build contract with acceptance criteria
- `CONTRACT_REVIEW.md` — Evaluator's contract review
- `CHANGES.md` — What the Generator built
- `CONFIDENCE_CHECK.md` — Confidence gate result
- `QA_REPORT.md` — QA evaluation report
- `QA_SCORES.json` — Machine-readable QA scores
- `IMPL_NOTES.md` — Generator's implementation notes (if any)
- `manifests/` — Per-stage JSON manifests + SUMMARY.json

## Requirements

- Python 3.12+
- Claude CLI (`claude`) authenticated with Claude Max
- Target project accessible on disk
