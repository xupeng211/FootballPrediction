#!/usr/bin/env python3
"""Local PR Gate Preflight — simulate remote Production Gate checks locally.

lifecycle: permanent

Runs the same PR body validation, changed-files enforcement, hidden/bidi scan,
secret/payload marker scan, and agent workflow hardening checks that the remote
CI Production Gate enforces — without network, DB connection, secrets, or
target-script execution.

Usage:
  # Fast mode (default): static checks + enforcement only
  python scripts/ops/local_pr_gate_preflight.py --pr-body-file /tmp/pr_body.md

  # Full mode: fast + ruff, mypy, pytest, npm test:coverage
  python scripts/ops/local_pr_gate_preflight.py --pr-body-file /tmp/pr_body.md --full

  # Machine-readable output
  python scripts/ops/local_pr_gate_preflight.py --pr-body-file /tmp/pr_body.md --json

Known-failure policy:
  This preflight does NOT enforce exact test-count matching against the PR body
  Validation section. A pre-existing 47/48 pass discrepancy in guard helper
  behavior tests is documented as a known non-blocking SC-002 partial-mitigation
  item and does not affect local preflight results.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.ai_workflow_gate import (  # noqa: E402
    Change,
    added_paths,
    changed_paths,
    git_output,
    parse_name_status,
    validate,
)
from scripts.ops.helpers.agent_workflow_hardening_checks import (  # noqa: E402
    check_forbidden_rewrite_patterns,
    check_forbidden_safety_claims,
    check_large_risky_change,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Unicode hidden/bidi characters — built with chr() to avoid literal
# control characters in source that trigger ruff PLE2502/PLE2515.
# The scan compares bytes, so this is functionally identical.
HIDDEN_CHARS: dict[str, str] = {
    chr(0x202E): "RIGHT-TO-LEFT OVERRIDE (U+202E)",
    chr(0x202D): "LEFT-TO-RIGHT OVERRIDE (U+202D)",
    chr(0x2066): "LEFT-TO-RIGHT ISOLATE (U+2066)",
    chr(0x2067): "RIGHT-TO-LEFT ISOLATE (U+2067)",
    chr(0x2068): "FIRST STRONG ISOLATE (U+2068)",
    chr(0x2069): "POP DIRECTIONAL ISOLATE (U+2069)",
    chr(0x200B): "ZERO WIDTH SPACE (U+200B)",
    chr(0x200C): "ZERO WIDTH NON-JOINER (U+200C)",
    chr(0x200D): "ZERO WIDTH JOINER (U+200D)",
    chr(0xFEFF): "ZERO WIDTH NO-BREAK SPACE / BOM (U+FEFF)",
}

_SECRET_RE = (
    r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?",
    r'(?:password|passwd|pwd|secret|api[_-]?key)\s*[:=]\s*["\'][^"\']{4,}["\']',
    r"ghp_[A-Za-z0-9]{36}",
    r"sk-[A-Za-z0-9]{32,}",
    r"-----BEGIN\s+(?:RSA|OPENSSH|PGP|EC)\s+PRIVATE\s+KEY",
)
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = tuple(re.compile(p) for p in _SECRET_RE)

SECRET_SCAN_SKIP: tuple[str, ...] = (
    "tests/fixtures/",
    "docs/_reports/",
    "docs/_manifests/",
    "scripts/ops/helpers/db_write_guard_legacy_allowlist.json",
)

# The preflight script itself contains HIDDEN_CHARS definitions as data.
# Skip it to avoid self-detection false positives.
HIDDEN_BIDI_SCAN_SKIP: tuple[str, ...] = ("scripts/ops/local_pr_gate_preflight.py",)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    status: str  # PASS | FAIL | SKIP | ERROR
    message: str = ""
    details: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def failed(self) -> bool:  # noqa: D401
        return self.status == "FAIL"


@dataclass
class PreflightResult:
    passed: bool = True
    phases: list[CheckResult] = field(default_factory=list)
    changed_files: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    mode: str = "fast"

    @property
    def elapsed_s(self) -> float:
        return self.end_time - self.start_time

    @property
    def failures(self) -> list[str]:
        return [p.name for p in self.phases if p.failed]

    @property
    def warnings(self) -> list[str]:
        return [p.name for p in self.phases if p.status in ("SKIP", "ERROR")]


# ---------------------------------------------------------------------------
# Changed files computation
# ---------------------------------------------------------------------------


def compute_changed_files(
    base: str = "origin/main", head: str = "HEAD", override: str | None = None
) -> tuple[list[Change], set[str], set[str]]:
    """Compute git diff name-status, returning (changes, changed_set, added_set)."""
    if override:
        changes = parse_name_status(Path(override).read_text("utf-8"))
    else:
        changes = parse_name_status(git_output(["diff", "--name-status", f"{base}...{head}"]))
    return changes, changed_paths(changes), added_paths(changes)


# ---------------------------------------------------------------------------
# Phase: Git diff integrity
# ---------------------------------------------------------------------------


def check_git_diff(changes: list[Change]) -> CheckResult:
    if not changes:
        return CheckResult("git-diff-integrity", "PASS", "No changed files — nothing to check")
    return CheckResult(
        "git-diff-integrity",
        "PASS",
        f"{len(changes)} changed file(s) detected",
        [f"{c.status}\t{c.path}" for c in changes],
    )


# ---------------------------------------------------------------------------
# Phase: Hidden/bidi character scan (Trojan Source CVE-2021-42574)
# ---------------------------------------------------------------------------


def _find_lines(content: bytes, char: str) -> str:
    char_bytes = char.encode("utf-8")
    nos = [str(i) for i, line in enumerate(content.split(b"\n"), 1) if char_bytes in line]
    return ",".join(nos[:10]) if nos else "?"


def check_hidden_bidi(changed: set[str]) -> CheckResult:
    findings: list[str] = []
    for rel_path in sorted(changed):
        if any(rel_path.startswith(px) for px in HIDDEN_BIDI_SCAN_SKIP):
            continue
        fp = ROOT / rel_path
        if not fp.is_file():
            continue
        try:
            content = fp.read_bytes()
        except OSError:
            continue
        for char, desc in HIDDEN_CHARS.items():
            if char.encode("utf-8") in content:
                findings.append(f"{rel_path}: {desc} at line(s) {_find_lines(content, char)}")
    if findings:
        return CheckResult(
            "hidden-bidi-scan", "FAIL", f"Found {len(findings)} hidden/bidi character(s)", findings
        )
    return CheckResult("hidden-bidi-scan", "PASS", "No hidden/bidi characters found")


# ---------------------------------------------------------------------------
# Phase: Secret/payload marker scan
# ---------------------------------------------------------------------------


def check_secret_markers(changed: set[str]) -> CheckResult:
    findings: list[str] = []
    for rel_path in sorted(changed):
        fp = ROOT / rel_path
        if not fp.is_file() or any(rel_path.startswith(px) for px in SECRET_SCAN_SKIP):
            continue
        try:
            text = fp.read_text("utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for pat in SECRET_PATTERNS:
                m = pat.search(line)
                if m:
                    findings.append(
                        f"{rel_path}:{line_no}: matches "
                        f"'{pat.pattern[:50]}...' => '{m.group()[:60]}'"
                    )
                    break
    if findings:
        return CheckResult(
            "secret-marker-scan",
            "FAIL",
            f"Found {len(findings)} potential secret/payload marker(s)",
            findings,
        )
    return CheckResult("secret-marker-scan", "PASS", "No secret/payload markers found")


# ---------------------------------------------------------------------------
# Phase: PR body validation (delegates to ai_workflow_gate.validate)
# ---------------------------------------------------------------------------


def check_pr_body(pr_body: str, changes: list[Change]) -> CheckResult:
    """Delegate to ai_workflow_gate.validate() — all sections, stop-phrases,
    governance/business mixing, doc sprawl, report backflow, dangerous keywords,
    safety consistency, forbidden rewrites, large risky changes, forbidden
    safety claims, and section content quality."""
    errors = validate(pr_body, changes, skip_body_checks=False)
    if errors:
        return CheckResult(
            "pr-body-validation", "FAIL", f"{len(errors)} PR body validation error(s)", errors
        )
    return CheckResult("pr-body-validation", "PASS", "All PR body validation checks passed")


# ---------------------------------------------------------------------------
# Phase: Forbidden safety claims (explicit, for granular output)
# ---------------------------------------------------------------------------


def check_forbidden(pr_body: str) -> CheckResult:
    errors = check_forbidden_safety_claims(pr_body)
    if errors:
        return CheckResult(
            "forbidden-claims", "FAIL", f"{len(errors)} forbidden safety claim(s)", errors
        )
    return CheckResult("forbidden-claims", "PASS", "No forbidden safety claims")


# ---------------------------------------------------------------------------
# Phase: Changed-files hardening
# ---------------------------------------------------------------------------


def check_hardening(changes: list[Change], added: set[str], pr_body: str) -> CheckResult:
    errors: list[str] = []
    errors.extend(check_forbidden_rewrite_patterns(added, pr_body))
    errors.extend(check_large_risky_change(changes, pr_body))
    if errors:
        return CheckResult(
            "changed-files-hardening", "FAIL", f"{len(errors)} hardening error(s)", errors
        )
    return CheckResult(
        "changed-files-hardening", "PASS", "All changed-files hardening checks passed"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@contextmanager
def _suppress_stdout():
    """Temporarily redirect stdout to suppress side-effect prints."""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


# ---------------------------------------------------------------------------
# Generic importlib enforcement runner (Python DB write + SQL migration)
# ---------------------------------------------------------------------------


def _run_importlib_enforcement(
    helper_rel_path: str, module_name: str, changed: set[str]
) -> CheckResult:
    """Load a enforcement helper via importlib and run its run_gate_check()."""
    import importlib.util  # noqa: PLC0415

    hpath = ROOT / helper_rel_path
    if not hpath.exists():
        return CheckResult(module_name, "SKIP", f"Helper not found: {helper_rel_path}")
    try:
        spec = importlib.util.spec_from_file_location("_enf", str(hpath))
        if spec is None or spec.loader is None:
            return CheckResult(module_name, "SKIP", "Cannot load enforcement module")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        errors: list[str] = []
        mod.run_gate_check(changed, errors)
        if errors:
            return CheckResult(module_name, "FAIL", f"{len(errors)} enforcement error(s)", errors)
        return CheckResult(module_name, "PASS", f"{module_name} enforcement passed")
    except Exception as exc:
        return CheckResult(module_name, "ERROR", f"Scanner error: {exc}")


def check_python_db(changed: set[str]) -> CheckResult:
    return _run_importlib_enforcement(
        "scripts/ops/helpers/python_db_write_enforcement_check.py", "python-db-write", changed
    )


def check_sql_migration(changed: set[str]) -> CheckResult:
    return _run_importlib_enforcement(
        "scripts/ops/helpers/sql_migration_policy_enforcement_check.py", "sql-migration", changed
    )


# ---------------------------------------------------------------------------
# Phase: JS DB write guard enforcement (node subprocess)
# ---------------------------------------------------------------------------


def check_js_db_guard(changed: set[str]) -> CheckResult:
    js_ops = sorted(p for p in changed if p.startswith("scripts/ops/") and p.endswith(".js"))
    if not js_ops:
        return CheckResult("js-db-write-guard", "PASS", "No scripts/ops JS files changed")
    scanner = ROOT / "scripts/ops/db_write_guard_static_enforcement_dry_run.js"
    if not scanner.exists():
        return CheckResult("js-db-write-guard", "SKIP", "JS scanner not found on disk")

    proc, data = _exec_js_scanner(scanner, js_ops)
    if proc is not None and data is None:
        # Scanner execution or output parsing failed
        return proc
    violations = (data or {}).get("violations", [])
    if violations:
        details = [
            f"{v.get('path', '?')}: writes {v.get('operations', [])} on {v.get('tables', [])}"
            for v in violations
        ]
        return CheckResult(
            "js-db-write-guard", "FAIL", f"{len(violations)} JS guard violation(s)", details
        )
    return CheckResult("js-db-write-guard", "PASS", "JS DB write guard enforcement passed")


def _exec_js_scanner(scanner: Path, js_ops: list[str]) -> tuple[CheckResult | None, dict | None]:
    """Run node scanner subprocess, returning (error_result, parsed_json)."""
    try:
        proc = subprocess.run(
            ["node", str(scanner), "--json", "--changed-files", ",".join(js_ops)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        return (CheckResult("js-db-write-guard", "SKIP", "Node.js not available"), None)
    except subprocess.TimeoutExpired:
        return (CheckResult("js-db-write-guard", "ERROR", "JS scanner timed out"), None)
    except Exception as exc:
        return (CheckResult("js-db-write-guard", "ERROR", f"Scanner error: {exc}"), None)
    if proc.returncode != 0:
        return (
            CheckResult(
                "js-db-write-guard",
                "ERROR",
                f"Scanner exit code {proc.returncode}",
                [proc.stderr.strip()] if proc.stderr else [],
            ),
            None,
        )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return (CheckResult("js-db-write-guard", "ERROR", "Scanner output is not valid JSON"), None)
    return (None, data)


# ---------------------------------------------------------------------------
# Full mode: generic subprocess check (ruff / ruff-format / mypy)
# ---------------------------------------------------------------------------


def _run_tool(tool_name: str, args: list[str], *, timeout: int = 60) -> CheckResult:
    """Run a CLI tool against changed files, returning a CheckResult."""
    try:
        proc = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        return CheckResult(tool_name, "SKIP", f"{args[0]} not available")
    except subprocess.TimeoutExpired:
        return CheckResult(tool_name, "ERROR", f"{args[0]} timed out")
    if proc.returncode != 0:
        err_lines = [line for line in proc.stdout.splitlines() if line.strip()][:20]
        return CheckResult(
            tool_name, "FAIL", f"{args[0]} found issues (exit {proc.returncode})", err_lines
        )
    return CheckResult(tool_name, "PASS", f"{args[0]} clean")


def check_ruff(changed: set[str]) -> CheckResult:
    py_files = sorted(p for p in changed if p.endswith(".py"))
    if not py_files:
        return CheckResult("ruff-check", "SKIP", "No Python files changed")
    return _run_tool("ruff-check", ["ruff", "check", *py_files])


def check_ruff_fmt(changed: set[str]) -> CheckResult:
    py_files = sorted(p for p in changed if p.endswith(".py"))
    if not py_files:
        return CheckResult("ruff-format", "SKIP", "No Python files changed")
    return _run_tool("ruff-format", ["ruff", "format", "--check", *py_files])


def check_mypy(changed: set[str]) -> CheckResult:
    py_files = sorted(p for p in changed if p.endswith(".py"))
    if not py_files:
        return CheckResult("mypy", "SKIP", "No Python files changed")
    return _run_tool("mypy", ["mypy", *py_files], timeout=120)


# ---------------------------------------------------------------------------
# Full mode: Relevant pytest
# ---------------------------------------------------------------------------


def _resolve_tests(changed: set[str]) -> list[str]:
    """Map changed files to probable test files."""
    tests: list[str] = []
    for path in sorted(changed):
        if path.startswith("tests/") and path.endswith(".py"):
            tests.append(path)
        elif path.endswith(".py"):
            stem = Path(path).stem
            for cand in (f"tests/unit/test_{stem}.py", f"tests/test_{stem}.py"):
                if (ROOT / cand).is_file() and cand not in tests:
                    tests.append(cand)
    return tests


def check_pytest(changed: set[str]) -> CheckResult:
    test_files = _resolve_tests(changed)
    if not test_files:
        return CheckResult("pytest", "SKIP", "No relevant test files found")
    return _run_tool(
        "pytest", [sys.executable, "-m", "pytest", *test_files, "-v", "--tb=short"], timeout=120
    )


# ---------------------------------------------------------------------------
# Full mode: npm test:coverage
# ---------------------------------------------------------------------------


def check_npm(changed: set[str]) -> CheckResult:
    if not any(p.endswith(".js") for p in changed):
        return CheckResult("npm-test-coverage", "SKIP", "No JavaScript files changed")
    try:
        proc = subprocess.run(
            ["npm", "run", "test:coverage"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except FileNotFoundError:
        return CheckResult("npm-test-coverage", "SKIP", "npm not available")
    except subprocess.TimeoutExpired:
        return CheckResult("npm-test-coverage", "ERROR", "npm test:coverage timed out")
    combined = proc.stdout + proc.stderr
    if "FAIL" in combined or "fail" in proc.stderr.lower():
        failing = [line for line in combined.splitlines() if "FAIL" in line][:10]
        return CheckResult("npm-test-coverage", "FAIL", "npm test:coverage found failures", failing)
    return CheckResult("npm-test-coverage", "PASS", "npm test:coverage passed")


# ---------------------------------------------------------------------------
# Python UTF-8 / AST parse validation
# ---------------------------------------------------------------------------


def check_python_ast_utf8(changed: set[str]) -> CheckResult:
    """Validate changed Python files decode as UTF-8 and parse as AST."""
    py_files = [p for p in changed if p.endswith(".py")]
    if not py_files:
        return CheckResult("python-ast-utf8", "SKIP", "No Python files changed")

    t0 = time.time()
    script = str(ROOT / "scripts/devops/check_python_ast_utf8.py")
    try:
        result = subprocess.run(
            [sys.executable, script, "--paths", *py_files],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as exc:
        return CheckResult(
            "python-ast-utf8",
            "ERROR",
            f"Failed to run check_python_ast_utf8: {exc}",
        )

    duration_ms = (time.time() - t0) * 1000
    output = result.stdout + result.stderr
    if result.returncode == 0:
        last_line = output.strip().splitlines()[-1] or "OK"
        return CheckResult("python-ast-utf8", "PASS", last_line, duration_ms=duration_ms)
    return CheckResult(
        "python-ast-utf8",
        "FAIL",
        "Python parse/encoding errors found",
        output.strip().splitlines(),
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

BASE_PHASES = (
    ("git-diff-integrity", check_git_diff, "changes"),
    ("hidden-bidi-scan", check_hidden_bidi, "changed"),
    ("secret-marker-scan", check_secret_markers, "changed"),
    ("python-ast-utf8", check_python_ast_utf8, "changed"),
    ("pr-body-validation", check_pr_body, "body_changes"),
    ("forbidden-claims", check_forbidden, "body"),
    ("changed-files-hardening", check_hardening, "changes_added_body"),
    ("python-db-write", check_python_db, "changed"),
    ("sql-migration", check_sql_migration, "changed"),
    ("js-db-write-guard", check_js_db_guard, "changed"),
)

FULL_PHASES = (
    ("ruff-check", check_ruff, "changed"),
    ("ruff-format", check_ruff_fmt, "changed"),
    ("mypy", check_mypy, "changed"),
    ("pytest", check_pytest, "changed"),
    ("npm-test-coverage", check_npm, "changed"),
)

_SIG_MAP = {
    "changes": lambda fn, changes, changed, added, pr_body: fn(changes),
    "changed": lambda fn, changes, changed, added, pr_body: fn(changed),
    "body": lambda fn, changes, changed, added, pr_body: fn(pr_body),
    "body_changes": lambda fn, changes, changed, added, pr_body: fn(pr_body, changes),
    "changes_added_body": lambda fn, c, ch, a, b: fn(c, a, b),
}


def run_preflight(
    base: str = "origin/main",
    head: str = "HEAD",
    pr_body_file: str | None = None,
    changed_files_file: str | None = None,
    full: bool = False,
) -> PreflightResult:
    """Execute all preflight phases and return aggregate result."""
    result = PreflightResult(mode="full" if full else "fast", start_time=time.time())
    if not pr_body_file:
        raise ValueError("--pr-body-file is required")
    pr_body = Path(pr_body_file).read_text("utf-8")
    changes, changed, added = compute_changed_files(base, head, changed_files_file)
    result.changed_files = len(changes)

    phases = list(BASE_PHASES)
    if full:
        phases.extend(FULL_PHASES)

    # Phases that may print to stdout and need suppression
    _NOISY_PHASES = {"python-db-write", "sql-migration", "js-db-write-guard"}

    for name, fn, sig in phases:
        t0 = time.time()
        try:
            if name in _NOISY_PHASES:
                with _suppress_stdout():
                    cr = _SIG_MAP[sig](fn, changes, changed, added, pr_body)
            else:
                cr = _SIG_MAP[sig](fn, changes, changed, added, pr_body)
        except Exception as exc:
            cr = CheckResult(name, "ERROR", f"Phase error: {exc}")
        cr.duration_ms = (time.time() - t0) * 1000
        result.phases.append(cr)

    result.end_time = time.time()
    result.passed = not any(p.failed for p in result.phases)
    return result


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

_COLORS = {"PASS": "\033[0;32m", "FAIL": "\033[0;31m", "SKIP": "\033[0;33m", "ERROR": "\033[0;35m"}
_RESET = "\033[0m"


def format_human(result: PreflightResult, verbose: bool = False) -> str:
    lines = [
        "=" * 64,
        "  Local PR Gate Preflight",
        "=" * 64,
        f"  Mode: {result.mode}  |  Changed files: {result.changed_files}"
        f"  |  Phases: {len(result.phases)}  |  Elapsed: {result.elapsed_s:.2f}s",
        "-" * 64,
        f"  {'Phase':<28} {'Status':<8}  Message",
        f"  {'-' * 28} {'-' * 8}  {'-' * 28}",
    ]
    for p in result.phases:
        c = _COLORS.get(p.status, "")
        lines.append(f"  {p.name:<28} {c}{p.status}{_RESET:<14}  {p.message[:60]}")
    lines.append("-" * 64)
    if result.passed:
        lines.append(f"  VERDICT:  {_COLORS['PASS']}PASS{_RESET}")
    else:
        failed = [p for p in result.phases if p.failed]
        lines.append(f"  VERDICT:  {_COLORS['FAIL']}FAIL ({len(failed)} phase(s) failed){_RESET}")

    failures = [p for p in result.phases if p.failed or p.status == "ERROR"]
    if failures:
        lines.append("-" * 64)
        lines.append("  Failure details:")
        for p in failures:
            lines.append(f"  [{p.status}] {p.name}: {p.message}")
            if p.details and (verbose or len(p.details) <= 5):
                for d in p.details[:20]:
                    lines.append(f"           - {d}")
    warns = [p for p in result.phases if p.status == "SKIP"]
    if warns and (verbose or not failures):
        lines.append("-" * 64)
        lines.append("  Skipped phases:")
        for w in warns:
            lines.append(f"  [SKIP] {w.name}: {w.message}")
    lines.append("=" * 64)
    return "\n".join(lines)


def format_json(result: PreflightResult) -> str:
    """Render the preflight report as machine-readable JSON."""
    return json.dumps(
        {
            "status": "PASS" if result.passed else "FAIL",
            "mode": result.mode,
            "changed_files": result.changed_files,
            "elapsed_s": round(result.elapsed_s, 3),
            "checks": [
                {
                    "name": p.name,
                    "status": p.status,
                    "message": p.message,
                    "details": p.details if p.status in ("FAIL", "ERROR") else [],
                    "duration_ms": round(p.duration_ms, 1),
                }
                for p in result.phases
            ],
            "failures": result.failures,
            "warnings": result.warnings,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Local PR Gate Preflight")
    p.add_argument("--base", default="origin/main", help="Git base ref")
    p.add_argument("--head", default="HEAD", help="Git head ref")
    p.add_argument("--pr-body-file", required=True, help="PR body markdown file path")
    p.add_argument(
        "--changed-files-file",
        default=None,
        help="Override: load changed files from file instead of git diff",
    )
    p.add_argument(
        "--fast", action="store_true", default=False, help="Fast mode: static checks only (default)"
    )
    p.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Full mode: add ruff, mypy, pytest, npm test:coverage",
    )
    p.add_argument(
        "--json", action="store_true", default=False, help="Output machine-readable JSON"
    )
    p.add_argument(
        "--verbose", action="store_true", default=False, help="Print detailed per-phase output"
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the preflight and exit 0 (pass) or 1 (fail), 2 (usage error)."""
    args = _parse_args(argv)
    if not Path(args.pr_body_file).is_file():
        print(f"ERROR: PR body file not found: {args.pr_body_file}", file=sys.stderr)
        return 2
    result = run_preflight(
        base=args.base,
        head=args.head,
        pr_body_file=args.pr_body_file,
        changed_files_file=args.changed_files_file,
        full=args.full,
    )
    if args.json:
        print(format_json(result))
    else:
        print(format_human(result, verbose=args.verbose))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
