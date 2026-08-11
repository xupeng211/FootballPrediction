"""Canonical inference package exports.

The PR-4 lifecycle boundary removes the old package-level compatibility
facade, which exposed an unverified ``ModelLoader`` and ``MatchPredictor``.
The supported HTTP API imports the canonical dispatcher and verified loader.
The non-API TITAN loader remains available through its direct module import;
its lifecycle is outside this PR.

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
from .titan_loader import TitanModelLoader, get_titan_model

__all__ = [
    "CanonicalModelLoader",
    "LoadedCanonicalModel",
    "ModelArtifactUnavailableError",
    "ModelDispatcher",
    "Predictor",
    "TitanModelLoader",
    "get_canonical_model_loader",
    "get_titan_model",
]
