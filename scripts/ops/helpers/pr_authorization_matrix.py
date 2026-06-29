#!/usr/bin/env python3
"""Task-level PR authorization matrix — pure classifier, parser, and validator.

lifecycle: permanent

Provides path classification, PR body task-type/authorization parsing, and
deterministic validation without side effects.  This helper is not yet wired
into ``scripts/ops/ai_workflow_gate.py`` and does not change current CI
behaviour.

Usage::

    from scripts.ops.helpers.pr_authorization_matrix import (
        classify_path,
        classify_paths,
        parse_task_type,
        parse_authorized_paths,
        validate_authorization,
        AuthorizationResult,
    )
"""

from __future__ import annotations

from collections.abc import Iterable  # noqa: TC003
from dataclasses import dataclass, field
from pathlib import Path
import re

# ============================================================================
# Task types
# ============================================================================

TASK_TYPE_DOCS_ONLY = "docs-only"
TASK_TYPE_TEST_ONLY = "test-only"
TASK_TYPE_SOURCE_CODE = "source-code"
TASK_TYPE_CONFIG_RUNTIME = "config-runtime"
TASK_TYPE_DOCKER_DEPLOY = "docker-deploy"
TASK_TYPE_WORKFLOW_GOVERNANCE = "workflow-governance"
TASK_TYPE_DB_MIGRATION_SQL = "db-migration-sql"
TASK_TYPE_SC002_DB_GOVERNANCE = "sc-002-db-governance"
TASK_TYPE_MODEL_ARTIFACT = "model-artifact"
TASK_TYPE_DATA_ARTIFACT = "data-artifact"
TASK_TYPE_MIXED = "mixed"
TASK_TYPE_AUDIT_ONLY = "audit-only"
TASK_TYPE_MERGE_ONLY = "merge-only"
TASK_TYPE_UNKNOWN = "unknown"

KNOWN_TASK_TYPES: frozenset[str] = frozenset(
    (
        TASK_TYPE_DOCS_ONLY,
        TASK_TYPE_TEST_ONLY,
        TASK_TYPE_SOURCE_CODE,
        TASK_TYPE_CONFIG_RUNTIME,
        TASK_TYPE_DOCKER_DEPLOY,
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        TASK_TYPE_DB_MIGRATION_SQL,
        TASK_TYPE_SC002_DB_GOVERNANCE,
        TASK_TYPE_MODEL_ARTIFACT,
        TASK_TYPE_DATA_ARTIFACT,
        TASK_TYPE_MIXED,
        TASK_TYPE_AUDIT_ONLY,
        TASK_TYPE_MERGE_ONLY,
    )
)

# Task types that MUST have Dangerous File Authorization to be valid.
_TASK_TYPES_REQUIRING_DANGEROUS_AUTH: frozenset[str] = frozenset(
    (
        TASK_TYPE_DOCKER_DEPLOY,
        TASK_TYPE_WORKFLOW_GOVERNANCE,
        TASK_TYPE_DB_MIGRATION_SQL,
        TASK_TYPE_SC002_DB_GOVERNANCE,
        TASK_TYPE_MODEL_ARTIFACT,
        TASK_TYPE_DATA_ARTIFACT,
        TASK_TYPE_MIXED,
    )
)

# Task types that allow each category.
# Missing category → forbidden for that task type (unless "mixed").
_TASK_TYPE_ALLOWED_CATEGORIES: dict[str, frozenset[str]] = {
    TASK_TYPE_DOCS_ONLY: frozenset({"docs", "workflow-governance"}),
    TASK_TYPE_TEST_ONLY: frozenset({"tests"}),
    TASK_TYPE_SOURCE_CODE: frozenset({"source", "tests", "docs"}),
    TASK_TYPE_CONFIG_RUNTIME: frozenset({"runtime-config", "tests", "docs"}),
    TASK_TYPE_DOCKER_DEPLOY: frozenset({"docker-deploy", "tests", "docs"}),
    TASK_TYPE_WORKFLOW_GOVERNANCE: frozenset({"workflow-governance", "tests", "docs"}),
    TASK_TYPE_DB_MIGRATION_SQL: frozenset({"db-migration-sql", "tests", "docs"}),
    TASK_TYPE_SC002_DB_GOVERNANCE: frozenset({"sc-002-db-governance", "tests", "docs"}),
    # audit-only: no file changes allowed (empty allowed set).
    # Any repo file change is a violation.
    TASK_TYPE_AUDIT_ONLY: frozenset(),
    # merge-only: only docs allowed (merge documentation).
    TASK_TYPE_MERGE_ONLY: frozenset({"docs"}),
    # model-artifact, data-artifact, mixed, unknown: handled specially below.
}


# ============================================================================
# Path categories
# ============================================================================

CATEGORY_DOCS = "docs"
CATEGORY_TESTS = "tests"
CATEGORY_SOURCE = "source"
CATEGORY_RUNTIME_CONFIG = "runtime-config"
CATEGORY_DOCKER_DEPLOY = "docker-deploy"
CATEGORY_WORKFLOW_GOVERNANCE = "workflow-governance"
CATEGORY_DB_MIGRATION_SQL = "db-migration-sql"
CATEGORY_SC002_DB_GOVERNANCE = "sc-002-db-governance"
CATEGORY_MODEL_ARTIFACT = "model-artifact"
CATEGORY_DATA_ARTIFACT = "data-artifact"
CATEGORY_ENV_SECRET = "env-secret"
CATEGORY_UNKNOWN = "unknown"

# Mapping: category -> tuple of glob/prefix patterns.
# Patterns ending with ``/`` are prefix-matched; otherwise glob-matched
# (``*`` and ``**`` wildcards supported).
_PATH_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    CATEGORY_DOCS: (
        "docs/**",
        "README*",
        "AGENTS.md",
        "CLAUDE.md",
        "*.md",
    ),
    CATEGORY_TESTS: ("tests/**",),
    CATEGORY_SOURCE: ("src/**",),
    CATEGORY_RUNTIME_CONFIG: (
        "pyproject.toml",
        "ruff.toml",
        "mypy.ini",
        "config/**",
    ),
    CATEGORY_DOCKER_DEPLOY: (
        "Dockerfile",
        "**/Dockerfile",
        "Dockerfile.*",
        "deploy/docker/**",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "compose*.yml",
        "compose*.yaml",
        ".devcontainer/**",
    ),
    CATEGORY_WORKFLOW_GOVERNANCE: (
        ".github/workflows/**",
        ".github/CODEOWNERS",
        ".github/pull_request_template.md",
        "scripts/ops/ai_workflow_gate.py",
        "scripts/ops/helpers/**",
        "scripts/devops/**",
        "scripts/**/*gate*",
        "scripts/**/*guard*",
        "scripts/**/*preflight*",
        "docs/AGENT_WORKFLOW.md",
        "docs/CODEX_WORKFLOW.md",
        "docs/DOCUMENTATION_GOVERNANCE.md",
    ),
    CATEGORY_DB_MIGRATION_SQL: (
        "migrations/**",
        "alembic/**",
        "database/migrations/**",
        "src/database/migrations/**",
        "*.sql",
        "deploy/docker/init*.sql",
        "**/*.sql",
    ),
    CATEGORY_SC002_DB_GOVERNANCE: (
        "scripts/**/*sc002*",
        "scripts/**/*SC-002*",
        "scripts/**/*sc-002*",
        "scripts/ops/helpers/db_write_guard*",
        "scripts/ops/db_write_guard*",
        "scripts/ops/p0_db_write_safety_gate*",
        "config/python_db_write_allowlist.json",
    ),
    CATEGORY_MODEL_ARTIFACT: (
        "models/**",
        "model_zoo/**",
        "*.joblib",
        "*.pkl",
    ),
    CATEGORY_DATA_ARTIFACT: (
        "data/**",
        "artifacts/**",
    ),
    CATEGORY_ENV_SECRET: (
        ".env",
        ".env.*",
    ),
}

# ---- internal glob helpers ----


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a glob-like pattern (``*``, ``**``) to a compiled regex.

    ``*`` matches within a single path segment; ``**`` matches across segments.
    """
    escaped = re.escape(pattern)
    # ** → match any characters including /
    escaped = escaped.replace(r"\*\*", "___D_STAR___")
    # * → match any characters except /
    escaped = escaped.replace(r"\*", "___S_STAR___")
    escaped = escaped.replace("___D_STAR___", r".*")
    escaped = escaped.replace("___S_STAR___", r"[^/]*")
    return re.compile("^" + escaped + "$")


def _match_category_pattern(path: str, pattern: str) -> bool:
    """Return True if *path* matches *pattern* (prefix or glob)."""
    # Directory prefix — path starts with
    if pattern.endswith("/"):
        return path.startswith(pattern)
    # No wildcards — check exact filename or prefix
    if "*" not in pattern:
        if "/" not in pattern:
            return Path(path).name == pattern
        return path.startswith(pattern)
    # Wildcard — compile and match
    return bool(_glob_to_regex(pattern).match(path))


# ============================================================================
# Public API: path classification
# ============================================================================


def classify_path(path: str) -> set[str]:
    """Classify a single changed path into zero or more path categories.

    Every path gets *at least* ``"unknown"`` if it matches no known category.
    """
    categories: set[str] = set()
    for cat, patterns in _PATH_CATEGORY_PATTERNS.items():
        if any(_match_category_pattern(path, p) for p in patterns):
            categories.add(cat)
    if not categories:
        categories.add(CATEGORY_UNKNOWN)
    return categories


def classify_paths(paths: Iterable[str]) -> dict[str, set[str]]:
    """Classify multiple changed paths into a ``{category: {path, ...}}`` map.

    Paths that match no known category appear under ``"unknown"``.
    """
    result: dict[str, set[str]] = {}
    for p in paths:
        for cat in classify_path(p):
            result.setdefault(cat, set()).add(p)
    return result


# ============================================================================
# Public API: PR body parsing
# ============================================================================


# Match a Scope table row like ``| Task type | docs-only |``.
_SCOPE_TASK_TYPE_RE = re.compile(r"\|\s*Task\s+type\s*\|\s*([^\s|]+)\s*\|", re.IGNORECASE)

# Match a checked PR Type checklist item: ``- [x] docs-only``.
_PR_TYPE_CHECK_RE = re.compile(r"-\s*\[x\]\s*([^\s]+)", re.IGNORECASE)


def _section_text(pr_body: str, start_heading: str) -> str:
    """Return text between *start_heading* and the next ``## `` heading."""
    idx = pr_body.find(start_heading)
    if idx == -1:
        return ""
    start = idx + len(start_heading)
    suffix = pr_body[start:]
    end_marker = re.search(r"\n##\s", suffix)
    if end_marker:
        suffix = suffix[: end_marker.start()]
    return suffix


def parse_task_type(pr_body: str) -> str:
    """Extract the declared task type from a PR body.

    Priority:
    1. ``| Task type | ... |`` row in the Scope section.
    2. First checked item in a ``## PR Type`` checklist.

    Returns ``"unknown"`` if no declaration is found, or ``"mixed"`` if
    multiple checked PR Types exist without a clear Scope declaration.
    """
    # 1. Scope table
    scope_match = _SCOPE_TASK_TYPE_RE.search(pr_body)
    if scope_match:
        raw = scope_match.group(1).strip().lower()
        if raw in KNOWN_TASK_TYPES:
            return raw
        # Still return what was declared even if not in the known set —
        # the caller can decide whether to treat it as unknown.
        return raw

    # 2. PR Type checklist — look inside the ## PR Type section
    pr_type_section = _section_text(pr_body, "## PR Type")
    if not pr_type_section:
        # Fall back to searching the whole body for checked types
        pr_type_section = pr_body

    checked = _PR_TYPE_CHECK_RE.findall(pr_type_section)
    known_checked = [t.lower() for t in checked if t.lower() in KNOWN_TASK_TYPES]

    if not known_checked:
        # Check if any of the matched values might be task types not in KNOWN
        if checked:
            return checked[0].lower()
        return TASK_TYPE_UNKNOWN

    if len(known_checked) == 1:
        return known_checked[0]

    return TASK_TYPE_MIXED


def parse_authorized_paths(pr_body: str) -> set[str]:  # noqa: C901
    """Extract explicitly authorized paths from a PR body.

    Looks in ``## Dangerous File Authorization`` (and the future
    ``## PR Authorization``) for:

    * Table rows: ``| Authorized paths | path1, path2 |``
    * Bullet lines: ``- Authorized paths: path1, path2``
    * Backtick-quoted paths: `` `path/to/file` ``

    Returns a (possibly empty) set of paths.
    """
    paths: set[str] = set()

    # Gather text from both sections
    sections = ""
    for heading in ("## Dangerous File Authorization", "## PR Authorization"):
        sections += _section_text(pr_body, heading) + "\n"

    if not sections.strip():
        return paths

    # 1. Table rows: | Authorized paths | path1, path2 |
    for m in re.finditer(
        r"\|\s*Authorized\s+paths\s*\|\s*([^|]+)\s*\|",
        sections,
        re.IGNORECASE,
    ):
        cell = m.group(1).strip()
        for token in re.split(r"[,;]+", cell):
            cleaned = token.strip().strip("`\"'")
            if cleaned:
                paths.add(cleaned)

    # 2. Bullet: - Authorized paths: path1, path2
    for m in re.finditer(
        r"-\s*Authorized\s+paths\s*:\s*(.+)",
        sections,
        re.IGNORECASE,
    ):
        line = m.group(1).strip()
        for token in re.split(r"[,;]+", line):
            cleaned = token.strip().strip("`\"'")
            if cleaned:
                paths.add(cleaned)

    # 3. Backtick paths in the section
    for m in re.finditer(r"`([^`]+)`", sections):
        part = m.group(1).strip()
        # Only capture things that look like file paths (contain /)
        if "/" in part and not part.startswith("http"):
            paths.add(part)

    return paths


def _has_dangerous_file_auth(pr_body: str) -> bool:
    """Check whether the PR body has a substantive Dangerous File Authorization section."""
    _min_dangerous_auth_lines = 2

    section = _section_text(pr_body, "## Dangerous File Authorization")
    if not section.strip():
        return False

    lines = [
        ln.strip()
        for ln in section.splitlines()
        if ln.strip() and not ln.strip().startswith("<!--")
    ]
    if len(lines) < _min_dangerous_auth_lines:
        return False

    # Reject hollow placeholders like "N/A" or "none"
    hollow = re.compile(
        r"^(?:N/?A|none\.?|no\s+dangerous\s+files?\.?|not\s+applicable\.?)$",
        re.IGNORECASE,
    )
    return all(not hollow.match(line) for line in lines)


# ============================================================================
# Validation result
# ============================================================================


@dataclass(frozen=True)
class AuthorizationResult:
    """Result of validating a PR against the task-level authorization matrix.

    Attributes:
        task_type: The extracted / resolved task type.
        categories: ``{category: {path, ...}}`` map for all changed paths.
        errors: Fatal authorization failures.
        warnings: Non-fatal concerns (e.g. ``"mixed"`` task type).
        has_dangerous_auth: Whether a substantive Dangerous File Authorization
            section was detected.
        authorized_paths: Paths explicitly listed in the authorization section.
    """

    task_type: str
    categories: dict[str, frozenset[str]] = field(default_factory=dict)
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    has_dangerous_auth: bool = False
    authorized_paths: frozenset[str] = field(default_factory=frozenset)

    @property
    def valid(self) -> bool:
        """Return True when no fatal authorization errors exist."""
        return len(self.errors) == 0


# ============================================================================
# Public API: validation
# ============================================================================


def validate_authorization(  # noqa: C901
    task_type: str,
    changed_paths: Iterable[str],
    pr_body: str = "",
) -> AuthorizationResult:
    """Validate *changed_paths* against *task_type* and (optionally) *pr_body*.

    This is the main entry-point for the PR authorization matrix.  It:
    1. Classifies every changed path.
    2. Checks whether the declared task type permits every detected category.
    3. Requires Dangerous File Authorization when the task type demands it.
    4. Blocks ``unknown`` task types.
    5. Flags ``env-secret`` touches.

    Returns an :class:`AuthorizationResult` — check ``.errors`` to decide
    whether the PR passes the matrix.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Resolve task type
    resolved_task = task_type.strip().lower() if task_type else TASK_TYPE_UNKNOWN

    # Classify
    cat_map = classify_paths(changed_paths)
    frozen_cats: dict[str, frozenset[str]] = {
        cat: frozenset(paths) for cat, paths in cat_map.items()
    }
    detected_categories = set(frozen_cats.keys())

    # Parse dangerous auth
    has_auth = _has_dangerous_file_auth(pr_body) if pr_body else False
    authorized = parse_authorized_paths(pr_body) if pr_body else set()

    # ---- env-secret is always a hard error ----
    if CATEGORY_ENV_SECRET in detected_categories:
        errors.append(
            "env-secret files changed ({}): .env / .env.* must never be "
            "committed to the repository.".format(
                ", ".join(sorted(frozen_cats.get(CATEGORY_ENV_SECRET, frozenset())))
            )
        )

    # ---- unknown task type → error ----
    if resolved_task not in KNOWN_TASK_TYPES and resolved_task != TASK_TYPE_UNKNOWN:
        warnings.append(f"Unrecognized task type '{resolved_task}'; treating as unknown.")
        resolved_task = TASK_TYPE_UNKNOWN

    if resolved_task == TASK_TYPE_UNKNOWN:
        errors.append(
            "No task type declared in PR body.  Add '| Task type | <type> |' "
            "to the Scope section or check a PR Type, then re-run."
        )
        return AuthorizationResult(
            task_type=resolved_task,
            categories=frozen_cats,
            errors=tuple(errors),
            warnings=tuple(warnings),
            has_dangerous_auth=has_auth,
            authorized_paths=frozenset(authorized),
        )

    # ---- mixed task type → warning, requires dangerous auth ----
    if resolved_task == TASK_TYPE_MIXED:
        warnings.append(
            "Mixed task type declared; requiring Dangerous File Authorization "
            "for any cross-category changes."
        )
        if not has_auth:
            errors.append(
                "Mixed task type requires a substantive '## Dangerous File Authorization' section."
            )

    # ---- dangerous-auth-required task types ----
    elif resolved_task in _TASK_TYPES_REQUIRING_DANGEROUS_AUTH:
        if not has_auth:
            errors.append(
                f"Task type '{resolved_task}' requires a substantive "
                "'## Dangerous File Authorization' section."
            )

    # ---- model-artifact / data-artifact: block cross-contamination ----
    if resolved_task in (TASK_TYPE_MODEL_ARTIFACT, TASK_TYPE_DATA_ARTIFACT):
        forbidden_cats = {
            CATEGORY_SOURCE,
            CATEGORY_DOCKER_DEPLOY,
            CATEGORY_DB_MIGRATION_SQL,
            CATEGORY_WORKFLOW_GOVERNANCE,
            CATEGORY_SC002_DB_GOVERNANCE,
        }
        contaminated = detected_categories & forbidden_cats
        if contaminated:
            errors.append(
                f"Task type '{resolved_task}' must not touch: "
                + ", ".join(sorted(contaminated))
                + ".  Affected paths: "
                + ", ".join(
                    sorted(p for c in contaminated for p in (frozen_cats.get(c, frozenset())))
                )
            )

    # ---- category-vs-task-type enforcement ----
    allowed = _TASK_TYPE_ALLOWED_CATEGORIES.get(
        resolved_task,
        frozenset(),  # unknown types handled above
    )
    if allowed:
        disallowed = detected_categories - {CATEGORY_UNKNOWN} - allowed
        if disallowed:
            errors.append(
                f"Task type '{resolved_task}' allows only categories: "
                + ", ".join(sorted(allowed))
                + ".  Detected disallowed: "
                + ", ".join(sorted(disallowed))
                + ".  Affected paths: "
                + ", ".join(
                    sorted(p for c in disallowed for p in (frozen_cats.get(c, frozenset())))
                )
            )

    return AuthorizationResult(
        task_type=resolved_task,
        categories=frozen_cats,
        errors=tuple(errors),
        warnings=tuple(warnings),
        has_dangerous_auth=has_auth,
        authorized_paths=frozenset(authorized),
    )


# ============================================================================
# Narrow blocking selector (#1651 Phase 5R8-G)
# ============================================================================


def narrow_blocking_errors(result: AuthorizationResult) -> tuple[str, ...]:  # noqa: C901, PLR0912, PLR0915
    """Return a narrow, low-false-positive subset of matrix errors suitable for
    gated blocking enforcement.

    Rules (G1 expanded from original A-D to A-L):

    * A. unknown task type
    * B. docs-only task touching source files
    * C. test-only task touching source files
    * D. env-secret files present
    * E. docs-only task touching tests/workflow/docker/db-migration/sc-002/config
    * F. test-only task touching workflow/docker/db-migration/sc-002/config
    * G. source-code task touching workflow/docker/db-migration/sc-002/env-secret
    * H. workflow-governance task touching source/config/docker/db-migration
    * I. audit-only task with any repo file change
    * J. merge-only task touching non-docs files
    * K. config-runtime task touching source/workflow/docker/db-migration
    * L. db-migration-sql task touching source/workflow/docker

    The ``unknown`` path category is intentionally excluded — it would produce
    false positives from CI workspace transient files.
    """
    errors: list[str] = []
    categories = set(result.categories.keys())
    # Exclude unknown paths from all checks — they are CI workspace transient files.
    real_categories = categories - {CATEGORY_UNKNOWN}

    # Categories that represent infrastructure/governance — source-code PRs
    # should not touch these.
    _governance_infra_categories: frozenset[str] = frozenset(
        {
            CATEGORY_WORKFLOW_GOVERNANCE,
            CATEGORY_DOCKER_DEPLOY,
            CATEGORY_DB_MIGRATION_SQL,
            CATEGORY_SC002_DB_GOVERNANCE,
        }
    )

    # Categories that represent business/implementation code — governance PRs
    # should not touch these.
    _business_categories: frozenset[str] = frozenset(
        {
            CATEGORY_SOURCE,
            CATEGORY_RUNTIME_CONFIG,
        }
    )

    # ---- A. unknown task type ----
    if result.task_type == TASK_TYPE_UNKNOWN:
        errors.append(
            "PR authorization matrix (A): unknown task type — "
            "must declare task type in PR body (see PR template)."
        )

    # ---- D. env-secret files (always blocked, high priority) ----
    if CATEGORY_ENV_SECRET in categories:
        paths = sorted(result.categories.get(CATEGORY_ENV_SECRET, frozenset()))
        errors.append(
            f"PR authorization matrix (D): env-secret files must not be committed: "
            f"{', '.join(paths)}"
        )

    # ---- B. docs-only touching source ----
    if result.task_type == TASK_TYPE_DOCS_ONLY and CATEGORY_SOURCE in categories:
        paths = sorted(result.categories.get(CATEGORY_SOURCE, frozenset()))
        errors.append(
            f"PR authorization matrix (B): docs-only PR touches source files: {', '.join(paths)}"
        )

    # ---- C. test-only touching source ----
    if result.task_type == TASK_TYPE_TEST_ONLY and CATEGORY_SOURCE in categories:
        paths = sorted(result.categories.get(CATEGORY_SOURCE, frozenset()))
        errors.append(
            f"PR authorization matrix (C): test-only PR touches source files: {', '.join(paths)}"
        )

    # ---- E. docs-only touching other non-docs, non-governance categories ----
    if result.task_type == TASK_TYPE_DOCS_ONLY:
        disallowed = real_categories - {CATEGORY_DOCS, CATEGORY_WORKFLOW_GOVERNANCE}
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (E): docs-only PR must not touch: "
                f"{', '.join(sorted(disallowed))}. Affected paths: {', '.join(all_paths)}"
            )

    # ---- F. test-only touching non-tests categories ----
    if result.task_type == TASK_TYPE_TEST_ONLY:
        disallowed = real_categories - {CATEGORY_TESTS}
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (F): test-only PR must not touch: "
                f"{', '.join(sorted(disallowed))}. Affected paths: {', '.join(all_paths)}"
            )

    # ---- G. source-code touching governance/infrastructure categories ----
    if result.task_type == TASK_TYPE_SOURCE_CODE:
        disallowed = real_categories & _governance_infra_categories | (
            {CATEGORY_ENV_SECRET} if CATEGORY_ENV_SECRET in categories else set()
        )
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (G): source-code PR must not touch "
                f"governance/infrastructure paths: {', '.join(sorted(disallowed))}. "
                f"Affected paths: {', '.join(all_paths)}. "
                f"Use workflow-governance, docker-deploy, or db-migration-sql task type "
                f"with Dangerous File Authorization."
            )

    # ---- H. workflow-governance touching business categories ----
    if result.task_type == TASK_TYPE_WORKFLOW_GOVERNANCE:
        disallowed = real_categories & _business_categories | (
            real_categories & {CATEGORY_DOCKER_DEPLOY, CATEGORY_DB_MIGRATION_SQL}
        )
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (H): workflow-governance PR must not touch "
                f"business/infrastructure paths: {', '.join(sorted(disallowed))}. "
                f"Affected paths: {', '.join(all_paths)}. "
                f"Workflow-governance PRs are limited to governance scripts, tests, and docs."
            )

    # ---- I. audit-only with any repo file change ----
    if result.task_type == TASK_TYPE_AUDIT_ONLY and real_categories:
        all_paths: list[str] = []
        for cat in sorted(real_categories):
            all_paths.extend(sorted(result.categories.get(cat, frozenset())))
        errors.append(
            f"PR authorization matrix (I): audit-only PR must not change any repo files. "
            f"Audit reports should be written to /tmp, not committed. "
            f"Detected changes in: {', '.join(sorted(real_categories))}. "
            f"Affected paths: {', '.join(all_paths)}"
        )

    # ---- J. merge-only touching non-docs files ----
    if result.task_type == TASK_TYPE_MERGE_ONLY:
        disallowed = real_categories - {CATEGORY_DOCS}
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (J): merge-only PR must not include "
                f"new development changes beyond docs. "
                f"Detected: {', '.join(sorted(disallowed))}. "
                f"Affected paths: {', '.join(all_paths)}"
            )

    # ---- K. config-runtime touching source/workflow/docker/db-migration ----
    if result.task_type == TASK_TYPE_CONFIG_RUNTIME:
        disallowed = real_categories & (_business_categories | _governance_infra_categories)
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (K): config-runtime PR must not touch: "
                f"{', '.join(sorted(disallowed))}. "
                f"Affected paths: {', '.join(all_paths)}."
            )

    # ---- L. db-migration-sql touching source/workflow/docker ----
    if result.task_type == TASK_TYPE_DB_MIGRATION_SQL:
        disallowed = real_categories & (
            {
                CATEGORY_SOURCE,
                CATEGORY_WORKFLOW_GOVERNANCE,
                CATEGORY_DOCKER_DEPLOY,
                CATEGORY_RUNTIME_CONFIG,
            }
        )
        if disallowed:
            all_paths: list[str] = []
            for cat in sorted(disallowed):
                all_paths.extend(sorted(result.categories.get(cat, frozenset())))
            errors.append(
                f"PR authorization matrix (L): db-migration-sql PR must not touch "
                f"non-migration paths: {', '.join(sorted(disallowed))}. "
                f"Affected paths: {', '.join(all_paths)}."
            )

    return tuple(errors)


# ============================================================================
# Report-only gate integration (#1651 Phase 5R8-D)
# ============================================================================


def run_pr_authorization_matrix_report_only(
    changed: set[str],
    pr_body: str,
) -> None:
    """Run #1651 PR authorization matrix in report-only mode.

    Prints matrix findings to stdout.  Matrix errors are NEVER added to the gate
    error list in this phase.  Exceptions are caught and reported as internal-errors
    without failing the gate.

    Intended to be called from ``scripts/ops/ai_workflow_gate.py``.
    """

    if not changed or not pr_body:
        return

    print("[PR Authorization Matrix][report-only] running #1651 matrix validation")

    try:
        task_type = parse_task_type(pr_body)
        result = validate_authorization(task_type, changed, pr_body=pr_body)
        _print_matrix_result(result)
    except Exception as exc:
        print(f"[PR Authorization Matrix][report-only][internal-error] {exc}")
        print(
            "[PR Authorization Matrix][report-only] internal errors are non-blocking in this phase."
        )


def _print_matrix_result(result: AuthorizationResult) -> None:
    """Print an AuthorizationResult to stdout in report-only format."""

    print(
        f"[PR Authorization Matrix][report-only] "
        f"task_type={result.task_type} "
        f"categories={sorted(result.categories.keys())}"
    )

    if result.task_type == TASK_TYPE_UNKNOWN:
        print(
            "[PR Authorization Matrix][report-only][warning] "
            "task type is unknown — matrix validation skipped"
        )
    elif result.has_dangerous_auth:
        print("[PR Authorization Matrix][report-only] Dangerous File Authorization detected")

    if result.warnings:
        for w in result.warnings:
            print(f"[PR Authorization Matrix][report-only][warning] {w}")

    if result.errors:
        for e in result.errors:
            print(f"[PR Authorization Matrix][report-only][error] {e}")

    if result.valid:
        label = "pass" if result.task_type != TASK_TYPE_UNKNOWN else "unknown-task-type"
        print(f"[PR Authorization Matrix][report-only] matrix validation result: {label}")
    else:
        print(
            "[PR Authorization Matrix][report-only] "
            f"matrix validation result: {len(result.errors)} error(s) found"
        )

    print(
        "[PR Authorization Matrix][report-only] "
        "matrix errors are currently non-blocking (#1651 Phase 5R8-D report-only)"
    )
