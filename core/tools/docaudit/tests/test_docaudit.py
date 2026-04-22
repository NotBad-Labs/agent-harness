"""docaudit self-test — engine behavior (no consumer-specific fixtures)."""

from __future__ import annotations

import io
import stat
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPT_DIR))
import docaudit  # noqa: E402


def _base_policy() -> dict:
    """Minimal generic policy for tests. Uses neutral directory names (no consumer-specific paths)."""
    return {
        "version": 1,
        "layout": {
            "rules_dir": "rules",
            "principles_dir": "principles",
            "rule_pointer_pattern": r"(?:Read and follow|指向|→)\s+({principles_dir}/[A-Za-z0-9_\-./]+\.md)",
            "rules_file": "rules.md",
            "rule_id_pattern": r"\bRULE-(\d{3})\b",
            "rule_header_pattern": r"^#{1,4}\s+RULE-(\d{3})\b",
            "orphan_scan_dir": "docs",
            "frontmatter_validator": "validator.py",
        },
        "scan": {
            "include": ["docs/", "rules/", "principles/", "rules.md", "README.md"],
            "exclude": ["archive/", "tests/fixtures/"],
        },
        "checks": {
            "links": {"level": "error", "description": ""},
            "archived-refs": {
                "level": "error",
                "description": "",
                "archived_sources": ["archive/study.md"],
            },
            "orphans": {
                "level": "warning",
                "description": "",
                "whitelist": ["docs/index/**", "archive/**"],
            },
            "home-path-refs": {
                "level": "warning",
                "description": "",
                "allowed_contexts": ["principles/memory-routing.md"],
            },
            "rule-pointer-sync": {
                "level": "error",
                "description": "",
                "allowlist_rules": ["rules/README.md"],
            },
            "rule-usage": {
                "level": "info",
                "description": "",
                "min_references": 1,
            },
        },
        "output": {"tsv_dir": "reports/", "summary_stdout": True, "verbose_default": False},
    }


def _write_policy(tmp: Path, overrides: dict | None = None) -> Path:
    policy = _base_policy()
    if overrides:
        for k, v in overrides.items():
            if k in policy and isinstance(policy[k], dict) and isinstance(v, dict):
                policy[k] = {**policy[k], **v}
            else:
                policy[k] = v
    path = tmp / "policy.yaml"
    with path.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(policy, fp, sort_keys=False)
    return path


def _make_fixture(repo: Path, fake_validator: bool = True) -> None:
    """Create minimal fixture directory tree using neutral names."""
    (repo / "docs").mkdir(parents=True)
    (repo / "principles").mkdir()
    (repo / "rules").mkdir()
    (repo / "archive").mkdir()
    (repo / "rules.md").write_text(
        "## RULE-001\nrule 1\n\n## RULE-002\nrule 2\n", encoding="utf-8"
    )
    if fake_validator:
        vf = repo / "validator.py"
        vf.write_text(
            "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n",
            encoding="utf-8",
        )
        vf.chmod(vf.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class DocauditTestCase(unittest.TestCase):
    """End-to-end: per subcommand, build fixture → run → assert exit + findings."""

    def setUp(self) -> None:
        self._tmp_ctx = TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        _make_fixture(self.repo)

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        """Run docaudit with --repo-root pointing at the test fixture."""
        full_argv = ["--repo-root", str(self.repo)] + argv
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = docaudit.main(full_argv)
            except SystemExit as exc:
                code = int(exc.code or 0)
        return code, stdout.getvalue(), stderr.getvalue()

    # ---------- links ----------

    def test_links_clean(self) -> None:
        (self.repo / "docs" / "ok.md").write_text("# ok\n", encoding="utf-8")
        (self.repo / "docs" / "index.md").write_text("see [ok](ok.md)\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "links"])
        self.assertEqual(code, 0, out)

    def test_links_broken(self) -> None:
        (self.repo / "docs" / "index.md").write_text("see [missing](gone.md)\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, err = self._run(["--policy", str(policy), "links"])
        self.assertEqual(code, 1, out)
        self.assertIn("error", out)
        self.assertIn("docaudit exit 1", err)

    # ---------- archived-refs ----------

    def test_archived_refs_clean(self) -> None:
        (self.repo / "archive" / "study.md").write_text(
            "---\nstatus: archived\n---\n# study\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "archived-refs"])
        self.assertEqual(code, 0, out)

    def test_archived_refs_NOT_matching_basename_only(self) -> None:
        """Basename-only match NOT applied; only exact path strings hit.
        A new archive path sharing basename with the deprecated one should not false-positive.
        Deprecated path 'deprecated/study.md' must NOT be a substring of new path 'docs/record/study.md'.
        """
        # Use a new archived_sources that cannot appear as substring in the new path below
        (self.repo / "deprecated").mkdir()
        (self.repo / "deprecated" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "record").mkdir()
        (self.repo / "docs" / "record" / "study.md").write_text("# archived\n", encoding="utf-8")
        (self.repo / "docs" / "narrative.md").write_text(
            "see docs/record/study.md for the archived study\n",
            encoding="utf-8",
        )
        policy = _write_policy(self.tmp, overrides={
            "checks": {
                "archived-refs": {
                    "level": "error",
                    "description": "",
                    "archived_sources": ["deprecated/study.md"],
                },
            },
        })
        code, out, _ = self._run(["--policy", str(policy), "archived-refs"])
        # narrative.md references "docs/record/study.md" which does NOT contain "deprecated/study.md"
        self.assertEqual(code, 0, out)

    def test_archived_refs_hit(self) -> None:
        (self.repo / "archive" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "active.md").write_text(
            "see archive/study.md for details\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, err = self._run(["--policy", str(policy), "archived-refs"])
        self.assertEqual(code, 1, out)
        self.assertIn("1 error", out)
        self.assertIn("docaudit exit 1", err)

    def test_archived_refs_suppressed_by_path(self) -> None:
        """Whitelist by path → finding suppressed → exit 0, but finding still visible."""
        (self.repo / "archive" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "active.md").write_text(
            "see archive/study.md\n", encoding="utf-8"
        )
        tomorrow = (date.today() + timedelta(days=30)).isoformat()
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "reason": "legacy baseline",
                "expires_on": tomorrow,
                "paths": ["docs/active.md"],
            }],
        })
        code, out, _ = self._run(["--policy", str(policy), "archived-refs", "--baseline"])
        self.assertEqual(code, 0, out)
        self.assertIn("1 suppressed", out)

    def test_archived_refs_new_file_NOT_suppressed(self) -> None:
        """New violation (path not whitelisted) still errors, prevents regression."""
        (self.repo / "archive" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "old.md").write_text("see archive/study.md\n", encoding="utf-8")
        (self.repo / "docs" / "new.md").write_text("see archive/study.md\n", encoding="utf-8")
        tomorrow = (date.today() + timedelta(days=30)).isoformat()
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "reason": "only old.md is baselined",
                "expires_on": tomorrow,
                "paths": ["docs/old.md"],
            }],
        })
        code, out, _ = self._run(["--policy", str(policy), "archived-refs", "--baseline"])
        self.assertEqual(code, 1, out)         # new.md still error
        self.assertIn("1 error", out)
        self.assertIn("1 suppressed", out)     # old.md suppressed

    def test_archived_refs_expired_whitelist_no_suppression(self) -> None:
        """Expired rules don't apply (fail-closed)."""
        (self.repo / "archive" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "active.md").write_text(
            "see archive/study.md\n", encoding="utf-8"
        )
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "reason": "expired",
                "expires_on": yesterday,
                "paths": ["docs/active.md"],
            }],
        })
        code, out, _ = self._run(["--policy", str(policy), "archived-refs", "--baseline"])
        self.assertEqual(code, 1, out)
        self.assertNotIn("suppressed", out)

    # ---------- whitelist schema edge cases (fail-closed) ----------

    def test_whitelist_invalid_expires_on_exit_2(self) -> None:
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "reason": "r",
                "expires_on": "not-a-date",
            }],
        })
        code, _, err = self._run(["--policy", str(policy), "archived-refs", "--baseline"])
        self.assertEqual(code, 2)
        self.assertIn("expires_on", err)

    def test_whitelist_missing_reason_exit_2(self) -> None:
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "expires_on": "2099-12-31",
            }],
        })
        code, _, err = self._run(["--policy", str(policy), "archived-refs"])
        self.assertEqual(code, 2)
        self.assertIn("reason", err)

    def test_whitelist_unknown_check_exit_2(self) -> None:
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "not-a-check",
                "reason": "r",
                "expires_on": "2099-12-31",
            }],
        })
        code, _, err = self._run(["--policy", str(policy), "archived-refs"])
        self.assertEqual(code, 2)
        self.assertIn("unknown", err.lower())

    def test_whitelist_not_applied_without_baseline_flag(self) -> None:
        (self.repo / "archive" / "study.md").write_text("archived\n", encoding="utf-8")
        (self.repo / "docs" / "active.md").write_text(
            "see archive/study.md\n", encoding="utf-8"
        )
        tomorrow = (date.today() + timedelta(days=30)).isoformat()
        policy = _write_policy(self.tmp, overrides={
            "legacy_whitelist": [{
                "check": "archived-refs",
                "reason": "r",
                "expires_on": tomorrow,
                "paths": ["docs/active.md"],
            }],
        })
        code, out, _ = self._run(["--policy", str(policy), "archived-refs"])
        self.assertEqual(code, 1, out)

    # ---------- orphans ----------

    def test_orphans_clean(self) -> None:
        (self.repo / "docs" / "a.md").write_text("# a\n", encoding="utf-8")
        (self.repo / "docs" / "b.md").write_text("see [a](a.md)\n", encoding="utf-8")
        (self.repo / "docs" / "c.md").write_text("see [b](b.md)\n", encoding="utf-8")
        (self.repo / "README.md").write_text("entry: docs/c.md\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "orphans"])
        self.assertEqual(code, 0, out)

    def test_orphans_hit_warning_does_not_fail(self) -> None:
        (self.repo / "docs" / "lonely.md").write_text("# lonely\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, err = self._run(["--policy", str(policy), "orphans"])
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)
        # warning mirrored to stderr
        self.assertIn("warning", err)

    def test_orphans_strict_escalates(self) -> None:
        (self.repo / "docs" / "lonely.md").write_text("# lonely\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, err = self._run(["--policy", str(policy), "orphans", "--strict"])
        self.assertEqual(code, 1)
        self.assertIn("Exit: 1", out)
        self.assertIn("strict", out)

    def test_orphans_skip_when_layout_missing(self) -> None:
        """Without layout.orphan_scan_dir, orphans check reports missing_layout_config warning and skips scan."""
        # Explicitly blank orphan_scan_dir to override base policy merge
        policy = _write_policy(self.tmp, overrides={
            "layout": {
                "orphan_scan_dir": "",
            },
        })
        code, out, _ = self._run(["--policy", str(policy), "orphans"])
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)

    # ---------- home-path-refs ----------

    def test_home_path_refs_clean(self) -> None:
        (self.repo / "docs" / "clean.md").write_text("no private path\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "home-path-refs"])
        self.assertEqual(code, 0, out)

    def test_home_path_refs_hit(self) -> None:
        (self.repo / "docs" / "dirty.md").write_text(
            "see ~/private-config/foo.md\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, err = self._run(["--policy", str(policy), "home-path-refs"])
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)
        self.assertIn("warning", err)

    def test_home_path_refs_allowed_context(self) -> None:
        mr = self.repo / "principles" / "memory-routing.md"
        mr.write_text("discuss ~/private-config/ here\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "home-path-refs"])
        self.assertEqual(code, 0, out)

    # ---------- rule-pointer-sync ----------

    def test_rule_pointer_sync_clean(self) -> None:
        (self.repo / "principles" / "coding.md").write_text("# coding\n", encoding="utf-8")
        (self.repo / "rules" / "coding.md").write_text(
            "Read and follow principles/coding.md for rules.\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "rule-pointer-sync"])
        self.assertEqual(code, 0, out)

    def test_rule_pointer_sync_broken(self) -> None:
        (self.repo / "rules" / "coding.md").write_text(
            "Read and follow principles/missing.md for rules.\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "rule-pointer-sync"])
        self.assertEqual(code, 1, out)
        self.assertIn("error", out)

    def test_rule_pointer_sync_missing_pointer(self) -> None:
        (self.repo / "rules" / "orphan.md").write_text(
            "This rule has no pointer.\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, _, _ = self._run(["--policy", str(policy), "rule-pointer-sync"])
        self.assertEqual(code, 1)

    def test_rule_pointer_sync_skip_when_layout_missing(self) -> None:
        # Explicitly blank rules_dir / principles_dir to override base policy merge
        policy = _write_policy(self.tmp, overrides={
            "layout": {
                "rules_dir": "",
                "principles_dir": "",
            },
        })
        code, out, _ = self._run(["--policy", str(policy), "rule-pointer-sync"])
        self.assertEqual(code, 0, out)
        self.assertIn("warning", out)

    # ---------- rule-usage ----------

    def test_rule_usage_info_only(self) -> None:
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "rule-usage"])
        self.assertEqual(code, 0, out)
        self.assertIn("info", out)

    def test_rule_usage_referenced(self) -> None:
        (self.repo / "docs" / "workflow.md").write_text(
            "remember RULE-001 applies\nalso RULE-002\n", encoding="utf-8"
        )
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "rule-usage"])
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    def test_rule_usage_custom_pattern(self) -> None:
        """Custom rule_id_pattern (F-NNN instead of RULE-NNN) works via layout override."""
        (self.repo / "custom-rules.md").write_text("## F-001\nrule 1\n", encoding="utf-8")
        (self.repo / "docs" / "ref.md").write_text("F-001 is referenced here\n", encoding="utf-8")
        policy = _write_policy(self.tmp, overrides={
            "layout": {
                "rules_dir": "rules",
                "principles_dir": "principles",
                "rules_file": "custom-rules.md",
                "rule_id_pattern": r"\bF-(\d{3})\b",
                "rule_header_pattern": r"^#{1,4}\s+F-(\d{3})\b",
                "orphan_scan_dir": "docs",
            },
        })
        code, out, _ = self._run(["--policy", str(policy), "rule-usage"])
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    # ---------- all (+ frontmatter subprocess) ----------

    def test_all_runs_every_check_with_fake_validator(self) -> None:
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "all"])
        self.assertIn("[frontmatter]", out)
        for name in docaudit.CHECK_NAMES:
            self.assertIn(f"[{name}]", out)

    def test_all_missing_validator_reports_error(self) -> None:
        """frontmatter_validator path set but file missing → frontmatter CheckResult reports error."""
        (self.repo / "validator.py").unlink()
        policy = _write_policy(self.tmp)
        code, out, _ = self._run(["--policy", str(policy), "all"])
        self.assertEqual(code, 1, out)
        self.assertIn("[frontmatter]", out)
        self.assertIn("error", out)

    def test_all_skips_frontmatter_when_validator_null(self) -> None:
        """When layout.frontmatter_validator is null, `all` skips the frontmatter check entirely."""
        policy = _write_policy(self.tmp, overrides={
            "layout": {
                "rules_dir": "rules",
                "principles_dir": "principles",
                "rules_file": "rules.md",
                "orphan_scan_dir": "docs",
                "frontmatter_validator": None,
            },
        })
        code, out, _ = self._run(["--policy", str(policy), "all"])
        self.assertNotIn("[frontmatter]", out)

    # ---------- TSV report ----------

    def test_report_writes_tsv(self) -> None:
        (self.repo / "docs" / "index.md").write_text("[bad](nope.md)\n", encoding="utf-8")
        policy = _write_policy(self.tmp)
        code, _, _ = self._run(["--policy", str(policy), "links", "--report"])
        tsv = self.repo / "reports" / "links.tsv"
        self.assertTrue(tsv.is_file())
        content = tsv.read_text(encoding="utf-8")
        self.assertIn("check\tpath", content)
        self.assertIn("status", content)
        self.assertIn("broken_link", content)

    # ---------- independent per-subcommand help ----------

    def test_subcommand_help_is_independent(self) -> None:
        parser = docaudit.build_parser()
        actions = [a for a in parser._actions if isinstance(a, __import__("argparse")._SubParsersAction)]
        self.assertTrue(actions)
        choices = actions[0].choices
        self.assertIn("links", choices)
        self.assertIn("all", choices)
        links_parser = choices["links"]
        combined = (links_parser.description or "") + " " + (links_parser.epilog or "")
        self.assertIn("broken_link", combined)


class PolicyEdgeCaseTests(unittest.TestCase):

    def test_missing_policy_exits_2(self) -> None:
        with TemporaryDirectory() as td:
            td_path = Path(td)
            missing = td_path / "no.yaml"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                try:
                    docaudit.main(["--repo-root", str(td_path), "--policy", str(missing), "links"])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 2)
                    self.assertIn("policy.yaml not found", stderr.getvalue())
                    return
                self.fail("expected SystemExit")

    def test_invalid_version_exits_2(self) -> None:
        with TemporaryDirectory() as td:
            td_path = Path(td)
            path = td_path / "policy.yaml"
            with path.open("w") as fp:
                yaml.safe_dump({"version": 99}, fp)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                try:
                    docaudit.main(["--repo-root", str(td_path), "--policy", str(path), "links"])
                except SystemExit as exc:
                    self.assertEqual(exc.code, 2)
                    return
                self.fail("expected SystemExit")

    def test_repo_root_override_via_cli(self) -> None:
        """--repo-root CLI arg takes precedence over env var and CWD."""
        with TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "docs").mkdir()
            (td_path / "docs" / "ok.md").write_text("# ok\n", encoding="utf-8")
            (td_path / "docs" / "index.md").write_text("see [ok](ok.md)\n", encoding="utf-8")
            policy = td_path / "policy.yaml"
            with policy.open("w") as fp:
                yaml.safe_dump({
                    "version": 1,
                    "layout": {
                        "rules_dir": "rules",
                        "principles_dir": "principles",
                        "rules_file": "rules.md",
                        "orphan_scan_dir": "docs",
                    },
                    "scan": {"include": ["docs/"], "exclude": []},
                    "checks": {
                        "links": {"level": "error"},
                        "archived-refs": {"level": "error", "archived_sources": []},
                        "orphans": {"level": "warning", "whitelist": []},
                        "home-path-refs": {"level": "warning"},
                        "rule-pointer-sync": {"level": "error"},
                        "rule-usage": {"level": "info", "min_references": 1},
                    },
                }, fp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                try:
                    code = docaudit.main([
                        "--repo-root", str(td_path),
                        "--policy", str(policy),
                        "links",
                    ])
                except SystemExit as exc:
                    code = int(exc.code or 0)
            self.assertEqual(code, 0, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
