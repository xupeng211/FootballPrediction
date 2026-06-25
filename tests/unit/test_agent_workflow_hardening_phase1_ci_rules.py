"""Tests for agent workflow hardening Phase1 — CI watch / final report / main Gate rules.

lifecycle: test-fixture

Covers: CI watch command prohibitions, final report evidence requirements,
main Gate independent verification, branch safety pre-task checks, scope drift
rules, completion definition, forbidden CI loop patterns, documentation
compliance with safety claims.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# CI watch rule tests — CLAUDE.md
# ---------------------------------------------------------------------------


def test_claude_md_prohibits_while_true_ci_loop():
    """CLAUDE.md must explicitly prohibit while true CI loops."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "while true" in body.lower() or "禁止自定义 while" in body, (
        "CLAUDE.md must prohibit while true CI loops"
    )


def test_claude_md_prohibits_sleep_loop_ci():
    """CLAUDE.md must explicitly prohibit sleep-loop CI monitoring."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "sleep loop" in body.lower() or "sleep" in body.lower(), (
        "CLAUDE.md must prohibit sleep-loop CI monitoring"
    )


def test_claude_md_prohibits_monitor_ci_loop():
    """CLAUDE.md must explicitly prohibit Monitor wrapper for CI loops."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "monitor" in body.lower(), "CLAUDE.md must mention Monitor prohibition"


def test_claude_md_requires_make_watch_pr():
    """CLAUDE.md must explicitly require make watch-pr PR=<number>."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "make watch-pr" in body, "CLAUDE.md must require make watch-pr for CI observation"


# ---------------------------------------------------------------------------
# Final report rule tests — CLAUDE.md
# ---------------------------------------------------------------------------


def test_claude_md_requires_final_report_pr_gate_run_id():
    """CLAUDE.md must require PR Gate run id in final report."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "PR Gate run id" in body, "CLAUDE.md must require PR Gate run id in final report"


def test_claude_md_requires_final_report_main_gate_run_id():
    """CLAUDE.md must require post-merge main Gate run id in final report."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "main Gate run id" in body or "post-merge main Gate run id" in body, (
        "CLAUDE.md must require main Gate run id in final report"
    )


def test_claude_md_requires_main_green_evidence():
    """CLAUDE.md must require evidence for 'main green' claim."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "independently verified" in body.lower() or "reported success" in body.lower(), (
        "CLAUDE.md must distinguish independently verified from reported success"
    )


def test_claude_md_prohibits_main_green_without_run_id():
    """CLAUDE.md must not allow main green yes without run id."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    has_no_run_id_rule = "could not be independently verified" in body or (
        "没有" in body and "run id" in body.lower()
    )
    assert has_no_run_id_rule, "CLAUDE.md must prohibit main green without run id"


# ---------------------------------------------------------------------------
# Completion definition and scope drift — CLAUDE.md
# ---------------------------------------------------------------------------


def test_claude_md_has_completion_definition():
    """CLAUDE.md must define what counts as task complete."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "Completion Definition" in body or "任务完成" in body, (
        "CLAUDE.md must have completion definition"
    )


def test_claude_md_has_scope_drift_rule():
    """CLAUDE.md must have scope drift rule."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "Scope Drift" in body or "scope drift" in body.lower(), (
        "CLAUDE.md must have scope drift rule"
    )


def test_claude_md_has_branch_safety_rule():
    """CLAUDE.md must have branch safety pre-task check rule."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "Branch Safety" in body or "branch --show-current" in body, (
        "CLAUDE.md must have branch safety rule"
    )


# ---------------------------------------------------------------------------
# Makefile CI watch target
# ---------------------------------------------------------------------------


def test_makefile_has_watch_pr_target():
    """Makefile must have a watch-pr target."""
    makefile = ROOT / "Makefile"
    body = makefile.read_text(encoding="utf-8")
    assert "watch-pr:" in body, "Makefile must have watch-pr target"


def test_makefile_watch_pr_uses_gh_pr_checks():
    """Makefile watch-pr must use gh pr checks --watch (not custom loop)."""
    makefile = ROOT / "Makefile"
    body = makefile.read_text(encoding="utf-8")
    assert "gh pr checks" in body, "Makefile watch-pr must use gh pr checks"


# ---------------------------------------------------------------------------
# Hardening document existence and content
# ---------------------------------------------------------------------------


def test_ai_agent_workflow_hardening_doc_exists():
    """docs/AI_AGENT_WORKFLOW_HARDENING.md must exist."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    assert doc.exists(), f"Missing hardening doc: {doc}"


def test_hardening_doc_has_final_report_template():
    """Hardening doc must contain final report template."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "Final Report" in body, "Hardening doc must have final report section"
    assert "PR Gate run id" in body, "Final report template must include PR Gate run id"
    assert "main Gate run id" in body, "Final report template must include main Gate run id"


def test_hardening_doc_has_forbidden_ci_patterns():
    """Hardening doc must list forbidden CI watch patterns."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "Forbidden CI Watch" in body, "Hardening doc must list forbidden CI watch patterns"
    assert "while true" in body, "Hardening doc must explicitly forbid while true"
    assert "Monitor" in body, "Hardening doc must explicitly forbid Monitor wrapper"


def test_hardening_doc_has_acceptable_examples():
    """Hardening doc must show acceptable vs unacceptable commands."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "ACCEPTABLE" in body, "Hardening doc must have acceptable examples"
    assert "UNACCEPTABLE" in body, "Hardening doc must have unacceptable examples"


def test_hardening_doc_distinguishes_reported_vs_verified():
    """Hardening doc must distinguish reported success from independently verified."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "reported success" in body.lower(), "Hardening doc must mention reported success"
    assert "independently verified" in body.lower(), (
        "Hardening doc must mention independent verification"
    )


def test_hardening_doc_has_main_gate_evidence_rule():
    """Hardening doc must state no main green without run id."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "no run id" in body.lower() or "No run id" in body, (
        "Hardening doc must have no-run-id rule"
    )
    assert "could not be independently verified" in body, (
        "Hardening doc must have fallback language for missing run id"
    )


def test_hardening_doc_has_completion_definition():
    """Hardening doc must define what counts as task completion."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "What counts as" in body, "Hardening doc must define task completion"
    assert "What does NOT count" in body, "Hardening doc must define what does NOT count"


def test_hardening_doc_has_branch_safety_rules():
    """Hardening doc must include branch safety rules."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "Branch Safety" in body, "Hardening doc must have branch safety rules"


def test_hardening_doc_has_scope_drift_rules():
    """Hardening doc must include scope drift rules."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "Scope Drift" in body, "Hardening doc must have scope drift rules"


def test_hardening_doc_mentions_staging_deployment():
    """Hardening doc must address stale staging branch handling."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "sc002_staging" in body.lower() or "staging" in body.lower(), (
        "Hardening doc should address stale staging branch handling"
    )


def test_hardening_doc_states_production_untouched():
    """Hardening doc must explicitly state it does not touch production/runtime."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "What This Document Does NOT Do" in body, (
        "Hardening doc must have explicit non-goals section"
    )
    assert "not modify" in body.lower() or "does not" in body.lower(), (
        "Hardening doc must state it does not modify production behavior"
    )


def test_hardening_doc_mentions_standard_pr_lifecycle():
    """Hardening doc must document standard PR lifecycle steps."""
    doc = ROOT / "docs" / "AI_AGENT_WORKFLOW_HARDENING.md"
    body = doc.read_text(encoding="utf-8")
    assert "PR Lifecycle" in body or "PR lifecycle" in body, (
        "Hardening doc must document standard PR lifecycle"
    )


# ---------------------------------------------------------------------------
# Safety claims — no doc affirmatively claims unsafe status
# ---------------------------------------------------------------------------


def test_no_docs_claim_safe_to_train():
    """Key governance docs must not affirmatively claim 'safe to train'."""
    check_docs = ["AI_AGENT_WORKFLOW_HARDENING.md", "PROJECT_STATUS.md"]
    for doc_name in check_docs:
        doc = ROOT / "docs" / doc_name
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8", errors="replace")
        for line in body.split("\n"):
            if "safe to train" in line.lower():
                assert (
                    "not" in line.lower()
                    or "forbidden" in line.lower()
                    or "blocked" in line.lower()
                    or "non-goal" in line.lower()
                    or "does not" in line.lower()
                    or "do not" in line.lower()
                    or "remain" in line.lower()
                ), f"{doc_name}: 'safe to train' must be in negation context"


def test_no_docs_claim_safe_to_write():
    """Key governance docs must not affirmatively claim 'safe to write'."""
    check_docs = ["AI_AGENT_WORKFLOW_HARDENING.md", "PROJECT_STATUS.md"]
    for doc_name in check_docs:
        doc = ROOT / "docs" / doc_name
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8", errors="replace")
        for line in body.split("\n"):
            if "safe to write" in line.lower():
                assert (
                    "not" in line.lower()
                    or "forbidden" in line.lower()
                    or "blocked" in line.lower()
                    or "non-goal" in line.lower()
                    or "does not" in line.lower()
                    or "do not" in line.lower()
                    or "remain" in line.lower()
                ), f"{doc_name}: 'safe to write' must be in negation context"


def test_no_docs_claim_production_ready():
    """Key governance docs must not affirmatively claim 'production ready'."""
    check_docs = ["AI_AGENT_WORKFLOW_HARDENING.md", "PROJECT_STATUS.md"]
    for doc_name in check_docs:
        doc = ROOT / "docs" / doc_name
        if not doc.exists():
            continue
        body = doc.read_text(encoding="utf-8", errors="replace")
        for line in body.split("\n"):
            if "production ready" in line.lower():
                assert (
                    "not" in line.lower()
                    or "forbidden" in line.lower()
                    or "blocked" in line.lower()
                    or "non-goal" in line.lower()
                    or "does not" in line.lower()
                    or "do not" in line.lower()
                    or "remain" in line.lower()
                ), f"{doc_name}: 'production ready' must be in negation context"


# ---------------------------------------------------------------------------
# Training / data expansion / DB write remain blocked in key docs
# ---------------------------------------------------------------------------


def test_training_remain_blocked_in_docs():
    """Key docs must state training remains blocked."""
    for doc_name in [
        "PROJECT_STATUS.md",
        "SC002_FINAL_CLOSURE_CHECK.md",
        "AI_AGENT_WORKFLOW_HARDENING.md",
        "SC002_CLOSURE_PLAN.md",
    ]:
        doc = ROOT / "docs" / doc_name
        if doc.exists():
            body = doc.read_text(encoding="utf-8", errors="replace")
            assert "train" in body.lower(), f"{doc_name} must mention training status"


def test_data_expansion_remain_blocked_in_docs():
    """Key docs must state data expansion remains blocked."""
    for doc_name in [
        "PROJECT_STATUS.md",
        "SC002_FINAL_CLOSURE_CHECK.md",
        "AI_AGENT_WORKFLOW_HARDENING.md",
    ]:
        doc = ROOT / "docs" / doc_name
        if doc.exists():
            body = doc.read_text(encoding="utf-8", errors="replace")
            assert "data expansion" in body.lower() or "data expansion" in body, (
                f"{doc_name} must mention data expansion status"
            )


def test_real_db_write_remain_blocked_in_docs():
    """Key docs must state real DB write remains blocked."""
    for doc_name in [
        "PROJECT_STATUS.md",
        "SC002_FINAL_CLOSURE_CHECK.md",
        "AI_AGENT_WORKFLOW_HARDENING.md",
        "SC002_CLOSURE_PLAN.md",
    ]:
        doc = ROOT / "docs" / doc_name
        if doc.exists():
            body = doc.read_text(encoding="utf-8", errors="replace")
            assert "DB write" in body or "db write" in body.lower(), (
                f"{doc_name} must mention DB write status"
            )


# ---------------------------------------------------------------------------
# Staging deployment task separation
# ---------------------------------------------------------------------------


def test_staging_deployment_not_continued():
    """This task must NOT continue staging DB deployment from the prior branch."""
    ps = ROOT / "docs" / "PROJECT_STATUS.md"
    body = ps.read_text(encoding="utf-8")
    assert "Did not continue staging DB deployment" in body, (
        "PROJECT_STATUS.md must confirm staging deployment was not continued"
    )


def test_claude_md_references_hardening_doc():
    """CLAUDE.md must reference the hardening doc for detailed rules."""
    claude_md = ROOT / "CLAUDE.md"
    body = claude_md.read_text(encoding="utf-8")
    assert "AI_AGENT_WORKFLOW_HARDENING.md" in body, (
        "CLAUDE.md must reference AI_AGENT_WORKFLOW_HARDENING.md"
    )
