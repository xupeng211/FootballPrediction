"""Tests for the canonical validation profile dispatcher.

lifecycle: test-fixture
"""

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/devops"))
import validation_profiles as profiles  # noqa: E402


def test_public_profile_surface_has_exactly_three_entries():
    assert profiles.PUBLIC_PROFILES == ("targeted", "pr", "strict")


def test_pr_and_strict_profiles_delegate_to_existing_gatekeeper_modes():
    pr_plan = profiles._profile_command_plan("pr", [])
    strict_plan = profiles._profile_command_plan("strict", [])

    assert pr_plan[0][1] == ["bash", "scripts/devops/gatekeeper.sh", "--mode=pr"]
    assert strict_plan[0][1] == ["bash", "scripts/devops/gatekeeper.sh", "--mode=push"]
    assert pr_plan[0][2] is True
    assert strict_plan[0][2] is True


def test_targeted_profile_selects_static_and_affected_test_commands():
    plan = profiles._profile_command_plan(
        "targeted",
        [
            "src/example.js",
            "scripts/example.py",
            "tests/unit/test_example.py",
        ],
    )
    labels = [label for label, _argv, _gatekeeper in plan]
    commands = [argv for _label, argv, _gatekeeper in plan]

    assert "JavaScript static check" in labels
    assert "Python changed-line static check" in labels
    assert "Python format check" in labels
    assert "changed Python tests" in labels
    assert "affected JavaScript tests" in labels
    assert ["npm", "run", "lint"] in commands


def test_profile_runner_propagates_required_failure_and_stops():
    calls: list[str] = []
    expected_status = 23

    def fake_run(label, _argv, *, gatekeeper):
        calls.append(label)
        assert gatekeeper is True
        return expected_status

    with (
        patch.object(
            profiles,
            "_profile_command_plan",
            return_value=[("canonical gate", ["false"], True), ("must not run", ["true"], True)],
        ),
        patch.object(profiles, "_run_command", side_effect=fake_run),
    ):
        status = profiles.run_profile("pr", [])

    assert status == expected_status
    assert calls == ["canonical gate"]


def test_locked_node_dependency_guard_initializes_missing_tree_and_rejects_global_fallback(
    tmp_path,
):
    expected = "8.57.1"
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"packages": {"node_modules/eslint": {"version": expected}}}),
        encoding="utf-8",
    )

    def fake_ci(argv, **_kwargs):
        assert argv == ["npm", "ci", "--ignore-scripts", "--no-fund", "--no-audit"]
        target = tmp_path / "node_modules/eslint"
        target.mkdir(parents=True)
        (target / "package.json").write_text(json.dumps({"version": expected}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    with (
        patch.object(profiles, "ROOT", tmp_path),
        patch.object(profiles.subprocess, "run", side_effect=fake_ci),
    ):
        assert profiles._ensure_locked_node_dependencies() == 0


def test_targeted_js_profile_stops_when_locked_dependency_initialization_fails():
    expected_status = 41
    with (
        patch.object(profiles, "_ensure_locked_node_dependencies", return_value=expected_status),
        patch.object(profiles, "_run_command") as run_command,
    ):
        assert profiles.run_profile("targeted", ["src/example.js"]) == expected_status
    run_command.assert_not_called()


def test_gatekeeper_dispatch_preserves_host_container_boundary():
    captured_environments: list[dict[str, str]] = []

    def fake_subprocess(_argv, **kwargs):
        captured_environments.append(kwargs["env"])
        return SimpleNamespace(returncode=0)

    with (
        patch.dict(
            profiles.os.environ,
            {"GATEKEEPER_IN_CONTAINER": "0", "GATEKEEPER_WORKSPACE_ROOT": "/host"},
            clear=True,
        ),
        patch.object(profiles, "_running_in_container", return_value=False),
        patch.object(profiles.subprocess, "run", side_effect=fake_subprocess),
    ):
        assert profiles._run_command("host gate", ["true"], gatekeeper=True) == 0

    assert "GATEKEEPER_IN_CONTAINER" not in captured_environments[0]
    assert "GATEKEEPER_WORKSPACE_ROOT" not in captured_environments[0]

    with (
        patch.object(profiles, "_running_in_container", return_value=True),
        patch.object(profiles.subprocess, "run", side_effect=fake_subprocess),
    ):
        assert profiles._run_command("container gate", ["true"], gatekeeper=True) == 0

    assert captured_environments[1]["GATEKEEPER_IN_CONTAINER"] == "1"
    assert captured_environments[1]["GATEKEEPER_WORKSPACE_ROOT"] == str(profiles.ROOT)


def test_make_compatibility_entries_delegate_to_verify_pr():
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert (
        "ci-local: ## 兼容入口：运行 canonical PR 验证（失败返回非零）\n\t@$(MAKE) verify-pr"
        in makefile
    )
    assert "ci-local-pr: ## 兼容入口：运行 canonical PR 验证\n\t@$(MAKE) verify-pr" in makefile
    assert "compatibility alias -> verify-pr" in makefile


def test_production_gate_calls_canonical_dispatcher():
    workflow = (ROOT / ".github/workflows/production-gate.yml").read_text(encoding="utf-8")

    assert 'python3 scripts/devops/validation_profiles.py "${validation_profile}"' in workflow
    assert 'bash scripts/devops/gatekeeper.sh --mode="${GATEKEEPER_CI_MODE}"' not in workflow


@pytest.fixture
def trusted_boundary(tmp_path):
    """仅离线文件/mountinfo 替身；不启动 Docker 或 profile。"""
    infra, app, image = (tmp_path / name for name in ("snapshot", "app", "image"))
    infra.mkdir()
    app.mkdir()
    image.mkdir()
    files = [
        "scripts/devops/validation_profiles.py",
        "scripts/devops/gatekeeper.sh",
        *profiles.QA_ANCHORS,
        "requirements.txt",
        ".git/cmh-qa/eslint-ignore",
        ".git/cmh-qa/c8.json",
    ]
    files = sorted(set(files))
    package = json.loads((ROOT / "package.json").read_text())
    packages = {
        f"node_modules/{name}": {"version": "fixture-locked"}
        for name in (
            "eslint",
            "c8",
            "eslint-plugin-jsdoc",
            "http-proxy-agent",
            "https-proxy-agent",
            "socks-proxy-agent",
        )
    }
    contents = dict.fromkeys(files, b"frozen fixture")
    contents.update(
        {
            "package.json": json.dumps(package).encode(),
            "package-lock.json": json.dumps({"packages": packages}).encode(),
            ".git/cmh-qa/c8.json": b"{}\n",
            ".git/cmh-qa/eslint-ignore": b"",
        }
    )
    mounts = {
        Path("/"): ({"ro"}, "overlay"),
        infra: ({"ro"}, "ext4"),
        app: ({"rw", "noexec", "nosuid"}, "tmpfs"),
        image: ({"ro"}, "overlay"),
    }
    for name, content in contents.items():
        path = infra / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        if name in profiles.QA_ANCHORS:
            candidate = app / name
            candidate.parent.mkdir(parents=True, exist_ok=True)
            candidate.write_bytes(content)
            mounts[candidate] = ({"ro"}, "ext4")
    binding = {
        "head": "a" * 40,
        "tree": "b" * 40,
        "image": "qa@sha256:" + "c" * 64,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()},
    }
    (infra / ".git/cmh-qa/binding.json").write_text(json.dumps(binding))
    for name in ("package-lock.json", "requirements.txt"):
        (image / name).write_bytes(contents[name])
    for name, package_version in packages.items():
        path = image / name / "package.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(package_version))
        candidate = app / name / "package.json"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(json.dumps(package_version))
    stamp = app / "node_modules/.package-lock.sha256"
    stamp.write_text(binding["files"]["package-lock.json"] + "\n")
    node = image / "node"
    node.write_text("fixture interpreter")
    node.chmod(0o755)
    tools = {
        name: str(image / "node_modules" / name / "bin" / (name + ".js"))
        for name in ("eslint", "c8")
    }
    for path in tools.values():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("fixture trusted tool")

    def git_identity(argv, **_kwargs):
        return binding["tree" if argv[-1] == "HEAD^{tree}" else "head"] + "\n"

    with ExitStack() as stack:
        for name, value in (
            ("TRUSTED_INFRA_ROOT", infra),
            ("CANDIDATE_WORK_ROOT", app),
            ("IMAGE_DEPENDENCY_ROOT", image),
            ("TRUSTED_NODE", str(node)),
            ("TRUSTED_TOOLS", tools),
            ("__file__", str(infra / "scripts/devops/validation_profiles.py")),
        ):
            stack.enter_context(patch.object(profiles, name, value))
        stack.enter_context(patch.object(profiles, "_mounts", return_value=mounts))
        stack.enter_context(
            patch.object(profiles.subprocess, "check_output", side_effect=git_identity)
        )
        yield SimpleNamespace(
            infra=infra, app=app, image=image, binding=binding, mounts=mounts, stamp=stamp
        )


def test_trusted_startup_ignores_candidate_scripts_bin_and_path(trusted_boundary):
    fixture = trusted_boundary
    for name in ("eslint", "c8"):
        path = fixture.app / "node_modules/.bin" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(fixture.app / "evil-interpreter")
    (fixture.app / "scripts/devops").mkdir(parents=True)
    (fixture.app / "scripts/devops/gatekeeper.sh").write_text("replaced gate")
    (fixture.app / "scripts/devops/validation_profiles.py").write_text("replaced profile")
    captured = []

    def run(argv, **kwargs):
        captured.append((argv, kwargs))
        return SimpleNamespace(returncode=0)

    with (
        patch.dict(
            os.environ,
            {
                "PATH": "/app/evil",
                "NODE_OPTIONS": "--require=/app/evil",
                "GATEKEEPER_LOCAL_CI_ACTIVE": "1",
                "BASH_ENV": "/app/evil",
            },
        ),
        patch.object(profiles.subprocess, "run", side_effect=run),
    ):
        assert (
            profiles._run_command(
                "gate", ["bash", "scripts/devops/gatekeeper.sh", "--mode=pr"], gatekeeper=True
            )
            == 0
        )
        assert profiles.run_trusted_tool("lint") == 0
        assert profiles.run_trusted_tool("recon-core") == 0
    assert captured[0][0] == [
        "/bin/bash",
        "-p",
        "/snapshot/scripts/devops/gatekeeper.sh",
        "--mode=pr",
    ]
    assert captured[1][0] == profiles.trusted_lint_argv()
    assert captured[2][0] == profiles.trusted_recon_argv()
    assert captured[3][0] == [profiles.TRUSTED_NODE, "scripts/test/check_recon_core_coverage.js"]
    for _argv, kwargs in captured:
        assert kwargs["cwd"] == fixture.app
        assert kwargs["env"]["PATH"] == profiles.TRUSTED_PATH
        assert not {"NODE_OPTIONS", "BASH_ENV", "GATEKEEPER_LOCAL_CI_ACTIVE"} & kwargs["env"].keys()


@pytest.mark.parametrize(
    "attack",
    [
        "snapshot-rw",
        "noexec-missing",
        "source-bytes",
        "source-link",
        "anchor-rw",
        "anchor-bytes",
        "anchor-link",
        "git-head",
        "tool-missing",
        "tool-link",
        "stamp",
        "plugin",
        "lock",
        "root-rw",
    ],
)
def test_trusted_boundary_and_dependencies_fail_closed(trusted_boundary, attack):
    fixture = trusted_boundary

    def replace_link(path, target):
        path.unlink()
        path.symlink_to(target)

    source = fixture.infra / "scripts/devops/gatekeeper.sh"
    anchor = fixture.app / "package.json"
    tool = Path(profiles.TRUSTED_TOOLS["eslint"])
    mutations = {
        "snapshot-rw": lambda: fixture.mounts.update({fixture.infra: ({"rw"}, "ext4")}),
        "noexec-missing": lambda: fixture.mounts.update({fixture.app: ({"rw", "nosuid"}, "tmpfs")}),
        "source-bytes": lambda: source.write_text("replaced"),
        "source-link": lambda: replace_link(source, anchor),
        "anchor-rw": lambda: fixture.mounts.update({anchor: ({"rw"}, "ext4")}),
        "anchor-bytes": lambda: anchor.write_text('{"c8":{"exclude":["**/*"]}}'),
        "anchor-link": lambda: replace_link(anchor, fixture.infra / "package.json"),
        "git-head": lambda: fixture.binding.update(head="d" * 40),
        "tool-missing": tool.unlink,
        "tool-link": lambda: replace_link(tool, anchor),
        "stamp": lambda: fixture.stamp.write_text("wrong"),
        "plugin": (fixture.image / "node_modules/eslint-plugin-jsdoc/package.json").unlink,
        "lock": lambda: (fixture.image / "package-lock.json").write_text("wrong"),
        "root-rw": lambda: fixture.mounts.update({Path("/"): ({"rw"}, "overlay")}),
    }
    mutations[attack]()
    with patch.object(profiles.subprocess, "run") as run, pytest.raises((ValueError, OSError)):
        profiles.run_trusted_tool("lint")
    run.assert_not_called()  # 包括 npm/pip 安装均未发生。


def test_trusted_mode_cannot_be_selected_by_environment_alone():
    with (
        patch.dict(os.environ, {"TRUSTED_INFRA_ROOT": "/snapshot", "TRUSTED_QA_MODE": "1"}),
        patch.object(profiles.subprocess, "run") as run,
        pytest.raises(ValueError, match="physical /snapshot"),
    ):
        profiles.run_trusted_tool("lint")
    run.assert_not_called()


def test_trusted_args_preserve_frozen_npm_contract_and_strict_native_coverage():
    package = json.loads((ROOT / "package.json").read_text())
    assert shlex.split(package["scripts"]["lint"]) == ["eslint", *profiles.LINT_ARGS]
    original_recon = shlex.split(package["scripts"]["test:coverage:recon-core"])
    assert original_recon == [
        "rm",
        "-rf",
        "reports/coverage/recon-core",
        "&&",
        "c8",
        *profiles.RECON_ARGS,
        "node",
        "scripts/test/run_test_suite.js",
        "recon-core",
        "&&",
        "node",
        "scripts/test/check_recon_core_coverage.js",
    ]
    assert profiles.trusted_lint_argv()[2 : 2 + len(profiles.LINT_ARGS)] == profiles.LINT_ARGS
    assert profiles.trusted_recon_argv()[4 : 4 + len(profiles.RECON_ARGS)] == profiles.RECON_ARGS
    assert package["scripts"]["test:coverage"] == "node scripts/test/run_test_suite.js coverage"
    gate = (ROOT / "scripts/devops/gatekeeper.sh").read_text()
    assert "'npm run test:coverage failed' npm run test:coverage" in gate


def test_recon_failure_propagates_without_checker_or_install(trusted_boundary):
    assert trusted_boundary.app.exists()
    failure_status = 23
    with patch.object(
        profiles.subprocess, "run", return_value=SimpleNamespace(returncode=failure_status)
    ) as run:
        assert profiles.run_trusted_tool("recon-core") == failure_status
    assert run.call_count == 1


def test_trusted_binding_rejects_changed_qa_contract(trusted_boundary):
    fixture = trusted_boundary
    package = json.loads((fixture.infra / "package.json").read_text())
    package["scripts"]["lint"] = "eslint src/single.js"
    data = json.dumps(package).encode()
    for root in (fixture.infra, fixture.app):
        (root / "package.json").write_bytes(data)
    fixture.binding["files"]["package.json"] = hashlib.sha256(data).hexdigest()
    (fixture.infra / ".git/cmh-qa/binding.json").write_text(json.dumps(fixture.binding))
    with pytest.raises(ValueError, match="npm QA contract"):
        profiles.verify_trusted_boundary()
