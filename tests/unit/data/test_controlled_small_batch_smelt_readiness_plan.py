"""Static guard tests for controlled small-batch smelt readiness plan.

These tests perform text-only checks. They do NOT connect to a database,
do NOT run smelt, and do NOT write any data.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_controlled_small_batch_smelt_plan_guardrails() -> None:
    """Verify the smelt readiness plan contains all required no-write guardrails."""
    doc = ROOT / "docs/data/controlled_small_batch_smelt_readiness_plan.md"
    text = doc.read_text(encoding="utf-8")

    required = [
        "Status: plan-only / no-write",
        "This document does not authorize a write",
        "No DB write",
        "No smelt",
        "Training dry-run remains blocked",
        "explicit user authorization",
        "`raw_match_data` delta = 0",
        "`l3_features` delta = N",
        "`dataset_generator.py` is marked legacy / non-production",
    ]

    for marker in required:
        assert marker in text, f"Missing required guardrail: {marker!r}"
