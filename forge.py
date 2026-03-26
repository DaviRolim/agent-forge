#!/usr/bin/env python3
"""Agent Forge — GAN-inspired multi-agent harness for building features and applications.

Usage:
    python3 forge.py "Build a checkout flow with progress indicator" --dir /path/to/project
    python3 forge.py --task-file task.md --dir /path/to/project --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from prompts import (
    PLANNER_PROMPT,
    GENERATOR_CONTRACT_PROMPT,
    EVALUATOR_CONTRACT_REVIEW_PROMPT,
    GENERATOR_BUILD_PROMPT,
    EVALUATOR_QA_PROMPT,
    GENERATOR_FIX_PROMPT,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAX_QA_ROUNDS = 3
MAX_CONTRACT_ROUNDS = 3
PLANNER_MODEL = "opus"           # Claude Opus 4.6
GENERATOR_MODEL = "opus"         # Claude Opus 4.6 (all agents use best model)
EVALUATOR_MODEL = "opus"         # Claude Opus 4.6
QA_SCORE_THRESHOLD = {
    "product_depth": 7,
    "functionality": 7,
    "visual_design": 6,
    "code_quality": 6,
}

CONTEXT_EXCLUDE = {
    ".git", "artifacts", "__pycache__", ".venv", "venv",
    "node_modules", ".next", ".svelte-kit", "dist", "build",
    ".mypy_cache", ".pytest_cache", "coverage",
}


# ---------------------------------------------------------------------------
# CLI Runner
# ---------------------------------------------------------------------------

def run_claude(prompt: str, cwd: Path, model: str = "sonnet", verbose: bool = False) -> str:
    """Run Claude CLI with a prompt in the target project directory."""
    cmd = [
        "claude",
        "--print",
        "--model", model,
        "--permission-mode", "bypassPermissions",
        "-p", prompt,
    ]

    if verbose:
        print(f"  → Running Claude ({model}) in {cwd}")

    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=not verbose,
        text=True,
        timeout=7200,  # 2 hour max per agent call
    )

    if result.returncode != 0 and not verbose:
        print(f"  ⚠ Claude exited with code {result.returncode}")
        if result.stderr:
            print(f"  stderr: {result.stderr[:500]}")

    return result.stdout if not verbose else ""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

@dataclass
class Forge:
    task: str
    work_dir: Path
    verbose: bool = False
    resume: bool = False
    log_file: Path | None = None

    artifacts: Path = field(init=False)
    _log_fh: object = field(init=False, default=None)

    def __post_init__(self):
        self.artifacts = self.work_dir / "artifacts"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self._log_fh = open(self.log_file, "a")

    def log(self, stage: str, message: str):
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] [{stage}] {message}"
        print(line)
        if self._log_fh:
            self._log_fh.write(json.dumps({"ts": ts, "stage": stage, "msg": message}) + "\n")
            self._log_fh.flush()

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(self):
        self.log("FORGE", f"Starting Agent Forge in {self.work_dir}")
        start = time.time()

        # Stage 1: Intake
        self._stage_intake()

        # Stage 2: Planner
        if not self.resume or not (self.artifacts / "SPEC.md").is_file():
            self._stage_planner()
        else:
            self.log("RESUME", "Skipping PLANNER — SPEC.md exists")

        # Stage 3: Contract negotiation
        if not self.resume or not (self.artifacts / "SPRINT_CONTRACT.md").is_file():
            self._stage_contract_negotiation()
        else:
            self.log("RESUME", "Skipping CONTRACT — SPRINT_CONTRACT.md exists")

        # Stage 4: Build + QA loop
        self._stage_build_qa_loop()

        elapsed = time.time() - start
        self.log("FORGE", f"Done in {elapsed/60:.1f} minutes")

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------

    def _stage_intake(self):
        """Write TASK.md and CONTEXT.md."""
        self.log("INTAKE", "Writing task and context files")

        # TASK.md
        (self.artifacts / "TASK.md").write_text(f"# Task\n\n{self.task}\n")

        # CONTEXT.md — repo file listing
        context_lines = ["# Project Context\n", "## File Listing\n", "```"]
        for root, dirs, files in os.walk(self.work_dir):
            dirs[:] = [d for d in dirs if d not in CONTEXT_EXCLUDE]
            rel = Path(root).relative_to(self.work_dir)
            for f in sorted(files):
                if not f.startswith("."):
                    context_lines.append(str(rel / f))
        context_lines.append("```\n")
        (self.artifacts / "CONTEXT.md").write_text("\n".join(context_lines))

        self.log("INTAKE", "TASK.md and CONTEXT.md written")

    def _stage_planner(self):
        """Planner expands the user prompt into a rich product spec."""
        self.log("PLANNER", "Opus 4.6 expanding prompt into product spec")
        run_claude(PLANNER_PROMPT, cwd=self.work_dir, model=PLANNER_MODEL, verbose=self.verbose)

        spec = self.artifacts / "SPEC.md"
        if not spec.is_file():
            raise RuntimeError("Planner did not create SPEC.md")

        self.log("PLANNER", f"SPEC.md created ({spec.stat().st_size} bytes)")

    def _stage_contract_negotiation(self):
        """Generator proposes contract, Evaluator reviews, iterate until agreed."""
        for round_num in range(1, MAX_CONTRACT_ROUNDS + 1):
            self.log("CONTRACT", f"Round {round_num}: Generator proposing contract")
            run_claude(GENERATOR_CONTRACT_PROMPT, cwd=self.work_dir, model=GENERATOR_MODEL, verbose=self.verbose)

            contract = self.artifacts / "SPRINT_CONTRACT.md"
            if not contract.is_file():
                raise RuntimeError("Generator did not create SPRINT_CONTRACT.md")

            self.log("CONTRACT", f"Round {round_num}: Evaluator reviewing contract")
            run_claude(EVALUATOR_CONTRACT_REVIEW_PROMPT, cwd=self.work_dir, model=EVALUATOR_MODEL, verbose=self.verbose)

            review = self.artifacts / "CONTRACT_REVIEW.md"
            if not review.is_file():
                self.log("CONTRACT", "No CONTRACT_REVIEW.md — assuming approved")
                break

            review_text = review.read_text()
            if "VERDICT: APPROVE" in review_text.upper() or "APPROVE" in review_text.upper().split("\n")[0]:
                self.log("CONTRACT", "Contract APPROVED")
                break
            else:
                self.log("CONTRACT", f"Round {round_num}: Contract needs changes — iterating")
                if round_num == MAX_CONTRACT_ROUNDS:
                    self.log("CONTRACT", "Max rounds reached — proceeding with current contract")

    def _stage_build_qa_loop(self):
        """Build → QA → Fix loop, up to MAX_QA_ROUNDS."""
        for round_num in range(1, MAX_QA_ROUNDS + 1):
            # Build
            self.log("BUILD", f"Round {round_num}: Generator implementing")
            prompt = GENERATOR_BUILD_PROMPT if round_num == 1 else GENERATOR_FIX_PROMPT
            run_claude(prompt, cwd=self.work_dir, model=GENERATOR_MODEL, verbose=self.verbose)

            changes = self.artifacts / "CHANGES.md"
            if not changes.is_file() and round_num == 1:
                self.log("BUILD", "⚠ No CHANGES.md — Generator may have failed")

            # QA
            self.log("QA", f"Round {round_num}: Evaluator testing the application")
            run_claude(EVALUATOR_QA_PROMPT, cwd=self.work_dir, model=EVALUATOR_MODEL, verbose=self.verbose)

            qa_report = self.artifacts / "QA_REPORT.md"
            if not qa_report.is_file():
                self.log("QA", "No QA_REPORT.md — assuming approved")
                break

            qa_text = qa_report.read_text()

            # Parse verdict
            if "VERDICT: APPROVE" in qa_text.upper():
                self.log("QA", f"Round {round_num}: ALL CRITERIA PASSED — Approved ✅")
                break
            else:
                # Parse scores if present
                scores = self._parse_qa_scores(qa_text)
                if scores:
                    score_str = " | ".join(f"{k}: {v}" for k, v in scores.items())
                    self.log("QA", f"Round {round_num}: Scores: {score_str}")

                if round_num < MAX_QA_ROUNDS:
                    self.log("QA", f"Round {round_num}: REQUEST_CHANGES — Generator will fix")
                else:
                    self.log("QA", "Max QA rounds reached — shipping as-is")

    def _parse_qa_scores(self, text: str) -> dict[str, str]:
        """Try to extract scores from QA report."""
        scores = {}
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            for criterion in ["product depth", "functionality", "visual design", "code quality"]:
                if criterion in line_lower:
                    # Look for a number
                    import re
                    match = re.search(r"(\d+)\s*/\s*10", line)
                    if match:
                        scores[criterion] = f"{match.group(1)}/10"
        return scores


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Agent Forge — multi-agent build harness")
    parser.add_argument("task", nargs="?", help="Task description")
    parser.add_argument("--task-file", help="Path to markdown file with task")
    parser.add_argument("--dir", required=True, help="Target project directory")
    parser.add_argument("--verbose", action="store_true", help="Stream agent output")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--log-file", help="Write structured JSONL events")

    args = parser.parse_args()

    # Get task from args or file
    if args.task_file:
        task = Path(args.task_file).read_text().strip()
    elif args.task:
        task = args.task
    else:
        parser.error("Provide a task string or --task-file")

    work_dir = Path(args.dir).resolve()
    if not work_dir.is_dir():
        print(f"Error: {work_dir} is not a directory")
        sys.exit(1)

    forge = Forge(
        task=task,
        work_dir=work_dir,
        verbose=args.verbose,
        resume=args.resume,
        log_file=Path(args.log_file) if args.log_file else None,
    )

    forge.run()


if __name__ == "__main__":
    main()
