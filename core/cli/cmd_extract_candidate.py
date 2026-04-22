"""`agent-harness extract-candidate` — scan consumer overlay for contribution candidates."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)


# 默认 denylist（跟 CI 扫描一致的关键词集合 + 常见消费项目术语）
# consumer 可在 .agent-harness/project.yaml 的 contribution.denylist 覆盖
DEFAULT_DENYLIST = [
    # Agent / CLI 特定（core/ 禁用；adapter-<agent>/ 例外）
    "openai", "cursor",
    # 语言 / 栈特定
    "swift", "swiftui", "swiftdata", "xcode", "kotlin", "flutter",
    # 示例常见 consumer 名
    "snapdrill", "myapp",
]


@dataclass
class Candidate:
    path: Path              # 相对 consumer root 的路径
    denylist_hits: int
    consumer_term_hits: int
    commit_count: int
    first_seen: str         # ISO date or "unknown"
    last_seen: str
    score: int              # 0-100
    suggested_layer: str    # core / adapter-<agent> / preset-<domain> / STAY / ADAPT

    def format_summary(self) -> str:
        loc = f"[score {self.score:>3}%] {self.path}"
        return loc


def _load_project_yaml(consumer_root: Path) -> dict:
    """Load consumer's .agent-harness/project.yaml. Return empty dict if missing."""
    project_yaml = consumer_root / ".agent-harness" / "project.yaml"
    if not project_yaml.is_file():
        return {}
    try:
        with project_yaml.open("r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _resolve_scan_paths(consumer_root: Path, project_yaml: dict) -> list[Path]:
    """Determine scan paths from contribution.scan_paths in project.yaml.
    Default to common consumer overlay locations if not specified."""
    defaults = [
        ".claude/skills/",
        ".claude/hooks/",
        "docs/principles/",
        "docs/memory/feedback.md",
    ]
    configured = project_yaml.get("contribution", {}).get("scan_paths", defaults)
    result = []
    for rel in configured:
        path = consumer_root / rel
        if path.exists():
            result.append(path)
    return result


def _resolve_denylist(project_yaml: dict) -> list[str]:
    """Resolve denylist from project.yaml override or DEFAULT_DENYLIST."""
    configured = project_yaml.get("contribution", {}).get("denylist")
    if isinstance(configured, list) and configured:
        return [str(term).lower() for term in configured]
    return DEFAULT_DENYLIST


def _iter_candidate_files(scan_paths: list[Path]) -> list[Path]:
    """Walk scan paths and yield eligible files (md / sh / py / yaml)."""
    result: list[Path] = []
    extensions = (".md", ".sh", ".py", ".yaml", ".yml")
    for path in scan_paths:
        if path.is_file():
            if any(path.name.endswith(ext) for ext in extensions):
                result.append(path)
        elif path.is_dir():
            for root, _dirs, files in os.walk(path):
                root_path = Path(root)
                for fn in files:
                    if any(fn.endswith(ext) for ext in extensions):
                        result.append(root_path / fn)
    return result


def _count_denylist_hits(file_path: Path, denylist: list[str]) -> int:
    """Case-insensitive count of denylist term occurrences in file content."""
    try:
        text = file_path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return 0
    pattern = re.compile("|".join(re.escape(t) for t in denylist))
    return len(pattern.findall(text))


def _count_consumer_term_hits(file_path: Path, consumer_terms: list[str]) -> int:
    """Count consumer-specific terms (beyond denylist) like table names, product nouns."""
    if not consumer_terms:
        return 0
    try:
        text = file_path.read_text(encoding="utf-8").lower()
    except (OSError, UnicodeDecodeError):
        return 0
    pattern = re.compile("|".join(re.escape(t.lower()) for t in consumer_terms))
    return len(pattern.findall(text))


def _git_log_stats(file_path: Path, consumer_root: Path) -> tuple[int, str, str]:
    """Return (commit_count, first_seen, last_seen) via git log.
    Return (0, 'unknown', 'unknown') on error."""
    try:
        rel = file_path.relative_to(consumer_root)
    except ValueError:
        return 0, "unknown", "unknown"
    try:
        completed = subprocess.run(
            ["git", "log", "--follow", "--format=%cs", "--", str(rel)],
            cwd=str(consumer_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode != 0:
            return 0, "unknown", "unknown"
        dates = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not dates:
            return 0, "unknown", "unknown"
        return len(dates), dates[-1], dates[0]
    except (OSError, subprocess.TimeoutExpired):
        return 0, "unknown", "unknown"


def _score_and_suggest(
    denylist_hits: int,
    consumer_term_hits: int,
    file_path: Path,
) -> tuple[int, str]:
    """Heuristic scoring (0-100) + suggested layer.

    Starting score 100, penalize denylist / consumer term hits.
    Floor at 0.
    """
    score = 100 - denylist_hits * 10 - consumer_term_hits * 5
    score = max(0, min(100, score))

    path_str = str(file_path).lower()
    # Suggested layer heuristic
    if "swift" in path_str or "xcode" in path_str or "ios" in path_str:
        suggested = "preset-ios (needs adapt)"
    elif "/hooks/" in path_str or "/skills/" in path_str:
        if score >= 80:
            suggested = "adapter-claude/ (high confidence)"
        elif score >= 50:
            suggested = "adapter-claude/ (needs rewrite)"
        else:
            suggested = "STAY (too coupled)"
    elif "/principles/" in path_str:
        if score >= 80:
            suggested = "core/principles/ (high confidence)"
        elif score >= 50:
            suggested = "core/ (needs rewrite)"
        else:
            suggested = "STAY (project-specific)"
    elif "feedback" in path_str:
        suggested = "feedback/ schema only; rule content stays consumer-local"
    else:
        if score >= 80:
            suggested = "core/ (high confidence)"
        elif score >= 50:
            suggested = "ADAPT"
        else:
            suggested = "STAY"
    return score, suggested


def _build_candidate(
    file_path: Path,
    consumer_root: Path,
    denylist: list[str],
    consumer_terms: list[str],
) -> Candidate:
    denylist_hits = _count_denylist_hits(file_path, denylist)
    consumer_term_hits = _count_consumer_term_hits(file_path, consumer_terms)
    commit_count, first_seen, last_seen = _git_log_stats(file_path, consumer_root)
    score, suggested = _score_and_suggest(denylist_hits, consumer_term_hits, file_path)
    rel_path = file_path.relative_to(consumer_root)
    return Candidate(
        path=rel_path,
        denylist_hits=denylist_hits,
        consumer_term_hits=consumer_term_hits,
        commit_count=commit_count,
        first_seen=first_seen,
        last_seen=last_seen,
        score=score,
        suggested_layer=suggested,
    )


def _print_report(
    consumer_root: Path,
    scan_paths: list[Path],
    candidates: list[Candidate],
) -> None:
    print(f"agent-harness extract-candidate: {consumer_root}")
    print()
    print("Scanning contribution.scan_paths:")
    for p in scan_paths:
        print(f"  - {p.relative_to(consumer_root)}")
    print()
    if not candidates:
        print("No candidates found (scan paths contained no eligible files).")
        return

    candidates_sorted = sorted(candidates, key=lambda c: -c.score)
    print(f"Candidates ({len(candidates_sorted)} found, ranked by score):")
    print()
    for c in candidates_sorted:
        print(f"  {c.format_summary()}")
        print(f"      Denylist hits: {c.denylist_hits}")
        print(f"      Consumer term hits: {c.consumer_term_hits}")
        if c.commit_count > 0:
            print(
                f"      Git history: {c.commit_count} commits "
                f"({c.first_seen} → {c.last_seen})"
            )
        else:
            print("      Git history: (not tracked or 0 commits)")
        print(f"      Suggested layer: {c.suggested_layer}")
        print()

    # Summary by score band
    high = sum(1 for c in candidates_sorted if c.score >= 80)
    mid = sum(1 for c in candidates_sorted if 50 <= c.score < 80)
    low = sum(1 for c in candidates_sorted if c.score < 50)
    print("Summary:")
    print(f"  - High score (>= 80, ready for proposal): {high}")
    print(f"  - Medium (50-79, needs adapt): {mid}")
    print(f"  - Low (< 50, likely STAY): {low}")
    print()
    print("Next step for a high-score candidate:")
    print("  agent-harness propose-upstream <relative-path> --target <consumer-root>")


def run(args: argparse.Namespace) -> int:
    consumer_root: Path = (args.target or Path.cwd()).resolve()
    if not (consumer_root / ".agent-harness" / "project.yaml").is_file():
        print(
            f"ERROR: {consumer_root}/.agent-harness/project.yaml not found. "
            "Run `agent-harness init` first or pass a valid --target.",
            file=sys.stderr,
        )
        return 2

    project_yaml = _load_project_yaml(consumer_root)
    scan_paths = _resolve_scan_paths(consumer_root, project_yaml)
    if not scan_paths:
        print(
            "WARN: No scan paths resolved. Configure contribution.scan_paths in "
            ".agent-harness/project.yaml or create default overlay paths.",
            file=sys.stderr,
        )
        return 0

    denylist = _resolve_denylist(project_yaml)
    consumer_terms = project_yaml.get("contribution", {}).get("consumer_terms", [])

    files = _iter_candidate_files(scan_paths)
    candidates = [
        _build_candidate(f, consumer_root, denylist, consumer_terms)
        for f in files
    ]

    # Min commit filter (P2: 3 iteration cycles), skip unless --include-untracked
    if not args.include_untracked:
        candidates = [c for c in candidates if c.commit_count >= 3]

    _print_report(consumer_root, scan_paths, candidates)
    return 0
