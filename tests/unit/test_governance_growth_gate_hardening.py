"""Hardening tests for M2 governance growth freeze gate.

lifecycle: test-fixture

Covers real process exit code verification and additional boundary scenarios
that exercise the full CLI integration path. These tests spawn subprocesses
to confirm the gate produces correct exit codes when invoked externally.

Kept in a separate file from test_governance_growth_gate.py to stay under
the 800-line gatekeeper limit.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ci"))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

import governance_growth_gate as ggg  # noqa: E402

# ---------------------------------------------------------------------------
# Git helpers (duplicated from test_governance_growth_gate.py for independence)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, text=True, capture_output=True, check=True,
    )
    return result.stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--initial-branch=main")
    _git(repo, "config", "user.email", "gate-test@example.invalid")
    _git(repo, "config", "user.name", "Gov Growth Gate Hardening Tests")
    return repo


def _commit_all(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _write_file(repo: Path, path: str, content: str) -> None:
    file_path = repo / path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Real process exit code helper
# ---------------------------------------------------------------------------


def _run_gate_via_cli(repo: Path, base_sha: str, head_sha: str) -> tuple[int, str]:
    """Run the gate via a subprocess to verify real exit codes.

    Imports the gate module from the real project tree, but runs it against
    the test repo for git operations.
    """
    gate_dir = str(Path(ggg.__file__).resolve().parent)
    project_root = str(Path(ggg.__file__).resolve().parents[2])

    helper = (
        "import sys; "
        f"sys.path.insert(0, {gate_dir!r}); "
        f"sys.path.insert(0, {project_root!r}); "
        "from governance_growth_gate import run_governance_growth_gate; "
        f"errors = run_governance_growth_gate({str(repo)!r}, sys.argv[1], sys.argv[2]); "
        "sys.stderr.write('\\n'.join(errors)); "
        "sys.exit(1 if errors else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", helper, base_sha, head_sha],
        cwd=repo, text=True, capture_output=True, check=False,
    )
    return result.returncode, result.stderr


# ---------------------------------------------------------------------------
# Test fixture
# ---------------------------------------------------------------------------


def _make_base_commit(repo: Path, files: dict[str, str]) -> str:
    for path, content in files.items():
        _write_file(repo, path, content)
    return _commit_all(repo, "base commit")


@pytest.fixture
def repo_with_base(tmp_path: Path) -> tuple[Path, str]:
    repo = _init_repo(tmp_path)
    base_files = {
        "docs/_reports/OLD_REPORT.md": "# Old historical report\nlifecycle: permanent\n",
        "docs/_manifests/old_manifest.json": '{"key": "old"}',
        "scripts/ops/fotmob_adg60_existing.js": "// Existing ADG script\n",
        "src/services/event_bus.py": textwrap.dedent("""\
            from scripts.ops.hunt_league_hashes import find_hash
            """),
        "src/main.py": "def main(): pass\n",
        "scripts/ci/normal_ci_check.py": "# Normal CI script\n",
        "src/services/old_dep.py": textwrap.dedent("""\
            from scripts.ops.old_helper import run
            """),
    }
    base_sha = _make_base_commit(repo, base_files)
    return repo, base_sha


# ---------------------------------------------------------------------------
# Real process exit code tests (Fix 6)
# ---------------------------------------------------------------------------


class TestRealProcessExitCode:
    """Verify the gate produces correct exit codes via actual subprocess."""

    def test_real_exit_zero_on_pass(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/innocent.py", "def foo(): pass\n")
        head = _commit_all(repo, "add innocent file")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. stderr: {stderr}"

    def test_real_exit_nonzero_on_violation(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/FAIL_ME.md", "# Will fail\n")
        head = _commit_all(repo, "add violation")
        exit_code, _stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Expected non-zero exit, got {exit_code}"

    def test_real_exit_nonzero_multi_violation(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "docs/_reports/MULTI_1.md", "# v1\n")
        _write_file(repo, "docs/_manifests/multi_1.json", "{}")
        _write_file(repo, "scripts/ops/phase_99_multi.py", "# Phase 99\n")
        _write_file(repo, "src/services/multi_dep.py",
                    "from scripts.ops.multi_helper import bad\n")
        head = _commit_all(repo, "multi violation")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Expected non-zero exit: {exit_code}"
        for code in [ggg.ERR_REPORT, ggg.ERR_MANIFEST, ggg.ERR_PHASE,
                     ggg.ERR_REVERSE_DEP]:
            assert code in stderr, f"Missing {code} in output"

    def test_real_exit_nonzero_on_bad_ref(self, repo_with_base):
        repo, base = repo_with_base
        exit_code, _stderr = _run_gate_via_cli(
            repo, "nonexistent-ref-99999", base)
        assert exit_code != 0, f"Expected non-zero exit on bad ref: {exit_code}"

    def test_real_exit_nonzero_rename_r100(self, repo_with_base):
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py",
             "scripts/ops/phase_99_new_gate.py")
        head = _commit_all(repo, "rename R100 into phase")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"R100 rename must fail: {exit_code}"
        assert ggg.ERR_PHASE in stderr

    def test_real_exit_nonzero_same_count_replacement(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/old_dep.py",
                    "from scripts.ops.new_helper import run\n")
        head = _commit_all(repo, "replace dep")
        exit_code, _stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Same-count replacement must fail: {exit_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
