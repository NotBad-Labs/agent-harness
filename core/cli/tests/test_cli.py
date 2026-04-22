"""CLI self-tests — init / doctor / sync subcommands."""

from __future__ import annotations

import io
import json
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


if __name__ == "__main__":
    unittest.main()
