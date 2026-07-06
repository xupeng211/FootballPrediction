#!/usr/bin/env python3
"""Training artifact write guard.

lifecycle: permanent
scope: training artifact write safety
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

TRAINING_WRITE_ENV = "ALLOW_TRAINING_WRITE"
FINAL_TRAINING_CONFIRMATION_ENV = "FINAL_TRAINING_WRITE_CONFIRMATION"
CONFIRMATION_VALUE = "yes"


class TrainingWriteGuardError(RuntimeError):
    """Raised when a training artifact write is not explicitly confirmed."""


def training_write_confirmed(environ: Mapping[str, str] | None = None) -> bool:
    """Return true only when both training write confirmations are present."""
    env = os.environ if environ is None else environ
    return (
        env.get(TRAINING_WRITE_ENV) == CONFIRMATION_VALUE
        and env.get(FINAL_TRAINING_CONFIRMATION_ENV) == CONFIRMATION_VALUE
    )


def require_training_write_confirmation(environ: Mapping[str, str] | None = None) -> None:
    """Fail closed unless training artifact writes are explicitly confirmed."""
    if training_write_confirmed(environ):
        return

    raise TrainingWriteGuardError(
        "Training artifact writes require "
        f"{TRAINING_WRITE_ENV}=yes and {FINAL_TRAINING_CONFIRMATION_ENV}=yes. "
        "Use --report-only --no-write for filtered matrix reporting."
    )
