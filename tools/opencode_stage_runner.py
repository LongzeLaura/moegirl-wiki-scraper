#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opencode_stage_runner.py — Automated multi-stage opencode task runner.

Splits the profile-based crawler refactor into multiple stages,
each executed in a separate opencode session for context isolation.

Usage:
    python tools/opencode_stage_runner.py --list
    python tools/opencode_stage_runner.py --dry-run
    python tools/opencode_stage_runner.py --from P0-3 --until P0-4 --dry-run
    python tools/opencode_stage_runner.py --from P0-3 --until P0-4
    python tools/opencode_stage_runner.py --only P1-2
    python tools/opencode_stage_runner.py --resume
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
AGENT_TASKS_DIR = ROOT / "docs" / "agent_tasks"
AGENT_RUNS_DIR = ROOT / "docs" / "agent_runs"

ALL_STAGES = [
    {"id": "P0-1", "name": "Global Link Filtering", "prompt": "P0-1_global_link_filtering.md"},
    {"id": "P0-2", "name": "Priority Queue & Checkpoint", "prompt": "P0-2_priority_queue_checkpoint.md"},
    {"id": "P0-3", "name": "Score Detail Logging", "prompt": "P0-3_score_detail_logging.md"},
    {"id": "P0-4", "name": "Dry-Run Mode", "prompt": "P0-4_dry_run_mode.md"},
    {"id": "P0-5", "name": "Crawl Report", "prompt": "P0-5_crawl_report.md"},
    {"id": "P1-1", "name": "Profile Loader & Entrypoint", "prompt": "P1-1_profile_loader_and_entrypoint.md"},
    {"id": "P1-2", "name": "FSN Profile & Template", "prompt": "P1-2_fsn_profile_and_template.md"},
    {"id": "P1-3", "name": "Output Isolation & Compat", "prompt": "P1-3_output_isolation_and_compat.md"},
    {"id": "P1-4", "name": "Docs & Final Validation", "prompt": "P1-4_docs_and_final_validation.md"},
]

STAGE_ID_LIST = [s["id"] for s in ALL_STAGES]
STAGE_MAP = {s["id"]: s for s in ALL_STAGES}


def stage_index(stage_id: str) -> int:
    if stage_id not in STAGE_ID_LIST:
        return -1
    return STAGE_ID_LIST.index(stage_id)


def resolve_stages(args) -> list[dict]:
    if args.only:
        if args.only not in STAGE_MAP:
            print(f"[ERROR] Unknown stage ID: {args.only}", file=sys.stderr)
            print(f"  Available: {', '.join(STAGE_ID_LIST)}", file=sys.stderr)
            sys.exit(1)
        return [STAGE_MAP[args.only]]

    start_idx = 0
    end_idx = len(ALL_STAGES) - 1

    if args.from_stage:
        if args.from_stage not in STAGE_MAP:
            print(f"[ERROR] Unknown stage ID: {args.from_stage}", file=sys.stderr)
            print(f"  Available: {', '.join(STAGE_ID_LIST)}", file=sys.stderr)
            sys.exit(1)
        start_idx = stage_index(args.from_stage)

    if args.until_stage:
        if args.until_stage not in STAGE_MAP:
            print(f"[ERROR] Unknown stage ID: {args.until_stage}", file=sys.stderr)
            print(f"  Available: {', '.join(STAGE_ID_LIST)}", file=sys.stderr)
            sys.exit(1)
        end_idx = stage_index(args.until_stage)

    if start_idx > end_idx:
        print(f"[ERROR] --from {ALL_STAGES[start_idx]['id']} is after --until {ALL_STAGES[end_idx]['id']}", file=sys.stderr)
        sys.exit(1)

    return ALL_STAGES[start_idx:end_idx + 1]


def get_completed_stages(run_dir: Path) -> set[str]:
    completed = set()
    log_file = run_dir / "run_log.jsonl"
    if not log_file.exists():
        return completed
    try:
        for line in log_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("event") == "stage_end" and entry.get("exit_code") == 0:
                completed.add(entry["stage_id"])
    except (json.JSONDecodeError, OSError):
        pass
    return completed


def find_latest_run_dir() -> Optional[Path]:
    if not AGENT_RUNS_DIR.exists():
        return None
    run_dirs = sorted([d for d in AGENT_RUNS_DIR.iterdir() if d.is_dir()])
    return run_dirs[-1] if run_dirs else None


def git_status_short() -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=str(ROOT),
            timeout=30,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"[ERROR] git status failed: {e}"


def build_stage_prompt(stage: dict, run_dir: Path, prev_report_path: Optional[Path]) -> str:
    global_ctx_path = AGENT_TASKS_DIR / "GLOBAL_CONTEXT.md"
    prompt_path = AGENT_TASKS_DIR / stage["prompt"]

    parts = []

    parts.append("# Task: Execute Stage " + stage["id"] + " - " + stage["name"])
    parts.append("")
    parts.append("## Global Context")
    parts.append("")
    parts.append("Please read the global context file first:")
    parts.append("  " + str(global_ctx_path))
    parts.append("")

    if prev_report_path and prev_report_path.exists():
        parts.append("## Previous Stage Report")
        parts.append("")
        parts.append("The previous stage completed successfully. Read its report:")
        parts.append("  " + str(prev_report_path))
        parts.append("")

    parts.append("## Current Stage Prompt")
    parts.append("")
    parts.append("Read and follow the instructions in:")
    parts.append("  " + str(prompt_path))
    parts.append("")

    parts.append("## Execution Context")
    parts.append("")
    parts.append("- Run ID: " + run_dir.name)
    parts.append("- Stage ID: " + stage["id"])
    parts.append("- Stage report output path: " + str(run_dir / (stage["id"] + "_report.md")))
    parts.append("")
    parts.append("## Important Rules")
    parts.append("")
    parts.append("1. Only do the tasks specified in the stage prompt.")
    parts.append("2. Do NOT do tasks from future stages.")
    parts.append("3. If you notice issues that belong to future stages, record them in the stage report but do NOT fix them now.")
    parts.append("4. After completing all tasks, write the stage report to: " + str(run_dir / (stage["id"] + "_report.md")))
    parts.append("5. The stage report must include: modified files, verification commands, verification results, incomplete items, notes for next stage.")

    return "\n".join(parts)


def run_stage(stage: dict, run_dir: Path, prev_report_path: Optional[Path],
              agent_cmd: str, agent_args: str, dry_run: bool, commit: bool) -> int:
    stage_id = stage["id"]
    prompt_content = build_stage_prompt(stage, run_dir, prev_report_path)

    prompt_file = run_dir / (stage_id + "_prompt.md")
    prompt_file.write_text(prompt_content, encoding="utf-8")

    stdout_file = run_dir / (stage_id + "_stdout.log")
    stderr_file = run_dir / (stage_id + "_stderr.log")

    log_entry_start = {
        "event": "stage_start",
        "stage_id": stage_id,
        "time": datetime.now(timezone.utc).isoformat(),
        "prompt_file": str(prompt_file),
        "stdout_file": str(stdout_file),
        "stderr_file": str(stderr_file),
        "report_file": str(run_dir / (stage_id + "_report.md")),
    }

    git_before = git_status_short()
    log_entry_start["git_status_before"] = git_before

    if git_before:
        print(f"  [WARN] Working directory has uncommitted changes:")
        for line in git_before.splitlines()[:10]:
            print(f"         {line}")
        if len(git_before.splitlines()) > 10:
            print(f"         ... and {len(git_before.splitlines()) - 10} more")

    append_log(run_dir, log_entry_start)

    if dry_run:
        print(f"  [DRY-RUN] Would execute stage {stage_id}")
        print(f"  [DRY-RUN] Prompt file: {prompt_file}")
        cmd_str = build_command_str(agent_cmd, agent_args, prompt_file)
        print(f"  [DRY-RUN] Command: {cmd_str}")
        log_entry_end = {
            "event": "stage_end",
            "stage_id": stage_id,
            "time": datetime.now(timezone.utc).isoformat(),
            "exit_code": 0,
            "dry_run": True,
        }
        append_log(run_dir, log_entry_end)
        return 0

    cmd_str = build_command_str(agent_cmd, agent_args, prompt_file)
    print(f"  [EXEC] Running: {cmd_str}")

    try:
        with open(stdout_file, "w", encoding="utf-8") as sf, open(stderr_file, "w", encoding="utf-8") as ef:
            proc = subprocess.run(
                cmd_str,
                shell=True,
                stdout=sf,
                stderr=ef,
                cwd=str(ROOT),
                timeout=None,
            )
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        exit_code = -1
    except Exception as e:
        print(f"  [ERROR] Failed to execute: {e}", file=sys.stderr)
        exit_code = -2

    git_after = git_status_short()

    log_entry_end = {
        "event": "stage_end" if exit_code == 0 else "stage_failed",
        "stage_id": stage_id,
        "time": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "git_status_after": git_after,
        "changed_files": git_after.splitlines() if git_after else [],
    }
    append_log(run_dir, log_entry_end)

    if exit_code == 0 and commit:
        commit_msg = f"agent: complete {stage_id} {stage['name'].lower().replace(' ', '_')}"
        try:
            subprocess.run(["git", "add", "-A"], cwd=str(ROOT), timeout=30)
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(ROOT), timeout=30)
            print(f"  [COMMIT] {commit_msg}")
        except Exception as e:
            print(f"  [WARN] Git commit failed: {e}", file=sys.stderr)

    return exit_code


def build_command_str(agent_cmd: str, agent_args: str, prompt_file: Path) -> str:
    if agent_args:
        return f'{agent_cmd} {agent_args} < "{prompt_file}"'
    else:
        return f'{agent_cmd} < "{prompt_file}"'


def append_log(run_dir: Path, entry: dict) -> None:
    log_file = run_dir / "run_log.jsonl"
    line = json.dumps(entry, ensure_ascii=False)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Automated multi-stage opencode task runner.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/opencode_stage_runner.py --list
  python tools/opencode_stage_runner.py --dry-run
  python tools/opencode_stage_runner.py --from P0-3 --until P0-4 --dry-run
  python tools/opencode_stage_runner.py --from P0-3 --until P0-4
  python tools/opencode_stage_runner.py --only P1-2
  python tools/opencode_stage_runner.py --resume
        """,
    )

    parser.add_argument("--list", action="store_true", help="List all stages and exit.")
    parser.add_argument("--only", type=str, default=None, metavar="STAGE_ID",
                        help="Execute only this stage (e.g. P0-3).")
    parser.add_argument("--from", dest="from_stage", type=str, default=None, metavar="STAGE_ID",
                        help="Start from this stage (inclusive).")
    parser.add_argument("--until", dest="until_stage", type=str, default=None, metavar="STAGE_ID",
                        help="End at this stage (inclusive).")
    parser.add_argument("--resume", action="store_true",
                        help="Skip completed stages, continue from first incomplete.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be done without executing.")
    parser.add_argument("--agent-cmd", type=str, default=None, metavar="CMD",
                        help="Command to invoke opencode (default: from OPENCODE_CMD env var or 'opencode').")
    parser.add_argument("--agent-args", type=str, default=None, metavar="ARGS",
                        help="Additional arguments for opencode (default: from OPENCODE_ARGS env var or '').")
    parser.add_argument("--commit", action="store_true",
                        help="Auto git commit after each successful stage.")
    parser.add_argument("--run-id", type=str, default=None,
                        help="Manually specify run ID (default: auto-generated timestamp).")

    args = parser.parse_args()

    if args.list:
        print("Available stages:")
        print()
        for s in ALL_STAGES:
            prompt_path = AGENT_TASKS_DIR / s["prompt"]
            exists = "EXISTS" if prompt_path.exists() else "MISSING"
            print(f"  {s['id']:6s}  {s['name']:40s}  [{exists}] {s['prompt']}")
        print()
        print(f"Total: {len(ALL_STAGES)} stages")
        return

    agent_cmd = args.agent_cmd or os.environ.get("OPENCODE_CMD", "opencode")
    agent_args = args.agent_args or os.environ.get("OPENCODE_ARGS", "")

    stages = resolve_stages(args)

    if not stages:
        print("[ERROR] No stages selected.", file=sys.stderr)
        sys.exit(1)

    run_id = args.run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = AGENT_RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.resume:
        latest_run = find_latest_run_dir()
        if latest_run:
            completed = get_completed_stages(latest_run)
            remaining = [s for s in stages if s["id"] not in completed]
            if not remaining:
                print(f"All selected stages already completed in {latest_run.name}")
                return
            print(f"[RESUME] Skipping completed stages: {', '.join(completed & {s['id'] for s in stages})}")
            stages = remaining
            run_dir = latest_run
            print(f"[RESUME] Continuing in run dir: {run_dir}")
        else:
            print("[RESUME] No previous run found. Starting fresh.")

    run_config = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "stages": [s["id"] for s in stages],
        "agent_cmd": agent_cmd,
        "agent_args": agent_args,
        "dry_run": args.dry_run,
        "commit": args.commit,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    run_config_path = run_dir / "run_config.json"
    run_config_path.write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("  OpenCode Stage Runner")
    print("=" * 60)
    print(f"  Run ID:    {run_id}")
    print(f"  Run Dir:   {run_dir}")
    print(f"  Stages:    {', '.join(s['id'] for s in stages)}")
    print(f"  Agent:     {agent_cmd} {agent_args}".strip())
    print(f"  Dry Run:   {args.dry_run}")
    print(f"  Auto Commit: {args.commit}")
    print("=" * 60)
    print()

    prev_report_path = None
    failed_stage = None

    for i, stage in enumerate(stages):
        stage_id = stage["id"]
        print(f"\n{'─' * 60}")
        print(f"  Stage {i+1}/{len(stages)}: {stage_id} — {stage['name']}")
        print(f"{'─' * 60}")

        if i > 0:
            prev_stage_id = stages[i - 1]["id"]
            prev_report_path = run_dir / (prev_stage_id + "_report.md")
            if not prev_report_path.exists():
                print(f"  [WARN] Previous stage report not found: {prev_report_path}")

        exit_code = run_stage(
            stage, run_dir, prev_report_path,
            agent_cmd, agent_args, args.dry_run, args.commit,
        )

        if exit_code != 0 and not args.dry_run:
            failed_stage = stage_id
            print(f"\n{'=' * 60}")
            print(f"  FAILED at stage: {stage_id}")
            print(f"{'=' * 60}")
            print(f"  Exit code:  {exit_code}")
            print(f"  Stdout log: {run_dir / (stage_id + '_stdout.log')}")
            print(f"  Stderr log: {run_dir / (stage_id + '_stderr.log')}")
            print(f"  Prompt:     {run_dir / (stage_id + '_prompt.md')}")
            print(f"  Git status: {git_status_short()}")
            print()
            print(f"  To continue after fixing:")
            print(f"    python tools/opencode_stage_runner.py --from {stage_id}")
            print(f"    python tools/opencode_stage_runner.py --resume")
            sys.exit(1)

        prev_report_path = run_dir / (stage_id + "_report.md")

    print(f"\n{'=' * 60}")
    print(f"  All stages completed successfully!")
    print(f"{'=' * 60}")
    print(f"  Run Dir: {run_dir}")
    print(f"  Stages:  {', '.join(s['id'] for s in stages)}")
    if args.dry_run:
        print(f"  (Dry-run mode — no actual execution)")
    print()


if __name__ == "__main__":
    main()
