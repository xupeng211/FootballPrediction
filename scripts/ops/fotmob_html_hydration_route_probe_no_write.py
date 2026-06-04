#!/usr/bin/env python3
"""Probe FotMob HTML hydration page routes — metadata only, no body read.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE

Tests only /match/{id} and /matches/{rc}/{id} routes.
Does NOT test /api/data/matchDetails (rejected 403 in #1441).
Does NOT read response body — only status + headers metadata.
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

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE"
SCHEMA = "fotmob_html_hydration_route_probe_no_write_v1"
DRY_RUN_NEXT = PHASE
OBSERVED_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE"
FAIL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-REVIEW-FOLLOWUP-NO-WRITE"
TIMEOUT = 10

ROUTE_TEMPLATES: list[dict[str, Any]] = [
    {"template": "https://www.fotmob.com/match/{match_id}", "name": "html_hydration_match_page"},
    {
        "template": "https://www.fotmob.com/matches/{route_code}/{match_id}",
        "name": "html_hydration_matches_page",
    },
]

PREFERRED: list[tuple[str, str, str]] = [
    ("4813722", "2ygkcb", "Liverpool vs Manchester United"),
    ("4813492", "2ynv4k", "Everton vs Manchester United"),
    ("4813622", "2xqo0r", "Tottenham Hotspur vs Manchester United"),
]

SAFETY = {
    "network_fetch_performed": False,
    "db_read_performed": False,
    "db_write_performed": False,
    "production_db_write_performed": False,
    "response_body_read": False,
    "raw_response_body_saved": False,
    "html_body_saved": False,
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


def build_plan(samples, templates):
    plan = []
    for i, s in enumerate(samples):
        for j, t in enumerate(templates[:2]):
            url = (
                t["template"]
                .replace("{match_id}", s["match_id"])
                .replace("{route_code}", s["route_code"])
            )
            plan.append(
                {
                    "probe_id": f"html-probe-s{i + 1:02d}-t{j + 1:02d}",
                    "match_id": s["match_id"],
                    "route_code": s["route_code"],
                    "team_pair": s["team_pair"],
                    "route_template": t["template"],
                    "route_name": t["name"],
                    "url_redacted": url,
                }
            )
    return plan


def probe_url(url):
    """HTTP GET — reads ONLY status and headers, NOT body."""
    r = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "redirect_url": None,
        "location_header": None,
        "stop_reason": None,
        "elapsed_ms": 0,
    }
    t0 = time.monotonic()
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "FootballPrediction/1.0 (html-route-probe; metadata-only)")
        req.add_header("Accept", "text/html,application/xhtml+xml")
        resp = request.urlopen(req, timeout=TIMEOUT)
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["status_code"] = resp.status
        r["content_type"] = resp.headers.get("Content-Type", "")
        r["redirect_url"] = resp.geturl()
        r["location_header"] = resp.headers.get("Location", None)
        cl = resp.headers.get("Content-Length")
        if cl:
            try:
                r["content_length"] = int(cl)
            except (ValueError, TypeError):
                pass
        # Do NOT read body — close immediately
        resp.close()
        if resp.status in (301, 302, 303, 307, 308):
            r["stop_reason"] = "redirect"
        elif resp.status == 403:
            r["stop_reason"] = "blocked_403"
        elif resp.status == 429:
            r["stop_reason"] = "blocked_429"
        elif resp.status == 404:
            r["stop_reason"] = "invalid_404"
    except error.HTTPError as e:
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["status_code"] = e.code
        if e.code == 403:
            r["stop_reason"] = "blocked_403"
        elif e.code == 429:
            r["stop_reason"] = "blocked_429"
        elif e.code == 404:
            r["stop_reason"] = "invalid_404"
        else:
            r["stop_reason"] = f"http_error_{e.code}"
    except Exception as e:
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["stop_reason"] = f"error_{type(e).__name__}"
    return r


def val_state(r):
    """Determine validation state from headers-only probe."""
    stop = r.get("stop_reason", "")
    if stop == "redirect":
        return "html_route_redirect_observed"
    if r.get("status_code") == 200:
        ct = r.get("content_type", "")
        if "html" in ct.lower():
            return "html_route_observed"
        return "html_route_not_html"
    if stop in ("blocked_403", "blocked_429"):
        return "html_route_blocked"
    if stop == "invalid_404":
        return "html_route_invalid"
    return "html_route_not_html"


def run_probes(plan, max_req, allow_net):
    results = []
    blocked = False
    for item in plan:
        pr = {
            "probe_id": item["probe_id"],
            "match_id": item["match_id"],
            "route_code": item["route_code"],
            "team_pair": item["team_pair"],
            "route_template": item["route_template"],
            "route_name": item["route_name"],
            "url_redacted": item["url_redacted"],
            "network_performed": False,
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "redirect_url": None,
            "location_header": None,
            "validation_state": "html_route_planned",
            "stop_reason": "dry_run_no_network",
            "elapsed_ms": 0,
            "body_read": False,
            "raw_response_body_saved": False,
            "html_body_saved": False,
            "raw_json_write_performed": False,
            "db_write_performed": False,
            "raw_write_eligible": False,
        }
        if (
            allow_net
            and not blocked
            and sum(1 for p in results if p["network_performed"]) < max_req
        ):
            pr["network_performed"] = True
            live = probe_url(item["url_redacted"])
            for k in (
                "status_code",
                "content_type",
                "content_length",
                "redirect_url",
                "location_header",
                "stop_reason",
                "elapsed_ms",
            ):
                pr[k] = live.get(k, pr.get(k))
            pr["validation_state"] = val_state(live)
            if live.get("stop_reason") in ("blocked_403", "blocked_429"):
                blocked = True
        results.append(pr)

    attempted = sum(1 for p in results if p["network_performed"])
    observed = sum(1 for p in results if p["validation_state"] == "html_route_observed")
    redirect = sum(1 for p in results if p["validation_state"] == "html_route_redirect_observed")
    blocked_c = sum(1 for p in results if p["validation_state"] == "html_route_blocked")
    invalid = sum(1 for p in results if p["validation_state"] == "html_route_invalid")
    not_html = sum(1 for p in results if p["validation_state"] == "html_route_not_html")
    sc_sum: dict = {}
    ct_sum: dict = {}
    for p in results:
        if p.get("status_code") is not None:
            sc_sum[str(p["status_code"])] = sc_sum.get(str(p["status_code"]), 0) + 1
        if p.get("content_type"):
            ct_sum[p["content_type"]] = ct_sum.get(p["content_type"], 0) + 1

    summary = {
        "allow_network_probe": allow_net,
        "max_network_requests": max_req,
        "network_requests_attempted": attempted,
        "status_code_summary": sc_sum,
        "content_type_summary": ct_sum,
        "html_route_observed_count": observed,
        "html_route_redirect_observed_count": redirect,
        "html_route_blocked_count": blocked_c,
        "html_route_invalid_count": invalid,
        "html_route_not_html_count": not_html,
    }
    return results, summary


def build_manifest(run_id, mode, samples, templates, results, summary, allow_net):
    observed = summary["html_route_observed_count"]
    rec = DRY_RUN_NEXT if not allow_net else (OBSERVED_NEXT if observed >= 1 else FAIL_NEXT)
    safety = dict(SAFETY)
    if allow_net and summary["network_requests_attempted"] > 0:
        safety["network_fetch_performed"] = True

    # Route decisions
    rs: dict = {}
    for r in results:
        t = r["route_template"]
        if t not in rs:
            rs[t] = {"attempted": 0, "observed": 0, "redirect": 0, "blocked": 0, "invalid": 0}
        rs[t]["attempted"] += 1
        if r["validation_state"] == "html_route_observed":
            rs[t]["observed"] += 1
        if r["validation_state"] == "html_route_redirect_observed":
            rs[t]["redirect"] += 1
        if r["validation_state"] == "html_route_blocked":
            rs[t]["blocked"] += 1
        if r["validation_state"] == "html_route_invalid":
            rs[t]["invalid"] += 1
    usable = [t for t, s in rs.items() if s["observed"] > 0]
    rejected = [t for t, s in rs.items() if s["invalid"] > 0 or s["blocked"] > 0]
    deferred = [t for t, s in rs.items() if s["redirect"] > 0 and s["observed"] == 0]

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_endpoint_probe": {
            "api_data_matchDetails_status": "blocked_403",
            "api_data_matchDetails_attempted": 1,
            "json_parse_ok_count": 0,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "probe_selection": {
            "max_samples": len(samples),
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "selected_teams": [s["team_pair"] for s in samples],
            "selected_route_templates": [t["template"] for t in templates[:2]],
        },
        "probe_results": results,
        "probe_summary": summary,
        "route_decision": {
            "usable_html_route_templates": usable,
            "rejected_route_templates": rejected,
            "deferred_route_templates": deferred,
            "recommended_next_template": usable[0]
            if usable
            else (deferred[0] if deferred else None),
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "html_hydration_extraction_planning_required": observed >= 1,
        },
        "safety": safety,
        "embedded_review": {"html_hydration_route_probe_status": "pass", "review_report_path": ""},
        "recommended_next_phase": rec,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Probe FotMob HTML hydration routes — metadata only")
    p.add_argument("--endpoint-probe-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--decision-report", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-samples", type=int, default=3)
    p.add_argument("--max-route-templates", type=int, default=2)
    p.add_argument("--max-network-requests", type=int, default=6)
    p.add_argument("--allow-network-probe", action="store_true", default=False)
    args = p.parse_args()

    if args.max_samples > 3:
        print("ERROR: max-samples must be <= 3", file=sys.stderr)
        return 1
    if args.max_route_templates > 2:
        print("ERROR: max-route-templates must be <= 2", file=sys.stderr)
        return 1
    if args.max_network_requests > 6:
        print("ERROR: max-network-requests must be <= 6", file=sys.stderr)
        return 1

    samples = [
        {"match_id": m, "route_code": r, "team_pair": t}
        for m, r, t in PREFERRED[: args.max_samples]
    ]
    templates = ROUTE_TEMPLATES[: args.max_route_templates]
    plan = build_plan(samples, templates)
    mode = (
        "controlled_network_probe_no_write"
        if args.allow_network_probe
        else "dry_run_probe_plan_only"
    )
    results, summary = run_probes(plan, args.max_network_requests, args.allow_network_probe)
    manifest = build_manifest(
        args.run_id, mode, samples, templates, results, summary, args.allow_network_probe
    )

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mp = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    from fotmob_html_hydration_route_probe_no_write_report import (  # noqa: E402
        write_decision_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, mode, manifest, samples, templates, summary)
    write_decision_report(Path(args.decision_report), results, templates, summary)
    ok = write_review_report(Path(args.review_report), args.run_id, manifest, summary)

    for r in results:
        if (
            r.get("raw_write_eligible")
            or r.get("raw_json_write_performed")
            or r.get("raw_response_body_saved")
            or r.get("html_body_saved")
        ):
            print(f"ERROR: SAFETY in {r['probe_id']}", file=sys.stderr)
            return 1
    s = manifest["safety"]
    if any(
        s.get(k) is not False
        for k in ["raw_json_write_performed", "html_body_saved", "db_write_performed"]
    ):
        print("ERROR: SAFETY", file=sys.stderr)
        return 1
    if not ok:
        print("WARNING: review blocked", file=sys.stderr)
        return 1
    print(
        f"SUCCESS: mode={mode}, selected={len(samples)}, attempted={summary['network_requests_attempted']}, observed={summary['html_route_observed_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
