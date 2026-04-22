#!/usr/bin/env python3
"""Documentation audit engine — agent-harness core.

Subcommands:
  all                  Run all checks (+ frontmatter via subprocess if configured)
  links                Markdown 内部 broken link 扫描
  archived-refs        对 policy.yaml 声明的 archived_sources 旧路径硬引用检测
  orphans              policy.layout.orphan_scan_dir 下零引用 Markdown 检测
  home-path-refs       仓库内对用户 home 私有路径的硬编码扫描
  rule-pointer-sync    policy.layout.rules_dir 下规则指针同步校验
  rule-usage           policy.layout.rules_file 中规则 ID 外部引用计数

Usage:
    python3 docaudit.py <subcommand> [--policy PATH] [--repo-root PATH]
                        [--strict] [--report] [--baseline] [--verbose]

Exit codes:
  0  pass
  1  error-level finding (or --strict 下 warning-level)
  2  configuration / invocation error

Path resolution priority (repo root):
  1. --repo-root CLI argument
  2. AGENT_HARNESS_REPO_ROOT environment variable
  3. `git rev-parse --show-toplevel` (if inside a git repo)
  4. CWD (fallback)

Policy resolution priority:
  1. --policy CLI argument
  2. AGENT_HARNESS_POLICY environment variable
  3. <repo-root>/.agent-harness/policy.yaml
  4. <repo-root>/Scripts/audit/policy.yaml (legacy consumer layout)
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip3 install pyyaml", file=sys.stderr)
    sys.exit(2)


CHECK_NAMES = [
    "links",
    "archived-refs",
    "orphans",
    "home-path-refs",
    "rule-pointer-sync",
    "rule-usage",
]

CHECK_DESCRIPTIONS = {
    "links": {
        "help": "Detect broken Markdown links in docs.",
        "description": "Scan all Markdown [text](path.md) references; target missing = broken_link finding.",
        "epilog": "Example: docaudit links --strict",
    },
    "archived-refs": {
        "help": "Detect hardcoded references to deprecated archived_sources paths (see policy).",
        "description": "Scan active hard-references to deprecated paths declared in policy.checks.archived-refs.archived_sources.",
        "epilog": "Example: docaudit archived-refs --baseline",
    },
    "orphans": {
        "help": "Detect Markdown files under layout.orphan_scan_dir with zero references.",
        "description": "Scan policy.layout.orphan_scan_dir for Markdown files referenced nowhere in scan include paths.",
        "epilog": "Whitelist via policy.checks.orphans.whitelist.",
    },
    "home-path-refs": {
        "help": "Detect hardcoded references to user home private paths (~/...).",
        "description": "Scan repo for hardcoded ~/ private path patterns (see policy.checks.home-path-refs.patterns).",
        "epilog": "Example: docaudit home-path-refs --verbose",
    },
    "rule-pointer-sync": {
        "help": "Verify rule pointer files point to existing principle documents.",
        "description": "Parse rule pointer files under layout.rules_dir; verify each pointer target under layout.principles_dir exists.",
        "epilog": "Example: docaudit rule-pointer-sync",
    },
    "rule-usage": {
        "help": "Count rule external references in repo (dead rule candidates).",
        "description": "For each rule id declared in layout.rules_file matching layout.rule_id_pattern, count external references.",
        "epilog": "Example: docaudit rule-usage --verbose",
    },
}

# Markdown 内部链接正则 — [text](path.md) 或 [text](path.md#anchor)；排除 http/mailto/图片
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)#]*?\.md)(?:#[^)]*)?\)")

# 任意 md 文件路径引用（orphan 检测）
PATH_REF_RE = re.compile(r"([A-Za-z_\-./][A-Za-z0-9_\-./]*\.md)")

# 用户 home 私有路径引用（默认 ~/，可通过 policy.checks.home-path-refs.patterns 覆盖）
DEFAULT_HOME_PATH_PATTERN = r"~/[A-Za-z0-9_\-./]+"


# ---------- 数据类型 ----------

@dataclass
class Finding:
    check: str
    path: str
    line: int
    category: str
    level: str                  # error / warning / info（原始级别，不受豁免影响）
    suggestion: str = ""
    matched_text: str = ""
    suppressed: bool = False    # post-filter 豁免命中标记
    suppressed_reason: str = ""

    def as_tsv(self) -> str:
        fields = [
            self.check,
            self.path,
            str(self.line),
            self.category,
            self.level,
            "suppressed" if self.suppressed else "active",
            self.suggestion,
            self.suppressed_reason,
            self.matched_text.replace("\t", " ").replace("\n", " ")[:200],
        ]
        return "\t".join(fields)


@dataclass
class CheckResult:
    check: str
    level: str                  # policy 默认级别
    findings: list[Finding] = field(default_factory=list)

    @property
    def active_findings(self) -> list[Finding]:
        return [f for f in self.findings if not f.suppressed]

    @property
    def error_count(self) -> int:
        return sum(1 for f in self.active_findings if f.level == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.active_findings if f.level == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.active_findings if f.level == "info")

    @property
    def suppressed_count(self) -> int:
        return sum(1 for f in self.findings if f.suppressed)


@dataclass(frozen=True)
class WhitelistRule:
    check: str
    reason: str
    expires_on: date
    paths: tuple[str, ...]          # glob patterns，空 tuple = 匹配该 check 的所有 findings
    categories: tuple[str, ...]     # 空 tuple = 匹配所有 category


# ---------- repo root / policy 解析 ----------

def resolve_repo_root(cli_arg: Path | None) -> Path:
    """按 docstring 描述的优先级解析 repo root。"""
    if cli_arg is not None:
        resolved = cli_arg.resolve()
        if not resolved.is_dir():
            print(f"ERROR: --repo-root not a directory: {resolved}", file=sys.stderr)
            sys.exit(2)
        return resolved

    env = os.environ.get("AGENT_HARNESS_REPO_ROOT")
    if env:
        resolved = Path(env).resolve()
        if not resolved.is_dir():
            print(f"ERROR: AGENT_HARNESS_REPO_ROOT not a directory: {resolved}", file=sys.stderr)
            sys.exit(2)
        return resolved

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if completed.returncode == 0 and completed.stdout.strip():
            return Path(completed.stdout.strip()).resolve()
    except (OSError, subprocess.TimeoutExpired):
        pass

    return Path.cwd().resolve()


def resolve_policy_path(cli_arg: Path | None, repo_root: Path) -> Path:
    """按 docstring 描述的优先级解析 policy 路径。"""
    if cli_arg is not None:
        return cli_arg.resolve()

    env = os.environ.get("AGENT_HARNESS_POLICY")
    if env:
        return Path(env).resolve()

    candidate = repo_root / ".agent-harness" / "policy.yaml"
    if candidate.is_file():
        return candidate

    candidate = repo_root / "Scripts" / "audit" / "policy.yaml"
    if candidate.is_file():
        return candidate

    # Fallback to first candidate even if missing (load_policy will error with a clear message)
    return repo_root / ".agent-harness" / "policy.yaml"


# ---------- policy 加载 ----------

def load_policy(path: Path) -> dict:
    if not path.exists():
        print(f"ERROR: policy.yaml not found at {path}", file=sys.stderr)
        sys.exit(2)
    try:
        with path.open("r", encoding="utf-8") as fp:
            policy = yaml.safe_load(fp)
    except yaml.YAMLError as exc:
        print(f"ERROR: policy.yaml parse failed: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(policy, dict) or policy.get("version") != 1:
        print("ERROR: policy.yaml version must be 1", file=sys.stderr)
        sys.exit(2)
    return policy


def _parse_whitelist(policy: dict) -> list[WhitelistRule]:
    """解析 legacy_whitelist。无效日期 / 缺字段 → exit 2 (fail-closed)。"""
    raw = policy.get("legacy_whitelist", [])
    if raw is None:
        return []
    if not isinstance(raw, list):
        print(
            "ERROR: policy.yaml legacy_whitelist must be a list of rule objects",
            file=sys.stderr,
        )
        sys.exit(2)
    rules: list[WhitelistRule] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            print(
                f"ERROR: legacy_whitelist[{idx}] must be a mapping",
                file=sys.stderr,
            )
            sys.exit(2)
        check_name = entry.get("check")
        if check_name not in CHECK_NAMES:
            print(
                f"ERROR: legacy_whitelist[{idx}].check '{check_name}' unknown; must be one of {CHECK_NAMES}",
                file=sys.stderr,
            )
            sys.exit(2)
        expires_raw = entry.get("expires_on")
        if not isinstance(expires_raw, str):
            print(
                f"ERROR: legacy_whitelist[{idx}].expires_on must be a YYYY-MM-DD string (got {expires_raw!r})",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            parts = expires_raw.split("-")
            if len(parts) != 3:
                raise ValueError("expects YYYY-MM-DD")
            y, m, d = (int(p) for p in parts)
            expires_on = date(y, m, d)
        except (ValueError, TypeError) as exc:
            print(
                f"ERROR: legacy_whitelist[{idx}].expires_on '{expires_raw}' is not a valid date: {exc}",
                file=sys.stderr,
            )
            sys.exit(2)
        reason = entry.get("reason", "").strip()
        if not reason:
            print(
                f"ERROR: legacy_whitelist[{idx}].reason is required (document why this is baselined)",
                file=sys.stderr,
            )
            sys.exit(2)
        paths = tuple(entry.get("paths") or ())
        categories = tuple(entry.get("categories") or ())
        rules.append(WhitelistRule(
            check=check_name,
            reason=reason,
            expires_on=expires_on,
            paths=paths,
            categories=categories,
        ))
    return rules


def _apply_whitelist(
    result: CheckResult,
    rules: list[WhitelistRule],
    baseline_flag: bool,
) -> None:
    """Finding 级 post-filter。只在 baseline_flag 且规则未过期时降级。"""
    if not baseline_flag:
        return
    today = date.today()
    for f in result.findings:
        for rule in rules:
            if rule.check != result.check:
                continue
            if rule.expires_on < today:
                continue  # 过期规则不生效（fail-closed 到未豁免状态）
            if rule.paths and not _path_matches(f.path, rule.paths):
                continue
            if rule.categories and f.category not in rule.categories:
                continue
            f.suppressed = True
            f.suppressed_reason = f"{rule.reason} (expires_on: {rule.expires_on})"
            break


def _path_matches(path: str, patterns: Iterable[str]) -> bool:
    p_norm = path.replace(os.sep, "/")
    for pat in patterns:
        pat_norm = pat.rstrip("/")
        if pat_norm.endswith("/**"):
            base = pat_norm[:-3].rstrip("/")
            if p_norm == base or p_norm.startswith(base + "/"):
                return True
        elif fnmatch.fnmatch(p_norm, pat_norm):
            return True
        elif p_norm == pat_norm:
            return True
    return False


# ---------- 文件扫描辅助 ----------

def _iter_text_files(
    policy: dict,
    repo_root: Path,
    extensions: Iterable[str] = (".md", ".sh", ".py", ".yaml", ".yml"),
) -> Iterable[Path]:
    scan = policy.get("scan", {})
    includes = scan.get("include", [])
    excludes = scan.get("exclude", [])

    for inc in includes:
        inc_path = repo_root / inc
        if inc_path.is_file():
            rel = inc_path.relative_to(repo_root)
            if any(_matches_exclude(rel, ex) for ex in excludes):
                continue
            yield inc_path
            continue
        if not inc_path.is_dir():
            continue
        for root, dirs, files in os.walk(inc_path):
            root_path = Path(root)
            rel = root_path.relative_to(repo_root)
            if any(_matches_exclude(rel, ex) for ex in excludes):
                dirs[:] = []
                continue
            for fn in files:
                if not any(fn.endswith(ext) for ext in extensions):
                    continue
                full = root_path / fn
                rel_full = full.relative_to(repo_root)
                if any(_matches_exclude(rel_full, ex) for ex in excludes):
                    continue
                yield full


def _matches_exclude(rel_path: Path, pattern: str) -> bool:
    p = pattern.rstrip("/")
    rel_str = str(rel_path).replace(os.sep, "/")
    if p.endswith("/**"):
        base = p[:-3].rstrip("/")
        return rel_str == base or rel_str.startswith(base + "/")
    if "*" not in p:
        return rel_str == p or rel_str.startswith(p + "/")
    return fnmatch.fnmatch(rel_str, p)


def _matches_whitelist_glob(rel_path: str, patterns: Iterable[str]) -> bool:
    for pat in patterns or ():
        p = pat.rstrip("/")
        rel_norm = rel_path.replace(os.sep, "/")
        if p.endswith("/**"):
            base = p[:-3].rstrip("/")
            if rel_norm == base or rel_norm.startswith(base + "/"):
                return True
        elif p == rel_norm:
            return True
        elif fnmatch.fnmatch(rel_norm, p):
            return True
    return False


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


# ---------- check: links ----------

def check_links(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["links"]
    level = conf["level"]
    result = CheckResult(check="links", level=level)

    for path in _iter_text_files(policy, repo_root, extensions=(".md",)):
        lines = _read_lines(path)
        for lineno, line in enumerate(lines, start=1):
            for match in LINK_RE.finditer(line):
                target = match.group(1).strip()
                if not target or target.startswith(("http://", "https://", "mailto:")):
                    continue
                if target.startswith("/"):
                    abs_target = repo_root / target.lstrip("/")
                else:
                    abs_target = (path.parent / target).resolve()
                if abs_target.exists():
                    continue
                rel = path.relative_to(repo_root)
                result.findings.append(Finding(
                    check="links",
                    path=str(rel),
                    line=lineno,
                    category="broken_link",
                    level=level,
                    suggestion=f"target does not exist: {target}",
                    matched_text=line.strip(),
                ))
    return result


# ---------- check: archived-refs ----------

def check_archived_refs(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["archived-refs"]
    level = conf["level"]
    archived = conf.get("archived_sources", [])
    result = CheckResult(check="archived-refs", level=level)

    # 只匹配完整路径，不匹配 basename — 完整路径匹配保持对声明路径的精准检测。
    # 新归档路径（与旧路径仅共享 basename）不会误判。
    patterns = [(src, re.escape(src)) for src in archived]

    for path in _iter_text_files(policy, repo_root, extensions=(".md", ".sh", ".py", ".yaml", ".yml")):
        rel = path.relative_to(repo_root)
        rel_str = str(rel)
        if rel_str in archived:
            continue
        lines = _read_lines(path)
        for lineno, line in enumerate(lines, start=1):
            for src, pat in patterns:
                if re.search(pat, line):
                    result.findings.append(Finding(
                        check="archived-refs",
                        path=rel_str,
                        line=lineno,
                        category="active_reference",
                        level=level,
                        suggestion=f"migrate reference to archive location or mark as historical note: {src}",
                        matched_text=line.strip(),
                    ))
                    break
    return result


# ---------- check: orphans ----------

def check_orphans(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["orphans"]
    level = conf["level"]
    whitelist = conf.get("whitelist", [])
    layout = policy.get("layout", {})
    orphan_scan_dir = layout.get("orphan_scan_dir")
    result = CheckResult(check="orphans", level=level)

    if not orphan_scan_dir:
        result.findings.append(Finding(
            check="orphans",
            path="(policy)",
            line=0,
            category="missing_layout_config",
            level="warning",
            suggestion="policy.layout.orphan_scan_dir not set; skipping orphans check",
        ))
        return result

    docs_mds: list[Path] = []
    scan_root = repo_root / orphan_scan_dir
    if scan_root.is_dir():
        for root, _dirs, files in os.walk(scan_root):
            for fn in files:
                if fn.endswith(".md"):
                    docs_mds.append(Path(root) / fn)

    referenced: set[str] = set()
    for path in _iter_text_files(policy, repo_root, extensions=(".md", ".sh", ".py", ".yaml", ".yml")):
        text = "\n".join(_read_lines(path))
        for match in PATH_REF_RE.finditer(text):
            ref = match.group(1)
            if ref.startswith("./"):
                ref = ref[2:]
            referenced.add(ref)
            referenced.add(Path(ref).name)

    scan_prefix = orphan_scan_dir.rstrip("/") + "/"
    for md in docs_mds:
        rel = md.relative_to(repo_root)
        rel_str = str(rel)
        if _matches_whitelist_glob(rel_str, whitelist):
            continue
        name = md.name
        if rel_str in referenced or name in referenced:
            continue
        if rel_str.startswith(scan_prefix) and rel_str[len(scan_prefix):] in referenced:
            continue
        result.findings.append(Finding(
            check="orphans",
            path=rel_str,
            line=0,
            category="unreferenced",
            level=level,
            suggestion="no reference found in repo; consider adding index entry or archive",
        ))
    return result


# ---------- check: home-path-refs ----------

def check_home_path_refs(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["home-path-refs"]
    level = conf["level"]
    allowed = conf.get("allowed_contexts", [])
    pattern = conf.get("pattern", DEFAULT_HOME_PATH_PATTERN)
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        print(f"ERROR: policy.checks.home-path-refs.pattern invalid regex: {exc}", file=sys.stderr)
        sys.exit(2)
    result = CheckResult(check="home-path-refs", level=level)

    for path in _iter_text_files(policy, repo_root, extensions=(".md", ".sh", ".py", ".yaml", ".yml")):
        rel = path.relative_to(repo_root)
        rel_str = str(rel)
        if _matches_whitelist_glob(rel_str, allowed):
            continue
        lines = _read_lines(path)
        for lineno, line in enumerate(lines, start=1):
            for match in compiled.finditer(line):
                result.findings.append(Finding(
                    check="home-path-refs",
                    path=rel_str,
                    line=lineno,
                    category="private_path_hardcoded",
                    level=level,
                    suggestion="migrate knowledge to public docs or mark as private with rationale",
                    matched_text=match.group(0),
                ))
    return result


# ---------- check: rule-pointer-sync ----------

def check_rule_pointer_sync(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["rule-pointer-sync"]
    level = conf["level"]
    allowlist = conf.get("allowlist_rules", [])
    layout = policy.get("layout", {})
    rules_dir_rel = layout.get("rules_dir")
    principles_dir_rel = layout.get("principles_dir")
    pointer_pattern_str = layout.get(
        "rule_pointer_pattern",
        r"(?:Read and follow|指向|→)\s+({principles_dir}/[A-Za-z0-9_\-./]+\.md)",
    )
    result = CheckResult(check="rule-pointer-sync", level=level)

    if not rules_dir_rel or not principles_dir_rel:
        result.findings.append(Finding(
            check="rule-pointer-sync",
            path="(policy)",
            line=0,
            category="missing_layout_config",
            level="warning",
            suggestion="policy.layout requires both rules_dir and principles_dir; skipping check",
        ))
        return result

    rules_dir = repo_root / rules_dir_rel
    if not rules_dir.is_dir():
        return result

    # pointer_pattern 中的 {principles_dir} 占位符由 layout.principles_dir 替换（escape 保护）
    try:
        pointer_pattern = pointer_pattern_str.format(
            principles_dir=re.escape(principles_dir_rel)
        )
        pointer_re = re.compile(pointer_pattern)
    except (KeyError, re.error, IndexError) as exc:
        print(
            f"ERROR: policy.layout.rule_pointer_pattern invalid: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)

    for rule_path in rules_dir.glob("*.md"):
        rel = rule_path.relative_to(repo_root)
        rel_str = str(rel)
        if _matches_whitelist_glob(rel_str, allowlist):
            continue
        text = "\n".join(_read_lines(rule_path))
        matches = list(pointer_re.finditer(text))
        if not matches:
            result.findings.append(Finding(
                check="rule-pointer-sync",
                path=rel_str,
                line=0,
                category="missing_pointer",
                level=level,
                suggestion=f"rule must point to a file under {principles_dir_rel}/",
            ))
            continue
        for match in matches:
            target = match.group(1).strip()
            abs_target = repo_root / target
            if not abs_target.exists():
                lineno = text[:match.start()].count("\n") + 1
                result.findings.append(Finding(
                    check="rule-pointer-sync",
                    path=rel_str,
                    line=lineno,
                    category="broken_pointer",
                    level=level,
                    suggestion=f"principle target missing: {target}",
                    matched_text=match.group(0),
                ))
    return result


# ---------- check: rule-usage ----------

def check_rule_usage(policy: dict, repo_root: Path) -> CheckResult:
    conf = policy["checks"]["rule-usage"]
    level = conf["level"]
    min_refs = conf.get("min_references", 1)
    layout = policy.get("layout", {})
    rules_file_rel = layout.get("rules_file")
    rule_id_pattern = layout.get("rule_id_pattern", r"\bRULE-(\d{3})\b")
    rule_header_pattern = layout.get(
        "rule_header_pattern",
        r"^#{1,4}\s+RULE-(\d{3})\b",
    )
    result = CheckResult(check="rule-usage", level=level)

    if not rules_file_rel:
        result.findings.append(Finding(
            check="rule-usage",
            path="(policy)",
            line=0,
            category="missing_layout_config",
            level="warning",
            suggestion="policy.layout.rules_file not set; skipping rule-usage check",
        ))
        return result

    try:
        usage_re = re.compile(rule_id_pattern)
        header_re = re.compile(rule_header_pattern)
    except re.error as exc:
        print(f"ERROR: policy.layout.rule_id_pattern or rule_header_pattern invalid regex: {exc}", file=sys.stderr)
        sys.exit(2)

    rules_file = repo_root / rules_file_rel
    if not rules_file.is_file():
        return result
    fb_text = rules_file.read_text(encoding="utf-8")
    declared = set()
    for line in fb_text.splitlines():
        m = header_re.match(line)
        if m:
            declared.add(m.group(1))

    counts: dict[str, int] = {d: 0 for d in declared}
    for path in _iter_text_files(policy, repo_root, extensions=(".md", ".sh", ".py", ".yaml", ".yml")):
        if path.resolve() == rules_file.resolve():
            continue
        text = "\n".join(_read_lines(path))
        for match in usage_re.finditer(text):
            rid = match.group(1)
            if rid in counts:
                counts[rid] += 1

    for rid in sorted(declared):
        if counts[rid] < min_refs:
            result.findings.append(Finding(
                check="rule-usage",
                path=rules_file_rel,
                line=0,
                category="dead_rule_candidate",
                level=level,
                suggestion=(
                    f"rule id {rid} has {counts[rid]} external references (< {min_refs}); "
                    "consider retiring or documenting why it exists"
                ),
            ))
    return result


# ---------- frontmatter via subprocess ----------

def check_frontmatter_via_subprocess(policy: dict, repo_root: Path) -> CheckResult | None:
    """以 subprocess 调用 policy.layout.frontmatter_validator，结果映射为 CheckResult。

    policy.layout.frontmatter_validator 未设置 → 返回 None（all 子命令不纳入结果）。
    设置但文件不存在 → 返回含 missing_orchestrator_target error 的 CheckResult。
    """
    layout = policy.get("layout", {})
    validator_rel = layout.get("frontmatter_validator")
    if not validator_rel:
        return None

    result = CheckResult(check="frontmatter", level="error")
    script = repo_root / validator_rel
    if not script.is_file():
        result.findings.append(Finding(
            check="frontmatter",
            path=validator_rel,
            line=0,
            category="missing_orchestrator_target",
            level="error",
            suggestion=f"frontmatter_validator path set in policy but file missing: {validator_rel}",
        ))
        return result
    try:
        completed = subprocess.run(
            ["python3", str(script), "--check"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result.findings.append(Finding(
            check="frontmatter",
            path=validator_rel,
            line=0,
            category="orchestrator_invocation_failed",
            level="error",
            suggestion=f"failed to invoke frontmatter validator: {exc}",
        ))
        return result
    if completed.returncode == 0:
        return result  # clean
    # 解析输出 — validator 打印 `path: message` 格式
    combined = (completed.stdout or "") + "\n" + (completed.stderr or "")
    for raw_line in combined.splitlines():
        s = raw_line.strip()
        if not s or s.lower().startswith(("found ", "no ", "ok", "passed")):
            continue
        if ":" in s:
            pth, _, msg = s.partition(":")
            result.findings.append(Finding(
                check="frontmatter",
                path=pth.strip() or "(unknown)",
                line=0,
                category="frontmatter_violation",
                level="error",
                suggestion=msg.strip(),
                matched_text=s[:200],
            ))
    if not result.findings:
        # 非零退出但无解析 finding — 报 generic 错
        result.findings.append(Finding(
            check="frontmatter",
            path=validator_rel,
            line=0,
            category="orchestrator_nonzero_exit",
            level="error",
            suggestion=f"frontmatter validator exit={completed.returncode}; output captured below",
            matched_text=combined.strip()[:200],
        ))
    return result


# ---------- 报告输出 ----------

CHECK_FUNCS = {
    "links": check_links,
    "archived-refs": check_archived_refs,
    "orphans": check_orphans,
    "home-path-refs": check_home_path_refs,
    "rule-pointer-sync": check_rule_pointer_sync,
    "rule-usage": check_rule_usage,
}


def _write_tsv(results: list[CheckResult], tsv_dir: Path) -> None:
    tsv_dir.mkdir(parents=True, exist_ok=True)
    for r in results:
        path = tsv_dir / f"{r.check}.tsv"
        with path.open("w", encoding="utf-8") as fp:
            fp.write("check\tpath\tline\tcategory\tlevel\tstatus\tsuggestion\tsuppressed_reason\tmatched\n")
            for f in r.findings:
                fp.write(f.as_tsv() + "\n")


def _format_check_summary(r: CheckResult) -> str:
    parts = []
    if r.error_count:
        parts.append(f"{r.error_count} error")
    if r.warning_count:
        parts.append(f"{r.warning_count} warning")
    if r.info_count:
        parts.append(f"{r.info_count} info")
    if r.suppressed_count:
        parts.append(f"{r.suppressed_count} suppressed")
    return " / ".join(parts) if parts else "clean"


def _print_summary(
    results: list[CheckResult],
    verbose: bool,
    exit_code: int,
    strict: bool,
    stream_stdout,
    stream_stderr,
) -> None:
    cats_with_active = [r.check for r in results if r.active_findings]
    header = f"docaudit: {len(results)} checks, {len(cats_with_active)} categories with findings"
    print(header, file=stream_stdout)
    print(file=stream_stdout)

    for r in results:
        label = f"[{r.check}]".ljust(22)
        summary = _format_check_summary(r)
        line = f"{label} {summary}"
        print(line, file=stream_stdout)
        if r.error_count or r.warning_count:
            # 镜像 warning/error 摘要到 stderr（策略契约）
            print(line, file=stream_stderr)
        if verbose and r.findings:
            for f in r.findings[:20]:
                loc = f"{f.path}:{f.line}" if f.line else f.path
                status = "[SUPPRESSED]" if f.suppressed else ""
                tail = f" [{f.suppressed_reason}]" if f.suppressed else ""
                print(f"  · {loc}  [{f.category}]  {f.suggestion}{tail} {status}".rstrip(),
                      file=stream_stdout)
            if len(r.findings) > 20:
                print(f"  ... and {len(r.findings) - 20} more", file=stream_stdout)
    print(file=stream_stdout)

    error_checks = [r.check for r in results if r.error_count > 0]
    strict_checks = [r.check for r in results if r.warning_count > 0 and r.error_count == 0]
    if exit_code == 0:
        print("Exit: 0", file=stream_stdout)
    elif error_checks and (strict and strict_checks):
        print(f"Exit: {exit_code} (error: {error_checks}; strict-upgraded warning: {strict_checks})",
              file=stream_stdout)
    elif error_checks:
        print(f"Exit: {exit_code} (error level in: {error_checks})", file=stream_stdout)
    elif strict and strict_checks:
        print(f"Exit: {exit_code} (strict mode; warning level in: {strict_checks})", file=stream_stdout)
    else:
        print(f"Exit: {exit_code}", file=stream_stdout)

    # 非零退出也镜像 final line 到 stderr
    if exit_code != 0:
        print(f"docaudit exit {exit_code}", file=stream_stderr)


def _overall_exit_code(results: list[CheckResult], strict: bool) -> int:
    for r in results:
        if r.error_count > 0:
            return 1
        if strict and r.warning_count > 0:
            return 1
    return 0


# ---------- CLI ----------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docaudit",
        description="agent-harness docaudit — documentation audit engine.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Override policy.yaml path (see module docstring for resolution priority).",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root (see module docstring for resolution priority).",
    )

    sub = parser.add_subparsers(dest="command", required=True, metavar="<subcommand>")

    def _add_common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--strict", action="store_true", help="Treat warning as error (exit 1).")
        sp.add_argument("--report", action="store_true", help="Write TSV reports to <tsv_dir>.")
        sp.add_argument("--baseline", action="store_true",
                        help="Apply legacy_whitelist finding-level suppression.")
        sp.add_argument("--verbose", "-v", action="store_true", help="Print finding details.")

    all_parser = sub.add_parser(
        "all",
        help="Run all checks (+ frontmatter via subprocess if configured).",
        description="Run all 6 checks plus frontmatter via subprocess (if policy.layout.frontmatter_validator is set).",
        epilog="Example: docaudit all --report --verbose",
    )
    _add_common(all_parser)

    for name in CHECK_NAMES:
        desc = CHECK_DESCRIPTIONS[name]
        sp = sub.add_parser(
            name,
            help=desc["help"],
            description=desc["description"],
            epilog=desc["epilog"],
        )
        _add_common(sp)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = resolve_repo_root(args.repo_root)
    policy_path = resolve_policy_path(args.policy, repo_root)
    policy = load_policy(policy_path)
    whitelist_rules = _parse_whitelist(policy)

    if args.command == "all":
        checks_to_run = CHECK_NAMES
        include_frontmatter = True
    else:
        checks_to_run = [args.command]
        include_frontmatter = False

    results: list[CheckResult] = []
    if include_frontmatter:
        try:
            fm_result = check_frontmatter_via_subprocess(policy, repo_root)
            if fm_result is not None:
                results.append(fm_result)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: frontmatter orchestration crashed: {exc}", file=sys.stderr)
            return 2

    for name in checks_to_run:
        func = CHECK_FUNCS[name]
        try:
            results.append(func(policy, repo_root))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: check {name} crashed: {exc}", file=sys.stderr)
            return 2

    for r in results:
        _apply_whitelist(r, whitelist_rules, args.baseline)

    if args.report:
        tsv_dir = repo_root / policy.get("output", {}).get("tsv_dir", "reports")
        _write_tsv(results, tsv_dir)

    exit_code = _overall_exit_code(results, args.strict)
    _print_summary(
        results,
        args.verbose,
        exit_code,
        args.strict,
        stream_stdout=sys.stdout,
        stream_stderr=sys.stderr,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
