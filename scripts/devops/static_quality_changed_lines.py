#!/usr/bin/env python3
"""Static quality changed-line gate — apply changed-line principle to diagnostics.

lifecycle: permanent

Filters ruff / mypy diagnostics so that only violations on lines ADDED/MODIFIED
by the current PR are treated as blocking.  Pre-existing violations in changed
files are reported as warnings but do not cause a non-zero exit.

Usage (ruff — default):
    python static_quality_changed_lines.py <file>...

Usage (mypy):
    python static_quality_changed_lines.py --mypy <file>...
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
from pathlib import Path
import posixpath
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Maximum number of EXISTING diagnostics to show in summary before truncating.
MAX_EXISTING_DIAGS_SHOWN = 15

# Maximum number of NEW diagnostics to show in summary before truncating.
MAX_NEW_DIAGS_SHOWN = 30

# Number of context lines to show around each diagnostic (reserved for future use).
DIAGNOSTIC_CONTEXT_LINES = 1

# Fallback display limit when changed-line data is unavailable.
FALLBACK_DIAG_DISPLAY_LIMIT = 20

# Minimum number of parts expected in a unified diff hunk header.
MIN_HUNK_HEADER_PARTS = 3

# Internal marker for a file whose diff could not be read.  Diagnostics in
# these files remain blocking because changed-line classification is unsafe.
UNRESOLVED_CHANGED_LINE_PREFIX = "__unresolved_changed_line__:"

# ---------------------------------------------------------------------------
# Safe decoding helper
# ---------------------------------------------------------------------------


def _safe_decode(data: bytes | str | None) -> str:
    """Decode subprocess output without crashing on invalid UTF-8 bytes.

    Uses ``errors="replace"`` so that corrupt bytes in git diff output
    (e.g. from files with legacy encoding damage) produce U+FFFD instead
    of raising ``UnicodeDecodeError``.
    """
    if data is None:
        return ""
    if isinstance(data, str):
        return data
    return data.decode("utf-8", errors="replace")


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
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
        else:
            result = subprocess.run(
                ["git", "merge-base", "HEAD", origin_ref],
                capture_output=True,
                timeout=5,
                check=False,
            )
            stdout = _safe_decode(result.stdout)
            if result.returncode == 0 and stdout.strip():
                return stdout.strip()

    # Staged changes.
    try:
        subprocess.run(
            ["git", "diff", "--cached", "--quiet", "--exit-code"],
            capture_output=True,
            timeout=5,
            check=False,
        )
    except subprocess.CalledProcessError:
        return "HEAD"

    # Unstaged changes.
    try:
        subprocess.run(
            ["git", "diff", "--quiet", "--exit-code", "HEAD", "--"],
            capture_output=True,
            timeout=5,
            check=False,
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
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    else:
        return "HEAD~1"


def _parse_hunk_new_start(hunk_header: str) -> int | None:
    """Parse the new-file start line from a unified diff hunk header.

    Example: "@@ -old_start,old_count +new_start,new_count @@" -> new_start.
    """
    parts = hunk_header.split()
    if len(parts) < MIN_HUNK_HEADER_PARTS:
        return None
    new_part = parts[2].lstrip("+")  # e.g., "+1,5" or "+1"
    if "," in new_part:
        return int(new_part.split(",")[0])
    return int(new_part)


def _collect_changed_lines_for_file_with_status(git_base: str, file: str) -> tuple[set[int], bool]:
    """Return changed lines and whether the diff was parsed safely."""
    try:
        result = subprocess.run(
            ["git", "diff", f"{git_base}...HEAD", "--", file],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return set(), False

    if result.returncode != 0:
        return set(), False

    lines: set[int] = set()
    current_new_line: int | None = None

    for diff_line in _safe_decode(result.stdout).splitlines():
        if diff_line.startswith("@@") and "@@" in diff_line[2:]:
            try:
                current_new_line = _parse_hunk_new_start(diff_line)
            except ValueError:
                return set(), False
            if current_new_line is None:
                return set(), False
            continue

        if current_new_line is None:
            continue

        if diff_line.startswith("+") and not diff_line.startswith("+++"):
            lines.add(current_new_line)
            current_new_line += 1
        elif not diff_line.startswith("-"):
            # Context or unchanged line — advance the new-line counter.
            current_new_line += 1

    return lines, True


def _collect_changed_lines_for_file(git_base: str, file: str) -> set[int]:
    """Return the set of changed (added) line numbers for a single file."""
    lines, _parsed = _collect_changed_lines_for_file_with_status(git_base, file)
    return lines


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
        normalised = _normalize_path(file)
        file_lines, parsed = _collect_changed_lines_for_file_with_status(git_base, file)
        if parsed:
            changed[normalised] = file_lines
        else:
            changed[f"{UNRESOLVED_CHANGED_LINE_PREFIX}{normalised}"] = set()

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
            timeout=30,
            check=False,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(
            f"[static-quality] ERROR: ruff invocation failed: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if result.returncode == 0:
        return []

    try:
        diagnostics: list[dict] = json.loads(_safe_decode(result.stdout))
    except json.JSONDecodeError:
        # Ruff may write to stderr; can't parse JSON — fall back to
        # treating all diagnostics as new.
        print(
            "[static-quality] WARN: could not parse ruff JSON output; "
            "falling back to whole-file (all diagnostics treated as new)",
            file=sys.stderr,
        )
        subprocess.run(
            ["python", "-m", "ruff", "check", *files],
            check=False,
            timeout=30,
        )
        sys.exit(1)
    else:
        return diagnostics


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _normalize_path(file_path: str) -> str:
    """Normalise a file path from ruff / git diff to a consistent relative form.

    Ruff may return absolute Docker paths (``/app/src/main.py``) while git diff
    returns repository-relative paths (``src/main.py``).  This function strips
    well-known container mount-point prefixes so both sources produce the same
    key for the ``changed_lines`` dict.
    """
    normalised = file_path.strip().replace("\\", "/")
    cwd = Path.cwd().as_posix()
    known_prefixes: tuple[str, ...] = (
        f"{cwd}/",
        "/app/",
        "/home/runner/work/FootballPrediction/FootballPrediction/",
    )
    for prefix in known_prefixes:
        if normalised.startswith(prefix):
            normalised = normalised[len(prefix) :]
            break
    return posixpath.normpath(normalised)


def _is_unmapped_absolute_path(file_path: str) -> bool:
    """Return True when a diagnostic path could not be made repo-relative."""
    return file_path.startswith("/") or bool(re.match(r"^[A-Za-z]:/", file_path))


def _split_changed_line_data(
    changed_lines: dict[str, set[int]],
) -> tuple[dict[str, set[int]], set[str]]:
    """Separate resolved changed-line data from fail-safe unresolved markers."""
    resolved: dict[str, set[int]] = {}
    unresolved: set[str] = set()
    for file_path, lines in changed_lines.items():
        if file_path.startswith(UNRESOLVED_CHANGED_LINE_PREFIX):
            unresolved.add(file_path[len(UNRESOLVED_CHANGED_LINE_PREFIX) :])
        else:
            resolved[file_path] = lines
    return resolved, unresolved


def classify_diagnostics(
    diagnostics: list[dict],
    changed_lines: dict[str, set[int]],
) -> tuple[list[dict], list[dict]]:
    """Classify diagnostics into NEW (on changed line) and EXISTING.

    Returns (new_diags, existing_diags).
    """
    new: list[dict] = []
    existing: list[dict] = []
    if not changed_lines:
        return diagnostics.copy(), existing

    resolved_changed_lines, unresolved_files = _split_changed_line_data(changed_lines)

    for diag in diagnostics:
        file_path = diag.get("filename", "")
        line = diag.get("location", {}).get("row", 0)

        if not file_path or not isinstance(line, int) or line <= 0:
            # Can't map — treat as new (fail-safe).
            new.append(diag)
            continue

        normalised = _normalize_path(file_path)
        if _is_unmapped_absolute_path(normalised):
            # Unknown absolute path — can't safely compare against git diff.
            new.append(diag)
            continue

        if normalised in unresolved_files:
            # The file was a target, but its diff could not be parsed safely.
            new.append(diag)
            continue

        if normalised not in resolved_changed_lines:
            # Mypy can emit diagnostics in imported files.  If the file is not
            # part of the resolved changed-file set, it is historical context.
            existing.append(diag)
            continue

        changed = resolved_changed_lines[normalised]
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
# Reporting
# ---------------------------------------------------------------------------


def _report_existing_diags(existing_diags: list[dict]) -> None:
    """Print EXISTING (pre-existing) diagnostics as warnings to stderr."""
    print(
        f"[static-quality] ruff: {len(existing_diags)} EXISTING violation(s) "
        f"(pre-existing, not on changed lines — WARN, not blocking)",
        file=sys.stderr,
    )
    for diag in existing_diags[:MAX_EXISTING_DIAGS_SHOWN]:
        print(format_diagnostic(diag), file=sys.stderr)
    if len(existing_diags) > MAX_EXISTING_DIAGS_SHOWN:
        remaining = len(existing_diags) - MAX_EXISTING_DIAGS_SHOWN
        print(
            f"  ... and {remaining} more existing violation(s)",
            file=sys.stderr,
        )


def _report_new_diags(new_diags: list[dict]) -> None:
    """Print NEW (changed-line) diagnostics as blocking errors to stderr."""
    print(
        f"[static-quality] ruff: {len(new_diags)} NEW violation(s) (on changed lines — BLOCKING)",
        file=sys.stderr,
    )
    for diag in new_diags[:MAX_NEW_DIAGS_SHOWN]:
        print(format_diagnostic(diag), file=sys.stderr)
    if len(new_diags) > MAX_NEW_DIAGS_SHOWN:
        remaining = len(new_diags) - MAX_NEW_DIAGS_SHOWN
        print(
            f"  ... and {remaining} more new violation(s)",
            file=sys.stderr,
        )


def _report_fallback(all_diags: list[dict]) -> int:
    """Fallback when changed-line data unavailable — treat all as new."""
    print(
        "[static-quality] WARN: could not determine changed line ranges; "
        "all diagnostics treated as new (fail-safe)",
        file=sys.stderr,
    )
    for diag in all_diags[:FALLBACK_DIAG_DISPLAY_LIMIT]:
        print(format_diagnostic(diag), file=sys.stderr)
    if len(all_diags) > FALLBACK_DIAG_DISPLAY_LIMIT:
        remaining = len(all_diags) - FALLBACK_DIAG_DISPLAY_LIMIT
        print(f"  ... and {remaining} more", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Mypy helpers
# ---------------------------------------------------------------------------

# Mypy output line patterns:
#   src/main.py:247: error: Argument 1 has incompatible type ...  [arg-type]
#   /app/src/main.py:247: error: ...  [error-code]
#   src/main.py:250: note: ...
_MYPY_LINE_RE = re.compile(r"^(.+?):(\d+):\s+(error|note):\s+(.*?)(?:\s+\[(.+?)\])?\s*$")


def parse_mypy_output(text: str) -> list[dict]:
    """Parse mypy text output into diagnostic dicts (same shape as ruff JSON).

    Only *error* severity lines are included.  ``note`` lines are ignored.
    """
    diagnostics: list[dict] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        m = _MYPY_LINE_RE.match(line)
        if m is None:
            continue
        file_path, line_no_str, severity, message, error_code = m.groups()
        if severity != "error":
            continue
        try:
            line_no = int(line_no_str)
        except ValueError:
            continue
        diagnostics.append(
            {
                "filename": file_path,
                "location": {"row": line_no, "column": 0},
                "code": error_code or "mypy",
                "message": message.strip(),
            }
        )
    return diagnostics


def run_mypy_changed_line(files: list[str]) -> int:
    """Run mypy with changed-line gating.  Return 0 on pass, 1 on new violations."""
    print(f"[static-quality-mypy] Checking {len(files)} Python file(s) with changed-line gate.")

    # 1. Run mypy and capture output.
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "--config-file",
                "mypy.ini",
                "--follow-imports=silent",
                *files,
            ],
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"[static-quality] ERROR: mypy invocation failed: {exc}", file=sys.stderr)
        return 1

    combined = _safe_decode(result.stdout) + "\n" + _safe_decode(result.stderr)

    if result.returncode == 0:
        print("[static-quality-mypy] mypy: no diagnostics — PASS")
        return 0

    all_diags = parse_mypy_output(combined)
    if not all_diags:
        # Mypy reported failure but output is unparseable — fail-safe.
        print(
            "[static-quality] WARN: could not parse mypy output; treating as failure (fail-safe)",
            file=sys.stderr,
        )
        print(combined, file=sys.stderr)
        return 1

    # 2. Compute changed line ranges.
    changed_lines = get_changed_line_ranges(files)
    if not changed_lines:
        return _report_fallback(all_diags)

    total_changed = sum(len(lines) for lines in changed_lines.values())
    print(
        f"[static-quality-mypy] Changed line ranges computed: "
        f"{len(changed_lines)} file(s), {total_changed} changed line(s)"
    )

    # 3. Classify and report.
    new_diags, existing_diags = classify_diagnostics(all_diags, changed_lines)

    if existing_diags:
        _report_existing_diags(existing_diags)

    if new_diags:
        _report_new_diags(new_diags)
        return 1

    print(
        f"[static-quality-mypy] mypy: PASS — 0 new violations, "
        f"{len(existing_diags)} pre-existing (warned above)"
    )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    """Run changed-line ruff check and return 0 on pass, 1 on new violations."""
    files = sys.argv[1:]
    if not files:
        print("[static-quality] No files to check.", file=sys.stderr)
        return 0

    # --mypy mode
    if files and files[0] == "--mypy":
        return run_mypy_changed_line(files[1:])

    print(f"[static-quality] Checking {len(files)} Python file(s) with changed-line gate.")

    # 1. Run ruff.
    all_diags = run_ruff(files)
    if not all_diags:
        print("[static-quality] ruff: no diagnostics found — PASS")
        return 0

    # 2. Compute changed line ranges.
    changed_lines = get_changed_line_ranges(files)
    if not changed_lines:
        return _report_fallback(all_diags)

    total_changed = sum(len(lines) for lines in changed_lines.values())
    print(
        f"[static-quality] Changed line ranges computed: "
        f"{len(changed_lines)} file(s), {total_changed} changed line(s)"
    )

    # 3. Classify and report.
    new_diags, existing_diags = classify_diagnostics(all_diags, changed_lines)

    if existing_diags:
        _report_existing_diags(existing_diags)

    if new_diags:
        _report_new_diags(new_diags)
        return 1

    print(
        f"[static-quality] ruff: PASS — 0 new violations, "
        f"{len(existing_diags)} pre-existing (warned above)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
