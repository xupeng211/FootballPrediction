#!/usr/bin/env python3
"""A-L PR authorization matrix blocking rules — extracted from pr_authorization_matrix.py.

lifecycle: permanent

Contains narrow_blocking_errors() with the G1-expanded rule set (A-L).
Extracted to keep pr_authorization_matrix.py under the 800-line gatekeeper limit.

Usage:
  from scripts.ops.helpers.pr_authorization_rules import narrow_blocking_errors
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.ops.helpers.pr_authorization_matrix import AuthorizationResult


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
    # Lazy imports to break circular dependency with pr_authorization_matrix.
    from scripts.ops.helpers.pr_authorization_matrix import (  # noqa: PLC0415
        CATEGORY_DB_MIGRATION_SQL,
        CATEGORY_DOCKER_DEPLOY,
        CATEGORY_DOCS,
        CATEGORY_ENV_SECRET,
        CATEGORY_RUNTIME_CONFIG,
        CATEGORY_SC002_DB_GOVERNANCE,
        CATEGORY_SOURCE,
        CATEGORY_TESTS,
        CATEGORY_UNKNOWN,
        CATEGORY_WORKFLOW_GOVERNANCE,
        TASK_TYPE_AUDIT_ONLY,
        TASK_TYPE_CONFIG_RUNTIME,
        TASK_TYPE_DB_MIGRATION_SQL,
        TASK_TYPE_DOCS_ONLY,
        TASK_TYPE_MERGE_ONLY,
        TASK_TYPE_SOURCE_CODE,
        TASK_TYPE_TEST_ONLY,
        TASK_TYPE_UNKNOWN,
        TASK_TYPE_WORKFLOW_GOVERNANCE,
    )

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
