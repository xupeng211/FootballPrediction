"""Tests for the one-day FotMob live fetch no-raw-write probe.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE
"""

from __future__ import annotations

import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
from urllib.error import HTTPError

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/ops/fotmob_one_day_live_fetch_no_raw_write.py"
CHECKER_PATH = REPO_ROOT / "scripts/ops/fotmob_one_day_live_fetch_no_raw_write_check.py"
MANIFEST_PATH = REPO_ROOT / "docs/_manifests/fotmob_one_day_live_fetch_no_raw_write_manifest.json"
REPORT_PATH = REPO_ROOT / "docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE.md"
REVIEW_PATH = REPO_ROOT / "docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE_REVIEW.md"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _json(path: Path) -> dict:
    return json.loads(_text(path))


def _target() -> dict:
    return {"target_id": 1, "source_match_id": "fixture-test-001", "source_url": None}


class FakeResponse:
    def __init__(self, payload: bytes, status: int = 200, content_type: str = "application/json"):
        self.payload = payload
        self.status = status
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.payload

    def getcode(self) -> int:
        return self.status


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def open(self, *_args, **_kwargs):
        if self.error is not None:
            raise self.error
        return self.response


def test_script_exists():
    assert SCRIPT_PATH.exists()


def test_checker_exists():
    assert CHECKER_PATH.exists()


def test_missing_explicit_allow_flag_blocks_execution(tmp_path, monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_missing_flag")
    monkeypatch.delenv(module.ALLOW_FLAG, raising=False)
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.md"
    review = tmp_path / "review.md"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe",
            "--output-manifest",
            str(manifest),
            "--report",
            str(report),
            "--review-report",
            str(review),
        ],
    )
    assert module.main() == 1
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["explicit_allow_flag_present"] is False
    assert data["stop_reason"] == "missing_explicit_allow_flag"


def test_production_env_blocks_execution():
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_prod")
    blocked, reasons = module.check_production_guard("prod-db.rds.amazonaws.com")
    assert blocked is True
    assert reasons


def test_max_targets_cannot_exceed_three(tmp_path, monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_max")
    monkeypatch.setenv(module.ALLOW_FLAG, "1")
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "probe",
            "--max-targets",
            "4",
            "--output-manifest",
            str(manifest),
            "--report",
            str(tmp_path / "report.md"),
            "--review-report",
            str(tmp_path / "review.md"),
        ],
    )
    assert module.main() == 1
    assert (
        json.loads(manifest.read_text(encoding="utf-8"))["stop_reason"] == "max_targets_exceeds_3"
    )


def test_concurrency_and_attempts_fixed_to_one():
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_limits")
    assert module.CONCURRENCY == 1
    assert module.MAX_ATTEMPTS_PER_TARGET == 1
    assert module.MAX_TARGETS_LIMIT == 3


def test_200_json_like_response_records_top_level_keys(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_json")
    response = FakeResponse(b'{"alpha":1,"beta":2}', content_type="application/json")
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(response=response))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["status_code"] == 200
    assert result["json_parse_ok"] is True
    assert result["top_level_keys_sample"] == ["alpha", "beta"]
    assert "body" not in result


def test_403_triggers_stop(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_403")
    error = HTTPError(
        "https://example.invalid", 403, "Forbidden", {"content-type": "text/html"}, BytesIO(b"no")
    )
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(error=error))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "http_403"
    assert result["stop_policy_triggered"] is True


def test_429_triggers_stop(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_429")
    error = HTTPError(
        "https://example.invalid", 429, "Too Many", {"content-type": "text/html"}, BytesIO(b"no")
    )
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(error=error))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "http_429"
    assert result["stop_policy_triggered"] is True


def test_text_html_triggers_unexpected_html(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_html")
    response = FakeResponse(b"<!doctype html><html></html>", content_type="text/html")
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(response=response))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "unexpected_html"
    assert result["stop_policy_triggered"] is True


def test_captcha_like_html_triggers_captcha_detected(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_captcha")
    response = FakeResponse(b"<html>captcha required</html>", content_type="text/html")
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(response=response))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "captcha_or_bot_challenge"
    assert result["stop_policy_triggered"] is True


def test_network_timeout_triggers_network_error(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_timeout")
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(error=TimeoutError()))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "network_timeout"
    assert result["stop_policy_triggered"] is True


def test_response_too_large_triggers_stop(monkeypatch):
    module = _load(SCRIPT_PATH, "fotmob_one_day_live_fetch_no_raw_write_large")
    payload = b"{" + b'"a":1,' * 200000 + b'"b":2}'
    response = FakeResponse(payload, content_type="application/json")
    monkeypatch.setattr(module, "build_opener", lambda *_args: FakeOpener(response=response))
    result = module.probe_target(_target(), timeout_seconds=1)
    assert result["error_category"] == "response_too_large"
    assert result["stop_policy_triggered"] is True


def test_no_raw_body_persistence_or_write_paths():
    code = _text(SCRIPT_PATH).lower()
    for token in ["ins" + "ert ", "upd" + "ate ", "del" + "ete ", "trun" + "cate ", "dr" + "op "]:
        assert token not in code
    assert "raw_response_body_saved" in code
    assert "body" not in _json(MANIFEST_PATH).get("fetch_results", [{}])[0]


def test_no_scheduler_parser_or_feature_path():
    data = _json(MANIFEST_PATH)
    safety = data["safety"]
    assert safety["scheduler_enabled"] is False
    assert safety["feature_parse_performed"] is False
    assert safety["raw_write_ready_marked"] is False


def test_checker_validates_manifest_report_review():
    checker = _load(CHECKER_PATH, "fotmob_one_day_live_fetch_no_raw_write_check")
    result = checker.run_checks()
    assert result["verdict"] == "pass"


def test_stop_policy_fields_required():
    data = _json(MANIFEST_PATH)
    assert "stopped_early" in data
    assert "stop_reason" in data
    assert "fetch_results" in data


def test_safety_flags_required():
    safety = _json(MANIFEST_PATH)["safety"]
    for key in [
        "network_fetch_performed",
        "raw_response_body_saved",
        "raw_json_write_performed",
        "fotmob_raw_match_payloads_write_performed",
        "raw_match_data_write_performed",
        "feature_parse_performed",
        "scheduler_enabled",
        "raw_write_ready_marked",
        "browser_automation_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
        "retry_storm_performed",
    ]:
        assert key in safety
