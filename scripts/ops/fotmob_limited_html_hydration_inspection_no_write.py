#!/usr/bin/env python3
"""Limited HTML hydration inspection — bounded body read, scan markers only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE

Reads at most MAX_BODY_BYTES per response, scans for structural markers
(__NEXT_DATA__, pageProps, matchId, etc.), records metadata only.
Never saves full HTML, raw JSON, or any body content.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import error, request

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"
SCHEMA = "fotmob_limited_html_hydration_inspection_no_write_v1"
DRY_RUN_NEXT = PHASE
MARKER_OK_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE"
MARKER_FAIL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-MARKER-REVIEW-FOLLOWUP-NO-WRITE"
TIMEOUT = 10
MAX_BODY = 524288
SCAN_MARKERS = [
    "__NEXT_DATA__",
    "pageProps",
    "matchId",
    "header",
    "general",
    "content",
    "script",
    "hydration",
    "nextData",
]

SAMPLES: list[tuple[str, str, str]] = [
    ("4813722", "2ygkcb", "Liverpool vs Manchester United"),
    ("4813492", "2ynv4k", "Everton vs Manchester United"),
]
ROUTES: list[dict[str, Any]] = [
    {"template": "https://www.fotmob.com/match/{match_id}", "name": "match_page"},
    {"template": "https://www.fotmob.com/matches/{route_code}/{match_id}", "name": "matches_page"},
]

SAFETY = {
    "network_fetch_performed": False,
    "bounded_body_read_performed": False,
    "full_body_read_performed": False,
    "full_html_saved": False,
    "raw_response_body_saved": False,
    "html_body_saved": False,
    "raw_json_write_performed": False,
    "db_read_performed": False,
    "db_write_performed": False,
    "production_db_write_performed": False,
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


def build_plan(samples, routes, max_body):
    plan = []
    for i, s in enumerate(samples):
        for j, r in enumerate(routes[:2]):
            if isinstance(s, dict):
                mid, rc, pair = s["match_id"], s["route_code"], s["team_pair"]
            else:
                mid, rc, pair = s[0], s[1], s[2]
            url = r["template"].replace("{match_id}", str(mid)).replace("{route_code}", str(rc))
            plan.append(
                {
                    "inspection_id": f"insp-s{i + 1:02d}-r{j + 1:02d}",
                    "match_id": str(mid),
                    "route_code": str(rc),
                    "team_pair": pair,
                    "route_template": r["template"],
                    "route_name": r["name"],
                    "url_redacted": url,
                    "max_body_bytes": min(max_body, 262144),
                }
            )
    return plan


def inspect_url(url, max_bytes):
    """Bounded read: scan first max_bytes for markers only. No body persistence."""
    r = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "marker_presence": {m: False for m in SCAN_MARKERS},
        "marker_offsets": {},
        "match_id_seen": False,
        "route_code_seen": False,
        "top_level_key_names": [],
        "stop_reason": None,
        "elapsed_ms": 0,
    }
    t0 = time.monotonic()
    body = None
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "FootballPrediction/1.0 (limited-inspection; bounded-read)")
        req.add_header("Accept", "text/html,application/xhtml+xml")
        resp = request.urlopen(req, timeout=TIMEOUT)
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["status_code"] = resp.status
        r["content_type"] = resp.headers.get("Content-Type", "")
        cl = resp.headers.get("Content-Length")
        if cl:
            try:
                r["content_length"] = int(cl)
            except (ValueError, TypeError):
                pass
        if resp.status == 403:
            r["stop_reason"] = "blocked_403"
            resp.close()
            return r
        if resp.status == 429:
            r["stop_reason"] = "blocked_429"
            resp.close()
            return r
        if resp.status == 404:
            r["stop_reason"] = "invalid_404"
            resp.close()
            return r
        if resp.status == 200 and "html" in (r["content_type"] or "").lower():
            body = resp.read(max_bytes)
            r["bytes_read"] = len(body)
            if r["content_length"] and r["bytes_read"] < r["content_length"]:
                r["body_truncated"] = True
            # Scan markers in memory only
            text = body.decode("utf-8", errors="replace")
            for m in SCAN_MARKERS:
                idx = text.find(m)
                if idx >= 0:
                    r["marker_presence"][m] = True
                    r["marker_offsets"][m] = idx
            r["match_id_seen"] = text.find("4813722") >= 0 or text.find("4813492") >= 0
            r["route_code_seen"] = text.find("2ygkcb") >= 0 or text.find("2ynv4k") >= 0
            # Try safe top-level key extraction from __NEXT_DATA__ snippet
            nd_idx = text.find('"__NEXT_DATA__"')
            if nd_idx < 0:
                nd_idx = text.find("__NEXT_DATA__")
            if nd_idx >= 0:
                snippet = text[nd_idx : nd_idx + 4096]
                keys = set(re.findall(r'"([a-zA-Z][a-zA-Z0-9]*)"\s*:', snippet))
                r["top_level_key_names"] = sorted(keys)[:30]
            resp.close()
        else:
            resp.close()
            r["stop_reason"] = "not_html"
    except error.HTTPError as e:
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["status_code"] = e.code
        r["stop_reason"] = (
            f"blocked_{e.code}"
            if e.code in (403, 429)
            else (f"invalid_{e.code}" if e.code == 404 else f"http_error_{e.code}")
        )
    except Exception as e:
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["stop_reason"] = f"error_{type(e).__name__}"
    finally:
        del body  # Ensure body is not persisted
    return r


def val_state(r):
    if r.get("marker_presence", {}).get("__NEXT_DATA__") or r.get("marker_presence", {}).get(
        "pageProps"
    ):
        if r.get("top_level_key_names"):
            return "hydration_structure_observed"
        return "hydration_marker_observed"
    stop = r.get("stop_reason", "")
    if stop in ("blocked_403", "blocked_429"):
        return "hydration_route_blocked"
    if stop == "invalid_404":
        return "hydration_route_invalid"
    if stop == "not_html":
        return "hydration_not_html"
    if r.get("status_code") == 200 and r.get("bytes_read", 0) > 0:
        return "hydration_marker_missing"
    return "hydration_not_html"


def run_inspections(plan, max_req, allow_net):
    results = []
    blocked = False
    for item in plan:
        pr = {
            "inspection_id": item["inspection_id"],
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
            "bytes_read": 0,
            "body_truncated": False,
            "marker_presence": {m: False for m in SCAN_MARKERS},
            "marker_offsets": {},
            "match_id_seen": False,
            "route_code_seen": False,
            "top_level_key_names": [],
            "extraction_viability": "unknown",
            "validation_state": "hydration_inspection_planned",
            "stop_reason": "dry_run_no_network",
            "elapsed_ms": 0,
            "full_html_saved": False,
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
            live = inspect_url(item["url_redacted"], item["max_body_bytes"])
            for k in (
                "status_code",
                "content_type",
                "content_length",
                "bytes_read",
                "body_truncated",
                "marker_presence",
                "marker_offsets",
                "match_id_seen",
                "route_code_seen",
                "top_level_key_names",
                "stop_reason",
                "elapsed_ms",
            ):
                pr[k] = live.get(k, pr.get(k))
            pr["validation_state"] = val_state(live)
            if live.get("stop_reason") in ("blocked_403", "blocked_429"):
                blocked = True
        results.append(pr)

    attempted = sum(1 for p in results if p["network_performed"])
    marker_obs = sum(1 for p in results if p["validation_state"] == "hydration_marker_observed")
    struct_obs = sum(1 for p in results if p["validation_state"] == "hydration_structure_observed")
    missing = sum(1 for p in results if p["validation_state"] == "hydration_marker_missing")
    b_count = sum(1 for p in results if p["validation_state"] == "hydration_route_blocked")
    inv_count = sum(1 for p in results if p["validation_state"] == "hydration_route_invalid")
    nh_count = sum(1 for p in results if p["validation_state"] == "hydration_not_html")
    sc_sum = {}
    ct_sum = {}
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
        "hydration_marker_observed_count": marker_obs,
        "hydration_structure_observed_count": struct_obs,
        "hydration_marker_missing_count": missing,
        "blocked_count": b_count,
        "invalid_count": inv_count,
        "not_html_count": nh_count,
    }
    return results, summary


def build_manifest(run_id, mode, samples, routes, plan, results, summary, allow_net):
    marker_ok = (
        summary["hydration_marker_observed_count"] + summary["hydration_structure_observed_count"]
    )
    rec = (
        DRY_RUN_NEXT if not allow_net else (MARKER_OK_NEXT if marker_ok >= 1 else MARKER_FAIL_NEXT)
    )
    safety = dict(SAFETY)
    if allow_net and summary["network_requests_attempted"] > 0:
        safety["network_fetch_performed"] = True
        safety["bounded_body_read_performed"] = True
    # Route viability
    rs = {}
    for r_ in results:
        t = r_["route_template"]
        if t not in rs:
            rs[t] = {
                "attempted": 0,
                "marker": 0,
                "struct": 0,
                "missing": 0,
                "blocked": 0,
                "invalid": 0,
            }
        rs[t]["attempted"] += 1
        if r_["validation_state"] in ("hydration_marker_observed", "hydration_structure_observed"):
            rs[t]["marker"] += 1
        if r_["validation_state"] == "hydration_structure_observed":
            rs[t]["struct"] += 1
        if r_["validation_state"] == "hydration_marker_missing":
            rs[t]["missing"] += 1
        if r_["validation_state"] == "hydration_route_blocked":
            rs[t]["blocked"] += 1
        if r_["validation_state"] == "hydration_route_invalid":
            rs[t]["invalid"] += 1
    viable = [t for t, s in rs.items() if s["marker"] > 0]
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_extraction_plan": {
            "html_route_observed_count": 6,
            "response_body_read": False,
            "max_body_bytes": MAX_BODY,
            "recommended_next_phase": PHASE,
        },
        "inspection_selection": {
            "max_samples": len(samples),
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] if isinstance(s, dict) else s[0] for s in samples],
            "selected_route_codes": [
                s["route_code"] if isinstance(s, dict) else s[1] for s in samples
            ],
            "selected_route_templates": [r["template"] for r in routes[:2]],
            "max_body_bytes": plan[0]["max_body_bytes"] if plan else MAX_BODY,
        },
        "inspection_results": results,
        "inspection_summary": summary,
        "hydration_decision": {
            "viable_routes": viable,
            "recommended_extraction_route": viable[0] if viable else None,
            "recommended_next_action": "extraction validation" if viable else "marker review",
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "controlled_extraction_validation_required": marker_ok >= 1,
        },
        "safety": safety,
        "embedded_review": {"limited_inspection_status": "pass", "review_report_path": ""},
        "recommended_next_phase": rec,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Limited HTML hydration inspection")
    p.add_argument("--extraction-plan-manifest", required=True)
    p.add_argument("--route-probe-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--decision-report", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-samples", type=int, default=2)
    p.add_argument("--max-route-templates", type=int, default=2)
    p.add_argument("--max-body-bytes", type=int, default=MAX_BODY)
    p.add_argument("--max-network-requests", type=int, default=4)
    p.add_argument("--allow-network-probe", action="store_true", default=False)
    args = p.parse_args()

    if args.max_samples > 2:
        print("ERROR: max-samples > 2", file=sys.stderr)
        return 1
    if args.max_route_templates > 2:
        print("ERROR: max-route-templates > 2", file=sys.stderr)
        return 1
    if args.max_network_requests > 4:
        print("ERROR: max-network-requests > 4", file=sys.stderr)
        return 1
    if args.max_body_bytes > MAX_BODY:
        print("ERROR: max-body-bytes > 524288", file=sys.stderr)
        return 1

    samples = [{"mid": s[0], "rc": s[1], "pair": s[2]} for s in SAMPLES[: args.max_samples]]
    routes = ROUTES[: args.max_route_templates]
    plan = build_plan(
        [{"match_id": s["mid"], "route_code": s["rc"], "team_pair": s["pair"]} for s in samples],
        routes,
        args.max_body_bytes,
    )
    mode = (
        "controlled_limited_body_inspection_no_write"
        if args.allow_network_probe
        else "dry_run_inspection_plan_only"
    )
    sample_dicts = [
        {"match_id": s["mid"], "route_code": s["rc"], "team_pair": s["pair"]} for s in samples
    ]
    results, summary = run_inspections(plan, args.max_network_requests, args.allow_network_probe)
    manifest = build_manifest(
        args.run_id, mode, sample_dicts, routes, plan, results, summary, args.allow_network_probe
    )

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mp = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    from fotmob_limited_html_hydration_inspection_no_write_report import (  # noqa: E402
        write_decision_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, mode, manifest, sample_dicts, routes, summary)
    write_decision_report(Path(args.decision_report), results, routes, summary)
    ok = write_review_report(Path(args.review_report), args.run_id, manifest, summary)

    s = manifest["safety"]
    for k in [
        "full_html_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        if s.get(k) is not False:
            print(f"ERROR: SAFETY {k}", file=sys.stderr)
            return 1
    if manifest["raw_write_readiness"]["json_validated_count"] != 0:
        print("ERROR: json_validated != 0", file=sys.stderr)
        return 1
    if not ok:
        print("WARNING: review blocked", file=sys.stderr)
        return 1
    print(
        f"SUCCESS: mode={mode}, attempted={summary['network_requests_attempted']}, marker_obs={summary['hydration_marker_observed_count']}, struct_obs={summary['hydration_structure_observed_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
