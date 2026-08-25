"""Regression coverage for retired future ``claude_reader`` provisioning."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RETIRED_PROVISIONING_SQL = ROOT / "deploy/docker/init_claude_reader.sql"
ACTIVE_INIT_SQL_FILES = tuple(sorted((ROOT / "deploy/docker").glob("*.sql")))
DEV_COMPOSE = ROOT / "docker-compose.dev.yml"
UNIFIED_COMPOSE = ROOT / "docker-compose.yml"
COMPOSE_FILES = (DEV_COMPOSE, UNIFIED_COMPOSE)
BOOTSTRAP_GUARD = ROOT / "deploy/docker/postgres-entrypoint-retired-role-guard.sh"
BOOTSTRAP_GUARD_CONTAINER_PATH = "/usr/local/bin/postgres-entrypoint-retired-role-guard.sh"
MCP_ARCHITECTURE = ROOT / "docs/MCP_ARCHITECTURE.md"
PROJECT_STATUS = ROOT / "docs/PROJECT_STATUS.md"
MCP_CONFIG = ROOT / ".claude/mcp-config.json"
TARGET_ROLE_NAME = "claude_reader"
FRESH_BOOTSTRAP_GUARD_REJECTION_EXIT_CODE = 78
PREEXISTING_DEV_POC_ROLES = {
    "football_app",
    "football_gatekeeper",
    "football_ingestion",
    "football_owner",
    "football_reader",
    "football_training",
}
FORBIDDEN_REPLACEMENT_ROLE_NAMES = {
    "ai_reader",
    "claude_reader_v2",
    "codex_reader",
    "mcp_reader",
    "readonly_ai",
}


def _without_sql_comments(sql: str) -> str:
    return re.sub(r"(?m)--.*$", "", sql)


def _active_init_sql() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in ACTIVE_INIT_SQL_FILES)


def _created_roles(sql: str) -> set[str]:
    return {
        match.group(1).casefold()
        for match in re.finditer(
            r"\bCREATE\s+(?:ROLE|USER)\s+\"?([a-z_][a-z0-9_]*)\"?",
            _without_sql_comments(sql),
            flags=re.IGNORECASE,
        )
    }


def _has_direct_target_login_instruction(documentation: str) -> bool:
    username_option = r"(?:-U(?:=|\s+)|--username(?:=|\s+))"
    role_token = rf"[`'\"]?{TARGET_ROLE_NAME}[`'\"]?"
    return bool(
        re.search(
            rf"\bpsql\b[^\n]*{username_option}{role_token}\b",
            documentation,
            flags=re.IGNORECASE,
        )
    )


def _has_active_target_login_claim(documentation: str) -> bool:
    role_token = rf"`?{TARGET_ROLE_NAME}`?"
    identity_label = r"(?:login\s+(?:user|identity)|user|登录身份|登录用户|用户)"
    forward_claim = re.search(
        rf"(?im)^\s*(?:[-*]\s*)?(?:current|active|当前|当前支持的)?"
        rf"[^\n]{{0,80}}?{identity_label}\s*(?:is|=|:|：|为|是)\s*{role_token}\b",
        documentation,
    )
    reverse_claim = re.search(
        rf"(?im)^\s*(?:[-*]\s*)?{role_token}\s+(?:is|为|是)"
        rf"[^\n]{{0,80}}?(?:current|active|当前)[^\n]{{0,40}}?{identity_label}\b",
        documentation,
    )
    return bool(forward_claim or reverse_claim)


def _is_postgres_mcp_entry(name: str, payload: object) -> bool:
    serialized = json.dumps({"name": name, "payload": payload}, ensure_ascii=False).casefold()
    postgres_markers = (
        "postgresql://",
        "postgres://",
        "server-postgres",
        "mcp-postgres",
        "postgres-mcp",
    )
    return any(marker in serialized for marker in postgres_markers)


def test_retired_provisioning_sql_is_deleted() -> None:
    assert not RETIRED_PROVISIONING_SQL.exists()
    assert RETIRED_PROVISIONING_SQL not in ACTIVE_INIT_SQL_FILES


def test_compose_files_do_not_mount_retired_provisioning() -> None:
    for compose_file in COMPOSE_FILES:
        compose = compose_file.read_text(encoding="utf-8").casefold()

        assert "init_claude_reader.sql" not in compose
        assert TARGET_ROLE_NAME not in compose


def test_compose_fresh_bootstrap_is_guarded_before_official_entrypoint() -> None:
    expected_mount = f"./deploy/docker/{BOOTSTRAP_GUARD.name}:{BOOTSTRAP_GUARD_CONTAINER_PATH}:ro"

    assert BOOTSTRAP_GUARD.is_file()
    assert os.access(BOOTSTRAP_GUARD, os.X_OK)
    for compose_file in COMPOSE_FILES:
        compose = compose_file.read_text(encoding="utf-8")
        assert compose.count(f"- {BOOTSTRAP_GUARD_CONTAINER_PATH}") == 1
        assert compose.count(expected_mount) == 1
        assert compose.count("POSTGRES_USER=${DB_USER:-football_user}") == 1


def test_fresh_bootstrap_guard_rejects_stale_target_db_user(tmp_path: Path) -> None:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "PGDATA": str(tmp_path),
        "POSTGRES_USER": TARGET_ROLE_NAME,
    }

    result = subprocess.run(
        [str(BOOTSTRAP_GUARD), "postgres"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == FRESH_BOOTSTRAP_GUARD_REJECTION_EXIT_CODE
    assert "fresh PostgreSQL bootstrap refuses retired POSTGRES_USER=claude_reader" in result.stderr
    assert not (tmp_path / "PG_VERSION").exists()


def test_active_future_provisioning_does_not_recreate_target_role_or_acl() -> None:
    sql = _without_sql_comments(_active_init_sql()).casefold()

    assert TARGET_ROLE_NAME not in sql
    assert not re.search(rf"\bcreate\s+(?:role|user)\s+\"?{TARGET_ROLE_NAME}\b", sql)
    assert not re.search(rf"\bgrant\b[^;]*\bto\s+\"?{TARGET_ROLE_NAME}\b", sql)
    assert not re.search(
        rf"\balter\s+default\s+privileges\b[^;]*\bto\s+\"?{TARGET_ROLE_NAME}\b",
        sql,
    )


def test_active_init_sql_role_set_has_no_replacement_identity() -> None:
    sql = _active_init_sql()
    created_roles = _created_roles(sql)

    # These six development POC roles predate this retirement. Pinning the complete
    # set makes any new replacement identity an explicit, reviewed contract change.
    assert created_roles == PREEXISTING_DEV_POC_ROLES
    assert created_roles.isdisjoint(FORBIDDEN_REPLACEMENT_ROLE_NAMES | {TARGET_ROLE_NAME})
    for role_name in FORBIDDEN_REPLACEMENT_ROLE_NAMES:
        assert role_name not in sql.casefold()


def test_development_schema_bootstrap_remains_active() -> None:
    compose = DEV_COMPOSE.read_text(encoding="utf-8")

    assert compose.count("./deploy/docker/init_db.sql:") == 1
    assert compose.count("/docker-entrypoint-initdb.d/init_db.sql:ro") == 1
    assert "sc002.init_sql_context=development" in compose
    assert "postgres_dev_data:/var/lib/postgresql/data" in compose
    assert "pg_isready -U ${DB_USER:-football_user}" in compose


def test_unified_database_keeps_existing_data_boundary_without_init_scripts() -> None:
    compose = UNIFIED_COMPOSE.read_text(encoding="utf-8")

    assert "./data/postgres:/var/lib/postgresql/data" in compose
    assert "/docker-entrypoint-initdb.d/" not in compose
    assert re.search(r"(?m)^\s+command:\n\s+- postgres$", compose)
    assert "schema 不在 unified/production-like Compose 启动时自动创建" in compose
    assert "pg_isready -U ${DB_USER:-football_user}" in compose


def test_mcp_documentation_records_future_provisioning_retirement() -> None:
    documentation = MCP_ARCHITECTURE.read_text(encoding="utf-8")

    assert not _has_direct_target_login_instruction(documentation)
    assert not _has_active_target_login_claim(documentation)
    for marker in (
        "CURRENT_ROLE_TYPE=RETAINED_ACL_ROLE",
        "CURRENT_LOGIN_STATE=NOLOGIN",
        "CURRENT_DIRECT_LOGIN_SUPPORT=NO",
        "CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=NOT_ESTABLISHED",
        "CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT",
        "CURRENT_FUTURE_PROVISIONING_STATE=RETIRED",
        "FRESH_PROVISIONING_RECREATES_ROLE_ACL_DEFAULT_ACL=NO",
        "EXTERNAL_HOST_CONSUMER_STATE=UNKNOWN",
        "EXTERNAL_CONSUMER_BLOCKER_CLEARED=NO",
        "LIVE_DATABASE_ACL_RETIREMENT_STATE=BLOCKED",
        "ROLE_DROP_STATE=BLOCKED",
    ):
        assert marker in documentation
    assert "PostgreSQL MCP（历史 / 已退役登录）" in documentation


def test_project_status_preserves_the_layer_boundaries() -> None:
    status = PROJECT_STATUS.read_text(encoding="utf-8")

    for marker in (
        "LOGIN_RETIREMENT_STATE=DONE",
        "FUTURE_PROVISIONING_RETIREMENT_STATE=DONE",
        "FRESH_PROVISIONING_RECREATES_ROLE_ACL_DEFAULT_ACL=NO",
        "PROVISIONING_BLOCKER_REMAINS=NO",
        "PROCESS_ENV_COVERAGE_COMPLETE=NO",
        "KNOWN_PROCESS_CONSUMER_STATE=UNKNOWN_INCOMPLETE_ENVIRONMENT_VISIBILITY",
        "LOCAL_DEVELOPMENT_HOST_CONSUMER_STATE="
        "UNKNOWN_DUE_TO_INCOMPLETE_PROCESS_ENVIRONMENT_VISIBILITY",
        "HOST_COVERAGE_COMPLETE=NO",
        "EXTERNAL_HOST_CONSUMER_STATE=UNKNOWN",
        "EXTERNAL_CONSUMER_BLOCKER_CLEARED=NO",
        "LIVE_DATABASE_ACL_RETIREMENT_STATE=BLOCKED",
        "ROLE_DROP_STATE=BLOCKED",
        "CLAUDE_READER_FULL_RETIREMENT=NOT_DONE",
        "UNKNOWN_STALE_FRESH_BOOTSTRAP_COMPATIBILITY_RISK",
    ):
        assert marker in status


def test_mcp_documentation_matches_current_tracked_configuration() -> None:
    documentation = MCP_ARCHITECTURE.read_text(encoding="utf-8")
    configuration = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    configured_postgres_entries = [
        name
        for name, payload in configuration.get("mcpServers", {}).items()
        if _is_postgres_mcp_entry(name, payload)
    ]

    assert configured_postgres_entries == []
    assert "当前 tracked `.claude/mcp-config.json` 没有 PostgreSQL MCP entry" in documentation
    assert "CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=NOT_ESTABLISHED" in documentation
    assert "CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT" in documentation
    assert "仓库没有 MCP loader" in documentation


def test_direct_login_detector_covers_short_and_long_username_options() -> None:
    assert _has_direct_target_login_instruction("psql -U claude_reader -d example")
    assert _has_direct_target_login_instruction("psql --username claude_reader -d example")
    assert _has_direct_target_login_instruction("psql --username=claude_reader -d example")


def test_active_login_claim_detector_covers_current_user_wording() -> None:
    assert _has_active_target_login_claim("Current PostgreSQL MCP login user is `claude_reader`.")
    assert _has_active_target_login_claim("当前 PostgreSQL MCP 登录用户是 `claude_reader`。")
    assert not _has_active_target_login_claim(
        "`claude_reader` 曾是 historical login identity；该登录已退役。"
    )


def test_postgres_mcp_detector_covers_aliased_entry_payload() -> None:
    aliased_entry = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
    }

    assert _is_postgres_mcp_entry("readonly-database", aliased_entry)
