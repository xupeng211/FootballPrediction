"""Tests for no-generated-artifacts check — P0-2 G1 hardening.

lifecycle: test-fixture

Covers: check_added_files with hard-block and report-only patterns.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.devops.check_no_generated_artifacts import check_added_files  # noqa: E402

# ---------------------------------------------------------------------------
# Hard-block tests — these paths should be unconditionally blocked
# ---------------------------------------------------------------------------


def test_pycache_blocked():
    errors, _warnings = check_added_files(["__pycache__/foo.cpython-314.pyc"])
    assert len(errors) >= 1
    assert any("__pycache__" in e for e in errors)


def test_pyc_blocked():
    errors, _warnings = check_added_files(["module.pyc"])
    assert len(errors) >= 1


def test_pytest_cache_blocked():
    errors, _warnings = check_added_files([".pytest_cache/v/cache/nodeids"])
    assert len(errors) >= 1


def test_ruff_cache_blocked():
    errors, _warnings = check_added_files([".ruff_cache/0.14.9/somefile"])
    assert len(errors) >= 1


def test_coverage_artifacts_blocked():
    errors, _warnings = check_added_files(["htmlcov/index.html"])
    assert len(errors) >= 1


def test_dot_coverage_blocked():
    errors, _warnings = check_added_files([".coverage"])
    assert len(errors) >= 1


def test_coverage_xml_blocked():
    errors, _warnings = check_added_files(["coverage.xml"])
    assert len(errors) >= 1


def test_build_output_blocked():
    errors, _warnings = check_added_files(["dist/app.tar.gz"])
    assert len(errors) >= 1


def test_log_file_blocked():
    errors, _warnings = check_added_files(["error.log"])
    assert len(errors) >= 1


def test_tmp_file_blocked():
    errors, _warnings = check_added_files(["scratch.tmp"])
    assert len(errors) >= 1


def test_temp_file_blocked():
    errors, _warnings = check_added_files(["data/temp/output.temp"])
    assert len(errors) >= 1


def test_bak_file_blocked():
    errors, _warnings = check_added_files(["src/module.py.bak"])
    assert len(errors) >= 1


def test_ds_store_blocked():
    errors, _warnings = check_added_files([".DS_Store"])
    assert len(errors) >= 1


def test_thumbs_db_blocked():
    errors, _warnings = check_added_files(["Thumbs.db"])
    assert len(errors) >= 1


def test_tmp_dir_blocked():
    errors, _warnings = check_added_files(["tmp/some_intermediate_file.json"])
    assert len(errors) >= 1


def test_scratch_dir_blocked():
    errors, _warnings = check_added_files(["scratch/debug_output.txt"])
    assert len(errors) >= 1


def test_parquet_blocked():
    errors, _warnings = check_added_files(["data/cache.parquet"])
    assert len(errors) >= 1


def test_node_modules_blocked():
    errors, _warnings = check_added_files(["node_modules/leftpad/index.js"])
    assert len(errors) >= 1


def test_nested_pycache_blocked():
    errors, _warnings = check_added_files(["src/__pycache__/module.cpython-314.pyc"])
    assert len(errors) >= 1


# ---------------------------------------------------------------------------
# Pass tests — legitimate files
# ---------------------------------------------------------------------------


def test_normal_py_file_passes():
    errors, _warnings = check_added_files(["src/business_logic.py"])
    assert len(errors) == 0


def test_normal_js_file_passes():
    errors, _warnings = check_added_files(["scripts/ops/gatekeeper.js"])
    assert len(errors) == 0


def test_normal_json_passes():
    errors, _warnings = check_added_files(["config/settings.json"])
    assert len(errors) == 0


def test_markdown_passes():
    errors, _warnings = check_added_files(["docs/readme.md"])
    assert len(errors) == 0


def test_gitkeep_not_added():
    """gitkeep files are allowlisted but this path wouldn't match hard blocks anyway."""
    errors, _warnings = check_added_files(["data/.gitkeep"])
    assert len(errors) == 0


def test_fixture_file_passes():
    """Test fixtures should pass (they're under tests/fixtures/ which is allowlisted)."""
    errors, _warnings = check_added_files(["tests/fixtures/sample.json"])
    assert len(errors) == 0


def test_empty_added_list():
    errors, warnings = check_added_files([])
    assert len(errors) == 0
    assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Allowlist tests
# ---------------------------------------------------------------------------


def test_data_gitkeep_allowlisted():
    errors, _warnings = check_added_files(["data/.gitkeep"])
    assert not any("data/.gitkeep" in e for e in errors)


def test_tests_fixtures_allowlisted():
    errors, _warnings = check_added_files(["tests/fixtures/data/sample.json"])
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# Report-only tests — suspicious but not hard-blocked
# ---------------------------------------------------------------------------


def test_debug_file_warns():
    errors, warnings = check_added_files(["debug_output.json"])
    assert len(errors) == 0
    assert len(warnings) >= 1


def test_diagnostic_file_warns():
    errors, warnings = check_added_files(["diagnostic_findings.md"])
    assert len(errors) == 0
    assert len(warnings) >= 1


def test_temp_named_file_warns():
    errors, warnings = check_added_files(["temp_fix.py"])
    assert len(errors) == 0
    assert len(warnings) >= 1


def test_one_shot_script_warns():
    errors, warnings = check_added_files(["one_shot_migration.py"])
    assert len(errors) == 0
    assert len(warnings) >= 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_path_ignored():
    errors, _warnings = check_added_files([""])
    assert len(errors) == 0


def test_directory_path_ignored():
    errors, _warnings = check_added_files(["data/"])
    assert len(errors) == 0


def test_allowlisted_model_zoo_registry():
    errors, _warnings = check_added_files(["model_zoo/registry.md"])
    assert len(errors) == 0


def test_normal_model_zoo_model_blocked():
    """A .joblib in model_zoo is not allowlisted and would be hard-blocked by *.joblib."""
    errors, _warnings = check_added_files(["model_zoo/some_model.joblib"])
    assert len(errors) >= 1
