"""Tests for dangerous file change check helper.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

from helpers.dangerous_file_change_check import (  # noqa: E402
    _classify_dangerous_paths,
    _has_dangerous_file_auth,
    _match_dangerous_path,
    _pr_declares_docs_only,
    _pr_declares_no_db,
    _pr_declares_no_docker,
    check_dangerous_file_changes,
)

# ---- Path matching tests ----


def test_match_dockerfile_exact():
    assert _match_dangerous_path("Dockerfile", ("Dockerfile",))


def test_match_dockerfile_glob():
    assert _match_dangerous_path(".devcontainer/Dockerfile", ("**/Dockerfile",))
    assert _match_dangerous_path("sub/deep/Dockerfile", ("**/Dockerfile",))


def test_match_migration_prefix():
    assert _match_dangerous_path("database/migrations/0001.sql", ("database/migrations/",))


def test_match_github_workflow():
    assert _match_dangerous_path(".github/workflows/production-gate.yml", (".github/workflows/",))


def test_match_sc002_glob():
    assert _match_dangerous_path("scripts/ops/sc002_something.py", ("scripts/**/*sc002*",))


def test_match_sql_glob():
    assert _match_dangerous_path("script.sql", ("*.sql",))


def test_match_alembic():
    assert _match_dangerous_path("alembic/versions/abc123.py", ("alembic/",))


def test_match_db_write_guard():
    assert _match_dangerous_path(
        "scripts/ops/helpers/db_write_guard.js",
        ("scripts/ops/helpers/db_write_guard*",),
    )


def test_no_match_safe_path():
    assert not _match_dangerous_path(
        "docs/CODEX_WORKFLOW.md",
        ("*.sql", "Dockerfile", ".github/workflows/"),
    )
    assert not _match_dangerous_path(
        "tests/unit/test_something.py",
        ("database/migrations/", "Dockerfile"),
    )


# ---- Classification tests ----


def test_classify_dangerous_paths():
    changed = {
        "Dockerfile",
        "database/migrations/0001.sql",
        "src/config/settings.py",
        "docs/readme.md",
    }
    classified = _classify_dangerous_paths(changed)
    assert "docker_or_compose" in classified
    assert "sql_or_migration" in classified
    assert classified["docker_or_compose"] == ["Dockerfile"]
    assert classified["sql_or_migration"] == ["database/migrations/0001.sql"]


def test_classify_empty():
    changed = {"docs/README.md", "tests/unit/test.py"}
    classified = _classify_dangerous_paths(changed)
    assert not classified


# ---- Auth section detection tests ----


def test_valid_auth_section():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        Modify Dockerfile because user explicitly authorized the change.
        Rollback: revert this commit.
        Validation: CI Docker build check.
    """)
    assert _has_dangerous_file_auth(body)


def test_missing_auth_section():
    body = "## Summary\n\nNo auth section here.\n"
    assert not _has_dangerous_file_auth(body)


def test_hollow_auth_section():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        N/A
    """)
    assert not _has_dangerous_file_auth(body)


def test_hollow_auth_none():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        none
    """)
    assert not _has_dangerous_file_auth(body)


def test_hollow_auth_no_dangerous_files():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        no dangerous files.
    """)
    assert not _has_dangerous_file_auth(body)


def test_auth_section_too_short():
    # Only 1 substantive line — needs at least 2
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        Authorized.
    """)
    assert not _has_dangerous_file_auth(body)


# ---- Safety declaration detection tests ----


def test_pr_declares_docs_only():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | docs-only |
    """)
    assert _pr_declares_docs_only(body)


def test_pr_does_not_declare_docs_only():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | runtime-code-change |
    """)
    assert not _pr_declares_docs_only(body)


def test_pr_declares_no_db():
    body = textwrap.dedent("""\
        ## Safety Impact

        | DB used | no |
    """)
    assert _pr_declares_no_db(body)


def test_pr_declares_no_db_safety_status():
    body = textwrap.dedent("""\
        ## Safety Status

        - no DB writes: yes
    """)
    assert _pr_declares_no_db(body)


def test_pr_declares_no_docker():
    body = textwrap.dedent("""\
        ## Safety Impact

        | Docker used | no |
    """)
    assert _pr_declares_no_docker(body)


# ---- Main gate check tests ----


def _safe_body() -> str:
    return textwrap.dedent("""\
        ## Summary

        Test PR.

        ## Scope

        | Task type | governance-only |

        ## Safety Impact

        | DB used | no |
        | Docker used | no |
    """)


def test_safe_pr_passes():
    """Normal docs-only or governance PR with only docs/tests changed passes."""
    changed = {"docs/README.md", "tests/unit/test_dangerous.py"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert not errors


def test_safe_code_change_without_dangerous_paths_passes():
    """Code change in src/ without dangerous files passes."""
    changed = {"src/config/settings.py", "tests/unit/test_config.py"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert not errors


def test_dockerfile_without_auth_fails():
    """Changing Dockerfile without Dangerous File Authorization fails."""
    changed = {"Dockerfile", "docs/README.md"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1
    assert any("Docker" in e for e in errors)
    assert any("authorization" in e.lower() for e in errors)


def test_migration_without_auth_fails():
    """Changing migration file without Dangerous File Authorization fails."""
    changed = {"database/migrations/0002.sql"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1
    assert any("SQL" in e or "migration" in e.lower() for e in errors)


def test_workflow_without_auth_fails():
    """Changing .github/workflows/ without Dangerous File Authorization fails."""
    changed = {".github/workflows/production-gate.yml"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1
    assert any("workflow" in e.lower() for e in errors)


def test_dangerous_file_with_valid_auth_passes():
    """Dangerous file change with valid auth section passes when safety consistent."""
    body = textwrap.dedent("""\
        ## Summary

        Authorized Dockerfile change.

        ## Scope

        | Task type | governance-only |

        ## Safety Impact

        | DB used | no |
        | Docker used | yes |

        ## Dangerous File Authorization

        Modifying Dockerfile to update base image version.
        User explicitly authorized this change in issue #XXXX.
        Rollback: revert this commit.
        Validation: CI Docker build validation job.
        No DB, no migration, no SC-002 impact.
    """)
    changed = {"Dockerfile"}
    errors = check_dangerous_file_changes(changed, body)
    assert not errors


def test_migration_with_no_db_claim_fails():
    """Migration file change with no-DB safety declaration fails (contradiction)."""
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        Need to update migration for schema fix.
        User authorized.

        ## Safety Impact

        | DB used | no |
    """)
    changed = {"database/migrations/0002.sql"}
    errors = check_dangerous_file_changes(changed, body)
    assert len(errors) >= 1
    assert any("no DB" in e or "no migration" in e.lower() for e in errors)


def test_docs_only_with_business_code_fails():
    """Docs-only declaration with src/ changes fails regardless of auth."""
    body = textwrap.dedent("""\
        ## Scope

        | Task type | docs-only |

        ## Dangerous File Authorization

        Authorized docs-only change.
        This is a valid authorization section.
    """)
    changed = {"src/config/settings.py", "docs/README.md"}
    errors = check_dangerous_file_changes(changed, body)
    assert len(errors) >= 1
    assert any("docs-only" in e.lower() for e in errors)


def test_no_docker_with_dockerfile_fails():
    """No-Docker declaration with Dockerfile change fails (contradiction)."""
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        Authorized to change Dockerfile.
        User explicitly approved.

        ## Safety Impact

        | Docker used | no |
    """)
    changed = {"Dockerfile"}
    errors = check_dangerous_file_changes(changed, body)
    assert len(errors) >= 1
    assert any("Docker" in e for e in errors)


def test_multiple_dangerous_categories_reported():
    """Multiple dangerous categories are all reported in errors."""
    changed = {
        "Dockerfile",
        "database/migrations/0001.sql",
        ".github/workflows/production-gate.yml",
    }
    errors = check_dangerous_file_changes(changed, _safe_body())
    min_categories = 3  # docker_or_compose, sql_or_migration, github_workflow
    assert len(errors) >= min_categories
    assert any("Docker" in e for e in errors)
    assert any("SQL" in e or "migration" in e.lower() for e in errors)
    assert any("workflow" in e.lower() for e in errors)


def test_sc002_paths_detected():
    """SC-002 role deployment paths are flagged as dangerous."""
    changed = {"scripts/ops/sc002_closure_execute.py"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1
    assert any("SC-002" in e for e in errors)


def test_env_files_detected():
    """.env file changes are flagged as dangerous."""
    changed = {".env.production"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1


def test_model_artifacts_detected():
    """Model/data artifact paths are flagged as dangerous."""
    changed = {"models/xgboost_v2.pkl"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1
    assert any("Model" in e for e in errors)


def test_deploy_paths_detected():
    """Deploy paths are flagged as dangerous."""
    changed = {"deploy/Dockerfile"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1


def test_gatekeeper_changes_detected():
    """Gatekeeper script changes are flagged as deploy/staging dangerous."""
    changed = {"scripts/ops/gatekeeper.js"}
    errors = check_dangerous_file_changes(changed, _safe_body())
    assert len(errors) >= 1


def test_auth_section_with_no_contradictions_passes():
    """Dangerous files with auth and consistent safety declarations pass."""
    body = textwrap.dedent("""\
        ## Summary

        Authorized workflow change.

        ## Scope

        | Task type | governance-only |

        ## Safety Impact

        | DB used | no |
        | Browser automation used | no |
        | Scraper run | no |

        ## Dangerous File Authorization

        Modifying Production Gate workflow to add dangerous-file-check step.
        This is explicitly scoped as a governance/CI guardrail change.
        User authorized in Phase 5R0-B task.
        No DB, no migration, no SC-002, no Docker runtime change.
        Rollback: revert commit.
        Validation: CI will run the new check.
    """)
    changed = {".github/workflows/production-gate.yml"}
    errors = check_dangerous_file_changes(changed, body)
    # With valid auth and no contradictions, should pass
    assert not errors
