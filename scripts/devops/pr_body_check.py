#!/usr/bin/env python3
"""Compatibility entry point for the canonical PR ready check.

lifecycle: compatibility

PR prose and CI evidence are validated by CI itself. This legacy path no
longer treats SHA prefixes, changed-file counts, or run IDs in Markdown as
workflow state; existing callers are redirected to the single read-only PR
state check.
"""

from __future__ import annotations

import sys

from scripts.devops.pr_ready_check import main

if __name__ == "__main__":
    sys.exit(main())
