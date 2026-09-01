#!/usr/bin/env python3
"""Canonical validation profile dispatcher.

lifecycle: permanent

The public validation surface has exactly three profiles:

* ``targeted`` — affected checks for fast local feedback;
* ``pr`` — the existing strict PR gatekeeper implementation;
* ``strict`` — the existing full push gatekeeper implementation.

This file owns profile selection and failure propagation. The underlying
gatekeeper remains the implementation of the repository's established static,
test, coverage, and integrity checks; it is deliberately not reimplemented
here.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[2]

PUBLIC_PROFILES: tuple[str, ...] = ("targeted", "pr", "strict")
PYTHON_CODE_PREFIXES: tuple[str, ...] = ("src/", "scripts/", "tests/")
JS_TRIGGER_SUFFIXES: frozenset[str] = frozenset({".cjs", ".js", ".json", ".mjs"})
JS_TRIGGER_FILES: frozenset[str] = frozenset({"package.json", "package-lock.json"})


def _ensure_locked_node_dependencies() -> int:
    """Install and verify the exact lockfile dependency tree before JS checks."""
    lock_path = ROOT / "package-lock.json"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        expected = lock["packages"]["node_modules/eslint"]["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"[Validation] cannot resolve lockfile ESLint version: {exc}", file=sys.stderr)
        return 2

    installed_path = ROOT / "node_modules" / "eslint" / "package.json"
    try:
        installed = json.loads(installed_path.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        installed = None

    if installed != expected:
        print(
            f"[Validation] initializing repository-locked Node dependencies "
            f"(ESLint {expected}, found {installed or 'none'}).",
            flush=True,
        )
        result = subprocess.run(
            ["npm", "ci", "--ignore-scripts", "--no-fund", "--no-audit"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            print("[Validation] npm ci failed; refusing any global tool fallback.", file=sys.stderr)
            return result.returncode

    try:
        installed = json.loads(installed_path.read_text(encoding="utf-8"))["version"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(
            f"[Validation] repository-local ESLint is unavailable after npm ci: {exc}",
            file=sys.stderr,
        )
        return 2
    if installed != expected:
        print(
            f"[Validation] repository-local ESLint {installed} != lockfile {expected}.",
            file=sys.stderr,
        )
        return 2
    print(f"[Validation] repository-local ESLint={installed} (lockfile exact).", flush=True)
    return 0


def _git_output(args: Sequence[str]) -> str:
    """Return Git stdout, or an empty string when a read-only probe fails."""
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def _git_ref_exists(ref: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", ref],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _resolve_branch_base() -> str | None:
    """Resolve a read-only comparison base for committed branch changes."""
    candidates: list[str] = []
    github_base = os.environ.get("GITHUB_BASE_REF", "").strip()
    if github_base:
        candidates.append(f"origin/{github_base}")
    candidates.extend(("origin/main", "main"))

    for candidate in candidates:
        if not _git_ref_exists(candidate):
            continue
        result = subprocess.run(
            ["git", "merge-base", "HEAD", candidate],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()

    if _git_ref_exists("HEAD~1"):
        return "HEAD~1"
    return None


def collect_changed_files() -> list[str]:
    """Collect branch, staged, unstaged, and untracked paths without mutation."""
    changed: set[str] = set()
    base = _resolve_branch_base()
    if base:
        changed.update(
            line.strip()
            for line in _git_output(
                ["diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"]
            ).splitlines()
            if line.strip()
        )

    changed.update(
        line.strip()
        for line in _git_output(["diff", "--name-only", "--diff-filter=ACMR", "HEAD"]).splitlines()
        if line.strip()
    )
    changed.update(
        line.strip()
        for line in _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
        if line.strip()
    )
    return sorted(changed)


def _is_python_path(path: str) -> bool:
    return path.endswith(".py") and path.startswith(PYTHON_CODE_PREFIXES)


def _is_python_runtime_path(path: str) -> bool:
    return _is_python_path(path) and not path.startswith("tests/")


def _is_js_trigger_path(path: str) -> bool:
    return path in JS_TRIGGER_FILES or Path(path).suffix in JS_TRIGGER_SUFFIXES


def _running_in_container() -> bool:
    """Return whether this dispatcher is already inside the dev container."""
    return Path("/.dockerenv").exists() or os.environ.get("GATEKEEPER_IN_CONTAINER") == "1"


def _profile_command_plan(
    profile: str,
    changed_files: Sequence[str],
) -> list[tuple[str, list[str], bool]]:
    """Build ``(label, argv, gatekeeper)`` commands for one profile."""
    if profile == "pr":
        return [
            (
                "PR Production Gate implementation",
                ["bash", "scripts/devops/gatekeeper.sh", "--mode=pr"],
                True,
            )
        ]

    if profile == "strict":
        return [
            (
                "full Production Gate implementation",
                ["bash", "scripts/devops/gatekeeper.sh", "--mode=push"],
                True,
            )
        ]

    if profile != "targeted":
        raise ValueError(f"unsupported validation profile: {profile}")

    commands: list[tuple[str, list[str], bool]] = []
    python_files = [path for path in changed_files if _is_python_path(path)]
    python_runtime_changed = any(_is_python_runtime_path(path) for path in changed_files)
    js_changed = any(_is_js_trigger_path(path) for path in changed_files)

    if js_changed:
        commands.append(("JavaScript static check", ["npm", "run", "lint"], False))

    if python_files:
        commands.extend(
            (
                (
                    "Python changed-line static check",
                    [
                        sys.executable,
                        "scripts/devops/static_quality_changed_lines.py",
                        *python_files,
                    ],
                    False,
                ),
                (
                    "Python format check",
                    [sys.executable, "-m", "ruff", "format", "--check", *python_files],
                    False,
                ),
            )
        )

        direct_python_tests = [
            path for path in changed_files if path.startswith("tests/") and path.endswith(".py")
        ]
        if direct_python_tests:
            commands.append(
                (
                    "changed Python tests",
                    [sys.executable, "-m", "pytest", "-q", *direct_python_tests],
                    False,
                )
            )
        elif python_runtime_changed:
            # There is no repository-wide Python dependency graph. Full unit
            # coverage is the fail-safe fallback when no direct test target is
            # discoverable; it is still limited to unit tests, not live flows.
            commands.append(
                (
                    "Python unit fallback",
                    [sys.executable, "-m", "pytest", "-q", "tests/unit"],
                    False,
                )
            )

    if js_changed:
        commands.append(
            (
                "affected JavaScript tests",
                ["node", "scripts/test/run_test_suite.js", "affected", *changed_files],
                False,
            )
        )

    return commands


def _normalise_profile(profile: str) -> str:
    normalised = profile.strip().lower()
    if normalised not in PUBLIC_PROFILES:
        choices = ", ".join(PUBLIC_PROFILES)
        raise ValueError(f"profile must be one of: {choices}")
    return normalised


def _run_command(label: str, argv: Sequence[str], *, gatekeeper: bool) -> int:
    """Run one command and return its exact exit status."""
    rendered = " ".join(shlex.quote(part) for part in argv)
    print(f"[Validation] {label}: {rendered}", flush=True)
    environment = None
    if gatekeeper:
        environment = os.environ.copy()
        # Make invokes this file inside dev, while GitHub Actions invokes it
        # from the runner before the existing gatekeeper enters dev. Preserve
        # both paths: only suppress nested Docker when already containerized.
        if _running_in_container():
            environment["GATEKEEPER_IN_CONTAINER"] = "1"
            environment["GATEKEEPER_WORKSPACE_ROOT"] = str(ROOT)
        else:
            environment.pop("GATEKEEPER_IN_CONTAINER", None)
            environment.pop("GATEKEEPER_WORKSPACE_ROOT", None)

    try:
        result = subprocess.run(argv, cwd=ROOT, env=environment, check=False)
    except OSError as exc:
        print(f"[Validation] {label} failed to start: {exc}", file=sys.stderr)
        return 127

    if result.returncode != 0:
        print(f"[Validation] {label} failed with exit code {result.returncode}.", file=sys.stderr)
    return result.returncode


def run_profile(profile: str, changed_files: Sequence[str] | None = None) -> int:
    """Run one canonical profile and fail closed on the first failed command."""
    normalised = _normalise_profile(profile)
    paths = list(changed_files) if changed_files is not None else collect_changed_files()
    print(f"[Validation] profile={normalised} changed_files={len(paths)}", flush=True)

    commands = _profile_command_plan(normalised, paths)
    if not commands:
        print("[Validation] no targeted runtime/test paths; profile is a no-op.", flush=True)
        return 0

    if normalised == "targeted" and any(_is_js_trigger_path(path) for path in paths):
        dependency_status = _ensure_locked_node_dependencies()
        if dependency_status != 0:
            return dependency_status

    for label, argv, gatekeeper in commands:
        status = _run_command(label, argv, gatekeeper=gatekeeper)
        if status != 0:
            return status
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the three public profiles."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PUBLIC_PROFILES)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the profile name and return the canonical runner status."""
    args = build_parser().parse_args(argv)
    return run_profile(args.profile)


if __name__ == "__main__":
    raise SystemExit(main())
