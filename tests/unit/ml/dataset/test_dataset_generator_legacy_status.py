"""Static guard tests for dataset_generator.py legacy status.

These tests perform text-only checks. They do NOT import or instantiate
ClassificationDatasetGenerator, do NOT connect to a database, and do NOT
generate random data.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_dataset_generator_declares_legacy_non_production_status() -> None:
    """Verify dataset_generator.py source contains all required legacy markers."""
    source = ROOT / "src/ml/dataset/dataset_generator.py"
    text = source.read_text(encoding="utf-8")

    assert "LIFECYCLE: LEGACY / NON-PRODUCTION" in text
    assert "not the production training dataset builder" in text
    assert "mock/random historical data" in text
    assert "l3_prematch_contract" in text


def test_dataset_generation_legacy_status_doc_exists() -> None:
    """Verify the legacy status document exists with required content."""
    doc = ROOT / "docs/data/dataset_generation_legacy_status.md"
    text = doc.read_text(encoding="utf-8")

    assert "Status: legacy / non-production" in text
    assert "Do not use `dataset_generator.py`" in text
    assert "Production training path: protected by #1721" in text
    assert "Production prediction path: protected by #1722" in text
