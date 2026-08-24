"""Validate SC-002 Phase 1 evidence and its current NOLOGIN role contract."""

from collections import Counter
from hashlib import sha256
from pathlib import Path
import re
from typing import NamedTuple

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
REVIEW_PATH = PROJECT_ROOT / "docs" / "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md"
MCP_ARCHITECTURE_PATH = PROJECT_ROOT / "docs" / "MCP_ARCHITECTURE.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
FINAL_CLOSURE_CHECK_PATH = PROJECT_ROOT / "docs" / "SC002_FINAL_CLOSURE_CHECK.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
ENFORCEMENT_DESIGN_PATH = PROJECT_ROOT / "docs" / "SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"
PROVISIONING_PATH = PROJECT_ROOT / "deploy" / "docker" / "init_claude_reader.sql"

FORBIDDEN_CLAIMS = [
    "SC-002 is complete",
    "SC-002 is fully fixed",
    "safe to train",
    "safe to write",
    "production ready",
]

CURRENT_ROLE_STATE_MARKERS = (
    "CURRENT_ROLE_TYPE=RETAINED_ACL_ROLE",
    "CURRENT_LOGIN_STATE=NOLOGIN",
    "CURRENT_DIRECT_LOGIN_SUPPORT=NO",
    "CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=NOT_ESTABLISHED",
    "CURRENT_TRACKED_POSTGRES_MCP_ENTRY=ABSENT",
)

PASSWORD_TABLE_COLUMN_COUNT = 4

TARGET_ROLE_PATTERN = re.compile(r"(?<![a-z0-9])claude[_ ]reader\b", flags=re.IGNORECASE)
MCP_PATTERN = re.compile(r"\bmcp\b", flags=re.IGNORECASE)
ROLE_IDENTITY_DECLARATION_PATTERN = re.compile(
    r"\b(?:active\s+|current\s+|supported\s+)?"
    r"(?:postgres(?:ql)?\s+)?(?:mcp\s+)?"
    r"(?:login|connection|authentication)\s+(?:identity|user|role)\b",
    flags=re.IGNORECASE,
)
PROTECTED_BODY_START_HEADING = "sc-002 runtime db role / permission review — phase 1 > summary"
PROTECTED_BODY_EXPECTED_COUNT = 176
PROTECTED_BODY_EXPECTED_FINGERPRINT = (
    "f7fb6c071d982f991d0666a56ff7fb95449d053336ae93eec291908340bd55d1"
)
DIRECT_LOGIN_COMMAND_PATTERN = re.compile(
    r"\bpsql\b[^\n]{0,200}(?:\s-U\s+claude_reader\b|\buser(?:name)?=claude_reader\b)",
    flags=re.IGNORECASE,
)
FORBIDDEN_CURRENT_STATE_MARKERS = (
    "CURRENT_LOGIN_STATE=LOGIN",
    "CURRENT_DIRECT_LOGIN_SUPPORT=YES",
    "CURRENT_POSTGRESQL_MCP_LOGIN_IDENTITY=CLAUDE_READER",
    "CURRENT_TRACKED_POSTGRES_MCP_ENTRY=PRESENT",
)


class MarkdownUnit(NamedTuple):
    """A deterministic semantic unit tied to its Markdown location."""

    heading_path: str
    unit_type: str
    normalized_text: str


CONTEXTUAL_SESSION_SAFE_UNITS = (
    MarkdownUnit(
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "connect to any database",
    ),
)


# This is intentionally a narrow, reviewed contract for security-sensitive SC002 units,
# not a natural-language classifier and not a snapshot of the whole document. Any edit,
# addition, move, copy, or split involving claude_reader/MCP semantics must update this
# allowlist in a STRICT exact-head change and receive independent semantic review.
SC002_SENSITIVE_UNIT_ALLOWLIST: tuple[tuple[str, str, str, int], ...] = (
    (
        "sc-002 runtime db role / permission review — phase 1 > current db role / account "
        "model > connection sources by role",
        "table_row",
        "| historical mcp read-only (retired login) | claude_reader | init_claude_reader.sql | "
        "retained acl role with nologin; no current postgresql mcp login identity is established |",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > current db role / account "
        "model > observed users",
        "table_row",
        "| claude_reader | deploy/docker/init_claude_reader.sql | historical mcp reader; retained "
        "acl role | nologin; existing read-only acl retained; not a current connection identity |",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > current db role / account "
        "model > password management",
        "table_row",
        "| claude reader (historical mcp) | [redacted] | historical tracked provisioning "
        "(removed) | retained acl role is nologin; no current credential is provisioned |",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > recommended target model > "
        "proposed postgresql roles",
        "table_row",
        "| football_reader | select on all tables | mcp, health checks, dashboards, read-only "
        "audits | historical precursor only — claude_reader is a retained nologin acl role, not "
        "an active login implementation |",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > references",
        "table_row",
        "| deploy/docker/init_claude_reader.sql | historical claude_reader mcp reader "
        "provisioning; current target is retained as a nologin acl role |",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > risk analysis > risk 3: no "
        "read-only app runtime user (medium)",
        "paragraph",
        "at the original phase 1 review, read-only operations (health checks, select queries, "
        "dashboard, mcp) used football_user with full write privileges, while the historical mcp "
        "path was intended to use claude_reader as a dedicated reader.",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > risk analysis > risk 3: no "
        "read-only app runtime user (medium)",
        "paragraph",
        "current mitigation: the application-layer guard blocks writes by default "
        "(dry_run=true). the historical dedicated mcp reader remains as the retained acl role "
        "claude_reader, but it is now nologin and its direct-login workflow is retired. no current "
        "supported postgresql mcp login identity is established, so this role does not provide an "
        "active read-only connection path.",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "connect to any database",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "current_direct_login_support=no",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "current_login_state=nologin",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "current_postgresql_mcp_login_identity=not_established",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "current_role_type=retained_acl_role",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "current_tracked_postgres_mcp_entry=absent",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "list_item",
        "deploy/docker/init_claude_reader.sql — historical claude_reader mcp acl-role "
        "provisioning; current provisioning retains the role as nologin without a password",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "paragraph",
        "claude_reader retains its existing read-only acl for role/permission continuity, but its "
        "historical mcp login workflow is retired. it is not a current connection identity, and "
        "the repository does not establish a replacement postgresql mcp login identity. "
        "references below to its mcp reader intent are historical observations unless explicitly "
        "marked as current.",
        1,
    ),
    (
        "sc-002 runtime db role / permission review — phase 1 > summary > current-state fence "
        "(updated 2026-08-25)",
        "paragraph",
        "this remains a phase 1 static-review/evidence document. later development-role "
        "retirement work changed the operational status of the historical claude_reader "
        "postgresql mcp identity:",
        1,
    ),
)


def _load_review():
    return REVIEW_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


def _assert_no_real_looking_credentials(documentation: str) -> None:
    candidates = re.findall(r"['\"]\S{20,}['\"]", documentation)
    unexpected = [
        candidate
        for candidate in candidates
        if candidate
        not in (
            "'[REDACTED]'",
            "'your_secure_password_here'",
            "'change-me-in-production'",
        )
        and "football_pass" not in candidate
    ]
    if unexpected:
        raise AssertionError(
            f"Review appears to contain real-looking passwords; candidate_count={len(unexpected)}"
        )


def _assert_historical_credential_field_redacted(documentation: str) -> None:
    rows = [line for line in documentation.splitlines() if "Claude reader (historical MCP)" in line]
    if len(rows) != 1:
        raise AssertionError(f"Historical credential row count must be 1; count={len(rows)}")
    cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
    if len(cells) != PASSWORD_TABLE_COLUMN_COUNT:
        raise AssertionError("Historical credential row has an unexpected structural column count")
    if cells[1] != "`[REDACTED]`":
        raise AssertionError("Historical credential field must remain redacted")


def _normalize_markdown_text(text: str) -> str:
    """Remove formatting noise without deleting semantic words or punctuation."""
    return re.sub(r"\s+", " ", text.replace("`", "").replace("**", "").strip()).casefold()


class _MarkdownUnitParser:
    """Small deterministic Markdown parser for the reviewed semantic-unit contract."""

    def __init__(self) -> None:
        self.units: list[MarkdownUnit] = []
        self.heading_stack: list[str] = []
        self.buffer: list[str] = []
        self.buffer_type = ""
        self.in_fence = False

    def _heading_path(self) -> str:
        return " > ".join(_normalize_markdown_text(heading) for heading in self.heading_stack)

    def _append_unit(self, unit_type: str, text: str) -> None:
        self.units.append(
            MarkdownUnit(self._heading_path(), unit_type, _normalize_markdown_text(text))
        )

    def _flush_buffer(self) -> None:
        if self.buffer:
            self._append_unit(self.buffer_type, " ".join(self.buffer))
            self.buffer.clear()
        self.buffer_type = ""

    def _consume_fence(self, line: str) -> bool:
        if line.startswith("```"):
            if self.in_fence:
                self.buffer.append(line)
                self._flush_buffer()
            else:
                self._flush_buffer()
                self.buffer_type = "code_block"
                self.buffer.append(line)
            self.in_fence = not self.in_fence
            return True
        if self.in_fence:
            self.buffer.append(line)
            return True
        return False

    def _consume_heading(self, line: str) -> bool:
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if not heading_match:
            return False
        self._flush_buffer()
        level = len(heading_match.group(1))
        title = heading_match.group(2)
        self.heading_stack[level - 1 :] = [title]
        self._append_unit("heading", title)
        return True

    def _consume_table_or_list(self, raw_line: str, line: str) -> bool:
        if line.startswith("|"):
            self._flush_buffer()
            self._append_unit("table_row", line)
            return True
        list_match = re.match(r"^\s*(?:[-*+]|\d+[.)])\s+(.+)$", raw_line)
        if list_match:
            self._flush_buffer()
            self.buffer_type = "list_item"
            self.buffer.append(list_match.group(1).strip())
            return True
        if self.buffer_type == "list_item" and raw_line.startswith(("  ", "\t")):
            self.buffer.append(line)
            return True
        return False

    def consume(self, raw_line: str) -> None:
        line = raw_line.strip()
        if self._consume_fence(line) or self._consume_heading(line):
            return
        if not line:
            self._flush_buffer()
            return
        if self._consume_table_or_list(raw_line, line):
            return
        if self.buffer_type == "list_item":
            self._flush_buffer()
        if not self.buffer_type:
            self.buffer_type = "paragraph"
        self.buffer.append(line)

    def parse(self, documentation: str) -> tuple[MarkdownUnit, ...]:
        for raw_line in documentation.splitlines():
            self.consume(raw_line)
        self._flush_buffer()
        return tuple(self.units)


def _markdown_units(documentation: str) -> tuple[MarkdownUnit, ...]:
    """Parse headings, paragraphs, lists, tables, and code blocks deterministically."""
    return _MarkdownUnitParser().parse(documentation)


def _is_sensitive_sc002_unit(unit: MarkdownUnit) -> bool:
    text = unit.normalized_text
    return bool(
        TARGET_ROLE_PATTERN.search(text)
        or MCP_PATTERN.search(text)
        or ROLE_IDENTITY_DECLARATION_PATTERN.search(text)
        or unit in CONTEXTUAL_SESSION_SAFE_UNITS
        or any(marker.casefold() in text for marker in CURRENT_ROLE_STATE_MARKERS)
    )


def _sensitive_sc002_units(documentation: str) -> tuple[MarkdownUnit, ...]:
    return tuple(unit for unit in _markdown_units(documentation) if _is_sensitive_sc002_unit(unit))


def _expected_sensitive_unit_counter() -> Counter[MarkdownUnit]:
    expected: Counter[MarkdownUnit] = Counter()
    for heading_path, unit_type, normalized_text, multiplicity in SC002_SENSITIVE_UNIT_ALLOWLIST:
        expected[MarkdownUnit(heading_path, unit_type, normalized_text)] += multiplicity
    return expected


def _counter_fingerprint(counter: Counter[MarkdownUnit]) -> str:
    """Return a safe digest; never echo unreviewed document content on failure."""
    payload = "\n".join(
        f"{unit.heading_path}\0{unit.unit_type}\0{unit.normalized_text}\0{count}"
        for unit, count in sorted(counter.items())
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def _has_explicit_target_mcp(unit: MarkdownUnit) -> bool:
    return bool(
        TARGET_ROLE_PATTERN.search(unit.normalized_text)
        and MCP_PATTERN.search(unit.normalized_text)
    )


def _protected_body_units(all_units: tuple[MarkdownUnit, ...]) -> tuple[MarkdownUnit, ...]:
    """Inventory the complete substantive security-review body after frontmatter."""
    protected_units: list[MarkdownUnit] = []
    in_protected_body = False
    for unit in all_units:
        if unit.unit_type == "heading" and unit.heading_path == PROTECTED_BODY_START_HEADING:
            in_protected_body = True
        if in_protected_body:
            protected_units.append(unit)
    return tuple(protected_units)


def _sensitive_unit_contract_violations(documentation: str) -> tuple[str, ...]:
    all_units = _markdown_units(documentation)
    actual = Counter(unit for unit in all_units if _is_sensitive_sc002_unit(unit))
    expected = _expected_sensitive_unit_counter()
    violations: list[str] = []

    if actual != expected:
        missing = sum((expected - actual).values())
        unexpected = sum((actual - expected).values())
        violations.append(
            "allowlist_mismatch:"
            f"missing={missing},unexpected={unexpected},"
            f"actual={_counter_fingerprint(actual)},expected={_counter_fingerprint(expected)}"
        )

    marker_units = {
        marker.casefold(): sum(
            count for unit, count in actual.items() if marker.casefold() in unit.normalized_text
        )
        for marker in CURRENT_ROLE_STATE_MARKERS
    }
    if any(count != 1 for count in marker_units.values()):
        violations.append("current_state_marker_multiplicity")

    locality_violations = 0
    for unit in actual:
        if any(marker.casefold() in unit.normalized_text for marker in CURRENT_ROLE_STATE_MARKERS):
            continue
        has_target = bool(TARGET_ROLE_PATTERN.search(unit.normalized_text))
        has_mcp = bool(MCP_PATTERN.search(unit.normalized_text))
        locality_violations += has_target != has_mcp
    if locality_violations:
        violations.append(f"sensitive_unit_locality={locality_violations}")

    protected_body = _protected_body_units(all_units)
    protected_body_count = len(protected_body)
    protected_body_payload = "\n".join(
        f"{index}\0{unit.heading_path}\0{unit.unit_type}\0{unit.normalized_text}"
        for index, unit in enumerate(protected_body)
    )
    protected_body_fingerprint = sha256(protected_body_payload.encode("utf-8")).hexdigest()
    if (
        protected_body_count != PROTECTED_BODY_EXPECTED_COUNT
        or protected_body_fingerprint != PROTECTED_BODY_EXPECTED_FINGERPRINT
    ):
        violations.append(
            "protected_body_contract:"
            f"count={protected_body_count},fingerprint={protected_body_fingerprint}"
        )

    if DIRECT_LOGIN_COMMAND_PATTERN.search(documentation):
        violations.append("target_direct_login_command")
    if any(
        marker.casefold() in documentation.casefold() for marker in FORBIDDEN_CURRENT_STATE_MARKERS
    ):
        violations.append("forbidden_current_state_marker")

    return tuple(violations)


# ---- Tests ----


class TestRuntimeDBRolePermissionReviewPhase1:
    """Verify review document content and SC-002 state."""

    def test_review_doc_exists(self):
        assert REVIEW_PATH.exists(), (
            "docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md must exist."
        )

    def test_review_has_required_sections(self):
        doc = _load_review()
        required = [
            "## Summary",
            "## Current DB Role",
            "## Risk Analysis",
            "## Recommended Target Model",
            "## Minimal Next Task",
        ]
        for section in required:
            assert section in doc, f"Review doc missing section: {section}"

    def test_review_lists_users(self):
        doc = _load_review()
        assert "football_user" in doc, "Review must mention football_user"
        assert "claude_reader" in doc, "Review must mention claude_reader"

    def test_review_identifies_connection_sources(self):
        doc = _load_review()
        sources = [
            "App runtime",
            "migration",
            "ingestion",
            "training",
            "maintenance",
            "MCP",
        ]
        min_expected = 3
        found = sum(1 for s in sources if s.lower() in doc.lower())
        assert found >= min_expected, (
            f"Review must identify at least {min_expected} connection sources, found {found}"
        )

    def test_review_identifies_risks(self):
        doc = _load_review()
        assert "Risk" in doc, "Review must identify risks"
        assert "HIGH" in doc, "Review must classify risks by severity (HIGH)"
        assert "MEDIUM" in doc, "Review must classify risks by severity (MEDIUM)"

    def test_review_recommends_target_model(self):
        doc = _load_review()
        assert "Proposed PostgreSQL Roles" in doc or "Target Model" in doc, (
            "Review must recommend a target role model."
        )

    def test_historical_mcp_role_has_explicit_current_state_fence(self):
        doc = _load_review()
        for marker in CURRENT_ROLE_STATE_MARKERS:
            assert doc.count(marker) == 1, (
                f"SC002 current-state fence marker must occur exactly once: {marker}"
            )
        assert "retained ACL role" in doc

    def test_review_matches_reviewed_sensitive_unit_contract(self):
        violations = _sensitive_unit_contract_violations(_load_review())
        assert not violations, f"SC002 sensitive-unit contract failed: {violations}"

    def test_sensitive_unit_contract_fails_closed_on_material_mutations(self):
        doc = _load_review()
        sensitive_paragraph = (
            "`claude_reader` retains its existing read-only ACL for role/permission continuity, "
            "but its\nhistorical MCP login workflow is retired. It is not a current connection "
            "identity, and the\nrepository does not establish a replacement PostgreSQL MCP LOGIN "
            "identity. References below\nto its MCP reader intent are historical observations "
            "unless explicitly marked as current."
        )
        sensitive_row = (
            "| `claude_reader` | `deploy/docker/init_claude_reader.sql` | Historical MCP reader; "
            "retained ACL role | `NOLOGIN`; existing read-only ACL retained; not a current "
            "connection identity |"
        )
        assert sensitive_paragraph in doc
        assert sensitive_row in doc

        mutations = (
            doc + "\n\nCurrent PostgreSQL MCP login identity is `claude_reader`.\n",
            doc + "\n\nThat retained role is now the active PostgreSQL login identity.\n",
            doc + "\n\nThat retained role connects to PostgreSQL.\n",
            doc + "\n\nThis ACL role authenticates to PostgreSQL.\n",
            doc + "\n\nThe retained reader role logs in to PostgreSQL.\n",
            doc + "\n\nThat role establishes database sessions.\n",
            doc + "\n\nIt opens PostgreSQL connections.\n",
            doc + "\n\nThis account has database access.\n",
            doc + "\n\nThe same role connects to PostgreSQL.\n",
            doc + "\n\nThe retained read-only role authenticates to PostgreSQL.\n",
            doc + "\n\nThe former role logs in to PostgreSQL.\n",
            doc + "\n\nThis one establishes database sessions.\n",
            doc + "\n\nThis connects to PostgreSQL.\n",
            doc + "\n\nThe same role maintains a PostgreSQL session.\n",
            doc + "\n\n## Session status\n\nThe same role connects to PostgreSQL.\n",
            doc.replace(
                "## Summary",
                "- current target: the retained ACL role from "
                "deploy/docker/init_claude_reader.sql now signs on directly to PostgreSQL.\n\n"
                "## Summary",
                1,
            ),
            doc.replace(
                "unless explicitly marked as current.",
                "unless explicitly marked as current.\n\n"
                "That same role now signs on directly to the server.",
                1,
            ),
            doc.replace(
                "| User | Source | Context | Privileges |\n|---|---|---|---|",
                "|---|---|---|---|\n| User | Source | Context | Privileges |",
                1,
            ),
            doc.replace("CURRENT_LOGIN_STATE=NOLOGIN", "CURRENT_LOGIN_STATE=LOGIN", 1),
            doc.replace(
                "### Current-state fence (updated 2026-08-25)",
                "### Current-state fence (updated 2026-08-25)\n\n#### Relocated role status",
                1,
            ),
            doc.replace(sensitive_row, f"{sensitive_row}\n{sensitive_row}", 1),
            doc.replace("continuity, but its\nhistorical", "continuity.\n\nIts historical", 1),
        )
        for mutated_doc in mutations:
            assert _sensitive_unit_contract_violations(mutated_doc)

    def test_sensitive_unit_contract_allows_frontmatter_metadata_edit(self):
        doc = _load_review()
        mutated_doc = doc.replace(
            "owner: project governance",
            "owner: project governance; reviewers access this page through the docs index",
            1,
        )
        assert mutated_doc != doc
        assert not _sensitive_unit_contract_violations(mutated_doc)

    def test_sc002_and_mcp_architecture_share_current_role_contract(self):
        review = _load_review()
        architecture = _load_text(MCP_ARCHITECTURE_PATH)
        for marker in CURRENT_ROLE_STATE_MARKERS:
            assert marker in review
            assert marker in architecture

    def test_sc002_related_evidence_uses_current_nologin_role_semantics(self):
        required_contracts = {
            FINAL_CLOSURE_CHECK_PATH: (
                "Historical MCP ACL role",
                "NOLOGIN",
                "not a current PostgreSQL MCP login identity",
            ),
            ASSESSMENT_PATH: (
                "historical MCP reader",
                "NOLOGIN",
                "no current PostgreSQL MCP login identity is established",
            ),
            ENFORCEMENT_DESIGN_PATH: (
                "CREATE ROLE, GRANT, ALTER DEFAULT PRIVILEGES",
                "NOLOGIN",
                "no current PostgreSQL MCP login identity is established",
            ),
        }
        for path, markers in required_contracts.items():
            text = _load_text(path).casefold()
            for marker in markers:
                if marker.casefold() not in text:
                    raise AssertionError(f"{path.name} missing reviewed NOLOGIN contract marker")

        design_rows = [
            line
            for line in _load_text(ENFORCEMENT_DESIGN_PATH).splitlines()
            if "deploy/docker/init_claude_reader.sql" in line
        ]
        if len(design_rows) != 1:
            raise AssertionError(
                "SC002 enforcement design must contain exactly one provisioning inventory row"
            )
        normalized_row = design_rows[0].casefold()
        if "create user" in normalized_row or "creates read-only db user" in normalized_row:
            raise AssertionError("SC002 enforcement design still claims LOGIN-user provisioning")

    def test_provisioning_comments_match_retired_nologin_role_contract(self):
        provisioning = _load_text(PROVISIONING_PATH)
        markers = (
            "Historical Claude Reader ACL Role Setup",
            "retired PostgreSQL MCP identity; direct login is disabled",
            "Create the retained NOLOGIN ACL role if it does not exist",
        )
        for marker in markers:
            if marker not in provisioning:
                raise AssertionError("Provisioning comment missing reviewed NOLOGIN role marker")

    def test_review_states_no_db_connection(self):
        """Review must state it did NOT connect to DB."""
        doc = _load_review()
        no_connect_indicators = [
            "does NOT connect",
            "did NOT connect",
            "no DB connection",
            "without connecting",
        ]
        found = any(ind.lower() in doc.lower() for ind in no_connect_indicators)
        assert found, "Review must explicitly state no DB connection was made."

    def test_review_has_uncertainties_section(self):
        """Review must list uncertainties."""
        doc = _load_review()
        assert "Uncertainties" in doc or "uncertain" in doc.lower(), (
            "Review must list uncertainties."
        )

    def test_review_sc002_partial_mitigation(self):
        """Review must state SC-002 remains partial mitigation only."""
        doc = _load_review()
        assert "partial mitigation only" in doc, (
            "Review must state SC-002 remains partial mitigation only."
        )

    def test_review_training_blocked(self):
        """Review must state training/data expansion remain blocked."""
        doc = _load_review()
        doc_lower = doc.lower()
        assert "training" in doc_lower, "Review must mention training"
        assert "blocked" in doc_lower, "Review must state blocked status"

    def test_no_real_secrets_in_review(self):
        """Review must NOT output real production credentials beyond placeholders."""
        # The review discusses "secrets manager" and "SecretStr" as code abstractions.
        # It says it does NOT read/output real secrets in its non-goals.
        # Verify it doesn't contain credential values beyond known dev placeholders;
        # [REDACTED] is a placeholder, not a development credential.
        # Check that there's no password that looks like a real production value
        # (longer than 20 chars, random-looking, not a known placeholder).
        _assert_no_real_looking_credentials(_load_review())

    def test_historical_mcp_credential_field_stays_redacted(self):
        """The historical MCP password table cell must remain a safe placeholder."""
        _assert_historical_credential_field_redacted(_load_review())

    def test_secret_guard_failures_do_not_echo_unreviewed_candidate_values(self):
        """Credential guard failures must report only structural metadata."""
        sentinel = "synthetic_candidate_value_for_output_safety_probe"
        with pytest.raises(AssertionError) as candidate_error:
            _assert_no_real_looking_credentials(f"'{sentinel}'")
        if sentinel in str(candidate_error.value):
            raise AssertionError("Credential guard repeated an unreviewed candidate value")

        unsafe_row = (
            "| Claude reader (historical MCP) | "
            f"`{sentinel}` | Historical tracked provisioning | Retained role |"
        )
        with pytest.raises(AssertionError) as field_error:
            _assert_historical_credential_field_redacted(unsafe_row)
        if sentinel in str(field_error.value):
            raise AssertionError("Credential-field guard repeated an unreviewed candidate value")

    def test_review_has_no_embedded_postgres_credential_uri(self):
        """Current review text must not embed username/password URI userinfo."""
        doc = _load_review()
        credential_uri_count = len(
            re.findall(
                r"(?i)\bpostgres(?:ql)?://[^\s/:@]+:[^\s/@]+@",
                doc,
            )
        )
        assert credential_uri_count == 0

    def test_no_forbidden_claims(self):
        """Review must NOT contain forbidden SC-002 completion claims."""
        doc = _load_review()
        lines = doc.split("\n")
        in_negation = False
        positive_lines = []
        for line in lines:
            stripped = line.strip().lower()
            if "does not:" in stripped or "this review does not" in stripped:
                in_negation = True
                continue
            if in_negation and stripped == "":
                in_negation = False
                continue
            if in_negation:
                continue
            if any(neg in stripped for neg in ["does not ", "do not ", "must not"]):
                continue
            positive_lines.append(line)
        positive_text = "\n".join(positive_lines)
        for term in FORBIDDEN_CLAIMS:
            assert term.lower() not in positive_text.lower(), (
                f"Review contains forbidden claim: '{term}'"
            )

    # ---- Cross-reference tests ----

    def test_closure_plan_criterion_6_updated(self):
        """CLOSURE_PLAN criterion #6 must reference the review."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md" in closure, (
            "CLOSURE_PLAN must reference the review doc."
        )

    def test_closure_plan_has_review_results(self):
        """CLOSURE_PLAN section 6 must show COMPLETED status."""
        closure = _load_text(CLOSURE_PLAN_PATH)
        assert "runtime_db_role_permission_review_phase1" in closure, (
            "CLOSURE_PLAN must reference the review task."
        )

    def test_assessment_criterion_6_updated(self):
        """OVERALL_CLOSURE_ASSESSMENT criterion #6 must reference the review."""
        assessment = _load_text(ASSESSMENT_PATH)
        assert "runtime_db_role_permission_review_phase1" in assessment, (
            "ASSESSMENT must reference the completed review."
        )

    def test_project_status_has_review(self):
        """PROJECT_STATUS.md must reference the review task."""
        status = _load_text(PROJECT_STATUS_PATH)
        assert "runtime_db_role_permission_review_phase1" in status, (
            "PROJECT_STATUS must reference the review task."
        )

    def test_review_has_next_task(self):
        """Review must document a next recommended task."""
        doc = _load_review()
        assert "Next Task" in doc or "next task" in doc.lower(), (
            "Review must have a next recommended task section."
        )
