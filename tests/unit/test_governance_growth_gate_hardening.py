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
import governance_reverse_dependency as grd  # noqa: E402

# ---------------------------------------------------------------------------
# Git helpers (duplicated from test_governance_growth_gate.py for independence)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=True,
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
# Gate runner helpers
# ---------------------------------------------------------------------------


def _run_gate(repo: Path, base_sha: str, head_sha: str) -> list[str]:
    return ggg.run_governance_growth_gate(repo, base_sha, head_sha)


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
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
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
        _write_file(repo, "src/services/multi_dep.py", "from scripts.ops.multi_helper import bad\n")
        head = _commit_all(repo, "multi violation")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Expected non-zero exit: {exit_code}"
        for code in [ggg.ERR_REPORT, ggg.ERR_MANIFEST, ggg.ERR_PHASE, grd.ERR_REVERSE_DEP]:
            assert code in stderr, f"Missing {code} in output"

    def test_real_exit_nonzero_on_bad_ref(self, repo_with_base):
        repo, base = repo_with_base
        exit_code, _stderr = _run_gate_via_cli(repo, "nonexistent-ref-99999", base)
        assert exit_code != 0, f"Expected non-zero exit on bad ref: {exit_code}"

    def test_real_exit_nonzero_rename_r100(self, repo_with_base):
        repo, base = repo_with_base
        _git(repo, "mv", "scripts/ci/normal_ci_check.py", "scripts/ops/phase_99_new_gate.py")
        head = _commit_all(repo, "rename R100 into phase")
        exit_code, stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"R100 rename must fail: {exit_code}"
        assert ggg.ERR_PHASE in stderr

    def test_real_exit_nonzero_same_count_replacement(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(repo, "src/services/old_dep.py", "from scripts.ops.new_helper import run\n")
        head = _commit_all(repo, "replace dep")
        exit_code, _stderr = _run_gate_via_cli(repo, base, head)
        assert exit_code != 0, f"Same-count replacement must fail: {exit_code}"


# ---------------------------------------------------------------------------
# Real AI Workflow Gate CLI propagation tests — fully isolated
# ---------------------------------------------------------------------------
# These tests create a complete temporary git repository (via git bundle)
# inside ``tmp_path`` and run the real ``ai_workflow_gate.py`` CLI against
# that isolated repo.  The source project working tree is never modified.
# ---------------------------------------------------------------------------


def _create_isolated_repo(tmp_path: Path, source_repo: Path) -> tuple[Path, str]:
    """Create a full isolated git clone from *source_repo*'s HEAD via bundle.

    Returns ``(temp_repo_path, source_head_sha)``.  The clone lives under
    *tmp_path* and is automatically cleaned up by pytest.
    """
    source_head = _git(source_repo, "rev-parse", "HEAD")

    bundle_path = tmp_path / "source.bundle"
    temp_repo = tmp_path / "isolated-repo"

    _git(source_repo, "bundle", "create", str(bundle_path), "HEAD")
    subprocess.run(
        ["git", "clone", "--no-checkout", str(bundle_path), str(temp_repo)],
        check=True,
        text=True,
        capture_output=True,
    )
    _git(temp_repo, "checkout", "--detach", source_head)
    _git(temp_repo, "config", "user.email", "gate-test@example.invalid")
    _git(temp_repo, "config", "user.name", "Governance Gate Isolation Test")

    return temp_repo, source_head


def _write_in_temp(path: Path, content: str) -> None:
    """Write *content* to *path*, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _snapshot_source(repo: Path) -> dict[str, str]:
    """Capture source repo state that must not change during the test."""
    return {
        "head": _git(repo, "rev-parse", "HEAD"),
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD"),
        "status": _git(repo, "status", "--porcelain=v1", "-uall"),
    }


def _assert_source_unchanged(repo: Path, before: dict[str, str]) -> None:
    """Assert that *repo* state matches *before*."""
    after = _snapshot_source(repo)
    assert after["head"] == before["head"], (
        f"Source HEAD changed: {before['head']} → {after['head']}"
    )
    assert after["branch"] == before["branch"], (
        f"Source branch changed: {before['branch']} → {after['branch']}"
    )
    assert after["status"] == before["status"], (
        f"Source working tree dirty:\nbefore={before['status']!r}\nafter={after['status']!r}"
    )


# PR body used by the CLI tests.  Describes a workflow-governance change
# that touches a single governance helper without adding reports, manifests,
# Phase scripts, or reverse dependencies.
_MINIMAL_PR_BODY = """\
## Summary
Test PR for AI workflow gate CLI isolation — fully isolated temporary repo.
## Scope
Test-only change: adds a comment to an existing governance gate module.
No runtime behaviour change.  No business logic, no DB, no scraper, no browser.
| Task type | workflow-governance |
## Documentation Impact
No new docs, reports, or manifests.  No user-facing documentation change.
## Safety Impact
No safety impact — comment-only change.  No new imports, no network or
filesystem access, no auth surface changes.
## Validation
Automated CLI isolation test verifies real entry-point chain.
## CI Gate Scope
Standard PR Gate: Python quality (ruff/mypy), tests (pytest), canonical
Python and JS unit-core, Docker Build Validation.
## No deletion / no move / no rename confirmation
Confirmed — no files are deleted, moved, or renamed.
## Dangerous File Authorization
scripts/ci/governance_growth_gate.py — comment-only change in an existing
governance gate module.  No new dependency paths or auth surface.
## PR Authorization Matrix
| Path | Category | Authorization |
|------|----------|---------------|
| scripts/ci/governance_growth_gate.py | workflow-governance | Comment-only test change in existing gate module. |
| Authorized paths | scripts/ci/governance_growth_gate.py |
## Rollback Plan
Revert the single test commit — a comment-only change with no side effects.
## Next Recommended Task
Do not start automatically.
Recommended next task only after user confirmation: final review of
Draft PR #1790 before deciding whether to mark Ready and merge.
## SC-002 status
No change — enforcement infrastructure remains complete.  Training,
data expansion, and real DB write remain blocked.
## Remaining risks
None — fully isolated test with no runtime behaviour change.
"""


class TestRealAIWorkflowGateCLI:
    """Real CLI propagation tests using fully isolated temporary git repos.

    Both the clean-fixture and violation tests create a complete git
    clone via bundle inside ``tmp_path`` and run ``ai_workflow_gate.py``
    from that clone.  The source project working tree is **never**
    modified — no checkout, no branch creation, no commits, and no
    ``--force`` recovery.
    """

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_cli(
        repo: Path,
        pr_body_file: Path,
        base_ref: str,
        head_ref: str,
    ) -> subprocess.CompletedProcess[str]:
        """Run the real ``ai_workflow_gate.py`` CLI inside *repo*."""
        gate_script = repo / "scripts" / "ops" / "ai_workflow_gate.py"
        return subprocess.run(
            [
                sys.executable,
                str(gate_script),
                "--pr-body-file",
                str(pr_body_file),
                "--base-ref",
                base_ref,
                "--head-ref",
                head_ref,
            ],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )

    # ------------------------------------------------------------------
    # clean fixture
    # ------------------------------------------------------------------

    def test_real_cli_exit_zero_on_clean_fixture(self, tmp_path):
        """Real CLI in isolated repo: no governance violations → exit 0."""
        project_root = Path(ggg.__file__).resolve().parents[2]
        before = _snapshot_source(project_root)

        # Create isolated clone and add a trivial non-governance change.
        temp_repo, base_sha = _create_isolated_repo(tmp_path, project_root)
        _write_in_temp(
            temp_repo / "scripts" / "ci" / "governance_growth_gate.py",
            (temp_repo / "scripts" / "ci" / "governance_growth_gate.py").read_text(encoding="utf-8")
            + "\n# isolated CLI test marker\n",
        )
        _git(temp_repo, "add", "scripts/ci/governance_growth_gate.py")
        _git(temp_repo, "commit", "-m", "test: add comment for CLI clean fixture")
        head_sha = _git(temp_repo, "rev-parse", "HEAD")

        pr_body_file = tmp_path / "pr_body.md"
        pr_body_file.write_text(_MINIMAL_PR_BODY, encoding="utf-8")

        result = self._run_cli(temp_repo, pr_body_file, base_sha, head_sha)
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Expected exit 0, got {result.returncode}. output={combined}"
        )

        # Source repo must be untouched.
        _assert_source_unchanged(project_root, before)

    # ------------------------------------------------------------------
    # violation fixture
    # ------------------------------------------------------------------

    def test_real_cli_exit_nonzero_on_report_violation(self, tmp_path):
        """Real CLI in isolated repo: new report → non-zero, GOV-GROWTH-REPORT.

        The violation commit is made inside the temporary clone — the
        source project working tree is never touched.  This test runs in
        CI without any skip / xfail / environment-variable gate.
        """
        project_root = Path(ggg.__file__).resolve().parents[2]
        before = _snapshot_source(project_root)

        # Isolated clone.
        temp_repo, base_sha = _create_isolated_repo(tmp_path, project_root)

        # Commit a new report inside the temp repo.
        _write_in_temp(
            temp_repo / "docs" / "_reports" / "CLI_REAL_VIOLATION.md",
            "# Real CLI violation\n",
        )
        _git(temp_repo, "add", "docs/_reports/CLI_REAL_VIOLATION.md")
        _git(temp_repo, "commit", "-m", "test: add isolated CLI report violation")
        head_sha = _git(temp_repo, "rev-parse", "HEAD")

        pr_body_file = tmp_path / "pr_body.md"
        pr_body_file.write_text(_MINIMAL_PR_BODY, encoding="utf-8")

        result = self._run_cli(temp_repo, pr_body_file, base_sha, head_sha)
        combined = result.stdout + result.stderr
        assert result.returncode != 0, (
            f"Real CLI must return non-zero on violation, "
            f"got {result.returncode}. output={combined}"
        )
        assert "GOV-GROWTH-REPORT" in combined, f"Expected GOV-GROWTH-REPORT in output: {combined}"
        assert "CLI_REAL_VIOLATION.md" in combined, (
            f"Expected CLI_REAL_VIOLATION.md in output: {combined}"
        )

        # Source repo must be untouched.
        _assert_source_unchanged(project_root, before)


# ---------------------------------------------------------------------------
# JS multiline static import boundary tests (Stage 5)
# ---------------------------------------------------------------------------


class TestJSMultilineImportBoundary:
    """Long ``import { ... } from '...'`` statements must be detected
    regardless of line count (no fixed 5-line lookback limit)."""

    def test_long_multiline_import_blocked_8plus_lines(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/longImport.js",
            "import {\n" + "first,\n" * 8 + "} from '../../scripts/ops/helper.js';\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add long import"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"8+ line import must be blocked: {errors}"
        )

    def test_long_import_in_comment_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/commentExample.js",
            "// Example of a long import:\n"
            "// import {\n"
            "//   first,\n"
            "//   second,\n"
            "//   third,\n"
            "//   fourth,\n"
            "//   fifth,\n"
            "//   sixth,\n"
            "//   seventh,\n"
            "//   eighth\n"
            "// } from '../../scripts/ops/helper.js';\n"
            "const x = 1;\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add comment example"))
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Comment should not be flagged: {errors}"
        )

    def test_long_import_in_template_string_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/templateExample.js",
            "const example = `import {\n"
            "  first,\n"
            "  second,\n"
            "  third,\n"
            "  fourth,\n"
            "  fifth,\n"
            "  sixth,\n"
            "  seventh,\n"
            "  eighth\n"
            '} from "../../scripts/ops/helper.js"`;\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add template example"))
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Template string should not be flagged: {errors}"
        )

    def test_normal_multiline_code_not_import_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/normalCode.js",
            "function processItems(\n"
            "  first,\n"
            "  second,\n"
            "  third,\n"
            "  fourth,\n"
            "  fifth,\n"
            "  sixth,\n"
            "  seventh,\n"
            "  eighth\n"
            ") {\n"
            "  return [first, second, third, fourth, fifth, sixth, seventh, eighth];\n"
            "}\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add normal code"))
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Normal code should not be flagged: {errors}"
        )


# ---------------------------------------------------------------------------
# JS constant backtick template path tests (Stage 6)
# ---------------------------------------------------------------------------


class TestJSBacktickConstantPath:
    """Constant backtick template literals in execution calls must be detected."""

    def test_spawn_backtick_constant_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/backtickSpawn.js",
            "const { spawn } = require('child_process');\n"
            "spawn('node', [`scripts/ops/task.js`]);\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add backtick spawn"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Backtick spawn must be blocked: {errors}"
        )

    def test_dynamic_import_backtick_constant_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/backtickImport.js",
            "async function load() {\n"
            "  const mod = await import(`../../scripts/ops/helper.js`);\n"
            "  return mod;\n"
            "}\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add backtick import"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Backtick import must be blocked: {errors}"
        )

    def test_backtick_documentation_string_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/docBacktick.js",
            'const example = `spawn("node", ["scripts/ops/demo.js"])`;\n'
            "// This is just documentation, not a real call\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add doc backtick"))
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Doc backtick should not be flagged: {errors}"
        )

    def test_interpolated_backtick_not_fingerprinted(self, repo_with_base):
        """Interpolated templates (``${...}``) cannot resolve to a static path."""
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/interpolatedSpawn.js",
            "const { spawn } = require('child_process');\n"
            "const name = 'task';\n"
            "spawn('node', [`scripts/ops/${name}.js`]);\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add interpolated spawn"))
        # Interpolated templates are NOT fingerprinted — they do not form
        # a definite static path.  This test confirms they are not silently
        # resolved to an incorrect fixed path.
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Interpolated backtick must not produce false fingerprint: {errors}"
        )


# ---------------------------------------------------------------------------
# JS target ./ normalisation tests (Stage 7)
# ---------------------------------------------------------------------------


class TestJSTargetDotSlashNormalization:
    """``./scripts/ops/x.js`` and ``scripts/ops/x.js`` must share a fingerprint."""

    def test_dot_slash_and_plain_are_same_fingerprint(self, repo_with_base):
        """Base uses ./ prefix, head uses bare path — no new dependency."""
        repo, _base = repo_with_base
        _write_file(
            repo,
            "src/services/dotSlash.js",
            'const x = require("./scripts/ops/helper.js");\n',
        )
        base2 = _commit_all(repo, "add ./ dependency")
        _write_file(
            repo,
            "src/services/dotSlash.js",
            'const x = require("scripts/ops/helper.js");\n',
        )
        errors = _run_gate(repo, base2, _commit_all(repo, "remove ./ prefix"))
        assert errors == [], f"./ removal should not be a new dependency: {errors}"

    def test_plain_to_dot_slash_passes(self, repo_with_base):
        """Base uses bare path, head uses ./ prefix — no new dependency."""
        repo, _base = repo_with_base
        _write_file(
            repo,
            "src/services/plainFirst.js",
            'const x = require("scripts/ops/helper.js");\n',
        )
        base2 = _commit_all(repo, "add plain dependency")
        _write_file(
            repo,
            "src/services/plainFirst.js",
            'const x = require("./scripts/ops/helper.js");\n',
        )
        errors = _run_gate(repo, base2, _commit_all(repo, "add ./ prefix"))
        assert errors == [], f"./ addition should not be a new dependency: {errors}"

    def test_different_target_with_dot_slash_still_blocked(self, repo_with_base):
        """Base has old.js, head has ./new.js — still a new dependency."""
        repo, _base = repo_with_base
        _write_file(
            repo,
            "src/services/changedTarget.js",
            'const x = require("scripts/ops/old.js");\n',
        )
        base2 = _commit_all(repo, "add old dependency")
        _write_file(
            repo,
            "src/services/changedTarget.js",
            'const x = require("./scripts/ops/new.js");\n',
        )
        errors = _run_gate(repo, base2, _commit_all(repo, "change to ./new.js"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"New target must be blocked even with ./ prefix: {errors}"
        )

    def test_dot_dot_slash_kept_distinct(self, repo_with_base):
        """``../scripts/ops/x.js`` must remain different from ``scripts/ops/x.js``."""
        repo, _base = repo_with_base
        _write_file(
            repo,
            "src/services/relative.js",
            'const x = require("../scripts/ops/helper.js");\n',
        )
        base2 = _commit_all(repo, "add ../ dependency")
        _write_file(
            repo,
            "src/services/relative.js",
            'const x = require("scripts/ops/helper.js");\n',
        )
        errors = _run_gate(repo, base2, _commit_all(repo, "change ../ to bare"))
        # ../ and bare are different targets — this IS a new fingerprint
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"../ → bare should be a new dependency: {errors}"
        )


# JS scanner bypass regression tests (M2 Hotfix) — Fix 1: abs offset, Fix 2: block-comment


class TestMultilineCallNonZeroOffset:
    """Multiline require()/import() detected when not on file line 1."""

    def test_multiline_require_after_prelude_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/multilineAfterPrelude.js",
            'const prelude = 1;\nconst helper = require(\n  "../../scripts/ops/helper.js"\n);\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add multiline require"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Multiline require after prelude must be blocked: {errors}"
        )

    def test_multiline_import_after_prelude_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/multilineImportAfterPrelude.js",
            'const prelude = 1;\nconst helper = import(\n  "../../scripts/ops/helper.js"\n);\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add multiline import"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Multiline import after prelude must be blocked: {errors}"
        )


class TestBlockCommentBoundary:
    """Code after leading block comment must be scanned."""

    def test_block_comment_then_require_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/commentThenRequire.js",
            '/* note */ const helper = require("../../scripts/ops/helper.js");\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add comment then require"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Block-comment then require must be blocked: {errors}"
        )

    def test_fake_in_comment_real_after_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/fakeThenReal.js",
            '/* require("../../scripts/ops/ignored.js"); */ const helper = require(\n'
            '  "../../scripts/ops/real.js"\n'
            ");\n",
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add fake then real require"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Real require after block comment must be blocked: {errors}"
        )
        for e in errors:
            assert "ignored.js" not in e, f"Fake require in comment should not be flagged: {e}"

    def test_block_comment_then_import_blocked(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/commentThenImport.js",
            '/* note */ const helper = import("../../scripts/ops/helper.js");\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add comment then import"))
        assert any(grd.ERR_REVERSE_DEP in e for e in errors), (
            f"Block-comment then import must be blocked: {errors}"
        )

    def test_pure_block_comment_passes(self, repo_with_base):
        repo, base = repo_with_base
        _write_file(
            repo,
            "src/services/pureComment.js",
            '/* const helper = require("../../scripts/ops/ignored.js"); */\n',
        )
        errors = _run_gate(repo, base, _commit_all(repo, "add pure block comment"))
        assert [e for e in errors if grd.ERR_REVERSE_DEP in e] == [], (
            f"Pure block comment must pass: {errors}"
        )


class TestRealAIWorkflowGateCLIReverseDep:
    """Real CLI must detect JS reverse-dependency scanner bypasses.

    Creates a new ``src/**/*.js`` file with previously-bypassable patterns
    inside an isolated temporary repo via git bundle.
    """

    def test_real_cli_exit_zero_on_js_clean(self, tmp_path):
        """Clean fixture: no new JS reverse dependency → exit 0."""
        project_root = Path(ggg.__file__).resolve().parents[2]
        before = _snapshot_source(project_root)
        temp_repo, base_sha = _create_isolated_repo(tmp_path, project_root)
        _write_in_temp(
            temp_repo / "src" / "services" / "cleanMarker.js",
            "// Clean file — no reverse dependency\nconst x = 1;\n",
        )
        _git(temp_repo, "add", "src/services/cleanMarker.js")
        _git(temp_repo, "commit", "-m", "test: clean JS file")
        head_sha = _git(temp_repo, "rev-parse", "HEAD")
        pr_body_file = tmp_path / "pr_body.md"
        pr_body_file.write_text(_MINIMAL_PR_BODY, encoding="utf-8")
        result = TestRealAIWorkflowGateCLI._run_cli(temp_repo, pr_body_file, base_sha, head_sha)
        combined = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"Clean JS must exit 0, got {result.returncode}. output={combined}"
        )
        _assert_source_unchanged(project_root, before)

    def test_real_cli_exit_nonzero_on_js_bypass(self, tmp_path):
        """Bypass fixture: multiline offset + block-comment patterns."""
        project_root = Path(ggg.__file__).resolve().parents[2]
        before = _snapshot_source(project_root)
        temp_repo, base_sha = _create_isolated_repo(tmp_path, project_root)
        _write_in_temp(
            temp_repo / "src" / "services" / "bypassTest.js",
            "const prelude = 1;\n\n"
            "const first = require(\n"
            '  "../../scripts/ops/multiline_helper.js"\n'
            ");\n\n"
            "/* note */ const second =\n"
            '  require("../../scripts/ops/comment_helper.js");\n',
        )
        _git(temp_repo, "add", "src/services/bypassTest.js")
        _git(temp_repo, "commit", "-m", "test: JS scanner bypass patterns")
        head_sha = _git(temp_repo, "rev-parse", "HEAD")
        pr_body_file = tmp_path / "pr_body.md"
        pr_body_file.write_text(_MINIMAL_PR_BODY, encoding="utf-8")
        result = TestRealAIWorkflowGateCLI._run_cli(temp_repo, pr_body_file, base_sha, head_sha)
        combined = result.stdout + result.stderr
        assert result.returncode != 0, (
            f"JS bypass must exit non-zero, got {result.returncode}. output={combined}"
        )
        assert grd.ERR_REVERSE_DEP in combined, (
            f"Must contain {grd.ERR_REVERSE_DEP}. output={combined}"
        )
        assert "bypassTest.js" in combined, f"Must reference bypassTest.js. output={combined}"
        _assert_source_unchanged(project_root, before)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
