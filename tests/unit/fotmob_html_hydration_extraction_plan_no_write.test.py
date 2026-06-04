"""Tests for FotMob HTML hydration extraction plan no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_html_hydration_extraction_plan_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_html_hydration_extraction_plan_no_write_check.py"

import fotmob_html_hydration_extraction_plan_no_write as pm  # noqa: E402


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, text=True, capture_output=True, check=False
    )


def _base(tmp_path) -> list[str]:
    return [
        "--route-probe-manifest",
        "docs/_manifests/fotmob_html_hydration_route_probe_no_write_manifest.json",
        "--seed-manifest",
        "docs/_manifests/fotmob_known_match_page_user_seeds_parse_no_write_manifest.json",
        "--output-manifest",
        str(tmp_path / "m.json"),
        "--report",
        str(tmp_path / "r.md"),
        "--review-report",
        str(tmp_path / "rv.md"),
        "--next-plan",
        str(tmp_path / "n.md"),
        "--run-id",
        "test",
    ]


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_missing_route_manifest_fails(tmp_path):
    args = _base(tmp_path)
    args[1] = str(tmp_path / "missing.json")
    assert _run(args).returncode != 0


def test_missing_seed_manifest_fails(tmp_path):
    args = _base(tmp_path)
    args[3] = str(tmp_path / "missing.json")
    assert _run(args).returncode != 0


def test_script_run_succeeds(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["mode"] == "offline_extraction_plan"
    assert m["inherited_route_probe"]["html_route_observed_count"] == 6


def test_extraction_candidates_generated():
    cands = pm.build_extraction_candidates(pm.SAMPLES, pm.ROUTES)
    assert len(cands) >= 2
    for c in cands:
        assert "candidate_id" in c
        assert "allowed_markers" in c
        assert "__NEXT_DATA__" in c["allowed_markers"]
        assert "pageProps" in c["allowed_markers"]
        assert c["body_read_limit_bytes"] <= pm.MAX_BODY_BYTES


def test_forbidden_persistence():
    next_plan = pm.build_next_plan([])
    fp = " ".join(str(x) for x in next_plan["forbidden_persistence"])
    assert "full HTML" in fp
    assert "raw JSON" in fp
    assert "DB write" in fp


def test_max_body_bytes():
    next_plan = pm.build_next_plan([])
    assert next_plan["max_body_bytes"] <= 524288


def test_max_network_requests():
    next_plan = pm.build_next_plan([])
    assert next_plan["max_network_requests"] <= 4


def test_next_phase_correct():
    next_plan = pm.build_next_plan([])
    assert "LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE" in next_plan["phase"]


def test_manifest_sections(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    for sec in [
        "schema_version",
        "phase",
        "mode",
        "inherited_route_probe",
        "extraction_plan_candidates",
        "limited_inspection_next_plan",
        "raw_write_readiness",
        "safety",
        "recommended_next_phase",
    ]:
        assert sec in m, f"Missing: {sec}"


def test_safety_flags(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    s = m["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "raw_response_body_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
        "scheduler_enabled",
        "browser_automation_performed",
    ]:
        assert s[k] is False, f"{k} must be false"


def test_readiness_values(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    rw = m["raw_write_readiness"]
    assert rw["json_validated_count"] == 0
    assert rw["raw_write_eligible_count"] == 0


def test_next_phase_not_raw_write(tmp_path):
    r = _run(_base(tmp_path))
    assert r.returncode == 0
    m = json.loads(Path(tmp_path / "m.json").read_text(encoding="utf-8"))
    assert m["recommended_next_phase"] == pm.NEXT_PHASE
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        assert w not in m["recommended_next_phase"]
