#!/usr/bin/env python3
"""Checker for match detail subtree extraction plan no-write."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MP = ROOT / "docs/_manifests/fotmob_match_detail_subtree_extraction_plan_no_write_manifest.json"
RP = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_SUBTREE_EXTRACTION_PLAN_NO_WRITE.md"
RR = ROOT / "docs/_reports/FOTMOB_MATCH_DETAIL_SUBTREE_EXTRACTION_PLAN_NO_WRITE_REVIEW.md"
NP = ROOT / "docs/_reports/FOTMOB_CONTROLLED_MATCH_DETAIL_SUBTREE_EXTRACTION_NEXT_PLAN.md"
EP = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE"
EN = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE"

errors = []


def check(c, m):
    if not c:
        errors.append(m)


def main():
    check(MP.exists(), "manifest")
    check(RP.exists(), "report")
    check(RR.exists(), "review")
    check(NP.exists(), "next plan")
    if not MP.exists():
        return 1
    m = json.loads(MP.read_text(encoding="utf-8"))
    check(m.get("phase") == EP, "phase")
    check(m.get("mode") == "offline_subtree_extraction_plan", "mode")
    ih = m.get("inherited_hydration_validation", {})
    check(ih.get("next_data_parse_ok_count") == 2, "nd_parse_ok")
    check(ih.get("pageProps_present_count") == 2, "pp_present")
    check(ih.get("match_detail_candidate_observed_count") == 2, "cand_obs")
    check(ih.get("target_match_id_seen_count") == 0, "mid_seen")
    plan = m.get("subtree_extraction_plan", {})
    check(plan.get("root_path") == "props.pageProps", "root_path")
    check(any("fallback" in p["path"] for p in plan.get("priority_paths", [])), "fallback in paths")
    check(len(plan.get("scoring_rules", [])) >= 5, "scoring rules")
    scope = m.get("selected_next_phase_scope", {})
    check(scope.get("max_network_requests") <= 2, "next requests > 2")
    check(scope.get("max_body_bytes") <= 524288, "next body > 512K")
    check(scope.get("max_subtree_scan_depth") <= 8, "next depth > 8")
    check(m["recommended_next_phase"] == EN, f"next phase mismatch: {m['recommended_next_phase']}")
    s = m["safety"]
    for k in [
        "network_fetch_performed",
        "response_body_read",
        "full_html_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]:
        check(s.get(k) is False, k)
    rw = m["raw_write_readiness"]
    check(rw.get("json_validated_count") == 0, "json_validated")
    check(rw.get("raw_write_eligible_count") == 0, "raw_write_eligible")
    for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]:
        check(w not in m["recommended_next_phase"], f"forbidden: {w}")
    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
