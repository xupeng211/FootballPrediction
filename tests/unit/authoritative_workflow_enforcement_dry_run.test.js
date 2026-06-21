'use strict';

// lifecycle: permanent
// scope: unit safety coverage for authoritative workflow enforcement dry-run scanner

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const {
    PHASE,
    buildAudit,
    buildAuthoritativeDocs,
    buildReportsInventory,
    buildReportsWithoutBacklink,
    buildAiWorkflowRuleGaps,
    buildPrTemplateGaps,
    buildGatekeeperGaps,
    buildRecentReportReflection,
    hasPrTemplateDocChecklist,
    formatSummary,
    parseArgs,
} = require('../../scripts/ops/authoritative_workflow_enforcement_dry_run');

function writeFile(root, relPath, content) {
    const absPath = path.join(root, relPath);
    fs.mkdirSync(path.dirname(absPath), { recursive: true });
    fs.writeFileSync(absPath, content);
}

function makeFixture(overrides = {}) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'authoritative-workflow-'));

    writeFile(root, 'docs/PROJECT_STATUS.md', overrides.projectStatus || [
        '# Project Status',
        '- lifecycle: current-state',
        'Last updated: 2026-06-07',
        '',
        '## Current technical debt posture',
        '- `docs/_reports/` contains 363 historical report files.',
        '- `docs/_manifests/` contains 171 historical manifest files.',
    ].join('\n'));

    writeFile(root, 'docs/DOCUMENTATION_GOVERNANCE.md', overrides.docGov || [
        '# Documentation Governance',
        '- lifecycle: permanent',
        '',
        '| Path | Status | Notes |',
        '|---|---|---|',
        '| docs/PROJECT_STATUS.md | planned | Overall project status and blockers. |',
        '| docs/DATA_SOURCE_STRATEGY.md | planned | Strategy. |',
        '',
        'First update main docs such as PROJECT_STATUS before reports.',
    ].join('\n'));

    writeFile(root, 'docs/CODEX_WORKFLOW.md', overrides.codex || [
        '# Codex Workflow',
        '- lifecycle: permanent',
        '',
        'Read current source-of-truth docs before starting a task.',
        'Never develop directly on `main`.',
        'Do not run DB writes, raw write, network data collection, or training unless authorized.',
        'Do not skip source-of-truth updates while adding more reports.',
        'Final Report Format',
    ].join('\n'));

    writeFile(root, 'docs/AGENT_WORKFLOW.md', '- lifecycle: permanent\nsource-of-truth docs first\n');
    writeFile(root, 'docs/DATA_SOURCE_STRATEGY.md', '- lifecycle: current-state\n');
    writeFile(root, 'docs/data/FOTMOB_CURRENT_STATE.md', '- lifecycle: current-state\n');
    writeFile(root, 'docs/CHANGELOG.md', '# Old Changelog\n2026-03-11\n');
    writeFile(root, 'README.md', '# README\nProduction-Ready\n');
    writeFile(root, 'AGENTS.md', '- lifecycle: permanent\n不在 `main` 分支直接开发。\n');
    writeFile(root, 'CLAUDE.md', '- lifecycle: permanent\nRead order\n');

    writeFile(root, '.github/pull_request_template.md', overrides.prTemplate || [
        '## Files Changed',
        '| Path | Purpose |',
        '## Documentation Impact',
        '| Reports added | 1 |',
    ].join('\n'));
    writeFile(root, '.github/PULL_REQUEST_TEMPLATE.md', '# Legacy template\n');
    writeFile(root, '.github/workflows/production-gate.yml', overrides.workflow || [
        'name: Production Gate',
        'run: python3 scripts/ops/ai_workflow_gate.py --skip-body-checks',
    ].join('\n'));

    writeFile(root, 'scripts/devops/gatekeeper.sh', overrides.gatekeeper || '#!/usr/bin/env bash\n');
    writeFile(root, 'scripts/ops/ai_workflow_gate.py', overrides.aiGate || [
        'MAX_DOC_SPRAWL_NEW_FILES = 5',
        'def check_doc_sprawl(): pass',
    ].join('\n'));
    writeFile(root, 'scripts/ops/documentation_governance_check.py', overrides.docChecker || [
        'ALLOWED_ADDED = set()',
        '# budget-only checker',
    ].join('\n'));

    writeFile(root, 'docs/_manifests/sample.json', '{"lifecycle":"phase-artifact"}\n');
    writeFile(root, 'docs/_reports/no_backlink.md', '# Report\n- lifecycle: phase-artifact\n');
    writeFile(root, 'docs/_reports/with_backlink.md', '# Report\nSee docs/PROJECT_STATUS.md\n');
    writeFile(root, 'docs/_reports/formal_training_cohort_inventory_dry_run_20260620.md', '# Formal\n58 rows\n');
    writeFile(root, 'docs/_reports/technical_debt_workflow_audit_dry_run_20260620.md', '# Debt\nEXTREMELY_HIGH\n');
    writeFile(root, 'docs/_reports/p0_db_write_safety_gate_dry_run_20260620.md', '# Gate\n122\n');

    return root;
}

test('parseArgs supports JSON and help flags', () => {
    assert.equal(parseArgs(['--json']).json, true);
    assert.equal(parseArgs(['--help']).help, true);
    assert.equal(parseArgs(['-h']).help, true);
    assert.throws(() => parseArgs(['--bad']), /Unknown argument/);
});

test('buildAuthoritativeDocs identifies existing authoritative documents', () => {
    const root = makeFixture();
    const docs = buildAuthoritativeDocs(root);
    const paths = docs.map(doc => doc.path);

    assert.ok(paths.includes('docs/PROJECT_STATUS.md'));
    assert.ok(paths.includes('docs/DOCUMENTATION_GOVERNANCE.md'));
    assert.ok(paths.includes('docs/CODEX_WORKFLOW.md'));
    assert.ok(paths.includes('AGENTS.md'));
    assert.ok(paths.includes('CLAUDE.md'));
});

test('buildReportsInventory identifies docs/_reports and docs/_manifests', () => {
    const root = makeFixture();
    const inventory = buildReportsInventory(root);

    assert.equal(inventory.reports_count, 5);
    assert.equal(inventory.manifests_count, 1);
    assert.ok(inventory.report_files.includes('docs/_reports/no_backlink.md'));
});

test('buildReportsWithoutBacklink detects reports missing authoritative backlinks', () => {
    const root = makeFixture();
    const inventory = buildReportsInventory(root);
    const missing = buildReportsWithoutBacklink(root, inventory.report_files);

    assert.ok(missing.includes('docs/_reports/no_backlink.md'));
    assert.equal(missing.includes('docs/_reports/with_backlink.md'), false);
});

test('hasPrTemplateDocChecklist detects authoritative document checklist wording', () => {
    assert.equal(hasPrTemplateDocChecklist('| Source-of-truth docs updated | yes |'), true);
    assert.equal(hasPrTemplateDocChecklist('| 权威文档更新 | yes |'), true);
    assert.equal(hasPrTemplateDocChecklist('| Reports added | 1 |'), false);
});

test('buildPrTemplateGaps detects missing authoritative-doc checklist', () => {
    const root = makeFixture();
    const gaps = buildPrTemplateGaps(root);

    assert.ok(gaps.some(gap => gap.severity === 'P0' && gap.gap.includes('authoritative')));
    assert.ok(gaps.some(gap => gap.severity === 'P2' && gap.gap.includes('legacy')));
});

test('buildAiWorkflowRuleGaps recognizes complete read/update workflow wording', () => {
    const root = makeFixture({
        codex: [
            '# Codex Workflow',
            'Read current source-of-truth docs before starting a task.',
            'Never develop directly on `main`.',
            'Do not run DB writes, raw write, network data collection, or training unless authorized.',
            'Do not skip source-of-truth updates while adding more reports.',
            'Every report conclusion must be summarized or linked from a source-of-truth doc.',
            'Final Report Format must include Current-state doc updated.',
        ].join('\n'),
        docGov: [
            '# Documentation Governance',
            '| docs/PROJECT_STATUS.md | exists | Status |',
            'First update main docs such as PROJECT_STATUS before reports.',
            'Report conclusions must be summarized or linked from a source-of-truth doc.',
        ].join('\n'),
    });
    const gaps = buildAiWorkflowRuleGaps(root);

    assert.equal(gaps.some(gap => gap.severity === 'P0'), false);
});

test('buildGatekeeperGaps detects missing report-to-authoritative enforcement', () => {
    const root = makeFixture();
    const gaps = buildGatekeeperGaps(root);

    assert.ok(gaps.some(gap => gap.severity === 'P0' && gap.gap.includes('PROJECT_STATUS')));
    assert.ok(gaps.some(gap => gap.severity === 'P1' && gap.gap.includes('Production Gate')));
});

test('buildRecentReportReflection detects dry-run reports not reflected in PROJECT_STATUS', () => {
    const root = makeFixture();
    const reflection = buildRecentReportReflection(root);

    assert.equal(reflection.length, 3);
    assert.equal(reflection.every(item => item.report_exists), true);
    assert.equal(reflection.every(item => item.needs_project_status_delta), true);
});

test('buildAudit exposes required JSON structure and severity classification', () => {
    const root = makeFixture();
    const audit = buildAudit(root);

    assert.equal(audit.phase, PHASE);
    assert.ok(Array.isArray(audit.authoritative_docs_found));
    assert.ok(Array.isArray(audit.missing_authoritative_docs));
    assert.ok(Array.isArray(audit.stale_authoritative_docs));
    assert.equal(typeof audit.reports_without_status_backlink.count, 'number');
    assert.ok(Array.isArray(audit.reports_not_reflected_in_project_status));
    assert.ok(Array.isArray(audit.ai_workflow_rule_gaps));
    assert.ok(Array.isArray(audit.pr_template_gaps));
    assert.ok(Array.isArray(audit.gatekeeper_gaps));
    assert.ok(audit.recommended_enforcement_steps.P0.length > 0);
    assert.ok(audit.severity_summary.P0 > 0);
    assert.ok(audit.severity_summary.P1 > 0);
    assert.ok(audit.severity_summary.P2 > 0);
});

test('formatSummary includes key human-readable fields', () => {
    const root = makeFixture();
    const summary = formatSummary(buildAudit(root));

    assert.match(summary, /Authoritative docs found/);
    assert.match(summary, /docs\/_reports/);
    assert.match(summary, /Recent report reflection/);
    assert.match(summary, /Severity summary: P0=/);
    assert.match(summary, /Recommend fix_phase1: yes/);
});
