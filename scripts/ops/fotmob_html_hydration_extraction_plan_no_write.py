#!/usr/bin/env python3
"""Plan FotMob HTML hydration extraction — offline design only, no body read.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE

Designs the safe boundaries for next-phase limited HTML body inspection.
No network. No body read. No HTML save. No raw JSON save. No DB write.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE"
SCHEMA = "fotmob_html_hydration_extraction_plan_no_write_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"

MAX_BODY_BYTES = 524288  # 512 KB
ALLOWED_MARKERS = [
    "__NEXT_DATA__",
    "pageProps",
    "matchId",
    "header",
    "general",
    "content",
    "script",
]

SAFETY = {
    "network_fetch_performed": False,
    "response_body_read": False,
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

SAMPLES: list[tuple[str, str, str]] = [
    ("4813722", "2ygkcb", "Liverpool vs Manchester United"),
    ("4813492", "2ynv4k", "Everton vs Manchester United"),
    ("4813622", "2xqo0r", "Tottenham Hotspur vs Manchester United"),
]

ROUTES: list[dict[str, Any]] = [
    {"template": "https://www.fotmob.com/match/{match_id}", "name": "match_page"},
    {"template": "https://www.fotmob.com/matches/{route_code}/{match_id}", "name": "matches_page"},
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_extraction_candidates(samples, routes) -> list[dict[str, Any]]:
    """Build extraction plan candidates for next limited inspection phase."""
    cands: list[dict[str, Any]] = []
    for i, s in enumerate(samples):
        for j, r in enumerate(routes[:2]):
            url = r["template"].replace("{match_id}", s[0]).replace("{route_code}", s[1])
            cands.append(
                {
                    "candidate_id": f"extract-cand-s{i + 1:02d}-r{j + 1:02d}",
                    "route_template": r["template"],
                    "route_name": r["name"],
                    "sample_match_id": s[0],
                    "sample_route_code": s[1],
                    "sample_pair": s[2],
                    "planned_url": url,
                    "body_read_limit_bytes": min(MAX_BODY_BYTES, 262144),
                    "allowed_markers": list(ALLOWED_MARKERS),
                    "allowed_extraction_scope": "bounded_snippet_only_first_256KB",
                    "forbidden_persistence": [
                        "full_HTML_body_save",
                        "raw_JSON_file_write",
                        "DB_write",
                        "raw_response_body_persistence",
                        "pageProps_full_extraction_save",
                    ],
                    "expected_structural_signals": [
                        "__NEXT_DATA__ script tag presence",
                        "pageProps JSON blob presence",
                        "matchId field in hydrated data",
                        "header.teams structure",
                        "general.matchTimeUTC",
                    ],
                    "success_criteria": [
                        "__NEXT_DATA__ marker found in first 256KB",
                        "pageProps key found in embedded JSON",
                        "match_id matches expected value",
                    ],
                    "stop_conditions": [
                        "HTTP 403 → stop all probes",
                        "HTTP 429 → stop all probes",
                        "captcha/cloudflare signature detected → stop",
                        "body exceeds read limit without finding markers → stop that route",
                        "non-HTML content_type → record and skip",
                    ],
                    "risk_score": 2 if r["name"] == "match_page" else 3,
                    "confidence_score": 9 if r["name"] == "match_page" else 8,
                    "recommended_priority": j + 1,
                    "next_phase_allowed": True,
                }
            )
    return cands


def build_next_plan(candidates) -> dict[str, Any]:
    """Build the limited inspection plan for next phase."""
    selected = [c for c in candidates if c["next_phase_allowed"]][:2]
    return {
        "phase": NEXT_PHASE,
        "max_samples": min(len(SAMPLES), 2),
        "max_route_templates": min(len(ROUTES), 2),
        "max_network_requests": 4,
        "max_body_bytes": MAX_BODY_BYTES,
        "allowed_markers": list(ALLOWED_MARKERS),
        "forbidden_persistence": [
            "full HTML body save",
            "raw JSON file write",
            "DB write (any table)",
            "raw response body persistence",
            "pageProps full extraction save",
            "__NEXT_DATA__ full dump save",
        ],
        "success_criteria": [
            "__NEXT_DATA__ script tag found in first 256KB",
            "pageProps marker found",
            "match_id confirmed in hydrated data",
        ],
        "stop_conditions": [
            "403 on any route → stop all",
            "429 on any route → stop all",
            "captcha/bot page detected → stop all",
            "body exceeds 512KB without marker → stop that route",
        ],
        "next_phase_after_success": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-EXTRACTION-VALIDATION-NO-WRITE",
        "next_phase_after_failure": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-REVIEW-FOLLOWUP-NO-WRITE",
        "notes": (
            "Even if markers are found, next phase is extraction validation no-write, "
            "not raw JSON write. Full body extraction requires separate planning. "
            "L2 raw harvesting remains blocked until json_validated."
        ),
    }


def build_manifest(run_id, route_manifest, seed_manifest, candidates, next_plan) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_extraction_plan",
        "inherited_route_probe": {
            "html_route_observed_count": route_manifest.get("probe_summary", {}).get(
                "html_route_observed_count", 6
            ),
            "html_route_blocked_count": route_manifest.get("probe_summary", {}).get(
                "html_route_blocked_count", 0
            ),
            "html_route_invalid_count": route_manifest.get("probe_summary", {}).get(
                "html_route_invalid_count", 0
            ),
            "response_body_read": route_manifest.get("safety", {}).get("response_body_read", False),
            "html_body_saved": route_manifest.get("safety", {}).get("html_body_saved", False),
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "selected_routes_for_next_phase": {
            "selected_sample_count": min(len(SAMPLES), 2),
            "selected_match_ids": [s[0] for s in SAMPLES[:2]],
            "selected_route_codes": [s[1] for s in SAMPLES[:2]],
            "selected_route_templates": [r["template"] for r in ROUTES[:2]],
        },
        "extraction_plan_candidates": candidates,
        "limited_inspection_next_plan": next_plan,
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "limited_body_inspection_required": True,
        },
        "safety": dict(SAFETY),
        "embedded_review": {"extraction_plan_status": "pass", "review_report_path": ""},
        "recommended_next_phase": NEXT_PHASE,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Plan FotMob HTML hydration extraction offline")
    p.add_argument("--route-probe-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--next-plan", required=True)
    p.add_argument("--run-id", required=True)
    args = p.parse_args()

    route_m = _load_json(Path(args.route_probe_manifest), "route probe manifest")
    _load_json(Path(args.seed_manifest), "seed manifest")

    candidates = build_extraction_candidates(SAMPLES, ROUTES)
    next_plan = build_next_plan(candidates)
    manifest = build_manifest(args.run_id, route_m, {}, candidates, next_plan)

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mp = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    from fotmob_html_hydration_extraction_plan_no_write_report import (  # noqa: E402
        write_next_plan_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, manifest, candidates, next_plan)
    write_next_plan_report(Path(args.next_plan), candidates, next_plan)
    ok = write_review_report(Path(args.review_report), args.run_id, manifest)

    # Safety checks
    s = manifest["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "raw_response_body_saved",
        "html_body_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        if s.get(k) is not False:
            print(f"ERROR: SAFETY {k}", file=sys.stderr)
            return 1
    rw = manifest["raw_write_readiness"]
    if rw.get("raw_write_eligible_count") != 0:
        print("ERROR: raw_write_eligible", file=sys.stderr)
        return 1
    if "RAW-JSON-DEV-WRITE" in manifest["recommended_next_phase"]:
        print("ERROR: direct raw write recommendation", file=sys.stderr)
        return 1
    if not ok:
        print("WARNING: review blocked", file=sys.stderr)
        return 1
    print(f"SUCCESS: {len(candidates)} extraction candidates, next phase {NEXT_PHASE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
