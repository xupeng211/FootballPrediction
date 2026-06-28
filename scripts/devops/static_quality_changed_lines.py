#!/usr/bin/env python3
"""Static quality changed-line gate — apply changed-line principle to ruff diagnostics.

lifecycle: permanent

Filters ruff diagnostics so that only violations on lines ADDED/MODIFIED by
the current PR are treated as blocking. Pre-existing violations in changed
files are reported as warnings but do not cause a non-zero exit.

Usage:
  python scripts/devops/static_quality_changed_lines.py <file1> <file2> ...

The script:
  1. Runs ruff check --output-format json on the given files.
  2. Computes changed line ranges from git diff.
  3. Classifies each diagnostic as NEW (on changed line) or EXISTING.
  4. Exits 0 if only EXISTING violations exist (with warnings on stderr).
  5. Exits 1 if any NEW violations are found.

TECHDEBT-E: Changed-line gate for static quality checks.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Number of context lines to show around each diagnostic in the summary.
DIAGNOSTIC_CONTEXT_LINES = 1

# ---------------------------------------------------------------------------
# Git helpers (aligned with grep_added_lines() in gatekeeper.sh)
# ---------------------------------------------------------------------------


def _resolve_git_diff_base() -> str | None:
    """Resolve the git diff base using the same logic as gatekeeper.sh."""
    git_base_ref = os.environ.get("GITHUB_BASE_REF", "")

    # CI PR context — use GitHub's base ref.
    if git_base_ref:
        origin_ref = f"origin/{git_base_ref}"
        try:
            subprocess.run(
                ["git", "rev-parse", "--verify", origin_ref],
                capture_output=True,
                check=True,
                timeout=5,
            )
            result = subprocess.run(
                ["git", "merge-base", "HEAD", origin_ref],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # Staged changes.
    try:
        subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--exit-code"],
            capture_output=True,
            timeout=5,
        )
    except subprocess.CalledProcessError:
        return "HEAD"

    # Unstaged changes.
    try:
        subprocess.run(
            ["git", "diff", "--quiet", "--exit-code", "HEAD", "--"],
            capture_output=True,
            timeout=5,
        )
    except subprocess.CalledProcessError:
        return "HEAD"

    # Fallback: HEAD~1
    try:
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD~1"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        return "HEAD~1"
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def get_changed_line_ranges(files: list[str]) -> dict[str, set[int]]:
    """Return {file_path: set_of_changed_line_numbers} for the current PR.

    Parses unified diff output.  Counts ADDED lines (starting with '+')
    as changed lines.  For each changed file, returns the set of line
    numbers that were added or modified.
    """
    git_base = _resolve_git_diff_base()
    if git_base is None:
        # Can't determine base — treat all lines as changed (fail-safe).
        return {}

    changed: dict[str, set[int]] = {}
    for file in files:
        try:
            result = subprocess.run(
                ["git", "diff", f"{git_base}...HEAD", "--", file],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue

        if result.returncode != 0:
            continue

        lines: set[int] = set()
        current_new_line: int | None = None

        for diff_line in result.stdout.splitlines():
            if diff_line.startswith("@@") and diff_line.endswith("@@"):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                parts = diff_line.split()
                if len(parts) >= 3:
                    new_part = parts[2]  # e.g., "+1,5"
                    new_part = new_part.lstrip("+")
                    if "," in new_part:
                        current_new_line = int(new_part.split(",")[0])
                    else:
                        current_new_line = int(new_part)
                continue

            if current_new_line is None:
                continue

            if diff_line.startswith("+") and not diff_line.startswith("+++"):
                lines.add(current_new_line)
                current_new_line += 1
            elif not diff_line.startswith("-"):
                # Context line or unchanged line in hunk — advance new-line counter.
                current_new_line += 1

        if lines:
            changed[file] = lines

    return changed


# ---------------------------------------------------------------------------
# Ruff helpers
# ---------------------------------------------------------------------------


def run_ruff(files: list[str]) -> list[dict]:
    """Run ruff check --output-format json and return diagnostics."""
    try:
        result = subprocess.run(
            ["python", "-m", "ruff", "check", "--output-format", "json", *files],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"[static-quality] ERROR: ruff invocation failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if result.returncode == 0:
        return []

    try:
        diagnostics: list[dict] = json.loads(result.stdout)
        return diagnostics
    except json.JSONDecodeError:
        # Ruff may write to stderr; try parsing stdout loosely.
        # If we can't parse JSON, fall back to treating all as new.
        print(
            "[static-quality] WARN: could not parse ruff JSON output; "
            "falling back to whole-file (all diagnostics treated as new)",
            file=sys.stderr,
        )
        # Re-run without JSON and let it fail normally.
        subprocess.run(
            ["python", "-m", "ruff", "check", *files],
            check=False,
            timeout=30,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify_diagnostics(
    diagnostics: list[dict],
    changed_lines: dict[str, set[int]],
) -> tuple[list[dict], list[dict]]:
    """Classify diagnostics into NEW (on changed line) and EXISTING.

    Returns (new_diags, existing_diags).
    """
    new: list[dict] = []
    existing: list[dict] = []

    for diag in diagnostics:
        file_path = diag.get("filename", "")
        line = diag.get("location", {}).get("row", 0)

        if not file_path or line == 0:
            # Can't map — treat as new (fail-safe).
            new.append(diag)
            continue

        changed = changed_lines.get(file_path, set())
        if not changed:
            # No changed-line data for this file — treat as new (fail-safe).
            new.append(diag)
            continue

        if line in changed:
            new.append(diag)
        else:
            existing.append(diag)

    return new, existing


def format_diagnostic(diag: dict) -> str:
    """Format a single ruff diagnostic for display."""
    file_path = diag.get("filename", "?")
    loc = diag.get("location", {})
    line = loc.get("row", "?")
    col = loc.get("column", "?")
    code = diag.get("code", "?")
    message = diag.get("message", "")

    return f"  {file_path}:{line}:{col}: {code} {message}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    files = sys.argv[1:]
    if not files:
        print("[static-quality] No files to check.", file=sys.stderr)
        return 0

    print(f"[static-quality] Checking {len(files)} Python file(s) with changed-line gate.")

    # 1. Run ruff.
    all_diags = run_ruff(files)
    if not all_diags:
        print("[static-quality] ruff: no diagnostics found — PASS")
        return 0

    # 2. Compute changed line ranges.
    changed_lines = get_changed_line_ranges(files)
    if not changed_lines:
        print(
            "[static-quality] WARN: could not determine changed line ranges; "
            "all diagnostics treated as new (fail-safe)",
            file=sys.stderr,
        )
        for diag in all_diags[:20]:
            print(format_diagnostic(diag), file=sys.stderr)
        if len(all_diags) > 20:
            print(f"  ... and {len(all_diags) - 20} more", file=sys.stderr)
        return 1

    total_changed = sum(len(lines) for lines in changed_lines.values())
    print(f"[static-quality] Changed line ranges computed: {len(changed_lines)} file(s), {total_changed} changed line(s)")

    # 3. Classify.
    new_diags, existing_diags = classify_diagnostics(all_diags, changed_lines)

    # 4. Report.
    if existing_diags:
        print(
            f"[static-quality] ruff: {len(existing_diags)} EXISTING violation(s) "
            f"(pre-existing, not on changed lines — WARN, not blocking)",
            file=sys.stderr,
        )
        for diag in existing_diags[:15]:
            print(format_diagnostic(diag), file=sys.stderr)
        if len(existing_diags) > 15:
            print(
                f"  ... and {len(existing_diags) - 15} more existing violation(s)",
                file=sys.stderr,
            )

    if new_diags:
        print(
            f"[static-quality] ruff: {len(new_diags)} NEW violation(s) "
            f"(on changed lines — BLOCKING)",
            file=sys.stderr,
        )
        for diag in new_diags[:30]:
            print(format_diagnostic(diag), file=sys.stderr)
        if len(new_diags) > 30:
            print(f"  ... and {len(new_diags) - 30} more new violation(s)", file=sys.stderr)
        return 1

    print(
        f"[static-quality] ruff: PASS — 0 new violations, "
        f"{len(existing_diags)} pre-existing (warned above)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
