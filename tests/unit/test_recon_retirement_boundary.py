"""Retired probe discovery regressions; active DB/SQL signals stay enforced.

lifecycle: permanent
"""

from pathlib import Path

from scripts.ops import python_db_write_static_enforcement as py
from scripts.ops import sql_migration_policy_static_enforcement as sql

RETIRED_ROOT = "archive/recon_v2_research"


def test_scanners_prune_retired_probes_and_preserve_active_findings(tmp_path, monkeypatch):
    """Prune before traversal, without masking adjacent or maintained source."""
    for directory in (RETIRED_ROOT, "archive/recon_v2_research_active", "src"):
        root = tmp_path / directory
        root.mkdir(parents=True)
        # Discovery needs only a DB-client signal; write-risk behavior is covered
        # by the maintained phase2a regressions. Never execute these fixtures.
        (root / "write.py").write_text("import psycopg2\n")
        (root / "schema.sql").write_text("CREATE TABLE matches (match_id text);\n")
    monkeypatch.setattr(py, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sql, "REPO_ROOT", tmp_path)
    original = py.os.scandir
    visited = []

    def tracked_scandir(target):
        visited.append(Path(target).relative_to(tmp_path).as_posix())
        return original(target)

    monkeypatch.setattr(py.os, "scandir", tracked_scandir)
    python_results = py.scan_repository()
    sql_results = sql.scan_repo()
    assert RETIRED_ROOT not in visited
    assert sorted(row["path"] for row in python_results) == [
        "archive/recon_v2_research_active/write.py",
        "src/write.py",
    ]
    assert all(row["db_client_signals"] for row in python_results)
    assert sorted(row["path"] for row in sql_results) == [
        "archive/recon_v2_research_active/schema.sql",
        "src/schema.sql",
    ]
    assert all(row["ddl_signals"] for row in sql_results)
