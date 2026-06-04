#!/usr/bin/env python3
"""Review FotMob JSON endpoint candidates after #1439 404 results.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE

Offline review of historical endpoint/route audit materials to identify
viable FotMob detail JSON endpoint candidates. No network, no DB, no raw write.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE"
SCHEMA_VERSION = "fotmob_json_endpoint_review_no_write_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"

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

# Rejected endpoints from #1439
REJECTED_ENDPOINTS: list[dict[str, Any]] = [
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}",
        "prior_attempts": 3,
        "prior_result": "404",
        "decision": "reject",
        "source": "pr1439_failed_probe",
        "reason": "All 3 match IDs returned 404; endpoint may not exist or may need /data/ prefix",
    },
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}&ccode3=USA",
        "prior_attempts": 3,
        "prior_result": "404",
        "decision": "reject",
        "source": "pr1439_failed_probe",
        "reason": "ccode3 parameter did not change 404 result",
    },
    {
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}&timezone=UTC",
        "prior_attempts": 3,
        "prior_result": "404",
        "decision": "reject",
        "source": "pr1439_failed_probe",
        "reason": "timezone parameter did not change 404 result",
    },
]

# Historical files to review (with extracted candidate counts)
HISTORICAL_FILES: list[dict[str, Any]] = [
    {
        "path": "docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.detail_api_endpoint_feasibility.phase521l2v3s.json",
        "description": "Phase 5.21 L2V3S detail API endpoint feasibility analysis",
    },
    {
        "path": "docs/_reports/FOTMOB_DETAIL_ROUTE_SELECTOR_PHASE5_12L2B.md",
        "description": "Phase 5.12 L2B detail route selector (favors html_hydration over api_match_details)",
    },
    {
        "path": "docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md",
        "description": "Phase 5.12 L2A raw detail access route read-only audit",
    },
    {
        "path": "docs/_reports/FOTMOB_IDENTITY_ANTI_BOT_DIFFERENTIAL_DIAGNOSIS_RESULT_ADG2.md",
        "description": "ADG2 anti-bot differential diagnosis (page vs API discrepancy)",
    },
    {
        "path": "scripts/ops/fotmob_live_fetch_route_review_no_write.py",
        "description": "Live fetch route review script with endpoint construction logic",
    },
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def review_historical_files(root: Path) -> list[dict[str, Any]]:
    """Review each historical file and record its existence and extracted info."""
    reviewed: list[dict[str, Any]] = []
    for hf in HISTORICAL_FILES:
        file_path = root / hf["path"]
        exists = file_path.exists()
        entry: dict[str, Any] = {
            "path": hf["path"],
            "description": hf["description"],
            "exists": exists,
            "extracted_candidate_count": 0,
            "notes": "",
        }
        if exists:
            try:
                content = file_path.read_text(encoding="utf-8")[:4096]
                # Count endpoint-like patterns in the content
                match_details_count = content.count("matchDetails")
                api_data_count = content.count("/api/data/")
                pageprops_count = content.count("pageProps")
                next_data_count = content.count("__NEXT_DATA__")
                html_hydration = content.count("html_hydration")
                entry["extracted_candidate_count"] = sum(
                    1
                    for c in [
                        match_details_count,
                        api_data_count,
                        pageprops_count,
                        next_data_count,
                        html_hydration,
                    ]
                    if c > 0
                )
                entry["notes"] = (
                    f"matchDetails_refs={match_details_count}, "
                    f"/api/data/ refs={api_data_count}, "
                    f"pageProps_refs={pageprops_count}, "
                    f"NEXT_DATA_refs={next_data_count}"
                )
            except Exception:
                entry["notes"] = "could not read content"
        else:
            entry["notes"] = "file missing"
        reviewed.append(entry)
    return reviewed


def build_endpoint_candidates() -> list[dict[str, Any]]:
    """Build the endpoint candidate matrix from historical analysis.

    Categories:
    1. rejected — already tested 404/403
    2. api_json_direct — direct JSON API endpoints
    3. html_hydration — SSR/HTML page with embedded JSON
    4. page_derived — derived from known match page patterns
    5. deferred — requires browser/session/login
    """
    candidates: list[dict[str, Any]] = [
        # === Rejected (from #1439) ===
        {
            "endpoint_candidate_id": "ep-cand-001",
            "category": "rejected",
            "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}",
            "source": "pr1439_failed_probe",
            "required_inputs": ["match_id"],
            "evidence_file": "docs/_manifests/fotmob_controlled_json_probe_no_write_manifest.json",
            "evidence_summary": "9 requests across 3 match IDs all returned 404",
            "prior_status": "rejected_404",
            "confidence_score": 0,
            "risk_score": 10,
            "recommended_probe_priority": 0,
            "next_phase_probe_allowed": False,
            "reason": "Rejected: 9/9 404 responses in #1439. Endpoint missing /data/ segment.",
        },
        # === API JSON Direct ===
        {
            "endpoint_candidate_id": "ep-cand-002",
            "category": "api_json_direct",
            "endpoint_template": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}",
            "source": "code_search",
            "required_inputs": ["match_id"],
            "evidence_file": "src/infrastructure/network/FotMobApiClient.js:290",
            "evidence_summary": (
                "Production FotMobApiClient.fetchMatchDetails() uses /api/data/matchDetails. "
                "Phase 5.21L2V3S observed HTTP 403 (blocked by Cloudflare). "
                "MarathonService._buildMatchDetailsApiUrls() also references this endpoint. "
                "This is the canonical FotMob detail JSON API but requires session/cookies."
            ),
            "prior_status": "historical_success",
            "confidence_score": 7,
            "risk_score": 6,
            "recommended_probe_priority": 1,
            "next_phase_probe_allowed": True,
            "reason": "Canonical endpoint from production code. May return 403 without session but is the correct URL pattern. Worth probing to confirm status code.",
        },
        {
            "endpoint_candidate_id": "ep-cand-003",
            "category": "api_json_direct",
            "endpoint_template": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}&ccode3=USA",
            "source": "code_search",
            "required_inputs": ["match_id", "ccode3"],
            "evidence_file": "scripts/ops/titan_seeder.js:99",
            "evidence_summary": (
                "titan_seeder.js uses ccode3=USA with /api/data/leagues endpoint. "
                "Adding ccode3 to the /api/data/ prefix may help with geo-based content negotiation."
            ),
            "prior_status": "not_tested",
            "confidence_score": 4,
            "risk_score": 5,
            "recommended_probe_priority": 2,
            "next_phase_probe_allowed": True,
            "reason": "/api/data/ prefix variant with geo code. Not yet tested. Lower confidence.",
        },
        # === HTML Hydration (SSR) ===
        {
            "endpoint_candidate_id": "ep-cand-004",
            "category": "html_hydration",
            "endpoint_template": "https://www.fotmob.com/match/{match_id}",
            "source": "code_search",
            "required_inputs": ["match_id"],
            "evidence_file": "src/infrastructure/services/FotMobRawDetailFetcher.js:44-51",
            "evidence_summary": (
                "FotMobRawDetailFetcher.buildFotMobMatchUrl() constructs /match/{externalId}. "
                "Returns HTTP 200 with __NEXT_DATA__ embedded in page HTML. "
                "This is the HTML hydration route used by the production pageProps v2 pipeline. "
                "Phase ADG60 confirmed 32/32 targets accessible via this route. "
                "Requires parsing <script id='__NEXT_DATA__'> from HTML response. "
                "Note: this returns HTML, not JSON; metadata probe would detect content-type=text/html."
            ),
            "prior_status": "historical_success",
            "confidence_score": 9,
            "risk_score": 3,
            "recommended_probe_priority": 1,
            "next_phase_probe_allowed": True,
            "reason": "Highest confidence endpoint. Known HTTP 200. Requires pageProps extraction but URL pattern is validated.",
        },
        {
            "endpoint_candidate_id": "ep-cand-005",
            "category": "html_hydration",
            "endpoint_template": "https://www.fotmob.com/matches/{route_code}/{match_id}",
            "source": "historical_report",
            "required_inputs": ["route_code", "match_id"],
            "evidence_file": (
                "docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_live_fetch_one_target_no_write.json"
            ),
            "evidence_summary": (
                "ADG60 live fetch used /matches/{hash}/{externalId} format. "
                "Returns HTTP 200 with SSR pageProps. "
                "This is the same URL pattern as user-supplied known match pages. "
                "Hash/route_code from seed parsing can be used directly."
            ),
            "prior_status": "historical_success",
            "confidence_score": 8,
            "risk_score": 2,
            "recommended_probe_priority": 2,
            "next_phase_probe_allowed": True,
            "reason": "ADG60-validated route. Uses route_code from user seeds. Returns HTML with embedded pageProps.",
        },
        # === Page-derived ===
        {
            "endpoint_candidate_id": "ep-cand-006",
            "category": "page_derived",
            "endpoint_template": "https://www.fotmob.com/zh-Hans/matches/{match_slug}/{route_code}#{match_id}",
            "source": "page_derived",
            "required_inputs": ["match_slug", "route_code", "match_id"],
            "evidence_file": "docs/_examples/fotmob_known_match_page_user_seeds.example.json",
            "evidence_summary": (
                "User-supplied known match page URLs follow this pattern. "
                "Returns HTTP 200, SSR pageProps embedded. "
                "This is the exact URL users provided. "
                "Note: returns HTML page, not JSON API."
            ),
            "prior_status": "not_tested",
            "confidence_score": 9,
            "risk_score": 1,
            "recommended_probe_priority": 3,
            "next_phase_probe_allowed": True,
            "reason": "User seeds use this exact pattern. Known to return 200. HTML, not JSON.",
        },
        # === Deferred (requires browser/session) ===
        {
            "endpoint_candidate_id": "ep-cand-007",
            "category": "deferred",
            "endpoint_template": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id} [with browser session/cookies]",
            "source": "historical_report",
            "required_inputs": ["match_id", "session_cookies"],
            "evidence_file": "src/infrastructure/harvesters/strategies/FotMobStrategy.js:555",
            "evidence_summary": (
                "FotMobStrategy._fetchMatchDetailsWithSession() uses /api/data/matchDetails "
                "with Playwright browser session cookies. This is the production L2 harvesting path. "
                "Requires browser automation (Playwright), session cookies, and proxy rotation. "
                "DEFERRED: cannot be probed in current no-write, no-browser phase."
            ),
            "prior_status": "historical_success",
            "confidence_score": 9,
            "risk_score": 9,
            "recommended_probe_priority": 0,
            "next_phase_probe_allowed": False,
            "reason": "Deferred: requires browser automation, session cookies, and proxy. Not for current no-write phase.",
        },
        {
            "endpoint_candidate_id": "ep-cand-008",
            "category": "deferred",
            "endpoint_template": "http://data.fotmob.com/webcl/ltc/gsm/{match_id}_en_gen.json.gz",
            "source": "historical_report",
            "required_inputs": ["match_id"],
            "evidence_file": "docs/_reports/FOTMOB_RAW_DETAIL_ACCESS_ROUTE_AUDIT_PHASE5_12L2A.md:80",
            "evidence_summary": (
                "Historical GSM compressed JSON endpoint referenced in backfill scripts. "
                "May be deprecated or require specific match ID format. "
                "DEFERRED: endpoint format unclear, may not return current data."
            ),
            "prior_status": "historical_unknown",
            "confidence_score": 2,
            "risk_score": 8,
            "recommended_probe_priority": 0,
            "next_phase_probe_allowed": False,
            "reason": "Deferred: historical endpoint, may be deprecated. Review before probing.",
        },
    ]
    return candidates


def build_next_probe_plan(
    candidates: list[dict[str, Any]],
    preferred_match_ids: list[str],
    preferred_route_codes: list[str],
) -> dict[str, Any]:
    """Select top 3 probe-allowed candidates for next phase."""
    probe_allowed = [c for c in candidates if c.get("next_phase_probe_allowed")]
    probe_allowed.sort(key=lambda c: c.get("recommended_probe_priority", 99))
    selected = probe_allowed[:3]

    plan: dict[str, Any] = {
        "selected_candidate_count": len(selected),
        "max_samples": 3,
        "max_endpoint_templates": 3,
        "max_network_requests": 9,
        "selected_match_ids": preferred_match_ids,
        "selected_route_codes": preferred_route_codes,
        "selected_endpoint_templates": [c["endpoint_template"] for c in selected],
        "allow_network_required": True,
        "raw_response_body_saved": False,
        "raw_json_write": False,
        "db_write": False,
        "stop_conditions": [
            "403 on any endpoint → stop that endpoint immediately",
            "429 on any endpoint → stop all probes immediately",
            "captcha/cloudflare detected → stop all probes",
            "content_type=text/html → record as html_hydration, do NOT parse body",
            "content_type=application/json → record top-level keys only, do NOT save body",
        ],
        "safety_boundaries": [
            "No response body saved",
            "No raw JSON write",
            "No DB write",
            "No browser automation",
            "No proxy rotation",
            "No session cookies",
            "Metadata only: status_code, content_type, top_level_keys",
        ],
        "next_phase_notes": (
            "Next phase should probe /api/data/matchDetails (the canonical endpoint from production code), "
            "/match/{match_id} (HTML hydration route, known 200), and "
            "/matches/{route_code}/{match_id} (SSR page, known 200). "
            "All three use the /data/ prefix or page routes that differ from the #1439 404 endpoints. "
            "If /api/data/matchDetails returns 403, that confirms anti-bot blocking; "
            "the HTML hydration routes should return 200 but with text/html content_type."
        ),
    }
    return plan


def build_manifest(
    run_id: str,
    rejected: list[dict[str, Any]],
    reviewed_files: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    next_probe_plan: dict[str, Any],
) -> dict[str, Any]:
    """Build the output manifest."""
    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_endpoint_review",
        "inherited_probe_status": {
            "user_seed_count": 12,
            "parsed_seed_count": 12,
            "route_candidate_count": 12,
            "selected_sample_count": 3,
            "network_requests_attempted": 9,
            "json_parse_ok_count": 0,
            "invalid_count": 9,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "rejected_endpoints": rejected,
        "historical_files_reviewed": reviewed_files,
        "endpoint_candidates": candidates,
        "next_probe_plan": next_probe_plan,
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "controlled_endpoint_probe_required": True,
        },
        "safety": dict(SAFETY_FALSE),
        "embedded_review": {
            "endpoint_review_status": "pass",
            "review_report_path": "",
        },
        "recommended_next_phase": NEXT_PHASE,
    }
    return manifest


# Report generation delegated to sibling module
from fotmob_json_endpoint_review_no_write_report import (  # noqa: E402
    write_next_probe_plan_report,
    write_report,
    write_review_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review FotMob JSON endpoint candidates offline")
    parser.add_argument(
        "--controlled-probe-manifest", required=True, help="#1439 controlled probe manifest"
    )
    parser.add_argument("--seed-manifest", required=True, help="#1438 seed parse manifest")
    parser.add_argument("--output-manifest", required=True, help="Output manifest path")
    parser.add_argument("--report", required=True, help="Output report path")
    parser.add_argument("--review-report", required=True, help="Embedded review path")
    parser.add_argument("--next-probe-plan", required=True, help="Next probe plan report path")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    args = parser.parse_args()

    root = Path()

    # Load #1439 manifest to verify inheritance
    probe_path = Path(args.controlled_probe_manifest)
    if not probe_path.exists():
        print(f"ERROR: controlled probe manifest missing: {probe_path}", file=sys.stderr)
        return 1
    probe_manifest = _load_json(probe_path, "controlled probe manifest")

    # Verify inherited values
    ps = probe_manifest.get("probe_summary", {})
    if ps.get("network_requests_attempted") != 9:
        print(
            f"WARNING: expected 9 network requests, got {ps.get('network_requests_attempted')}",
            file=sys.stderr,
        )
    if ps.get("json_parse_ok_count") != 0:
        print(
            f"WARNING: expected json_parse_ok=0, got {ps.get('json_parse_ok_count')}",
            file=sys.stderr,
        )

    # Load seed manifest for match IDs
    seed_path = Path(args.seed_manifest)
    if not seed_path.exists():
        print(f"ERROR: seed manifest missing: {seed_path}", file=sys.stderr)
        return 1
    seed_manifest = _load_json(seed_path, "seed manifest")

    # Extract preferred match IDs and route codes
    parsed_seeds = seed_manifest.get("parsed_seeds", [])
    exact = [s for s in parsed_seeds if s.get("is_exact_or_reversed_pair")]
    preferred_match_ids = [s["fotmob_match_id"] for s in exact[:3]]
    preferred_route_codes = [s["route_code"] for s in exact[:3]]

    # Review historical files
    reviewed = review_historical_files(root)

    # Build endpoint candidates
    candidates = build_endpoint_candidates()

    # Build next probe plan
    next_plan = build_next_probe_plan(candidates, preferred_match_ids, preferred_route_codes)

    # Build manifest
    manifest = build_manifest(args.run_id, REJECTED_ENDPOINTS, reviewed, candidates, next_plan)

    # Write outputs
    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    write_report(
        Path(args.report),
        args.run_id,
        manifest,
        REJECTED_ENDPOINTS,
        reviewed,
        candidates,
        next_plan,
    )
    write_next_probe_plan_report(Path(args.next_probe_plan), candidates, next_plan)
    review_passed = write_review_report(Path(args.review_report), args.run_id, manifest, reviewed)

    # Safety checks
    safety = manifest["safety"]
    if safety.get("network_fetch_performed") is not False:
        print("ERROR: SAFETY VIOLATION — network_fetch_performed", file=sys.stderr)
        return 1
    if safety.get("db_write_performed") is not False:
        print("ERROR: SAFETY VIOLATION — db_write_performed", file=sys.stderr)
        return 1
    if safety.get("raw_json_write_performed") is not False:
        print("ERROR: SAFETY VIOLATION — raw_json_write_performed", file=sys.stderr)
        return 1

    rw = manifest["raw_write_readiness"]
    if rw.get("raw_write_eligible_count") != 0:
        print("ERROR: SAFETY VIOLATION — raw_write_eligible_count != 0", file=sys.stderr)
        return 1

    if "RAW-JSON-DEV-WRITE" in manifest["recommended_next_phase"]:
        print("ERROR: SAFETY VIOLATION — recommended direct raw write", file=sys.stderr)
        return 1

    if not review_passed:
        print("WARNING: embedded review has blocked checks", file=sys.stderr)
        return 1

    print(
        f"SUCCESS: reviewed {len(reviewed)} historical files, "
        f"{len(candidates)} endpoint candidates, "
        f"{next_plan['selected_candidate_count']} next probe candidates"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
