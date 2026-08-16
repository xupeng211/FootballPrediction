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
LEGACY_SUPPORTED_SCHEMA_VERSION = "model-feature-contract-registry/v1"
SUPPORTED_SCHEMA_VERSION = "model-feature-contract-registry/v2"
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SUPPORTED_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSION})
EXPECTED_LIFECYCLE = "permanent"

V1_CONTRACT_ID = "v26_7_aligned/v1"
VNEXT_CONTRACT_ID = "canonical_prematch/vnext-v1"

_V1_ROOT_FIELDS = frozenset({"schema_version", "lifecycle", "contracts"})
_V2_ROOT_FIELDS = frozenset(
    {
        "schema_version",
        "lifecycle",
        "contracts",
        "migration_map",
        "decision_boundaries",
    }
)
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
_CONTRACT_OPTIONAL_FIELDS = frozenset({"contract_role", "activation_status", "feature_statuses"})
_FEATURE_STATUS_FIELDS = frozenset(
    {
        "feature_name",
        "v_next_status",
        "semantic_definition_status",
        "historical_source_status",
        "runtime_source_status",
        "training_eligibility",
        "reason_code",
    }
)
_MIGRATION_MAP_FIELDS = frozenset({"from_contract_id", "to_contract_id", "entries"})
_MIGRATION_ENTRY_FIELDS = frozenset({"from_feature", "to_feature", "classification", "reason"})
_MIGRATION_CLASSIFICATIONS = frozenset(
    {"UNCHANGED", "REMOVED", "SEMANTICS_PENDING", "SOURCE_PENDING", "CONTRACT_PENDING"}
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
class FeatureStatus:
    """Versioned readiness metadata for one V-next feature."""

    feature_name: str
    v_next_status: str
    semantic_definition_status: str
    historical_source_status: str
    runtime_source_status: str
    training_eligibility: str
    reason_code: str


@dataclass(frozen=True)
class FeatureMigration:
    """One immutable V1-to-V-next feature migration decision."""

    from_feature: str
    to_feature: str | None
    classification: str
    reason: str


@dataclass(frozen=True)
class FeatureContract:
    """One validated contract with immutable ordered feature semantics."""

    contract_id: str
    artifact_name: str
    model_type: str
    feature_contract_version: str
    feature_count: int
    ordered_features: tuple[str, ...]
    contract_role: str = "UNSPECIFIED"
    activation_status: str = "UNSPECIFIED"
    feature_statuses: tuple[FeatureStatus, ...] = ()


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
        validated_contracts = tuple(contracts)
        if payload.get("schema_version") == SUPPORTED_SCHEMA_VERSION:
            self._validate_v2_document(payload, validated_contracts)
        return validated_contracts

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

    def migration_map(
        self,
        from_contract_id: str = V1_CONTRACT_ID,
        to_contract_id: str = VNEXT_CONTRACT_ID,
    ) -> tuple[FeatureMigration, ...]:
        """Return the validated migration map for one exact contract pair."""
        self.contracts()
        payload = self._read_payload()
        if payload.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
            raise FeatureContractRegistryError(
                "migration map requires the versioned registry schema"
            )
        raw_map = payload["migration_map"]
        if (
            raw_map["from_contract_id"] != from_contract_id
            or raw_map["to_contract_id"] != to_contract_id
        ):
            raise FeatureContractNotFoundError("feature contract migration map not found")
        return tuple(
            FeatureMigration(
                from_feature=entry["from_feature"],
                to_feature=entry["to_feature"],
                classification=entry["classification"],
                reason=entry["reason"],
            )
            for entry in raw_map["entries"]
        )

    def _read_payload(self) -> dict[str, Any]:
        try:
            payload = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FeatureContractRegistryError("feature contract registry unreadable") from exc

        if not isinstance(payload, dict):
            raise FeatureContractRegistryError("feature contract registry malformed")
        schema_version = payload.get("schema_version")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise FeatureContractRegistryError(
                "unsupported feature contract registry schema version"
            )
        expected_fields = (
            _V2_ROOT_FIELDS if schema_version == SUPPORTED_SCHEMA_VERSION else _V1_ROOT_FIELDS
        )
        if set(payload) != expected_fields:
            raise FeatureContractRegistryError("feature contract registry malformed")
        if payload.get("lifecycle") != EXPECTED_LIFECYCLE:
            raise FeatureContractRegistryError("feature contract registry lifecycle malformed")
        return payload

    @staticmethod
    def _parse_contract(raw_contract: Any, index: int) -> FeatureContract:
        if not isinstance(raw_contract, dict):
            raise FeatureContractRegistryError(f"feature contract entry #{index} malformed")
        if not _CONTRACT_FIELDS.issubset(raw_contract) or (
            set(raw_contract) - _CONTRACT_FIELDS - _CONTRACT_OPTIONAL_FIELDS
        ):
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

        ordered_features = FeatureContractRegistry._parse_ordered_features(
            raw_contract["ordered_features"], index
        )

        if feature_count != len(ordered_features):
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} feature count mismatch"
            )

        contract_role, activation_status = FeatureContractRegistry._parse_contract_metadata(
            raw_contract, index
        )
        feature_statuses = FeatureContractRegistry._parse_feature_statuses(
            raw_contract.get("feature_statuses"), index
        )
        return FeatureContract(
            contract_id=contract_id,
            artifact_name=artifact_name,
            model_type=model_type,
            feature_contract_version=feature_contract_version,
            feature_count=feature_count,
            ordered_features=tuple(ordered_features),
            contract_role=contract_role,
            activation_status=activation_status,
            feature_statuses=feature_statuses,
        )

    @staticmethod
    def _parse_ordered_features(raw_features: Any, index: int) -> tuple[str, ...]:
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
        return tuple(ordered_features)

    @staticmethod
    def _parse_contract_metadata(raw_contract: dict[str, Any], index: int) -> tuple[str, str]:
        contract_role = raw_contract.get("contract_role", "UNSPECIFIED")
        activation_status = raw_contract.get("activation_status", "UNSPECIFIED")
        if not isinstance(contract_role, str) or not contract_role:
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} contract role malformed"
            )
        if not isinstance(activation_status, str) or not activation_status:
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} activation status malformed"
            )
        return contract_role, activation_status

    @staticmethod
    def _parse_feature_statuses(raw_statuses: Any, index: int) -> tuple[FeatureStatus, ...]:
        if raw_statuses is None:
            return ()
        if not isinstance(raw_statuses, list) or not raw_statuses:
            raise FeatureContractRegistryError(
                f"feature contract entry #{index} feature statuses malformed"
            )

        statuses: list[FeatureStatus] = []
        seen_features: set[str] = set()
        for raw_status in raw_statuses:
            if not isinstance(raw_status, dict) or set(raw_status) != _FEATURE_STATUS_FIELDS:
                raise FeatureContractRegistryError(
                    f"feature contract entry #{index} feature status malformed"
                )
            values: dict[str, str] = {}
            for field in _FEATURE_STATUS_FIELDS:
                value = raw_status[field]
                if not isinstance(value, str) or not value.strip():
                    raise FeatureContractRegistryError(
                        f"feature contract entry #{index} feature status value malformed"
                    )
                values[field] = value
            feature_name = values["feature_name"]
            if not _FEATURE_NAME_RE.fullmatch(feature_name) or feature_name in seen_features:
                raise FeatureContractRegistryError(
                    f"feature contract entry #{index} feature status name malformed"
                )
            seen_features.add(feature_name)
            statuses.append(FeatureStatus(**values))
        return tuple(statuses)

    @classmethod
    def _validate_v2_document(
        cls, payload: dict[str, Any], contracts: tuple[FeatureContract, ...]
    ) -> None:
        by_id = {contract.contract_id: contract for contract in contracts}
        v1_contract = by_id.get(V1_CONTRACT_ID)
        vnext_contract = by_id.get(VNEXT_CONTRACT_ID)
        if v1_contract is None or vnext_contract is None:
            raise FeatureContractRegistryError(
                "versioned registry must contain the frozen V1 and V-next contracts"
            )
        if contracts[0].contract_id != V1_CONTRACT_ID:
            raise FeatureContractRegistryError("frozen V1 contract must remain the first entry")
        if (
            v1_contract.contract_role != "HISTORICAL_DEFAULT"
            or v1_contract.activation_status != "ACTIVE_DEFAULT"
        ):
            raise FeatureContractRegistryError("frozen V1 contract default binding malformed")
        if vnext_contract.contract_role != "VERSIONED_NEXT":
            raise FeatureContractRegistryError("V-next contract role malformed")
        if vnext_contract.activation_status == "ACTIVE_DEFAULT":
            raise FeatureContractRegistryError("V-next contract cannot be active by definition")
        if vnext_contract.activation_status != "DEFINED_NOT_ACTIVATED":
            raise FeatureContractRegistryError("V-next activation status malformed")
        if len(vnext_contract.feature_statuses) != vnext_contract.feature_count:
            raise FeatureContractRegistryError("V-next feature status matrix is incomplete")
        if tuple(status.feature_name for status in vnext_contract.feature_statuses) != (
            vnext_contract.ordered_features
        ):
            raise FeatureContractRegistryError(
                "V-next feature status order does not match contract"
            )

        cls._validate_v2_migration_map(payload, v1_contract, vnext_contract)
        cls._validate_v2_decision_boundaries(payload)

    @classmethod
    def _validate_v2_migration_map(
        cls,
        payload: dict[str, Any],
        v1_contract: FeatureContract,
        vnext_contract: FeatureContract,
    ) -> None:
        raw_map = payload.get("migration_map")
        if not isinstance(raw_map, dict) or set(raw_map) != _MIGRATION_MAP_FIELDS:
            raise FeatureContractRegistryError("feature contract migration map malformed")
        if (
            raw_map["from_contract_id"] != V1_CONTRACT_ID
            or raw_map["to_contract_id"] != VNEXT_CONTRACT_ID
        ):
            raise FeatureContractRegistryError("feature contract migration endpoints malformed")
        raw_entries = raw_map["entries"]
        if not isinstance(raw_entries, list) or len(raw_entries) != v1_contract.feature_count:
            raise FeatureContractRegistryError("feature contract migration map is incomplete")
        seen_from_features: set[str] = set()
        for entry in raw_entries:
            from_feature = cls._validate_migration_entry(
                entry, v1_contract, vnext_contract, seen_from_features
            )
            seen_from_features.add(from_feature)
        if seen_from_features != set(v1_contract.ordered_features):
            raise FeatureContractRegistryError(
                "feature contract migration source coverage malformed"
            )

    @staticmethod
    def _validate_migration_entry(
        entry: Any,
        v1_contract: FeatureContract,
        vnext_contract: FeatureContract,
        seen_from_features: set[str],
    ) -> str:
        if not isinstance(entry, dict) or set(entry) != _MIGRATION_ENTRY_FIELDS:
            raise FeatureContractRegistryError("feature contract migration entry malformed")
        from_feature = entry["from_feature"]
        to_feature = entry["to_feature"]
        classification = entry["classification"]
        reason = entry["reason"]
        if (
            not isinstance(from_feature, str)
            or from_feature not in v1_contract.ordered_features
            or from_feature in seen_from_features
        ):
            raise FeatureContractRegistryError(
                "feature contract migration source feature malformed"
            )
        if to_feature is not None and (
            not isinstance(to_feature, str) or to_feature not in vnext_contract.ordered_features
        ):
            raise FeatureContractRegistryError(
                "feature contract migration target feature malformed"
            )
        if classification not in _MIGRATION_CLASSIFICATIONS:
            raise FeatureContractRegistryError(
                "feature contract migration classification malformed"
            )
        if not isinstance(reason, str) or not reason.strip():
            raise FeatureContractRegistryError("feature contract migration reason malformed")
        if classification == "REMOVED" and to_feature is not None:
            raise FeatureContractRegistryError("removed feature migration must not have a target")
        if classification != "REMOVED" and to_feature is None:
            raise FeatureContractRegistryError("retained feature migration must have a target")
        return from_feature

    @staticmethod
    def _validate_v2_decision_boundaries(payload: dict[str, Any]) -> None:
        boundaries = payload.get("decision_boundaries")
        if not isinstance(boundaries, dict):
            raise FeatureContractRegistryError("feature contract decision boundaries malformed")
        required_boundary_names = {
            "raw_elo",
            "standings",
            "sot",
            "possession",
            "shared_engine",
            "activation",
            "legacy_proxy_policy",
        }
        if set(boundaries) != required_boundary_names:
            raise FeatureContractRegistryError("feature contract decision boundaries incomplete")

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
