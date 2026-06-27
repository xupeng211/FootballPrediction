"""Tests for PR authorization matrix — path classification.

lifecycle: test-fixture

Covers: classify_path and classify_paths positive / negative / edge cases.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

from helpers.pr_authorization_matrix import (  # noqa: E402
    CATEGORY_DATA_ARTIFACT,
    CATEGORY_DB_MIGRATION_SQL,
    CATEGORY_DOCKER_DEPLOY,
    CATEGORY_DOCS,
    CATEGORY_ENV_SECRET,
    CATEGORY_MODEL_ARTIFACT,
    CATEGORY_RUNTIME_CONFIG,
    CATEGORY_SC002_DB_GOVERNANCE,
    CATEGORY_SOURCE,
    CATEGORY_TESTS,
    CATEGORY_UNKNOWN,
    CATEGORY_WORKFLOW_GOVERNANCE,
    classify_path,
    classify_paths,
)

# ---------------------------------------------------------------------------
# classify_path — docs
# ---------------------------------------------------------------------------


def test_classify_docs_md():
    cats = classify_path("docs/AGENT_WORKFLOW.md")
    assert CATEGORY_DOCS in cats
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_docs_generic():
    cats = classify_path("docs/foo.md")
    assert CATEGORY_DOCS in cats


def test_classify_readme_md():
    cats = classify_path("README.md")
    assert CATEGORY_DOCS in cats


def test_classify_agents_md():
    cats = classify_path("AGENTS.md")
    assert CATEGORY_DOCS in cats


def test_classify_claude_md():
    cats = classify_path("CLAUDE.md")
    assert CATEGORY_DOCS in cats


# ---------------------------------------------------------------------------
# classify_path — tests / source / config
# ---------------------------------------------------------------------------


def test_classify_tests():
    cats = classify_path("tests/unit/test_x.py")
    assert CATEGORY_TESTS in cats


def test_classify_tests_js():
    cats = classify_path("tests/unit/foo.test.js")
    assert CATEGORY_TESTS in cats


def test_classify_source():
    cats = classify_path("src/foo.py")
    assert CATEGORY_SOURCE in cats


def test_classify_source_deep():
    cats = classify_path("src/api/routes/predict.py")
    assert CATEGORY_SOURCE in cats


def test_classify_pyproject_toml():
    cats = classify_path("pyproject.toml")
    assert CATEGORY_RUNTIME_CONFIG in cats


def test_classify_ruff_toml():
    cats = classify_path("ruff.toml")
    assert CATEGORY_RUNTIME_CONFIG in cats


def test_classify_mypy_ini():
    cats = classify_path("mypy.ini")
    assert CATEGORY_RUNTIME_CONFIG in cats


def test_classify_config_dir():
    cats = classify_path("config/settings.py")
    assert CATEGORY_RUNTIME_CONFIG in cats


# ---------------------------------------------------------------------------
# classify_path — docker-deploy
# ---------------------------------------------------------------------------


def test_classify_dockerfile():
    cats = classify_path("Dockerfile")
    assert CATEGORY_DOCKER_DEPLOY in cats


def test_classify_docker_compose():
    cats = classify_path("docker-compose.yml")
    assert CATEGORY_DOCKER_DEPLOY in cats


def test_classify_docker_compose_yaml():
    cats = classify_path("docker-compose.dev.yaml")
    assert CATEGORY_DOCKER_DEPLOY in cats


def test_classify_devcontainer():
    cats = classify_path(".devcontainer/Dockerfile")
    assert CATEGORY_DOCKER_DEPLOY in cats


def test_classify_deploy_docker():
    cats = classify_path("deploy/docker/Dockerfile")
    assert CATEGORY_DOCKER_DEPLOY in cats


# ---------------------------------------------------------------------------
# classify_path — workflow-governance
# ---------------------------------------------------------------------------


def test_classify_github_workflow():
    cats = classify_path(".github/workflows/production-gate.yml")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_codeowners():
    cats = classify_path(".github/CODEOWNERS")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_pr_template():
    cats = classify_path(".github/pull_request_template.md")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_ai_workflow_gate():
    cats = classify_path("scripts/ops/ai_workflow_gate.py")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_helper():
    cats = classify_path("scripts/ops/helpers/pr_authorization_matrix.py")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_devops():
    cats = classify_path("scripts/devops/deploy.sh")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_gate_script():
    cats = classify_path("scripts/ops/my_gate.py")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


def test_classify_agent_workflow_docs():
    cats = classify_path("docs/AGENT_WORKFLOW.md")
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats


# ---------------------------------------------------------------------------
# classify_path — db-migration-sql / sc-002 / model / data / env
# ---------------------------------------------------------------------------


def test_classify_db_migration_sql():
    cats = classify_path("database/migrations/001.sql")
    assert CATEGORY_DB_MIGRATION_SQL in cats


def test_classify_alembic():
    cats = classify_path("alembic/versions/abc123.py")
    assert CATEGORY_DB_MIGRATION_SQL in cats


def test_classify_src_migration():
    cats = classify_path("src/database/migrations/002.sql")
    assert CATEGORY_DB_MIGRATION_SQL in cats


def test_classify_raw_sql():
    cats = classify_path("scripts/fix.sql")
    assert CATEGORY_DB_MIGRATION_SQL in cats


def test_classify_deploy_init_sql():
    cats = classify_path("deploy/docker/init_db.sql")
    assert CATEGORY_DB_MIGRATION_SQL in cats
    assert CATEGORY_DOCKER_DEPLOY in cats


def test_classify_sc002_script():
    cats = classify_path("scripts/ops/sc002_check.py")
    assert CATEGORY_SC002_DB_GOVERNANCE in cats


def test_classify_sc002_dash():
    cats = classify_path("scripts/ops/SC-002-guard.py")
    assert CATEGORY_SC002_DB_GOVERNANCE in cats


def test_classify_db_write_guard_helper():
    cats = classify_path("scripts/ops/helpers/db_write_guard.py")
    assert CATEGORY_SC002_DB_GOVERNANCE in cats


def test_classify_db_write_guard_ops():
    cats = classify_path("scripts/ops/db_write_guard.py")
    assert CATEGORY_SC002_DB_GOVERNANCE in cats


def test_classify_allowlist():
    cats = classify_path("config/python_db_write_allowlist.json")
    assert CATEGORY_SC002_DB_GOVERNANCE in cats


def test_classify_model_joblib():
    cats = classify_path("models/foo.joblib")
    assert CATEGORY_MODEL_ARTIFACT in cats


def test_classify_model_pkl():
    cats = classify_path("model_zoo/bar.pkl")
    assert CATEGORY_MODEL_ARTIFACT in cats


def test_classify_pkl_at_root():
    cats = classify_path("predictor.pkl")
    assert CATEGORY_MODEL_ARTIFACT in cats


def test_classify_data_csv():
    cats = classify_path("data/foo.csv")
    assert CATEGORY_DATA_ARTIFACT in cats


def test_classify_artifacts():
    cats = classify_path("artifacts/bar.json")
    assert CATEGORY_DATA_ARTIFACT in cats


def test_classify_env_file():
    cats = classify_path(".env")
    assert CATEGORY_ENV_SECRET in cats


def test_classify_env_staging():
    cats = classify_path(".env.staging")
    assert CATEGORY_ENV_SECRET in cats


# ---------------------------------------------------------------------------
# classify_path — unknown
# ---------------------------------------------------------------------------


def test_classify_unknown():
    cats = classify_path("some_random_dir/file.txt")
    assert cats == {CATEGORY_UNKNOWN}


def test_classify_path_multiple_categories():
    """A single path can match multiple categories."""
    cats = classify_path("docs/AGENT_WORKFLOW.md")
    assert CATEGORY_DOCS in cats
    assert CATEGORY_WORKFLOW_GOVERNANCE in cats
    assert len(cats) >= 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# classify_paths — aggregation
# ---------------------------------------------------------------------------


def test_classify_paths_aggregates():
    paths = {
        "docs/readme.md",
        "tests/unit/x.py",
        "src/foo.py",
        "Dockerfile",
    }
    result = classify_paths(paths)
    assert CATEGORY_DOCS in result
    assert CATEGORY_TESTS in result
    assert CATEGORY_SOURCE in result
    assert CATEGORY_DOCKER_DEPLOY in result
    assert "docs/readme.md" in result[CATEGORY_DOCS]
    assert "tests/unit/x.py" in result[CATEGORY_TESTS]
    assert "src/foo.py" in result[CATEGORY_SOURCE]
    assert "Dockerfile" in result[CATEGORY_DOCKER_DEPLOY]


def test_classify_paths_unknown():
    result = classify_paths(["weird/path.xyz"])
    assert CATEGORY_UNKNOWN in result
    assert "weird/path.xyz" in result[CATEGORY_UNKNOWN]


def test_classify_paths_empty():
    result = classify_paths([])
    assert result == {}
