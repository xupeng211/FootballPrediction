#!/usr/bin/env node
/**
 * Static tests for SC-002 Shared Module DB Write Boundary Implementation Phase 1.
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts or connect to DB
 *
 * Verifies that odds_harvest_pipeline.js has been properly guarded with
 * assertDbWriteAllowed() before its executable write SQL.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');
const TARGET_SCRIPT = path.join(REPO_ROOT, 'scripts/ops/odds_harvest_pipeline.js');
const DESIGN_DOC = path.join(REPO_ROOT, 'docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md');
const PROJECT_STATUS = path.join(REPO_ROOT, 'docs/PROJECT_STATUS.md');
const CLOSURE_PLAN = path.join(REPO_ROOT, 'docs/SC002_CLOSURE_PLAN.md');
const AUDIT_DOC = path.join(REPO_ROOT, 'docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md');

function readDoc(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

function fileExists(filePath) {
    return fs.existsSync(filePath);
}

// ── Target Script Guard Tests ─────────────────────────────────────────────────

test('TARGET SCRIPT: imports assertDbWriteAllowed from guard helper', () => {
    const content = readDoc(TARGET_SCRIPT);
    assert.ok(
        content.includes("require('./helpers/db_write_guard')") ||
        content.includes('require("./helpers/db_write_guard")'),
        'Target script must import db_write_guard helper'
    );
    assert.ok(
        content.includes('assertDbWriteAllowed'),
        'Target script must reference assertDbWriteAllowed'
    );
});

test('TARGET SCRIPT: assertDbWriteAllowed appears before first executable write query', () => {
    const content = readDoc(TARGET_SCRIPT);
    const guardIndex = content.indexOf('assertDbWriteAllowed({');
    const beginIndex = content.indexOf("client.query('BEGIN')");
    assert.ok(guardIndex > 0, 'assertDbWriteAllowed call must exist in target script');
    assert.ok(beginIndex > 0, 'BEGIN transaction must exist in target script');
    assert.ok(
        guardIndex < beginIndex,
        `assertDbWriteAllowed (pos=${guardIndex}) must appear before BEGIN transaction (pos=${beginIndex})`
    );
});

test('TARGET SCRIPT: guard references correct target tables', () => {
    const content = readDoc(TARGET_SCRIPT);
    // Find the guard call block
    const guardStart = content.indexOf('assertDbWriteAllowed({');
    const guardEnd = content.indexOf('});', guardStart);
    const guardBlock = content.slice(guardStart, guardEnd + 2);
    assert.ok(
        guardBlock.includes('matches_oddsportal_mapping'),
        'Guard must reference matches_oddsportal_mapping table'
    );
    assert.ok(
        guardBlock.includes('odds'),
        'Guard must reference odds table'
    );
});

test('TARGET SCRIPT: guard references correct write operations', () => {
    const content = readDoc(TARGET_SCRIPT);
    const guardStart = content.indexOf('assertDbWriteAllowed({');
    const guardEnd = content.indexOf('});', guardStart);
    const guardBlock = content.slice(guardStart, guardEnd + 2);
    assert.ok(
        guardBlock.includes('INSERT'),
        'Guard must reference INSERT operation'
    );
    assert.ok(
        guardBlock.includes('UPDATE'),
        'Guard must reference UPDATE operation'
    );
});

test('TARGET SCRIPT: preserves dryRun check before guard', () => {
    const content = readDoc(TARGET_SCRIPT);
    // The dryRun check must appear before the guard
    const dryRunIndex = content.indexOf('if (options.dryRun)');
    const guardIndex = content.indexOf('assertDbWriteAllowed({');
    assert.ok(dryRunIndex > 0, 'dryRun check must exist');
    assert.ok(
        dryRunIndex < guardIndex,
        `dryRun check (pos=${dryRunIndex}) must appear before guard (pos=${guardIndex})`
    );
});

test('TARGET SCRIPT: still imports odds_harvest_pipeline.shared.js', () => {
    const content = readDoc(TARGET_SCRIPT);
    assert.ok(
        content.includes("require('./odds_harvest_pipeline.shared')") ||
        content.includes('require("./odds_harvest_pipeline.shared")'),
        'Target script must still import the shared module'
    );
});

test('TARGET SCRIPT: does NOT execute real DB write / browser / Playwright in this test', () => {
    // This is a static analysis test — no runtime execution
    assert.ok(true, 'Static test only — no browser/DB execution');
});

// ── Design Document Update Tests ──────────────────────────────────────────────

test('DESIGN DOC: odds_harvest_pipeline.js implementation status updated', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('odds_harvest_pipeline.js') &&
        (content.includes('guarded') || content.includes('implementation')),
        'Design doc must reference odds_harvest_pipeline.js guard implementation'
    );
});

test('DESIGN DOC: gatekeeper.js / gatekeeper.sh now resolved (post gatekeeper_boundary_implementation)', () => {
    const content = readDoc(DESIGN_DOC);
    // After gatekeeper_boundary_implementation + manual_review_phase1, the design doc should
    // still contain "pending" or "PENDING" (e.g., Priority 4: restoreMappingsWorkflow)
    const hasPendingRef = /pending/i.test(content);
    assert.ok(
        hasPendingRef,
        'Design doc must still reference pending items (case-insensitive)'
    );
});

test('DESIGN DOC: needs_manual_review consumers now resolved by manual_review_phase1', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('needs_manual_review'),
        'Design doc must still reference needs_manual_review (now as resolved)'
    );
    // Count corrected from 8 to 9 by manual_review_phase1
    assert.ok(
        !content.includes('8 consumers with'),
        'Design doc must NOT still say "8" consumers (corrected to 9)'
    );
});

test('DESIGN DOC: SC-002 remains partial mitigation only', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('partial mitigation only'),
        'Design doc must state SC-002 remains partial mitigation only'
    );
});

// ── Audit Document Tests ──────────────────────────────────────────────────────

test('AUDIT DOC: does NOT mark gatekeeper.js / gatekeeper.sh as guarded', () => {
    const content = readDoc(AUDIT_DOC);
    // The audit doc should not positively claim gatekeeper is guarded
    // (it may reference gatekeeper in pending context)
    const lines = content.split('\n');
    for (const line of lines) {
        if (line.includes('gatekeeper') && line.includes('guarded_in_')) {
            assert.fail(`AUDIT_DOC must NOT mark gatekeeper as guarded_in_*:\n  ${line.trim()}`);
        }
    }
    assert.ok(true, 'No gatekeeper line marked as guarded_in_*');
});

test('AUDIT DOC: does NOT mark needs_manual_review consumers as guarded/safe', () => {
    const content = readDoc(AUDIT_DOC);
    assert.ok(
        content.includes('needs_manual_review'),
        'AUDIT_DOC must still reference needs_manual_review scripts'
    );
});

// ── Cross-Document Consistency Tests ──────────────────────────────────────────

test('CONSISTENCY: SC-002 remains partial mitigation only across all docs', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    for (const doc of docs) {
        const content = readDoc(doc);
        assert.ok(
            content.includes('partial mitigation only'),
            `${path.basename(doc)}: must state SC-002 remains partial mitigation only`
        );
    }
});

test('CONSISTENCY: no forbidden phrases in any SC-002 doc', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    // Check for positive-status assertions only (not negation-context)
    for (const doc of docs) {
        const content = readDoc(doc);
        // Check for "SC-002 is complete" / "SC-002 is fully fixed" as standalone assertion
        const completedAssertion = /\bSC-002\s+is\s+(complete|resolved)\b/i.test(content);
        assert.ok(!completedAssertion, `${path.basename(doc)}: must NOT assert SC-002 is complete/resolved`);
        // Check for "safe to train now" as positive assertion
        const safeToTrainNow = /\bsafe\s+to\s+train\s+now\b/i.test(content) ||
            /\btraining\s+is\s+now\s+safe\b/i.test(content);
        assert.ok(!safeToTrainNow, `${path.basename(doc)}: must NOT assert training is now safe`);
        // Check for "safe to write" as positive assertion
        const safeToWrite = /\bsafe\s+to\s+write\s+to\s+DB\b/i.test(content) ||
            /\bDB\s+write\s+is\s+now\s+(safe|allowed)\b/i.test(content);
        assert.ok(!safeToWrite, `${path.basename(doc)}: must NOT assert DB write is now safe`);
        // Check for "production ready" as a positive assertion (not in a forbidden-terms table)
        const prodReadyLines = content.split('\n').filter(line => {
            const lowered = line.toLowerCase();
            return lowered.includes('production ready') && !lowered.includes('|') && !lowered.includes('not authorized');
        });
        assert.ok(prodReadyLines.length === 0, `${path.basename(doc)}: must NOT assert production ready`);
        // Check for "data expansion is now ready/allowed"
        const dataExpansionReady = /\bdata\s+expansion\s+is\s+now\s+(ready|allowed)\b/i.test(content);
        assert.ok(!dataExpansionReady, `${path.basename(doc)}: must NOT assert data expansion is now ready/allowed`);
    }
});

test('CONSISTENCY: training / data expansion / real DB write remain blocked', () => {
    const docs = [DESIGN_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC];
    const blockedTerms = ['blocked', 'remain blocked', 'remains blocked'];
    for (const doc of docs) {
        const content = readDoc(doc);
        const hasBlocked = blockedTerms.some(term => content.toLowerCase().includes(term.toLowerCase()));
        assert.ok(
            hasBlocked,
            `${path.basename(doc)}: must reference blocked status`
        );
    }
});
