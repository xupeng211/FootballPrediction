"""PR-1 manifest contract + verification core tests (tests written first).

lifecycle: permanent

Contract under test:
- The git-tracked manifest (config/model_artifacts.json lineage) is the SINGLE
  source of truth for artifact identity and the whole-file SHA256 checksum.
- Manifest parsing fails closed on: missing file, malformed JSON, invalid
  structure, duplicate artifact identity, path escaping the approved roots.
- Status model: "pending" (never production-ready) vs "active" (checksum
  required; file must exist and match).
- ARTIFACT VERIFIED != SERVICE READY: checksum matching proves integrity only;
  service readiness additionally requires a process-local loaded-model signal
  (mark_model_loaded, the PR-3 hook) bound to the verified identity AND an
  unchanged cheap stat fingerprint (st_dev/st_ino/st_size/st_mtime_ns). A
  checksum-matching-but-unloadable/corrupt artifact can never make
  /health/readiness or /health/quick return 200.
- Cheap fingerprint invariants run per health request (one stat, no hash);
  any change after verification invalidates readiness immediately; full-file
  hashing runs on initialization/refresh only. API readiness depends ONLY on
  required_for="api" artifacts (pending CLI rows never poison it); the core
  NEVER deserializes artifacts, and the artifact file carries no checksum.

Side-effect safety: all artifacts are synthetic byte files created under
tmp_path; no real model_zoo/, models/, *.pkl, *.joblib, DB, or training.
"""

import hashlib
import json
import os
from pathlib import Path
import threading
import time

import pytest

from src.ml.inference.artifact_manifest import (
    ArtifactEntry,
    ArtifactManifest,
    ManifestError,
    ReadinessManager,
)

MANIFEST_VERSION = 2

# Corrupt pickle-like bytes: hash-only verification is integrity checking,
# NOT a load signal — rejected from service readiness.
CORRUPT_PICKLE_BYTES = b"\x80\x04\x95corrupted-synthetic"


# ---- helpers ----


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


def _install_verified_manager(tmp_path: Path, content: bytes = b"synthetic-test-artifact"):
    """Active api artifact + matching checksum -> ARTIFACT VERIFIED manager;
    service readiness still requires an explicit mark_model_loaded call."""
    artifact_path = _write_artifact(tmp_path, "model_zoo/production/api_model.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("api_model", "model_zoo/production/api_model.pkl", checksum=_sha256_of(content))],
    )
    manager = ReadinessManager(manifest_path)
    return manager, manifest_path, artifact_path


def _count_hashes(monkeypatch) -> tuple[list[str], object]:
    """Install a SHA256 counter; returns (hashes, original) for the manager."""
    hashes: list[str] = []
    original = ArtifactManifest.compute_sha256

    def counting_sha256(_self, path):
        hashes.append(str(path))
        return original(path)

    monkeypatch.setattr(ArtifactManifest, "compute_sha256", counting_sha256)
    return hashes, original


def _manifest_for(checksum_content: bytes) -> str:
    """Full version-2 manifest JSON with one active api_model entry."""
    return json.dumps(
        {
            "version": MANIFEST_VERSION,
            "artifact_root": "models",
            "model_zoo_root": "model_zoo",
            "artifacts": [
                _entry(
                    "api_model",
                    "model_zoo/production/api_model.pkl",
                    checksum=_sha256_of(checksum_content),
                )
            ],
        }
    )


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch) -> None:
    """CWD redirected to tmp_path: manifest/artifact paths are cwd-relative
    (repo convention — same as check_model_artifacts.py), so hermetic."""
    monkeypatch.chdir(tmp_path)


# TEST A — valid manifest parses


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
    assert manifest.load()["version"] == MANIFEST_VERSION
    entry = manifest.entries()[0]
    assert (entry.name, entry.status) == ("v26_7_aligned", "active")


# TEST B — missing manifest fails closed


def test_missing_manifest_fails_closed(tmp_path):
    manager = ReadinessManager(tmp_path / "does-not-exist.json")
    ready, reason = manager.service_ready()
    assert ready is False
    assert "manifest" in reason


# TEST C — malformed manifest fails closed


@pytest.mark.parametrize(
    "content",
    [
        "{not json",  # invalid JSON
        '{"version": 2}',  # missing artifacts list
        '{"version": "x", "artifacts": []}',  # wrong version type
        '{"version": 2, "artifacts": "nope"}',  # artifacts not a list
        # F5 (Codex): unsafe artifact name (path-ish) fails closed
        '{"version": 2, "artifacts": [{"name": "../evil", "path": "models/x.pkl",'
        ' "required_for": "api", "status": "active", "checksum_sha256": "0"}]}',
    ],
)
def test_malformed_manifest_fails_closed(tmp_path, content):
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text(content, encoding="utf-8")
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.service_ready()
    assert ready is False
    assert reason


def test_unsupported_version_rejected(tmp_path):
    """F4 (Codex): wrong manifest version fails closed, never goes ready."""
    manifest_path = tmp_path / "bad-version.json"
    manifest_path.write_text('{"version": 1, "artifacts": []}', encoding="utf-8")
    with pytest.raises(ManifestError, match="version"):
        ArtifactManifest(manifest_path).load()
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.service_ready()
    assert ready is False
    assert "version" in reason


def test_required_for_invalid_value_rejected(tmp_path):
    """F3 (Codex): non-string / unknown / MISSING required_for fails closed."""
    for bad_value in (None, 123, "prediction_runtime"):
        manifest_path = _write_manifest(tmp_path, [_entry("m", required_for=bad_value)])
        with pytest.raises(ManifestError, match="required_for"):
            ArtifactManifest(manifest_path).entries()
    # missing key entirely: no silent default-to-api (fail closed)
    manifest_path = _write_manifest(
        tmp_path,
        [{"name": "m", "path": "models/x.pkl", "status": "active", "checksum_sha256": "0" * 64}],
    )
    with pytest.raises(ManifestError, match="required_for"):
        ArtifactManifest(manifest_path).entries()


# TEST D — duplicate artifact identity rejected


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


# TEST E — path escaping approved artifact roots rejected


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


# TEST F — pending artifact is NOT ready (reason + load-signal refusal)


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
    ready, reason = manager.service_ready()
    assert ready is False
    assert "pending" in reason
    assert manager.mark_model_loaded("v26_7_aligned") is False  # cannot load pending


# TEST G — active artifact with missing file is NOT ready (reason asserted)


def test_active_artifact_missing_file_not_ready(tmp_path):
    manifest_path = _write_manifest(
        tmp_path, [_entry("v26_7_aligned", "model_zoo/production/missing.pkl")]
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.service_ready()
    assert ready is False
    assert "missing" in reason
    assert manager.mark_model_loaded("v26_7_aligned") is False


# TEST H — active artifact with checksum mismatch is NOT ready


def test_active_artifact_checksum_mismatch_not_ready(tmp_path):
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", b"actual-bytes")
    manifest_path = _write_manifest(
        tmp_path, [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum="1" * 64)]
    )
    manager = ReadinessManager(manifest_path)
    ready, reason = manager.service_ready()
    assert ready is False
    assert "checksum" in reason
    assert manager.mark_model_loaded("v26_7_aligned") is False


# TEST I+B — verified but NOT loaded -> NOT ready; matching load signal -> ready


def test_verified_then_loaded_readiness_transition(tmp_path):
    """Checksum match alone is artifact-verified, NOT service-ready; a
    matching load signal flips readiness (snapshot distinguishes layers)."""
    manager, _, _ = _install_verified_manager(tmp_path)
    ready, reason = manager.service_ready()
    assert ready is False
    assert "not loaded" in reason
    snapshot = manager.snapshot()
    assert (snapshot["artifact_verified"], snapshot["service_ready"], snapshot["model_loaded"]) == (
        True,
        False,
        False,
    )
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    assert manager.service_ready() == (True, "")
    snapshot = manager.snapshot()
    assert (snapshot["artifact_verified"], snapshot["service_ready"], snapshot["model_loaded"]) == (
        True,
        True,
        True,
    )


# TEST A (required) — corrupt bytes: verified-by-hash but NEVER ready unloaded


def test_corrupt_bytes_verified_but_not_service_ready(tmp_path):
    """Matching-checksum corrupt bytes: hash-only verification proves integrity
    (never deserializes) — verified, but NOT service-ready without a load."""
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", CORRUPT_PICKLE_BYTES)
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned",
                "model_zoo/production/v26.7.pkl",
                checksum=_sha256_of(CORRUPT_PICKLE_BYTES),
            )
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.snapshot()["artifact_verified"] is True
    assert manager.service_ready()[0] is False  # checksum match alone != ready
    # the load signal is what flips readiness (PR-3 contract; PR-1 never
    # deserializes the corrupt bytes)
    assert manager.mark_model_loaded("v26_7_aligned", _sha256_of(CORRUPT_PICKLE_BYTES)) is True
    assert manager.service_ready()[0] is True


# TEST C (required) — loaded signal without verified artifact -> NOT ready


def test_loaded_without_verified_not_ready(tmp_path):
    """Load signal without a verified artifact: refused, readiness stays off."""
    manager, _, _ = _install_verified_manager(tmp_path)
    assert manager.mark_model_loaded("titan_v4466_real_combat", "0" * 64) is False
    assert manager.service_ready()[0] is False
    # pending artifact: load signal refused (not verified)
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned", "model_zoo/production/v26.7.pkl", status="pending", checksum=None
            )
        ],
    )
    pending = ReadinessManager(manifest_path)
    assert pending.mark_model_loaded("v26_7_aligned") is False
    assert pending.service_ready()[0] is False


# TEST D (required) — identity mismatch -> NOT ready


def test_identity_mismatch_loaded_signal_refused(tmp_path):
    """A load signal for a non-matching name/checksum must be refused."""
    manager, _, _ = _install_verified_manager(tmp_path)
    assert manager.mark_model_loaded("other_artifact", "0" * 64) is False
    assert manager.mark_model_loaded("api_model", "1" * 64) is False  # wrong checksum
    assert manager.service_ready()[0] is False
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    assert manager.service_ready()[0] is True


def test_identity_change_clears_stale_loaded_signal(tmp_path):
    """Re-verifying a DIFFERENT file must not preserve the old loaded signal:
    service stays not-ready until a fresh matching load (TEST H + D legs)."""
    content_a = b"version-a-bytes"
    manager, manifest_path, artifact_path = _install_verified_manager(tmp_path, content_a)
    assert manager.mark_model_loaded("api_model", _sha256_of(content_a)) is True
    assert manager.service_ready()[0] is True

    # leg 1: in-place edit (same inode) + manifest checksum updated -> refresh
    content_b = b"version-b-bytes"
    artifact_path.write_bytes(content_b)
    manifest_path.write_text(_manifest_for(content_b), encoding="utf-8")
    manager.refresh()
    assert manager.service_ready()[0] is False  # stale load signal NOT preserved
    assert manager.snapshot()["model_loaded"] is False

    # leg 2: atomic replacement (new inode) while manifest still declares B
    replacement = tmp_path / "replacement.pkl"
    replacement.write_bytes(b"version-c-bytes")
    replacement.replace(artifact_path)
    assert manager.service_ready()[0] is False  # cheap invariant catches it
    manager.refresh()
    assert manager.service_ready()[0] is False  # checksum mismatch -> unverified

    # operator fixes the manifest checksum; refresh still must NOT resurrect
    manifest_path.write_text(_manifest_for(b"version-c-bytes"), encoding="utf-8")
    manager.refresh()
    assert manager.service_ready()[0] is False
    assert manager.snapshot()["model_loaded"] is False

    # only a fresh matching load signal restores readiness
    assert manager.mark_model_loaded("api_model", _sha256_of(b"version-c-bytes")) is True
    assert manager.service_ready()[0] is True


# TEST E (required) — artifact deleted after ready -> NOT ready (no re-hash)


def test_delete_after_ready_invalidates(tmp_path, monkeypatch):
    manager, _, artifact_path = _install_verified_manager(tmp_path)
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    assert manager.service_ready()[0] is True

    hashes, _ = _count_hashes(monkeypatch)
    artifact_path.unlink()
    ready, reason = manager.service_ready()
    assert ready is False
    assert "changed" in reason
    assert hashes == []  # deletion detected by stat only — no SHA256
    assert all(manager.service_ready()[0] is False for _ in range(3))
    assert hashes == []  # negative-cached: no re-hash while invalid


# TEST F (required) — artifact replaced after ready -> NOT ready (no re-hash)


def test_replace_after_ready_invalidates(tmp_path, monkeypatch):
    """Atomic replacement (new inode) OR same-inode mtime bump: invalidates."""
    manager, _, artifact_path = _install_verified_manager(tmp_path)
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    assert manager.service_ready()[0] is True
    hashes, _ = _count_hashes(monkeypatch)

    replacement = tmp_path / "replacement.pkl"
    replacement.write_bytes(b"replacement-bytes")
    replacement.replace(artifact_path)  # atomic: new inode, same path
    ready, reason = manager.service_ready()
    assert ready is False
    assert "changed" in reason
    assert hashes == []  # replacement detected by stat only — no SHA256

    # N2 (Codex): mtime bump on a FRESH manager with healthy verified state
    # (the manager above is already invalidated + negative-cached)
    manifest_path2 = _write_manifest(
        tmp_path,
        [
            _entry(
                "api_model",
                "model_zoo/production/api_model.pkl",
                checksum=_sha256_of(b"replacement-bytes"),
            )
        ],
    )
    fresh = ReadinessManager(manifest_path2)
    assert fresh.mark_model_loaded("api_model", _sha256_of(b"replacement-bytes")) is True
    assert fresh.service_ready()[0] is True
    hashes_before = len(hashes)
    os.utime(artifact_path, ns=(time.time_ns(), time.time_ns()))
    assert fresh.service_ready()[0] is False
    assert len(hashes) == hashes_before  # mtime detected by stat only — no SHA256


def test_symlink_retarget_after_ready_invalidates(tmp_path, monkeypatch):
    """F4 (Codex): symlink retargeted after verification -> invariant fails."""
    production = tmp_path / "model_zoo" / "production"
    production.mkdir(parents=True)
    target_a = production / "a.pkl"
    target_b = production / "b.pkl"
    target_a.write_bytes(b"bytes-a")
    target_b.write_bytes(b"bytes-b")
    link = production / "current.pkl"
    link.symlink_to(target_a)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("api_model", "model_zoo/production/current.pkl", checksum=_sha256_of(b"bytes-a"))],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.mark_model_loaded("api_model", _sha256_of(b"bytes-a")) is True
    assert manager.service_ready()[0] is True

    hashes, _ = _count_hashes(monkeypatch)
    link.unlink()
    link.symlink_to(target_b)  # retarget: same declared path, different file
    assert manager.service_ready()[0] is False
    assert hashes == []  # detected by re-resolution + stat — no SHA256


def test_verify_rejects_file_changed_during_verification(tmp_path, monkeypatch):
    """F1 (Codex): a replacement between hash and fingerprint capture fails
    closed — the cached fingerprint can never belong to unverified bytes."""
    content = b"version-a-bytes"
    _write_artifact(tmp_path, "model_zoo/production/api_model.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("api_model", "model_zoo/production/api_model.pkl", checksum=_sha256_of(content))],
    )
    manager = ReadinessManager(manifest_path)
    original = ArtifactManifest.compute_sha256

    def swapping_sha256(_self, p):
        digest = original(p)
        p.write_bytes(b"version-b-bytes")  # swap AFTER hashing (stat race)
        return digest

    monkeypatch.setattr(ArtifactManifest, "compute_sha256", swapping_sha256)
    snapshot = manager.snapshot()
    assert snapshot["artifact_verified"] is False
    assert snapshot["artifacts"]["api_model"]["status"] == "verification_error"
    assert manager.service_ready()[0] is False


def test_checksum_binding_catches_fingerprint_identical_change(tmp_path):
    """F2 (Codex): a same-size edit with restored mtime keeps the fingerprint,
    but the manifest checksum change still clears the stale loaded signal."""
    content_a, content_b = b"version-a-bytes", b"version-b-bytes"  # same size
    manager, manifest_path, artifact_path = _install_verified_manager(tmp_path, content_a)
    assert manager.mark_model_loaded("api_model", _sha256_of(content_a)) is True
    assert manager.service_ready()[0] is True

    stat_before = artifact_path.stat()
    artifact_path.write_bytes(content_b)  # same size -> same fingerprint fields
    os.utime(artifact_path, ns=(stat_before.st_atime_ns, stat_before.st_mtime_ns))
    manifest_path.write_text(_manifest_for(content_b), encoding="utf-8")

    manager.refresh()  # full re-verify: identical fingerprint, new checksum
    snapshot = manager.snapshot()
    assert snapshot["artifact_verified"] is True
    assert snapshot["model_loaded"] is False  # loaded signal bound to A cleared
    assert snapshot["service_ready"] is False
    assert manager.mark_model_loaded("api_model", _sha256_of(content_b)) is True
    assert manager.service_ready()[0] is True


# TEST G (required) — unchanged ready file never re-hashes
# (covered by test_ready_probes_never_rehash below)
# TEST H (required) — refresh does NOT restore stale loaded state
# (covered by test_identity_change_clears_stale_loaded_signal)


# TEST J — checksum is SHA256 of COMPLETE artifact bytes


def test_checksum_is_sha256_of_complete_bytes(tmp_path):
    content = b"synthetic-test-artifact"
    path = _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest = ArtifactManifest(tmp_path / "nested" / "does-not-matter.json")
    computed = manifest.compute_sha256(path)
    assert computed == hashlib.sha256(content).hexdigest()
    # trailing byte changes the whole-file hash
    path.write_bytes(content + b"!")
    assert manifest.compute_sha256(path) != hashlib.sha256(content).hexdigest()


# TEST L — CLI artifacts never poison API readiness (pending + broken active)


def test_cli_artifacts_never_poison_api_readiness(tmp_path):
    """Pending or broken active CLI artifacts leave API readiness untouched."""
    content = b"api-artifact"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    api = _entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(content))
    manifest_path = _write_manifest(
        tmp_path,
        [
            api,
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
    assert manager.snapshot()["artifact_verified"] is True
    assert manager.service_ready()[0] is False  # verified but not loaded
    assert manager.mark_model_loaded("v26_7_aligned", _sha256_of(content)) is True
    assert manager.service_ready() == (True, "")

    # phase 2: active CLI artifact whose path IS a directory (verify error)
    (tmp_path / "models" / "titan_dir").mkdir(parents=True, exist_ok=True)
    manifest_path = _write_manifest(
        tmp_path,
        [
            api,
            _entry("titan", "models/titan_dir", required_for="cli", checksum="0" * 64),
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.mark_model_loaded("v26_7_aligned", _sha256_of(content)) is True
    assert manager.service_ready() == (True, "")
    # CLI failure visible per-artifact, never poisoning API readiness
    snapshot = manager.snapshot()
    assert snapshot["artifacts"]["titan"]["status"] == "verification_error"
    assert snapshot["artifacts"]["v26_7_aligned"]["status"] == "verified"


# TEST M — required API artifact pending/missing/mismatch makes service unready


def test_api_artifact_pending_missing_mismatch_unready(tmp_path):
    """Required api artifact pending / file missing / checksum mismatch:
    each alone keeps service readiness false (CLI rows never rescue it)."""
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
    assert ReadinessManager(manifest_path).service_ready()[0] is False  # pending

    manifest_path = _write_manifest(
        tmp_path, [_entry("v26_7_aligned", "model_zoo/production/absent.pkl")]
    )
    assert ReadinessManager(manifest_path).service_ready()[0] is False  # missing

    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", b"different")
    manifest_path = _write_manifest(
        tmp_path,
        [
            _entry(
                "v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum=_sha256_of(b"expected")
            )
        ],
    )
    assert ReadinessManager(manifest_path).service_ready()[0] is False  # mismatch


# CACHE — full hashing is NOT repeated for every readiness query


def test_ready_probes_never_rehash(tmp_path, monkeypatch):
    """TEST G+CACHE: verification runs once at init; repeated ready probes
    check cheap stat invariants only (zero re-hash); refresh re-hashes once."""
    manager, _, _ = _install_verified_manager(tmp_path)
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    hashes, _ = _count_hashes(monkeypatch)

    assert manager.service_ready()[0] is True  # cached verification, no new hash
    first_verify_count = len(hashes)
    for _ in range(5):
        assert manager.service_ready()[0] is True  # cheap stat invariants only
    assert len(hashes) == first_verify_count  # zero re-hash while unchanged+ready
    manager.refresh()  # explicit refresh re-verifies (re-hashes exactly once)
    assert len(hashes) == first_verify_count + 1


def test_manager_accepts_entry_model_type(tmp_path):
    content = b"x"
    _write_artifact(tmp_path, "model_zoo/production/m.pkl", content)
    manifest_path = _write_manifest(
        tmp_path, [_entry("m", "model_zoo/production/m.pkl", checksum=_sha256_of(content))]
    )
    entry = ArtifactManifest(manifest_path).entries()[0]
    assert isinstance(entry, ArtifactEntry)
    assert entry.model_type == "m"


# F1 (Codex) — unexpected I/O errors fail closed instead of surfacing 500


def test_unreadable_manifest_fails_closed_not_raise(tmp_path):
    """Manifest path is a directory: open() raises OSError -> contained."""
    dir_path = tmp_path / "not-a-file.json"
    dir_path.mkdir()
    manager = ReadinessManager(dir_path)
    ready, reason = manager.service_ready()  # must NOT raise
    assert ready is False
    assert reason


# concurrency — first initialization hashes exactly once under threads


def test_concurrent_first_initialization_hashes_once(tmp_path, monkeypatch):
    """Concurrent first probes: exactly one verification, no deadlock."""
    manager, _, _ = _install_verified_manager(tmp_path)
    hashes, _ = _count_hashes(monkeypatch)
    barrier = threading.Barrier(2)
    results: list[tuple[bool, str]] = []

    def _probe() -> None:
        barrier.wait()
        results.append(manager.service_ready())

    threads = [threading.Thread(target=_probe) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(ready is False for ready, _ in results)  # no load signal yet
    assert len(hashes) == 1  # one verification despite concurrent first calls
    assert manager.mark_model_loaded("api_model", _sha256_of(b"synthetic-test-artifact")) is True
    assert manager.service_ready()[0] is True
    assert len(hashes) == 1  # load signal reuses the cached verification


# N4 (Codex) — negative cache: failing probes never re-hash per request


def test_negative_cache_bounds_rehashing(tmp_path, monkeypatch):
    """Active + checksum mismatch: failing probes never re-hash per request."""
    content = b"actual-bytes"
    _write_artifact(tmp_path, "model_zoo/production/v26.7.pkl", content)
    manifest_path = _write_manifest(
        tmp_path,
        [_entry("v26_7_aligned", "model_zoo/production/v26.7.pkl", checksum="1" * 64)],
    )
    manager = ReadinessManager(manifest_path)

    hashes, _ = _count_hashes(monkeypatch)

    assert manager.service_ready()[0] is False
    assert len(hashes) == 1  # first probe hashes once
    for _ in range(5):
        assert manager.service_ready()[0] is False
    assert len(hashes) == 1  # negative cache: no re-hash within TTL

    # explicit refresh forces re-verification despite the negative cache
    first_verify_count = len(hashes)
    manager.refresh()
    assert len(hashes) == first_verify_count + 1

    # TTL=0: every probe re-evaluates (self-healing path, no negative cache)
    ttl_zero = ReadinessManager(manifest_path, negative_cache_ttl=0.0)
    probe_count = 3
    for _ in range(probe_count):
        assert ttl_zero.service_ready()[0] is False
    assert len(hashes) == first_verify_count + 1 + probe_count
