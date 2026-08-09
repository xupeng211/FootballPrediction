"""Leakage guards for VALUE_MVP-1.

Two complementary guards: (1) a static scan of the model feature frame for
forbidden raw/current-match source keywords (odds, market, result, FTR,
FTHG/FTAG, postmatch, ...) — deliberately not a naive substring scan of
legitimate rolling feature names; (2) a static scan of the business path for
random-split constructs. Both are enforced at runtime and tested in unit tests.
"""

from __future__ import annotations

from pathlib import Path

from src.ml.value_mvp.protocol import FEATURE_NAMES, FORBIDDEN_FEATURE_KEYWORDS

_RANDOM_SPLIT_MARKERS = (
    "train_test_split",
    "ShuffleSplit",
    "StratifiedShuffleSplit",
    "random_split",
    "shuffle=True",
    "GridSearchCV",
    "RandomizedSearchCV",
    "Optuna",
)


def feature_name_violations(feature_names: tuple[str, ...] = FEATURE_NAMES) -> list[str]:
    """Return feature names that collide with forbidden source keywords."""
    violations: list[str] = []
    violations.extend(
        f"{feature} collides with forbidden keyword {keyword}"
        for feature in feature_names
        for keyword in FORBIDDEN_FEATURE_KEYWORDS
        if keyword in feature.lower()
    )
    return violations


def scan_business_path_for_random_split(roots: list[Path]) -> list[str]:
    """Scan source files for random-split constructs (business path only).

    Reads only .py files under the given roots; returns one violation string
    per marker hit with file and line. Comment text (line comments and
    trailing comments) and this marker module itself are excluded — the
    markers must appear in this file by definition.
    """
    violations: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.py")):
            if path == Path(__file__).resolve():
                continue
            violations.extend(
                f"{path.relative_to(root)}:{line_number}: {marker}"
                for line_number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), start=1
                )
                for marker in _RANDOM_SPLIT_MARKERS
                if marker in line.split("#", 1)[0]
            )
    return violations
