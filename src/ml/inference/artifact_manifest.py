"""Canonical model artifact manifest + verification core (PR-1).

lifecycle: permanent

Single source of truth for model artifact identity and integrity:

- Git-tracked manifest (``config/model_artifacts.json`` lineage) holds the
  authoritative whole-file checksum: ``checksum_sha256 = SHA256(complete
  artifact file bytes)`` (MANIFEST_ONLY — the artifact envelope carries no
  duplicate checksum).
- Declared status model: ``pending`` (never production-ready; checksum may be
  null) vs ``active`` (checksum required; file must exist and match).
- Verification order: manifest -> safe path resolution (approved roots, no
  escape) -> file exists -> whole-file SHA256 -> manifest checksum match ->
  verified state.
- API readiness depends ONLY on artifacts marked ``required_for="api"``; a
  pending/missing CLI-only artifact must not poison API readiness.
- Process-local cached readiness: full-file hashing happens on explicit
  initialization/refresh only, never per health request. Each Uvicorn worker
  holds its own manager (no shared/global state).

HARD BOUNDARY: this module MUST NOT deserialize artifacts. It never calls
``joblib.load``/``pickle.load``, imports XGBoost, trains, predicts, writes
artifact files, edits the manifest, queries the DB, or creates
``model_zoo/``/``models/``. Deserialization of the verified artifact belongs
to the canonical loader integration (future PR).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import logging
from pathlib import Path
import threading
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = Path("config/model_artifacts.json")

# Declared artifact states (minimal, explicit; no large state machine).
STATUS_PENDING = "pending"
STATUS_ACTIVE = "active"
VALID_STATUSES = frozenset({STATUS_PENDING, STATUS_ACTIVE})

# Consumer/surface identity.
REQUIRED_FOR_API = "api"
REQUIRED_FOR_CLI = "cli"

# Verification result statuses.
VERIFIED = "verified"
NOT_ACTIVE = "not_active"
FILE_MISSING = "file_missing"
CHECKSUM_MISMATCH = "checksum_mismatch"
PATH_INVALID = "path_invalid"
VERIFICATION_ERROR = "verification_error"
MANIFEST_MISSING = "manifest_missing"
MANIFEST_MALFORMED = "manifest_malformed"

# Manifest schema version this core understands (fail closed otherwise).
MANIFEST_VERSION = 2

# Accepted required_for values (strict; anything else fails closed).
VALID_REQUIRED_FOR = frozenset({REQUIRED_FOR_API, REQUIRED_FOR_CLI})

_CHUNK_SIZE = 1024 * 1024


class ManifestError(ValueError):
    """Raised when the git-tracked artifact manifest is invalid (fail closed)."""


@dataclass(frozen=True)
class ArtifactEntry:
    """One validated manifest row."""

    name: str
    path: str
    required_for: str
    status: str
    checksum_sha256: str | None
    model_type: str | None = None
    schema_version: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class ArtifactVerification:
    """Result of verifying one artifact against the manifest."""

    name: str
    status: str
    declared_status: str
    required_for: str
    reason: str = ""


@dataclass
class ReadinessState:
    """Aggregate readiness snapshot (process-local, cached)."""

    api_ready: bool
    api_reason: str
    verified_at: str | None
    verifications: dict[str, ArtifactVerification]


class ArtifactManifest:
    """Parse/validate the manifest and verify artifacts (read-only)."""

    def __init__(self, manifest_path: Path | None = None):
        self._manifest_path = (
            Path(manifest_path) if manifest_path is not None else DEFAULT_MANIFEST_PATH
        )

    @property
    def manifest_path(self) -> Path:
        """Absolute path to the manifest file this instance reads."""
        return self._manifest_path

    def load(self) -> dict[str, Any]:
        """Parse the manifest, failing closed on any structural problem."""
        if not self._manifest_path.exists():
            raise ManifestError("model artifact manifest missing")
        try:
            with self._manifest_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ManifestError("model artifact manifest malformed") from exc
        if not isinstance(data, dict) or not isinstance(data.get("artifacts"), list):
            raise ManifestError("model artifact manifest malformed")
        if data.get("version") != MANIFEST_VERSION:
            raise ManifestError(
                f"model artifact manifest malformed (unsupported version: {data.get('version')!r})"
            )
        return data

    def _resolve_root(self, raw: Any) -> Path:
        """Resolve one approved artifact root from a manifest field."""
        if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
            raise ManifestError("model artifact manifest malformed")
        root = Path(raw)
        if any(part == ".." for part in root.parts):
            raise ManifestError("model artifact manifest malformed")
        return (Path.cwd() / root).resolve()

    def approved_roots(self) -> list[Path]:
        """Approved artifact roots declared by the manifest (cwd-relative)."""
        data = self.load()
        return [
            self._resolve_root(data[key])
            for key in ("artifact_root", "model_zoo_root")
            if data.get(key) is not None
        ]

    def entries(self) -> list[ArtifactEntry]:
        """All manifest rows, rejecting duplicates and malformed entries."""
        data = self.load()
        seen: set[str] = set()
        entries: list[ArtifactEntry] = []
        for index, raw in enumerate(data["artifacts"], start=1):
            entry = self._parse_entry(raw, index)
            if entry.name in seen:
                raise ManifestError(f"duplicate artifact identity: {entry.name}")
            seen.add(entry.name)
            entries.append(entry)
        return entries

    def _parse_entry(self, raw: Any, index: int) -> ArtifactEntry:
        if not isinstance(raw, dict):
            raise ManifestError(f"model artifact manifest malformed (entry #{index})")
        name = raw.get("name")
        path = raw.get("path")
        if not isinstance(name, str) or not name.strip():
            raise ManifestError(f"model artifact manifest malformed (entry #{index}: name)")
        if not isinstance(path, str) or not path.strip():
            raise ManifestError(f"model artifact manifest malformed (entry #{index}: path)")
        status = raw.get("status", STATUS_PENDING)
        if status not in VALID_STATUSES:
            raise ManifestError(f"model artifact manifest malformed (artifact {name}: status)")
        checksum = raw.get("checksum_sha256")
        if checksum is not None and not isinstance(checksum, str):
            raise ManifestError(f"model artifact manifest malformed (artifact {name}: checksum)")
        if status == STATUS_ACTIVE and not checksum:
            raise ManifestError(
                f"model artifact manifest malformed (artifact {name}: active requires checksum)"
            )
        required_for = raw.get("required_for", REQUIRED_FOR_API)
        if not isinstance(required_for, str) or required_for not in VALID_REQUIRED_FOR:
            raise ManifestError(
                f"model artifact manifest malformed (artifact {name}: required_for)"
            )
        return ArtifactEntry(
            name=name,
            path=path,
            required_for=required_for,
            status=status,
            checksum_sha256=checksum,
            model_type=raw.get("model_type"),
            schema_version=raw.get("schema_version"),
            source=raw.get("source"),
        )

    def resolve_path(self, entry_path: str) -> Path:
        """Resolve an artifact path under an approved root, rejecting escape.

        Rejects absolute paths, ``..`` traversal, and symlink escapes (the
        resolved candidate must remain inside a resolved approved root).
        """
        if not entry_path or Path(entry_path).is_absolute():
            raise ManifestError("artifact path must be relative")
        path = Path(entry_path)
        if any(part == ".." for part in path.parts):
            raise ManifestError("artifact path escapes approved root")
        candidate = (Path.cwd() / path).resolve()
        for root in self.approved_roots():
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            return candidate
        raise ManifestError("artifact path escapes approved root")

    @staticmethod
    def compute_sha256(path: Path) -> str:
        """Whole-file SHA256 (chunked; the single authoritative checksum)."""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def verify(self, entry: ArtifactEntry) -> ArtifactVerification:
        """Verify one entry: manifest -> path -> exists -> hash -> match."""
        if entry.status != STATUS_ACTIVE:
            return ArtifactVerification(
                name=entry.name,
                status=NOT_ACTIVE,
                declared_status=entry.status,
                required_for=entry.required_for,
                reason="pending artifact is not production-ready",
            )
        try:
            path = self.resolve_path(entry.path)
        except ManifestError:
            return ArtifactVerification(
                name=entry.name,
                status=PATH_INVALID,
                declared_status=entry.status,
                required_for=entry.required_for,
                reason="artifact path invalid",
            )
        if not path.exists():
            return ArtifactVerification(
                name=entry.name,
                status=FILE_MISSING,
                declared_status=entry.status,
                required_for=entry.required_for,
                reason="artifact file missing",
            )
        actual = self.compute_sha256(path)
        if entry.checksum_sha256 is None or actual != entry.checksum_sha256:
            return ArtifactVerification(
                name=entry.name,
                status=CHECKSUM_MISMATCH,
                declared_status=entry.status,
                required_for=entry.required_for,
                reason="artifact checksum mismatch",
            )
        return ArtifactVerification(
            name=entry.name,
            status=VERIFIED,
            declared_status=entry.status,
            required_for=entry.required_for,
            reason="",
        )

    def evaluate(self) -> ReadinessState:
        """Evaluate manifest-level readiness (fail closed on ANY error).

        Never raises: an unreadable/malformed manifest, or any I/O error
        while verifying an artifact (unreadable file, directory path, race
        between exists() and open()), collapses to a not-ready state instead
        of surfacing HTTP 500. Per-artifact errors are contained so a broken
        CLI-only artifact can never poison API readiness.
        """
        try:
            entries = self.entries()
        except ManifestError as exc:
            # ManifestError messages are fixed strings — safe to surface.
            return ReadinessState(
                api_ready=False, api_reason=str(exc), verified_at=None, verifications={}
            )
        except Exception:  # fail-closed by contract (e.g. unreadable file)
            # str(exc) may embed absolute paths — keep it server-side only.
            logger.exception("模型产物 manifest 读取失败")
            return ReadinessState(
                api_ready=False,
                api_reason="model artifact manifest unavailable",
                verified_at=None,
                verifications={},
            )

        verifications: dict[str, ArtifactVerification] = {}
        for entry in entries:
            try:
                verifications[entry.name] = self.verify(entry)
            except Exception:  # fail-closed by contract
                logger.exception("模型产物校验异常: %s", entry.name)
                verifications[entry.name] = ArtifactVerification(
                    name=entry.name,
                    status=VERIFICATION_ERROR,
                    declared_status=entry.status,
                    required_for=entry.required_for,
                    reason="artifact verification error",
                )
        api_required = [v for v in verifications.values() if v.required_for == REQUIRED_FOR_API]
        if not api_required:
            return ReadinessState(
                api_ready=False,
                api_reason="no api model artifact configured",
                verified_at=None,
                verifications=verifications,
            )
        failing = next((v for v in api_required if v.status != VERIFIED), None)
        if failing is not None:
            return ReadinessState(
                api_ready=False,
                api_reason=f"model artifact not ready: {failing.name} ({failing.reason})",
                verified_at=None,
                verifications=verifications,
            )
        return ReadinessState(
            api_ready=True,
            api_reason="",
            verified_at=datetime.now(UTC).isoformat(),
            verifications=verifications,
        )


class ReadinessManager:
    """Process-local cached readiness.

    Full-file verification runs on lazy one-time initialization or explicit
    ``refresh()``; repeated readiness queries read the cached state only.
    """

    def __init__(self, manifest_path: Path | None = None):
        self._manifest = ArtifactManifest(manifest_path)
        self._lock = threading.Lock()
        self._state: ReadinessState | None = None

    @property
    def manifest_path(self) -> Path:
        """Manifest path backing this manager's cached state."""
        return self._manifest.manifest_path

    def initialize(self) -> ReadinessState:
        """Verify lazily; VERIFIED states are cached, failures are NOT.

        A not-ready evaluation is deliberately not cached: transient failures
        (manifest mid-replace, volume not yet mounted, operator correcting a
        checksum) self-heal on the next probe without a process restart.
        Ready states are cached so health requests never re-hash.
        """
        with self._lock:
            if self._state is None:
                state = self._manifest.evaluate()
                if state.api_ready:
                    self._state = state
                return state
            return self._state

    def refresh(self) -> ReadinessState:
        """Explicit re-verification (startup / activation / reload hook)."""
        with self._lock:
            state = self._manifest.evaluate()
            self._state = state if state.api_ready else None
            return state

    def api_ready(self) -> tuple[bool, str]:
        """Cached API-model readiness: (ready, reason). Never re-hashes."""
        state = self.initialize()
        return (state.api_ready, state.api_reason)

    def snapshot(self) -> dict[str, Any]:
        """Informational per-artifact snapshot (no filesystem paths)."""
        state = self.initialize()
        return {
            "api_ready": state.api_ready,
            "api_reason": state.api_reason,
            "verified_at": state.verified_at,
            "artifacts": {
                name: {
                    "status": verification.status,
                    "declared_status": verification.declared_status,
                    "required_for": verification.required_for,
                    "reason": verification.reason,
                }
                for name, verification in state.verifications.items()
            },
        }
