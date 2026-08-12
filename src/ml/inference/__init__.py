"""Canonical inference package exports.

The PR-4 lifecycle boundary removes the old package-level compatibility
facade, which exposed an unverified ``ModelLoader`` and ``MatchPredictor``.
The supported HTTP API and canonical CLI use the shared runtime owner,
dispatcher, and verified loader. The non-API TITAN loader remains available
only through its direct module import; its lifecycle is outside this package
surface.

lifecycle: permanent
component: Canonical package surface
"""

from .canonical_model_loader import (
    CanonicalModelLoader,
    LoadedCanonicalModel,
    ModelArtifactUnavailableError,
    get_canonical_model_loader,
)
from .model_dispatcher import ModelDispatcher, Predictor
from .prediction_runtime import get_predictor

__all__ = [
    "CanonicalModelLoader",
    "LoadedCanonicalModel",
    "ModelArtifactUnavailableError",
    "ModelDispatcher",
    "Predictor",
    "get_canonical_model_loader",
    "get_predictor",
]
