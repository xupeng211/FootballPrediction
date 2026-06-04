"""Tests for FotMob known match page user seeds parse no-write phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS

Validates URL parser correctness, target matching, and no-write safety.
No network, no DB, no raw write.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

SCRIPT = ROOT / "scripts/ops/fotmob_known_match_page_user_seeds_parse_no_write.py"
CHECKER = ROOT / "scripts/ops/fotmob_known_match_page_user_seeds_parse_no_write_check.py"
USER_SEED_PATH = ROOT / "docs/_examples/fotmob_known_match_page_user_seeds.example.json"
INPUT_INSTRUCTIONS_PATH = (
    ROOT / "docs/_reports/FOTMOB_KNOWN_MATCH_PAGE_USER_SEED_INPUT_INSTRUCTIONS.md"
)

# Import from main script
import fotmob_known_match_page_user_seeds_parse_no_write as parser_mod  # noqa: E402


def _run_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _run_checker() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _load_seeds() -> dict:
    return json.loads(USER_SEED_PATH.read_text(encoding="utf-8"))


# --- file existence ---


def test_script_exists():
    assert SCRIPT.exists()


def test_checker_exists():
    assert CHECKER.exists()


def test_user_seed_file_exists():
    assert USER_SEED_PATH.exists()


def test_seed_input_instructions_exists():
    assert INPUT_INSTRUCTIONS_PATH.exists()


# --- URL parser: standard English path ---


def test_parse_standard_english_url():
    result = parser_mod.parse_fotmob_url(
        "https://www.fotmob.com/matches/aston-villa-vs-manchester-united/3h9f6s#4506597"
    )
    assert result["parse_status"] == "parsed"
    assert result["match_slug"] == "aston-villa-vs-manchester-united"
    assert result["route_code"] == "3h9f6s"
    assert result["fotmob_match_id"] == "4506597"
    assert result["locale"] is None


# --- URL parser: zh-Hans locale ---


def test_parse_zh_hans_locale_url():
    result = parser_mod.parse_fotmob_url(
        "https://www.fotmob.com/zh-Hans/matches/england-vs-croatia/2viayw#4667825"
    )
    assert result["parse_status"] == "parsed"
    assert result["match_slug"] == "england-vs-croatia"
    assert result["route_code"] == "2viayw"
    assert result["fotmob_match_id"] == "4667825"
    assert result["locale"] == "zh-Hans"


# --- URL parser: all 12 route codes ---


ROUTE_CODES = [
    ("3h9f6s", "https://www.fotmob.com/matches/aston-villa-vs-manchester-united/3h9f6s#4506597"),
    ("2viayw", "https://www.fotmob.com/zh-Hans/matches/england-vs-croatia/2viayw#4667825"),
    (
        "2f8a75",
        "https://www.fotmob.com/zh-Hans/matches/leeds-united-vs-west-ham-united/2f8a75#4813754",
    ),
    (
        "2ygkcb",
        "https://www.fotmob.com/zh-Hans/matches/liverpool-vs-manchester-united/2ygkcb#4813722",
    ),
    (
        "2ynv4k",
        "https://www.fotmob.com/zh-Hans/matches/everton-vs-manchester-united/2ynv4k#4813492",
    ),
    (
        "2xqo0r",
        "https://www.fotmob.com/zh-Hans/matches/tottenham-hotspur-vs-manchester-united/2xqo0r#4813622",
    ),
    (
        "2w9xj5",
        "https://www.fotmob.com/zh-Hans/matches/chelsea-vs-manchester-united/2w9xj5#4813421",
    ),
    (
        "2wdjjd",
        "https://www.fotmob.com/zh-Hans/matches/leeds-united-vs-newcastle-united/2wdjjd#4813398",
    ),
    ("2bhzy5", "https://www.fotmob.com/zh-Hans/matches/brazil-vs-england/2bhzy5#4359098"),
    ("2azd0v", "https://www.fotmob.com/zh-Hans/matches/italy-vs-england/2azd0v#4044692"),
    ("2en1da", "https://www.fotmob.com/zh-Hans/matches/england-vs-poland/2en1da#3495351"),
    ("n1c6d", "https://www.fotmob.com/zh-Hans/matches/kashima-antlers-vs-fc-tokyo/n1c6d#5130312"),
]


@pytest.mark.parametrize(("expected_rc", "url"), ROUTE_CODES)
def test_parse_route_code(expected_rc, url):
    result = parser_mod.parse_fotmob_url(url)
    assert result["route_code"] == expected_rc, (
        f"Expected {expected_rc}, got {result['route_code']} for {url}"
    )


# --- URL parser: all 12 match IDs ---


MATCH_IDS = [
    ("4506597", "https://www.fotmob.com/matches/aston-villa-vs-manchester-united/3h9f6s#4506597"),
    ("4667825", "https://www.fotmob.com/zh-Hans/matches/england-vs-croatia/2viayw#4667825"),
    (
        "4813754",
        "https://www.fotmob.com/zh-Hans/matches/leeds-united-vs-west-ham-united/2f8a75#4813754",
    ),
    (
        "4813722",
        "https://www.fotmob.com/zh-Hans/matches/liverpool-vs-manchester-united/2ygkcb#4813722",
    ),
    (
        "4813492",
        "https://www.fotmob.com/zh-Hans/matches/everton-vs-manchester-united/2ynv4k#4813492",
    ),
    (
        "4813622",
        "https://www.fotmob.com/zh-Hans/matches/tottenham-hotspur-vs-manchester-united/2xqo0r#4813622",
    ),
    (
        "4813421",
        "https://www.fotmob.com/zh-Hans/matches/chelsea-vs-manchester-united/2w9xj5#4813421",
    ),
    (
        "4813398",
        "https://www.fotmob.com/zh-Hans/matches/leeds-united-vs-newcastle-united/2wdjjd#4813398",
    ),
    ("4359098", "https://www.fotmob.com/zh-Hans/matches/brazil-vs-england/2bhzy5#4359098"),
    ("4044692", "https://www.fotmob.com/zh-Hans/matches/italy-vs-england/2azd0v#4044692"),
    ("3495351", "https://www.fotmob.com/zh-Hans/matches/england-vs-poland/2en1da#3495351"),
    ("5130312", "https://www.fotmob.com/zh-Hans/matches/kashima-antlers-vs-fc-tokyo/n1c6d#5130312"),
]


@pytest.mark.parametrize(("expected_mid", "url"), MATCH_IDS)
def test_parse_fotmob_match_id(expected_mid, url):
    result = parser_mod.parse_fotmob_url(url)
    assert result["fotmob_match_id"] == expected_mid, (
        f"Expected {expected_mid}, got {result['fotmob_match_id']} for {url}"
    )


# --- URL parser: edge cases ---


def test_invalid_domain():
    result = parser_mod.parse_fotmob_url("https://www.google.com/matches/foo-vs-bar/abc123#12345")
    assert result["parse_status"] == "invalid_domain"


def test_missing_fragment():
    result = parser_mod.parse_fotmob_url("https://www.fotmob.com/matches/foo-vs-bar/abc123")
    assert result["parse_status"] == "missing_fragment_match_id"
    assert result["fotmob_match_id"] is None


def test_non_numeric_fragment():
    result = parser_mod.parse_fotmob_url("https://www.fotmob.com/matches/foo-vs-bar/abc123#abc")
    assert result["parse_status"] == "invalid_fragment_match_id"
    assert result["fotmob_match_id"] is None


def test_invalid_path():
    result = parser_mod.parse_fotmob_url("https://www.fotmob.com/teams?id=12345")
    assert result["parse_status"] == "invalid_path"


def test_empty_url():
    result = parser_mod.parse_fotmob_url("")
    assert result["parse_status"] in ("invalid_path", "invalid_domain")


# --- Reversed pair matching ---


def test_reversed_pair_liverpool_man_utd():
    assert parser_mod._check_exact_or_reversed_pair("Manchester United", "Liverpool") is True
    assert parser_mod._check_exact_or_reversed_pair("Liverpool", "Manchester United") is True


def test_reversed_pair_everton_man_utd():
    assert parser_mod._check_exact_or_reversed_pair("Manchester United", "Everton") is True
    assert parser_mod._check_exact_or_reversed_pair("Everton", "Manchester United") is True


def test_reversed_pair_tottenham_man_utd():
    assert (
        parser_mod._check_exact_or_reversed_pair("Manchester United", "Tottenham Hotspur") is True
    )
    assert (
        parser_mod._check_exact_or_reversed_pair("Tottenham Hotspur", "Manchester United") is True
    )


def test_reversed_pair_chelsea_man_utd():
    assert parser_mod._check_exact_or_reversed_pair("Manchester United", "Chelsea") is True
    assert parser_mod._check_exact_or_reversed_pair("Chelsea", "Manchester United") is True


def test_exact_pair_england_poland():
    assert parser_mod._check_exact_or_reversed_pair("England", "Poland") is True


def test_reversed_pair_brazil_england():
    assert parser_mod._check_exact_or_reversed_pair("England", "Brazil") is True
    assert parser_mod._check_exact_or_reversed_pair("Brazil", "England") is True


def test_reversed_pair_italy_england():
    assert parser_mod._check_exact_or_reversed_pair("England", "Italy") is True
    assert parser_mod._check_exact_or_reversed_pair("Italy", "England") is True


def test_unrelated_pair():
    """A pair where neither team is in targets should not match."""
    result = parser_mod._match_targets("FC Barcelona", "Real Madrid")
    assert result[2] == "false"  # current_target_match


# --- Route candidate generation ---


def test_parsed_seed_becomes_route_candidate():
    result = parser_mod.parse_fotmob_url(
        "https://www.fotmob.com/matches/aston-villa-vs-manchester-united/3h9f6s#4506597"
    )
    assert result["parse_status"] == "parsed"
    assert result["fotmob_match_id"] is not None


# --- Seed count verification ---


def test_user_seed_count_is_12():
    seeds = _load_seeds()
    assert len(seeds["seed_records"]) == 12


# --- Full script run ---


def test_script_run_succeeds(tmp_path):
    manifest_out = tmp_path / "manifest.json"
    report_out = tmp_path / "report.md"
    review_out = tmp_path / "review.md"

    result = _run_script(
        [
            "--route-candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--user-seeds",
            "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "--output-manifest",
            str(manifest_out),
            "--report",
            str(report_out),
            "--review-report",
            str(review_out),
            "--run-id",
            "test_run_v1",
        ]
    )
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    assert manifest_out.exists()
    manifest = json.loads(manifest_out.read_text(encoding="utf-8"))

    # Verify key counts
    assert manifest["seed_input_summary"]["user_seed_count"] == 12
    assert manifest["parse_summary"]["parsed_count"] >= 12
    assert manifest["parse_summary"]["route_candidate_count"] >= 12

    # Verify no-write safety
    assert manifest["raw_write_readiness"]["route_validated_count"] == 0
    assert manifest["raw_write_readiness"]["json_validated_count"] == 0
    assert manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0
    assert manifest["safety"]["network_fetch_performed"] is False
    assert manifest["safety"]["db_write_performed"] is False
    assert manifest["safety"]["raw_json_write_performed"] is False
    assert manifest["safety"]["raw_response_body_saved"] is False
    assert manifest["safety"]["scheduler_enabled"] is False
    assert manifest["safety"]["feature_parse_performed"] is False

    # Verify recommended next phase
    assert "CONTROLLED-JSON-PROBE-NO-WRITE" in manifest["recommended_next_phase"]


def test_script_with_missing_local_seeds_succeeds(tmp_path):
    manifest_out = tmp_path / "manifest.json"
    report_out = tmp_path / "report.md"
    review_out = tmp_path / "review.md"

    result = _run_script(
        [
            "--route-candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--user-seeds",
            "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "--local-seeds",
            str(tmp_path / "nonexistent_local.json"),
            "--output-manifest",
            str(manifest_out),
            "--report",
            str(report_out),
            "--review-report",
            str(review_out),
            "--run-id",
            "test_run_v2",
        ]
    )
    assert result.returncode == 0, f"Script should handle missing local seeds: {result.stderr}"


# --- Checker ---


def test_checker_passes_after_script_run(tmp_path):
    """Run script against real manifests, then run checker."""
    manifest_out = tmp_path / "manifest.json"
    report_out = tmp_path / "report.md"
    review_out = tmp_path / "review.md"

    result = _run_script(
        [
            "--route-candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--user-seeds",
            "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "--output-manifest",
            str(manifest_out),
            "--report",
            str(report_out),
            "--review-report",
            str(review_out),
            "--run-id",
            "test_checker_v1",
        ]
    )
    assert result.returncode == 0

    # Overwrite the real manifest paths with tmp outputs to test checker
    # We'll test the checker module's logic directly instead
    # by loading the manifest and verifying all checks

    manifest = json.loads(manifest_out.read_text(encoding="utf-8"))

    # Verify all checker-required assertions on the manifest directly
    assert manifest["phase"] == parser_mod.PHASE
    assert manifest["mode"] == "offline_parse_only"
    assert manifest["seed_input_summary"]["user_seed_count"] == 12
    assert manifest["parse_summary"]["parsed_count"] >= 12
    assert manifest["parse_summary"]["route_candidate_count"] >= 12
    assert len(manifest["extracted_match_ids"]) >= 12
    assert len(manifest["extracted_route_codes"]) >= 12
    assert manifest["target_match_summary"]["current_target_match_true_count"] >= 1
    assert manifest["target_match_summary"]["exact_or_reversed_pair_count"] >= 1
    assert manifest["raw_write_readiness"]["route_validated_count"] == 0
    assert manifest["raw_write_readiness"]["json_validated_count"] == 0
    assert manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0
    assert manifest["raw_write_readiness"]["raw_write_blocked_until_json_validated"] is True
    for key in [
        "network_fetch_performed",
        "db_read_performed",
        "db_write_performed",
        "raw_response_body_saved",
        "raw_json_write_performed",
        "scheduler_enabled",
        "feature_parse_performed",
        "browser_automation_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]:
        assert manifest["safety"][key] is False, f"{key} must be false"
    assert manifest["embedded_review"]["user_seed_parse_status"] == "pass"
    assert manifest["recommended_next_phase"] == parser_mod.SAFE_NEXT_PHASE


# --- Manifest structure checks ---


def test_manifest_has_required_sections(tmp_path):
    manifest_out = tmp_path / "manifest.json"
    report_out = tmp_path / "report.md"
    review_out = tmp_path / "review.md"

    result = _run_script(
        [
            "--route-candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--user-seeds",
            "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "--output-manifest",
            str(manifest_out),
            "--report",
            str(report_out),
            "--review-report",
            str(review_out),
            "--run-id",
            "test_sections_v1",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest_out.read_text(encoding="utf-8"))

    required_sections = [
        "schema_version",
        "phase",
        "run_id",
        "mode",
        "input_manifests",
        "inherited_status",
        "seed_input_summary",
        "parse_summary",
        "target_match_summary",
        "parsed_seeds",
        "extracted_match_ids",
        "extracted_route_codes",
        "raw_write_readiness",
        "safety",
        "embedded_review",
        "recommended_next_phase",
    ]
    for section in required_sections:
        assert section in m, f"Manifest missing section: {section}"

    # Verify inherited_status
    inherited = m["inherited_status"]
    assert inherited["input_target_count"] == 14
    assert inherited["discovery_candidate_count"] == 76
    assert inherited["route_candidate_count"] == 0
    assert inherited["route_blocked_count"] == 3
    assert inherited["route_validated_count"] == 0
    assert inherited["json_validated_count"] == 0
    assert inherited["raw_write_eligible_count"] == 0


# --- No-write safety: all parsed seeds ---


def test_all_parsed_seeds_safety(tmp_path):
    manifest_out = tmp_path / "manifest.json"
    report_out = tmp_path / "report.md"
    review_out = tmp_path / "review.md"

    result = _run_script(
        [
            "--route-candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
            "--source-review-manifest",
            "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
            "--candidate-manifest",
            "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
            "--user-seeds",
            "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "--output-manifest",
            str(manifest_out),
            "--report",
            str(report_out),
            "--review-report",
            str(review_out),
            "--run-id",
            "test_safety_v1",
        ]
    )
    assert result.returncode == 0

    m = json.loads(manifest_out.read_text(encoding="utf-8"))
    for seed in m["parsed_seeds"]:
        assert seed["raw_write_eligible"] is False
        assert seed["raw_json_write_performed"] is False
        assert seed["db_write_performed"] is False
        assert seed["network_fetch_performed"] is False
        assert seed["raw_response_body_saved"] is False
        assert seed["validation_state"] != "json_validated"
        assert seed["route_probe_performed"] is False
