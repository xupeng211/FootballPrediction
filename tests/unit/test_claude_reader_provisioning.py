"""Regression coverage for the retired development PostgreSQL login role."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROVISIONING_SQL = ROOT / "deploy/docker/init_claude_reader.sql"
COMPOSE_FILES = (ROOT / "docker-compose.yml", ROOT / "docker-compose.dev.yml")
TARGET_ROLE_PATTERN = r'"?CLAUDE_READER"?'


def _normalized_statements() -> tuple[str, ...]:
    sql = PROVISIONING_SQL.read_text(encoding="utf-8")
    sql_without_comments = re.sub(r"(?m)--.*$", "", sql)
    return tuple(
        " ".join(statement.split()).upper()
        for statement in sql_without_comments.split(";")
        if statement.strip()
    )


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
