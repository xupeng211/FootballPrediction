"""Thin, no-DB canonical prediction CLI adapter.

lifecycle: permanent
component: Canonical

The CLI accepts the same raw JSON payload shape as the HTTP prediction
surface. It never discovers matches, invokes the legacy DB/Titan batch
repositories, fetches network data, selects Titan, or creates a fallback
model. Prediction calls resolve through ``prediction_runtime.get_predictor``
and therefore use the same verified canonical lifecycle as HTTP.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, Protocol, TextIO, cast

if TYPE_CHECKING:
    from collections.abc import Callable

from src.ml.inference import prediction_runtime
from src.ml.inference.canonical_model_loader import (
    CANONICAL_API_MODEL_TYPE,
    ModelArtifactUnavailableError,
)

CANONICAL_MODEL_TYPE = CANONICAL_API_MODEL_TYPE
EXIT_SUCCESS = 0
EXIT_PREDICTION_ERROR = 1
EXIT_INPUT_ERROR = 2
EXIT_MODEL_UNAVAILABLE = 3


class InputError(ValueError):
    """Raised when CLI input cannot be accepted as an HTTP-compatible payload."""


class _CanonicalPredictor(Protocol):
    """Minimal predictor surface required by this thin adapter."""

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def predict_batch(self, payload: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


def get_predictor() -> _CanonicalPredictor:
    """Resolve the shared canonical runtime owner.

    This small seam lets hermetic behavior tests inject a predictor without
    changing the production owner.
    """
    return cast("_CanonicalPredictor", prediction_runtime.get_predictor())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="canonical v26_7_aligned prediction CLI",
    )
    parser.add_argument(
        "--input",
        metavar="FILE",
        help="UTF-8 JSON file; use '-' or omit the option to read stdin",
    )
    parser.add_argument(
        "--format",
        choices=("json",),
        default="json",
        help="output format (currently JSON only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="compatibility alias for --format json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the JSON payload without loading a model or predicting",
    )
    return parser


def _read_input(input_path: str | None, stdin: TextIO) -> Any:
    if input_path and input_path != "-":
        try:
            source = Path(input_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise InputError("unable to read input JSON") from exc
    else:
        if stdin.isatty():
            raise InputError("provide --input FILE or pipe JSON on stdin")
        source = stdin.read()

    if not source.strip():
        raise InputError("input JSON is empty")
    try:
        return json.loads(source)
    except json.JSONDecodeError as exc:
        raise InputError("malformed JSON") from exc


def validate_payload(payload: Any) -> dict[str, Any] | list[dict[str, Any]]:
    """Validate only the outer shape shared by HTTP single and batch routes."""
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise InputError("expected a JSON object or an array of JSON objects")


def predict_payload(
    payload: Any,
    *,
    predictor_provider: Callable[[], _CanonicalPredictor] | None = None,
) -> dict[str, Any] | list[dict[str, Any]]:
    """Validate and predict one HTTP-compatible payload without feature translation."""
    validated = validate_payload(payload)
    predictor = predictor_provider() if predictor_provider is not None else get_predictor()
    if isinstance(validated, list):
        return predictor.predict_batch(validated)
    return predictor.predict(validated)


def _safe_value_error(error: ValueError) -> str:
    """Keep adapter errors useful without echoing paths or multiline internals."""
    detail = " ".join(str(error).split())
    if not detail or any(token in detail for token in ("/home/", "/tmp/", "model_zoo", "models/")):
        return "prediction input rejected"
    return f"prediction input rejected: {detail[:240]}"


def _write_json(value: Any, stdout: TextIO) -> None:
    stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    predictor_provider: Callable[[], _CanonicalPredictor] | None = None,
) -> int:
    """Run the hermetic canonical CLI and return a deterministic exit code."""
    input_stream = stdin or sys.stdin
    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    args = _parser().parse_args(argv)

    try:
        payload = _read_input(args.input, input_stream)
        validated = validate_payload(payload)

        if args.dry_run:
            item_count = len(validated) if isinstance(validated, list) else 1
            _write_json(
                {
                    "status": "input_valid",
                    "model_type": CANONICAL_MODEL_TYPE,
                    "item_count": item_count,
                },
                output_stream,
            )
            return EXIT_SUCCESS

        result = predict_payload(validated, predictor_provider=predictor_provider)
        _write_json(result, output_stream)
        exit_code = EXIT_SUCCESS
    except InputError as exc:
        print(f"input error: {exc}", file=error_stream)
        exit_code = EXIT_INPUT_ERROR
    except ModelArtifactUnavailableError:
        print("prediction model unavailable", file=error_stream)
        exit_code = EXIT_MODEL_UNAVAILABLE
    except ValueError as exc:
        print(_safe_value_error(exc), file=error_stream)
        exit_code = EXIT_INPUT_ERROR
    except KeyboardInterrupt:
        print("prediction interrupted", file=error_stream)
        exit_code = 130
    except Exception:
        print("prediction failed", file=error_stream)
        exit_code = EXIT_PREDICTION_ERROR

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
