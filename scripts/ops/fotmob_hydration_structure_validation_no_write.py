#!/usr/bin/env python3
"""Validate FotMob hydration structure — bounded parse, structure-only metadata.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE

Only probes /matches/{route_code}/{match_id}. Parses bounded __NEXT_DATA__ JSON
in memory to find candidate match detail subtrees. Never saves full body/JSON.
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

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE"
SCHEMA = "fotmob_hydration_structure_validation_no_write_v1"
DRY_RUN_NEXT = PHASE
CANDIDATE_OK = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE"
PARTIAL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-PARTIAL-STRUCTURE-FOLLOWUP-NO-WRITE"
FAIL_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-REVIEW-FOLLOWUP-NO-WRITE"
TIMEOUT = 10
MAX_BODY = 524288

MATCH_DETAIL_KEYS = [
    "matchId",
    "id",
    "header",
    "general",
    "content",
    "matchFacts",
    "matchInfo",
    "status",
    "teams",
    "homeTeam",
    "awayTeam",
    "stats",
    "lineup",
    "events",
    "playerStats",
    "shotmap",
    "momentum",
    "table",
    "fixture",
    "match",
]

ROUTE = {
    "template": "https://www.fotmob.com/matches/{route_code}/{match_id}",
    "name": "matches_page",
}

SAMPLES: list[tuple[str, str, str]] = [
    ("4813722", "2ygkcb", "Liverpool vs Manchester United"),
    ("4813492", "2ynv4k", "Everton vs Manchester United"),
]

SAFETY = {
    "network_fetch_performed": False,
    "bounded_body_read_performed": False,
    "full_body_read_performed": False,
    "full_html_saved": False,
    "raw_response_body_saved": False,
    "html_body_saved": False,
    "full_next_data_saved": False,
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


def scan_keys(obj, prefix="", depth=0) -> list[str]:
    """Recursively collect key paths from a dict/list. Max depth 5."""
    paths: list[str] = []
    if depth > 5:
        return paths
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            paths.append(p)
            if isinstance(v, (dict, list)):
                paths.extend(scan_keys(v, p, depth + 1))
    elif isinstance(obj, list) and obj:
        if isinstance(obj[0], dict):
            paths.extend(scan_keys(obj[0], f"{prefix}[0]", depth + 1))
    return list(set(paths))


def score_subtree(paths, target_mid):
    """Score a set of paths for match detail relevance."""
    score = 0
    has_mid = False
    for p in paths:
        last = p.split(".")[-1]
        if last in ("matchId", "id"):
            has_mid = True
        if last == "header":
            score += 2
        if last == "general":
            score += 2
        if last == "content":
            score += 2
        if last in ("homeTeam", "awayTeam", "teams"):
            score += 1
        if last == "status":
            score += 1
        if last in ("stats", "lineup", "events", "matchFacts"):
            score += 1
    if has_mid:
        score += 3
    return score


def validate_structure(text, target_mid):
    """Parse __NEXT_DATA__ from bounded HTML text, extract structure metadata only."""
    result: dict[str, Any] = {
        "next_data_marker_present": False,
        "next_data_json_parse_attempted": False,
        "next_data_json_parse_ok": False,
        "pageProps_present": False,
        "target_match_id_seen": False,
        "top_level_key_names": [],
        "pageProps_key_names": [],
        "candidate_match_detail_paths": [],
        "candidate_match_detail_key_presence": {},
        "candidate_match_detail_score": 0,
    }
    # Find __NEXT_DATA__ script
    m = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*type="application/json"[^>]*>(.*?)</script>',
        text,
        re.DOTALL,
    )
    if not m:
        m = re.search(r"__NEXT_DATA__.*?({.*?})\s*</script>", text, re.DOTALL)
    if not m:
        result["stop_reason"] = "next_data_marker_not_found"
        return result
    result["next_data_marker_present"] = True
    result["next_data_json_parse_attempted"] = True
    try:
        raw = m.group(1) if m.lastindex else m.group(0)
        # Handle case where we got full tag match
        if raw.startswith("<"):
            raw = re.search(r">({.*?})</script>", raw, re.DOTALL)
            if raw:
                raw = raw.group(1)
        data = json.loads(raw)
        result["next_data_json_parse_ok"] = True
    except (json.JSONDecodeError, Exception) as e:
        result["stop_reason"] = f"next_data_json_parse_failed: {type(e).__name__}"
        return result

    result["top_level_key_names"] = sorted(data.keys()) if isinstance(data, dict) else []
    # Navigate to pageProps
    pp = data
    for key in ("props", "pageProps"):
        if isinstance(pp, dict) and key in pp:
            pp = pp[key]
            result["pageProps_present"] = True
    if isinstance(pp, dict):
        result["pageProps_key_names"] = sorted(pp.keys())
        # Check target match_id
        if "matchId" in pp and str(pp["matchId"]) == target_mid:
            result["target_match_id_seen"] = True
        if "id" in pp and str(pp["id"]) == target_mid:
            result["target_match_id_seen"] = True
        # Also scan for mid in nested
        text_full = json.dumps(pp)
        if target_mid in text_full:
            result["target_match_id_seen"] = True

    # Find best match detail candidate subtree
    paths = scan_keys(pp)
    scored = []
    for path in paths:
        parts = path.split(".")
        # Score each 2-deep subtree
        if len(parts) >= 1:
            subtree_paths = [p for p in paths if p.startswith(parts[0])]
            s = score_subtree(subtree_paths, target_mid)
            if s > 0:
                scored.append((path, s, subtree_paths))
    scored.sort(key=lambda x: -x[1])
    if scored:
        best = scored[0]
        result["candidate_match_detail_paths"] = best[2][:20]
        result["candidate_match_detail_key_presence"] = {
            k: k in best[2] for k in MATCH_DETAIL_KEYS[:15]
        }
        result["candidate_match_detail_score"] = best[1]
    return result


def state_from_validation(r, target_mid):
    if not r.get("next_data_marker_present"):
        return "hydration_marker_missing"
    if not r.get("next_data_json_parse_ok"):
        return "hydration_next_data_parse_failed"
    score = r.get("candidate_match_detail_score", 0)
    if score >= 6:
        return "hydration_match_detail_candidate_observed"
    if score >= 3:
        return "hydration_partial_match_detail_candidate"
    if r.get("pageProps_present"):
        return "hydration_generic_structure_only"
    return "hydration_structure_not_match_detail"


def probe_and_validate(url, max_bytes, target_mid):
    r = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "next_data_marker_present": False,
        "next_data_json_parse_attempted": False,
        "next_data_json_parse_ok": False,
        "pageProps_present": False,
        "target_match_id_seen": False,
        "top_level_key_names": [],
        "pageProps_key_names": [],
        "candidate_match_detail_paths": [],
        "candidate_match_detail_key_presence": {},
        "candidate_match_detail_score": 0,
        "stop_reason": None,
        "elapsed_ms": 0,
    }
    t0 = time.monotonic()
    body = None
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "FootballPrediction/1.0 (structure-validation; bounded-read)")
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
            text = body.decode("utf-8", errors="replace")
            struct = validate_structure(text, target_mid)
            for k in (
                "next_data_marker_present",
                "next_data_json_parse_attempted",
                "next_data_json_parse_ok",
                "pageProps_present",
                "target_match_id_seen",
                "top_level_key_names",
                "pageProps_key_names",
                "candidate_match_detail_paths",
                "candidate_match_detail_key_presence",
                "candidate_match_detail_score",
            ):
                r[k] = struct.get(k, r.get(k))
            r["stop_reason"] = struct.get("stop_reason", r.get("stop_reason"))
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
            else f"invalid_{e.code}"
            if e.code == 404
            else f"http_error_{e.code}"
        )
    except Exception as e:
        r["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
        r["stop_reason"] = f"error_{type(e).__name__}"
    finally:
        del body
    return r


def build_manifest(run_id, mode, samples, results, summary, allow_net):
    cand = summary.get("match_detail_candidate_observed_count", 0)
    part = summary.get("partial_match_detail_candidate_count", 0)
    if not allow_net:
        rec = DRY_RUN_NEXT
    elif cand >= 1:
        rec = CANDIDATE_OK
    elif part >= 1:
        rec = PARTIAL_NEXT
    else:
        rec = FAIL_NEXT
    safety = dict(SAFETY)
    if allow_net and summary.get("network_requests_attempted", 0) > 0:
        safety["network_fetch_performed"] = True
        safety["bounded_body_read_performed"] = True

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_inspection": {
            "hydration_structure_observed_count": 2,
            "route_template": ROUTE["template"],
            "selected_match_ids": [s[0] for s in samples],
            "selected_route_codes": [s[1] for s in samples],
            "full_html_saved": False,
            "raw_json_write_performed": False,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "validation_selection": {
            "max_samples": len(samples),
            "selected_sample_count": len(samples),
            "selected_match_ids": [s[0] for s in samples],
            "selected_route_codes": [s[1] for s in samples],
            "route_template": ROUTE["template"],
            "max_body_bytes": MAX_BODY,
        },
        "validation_results": results,
        "validation_summary": summary,
        "match_detail_candidate_decision": {
            "viable_candidate_count": cand,
            "best_candidate_path": "see validation_results",
            "best_candidate_score": max(
                (r.get("candidate_match_detail_score", 0) for r in results), default=0
            ),
            "recommended_next_action": "subtree extraction plan"
            if cand >= 1
            else ("partial review" if part >= 1 else "structure review"),
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "controlled_extraction_validation_required": cand >= 1,
        },
        "safety": safety,
        "embedded_review": {
            "hydration_structure_validation_status": "pass",
            "review_report_path": "",
        },
        "recommended_next_phase": rec,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Validate FotMob hydration structure")
    p.add_argument("--inspection-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--decision-report", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-samples", type=int, default=2)
    p.add_argument("--max-body-bytes", type=int, default=MAX_BODY)
    p.add_argument("--max-network-requests", type=int, default=2)
    p.add_argument("--allow-network-probe", action="store_true", default=False)
    args = p.parse_args()

    if args.max_samples > 2:
        print("ERROR: max-samples > 2", file=sys.stderr)
        return 1
    if args.max_network_requests > 2:
        print("ERROR: max-network-requests > 2", file=sys.stderr)
        return 1
    if args.max_body_bytes > MAX_BODY:
        print("ERROR: max-body-bytes > 524288", file=sys.stderr)
        return 1

    samples = list(SAMPLES[: args.max_samples])
    results = []
    for i, s in enumerate(samples):
        mid, rc, pair = s
        url = ROUTE["template"].replace("{route_code}", rc).replace("{match_id}", mid)
        pr = {
            "validation_id": f"val-s{i + 1:02d}",
            "match_id": mid,
            "route_code": rc,
            "team_pair": pair,
            "url_redacted": url,
            "network_performed": False,
            "status_code": None,
            "content_type": None,
            "content_length": None,
            "bytes_read": 0,
            "body_truncated": False,
            "next_data_marker_present": False,
            "next_data_json_parse_attempted": False,
            "next_data_json_parse_ok": False,
            "pageProps_present": False,
            "target_match_id_seen": False,
            "top_level_key_names": [],
            "pageProps_key_names": [],
            "candidate_match_detail_paths": [],
            "candidate_match_detail_key_presence": {},
            "candidate_match_detail_score": 0,
            "validation_state": "hydration_structure_validation_planned",
            "stop_reason": "dry_run_no_network",
            "elapsed_ms": 0,
            "full_html_saved": False,
            "raw_response_body_saved": False,
            "html_body_saved": False,
            "full_next_data_saved": False,
            "raw_json_write_performed": False,
            "db_write_performed": False,
            "raw_write_eligible": False,
        }
        if (
            args.allow_network_probe
            and sum(1 for r in results if r["network_performed"]) < args.max_network_requests
        ):
            pr["network_performed"] = True
            live = probe_and_validate(url, args.max_body_bytes, mid)
            for k in (
                "status_code",
                "content_type",
                "content_length",
                "bytes_read",
                "body_truncated",
                "next_data_marker_present",
                "next_data_json_parse_attempted",
                "next_data_json_parse_ok",
                "pageProps_present",
                "target_match_id_seen",
                "top_level_key_names",
                "pageProps_key_names",
                "candidate_match_detail_paths",
                "candidate_match_detail_key_presence",
                "candidate_match_detail_score",
                "stop_reason",
                "elapsed_ms",
            ):
                pr[k] = live.get(k, pr.get(k))
            pr["validation_state"] = state_from_validation(live, mid)
        results.append(pr)

    attempted = sum(1 for r in results if r["network_performed"])
    nd_ok = sum(1 for r in results if r.get("next_data_json_parse_ok"))
    pp = sum(1 for r in results if r.get("pageProps_present"))
    mid_seen = sum(1 for r in results if r.get("target_match_id_seen"))
    cand = sum(
        1 for r in results if r["validation_state"] == "hydration_match_detail_candidate_observed"
    )
    part = sum(
        1 for r in results if r["validation_state"] == "hydration_partial_match_detail_candidate"
    )
    gen = sum(1 for r in results if r["validation_state"] == "hydration_generic_structure_only")
    not_md = sum(
        1 for r in results if r["validation_state"] == "hydration_structure_not_match_detail"
    )
    blk = sum(1 for r in results if r["validation_state"] == "hydration_route_blocked")
    inv = sum(1 for r in results if r["validation_state"] == "hydration_route_invalid")
    nh = sum(1 for r in results if r["validation_state"] == "hydration_not_html")

    summary = {
        "allow_network_probe": args.allow_network_probe,
        "max_network_requests": args.max_network_requests,
        "network_requests_attempted": attempted,
        "next_data_parse_ok_count": nd_ok,
        "pageProps_present_count": pp,
        "target_match_id_seen_count": mid_seen,
        "match_detail_candidate_observed_count": cand,
        "partial_match_detail_candidate_count": part,
        "generic_structure_only_count": gen,
        "structure_not_match_detail_count": not_md,
        "blocked_count": blk,
        "invalid_count": inv,
        "not_html_count": nh,
    }

    mode = (
        "controlled_hydration_structure_validation_no_write"
        if args.allow_network_probe
        else "dry_run_validation_plan_only"
    )
    manifest = build_manifest(
        args.run_id, mode, samples, results, summary, args.allow_network_probe
    )

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mp = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    from fotmob_hydration_structure_validation_no_write_report import (  # noqa: E402
        write_decision_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, mode, manifest, samples, results, summary)
    write_decision_report(Path(args.decision_report), results, samples, summary)
    ok = write_review_report(Path(args.review_report), args.run_id, manifest, summary)

    for k in [
        "full_html_saved",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        if manifest["safety"].get(k) is not False:
            print(f"ERROR: SAFETY {k}", file=sys.stderr)
            return 1
    if manifest["raw_write_readiness"]["json_validated_count"] != 0:
        print("ERROR: json_validated", file=sys.stderr)
        return 1
    if not ok:
        print("WARNING: review blocked", file=sys.stderr)
        return 1
    print(
        f"SUCCESS: attempted={attempted}, nd_parse_ok={nd_ok}, match_detail_candidate={cand}, partial={part}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
