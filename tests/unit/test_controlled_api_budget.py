"""离线预算原子性、候选绑定与恢复故障注入。"""

from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_policy import (
    ControlError,
    prepare,
    source_identity,
    validate_plan,
)
from scripts.devops.independent_review_protocol import IndependentReviewProtocolError
from scripts.devops.independent_review_receipt import ReceiptEvidenceContext, validate_receipt

SOURCE = {
    "repository": "xupeng211/FootballPrediction",
    "mission": "DIRECT_API_OFFLINE",
    "base": "a" * 40,
    "head": "b" * 40,
    "diff_sha256": "c" * 64,
    "scope_sha256": "d" * 64,
}


@pytest.fixture
def budget(tmp_path):
    return Budget(tmp_path / "state", initialize=True)


def grant(budget, plans, **overrides):
    limits = {
        "requests": len(plans),
        "tokens": sum(p["reserve_tokens"] for p in plans),
        "nano_usd": sum(p["reserve_nano_usd"] for p in plans),
    }
    limits.update(overrides)
    return budget.create(SOURCE, plans, **limits)


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_fixed_models_text_only_output_and_conditional_prices(provider):
    plan = prepare(provider, "检查跨文件风险", 100)
    assert validate_plan(plan) == plan
    assert plan["policy"]["price_status"] == "CONDITIONAL_SNAPSHOT_NOT_PROVIDER_GUARANTEE"
    assert plan["reserve_nano_usd"] == (
        plan["policy"]["input_cap"] * plan["policy"]["input_nano_usd"]
        + 100 * plan["policy"]["output_nano_usd"]
    )
    assert "tools" not in plan["body"]
    assert plan["body"]["stream"] is False
    if provider == "openai":
        assert plan["body"]["max_output_tokens"] == plan["policy"]["output_cap"]
        assert plan["body"]["reasoning"] == {"effort": "medium"}
        assert plan["body"]["service_tier"] == "default"
        assert plan["body"]["truncation"] == "disabled"
        assert plan["policy"]["input_nano_usd"] == 2_000 * 2 * 1.25
        assert plan["policy"]["output_nano_usd"] == 12_000 * 1.5
    else:
        assert plan["body"]["max_tokens"] == plan["policy"]["output_cap"]
        assert plan["body"]["thinking"] == {"type": "enabled"}


@pytest.mark.parametrize("mutation", ["cost", "model", "tools", "prompt", "price", "extra"])
def test_request_plan_cannot_underreserve_or_add_charge_paths(mutation):
    plan = prepare("openai", "source", 10)
    if mutation == "cost":
        plan["reserve_nano_usd"] = 1
    elif mutation == "model":
        plan["body"]["model"] = "unapproved"
    elif mutation == "tools":
        plan["body"]["tools"] = [{"type": "web_search"}]
    elif mutation == "prompt":
        plan["body"]["input"] = "changed"
    elif mutation == "price":
        plan["policy"]["input_nano_usd"] = 0
    else:
        plan["extra"] = "unsupported"
    with pytest.raises(ControlError, match="INVALID_REQUEST_PLAN"):
        validate_plan(plan)


@pytest.mark.parametrize("output", [True, 0, -1, 128_001, 1.5])
def test_invalid_output_limits(output):
    with pytest.raises(ControlError):
        prepare("openai", "source", output)


def test_unknown_model_or_price():
    with pytest.raises(ControlError, match="UNKNOWN_MODEL_OR_PRICE"):
        prepare("unknown", "source", 1)


def test_shared_provider_budget_and_same_candidate_no_regrant(budget):
    plans = [prepare("openai", "source", 10), prepare("deepseek", "source", 10)]
    identity = grant(budget, plans)
    budget.claim(identity, 1, plans[0])
    restored = Budget(budget.root)
    restored.claim(identity, 2, plans[1])
    evidence = restored.evidence(identity)
    assert evidence["claimed_requests"] == len(plans)
    assert evidence["reserved_nano_usd"] == sum(p["reserve_nano_usd"] for p in plans)
    assert evidence["current_approval_eligible"] is False
    assert evidence["qualification_required"] is True
    changed = {**SOURCE, "mission": "NEW_NAME", "scope_sha256": "e" * 64}
    assert source_identity(changed) == identity
    with pytest.raises(ControlError, match="TASK_ALREADY_EXISTS"):
        restored.create(changed, plans, requests=2, tokens=10**9, nano_usd=10**12)
    assert restored.evidence(identity)["execution"] == evidence["execution"]


@pytest.mark.parametrize(
    ("limit", "error"),
    [("requests", "REQUEST_CAP"), ("tokens", "TOKEN_CAP"), ("nano_usd", "MONEY_CAP")],
)
def test_exact_cap_then_next_slot_denied(budget, limit, error):
    plan = prepare("deepseek", "source", 10)
    value = {"requests": 1, "tokens": plan["reserve_tokens"], "nano_usd": plan["reserve_nano_usd"]}[
        limit
    ]
    identity = grant(budget, [plan, plan], **{limit: value})
    budget.claim(identity, 1, plan)
    before = budget.evidence(identity)
    with pytest.raises(ControlError, match=error):
        budget.claim(identity, 2, plan)
    assert budget.evidence(identity) == before


def test_frozen_slots_unknown_task_and_plan_replacement(budget):
    plan = prepare("deepseek", "source", 10)
    identity = grant(budget, [plan])
    for task, slot, candidate in [
        ("unknown", 1, plan),
        (identity, 2, plan),
        (identity, 1, prepare("deepseek", "changed", 10)),
    ]:
        with pytest.raises(ControlError):
            budget.claim(task, slot, candidate)
    assert budget.evidence(identity)["claimed_requests"] == 0


def _race(root, identity, slot, plan):
    try:
        Budget(Path(root)).claim(identity, slot, plan)
    except ControlError:
        return "DENIED"
    else:
        return "CLAIMED"


def test_multiprocess_atomic_budget_competition(budget):
    plan = prepare("deepseek", "source", 10)
    identity = grant(budget, [plan] * 8, requests=2)
    with ProcessPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(_race, [budget.root] * 8, [identity] * 8, range(1, 9), [plan] * 8))
    assert outcomes.count("CLAIMED") == sum(o == "CLAIMED" for o in outcomes) == len(outcomes) // 4
    assert outcomes.count("DENIED") == len(outcomes) * 3 // 4
    assert budget.evidence(identity)["claimed_requests"] == len(outcomes) // 4


def test_crash_after_commit_before_send_never_replays(budget):
    plan = prepare("deepseek", "source", 10)
    identity = grant(budget, [plan])
    code = """
import json,os,sys
from pathlib import Path
from scripts.devops.controlled_api_budget import Budget
Budget(Path(sys.argv[1])).claim(sys.argv[2],1,json.loads(sys.argv[3]))
os._exit(73)
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(budget.root), identity, json.dumps(plan)], check=False
    )
    expected_crash_code = 73
    assert result.returncode == expected_crash_code
    assert Budget(budget.root).evidence(identity)["claimed_requests"] == 1
    with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
        Budget(budget.root).claim(identity, 1, plan)
    assert budget.evidence(identity)["slots"][0]["state"] == "CLAIMED"


def test_immutable_schema_and_domain_operations_cannot_reset_budget(budget):
    plan = prepare("deepseek", "source", 10)
    identity = grant(budget, [plan])
    budget.claim(identity, 1, plan)
    # 门禁禁止 tests/ 直接写 SQL；以只读 schema 和实际领域操作验证不可重置边界。
    with budget.connect() as reader:
        triggers = {
            row[0] for row in reader.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
    assert triggers == {"no_task_delete", "no_budget_reset", "no_slot_delete", "no_slot_replay"}
    before = budget.evidence(identity)
    with pytest.raises(ControlError, match="TASK_ALREADY_EXISTS"):
        budget.create(SOURCE, [plan], requests=100, tokens=10**9, nano_usd=10**12)
    with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
        Budget(budget.root).claim(identity, 1, plan)
    budget.finish(identity, 1, complete=False, category="TIMEOUT", response_sha256="0" * 64)
    with pytest.raises(ControlError, match="INVALID_COMPLETION"):
        budget.finish(
            identity, 1, complete=True, category="VALID_OFFLINE_RESPONSE", response_sha256="1" * 64
        )
    after = budget.evidence(identity)
    for field in ("execution", "caps", "claimed_requests", "reserved_tokens", "reserved_nano_usd"):
        assert after[field] == before[field]


def test_unsafe_state_paths_rejected(tmp_path):
    root = tmp_path / "state"
    root.mkdir(mode=0o755)
    with pytest.raises(ControlError, match="UNSAFE_STATE_DIRECTORY"):
        Budget(root)
    root.chmod(0o700)
    outside = tmp_path / "outside"
    outside.write_text("private")
    (root / "budget.sqlite3").symlink_to(outside)
    with pytest.raises(OSError, match="Too many levels"):
        Budget(root)
    assert outside.read_text() == "private"


def test_no_raw_response_or_credentials_in_evidence(budget):
    plan = prepare("deepseek", "source", 10)
    identity = grant(budget, [plan])
    budget.claim(identity, 1, plan)
    budget.finish(identity, 1, complete=False, category="TIMEOUT", response_sha256="0" * 64)
    evidence = budget.evidence(identity)
    assert "body" not in str(evidence)
    assert "Authorization" not in str(evidence)
    assert evidence["slots"][0]["state"] == "UNKNOWN"
    assert evidence["reserved_nano_usd"] == plan["reserve_nano_usd"]


def test_invalid_source_and_numeric_budget(budget):
    plan = prepare("openai", "source", 1)
    for source in ({}, {**SOURCE, "head": "short"}, {**SOURCE, "repository": "other"}):
        with pytest.raises(ValueError, match=r"INVALID|digest"):
            budget.create(source, [plan], requests=1, tokens=10**8, nano_usd=10**12)
    for value in (True, -1, 0, 1.5, 2**63):
        with pytest.raises(ControlError):
            budget.create(SOURCE, [deepcopy(plan)], requests=value, tokens=10**8, nano_usd=10**12)
    assert not (budget.root / "receipt.json").exists()


def test_missing_or_corrupt_ledger_never_reinitializes(tmp_path):
    root = tmp_path / "state"
    with pytest.raises(ControlError, match="STATE_MISSING"):
        Budget(root)
    budget = Budget(root, initialize=True)
    budget.path.unlink()  # 模拟状态丢失；恢复不能得到新预算。
    with pytest.raises(FileNotFoundError):
        Budget(root)
    with pytest.raises(FileExistsError):
        Budget(root, initialize=True)
    budget.path.write_bytes(b"corrupt")
    budget.path.chmod(0o600)
    with pytest.raises(sqlite3.DatabaseError, match="not a database"):
        Budget(root)


def test_execution_evidence_is_rejected_by_formal_receipt_validator(budget):
    plan = prepare("deepseek", "source", 10)
    task = grant(budget, [plan])
    context = ReceiptEvidenceContext(
        Path.cwd(), SOURCE["base"], SOURCE["head"], "unused", b"", b"", b""
    )
    with pytest.raises(IndependentReviewProtocolError, match="schema"):
        validate_receipt(budget.evidence(task), registry={}, evidence_context=context)
