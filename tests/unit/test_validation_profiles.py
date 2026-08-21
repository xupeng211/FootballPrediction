"""Tests for the canonical validation profile dispatcher.

lifecycle: test-fixture
"""

from pathlib import Path
import sys
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
