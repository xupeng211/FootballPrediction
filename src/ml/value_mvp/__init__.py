"""VALUE_MVP-1: offline baseline model vs closing market benchmark.

Offline research-only modules. Zero DB, zero network. Consumes M3-R2 canonical
observation outputs and pinned Football-Data historical CSVs (git blobs).
"""

from src.ml.value_mvp.protocol import (
    CLASS_LABELS,
    FEATURE_NAMES,
    FORBIDDEN_FEATURE_KEYWORDS,
    PROTOCOL_SCHEMA,
    load_protocol,
    protocol_sha256,
    validate_protocol,
)

__all__ = [
    "CLASS_LABELS",
    "FEATURE_NAMES",
    "FORBIDDEN_FEATURE_KEYWORDS",
    "PROTOCOL_SCHEMA",
    "load_protocol",
    "protocol_sha256",
    "validate_protocol",
]
