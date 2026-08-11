"""Versioned canonical inference feature-contract registry.

lifecycle: permanent
component: Specialized / Internal (PR-2 registry reader; not a serving entrypoint)

This module reads the git-tracked registry without loading a model, touching a
database, or discovering features dynamically.  The ordered feature declaration
is intentionally separate from the current adapter declaration so a drift test
can detect an unsynchronized change before a future loader consumes the
contract.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "model_feature_contracts.json"
)
SUPPORTED_SCHEMA_VERSION = "model-feature-contract-registry/v1"
EXPECTED_LIFECYCLE = "permanent"

_ROOT_FIELDS = frozenset({"schema_version", "lifecycle", "contracts"})
_CONTRACT_FIELDS = frozenset(
    {
        "contract_id",
        "artifact_name",
        "model_type",
        "feature_contract_version",
        "feature_count",
        "ordered_features",
    }
)
_IDENTIFIER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-/]*")
_FEATURE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_]*")


class FeatureContractRegistryError(ValueError):
    """Raised when the versioned feature-contract registry is invalid."""


class FeatureContractNotFoundError(FeatureContractRegistryError):
    """Raised when an exact contract or model binding is not registered."""


class FeatureContractAmbiguousError(FeatureContractRegistryError):
    """Raised when a model lookup would select more than one contract."""


@dataclass(frozen=True)
class FeatureContract:
    """One validated contract with immutable ordered feature semantics."""

    contract_id: str
    artifact_name: str
    model_type: str
    feature_contract_version: str
    feature_count: int
    ordered_features: tuple[str, ...]


class FeatureContractRegistry:
    """Read and validate the canonical feature-contract registry."""

    def __init__(self, registry_path: str | Path | None = None):
        self._registry_path = (
            Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH
        )

    @property
    def registry_path(self) -> Path:
        """Return the configured registry path without writing to it."""
        return self._registry_path

    def contracts(self) -> tuple[FeatureContract, ...]:
        """Load every contract and fail closed on any schema violation."""
        payload = self._read_payload()
        raw_contracts = payload.get("contracts")
        if not isinstance(raw_contracts, list) or not raw_contracts:
            raise FeatureContractRegistryError("feature contract registry contracts malformed")

        contracts: list[FeatureContract] = []
        seen_contract_ids: set[str] = set()
        seen_bindings: set[tuple[str, str]] = set()
        for index, raw_contract in enumerate(raw_contracts, start=1):
            contract = self._parse_contract(raw_contract, index)
            if contract.contract_id in seen_contract_ids:
                raise FeatureContractRegistryError("duplicate feature contract id")
            binding = (contract.artifact_name, contract.model_type)
            if binding in seen_bindings:
                raise FeatureContractRegistryError("duplicate feature contract model binding")
            seen_contract_ids.add(contract.contract_id)
            seen_bindings.add(binding)
            contracts.append(contract)
        return tuple(contracts)

    def get_by_contract_id(self, contract_id: str) -> FeatureContract:
        """Return the exact contract ID or fail closed; never choose a fallback."""
        for contract in self.contracts():
            if contract.contract_id == contract_id:
                return contract
        raise FeatureContractNotFoundError("feature contract id not found")

    def get_for_model(self, model_type: str, artifact_name: str | None = None) -> FeatureContract:
        """Return an exact model binding or fail closed on unknown/ambiguous input."""
        if not isinstance(model_type, str) or not model_type:
            raise FeatureContractNotFoundError("feature contract model binding not found")
        if artifact_name is not None and (not isinstance(artifact_name, str) or not artifact_name):
            raise FeatureContractNotFoundError("feature contract artifact binding not found")

        matches = [
            contract
            for contract in self.contracts()
            if contract.model_type == model_type
            and (artifact_name is None or contract.artifact_name == artifact_name)
        ]
        if not matches:
            raise FeatureContractNotFoundError("feature contract model binding not found")
        if len(matches) > 1:
            raise FeatureContractAmbiguousError("feature contract model binding is ambiguous")
        return matches[0]

    def _read_payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FeatureContractRegistryError("feature contract registry unreadable") from exc

        if not isinstance(payload, dict) or set(payload) != _ROOT_FIELDS:
            raise FeatureContractRegistryError("feature contract registry malformed")
        if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
            raise FeatureContractRegistryError(
                "unsupported feature contract registry schema version"
            )
        if payload.get("lifecycle") != EXPECTED_LIFECYCLE:
            raise FeatureContractRegistryError("feature contract registry lifecycle malformed")
        return payload

    @staticmethod
    def _parse_contract(raw_contract: Any, index: int) -> FeatureContract:
        if not isinstance(raw_contract, dict) or set(raw_contract) != _CONTRACT_FIELDS:
            raise FeatureContractRegistryError(f"feature contract entry #{index} malformed")

        contract_id = FeatureContractRegistry._require_identifier(
            raw_contract["contract_id"], index, "id"
        )
        artifact_name = FeatureContractRegistry._require_identifier(
            raw_contract["artifact_name"], index, "artifact"
        )
        model_type = FeatureContractRegistry._require_identifier(
            raw_contract["model_type"], index, "model"
        )
        feature_contract_version = FeatureContractRegistry._require_identifier(
            raw_contract["feature_contract_version"], index, "version"
        )

        feature_count = raw_contract["feature_count"]
        if (
            isinstance(feature_count, bool)
            or not isinstance(feature_count, int)
            or feature_count <= 0
        ):
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} feature count malformed"
            )

        raw_features = raw_contract["ordered_features"]
        if not isinstance(raw_features, list) or not raw_features:
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} ordered features malformed"
            )
        ordered_features: list[str] = []
        seen_features: set[str] = set()
        for feature in raw_features:
            if (
                not isinstance(feature, str)
                or feature != feature.strip()
                or not _FEATURE_NAME_RE.fullmatch(feature)
            ):
                raise FeatureContractRegistryError(
                    f"feature contract entry #{index} feature name malformed"
                )
            if feature in seen_features:
                raise FeatureContractRegistryError(
                    f"feature contract entry #{index} duplicate feature name"
                )
            seen_features.add(feature)
            ordered_features.append(feature)

        if feature_count != len(ordered_features):
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} feature count mismatch"
            )
        return FeatureContract(
            contract_id=contract_id,
            artifact_name=artifact_name,
            model_type=model_type,
            feature_contract_version=feature_contract_version,
            feature_count=feature_count,
            ordered_features=tuple(ordered_features),
        )

    @staticmethod
    def _require_identifier(value: Any, index: int, field: str) -> str:
        if (
            not isinstance(value, str)
            or value != value.strip()
            or not _IDENTIFIER_RE.fullmatch(value)
        ):
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} {field} binding malformed"
            )
        return value


def load_feature_contract_registry(
    registry_path: str | Path | None = None,
) -> FeatureContractRegistry:
    """Create and immediately validate a read-only feature-contract registry."""
    registry = FeatureContractRegistry(registry_path)
    registry.contracts()
    return registry
