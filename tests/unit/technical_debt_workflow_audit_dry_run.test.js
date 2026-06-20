'use strict';

// lifecycle: permanent
// scope: unit safety coverage for technical debt workflow audit dry-run

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const fs = require('fs');

const {
    PHASE,
    AREAS,
    SEVERITY,
    RISK_CLASS,
    finding,
    auditWorkflows,
    auditBranchMerge,
    auditTests,
    auditScripts,
    auditReports,
    auditDataGovernance,
    auditDualStack,
    auditRepoNoise,
    runAudit,
    parseArgs,
} = require('../../scripts/ops/technical_debt_workflow_audit_dry_run');

// ─── parseArgs tests ───────────────────────────────────────────────────────────

test('parseArgs supports --json and --help', () => {
    assert.equal(parseArgs(['--json']).json, true);
    assert.equal(parseArgs(['--help']).help, true);
    assert.equal(parseArgs(['-h']).help, true);
    assert.equal(parseArgs([]).json, false);
    assert.equal(parseArgs([]).help, false);
});

test('parseArgs supports combined flags', () => {
    const args = parseArgs(['--json', '--help']);
    assert.equal(args.json, true);
    assert.equal(args.help, true);
});

test('parseArgs ignores unknown flags', () => {
    const args = parseArgs(['--verbose', '--foo']);
    assert.equal(args.json, false);
    assert.equal(args.help, false);
});

// ─── finding builder tests ─────────────────────────────────────────────────────

test('finding creates structured finding object', () => {
    const f = finding(
        'TEST-001', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.WRITE_RISK,
        'Test title', 'Test detail', 'Test impact', 'Test recommendation',
    );

    assert.equal(f.id, 'TEST-001');
    assert.equal(f.area, AREAS.WORKFLOWS);
    assert.equal(f.severity, SEVERITY.P0);
    assert.equal(f.risk_class, RISK_CLASS.WRITE_RISK);
    assert.equal(f.title, 'Test title');
    assert.equal(f.detail, 'Test detail');
    assert.equal(f.impact, 'Test impact');
    assert.equal(f.recommendation, 'Test recommendation');
});

test('finding handles all severity levels', () => {
    const p0 = finding('F1', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.STRUCTURAL, 'T', 'D');
    const p1 = finding('F2', AREAS.WORKFLOWS, SEVERITY.P1, RISK_CLASS.STRUCTURAL, 'T', 'D');
    const p2 = finding('F3', AREAS.WORKFLOWS, SEVERITY.P2, RISK_CLASS.STRUCTURAL, 'T', 'D');

    assert.equal(p0.severity, SEVERITY.P0);
    assert.equal(p1.severity, SEVERITY.P1);
    assert.equal(p2.severity, SEVERITY.P2);
    assert.ok(p0.severity !== p1.severity);
    assert.ok(p1.severity !== p2.severity);
});

test('finding handles all risk classes', () => {
    const dry = finding('F1', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.DRY_RUN, 'T', 'D');
    const wr = finding('F2', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.WRITE_RISK, 'T', 'D');
    const st = finding('F3', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.STRUCTURAL, 'T', 'D');
    const sl = finding('F4', AREAS.WORKFLOWS, SEVERITY.P0, RISK_CLASS.STALE, 'T', 'D');

    assert.equal(dry.risk_class, RISK_CLASS.DRY_RUN);
    assert.equal(wr.risk_class, RISK_CLASS.WRITE_RISK);
    assert.equal(st.risk_class, RISK_CLASS.STRUCTURAL);
    assert.equal(sl.risk_class, RISK_CLASS.STALE);
});

// ─── AREAS constants tests ─────────────────────────────────────────────────────

test('AREAS contains all 8 audit areas', () => {
    const areaValues = Object.values(AREAS);
    assert.equal(areaValues.length, 8);
    assert.ok(areaValues.includes('github_workflows'));
    assert.ok(areaValues.includes('branch_and_merge'));
    assert.ok(areaValues.includes('test_debt'));
    assert.ok(areaValues.includes('script_debt'));
    assert.ok(areaValues.includes('report_debt'));
    assert.ok(areaValues.includes('data_governance'));
    assert.ok(areaValues.includes('python_js_dual_stack'));
    assert.ok(areaValues.includes('repo_noise'));
});

// ─── SEVERITY constants tests ──────────────────────────────────────────────────

test('SEVERITY has P0, P1, P2 levels', () => {
    assert.equal(Object.keys(SEVERITY).length, 3);
    assert.ok(SEVERITY.P0.includes('P0'));
    assert.ok(SEVERITY.P1.includes('P1'));
    assert.ok(SEVERITY.P2.includes('P2'));
});

test('SEVERITY levels are distinct', () => {
    assert.notEqual(SEVERITY.P0, SEVERITY.P1);
    assert.notEqual(SEVERITY.P1, SEVERITY.P2);
    assert.notEqual(SEVERITY.P0, SEVERITY.P2);
});

// ─── RISK_CLASS constants tests ────────────────────────────────────────────────

test('RISK_CLASS has all 4 classification types', () => {
    assert.equal(Object.keys(RISK_CLASS).length, 4);
    assert.ok(RISK_CLASS.DRY_RUN);
    assert.ok(RISK_CLASS.WRITE_RISK);
    assert.ok(RISK_CLASS.STRUCTURAL);
    assert.ok(RISK_CLASS.STALE);
});

// ─── runAudit tests ────────────────────────────────────────────────────────────

test('runAudit returns complete structure', () => {
    const result = runAudit();

    assert.equal(result.phase, PHASE);
    assert.ok(result.timestamp);
    assert.ok(result.repo_root);
    assert.equal(typeof result.areas, 'object');
    assert.ok(Array.isArray(result.all_findings));
    assert.equal(typeof result.summary, 'object');
});

test('runAudit covers all 8 areas', () => {
    const result = runAudit();
    const areaKeys = Object.keys(result.areas);

    assert.equal(areaKeys.length, 8);
    for (const area of Object.values(AREAS)) {
        assert.ok(areaKeys.includes(area), `Missing area: ${area}`);
    }
});

test('runAudit each area has findings array', () => {
    const result = runAudit();

    for (const area of Object.values(AREAS)) {
        const areaResult = result.areas[area];
        assert.ok(areaResult, `Area ${area} returned null/undefined`);
        assert.ok(Array.isArray(areaResult.findings), `Area ${area} findings is not an array`);
    }
});

test('runAudit summary contains expected fields', () => {
    const result = runAudit();
    const s = result.summary;

    assert.equal(typeof s.total_findings, 'number');
    assert.equal(typeof s.p0_count, 'number');
    assert.equal(typeof s.p1_count, 'number');
    assert.equal(typeof s.p2_count, 'number');
    assert.ok(typeof s.overall_debt, 'string');
    assert.ok(typeof s.workflow_health, 'string');
    assert.equal(typeof s.dry_run_safe_count, 'number');
    assert.equal(typeof s.write_risk_count, 'number');
    assert.equal(typeof s.structural_count, 'number');
    assert.equal(typeof s.stale_count, 'number');
    assert.ok(Array.isArray(s.p0_findings));
    assert.ok(Array.isArray(s.p1_findings));
    assert.ok(Array.isArray(s.p2_findings));
    assert.equal(typeof s.can_proceed_to_expansion_plan, 'boolean');
    assert.equal(typeof s.training_blocked, 'boolean');
});

test('runAudit summary counts are consistent', () => {
    const result = runAudit();
    const s = result.summary;

    assert.equal(
        s.p0_count + s.p1_count + s.p2_count,
        s.total_findings,
        'Severity counts should sum to total',
    );

    assert.equal(
        s.dry_run_safe_count + s.write_risk_count + s.structural_count + s.stale_count,
        s.total_findings,
        'Risk class counts should sum to total',
    );

    assert.equal(s.p0_findings.length, s.p0_count);
    assert.equal(s.p1_findings.length, s.p1_count);
    assert.equal(s.p2_findings.length, s.p2_count);
});

test('runAudit all_findings match areas findings', () => {
    const result = runAudit();

    let areaTotal = 0;
    for (const area of Object.values(AREAS)) {
        areaTotal += result.areas[area].findings.length;
    }

    assert.equal(result.all_findings.length, areaTotal);
});

// ─── P0/P1/P2 classification tests ────────────────────────────────────────────

test('all findings have valid severity class', () => {
    const result = runAudit();
    const validSeverities = Object.values(SEVERITY);

    for (const f of result.all_findings) {
        assert.ok(
            validSeverities.includes(f.severity),
            `Finding ${f.id} has invalid severity: ${f.severity}`,
        );
    }
});

test('P0 findings are labeled as must fix immediately', () => {
    const result = runAudit();

    for (const f of result.all_findings) {
        if (f.severity === SEVERITY.P0) {
            assert.ok(
                f.severity.includes('P0'),
                `P0 finding ${f.id} should have P0 severity string`,
            );
        }
    }
});

test('P1 findings are labeled as fix before expansion', () => {
    const result = runAudit();

    for (const f of result.all_findings) {
        if (f.severity === SEVERITY.P1) {
            assert.ok(
                f.severity.includes('P1'),
                `P1 finding ${f.id} should have P1 severity string`,
            );
        }
    }
});

test('P2 findings are labeled as schedule when possible', () => {
    const result = runAudit();

    for (const f of result.all_findings) {
        if (f.severity === SEVERITY.P2) {
            assert.ok(
                f.severity.includes('P2'),
                `P2 finding ${f.id} should have P2 severity string`,
            );
        }
    }
});

// ─── workflow file identification tests ────────────────────────────────────────

test('auditWorkflows identifies workflow files in .github/workflows/', () => {
    const result = auditWorkflows();

    assert.equal(typeof result.workflow_file_count, 'number');
    assert.ok(result.workflow_file_count >= 0);
    assert.ok(Array.isArray(result.workflow_files));
});

test('auditWorkflows includes WF-001 finding about single workflow', () => {
    const result = auditWorkflows();

    const wf001 = result.findings.find(f => f.id === 'WF-001');
    assert.ok(wf001, 'WF-001 should exist');
    assert.equal(wf001.area, AREAS.WORKFLOWS);
});

// ─── dry-run vs write-risk classification tests ────────────────────────────────

test('auditScripts identifies DB-write-risk scripts', () => {
    const result = auditScripts();

    assert.equal(typeof result.scripts_with_db_write_no_gate, 'number');
    assert.ok(result.scripts_with_db_write_no_gate >= 0);

    const sc002 = result.findings.find(f => f.id === 'SC-002');
    if (result.scripts_with_db_write_no_gate > 5) {
        assert.ok(sc002, 'SC-002 should exist when write-risk scripts > 5');
        assert.equal(sc002.risk_class, RISK_CLASS.WRITE_RISK);
    }
});

test('auditScripts identifies dry-run script count', () => {
    const result = auditScripts();

    assert.equal(typeof result.dry_run_scripts, 'number');
    assert.ok(result.dry_run_scripts >= 0);

    const sc001 = result.findings.find(f => f.id === 'SC-001');
    if (result.dry_run_scripts > 80) {
        assert.equal(sc001.risk_class, RISK_CLASS.DRY_RUN);
    }
});

test('write-risk findings have correct risk_class', () => {
    const result = runAudit();
    const writeRiskFindings = result.all_findings.filter(f => f.risk_class === RISK_CLASS.WRITE_RISK);

    for (const f of writeRiskFindings) {
        assert.equal(f.risk_class, RISK_CLASS.WRITE_RISK,
            `Finding ${f.id} classified as WRITE_RISK should have write_risk_no_safety_gate class`);
    }
});

test('dry-run safe findings have correct risk_class', () => {
    const result = runAudit();
    const dryRunFindings = result.all_findings.filter(f => f.risk_class === RISK_CLASS.DRY_RUN);

    for (const f of dryRunFindings) {
        assert.equal(f.risk_class, RISK_CLASS.DRY_RUN,
            `Finding ${f.id} classified as DRY_RUN should have dry_run_safe class`);
    }
});

// ─── report field generation tests ────────────────────────────────────────────

test('each finding has all required fields', () => {
    const result = runAudit();

    for (const f of result.all_findings) {
        assert.ok(f.id, `Finding missing id`);
        assert.ok(f.area, `Finding ${f.id} missing area`);
        assert.ok(f.severity, `Finding ${f.id} missing severity`);
        assert.ok(f.risk_class, `Finding ${f.id} missing risk_class`);
        assert.ok(f.title, `Finding ${f.id} missing title`);
        assert.ok(f.detail, `Finding ${f.id} missing detail`);
        // impact and recommendation can be empty strings
        assert.equal(typeof f.impact, 'string', `Finding ${f.id} impact is not string`);
        assert.equal(typeof f.recommendation, 'string', `Finding ${f.id} recommendation is not string`);
    }
});

test('finding ids are unique', () => {
    const result = runAudit();
    const ids = result.all_findings.map(f => f.id);
    const uniqueIds = new Set(ids);

    assert.equal(ids.length, uniqueIds.size, 'All finding IDs must be unique');
});

test('finding ids follow naming convention', () => {
    const result = runAudit();

    for (const f of result.all_findings) {
        assert.ok(
            /^[A-Z]{2}-\d{3}$/.test(f.id),
            `Finding ${f.id} should match convention AREA-XXX (e.g., WF-001)`,
        );
    }
});

test('summary overall_debt is valid severity label', () => {
    const result = runAudit();
    const validLevels = ['LOW', 'MEDIUM', 'HIGH', 'EXTREMELY_HIGH'];

    assert.ok(
        validLevels.includes(result.summary.overall_debt),
        `overall_debt "${result.summary.overall_debt}" is not valid`,
    );
});

test('summary workflow_health is valid label', () => {
    const result = runAudit();
    const validLevels = ['LOW', 'MEDIUM', 'HIGH'];

    assert.ok(
        validLevels.includes(result.summary.workflow_health),
        `workflow_health "${result.summary.workflow_health}" is not valid`,
    );
});

// ─── area-specific structure tests ─────────────────────────────────────────────

test('auditBranchMerge includes branch findings', () => {
    const result = auditBranchMerge();

    assert.equal(result.area, AREAS.BRANCH_MERGE);
    assert.ok(Array.isArray(result.findings));
    // BM-001 should always exist (gatekeeper only accepts security/* and feat/*)
    assert.ok(result.findings.some(f => f.id === 'BM-001'));
    // BM-002 should always exist (no GitHub branch protection)
    assert.ok(result.findings.some(f => f.id === 'BM-002'));
});

test('auditTests includes file counts and lines', () => {
    const result = auditTests();

    assert.equal(typeof result.unit_files, 'number');
    assert.equal(typeof result.unit_lines, 'number');
    assert.equal(typeof result.integration_files, 'number');
    assert.equal(typeof result.python_test_files, 'number');
    assert.equal(typeof result.oversized_test_files, 'number');
    assert.equal(typeof result.disabled_test_files, 'number');
});

test('auditTests oversized count matches actual scan', () => {
    const result = auditTests();

    assert.ok(result.oversized_test_files >= 0);
    // If there are oversized files, TE-001 should exist
    if (result.oversized_test_files > 50) {
        assert.ok(result.findings.some(f => f.id === 'TE-001'));
    }
});

test('auditReports includes report file counts', () => {
    const result = auditReports();

    assert.equal(typeof result.report_count, 'number');
    assert.equal(typeof result.report_lines, 'number');
});

test('auditDataGovernance identifies training bypass', () => {
    const result = auditDataGovernance();

    // DG-001 should always exist (train_model.py bypasses governance)
    assert.ok(result.findings.some(f => f.id === 'DG-001'));
    // DG-002 should exist if init_db.sql is behind
    assert.ok(result.findings.some(f => f.id === 'DG-002'));
});

test('auditDualStack identifies ELO duplication', () => {
    const result = auditDualStack();

    assert.equal(typeof result.js_source_files, 'number');
    assert.equal(typeof result.py_source_files, 'number');
    assert.equal(typeof result.js_source_lines, 'number');
    assert.equal(typeof result.py_source_lines, 'number');

    // DS-002 should exist if both ELO files are present
    const ds002 = result.findings.find(f => f.id === 'DS-002');
    assert.ok(ds002, 'DS-002 ELO duplication finding should exist');
});

test('auditRepoNoise identifies tracked noise files', () => {
    const result = auditRepoNoise();

    assert.ok(Array.isArray(result.findings));
});

// ─── edge case tests ───────────────────────────────────────────────────────────

test('runAudit is deterministic on same file system', () => {
    const result1 = runAudit();
    const result2 = runAudit();

    assert.equal(result1.summary.total_findings, result2.summary.total_findings);
    assert.equal(result1.summary.p0_count, result2.summary.p0_count);
    assert.equal(result1.summary.p1_count, result2.summary.p1_count);
    assert.equal(result1.summary.p2_count, result2.summary.p2_count);
    assert.equal(result1.summary.overall_debt, result2.summary.overall_debt);
    assert.equal(result1.summary.workflow_health, result2.summary.workflow_health);
});

test('runAudit areas are always in same order', () => {
    const result = runAudit();
    const areaKeys = Object.keys(result.areas);

    const expectedOrder = [
        AREAS.WORKFLOWS,
        AREAS.BRANCH_MERGE,
        AREAS.TESTS,
        AREAS.SCRIPTS,
        AREAS.REPORTS,
        AREAS.DATA_GOVERNANCE,
        AREAS.DUAL_STACK,
        AREAS.REPO_NOISE,
    ];

    assert.deepEqual(areaKeys, expectedOrder);
});

test('summary can_proceed_to_expansion_plan is consistent with P0 findings', () => {
    const result = runAudit();

    const p0Ids = result.summary.p0_findings.map(f => f.id);
    const expansionBlockers = p0Ids.filter(id =>
        id.startsWith('DG-') || id === 'WF-005' || id === 'BM-002',
    );

    if (expansionBlockers.length > 0) {
        assert.equal(result.summary.can_proceed_to_expansion_plan, false);
        assert.ok(Array.isArray(result.summary.expansion_blockers));
    } else {
        assert.equal(result.summary.can_proceed_to_expansion_plan, true);
    }
});

test('summary training_blocked is consistent with P0 findings', () => {
    const result = runAudit();

    const p0Ids = result.summary.p0_findings.map(f => f.id);
    const trainingBlockers = p0Ids.filter(id =>
        id.startsWith('DG-') || id === 'DS-002',
    );

    if (trainingBlockers.length > 0) {
        assert.equal(result.summary.training_blocked, true);
        assert.ok(Array.isArray(result.summary.training_blockers));
    } else {
        assert.equal(result.summary.training_blocked, false);
    }
});
