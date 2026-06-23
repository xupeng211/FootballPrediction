#!/usr/bin/env python3
"""SQL / Migration Policy Static Enforcement Scanner. lifecycle: permanent."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SQL_DIRS = (
    "database/migrations/",
    "migrations/",
    "scripts/maintenance/migrations/",
    "src/database/migrations/versions/",
    "deploy/docker/",
)

DDL = [
    (n, re.compile(p, re.I))
    for n, p in [
        ("CREATE_TABLE", r"\bCREATE\s+TABLE\b"),
        ("ALTER_TABLE", r"\bALTER\s+TABLE\b"),
        ("DROP_TABLE", r"\bDROP\s+TABLE\b"),
        ("CREATE_INDEX", r"\bCREATE\s+(?:UNIQUE\s+)?INDEX\b"),
        ("DROP_INDEX", r"\bDROP\s+INDEX\b"),
        ("TRUNCATE", r"\bTRUNCATE\b"),
    ]
]
DML = [
    (n, re.compile(p, re.I))
    for n, p in [
        ("INSERT", r"\bINSERT\s+INTO\b"),
        ("UPDATE", r"\bUPDATE\s+\w+\s+SET\b"),
        ("DELETE", r"\bDELETE\s+FROM\b"),
        ("ON_CONFLICT", r"\bON\s+CONFLICT\b"),
        ("COPY", r"\bCOPY\b.*\b(?:FROM|TO)\b"),
    ]
]
PRIV = [
    (n, re.compile(p, re.I))
    for n, p in [
        ("GRANT", r"\bGRANT\s+\w+\s+(?:ON|TO)\b"),
        ("REVOKE", r"\bREVOKE\s+\w+\s+(?:ON|FROM)\b"),
        ("CREATE_ROLE", r"\bCREATE\s+(?:ROLE|USER)\b"),
        ("ALTER_ROLE", r"\bALTER\s+(?:ROLE|USER)\b"),
        ("DROP_ROLE", r"\bDROP\s+(?:ROLE|USER)\b"),
        ("ALTER_DEFAULT_PRIVILEGES", r"\bALTER\s+DEFAULT\s+PRIVILEGES\b"),
    ]
]
DEST = [
    (n, re.compile(p, re.I))
    for n, p in [
        ("DROP_DATABASE", r"\bDROP\s+DATABASE\b"),
        ("CREATE_DATABASE", r"\bCREATE\s+DATABASE\b"),
        ("DROP_SCHEMA", r"\bDROP\s+SCHEMA\b"),
        ("DROP_TABLE", r"\bDROP\s+TABLE\b"),
        ("TRUNCATE", r"\bTRUNCATE\b"),
        ("REVOKE", r"\bREVOKE\s+\w+\s+ON\b"),
        ("DROP_ROLE", r"\bDROP\s+(?:ROLE|USER)\b"),
        ("GRANT_ALL", r"\bGRANT\s+ALL\b"),
    ]
]
ALEMBIC = [
    (n, re.compile(p, re.I))
    for n, p in [
        ("op_create_table", r"\bop\.create_table\s*\("),
        ("op_drop_table", r"\bop\.drop_table\s*\("),
        ("op_add_column", r"\bop\.add_column\s*\("),
        ("op_alter_column", r"\bop\.alter_column\s*\("),
        ("op_execute", r"\bop\.execute\s*\("),
        ("upgrade_fn", r"\bdef\s+upgrade\s*\("),
        ("downgrade_fn", r"\bdef\s+downgrade\s*\("),
        ("op_bulk_insert", r"\bop\.bulk_insert\s*\("),
    ]
]

COMMENT_RE = re.compile(r"^\s*--")


def _classify(line, ms, in_block, in_line):  # noqa: ARG001
    return "comment_context" if (in_line or in_block) else "executable_context"


def _read(fp):
    try:
        return fp.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []


def _is_sql(fp):
    return fp.endswith(".sql") or (any(fp.startswith(d) for d in SQL_DIRS) and fp.endswith(".py"))


def _ftype(fp):  # noqa: PLR0911
    if fp.endswith(".sql"):
        for d in SQL_DIRS:
            if fp.startswith(d):
                if "init" in fp.lower() or "seed" in fp.lower():
                    return "sql_init_or_seed"
                if "docker" in fp.lower():
                    return "sql_docker_init"
                return "sql_migration"
        if "docs/_reports" in fp:
            return "sql_docs_or_example"
        return "sql_other"
    if fp.endswith(".py") and "migrations" in fp.lower() and "versions" in fp:
        return "alembic_migration"
    if fp.endswith(".py") and "migrations" in fp.lower():
        return "python_migration"
    return "unknown"


def _scan(fp):  # noqa: C901, PLR0912
    lines = _read(fp)
    rel = str(fp.relative_to(REPO_ROOT))
    ft = _ftype(rel)
    if not lines:
        return _empty(rel, ft)
    ddl, dml, priv, dest, al = [], [], [], [], []
    in_block = False
    for n, line in enumerate(lines, 1):
        il = bool(COMMENT_RE.match(line.strip()))
        if "/*" in line:
            in_block = True
        if "*/" in line:
            in_block = False
        for lst, pats in [(ddl, DDL), (dml, DML), (priv, PRIV), (dest, DEST)]:
            for name, pat in pats:
                for m in pat.finditer(line):
                    lst.append(
                        {
                            "signal": name,
                            "line": n,
                            "match": m.group()[:80],
                            "evidence_type": _classify(line, m.start(), in_block, il),
                        }
                    )
        if ft in ("alembic_migration", "python_migration"):
            for name, pat in ALEMBIC:
                for m in pat.finditer(line):
                    al.append(  # noqa: PERF401
                        {
                            "signal": name,
                            "line": n,
                            "match": m.group()[:80],
                            "evidence_type": _classify(line, m.start(), in_block, il),
                        }
                    )
    ed = lambda s: any(x["evidence_type"] == "executable_context" for x in s)  # noqa: E731
    dd, dm, ds, dp, ea = ed(ddl), ed(dml), ed(dest), ed(priv), ed(al)
    if "docs/_reports" in rel:
        cls = "sql_docs_or_example_only"
    elif ds:
        cls = "sql_destructive_needs_policy_review"
    elif dd and not dm:
        cls = "sql_schema_definition"
    elif dm and ft == "sql_migration":
        cls = "sql_allowed_migration_with_dml"
    elif dm and ft in ("sql_init_or_seed", "sql_docker_init"):
        cls = "sql_seed_or_data_write_needs_gate"
    elif dm:
        cls = "sql_dml_detected_needs_review"
    elif ea:
        cls = "alembic_migration_candidate"
    elif dp:
        cls = "sql_privilege_operations_detected"
    else:
        cls = "sql_no_actionable_signals"
    all_s = ddl + dml + priv + dest + al
    exec_s = [s for s in all_s if s["evidence_type"] == "executable_context"]
    ev = [
        {
            "line": s["line"],
            "signal": s["signal"],
            "snippet": lines[s["line"] - 1].strip()[:120] if s["line"] <= len(lines) else "",
        }
        for s in exec_s[:50]
    ]
    review = cls in (
        "sql_destructive_needs_policy_review",
        "sql_dml_detected_needs_review",
        "sql_seed_or_data_write_needs_gate",
    )
    return {
        "path": rel,
        "file_type": ft,
        "classification": cls,
        "ddl_signals": ddl,
        "dml_signals": dml,
        "destructive_signals": dest,
        "privilege_signals": priv,
        "migration_api_signals": al,
        "evidence_lines": ev,
        "allowlist_status": "not_in_allowlist",
        "requires_review": review,
        "would_fail_changed_files_gate": review,
        "recommended_next_action": "review" if review else "none",
    }


def _empty(path, ft):
    return {
        "path": path,
        "file_type": ft,
        "classification": "unreadable",
        "ddl_signals": [],
        "dml_signals": [],
        "destructive_signals": [],
        "privilege_signals": [],
        "migration_api_signals": [],
        "evidence_lines": [],
        "allowlist_status": "not_in_allowlist",
        "requires_review": False,
        "would_fail_changed_files_gate": False,
    }


def _load_al(path=None):
    if path is None:
        path = REPO_ROOT / "config" / "sql_migration_policy_allowlist.json"
    if not path.exists():
        return {}
    try:
        return {
            e["path"]: e for e in json.loads(path.read_text(encoding="utf-8")).get("entries", [])
        }
    except Exception:
        return {}


def _validate_entry(e):
    req = [
        "path",
        "file_type",
        "classification",
        "reason",
        "evidence",
        "source_doc",
        "owner_task",
        "allowed_operations",
        "disallowed_operations",
    ]
    return [f for f in req if f not in e or not e[f]]


def _apply_al(results, al):
    for r in results:
        p = r["path"]
        if p in al:
            e = al[p]
            r["allowlist_status"] = "in_allowlist"
            r["allowlist_entry_complete"] = len(_validate_entry(e)) == 0
            r["allowlist_missing_fields"] = _validate_entry(e)
            if e.get("classification", "").startswith("historical_sql_"):
                r["would_fail_changed_files_gate"] = False
                r["recommended_next_action"] = "historical_baseline"
    return results


def scan_files(fps, ap=None):  # noqa: D103
    al = _load_al(ap)
    res = []
    for fp in fps:
        full = REPO_ROOT / fp
        if not full.exists() or not full.is_file():
            res.append(_empty(fp, "unknown"))
        else:
            res.append(_scan(full))
    return _apply_al(res, al)


def scan_repo(ap=None):  # noqa: D103
    files = []
    for root, dirs, fnames in os.walk(str(REPO_ROOT)):
        dirs[:] = [
            d
            for d in dirs
            if d not in {".git", "node_modules", "__pycache__", ".pytest_cache", ".claude"}
        ]
        for fn in fnames:
            if fn.endswith(".sql"):
                files.append(str(Path(root) / fn).replace(str(REPO_ROOT) + "/", ""))
            if (
                fn.endswith(".py")
                and "migrations" in root
                and "versions" in root
                and fn != "env.py"
            ):
                files.append(str(Path(root) / fn).replace(str(REPO_ROOT) + "/", ""))
    return scan_files(files, ap)


def changed_files_check(cf, ap=None):  # noqa: D103
    sql = [f for f in cf if _is_sql(f)]
    if not sql:
        return {
            "violations": [],
            "passed": [],
            "would_hard_fail": False,
            "results": [],
            "note": "No SQL/migration files changed",
        }
    results = scan_files(sql, ap)
    violations, passed = [], []
    for r in results:
        has_dest = any(
            s["evidence_type"] == "executable_context" for s in r.get("destructive_signals", [])
        )
        if has_dest or r.get("would_fail_changed_files_gate"):
            violations.append(r)
        else:
            passed.append(r)
    return {
        "violations": violations,
        "passed": passed,
        "would_hard_fail": len(violations) > 0,
        "results": results,
    }


def main(argv=None):  # noqa: D103, PLR0912
    p = argparse.ArgumentParser(description="SQL Migration Policy Scanner")
    p.add_argument("--json", action="store_true")
    p.add_argument("--changed-files", default=None)
    p.add_argument("--allowlist", default=None)
    p.add_argument("--files", default=None)
    p.add_argument("--full-scan", action="store_true")
    p.add_argument("--validate-allowlist", action="store_true")
    args = p.parse_args(argv)
    ap = Path(args.allowlist) if args.allowlist else None
    if ap and not ap.is_absolute():
        ap = REPO_ROOT / ap
    if args.validate_allowlist:
        al = _load_al(ap)
        valid = sum(1 for e in al.values() if not _validate_entry(e))
        if args.json:
            print(json.dumps({"total": len(al), "valid": valid, "invalid": len(al) - valid}))
        else:
            print(f"Allowlist: {valid}/{len(al)} valid")
        return 0 if valid == len(al) else 1
    if args.changed_files:
        cf = [f.strip() for f in args.changed_files.split(",") if f.strip()]
        r = changed_files_check(cf, ap)
        if args.json:
            print(json.dumps(r, indent=2, default=str))
        else:
            print(f"SQL: {len(r['violations'])} violations, fail={r['would_hard_fail']}")
        return 1 if r["would_hard_fail"] else 0
    if args.files:
        fl = [f.strip() for f in args.files.split(",") if f.strip()]
        results = scan_files(fl, ap)
        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            for r in results:
                print(f"  {r['path']}: {r['classification']}")
        return 0
    results = scan_repo(ap)
    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        risky = [r for r in results if r.get("requires_review")]
        print(f"SQL scan: {len(results)} files, {len(risky)} need review")
    return 0


if __name__ == "__main__":
    sys.exit(main())
