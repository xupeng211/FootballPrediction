"""Repository-external canonical prematch frame input adapter.

This module owns the file/receipt boundary for the canonical vnext frame.  It
deliberately imports the producer lazily so the public ``canonical_training_producer``
module remains the one training entrypoint and can re-export this adapter.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from src.ml.inference.feature_contract_registry import FeatureContractRegistry
    from src.ml.training.canonical_training_producer import ValidatedTrainingData


def _producer():
    """Resolve the producer lazily to avoid an import cycle."""
    from src.ml.training import canonical_training_producer as producer  # noqa: PLC0415

    return producer


def _read_external_file(path_value: str | Path, label: str) -> tuple[Path, bytes]:
    """Read one ordinary repository-external file without following symlinks."""
    producer = _producer()
    path = Path(path_value)
    if not path.is_absolute():
        raise producer.TrainingContractError(f"{label} path must be absolute")
    current = path
    while current != current.parent:
        if current.is_symlink():
            raise producer.TrainingContractError(f"{label} path contains a symlink")
        current = current.parent
    repository_root = Path(producer.__file__).resolve().parents[3]
    resolved = path.resolve()
    try:
        resolved.relative_to(repository_root)
    except ValueError:
        pass
    else:
        raise producer.TrainingContractError(f"{label} must be repository-external")
    try:
        before = path.stat()
        if not path.is_file() or path.is_symlink():
            raise producer.TrainingContractError(f"{label} must be an ordinary file")
        payload = path.read_bytes()
        after = path.stat()
    except OSError as exc:
        raise producer.TrainingContractError(f"{label} is unreadable") from exc
    if (
        before.st_dev,
        before.st_ino,
        before.st_size,
        before.st_mtime_ns,
    ) != (
        after.st_dev,
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise producer.TrainingContractError(f"{label} changed while being read")
    return resolved, payload


def _validate_frame_files_with_canonical_contract(artifact_path: Path, receipt_path: Path) -> None:
    """Reuse the existing JavaScript frame contract before flattening rows."""
    producer = _producer()
    repository_root = Path(producer.__file__).resolve().parents[3]
    validator = (
        "const fs = require('node:fs');"
        "const { validateFrameOutputFiles } = require("
        "'./src/infrastructure/golden_dataset/CanonicalPrematchFeatureFrameContract');"
        "try {"
        "validateFrameOutputFiles(fs.readFileSync(process.argv[1]), fs.readFileSync(process.argv[2]));"
        "} catch (error) {"
        "process.stderr.write(String(error && error.message ? error.message : error));"
        "process.exit(1);"
        "}"
    )
    try:
        result = subprocess.run(
            ["node", "-e", validator, str(artifact_path), str(receipt_path)],
            cwd=repository_root,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise producer.TrainingContractError(
            "canonical feature frame validator could not run"
        ) from exc
    if result.returncode != 0:
        reason = result.stderr.strip()[:240]
        raise producer.TrainingContractError(f"canonical feature frame contract rejected: {reason}")


def load_canonical_feature_frame(  # noqa: C901, PLR0912, PLR0915
    artifact_path: str | Path,
    receipt_path: str | Path,
    *,
    registry: FeatureContractRegistry | None = None,
) -> ValidatedTrainingData:
    """Load only eligible rows from one validated canonical frame artifact."""
    producer = _producer()
    artifact_file, artifact_bytes = _read_external_file(artifact_path, "frame artifact")
    receipt_file, receipt_bytes = _read_external_file(receipt_path, "frame receipt")
    _validate_frame_files_with_canonical_contract(artifact_file, receipt_file)
    # Re-read after the cross-language validator so a replacement between the
    # two reads cannot be silently bound to the first hash.
    artifact_file_after, artifact_bytes_after = _read_external_file(artifact_file, "frame artifact")
    receipt_file_after, receipt_bytes_after = _read_external_file(receipt_file, "frame receipt")
    if artifact_file_after != artifact_file or receipt_file_after != receipt_file:
        raise producer.TrainingContractError(
            "canonical feature frame path changed while validating"
        )
    if artifact_bytes_after != artifact_bytes or receipt_bytes_after != receipt_bytes:
        raise producer.TrainingContractError("canonical feature frame changed while validating")

    try:
        artifact = json.loads(artifact_bytes.decode("utf-8"))
        receipt = json.loads(receipt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise producer.TrainingContractError("canonical feature frame JSON is unreadable") from exc
    if not isinstance(artifact, dict) or not isinstance(receipt, dict):
        raise producer.TrainingContractError("canonical feature frame JSON is malformed")

    contract = producer.resolve_training_contract(registry)
    frame_contract = artifact.get("feature_contract")
    if not isinstance(frame_contract, dict):
        raise producer.TrainingContractError("canonical feature frame contract is missing")
    if (
        artifact.get("schema_version") != producer.FRAME_SCHEMA_VERSION
        or receipt.get("schema_version") != producer.FRAME_RECEIPT_SCHEMA_VERSION
        or frame_contract.get("contract_id") != contract.contract_id
        or frame_contract.get("feature_contract_version") != contract.feature_contract_version
        or frame_contract.get("training_feature_order") != list(contract.ordered_features)
        or frame_contract.get("training_feature_count") != contract.feature_count
    ):
        raise producer.TrainingContractError("canonical training frame contract binding is invalid")
    if artifact.get("real_training_readiness") != "READY_FOR_OFFLINE_CANDIDATE_INPUT":
        raise producer.TrainingContractError(
            "canonical feature frame is not ready for offline training input"
        )

    expected_artifact_sha = hashlib.sha256(artifact_bytes).hexdigest()
    expected_receipt_sha = hashlib.sha256(receipt_bytes).hexdigest()
    if receipt.get("artifact_sha256") != expected_artifact_sha:
        raise producer.TrainingContractError("canonical frame receipt artifact hash mismatch")
    if receipt.get("output_business_sha256") != artifact.get("business_content_sha256"):
        raise producer.TrainingContractError("canonical frame receipt business hash mismatch")
    if receipt.get("training_runs") != 0:
        raise producer.TrainingContractError(
            "canonical feature frame already contains training execution"
        )
    if any(
        receipt.get(field) != 0
        for field in ("live_fetch", "db_writes", "raw_writes", "backtest_runs", "model_activations")
    ):
        raise producer.TrainingContractError(
            "canonical feature frame side-effect boundary is invalid"
        )
    frame_rows = artifact.get("rows")
    if not isinstance(frame_rows, list) or not frame_rows:
        raise producer.TrainingContractError("canonical feature frame rows are missing")
    population = artifact.get("population_accounting")
    if not isinstance(population, dict):
        raise producer.TrainingContractError(
            "canonical feature frame population accounting is missing"
        )

    all_row_ids: list[str] = []
    eligible_row_ids: list[str] = []
    records: list[dict[str, Any]] = []
    for row in frame_rows:
        if not isinstance(row, dict) or not isinstance(row.get("canonical_match_id"), str):
            raise producer.TrainingContractError("canonical feature frame row identity is invalid")
        row_id = row["canonical_match_id"]
        all_row_ids.append(row_id)
        if row.get("training_eligibility", {}).get("status") != "ELIGIBLE":
            continue
        features = row.get("features")
        label = row.get("target_label")
        if not isinstance(features, dict) or list(features) != list(contract.ordered_features):
            raise producer.TrainingContractError("canonical feature frame feature order is invalid")
        if not isinstance(label, dict) or label.get("status") != "AVAILABLE":
            raise producer.TrainingContractError("eligible canonical row has no available label")
        if set(contract.ordered_features).intersection(label):
            raise producer.TrainingContractError("canonical feature columns overlap label fields")
        record: dict[str, Any] = {
            "match_id": row_id,
            "match_date": row.get("target_kickoff_utc"),
            "feature_as_of_utc": row.get("feature_as_of_utc"),
            # 在时间切分隔离训练分区前保持 label payload 未打开；producer
            # 只在 fit 时解析训练 labels，reserved labels 保持不透明。
            "result": label,
        }
        for feature_name in contract.ordered_features:
            line = features[feature_name]
            if not isinstance(line, dict) or line.get("availability_status") != "AVAILABLE":
                raise producer.TrainingContractError(
                    "eligible canonical row contains unavailable feature"
                )
            value = line.get("value")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not np.isfinite(value)
            ):
                raise producer.TrainingContractError(
                    "eligible canonical row contains invalid feature value"
                )
            record[feature_name] = float(value)
        records.append(record)
        eligible_row_ids.append(row_id)

    expected_eligible = population.get("training_eligible")
    expected_ineligible = population.get("training_ineligible")
    if (
        population.get("target_population") != len(frame_rows)
        or expected_eligible != len(records)
        or expected_ineligible != len(frame_rows) - len(records)
        or population.get("rows_accounted") != len(frame_rows)
        or receipt.get("target_population") != len(frame_rows)
        or receipt.get("rows_accounted") != len(frame_rows)
        or receipt.get("training_eligible") != len(records)
        or receipt.get("training_ineligible") != len(frame_rows) - len(records)
    ):
        raise producer.TrainingContractError(
            "canonical feature frame eligibility accounting mismatch"
        )
    if len(set(all_row_ids)) != len(all_row_ids) or len(set(eligible_row_ids)) != len(
        eligible_row_ids
    ):
        raise producer.TrainingContractError("canonical feature frame row IDs are not unique")

    frame_binding = producer.CanonicalFrameBinding(
        artifact_sha256=expected_artifact_sha,
        receipt_sha256=expected_receipt_sha,
        business_sha256=producer._assert_sha256(
            artifact.get("business_content_sha256"), "frame business hash"
        ),
        contract_id=contract.contract_id,
        contract_version=contract.feature_contract_version,
        feature_names=contract.ordered_features,
        target_population=len(frame_rows),
        rows_accounted=int(population["rows_accounted"]),
        eligible_rows=len(records),
        ineligible_rows=len(frame_rows) - len(records),
        target_row_id_sha256=producer._row_id_hash(all_row_ids),
        eligible_row_id_sha256=producer._row_id_hash(eligible_row_ids),
        frame_code_revision=producer._assert_full_sha(
            receipt.get("code_revision"), "frame receipt code revision"
        ),
    )
    data = producer.validate_training_frame(
        pd.DataFrame(records),
        registry=registry,
        feature_cutoff_column="feature_as_of_utc",
        validate_target=False,
    )
    return replace(
        data,
        source_binding=frame_binding,
        frame_eligible_rows=frame_binding.eligible_rows,
        frame_ineligible_rows=frame_binding.ineligible_rows,
    )
