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
  ARTIFACT VERIFIED.

TWO-LAYER READINESS (integrity != serving):

- ``artifact_verified`` is an integrity/storage property: manifest valid +
  row active + path approved + file exists + whole-file SHA256 matches. It
  says NOTHING about whether the model can serve.
- ``service_ready`` is a serving property: the required artifact is verified
  AND a process-local loaded-model signal (``mark_model_loaded`` — the PR-3
  loader hook) matches the verified identity AND the cheap stat fingerprint
  of the verified file is unchanged. A checksum-matching but unloadable or
  corrupt artifact can NEVER make service readiness true by hash alone.

CHEAP INVARIANTS (no per-request hashing): at verification time the manager
captures a stat()-based fingerprint (st_dev/st_ino/st_size/st_mtime_ns).
Health requests re-check it with one stat() per verified file; deletion,
atomic replacement (inode change), or size/mtime modification invalidates
service readiness immediately, without any SHA256. The fingerprint is NOT a
cryptographic integrity proof — after any mismatch, full whole-file
verification is required again before readiness can return.

- API readiness depends ONLY on artifacts marked ``required_for="api"``; a
  pending/missing CLI-only artifact must not poison API readiness.
- Process-local cached readiness: full-file hashing happens on explicit
  initialization/refresh only, never per health request. Each Uvicorn worker
  holds its own manager (no shared/global state).

HARD BOUNDARY: this module MUST NOT deserialize artifacts. It never calls
``joblib.load``/``pickle.load``, imports XGBoost, trains, predicts, writes
artifact files, edits the manifest, queries the DB, or creates
``model_zoo/``/``models/``. Deserialization of the verified artifact belongs
to the canonical loader integration (future PR). ``mark_model_loaded`` is
the minimal process-local hook that future PR will call AFTER a real load;
PR-1 never invokes it itself.
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

# Not-ready states are negative-cached for a short window so a failing probe
# never re-hashes an artifact file on every request (bounds the worst case to
# once per window, matching the Docker healthcheck interval).
NEGATIVE_CACHE_TTL_SECONDS = 30.0


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
class FileFingerprint:
    """Cheap stat-based fingerprint of a verified artifact file.

    Captured once at whole-file verification time, re-checked with a single
    ``stat()`` on health requests. Detects deletion, atomic replacement
    (inode change), and size/mtime modification. This is NOT a cryptographic
    integrity proof — it only proves the file is still the file we verified;
    full SHA256 re-verification is required after any mismatch.
    """

    st_dev: int
    st_ino: int
    st_size: int
    st_mtime_ns: int

    @classmethod
    def of(cls, path: Path) -> FileFingerprint:
        """Capture the fingerprint of ``path`` (one stat, no hashing)."""
        stat = path.stat()
        return cls(
            st_dev=stat.st_dev,
            st_ino=stat.st_ino,
            st_size=stat.st_size,
            st_mtime_ns=stat.st_mtime_ns,
        )

    def matches(self, path: Path) -> bool:
        """True iff ``path.stat()`` still equals this fingerprint (no hash)."""
        try:
            return self == FileFingerprint.of(path)
        except OSError:
            return False


@dataclass(frozen=True)
class LoadedModelIdentity:
    """Process-local record of a successful model load (PR-3 producer).

    PR-1 never creates this itself: ``mark_model_loaded`` is the minimal
    hook the future canonical loader integration (PR-3) will call AFTER a
    real load. The signal is bound to the artifact identity AND the
    filesystem fingerprint that were verified at load time, so an artifact
    replaced or re-verified after loading invalidates the stale signal
    instead of leaving readiness permanently green.
    """

    artifact_name: str
    checksum_sha256: str | None
    fingerprint: FileFingerprint | None = None


@dataclass(frozen=True)
class ArtifactVerification:
    """Result of verifying one artifact against the manifest."""

    name: str
    status: str
    declared_status: str
    required_for: str
    reason: str = ""
    declared_checksum: str | None = None
    # Internal bookkeeping for the cheap per-request invariant (never
    # exposed through snapshot()/HTTP bodies).
    resolved_path: Path | None = None
    fingerprint: FileFingerprint | None = None


@dataclass
class ReadinessState:
    """Aggregate readiness snapshot (process-local, cached).

    ``artifact_verified``: integrity/storage property — manifest valid, row
        active, path approved, file exists, whole-file SHA256 matches.
    ``service_ready``: serving property — the required artifact is verified
        AND a matching process-local loaded-model signal exists AND the
        cheap fingerprint of the verified file is unchanged.
    """

    artifact_verified: bool
    service_ready: bool
    reason: str
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
        # The fingerprint anchors the cheap per-request invariant to the file
        # that was actually hashed. A stat race (file replaced between hash
        # and stat) yields fingerprint=None -> the manager conservatively
        # treats the artifact as not service-ready until the next verify.
        try:
            fingerprint = FileFingerprint.of(path)
        except OSError:
            fingerprint = None
        return ArtifactVerification(
            name=entry.name,
            status=VERIFIED,
            declared_status=entry.status,
            required_for=entry.required_for,
            reason="",
            declared_checksum=entry.checksum_sha256,
            resolved_path=path,
            fingerprint=fingerprint,
        )

    def evaluate(self) -> ReadinessState:
        """Evaluate ARTIFACT verification only (fail closed on ANY error).

        Never raises: an unreadable/malformed manifest, or any I/O error
        while verifying an artifact (unreadable file, directory path, race
        between exists() and open()), collapses to a not-verified state
        instead of surfacing HTTP 500. Per-artifact errors are contained so
        a broken CLI-only artifact can never poison API readiness.

        ``service_ready`` is always False here: the manifest layer has no
        knowledge of model loading. The ``ReadinessManager`` composes
        service readiness from this result + the loaded-model signal.
        """
        try:
            entries = self.entries()
        except ManifestError as exc:
            # ManifestError messages are fixed strings — safe to surface.
            return ReadinessState(
                artifact_verified=False,
                service_ready=False,
                reason=str(exc),
                verified_at=None,
                verifications={},
            )
        except Exception:  # fail-closed by contract (e.g. unreadable file)
            # str(exc) may embed absolute paths — keep it server-side only.
            logger.exception("模型产物 manifest 读取失败")
            return ReadinessState(
                artifact_verified=False,
                service_ready=False,
                reason="model artifact manifest unavailable",
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
                artifact_verified=False,
                service_ready=False,
                reason="no api model artifact configured",
                verified_at=None,
                verifications=verifications,
            )
        failing = next((v for v in api_required if v.status != VERIFIED), None)
        if failing is not None:
            return ReadinessState(
                artifact_verified=False,
                service_ready=False,
                reason=f"model artifact not ready: {failing.name} ({failing.reason})",
                verified_at=None,
                verifications=verifications,
            )
        return ReadinessState(
            artifact_verified=True,
            service_ready=False,
            reason="",
            verified_at=datetime.now(UTC).isoformat(),
            verifications=verifications,
        )


class ReadinessManager:
    """Process-local cached readiness (two-layer: verified vs serving).

    Full-file verification runs on lazy one-time initialization or explicit
    ``refresh()``; repeated readiness queries check only cheap stat
    fingerprints of the verified files (never re-hashing).

    Service readiness = artifact verified AND a matching loaded-model signal
    (``mark_model_loaded``, PR-3 hook) AND unchanged fingerprints. If a
    verified file is deleted/replaced/modified after verification, the next
    query fails the cheap invariant, invalidates the cached verified state
    AND the loaded signal, and reports not-ready immediately — the artifact
    can never leave readiness permanently green.
    """

    def __init__(
        self,
        manifest_path: Path | None = None,
        negative_cache_ttl: float = NEGATIVE_CACHE_TTL_SECONDS,
    ):
        self._manifest = ArtifactManifest(manifest_path)
        self._lock = threading.Lock()
        self._state: ReadinessState | None = None
        self._negative_state: ReadinessState | None = None
        self._negative_until: float = 0.0
        self._negative_cache_ttl = negative_cache_ttl
        self._loaded_identity: LoadedModelIdentity | None = None

    @property
    def manifest_path(self) -> Path:
        """Manifest path backing this manager's cached state."""
        return self._manifest.manifest_path

    def _cheap_invariants_hold(self, state: ReadinessState) -> bool:
        """One stat() per verified API artifact — no hashing on this path.

        A verified artifact whose file no longer matches its verification
        fingerprint (deleted, atomically replaced, size/mtime modified)
        fails the invariant. Missing fingerprint bookkeeping is treated
        conservatively as "cannot confirm" (not-ready).
        """
        for verification in state.verifications.values():
            if verification.status != VERIFIED or verification.required_for != REQUIRED_FOR_API:
                continue
            if verification.resolved_path is None or verification.fingerprint is None:
                return False
            if not verification.fingerprint.matches(verification.resolved_path):
                return False
        return True

    def _invalidate_locked(self) -> ReadinessState:
        """Cheap invariant failed: the verified file changed after verification.

        Returns an immediately-not-ready state, drops the cached verified
        state and the loaded-model signal, and negative-caches the change so
        probes do not re-verify (or re-hash) until the TTL window expires —
        full verification is then required again before readiness returns.
        """
        state = ReadinessState(
            artifact_verified=False,
            service_ready=False,
            reason="artifact file changed after verification",
            verified_at=None,
            verifications={},
        )
        self._state = None
        self._loaded_identity = None
        self._negative_state = state
        self._negative_until = datetime.now(UTC).timestamp() + self._negative_cache_ttl
        return state

    def _loaded_matches_current(self, state: ReadinessState) -> bool:
        """True iff the loaded signal is bound to the currently verified file."""
        loaded = self._loaded_identity
        if loaded is None:
            return True
        verified = next(
            (
                v
                for v in state.verifications.values()
                if v.required_for == REQUIRED_FOR_API
                and v.status == VERIFIED
                and v.name == loaded.artifact_name
            ),
            None,
        )
        return (
            verified is not None
            and verified.fingerprint is not None
            and loaded.fingerprint is not None
            and verified.fingerprint == loaded.fingerprint
        )

    def _service_state(self, state: ReadinessState) -> ReadinessState:
        """Compose service readiness from artifact verification + load signal.

        Pure: never mutates manager state. A stale loaded signal (fingerprint
        no longer equal to the verified file's) does NOT grant readiness.
        """
        if not state.artifact_verified:
            return state
        loaded = self._loaded_identity
        if loaded is None:
            return ReadinessState(
                artifact_verified=True,
                service_ready=False,
                reason="model artifact verified but not loaded (no process-local load signal)",
                verified_at=state.verified_at,
                verifications=state.verifications,
            )
        verified = next(
            (
                v
                for v in state.verifications.values()
                if v.required_for == REQUIRED_FOR_API
                and v.status == VERIFIED
                and v.name == loaded.artifact_name
            ),
            None,
        )
        if (
            verified is None
            or verified.fingerprint is None
            or loaded.fingerprint is None
            or verified.fingerprint != loaded.fingerprint
        ):
            return ReadinessState(
                artifact_verified=True,
                service_ready=False,
                reason="model artifact verified but load signal is stale (artifact identity changed)",
                verified_at=state.verified_at,
                verifications=state.verifications,
            )
        return ReadinessState(
            artifact_verified=True,
            service_ready=True,
            reason="",
            verified_at=state.verified_at,
            verifications=state.verifications,
        )

    def _initialize_locked(self) -> ReadinessState:
        """Lock-free core of initialize() (caller holds the lock)."""
        if self._state is not None:
            if self._state.artifact_verified and not self._cheap_invariants_hold(self._state):
                return self._invalidate_locked()
            return self._service_state(self._state)
        now = datetime.now(UTC).timestamp()
        if now < self._negative_until and self._negative_state is not None:
            return self._negative_state
        state = self._manifest.evaluate()
        if state.artifact_verified:
            self._state = state
        else:
            self._negative_state = state
            self._negative_until = now + self._negative_cache_ttl
        return self._service_state(state)

    def initialize(self) -> ReadinessState:
        """Verify lazily; VERIFIED states are cached, failures negative-cached.

        Verified states are cached indefinitely and re-checked per request
        via cheap stat fingerprints only (never re-hashed). Not-ready states
        are negative-cached for a short TTL (default 30s): transient failures
        (manifest mid-replace, volume not yet mounted, an operator correcting
        a checksum) self-heal after the window without a process restart, and
        a failing probe never re-hashes an artifact file on every request.
        """
        with self._lock:
            return self._initialize_locked()

    def refresh(self) -> ReadinessState:
        """Explicit full re-verification (startup / activation / reload hook).

        Re-hashes every active artifact. A verification with a different
        fingerprint clears the stale loaded-model signal: re-verification
        alone MUST NOT resurrect a load recorded for a different file — a
        new matching ``mark_model_loaded`` is required before readiness
        returns.
        """
        with self._lock:
            state = self._manifest.evaluate()
            if state.artifact_verified:
                self._state = state
                self._negative_state = None
                self._negative_until = 0.0
                if not self._loaded_matches_current(state):
                    self._loaded_identity = None
            else:
                self._state = None
                self._loaded_identity = None
                self._negative_state = state
                self._negative_until = datetime.now(UTC).timestamp() + self._negative_cache_ttl
            return self._service_state(state)

    def service_ready(self) -> tuple[bool, str]:
        """Cached SERVICE readiness: (ready, reason). Never re-hashes.

        Ready means: required artifact verified AND matching loaded-model
        signal AND unchanged cheap fingerprint. Checksum matching alone is
        never enough — a corrupt-but-checksum-matching artifact stays
        not-ready until a real load signal is recorded.
        """
        state = self.initialize()
        return (state.service_ready, state.reason)

    def mark_model_loaded(self, artifact_name: str, checksum_sha256: str | None = None) -> bool:
        """Record a successful process-local model load (PR-3 hook, fail closed).

        Binds the load signal to the CURRENTLY VERIFIED artifact identity and
        filesystem fingerprint. Returns False (recording nothing) when the
        artifact is not verified or the identity does not match — a load
        signal without a matching verified artifact must never create
        service readiness. When a checksum is supplied it must equal the
        verified artifact's manifest checksum. PR-1 never calls this itself.
        """
        with self._lock:
            state = self._initialize_locked()
            verified = next(
                (
                    v
                    for v in state.verifications.values()
                    if v.required_for == REQUIRED_FOR_API
                    and v.status == VERIFIED
                    and v.name == artifact_name
                ),
                None,
            )
            if verified is None or verified.fingerprint is None:
                logger.warning(
                    "mark_model_loaded refused: artifact %s is not verified", artifact_name
                )
                return False
            if checksum_sha256 is not None and verified.declared_checksum != checksum_sha256:
                logger.warning(
                    "mark_model_loaded refused: checksum identity mismatch for %s",
                    artifact_name,
                )
                return False
            self._loaded_identity = LoadedModelIdentity(
                artifact_name=artifact_name,
                checksum_sha256=checksum_sha256,
                fingerprint=verified.fingerprint,
            )
            return True

    def snapshot(self) -> dict[str, Any]:
        """Informational per-artifact snapshot (no filesystem paths)."""
        state = self.initialize()
        return {
            "artifact_verified": state.artifact_verified,
            "service_ready": state.service_ready,
            "model_loaded": self._loaded_identity is not None,
            "reason": state.reason,
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
