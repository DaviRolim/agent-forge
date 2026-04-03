#!/usr/bin/env python3
"""Agent Forge — GAN-inspired multi-agent harness for building features and applications.

Usage:
    python3 forge.py "Build a checkout flow with progress indicator" --dir /path/to/project
    python3 forge.py --task-file task.md --dir /path/to/project --verbose
    python3 forge.py "Build X" --dir /path/to/project --all-opus
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    CONFIDENCE_GATE_PROMPT,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MAX_QA_ROUNDS = 3
MAX_CONTRACT_ROUNDS = 3
MAX_CONFIDENCE_RETRIES = 1
CONFIDENCE_THRESHOLD = 6

# Model tiering — Opus for creative/complex, Sonnet for structured/checklist
PLANNER_MODEL = "opus"
GENERATOR_MODEL = "opus"
EVALUATOR_CONTRACT_MODEL = "sonnet"   # structured review — cheaper
EVALUATOR_QA_MODEL = "sonnet"         # following a checklist — cheaper
CONFIDENCE_MODEL = "sonnet"           # binary go/no-go — cheap

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

# Least-privilege tool subsets per agent role
TOOLS_READ_ONLY = ["Read", "ListFiles", "Search", "Glob"]
TOOLS_READ_EXECUTE = ["Read", "ListFiles", "Search", "Glob", "Bash"]
# Generator uses full bypassPermissions (no tool restriction)

# Stack detection files
STACK_INDICATORS = {
    "package.json": "Node.js",
    "requirements.txt": "Python",
    "pyproject.toml": "Python",
    "Cargo.toml": "Rust",
    "go.mod": "Go",
    "Gemfile": "Ruby",
    "pom.xml": "Java (Maven)",
    "build.gradle": "Java/Kotlin (Gradle)",
    "composer.json": "PHP",
    "mix.exs": "Elixir",
    "Makefile": "Make",
}

# Config/meta files worth mentioning in the project summary
CONFIG_FILES = [
    "tsconfig.json", "next.config.js", "next.config.mjs", "next.config.ts",
    "vite.config.ts", "vite.config.js", "svelte.config.js",
    "tailwind.config.js", "tailwind.config.ts", "postcss.config.js",
    ".eslintrc.json", ".eslintrc.js", "biome.json",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.local",
    "jest.config.js", "vitest.config.ts", "playwright.config.ts",
]


# ---------------------------------------------------------------------------
# CLI Runner
# ---------------------------------------------------------------------------

def run_claude(
    prompt: str,
    cwd: Path,
    model: str = "sonnet",
    verbose: bool = False,
    allowed_tools: list[str] | None = None,
) -> str:
    """Run Claude CLI with a prompt in the target project directory.

    Args:
        prompt: The prompt to send to Claude.
        cwd: Working directory for the Claude process.
        model: Model name (opus, sonnet, etc.).
        verbose: If True, stream output to stdout instead of capturing.
        allowed_tools: If provided, use --allowedTools instead of bypassPermissions.
            This restricts the agent to only the listed tools (least-privilege).
    """
    cmd = [
        "claude",
        "--print",
        "--model", model,
    ]

    if allowed_tools:
        # Least-privilege: restrict to specific tools
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    else:
        # Full access (Generator)
        cmd.extend(["--permission-mode", "bypassPermissions"])

    cmd.extend(["-p", prompt])

    if verbose:
        print(f"  → Running Claude ({model}) in {cwd}")
        if allowed_tools:
            print(f"    Tools: {', '.join(allowed_tools)}")

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


def _prepend_git_context(prompt: str, git_context: str) -> str:
    """Prepend git context to a prompt, inserting it after the dynamic boundary marker."""
    marker = "__FORGE_DYNAMIC_BOUNDARY__"
    if marker in prompt and git_context:
        return prompt.replace(
            marker,
            f"{marker}\n\n## Current Git State\n```\n{git_context}\n```\n",
        )
    elif git_context:
        return f"## Current Git State\n```\n{git_context}\n```\n\n{prompt}"
    return prompt


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
    all_opus: bool = False

    artifacts: Path = field(init=False)
    _log_fh: object = field(init=False, default=None)
    _stage_timings: dict = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.artifacts = self.work_dir / "artifacts"
        self.artifacts.mkdir(parents=True, exist_ok=True)
        (self.artifacts / "manifests").mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self._log_fh = open(self.log_file, "a")

        # Override model tiering if --all-opus
        if self.all_opus:
            global PLANNER_MODEL, GENERATOR_MODEL, EVALUATOR_CONTRACT_MODEL
            global EVALUATOR_QA_MODEL, CONFIDENCE_MODEL
            PLANNER_MODEL = "opus"
            GENERATOR_MODEL = "opus"
            EVALUATOR_CONTRACT_MODEL = "opus"
            EVALUATOR_QA_MODEL = "opus"
            CONFIDENCE_MODEL = "opus"

    def log(self, stage: str, message: str):
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] [{stage}] {message}"
        print(line)
        if self._log_fh:
            self._log_fh.write(json.dumps({"ts": ts, "stage": stage, "msg": message}) + "\n")
            self._log_fh.flush()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_git_context(self) -> str:
        """Get current git status and diff stats from the work directory."""
        parts = []
        try:
            status = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=str(self.work_dir), capture_output=True, text=True, timeout=10,
            )
            if status.returncode == 0 and status.stdout.strip():
                parts.append(status.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        try:
            diff = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=str(self.work_dir), capture_output=True, text=True, timeout=10,
            )
            if diff.returncode == 0 and diff.stdout.strip():
                parts.append(diff.stdout.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return "\n".join(parts)

    def _emit_manifest(self, stage: str, status: str, duration_s: float,
                       model: str, round_num: int = 1):
        """Write a JSON manifest for a completed stage."""
        manifest = {
            "stage": stage,
            "status": status,
            "duration_s": round(duration_s, 1),
            "model": model,
            "round": round_num,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        filename = f"{stage.lower()}_r{round_num}.json"
        manifest_path = self.artifacts / "manifests" / filename
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        self.log("MANIFEST", f"Wrote {filename}")

        # Track for summary
        key = f"{stage}_r{round_num}"
        self._stage_timings[key] = manifest

    def _emit_summary_manifest(self, total_duration: float):
        """Write the final summary manifest with all stage timings."""
        summary = {
            "total_duration_s": round(total_duration, 1),
            "total_duration_min": round(total_duration / 60, 1),
            "stages": self._stage_timings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models": {
                "planner": PLANNER_MODEL,
                "generator": GENERATOR_MODEL,
                "evaluator_contract": EVALUATOR_CONTRACT_MODEL,
                "evaluator_qa": EVALUATOR_QA_MODEL,
                "confidence": CONFIDENCE_MODEL,
            },
        }
        path = self.artifacts / "manifests" / "SUMMARY.json"
        path.write_text(json.dumps(summary, indent=2) + "\n")
        self.log("MANIFEST", "Wrote SUMMARY.json")

    def _detect_project_summary(self) -> str:
        """Generate a concise project summary instead of a full file tree dump."""
        lines = []

        # Project name detection
        project_name = self.work_dir.name
        for manifest_file, label in [
            ("package.json", "name"),
            ("Cargo.toml", "name"),
            ("pyproject.toml", "name"),
        ]:
            manifest_path = self.work_dir / manifest_file
            if manifest_path.is_file():
                try:
                    content = manifest_path.read_text()
                    if manifest_file == "package.json":
                        data = json.loads(content)
                        project_name = data.get("name", project_name)
                    elif "name" in content:
                        # Simple regex for TOML name field
                        m = re.search(r'name\s*=\s*"([^"]+)"', content)
                        if m:
                            project_name = m.group(1)
                except Exception:
                    pass
                break

        lines.append(f"# Project: {project_name}")
        lines.append("")

        # Stack detection
        detected_stacks = []
        for indicator, stack in STACK_INDICATORS.items():
            if (self.work_dir / indicator).is_file():
                detected_stacks.append(f"- {stack} ({indicator})")
        if detected_stacks:
            lines.append("## Stack")
            lines.extend(detected_stacks)
            lines.append("")

        # Key config files
        found_configs = []
        for cfg in CONFIG_FILES:
            if (self.work_dir / cfg).is_file():
                found_configs.append(f"- {cfg}")
        if found_configs:
            lines.append("## Config Files")
            lines.extend(found_configs)
            lines.append("")

        # Top-level directory structure (1 level deep only)
        top_dirs = []
        top_files = []
        for item in sorted(self.work_dir.iterdir()):
            name = item.name
            if name.startswith(".") or name in CONTEXT_EXCLUDE:
                continue
            if item.is_dir():
                top_dirs.append(f"  {name}/")
            elif item.is_file():
                top_files.append(f"  {name}")
        if top_dirs or top_files:
            lines.append("## Top-Level Structure")
            lines.extend(top_dirs[:20])
            lines.extend(top_files[:20])
            lines.append("")

        lines.append("## Exploration")
        lines.append("Use Read, Search, and Glob tools to explore the codebase as needed.")
        lines.append("Do NOT assume the full file tree is provided — discover it yourself.")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(self):
        self.log("FORGE", f"Starting Agent Forge in {self.work_dir}")
        if self.all_opus:
            self.log("FORGE", "All-Opus mode: every agent uses Opus")
        else:
            self.log("FORGE", f"Model tiering: Planner={PLANNER_MODEL}, Generator={GENERATOR_MODEL}, "
                     f"EvalContract={EVALUATOR_CONTRACT_MODEL}, EvalQA={EVALUATOR_QA_MODEL}, "
                     f"Confidence={CONFIDENCE_MODEL}")
        start = time.time()

        # Stage 1: Intake
        self._stage_intake()

        # Stage 2: Planner
        if not self.resume or not (self.artifacts / "SPEC.md").is_file():
            self._stage_planner()
        else:
            self.log("RESUME", "Skipping PLANNER — SPEC.md exists")

        # Stage 3: Contract negotiation
        if not self.resume or not (self.artifacts / "CONTRACT.md").is_file():
            self._stage_contract_negotiation()
        else:
            self.log("RESUME", "Skipping CONTRACT — CONTRACT.md exists")

        # Stage 4: Build + QA loop (with confidence gate)
        self._stage_build_qa_loop()

        elapsed = time.time() - start
        self._emit_summary_manifest(elapsed)
        self.log("FORGE", f"Done in {elapsed/60:.1f} minutes")

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------

    def _stage_intake(self):
        """Write TASK.md and CONTEXT.md (concise project summary, not full tree)."""
        self.log("INTAKE", "Writing task and context files")
        t0 = time.time()

        # TASK.md
        (self.artifacts / "TASK.md").write_text(f"# Task\n\n{self.task}\n")

        # CONTEXT.md — concise project summary (deferred context)
        summary = self._detect_project_summary()
        (self.artifacts / "CONTEXT.md").write_text(summary + "\n")

        elapsed = time.time() - t0
        self._emit_manifest("INTAKE", "complete", elapsed, "none")
        self.log("INTAKE", "TASK.md and CONTEXT.md written (deferred context mode)")

    def _stage_planner(self):
        """Planner expands the user prompt into a rich product spec (read-only tools)."""
        self.log("PLANNER", f"Expanding prompt into product spec ({PLANNER_MODEL})")
        t0 = time.time()

        run_claude(
            PLANNER_PROMPT,
            cwd=self.work_dir,
            model=PLANNER_MODEL,
            verbose=self.verbose,
            allowed_tools=TOOLS_READ_ONLY,  # Planner: read-only
        )

        spec = self.artifacts / "SPEC.md"
        if not spec.is_file():
            raise RuntimeError("Planner did not create SPEC.md")

        elapsed = time.time() - t0
        self._emit_manifest("PLANNER", "complete", elapsed, PLANNER_MODEL)
        self.log("PLANNER", f"SPEC.md created ({spec.stat().st_size} bytes)")

    def _stage_contract_negotiation(self):
        """Generator proposes contract, Evaluator reviews, iterate until agreed."""
        for round_num in range(1, MAX_CONTRACT_ROUNDS + 1):
            # Generator proposes (full access)
            self.log("CONTRACT", f"Round {round_num}: Generator proposing contract")
            t0 = time.time()
            run_claude(
                GENERATOR_CONTRACT_PROMPT,
                cwd=self.work_dir,
                model=GENERATOR_MODEL,
                verbose=self.verbose,
                # Generator gets full access (no allowed_tools)
            )

            contract = self.artifacts / "CONTRACT.md"
            if not contract.is_file():
                raise RuntimeError("Generator did not create CONTRACT.md")
            gen_elapsed = time.time() - t0
            self._emit_manifest("CONTRACT_GEN", "complete", gen_elapsed, GENERATOR_MODEL, round_num)

            # Evaluator reviews (read-only)
            self.log("CONTRACT", f"Round {round_num}: Evaluator reviewing contract")
            t0 = time.time()
            run_claude(
                EVALUATOR_CONTRACT_REVIEW_PROMPT,
                cwd=self.work_dir,
                model=EVALUATOR_CONTRACT_MODEL,
                verbose=self.verbose,
                allowed_tools=TOOLS_READ_ONLY,  # Evaluator contract review: read-only
            )
            eval_elapsed = time.time() - t0
            self._emit_manifest("CONTRACT_EVAL", "complete", eval_elapsed, EVALUATOR_CONTRACT_MODEL, round_num)

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

    def _stage_confidence_gate(self) -> tuple[bool, str]:
        """Cheap Sonnet check: does CHANGES.md cover all acceptance criteria?

        Returns:
            (passed, message) — passed is True if confidence >= threshold.
        """
        self.log("CONFIDENCE", f"Running confidence gate ({CONFIDENCE_MODEL})")
        t0 = time.time()

        output = run_claude(
            CONFIDENCE_GATE_PROMPT,
            cwd=self.work_dir,
            model=CONFIDENCE_MODEL,
            verbose=self.verbose,
            allowed_tools=TOOLS_READ_ONLY,
        )

        elapsed = time.time() - t0
        self._emit_manifest("CONFIDENCE", "complete", elapsed, CONFIDENCE_MODEL)

        # Try to parse JSON from output
        score = 10  # default pass
        missing_items: list[str] = []
        summary = ""

        try:
            # Find JSON block in output
            json_match = re.search(r'\{[^{}]*"confidence_score"[^{}]*\}', output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = int(data.get("confidence_score", 10))
                missing_items = data.get("missing_items", [])
                summary = data.get("summary", "")
        except (json.JSONDecodeError, ValueError, TypeError):
            self.log("CONFIDENCE", "Could not parse confidence JSON — assuming pass")

        # Write result
        result_md = f"# Confidence Check\n\n"
        result_md += f"**Score:** {score}/10\n"
        result_md += f"**Threshold:** {CONFIDENCE_THRESHOLD}\n"
        result_md += f"**Summary:** {summary}\n\n"
        if missing_items:
            result_md += "## Missing Items\n"
            for item in missing_items:
                result_md += f"- {item}\n"
        result_md += f"\n**Result:** {'PASS' if score >= CONFIDENCE_THRESHOLD else 'FAIL'}\n"
        (self.artifacts / "CONFIDENCE_CHECK.md").write_text(result_md)

        passed = score >= CONFIDENCE_THRESHOLD
        missing_str = "; ".join(missing_items) if missing_items else "none"
        self.log("CONFIDENCE", f"Score: {score}/10 — {'PASS' if passed else 'FAIL'} (missing: {missing_str})")

        return passed, missing_str

    def _stage_build_qa_loop(self):
        """Build → Confidence Gate → QA → Fix loop, up to MAX_QA_ROUNDS."""
        for round_num in range(1, MAX_QA_ROUNDS + 1):
            git_context = self._get_git_context()

            # Build
            self.log("BUILD", f"Round {round_num}: Generator implementing")
            t0 = time.time()

            if round_num == 1:
                prompt = _prepend_git_context(GENERATOR_BUILD_PROMPT, git_context)
            else:
                prompt = _prepend_git_context(GENERATOR_FIX_PROMPT, git_context)

            run_claude(
                prompt,
                cwd=self.work_dir,
                model=GENERATOR_MODEL,
                verbose=self.verbose,
                # Generator: full access (no allowed_tools)
            )

            build_elapsed = time.time() - t0
            self._emit_manifest("BUILD", "complete", build_elapsed, GENERATOR_MODEL, round_num)

            changes = self.artifacts / "CHANGES.md"
            if not changes.is_file() and round_num == 1:
                self.log("BUILD", "⚠ No CHANGES.md — Generator may have failed")

            # Confidence Gate (only on first build + retries)
            if changes.is_file():
                confidence_passed, missing_msg = self._stage_confidence_gate()
                if not confidence_passed and round_num == 1:
                    # One retry: tell Generator what's missing
                    self.log("CONFIDENCE", "Gate FAILED — retrying build with missing items")
                    retry_prompt = _prepend_git_context(
                        GENERATOR_FIX_PROMPT + f"\n\nCONFIDENCE GATE FAILED. Missing items:\n{missing_msg}\n"
                        "Address these missing items before proceeding.",
                        self._get_git_context(),
                    )
                    t0 = time.time()
                    run_claude(
                        retry_prompt,
                        cwd=self.work_dir,
                        model=GENERATOR_MODEL,
                        verbose=self.verbose,
                    )
                    retry_elapsed = time.time() - t0
                    self._emit_manifest("BUILD_RETRY", "complete", retry_elapsed, GENERATOR_MODEL, round_num)

            # QA
            self.log("QA", f"Round {round_num}: Evaluator testing the application")
            t0 = time.time()

            qa_prompt = _prepend_git_context(EVALUATOR_QA_PROMPT, self._get_git_context())
            run_claude(
                qa_prompt,
                cwd=self.work_dir,
                model=EVALUATOR_QA_MODEL,
                verbose=self.verbose,
                allowed_tools=TOOLS_READ_EXECUTE,  # Evaluator QA: read + execute (no code writes)
            )

            qa_elapsed = time.time() - t0
            self._emit_manifest("QA", "complete", qa_elapsed, EVALUATOR_QA_MODEL, round_num)

            qa_report = self.artifacts / "QA_REPORT.md"
            if not qa_report.is_file():
                self.log("QA", "No QA_REPORT.md — assuming approved")
                break

            qa_text = qa_report.read_text()

            # Check verdict — JSON first, then text fallback
            approved = False

            # Try JSON scores first
            scores = self._parse_qa_scores(qa_text)
            if scores:
                score_str = " | ".join(f"{k}: {v}" for k, v in scores.items() if k != "verdict" and k != "ac_results")
                self.log("QA", f"Round {round_num}: Scores: {score_str}")

                # Auto-approve if ALL scores meet threshold
                all_meet = True
                for criterion, threshold in QA_SCORE_THRESHOLD.items():
                    score_val = scores.get(criterion)
                    if score_val is not None:
                        try:
                            if int(score_val) < threshold:
                                all_meet = False
                                break
                        except (ValueError, TypeError):
                            all_meet = False
                            break
                    else:
                        all_meet = False
                        break

                if all_meet:
                    approved = True
                    self.log("QA", f"Round {round_num}: ALL scores meet thresholds — auto-approved ✅")

            # Text-based verdict check
            if not approved and "VERDICT: APPROVE" in qa_text.upper():
                approved = True
                self.log("QA", f"Round {round_num}: VERDICT: APPROVE found ✅")

            if approved:
                break
            elif round_num < MAX_QA_ROUNDS:
                self.log("QA", f"Round {round_num}: REQUEST_CHANGES — Generator will fix")
            else:
                self.log("QA", "Max QA rounds reached — shipping as-is")

    def _parse_qa_scores(self, text: str) -> dict[str, any]:
        """Parse QA scores — try JSON file first, then regex fallback on report text."""
        # Try reading QA_SCORES.json first
        json_path = self.artifacts / "QA_SCORES.json"
        if json_path.is_file():
            try:
                data = json.loads(json_path.read_text())
                self.log("QA", "Parsed scores from QA_SCORES.json")
                return data
            except (json.JSONDecodeError, KeyError):
                self.log("QA", "QA_SCORES.json exists but failed to parse — falling back to regex")

        # Regex fallback on QA report text
        scores = {}
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            for criterion in ["product_depth", "product depth", "functionality",
                              "visual_design", "visual design", "code_quality", "code quality"]:
                if criterion.replace("_", " ") in line_lower or criterion in line_lower:
                    match = re.search(r"(\d+)\s*/\s*10", line)
                    if match:
                        # Normalize key to underscore format
                        key = criterion.replace(" ", "_")
                        scores[key] = int(match.group(1))
        return scores if scores else {}


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
    parser.add_argument("--all-opus", action="store_true",
                        help="Force all agents to use Opus (override model tiering)")

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
        all_opus=args.all_opus,
    )

    forge.run()


if __name__ == "__main__":
    main()
