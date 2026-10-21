"""本地真实 TLS broker 的预算、认证、异常和不可重发验收。"""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.devops import controlled_api_broker as module
from scripts.devops.controlled_api_broker import Broker, request_slot, serve
from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_https import Credential, post_once
from scripts.devops.controlled_api_policy import ControlError, prepare
from scripts.devops.controlled_api_sandbox import broker_worker_command
from tests.unit.controlled_api_tls_fixture import make_tls_site
from tests.unit.test_controlled_api_budget import grant
from tests.unit.test_controlled_api_runner import response

PROJECT = Path(__file__).resolve().parents[2]
CRASH_EXIT = 37
CREDENTIAL = Credential("fixture-not-a-real-key")


@pytest.fixture
def tls_site(tmp_path):
    return make_tls_site(tmp_path)


def setup(tmp_path, fixture, *, provider="deepseek", timeout=0.5, **limits):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare(provider, "源码候选", 100)
    task = grant(budget, [plan], **limits)
    return Broker(budget, task, [plan], CREDENTIAL, fixture, timeout=timeout), plan


@pytest.mark.parametrize("provider", ["deepseek", "openai"])
@pytest.mark.parametrize("review", ["PASS", "FAIL"])
def test_tls_single_post_result_persisted_never_qualified(tmp_path, tls_site, provider, review):
    with tls_site(response(provider, review=review)) as (fixture, calls):
        broker, plan = setup(tmp_path, fixture, provider=provider)
        with serve(broker, tmp_path / "socket") as path:
            evidence = request_slot(path, broker.task, 1)
            with pytest.raises(ControlError, match="BROKER_EXECUTION_REJECTED"):
                request_slot(path, broker.task, 1)
        assert len(calls) == 1
        assert calls[0] == (plan["policy"]["path"], plan["body"], "Bearer " + CREDENTIAL.value)
    assert evidence["claimed_requests"] == 1
    assert evidence["current_approval_eligible"] is False
    saved = json.loads(next(broker.budget.root.glob("result-*.json")).read_text())
    assert saved["result"]["review_result"] == review
    assert saved["result"]["blocking_findings"] == (1 if review == "FAIL" else 0)
    assert saved["current_approval_eligible"] is False
    assert saved["request_sha256"] == plan["request_sha256"]
    assert saved["reviewer_identity"].endswith("/" + provider)
    assert saved["qualification_status"] == "NOT_RUN"
    assert CREDENTIAL.value not in str(saved)


@pytest.mark.parametrize("mode", ["timeout", "disconnect", "truncated", "redirect"])
def test_tls_failure_consumes_budget_no_retry_or_redirect(tmp_path, tls_site, mode):
    with tls_site(response(), mode) as (fixture, calls):
        broker, plan = setup(tmp_path, fixture, timeout=0.04)
        for _ in range(3):
            with pytest.raises(ControlError):
                broker.execute({"task": broker.task, "slot": 1})
        assert len(calls) == 1
        restarted = Broker(Budget(broker.budget.root), broker.task, [plan], CREDENTIAL, fixture)
        with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
            restarted.execute({"task": broker.task, "slot": 1})
    assert broker.budget.evidence(broker.task)["slots"][0]["state"] == "UNKNOWN"
    assert broker.budget.evidence(broker.task)["reserved_nano_usd"] == plan["reserve_nano_usd"]


def test_tls_concurrent_brokers_share_claim(tmp_path, tls_site):
    with tls_site(response()) as (fixture, calls):
        broker, plan = setup(tmp_path, fixture)
        other = Broker(Budget(broker.budget.root), broker.task, [plan], CREDENTIAL, fixture)

        def attempt(instance):
            try:
                instance.execute({"task": broker.task, "slot": 1})
            except ControlError:
                return False
            return True

        with ThreadPoolExecutor(2) as pool:
            assert sorted(pool.map(attempt, [broker, other])) == [False, True]
        assert len(calls) == 1


@pytest.mark.parametrize("change", ["usage", "model", "secret", "escaped_secret"])
def test_tls_unknown_billing_or_identity_no_receipt(tmp_path, tls_site, change):
    payload = response()
    if change == "secret":
        payload["choices"][0]["message"]["content"] = CREDENTIAL.value
    elif change == "escaped_secret":
        review = json.loads(payload["choices"][0]["message"]["content"])
        review["findings"] = [
            {"severity": "P3", "title": "不要暴露凭据", "evidence": CREDENTIAL.value}
        ]
        text = json.dumps(review).replace("fixture-", "\\u0066ixture-")
        payload["choices"][0]["message"]["content"] = text
    else:
        payload.pop(change)
    with tls_site(payload) as (fixture, calls):
        broker, _ = setup(tmp_path, fixture)
        with pytest.raises(ControlError):
            broker.execute({"task": broker.task, "slot": 1})
        assert len(calls) == 1
    assert not list(broker.budget.root.glob("result-*.json"))
    assert CREDENTIAL.value.encode() not in broker.budget.path.read_bytes()


@pytest.mark.parametrize("invalid", ["host", "address", "ca", "credential"])
def test_tls_target_certificate_and_credential_enforced(tmp_path, tls_site, invalid):
    with tls_site(response()) as (fixture, calls):
        broker, _ = setup(tmp_path, fixture)
        if invalid == "host":
            broker.fixture = replace(fixture, hostname="api.deepseek.com")
        elif invalid == "address":
            broker.fixture = replace(fixture, address="192.0.2.1")
        elif invalid == "ca":
            broker.fixture = replace(fixture, ca_file=Path("/etc/ssl/certs/ca-certificates.crt"))
        else:
            broker.credential = Credential("not-a-fixture-key")
        with pytest.raises((ControlError, OSError)):
            broker.execute({"task": broker.task, "slot": 1})
        assert calls == []


def test_live_route_never_admitted_even_with_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ALLOW_LIVE", "yes")
    monkeypatch.setenv("HTTPS_PROXY", "https://api.deepseek.com")
    broker, plan = setup(tmp_path, None)
    with pytest.raises(ControlError, match="ADMISSION_NOT_PROVEN"):
        broker.execute({"task": broker.task, "slot": 1})
    with pytest.raises(ControlError, match="ADMISSION_NOT_PROVEN"):
        post_once(plan, CREDENTIAL, fixture=None)
    assert broker.budget.evidence(broker.task)["claimed_requests"] == 0
    assert CREDENTIAL.value not in repr(CREDENTIAL)


@pytest.mark.parametrize(
    "message",
    [{"url": "https://api.openai.com"}, {"task": "wrong", "slot": 1}, {"task": "x", "slot": True}],
)
def test_worker_cannot_select_url_body_credential_or_other_task(tmp_path, message):
    broker, _ = setup(tmp_path, None)
    with pytest.raises(ControlError):
        broker.execute(message)
    assert broker.budget.evidence(broker.task)["claimed_requests"] == 0


def test_budget_exhaustion_no_tls_post(tmp_path, tls_site):
    with tls_site(response()) as (fixture, calls):
        broker, _ = setup(tmp_path, fixture, nano_usd=1)
        with pytest.raises(ControlError, match="MONEY_CAP_EXHAUSTED"):
            broker.execute({"task": broker.task, "slot": 1})
        assert calls == []


def test_broker_worker_actual_namespace_no_direct_tls_or_credential(tmp_path, tls_site):
    if not shutil.which("bwrap"):
        if os.environ.get("CONTROLLED_API_REQUIRE_SANDBOX_TESTS") == "1":
            pytest.fail("required bwrap runtime unavailable")
        pytest.skip("bwrap unavailable; run forced isolation acceptance locally")
    with tls_site(response()) as (fixture, calls):
        broker, _ = setup(tmp_path, fixture)
        with serve(broker, tmp_path / "socket") as path:
            script = f"""
import os,socket,json
from scripts.devops.controlled_api_broker import request_slot
assert not os.path.exists({str(broker.budget.root)!r})
assert not os.path.exists('/home/xupeng')
assert not any('KEY' in k or 'TOKEN' in k for k in os.environ)
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(.1)
try:
    s.connect(('127.0.0.1',{fixture.port}))
except OSError:
    pass
else:
    raise AssertionError('direct TLS bypass')
print(json.dumps(request_slot('/run/broker.sock',{broker.task!r},1)))
"""
            result = subprocess.run(
                broker_worker_command(PROJECT, path, ["-c", script]),
                env={},
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if (
                result.returncode
                and "Operation not permitted" in result.stderr
                and os.environ.get("CONTROLLED_API_REQUIRE_SANDBOX_TESTS") != "1"
            ):
                pytest.skip("namespace denied; isolation NOT_VERIFIED on this environment")
            assert result.returncode == 0, result.stderr
            assert json.loads(result.stdout)["current_approval_eligible"] is False
            assert len(calls) == 1


def _crash_after_send(root, task, plan, fixture):
    original = module.post_once

    def send_then_crash(*args, **kwargs):
        original(*args, **kwargs)
        os._exit(CRASH_EXIT)

    module.post_once = send_then_crash
    broker = Broker(Budget(root), task, [plan], CREDENTIAL, fixture)
    broker.execute({"task": task, "slot": 1})


def test_process_crash_after_tls_send_never_replays(tmp_path, tls_site):
    with tls_site(response()) as (fixture, calls):
        broker, plan = setup(tmp_path, fixture)
        process = multiprocessing.get_context("spawn").Process(
            target=_crash_after_send, args=(broker.budget.root, broker.task, plan, fixture)
        )
        process.start()
        process.join(10)
        assert process.exitcode == CRASH_EXIT
        recovered = Broker(Budget(broker.budget.root), broker.task, [plan], CREDENTIAL, fixture)
        with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
            recovered.execute({"task": broker.task, "slot": 1})
        assert len(calls) == 1
        assert recovered.budget.evidence(broker.task)["slots"][0]["state"] == "CLAIMED"


def test_tls_result_persistence_failure_no_replay(tmp_path, tls_site, monkeypatch):
    with tls_site(response()) as (fixture, calls):
        broker, _ = setup(tmp_path, fixture)
        original = module.os.open

        def fail_result(path, *args, **kwargs):
            if Path(path).name.startswith("result-"):
                raise OSError("disk full fixture")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(module.os, "open", fail_result)
        with pytest.raises(ControlError, match="PERSISTENCE_FAILURE"):
            broker.execute({"task": broker.task, "slot": 1})
        with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
            broker.execute({"task": broker.task, "slot": 1})
        assert len(calls) == 1
        assert not list(broker.budget.root.glob("result-*.json"))
