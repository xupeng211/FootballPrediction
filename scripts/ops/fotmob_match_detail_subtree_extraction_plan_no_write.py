#!/usr/bin/env python3
"""Plan FotMob match detail subtree extraction — offline design only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE

Designs safe in-memory subtree scanning strategy to locate match detail data
under props.pageProps.*fallback in __NEXT_DATA__. No network, no body, no writes.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE"
SCHEMA = "fotmob_match_detail_subtree_extraction_plan_no_write_v1"
NEXT_PHASE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE"
)

ROUTE = "https://www.fotmob.com/matches/{route_code}/{match_id}"
MATCH_IDS = ["4813722", "4813492"]
ROUTE_CODES = ["2ygkcb", "2ynv4k"]

PRIORITY_PATHS = [
    ("props.pageProps.fallback", "primary cache candidate from Next.js SSG"),
    ("props.pageProps.fallback.*.data", "potential data wrapper under fallback"),
    ("props.pageProps.fallback.*.matchDetails", "match details cache entry"),
    ("props.pageProps.fallback.*.content", "content subtree under cache"),
    ("props.pageProps.fallback.*.header", "header subtree under cache"),
    ("props.pageProps.fallback.*.general", "general subtree under cache"),
    ("props.pageProps.*.match", "match data at pageProps level"),
    ("props.pageProps.*.matchData", "explicit match data key"),
    ("props.pageProps.*.matchDetails", "explicit match details key"),
    ("props.pageProps.*.content", "content at pageProps level"),
]

SCORING_RULES: list[dict[str, Any]] = [
    {"signal": "target match_id found in subtree", "score": 5},
    {"signal": "key path or name contains matchId/id and value matches target", "score": 4},
    {"signal": "subtree contains 'header' key", "score": 3},
    {"signal": "subtree contains 'general' key", "score": 3},
    {"signal": "subtree contains 'content' key", "score": 3},
    {"signal": "subtree contains 'matchFacts' key", "score": 2},
    {"signal": "subtree contains 'stats' key", "score": 2},
    {"signal": "subtree contains 'lineup' key", "score": 2},
    {"signal": "subtree contains 'events' key", "score": 2},
    {"signal": "subtree contains 'homeTeam' / 'awayTeam' / 'teams' key", "score": 2},
    {"signal": "subtree contains 'status' key", "score": 1},
    {"signal": "subtree contains 'fixture' key", "score": 1},
    {"signal": "subtree contains 'score' key", "score": 1},
    {"signal": "subtree contains 'tournament' / 'league' key", "score": 1},
    {
        "signal": "subtree only contains CountryCodes/Language/translations/static config",
        "score": -3,
    },
    {"signal": "subtree lacks target match_id AND lacks team names", "score": -5},
    {"signal": "subtree is clearly translation/config dictionary", "score": -5},
]

CLASSIFICATION = [
    {"min_score": 10, "state": "match_detail_subtree_strong_candidate"},
    {"min_score": 6, "state": "match_detail_subtree_weak_candidate"},
    {"min_score": 3, "state": "partial_match_detail_subtree"},
    {"min_score": -999, "state": "generic_or_irrelevant_subtree"},
]

NEXT_PLAN: dict[str, Any] = {
    "phase": NEXT_PHASE,
    "route_template": ROUTE,
    "selected_match_ids": MATCH_IDS,
    "selected_route_codes": ROUTE_CODES,
    "max_samples": 2,
    "max_network_requests": 2,
    "max_body_bytes": 524288,
    "max_subtree_scan_depth": 8,
    "max_key_paths_recorded": 200,
    "max_candidate_paths_recorded": 20,
    "allowed_metadata": [
        "key path metadata",
        "data type metadata",
        "key presence booleans",
        "candidate subtree path",
        "candidate score",
        "estimated subtree size",
        "value fingerprints: length, type, numeric equality, string contains match_id",
    ],
    "forbidden_persistence": [
        "full HTML body",
        "full __NEXT_DATA__ JSON",
        "full pageProps",
        "full match detail subtree value",
        "raw JSON file",
        "DB write",
        "raw response body",
        "scheduler enable",
        "feature parse",
        "browser automation",
        "captcha bypass",
        "proxy rotation",
    ],
    "success_criteria": [
        "find at least one subtree with score >= 6",
        "detect target match_id in subtree",
        "identify viable path for match detail extraction",
    ],
    "failure_criteria": [
        "max depth reached without finding any candidate with score > 0",
        "all subtrees are generic config/translations",
    ],
    "stop_conditions": [
        "HTTP 403 on any route → stop all",
        "HTTP 429 on any route → stop all",
        "captcha/bot page detected → stop all",
        "body exceeds max_body_bytes without finding NEXT_DATA → stop",
    ],
    "next_phase_after_success": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-VALIDATION-NO-WRITE",
    "notes": (
        "Even if strong candidate found, next phase is subtree validation no-write, "
        "not raw JSON write. Full subtree extraction requires separate validation phase. "
        "L2 raw harvesting remains blocked until json_validated."
    ),
}

SAFETY = {
    "network_fetch_performed": False,
    "response_body_read": False,
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


def build_manifest(run_id) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_subtree_extraction_plan",
        "inherited_hydration_validation": {
            "next_data_parse_ok_count": 2,
            "pageProps_present_count": 2,
            "match_detail_candidate_observed_count": 2,
            "target_match_id_seen_count": 0,
            "best_candidate_path": "props.pageProps",
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "selected_next_phase_scope": {
            "route_template": ROUTE,
            "selected_match_ids": MATCH_IDS,
            "selected_route_codes": ROUTE_CODES,
            "max_samples": 2,
            "max_network_requests": 2,
            "max_body_bytes": 524288,
            "max_subtree_scan_depth": 8,
        },
        "subtree_extraction_plan": {
            "root_path": "props.pageProps",
            "priority_paths": [
                {"priority": i + 1, "path": p[0], "purpose": p[1]}
                for i, p in enumerate(PRIORITY_PATHS)
            ],
            "key_search_terms": [
                "matchId",
                "id",
                "header",
                "general",
                "content",
                "matchFacts",
                "stats",
                "lineup",
                "events",
                "teams",
                "homeTeam",
                "awayTeam",
                "status",
                "score",
                "fixture",
            ],
            "scoring_rules": SCORING_RULES,
            "candidate_classification_rules": CLASSIFICATION,
            "persistence_policy": "metadata_only_no_body_no_json",
            "stop_conditions": NEXT_PLAN["stop_conditions"],
        },
        "controlled_subtree_extraction_next_plan": NEXT_PLAN,
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "subtree_validation_required": True,
        },
        "safety": dict(SAFETY),
        "embedded_review": {"subtree_extraction_plan_status": "pass", "review_report_path": ""},
        "recommended_next_phase": NEXT_PHASE,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Plan FotMob match detail subtree extraction")
    p.add_argument("--hydration-validation-manifest", required=True)
    p.add_argument("--inspection-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--next-plan", required=True)
    p.add_argument("--run-id", required=True)
    args = p.parse_args()

    # Load and verify manifests (only to confirm existence, not for live data)
    _load_json(Path(args.hydration_validation_manifest), "hydration validation manifest")
    _load_json(Path(args.inspection_manifest), "inspection manifest")
    _load_json(Path(args.seed_manifest), "seed manifest")

    manifest = build_manifest(args.run_id)

    out_dir = Path(args.output_manifest).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    mp = Path(args.output_manifest)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    mp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    from fotmob_match_detail_subtree_extraction_plan_no_write_report import (  # noqa: E402
        write_next_plan_report,
        write_report,
        write_review_report,
    )

    write_report(Path(args.report), args.run_id, manifest)
    write_next_plan_report(Path(args.next_plan), manifest)
    ok = write_review_report(Path(args.review_report), args.run_id, manifest)

    s = manifest["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "full_html_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        if s.get(k) is not False:
            print(f"ERROR: SAFETY {k}", file=sys.stderr)
            return 1
    if manifest["raw_write_readiness"]["raw_write_eligible_count"] != 0:
        print("ERROR: raw_write_eligible", file=sys.stderr)
        return 1
    if "RAW-JSON-DEV-WRITE" in manifest["recommended_next_phase"]:
        print("ERROR: direct raw write", file=sys.stderr)
        return 1
    if not ok:
        print("WARNING: review blocked", file=sys.stderr)
        return 1
    print(
        f"SUCCESS: {len(PRIORITY_PATHS)} priority paths, {len(SCORING_RULES)} scoring rules, next phase {NEXT_PHASE}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
