"""Git object 绑定与独立未合格身份的离线验收。"""

import json
from pathlib import Path
import subprocess

import pytest

from scripts.devops.controlled_api_binding import bind_source, qualification_requirements
from scripts.devops.controlled_api_policy import ControlError
from scripts.devops.exact_head import ExactHeadError
from scripts.devops.independent_review_protocol import sha256_bytes

PROJECT = Path(__file__).resolve().parents[2]
MISSION = "QUALIFICATION_FIXTURE"
SCOPE = f"docs/agentic/missions/{MISSION}.json"


@pytest.fixture
def source_repo(tmp_path):
    def git(*args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "user.name=Offline Test",
                "-c",
                "user.email=offline@example.invalid",
                *args,
            ],
            cwd=tmp_path,
        ).strip()

    git("init", "--quiet")
    git("commit", "--allow-empty", "-qm", "base")
    base = git("rev-parse", "HEAD").decode()
    # 固定 schema，授权只服务本测试，不授予真实 Reviewer 资格。
    template = next((PROJECT / "docs/agentic/missions").glob("FOOTBALLPREDICTION*AUTONOMOUS*.json"))
    scope = json.loads(template.read_text())
    scope["mission_id"] = MISSION
    scope["authorized_paths"] = [SCOPE]
    target = tmp_path / SCOPE
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(scope))
    git("add", SCOPE)
    git("commit", "-qm", "scope")
    return tmp_path, base, git("rev-parse", "HEAD").decode(), git


def test_source_binding_reads_exact_git_blobs_and_canonical_diff(source_repo):
    root, base, head, _git = source_repo
    source = bind_source(root, base, head, MISSION, SCOPE)
    assert source["scope_sha256"] == sha256_bytes((root / SCOPE).read_bytes())
    raw = subprocess.check_output(
        ["git", "diff", "--binary", "--no-ext-diff", f"{base}...{head}"], cwd=root
    )
    assert source["diff_sha256"] == sha256_bytes(raw)
    assert source["head"] == head


@pytest.mark.parametrize("change", ["dirty", "stale", "short", "scope"])
def test_source_binding_fails_closed(source_repo, change):
    root, base, head, _git = source_repo
    scope = SCOPE
    if change == "dirty":
        (root / "unknown.txt").write_text("other work")
    elif change == "stale":
        head = base
    elif change == "short":
        head = head[:12]
    else:
        scope = "../outside.json"
    with pytest.raises((ControlError, ExactHeadError)):
        bind_source(root, base, head, MISSION, scope)


def test_new_channels_do_not_inherit_legacy_qualification():
    identities = []
    for provider in ("deepseek", "openai"):
        contract = qualification_requirements(provider)
        assert contract["current_approval_eligible"] is False
        assert contract["legacy_qualification_inheritance"] is False
        assert contract["qualification_status"] == "NOT_RUN"
        assert contract["formal_receipt_supported"] is False
        identities.append(contract["execution_identity"])
    assert identities[0] != identities[1]
    with pytest.raises(ControlError):
        qualification_requirements("legacy-codex")
