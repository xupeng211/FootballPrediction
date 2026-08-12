"""Shared canonical prediction runtime owner.

lifecycle: permanent
component: Canonical

This module owns the process-local ``v26_7_aligned`` predictor used by every
supported prediction surface. It deliberately delegates model identity,
artifact verification, feature-contract validation, and readiness to the
existing canonical ``Predictor`` and verified loader.
"""

from __future__ import annotations

import logging
import threading

from src.ml.inference.canonical_model_loader import ModelArtifactUnavailableError
from src.ml.inference.model_dispatcher import Predictor

logger = logging.getLogger(__name__)


class _RuntimeState:
    """Mutable cache holder so the module exposes one explicit owner."""

    predictor: Predictor | None = None


_runtime_state = _RuntimeState()
_predictor_lock = threading.RLock()


def get_predictor() -> Predictor:
    """Return the shared canonical predictor, refreshing its identity first."""
    with _predictor_lock:
        if _runtime_state.predictor is None:
            logger.info("初始化 canonical v26_7_aligned 预测器...")
            _runtime_state.predictor = Predictor.create_v26_7_aligned()
        else:
            try:
                _runtime_state.predictor.ensure_canonical_model_current()
            except ModelArtifactUnavailableError:
                # Never retain an object after manifest/artifact invalidation
                # makes the canonical load unavailable.
                _runtime_state.predictor = None
                raise
        return _runtime_state.predictor


def reset_predictor() -> None:
    """Clear the process-local cache for isolated lifecycle tests."""
    with _predictor_lock:
        _runtime_state.predictor = None


__all__ = ["get_predictor"]
