#!/usr/bin/env python3
"""Shared full-SHA freshness primitives for workflow state checks.

lifecycle: permanent

Only complete 40-hex commit IDs may authorize freshness, review, CI, merge,
or completion decisions.  Short IDs remain suitable for human-facing output,
but this module deliberately never accepts them for comparisons.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}\Z")


class ExactHeadError(ValueError):
    """Raised when an authority-sensitive SHA is missing or abbreviated."""


def is_full_sha(value: str | None) -> bool:
    """Return whether *value* is exactly one complete 40-hex SHA."""
    return bool(value and FULL_SHA_RE.fullmatch(value))


def normalize_full_sha(value: str | None, *, role: str) -> str:
    """Validate and normalize one authority-sensitive SHA."""
    if not is_full_sha(value):
        raise ExactHeadError(f"{role} must be a full 40-hex commit SHA")
    return value.lower()


def assert_exact_head(expected: str | None, actual: str | None, *, role: str) -> str:
    """Return the normalized SHA when two complete IDs are exactly equal."""
    expected_sha = normalize_full_sha(expected, role=f"expected {role}")
    actual_sha = normalize_full_sha(actual, role=f"actual {role}")
    if expected_sha != actual_sha:
        raise ExactHeadError(f"{role} is stale: expected {expected_sha}, observed {actual_sha}")
    return actual_sha


def same_exact_head(expected: str | None, actual: str | None) -> bool:
    """Return true only for equal complete SHA values."""
    try:
        assert_exact_head(expected, actual, role="HEAD")
    except ExactHeadError:
        return False
    return True


def assert_review_is_current(reviewed_head: str | None, current_pr_head: str | None) -> str:
    """Require an adversarial review to cover the current PR HEAD."""
    return assert_exact_head(current_pr_head, reviewed_head, role="review HEAD")


def assert_ci_is_current(ci_head: str | None, current_pr_head: str | None) -> str:
    """Require a CI result to cover the current PR HEAD."""
    return assert_exact_head(current_pr_head, ci_head, role="CI HEAD")


def assert_merge_sha(merge_sha: str | None, verified_sha: str | None) -> str:
    """Require main verification to cover the exact merge SHA."""
    return assert_exact_head(merge_sha, verified_sha, role="merge SHA")


def get_current_head(run_git: Callable[[Sequence[str]], str]) -> str:
    """Read and validate the repository HEAD through a caller-supplied Git runner."""
    return normalize_full_sha(run_git(["rev-parse", "HEAD"]), role="current repository HEAD")
