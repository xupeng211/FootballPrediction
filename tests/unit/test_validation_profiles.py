"""Tests for the canonical validation profile dispatcher.

lifecycle: test-fixture
"""

import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

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
