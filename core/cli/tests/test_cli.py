"""CLI self-tests — init / doctor / sync / extract-candidate / propose-upstream."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

# Make `core` package importable when tests run from repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from core.cli import main as cli_main  # noqa: E402
from core.cli import cmd_init, cmd_doctor, cmd_sync  # noqa: E402
from core.cli import cmd_extract_candidate, cmd_propose_upstream  # noqa: E402


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_ctx = TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.target = self.tmp / "consumer"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = cli_main.entry(argv)
            except SystemExit as exc:
                code = int(exc.code or 0)
        return code, stdout.getvalue(), stderr.getvalue()

    # ---------- init ----------

    def test_init_minimal_creates_lock_and_project(self) -> None:
        code, out, err = self._run(["init", "--minimal", str(self.target)])
        self.assertEqual(code, 0, err)
        self.assertTrue((self.target / ".agent-harness" / "project.yaml").is_file())
        self.assertTrue((self.target / ".agent-harness" / "lock.json").is_file())
        # minimal 不生成 policy
        self.assertFalse((self.target / "Scripts" / "audit" / "policy.yaml").is_file())
        self.assertIn("minimal", out)

    def test_init_pragmatic_creates_policy_stub(self) -> None:
        code, out, err = self._run(["init", "--pragmatic", str(self.target)])
        self.assertEqual(code, 0, err)
        policy = self.target / "Scripts" / "audit" / "policy.yaml"
        self.assertTrue(policy.is_file())
        # policy stub 应可被 yaml 解析
        data = yaml.safe_load(policy.read_text())
        self.assertEqual(data.get("version"), 1)
        self.assertIn("layout", data)
        self.assertIn("checks", data)

    def test_init_defaults_to_pragmatic(self) -> None:
        code, out, err = self._run(["init", str(self.target)])
        self.assertEqual(code, 0, err)
        self.assertTrue((self.target / "Scripts" / "audit" / "policy.yaml").is_file())

    def test_init_project_name_override(self) -> None:
        code, _, _ = self._run([
            "init", "--minimal",
            "--project-name", "custom-name",
            "--project-type", "cli",
            str(self.target),
        ])
        self.assertEqual(code, 0)
        data = yaml.safe_load((self.target / ".agent-harness" / "project.yaml").read_text())
        self.assertEqual(data["project"]["name"], "custom-name")
        self.assertEqual(data["project"]["type"], "cli")

    def test_init_default_name_is_target_dirname(self) -> None:
        code, _, _ = self._run(["init", "--minimal", str(self.target)])
        self.assertEqual(code, 0)
        data = yaml.safe_load((self.target / ".agent-harness" / "project.yaml").read_text())
        self.assertEqual(data["project"]["name"], "consumer")

    def test_init_upstream_commit_lock(self) -> None:
        commit = "a" * 40
        code, _, _ = self._run([
            "init", "--minimal", "--upstream-commit", commit, str(self.target),
        ])
        self.assertEqual(code, 0)
        lock = json.loads((self.target / ".agent-harness" / "lock.json").read_text())
        self.assertEqual(lock["upstream_commit"], commit)

    def test_init_refuses_to_overwrite_without_force(self) -> None:
        self._run(["init", "--minimal", str(self.target)])
        code, _, err = self._run(["init", "--minimal", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("already contains", err)

    def test_init_force_overwrites(self) -> None:
        self._run(["init", "--minimal", str(self.target)])
        code, _, _ = self._run([
            "init", "--minimal", "--project-name", "new", "--force", str(self.target),
        ])
        self.assertEqual(code, 0)
        data = yaml.safe_load((self.target / ".agent-harness" / "project.yaml").read_text())
        self.assertEqual(data["project"]["name"], "new")

    def test_init_target_must_exist(self) -> None:
        missing = self.tmp / "nonexistent"
        code, _, err = self._run(["init", "--minimal", str(missing)])
        self.assertEqual(code, 2)
        self.assertIn("not an existing directory", err)

    # ---------- doctor ----------

    def test_doctor_on_fresh_init_pragmatic_passes(self) -> None:
        self._run(["init", "--pragmatic", "--upstream-commit", "b" * 40, str(self.target)])
        code, out, _ = self._run(["doctor", str(self.target)])
        # project.yaml + lock.json + policy + docaudit dry-run should all pass
        self.assertEqual(code, 0, out)
        self.assertIn("Exit: 0", out)

    def test_doctor_on_missing_project_yaml_fails(self) -> None:
        code, out, _ = self._run(["doctor", str(self.target)])
        self.assertEqual(code, 1, out)
        self.assertIn("missing", out.lower())

    def test_doctor_warns_on_empty_lock(self) -> None:
        self._run(["init", "--minimal", str(self.target)])
        # lock.json 默认 upstream_commit = ""
        code, out, _ = self._run(["doctor", str(self.target)])
        self.assertEqual(code, 1, out)
        self.assertIn("upstream_commit is empty", out)

    def test_doctor_minimal_has_no_policy_check_fails(self) -> None:
        """--minimal 不生成 policy → doctor 报 policy 缺失 fail。"""
        self._run(["init", "--minimal", "--upstream-commit", "c" * 40, str(self.target)])
        code, out, _ = self._run(["doctor", str(self.target)])
        # lock 正常；project.yaml 正常；policy 缺失 = fail
        self.assertEqual(code, 1, out)
        self.assertIn("no policy.yaml found", out)

    def test_doctor_default_target_is_cwd(self) -> None:
        """doctor 无 target 参数时用 CWD。"""
        self._run(["init", "--pragmatic", "--upstream-commit", "d" * 40, str(self.target)])
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(str(self.target))
            code, _, _ = self._run(["doctor"])
            self.assertEqual(code, 0)
        finally:
            os.chdir(old_cwd)

    # ---------- sync ----------

    def test_sync_check_up_to_date(self) -> None:
        self._run(["init", "--minimal", "--upstream-commit", "e" * 40, str(self.target)])
        fake_head = "e" * 40
        with patch.object(cmd_sync, "_git_ls_remote_head", return_value=(True, fake_head)):
            code, out, _ = self._run(["sync", "--check", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertIn("up to date", out)

    def test_sync_check_drift(self) -> None:
        self._run(["init", "--minimal", "--upstream-commit", "e" * 40, str(self.target)])
        with patch.object(cmd_sync, "_git_ls_remote_head", return_value=(True, "f" * 40)):
            code, out, _ = self._run(["sync", "--check", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertIn("drift detected", out)

    def test_sync_check_empty_lock_warns(self) -> None:
        self._run(["init", "--minimal", str(self.target)])  # no --upstream-commit
        with patch.object(cmd_sync, "_git_ls_remote_head", return_value=(True, "f" * 40)):
            code, out, _ = self._run(["sync", "--check", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertIn("WARNING", out)
        self.assertIn("no upstream_commit", out)

    def test_sync_apply_is_reserved(self) -> None:
        self._run(["init", "--minimal", str(self.target)])
        code, _, err = self._run(["sync", "--apply", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("reserved", err)

    def test_sync_check_missing_lock_exits_2(self) -> None:
        code, _, err = self._run(["sync", "--check", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("lock.json not found", err.lower().replace(".agent-harness/", ""))

    def test_sync_check_network_failure_exits_2(self) -> None:
        self._run(["init", "--minimal", "--upstream-commit", "e" * 40, str(self.target)])
        with patch.object(cmd_sync, "_git_ls_remote_head", return_value=(False, "network unreachable")):
            code, _, err = self._run(["sync", "--check", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("unable to resolve upstream HEAD", err)

    # ---------- version / help ----------

    def test_version_flag(self) -> None:
        code, out, _ = self._run(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("agent-harness", out)


class ContribCliTestCase(unittest.TestCase):
    """extract-candidate / propose-upstream tests. Fixture uses a real git repo."""

    def setUp(self) -> None:
        self._tmp_ctx = TemporaryDirectory()
        self.tmp = Path(self._tmp_ctx.name)
        self.target = self.tmp / "consumer"
        self.target.mkdir()
        # Init git repo so _git_log_stats works
        self._git("init", "-q", "--initial-branch=main")
        self._git("config", "user.email", "test@example.com")
        self._git("config", "user.name", "Test")
        # Run agent-harness init
        self._run(["init", "--pragmatic", "--upstream-commit", "a" * 40, str(self.target)])
        # Update project.yaml to include scan_paths pointing at fixture overlays
        project_yaml_path = self.target / ".agent-harness" / "project.yaml"
        project_yaml_path.write_text(
            yaml.safe_dump({
                "version": 1,
                "project": {"name": "consumer-test", "type": "cli"},
                "upstream": {"repo": "NotBad-Labs/agent-harness", "channel": "main"},
                "contribution": {
                    "enabled": True,
                    "scan_paths": [".claude/skills", ".claude/hooks"],
                    "consumer_terms": ["bespoke-product-name"],
                },
            }),
            encoding="utf-8",
        )
        self._git("add", ".")
        self._git("commit", "-q", "-m", "init fixture")

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=str(self.target),
            check=True,
            capture_output=True,
        )

    def _run(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                code = cli_main.entry(argv)
            except SystemExit as exc:
                code = int(exc.code or 0)
        return code, stdout.getvalue(), stderr.getvalue()

    def _add_fixture_file(self, rel_path: str, content: str, commits: int = 1) -> Path:
        """Write file + commit N times (commits must >= 1)."""
        path = self.target / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        for i in range(commits):
            path.write_text(content + f"\n<!-- rev {i} -->\n", encoding="utf-8")
            self._git("add", rel_path)
            self._git("commit", "-q", "-m", f"add {rel_path} rev {i}")
        return path

    # ---------- extract-candidate ----------

    def test_extract_candidate_missing_project_yaml_exits_2(self) -> None:
        empty_dir = self.tmp / "empty"
        empty_dir.mkdir()
        code, _, err = self._run(["extract-candidate", str(empty_dir)])
        self.assertEqual(code, 2)
        self.assertIn("project.yaml not found", err)

    def test_extract_candidate_reports_candidate_with_3_commits(self) -> None:
        self._add_fixture_file(
            ".claude/skills/generic-skill/SKILL.md",
            "# Generic skill about cross-agent work",
            commits=3,
        )
        code, out, _ = self._run(["extract-candidate", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertIn("generic-skill/SKILL.md", out)
        self.assertIn("Suggested layer:", out)

    def test_extract_candidate_filters_by_3_commits_by_default(self) -> None:
        """File with < 3 commits should be filtered unless --include-untracked."""
        self._add_fixture_file(
            ".claude/skills/new-skill/SKILL.md",
            "# Brand new skill",
            commits=1,
        )
        code, out, _ = self._run(["extract-candidate", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertNotIn("new-skill/SKILL.md", out)

    def test_extract_candidate_include_untracked(self) -> None:
        self._add_fixture_file(
            ".claude/skills/new-skill/SKILL.md",
            "# Brand new skill",
            commits=1,
        )
        code, out, _ = self._run(
            ["extract-candidate", "--include-untracked", str(self.target)]
        )
        self.assertEqual(code, 0, out)
        self.assertIn("new-skill/SKILL.md", out)

    def test_extract_candidate_detects_denylist_hits(self) -> None:
        """File with swift/xcode etc. should get low score + preset-ios suggestion."""
        self._add_fixture_file(
            ".claude/hooks/swift-lint.sh",
            "#!/bin/bash\n# runs swiftlint and xcodebuild tests",
            commits=3,
        )
        code, out, _ = self._run(["extract-candidate", str(self.target)])
        self.assertEqual(code, 0, out)
        self.assertIn("swift-lint.sh", out)
        # Should hit denylist and suggest preset-ios or STAY
        self.assertTrue(
            "preset-ios" in out or "STAY" in out,
            f"expected preset-ios/STAY suggestion in:\n{out}",
        )

    # ---------- propose-upstream ----------

    def test_propose_upstream_generates_draft(self) -> None:
        self._add_fixture_file(
            ".claude/skills/generic-skill/SKILL.md",
            "# Generic skill",
            commits=3,
        )
        code, out, _ = self._run([
            "propose-upstream",
            ".claude/skills/generic-skill/SKILL.md",
            "--target",
            str(self.target),
        ])
        self.assertEqual(code, 0, out)
        self.assertIn("Proposal draft written to:", out)
        proposals_dir = self.target / ".agent-harness" / "proposals"
        self.assertTrue(proposals_dir.is_dir())
        proposals = list(proposals_dir.glob("*.md"))
        self.assertEqual(len(proposals), 1)
        body = proposals[0].read_text(encoding="utf-8")
        self.assertIn("consumer-test", body)
        self.assertIn("generic-skill/SKILL.md", body)
        # P2 status should be ✓ (3 commits >= 3)
        self.assertIn("已独立有效使用 3 次（>= 3）", body)

    def test_propose_upstream_p2_failing_when_below_3_commits(self) -> None:
        self._add_fixture_file(
            ".claude/skills/green-skill/SKILL.md",
            "# New skill",
            commits=1,
        )
        code, out, _ = self._run([
            "propose-upstream",
            ".claude/skills/green-skill/SKILL.md",
            "--target",
            str(self.target),
        ])
        self.assertEqual(code, 0, out)
        body = next((self.target / ".agent-harness" / "proposals").glob("*.md")).read_text()
        self.assertIn("< 3，不满足次门槛", body)
        self.assertIn("NOTE: commit count < 3", out)

    def test_propose_upstream_source_not_found_exits_2(self) -> None:
        code, _, err = self._run([
            "propose-upstream",
            "nonexistent/path.md",
            "--target",
            str(self.target),
        ])
        self.assertEqual(code, 2)
        self.assertIn("source file not found", err)

    def test_propose_upstream_source_outside_consumer_exits_2(self) -> None:
        external = self.tmp / "outside.md"
        external.write_text("# external", encoding="utf-8")
        code, _, err = self._run([
            "propose-upstream",
            str(external),
            "--target",
            str(self.target),
        ])
        self.assertEqual(code, 2)
        self.assertIn("must be inside consumer root", err)

    def test_propose_upstream_missing_project_yaml_exits_2(self) -> None:
        empty = self.tmp / "empty-consumer"
        empty.mkdir()
        (empty / "foo.md").write_text("x", encoding="utf-8")
        code, _, err = self._run([
            "propose-upstream",
            "foo.md",
            "--target",
            str(empty),
        ])
        self.assertEqual(code, 2)
        self.assertIn("project.yaml", err)


if __name__ == "__main__":
    unittest.main()
