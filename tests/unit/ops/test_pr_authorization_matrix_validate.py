"""Tests for PR authorization matrix — parsing and validation.

lifecycle: test-fixture

Covers: parse_task_type, parse_authorized_paths, validate_authorization
positive / negative / edge / real-world scenarios.
"""

from __future__ import annotations

from pathlib import Path
import sys
import textwrap

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

from helpers.pr_authorization_matrix import (  # noqa: E402
    CATEGORY_DOCS,
    TASK_TYPE_CONFIG_RUNTIME,
    TASK_TYPE_DATA_ARTIFACT,
    TASK_TYPE_DB_MIGRATION_SQL,
    TASK_TYPE_DOCKER_DEPLOY,
    TASK_TYPE_DOCS_ONLY,
    TASK_TYPE_MIXED,
    TASK_TYPE_MODEL_ARTIFACT,
    TASK_TYPE_SC002_DB_GOVERNANCE,
    TASK_TYPE_SOURCE_CODE,
    TASK_TYPE_TEST_ONLY,
    TASK_TYPE_UNKNOWN,
    TASK_TYPE_WORKFLOW_GOVERNANCE,
    parse_authorized_paths,
    parse_task_type,
    validate_authorization,
)

# ---------------------------------------------------------------------------
# parse_task_type — Scope table
# ---------------------------------------------------------------------------


def test_parse_scope_docs_only():
    body = textwrap.dedent("""\
        ## Scope

        | Item | Value |
        |---|---|
        | Task type | docs-only |
        | One task | yes |
    """)
    assert parse_task_type(body) == TASK_TYPE_DOCS_ONLY


def test_parse_scope_docker_deploy():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | docker-deploy |
    """)
    assert parse_task_type(body) == TASK_TYPE_DOCKER_DEPLOY


def test_parse_scope_workflow_governance():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | workflow-governance |
    """)
    assert parse_task_type(body) == TASK_TYPE_WORKFLOW_GOVERNANCE


def test_parse_scope_test_only():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | test-only |
    """)
    assert parse_task_type(body) == TASK_TYPE_TEST_ONLY


# ---------------------------------------------------------------------------
# parse_task_type — PR Type checklist
# ---------------------------------------------------------------------------


def test_parse_pr_type_docs_only():
    body = textwrap.dedent("""\
        ## PR Type

        - [x] docs-only
        - [ ] test-only
        - [ ] source-code
    """)
    assert parse_task_type(body) == TASK_TYPE_DOCS_ONLY


def test_parse_pr_type_test_only():
    body = textwrap.dedent("""\
        ## PR Type

        - [ ] docs-only
        - [X] test-only
        - [ ] source-code
    """)
    assert parse_task_type(body) == TASK_TYPE_TEST_ONLY


def test_parse_pr_type_multiple_checked():
    body = textwrap.dedent("""\
        ## PR Type

        - [x] docs-only
        - [x] test-only
        - [ ] source-code
    """)
    assert parse_task_type(body) == TASK_TYPE_MIXED


# ---------------------------------------------------------------------------
# parse_task_type — absent / unknown
# ---------------------------------------------------------------------------


def test_parse_task_type_absent():
    body = textwrap.dedent("""\
        ## Scope

        No task type here.
    """)
    assert parse_task_type(body) == TASK_TYPE_UNKNOWN


def test_parse_task_type_empty_body():
    assert parse_task_type("") == TASK_TYPE_UNKNOWN


def test_parse_scope_unknown_type():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | something-weird |
    """)
    result = parse_task_type(body)
    assert result == "something-weird"


# ---------------------------------------------------------------------------
# parse_authorized_paths
# ---------------------------------------------------------------------------


def test_parse_authorized_table_row():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        | Authorized paths | scripts/ops/helpers/foo.py, tests/unit/ops/test_foo.py |
    """)
    paths = parse_authorized_paths(body)
    assert "scripts/ops/helpers/foo.py" in paths
    assert "tests/unit/ops/test_foo.py" in paths


def test_parse_authorized_bullet():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        - Authorized paths: scripts/ops/helpers/bar.py, tests/unit/bar.py
    """)
    paths = parse_authorized_paths(body)
    assert "scripts/ops/helpers/bar.py" in paths
    assert "tests/unit/bar.py" in paths


def test_parse_authorized_backtick():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        This PR touches `scripts/ops/helpers/pr_authorization_matrix.py`
        and `tests/unit/ops/test_pr_authorization_matrix.py`.
    """)
    paths = parse_authorized_paths(body)
    assert "scripts/ops/helpers/pr_authorization_matrix.py" in paths
    assert "tests/unit/ops/test_pr_authorization_matrix.py" in paths


def test_parse_authorized_semicolon():
    body = textwrap.dedent("""\
        ## Dangerous File Authorization

        | Authorized paths | a.py; b.py; c.py |
    """)
    paths = parse_authorized_paths(body)
    assert "a.py" in paths
    assert "b.py" in paths
    assert "c.py" in paths


def test_parse_authorized_empty():
    body = textwrap.dedent("""\
        ## Scope

        No auth section here.
    """)
    assert parse_authorized_paths(body) == set()


# ---------------------------------------------------------------------------
# validate_authorization — positive cases
# ---------------------------------------------------------------------------


def test_docs_only_with_docs_file_passes():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md"],
        pr_body="| Task type | docs-only |",
    )
    assert res.valid
    assert res.errors == ()


def test_test_only_with_tests_passes():
    res = validate_authorization(
        TASK_TYPE_TEST_ONLY,
        ["tests/unit/x.py"],
        pr_body="| Task type | test-only |",
    )
    assert res.valid


def test_source_code_with_source_tests_docs_passes():
    res = validate_authorization(
        TASK_TYPE_SOURCE_CODE,
        ["src/foo.py", "tests/unit/bar.py", "docs/readme.md"],
        pr_body="| Task type | source-code |",
    )
    assert res.valid


def test_config_runtime_with_config_tests_docs_passes():
    res = validate_authorization(
        TASK_TYPE_CONFIG_RUNTIME,
        ["pyproject.toml", "tests/config_test.py"],
        pr_body="| Task type | config-runtime |",
    )
    assert res.valid


def test_docker_deploy_with_dangerous_auth_passes():
    body = textwrap.dedent("""\
        | Task type | docker-deploy |

        ## Dangerous File Authorization

        User authorized changes to docker-compose.yml.
        Rollback: revert.
    """)
    res = validate_authorization(
        TASK_TYPE_DOCKER_DEPLOY,
        ["docker-compose.yml"],
        pr_body=body,
    )
    assert res.valid
    assert res.has_dangerous_auth


def test_workflow_governance_with_dangerous_auth_passes():
    body = textwrap.dedent("""\
        | Task type | workflow-governance |

        ## Dangerous File Authorization

        This PR touches governance helpers.

        - Authorized paths: scripts/ops/helpers/pr_authorization_matrix.py
    """)
    res = validate_authorization(
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        ["scripts/ops/helpers/pr_authorization_matrix.py"],
        pr_body=body,
    )
    assert res.valid
    assert res.has_dangerous_auth


def test_db_migration_sql_with_dangerous_auth_passes():
    body = textwrap.dedent("""\
        | Task type | db-migration-sql |

        ## Dangerous File Authorization

        Migration approved by DBA.
        Rollback plan: run the down migration script.
    """)
    res = validate_authorization(
        TASK_TYPE_DB_MIGRATION_SQL,
        ["database/migrations/001.sql"],
        pr_body=body,
    )
    assert res.valid


def test_sc002_with_dangerous_auth_passes():
    body = textwrap.dedent("""\
        | Task type | sc-002-db-governance |

        ## Dangerous File Authorization

        SC-002 guard update approved by security review.
        Rollback: revert to previous guard version.
    """)
    res = validate_authorization(
        TASK_TYPE_SC002_DB_GOVERNANCE,
        ["scripts/ops/sc002_check.py"],
        pr_body=body,
    )
    assert res.valid


def test_unknown_path_does_not_block():
    """An unknown path category should not, by itself, block validation."""
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md", "some/weird/file.xyz"],
        pr_body="| Task type | docs-only |",
    )
    assert res.valid


# ---------------------------------------------------------------------------
# validate_authorization — negative cases
# ---------------------------------------------------------------------------


def test_docs_only_touching_src_fails():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md", "src/foo.py"],
        pr_body="| Task type | docs-only |",
    )
    assert not res.valid
    assert len(res.errors) >= 1
    assert any("source" in e.lower() for e in res.errors)


def test_docs_only_touching_tests_fails():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md", "tests/unit/x.py"],
        pr_body="| Task type | docs-only |",
    )
    assert not res.valid
    assert any("tests" in e for e in res.errors)


def test_test_only_touching_src_fails():
    res = validate_authorization(
        TASK_TYPE_TEST_ONLY,
        ["tests/unit/x.py", "src/foo.py"],
        pr_body="| Task type | test-only |",
    )
    assert not res.valid
    assert any("source" in e.lower() for e in res.errors)


def test_source_code_touching_sql_fails():
    res = validate_authorization(
        TASK_TYPE_SOURCE_CODE,
        ["src/foo.py", "fix.sql"],
        pr_body="| Task type | source-code |",
    )
    assert not res.valid
    assert any("db-migration-sql" in e.lower() or "sql" in e.lower() for e in res.errors)


def test_source_code_touching_docker_fails():
    res = validate_authorization(
        TASK_TYPE_SOURCE_CODE,
        ["src/foo.py", "Dockerfile"],
        pr_body="| Task type | source-code |",
    )
    assert not res.valid


def test_docker_deploy_without_dangerous_auth_fails():
    res = validate_authorization(
        TASK_TYPE_DOCKER_DEPLOY,
        ["docker-compose.yml"],
        pr_body="| Task type | docker-deploy |",
    )
    assert not res.valid
    assert any("dangerous file authorization" in e.lower() for e in res.errors)


def test_docker_deploy_touching_src_fails():
    body = textwrap.dedent("""\
        | Task type | docker-deploy |

        ## Dangerous File Authorization

        Approved.
    """)
    res = validate_authorization(
        TASK_TYPE_DOCKER_DEPLOY,
        ["docker-compose.yml", "src/app.py"],
        pr_body=body,
    )
    assert not res.valid


def test_workflow_governance_touching_db_migration_fails():
    body = textwrap.dedent("""\
        | Task type | workflow-governance |

        ## Dangerous File Authorization

        Approved.
    """)
    res = validate_authorization(
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        [".github/workflows/ci.yml", "database/migrations/001.sql"],
        pr_body=body,
    )
    assert not res.valid
    assert any("db-migration-sql" in e.lower() for e in res.errors)


def test_unknown_task_type_fails():
    res = validate_authorization(
        TASK_TYPE_UNKNOWN,
        ["docs/readme.md"],
        pr_body="",
    )
    assert not res.valid


def test_env_secret_always_fails():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        [".env"],
        pr_body="| Task type | docs-only |",
    )
    assert not res.valid
    assert any("env" in e.lower() for e in res.errors)


def test_env_secret_fails_even_with_auth():
    body = textwrap.dedent("""\
        | Task type | config-runtime |

        ## Dangerous File Authorization

        Approved.
    """)
    res = validate_authorization(
        TASK_TYPE_CONFIG_RUNTIME,
        [".env.staging"],
        pr_body=body,
    )
    assert not res.valid


def test_model_artifact_touching_source_fails():
    body = textwrap.dedent("""\
        | Task type | model-artifact |

        ## Dangerous File Authorization

        Approved.
    """)
    res = validate_authorization(
        TASK_TYPE_MODEL_ARTIFACT,
        ["models/foo.joblib", "src/train.py"],
        pr_body=body,
    )
    assert not res.valid


def test_data_artifact_touching_source_fails():
    body = textwrap.dedent("""\
        | Task type | data-artifact |

        ## Dangerous File Authorization

        Approved.
    """)
    res = validate_authorization(
        TASK_TYPE_DATA_ARTIFACT,
        ["data/foo.csv", "src/import_data.py"],
        pr_body=body,
    )
    assert not res.valid


def test_mixed_without_dangerous_auth_fails():
    res = validate_authorization(
        TASK_TYPE_MIXED,
        ["src/foo.py", "docs/readme.md"],
        pr_body="| Task type | mixed |",
    )
    assert not res.valid
    assert any("dangerous file authorization" in e.lower() for e in res.errors)


def test_mixed_with_dangerous_auth_warns_but_does_not_error_on_categories():
    """Mixed task type warns; category checks are relaxed for mixed."""
    body = textwrap.dedent("""\
        | Task type | mixed |

        ## Dangerous File Authorization

        Mixed PR approved by team lead.
        Rollback: standard revert procedure.
    """)
    res = validate_authorization(
        TASK_TYPE_MIXED,
        ["src/foo.py", "docs/readme.md"],
        pr_body=body,
    )
    assert res.valid
    assert len(res.warnings) >= 1


# ---------------------------------------------------------------------------
# validate_authorization — edge cases
# ---------------------------------------------------------------------------


def test_validate_empty_paths():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        [],
        pr_body="| Task type | docs-only |",
    )
    assert res.valid


def test_validate_without_pr_body():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md"],
        pr_body="",
    )
    assert res.valid
    assert not res.has_dangerous_auth


def test_result_dataclass_fields():
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md"],
        pr_body="| Task type | docs-only |",
    )
    assert res.task_type == TASK_TYPE_DOCS_ONLY
    assert CATEGORY_DOCS in res.categories
    assert isinstance(res.errors, tuple)
    assert isinstance(res.warnings, tuple)
    assert isinstance(res.categories, dict)


def test_hollow_dangerous_auth_rejected():
    body = textwrap.dedent("""\
        | Task type | docker-deploy |

        ## Dangerous File Authorization

        N/A
    """)
    res = validate_authorization(
        TASK_TYPE_DOCKER_DEPLOY,
        ["docker-compose.yml"],
        pr_body=body,
    )
    assert not res.valid
    assert not res.has_dangerous_auth


def test_no_pr_body_does_not_crash():
    res = validate_authorization(TASK_TYPE_TEST_ONLY, ["tests/unit/x.py"])
    assert res.valid
    assert not res.has_dangerous_auth
    assert res.authorized_paths == frozenset()


def test_task_type_resolved_from_pr_body():
    """validate_authorization uses the explicit task_type arg, not pr_body."""
    body = textwrap.dedent("""\
        | Task type | test-only |
    """)
    res = validate_authorization(
        TASK_TYPE_DOCS_ONLY,
        ["docs/readme.md"],
        pr_body=body,
    )
    assert res.valid
    assert res.task_type == TASK_TYPE_DOCS_ONLY


# ---------------------------------------------------------------------------
# Real-world scenario tests
# ---------------------------------------------------------------------------


def test_realistic_workflow_governance_pr():
    """Simulates the actual Phase 5R8-B PR."""
    body = textwrap.dedent("""\
        ## Scope

        | Item | Value |
        |---|---|
        | Task type | workflow-governance |
        | One task / one branch / one PR | yes |

        ## Dangerous File Authorization

        This PR intentionally touches AI workflow governance helper paths:

        - `scripts/ops/helpers/pr_authorization_matrix.py`
        - `tests/unit/ops/test_pr_authorization_matrix.py`

        User authorization for Phase 5R8-B explicitly allows only
        `scripts/ops/helpers/*` and `tests/unit/*`.
    """)
    changed = [
        "scripts/ops/helpers/pr_authorization_matrix.py",
        "tests/unit/ops/test_pr_authorization_matrix.py",
    ]
    res = validate_authorization(
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        changed,
        pr_body=body,
    )
    assert res.valid
    assert res.has_dangerous_auth
    assert "scripts/ops/helpers/pr_authorization_matrix.py" in res.authorized_paths


def test_realistic_docs_only_pr():
    body = textwrap.dedent("""\
        ## Scope

        | Item | Value |
        |---|---|
        | Task type | docs-only |

        ## Summary

        Update documentation.
    """)
    changed = ["docs/readme.md", "docs/AGENT_WORKFLOW.md"]
    res = validate_authorization(TASK_TYPE_DOCS_ONLY, changed, pr_body=body)
    assert res.valid


def test_realistic_source_code_pr():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | source-code |

        ## Summary

        Fix a bug.
    """)
    changed = ["src/fix.py", "tests/unit/test_fix.py", "docs/changelog.md"]
    res = validate_authorization(TASK_TYPE_SOURCE_CODE, changed, pr_body=body)
    assert res.valid


def test_realistic_docker_deploy_pr():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | docker-deploy |

        ## Dangerous File Authorization

        Update Docker image.
        Rollback: revert.
    """)
    changed = ["deploy/docker/Dockerfile", "docker-compose.yml", "docs/deploy.md"]
    res = validate_authorization(TASK_TYPE_DOCKER_DEPLOY, changed, pr_body=body)
    assert res.valid
    assert res.has_dangerous_auth


def test_realistic_db_migration_pr():
    body = textwrap.dedent("""\
        ## Scope

        | Task type | db-migration-sql |

        ## Dangerous File Authorization

        Migration approved by DBA.
        Rollback: down migration.
    """)
    changed = ["database/migrations/002_add_index.sql", "docs/migration_notes.md"]
    res = validate_authorization(TASK_TYPE_DB_MIGRATION_SQL, changed, pr_body=body)
    assert res.valid
    assert res.has_dangerous_auth
