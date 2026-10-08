"""Deterministic canonical-diff chunk planning and fail-closed aggregation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    canonical_json,
    sha256_bytes,
    validate_result,
)

CHUNKING_ALGORITHM_VERSION = "canonical-diff-files/v3"
MAX_CHUNK_DIFF_BYTES = 48_000
# Soft packing target for complete small-file diffs, not a larger call cap.
COMPOSITE_FILE_TARGET_BYTES = 24_000
MAX_CHUNK_PROMPT_BYTES = 56_000
MAX_TOTAL_PROMPT_BYTES = 3 * 1024 * 1024
MAX_REVIEW_PROVIDER_SECONDS = 1800
UTF8_CONTINUATION_MARKER = 0x80
EXPECTED_DIFF_PATH_PARTS = 2
# Bound the number of provider calls for one logical review before any call is
# made.  This keeps the bootstrap review bounded even for unusually large diffs.
MAX_CHUNK_COUNT = 64


class ChunkReviewError(ValueError):
    """A chunk manifest or its evidence cannot establish a review verdict."""


@dataclass(frozen=True)
class Chunk:
    """One contiguous byte range of the canonical diff."""

    index: int
    start: int
    end: int
    source_sha256: str
    changed_paths: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return the manifest representation of this chunk."""

        return {
            **asdict(self),
            "changed_paths": list(self.changed_paths),
            "byte_length": self.end - self.start,
        }


@dataclass(frozen=True)
class Manifest:
    """Immutable metadata proving complete chunk coverage of one diff."""

    base_sha: str
    head_sha: str
    mission_id: str
    mission_scope_sha256: str
    full_diff_sha256: str
    full_diff_bytes: int
    chunks: tuple[Chunk, ...]

    def payload(self) -> dict[str, Any]:
        """Return the canonical hash-bound manifest payload."""

        return {
            "manifest_version": "deepseek-chunk-manifest/v3",
            "chunking_algorithm": CHUNKING_ALGORITHM_VERSION,
            "max_chunk_diff_bytes": MAX_CHUNK_DIFF_BYTES,
            "composite_file_target_bytes": COMPOSITE_FILE_TARGET_BYTES,
            "max_chunk_prompt_bytes": MAX_CHUNK_PROMPT_BYTES,
            "max_chunk_count": MAX_CHUNK_COUNT,
            "max_total_prompt_bytes": MAX_TOTAL_PROMPT_BYTES,
            "max_review_provider_seconds": MAX_REVIEW_PROVIDER_SECONDS,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "mission_id": self.mission_id,
            "mission_scope_sha256": self.mission_scope_sha256,
            "full_diff_sha256": self.full_diff_sha256,
            "full_diff_bytes": self.full_diff_bytes,
            "chunk_count": len(self.chunks),
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }

    @property
    def sha256(self) -> str:
        """Return the hash of the canonical manifest payload."""

        return sha256_bytes(canonical_json(self.payload()))


def _paths(chunk: bytes) -> tuple[str, ...]:
    paths: list[str] = []
    for line in chunk.decode("utf-8", "strict").splitlines():
        if line.startswith("diff --git a/"):
            parts = line.split(" b/", 1)
            if len(parts) == EXPECTED_DIFF_PATH_PARTS:
                paths.append(parts[1])
    return tuple(dict.fromkeys(paths))


def _cut(diff: bytes, start: int) -> int:
    """Prefer newline boundaries; a giant line is split by its byte identity."""

    target = min(len(diff), start + MAX_CHUNK_DIFF_BYTES)
    # Avoid cutting ordinary code files in half, which creates speculative
    # missing-context reasoning. Large single artifacts retain the hard byte cap.
    soft_target = min(target, start + COMPOSITE_FILE_TARGET_BYTES)
    boundary = diff.rfind(b"\ndiff --git ", start, soft_target)
    if boundary < start:
        boundary = diff.find(b"\ndiff --git ", soft_target, target)
    if boundary >= start:
        return boundary + 1
    if target == len(diff):
        return target
    newline = diff.rfind(b"\n", start + 1, target)
    if newline > start:
        return newline + 1
    # A giant Unicode line must retain complete code points in each prompt.
    while target > start and diff[target] & 0xC0 == UTF8_CONTINUATION_MARKER:
        target -= 1
    return target


def plan(
    diff: bytes, *, base_sha: str, head_sha: str, mission_id: str, mission_scope_sha256: str
) -> Manifest:
    """Partition immutable canonical diff bytes without gaps or overlap."""

    if not diff:
        raise ChunkReviewError("empty canonical diff cannot be reviewed")
    # Never replace undecodable source bytes in a supposedly complete review.
    diff.decode("utf-8", errors="strict")
    chunks: list[Chunk] = []
    start = 0
    current_path: tuple[str, ...] = ()
    while start < len(diff):
        end = _cut(diff, start)
        source = diff[start:end]
        paths = _paths(source)
        carried = () if source.startswith(b"diff --git a/") else current_path
        owners = tuple(dict.fromkeys(carried + paths))
        chunks.append(Chunk(len(chunks), start, end, sha256_bytes(source), owners))
        if paths:
            current_path = paths[-1:]
        start = end
    manifest = Manifest(
        base_sha,
        head_sha,
        mission_id,
        mission_scope_sha256,
        sha256_bytes(diff),
        len(diff),
        tuple(chunks),
    )
    validate_manifest(manifest, diff)
    return manifest


def validate_manifest(manifest: Manifest, diff: bytes) -> None:
    """Prove chunks exactly reconstruct the canonical immutable diff."""

    if manifest.full_diff_bytes != len(diff) or manifest.full_diff_sha256 != sha256_bytes(diff):
        raise ChunkReviewError("full diff binding mismatch")
    if not manifest.chunks:
        raise ChunkReviewError("chunk manifest is empty")
    if len(manifest.chunks) > MAX_CHUNK_COUNT:
        raise ChunkReviewError("chunk count exceeds bounded review limit")
    position = 0
    reconstructed = bytearray()
    for index, chunk in enumerate(manifest.chunks):
        if (
            chunk.index != index
            or chunk.start != position
            or chunk.end <= chunk.start
            or chunk.end - chunk.start > MAX_CHUNK_DIFF_BYTES
        ):
            raise ChunkReviewError("chunk ranges are not an exact ordered partition")
        source = diff[chunk.start : chunk.end]
        if sha256_bytes(source) != chunk.source_sha256:
            raise ChunkReviewError("chunk source hash mismatch")
        reconstructed.extend(source)
        position = chunk.end
    if position != len(diff) or sha256_bytes(bytes(reconstructed)) != manifest.full_diff_sha256:
        raise ChunkReviewError("chunk coverage is incomplete")


def build_chunk_prompt(*, chunk: Chunk, source: bytes, manifest: Manifest, scope_sha: str) -> str:
    """Build the canonical prompt whose final argument is sent to Claude."""

    return (
        "You are an independent read-only code reviewer. Submit the required generic JSON result using the StructuredOutput tool; do not return it as plain text. "
        "PASS only when P0/P1/P2 are absent.\n"
        f"Mission: {manifest.mission_id}\nBase: {manifest.base_sha}\nHead: {manifest.head_sha}\n"
        f"Scope SHA256: {scope_sha}\nFull diff SHA256: {manifest.full_diff_sha256}\n"
        f"Chunk manifest SHA256: {manifest.sha256}\nChunk: {chunk.index + 1}/{len(manifest.chunks)} "
        f"range={chunk.start}:{chunk.end} source_sha256={chunk.source_sha256}\n"
        f"Changed paths: {','.join(chunk.changed_paths)}\n"
        f"Canonical chunk diff:\n{source.decode('utf-8', 'strict')}"
    )


def aggregate(results: Iterable[dict[str, Any]], manifest: Manifest) -> dict[str, Any]:
    """Aggregate only one validated result per manifest chunk; never vote."""

    values = list(results)
    if len(values) != len(manifest.chunks):
        raise ChunkReviewError("missing chunk result")
    findings: list[dict[str, Any]] = []
    for index, value in enumerate(values):
        if value.get("chunk_index") != index:
            raise ChunkReviewError("chunk result order/identity mismatch")
        normalized = validate_result(value.get("result"))
        findings.extend(normalized["findings"])
    blocking = any(item["severity"] in {"P0", "P1", "P2"} for item in findings)
    return validate_result(
        {
            "protocol_version": PROTOCOL_VERSION,
            "review_result": "FAIL" if blocking else "PASS",
            "findings": findings,
        }
    )


def chunk_evidence_manifest_bytes(entries: Iterable[dict[str, Any]]) -> bytes:
    """Return the sole canonical per-chunk evidence manifest representation."""

    fields = ("index", "source_sha256", "prompt_sha256", "raw_sha256", "final_sha256", "session_id")
    return canonical_json([{field: entry[field] for field in fields} for entry in entries])
