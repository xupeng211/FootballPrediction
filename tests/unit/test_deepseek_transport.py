"""真实本地 HTTP 路径的额度、重定向及失败证据回归（无 provider 访问）。"""

from __future__ import annotations

from hashlib import sha256
from http import HTTPStatus
import http.client
import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from scripts.devops.independent_review_backends import deepseek_transport as transport
from scripts.devops.independent_review_protocol import IndependentReviewProtocolError

PRIVATE_MODE = 0o600
COMPLETE_SSE = b'event: message_start\ndata: {"type":"message_start","message":{"model":"deepseek-flash"}}\n\nevent: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"tool_use"},"usage":{"output_tokens":20}}\n\nevent: message_stop\ndata: {"type":"message_stop"}\n\n'


def synthetic_transport_evidence(prompt: bytes):
    """仅为协议单元测试生成合成 transport 证据；不用于真实审核。"""
    complete = {
        "policy": transport.POLICY,
        "endpoint": transport.PROVIDER_ENDPOINT,
        "physical_attempts": 1,
        "request_sha256": "a" * 64,
        "request_bytes": 100,
        "prompt_sha256": sha256(prompt).hexdigest(),
        "response_sha256": "b" * 64,
        "response_bytes": 200,
        "output_limit": 16384,
        "observed_output_usage": 20,
        "redirects": 0,
        "retries": 0,
    }
    events = [
        {"event": "START", "policy": transport.POLICY},
        {"event": "ATTEMPT", "request_sha256": "a" * 64, "outcome": "UNKNOWN"},
        {"event": "COMPLETE", **complete},
    ]
    log = b"".join(transport._json(event) for event in events)
    return {
        **complete,
        "attempt_log": "synthetic.jsonl",
        "attempt_log_sha256": sha256(log).hexdigest(),
    }, log


def _body(prompt="review", **overrides):
    return json.dumps(
        {
            "model": "deepseek-flash",
            "max_tokens": 16384,
            "stream": True,
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            **overrides,
        }
    ).encode()


def _fake_upstream(monkeypatch, counter: Path, *, status=200, response=COMPLETE_SSE):
    class Connection:
        sock = None

        def __init__(self, host, timeout, context):
            assert host == transport.PROVIDER_HOST
            assert timeout > 0
            assert context.check_hostname
            assert context.verify_mode == transport.ssl.CERT_REQUIRED

        def request(self, method, path, body, headers):
            with counter.open("ab") as file:
                file.write(b"attempt\n")
            assert method == "POST"
            assert path == transport.PROVIDER_PATH
            assert body
            assert headers["Authorization"] == "Bearer synthetic-provider-secret"

        def getresponse(self):
            chunks = iter([response, b""])

            def header(name, default=None):
                if name == "Content-Type":
                    return "text/event-stream"
                return default

            return SimpleNamespace(
                status=status,
                getheader=header,
                read1=lambda _n: next(chunks),
            )

        def close(self):
            pass

    monkeypatch.setattr(transport.http.client, "HTTPSConnection", Connection)


def _post(gateway, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", gateway._server.server_port, timeout=5)
    connection.request(
        "POST",
        transport.PROVIDER_PATH,
        body=body or _body(),
        headers={"Authorization": f"Bearer {gateway.cli_token}"},
    )
    response = connection.getresponse()
    value = response.status, response.read()
    connection.close()
    return value


def test_real_local_http_allows_exactly_one_upstream_request(monkeypatch, tmp_path):
    counter, attempt = tmp_path / "counter", tmp_path / "attempt.jsonl"
    _fake_upstream(monkeypatch, counter)
    with transport.SingleRequestTransport(
        secret="synthetic-provider-secret", prompt="review", timeout=30, attempt_path=attempt
    ) as gateway:
        assert _post(gateway)[0] == HTTPStatus.OK
        evidence = gateway.evidence()
        transport.validate_transport(evidence, attempt.read_bytes(), b"review")
        assert _post(gateway)[0] == HTTPStatus.BAD_GATEWAY
        with pytest.raises(transport.TransportError):
            gateway.evidence()
    assert counter.read_bytes() == b"attempt\n"
    assert attempt.stat().st_mode & 0o777 == PRIVATE_MODE
    assert b"synthetic-provider-secret" not in attempt.read_bytes()
    assert not gateway._process.is_alive()


@pytest.mark.parametrize("status", [301, 302, 307, 308, 429, 503])
def test_redirect_or_provider_failure_is_not_forwarded_or_retried(monkeypatch, tmp_path, status):
    counter, attempt = tmp_path / "counter", tmp_path / "attempt.jsonl"
    _fake_upstream(monkeypatch, counter, status=status)
    with transport.SingleRequestTransport(
        secret="synthetic-provider-secret", prompt="review", timeout=30, attempt_path=attempt
    ) as gateway:
        assert _post(gateway)[0] == HTTPStatus.BAD_GATEWAY
        assert _post(gateway)[0] == HTTPStatus.BAD_GATEWAY
        with pytest.raises(transport.TransportError):
            gateway.evidence()
    assert counter.read_bytes() == b"attempt\n"
    assert b'"outcome":"UNKNOWN"' in attempt.read_bytes()


@pytest.mark.parametrize(
    "body",
    [_body("changed prompt"), _body(max_tokens=16385), _body(model="other"), _body("x" * 60001)],
)
def test_unapproved_or_oversized_request_never_dispatches(monkeypatch, tmp_path, body):
    counter, attempt = tmp_path / "counter", tmp_path / "attempt.jsonl"
    _fake_upstream(monkeypatch, counter)
    with transport.SingleRequestTransport(
        secret="synthetic-provider-secret", prompt="review", timeout=30, attempt_path=attempt
    ) as gateway:
        assert _post(gateway, body)[0] == HTTPStatus.BAD_GATEWAY
    assert not counter.exists()


@pytest.mark.parametrize(
    "response", [b"partial stream", b"synthetic-provider-secret\nevent: message_stop\n"]
)
def test_partial_or_secret_reflecting_response_fails_closed(monkeypatch, tmp_path, response):
    counter, attempt = tmp_path / "counter", tmp_path / "attempt.jsonl"
    _fake_upstream(monkeypatch, counter, response=response)
    with transport.SingleRequestTransport(
        secret="synthetic-provider-secret", prompt="review", timeout=30, attempt_path=attempt
    ) as gateway:
        assert _post(gateway)[0] == HTTPStatus.BAD_GATEWAY
        with pytest.raises(transport.TransportError):
            gateway.evidence()
    assert counter.read_bytes() == b"attempt\n"
    assert b"synthetic-provider-secret" not in attempt.read_bytes()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("physical_attempts", 2),
        ("redirects", 1),
        ("prompt_sha256", "c" * 64),
        ("request_bytes", 999999),
    ],
)
def test_reader_rejects_forged_transport_summary(field, value):
    evidence, log = synthetic_transport_evidence(b"review")
    evidence[field] = value
    with pytest.raises(IndependentReviewProtocolError):
        transport.validate_transport(evidence, log, b"review")


@pytest.mark.parametrize(
    "stop,usage", [("max_tokens", 20), ("tool_use", 16385), ("tool_use", None)]
)
def test_provider_completion_and_output_budget_must_be_provable(stop, usage):
    raw = COMPLETE_SSE.replace(b'"tool_use"', json.dumps(stop).encode()).replace(
        b'"output_tokens":20', b'"output_tokens":' + json.dumps(usage).encode()
    )
    with pytest.raises(transport.TransportError):
        transport._completed_output_usage(raw)
