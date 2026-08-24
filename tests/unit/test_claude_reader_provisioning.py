"""Regression coverage for the retired development PostgreSQL login role."""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROVISIONING_SQL = ROOT / "deploy/docker/init_claude_reader.sql"
COMPOSE_FILES = (ROOT / "docker-compose.yml", ROOT / "docker-compose.dev.yml")
MCP_ARCHITECTURE = ROOT / "docs/MCP_ARCHITECTURE.md"
MCP_CONFIG = ROOT / ".claude/mcp-config.json"
TARGET_ROLE_PATTERN = r'"?CLAUDE_READER"?'
TARGET_ROLE_NAME = "claude_reader"


def _normalized_statements() -> tuple[str, ...]:
    sql = PROVISIONING_SQL.read_text(encoding="utf-8")
    sql_without_comments = re.sub(r"(?m)--.*$", "", sql)
    return tuple(
        " ".join(statement.split()).upper()
        for statement in sql_without_comments.split(";")
        if statement.strip()
    )


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


def test_historical_development_role_is_provisioned_without_login_or_password() -> None:
    statements = _normalized_statements()
    target_statements = tuple(
        statement
        for statement in statements
        if re.search(rf"\b(?:USER|ROLE)\s+{TARGET_ROLE_PATTERN}\b", statement)
    )

    create_user_count = sum(
        bool(re.match(rf"CREATE\s+USER\s+{TARGET_ROLE_PATTERN}\b", statement))
        for statement in statements
    )
    create_nologin_count = sum(
        bool(
            re.match(rf"CREATE\s+ROLE\s+{TARGET_ROLE_PATTERN}\b", statement)
            and re.search(r"\bNOLOGIN\b", statement)
        )
        for statement in statements
    )
    target_login_count = sum(
        bool(re.search(r"\bLOGIN\b", statement)) for statement in target_statements
    )
    target_password_count = sum(
        bool(re.search(r"\bPASSWORD\b", statement)) for statement in target_statements
    )
    alter_target_login_count = sum(
        bool(
            re.match(rf"ALTER\s+ROLE\s+{TARGET_ROLE_PATTERN}\b", statement)
            and re.search(r"\bLOGIN\b", statement)
        )
        for statement in statements
    )

    assert create_user_count == 0
    assert create_nologin_count == 1
    assert target_login_count == 0
    assert target_password_count == 0
    assert alter_target_login_count == 0


def test_historical_role_acl_provisioning_is_preserved() -> None:
    statements = set(_normalized_statements())
    expected_acl_statements = {
        "GRANT CONNECT ON DATABASE FOOTBALL_DB TO CLAUDE_READER",
        "GRANT USAGE ON SCHEMA PUBLIC TO CLAUDE_READER",
        "GRANT SELECT ON ALL TABLES IN SCHEMA PUBLIC TO CLAUDE_READER",
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA PUBLIC TO CLAUDE_READER",
        ("ALTER DEFAULT PRIVILEGES IN SCHEMA PUBLIC GRANT SELECT ON TABLES TO CLAUDE_READER"),
        (
            "ALTER DEFAULT PRIVILEGES IN SCHEMA PUBLIC "
            "GRANT USAGE, SELECT ON SEQUENCES TO CLAUDE_READER"
        ),
    }

    missing_acl_statement_count = len(expected_acl_statements - statements)
    acl_statement_count = sum(
        statement.startswith(("GRANT ", "ALTER DEFAULT PRIVILEGES ")) for statement in statements
    )

    assert missing_acl_statement_count == 0
    assert acl_statement_count == len(expected_acl_statements)


def test_compose_keeps_the_hardened_provisioning_entrypoint() -> None:
    for compose_file in COMPOSE_FILES:
        compose = compose_file.read_text(encoding="utf-8")
        source_reference_count = compose.count("./deploy/docker/init_claude_reader.sql:")
        initdb_destination_count = compose.count(
            "/docker-entrypoint-initdb.d/init_claude_reader.sql:ro"
        )

        assert source_reference_count == 1
        assert initdb_destination_count == 1


def test_mcp_documentation_retires_the_historical_direct_login() -> None:
    documentation = MCP_ARCHITECTURE.read_text(encoding="utf-8")

    assert not _has_direct_target_login_instruction(documentation)
    assert not _has_active_target_login_claim(documentation)
    assert "CURRENT_ROLE_TYPE=RETAINED_ACL_ROLE" in documentation
    assert "CURRENT_LOGIN_STATE=NOLOGIN" in documentation
    assert "CURRENT_DIRECT_LOGIN_SUPPORT=NO" in documentation
    assert "CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=NOT_ESTABLISHED" in documentation
    assert "CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT" in documentation
    assert "PostgreSQL MCP（历史 / 已退役登录）" in documentation


def test_mcp_documentation_matches_current_tracked_configuration() -> None:
    documentation = MCP_ARCHITECTURE.read_text(encoding="utf-8")
    configuration = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    configured_postgres_entries = [
        name
        for name, payload in configuration.get("mcpServers", {}).items()
        if _is_postgres_mcp_entry(name, payload)
    ]

    assert configured_postgres_entries == []
    assert "当前 tracked `.claude/mcp-config.json` 也没有 PostgreSQL MCP entry" in documentation
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
