"""真实 AF_UNIX HTTP 的零 Provider 故障注入；模拟不是计费保证。"""

from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import socketserver
import subprocess
import sys
import threading
import time

import pytest

from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_policy import ControlError, prepare
from scripts.devops.controlled_api_runner import execute
from scripts.devops.independent_review_protocol import PROTOCOL_VERSION, canonical_json
from tests.unit.test_controlled_api_budget import grant


def response(provider="deepseek", *, review="PASS"):
    result = {"protocol_version": PROTOCOL_VERSION, "review_result": review, "findings": []}
    if review == "FAIL":
        result["findings"] = [
            {
                "severity": "P2",
                "title": "跨文件使用了不同的候选身份",
                "evidence": "producer 以 head A 发布，consumer 未比较 head 就读取，可能错误授权 head B。",
            }
        ]
    text = json.dumps(result)
    if provider == "openai":
        return {
            "model": "gpt-5.6-terra",
            "status": "completed",
            "usage": {"input_tokens": 10, "output_tokens": 9, "total_tokens": 19},
            "output": [
                {
                    "type": "message",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
        }
    return {
        "model": "deepseek-flash",
        "usage": {"prompt_tokens": 10, "completion_tokens": 9, "total_tokens": 19},
        "choices": [{"finish_reason": "stop", "message": {"content": text}}],
    }


@contextmanager
def mock_provider(path: Path, payload: dict, mode="normal"):
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append((self.path, json.loads(body), dict(self.headers)))
            if mode == "timeout":
                time.sleep(0.15)
                return
            if mode == "disconnect":
                return
            raw = canonical_json(payload)
            if mode == "duplicate_json":
                raw = raw[:-2] + b',"model":"deepseek-flash"}\n'
            self.send_response(307 if mode == "redirect" else 200)
            if mode == "redirect":
                self.send_header("Location", "https://api.deepseek.com/chat/completions")
            self.send_header(
                "Content-Length", str(len(raw) + 30 if mode == "truncated" else len(raw))
            )
            self.end_headers()
            self.wfile.write(raw)

    with socketserver.UnixStreamServer(str(path), Handler) as server:
        thread = threading.Thread(
            target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True
        )
        thread.start()
        try:
            yield calls
        finally:
            server.shutdown()
            thread.join()


@pytest.mark.parametrize("provider", ["deepseek", "openai"])
@pytest.mark.parametrize("review", ["PASS", "FAIL"])
def test_real_http_shape_valid_result_not_formal_approval(tmp_path, provider, review):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare(provider, "源码与所有审核上下文", 100)
    identity = grant(budget, [plan])
    path = tmp_path / "provider.sock"
    with mock_provider(path, response(provider, review=review)) as calls:
        evidence = execute(budget, identity, 1, plan, socket_path=path)
        assert len(calls) == 1
        assert calls[0][0] == plan["policy"]["path"]
        assert calls[0][1] == plan["body"]
        assert "Authorization" not in calls[0][2]
        with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
            execute(budget, identity, 1, plan, socket_path=path)
        assert len(calls) == 1
    assert evidence["slots"][0]["state"] == "COMPLETE"
    assert evidence["current_approval_eligible"] is False
    assert evidence["physical_usd_bound"] == "NOT_PROVEN"
    assert list(tmp_path.rglob("*receipt*")) == []


@pytest.mark.parametrize(
    ("mode", "category"),
    [
        ("timeout", "TIMEOUT"),
        ("disconnect", "TRANSPORT_FAILURE"),
        ("truncated", "TRANSPORT_FAILURE"),
        ("redirect", "RESPONSE_INVALID"),
        ("duplicate_json", "RESPONSE_INVALID"),
    ],
)
def test_timeout_disconnect_stream_interruption_redirect_no_automatic_retry(
    tmp_path, mode, category
):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    identity = grant(budget, [plan])
    path = tmp_path / "provider.sock"
    with mock_provider(path, response(), mode) as calls:
        with pytest.raises(ControlError, match=category):
            execute(budget, identity, 1, plan, socket_path=path, timeout=0.04)
        for _ in range(3):  # 模拟 SDK/调用方内部重复调用；没有新 POST。
            with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
                execute(Budget(budget.root), identity, 1, plan, socket_path=path)
        assert len(calls) == 1
    evidence = budget.evidence(identity)
    assert evidence["slots"][0]["state"] == "UNKNOWN"
    assert evidence["reserved_nano_usd"] == plan["reserve_nano_usd"]


@pytest.mark.parametrize(
    "change",
    ["missing_usage", "over_usage", "bool_usage", "unknown_model", "incomplete", "invalid_result"],
)
def test_invalid_or_missing_data_no_refund_no_receipt(tmp_path, change):
    payload = response()
    if change == "missing_usage":
        del payload["usage"]
    elif change == "over_usage":
        payload["usage"]["completion_tokens"] = 1_000
    elif change == "bool_usage":
        payload["usage"]["prompt_tokens"] = True
    elif change == "unknown_model":
        payload["model"] = "unapproved"
    elif change == "incomplete":
        payload["choices"][0]["finish_reason"] = "length"
    else:
        payload["choices"][0]["message"]["content"] = "secret API_KEY_NOT_FOR_LOGGING"
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    identity = grant(budget, [plan])
    path = tmp_path / "provider.sock"
    with mock_provider(path, payload) as calls:
        with pytest.raises(ControlError, match=r"^RESPONSE_INVALID$") as error:
            execute(budget, identity, 1, plan, socket_path=path)
        assert len(calls) == 1
    assert "secret" not in str(error.value)
    assert b"API_KEY_NOT_FOR_LOGGING" not in budget.path.read_bytes()
    assert budget.evidence(identity)["reserved_nano_usd"] == plan["reserve_nano_usd"]


def test_budget_failure_prevents_any_http_request(tmp_path):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    identity = grant(budget, [plan], nano_usd=plan["reserve_nano_usd"] - 1)
    path = tmp_path / "provider.sock"
    with mock_provider(path, response()) as calls:
        with pytest.raises(ControlError, match="MONEY_CAP_EXHAUSTED"):
            execute(budget, identity, 1, plan, socket_path=path)
        assert calls == []


def test_evidence_write_failure_cannot_return_success_or_resend(tmp_path, monkeypatch):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    identity = grant(budget, [plan])
    path = tmp_path / "provider.sock"
    with mock_provider(path, response()) as calls:

        def failure(*_args, **_kwargs):
            raise OSError("simulated disk failure")

        monkeypatch.setattr(budget, "finish", failure)
        with pytest.raises(OSError, match="simulated disk failure"):
            execute(budget, identity, 1, plan, socket_path=path)
        with pytest.raises(ControlError, match="REQUEST_ALREADY_CLAIMED"):
            execute(Budget(budget.root), identity, 1, plan, socket_path=path)
        assert len(calls) == 1
    assert budget.evidence(identity)["slots"][0]["state"] == "CLAIMED"


def test_cli_cannot_accept_live_provider_flags():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.devops.controlled_api_runner",
            "--live",
            "--endpoint",
            "https://api.deepseek.com",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    argparse_error = 2
    assert result.returncode == argparse_error
    assert "CONTROLLED_API" not in result.stdout


@pytest.mark.parametrize("provider", ["openai", "deepseek"])
def test_unexpected_tools_rejected_even_with_valid_review_text(tmp_path, provider):
    payload = response(provider)
    if provider == "openai":
        payload["output"].append({"type": "function_call", "name": "shell"})
    else:
        payload["choices"][0]["message"]["tool_calls"] = [{"type": "function", "name": "shell"}]
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare(provider, "source", 100)
    task = grant(budget, [plan])
    path = tmp_path / "mock.sock"
    with mock_provider(path, payload) as calls:
        with pytest.raises(ControlError, match="RESPONSE_INVALID"):
            execute(budget, task, 1, plan, socket_path=path)
        assert len(calls) == 1


def test_claim_write_failure_never_sends(tmp_path, monkeypatch):
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    task = grant(budget, [plan])
    path = tmp_path / "mock.sock"

    def disk_failure(*_args):
        raise OSError("claim persistence failed")

    monkeypatch.setattr(budget, "claim", disk_failure)
    with mock_provider(path, response()) as calls:
        with pytest.raises(OSError, match="claim persistence failed"):
            execute(budget, task, 1, plan, socket_path=path)
        assert calls == []
