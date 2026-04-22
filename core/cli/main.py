"""CLI dispatcher."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import cmd_init, cmd_doctor, cmd_sync, cmd_extract_candidate, cmd_propose_upstream

HARNESS_VERSION = "0.3.0-dev"  # 0.1.0 = PR-D1 skeleton / 0.2.0 = PR-D3 CLI / 0.3.0 = PR-E2 contrib CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-harness",
        description="agent-harness CLI — meta-dev-loop kit for autonomous iteration.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"agent-harness {HARNESS_VERSION}",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<subcommand>")

    # ---- init ----
    init_parser = sub.add_parser(
        "init",
        help="Initialize agent-harness in a target project directory.",
        description=(
            "Create .agent-harness/project.yaml + lock.json and scaffold directories. "
            "Two tiers: --minimal (bare skeleton) and --pragmatic (skeleton + docaudit policy stub)."
        ),
        epilog="Example: agent-harness init --pragmatic /path/to/new-project",
    )
    init_tier = init_parser.add_mutually_exclusive_group()
    init_tier.add_argument(
        "--minimal",
        dest="tier",
        action="store_const",
        const="minimal",
        help="Produce only .agent-harness/ config; no docaudit policy stub.",
    )
    init_tier.add_argument(
        "--pragmatic",
        dest="tier",
        action="store_const",
        const="pragmatic",
        help="Minimal + Scripts/audit/policy.yaml stub. (Default tier.)",
    )
    init_parser.set_defaults(tier="pragmatic")
    init_parser.add_argument(
        "target",
        type=Path,
        help="Target directory (must exist, typically a fresh project root).",
    )
    init_parser.add_argument(
        "--upstream-commit",
        default="",
        help="Override upstream commit to lock (default: leave empty; sync --check will warn).",
    )
    init_parser.add_argument(
        "--project-name",
        default="",
        help="Override project.name (default: target directory name).",
    )
    init_parser.add_argument(
        "--project-type",
        default="generic",
        help="Override project.type (default: generic; consumer fills later).",
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .agent-harness/ contents (dangerous).",
    )

    # ---- doctor ----
    doctor_parser = sub.add_parser(
        "doctor",
        help="Verify a consumer project's agent-harness integration.",
        description=(
            "Check that .agent-harness/project.yaml is present and valid, that "
            "declared policy.yaml exists and parses, and run docaudit dry-run to confirm engine is callable."
        ),
        epilog="Example: agent-harness doctor /path/to/consumer-project",
    )
    doctor_parser.add_argument(
        "target",
        type=Path,
        nargs="?",
        default=None,
        help="Target consumer project root (default: CWD).",
    )

    # ---- sync ----
    sync_parser = sub.add_parser(
        "sync",
        help="Inspect or apply drift between consumer lock and upstream.",
        description=(
            "Report drift between .agent-harness/lock.json and the latest upstream commit. "
            "--check (default) reports only; --apply (not implemented in PR-D3) updates lock."
        ),
        epilog="Example: agent-harness sync --check /path/to/consumer-project",
    )
    sync_parser.add_argument(
        "target",
        type=Path,
        nargs="?",
        default=None,
        help="Target consumer project root (default: CWD).",
    )
    mode = sync_parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        dest="mode",
        action="store_const",
        const="check",
        help="Report drift only (default).",
    )
    mode.add_argument(
        "--apply",
        dest="mode",
        action="store_const",
        const="apply",
        help="Apply upstream HEAD to lock.json (NOT implemented in PR-D3; reserved).",
    )
    sync_parser.set_defaults(mode="check")
    sync_parser.add_argument(
        "--upstream-repo",
        default="NotBad-Labs/agent-harness",
        help="Override upstream repo (default: NotBad-Labs/agent-harness).",
    )

    # ---- extract-candidate ----
    ec_parser = sub.add_parser(
        "extract-candidate",
        help="Scan consumer overlay for potential upstream contribution candidates.",
        description=(
            "Walk contribution.scan_paths declared in .agent-harness/project.yaml, "
            "score each file by denylist / consumer-term hits + git history, "
            "and print a ranked report."
        ),
        epilog="Example: agent-harness extract-candidate /path/to/consumer",
    )
    ec_parser.add_argument(
        "target",
        type=Path,
        nargs="?",
        default=None,
        help="Target consumer project root (default: CWD).",
    )
    ec_parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include files with < 3 commits (would otherwise be filtered by P2 rule).",
    )

    # ---- propose-upstream ----
    pu_parser = sub.add_parser(
        "propose-upstream",
        help="Generate a PR body draft for a specific candidate file.",
        description=(
            "Fill the agent-harness PR template with auto-scanned data "
            "(denylist hits, git history, suggested layer) for a specific consumer file. "
            "The draft is written to .agent-harness/proposals/; author fills TODO fields."
        ),
        epilog="Example: agent-harness propose-upstream .claude/skills/new/SKILL.md",
    )
    pu_parser.add_argument(
        "source",
        type=Path,
        help="Source file path (relative to consumer root, or absolute).",
    )
    pu_parser.add_argument(
        "--target",
        type=Path,
        default=None,
        help="Target consumer project root (default: CWD).",
    )

    return parser


def entry(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        return cmd_init.run(args)
    if args.command == "doctor":
        return cmd_doctor.run(args)
    if args.command == "sync":
        return cmd_sync.run(args)
    if args.command == "extract-candidate":
        return cmd_extract_candidate.run(args)
    if args.command == "propose-upstream":
        return cmd_propose_upstream.run(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


def main() -> None:
    sys.exit(entry())


if __name__ == "__main__":
    main()
