#!/usr/bin/env python3
"""Compatibility entry point for the canonical PR ready check.

lifecycle: compatibility

The old merge preflight used a separate CI-only implementation. Keep this
path for existing callers, but delegate all behavior to
``scripts/devops/pr_ready_check.py`` so it cannot become a second authority.
"""

from __future__ import annotations

import sys

from scripts.devops.pr_ready_check import main

if __name__ == "__main__":
    sys.exit(main())
