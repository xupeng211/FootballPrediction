#!/usr/bin/env python3
"""
TECHDEBT-L3G Warning-Only Changed-File Classifier.

Reads a list of changed files (from --changed-files-file or git diff via
--base-ref/--head-ref) and classifies each file by its L3 entrypoint label.

This script is warning-only: it always exits 0. It does not block CI,
does not authorize or reject changes, does not implement hard enforcement.

Classification rules are based on:
  - L3B Active Entrypoint Whitelist
  - L3C Label Semantics
  - L3E Unknown Entrypoint Owner Decisions
  - L3F Enforcement Design Proposal

Lifecycle: L3G active CI governance script (warning-only).
"""

import argparse
from collections import Counter
import fnmatch
from pathlib import Path
import subprocess
import sys

# ---------------------------------------------------------------------------
# Label constants
# ---------------------------------------------------------------------------

LABEL_L3_DOCS = "l3-docs"
LABEL_DOCUMENTATION = "documentation"
LABEL_ACTIVE_RUNTIME = "active-runtime"
LABEL_ACTIVE_API_ROUTER = "active-api-router"
LABEL_ACTIVE_GOVERNANCE = "active-governance"
LABEL_OPERATIONAL_GUARDED = "operational-guarded"
LABEL_RESTRICTED_LEGACY = "restricted-legacy"
LABEL_ARCHIVE_READ_ONLY = "archive-read-only"
LABEL_TEST_ONLY = "test-only"
LABEL_CODEOWNERS_SENSITIVE = "codeowners-sensitive"
LABEL_GITHUB_WORKFLOW_SENSITIVE = "github-workflow-sensitive"
LABEL_GATE_SENSITIVE = "gate-sensitive"
LABEL_DOCKER_SENSITIVE = "docker-sensitive"
LABEL_DB_MIGRATION_SENSITIVE = "db-migration-sensitive"
LABEL_SCRAPER_TRAINING_SENSITIVE = "scraper-training-sensitive"
LABEL_HIGH_RISK = "high-risk"
LABEL_UNCLASSIFIED = "unclassified-path"

# ---------------------------------------------------------------------------
# Classification rule definitions
# ---------------------------------------------------------------------------

# Active runtime — sole production API entrypoint
ACTIVE_RUNTIME_PATHS: list[str] = [
    "src/main.py",
]

# Active API routers — mounted by src/main.py
ACTIVE_API_ROUTER_PATHS: list[str] = [
    "src/api/health.py",
    "src/api/monitoring.py",
    "src/api/model_management.py",
    "src/api/v1/endpoints/admin.py",
]

# Active governance / CI entrypoints (L3B whitelist)
ACTIVE_GOVERNANCE_PATHS: list[str] = [
    "scripts/devops/gatekeeper.sh",
    "scripts/ops/ai_workflow_gate.py",
    "scripts/devops/check_python_ast_utf8.py",
    "scripts/devops/static_quality_changed_lines.py",
    "scripts/ops/local_pr_gate_preflight.py",
    "scripts/devops/pr_body_check.py",
    "scripts/devops/pr_merge_preflight.py",
    "scripts/devops/pr_post_merge_check.py",
    "scripts/devops/install_git_hooks.sh",
    "scripts/devops/init_dev.sh",
    "scripts/ops/helpers/",
]

# Restricted legacy entrypoints (L3B whitelist §Restricted Legacy + L3E decisions)
RESTRICTED_LEGACY_PATH_PATTERNS: list[str] = [
    # L3B restricted legacy (18 entries)
    "scripts/ops/run_production.js",
    "scripts/ops/titan_discovery.js",
    "scripts/ops/total_war_pipeline.js",
    "scripts/ops/batch_historical_backfill.js",
    "scripts/ops/odds_harvest_pipeline.js",
    "scripts/ops/train_model.py",
    "scripts/ops/predict_pipeline.py",
    "scripts/ops/smelt_all.js",
    "scripts/ops/l3_stitch_pipeline.js",
    "scripts/ops/odds_sniper.js",
    "scripts/ops/seed_fixtures.js",
    "scripts/ops/local_dom_ingestor.js",
    "scripts/ops/csv_bulk_loader.js",
    "scripts/ops/fetch_and_adapt_euro_leagues.js",
    "src/api/predictions/predict_router.py",
    "src/ml/**",
    "src/services/**",
    "scripts/maintenance/**",
    # L3E owner decisions: restricted-legacy
    "scripts/ops/fotmob_*.py",
    "scripts/ops/check_health.js",
    "scripts/ops/sentinel_watch.js",
    "scripts/ops/audit_dataset.js",
    "scripts/maintenance/integrity_guard.sh",
]

# High-risk paths (require special attention)
HIGH_RISK_PATHS: list[str] = [
    "scripts/ops/sentinel_watch.js",
]

# Test-only paths
TEST_ONLY_PATTERNS: list[str] = [
    "tests/**",
    "scripts/test/run_test_suite.js",
]

# Archive read-only paths
ARCHIVE_READ_ONLY_PATTERNS: list[str] = [
    "archive_vault_2026/**",
    "tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**",
]

# L3 governance docs
L3_DOCS_PATTERNS: list[str] = [
    "docs/techdebt/L3_*",
    "docs/techdebt/L3*.md",
    "docs/_reports/L3*",
]

# General documentation
DOCUMENTATION_PATTERNS: list[str] = [
    "docs/**",
    "*.md",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "AGENTS.md",
    "CLAUDE.md",
]

# GitHub workflow sensitive
GITHUB_WORKFLOW_PATTERNS: list[str] = [
    ".github/**",
]

# Gate-sensitive paths (gate infrastructure)
GATE_SENSITIVE_PATHS: list[str] = [
    "scripts/devops/gatekeeper.sh",
    "scripts/ops/ai_workflow_gate.py",
    "scripts/ops/helpers/",
]

# CODEOWNERS sensitive
CODEOWNERS_PATHS: list[str] = [
    "CODEOWNERS",
    ".github/CODEOWNERS",
    "docs/CODEOWNERS",
]

# Docker sensitive
DOCKER_SENSITIVE_PATTERNS: list[str] = [
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose*.yml",
    "docker-compose*.yaml",
    ".devcontainer/**",
    ".dockerignore",
]

# DB / migration sensitive
DB_MIGRATION_SENSITIVE_PATTERNS: list[str] = [
    "alembic/**",
    "alembic.ini",
    "migrations/**",
    "db/**",
]

# Scraper / training / pipeline sensitive
SCRAPER_TRAINING_SENSITIVE_PATTERNS: list[str] = [
    "scripts/scraper/**",
    "scripts/training/**",
    "scripts/pipeline/**",
    "scripts/data/**",
    "scripts/etl/**",
    "scripts/ops/fotmob_*.py",
    "scripts/ops/train_model.py",
    "scripts/ops/predict_pipeline.py",
    "scripts/ops/batch_historical_backfill.js",
    "scripts/ops/odds_harvest_pipeline.js",
    "scripts/ops/seed_fixtures.js",
    "scripts/ops/fetch_and_adapt_euro_leagues.js",
    "scripts/ops/odds_sniper.js",
    "scripts/ops/local_dom_ingestor.js",
    "scripts/ops/csv_bulk_loader.js",
]

# Source runtime paths
SOURCE_RUNTIME_PATTERNS: list[str] = [
    "src/**",
]

# Source modules with __main__ blocks (L3E Decision 7)
SOURCE_MAIN_NOTE_PATTERNS: list[str] = [
    "src/core/environment_detector.py",
    "src/core/environment_validator.py",
    "src/core/path_manager.py",
    "src/utils/types.py",
    "src/utils/safe_eval.py",
    "src/utils/typed_matcher.py",
    "src/utils/notifier.py",
    "src/schemas/team_alias.py",
    "src/schemas/match_features.py",
]


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------


def _match_glob(path: str, pattern: str) -> bool:
    """Match a path against a glob pattern.

    Handles:
      - Exact path match: "src/main.py"
      - Glob patterns: "scripts/ops/fotmob_*.py"
      - Directory patterns: "scripts/maintenance/**"
      - Recursive patterns: "src/**"
    """
    # Exact match
    if path == pattern:
        return True

    # Glob match
    if fnmatch.fnmatch(path, pattern):
        return True

    # Prefix match for directory patterns (e.g., "scripts/maintenance/" matches
    # all files under it)
    if pattern.endswith("/") and path.startswith(pattern):
        return True

    # Pattern "foo/**" matches "foo/bar" and "foo/bar/baz"
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        if path.startswith(prefix):
            return True

    return False


def _match_any(path: str, patterns: list[str]) -> bool:
    """Return True if path matches any pattern in the list."""
    return any(_match_glob(path, p) for p in patterns)


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------


def classify_path(path: str) -> list[str]:  # noqa: C901, PLR0911, PLR0912
    """Classify a single changed file path and return its L3 labels.

    Returns a list of labels. Most paths get one primary label plus
    optionally secondary labels (e.g., restricted-legacy + high-risk).
    """
    labels: list[str] = []

    # --- Primary classification (ordered by specificity) ---

    # 1. L3 governance docs
    if _match_any(path, L3_DOCS_PATTERNS):
        labels.append(LABEL_L3_DOCS)
        return labels  # L3 docs are their own category, don't mix

    # 2. CODEOWNERS (exact, before .github patterns)
    if _match_any(path, CODEOWNERS_PATHS):
        labels.append(LABEL_CODEOWNERS_SENSITIVE)
        # CODEOWNERS is also github-workflow-sensitive
        if LABEL_GITHUB_WORKFLOW_SENSITIVE not in labels:
            labels.append(LABEL_GITHUB_WORKFLOW_SENSITIVE)
        return labels

    # 3. Restricted legacy (most specific, including L3E decisions)
    if _match_any(path, RESTRICTED_LEGACY_PATH_PATTERNS):
        labels.append(LABEL_RESTRICTED_LEGACY)
        # Add high-risk if applicable
        if _match_any(path, HIGH_RISK_PATHS):
            labels.append(LABEL_HIGH_RISK)
        # Add scraper/training if applicable
        if _match_any(path, SCRAPER_TRAINING_SENSITIVE_PATTERNS):
            labels.append(LABEL_SCRAPER_TRAINING_SENSITIVE)
        return labels

    # 4. Archive read-only
    if _match_any(path, ARCHIVE_READ_ONLY_PATTERNS):
        labels.append(LABEL_ARCHIVE_READ_ONLY)
        return labels

    # 5. Test-only
    if _match_any(path, TEST_ONLY_PATTERNS):
        labels.append(LABEL_TEST_ONLY)
        return labels

    # 6. Gate sensitive (specific gate infrastructure)
    if _match_any(path, GATE_SENSITIVE_PATHS):
        labels.append(LABEL_ACTIVE_GOVERNANCE)
        labels.append(LABEL_GATE_SENSITIVE)
        return labels

    # 7. GitHub workflow sensitive
    if _match_any(path, GITHUB_WORKFLOW_PATTERNS):
        labels.append(LABEL_GITHUB_WORKFLOW_SENSITIVE)
        # Check if also governance
        if _match_any(path, ACTIVE_GOVERNANCE_PATHS):
            labels.append(LABEL_ACTIVE_GOVERNANCE)
        return labels

    # 8. Active governance (exact or prefix match)
    if _match_any(path, ACTIVE_GOVERNANCE_PATHS):
        labels.append(LABEL_ACTIVE_GOVERNANCE)
        return labels

    # 9. Docker sensitive
    if _match_any(path, DOCKER_SENSITIVE_PATTERNS):
        labels.append(LABEL_DOCKER_SENSITIVE)
        return labels

    # 10. DB / migration sensitive
    if _match_any(path, DB_MIGRATION_SENSITIVE_PATTERNS):
        labels.append(LABEL_DB_MIGRATION_SENSITIVE)
        return labels

    # 11. Active API router
    if _match_any(path, ACTIVE_API_ROUTER_PATHS):
        labels.append(LABEL_ACTIVE_API_ROUTER)
        return labels

    # 12. Active runtime
    if _match_any(path, ACTIVE_RUNTIME_PATHS):
        labels.append(LABEL_ACTIVE_RUNTIME)
        # Check if it has __main__ note
        if _match_any(path, SOURCE_MAIN_NOTE_PATTERNS):
            pass  # Note handled in attention rendering
        return labels

    # 13. Documentation (broad catch-all for docs/)
    if _match_any(path, DOCUMENTATION_PATTERNS):
        labels.append(LABEL_DOCUMENTATION)
        return labels

    # 14. Source runtime (default for src/**)
    if _match_any(path, SOURCE_RUNTIME_PATTERNS):
        labels.append(LABEL_ACTIVE_RUNTIME)
        if _match_any(path, SOURCE_MAIN_NOTE_PATTERNS):
            pass  # __main__ note handled separately
        return labels

    # 15. Scraper/training sensitive (check after more specific patterns)
    if _match_any(path, SCRAPER_TRAINING_SENSITIVE_PATTERNS):
        labels.append(LABEL_SCRAPER_TRAINING_SENSITIVE)
        return labels

    # 16. Unclassified
    labels.append(LABEL_UNCLASSIFIED)
    return labels


# ---------------------------------------------------------------------------
# Attention notes
# ---------------------------------------------------------------------------


def _is_deletion(status: str) -> bool:
    return status == "D"


def _is_rename(status: str) -> bool:
    return status.startswith("R")


def attention_notes(  # noqa: C901, PLR0912
    path: str,
    status: str,
    labels: list[str],
) -> list[str]:
    """Generate attention notes for a classified path."""
    notes: list[str] = []

    if _is_deletion(status):
        notes.append("DELETION DETECTED — requires dedicated PR authorization")

    if _is_rename(status):
        notes.append("RENAME/MOVE DETECTED — requires dedicated PR authorization")

    if LABEL_HIGH_RISK in labels:
        notes.append(
            "HIGH-RISK: sentinel_watch.js — automated shutdown capability; "
            "requires explicit operational authorization + shutdown "
            "risk acknowledgement"
        )

    if LABEL_RESTRICTED_LEGACY in labels:
        notes.append(
            "restricted-legacy: read-only by default; modification, "
            "execution, or deletion requires explicit user authorization"
        )

    if LABEL_ARCHIVE_READ_ONLY in labels:
        notes.append(
            "archive-read-only: historical reference; modification requires dedicated archive authorization"
        )

    if LABEL_CODEOWNERS_SENSITIVE in labels:
        notes.append(
            "CODEOWNERS touched — requires separate authorization; do not create or modify without explicit approval"
        )

    if LABEL_GATE_SENSITIVE in labels:
        notes.append(
            "Gate infrastructure touched — Gatekeeper or AI Workflow "
            "Gate; changes require explicit governance authorization"
        )

    if LABEL_GITHUB_WORKFLOW_SENSITIVE in labels:
        notes.append(".github/workflow touched — CI behavior may change; review workflow impact carefully")

    if LABEL_DOCKER_SENSITIVE in labels:
        notes.append(
            "Docker/build touched — may affect container builds; validate Docker Build Validation still passes"
        )

    if LABEL_DB_MIGRATION_SENSITIVE in labels:
        notes.append(
            "DB/migration touched — schema changes may be involved; "
            "do not run migrations without explicit authorization"
        )

    if LABEL_SCRAPER_TRAINING_SENSITIVE in labels:
        notes.append(
            "scraper/training/pipeline touched — data ingestion or "
            "model training surface; requires explicit authorization"
        )

    if LABEL_UNCLASSIFIED in labels:
        notes.append(
            "UNCLASSIFIED: path not in L3 taxonomy; manual review required to determine entrypoint classification"
        )

    # __main__ note for source modules
    if _match_any(path, SOURCE_MAIN_NOTE_PATTERNS):
        notes.append(
            "source module with __main__ self-test block; standalone execution is test-only, not production"
        )

    return notes


# ---------------------------------------------------------------------------
# File list parsing
# ---------------------------------------------------------------------------


def parse_changed_files_file(filepath: str) -> list[tuple[str, str]]:
    """Parse a changed-files file.

    Supports two formats:
      1. Path only (one per line)
      2. git diff --name-status format:
         M    path
         A    path
         D    path
         R100 old_path  new_path

    Returns list of (status, path) tuples. Status defaults to 'M' for
    path-only format.
    """
    entries: list[tuple[str, str]] = []
    with Path(filepath).open(encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # git diff --name-status format: <status> <path> [old_path]
            parts = line.split(None, 1)
            if len(parts) >= 2 and parts[0] in (  # noqa: PLR2004
                "M",
                "A",
                "D",
                "R",
                "C",
                "T",
                "U",
                "X",
                "R100",
                "R050",
                "R075",
                "R090",
                "R095",
                "R099",
                "R100",
            ):
                status = parts[0]
                rest = parts[1]
                # For renames: "R100 old.py new.py" — take new path
                if status.startswith("R"):
                    rename_parts = rest.split()
                    path = rename_parts[-1] if len(rename_parts) >= 2 else rest  # noqa: PLR2004
                else:
                    path = rest.strip()
                entries.append((status, path))
            elif len(parts) == 1:
                # Path only
                entries.append(("M", parts[0]))
            else:
                # Try as path only (line may contain spaces in path)
                entries.append(("M", line))

    return entries


def get_changed_files_from_git(
    repo_root: str,
    base_ref: str,
    head_ref: str,
) -> list[tuple[str, str]]:
    """Get changed files from git diff between two refs.

    Uses git diff --name-status to get file list with status.
    """
    cmd = [
        "git",
        "-C",
        repo_root,
        "diff",
        "--name-status",
        "--diff-filter=AMDRCT",
        base_ref,
        head_ref,
    ]
    try:
        result = subprocess.run(  # noqa: PLW1510
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"[L3-ENFORCEMENT] WARNING: git diff failed: {exc}", file=sys.stderr)
        return []

    if result.returncode != 0:
        print(
            f"[L3-ENFORCEMENT] WARNING: git diff returned {result.returncode}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return []

    entries: list[tuple[str, str]] = []
    raw_lines = result.stdout.strip().split("\n")
    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) >= 2:  # noqa: PLR2004
            status = parts[0]
            # For renames, format is: R100\told.py\tnew.py
            if status.startswith("R") and "\t" in parts[1]:
                rename_parts = parts[1].split("\t")
                path = rename_parts[-1] if len(rename_parts) >= 2 else parts[1]  # noqa: PLR2004
            else:
                path = parts[1]
            entries.append((status, path))
        else:
            entries.append(("M", line))

    return entries


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------


def render_output(  # noqa: C901, PLR0912, PLR0915
    entries: list[tuple[str, str]],
    _repo_root: str,
) -> str:
    """Render the full classifier output."""
    lines: list[str] = []

    lines.append("=" * 72)
    lines.append("TECHDEBT-L3G warning-only changed-file classifier")
    lines.append("=" * 72)
    lines.append("")
    lines.append("This step is warning-only and does not block CI.")
    lines.append("This classifier does not authorize or reject changes.")
    lines.append("It does not modify Gatekeeper, AI Workflow Gate, or CODEOWNERS.")
    lines.append("")

    if not entries:
        lines.append("No changed files detected.")
        lines.append("")
        lines.append("Summary: 0 changed files. Nothing to classify.")
        return "\n".join(lines)

    # Classify each entry
    classified: list[dict] = []
    label_counts: Counter = Counter()
    deletion_count = 0
    rename_count = 0
    restricted_legacy_count = 0
    high_risk_count = 0
    unclassified_count = 0
    codeowners_touched = False
    github_touched = False
    gate_touched = False
    docker_touched = False
    db_migration_touched = False
    scraper_training_touched = False
    archive_touched = False

    for status, path in entries:
        labels = classify_path(path)
        notes = attention_notes(path, status, labels)
        classified.append(
            {
                "status": status,
                "path": path,
                "labels": labels,
                "notes": notes,
            }
        )

        for lbl in labels:
            label_counts[lbl] += 1

        if _is_deletion(status):
            deletion_count += 1
        if _is_rename(status):
            rename_count += 1
        if LABEL_RESTRICTED_LEGACY in labels:
            restricted_legacy_count += 1
        if LABEL_HIGH_RISK in labels:
            high_risk_count += 1
        if LABEL_UNCLASSIFIED in labels:
            unclassified_count += 1
        if LABEL_CODEOWNERS_SENSITIVE in labels:
            codeowners_touched = True
        if LABEL_GITHUB_WORKFLOW_SENSITIVE in labels:
            github_touched = True
        if LABEL_GATE_SENSITIVE in labels:
            gate_touched = True
        if LABEL_DOCKER_SENSITIVE in labels:
            docker_touched = True
        if LABEL_DB_MIGRATION_SENSITIVE in labels:
            db_migration_touched = True
        if LABEL_SCRAPER_TRAINING_SENSITIVE in labels:
            scraper_training_touched = True
        if LABEL_ARCHIVE_READ_ONLY in labels:
            archive_touched = True

    # --- Summary ---
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Changed file count: {len(entries)}")
    lines.append(f"- Labels touched: {', '.join(sorted(label_counts.keys())) if label_counts else 'none'}")
    lines.append("")

    attention_items: list[str] = []
    if deletion_count:
        attention_items.append(f"{deletion_count} deletion(s) detected")
    if rename_count:
        attention_items.append(f"{rename_count} rename/move(s) detected")
    if restricted_legacy_count:
        attention_items.append(f"{restricted_legacy_count} restricted-legacy path(s) touched")
    if high_risk_count:
        attention_items.append(f"{high_risk_count} high-risk path(s) touched — sentinel_watch.js")
    if unclassified_count:
        attention_items.append(f"{unclassified_count} unclassified path(s) — manual review required")
    if codeowners_touched:
        attention_items.append("CODEOWNERS touched")
    if github_touched:
        attention_items.append(".github/workflow touched")
    if gate_touched:
        attention_items.append("Gate (Gatekeeper / AI Workflow Gate) path touched")
    if docker_touched:
        attention_items.append("Docker/build path touched")
    if db_migration_touched:
        attention_items.append("DB/migration path touched")
    if scraper_training_touched:
        attention_items.append("scraper/training/pipeline path touched")
    if archive_touched:
        attention_items.append("archive-read-only path touched")

    if attention_items:
        lines.append(f"- Attention needed: {len(attention_items)} item(s)")
        lines.extend(f"  - {item}" for item in attention_items)
    else:
        lines.append("- Attention needed: 0 items")

    lines.append(f"- High-risk paths: {high_risk_count}")
    lines.append(f"- Deletion/move/rename count: {deletion_count + rename_count}")
    lines.append(f"- Restricted legacy touched: {'yes' if restricted_legacy_count else 'no'}")
    lines.append(f"- Unknown/unclassified touched: {'yes' if unclassified_count else 'no'}")
    lines.append("")

    # --- Markdown table ---
    lines.append("## Changed File Classification")
    lines.append("")
    lines.append("| Status | Path | Labels | Attention |")
    lines.append("|---|---|---|---|")

    for entry in classified:
        status = entry["status"]
        path = entry["path"]
        labels_str = ", ".join(entry["labels"])
        notes_str = "; ".join(entry["notes"]) if entry["notes"] else "—"
        lines.append(f"| {status} | `{path}` | {labels_str} | {notes_str} |")

    lines.append("")

    # --- Non-enforcement footer ---
    lines.append("---")
    lines.append("")
    lines.append("[L3-ENFORCEMENT][Layer-2][WARNING-ONLY]")
    lines.append("This classifier does not block CI.")
    lines.append("It does not decide ownership, authorization, or merge eligibility.")
    lines.append("Any future blocking behavior requires separate explicit authorization.")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="TECHDEBT-L3G warning-only changed-file classifier",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root directory (default: .)",
    )
    parser.add_argument(
        "--base-ref",
        default=None,
        help="Base git ref for diff (e.g., origin/main)",
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Head git ref for diff (default: HEAD)",
    )
    parser.add_argument(
        "--changed-files-file",
        default=None,
        help="File containing changed file paths (path-only or git diff --name-status format)",
    )
    return parser


def main() -> None:
    """Run the L3G warning-only changed-file classifier from CLI."""
    parser = build_parser()
    args = parser.parse_args()

    repo_root = str(Path(args.repo_root).resolve())

    if args.changed_files_file:
        entries = parse_changed_files_file(args.changed_files_file)
    elif args.base_ref:
        entries = get_changed_files_from_git(
            repo_root,
            args.base_ref,
            args.head_ref,
        )
    else:
        # Default: diff against origin/main if available
        base = "origin/main"
        entries = get_changed_files_from_git(repo_root, base, args.head_ref)

    output = render_output(entries, repo_root)
    print(output)

    # Always exit 0 — warning-only
    sys.exit(0)


if __name__ == "__main__":
    main()
