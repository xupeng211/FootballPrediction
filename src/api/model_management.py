"""Canonical read-only model observability API.

lifecycle: permanent
component: Canonical

This router reports the model state declared by the canonical artifact
manifest, the exact feature-contract binding, and the process-local readiness
state already shared by the canonical loader and health endpoints.

It deliberately has no model lifecycle mutation surface.  Artifact activation
remains a reviewed manifest change followed by startup loading; this module
never deserializes a model, discovers local files, or writes repository state.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.ml.inference.artifact_manifest import (
    REQUIRED_FOR_API,
    STATUS_PENDING,
    VERIFIED,
    ArtifactEntry,
    ArtifactManifest,
    get_process_readiness_manager,
)
from src.ml.inference.canonical_model_loader import (
    CANONICAL_API_ARTIFACT_NAME,
    CANONICAL_API_MODEL_TYPE,
)
from src.ml.inference.feature_contract_registry import (
    FeatureContract,
    FeatureContractRegistry,
    FeatureContractRegistryError,
)

logger = logging.getLogger(__name__)

_PUBLIC_UNAVAILABLE_MESSAGE = "model management state unavailable"
_SAFE_METADATA_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:+-]{0,119}")
_SAFE_TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})"
)
_SAFE_VERIFICATION_STATUSES = frozenset(
    {
        "verified",
        "not_active",
        "file_missing",
        "checksum_mismatch",
        "path_invalid",
        "verification_error",
        "manifest_missing",
        "manifest_malformed",
    }
)


class ArtifactSummary(BaseModel):
    """Safe manifest-derived identity and declared state."""

    name: str
    model_type: str | None = None
    required_for: str
    declared_status: str
    checksum_present: bool
    schema_version: str | None = None
    source: str | None = None
    verification_status: str


class FeatureContractSummary(BaseModel):
    """Safe summary of an exact registered feature-contract binding."""

    contract_id: str
    feature_contract_version: str
    feature_count: int


class RuntimeSummary(BaseModel):
    """Process-local serving status without paths or internal diagnostics."""

    artifact_verified: bool
    model_loaded: bool
    service_ready: bool
    reason: str
    verified_at: str | None = None


class ModelInfoResponse(BaseModel):
    """Canonical API model information."""

    artifact: ArtifactSummary
    feature_contract: FeatureContractSummary
    runtime: RuntimeSummary


class ModelListItem(ArtifactSummary):
    """One manifest-declared model with an optional exact contract binding."""

    feature_contract: FeatureContractSummary | None = None


class ModelListResponse(BaseModel):
    """Manifest-declared model inventory."""

    total_models: int
    models: list[ModelListItem]


# One process-local owner is deliberately shared with health and the
# canonical loader.  Tests may replace this reference with an isolated
# ReadinessManager, but production imports resolve to the singleton owner.
_readiness_manager = get_process_readiness_manager()

router = APIRouter(
    prefix="/api/v1/models",
    tags=["模型管理"],
    responses={503: {"description": "模型管理状态不可用"}},
)


class _ManagementStateError(ValueError):
    """Internal fail-closed marker for invalid canonical management state."""


def _safe_public_value(value: Any) -> str | None:
    """Return only short identifier-like metadata suitable for an HTTP body."""
    if not isinstance(value, str) or not _SAFE_METADATA_RE.fullmatch(value):
        return None
    return value


def _canonical_api_artifact(manifest: ArtifactManifest) -> ArtifactEntry:
    """Resolve the exact API identity already owned by the canonical loader."""
    entries = manifest.entries()
    matches = [entry for entry in entries if entry.name == CANONICAL_API_ARTIFACT_NAME]
    if len(matches) != 1:
        raise _ManagementStateError("canonical API artifact identity unavailable")

    artifact = matches[0]
    if artifact.required_for != REQUIRED_FOR_API or artifact.model_type != CANONICAL_API_MODEL_TYPE:
        raise _ManagementStateError("canonical API artifact binding unavailable")
    return artifact


def _exact_feature_contract(
    registry: FeatureContractRegistry, artifact: ArtifactEntry
) -> FeatureContract:
    """Resolve and re-check one exact artifact/model contract binding."""
    contract = registry.get_for_model(
        CANONICAL_API_MODEL_TYPE,
        artifact_name=CANONICAL_API_ARTIFACT_NAME,
    )
    if (
        artifact.name != contract.artifact_name
        or artifact.model_type != contract.model_type
        or contract.artifact_name != CANONICAL_API_ARTIFACT_NAME
        or contract.model_type != CANONICAL_API_MODEL_TYPE
    ):
        raise _ManagementStateError("canonical artifact and feature contract are mismatched")
    return contract


def _contract_summary(contract: FeatureContract) -> FeatureContractSummary:
    """Convert a validated registry record to its safe public shape."""
    return FeatureContractSummary(
        contract_id=contract.contract_id,
        feature_contract_version=contract.feature_contract_version,
        feature_count=contract.feature_count,
    )


def _verification_status(snapshot: dict[str, Any], artifact_name: str) -> str:
    """Read a bounded per-artifact verification label from readiness state."""
    artifacts = snapshot.get("artifacts")
    if not isinstance(artifacts, dict):
        return "not_available"
    state = artifacts.get(artifact_name)
    if not isinstance(state, dict):
        return "not_available"
    value = state.get("status")
    if isinstance(value, str) and value in _SAFE_VERIFICATION_STATUSES:
        return value
    return "not_available"


def _artifact_summary(artifact: ArtifactEntry, snapshot: dict[str, Any]) -> ArtifactSummary:
    """Build a manifest-only summary without exposing path or checksum values."""
    return ArtifactSummary(
        name=artifact.name,
        model_type=_safe_public_value(artifact.model_type),
        required_for=artifact.required_for,
        declared_status=artifact.status,
        checksum_present=artifact.checksum_sha256 is not None,
        schema_version=_safe_public_value(artifact.schema_version),
        source=_safe_public_value(artifact.source),
        verification_status=_verification_status(snapshot, artifact.name),
    )


def _list_feature_contract(
    artifact: ArtifactEntry,
    contracts: dict[tuple[str, str], FeatureContract],
) -> FeatureContract | None:
    """Return an exact list binding, requiring one for the API artifact."""
    contract = (
        contracts.get((artifact.name, artifact.model_type))
        if isinstance(artifact.model_type, str)
        else None
    )
    if artifact.required_for != REQUIRED_FOR_API:
        return contract
    if contract is None:
        raise _ManagementStateError("canonical API feature contract unavailable")
    if contract.artifact_name != artifact.name or contract.model_type != artifact.model_type:
        raise _ManagementStateError("canonical artifact and feature contract mismatch")
    return contract


def _runtime_summary(artifact: ArtifactEntry, snapshot: dict[str, Any]) -> RuntimeSummary:
    """Expose stable readiness semantics rather than internal reason text."""
    artifacts = snapshot.get("artifacts")
    artifact_state = artifacts.get(artifact.name) if isinstance(artifacts, dict) else None
    artifact_verified = isinstance(artifact_state, dict) and (
        artifact_state.get("status") == VERIFIED
    )
    model_loaded = bool(snapshot.get("model_loaded")) and artifact_verified
    service_ready = bool(snapshot.get("service_ready")) and artifact_verified

    if service_ready:
        reason = ""
    elif artifact.status == STATUS_PENDING:
        reason = "model artifact pending"
    elif not artifact_verified:
        reason = "model artifact not verified"
    elif not model_loaded:
        reason = "model artifact verified but not loaded"
    else:
        reason = "model service not ready"

    verified_at = snapshot.get("verified_at") if artifact_verified else None
    if not isinstance(verified_at, str) or not _SAFE_TIMESTAMP_RE.fullmatch(verified_at):
        verified_at = None

    return RuntimeSummary(
        artifact_verified=artifact_verified,
        model_loaded=model_loaded,
        service_ready=service_ready,
        reason=reason,
        verified_at=verified_at,
    )


def _management_unavailable() -> HTTPException:
    """Return the stable public error for malformed/unavailable canonical state."""
    return HTTPException(status_code=503, detail=_PUBLIC_UNAVAILABLE_MESSAGE)


@router.get("/info", response_model=ModelInfoResponse)
async def get_model_info() -> ModelInfoResponse:
    """Report the canonical API artifact and its read-only runtime state."""
    try:
        manifest = ArtifactManifest()
        artifact = _canonical_api_artifact(manifest)
        contract = _exact_feature_contract(FeatureContractRegistry(), artifact)
        snapshot = _readiness_manager.snapshot()
        return ModelInfoResponse(
            artifact=_artifact_summary(artifact, snapshot),
            feature_contract=_contract_summary(contract),
            runtime=_runtime_summary(artifact, snapshot),
        )
    except HTTPException:
        raise
    except (OSError, ValueError, FeatureContractRegistryError, RuntimeError):
        logger.exception("模型管理 canonical 状态读取失败")
        raise _management_unavailable() from None
    except Exception:
        logger.exception("模型管理 canonical 状态出现未预期错误")
        raise _management_unavailable() from None


@router.get("/list", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    """List only rows declared by the canonical manifest."""
    try:
        manifest = ArtifactManifest()
        entries = manifest.entries()
        registry = FeatureContractRegistry()
        contracts = {
            (contract.artifact_name, contract.model_type): contract
            for contract in registry.contracts()
        }
        snapshot = _readiness_manager.snapshot()

        models: list[ModelListItem] = []
        for artifact in entries:
            contract = _list_feature_contract(artifact, contracts)
            models.append(
                ModelListItem(
                    **_artifact_summary(artifact, snapshot).model_dump(),
                    feature_contract=(
                        _contract_summary(contract) if contract is not None else None
                    ),
                )
            )

        return ModelListResponse(total_models=len(models), models=models)
    except HTTPException:
        raise
    except (OSError, ValueError, FeatureContractRegistryError, RuntimeError):
        logger.exception("模型管理 manifest/registry 读取失败")
        raise _management_unavailable() from None
    except Exception:
        logger.exception("模型管理列表出现未预期错误")
        raise _management_unavailable() from None
