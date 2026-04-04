# Agent Forge — Eval Suite

Regression tests for Agent Forge. Run after any major change to verify improvements.

## Tasks

| # | Task | Tests | Stack |
|---|------|-------|-------|
| 01 | Calculator | Basic CRUD, keyboard events | Next.js + Tailwind |
| 02 | Todo App | State management, localStorage | Next.js + Tailwind |
| 03 | Multi-Step Form | Validation, navigation, progress | Next.js + Tailwind |
| 04 | Dashboard + Charts | 3rd party libs, data viz, responsive | Next.js + Tailwind |
| 05 | Chat App (Full Stack) | WebSocket, real-time, backend + frontend | SvelteKit + Tailwind |

Tasks increase in complexity. Task 05 is the hardest — full-stack with real-time features.

## Running

```bash
# All tasks
bash eval/run-eval.sh

# Single task
bash eval/run-eval.sh 01
bash eval/run-eval.sh 05
```

## Scoring

For each task, check:

| Metric | Source | Good | Bad |
|--------|--------|------|-----|
| Build success | console.log | Completes | Crashes |
| First-round QA pass | QA_SCORES.json | All ≥ threshold | Multiple fails |
| Fix rounds needed | forge.jsonl | 0-1 | 3 (max) |
| Total time | SUMMARY.json | < 10 min | > 30 min |
| Total cost | SUMMARY.json | < $1 | > $3 |
| Visual quality | Screenshot | Polished | Template-y |

## Results

Results are saved to `eval/results/YYYY-MM-DD_HHMM/<task>/` and gitignored.

Each result contains:
- `artifacts/` — SPEC.md, CONTRACT.md, QA_REPORT.md, QA_SCORES.json, manifests/
- `forge.jsonl` — structured event log
- `console.log` — full console output
- The generated project files
