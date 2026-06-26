#!/usr/bin/env python3
"""Dangerous file change guard — hard-fail when PR touches high-risk paths without authorization.

lifecycle: permanent

Detects dangerous file path changes (Docker, migration, SQL, workflow, env, deploy,
SC-002, model/data artifacts) and requires an explicit "## Dangerous File Authorization"
section in the PR body. Also cross-validates that safety declarations do not contradict
the files actually changed.

Usage:
  from scripts.ops.helpers.dangerous_file_change_check import check_dangerous_file_changes
  errors = check_dangerous_file_changes(changed, pr_body)
"""

from __future__ import annotations

from pathlib import Path
import re

# ---- Dangerous file path categories ----

# Patterns that match dangerous paths.  Each pattern is checked via
# fnmatch-style prefix/glob matching against the changed path.
DANGEROUS_CATEGORIES: dict[str, tuple[str, ...]] = {
    "docker_or_compose": (
        "Dockerfile",
        "**/Dockerfile",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        ".devcontainer/Dockerfile",
        "deploy/Dockerfile",
        "deploy/Dockerfile*",
    ),
    "env_or_secret_config": (
        ".env",
        ".env.*",
    ),
    "sql_or_migration": (
        "*.sql",
        "database/migrations/",
        "src/database/migrations/",
        "alembic/",
        "scripts/maintenance/migrations/",
        "scripts/**/*migration*",
    ),
    "github_workflow": (".github/workflows/",),
    "deploy_or_staging": (
        "deploy/",
        "scripts/devops/",
        "scripts/ops/gatekeeper.js",
    ),
    "sc002_role_deployment": (
        "scripts/**/*sc002*",
        "scripts/**/*SC-002*",
        "scripts/**/*sc-002*",
        "scripts/ops/helpers/db_write_guard*",
        "scripts/ops/db_write_guard*",
        "scripts/ops/p0_db_write_safety_gate*",
    ),
    "model_or_data_artifact": (
        "models/",
        "data/backups/",
        "data/*.pkl",
        "data/*.joblib",
        "data/*.json",
        "data/*.csv",
    ),
}

# Human-readable labels for each category.
CATEGORY_LABELS: dict[str, str] = {
    "docker_or_compose": "Docker / Compose",
    "env_or_secret_config": ".env / secret config",
    "sql_or_migration": "SQL / Migration / Alembic",
    "github_workflow": "GitHub Actions workflow",
    "deploy_or_staging": "Deploy / Staging",
    "sc002_role_deployment": "SC-002 / DB write guard",
    "model_or_data_artifact": "Model / Data artifact",
}

# Safety-status labels that claim a category is untouched.
# Maps category -> (safety_declared_no_label, safety_status_no_label)
CATEGORY_SAFETY_LABELS: dict[str, tuple[str, str]] = {
    "docker_or_compose": (r"Docker|Compose", r"docker|compose"),
    "sql_or_migration": (r"DB\s+used|migration|SQL", r"DB\s+writes|migration|SQL"),
    "github_workflow": (r"workflow", r"workflow"),
    "deploy_or_staging": (r"staging|deploy", r"staging|deploy"),
    "sc002_role_deployment": (r"SC-002", r"SC-002"),
    "model_or_data_artifact": (
        r"model\s+artifact|training|data",
        r"training|model|data\s+expansion",
    ),
}

# Minimum line count for a valid Dangerous File Authorization section.
MIN_DANGEROUS_AUTH_SECTION_LINES = 2

# Maximum number of paths to show in error messages (before "+N more").
MAX_PATH_PREVIEW_COUNT = 5

# Patterns that indicate the Dangerous File Authorization section is hollow.
HOLLOW_DANGEROUS_AUTH_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"^N/?A$",
        r"^none\.?$",
        r"^no\s+dangerous\s+files?\.?$",
        r"^not\s+applicable\.?$",
    )
)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a glob-like pattern with * and ** to a compiled regex."""
    # Escape regex special chars except * (which we handle specially)
    # First replace **, then replace single *
    escaped = re.escape(pattern)
    # ** → match any characters including /
    escaped = escaped.replace(r"\*\*", "___DOUBLE_STAR___")
    # * → match any characters except /
    escaped = escaped.replace(r"\*", "___SINGLE_STAR___")
    # Now replace back with actual regex patterns
    escaped = escaped.replace("___DOUBLE_STAR___", r".*")
    escaped = escaped.replace("___SINGLE_STAR___", r"[^/]*")
    return re.compile("^" + escaped + "$")


def _match_dangerous_path(path: str, patterns: tuple[str, ...]) -> bool:
    """Check if *path* matches any of the dangerous patterns.

    Uses prefix matching for directory patterns, glob matching for file patterns.
    """
    for pat in patterns:
        # Directory prefix (ends with /) — use startswith for speed
        if pat.endswith("/") and path.startswith(pat):
            return True
        # Exact filename match (no / in pattern, no wildcard)
        if "/" not in pat and "*" not in pat and Path(path).name == pat:
            return True
        # Exact path prefix match (no wildcard)
        if "*" not in pat and path.startswith(pat):
            return True
        # Glob pattern — convert to regex
        if "*" in pat and _glob_to_regex(pat).match(path):
            return True
    return False
    return False


def _classify_dangerous_paths(changed: set[str]) -> dict[str, list[str]]:
    """Classify changed paths into dangerous categories.

    Returns a dict mapping category name to list of matched paths.
    """
    classified: dict[str, list[str]] = {}
    for cat, patterns in DANGEROUS_CATEGORIES.items():
        matched = sorted(p for p in changed if _match_dangerous_path(p, patterns))
        if matched:
            classified[cat] = matched
    return classified


def _section_present(pr_body: str, heading: str) -> bool:
    """Check if *heading* appears in the PR body."""
    return heading in pr_body


def _section_text(pr_body: str, start_heading: str) -> str:
    """Return text between *start_heading* and the next ## heading."""
    idx = pr_body.find(start_heading)
    if idx == -1:
        return ""
    start = idx + len(start_heading)
    suffix = pr_body[start:]
    end_marker = re.search(r"\n##\s", suffix)
    if end_marker:
        suffix = suffix[: end_marker.start()]
    return suffix


def _safety_declared_no(pr_body: str, label: str) -> bool:
    """Check if Safety Impact section declares *label* as 'no'."""
    return bool(re.search(rf"\|\s*{label}\s*\|\s*no\b", pr_body, re.IGNORECASE))


def _safety_status_no(pr_body: str, label: str) -> bool:
    """Check if Safety Status section declares no-* label as 'yes'."""
    return bool(re.search(rf"-\s*no\s+{label}\s*:\s*yes", pr_body, re.IGNORECASE))


def _has_dangerous_file_auth(pr_body: str) -> bool:
    """Check if PR body has a substantive Dangerous File Authorization section."""
    section = _section_text(pr_body, "## Dangerous File Authorization")
    if not section.strip():
        return False
    lines = [
        ln.strip()
        for ln in section.splitlines()
        if ln.strip() and not ln.strip().startswith("<!--")
    ]
    if len(lines) < MIN_DANGEROUS_AUTH_SECTION_LINES:
        return False
    # Check that the first non-comment line isn't just a hollow placeholder
    for line in lines:
        for pat in HOLLOW_DANGEROUS_AUTH_PATTERNS:
            if pat.match(line):
                return False
    return True


def _pr_declares_docs_only(pr_body: str) -> bool:
    """Check if PR body declares a docs-only task type."""
    return bool(
        re.search(r"Task type\s*\|\s*docs-only", pr_body, re.IGNORECASE)
        or re.search(r"docs-only", pr_body, re.IGNORECASE)
    )


def _pr_declares_no_db(pr_body: str) -> bool:
    """Check if PR body declares no DB involvement."""
    safety_section = _section_text(pr_body, "## Safety Impact")
    safety_status = _section_text(pr_body, "## Safety Status")
    combined = (safety_section or "") + "\n" + (safety_status or "")
    return bool(
        re.search(r"\|\s*DB\s+used\s*\|\s*no\b", combined, re.IGNORECASE)
        or re.search(r"-\s*no\s+DB\s+writes\s*:\s*yes", combined, re.IGNORECASE)
        or re.search(r"-\s*no\s+migration\s*:\s*yes", combined, re.IGNORECASE)
    )


def _pr_declares_no_docker(pr_body: str) -> bool:
    """Check if PR body declares no Docker changes."""
    return bool(
        re.search(r"\|\s*Docker\s+used\s*\|\s*no\b", pr_body, re.IGNORECASE)
        or re.search(r"-\s*no\s+docker\s*:\s*yes", pr_body, re.IGNORECASE)
    )


def _pr_declares_no_workflow(pr_body: str) -> bool:
    """Check if PR body declares no workflow changes."""
    return bool(
        re.search(r"\|\s*workflow\s+changed\s*\|\s*no\b", pr_body, re.IGNORECASE)
        or re.search(r"-\s*no\s+workflow\s+change\s*:\s*yes", pr_body, re.IGNORECASE)
    )


def _pr_declares_no_migration(pr_body: str) -> bool:
    """Check if PR body declares no migration/SQL changes."""
    return bool(
        re.search(r"\|\s*migration\s+used\s*\|\s*no\b", pr_body, re.IGNORECASE)
        or re.search(r"-\s*no\s+migration\s*:\s*yes", pr_body, re.IGNORECASE)
        or re.search(r"-\s*no\s+SQL\s*:\s*yes", pr_body, re.IGNORECASE)
    )


# Path prefixes that indicate business/implementation code (as opposed to docs/governance).
BUSINESS_CODE_PREFIXES: tuple[str, ...] = (
    "src/",
    "scripts/ops/",
    "scripts/data/",
    "config/",
)


def _touches_business_code(changed: set[str]) -> bool:
    """Check if any changed paths are under business code directories."""
    return any(
        any(p.startswith(prefix) for prefix in BUSINESS_CODE_PREFIXES)
        and not p.startswith("scripts/ops/helpers/")  # helpers are governance
        and not p.startswith("scripts/ops/ai_workflow_gate")  # gate itself is governance
        for p in changed
    )


def check_dangerous_file_changes(
    changed: set[str],
    pr_body: str,
) -> list[str]:
    """Check dangerous file paths and return a list of error strings.

    Rules:
    1. Safety declaration contradictions are checked FIRST, regardless of
       dangerous file classification or authorization status.
       a. docs-only PRs touching business code paths fail.
       b. no-DB declarations touching migration/SQL paths fail.
       c. no-Docker declarations touching Docker/Compose paths fail.
    2. Dangerous path changes WITHOUT a "## Dangerous File Authorization"
       section fail with details.
    """
    errors: list[str] = []

    classified = _classify_dangerous_paths(changed)

    # ---- Rule 1: Contradictory safety declarations (always checked) ----

    # 1a: docs-only claim + business code changed
    if _pr_declares_docs_only(pr_body) and _touches_business_code(changed):
        biz_paths = sorted(
            p
            for p in changed
            if any(p.startswith(px) for px in BUSINESS_CODE_PREFIXES)
            and not p.startswith("scripts/ops/helpers/")
            and not p.startswith("scripts/ops/ai_workflow_gate")
        )
        errors.append(
            "PR declares docs-only task type but changes business code paths: "
            + ", ".join(biz_paths[:MAX_PATH_PREVIEW_COUNT])
            + (
                f" (+{len(biz_paths) - MAX_PATH_PREVIEW_COUNT} more)"
                if len(biz_paths) > MAX_PATH_PREVIEW_COUNT
                else ""
            )
            + ". Docs-only PRs must not modify src/ or scripts/ops/ runtime paths."
        )

    # 1b: no-DB claim + migration/SQL changed
    if "sql_or_migration" in classified and _pr_declares_no_db(pr_body):
        errors.append(
            "PR declares no DB / no migration but changes SQL/migration paths: "
            + ", ".join(classified["sql_or_migration"][:MAX_PATH_PREVIEW_COUNT])
            + ". Remove the contradictory safety declaration or remove the "
            "migration/SQL changes."
        )

    # 1c: no-Docker claim + Docker/Compose changed
    if "docker_or_compose" in classified and _pr_declares_no_docker(pr_body):
        errors.append(
            "PR declares no Docker changes but modifies Docker/Compose files: "
            + ", ".join(classified["docker_or_compose"][:MAX_PATH_PREVIEW_COUNT])
            + ". Remove the contradictory safety declaration or remove the "
            "Docker/Compose changes."
        )

    # ---- Rule 2: Dangerous files require authorization ----

    if not classified:
        return errors

    has_auth = _has_dangerous_file_auth(pr_body)
    if not has_auth:
        for cat, paths in classified.items():
            label = CATEGORY_LABELS.get(cat, cat)
            errors.append(
                f"Dangerous file change without authorization: "
                f"{label} — {', '.join(paths[:MAX_PATH_PREVIEW_COUNT])}"
                + (
                    f" (+{len(paths) - MAX_PATH_PREVIEW_COUNT} more)"
                    if len(paths) > MAX_PATH_PREVIEW_COUNT
                    else ""
                )
                + ". Add a '## Dangerous File Authorization' section to the PR body "
                "explaining why these files must be changed, user authorization, "
                "rollback plan, and validation plan."
            )

    return errors
