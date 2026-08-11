"""Verified canonical API model loader (PR-3).

lifecycle: permanent
component: Canonical

The loader is the only production load path for the canonical
``v26_7_aligned`` API model.  It resolves the artifact from the PR-1
manifest, binds it to the PR-2 feature contract, copies and hashes the exact
bytes that will be deserialized, and records the process-local loaded signal
only after every validation step succeeds.

This module deliberately does not train, activate, or mutate artifacts.  The
manifest remains the authority for production artifact identity and status.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import logging
from numbers import Integral
import tempfile
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import joblib

from src.ml.feature_adapter import FeatureAdapterFactory, ModelType, V26_6_PreMatchAdapter
from src.ml.inference.artifact_manifest import (
    REQUIRED_FOR_API,
    STATUS_ACTIVE,
    VERIFIED,
    ArtifactEntry,
    ArtifactManifest,
    FileFingerprint,
    ReadinessManager,
    get_process_readiness_manager,
)
from src.ml.inference.feature_contract_registry import (
    FeatureContract,
    FeatureContractRegistry,
    FeatureContractRegistryError,
)

logger = logging.getLogger(__name__)

CANONICAL_API_MODEL_TYPE = "v26_7_aligned"
CANONICAL_API_ARTIFACT_NAME = "v26_7_aligned"


class ModelArtifactUnavailableError(Exception):
    """Expected fail-closed error for an unavailable canonical model."""


class _LoaderValidationError(ValueError):
    """Internal validation failure that must not cross the HTTP boundary."""


@dataclass(frozen=True)
class LoadedCanonicalModel:
    """A validated model object and the identity that authorized its load."""

    model: Any
    scaler: Any
    feature_names: tuple[str, ...]
    artifact_name: str
    artifact_path: str
    model_type: str
    checksum_sha256: str
    contract_id: str
    feature_contract_version: str

    @property
    def binding_key(self) -> tuple[Any, ...]:
        """Return the immutable identity used to invalidate a cached load."""
        return (
            self.artifact_name,
            self.artifact_path,
            self.model_type,
            self.checksum_sha256,
            self.contract_id,
            self.feature_contract_version,
            self.feature_names,
        )


@dataclass(frozen=True)
class _CanonicalBinding:
    """Manifest/registry/runtime identity resolved before deserialization."""

    artifact: ArtifactEntry
    contract: FeatureContract
    runtime_features: tuple[str, ...]

    @property
    def key(self) -> tuple[Any, ...]:
        """Return all identity fields that must remain stable during a load."""
        return (
            self.artifact.name,
            self.artifact.path,
            self.artifact.status,
            self.artifact.required_for,
            self.artifact.model_type,
            self.artifact.checksum_sha256,
            self.contract.contract_id,
            self.contract.artifact_name,
            self.contract.model_type,
            self.contract.feature_contract_version,
            self.contract.feature_count,
            self.contract.ordered_features,
            self.runtime_features,
        )

    @property
    def loaded_key(self) -> tuple[Any, ...]:
        """Return the identity retained by ``LoadedCanonicalModel``."""
        return (
            self.artifact.name,
            self.artifact.path,
            STATUS_ACTIVE,
            REQUIRED_FOR_API,
            self.artifact.model_type,
            self.artifact.checksum_sha256,
            self.contract.contract_id,
            self.contract.feature_contract_version,
            self.contract.ordered_features,
        )


class CanonicalModelLoader:
    """Load the canonical API model only after exact integrity validation."""

    def __init__(
        self,
        manifest: ArtifactManifest | None = None,
        registry: FeatureContractRegistry | None = None,
        readiness_manager: ReadinessManager | None = None,
        artifact_name: str = CANONICAL_API_ARTIFACT_NAME,
        model_type: str = CANONICAL_API_MODEL_TYPE,
    ):
        self._manifest = manifest or ArtifactManifest()
        self._registry = registry or FeatureContractRegistry()
        self._readiness = readiness_manager or get_process_readiness_manager()
        self._artifact_name = artifact_name
        self._model_type = model_type
        self._lock = threading.RLock()
        self._loaded: LoadedCanonicalModel | None = None

    @property
    def readiness_manager(self) -> ReadinessManager:
        """Return the manager whose state is published to health endpoints."""
        return self._readiness

    def load(self) -> LoadedCanonicalModel:
        """Resolve, verify, deserialize, validate, and publish one model load."""
        with self._lock:
            binding = self._resolve_binding_or_fail()
            if self._loaded is not None and self._is_cached_load_ready(binding):
                return self._loaded

            snapshot_binding = binding
            with self._verified_snapshot(binding.artifact) as snapshot:
                # The manifest and registry are re-read after snapshotting.  A
                # config change during the copy must fail before unsafe load.
                if self._resolve_binding_or_fail().key != snapshot_binding.key:
                    raise self._unavailable("canonical model identity changed during verification")

                self._refresh_verified_binding(binding)

                try:
                    loaded_data = joblib.load(snapshot)
                except Exception as exc:
                    logger.exception("canonical model deserialization failed")
                    raise self._unavailable("canonical model deserialization failed") from exc

            try:
                loaded = self._validate_loaded_model(loaded_data, binding)
            except ModelArtifactUnavailableError:
                raise
            except Exception as exc:
                logger.exception("canonical loaded-model validation failed")
                raise self._unavailable("canonical loaded-model validation failed") from exc

            # Do not publish a load signal if the manifest or registry changed
            # while joblib reconstructed the object.
            if self._resolve_binding_or_fail().key != snapshot_binding.key:
                raise self._unavailable("canonical model identity changed during load")
            self._refresh_verified_binding(binding)
            if not self._readiness.mark_model_loaded(
                binding.artifact.name, binding.artifact.checksum_sha256
            ):
                raise self._unavailable("canonical model readiness signal was refused")

            self._loaded = loaded
            return loaded

    def _is_cached_load_ready(self, binding: _CanonicalBinding) -> bool:
        """Reuse only a load whose exact identity is still service-ready."""
        if self._loaded is None or binding.loaded_key != self._binding_key_for_loaded(self._loaded):
            self._loaded = None
            return False
        ready, _ = self._readiness.service_ready()
        if not ready:
            self._loaded = None
            return False
        return True

    @staticmethod
    def _binding_key_for_loaded(loaded: LoadedCanonicalModel) -> tuple[Any, ...]:
        """Build the comparable subset of a binding identity from a load."""
        return (
            loaded.artifact_name,
            loaded.artifact_path,
            STATUS_ACTIVE,
            REQUIRED_FOR_API,
            loaded.model_type,
            loaded.checksum_sha256,
            loaded.contract_id,
            loaded.feature_contract_version,
            loaded.feature_names,
        )

    def _resolve_binding_or_fail(self) -> _CanonicalBinding:
        """Resolve one exact manifest row and one exact runtime contract."""
        try:
            entries = self._manifest.entries()
            matches = [entry for entry in entries if entry.name == self._artifact_name]
            if len(matches) != 1:
                raise _LoaderValidationError("canonical artifact identity is unknown or ambiguous")
            artifact = matches[0]
            if (
                artifact.required_for != REQUIRED_FOR_API
                or artifact.status != STATUS_ACTIVE
                or artifact.checksum_sha256 is None
                or artifact.model_type != self._model_type
            ):
                raise _LoaderValidationError("canonical artifact is not active and checksum-bound")

            contract = self._registry.get_for_model(
                self._model_type, artifact_name=self._artifact_name
            )
            if (
                contract.artifact_name != artifact.name
                or contract.model_type != artifact.model_type
                or artifact.required_for != REQUIRED_FOR_API
            ):
                raise _LoaderValidationError(
                    "canonical artifact and feature contract are mismatched"
                )

            runtime_adapter = FeatureAdapterFactory.get_adapter(ModelType.V26_6_PRE_MATCH)
            if type(runtime_adapter) is not V26_6_PreMatchAdapter:
                raise _LoaderValidationError("canonical runtime adapter binding is unexpected")
            runtime_features = tuple(runtime_adapter.get_required_features())
            if (
                contract.feature_count != len(runtime_features)
                or contract.ordered_features != runtime_features
            ):
                raise _LoaderValidationError(
                    "canonical feature contract does not match runtime adapter"
                )
            return _CanonicalBinding(artifact, contract, runtime_features)
        except (OSError, ValueError, FeatureContractRegistryError) as exc:
            self._clear_stale_readiness()
            if isinstance(exc, ModelArtifactUnavailableError):
                raise
            raise self._unavailable("canonical model binding is unavailable") from exc

    def _clear_stale_readiness(self) -> None:
        """Force a full readiness re-evaluation after a binding failure."""
        try:
            self._readiness.invalidate()
            self._readiness.refresh()
        except Exception:
            logger.exception("canonical readiness refresh failed")

    def _refresh_verified_binding(self, binding: _CanonicalBinding) -> None:
        """Require the current manifest bytes to still verify this binding."""
        readiness_state = self._readiness.refresh()
        verification = readiness_state.verifications.get(self._artifact_name)
        if (
            not readiness_state.artifact_verified
            or verification is None
            or verification.status != VERIFIED
            or verification.declared_checksum != binding.artifact.checksum_sha256
        ):
            raise self._unavailable("canonical artifact is not verified")

    @contextmanager
    def _verified_snapshot(self, artifact: ArtifactEntry) -> Iterator[Any]:
        """Yield exactly the bytes whose digest matched the manifest checksum.

        ``joblib.load`` receives this temporary file object, never the source
        pathname.  Therefore a replacement after hashing cannot cause a
        different pathname target to be deserialized.  Source fingerprints
        additionally reject a replacement during the copy itself.
        """
        try:
            path = self._manifest.resolve_path(artifact.path)
            fingerprint_before = FileFingerprint.of(path)
            digest = sha256()
            with path.open("rb") as source, tempfile.TemporaryFile(mode="w+b") as snapshot:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                    snapshot.write(chunk)
                snapshot.flush()
                fingerprint_after = FileFingerprint.of(path)
                if fingerprint_after != fingerprint_before:
                    raise _LoaderValidationError("artifact changed during verified snapshot")
                if (
                    artifact.checksum_sha256 is None
                    or digest.hexdigest() != artifact.checksum_sha256
                ):
                    raise _LoaderValidationError("artifact checksum mismatch")
                snapshot.seek(0)
                yield snapshot
        except (OSError, ValueError) as exc:
            raise self._unavailable("canonical artifact integrity verification failed") from exc

    def _validate_loaded_model(
        self, model_data: Any, binding: _CanonicalBinding
    ) -> LoadedCanonicalModel:
        """Validate the stable model envelope and evidence-backed metadata."""
        model, scaler, feature_names = self._extract_model_payload(model_data, binding)
        self._validate_model_interfaces(model, scaler)
        feature_names = self._validate_model_metadata(model, feature_names, binding)

        return LoadedCanonicalModel(
            model=model,
            scaler=scaler,
            feature_names=feature_names or binding.contract.ordered_features,
            artifact_name=binding.artifact.name,
            artifact_path=binding.artifact.path,
            model_type=binding.artifact.model_type or self._model_type,
            checksum_sha256=binding.artifact.checksum_sha256 or "",
            contract_id=binding.contract.contract_id,
            feature_contract_version=binding.contract.feature_contract_version,
        )

    def _extract_model_payload(
        self, model_data: Any, binding: _CanonicalBinding
    ) -> tuple[Any, Any, tuple[str, ...]]:
        """Extract the existing bare-model or saved-envelope formats."""
        if not isinstance(model_data, dict):
            return model_data, None, ()

        model = model_data.get("model")
        scaler = model_data.get("scaler")
        declared_model_type = model_data.get("model_type")
        if declared_model_type is not None and declared_model_type != self._model_type:
            raise self._unavailable("loaded model identity mismatch")

        declared_features = model_data.get("feature_columns")
        if not declared_features:
            return model, scaler, ()
        if not isinstance(declared_features, (list, tuple)) or not all(
            isinstance(feature, str) for feature in declared_features
        ):
            raise self._unavailable("loaded model feature metadata malformed")
        feature_names = tuple(declared_features)
        if feature_names != binding.contract.ordered_features:
            raise self._unavailable("loaded model feature order mismatch")
        return model, scaler, feature_names

    def _validate_model_interfaces(self, model: Any, scaler: Any) -> None:
        """Validate only interfaces used by the current canonical predictor."""
        if model is None or not callable(getattr(model, "predict", None)):
            raise self._unavailable("loaded model prediction interface unavailable")
        if not callable(getattr(model, "predict_proba", None)):
            raise self._unavailable("loaded model probability interface unavailable")
        if scaler is not None and not callable(getattr(scaler, "transform", None)):
            raise self._unavailable("loaded model scaler interface unavailable")

    def _validate_model_metadata(
        self,
        model: Any,
        feature_names: tuple[str, ...],
        binding: _CanonicalBinding,
    ) -> tuple[str, ...]:
        """Validate stable count/name metadata when the loaded model exposes it."""
        n_features = getattr(model, "n_features_in_", None)
        if n_features is not None:
            if isinstance(n_features, bool) or not isinstance(n_features, Integral):
                raise self._unavailable("loaded model feature count metadata malformed")
            if int(n_features) != binding.contract.feature_count:
                raise self._unavailable("loaded model feature count mismatch")

        model_feature_names = getattr(model, "feature_names_in_", None)
        if model_feature_names is None:
            return feature_names or binding.contract.ordered_features
        try:
            model_feature_names_tuple = tuple(model_feature_names)
        except TypeError as exc:
            raise self._unavailable("loaded model feature metadata malformed") from exc
        if model_feature_names_tuple != binding.contract.ordered_features:
            raise self._unavailable("loaded model feature order mismatch")
        return feature_names or model_feature_names_tuple

    def _unavailable(self, reason: str) -> ModelArtifactUnavailableError:
        """Create the sanitized public error while retaining server diagnostics."""
        logger.warning("canonical model unavailable (%s): %s", self._model_type, reason)
        return ModelArtifactUnavailableError(f"canonical model unavailable: {self._model_type}")


_PROCESS_LOADER_HOLDER: dict[str, CanonicalModelLoader | None] = {"loader": None}
_PROCESS_LOADER_LOCK = threading.Lock()


def get_canonical_model_loader() -> CanonicalModelLoader:
    """Return the one canonical loader/readiness owner for this process."""
    with _PROCESS_LOADER_LOCK:
        loader = _PROCESS_LOADER_HOLDER["loader"]
        if loader is None:
            loader = CanonicalModelLoader(readiness_manager=get_process_readiness_manager())
            _PROCESS_LOADER_HOLDER["loader"] = loader
        return loader
