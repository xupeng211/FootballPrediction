#!/usr/bin/env python3
"""AI Workflow Gate safety-declaration checks.

lifecycle: permanent
owner: engineering workflow governance

This helper keeps the shared AI gate below the repository's Python file-size
limit while preserving the existing safety consistency contract.
"""

from __future__ import annotations

import re

DB_TOUCH_PATHS: tuple[str, ...] = (
    "src/db/",
    "database/",
    "src/data/db_",
    "src/infrastructure/db_",
    "scripts/ops/db_",
)
SCRAPER_TOUCH_PATHS: tuple[str, ...] = (
    "src/scraper/",
    "src/data/scraper/",
    "scripts/scraper/",
    "src/data/fotmob",
    "scripts/ops/fotmob",
)
BROWSER_TOUCH_PATHS: tuple[str, ...] = (
    "src/browser/",
    "playwright",
    "chromium",
    "stealth",
)


def _section_text_between(pr_body: str, start_heading: str) -> str:
    """Return a section body until the next second-level heading."""

    start = pr_body.find(start_heading)
    if start == -1:
        return ""
    suffix = pr_body[start + len(start_heading) :]
    next_heading = re.search(r"\n##\s", suffix)
    return suffix[: next_heading.start()] if next_heading else suffix


def _safety_declared_no(pr_body: str, label: str) -> bool:
    return bool(
        re.search(rf"\|\s*{label}\s*\|\s*no\b", pr_body, re.IGNORECASE)
        or re.search(rf"-\s*no\s+{label}\s*:\s*yes", pr_body, re.IGNORECASE)
    )


def _safety_status_no(pr_body: str, label: str) -> bool:
    return bool(re.search(rf"-\s*no\s+{label}\s*:\s*yes", pr_body, re.IGNORECASE))


def _risk_declared_no(pr_body: str, label: str) -> bool:
    risk = _section_text_between(pr_body, "## Risk")
    if not risk:
        return False
    label_pattern = label.replace(r"\s+", r"\s+")
    return bool(
        re.search(rf"\bno\s+(?:live\s+)?{label_pattern}\b", risk, re.IGNORECASE)
        or re.search(rf"\b{label_pattern}\s*:\s*no\b", risk, re.IGNORECASE)
    )


def check_safety_consistency(pr_body: str, changed: set[str]) -> list[str]:
    """Fail if safety declarations contradict the files actually changed."""

    errors: list[str] = []

    db_declared_no = (
        _safety_declared_no(pr_body, r"DB\s+used")
        or _safety_status_no(pr_body, r"DB\s+writes")
        or _risk_declared_no(pr_body, r"(?:DB|database)\s+writes?")
    )
    if db_declared_no and any(
        any(path.startswith(prefix) for prefix in DB_TOUCH_PATHS) for path in changed
    ):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in DB_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no DB, but changed files touch DB paths: "
            + ", ".join(touching)
        )

    scraper_declared_no = (
        _safety_declared_no(pr_body, r"Scraper\s+run")
        or _safety_status_no(pr_body, r"scraper")
        or _risk_declared_no(pr_body, r"(?:live\s+)?fetch|scraper\s+run")
    )
    if scraper_declared_no and any(
        any(path.startswith(prefix) for prefix in SCRAPER_TOUCH_PATHS) for path in changed
    ):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in SCRAPER_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no scraper, but changed files touch scraper/data paths: "
            + ", ".join(touching)
        )

    browser_declared_no = (
        _safety_declared_no(pr_body, r"Browser\s+automation\s+used")
        or _safety_status_no(pr_body, r"browser")
        or _risk_declared_no(pr_body, r"browser(?:\s+automation)?")
    )
    if browser_declared_no and any(
        any(path.startswith(prefix) for prefix in BROWSER_TOUCH_PATHS) for path in changed
    ):
        touching = sorted(p for p in changed if any(p.startswith(px) for px in BROWSER_TOUCH_PATHS))
        errors.append(
            "Safety declaration says no browser, but changed files touch "
            "browser/automation paths: " + ", ".join(touching)
        )

    return errors
