"""PR-1 health readiness/quick HTTP semantics tests.

lifecycle: permanent

Contract under test:
- /health/readiness: DB ready + API model SERVICE ready -> 200; model not
  ready -> 503; DB unavailable -> 503.
- SERVICE READY means: artifact verified (active + exists + whole-file SHA256
  match) AND a process-local loaded-model signal (mark_model_loaded) AND an
  unchanged cheap stat fingerprint. Checksum matching ALONE never yields 200.
- /health/quick: cheap subset (DB + CACHED model readiness, no full hash on
  request); not-ready -> 503 (never a false-green 200); ready -> 200.
- 503 response bodies stay useful but expose no absolute filesystem paths,
  credentials, or raw exception traces.
- Health requests must NOT re-run whole-file SHA256 verification (cached);
  readiness responses may expose the safe artifact_integrity/model_loaded
  distinction.

Side-effect safety: synthetic byte artifacts under tmp_path only; the real
Predictor is never instantiated; DB checks are monkeypatched (no live DB).
"""

import hashlib
import json
import os
from pathlib import Path

os.environ["LOG_LEVEL"] = "INFO"  # must precede src imports (pydantic enum)

from fastapi.testclient import TestClient
import pytest
from starlette import status

import src.api.health as health_module
from src.main import app as fastapi_app
from src.ml.inference.artifact_manifest import ArtifactManifest, ReadinessManager

ARTIFACT_CONTENT = b"synthetic-test-artifact"
CORRUPT_PICKLE_BYTES = b"\x80\x04\x95corrupted-synthetic"


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path, monkeypatch):
    """cwd-relative artifact resolution stays hermetic."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def db_healthy(monkeypatch):
    """Default: DB healthy on both check paths; tests override as needed."""

    async def _db_async_ok():
        return {"healthy": True, "message": "ok", "response_time_ms": 1.0}

    async def _db_quick_ok():
        return True

    monkeypatch.setattr(health_module, "_check_database_async", _db_async_ok)
    monkeypatch.setattr(health_module, "_check_database_quick", _db_quick_ok)


@pytest.fixture
def client():
    fastapi_app.state.limiter.enabled = False
    return TestClient(fastapi_app)


def _write_manifest(tmp_path: Path, artifacts: list[dict]) -> Path:
    data = {
        "version": 2,
        "artifact_root": "models",
        "model_zoo_root": "model_zoo",
        "artifacts": artifacts,
    }
    manifest_path = tmp_path / "model_artifacts.json"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    return manifest_path


def _sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _api_entry(checksum: str | None, status: str = "active") -> dict:
    return {
        "name": "v26_7_aligned",
        "path": "model_zoo/production/v26.7_aligned_production.pkl",
        "required_for": "api",
        "status": status,
        "checksum_sha256": checksum,
        "model_type": "v26_7_aligned",
    }


def _cli_entry() -> dict:
    return {
        "name": "titan_v4466_real_combat",
        "path": "models/titan_v4466_real_combat.joblib",
        "required_for": "cli",
        "status": "pending",
        "checksum_sha256": None,
        "model_type": "titan",
    }


def _install_ready_manager(
    tmp_path, monkeypatch, content: bytes = ARTIFACT_CONTENT
) -> ReadinessManager:
    """API artifact verified + loaded signal -> SERVICE ready manager."""
    artifact_dir = tmp_path / "model_zoo" / "production"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "v26.7_aligned_production.pkl").write_bytes(content)
    manifest_path = _write_manifest(tmp_path, [_api_entry(_sha256_hex(content)), _cli_entry()])
    manager = ReadinessManager(manifest_path)
    # artifact VERIFIED alone is NOT service-ready — the load signal is
    # required (and CLI-only pending must not poison it)
    assert manager.snapshot()["artifact_verified"] is True
    assert manager.service_ready()[0] is False
    assert manager.mark_model_loaded("v26_7_aligned", _sha256_hex(content)) is True
    assert manager.service_ready()[0] is True
    monkeypatch.setattr(health_module, "_readiness_manager", manager)
    return manager


def _install_not_ready_manager(tmp_path, monkeypatch) -> ReadinessManager:
    """API artifact pending -> not ready manager (mirrors current repo reality)."""
    manifest_path = _write_manifest(tmp_path, [_api_entry(None, status="pending"), _cli_entry()])
    manager = ReadinessManager(manifest_path)
    assert manager.service_ready()[0] is False
    monkeypatch.setattr(health_module, "_readiness_manager", manager)
    return manager


# ---------------------------------------------------------------------------
# /health/readiness
# ---------------------------------------------------------------------------


def test_readiness_200_when_db_and_model_ready(client, tmp_path, monkeypatch):
    _install_ready_manager(tmp_path, monkeypatch)
    resp = client.get("/health/readiness")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["ready"] is True
    assert body["checks"]["model"]["status"] == "healthy"


def test_readiness_503_when_model_not_ready(client, tmp_path, monkeypatch):
    _install_not_ready_manager(tmp_path, monkeypatch)
    resp = client.get("/health/readiness")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    # main.py:338 wraps HTTPException detail into {"error", "message", ...}
    body = resp.json()
    assert body["error"] is True
    assert body["message"]["ready"] is False
    assert body["message"]["checks"]["model"]["status"] == "unhealthy"


def test_readiness_503_when_db_unavailable(client, tmp_path, monkeypatch):
    _install_ready_manager(tmp_path, monkeypatch)

    async def _db_async_down():
        return {"healthy": False, "message": "数据库连接失败", "response_time_ms": 1.0}

    monkeypatch.setattr(health_module, "_check_database_async", _db_async_down)
    resp = client.get("/health/readiness")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# /health (full) — informational: 200 even when model is unhealthy
# ---------------------------------------------------------------------------


def test_health_full_200_when_model_unhealthy(client, tmp_path, monkeypatch):
    """F7 (Codex): /health stays informational (200) with truthful body."""
    _install_not_ready_manager(tmp_path, monkeypatch)
    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert body["checks"]["model"]["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# unexpected manifest I/O errors -> 503 (never 500)
# ---------------------------------------------------------------------------


def test_manifest_unreadable_503_not_500(client, tmp_path, monkeypatch):
    """F1 (Codex): unreadable manifest fails closed to 503, never 500."""
    dir_path = tmp_path / "not-a-file.json"
    dir_path.mkdir()
    manager = ReadinessManager(dir_path)
    monkeypatch.setattr(health_module, "_readiness_manager", manager)

    for endpoint in ("/health/readiness", "/health/quick"):
        resp = client.get(endpoint)
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        # N2 (Codex): the generic reason must not embed the OSError text
        # (which would carry the absolute tmp_path)
        text = resp.text
        assert "Traceback" not in text
        assert str(dir_path) not in text
        assert "not-a-file.json" not in text


# ---------------------------------------------------------------------------
# /health/quick
# ---------------------------------------------------------------------------


def test_quick_503_when_model_pending(client, tmp_path, monkeypatch):
    _install_not_ready_manager(tmp_path, monkeypatch)
    resp = client.get("/health/quick")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    # main.py:338 wraps HTTPException detail into {"error", "message", ...}
    body = resp.json()
    assert body["error"] is True
    assert body["message"]["status"] == "not_ready"
    assert body["message"]["checks"]["model"] is False


def test_quick_503_when_db_unavailable(client, tmp_path, monkeypatch):
    _install_ready_manager(tmp_path, monkeypatch)

    async def _db_quick_down():
        return False

    monkeypatch.setattr(health_module, "_check_database_quick", _db_quick_down)
    resp = client.get("/health/quick")
    assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = resp.json()
    assert body["message"]["status"] == "not_ready"
    assert body["message"]["checks"]["database"] is False


def test_quick_200_when_db_and_model_ready(client, tmp_path, monkeypatch):
    _install_ready_manager(tmp_path, monkeypatch)
    resp = client.get("/health/quick")
    assert resp.status_code == status.HTTP_200_OK
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"] is True
    assert body["checks"]["model"] is True


# ---------------------------------------------------------------------------
# TEST I (required) — checksum-matching but unloadable artifact NEVER 200;
# only a matching load signal flips readiness to 200
# ---------------------------------------------------------------------------


def test_verified_but_not_loaded_503_until_load_signal(client, tmp_path, monkeypatch):
    """HTTP semantics of ARTIFACT VERIFIED != SERVICE READY."""
    artifact_dir = tmp_path / "model_zoo" / "production"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "v26.7_aligned_production.pkl").write_bytes(CORRUPT_PICKLE_BYTES)
    manifest_path = _write_manifest(
        tmp_path, [_api_entry(_sha256_hex(CORRUPT_PICKLE_BYTES)), _cli_entry()]
    )
    manager = ReadinessManager(manifest_path)
    # artifact VERIFIED by hash (never deserialized) but no load signal
    assert manager.snapshot()["artifact_verified"] is True
    monkeypatch.setattr(health_module, "_readiness_manager", manager)

    for endpoint in ("/health/readiness", "/health/quick"):
        resp = client.get(endpoint)
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    # the load signal is what flips service readiness to 200
    assert manager.mark_model_loaded("v26_7_aligned", _sha256_hex(CORRUPT_PICKLE_BYTES)) is True
    for endpoint in ("/health/readiness", "/health/quick"):
        resp = client.get(endpoint)
        assert resp.status_code == status.HTTP_200_OK


def test_health_full_exposes_integrity_vs_loaded_distinction(client, tmp_path, monkeypatch):
    """The informational /health body shows artifact integrity separately
    from the load signal — never conflates the two."""
    artifact_dir = tmp_path / "model_zoo" / "production"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "v26.7_aligned_production.pkl").write_bytes(ARTIFACT_CONTENT)
    manifest_path = _write_manifest(
        tmp_path, [_api_entry(_sha256_hex(ARTIFACT_CONTENT)), _cli_entry()]
    )
    manager = ReadinessManager(manifest_path)
    monkeypatch.setattr(health_module, "_readiness_manager", manager)

    resp = client.get("/health")
    assert resp.status_code == status.HTTP_200_OK
    model = resp.json()["checks"]["model"]
    assert model["details"]["artifact_integrity"] == "verified"
    assert model["details"]["model_loaded"] is False
    assert model["status"] == "unhealthy"

    assert manager.mark_model_loaded("v26_7_aligned", _sha256_hex(ARTIFACT_CONTENT)) is True
    resp = client.get("/health")
    assert resp.json()["checks"]["model"]["details"]["model_loaded"] is True
    assert resp.json()["checks"]["model"]["status"] == "healthy"


# ---------------------------------------------------------------------------
# 503 bodies: useful, no absolute paths / credentials / traces
# ---------------------------------------------------------------------------


def test_not_ready_bodies_do_not_leak_paths_or_traces(client, tmp_path, monkeypatch):
    _install_not_ready_manager(tmp_path, monkeypatch)

    for endpoint in ("/health/readiness", "/health/quick"):
        resp = client.get(endpoint)
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        text = resp.text
        assert "Traceback" not in text
        assert "/home/" not in text
        assert "tmp/" not in text  # no tmp_path leakage
        assert "password" not in text.lower()
        assert "secret" not in text.lower()

    # DB-down bodies must also stay leak-free (F7 Codex extension)
    async def _db_async_down():
        return {"healthy": False, "message": "数据库连接失败", "response_time_ms": 1.0}

    async def _db_quick_down():
        return False

    monkeypatch.setattr(health_module, "_check_database_async", _db_async_down)
    monkeypatch.setattr(health_module, "_check_database_quick", _db_quick_down)
    for endpoint in ("/health/readiness", "/health/quick"):
        resp = client.get(endpoint)
        assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        text = resp.text
        assert "Traceback" not in text
        assert "/home/" not in text
        assert "password" not in text.lower()
        assert "secret" not in text.lower()


# ---------------------------------------------------------------------------
# cached model readiness: health requests never re-hash the artifact
# ---------------------------------------------------------------------------


def test_health_requests_do_not_rehash_artifact(client, tmp_path, monkeypatch):
    manager = _install_ready_manager(tmp_path, monkeypatch)
    manager.refresh()  # explicit one-time verification before probes

    hashes = []
    original = ArtifactManifest.compute_sha256

    def counting_sha256(self, path):
        hashes.append(str(path))
        return original(self, path)

    monkeypatch.setattr(ArtifactManifest, "compute_sha256", counting_sha256)

    for _ in range(3):
        assert client.get("/health/quick").status_code == status.HTTP_200_OK
        assert client.get("/health/readiness").status_code == status.HTTP_200_OK

    assert hashes == []  # cached state; zero hashing during health requests
