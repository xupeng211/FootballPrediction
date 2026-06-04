#!/usr/bin/env python3
"""Probe FotMob endpoint candidates selected by #1440 — metadata only, no body save.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE

Probes up to 3 match IDs against 3 endpoint templates from #1440 review.
Default dry-run. Requires --allow-network-probe for live. Metadata only.
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

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"
SCHEMA_VERSION = "fotmob_controlled_endpoint_candidate_probe_no_write_v1"
DRY_RUN_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"
JSON_OK_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-BODY-CAPTURE-PLAN-NO-WRITE"
JSON_FAIL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-CANDIDATE-REVIEW-FOLLOWUP-NO-WRITE"
NETWORK_TIMEOUT = 10
READ_LIMIT = 1024

# From #1440 next probe plan
ENDPOINT_TEMPLATES: list[dict[str, Any]] = [
    {
        "template": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}",
        "source": "#1440 ep-cand-002",
        "reason": "Canonical /api/data/matchDetails from production FotMobApiClient.js",
    },
    {
        "template": "https://www.fotmob.com/match/{match_id}",
        "source": "#1440 ep-cand-004",
        "reason": "HTML hydration route from FotMobRawDetailFetcher.js, known HTTP 200",
    },
    {
        "template": "https://www.fotmob.com/matches/{route_code}/{match_id}",
        "source": "#1440 ep-cand-005",
        "reason": "SSR page route, ADG60 validated, uses route_code from user seeds",
    },
]

# Preferred samples from #1440
PREFERRED_SAMPLES: list[tuple[str, str, str]] = [
    ("4813722", "2ygkcb", "Liverpool vs Manchester United"),
    ("4813492", "2ynv4k", "Everton vs Manchester United"),
    ("4813622", "2xqo0r", "Tottenham Hotspur vs Manchester United"),
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


def build_urls(
    samples: list[dict[str, str]], templates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build probe plan cross product of samples x templates."""
    plan: list[dict[str, Any]] = []
    for i, s in enumerate(samples):
        for j, t in enumerate(templates):
            url = (
                t["template"]
                .replace("{match_id}", s["match_id"])
                .replace("{route_code}", s["route_code"])
            )
            plan.append(
                {
                    "probe_id": f"probe-s{i + 1:02d}-t{j + 1:02d}",
                    "match_id": s["match_id"],
                    "route_code": s["route_code"],
                    "team_pair": s["team_pair"],
                    "endpoint_template": t["template"],
                    "endpoint_source": t["source"],
                    "url_redacted": url,
                }
            )
    return plan


def probe_url(url: str, timeout: int) -> dict[str, Any]:
    """Single HTTP GET probe, returns metadata only."""
    result: dict[str, Any] = {
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
        req.add_header(
            "User-Agent", "FootballPrediction/1.0 (endpoint-candidate-probe; metadata-only)"
        )
        req.add_header("Accept", "application/json")
        resp = request.urlopen(req, timeout=timeout)
        elapsed = int((time.monotonic() - t0) * 1000)
        result["elapsed_ms"] = elapsed
        result["status_code"] = resp.status
        ct = resp.headers.get("Content-Type", "")
        result["content_type"] = ct
        cl = resp.headers.get("Content-Length")
        if cl:
            try:
                result["content_length"] = int(cl)
            except (ValueError, TypeError):
                pass
        result["redirect_url"] = resp.geturl()
        if resp.status == 200 and "json" in ct.lower():
            result["json_parse_attempted"] = True
            try:
                data = json.loads(resp.read(READ_LIMIT))
                result["json_parse_ok"] = True
                result["top_level_key_names"] = (
                    sorted(data.keys()) if isinstance(data, dict) else []
                )
                if isinstance(data, dict):
                    for k in ("matchId", "header", "general", "content"):
                        result["required_key_presence"][k] = k in data
            except Exception:
                result["json_parse_ok"] = False
        elif resp.status == 403:
            result["stop_reason"] = "blocked_403"
        elif resp.status == 429:
            result["stop_reason"] = "blocked_429"
        elif resp.status == 404:
            result["stop_reason"] = "invalid_404"
    except error.HTTPError as e:
        result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        result["status_code"] = e.code
        if e.code == 403:
            result["stop_reason"] = "blocked_403"
        elif e.code == 429:
            result["stop_reason"] = "blocked_429"
        elif e.code == 404:
            result["stop_reason"] = "invalid_404"
        else:
            result["stop_reason"] = f"http_error_{e.code}"
    except Exception as e:
        result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        result["stop_reason"] = f"error_{type(e).__name__}"
    return result


def validation_state(r: dict[str, Any]) -> str:
    if r.get("json_parse_ok"):
        return "endpoint_candidate_json_observed"
    stop = r.get("stop_reason", "")
    if stop in ("blocked_403", "blocked_429"):
        return "endpoint_candidate_blocked"
    if stop == "invalid_404":
        return "endpoint_candidate_invalid"
    if r.get("content_type") and "html" in str(r["content_type"]).lower():
        return "endpoint_candidate_html"
    return "endpoint_candidate_not_json"


def run_probes(plan, max_requests, allow_network):
    results = []
    blocked = False
    for item in plan:
        r = {
            "probe_id": item["probe_id"],
            "match_id": item["match_id"],
            "route_code": item["route_code"],
            "team_pair": item["team_pair"],
            "endpoint_template": item["endpoint_template"],
            "endpoint_source": item["endpoint_source"],
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
            "validation_state": "endpoint_candidate_planned",
            "stop_reason": "dry_run_no_network",
            "elapsed_ms": 0,
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "db_write_performed": False,
            "raw_write_eligible": False,
        }
        if (
            allow_network
            and not blocked
            and sum(1 for p in results if p["network_performed"]) < max_requests
        ):
            r["network_performed"] = True
            live = probe_url(item["url_redacted"], NETWORK_TIMEOUT)
            for k in (
                "status_code",
                "content_type",
                "content_length",
                "redirect_url",
                "json_parse_attempted",
                "json_parse_ok",
                "top_level_key_names",
                "required_key_presence",
                "elapsed_ms",
            ):
                r[k] = live.get(k, r[k])
            r["stop_reason"] = live.get("stop_reason") or r["stop_reason"]
            r["validation_state"] = validation_state(live)
            if live.get("stop_reason") in ("blocked_403", "blocked_429"):
                blocked = True
        results.append(r)

    attempted = sum(1 for p in results if p["network_performed"])
    json_ok = sum(1 for p in results if p.get("json_parse_ok"))
    json_attempted = sum(1 for p in results if p.get("json_parse_attempted"))
    html_count = sum(
        1 for p in results if p.get("content_type") and "html" in str(p["content_type"]).lower()
    )
    blocked_count = sum(
        1 for p in results if p.get("validation_state") == "endpoint_candidate_blocked"
    )
    invalid_count = sum(
        1 for p in results if p.get("validation_state") == "endpoint_candidate_invalid"
    )
    not_json_count = sum(
        1 for p in results if p.get("validation_state") == "endpoint_candidate_not_json"
    )
    observed_count = sum(
        1 for p in results if p.get("validation_state") == "endpoint_candidate_json_observed"
    )

    sc_summary: dict[str, int] = {}
    ct_summary: dict[str, int] = {}
    for p in results:
        if p.get("status_code") is not None:
            sc_summary[str(p["status_code"])] = sc_summary.get(str(p["status_code"]), 0) + 1
        if p.get("content_type"):
            ct_summary[p["content_type"]] = ct_summary.get(p["content_type"], 0) + 1

    summary = {
        "allow_network_probe": allow_network,
        "max_network_requests": max_requests,
        "network_requests_attempted": attempted,
        "status_code_summary": sc_summary,
        "content_type_summary": ct_summary,
        "json_parse_attempted_count": json_attempted,
        "json_parse_ok_count": json_ok,
        "json_observed_count": observed_count,
        "html_detected_count": html_count,
        "blocked_count": blocked_count,
        "invalid_count": invalid_count,
        "not_json_count": not_json_count,
    }
    return results, summary


def build_manifest(
    run_id,
    mode,
    seed_manifest,
    review_manifest,
    samples,
    templates,
    results,
    summary,
    allow_network,
):
    json_ok = summary["json_parse_ok_count"]
    rec_next = (
        DRY_RUN_NEXT if not allow_network else (JSON_OK_NEXT if json_ok >= 1 else JSON_FAIL_NEXT)
    )

    safety = dict(SAFETY_FALSE)
    if allow_network and summary["network_requests_attempted"] > 0:
        safety["network_fetch_performed"] = True

    observed = sum(
        1 for r in results if r["validation_state"] == "endpoint_candidate_json_observed"
    )
    blocked = sum(1 for r in results if r["validation_state"] == "endpoint_candidate_blocked")
    invalid = sum(1 for r in results if r["validation_state"] == "endpoint_candidate_invalid")
    not_json = sum(1 for r in results if r["validation_state"] == "endpoint_candidate_not_json")

    # Endpoint decisions
    ep_stats: dict[str, dict] = {}
    for r in results:
        t = r["endpoint_template"]
        if t not in ep_stats:
            ep_stats[t] = {
                "attempted": 0,
                "json_observed": 0,
                "html": 0,
                "blocked": 0,
                "invalid": 0,
            }
        ep_stats[t]["attempted"] += 1
        if r["validation_state"] == "endpoint_candidate_json_observed":
            ep_stats[t]["json_observed"] += 1
        if r["validation_state"] == "endpoint_candidate_html":
            ep_stats[t]["html"] += 1
        if r["validation_state"] == "endpoint_candidate_blocked":
            ep_stats[t]["blocked"] += 1
        if r["validation_state"] == "endpoint_candidate_invalid":
            ep_stats[t]["invalid"] += 1

    usable = [t for t, s in ep_stats.items() if s["json_observed"] > 0]
    rejected = [t for t, s in ep_stats.items() if s["invalid"] > 0 or s["blocked"] > 0]
    deferred = [t for t, s in ep_stats.items() if s["html"] > 0 and s["json_observed"] == 0]

    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_endpoint_review": {
            "rejected_endpoint_count": len(review_manifest.get("rejected_endpoints", [])),
            "endpoint_candidate_count": len(review_manifest.get("endpoint_candidates", [])),
            "next_probe_candidate_count": review_manifest.get("next_probe_plan", {}).get(
                "selected_candidate_count", 3
            ),
            "previous_invalid_count": review_manifest.get("inherited_probe_status", {}).get(
                "invalid_count", 9
            ),
            "previous_json_parse_ok_count": review_manifest.get("inherited_probe_status", {}).get(
                "json_parse_ok_count", 0
            ),
        },
        "probe_selection": {
            "max_samples": len(samples),
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "selected_teams": [s["team_pair"] for s in samples],
            "selected_endpoint_templates": [t["template"] for t in templates],
        },
        "probe_results": results,
        "probe_summary": summary,
        "endpoint_decision": {
            "usable_endpoint_templates": usable,
            "rejected_endpoint_templates": rejected,
            "deferred_endpoint_templates": deferred,
            "recommended_next_template": usable[0]
            if usable
            else (deferred[0] if deferred else None),
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "raw_body_capture_planning_required": json_ok >= 1,
        },
        "safety": safety,
        "embedded_review": {
            "endpoint_candidate_probe_status": "pass",
            "review_report_path": "",
        },
        "recommended_next_phase": rec_next,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Probe FotMob endpoint candidates — metadata only")
    p.add_argument("--endpoint-review-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--decision-report", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-samples", type=int, default=3)
    p.add_argument("--max-endpoint-templates", type=int, default=3)
    p.add_argument("--max-network-requests", type=int, default=9)
    p.add_argument("--allow-network-probe", action="store_true", default=False)
    args = p.parse_args()

    if args.max_samples > 3:
        print("ERROR: max-samples must be <= 3", file=sys.stderr)
        return 1
    if args.max_endpoint_templates > 3:
        print("ERROR: max-endpoint-templates must be <= 3", file=sys.stderr)
        return 1
    if args.max_network_requests > 9:
        print("ERROR: max-network-requests must be <= 9", file=sys.stderr)
        return 1

    seed = _load_json(Path(args.seed_manifest), "seed manifest")
    review = _load_json(Path(args.endpoint_review_manifest), "endpoint review manifest")

    # Build samples from preferred list
    samples: list[dict[str, str]] = []
    for mid, rc, tp in PREFERRED_SAMPLES[: args.max_samples]:
        samples.append({"match_id": mid, "route_code": rc, "team_pair": tp})

    templates = ENDPOINT_TEMPLATES[: args.max_endpoint_templates]
    plan = build_urls(samples, templates)
    mode = (
        "controlled_network_probe_no_write"
        if args.allow_network_probe
        else "dry_run_probe_plan_only"
    )
    results, summary = run_probes(plan, args.max_network_requests, args.allow_network_probe)

    manifest = build_manifest(
        args.run_id,
        mode,
        seed,
        review,
        samples,
        templates,
        results,
        summary,
        args.allow_network_probe,
    )

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Reports delegated to sibling module
    from fotmob_controlled_endpoint_candidate_probe_no_write_report import (  # noqa: E402
        write_decision_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, mode, manifest, samples, templates, summary)
    write_decision_report(Path(args.decision_report), manifest, results, templates, summary)
    review_ok = write_review_report(Path(args.review_report), args.run_id, manifest, summary)

    for r in results:
        if (
            r.get("raw_write_eligible")
            or r.get("raw_json_write_performed")
            or r.get("raw_response_body_saved")
        ):
            print(f"ERROR: SAFETY VIOLATION in {r['probe_id']}", file=sys.stderr)
            return 1

    s = manifest["safety"]
    if s.get("raw_json_write_performed") is not False or s.get("db_write_performed") is not False:
        print("ERROR: SAFETY VIOLATION", file=sys.stderr)
        return 1

    if not review_ok:
        print("WARNING: embedded review has blocked checks", file=sys.stderr)
        return 1

    print(
        f"SUCCESS: mode={mode}, selected={len(samples)}, attempted={summary['network_requests_attempted']}, json_ok={summary['json_parse_ok_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
