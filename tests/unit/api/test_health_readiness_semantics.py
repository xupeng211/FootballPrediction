"""PR-1 health readiness/quick HTTP semantics tests.

Contract under test:
- /health/readiness: DB ready + API model ready -> 200; model not ready -> 503;
  DB unavailable -> 503.
- /health/quick: cheap subset (DB + CACHED model readiness, no full hash on
  request); not-ready -> 503 (never a false-green 200); ready -> 200.
- 503 response bodies stay useful but expose no absolute filesystem paths,
  credentials, or raw exception traces.
- Health requests must NOT re-run whole-file SHA256 verification (cached).

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


def _install_ready_manager(tmp_path, monkeypatch) -> ReadinessManager:
    """API artifact present + checksum match -> verified/ready manager."""
    artifact_dir = tmp_path / "model_zoo" / "production"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "v26.7_aligned_production.pkl").write_bytes(ARTIFACT_CONTENT)
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "v26_7_aligned",
                "path": "model_zoo/production/v26.7_aligned_production.pkl",
                "required_for": "api",
                "status": "active",
                "checksum_sha256": _sha256_hex(ARTIFACT_CONTENT),
                "model_type": "v26_7_aligned",
            },
            {
                "name": "titan_v4466_real_combat",
                "path": "models/titan_v4466_real_combat.joblib",
                "required_for": "cli",
                "status": "pending",
                "checksum_sha256": None,
                "model_type": "titan",
            },
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is True  # CLI-only pending must not poison API
    monkeypatch.setattr(health_module, "_readiness_manager", manager)
    return manager


def _install_not_ready_manager(tmp_path, monkeypatch) -> ReadinessManager:
    """API artifact pending -> not ready manager (mirrors current repo reality)."""
    manifest_path = _write_manifest(
        tmp_path,
        [
            {
                "name": "v26_7_aligned",
                "path": "model_zoo/production/v26.7_aligned_production.pkl",
                "required_for": "api",
                "status": "pending",
                "checksum_sha256": None,
                "model_type": "v26_7_aligned",
            },
            {
                "name": "titan_v4466_real_combat",
                "path": "models/titan_v4466_real_combat.joblib",
                "required_for": "cli",
                "status": "pending",
                "checksum_sha256": None,
                "model_type": "titan",
            },
        ],
    )
    manager = ReadinessManager(manifest_path)
    assert manager.api_ready()[0] is False
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
