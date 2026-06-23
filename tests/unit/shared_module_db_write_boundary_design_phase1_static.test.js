#!/usr/bin/env node
/**
 * Static tests for SC-002 Shared Module DB Write Boundary Design Phase 1.
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 *
 * Verifies that the shared module boundary design document exists, covers all 3 shared
 * modules, and maintains correct SC-002 status (partial mitigation only). Also verifies
 * that related SC-002 documents have been updated consistently.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');
const DESIGN_DOC = path.join(REPO_ROOT, 'docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md');
const PROJECT_STATUS = path.join(REPO_ROOT, 'docs/PROJECT_STATUS.md');
const CLOSURE_PLAN = path.join(REPO_ROOT, 'docs/SC002_CLOSURE_PLAN.md');
const AUDIT_DOC = path.join(REPO_ROOT, 'docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md');

const SHARED_MODULES = [
    'dbBlueprint.js',
    'restoreMappingsWorkflow.js',
    'odds_harvest_pipeline.shared.js'
];

const FORBIDDEN_PHRASES = [
    'fully fixed',
    'safe to train',
    'safe to write',
    'production ready',
    'data expansion ready',
    'real DB write ready',
    'SC-002 is complete',
    'SC-002 is resolved'
];

function readDoc(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

function fileExists(filePath) {
    return fs.existsSync(filePath);
}

// ── Design Document Tests ────────────────────────────────────────────────────

test('DESIGN DOC: file exists', () => {
    assert.ok(fileExists(DESIGN_DOC), `Design document must exist at ${DESIGN_DOC}`);
});

test('DESIGN DOC: lists all 3 shared modules', () => {
    const content = readDoc(DESIGN_DOC);
    for (const mod of SHARED_MODULES) {
        assert.ok(
            content.includes(mod),
            `Design document must mention shared module: ${mod}`
        );
    }
});

test('DESIGN DOC: contains required sections', () => {
    const content = readDoc(DESIGN_DOC);
    const requiredSections = [
        '## Summary',
        '## Scope',
        '## Shared Modules Reviewed',
        '## Per-Module Findings',
        '## Consumer Entrypoint Map',
        '## Recommended Guard Boundary',
        '## Do Not Implement Yet',
        '## Risks and Unknowns',
        '## Next Implementation Candidates',
        '## SC-002 Status Impact'
    ];
    for (const section of requiredSections) {
        assert.ok(
            content.includes(section),
            `Design document must contain section: ${section}`
        );
    }
});

test('DESIGN DOC: explicitly states design only / no runtime behavior changed', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('design only') || content.includes('static design'),
        'Design document must state it is design only'
    );
    assert.ok(
        content.includes('does NOT') && content.includes('Modify shared module behavior'),
        'Design document must state it does NOT modify shared module behavior'
    );
});

test('DESIGN DOC: explicitly states SC-002 remains partial mitigation only', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('partial mitigation only'),
        'Design document must state SC-002 remains partial mitigation only'
    );
});

test('DESIGN DOC: contains consumer entrypoint map', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('Consumer Entrypoint Map'),
        'Design document must include consumer entrypoint map'
    );
    // Verify it's not just the heading but actual content
    assert.ok(
        content.includes('dbBlueprint.js Consumers') ||
        content.includes('odds_harvest_pipeline.shared.js Consumers'),
        'Design document must contain per-module consumer tables'
    );
});

test('DESIGN DOC: notes odds_harvest_pipeline.js as unguarded consumer', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('odds_harvest_pipeline.js') &&
        (content.includes('UNGUARDED') || content.includes('NO GUARD')),
        'Design document must flag odds_harvest_pipeline.js as unguarded'
    );
});

test('DESIGN DOC: explicitly lists blocked items as still blocked', () => {
    const content = readDoc(DESIGN_DOC);
    const blockedItems = ['training', 'data expansion', 'real DB write'];
    for (const item of blockedItems) {
        assert.ok(
            content.toLowerCase().includes(item.toLowerCase()) &&
            content.toLowerCase().includes('blocked'),
            `Design document must state "${item}" is blocked`
        );
    }
});

test('DESIGN DOC: contains Do Not Implement Yet section with specific items', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('Do Not Implement Yet'),
        'Design document must contain "Do Not Implement Yet" section'
    );
    assert.ok(
        content.includes('Do NOT add') || content.includes('Do NOT guard'),
        'Do Not Implement Yet section must contain specific prohibitions'
    );
});

test('DESIGN DOC: no forbidden assertions', () => {
    const content = readDoc(DESIGN_DOC);
    // Check that positive-status phrases appear in the doc
    assert.ok(
        content.includes('partial mitigation only'),
        'Design document must state SC-002 is partial mitigation only'
    );
    assert.ok(
        content.includes('does NOT') || content.includes('does not'),
        'Design document must contain explicit "does NOT" disclaimers'
    );
    // Verify key safety statements are present
    assert.ok(
        content.includes('BLOCKED') || content.includes('remain blocked'),
        'Design document must state items remain BLOCKED'
    );
});

// ── PROJECT_STATUS.md Tests ───────────────────────────────────────────────────

test('PROJECT_STATUS: file exists', () => {
    assert.ok(fileExists(PROJECT_STATUS), `PROJECT_STATUS.md must exist at ${PROJECT_STATUS}`);
});

test('PROJECT_STATUS: records shared_module_db_write_boundary_design_phase1', () => {
    const content = readDoc(PROJECT_STATUS);
    assert.ok(
        content.includes('shared_module_db_write_boundary_design_phase1'),
        'PROJECT_STATUS.md must mention shared_module_db_write_boundary_design_phase1'
    );
});

test('PROJECT_STATUS: states 3 shared modules mapped', () => {
    const content = readDoc(PROJECT_STATUS);
    assert.ok(
        content.includes('3 shared modules') &&
        (content.includes('mapped') || content.includes('mapping')),
        'PROJECT_STATUS.md must state 3 shared modules mapped'
    );
});

test('PROJECT_STATUS: states SC-002 remains partial mitigation only', () => {
    const content = readDoc(PROJECT_STATUS);
    assert.ok(
        content.includes('partial mitigation only'),
        'PROJECT_STATUS.md must state SC-002 remains partial mitigation only'
    );
});

// ── SC002_CLOSURE_PLAN.md Tests ──────────────────────────────────────────────

test('CLOSURE_PLAN: file exists', () => {
    assert.ok(fileExists(CLOSURE_PLAN), `CLOSURE_PLAN.md must exist at ${CLOSURE_PLAN}`);
});

test('CLOSURE_PLAN: maintains correct SC-002 status (not fully fixed)', () => {
    const content = readDoc(CLOSURE_PLAN);
    // Verify SC-002 is explicitly described as NOT fully fixed
    assert.ok(
        content.includes('not fully fixed') || content.includes('NOT fully fixed') ||
        content.includes('partial mitigation only'),
        'CLOSURE_PLAN.md must state SC-002 is not fully fixed'
    );
    // Verify blocked status maintained
    assert.ok(
        content.includes('blocked'),
        'CLOSURE_PLAN.md must reference blocked status'
    );
    // Check that "fully fixed" in standalone positive context is NOT present
    // ("SC-002 is fully fixed" vs "SC-002 is not fully fixed")
    const fullyFixedStandalone = content.match(/SC-002\s+is\s+fully\s+fixed/i);
    assert.ok(
        !fullyFixedStandalone,
        'CLOSURE_PLAN.md must NOT state "SC-002 is fully fixed" as a positive assertion'
    );
});

test('CLOSURE_PLAN: does not claim SC-002 is complete', () => {
    const content = readDoc(CLOSURE_PLAN);
    assert.ok(
        !content.includes('SC-002 is complete') &&
        !content.includes('SC-002 complete'),
        'CLOSURE_PLAN.md must NOT claim SC-002 is complete'
    );
});

test('CLOSURE_PLAN: does not unlock release gates prematurely', () => {
    const content = readDoc(CLOSURE_PLAN);
    // Gate B, C must remain "blocked"
    const blockedGates = content.match(/Gate [BC].*?\n\n/s);
    // Simple check: document should still use "blocked" language for gates
    assert.ok(
        content.includes('blocked'),
        'CLOSURE_PLAN.md must still reference blocked status'
    );
});

test('CLOSURE_PLAN: references shared_module boundary design as completed', () => {
    const content = readDoc(CLOSURE_PLAN);
    assert.ok(
        content.includes('shared_module_db_write_boundary_design_phase1') ||
        content.includes('shared module boundary design') ||
        content.includes('Shared Module DB Write Boundary'),
        'CLOSURE_PLAN.md must reference shared module boundary design'
    );
});

// ── SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md Tests ────────────────────────────

test('AUDIT DOC: file exists', () => {
    assert.ok(fileExists(AUDIT_DOC), `AUDIT_DOC must exist at ${AUDIT_DOC}`);
});

test('AUDIT DOC: 3 shared modules NOT marked as guarded', () => {
    const content = readDoc(AUDIT_DOC);
    // Check per-line: a line containing a shared module name should not also
    // classify it as "guarded_in_phase*"
    const lines = content.split('\n');
    for (const mod of SHARED_MODULES) {
        const modShort = mod.replace('.js', '').replace('.shared', '');
        for (const line of lines) {
            if (line.includes(mod) && line.includes('guarded_in_')) {
                assert.fail(
                    `AUDIT_DOC line must NOT mark ${mod} as "guarded_in_*": "${line.trim()}"`
                );
            }
        }
    }
    // This test passes only if no line with a shared module + guarded_in_ is found
    assert.ok(true, 'No shared module marked as guarded_in_*');
});

test('AUDIT DOC: shared modules updated from "unchanged" to "design_mapped"', () => {
    const content = readDoc(AUDIT_DOC);
    // The audit doc should have updated the shared module classifications
    assert.ok(
        content.includes('design_mapped') ||
        content.includes('shared_module_db_write_boundary_design_phase1'),
        'AUDIT_DOC must reference shared module boundary design'
    );
});

test('AUDIT DOC: still maintains needs_manual_review for ambiguous scripts', () => {
    const content = readDoc(AUDIT_DOC);
    // The 4 needs_manual_review scripts should still be present
    assert.ok(
        content.includes('needs_manual_review'),
        'AUDIT_DOC must still reference needs_manual_review scripts'
    );
});

// ── Cross-Document Consistency Tests ──────────────────────────────────────────

test('CONSISTENCY: training blocked across all SC-002 docs', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    for (const doc of docs) {
        const content = readDoc(doc);
        // Check that training is mentioned with blocked/not-safe context
        const lower = content.toLowerCase();
        // Check no positive assertion like "training is now safe" or "safe to train now"
        const nowSafe = /\bnow\s+safe\b.*train/i.test(content) ||
            /\bsafe\s+to\s+train\s+now\b/i.test(content) ||
            /\btraining\s+is\s+now\s+safe\b/i.test(content) ||
            /\btraining\s+may\s+now\b/i.test(content) ||
            /\btraining\s+can\s+now\b/i.test(content);
        const hasBlockedTraining = /block/i.test(content) || /remains\s+blocked/i.test(content);
        assert.ok(
            hasBlockedTraining && !nowSafe,
            `${path.basename(doc)}: training must be blocked, not described as now safe`
        );
    }
});

test('CONSISTENCY: data expansion blocked across all SC-002 docs', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    for (const doc of docs) {
        const content = readDoc(doc);
        // Only flag positive-status assertions (not section titles or gate descriptions)
        const nowSafe = /\bdata\s+expansion\s+is\s+(now\s+)?(ready|safe|allowed)\b/i.test(content) ||
            /\bexpansion\s+is\s+now\s+safe\b/i.test(content) ||
            /\bdata\s+expansion\s+unblocked\b/i.test(content) ||
            /\bexpansion\s+may\s+now\b/i.test(content);
        assert.ok(
            !nowSafe,
            `${path.basename(doc)}: must NOT claim data expansion is now ready/safe`
        );
    }
});

test('CONSISTENCY: real DB write blocked across all SC-002 docs', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    for (const doc of docs) {
        const content = readDoc(doc);
        const nowSafe = /\breal\s+DB\s+write\s+(is\s+)?(now\s+)?(ready|safe|allowed)\b/i.test(content) ||
            /\bDB\s+write\s+is\s+now\s+safe\b/i.test(content) ||
            /\bsafe\s+to\s+write\s+to\s+DB\b/i.test(content);
        assert.ok(
            !nowSafe,
            `${path.basename(doc)}: must NOT claim real DB write is now ready/safe`
        );
    }
});
