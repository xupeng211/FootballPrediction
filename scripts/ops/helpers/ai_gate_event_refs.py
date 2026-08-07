#!/usr/bin/env python3
"""Event-to-base/head ref selection for the AI Workflow Gate incremental diff.

lifecycle: permanent
task: fix_production_gate_workflow_dispatch_base_head_resolution

The Production Gate (production-gate.yml) must compare each triggering event
against a deterministic base/head pair.  The three supported event types
expose different ref fields:

- pull_request:      base = pr.base.sha,        head = pr.head.sha
- push:              base = event.before,       head = event.after
- workflow_dispatch: base = explicit base_sha input (REQUIRED); head = the
                     dispatched commit (GITHUB_SHA) — the exact revision that
                     actions/checkout checked out and tested.

Contracts enforced here (all fail-closed):

- Every ref must be a full 40-hex commit SHA (^[0-9a-fA-F]{40}$).  Short
  SHAs, HEAD, branch names, tags, refs/heads/*, whitespace, newlines and
  shell syntax are rejected before any git use.
- workflow_dispatch head MUST equal the environment GITHUB_SHA (defense in
  depth: the AI Gate can never analyze a revision different from the
  checked-out one).  A missing or malformed GITHUB_SHA is a hard failure —
  there is NO literal "HEAD" fallback.
- workflow_dispatch base must resolve to a commit in the repository, must NOT
  equal head, and must be an ancestor of head (git merge-base --is-ancestor).
- Unknown event names are rejected.

workflow_dispatch is a MANUAL RECOVERY mechanism: the operator supplies the
intended historical recovery baseline.  This helper does not guess that
baseline; it only guarantees that the supplied baseline is explicit,
full-SHA, resolvable, distinct from the tested head and an actual ancestor of
it.  An older legitimate ancestor may broaden the inspected diff, which is
safe.

Note: workflow_dispatch uses Gatekeeper push-style semantics and AI Gate
diff-only (--skip-body-checks) semantics.  It is a recovery tool, NOT a full
PR Gate (WORKFLOW_DISPATCH_IS_FULL_PR_GATE=NO).

Usage (called by production-gate.yml for every event type):
  python3 ai_gate_event_refs.py <event-name> <base> <head>
Prints "<resolved-base> <resolved-head>" on a single line (SHAs are
whitespace-free).  Exits non-zero with a stderr message on any violation.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

GITHUB_SHA_ENV = "GITHUB_SHA"
EXPECTED_ARG_COUNT = 3
EXIT_USAGE = 2

# \Z (not $) anchors at the absolute end of the string: a trailing newline
# must be rejected like any other malformed input.
FULL_SHA_RE = re.compile(r"^[0-9a-fA-F]{40}\Z")


def validate_full_sha(value: str | None, *, role: str) -> str:
    """Return the SHA if it is a full 40-hex commit SHA, else raise."""
    if not value or not FULL_SHA_RE.match(value):
        raise RuntimeError(f"{role} is not a full 40-hex commit SHA")
    return value


def _git(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a local Git command in the current working directory."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _commit_exists(sha: str) -> bool:
    """Return True when the full SHA resolves to a commit."""
    return _git(["rev-parse", "--verify", f"{sha}^{{commit}}"]).returncode == 0


def _is_ancestor(base: str, head: str) -> bool:
    """Return True when base is an ancestor of head (git merge-base)."""
    return _git(["merge-base", "--is-ancestor", base, head]).returncode == 0


def resolve_event_refs(
    event_name: str,
    base_sha: str | None,
    head_sha: str | None,
) -> tuple[str, str]:
    """Return the (base, head) comparison pair for a GitHub event, fail-closed.

    Raises RuntimeError on any violation so the caller can never fall back to
    an empty, guessed, or mismatched baseline.
    """
    if event_name in ("pull_request", "push"):
        # Platform-provided commit identities (pr.base.sha / pr.head.sha /
        # event.before / event.after).  Syntax validation only — existing PR
        # and push semantics are preserved; no ancestry rules are imposed
        # here (a PR base tip may legitimately not be an ancestor of the PR
        # head).  An all-zero "before" (first push to a branch) passes syntax
        # validation and is rejected downstream by the gate's ref resolver.
        resolved_base = validate_full_sha(base_sha, role=f"{event_name} base")
        resolved_head = validate_full_sha(head_sha, role=f"{event_name} head")
        return resolved_base, resolved_head

    if event_name == "workflow_dispatch":
        base = validate_full_sha(base_sha, role="workflow_dispatch base_sha")

        env_sha = os.environ.get(GITHUB_SHA_ENV)
        if not env_sha or not FULL_SHA_RE.match(env_sha):
            raise RuntimeError(
                "workflow_dispatch head must be the dispatched commit "
                "(GITHUB_SHA); missing or malformed GITHUB_SHA"
            )
        # The supplied head (github.sha via step env) must equal the runner's
        # GITHUB_SHA.  A caller cannot validate arbitrary commit B while the
        # workflow is executing commit A.
        if head_sha:
            validate_full_sha(head_sha, role="workflow_dispatch head")
            if head_sha.lower() != env_sha.lower():
                raise RuntimeError(
                    "workflow_dispatch head must equal GITHUB_SHA (the checked-out revision)"
                )
        head = env_sha

        if not _commit_exists(base):
            raise RuntimeError(f"workflow_dispatch base {base} does not resolve to a commit")
        if not _commit_exists(head):
            raise RuntimeError(f"workflow_dispatch head {head} does not resolve to a commit")
        if base.lower() == head.lower():
            raise RuntimeError("workflow_dispatch base must not equal head")
        if not _is_ancestor(base, head):
            raise RuntimeError(
                "workflow_dispatch base must be an ancestor of head "
                "(no guessed baseline is substituted)"
            )
        return base, head

    raise RuntimeError(f"unsupported event {event_name!r}")


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by production-gate.yml."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != EXPECTED_ARG_COUNT:
        print(
            "usage: ai_gate_event_refs.py <event-name> <base-sha> <head-sha>",
            file=sys.stderr,
        )
        return EXIT_USAGE
    try:
        base, head = resolve_event_refs(args[0], args[1], args[2])
    except RuntimeError as exc:
        print(f"[AI Gate Event Refs] {exc}", file=sys.stderr)
        return 1
    print(f"{base} {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
