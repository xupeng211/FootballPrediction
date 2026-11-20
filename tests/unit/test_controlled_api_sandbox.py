"""网络 namespace 的实际负例与受控 socket 正例；不读取真实凭据。"""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts.devops.controlled_api_budget import Budget
from scripts.devops.controlled_api_policy import ControlError, prepare
from scripts.devops.controlled_api_sandbox import run_offline, sandbox_command
from scripts.devops.independent_review_protocol import canonical_json
from tests.unit.test_controlled_api_budget import grant
from tests.unit.test_controlled_api_runner import mock_provider, response

PROJECT = Path(__file__).resolve().parents[2]


def test_missing_namespace_tool_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(ControlError, match="NETWORK_ISOLATION_UNAVAILABLE"):
        sandbox_command(PROJECT, tmp_path, tmp_path, tmp_path, [])


def test_actual_namespace_blocks_external_network_and_keeps_mock_path(tmp_path):
    if not shutil.which("bwrap"):
        if os.environ.get("CONTROLLED_API_REQUIRE_SANDBOX_TESTS") == "1":
            pytest.fail("required bwrap runtime unavailable")
        pytest.skip("bwrap unavailable; production isolation remains NOT_VERIFIED")
    budget = Budget(tmp_path / "state", initialize=True)
    plan = prepare("deepseek", "source", 100)
    task = grant(budget, [plan])
    plan_path = tmp_path / "plan.json"
    plan_path.write_bytes(canonical_json(plan))
    socket_path = tmp_path / "mock.sock"
    with mock_provider(socket_path, response()) as calls:
        # RFC 5737 TEST-NET 地址；namespace 没有路由，不做 DNS、不联系 Provider。
        probe = """
import os,socket
assert not os.path.exists('/home/xupeng')
assert 'ANTHROPIC_AUTH_TOKEN' not in os.environ
assert 'OPENAI_API_KEY' not in os.environ
assert not os.path.exists('/run/docker.sock')
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.settimeout(0.1)
try:
    s.connect(('192.0.2.1',443))
except OSError:
    print('EXTERNAL_NETWORK_DENIED')
else:
    raise AssertionError('network bypass')
"""
        command = sandbox_command(PROJECT, budget.root, plan_path, socket_path, ["-c", probe])
        result = subprocess.run(
            command, env={}, capture_output=True, text=True, timeout=10, check=False
        )
        if result.returncode and "Operation not permitted" in result.stderr:
            if os.environ.get("CONTROLLED_API_REQUIRE_SANDBOX_TESTS") == "1":
                pytest.fail("required network namespace creation denied")
            pytest.skip(
                "network namespace creation denied; production isolation remains NOT_VERIFIED"
            )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "EXTERNAL_NETWORK_DENIED"
        completed = run_offline(PROJECT, budget.root, plan_path, socket_path, task, 1)
        assert completed.returncode == 0, completed.stderr
        assert json.loads(completed.stdout)["current_approval_eligible"] is False
        assert len(calls) == 1
        repeat = run_offline(PROJECT, budget.root, plan_path, socket_path, task, 1)
        assert repeat.returncode != 0
        assert len(calls) == 1
