#!/usr/bin/env python3
"""Event-to-base/head ref selection for the AI Workflow Gate incremental diff.

lifecycle: permanent
task: fix_production_gate_workflow_dispatch_base_head_resolution

The Production Gate (production-gate.yml) must compare each triggering event
against a deterministic base/head pair.  The three supported event types
expose different ref fields:

- pull_request:      base = pr.base.sha,        head = pr.head.sha
- push:              base = event.before,       head = event.after
- workflow_dispatch: base = inputs.base_sha (REQUIRED), head = inputs.head_sha
                     or the dispatched commit (GITHUB_SHA)

workflow_dispatch carries neither before/after nor PR context; previously the
workflow treated it as a push event and passed empty strings, producing the
fail-closed error "incremental baseline unavailable; unable to resolve base
revision ''".  Manual dispatch therefore requires an explicit base_sha input,
resolved here and validated fail-closed — a missing or empty baseline aborts
the gate instead of guessing one.

Usage (called by production-gate.yml for every event type):
  python3 ai_gate_event_refs.py <event-name> <base> <head>
Prints "<resolved-base> <resolved-head>" on a single line (SHAs are
whitespace-free).  Exits non-zero with a stderr message when the event is
unsupported or a required ref is missing/empty.
"""

from __future__ import annotations

import os
import sys

GITHUB_SHA_ENV = "GITHUB_SHA"
EXPECTED_ARG_COUNT = 3
EXIT_USAGE = 2


def resolve_event_refs(
    event_name: str,
    base_sha: str | None,
    head_sha: str | None,
) -> tuple[str, str]:
    """Return the (base, head) comparison pair for a GitHub event, fail-closed.

    Raises RuntimeError when the event is unsupported or a required ref is
    missing/empty, so the caller can never fall back to an empty baseline.
    """
    if event_name == "pull_request":
        if not base_sha or not head_sha:
            raise RuntimeError("pull_request event missing base/head SHAs")
        return base_sha, head_sha
    if event_name == "push":
        if not base_sha or not head_sha:
            raise RuntimeError("push event missing before/after SHAs")
        return base_sha, head_sha
    if event_name == "workflow_dispatch":
        if not base_sha:
            raise RuntimeError(
                "workflow_dispatch requires an explicit base_sha input; "
                "unable to resolve base revision"
            )
        resolved_head = head_sha or os.environ.get(GITHUB_SHA_ENV) or "HEAD"
        return base_sha, resolved_head
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
