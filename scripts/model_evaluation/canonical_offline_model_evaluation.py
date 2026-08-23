#!/usr/bin/env python3
"""CLI for the frozen canonical offline model evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from src.ml.evaluation import canonical_offline_model_evaluation as evaluation


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canonical offline model evaluation")
    parser.add_argument("--candidate", required=True, help="repository-external candidate artifact")
    parser.add_argument("--metadata", required=True, help="repository-external candidate metadata")
    parser.add_argument("--frame", required=True, help="repository-external canonical frame")
    parser.add_argument("--receipt", required=True, help="repository-external frame receipt")
    parser.add_argument("--protocol", required=True, help="checked-in frozen protocol JSON")
    parser.add_argument(
        "--output-dir", required=True, help="new repository-external output directory"
    )
    parser.add_argument(
        "--protocol-freeze-sha", required=True, help="full SHA containing the frozen protocol"
    )
    parser.add_argument(
        "--source-head", help="full evaluation source HEAD; defaults to current HEAD"
    )
    parser.add_argument(
        "--outcome-opened-at", required=True, help="UTC/RFC3339 outcome-open timestamp"
    )
    parser.add_argument("--json", action="store_true", help="emit one machine-readable summary")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one hash-bound evaluation and write repository-external evidence."""
    args = _parse_args(argv)
    source_head = args.source_head or evaluation.current_git_head()
    evaluation.assert_clean_worktree()
    output_destination = evaluation.prepare_evaluation_output_destination(Path(args.output_dir))
    artifact = evaluation.run_evaluation(
        candidate_path=Path(args.candidate),
        metadata_path=Path(args.metadata),
        frame_path=Path(args.frame),
        receipt_path=Path(args.receipt),
        protocol_path=Path(args.protocol),
        source_head=source_head,
        protocol_freeze_sha=args.protocol_freeze_sha,
        outcome_opened_at=args.outcome_opened_at,
        output_destination=output_destination,
    )
    try:
        output = evaluation.write_evaluation_outputs(
            artifact,
            output_destination=output_destination,
            protocol_freeze_sha=args.protocol_freeze_sha,
            evaluation_source_head=source_head,
        )
    except Exception as exc:
        evaluation.append_evaluation_journal_event(
            output_destination,
            event_type="EVALUATION_ATTEMPT_INVALIDATED",
            event_at=args.outcome_opened_at,
            fields={
                "evaluation_protocol_sha256": artifact["evaluation_protocol_sha256"],
                "protocol_freeze_sha": args.protocol_freeze_sha,
                "evaluation_source_head": source_head,
                "error_type": type(exc).__name__,
                "evaluation_attempt": "INVALIDATED_BY_OUTPUT_FAILURE",
                "invalidated_by": "OUTPUT_FAILURE",
                "holdout_status_after": evaluation.RESERVED_STATUS_AFTER,
            },
            allow_existing_outputs=True,
        )
        raise
    evaluation.append_evaluation_journal_event(
        output_destination,
        event_type="EVALUATION_ARTIFACT_WRITTEN",
        event_at=args.outcome_opened_at,
        fields={
            "evaluation_protocol_sha256": artifact["evaluation_protocol_sha256"],
            "protocol_freeze_sha": args.protocol_freeze_sha,
            "evaluation_source_head": source_head,
            "artifact_sha256": output["artifact_sha256"],
            "receipt_sha256": output["receipt_sha256"],
            "holdout_status_after": evaluation.RESERVED_STATUS_AFTER,
        },
        allow_existing_outputs=True,
    )
    summary = {
        "evaluation_id": artifact["evaluation_id"],
        "evaluated_rows": artifact["population"]["evaluated_rows"],
        "primary_metric": artifact["primary_metric"],
        "candidate_metrics": artifact["candidate_metrics"],
        "baseline_metrics": artifact["baseline_metrics"],
        "metric_deltas": artifact["metric_deltas"],
        "model_offline_quality_status": artifact["model_offline_quality_status"],
        "holdout_status_after": artifact["holdout"]["status_after"],
        "artifact_path": output["artifact_path"],
        "artifact_sha256": output["artifact_sha256"],
        "receipt_path": output["receipt_path"],
        "receipt_sha256": output["receipt_sha256"],
    }
    sys.stdout.write(
        f"{json.dumps(summary, ensure_ascii=False, sort_keys=True) if args.json else summary}\n"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except evaluation.EvaluationContractError as exc:
        sys.stderr.write(f"canonical offline evaluation blocked: {exc}\n")
        raise SystemExit(1) from exc
