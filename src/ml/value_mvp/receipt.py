"""Run receipt assembly and human-readable summary for VALUE_MVP-1.

The receipt (schema value-mvp-1-run-receipt/v2) binds protocol_sha256, the
evaluation population hash, the runtime environment fingerprint and per-fold
optimizer convergence to every summarized output file via output_digests.
The validator cross-checks every one of these against the files and the
runtime environment.

numpy is module-level safe for the CI collection gate (the training-guard
stub keeps it in sys.modules); sklearn/scipy stay function-level.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

import numpy as np

from src.ml.value_mvp.protocol import protocol_sha256

if TYPE_CHECKING:
    from pathlib import Path

_RECEIPT_SCHEMA = "value-mvp-1-run-receipt/v2"


def write_json(path: Path, obj: dict[str, Any]) -> None:
    """Write byte-stable canonical JSON (sorted keys, rounded floats)."""
    path.write_text(
        json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )


def sha256_file(path: Path) -> str:
    """SHA256 of a file's bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _environment_fingerprint() -> dict[str, Any]:
    """Runtime environment facts bound into the run receipt (no wall-clock).

    The frozen hyperparameters include max_iter=2000; on the real data lbfgs
    stops at the iteration limit, so the fitted probabilities live on the
    optimizer trajectory and exact reproduction requires this pinned
    environment. sklearn/scipy must stay function-level imports (the CI
    collection gate stubs sklearn with __path__=[]).
    """
    import platform  # noqa: PLC0415

    import scipy  # type: ignore[import-untyped]  # noqa: PLC0415
    import sklearn  # noqa: PLC0415

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }


_RECEIPT_OUTPUT_FILES = (
    "fold1-predictions.csv",
    "fold2-predictions.csv",
    "fold1-metrics.json",
    "fold2-metrics.json",
    "pooled-metrics.json",
    "bootstrap.json",
    "calibration.json",
    "input-manifest.json",
    "evaluation-dataset-manifest.json",
    "summary.md",
)


def build_run_receipt(
    pooled: dict[str, Any],
    fold1: dict[str, Any],
    fold2: dict[str, Any],
    protocol: dict[str, Any],
    manifest: dict[str, Any],
    population_manifest: dict[str, Any],
    git_revision: str,
    output_dir: Path,
    compute_digests: bool = True,
) -> dict[str, Any]:
    """Assemble the run receipt (all business results + hashes; no wall-clock).

    output_digests binds the receipt to the exact bytes of every summarized
    file, so tampering with either side is rejected by the validator. The
    caller passes compute_digests=False before summary.md exists, then fills
    the digests in before writing the receipt.
    """
    return {
        "schema": _RECEIPT_SCHEMA,
        "task": protocol["task"],
        "git_revision": git_revision,
        "protocol_sha256": protocol_sha256(protocol),
        "input_manifest_sha256": hashlib.sha256(
            json.dumps(manifest, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "evaluation_population_hash": population_manifest["evaluation_population_hash"],
        "environment": _environment_fingerprint(),
        "model_convergence": {
            "fold1": fold1["convergence"],
            "fold2": fold2["convergence"],
        },
        "output_digests": (
            {name: sha256_file(output_dir / name) for name in _RECEIPT_OUTPUT_FILES}
            if compute_digests
            else {}
        ),
        "fold1": fold1["metrics"],
        "fold2": fold2["metrics"],
        "pooled": pooled["metrics"],
        "bootstrap": pooled["bootstrap"],
        "calibration": pooled["calibration"],
        "claim_boundary": protocol["claim_boundary"],
        "forbidden_claims": protocol["forbidden_claims"],
    }


def write_summary(path: Path, receipt: dict[str, Any]) -> None:
    """Human-readable summary (markdown) of the run receipt."""
    pooled = receipt["pooled"]
    lines = [
        "# VALUE_MVP-1 run summary",
        "",
        f"- protocol SHA256: {receipt['protocol_sha256']}",
        f"- git revision: {receipt['git_revision']}",
        f"- evaluation population hash: {receipt['evaluation_population_hash']}",
        "",
        "## Fold 1 (train 2022/23 -> test 2023/24)",
    ]
    lines.extend(_metrics_lines(receipt["fold1"]))
    lines.extend(["## Fold 2 (train 2022/23+2023/24 -> test 2024/25)"])
    lines.extend(_metrics_lines(receipt["fold2"]))
    lines.extend(["## Pooled OOS"])
    lines.extend(_metrics_lines(pooled))
    lines.extend(
        [
            f"- delta_log_loss 95% CI: [{pooled['delta_log_loss_ci95_low']}, {pooled['delta_log_loss_ci95_high']}]",
            f"- FINAL CLASSIFICATION: {pooled['final_classification']}",
            "",
            "## Model convergence (lbfgs)",
        ]
    )
    for fold_name, entry in receipt.get("model_convergence", {}).items():
        lines.append(
            f"- {fold_name}: converged={entry.get('converged')} "
            f"(iterations {entry.get('iterations')} / max_iter {entry.get('max_iter')})"
        )
    env = receipt.get("environment", {})
    lines.extend(
        [
            "",
            "## Environment (reproducibility boundary)",
            f"- python {env.get('python')} / sklearn {env.get('sklearn')} / "
            f"numpy {env.get('numpy')} / scipy {env.get('scipy')}",
            f"- platform: {env.get('platform')}",
            "",
            "## Claim boundary",
            f"- {receipt['claim_boundary']}",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _metrics_lines(metrics: dict[str, Any]) -> list[str]:
    """Markdown lines for a metrics block."""
    return [
        f"- OOS count: {metrics.get('oos_count')}",
        f"- model log loss: {metrics.get('model_log_loss')}",
        f"- market log loss: {metrics.get('market_log_loss')}",
        f"- class-frequency log loss: {metrics.get('class_frequency_log_loss')}",
        f"- delta log loss (model - market): {metrics.get('delta_log_loss')}",
        f"- model brier: {metrics.get('model_brier')}",
        f"- market brier: {metrics.get('market_brier')}",
        f"- delta brier: {metrics.get('delta_brier')}",
        f"- model accuracy: {metrics.get('model_accuracy')}",
        f"- market accuracy: {metrics.get('market_accuracy')}",
    ]
