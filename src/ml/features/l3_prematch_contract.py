#!/usr/bin/env python3
"""L3 Prematch-Safe Feature Contract loader and filter.

lifecycle: permanent
scope: l3_features training input safety enforcement

Loads the machine-readable contract and provides filter functions
that training entrypoints must call before using L3 feature JSON.

Usage::

    from src.ml.features.l3_prematch_contract import (
        load_l3_prematch_contract,
        filter_l3_feature_group,
        filter_l3_feature_payload,
    )

    contract = load_l3_prematch_contract()
    safe_golden = filter_l3_feature_group("golden_features", raw_golden)
    # tactical_features returns {} in prematch mode
    safe_tactical = filter_l3_feature_group("tactical_features", raw_tactical)
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

# ── constants ────────────────────────────────────────────────────────────────

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "config"
    / "features"
    / "l3_prematch_safe_contract.v0.json"
)

# ============================================================================
# public API
# ============================================================================


def load_l3_prematch_contract(path: str | Path | None = None) -> dict[str, Any]:
    """Load the L3 prematch-safe feature contract from JSON.

    Args:
        path: Optional override path.  Defaults to the canonical location
              ``config/features/l3_prematch_safe_contract.v0.json``.

    Returns:
        The parsed contract dictionary.

    Raises:
        FileNotFoundError: if the contract file cannot be found.
        json.JSONDecodeError: if the file is not valid JSON.
    """
    p = Path(path) if path else _CONTRACT_PATH
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def filter_l3_feature_group(  # noqa: C901 PLR0912 PLR0911
    group_name: str,
    features: dict[str, Any] | None,
    *,
    include_conditional: bool = False,
    allow_diagnostic_postmatch: bool = False,
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Filter a single L3 feature group through the prematch-safe contract.

    Args:
        group_name: One of the known feature group keys (``"golden_features"``, etc.).
        features: The raw feature dict from l3_features JSONB.  ``None`` or empty
                  dict is handled safely.
        include_conditional: If ``True``, conditional-safe features that pass
                  their ``allow_only_when`` checks are retained.  Default
                  ``False`` (only PREMATCH_SAFE keys pass).
        allow_diagnostic_postmatch: If ``True``, postmatch-leakage groups
                  (tactical_features) are passed through unfiltered for
                  diagnostic use.  **Never** set this for prematch prediction.
        contract: Pre-loaded contract.  If ``None``, loads from disk.

    Returns:
        A filtered dict containing only the keys permitted by the contract.
        Returns an empty dict when the entire group is denied.
    """
    if contract is None:
        contract = load_l3_prematch_contract()

    groups_cfg = contract.get("feature_groups", {})
    group_cfg = groups_cfg.get(group_name)

    # ── unknown group → deny ────────────────────────────────────────────────
    if group_cfg is None:
        return {}

    # ── None / empty input → safe pass-through ──────────────────────────────
    if features is None:
        return {}
    if not isinstance(features, dict):
        return {}
    if len(features) == 0:
        return {}

    # ── deny_all (tactical_features, stitch_summary) ────────────────────────
    if group_cfg.get("deny_all"):
        if allow_diagnostic_postmatch:
            # In diagnostic mode, pass through unfiltered — caller must
            # label output as postmatch diagnostic, not prematch predictor.
            return dict(features)
        return {}

    # ── conditional_safe without evidence → deny ────────────────────────────
    if group_cfg.get("conditional_safe") and not include_conditional:
        default_action = group_cfg.get("default_action", "deny")
        if default_action in ("deny", "deny_when_default", "deny_until_verified"):
            return {}

    # ── explicit denylist (checked first, overrides allowlist) ──────────────
    deny_exact: list[str] = group_cfg.get("deny_exact", [])
    deny_patterns: list[str] = group_cfg.get("deny_patterns", [])
    deny_metadata: list[str] = group_cfg.get("deny_metadata_keys", [])

    denied: set[str] = set()

    # exact denylist
    for key in features:
        if key in deny_exact or key in deny_metadata:
            denied.add(key)

    # pattern denylist
    for key in features:
        if key in denied:
            continue
        for pat in deny_patterns:
            if re.match(pat, key):
                denied.add(key)
                break

    # ── allowlist ────────────────────────────────────────────────────────────
    allowlist: list[str] = group_cfg.get("prematch_safe_allowlist", [])
    allow_set = set(allowlist)

    allowed: dict[str, Any] = {}
    for key, value in features.items():
        if key in denied:
            continue
        if key in allow_set:
            allowed[key] = value

    return allowed


def filter_l3_feature_payload(
    payload: dict[str, Any],
    *,
    include_conditional: bool = False,
    allow_diagnostic_postmatch: bool = False,
    contract: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Filter an entire L3 feature payload (all groups).

    Args:
        payload: A dict keyed by feature group name, each value a raw feature
                 dict from l3_features JSONB.
        include_conditional: Forwarded to :func:`filter_l3_feature_group`.
        allow_diagnostic_postmatch: Forwarded to :func:`filter_l3_feature_group`.
        contract: Pre-loaded contract.

    Returns:
        A dict with the same structure, but each group filtered.

    ``dropped_summary`` is included as a ``_dropped`` key for logging purposes.
    """
    if contract is None:
        contract = load_l3_prematch_contract()

    groups_cfg = contract.get("feature_groups", {})

    filtered: dict[str, dict[str, Any]] = {}
    dropped: dict[str, int] = {}

    for group_name, raw_features in payload.items():
        if raw_features is None:
            filtered[group_name] = {}
            continue
        if not isinstance(raw_features, dict):
            filtered[group_name] = {}
            continue

        safe = filter_l3_feature_group(
            group_name,
            raw_features,
            include_conditional=include_conditional,
            allow_diagnostic_postmatch=allow_diagnostic_postmatch,
            contract=contract,
        )
        filtered[group_name] = safe
        dropped_count = len(raw_features) - len(safe)
        if dropped_count > 0 or group_name in groups_cfg:
            dropped[group_name] = dropped_count

    # Attach summary for logging — non-intrusive, won't break existing consumers
    filtered["_dropped"] = dropped
    return filtered
