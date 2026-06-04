#!/usr/bin/env python3
"""Controlled JSON probe for FotMob match IDs — metadata only, no body save.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE

Probes up to 3 FotMob match IDs against up to 3 endpoint templates each,
saving only response metadata. No raw response body, no DB, no raw JSON.
Default mode is dry-run (probe plan). Requires --allow-network-probe for live.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib import error, request

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"
SCHEMA_VERSION = "fotmob_controlled_json_probe_no_write_v1"
DRY_RUN_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"
JSON_OK_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-JSON-DEV-WRITE-PLANNING"
JSON_FAIL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE"
NETWORK_TIMEOUT_SECONDS = 10
READ_LIMIT_BYTES = 1024  # Only read first 1KB for metadata detection

ENDPOINT_CANDIDATES: list[dict[str, Any]] = [
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}",
        "reason": "Standard FotMob matchDetails API without geo/locale params",
        "enabled": True,
    },
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA",
        "reason": "FotMob matchDetails API with USA country code for content negotiation",
        "enabled": True,
    },
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC",
        "reason": "FotMob matchDetails API with UTC timezone override",
        "enabled": True,
    },
]

SAFETY_FALSE = {
    "network_fetch_performed": False,
    "db_read_performed": False,
    "db_write_performed": False,
    "production_db_write_performed": False,
    "raw_response_body_saved": False,
    "raw_json_write_performed": False,
    "fotmob_raw_match_payloads_write_performed": False,
    "raw_match_data_write_performed": False,
    "feature_parse_performed": False,
    "scheduler_enabled": False,
    "raw_write_ready_marked": False,
    "browser_automation_performed": False,
    "captcha_bypass_performed": False,
    "proxy_rotation_performed": False,
}


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def select_probe_samples(
    parsed_seeds: list[dict[str, Any]], max_samples: int
) -> list[dict[str, Any]]:
    """Select probes: exact/reversed pairs first, then team-related."""
    exact = [s for s in parsed_seeds if s.get("is_exact_or_reversed_pair")]
    team = [s for s in parsed_seeds if s.get("target_relevance") == "current_target_team_related"]
    selected = list(exact[:max_samples])
    if len(selected) < max_samples:
        selected.extend(team[: max_samples - len(selected)])
    return selected[:max_samples]


def build_probe_plan(
    selected: list[dict[str, Any]],
    endpoint_candidates: list[dict[str, Any]],
    max_endpoints: int,
) -> list[dict[str, Any]]:
    """Build the probe plan: cross product of seeds x endpoints."""
    plan: list[dict[str, Any]] = []
    for seed in selected:
        for i, ep in enumerate(endpoint_candidates[:max_endpoints]):
            if not ep.get("enabled", True):
                continue
            plan.append(
                {
                    "probe_id": f"probe-{seed['source_seed_id']}-ep{i + 1:02d}",
                    "source_seed_id": seed["source_seed_id"],
                    "team_hint": seed["team_hint"],
                    "opponent_hint": seed["opponent_hint"],
                    "route_code": seed["route_code"],
                    "fotmob_match_id": seed["fotmob_match_id"],
                    "endpoint_template": ep["endpoint_template"],
                    "url_redacted": ep["endpoint_template"].replace(
                        "{match_id}", seed["fotmob_match_id"]
                    ),
                }
            )
    return plan


def probe_endpoint(url: str, timeout: int) -> dict[str, Any]:
    """Perform a single HTTP GET probe, returning metadata only.

    Reads at most READ_LIMIT_BYTES of the response body for JSON detection,
    then discards it. Never persists the body.
    """
    result: dict[str, Any] = {
        "url_redacted": url,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "redirect_url": None,
        "json_parse_attempted": False,
        "json_parse_ok": False,
        "top_level_key_names": [],
        "required_key_presence": {},
        "stop_reason": None,
        "elapsed_ms": 0,
    }

    t0 = time.monotonic()
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "FootballPrediction/1.0 (controlled-probe; metadata-only)")
        req.add_header("Accept", "application/json")
        resp = request.urlopen(req, timeout=timeout)
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["status_code"] = resp.status
        content_type = resp.headers.get("Content-Type", "")
        result["content_type"] = content_type
        cl = resp.headers.get("Content-Length")
        if cl:
            try:
                result["content_length"] = int(cl)
            except (ValueError, TypeError):
                pass
        result["redirect_url"] = resp.geturl()

        if resp.status == 200:
            if "json" in content_type.lower():
                result["json_parse_attempted"] = True
                try:
                    raw = resp.read(READ_LIMIT_BYTES)
                    data = json.loads(raw)
                    result["json_parse_ok"] = True
                    result["top_level_key_names"] = (
                        sorted(data.keys()) if isinstance(data, dict) else []
                    )
                    if isinstance(data, dict):
                        for k in ("matchId", "header", "general", "content"):
                            result["required_key_presence"][k] = k in data
                except (json.JSONDecodeError, Exception):
                    result["json_parse_ok"] = False
            else:
                result["stop_reason"] = "not_json_content_type"
        elif resp.status == 403:
            result["stop_reason"] = "blocked_403"
        elif resp.status == 429:
            result["stop_reason"] = "blocked_429_rate_limited"
        elif resp.status == 404:
            result["stop_reason"] = "invalid_404"

    except error.HTTPError as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["status_code"] = e.code
        if e.code == 403:
            result["stop_reason"] = "blocked_403"
        elif e.code == 429:
            result["stop_reason"] = "blocked_429_rate_limited"
        elif e.code == 404:
            result["stop_reason"] = "invalid_404"
        else:
            result["stop_reason"] = f"http_error_{e.code}"
    except error.URLError as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["stop_reason"] = f"url_error_{type(e.reason).__name__}"
    except TimeoutError:
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["stop_reason"] = "timeout"
    except Exception as e:
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["stop_reason"] = f"exception_{type(e).__name__}"

    return result


def determine_validation_state(probe_result: dict[str, Any]) -> str:
    """Map probe result to validation state."""
    if probe_result.get("json_parse_ok"):
        return "json_probe_observed"
    stop = probe_result.get("stop_reason", "")
    if stop in ("blocked_403", "blocked_429_rate_limited"):
        return "json_probe_blocked"
    if stop in ("invalid_404",):
        return "json_probe_invalid"
    if probe_result.get("status_code") and not probe_result.get("json_parse_ok"):
        ct = probe_result.get("content_type", "")
        if ct and "html" in ct.lower():
            return "json_probe_not_json"
    if stop and "url_error" in stop:
        return "json_probe_invalid"
    if stop and "timeout" in stop:
        return "json_probe_blocked"
    return "json_probe_not_json"


def run_probes(
    plan: list[dict[str, Any]],
    max_requests: int,
    allow_network: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute or dry-run the probe plan."""
    results: list[dict[str, Any]] = []
    blocked_globally = False

    for item in plan:
        probe_result = {
            "probe_id": item["probe_id"],
            "source_seed_id": item["source_seed_id"],
            "team_hint": item["team_hint"],
            "opponent_hint": item["opponent_hint"],
            "route_code": item["route_code"],
            "fotmob_match_id": item["fotmob_match_id"],
            "endpoint_template": item["endpoint_template"],
            "url_redacted": item["url_redacted"],
            "network_performed": False,
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "redirect_url": None,
            "json_parse_attempted": False,
            "json_parse_ok": False,
            "top_level_key_names": [],
            "required_key_presence": {},
            "stop_reason": "dry_run_no_network",
            "elapsed_ms": 0,
            "validation_state": "route_candidate",
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "db_write_performed": False,
            "raw_write_eligible": False,
        }

        if (
            allow_network
            and not blocked_globally
            and len([r for r in results if r["network_performed"]]) < max_requests
        ):
            # Check if previous probe blocked globally
            for prev in results:
                if prev.get("stop_reason") in ("blocked_429_rate_limited",):
                    blocked_globally = True
                    break

            if not blocked_globally:
                probe_result["network_performed"] = True
                live = probe_endpoint(item["url_redacted"], NETWORK_TIMEOUT_SECONDS)
                probe_result.update({k: v for k, v in live.items() if k in probe_result})
                probe_result["validation_state"] = determine_validation_state(live)

                # Stop if 403/429
                if live.get("stop_reason") in ("blocked_403", "blocked_429_rate_limited"):
                    blocked_globally = True
                    probe_result["stop_reason"] = live["stop_reason"]
            else:
                probe_result["stop_reason"] = "stopped_due_to_global_block"
        else:
            probe_result["stop_reason"] = "dry_run_no_network"

        results.append(probe_result)

    # Compute summary
    network_attempted = sum(1 for r in results if r["network_performed"])
    json_parse_ok_count = sum(1 for r in results if r.get("json_parse_ok"))
    json_parse_attempted_count = sum(1 for r in results if r.get("json_parse_attempted"))
    html_detected_count = sum(
        1 for r in results if r.get("content_type") and "html" in str(r["content_type"]).lower()
    )
    blocked_count = sum(1 for r in results if r.get("validation_state") == "json_probe_blocked")
    invalid_count = sum(1 for r in results if r.get("validation_state") == "json_probe_invalid")
    not_json_count = sum(1 for r in results if r.get("validation_state") == "json_probe_not_json")

    status_summary: dict[str, int] = {}
    for r in results:
        sc = r.get("status_code")
        if sc is not None:
            key = str(sc)
            status_summary[key] = status_summary.get(key, 0) + 1

    ct_summary: dict[str, int] = {}
    for r in results:
        ct = r.get("content_type")
        if ct:
            ct_summary[ct] = ct_summary.get(ct, 0) + 1

    summary: dict[str, Any] = {
        "allow_network_probe": allow_network,
        "max_network_requests": max_requests,
        "network_requests_attempted": network_attempted,
        "status_code_summary": status_summary,
        "content_type_summary": ct_summary,
        "json_parse_attempted_count": json_parse_attempted_count,
        "json_parse_ok_count": json_parse_ok_count,
        "html_detected_count": html_detected_count,
        "blocked_count": blocked_count,
        "invalid_count": invalid_count,
        "not_json_count": not_json_count,
    }

    return results, summary


def build_manifest(
    run_id: str,
    mode: str,
    seed_manifest: dict[str, Any],
    selected: list[dict[str, Any]],
    endpoint_candidates: list[dict[str, Any]],
    max_endpoints: int,
    probe_results: list[dict[str, Any]],
    probe_summary: dict[str, Any],
    allow_network: bool,
) -> dict[str, Any]:
    """Build the output manifest."""
    seed_summary = seed_manifest["seed_input_summary"]
    parse_summary = seed_manifest["parse_summary"]
    target_summary = seed_manifest["target_match_summary"]

    observed_count = sum(
        1 for r in probe_results if r.get("validation_state") == "json_probe_observed"
    )
    blocked_count = sum(
        1 for r in probe_results if r.get("validation_state") == "json_probe_blocked"
    )
    invalid_count = sum(
        1 for r in probe_results if r.get("validation_state") == "json_probe_invalid"
    )
    not_json_count = sum(
        1 for r in probe_results if r.get("validation_state") == "json_probe_not_json"
    )

    json_ok = probe_summary.get("json_parse_ok_count", 0)

    if not allow_network:
        rec_next = DRY_RUN_NEXT
    elif json_ok >= 1:
        rec_next = JSON_OK_NEXT
    else:
        rec_next = JSON_FAIL_NEXT

    safety = dict(SAFETY_FALSE)
    if allow_network and probe_summary.get("network_requests_attempted", 0) > 0:
        safety["network_fetch_performed"] = True

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_seed_status": {
            "user_seed_count": seed_summary["user_seed_count"],
            "parsed_count": parse_summary["parsed_count"],
            "route_candidate_count": parse_summary["route_candidate_count"],
            "current_target_match_true_count": target_summary["current_target_match_true_count"],
            "exact_or_reversed_pair_count": target_summary["exact_or_reversed_pair_count"],
            "route_validated_count": 0,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "probe_selection": {
            "max_samples": len(selected),
            "selected_sample_count": len(selected),
            "selected_match_ids": [s["fotmob_match_id"] for s in selected],
            "selected_route_codes": [s["route_code"] for s in selected],
            "selected_teams": [f"{s['team_hint']} vs {s['opponent_hint']}" for s in selected],
        },
        "endpoint_candidates": [
            {
                "endpoint_template": ep["endpoint_template"],
                "reason": ep["reason"],
                "enabled": ep.get("enabled", True),
            }
            for ep in endpoint_candidates[:max_endpoints]
        ],
        "probe_results": probe_results,
        "probe_summary": probe_summary,
        "json_probe_readiness": {
            "json_probe_observed_count": observed_count,
            "json_probe_blocked_count": blocked_count,
            "json_probe_invalid_count": invalid_count,
            "json_probe_not_json_count": not_json_count,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "safety": safety,
        "embedded_review": {
            "controlled_json_probe_status": "pass"
            if not allow_network or json_ok >= 0
            else "blocked",
            "review_report_path": "",
        },
        "recommended_next_phase": rec_next,
    }
    return manifest


# Report generation delegated to sibling module
from fotmob_controlled_json_probe_no_write_report import (  # noqa: E402
    write_endpoint_decision_report,
    write_report,
    write_review_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Controlled FotMob JSON endpoint probe — metadata only"
    )
    parser.add_argument("--seed-manifest", required=True, help="Path to #1438 seed parse manifest")
    parser.add_argument("--output-manifest", required=True, help="Path for output manifest")
    parser.add_argument("--report", required=True, help="Path for output report")
    parser.add_argument("--review-report", required=True, help="Path for embedded review")
    parser.add_argument(
        "--endpoint-decision-report", required=True, help="Path for endpoint decision report"
    )
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--max-samples", type=int, default=3, help="Max probe samples (<=3)")
    parser.add_argument(
        "--max-endpoints-per-sample", type=int, default=3, help="Max endpoints per sample (<=3)"
    )
    parser.add_argument(
        "--max-network-requests", type=int, default=9, help="Max total network requests (<=9)"
    )
    parser.add_argument(
        "--allow-network-probe",
        action="store_true",
        default=False,
        help="Enable live network probes",
    )
    args = parser.parse_args()

    if args.max_samples > 3:
        print("ERROR: max-samples must be <= 3", file=sys.stderr)
        return 1
    if args.max_endpoints_per_sample > 3:
        print("ERROR: max-endpoints-per-sample must be <= 3", file=sys.stderr)
        return 1
    if args.max_network_requests > 9:
        print("ERROR: max-network-requests must be <= 9", file=sys.stderr)
        return 1

    seed_path = Path(args.seed_manifest)
    seed_manifest = _load_json(seed_path, "seed manifest")
    parsed_seeds = seed_manifest.get("parsed_seeds", [])
    selected = select_probe_samples(parsed_seeds, args.max_samples)
    if not selected:
        print("ERROR: no probe samples selected", file=sys.stderr)
        return 1

    enabled_eps = [ep for ep in ENDPOINT_CANDIDATES if ep.get("enabled", True)]
    plan = build_probe_plan(selected, enabled_eps, args.max_endpoints_per_sample)

    mode = (
        "controlled_network_probe_no_write"
        if args.allow_network_probe
        else "dry_run_probe_plan_only"
    )
    probe_results, probe_summary = run_probes(
        plan, args.max_network_requests, args.allow_network_probe
    )

    manifest = build_manifest(
        args.run_id,
        mode,
        seed_manifest,
        selected,
        enabled_eps,
        args.max_endpoints_per_sample,
        probe_results,
        probe_summary,
        args.allow_network_probe,
    )

    output_dir = Path(args.output_manifest).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    write_report(
        Path(args.report), args.run_id, mode, manifest, selected, probe_results, probe_summary
    )
    write_endpoint_decision_report(Path(args.endpoint_decision_report), manifest, probe_results)
    review_passed = write_review_report(
        Path(args.review_report), args.run_id, manifest, probe_summary
    )

    for r in probe_results:
        if r.get("raw_write_eligible"):
            print(
                f"ERROR: SAFETY VIOLATION — {r['probe_id']} raw_write_eligible=true",
                file=sys.stderr,
            )
            return 1
        if r.get("raw_json_write_performed"):
            print(
                f"ERROR: SAFETY VIOLATION — {r['probe_id']} raw_json_write_performed=true",
                file=sys.stderr,
            )
            return 1
        if r.get("raw_response_body_saved"):
            print(
                f"ERROR: SAFETY VIOLATION — {r['probe_id']} raw_response_body_saved=true",
                file=sys.stderr,
            )
            return 1

    safety = manifest["safety"]
    if safety.get("raw_json_write_performed") is not False:
        print("ERROR: SAFETY VIOLATION — raw_json_write_performed", file=sys.stderr)
        return 1
    if safety.get("db_write_performed") is not False:
        print("ERROR: SAFETY VIOLATION — db_write_performed", file=sys.stderr)
        return 1

    if not review_passed:
        print("WARNING: embedded review has blocked checks", file=sys.stderr)
        return 1

    print(
        f"SUCCESS: mode={mode}, selected={len(selected)} samples, attempted={probe_summary['network_requests_attempted']} requests, json_ok={probe_summary['json_parse_ok_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
