#!/usr/bin/env python3
"""Block newly-added generated artifacts, temp files, cache, logs, and build outputs.

lifecycle: permanent

Detects generated/transient files that AI agents may accidentally commit:
- cache directories (__pycache__, .pytest_cache, .mypy_cache, .ruff_cache)
- compiled outputs (*.pyc, dist/, build/)
- coverage artifacts (.coverage, coverage.xml, htmlcov/)
- log and temp files (*.log, *.tmp, *.temp)
- backup/editor artifacts (*.bak, *.old, *.orig, *.rej, .DS_Store, Thumbs.db)
- explicit garbage directories (tmp/, temp/, scratch/, generated/, artifacts/)
- large binaries that should be in .gitignore (*.parquet, *.tar.gz, *.zip, etc.)

Only checks newly-added (status A) files to avoid false positives from
pre-existing tracked files.  Deleted garbage files are not flagged.

Usage:
    python scripts/devops/check_no_generated_artifacts.py --added added_paths.txt
    python scripts/devops/check_no_generated_artifacts.py --paths \\
        htmlcov/index.html data/tmp/cache.parquet
"""

from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path, PurePath
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# ---------------------------------------------------------------------------
# Hard-block patterns — newly-added files matching these are unconditionally blocked.
#
# Two types of checks:
# 1. FORBIDDEN_EXTENSIONS: file extension matches — blocked regardless of location
# 2. FORBIDDEN_DIR_NAMES: any path component matches — blocked regardless of extension
# 3. FORBIDDEN_PATH_PREFIXES: path starts with prefix — blocked
# ---------------------------------------------------------------------------
FORBIDDEN_EXTENSIONS: frozenset[str] = frozenset({
    ".pyc",
    ".pyo",
    ".log",
    ".tmp",
    ".temp",
    ".swp",
    ".swo",
    ".bak",
    ".old",
    ".orig",
    ".rej",
    ".parquet",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".zip",
    ".7z",
    ".rar",
    ".bundle",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".onnx",
    ".ipynb",
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".joblib",
    ".pkl",
    ".h5",
    ".pt",
    ".pth",
    ".ckpt",
    ".keras",
    ".pb",
    ".tflite",
})

FORBIDDEN_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    "node_modules",
    ".benchmarks",
})

FORBIDDEN_PATH_PREFIXES: tuple[str, ...] = (
    ".coverage",
    "coverage.xml",
    "htmlcov/",
    "coverage/",
    "dist/",
    "build/",
    "tmp/",
    "temp/",
    "scratch/",
    "generated/",
    "artifacts/",
    "artifact/",
    "cache/",
    "caches/",
    "test-results/",
    "playwright-report/",
    "browser_cache/",
    ".eslintcache",
    ".dmypy.json",
    "dmypy.json",
    ".DS_Store",
    "Thumbs.db",
    "._",
    "logs/",
    "*.egg-info/",
    "data/temp/",
    "data/logs/",
    "data/debug/",
    "data/network/",
    "data/screenshots/",
    "data/backups/",
    "data/backup/",
)

# ---------------------------------------------------------------------------
# Report-only patterns — suspicious but not automatically blocked.
# These produce warnings only; the PR author should explain or remove.
# ---------------------------------------------------------------------------
REPORT_ONLY_PATTERNS: tuple[str, ...] = (
    "*debug*",
    "*diagnostic*",
    "*diagnose*",
    "*analysis*",
    "*audit*",
    "*final_report*",
    "*summary_report*",
    "*temp*",
    "*scratch*",
    "*manual*",
    "*experiment*",
    "*prototype*",
    "*one_shot*",
    "*one-shot*",
    "*ad_hoc*",
    "*adhoc*",
    "*snapshot*",
    "*dump*",
)

# Paths that are exempt even if they match hard-block patterns.
# These are explicitly-allowlisted files (e.g., small test fixtures).
ALLOWLISTED_PATHS: frozenset[str] = frozenset(
    {
        "data/.gitkeep",
        "data/manual_html/.gitkeep",
        "data/manual_html/test_sample.html",
        "data/mock/sample_history.csv",
        "data/snapshots/.gitkeep",
        "tests/fixtures/",
        "model_zoo/v188_iron_shield_final.model",
        "logs/.gitkeep",
        "src/production_models/.gitkeep",
        "model_zoo/.gitkeep",
        "model_zoo/registry.md",
    }
)


def _matches_hard_block(path: str) -> bool:
    """Return True if *path* should be hard-blocked as a generated artifact.

    Checks: forbidden extensions, forbidden directory names, and forbidden path prefixes.
    """
    normalized = path.replace("\\", "/")

    # Check forbidden extensions
    for ext in FORBIDDEN_EXTENSIONS:
        if normalized.endswith(ext) or ("." + ext.lstrip(".")) in normalized:
            # For compound extensions like .tar.gz, check exact suffix match
            if normalized.endswith(ext):
                return True

    # Check for compound extensions like .tar.gz more carefully
    for ext in (".tar.gz", ".tar.bz2", ".tar.xz"):
        if normalized.endswith(ext):
            return True

    # Check single-dot extensions
    for ext in FORBIDDEN_EXTENSIONS:
        if not ext.startswith("."):
            continue
        # Only check the file extension, not substrings in path
        name = PurePath(normalized).name
        if name.endswith(ext) and ext not in (".tar.gz", ".tar.bz2", ".tar.xz"):
            return True

    # Check forbidden directory names in path components
    parts = PurePath(normalized).parts
    for part in parts:
        if part in FORBIDDEN_DIR_NAMES:
            return True

    # Check forbidden path prefixes
    for prefix in FORBIDDEN_PATH_PREFIXES:
        if normalized.startswith(prefix) or normalized == prefix.rstrip("/"):
            return True
        # Also check if any parent directory path starts with the prefix
        if "/" + prefix in "/" + normalized:
            return True

    return False


def _matches_any_pattern(path: str, patterns: Iterable[str]) -> bool:
    """Check if *path* matches any report-only pattern by fnmatch glob."""
    normalized = path.replace("\\", "/")
    name = PurePath(normalized).name.lower()
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def _is_allowlisted(path: str) -> bool:
    """Return True if *path* is explicitly allowlisted (exact or prefix match)."""
    normalized = path.replace("\\", "/")
    for allowed in ALLOWLISTED_PATHS:
        if normalized == allowed:
            return True
        if allowed.endswith("/") and normalized.startswith(allowed):
            return True
    return False


def check_added_files(added_paths: Iterable[str]) -> tuple[list[str], list[str]]:
    """Check newly-added files for generated artifacts.

    Returns (errors, warnings):
    - errors: hard-block matches (must be removed from commit)
    - warnings: report-only matches (should be explained or removed)

    Only checks *new* (status A) files to avoid false positives from
    pre-existing tracked files.  Deleted files are ignored.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for path in added_paths:
        if not path or path.endswith("/"):
            continue

        # Skip allowlisted paths
        if _is_allowlisted(path):
            continue

        # Hard-block check
        if _matches_hard_block(path):
            errors.append(
                f"Generated artifact detected: '{path}' — "
                f"matches hard-block pattern. Generated/built/cached/temp files "
                f"must not be committed. Remove from commit and keep in /tmp "
                f"or CI artifacts instead."
            )

        # Report-only check (only if not already hard-blocked)
        elif _matches_any_pattern(path, REPORT_ONLY_PATTERNS):
            warnings.append(
                f"Suspicious file detected: '{path}' — "
                f"matches report-only pattern (debug/diagnostic/temp/scratch/one-shot). "
                f"Verify this is a legitimate source file, not a generated report "
                f"or temporary diagnostic. Consider writing to /tmp instead."
            )

    return errors, warnings


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Block newly-added generated artifacts, temp files, caches, "
        "logs, and build outputs.",
    )
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--added",
        metavar="FILE",
        help="File containing one path per line of newly-added files (status A).",
    )
    input_group.add_argument(
        "--paths",
        nargs="*",
        metavar="PATH",
        help="One or more paths to check directly.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only produce warnings, never hard-block (for phased rollout).",
    )
    return parser.parse_args(argv)


def _read_added_file(file_path: str) -> list[str]:
    """Read added paths from a file, one per line."""
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def main(argv: list[str]) -> int:
    """Entry point — check added files and return 1 on error, 0 otherwise."""
    args = parse_args(argv)

    added = _read_added_file(args.added) if args.added else args.paths or []

    errors, warnings = check_added_files(added)

    if warnings:
        print(f"[no-generated-artifacts] {len(warnings)} suspicious file(s) detected:")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        if args.report_only:
            print(
                f"[no-generated-artifacts] {len(errors)} generated artifact(s) "
                f"would be blocked (report-only mode):"
            )
            for e in errors:
                print(f"  WOULD-BLOCK: {e}")
            print("[no-generated-artifacts] report-only mode — not failing.")
            return 0

        print(f"[no-generated-artifacts] {len(errors)} generated artifact(s) blocked:")
        for e in errors:
            print(f"  BLOCKED: {e}")
        print("[no-generated-artifacts] Remove generated files from commit and retry.")
        return 1

    print(
        f"[no-generated-artifacts] {len(added)} added file(s) checked — "
        f"no generated artifacts detected."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
