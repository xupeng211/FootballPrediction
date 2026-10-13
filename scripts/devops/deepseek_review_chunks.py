"""Deterministic canonical-diff chunk planning and fail-closed aggregation."""

from __future__ import annotations

import codecs
from dataclasses import asdict, dataclass
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from scripts.devops.independent_review_protocol import (
    PROTOCOL_VERSION,
    canonical_json,
    sha256_bytes,
    validate_result,
)

CHUNKING_ALGORITHM_VERSION = "canonical-diff-lines/v1"
MAX_CHUNK_DIFF_BYTES = 32_000
MAX_CHUNK_PROMPT_BYTES = 40_000
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
    # Derived from the full diff, never from a union of chunk-local inventories.
    # Not a new manifest field on disk: validators rederive it from trusted Git bytes.
    full_changed_paths: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        """Return the canonical hash-bound manifest payload."""

        return {
            "manifest_version": "deepseek-chunk-manifest/v1",
            "chunking_algorithm": CHUNKING_ALGORITHM_VERSION,
            "max_chunk_diff_bytes": MAX_CHUNK_DIFF_BYTES,
            "max_chunk_prompt_bytes": MAX_CHUNK_PROMPT_BYTES,
            "max_chunk_count": MAX_CHUNK_COUNT,
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


def _quote_path(value: bytes) -> str:
    """Use Git's reversible C quoting for paths that cannot be plain UTF-8."""

    escapes = {
        7: r"\a",
        8: r"\b",
        9: r"\t",
        10: r"\n",
        11: r"\v",
        12: r"\f",
        13: r"\r",
        34: r"\"",
        92: r"\\",
    }
    printable_ascii = range(0x20, 0x7F)
    return (
        '"'
        + "".join(
            escapes.get(byte, chr(byte) if byte in printable_ascii else f"\\{byte:03o}")
            for byte in value
        )
        + '"'
    )


def _decode_path(value: bytes, *, prefix: bytes = b"") -> str:
    """Preserve raw bytes using Git quoting; plain UTF-8 inventories stay readable.

    Literal leading quotes are quoted too, so a UTF-8 filename cannot collide
    with the C-quoted representation of a non-UTF-8 filename. Strip diff's
    a/b prefix from raw bytes before rendering, never from the quoted string.
    """

    if value.startswith(b'"'):
        if not re.fullmatch(rb'"(?:[^"\\]|\\(?:[abtnvfr"\\]|[0-3][0-7]{2}))*"', value):
            raise ChunkReviewError("invalid quoted diff path")
        value = codecs.escape_decode(value[1:-1])[0]
    if not value.startswith(prefix):
        raise ChunkReviewError("invalid diff path prefix")
    value = value[len(prefix) :]
    if not value or b"\0" in value:
        raise ChunkReviewError("empty or NUL diff path")
    try:
        decoded = value.decode("utf-8")
    except UnicodeDecodeError:
        return _quote_path(value)
    return _quote_path(value) if decoded.startswith('"') else decoded


def _file_paths(header: bytes, section: bytes) -> tuple[str, ...]:
    """Include both rename endpoints; otherwise deduplicate old/new paths."""

    metadata = section.split(b"\n@@", 1)[0].split(b"\nGIT binary patch", 1)[0]
    for action in (b"rename", b"copy"):
        old = re.search(rb"^" + action + rb" from (.+)$", metadata, re.MULTILINE)
        new = re.search(rb"^" + action + rb" to (.+)$", metadata, re.MULTILINE)
        if old and new:
            return tuple(dict.fromkeys((_decode_path(old[1]), _decode_path(new[1]))))
    candidates: list[tuple[str, str]] = []
    for separator in re.finditer(rb' (?=b/|"b/)', header):
        left, right = header[: separator.start()], header[separator.end() :]
        # A quoted token must be consumed completely, including escaped quotes.
        try:
            old_path = _decode_path(left, prefix=b"a/")
            new_path = _decode_path(right, prefix=b"b/")
        except ChunkReviewError:
            continue
        candidates.append((old_path, new_path))
    identical = [pair for pair in candidates if pair[0] == pair[1]]
    candidates = identical or candidates
    if len(candidates) != 1:
        raise ChunkReviewError("ambiguous or invalid canonical diff paths")
    return tuple(dict.fromkeys(candidates[0]))


def _file_ranges(diff: bytes) -> tuple[tuple[int, int, tuple[str, ...]], ...]:
    """Locate file sections in full diff byte order, independently of chunks."""

    headers = list(re.finditer(rb"^diff --git (.+)\n", diff, re.MULTILINE))
    return tuple(
        (
            header.start(),
            headers[index + 1].start() if index + 1 < len(headers) else len(diff),
            _file_paths(
                header[1],
                diff[
                    header.end() : headers[index + 1].start()
                    if index + 1 < len(headers)
                    else len(diff)
                ],
            ),
        )
        for index, header in enumerate(headers)
    )


def _range_paths(
    files: tuple[tuple[int, int, tuple[str, ...]], ...], start: int, end: int
) -> tuple[str, ...]:
    """First-appearance ordering, with exact-path deduplication and overlap."""

    return tuple(
        dict.fromkeys(
            path for left, right, paths in files if left < end and right > start for path in paths
        )
    )


def _cut(diff: bytes, start: int) -> int:
    """Prefer newline boundaries; a giant line is split by its byte identity."""

    target = min(len(diff), start + MAX_CHUNK_DIFF_BYTES)
    if target == len(diff):
        return target
    newline = diff.rfind(b"\n", start + 1, target + 1)
    return newline + 1 if newline > start else target


def plan(
    diff: bytes, *, base_sha: str, head_sha: str, mission_id: str, mission_scope_sha256: str
) -> Manifest:
    """Partition immutable canonical diff bytes without gaps or overlap."""

    if not diff:
        raise ChunkReviewError("empty canonical diff cannot be reviewed")
    chunks: list[Chunk] = []
    files = _file_ranges(diff)
    start = 0
    while start < len(diff):
        end = _cut(diff, start)
        source = diff[start:end]
        chunks.append(
            Chunk(len(chunks), start, end, sha256_bytes(source), _range_paths(files, start, end))
        )
        start = end
    manifest = Manifest(
        base_sha,
        head_sha,
        mission_id,
        mission_scope_sha256,
        sha256_bytes(diff),
        len(diff),
        tuple(chunks),
        _range_paths(files, 0, len(diff)),
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
    files = _file_ranges(diff)
    if manifest.full_changed_paths != _range_paths(files, 0, len(diff)):
        raise ChunkReviewError("full changed paths binding mismatch")
    position = 0
    reconstructed = bytearray()
    for index, chunk in enumerate(manifest.chunks):
        if chunk.index != index or chunk.start != position or chunk.end <= chunk.start:
            raise ChunkReviewError("chunk ranges are not an exact ordered partition")
        source = diff[chunk.start : chunk.end]
        if sha256_bytes(source) != chunk.source_sha256:
            raise ChunkReviewError("chunk source hash mismatch")
        if chunk.changed_paths != _range_paths(files, chunk.start, chunk.end):
            raise ChunkReviewError("chunk changed paths binding mismatch")
        reconstructed.extend(source)
        position = chunk.end
    if position != len(diff) or sha256_bytes(bytes(reconstructed)) != manifest.full_diff_sha256:
        raise ChunkReviewError("chunk coverage is incomplete")


def build_chunk_prompt(*, chunk: Chunk, source: bytes, manifest: Manifest, scope_sha: str) -> str:
    """Build the canonical prompt whose final argument is sent to Claude."""

    return (
        "You are an independent read-only code reviewer. Return only the required generic JSON result. "
        "PASS only when P0/P1/P2 are absent.\n"
        f"Mission: {manifest.mission_id}\nBase: {manifest.base_sha}\nHead: {manifest.head_sha}\n"
        f"Scope SHA256: {scope_sha}\nFull diff SHA256: {manifest.full_diff_sha256}\n"
        f"Chunk manifest SHA256: {manifest.sha256}\nChunk: {chunk.index + 1}/{len(manifest.chunks)} "
        f"range={chunk.start}:{chunk.end} source_sha256={chunk.source_sha256}\n"
        f"Full PR changed paths: {canonical_json(list(manifest.full_changed_paths)).decode()}\n"
        f"Current chunk changed paths: {canonical_json(list(chunk.changed_paths)).decode()}\n"
        "The full PR inventory is derived from the entire canonical diff; the current chunk inventory "
        "identifies file sections overlapping this byte range, which may start or end inside a file.\n"
        "A file absent from this chunk is not necessarily absent from the full PR. Do not assert that "
        "the PR omits a test or other asset solely because it is not shown in this chunk. If a conclusion "
        "requires content from another chunk that is unavailable here, state the evidence limitation "
        "rather than inventing a missing-file fact.\n"
        f"Canonical chunk diff:\n{source.decode('utf-8', 'replace')}"
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
