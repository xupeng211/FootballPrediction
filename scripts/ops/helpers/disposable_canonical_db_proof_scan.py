"""Marker-bound SQL scan exemption for the M3 disposable canonical proof.

lifecycle: permanent

The AI workflow gate normally blocks new write SQL in ``tests/``. Two exact
integration-proof files intentionally exercise task-labelled disposable
PostgreSQL write paths. This helper exempts only their DB-keyword scan when
the source marker is present; all other dangerous scanners still apply.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    import re

from scripts.ops.helpers.git_change_helpers import (
    Change,
    IncrementalScanResult,
    IncrementalScanSummary,
    scan_incremental_findings,
)

ROOT = Path(__file__).resolve().parents[3]

DISPOSABLE_DB_WRITE_PROOF_PATHS: frozenset[str] = frozenset(
    {
        "tests/integration/canonical_inventory/canonicalMigrationHarness.js",
        "tests/integration/canonical_inventory/disposable_postgres.test.js",
    }
)
DISPOSABLE_DB_WRITE_PROOF_MARKER = "M3_CANONICAL_DISPOSABLE_DB_WRITE_PROOF_V1"


def is_explicit_disposable_db_write_proof(path: str) -> bool:
    """Return whether *path* is an exact, marker-bound synthetic proof file."""
    if path not in DISPOSABLE_DB_WRITE_PROOF_PATHS:
        return False
    try:
        return DISPOSABLE_DB_WRITE_PROOF_MARKER in (ROOT / path).read_text(encoding="utf-8")
    except OSError:
        return False


def scan_with_disposable_db_proof_exemption(
    changes: list[Change],
    *,
    path_predicate: Callable[[str], bool],
    pattern_groups: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...],
    base_ref: str | None,
    head_ref: str | None,
    error_prefix: str,
) -> IncrementalScanResult:
    """Scan all rules while exempting only marked proof files from DB keywords."""
    non_db_groups = tuple(group for group in pattern_groups if group[0] != "DB write")
    non_db = scan_incremental_findings(
        changes,
        path_predicate=path_predicate,
        pattern_groups=non_db_groups,
        base_ref=base_ref,
        head_ref=head_ref,
        error_prefix=error_prefix,
    )
    db_only = scan_incremental_findings(
        changes,
        path_predicate=lambda path: path_predicate(path)
        and not is_explicit_disposable_db_write_proof(path),
        pattern_groups=tuple(group for group in pattern_groups if group[0] == "DB write"),
        base_ref=base_ref,
        head_ref=head_ref,
        error_prefix=error_prefix,
    )
    return IncrementalScanResult(
        errors=(*non_db.errors, *db_only.errors),
        summary=IncrementalScanSummary(
            base_ref=non_db.summary.base_ref,
            head_ref=non_db.summary.head_ref,
            scanned_files=non_db.summary.scanned_files + db_only.summary.scanned_files,
            base_violations=non_db.summary.base_violations + db_only.summary.base_violations,
            head_violations=non_db.summary.head_violations + db_only.summary.head_violations,
            new_violations=non_db.summary.new_violations + db_only.summary.new_violations,
            removed_violations=non_db.summary.removed_violations
            + db_only.summary.removed_violations,
            unchanged_historical_violations=(
                non_db.summary.unchanged_historical_violations
                + db_only.summary.unchanged_historical_violations
            ),
        ),
    )
