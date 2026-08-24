"""
Static test: SC-002 Runtime DB Role Permission Review Phase1 validation.

Validates:
1. Review doc exists and has required sections
2. Doc lists observed users and connection sources
3. Doc identifies specific risks with severity levels
4. Doc recommends a target model with least-privilege roles
5. Doc explicitly states no DB connection, no permission changes
6. Doc does NOT contain real secrets/passwords (only placeholders)
7. Doc states SC-002 remains partial mitigation only
8. Doc states training/data expansion/real DB write remain blocked
9. CLOSURE_PLAN criterion #6 updated to reference this review
10. OVERALL_CLOSURE_ASSESSMENT updated for criterion #6
11. Historical claude_reader MCP intent is fenced from its current NOLOGIN state
"""

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent
REVIEW_PATH = PROJECT_ROOT / "docs" / "SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md"
MCP_ARCHITECTURE_PATH = PROJECT_ROOT / "docs" / "MCP_ARCHITECTURE.md"
CLOSURE_PLAN_PATH = PROJECT_ROOT / "docs" / "SC002_CLOSURE_PLAN.md"
ASSESSMENT_PATH = PROJECT_ROOT / "docs" / "SC002_OVERALL_CLOSURE_ASSESSMENT.md"
PROJECT_STATUS_PATH = PROJECT_ROOT / "docs" / "PROJECT_STATUS.md"

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

HISTORICAL_MCP_FENCE_MARKERS = (
    "historical",
    "retired",
    "nologin",
    "retained acl",
    "not a current",
    "no current",
    "original phase 1",
)

ACTIVE_MCP_IDENTITY_MARKERS = (
    "connection",
    "login",
    "identity",
    "user",
    "dedicated",
    "mcp read-only",
    "read-only mcp",
    "exists for mcp",
    "role separation",
    "mcp which has",
)

EXPLICIT_CURRENT_STATUS_PATTERN = re.compile(
    r"\b(?:current|currently|active|supported|present-day)\b|当前|现行|受支持",
    flags=re.IGNORECASE,
)

EXPLICIT_MCP_IDENTITY_PATTERN = re.compile(
    r"\b(?:login|identity|user|connection|dedicated)\b"
    r"|\bmcp\s+read[- ]only\b|\bread[- ]only\s+mcp\b"
    r"|\brole\s+separation\b|\bexists\s+for\s+mcp\b",
    flags=re.IGNORECASE,
)

EXPLICIT_CURRENT_NEGATION_PATTERN = re.compile(
    r"\bno\s+(?:current|supported)\b"
    r"|\bnot\s+(?:a\s+|an\s+)?(?:current|active|supported)\b"
    r"|\bdoes\s+not\s+establish\b|\bnot[ _-]established\b|不支持|未建立|已退役",
    flags=re.IGNORECASE,
)

ROLE_FIRST_MCP_IDENTITY_RELATION_PATTERN = re.compile(
    r"`?claude_reader`?(?:\s*\|\s*)?\s+"
    r"(?:(?:is\s+(?:still\s+)?)|(?:still\s+is\s+)|remains\s+|"
    r"serves\s+as\s+|continues\s+(?:to\s+be|as)\s+|acts\s+as\s+)"
    r"(?P<predicate>[^.;。；\n]{0,180})",
    flags=re.IGNORECASE,
)

IDENTITY_FIRST_ROLE_RELATION_PATTERN = re.compile(
    r"(?:postgres(?:ql)?\s+)?mcp"
    r"(?=[^.;。；\n]{0,120}\b(?:login|identity|user|connection|dedicated)\b)"
    r"[^.;。；\n]{0,120}\b(?:is|remains|=|:)\s*`?claude_reader`?\b",
    flags=re.IGNORECASE,
)

MCP_USES_ROLE_PATTERN = re.compile(
    r"(?:the\s+)?(?:postgres(?:ql)?\s+)?mcp\s+"
    r"(?:continues\s+to\s+use|uses|authenticates\s+as|connects\s+as|relies\s+on)\s+"
    r"`?claude_reader`?\b",
    flags=re.IGNORECASE,
)

HISTORICAL_IDENTITY_QUALIFIER_PATTERN = re.compile(
    r"\b(?:historical|retired)\s+(?:postgres(?:ql)?\s+)?mcp\b|历史(?:的)?\s*mcp|已退役(?:的)?\s*mcp",
    flags=re.IGNORECASE,
)

PASSWORD_TABLE_COLUMN_COUNT = 4


def _load_review():
    return REVIEW_PATH.read_text(encoding="utf-8")


def _load_text(path: Path):
    return path.read_text(encoding="utf-8")


def _semantic_units(documentation: str) -> tuple[str, ...]:
    """Group prose while keeping Markdown table rows and list items independent."""
    units: list[str] = []
    paragraph: list[str] = []
    list_item: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            units.append(" ".join(paragraph))
            paragraph.clear()

    def flush_list_item() -> None:
        if list_item:
            units.append(" ".join(list_item))
            list_item.clear()

    for raw_line in documentation.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_list_item()
        elif line.startswith("|"):
            flush_paragraph()
            flush_list_item()
            units.append(line)
        elif re.match(r"^[-*]\s+", line):
            flush_paragraph()
            flush_list_item()
            list_item.append(line)
        elif list_item and raw_line.startswith(("  ", "\t")):
            list_item.append(line)
        else:
            flush_list_item()
            paragraph.append(line)
    flush_paragraph()
    flush_list_item()
    return tuple(units)


def _has_role_first_positive_identity_claim(normalized: str) -> bool:
    for relation in ROLE_FIRST_MCP_IDENTITY_RELATION_PATTERN.finditer(normalized):
        predicate = relation.group("predicate")
        if "mcp" not in predicate or not EXPLICIT_MCP_IDENTITY_PATTERN.search(predicate):
            continue
        if EXPLICIT_CURRENT_NEGATION_PATTERN.search(predicate):
            continue
        if HISTORICAL_IDENTITY_QUALIFIER_PATTERN.search(predicate):
            continue
        return True
    return False


def _has_identity_first_positive_claim(normalized: str) -> bool:
    for relation in IDENTITY_FIRST_ROLE_RELATION_PATTERN.finditer(normalized):
        context_start = max(0, relation.start() - 40)
        relation_context = normalized[context_start : relation.end()]
        if HISTORICAL_IDENTITY_QUALIFIER_PATTERN.search(relation_context):
            continue
        if EXPLICIT_CURRENT_NEGATION_PATTERN.search(relation_context):
            continue
        return True
    return False


def _has_explicit_positive_current_claim(normalized: str) -> bool:
    claim_segments = (
        normalized,
        *re.split(
            r"[.;。；,，]|\b(?:and|but|however|although|while)\b|并且|而且|但是|不过|但",
            normalized,
        ),
    )
    return any(
        "claude_reader" in segment
        and "mcp" in segment
        and EXPLICIT_CURRENT_STATUS_PATTERN.search(segment)
        and EXPLICIT_MCP_IDENTITY_PATTERN.search(segment)
        and not EXPLICIT_CURRENT_NEGATION_PATTERN.search(segment)
        for segment in claim_segments
    )


def _is_unfenced_active_claude_reader_mcp_claim(unit: str) -> bool:
    normalized = unit.casefold()
    if "claude_reader" not in normalized or "mcp" not in normalized:
        return False
    if (
        _has_role_first_positive_identity_claim(normalized)
        or _has_identity_first_positive_claim(normalized)
        or MCP_USES_ROLE_PATTERN.search(normalized)
        or _has_explicit_positive_current_claim(normalized)
    ):
        return True
    has_active_identity_semantics = any(
        marker in normalized for marker in ACTIVE_MCP_IDENTITY_MARKERS
    )
    has_historical_fence = any(marker in normalized for marker in HISTORICAL_MCP_FENCE_MARKERS)
    return has_active_identity_semantics and not has_historical_fence


def _unfenced_active_claude_reader_mcp_claim_count(documentation: str) -> int:
    return sum(
        _is_unfenced_active_claude_reader_mcp_claim(unit) for unit in _semantic_units(documentation)
    )


# ---- Tests ----


class TestRuntimeDBRolePermissionReviewPhase1:
    """Verify review document content and SC-002 state."""

    def test_review_doc_exists(self):
        """Review doc must exist."""
        assert REVIEW_PATH.exists(), (
            "docs/SC002_RUNTIME_DB_ROLE_PERMISSION_REVIEW_PHASE1.md must exist."
        )

    def test_review_has_required_sections(self):
        """Review must contain required sections."""
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
        """Review must list observed DB users."""
        doc = _load_review()
        assert "football_user" in doc, "Review must mention football_user"
        assert "claude_reader" in doc, "Review must mention claude_reader"

    def test_review_identifies_connection_sources(self):
        """Review must identify per-component connection sources."""
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
        """Review must identify specific risks with severity."""
        doc = _load_review()
        assert "Risk" in doc, "Review must identify risks"
        assert "HIGH" in doc, "Review must classify risks by severity (HIGH)"
        assert "MEDIUM" in doc, "Review must classify risks by severity (MEDIUM)"

    def test_review_recommends_target_model(self):
        """Review must recommend a target role model."""
        doc = _load_review()
        assert "Proposed PostgreSQL Roles" in doc or "Target Model" in doc, (
            "Review must recommend a target role model."
        )

    def test_historical_mcp_role_has_explicit_current_state_fence(self):
        """SC002 must separate historical MCP intent from current role state."""
        doc = _load_review()
        for marker in CURRENT_ROLE_STATE_MARKERS:
            assert marker in doc, f"SC002 current-state fence missing marker: {marker}"
        assert "retained ACL role" in doc

    def test_review_has_no_unfenced_active_claude_reader_mcp_claim(self):
        """Historical context must not read as current MCP LOGIN support."""
        claim_count = _unfenced_active_claude_reader_mcp_claim_count(_load_review())
        assert claim_count == 0, (
            f"SC002 contains unfenced active claude_reader MCP identity claims; count={claim_count}"
        )

    def test_active_mcp_claim_detector_distinguishes_current_and_historical_context(self):
        """Regression detector must catch active claims without banning history."""
        active_claims = (
            "| claude_reader | MCP read-only PostgreSQL connection | SELECT only |",
            "| MCP read-only | claude_reader | SELECT only |",
            "MCP has a dedicated read-only user claude_reader.",
            "claude_reader exists for MCP only.",
            "Current PostgreSQL MCP login identity is claude_reader.",
            "Current PostgreSQL MCP login identity is claude_reader and has no password.",
        )
        historical_masking_active_claims = (
            (
                "Historically claude_reader was an MCP reader; current PostgreSQL MCP "
                "login identity is claude_reader."
            ),
            ("| Historical MCP reader | claude_reader | current supported connection user |"),
            ("claude_reader is retired, but remains an active PostgreSQL MCP connection user."),
            "claude_reader is the PostgreSQL MCP login identity; the role is NOLOGIN.",
            (
                "claude_reader remains the PostgreSQL MCP connection user; "
                "historical provisioning is retired."
            ),
            (
                "claude_reader is still the PostgreSQL MCP login identity; "
                "the historical path is retired."
            ),
            (
                "No current replacement exists and claude_reader is the active "
                "PostgreSQL MCP login identity."
            ),
            (
                "| claude_reader | remains the PostgreSQL MCP connection user | "
                "historical path retired |"
            ),
            (
                "claude_reader continues to be the PostgreSQL MCP login identity; "
                "the historical path is retired."
            ),
            ("claude_reader acts as the PostgreSQL MCP connection user; the role is NOLOGIN."),
            (
                "The PostgreSQL MCP uses claude_reader as its login identity; "
                "the historical path is retired."
            ),
            (
                "The PostgreSQL MCP continues to use claude_reader as its login identity; "
                "the role is NOLOGIN."
            ),
            "claude_reader serves as the PostgreSQL MCP login user.",
            "The PostgreSQL MCP authenticates as claude_reader.",
            "The PostgreSQL MCP connects as claude_reader.",
            "The PostgreSQL MCP login identity is claude_reader.",
        )
        historical_claim = (
            "Historically claude_reader was the MCP reader; the retained ACL role "
            "is now NOLOGIN and that login is retired."
        )
        explicitly_unsupported_claim = (
            "claude_reader is not a current PostgreSQL MCP login identity; "
            "the historical login is retired."
        )
        safe_copular_historical_claims = (
            ("claude_reader is a historical PostgreSQL MCP login identity; the login is retired."),
            "claude_reader is the retired PostgreSQL MCP login identity.",
            (
                "claude_reader is a retained ACL role and is not a current "
                "PostgreSQL MCP login identity."
            ),
            "Historical PostgreSQL MCP login identity is claude_reader.",
            "Retired PostgreSQL MCP login identity is claude_reader.",
            "claude_reader serves as a historical PostgreSQL MCP login identity.",
        )

        for claim in active_claims:
            assert _unfenced_active_claude_reader_mcp_claim_count(claim) == 1
        for claim in historical_masking_active_claims:
            assert _unfenced_active_claude_reader_mcp_claim_count(claim) == 1
        assert _unfenced_active_claude_reader_mcp_claim_count(historical_claim) == 0
        assert _unfenced_active_claude_reader_mcp_claim_count(explicitly_unsupported_claim) == 0
        for claim in safe_copular_historical_claims:
            assert _unfenced_active_claude_reader_mcp_claim_count(claim) == 0

    def test_sc002_and_mcp_architecture_share_current_role_contract(self):
        """Both operational documents must expose the same material role state."""
        review = _load_review()
        architecture = _load_text(MCP_ARCHITECTURE_PATH)
        for marker in CURRENT_ROLE_STATE_MARKERS:
            assert marker in review
            assert marker in architecture

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
        doc = _load_review()
        # The review discusses "secrets manager" and "SecretStr" as code abstractions.
        # It says it does NOT read/output real secrets in its non-goals.
        # Verify it doesn't contain credential values beyond known dev placeholders;
        # [REDACTED] is a placeholder, not a development credential.
        # Check that there's no password that looks like a real production value
        # (longer than 20 chars, random-looking, not a known placeholder).
        pwd_pattern = re.findall(r"['\"]\S{20,}['\"]", doc)
        real_looking = [
            p
            for p in pwd_pattern
            if p
            not in (
                "'[REDACTED]'",
                "'your_secure_password_here'",
                "'change-me-in-production'",
            )
            and "football_pass" not in p
        ]
        assert len(real_looking) == 0, (
            f"Review appears to contain real-looking passwords; candidate_count={len(real_looking)}"
        )

    def test_historical_mcp_credential_field_stays_redacted(self):
        """The historical MCP password table cell must remain a safe placeholder."""
        rows = [
            line for line in _load_review().splitlines() if "Claude reader (historical MCP)" in line
        ]
        assert len(rows) == 1
        cells = [cell.strip() for cell in rows[0].strip("|").split("|")]
        assert len(cells) == PASSWORD_TABLE_COLUMN_COUNT
        assert cells[1] == "`[REDACTED]`"

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
