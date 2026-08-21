"""AI Workflow Gate check 7: anti-hollow-compliance section content validation.

lifecycle: permanent

Rejects PR bodies where canonical Tests, Risk, or Rollback sections (or the
retired Documentation Impact, Validation, or Rollback Plan sections) contain
only hollow placeholders (N/A, passed, revert PR, etc.).

This module is extracted from ai_workflow_gate.py to keep the main gate file
under the 800-line architecture limit enforced by gatekeeper.sh.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

CANONICAL_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Summary",
    "## Scope",
    "## Tests",
    "## Risk",
    "## Rollback",
)

# Compatibility contract for already-open or older PRs. It is not a second
# current template or workflow authority.
LEGACY_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Summary",
    "## Scope",
    "## Documentation Impact",
    "## Safety Impact",
    "## Validation",
    "## CI Gate Scope",
    "## No deletion / no move / no rename confirmation",
    "## Rollback Plan",
    "## Next Recommended Task",
    "## SC-002 status",
    "## Remaining risks",
)

REQUIRED_SECTIONS: tuple[str, ...] = CANONICAL_REQUIRED_SECTIONS

NEXT_TASK_MANDATORY_PHRASES: tuple[str, ...] = (
    "Do not start automatically",
    "Recommended next task only after user confirmation",
)


def _heading_line_present(pr_body: str, heading: str) -> bool:
    """Check for an exact Markdown heading, avoiding prefix collisions."""
    return bool(re.search(rf"(?m)^\s*{re.escape(heading)}\s*$", pr_body))


def check_required_sections(pr_body: str) -> list[str]:
    """Return missing headings for the canonical or retired PR contract."""
    has_canonical = any(
        _heading_line_present(pr_body, heading) for heading in CANONICAL_REQUIRED_SECTIONS[2:]
    )
    has_legacy = any(
        _heading_line_present(pr_body, heading) for heading in LEGACY_REQUIRED_SECTIONS[2:]
    )
    headings = (
        LEGACY_REQUIRED_SECTIONS
        if has_legacy and not has_canonical
        else CANONICAL_REQUIRED_SECTIONS
    )
    return [heading for heading in headings if heading not in pr_body]


def check_next_task_stop_phrase(
    pr_body: str,
    section_text_between_fn: Callable[[str, str], str],
) -> list[str]:
    """Check the retired no-auto-next-task section when an old body uses it."""
    section = section_text_between_fn(pr_body, "## Next Recommended Task")
    if not section:
        return []
    return [
        f"## Next Recommended Task missing phrase: '{phrase}'"
        for phrase in NEXT_TASK_MANDATORY_PHRASES
        if phrase not in section
    ]


# Sections that MUST contain substantive content — not just "N/A" or similar.
LEGACY_CRITICAL_SECTIONS: tuple[str, ...] = (
    "## Documentation Impact",
    "## Validation",
    "## Rollback Plan",
)

CANONICAL_CRITICAL_SECTIONS: tuple[str, ...] = (
    "## Tests",
    "## Risk",
    "## Rollback",
)

# Compatibility export for callers that inspected the retired contract.
CRITICAL_SECTIONS: tuple[str, ...] = CANONICAL_CRITICAL_SECTIONS

# General hollow-content patterns that are rejected in any critical section.
HOLLOW_CONTENT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^N/?A$",  # N/A, NA, n/a
        r"^none\.?$",  # none, None
        r"^not\s+applicable\.?$",  # not applicable
        r"^no\s+impact\.?$",  # no impact
        r"^no\s+documentation\s+impact\.?$",  # no documentation impact
        r"^passed\.?$",  # passed (for Validation)
        r"^ok(ay)?\.?$",  # ok / okay (for Validation)
        r"^no\s+validation\.?$",  # no validation
        r"^all\s+tests?\s+pass(ed)?\.?$",  # all tests pass / passed
        r"^tests?\s+pass(ed)?\.?$",  # tests pass / passed
        r"^n/?c\.?$",  # N/C (no change)
        r"^not?\s+required\.?$",  # not required
        r"^nothing\.?$",  # nothing
        r"^no\s+changes?\.?$",  # no change / no changes
    )
)

# Rollback Plan-specific hollow patterns.
ROLLBACK_HOLLOW_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^revert\s+(the\s+|this\s+)?(PR|commit|merge|change)\.?$",
        r"^revert\.?$",
        r"^rollback\s+by\s+revert(ing)?\.?$",
        r"^revert\s+to\s+previous\s+(version|state)\.?$",
        r"^git\s+revert\b.*$",
    )
)

# Minimum number of meaningful characters a critical section must contain.
MIN_SECTION_CONTENT_LENGTH = 15


def _clean_markdown_content(raw_text: str) -> str:
    """Strip markdown table formatting, bullets, and link syntax.

    Returns the cleaned prose text — what remains after removing formatting
    artifacts.  Used to determine whether a PR body section has substantive
    human-written content or is just template boilerplate.
    """
    lines = raw_text.splitlines()
    meaningful: list[str] = []
    # Words that are pure table-header boilerplate, not human content.
    _header_words = frozenset(
        {
            "item",
            "value",
            "result",
            "check",
            "status",
            "notes",
            "description",
            "details",
            "validation",
            "metric",
            "count",
            "added",
            "deleted",
            "changed",
            "total",
        }
    )

    for line in lines:
        stripped = line.strip()

        # Skip pure table-formatting lines: |---|---|, :---:, etc.
        if not stripped or re.fullmatch(r"[\s\|\-:\+]+", stripped):
            continue

        # Remove leading bullet / number markers: "- ", "* ", "1. "
        stripped = re.sub(r"^[\-\*\d]+\.[ \t]*", "", stripped)
        stripped = re.sub(r"^[\-\*][ \t]+", "", stripped)

        # Extract text from table rows: strip leading/trailing |, split, filter.
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped[1:-1].split("|")]
            # Skip rows that are entirely header-keyword boilerplate.
            if all(c.lower() in _header_words for c in cells if c):
                continue
            meaningful.extend(c for c in cells if c)
        else:
            meaningful.append(stripped)

    # Join with spaces and collapse runs of whitespace.
    return re.sub(r"\s+", " ", " ".join(meaningful)).strip()


def _section_content_is_hollow(
    raw_text: str,
    extra_patterns: tuple[re.Pattern[str], ...] = (),
) -> bool:
    """Return True if *raw_text* contains no substantive human-written content."""
    cleaned = _clean_markdown_content(raw_text)

    # Empty after cleaning → hollow.
    if not cleaned:
        return True

    # Too short to carry meaning.
    if len(cleaned) < MIN_SECTION_CONTENT_LENGTH:
        return True

    # Check general hollow patterns.
    for pat in HOLLOW_CONTENT_PATTERNS:
        if pat.fullmatch(cleaned):
            return True

    # Check extra (section-specific) hollow patterns.
    return any(pat.fullmatch(cleaned) for pat in extra_patterns)


def check_section_content_quality(
    pr_body: str,
    section_text_between_fn: Callable[[str, str], str],
) -> list[str]:
    """Validate the active PR contract's content sections.

    Args:
        pr_body: The full PR body text.
        section_text_between_fn: Callable(heading, body) -> section text.
            Passed in from the parent module to avoid circular imports.

    Returns a list of error messages (empty list = pass).
    """
    errors: list[str] = []

    # Existing PR bodies use the retired headings. New bodies use the
    # canonical five-section template. Keep the compatibility path narrow.
    uses_canonical = any(
        _heading_line_present(pr_body, heading) for heading in CANONICAL_CRITICAL_SECTIONS
    )
    critical_sections = CANONICAL_CRITICAL_SECTIONS if uses_canonical else LEGACY_CRITICAL_SECTIONS

    for heading in critical_sections:
        raw = section_text_between_fn(heading, pr_body)
        label = heading.removeprefix("## ")

        extra: tuple[re.Pattern[str], ...] = ()
        if heading in {"## Rollback Plan", "## Rollback"}:
            extra = ROLLBACK_HOLLOW_PATTERNS

        if _section_content_is_hollow(raw, extra):
            errors.append(
                f"{heading} section is hollow or contains only placeholder text. "
                f"Must describe substantive {label.lower()}."
            )

    return errors
