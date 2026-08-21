"""Tests for the shared full-SHA freshness contract.

lifecycle: test-fixture

These tests are pure and offline.  They cover the authority boundary used by
PR readiness, CI freshness, strict review freshness, and main completion.
"""

from __future__ import annotations

import pytest

from scripts.devops.exact_head import (
    ExactHeadError,
    assert_ci_is_current,
    assert_exact_head,
    assert_merge_sha,
    assert_review_is_current,
    get_current_head,
    is_full_sha,
)

HEAD_A = "abcdef0" + "1" * 33
HEAD_B = "abcdef0" + "2" * 33
OTHER_HEAD = "1234567" + "3" * 33


def test_same_full_sha_passes() -> None:
    assert assert_exact_head(HEAD_A, HEAD_A.upper(), role="HEAD") == HEAD_A


def test_different_full_sha_fails() -> None:
    with pytest.raises(ExactHeadError, match="stale"):
        assert_exact_head(HEAD_A, OTHER_HEAD, role="HEAD")


def test_same_seven_character_prefix_different_full_sha_fails() -> None:
    assert HEAD_A[:7] == HEAD_B[:7]
    with pytest.raises(ExactHeadError, match="stale"):
        assert_exact_head(HEAD_A, HEAD_B, role="HEAD")


def test_short_sha_is_never_full_or_authoritative() -> None:
    assert not is_full_sha(HEAD_A[:7])
    with pytest.raises(ExactHeadError, match="full 40-hex"):
        assert_exact_head(HEAD_A, HEAD_A[:7], role="HEAD")


def test_review_old_head_is_stale() -> None:
    with pytest.raises(ExactHeadError, match="review HEAD"):
        assert_review_is_current(HEAD_A, OTHER_HEAD)


def test_review_current_head_passes() -> None:
    assert assert_review_is_current(HEAD_A, HEAD_A) == HEAD_A


def test_ci_old_head_is_stale() -> None:
    with pytest.raises(ExactHeadError, match="CI HEAD"):
        assert_ci_is_current(HEAD_A, OTHER_HEAD)


def test_merge_verification_must_cover_exact_merge_sha() -> None:
    assert assert_merge_sha(HEAD_A, HEAD_A) == HEAD_A
    with pytest.raises(ExactHeadError, match="merge SHA"):
        assert_merge_sha(HEAD_A, OTHER_HEAD)


def test_current_repository_head_uses_full_sha() -> None:
    assert get_current_head(lambda _args: HEAD_A) == HEAD_A
    with pytest.raises(ExactHeadError, match="current repository HEAD"):
        get_current_head(lambda _args: HEAD_A[:7])
