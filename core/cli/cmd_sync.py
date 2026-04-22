"""`agent-harness sync` — drift check between consumer lock and upstream."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git_ls_remote_head(upstream_repo: str) -> tuple[bool, str]:
    """Return upstream main branch HEAD sha via `git ls-remote`."""
    url = f"https://github.com/{upstream_repo}.git"
    try:
        completed = subprocess.run(
            ["git", "ls-remote", url, "refs/heads/main"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"git ls-remote failed: {exc}"
    if completed.returncode != 0:
        return False, f"git ls-remote non-zero ({completed.returncode}): {completed.stderr.strip()[:200]}"
    line = completed.stdout.strip().split("\n", 1)[0] if completed.stdout.strip() else ""
    if not line:
        return False, f"no output from git ls-remote {url}"
    sha = line.split()[0]
    return True, sha


def run(args: argparse.Namespace) -> int:
    target: Path = (args.target or Path.cwd()).resolve()
    lock_path = target / ".agent-harness" / "lock.json"

    if args.mode == "apply":
        print(
            "ERROR: `sync --apply` is reserved and not implemented in PR-D3. "
            "Manually edit .agent-harness/lock.json for now.",
            file=sys.stderr,
        )
        return 2

    # --check mode
    if not lock_path.is_file():
        print(
            f"ERROR: {lock_path} not found. "
            "Run `agent-harness init` first or pass a valid --target.",
            file=sys.stderr,
        )
        return 2

    try:
        with lock_path.open("r", encoding="utf-8") as fp:
            lock = json.load(fp)
    except json.JSONDecodeError as exc:
        print(f"ERROR: {lock_path} JSON parse error: {exc}", file=sys.stderr)
        return 2

    locked_commit = lock.get("upstream_commit", "")
    channel = lock.get("channel", "main")

    ok, remote_head = _git_ls_remote_head(args.upstream_repo)
    if not ok:
        print(f"ERROR: unable to resolve upstream HEAD: {remote_head}", file=sys.stderr)
        return 2

    print(f"agent-harness sync --check: {target}")
    print(f"  upstream_repo:    {args.upstream_repo}")
    print(f"  channel:          {channel}")
    print(f"  locked_commit:    {locked_commit or '(none)'}")
    print(f"  upstream_HEAD:    {remote_head}")
    print()

    if not locked_commit:
        print("WARNING: lock.json has no upstream_commit.")
        print("  Run `agent-harness sync --apply` (reserved) or manually pin "
              f"to {remote_head} in .agent-harness/lock.json.")
        return 0

    if locked_commit == remote_head:
        print("STATUS: up to date (locked commit == upstream HEAD).")
        return 0

    print("STATUS: drift detected.")
    print(f"  Consumer is locked to {locked_commit[:12]}...")
    print(f"  Upstream HEAD is     {remote_head[:12]}...")
    print("  Consider reviewing upstream CHANGELOG before bumping lock.json.")
    return 0
