#!/usr/bin/env python3
"""Checker for FotMob safe parser schema reuse plan no-write outputs.

lifecycle: permanent
phase: SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/_manifests/fotmob_safe_parser_schema_reuse_plan_no_write_manifest.json"
REPORT = ROOT / "docs/_reports/FOTMOB_SAFE_PARSER_SCHEMA_REUSE_PLAN_NO_WRITE.md"
REVIEW = ROOT / "docs/_reports/FOTMOB_SAFE_PARSER_SCHEMA_REUSE_PLAN_NO_WRITE_REVIEW.md"
NEXT_PLAN = ROOT / "docs/_reports/FOTMOB_PAYLOAD_SHAPE_RECONSTRUCTION_NEXT_PLAN.md"

PHASE = "SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE"
ALLOWED_NEXT = [
    "HISTORICAL-FOTMOB-PAYLOAD-SHAPE-RECONSTRUCTION-READONLY",
    "FOTMOB-CANONICAL-PAYLOAD-SCHEMA-ADAPTER-PLAN-NO-WRITE",
    "ALTERNATIVE-SOURCE-TO-FOTMOB-SCHEMA-MAPPING-PLAN-NO-WRITE",
    "FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE",
]
FORBIDDEN_REC = [
    "DIRECT-RAW-WRITE",
    "RAW-JSON-WRITE",
    "RAW-WRITE-EXECUTION",
    "BROWSER-AUTOMATION",
    "COOKIE-HARVEST",
    "CAPTCHA-BYPASS",
]

HIGH_RISK_PATHS = [
    "SessionManager",
    "AutoAuthManager",
    "SessionWarmer",
    "StealthNavigator",
    "StealthFingerprint",
    "enhanced_stealth_config",
    "FotMobApiClient",
    "BrowserFactory",
    "ContextPoolManager",
    "NetworkInterceptor",
    "archive_vault_2026",
    "legacy_v446",
    "FotMobExtractor",
]

SAFETY_FALSE = [
    "network_fetch_performed",
    "db_read_performed",
    "db_write_performed",
    "production_db_write_performed",
    "raw_json_write_performed",
    "feature_parse_performed",
    "scheduler_enabled",
    "browser_automation_performed",
    "browser_automation_allowed",
    "cookie_harvesting_performed",
    "cookie_harvesting_allowed",
    "captcha_bypass_performed",
    "captcha_bypass_allowed",
    "proxy_rotation_performed",
    "proxy_rotation_allowed",
    "secrets_printed",
]


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    check(MANIFEST.exists(), "manifest exists", errors)
    check(REPORT.exists(), "report exists", errors)
    check(REVIEW.exists(), "review report exists", errors)
    check(NEXT_PLAN.exists(), "next plan exists", errors)
    if not MANIFEST.exists():
        print("FAIL: manifest missing")
        return 1

    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    safe = m.get("safe_reuse_assets", [])
    risky = m.get("read_only_reference_assets", [])
    safety = m.get("safety", {})
    gate = m.get("raw_write_gate", {})

    check(m.get("phase") == PHASE, "phase correct", errors)
    check(m.get("mode") == "offline_safe_parser_schema_reuse_plan", "mode correct", errors)
    check(len(safe) > 0, "safe_reuse_assets count > 0", errors)
    check(len(risky) > 0, "read_only_reference_assets count > 0", errors)

    for asset in safe:
        path = asset.get("path", "")
        for risk_path in HIGH_RISK_PATHS:
            check(
                risk_path.lower() not in path.lower(),
                f"high-risk {asset['asset_id']} not in safe_reuse",
                errors,
            )

    check(gate.get("raw_write_allowed") is False, "raw_write_allowed=false", errors)
    check(gate.get("db_write_allowed") is False, "db_write_allowed=false", errors)
    check(gate.get("json_validated_count") == 0, "json_validated_count=0", errors)
    check(gate.get("raw_write_eligible_count") == 0, "raw_write_eligible_count=0", errors)

    for flag in SAFETY_FALSE:
        check(safety.get(flag) is False, f"{flag}=false", errors)

    rec = m.get("recommended_next_phase", "")
    check(rec in ALLOWED_NEXT, f"next phase in allowed list: {rec}", errors)
    check(not any(t in rec for t in FORBIDDEN_REC), "no forbidden recommendation", errors)

    if errors:
        print(f"FAIL: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: safe parser schema reuse plan no-write checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
