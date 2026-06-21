"""
DB Write Guard Static Enforcement — Advisory Check helper.

lifecycle: permanent
owner: DB write safety / ops governance

Provides `check_db_write_guard_advisory()` for use by ai_workflow_gate.py.
Runs the JS scanner in changed-files advisory mode and returns warnings.
"""

import json
from pathlib import Path
import subprocess


def check_db_write_guard_advisory(changed: set[str]) -> list[str]:
    """Run DB write guard static enforcement scanner in advisory mode.

    Only checks changed scripts/ops/*.js files.  Returns advisory warnings
    that do NOT cause CI failure.  Historical unguarded files are ignored.
    """
    warnings: list[str] = []

    js_ops_changed = [p for p in changed if p.startswith("scripts/ops/") and p.endswith(".js")]

    if not js_ops_changed:
        return warnings

    scanner = str(Path(__file__).resolve().parent.parent / "db_write_guard_static_enforcement_dry_run.js")

    try:
        proc = subprocess.run(
            ["node", scanner, "--json", "--changed-files", ",".join(js_ops_changed)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            warnings.append(
                "[DB-WRITE-GUARD ADVISORY] scanner execution failed — "
                "cannot verify guard coverage on changed scripts/ops JS files"
            )
            return warnings

        data = json.loads(proc.stdout)
        unguarded = data.get("unguarded_changed_js_ops", [])
        if unguarded:
            for entry in unguarded:
                ops = ", ".join(entry.get("writeOps", []))
                tables = ", ".join(entry.get("tables", []))
                risk = entry.get("riskLevel", "?")
                warnings.append(
                    f"[DB-WRITE-GUARD ADVISORY] {entry['path']}: "
                    f"DB write risk ({ops}) on tables ({tables}) risk={risk} "
                    f"— no db_write_guard detected. Consider adding assertDbWriteAllowed."
                )
            warnings.append(
                "[DB-WRITE-GUARD ADVISORY] "
                f"{len(unguarded)} changed scripts/ops JS file(s) have DB write risk "
                "without guard. This is an advisory warning — CI will NOT fail."
            )

    except Exception as exc:
        warnings.append(f"[DB-WRITE-GUARD ADVISORY] scanner error: {exc}")

    return warnings
