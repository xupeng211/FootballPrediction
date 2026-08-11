"""PR-1 manifest contract + verification core tests (tests written first).

Contract under test:
- The git-tracked manifest (config/model_artifacts.json lineage) is the SINGLE
  source of truth for artifact identity and the whole-file SHA256 checksum.
- Manifest parsing fails closed on: missing file, malformed JSON, invalid
  structure, duplicate artifact identity, path escaping the approved roots.
- Declared status model: "pending" (never production-ready, checksum may be
  null) vs "active" (checksum required; file must exist and match).
- Verification order: manifest -> safe path resolution -> exists -> whole-file
  SHA256 -> manifest checksum match -> verified state.
- API readiness depends ONLY on artifacts marked required_for="api"; a
  pending/missing CLI-only artifact must not poison API readiness.
- The verification core NEVER deserializes artifacts (no joblib/pickle), and
  the artifact file is NOT required to carry any internal checksum.
- Full-file hashing happens on explicit initialization/refresh only; repeated
  readiness queries must not re-hash.

Side-effect safety: all artifacts are synthetic byte files created under
tmp_path; no real model_zoo/, models/, *.pkl, *.joblib, DB, or training.
"""

import hashlib
import json
from pathlib import Path

import pytest

from src.ml.inference.artifact_manifest import (
    ArtifactEntry,
    ArtifactManifest,
    ManifestError,
    ReadinessManager,
)

MANIFEST_VERSION = 2


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, artifacts: list[dict]) -> Path:
    """Write a synthetic manifest under tmp_path and return its path."""
    data = {
        "version": MANIFEST_VERSION,
        "artifact_root": "models",
        "model_zoo_root": "model_zoo",
        "artifacts": artifacts,
    }
    manifest_path = tmp_path / "model_artifacts.json"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    return manifest_path


def _entry(
    name: str = "api_model",
    path: str | None = None,
    required_for: str = "api",
    status: str = "active",
    checksum: str | None = "0" * 64,
) -> dict:
    return {
        "name": name,
        "path": path or f"model_zoo/production/{name}.pkl",
        "required_for": required_for,
        "status": status,
        "checksum_sha256": checksum,
        "model_type": name,
    }


def _write_artifact(
    tmp_path: Path, rel_path: str, content: bytes = b"synthetic-test-artifact"
) -> Path:
    """Create a synthetic artifact file (arbitrary bytes, never deserialized)."""
    path = tmp_path / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _sha256_of(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch) -> None:
    """CWD redirected to tmp_path: manifest/artifact paths are cwd-relative
    (repo convention — same as check_model_artifacts.py), so hermetic."""
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# TEST A — valid manifest parses
# ---------------------------------------------------------------------------


def test_valid_manifest_parses(tmp_path):
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl")
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned",
                "model_zoo/production/v26.7.pkl",
                checksum=_sha256_of(b"synthetic-test-artifact"),
            )
        ],
    )
    manifest = ArtifactManifest(manifest_path)
    data = manifest.load()
    assert data["version"] == MANIFEST_VERSION
    entries = manifest.entries()
    assert len(entries) == 1
    assert entries[0].name == "v26_7_aligned"
    assert entries[0].status == "active"


# ---------------------------------------------------------------------------
# TEST B — missing manifest fails closed
# ---------------------------------------------------------------------------


def test_missing_manifest_fails_closed(tmp_path):
    manager = ReadinessManager(tmp_path / "does-not-exist.json")
    ready, reason = manager.api_ready()
    assert ready is False
    assert "manifest" in reason


# ---------------------------------------------------------------------------
# TEST C — malformed manifest fails closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content",
    [
        "{not json",  # invalid JSON
        '{"version": 2}',  # missing artifacts list
        '{"version": "x", "artifacts": []}',  # wrong version type
        '{"version": 2, "artifacts": "nope"}',  # artifacts not a list
    ],
)
def test_malformed_manifest_fails_closed(tmp_path, content):
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text(content, encoding="utf-8")
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is False
    assert reason


# ---------------------------------------------------------------------------
# TEST D — duplicate artifact identity rejected
# ---------------------------------------------------------------------------


def test_duplicate_artifact_identity_rejected(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry("dup", "model_zoo/production/a.pkl"),
            _entry("dup", "model_zoo/production/b.pkl"),
        ],
    )
    manifest = ArtifactManifest(manifest_path)
    with pytest.raises(ManifestError, match="duplicate"):
        manifest.entries()


# ---------------------------------------------------------------------------
# TEST E — path escaping approved artifact roots rejected
# ---------------------------------------------------------------------------


def test_path_escape_traversal_rejected(tmp_path):
    manifest_path = _write_manifest(tmp_path, [_entry("evil", "../outside.pkl")])
    manifest = ArtifactManifest(manifest_path)
    entry = manifest.entries()[0]
    with pytest.raises(ManifestError):
        manifest.resolve_path(entry.path)


def test_path_escape_absolute_rejected(tmp_path):
    manifest_path = _write_manifest(tmp_path, [_entry("evil", "/etc/passwd")])
    manifest = ArtifactManifest(manifest_path)
    entry = manifest.entries()[0]
    with pytest.raises(ManifestError):
        manifest.resolve_path(entry.path)


def test_path_escape_symlink_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.pkl").write_bytes(b"secret")
    # artifact path inside approved root, but a symlink points outside
    model_zoo = tmp_path / "model_zoo"
    model_zoo.mkdir()
    (model_zoo / "production").symlink_to(outside, target_is_directory=True)

    manifest_path = _write_manifest(
        tmp_path, [_entry("symlink", "model_zoo/production/secret.pkl")]
    )
    manifest = ArtifactManifest(manifest_path)
    entry = manifest.entries()[0]
    with pytest.raises(ManifestError):
        manifest.resolve_path(entry.path)


# ---------------------------------------------------------------------------
# TEST F — pending artifact is NOT ready
# ---------------------------------------------------------------------------


def test_pending_artifact_not_ready(tmp_path):
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl")
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned", "model_zoo/production/v26.7.pkl", status="pending", checksum=None
            )
        ],
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is False
    assert "pending" in reason


# ---------------------------------------------------------------------------
# TEST G — active artifact with missing file is NOT ready
# ---------------------------------------------------------------------------


def test_active_artifact_missing_file_not_ready(tmp_path):
    manifest_path = _write_manifest(
        tmp_path, [_entry("v26_7_aligned", "model_zoo/production/missing.pkl")]
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is False
    assert "missing" in reason


# ---------------------------------------------------------------------------
# TEST H — active artifact with checksum mismatch is NOT ready
# ---------------------------------------------------------------------------


def test_active_artifact_checksum_mismatch_not_ready(tmp_path):
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", b"actual-bytes")
    manifest_path = _write_manifest(
        tmp_path, [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum="1" * 64)]
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is False
    assert "checksum" in reason


# ---------------------------------------------------------------------------
# TEST I — active artifact with checksum match becomes VERIFIED/READY
# ---------------------------------------------------------------------------


def test_active_artifact_checksum_match_ready(tmp_path):
    content = b"synthetic-test-artifact"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(content))],
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is True
    assert reason == ""


# ---------------------------------------------------------------------------
# TEST J — checksum is SHA256 of COMPLETE artifact bytes
# ---------------------------------------------------------------------------


def test_checksum_is_sha256_of_complete_bytes(tmp_path):
    content = b"synthetic-test-artifact"
    path = _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest = ArtifactManifest(tmp_path / "nested" / "does-not-matter.json")
    computed = manifest.compute_sha256(path)
    assert computed == hashlib.sha256(content).hexdigest()
    # trailing byte changes the whole-file hash
    path.write_bytes(content + b"!")
    assert manifest.compute_sha256(path) != hashlib.sha256(content).hexdigest()


# ---------------------------------------------------------------------------
# TEST K — envelope/internal checksum is NOT required
# ---------------------------------------------------------------------------


def test_internal_checksum_not_required(tmp_path):
    # The artifact file is arbitrary bytes with NO internal checksum field;
    # the single authoritative checksum lives in the git-tracked manifest.
    content = b"synthetic-test-artifact"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(content))],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is True
    # and the verification never deserializes: corrupt "pickle-like" bytes
    # must still verify by hash alone
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", b"\x80\x04\x95corrupted-synthetic")
    corrupted = b"\x80\x04\x95corrupted-synthetic"
    manifest_path2 = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(corrupted))],
    )
    assert ReadinessManager(manifest_path2).api_ready()[0] is True


# ---------------------------------------------------------------------------
# TEST L — CLI-only pending artifact does not poison API readiness
# ---------------------------------------------------------------------------


def test_cli_only_pending_does_not_poison_api_readiness(tmp_path):
    content = b"api-artifact"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned",
                "model_zoo/production/v26.7.pkl",
                required_for="api",
                checksum=_sha256_of(content),
            ),
            _entry(
                "titan",
                "models/titan_v4466_real_combat.joblib",
                required_for="cli",
                status="pending",
                checksum=None,
            ),
        ],
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.api_ready()
    assert ready is True
    assert reason == ""


# ---------------------------------------------------------------------------
# TEST M — required API artifact pending/missing/mismatch makes API readiness false
# ---------------------------------------------------------------------------


def test_api_artifact_pending_makes_api_unready(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned", "model_zoo/production/v26.7.pkl", status="pending", checksum=None
            ),
            _entry(
                "titan",
                "models/titan.joblib",
                required_for="cli",
                status="active",
                checksum="0" * 64,
            ),
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is False


def test_api_artifact_missing_makes_api_unready(tmp_path):
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/absent.pkl")],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is False


def test_api_artifact_mismatch_makes_api_unready(tmp_path):
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", b"different")
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(b"expected")
            )
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is False


# ---------------------------------------------------------------------------
# CACHE — full hashing is NOT repeated for every readiness query
# ---------------------------------------------------------------------------


def test_full_hash_runs_once_per_initialization(tmp_path, monkeypatch):
    content = b"synthetic-test-artifact"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(content))],
    )
    manager = ReadinessManager(manifest_path)

    hashes = []
    original = ArtifactManifest.compute_sha256

    def counting_sha256(_self, path):
        hashes.append(str(path))
        return original(path)

    monkeypatch.setattr(ArtifactManifest, "compute_sha256", counting_sha256)

    # first query triggers the one-time verification
    assert manager.api_ready()[0] is True
    assert len(hashes) == 1
    first_verify_count = len(hashes)

    # repeated queries must NOT re-hash
    for _ in range(5):
        assert manager.api_ready()[0] is True
    assert len(hashes) == first_verify_count

    # explicit refresh re-verifies (and re-hashes exactly once more)
    manager.refresh()
    assert len(hashes) == first_verify_count + 1


def test_manager_accepts_entry_model_type(tmp_path):
    content = b"x"
    _write_artifact(tmp_path, "model_zoo/production/m.pkl", content)
    manifest_path = _write_manifest(
        tmp_path, [_entry("m", "model_zoo/production/m.pkl", checksum=_sha256_of(content))]
    )
    manifest = ArtifactManifest(manifest_path)
    entries = manifest.entries()
    assert isinstance(entries[0], ArtifactEntry)
    assert entries[0].model_type == "m"
