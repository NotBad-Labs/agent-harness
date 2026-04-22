"""`agent-harness doctor` — verify consumer integration."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)


REQUIRED_PROJECT_KEYS = ["version", "project", "upstream"]


class Check:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.detail = ""

    def ok(self, detail: str = "") -> "Check":
        self.passed = True
        self.detail = detail
        return self

    def fail(self, detail: str) -> "Check":
        self.passed = False
        self.detail = detail
        return self


def _run_docaudit_dry_run(
    repo_root: Path, policy_path: Path, agent_harness_root: Path
) -> tuple[bool, str]:
    """Invoke docaudit engine (from agent-harness root) against consumer policy."""
    engine = agent_harness_root / "core" / "tools" / "docaudit" / "docaudit.py"
    if not engine.is_file():
        return False, f"docaudit engine not found at {engine}"
    try:
        completed = subprocess.run(
            [
                "python3",
                str(engine),
                "--repo-root",
                str(repo_root),
                "--policy",
                str(policy_path),
                "links",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"docaudit invocation failed: {exc}"
    # exit code 2 = config error; anything else (0 or 1) = engine started
    if completed.returncode == 2:
        return False, f"docaudit reported config error (exit 2): {completed.stderr.strip()[:200]}"
    return True, f"docaudit engine callable (exit={completed.returncode})"


def run(args: argparse.Namespace) -> int:
    target: Path = (args.target or Path.cwd()).resolve()
    checks: list[Check] = []

    # 1. .agent-harness/project.yaml exists and parses
    ah_dir = target / ".agent-harness"
    project_yaml = ah_dir / "project.yaml"
    c = Check(".agent-harness/project.yaml exists and parses")
    if not project_yaml.is_file():
        checks.append(c.fail(f"missing: {project_yaml}"))
    else:
        try:
            with project_yaml.open("r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
            if not isinstance(data, dict):
                c.fail("project.yaml root must be a mapping")
            elif data.get("version") != 1:
                c.fail(f"project.yaml.version must be 1 (got {data.get('version')!r})")
            else:
                missing = [k for k in REQUIRED_PROJECT_KEYS if k not in data]
                if missing:
                    c.fail(f"missing required keys: {missing}")
                else:
                    c.ok(f"version=1, project.name={data.get('project', {}).get('name')!r}")
        except yaml.YAMLError as exc:
            c.fail(f"YAML parse error: {exc}")
        checks.append(c)

    # 2. lock.json exists and parses
    lock_path = ah_dir / "lock.json"
    c = Check(".agent-harness/lock.json exists and parses")
    if not lock_path.is_file():
        checks.append(c.fail(f"missing: {lock_path}"))
    else:
        try:
            with lock_path.open("r", encoding="utf-8") as fp:
                lock = json.load(fp)
            if not isinstance(lock, dict):
                c.fail("lock.json root must be an object")
            else:
                commit = lock.get("upstream_commit")
                if not commit:
                    c.fail("lock.json.upstream_commit is empty; run `agent-harness sync --apply` after PR-D3")
                else:
                    c.ok(f"locked to upstream_commit={commit[:12]}...")
        except json.JSONDecodeError as exc:
            c.fail(f"JSON parse error: {exc}")
        checks.append(c)

    # 3. Policy file (if declared in project.yaml or conventionally at Scripts/audit/policy.yaml)
    policy_candidates = [
        target / ".agent-harness" / "policy.yaml",
        target / "Scripts" / "audit" / "policy.yaml",
    ]
    policy_path = None
    for cand in policy_candidates:
        if cand.is_file():
            policy_path = cand
            break

    c = Check("docaudit policy.yaml present and parseable")
    if policy_path is None:
        c.fail(
            "no policy.yaml found at .agent-harness/policy.yaml or Scripts/audit/policy.yaml "
            "(OK for --minimal init; pragmatic tier should include stub)"
        )
        checks.append(c)
    else:
        try:
            with policy_path.open("r", encoding="utf-8") as fp:
                pol = yaml.safe_load(fp)
            if not isinstance(pol, dict) or pol.get("version") != 1:
                c.fail(f"policy.yaml version must be 1 (at {policy_path})")
            else:
                c.ok(f"policy.yaml valid at {policy_path.relative_to(target)}")
        except yaml.YAMLError as exc:
            c.fail(f"policy.yaml YAML parse error: {exc}")
        checks.append(c)

    # 4. docaudit engine callable (only if policy found)
    if policy_path is not None:
        # Locate agent-harness root: the directory containing this CLI module's parent-parent-parent
        # core/cli/cmd_doctor.py -> ../ = core/cli -> ../../ = core -> ../../../ = agent-harness root
        agent_harness_root = Path(__file__).resolve().parents[2]
        ok, detail = _run_docaudit_dry_run(target, policy_path, agent_harness_root)
        c = Check("docaudit engine dry-run")
        if ok:
            c.ok(detail)
        else:
            c.fail(detail)
        checks.append(c)

    # Print report
    print(f"agent-harness doctor: {target}")
    print()
    failed = 0
    for c in checks:
        status = "✓" if c.passed else "✗"
        if not c.passed:
            failed += 1
        print(f"  [{status}] {c.name}")
        if c.detail:
            print(f"      {c.detail}")
    print()
    if failed:
        print(f"Exit: 1 ({failed} of {len(checks)} checks failed)")
        return 1
    print(f"Exit: 0 (all {len(checks)} checks passed)")
    return 0
