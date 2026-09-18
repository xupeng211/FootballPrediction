from __future__ import annotations

import pytest

from scripts.devops.deepseek_review_chunks import (
    ChunkReviewError,
    aggregate,
    plan,
    validate_manifest,
)


def _manifest():
    return plan(
        (b"diff --git a/a b/a\n+line\n" * 3000),
        base_sha="a" * 40,
        head_sha="b" * 40,
        mission_id="MISSION",
        mission_scope_sha256="c" * 64,
    )


def _result(index: int, severity: str | None = None):
    findings = (
        []
        if severity is None
        else [{"severity": severity, "title": "finding", "evidence": "evidence"}]
    )
    return {
        "chunk_index": index,
        "result": {
            "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
            "review_result": "FAIL" if severity in {"P0", "P1", "P2"} else "PASS",
            "findings": findings,
        },
    }


def test_manifest_is_deterministic_and_reconstructable():
    manifest = _manifest()
    assert manifest.sha256 == _manifest().sha256
    validate_manifest(manifest, b"diff --git a/a b/a\n+line\n" * 3000)
    assert len(manifest.chunks) > 1


def test_manifest_rejects_gap_overlap_or_tampered_source():
    manifest = _manifest()
    with pytest.raises(ChunkReviewError):
        validate_manifest(manifest, b"x" + b"diff --git a/a b/a\n+line\n" * 3000)


def test_aggregate_is_fail_closed_and_surfaces_p3():
    manifest = _manifest()
    passed = aggregate(
        [_result(index, "P3" if index == 0 else None) for index in range(len(manifest.chunks))],
        manifest,
    )
    assert passed["review_result"] == "PASS" and passed["finding_counts_by_severity"]["P3"] == 1
    failed = aggregate(
        [_result(index, "P2" if index == 1 else None) for index in range(len(manifest.chunks))],
        manifest,
    )
    assert failed["review_result"] == "FAIL"
    with pytest.raises(ChunkReviewError):
        aggregate([_result(0)], manifest)
