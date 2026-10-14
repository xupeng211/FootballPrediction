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
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = Path(__file__).resolve().parents[2]

# 可信模式由真实只读加载位置决定；环境变量不授予该身份。
TRUSTED_INFRA_ROOT = Path("/snapshot")
CANDIDATE_WORK_ROOT = Path("/app")
TRUSTED_NODE = "/usr/local/bin/node"
TRUSTED_TOOLS = {
    "eslint": "/opt/cmh/node_modules/eslint/bin/eslint.js",
    "c8": "/opt/cmh/node_modules/c8/bin/c8.js",
}
IMAGE_DEPENDENCY_ROOT = Path("/opt/cmh")
QA_ANCHORS = (
    "package.json",
    "package-lock.json",
    ".eslintrc.json",
)
TRUSTED_PATH = "/usr/local/bin:/usr/bin:/bin"
LINT_ARGS = [
    "src/**/*.js",
    "config/**/*.js",
    "scripts/ops/**/*.js",
    "scripts/maintenance/**/*.js",
    "scripts/test/**/*.js",
    "--cache",
    "--cache-location",
    ".eslintcache",
]
RECON_ARGS = [
    "--all",
    "--include=src/infrastructure/recon/services/ReconDecryptorSourceExtractor.js",
    "--include=src/infrastructure/recon/services/ReconSourceProber.js",
    "--include=src/infrastructure/recon/services/ReconMatrixTargetRunner.js",
    "--include=src/infrastructure/recon/ReconDistributedLock.js",
    "--include=src/infrastructure/recon/services/ReconPureDecryptorRuntime.js",
    "--reporter=text-summary",
    "--reporter=json-summary",
    "--reports-dir",
    "reports/coverage/recon-core",
]


def _trusted_mode() -> bool:
    return Path(__file__).absolute() == TRUSTED_INFRA_ROOT / "scripts/devops/validation_profiles.py"


def _mounts() -> dict[Path, tuple[set[str], str]]:
    mounts = {}
    for line in Path("/proc/self/mountinfo").read_text().splitlines():
        fields = line.split()
        separator = fields.index("-")
        name = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
        mounts[Path(name)] = (set(fields[5].split(",")), fields[separator + 1])
    return mounts


def _require_readonly(path: Path, mounts) -> None:
    parents = [root for root in mounts if path == root or root in path.parents]
    if not parents or "ro" not in mounts[max(parents, key=lambda root: len(root.parts))][0]:
        raise ValueError(f"QA identity is not on a real read-only mount: {path}")


def verify_trusted_boundary() -> dict:
    """核验实际 mount、Git 身份及只读配置；不声称隔离所有恶意测试行为。"""
    if not _trusted_mode() or Path(__file__).resolve() != Path(__file__).absolute():
        raise ValueError("trusted dispatcher must be loaded from the physical /snapshot")
    mounts = _mounts()
    _require_readonly(Path("/"), mounts)
    _require_readonly(TRUSTED_INFRA_ROOT, mounts)
    if TRUSTED_INFRA_ROOT not in mounts:
        raise ValueError("missing snapshot mount")
    app_options, app_type = mounts.get(CANDIDATE_WORK_ROOT, (set(), ""))
    if app_type != "tmpfs" or not {"rw", "noexec", "nosuid"} <= app_options:
        raise ValueError("candidate tmpfs/noexec contract mismatch")
    binding_root = TRUSTED_INFRA_ROOT / ".git/cmh-qa"
    binding_path = binding_root / "binding.json"
    _require_readonly(binding_path, mounts)
    if binding_path.resolve() != binding_path:
        raise ValueError("binding path is not physical")
    binding: dict = json.loads(binding_path.read_text())
    if (
        not re.fullmatch(r"[0-9a-f]{40}", binding["head"])
        or not re.fullmatch(r"[0-9a-f]{40}", binding["tree"])
        or not re.fullmatch(r"[a-zA-Z0-9./_-]+@sha256:[0-9a-f]{64}", binding["image"])
    ):
        raise ValueError("invalid frozen identity")
    _verify_binding_files(binding, mounts)
    for expression, expected in (("HEAD", binding["head"]), ("HEAD^{tree}", binding["tree"])):
        actual = subprocess.check_output(
            [
                "/usr/bin/git",
                "-c",
                "safe.directory=/snapshot",
                "-C",
                "/snapshot",
                "rev-parse",
                expression,
            ],
            env=_trusted_environment(),
            text=True,
        ).strip()
        if actual != expected:
            raise ValueError("snapshot HEAD/tree mismatch")
    _verify_image_tools(mounts)
    _verify_frozen_scripts()
    return binding


def _verify_image_tools(mounts) -> None:
    for executable in (TRUSTED_NODE, *TRUSTED_TOOLS.values()):
        path = Path(executable)
        _require_readonly(path, mounts)
        if path.resolve() != path or not path.is_file() or not os.access(path, os.R_OK):
            raise ValueError(f"trusted image tool missing or redirected: {path}")
    if not os.access(TRUSTED_NODE, os.X_OK):
        raise ValueError("trusted Node interpreter is not executable")


def _verify_binding_files(binding: dict, mounts) -> None:
    expected_files = {
        "scripts/devops/validation_profiles.py",
        "scripts/devops/gatekeeper.sh",
        ".eslintrc.json",
        "package.json",
        "package-lock.json",
        "requirements.txt",
        ".git/cmh-qa/eslint-ignore",
        ".git/cmh-qa/c8.json",
    }
    if set(binding["files"]) != expected_files:
        raise ValueError("incomplete trusted binding")
    for name, expected in binding["files"].items():
        path = TRUSTED_INFRA_ROOT / name
        _require_readonly(path, mounts)
        if path.resolve() != path or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"frozen QA source mismatch: {name}")
    for name in QA_ANCHORS:
        path = CANDIDATE_WORK_ROOT / name
        _require_readonly(path, mounts)
        if (
            path not in mounts
            or path.resolve() != path
            or hashlib.sha256(path.read_bytes()).hexdigest() != binding["files"][name]
        ):
            raise ValueError(f"candidate configuration anchor mismatch: {name}")


def _verify_frozen_scripts() -> None:
    package = json.loads((TRUSTED_INFRA_ROOT / "package.json").read_text())
    lint = ["eslint", *LINT_ARGS]
    recon = [
        "rm",
        "-rf",
        "reports/coverage/recon-core",
        "&&",
        "c8",
        *RECON_ARGS,
        "node",
        "scripts/test/run_test_suite.js",
        "recon-core",
        "&&",
        "node",
        "scripts/test/check_recon_core_coverage.js",
    ]
    if (
        shlex.split(package["scripts"]["lint"]) != lint
        or shlex.split(package["scripts"]["test:coverage:recon-core"]) != recon
        or package["scripts"]["test:coverage"] != "node scripts/test/run_test_suite.js coverage"
        or any(key in package for key in ("c8", "nyc", "eslintConfig", "eslintIgnore"))
    ):
        raise ValueError("frozen npm QA contract mismatch")


def _trusted_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in (
        "NODE_OPTIONS",
        "NODE_PATH",
        "NODE_V8_COVERAGE",
        "BASH_ENV",
        "ENV",
        "PYTHONPATH",
        "PYTHONHOME",
        "LD_PRELOAD",
        "LD_LIBRARY_PATH",
        "GATEKEEPER_LOCAL_CI",
        "GATEKEEPER_DIRECT_MODE",
        "GATEKEEPER_LOCAL_CI_ACTIVE",
        "GATEKEEPER_PYTHON_BIN",
        "GATEKEEPER_LOCAL_HOOK_ACTIVE",
    ):
        environment.pop(key, None)
    environment["PATH"] = TRUSTED_PATH
    return environment


def verify_trusted_dependencies() -> None:
    """只核验冻结依赖，任何失配都禁止安装与 fallback。"""
    binding = verify_trusted_boundary()
    expected = binding["files"]["package-lock.json"]
    stamp = CANDIDATE_WORK_ROOT / "node_modules/.package-lock.sha256"
    if stamp.is_symlink() or stamp.read_text().strip() != expected:
        raise ValueError("dependency stamp mismatch; installation forbidden")
    image_root = IMAGE_DEPENDENCY_ROOT
    mounts = _mounts()
    for name in ("package-lock.json", "requirements.txt"):
        path = image_root / name
        _require_readonly(path, mounts)
        if (
            path.resolve() != path
            or hashlib.sha256(path.read_bytes()).hexdigest() != binding["files"][name]
        ):
            raise ValueError("image dependency lock mismatch")
    lock = json.loads((image_root / "package-lock.json").read_text())
    for name in (
        "eslint",
        "c8",
        "eslint-plugin-jsdoc",
        "http-proxy-agent",
        "https-proxy-agent",
        "socks-proxy-agent",
    ):
        path = image_root / "node_modules" / name / "package.json"
        _require_readonly(path, mounts)
        if (
            path.resolve() != path
            or json.loads(path.read_text())["version"]
            != lock["packages"][f"node_modules/{name}"]["version"]
        ):
            raise ValueError(f"trusted tool/plugin dependency mismatch: {name}")
    # 候选依赖仍供原测试加载；可信 QA 的执行身份不会从其 .bin 选择。
    for name in ("eslint", "c8", "http-proxy-agent", "https-proxy-agent", "socks-proxy-agent"):
        path = CANDIDATE_WORK_ROOT / "node_modules" / name / "package.json"
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(CANDIDATE_WORK_ROOT / "node_modules")
            or json.loads(path.read_text())["version"]
            != lock["packages"][f"node_modules/{name}"]["version"]
        ):
            raise ValueError(f"candidate locked dependency missing: {name}")


def trusted_lint_argv() -> list[str]:
    """保持 lint 参数与配置相对路径，固定镜像内工具及插件。"""
    # 配置放在只读 /app 锚点，保留 overrides 相对于项目根的原有语义。
    return [
        TRUSTED_NODE,
        TRUSTED_TOOLS["eslint"],
        *LINT_ARGS,
        "--no-eslintrc",
        "--config",
        "/app/.eslintrc.json",
        "--resolve-plugins-relative-to",
        "/opt/cmh",
        "--ignore-path",
        "/snapshot/.git/cmh-qa/eslint-ignore",
    ]


def trusted_recon_argv() -> list[str]:
    """保持五组 include、报告和原 Node 子进程合同。"""
    return [
        TRUSTED_NODE,
        TRUSTED_TOOLS["c8"],
        "--config",
        "/snapshot/.git/cmh-qa/c8.json",
        *RECON_ARGS,
        TRUSTED_NODE,
        "scripts/test/run_test_suite.js",
        "recon-core",
    ]


def run_trusted_tool(tool: str) -> int:
    """只读加载位置验证后执行两个既有 QA 工具。"""
    verify_trusted_dependencies()
    environment = _trusted_environment()
    if tool == "check":
        return 0
    if tool == "lint":
        argv = trusted_lint_argv()
    elif tool == "recon-core":
        reports = CANDIDATE_WORK_ROOT / "reports/coverage/recon-core"
        if reports.exists():
            shutil.rmtree(reports)
        argv = trusted_recon_argv()
    else:
        raise ValueError("unknown trusted tool")
    status = subprocess.run(argv, cwd=CANDIDATE_WORK_ROOT, env=environment, check=False).returncode
    if status == 0 and tool == "recon-core":
        status = subprocess.run(
            [TRUSTED_NODE, "scripts/test/check_recon_core_coverage.js"],
            cwd=CANDIDATE_WORK_ROOT,
            env=environment,
            check=False,
        ).returncode
    return status


PUBLIC_PROFILES: tuple[str, ...] = ("targeted", "pr", "strict")
PYTHON_CODE_PREFIXES: tuple[str, ...] = ("src/", "scripts/", "tests/")
JS_TRIGGER_SUFFIXES: frozenset[str] = frozenset({".cjs", ".js", ".json", ".mjs"})
JS_TRIGGER_FILES: frozenset[str] = frozenset({"package.json", "package-lock.json"})


def _ensure_locked_node_dependencies() -> int:
    """Install and verify the exact lockfile dependency tree before JS checks."""
    if _trusted_mode():
        verify_trusted_dependencies()
        return 0
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
        cwd=CANDIDATE_WORK_ROOT if _trusted_mode() else ROOT,
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
        cwd=CANDIDATE_WORK_ROOT if _trusted_mode() else ROOT,
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
            cwd=CANDIDATE_WORK_ROOT if _trusted_mode() else ROOT,
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
    environment = None
    if _trusted_mode():
        verify_trusted_dependencies()
        environment = _trusted_environment()
        if gatekeeper:
            argv = ["/bin/bash", "-p", "/snapshot/scripts/devops/gatekeeper.sh", *argv[2:]]
            environment["GATEKEEPER_IN_CONTAINER"] = "1"
            environment["GATEKEEPER_WORKSPACE_ROOT"] = "/app"
        elif list(argv) == ["npm", "run", "lint"]:
            argv = trusted_lint_argv()
        elif argv[0] == "node":
            argv = [TRUSTED_NODE, *argv[1:]]
    elif gatekeeper:
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

    rendered = " ".join(shlex.quote(part) for part in argv)
    print(f"[Validation] {label}: {rendered}", flush=True)
    try:
        result = subprocess.run(
            argv, cwd=CANDIDATE_WORK_ROOT if _trusted_mode() else ROOT, env=environment, check=False
        )
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
    parser.add_argument("profile", choices=PUBLIC_PROFILES, nargs="?")
    parser.add_argument("--trusted-tool", choices=("check", "lint", "recon-core"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Parse the profile name and return the canonical runner status."""
    args = build_parser().parse_args(argv)
    if (args.profile is None) == (args.trusted_tool is None):
        build_parser().error("select exactly one profile or authenticated trusted tool")
    if args.trusted_tool is None and not _trusted_mode():
        return run_profile(args.profile)
    try:
        if args.trusted_tool:
            return run_trusted_tool(args.trusted_tool)
        if _trusted_mode():
            verify_trusted_dependencies()
        return run_profile(args.profile)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"[Validation] trusted QA rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
