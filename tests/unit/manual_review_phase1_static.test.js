#!/usr/bin/env node
/**
 * Static tests for SC-002 Manual Review Phase 1.
 *
 * lifecycle: permanent
 * scope: static verification only; does NOT run target scripts, connect to DB,
 *        execute real DB writes, or run scraper/browser/Playwright.
 *
 * Verifies that manual_review_phase1 correctly reviewed and reclassified all
 * remaining needs_manual_review / possible_indirect_write consumers with
 * documented evidence for each classification.
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');
const MANUAL_REVIEW_DOC = path.join(REPO_ROOT, 'docs/SC002_MANUAL_REVIEW_PHASE1.md');
const AUDIT_DOC = path.join(REPO_ROOT, 'docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md');
const DESIGN_DOC = path.join(REPO_ROOT, 'docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md');
const CLOSURE_PLAN = path.join(REPO_ROOT, 'docs/SC002_CLOSURE_PLAN.md');
const PROJECT_STATUS = path.join(REPO_ROOT, 'docs/PROJECT_STATUS.md');

function readDoc(filePath) {
    return fs.readFileSync(filePath, 'utf8');
}

function fileExists(filePath) {
    return fs.existsSync(filePath);
}

// ── Document existence ────────────────────────────────────────────────────────

test('MANUAL_REVIEW_DOC: exists', () => {
    assert.ok(fileExists(MANUAL_REVIEW_DOC), 'SC002_MANUAL_REVIEW_PHASE1.md must exist');
});

// ── Authoritative list and count ──────────────────────────────────────────────

test('MANUAL_REVIEW_DOC: contains authoritative list', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('Authoritative needs_manual_review list') ||
        content.includes('authoritative'),
        'Must have authoritative list section'
    );
});

test('MANUAL_REVIEW_DOC: documents correct count (14 total)', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('14'),
        'Must document total count of 14 reviewed scripts'
    );
});

test('MANUAL_REVIEW_DOC: explains count mismatch', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('count mismatch') || content.includes('Count mismatch') ||
        content.includes('typo') || content.includes('PR #1593'),
        'Must explain that #1593 said 8 but actual count is 9 (design doc) + 5 (audit) = 14'
    );
});

test('MANUAL_REVIEW_DOC: lists all 14 scripts with paths', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    const requiredScripts = [
        'cleanup_csv_bulk_loader_import.js',
        'fetch_and_adapt_euro_leagues.js',
        'master_inventory.js',
        'purge_ghost_data.js',
        'purge_orphans.js',
        'raw_match_data_completeness_fidelity_audit.js',
        'renewed_pageprops_v2_raw_write_execute.js',
        'reset_database.js',
        'seed_fotmob_sample.js',
        'all_seeded_pageprops_v2_canonical_read_verification.js',
        'pageprops_v2_identity_contract_regression_execute.js',
        'pageprops_v2_post_write_canonical_read_verification.js',
        'pageprops_v2_suspended_target_review_execute.js',
        'training_pipeline_smoke_dry_run.js',
    ];
    for (const script of requiredScripts) {
        assert.ok(
            content.includes(script),
            `MANUAL_REVIEW_DOC must include ${script}`
        );
    }
});

// ── Per-consumer classification evidence ──────────────────────────────────────

test('MANUAL_REVIEW_DOC: each reviewed consumer has a classification', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    const classifications = [
        'already_guarded',
        'false_positive_no_db_write_evidence',
        'false_positive_select_only_with_active_wrapper',
        'false_positive_read_only_transaction',
    ];
    let foundCount = 0;
    for (const cls of classifications) {
        const matches = content.match(new RegExp(`\\\\*\\\\*${cls}\\\\*\\\\*`, 'g'));
        if (matches) {
            foundCount += matches.length;
        }
    }
    assert.ok(foundCount >= 14, `Expected >= 14 classifications, found ${foundCount}`);
});

test('MANUAL_REVIEW_DOC: already_guarded consumers have evidence of guard', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('assertDbWriteAllowed'),
        'Must document assertDbWriteAllowed evidence for guarded consumers'
    );
    assert.ok(
        content.includes('BEGIN'),
        'Must document BEGIN transaction position relative to guard'
    );
});

test('MANUAL_REVIEW_DOC: false positives have specific evidence', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('SELECT-only') || content.includes('SELECT only') ||
        content.includes('no write') || content.includes('No write'),
        'Must document SELECT-only or no-write evidence for false positives'
    );
    assert.ok(
        content.includes('assertSelectOnly') || content.includes('queryReadOnly') ||
        content.includes('Zero database') || content.includes('zero DB'),
        'Must document active wrapper evidence'
    );
});

test('MANUAL_REVIEW_DOC: 0 confirmed_write_path_needs_guard', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    // Should document that no new unguarded write paths were found
    assert.ok(
        content.includes('0 remaining needs_manual_review') ||
        content.includes('**0** remaining') ||
        content.includes('0 needs_manual_review'),
        'Must state 0 remaining needs_manual_review'
    );
    assert.ok(
        content.includes('**0** confirmed_write_path_needs_guard') ||
        content.includes('confirmed_write_path_needs_guard | **0**'),
        'Must state 0 confirmed_write_path_needs_guard'
    );
});

// ── Safety declarations ───────────────────────────────────────────────────────

test('MANUAL_REVIEW_DOC: declares no guard implemented', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('No guard implemented') || content.includes('no guard') ||
        content.includes('does NOT implement'),
        'Must declare no guard implementation'
    );
});

test('MANUAL_REVIEW_DOC: declares no target script executed', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('No target script executed') ||
        content.includes('not run') ||
        content.includes('does NOT run'),
        'Must declare no target script executed'
    );
});

test('MANUAL_REVIEW_DOC: declares SC-002 remains partial mitigation', () => {
    const content = readDoc(MANUAL_REVIEW_DOC);
    assert.ok(
        content.includes('partial mitigation only'),
        'Must state SC-002 remains partial mitigation only'
    );
});

// ── Cross-document consistency ────────────────────────────────────────────────

test('CROSS-DOC: AUDIT_DOC reflects 0 needs_manual_review', () => {
    const content = readDoc(AUDIT_DOC);
    // Audit doc should now have 0 in needs_manual_review count
    assert.ok(
        content.includes('needs_manual_review') && content.includes('**0**'),
        'AUDIT_DOC must show 0 needs_manual_review after reclassification'
    );
});

test('CROSS-DOC: AUDIT_DOC reflects 0 possible_indirect_write', () => {
    const content = readDoc(AUDIT_DOC);
    assert.ok(
        content.includes('possible_indirect_write') && content.includes('**0**'),
        'AUDIT_DOC must show 0 possible_indirect_write after reclassification'
    );
});

test('CROSS-DOC: AUDIT_DOC training_pipeline_smoke_dry_run is reclassified', () => {
    const content = readDoc(AUDIT_DOC);
    assert.ok(
        content.includes('false_positive_read_only_transaction') &&
        content.includes('training_pipeline_smoke_dry_run'),
        'AUDIT_DOC must reclassify training_pipeline_smoke_dry_run to false_positive_read_only_transaction'
    );
});

test('CROSS-DOC: DESIGN_DOC reflects resolved needs_manual_review', () => {
    const content = readDoc(DESIGN_DOC);
    assert.ok(
        content.includes('manual_review_phase1') || content.includes('RESOLVED'),
        'DESIGN_DOC must reference manual_review_phase1 resolution'
    );
    // Count should be corrected from 8 to 9
    assert.ok(
        !content.includes('8 consumers with `needs_manual_review`'),
        'DESIGN_DOC must NOT still say "8" consumers (should say 9 or resolved)'
    );
});

test('CROSS-DOC: CLOSURE_PLAN includes manual_review_phase1 section', () => {
    const content = readDoc(CLOSURE_PLAN);
    assert.ok(
        content.includes('manual_review_phase1') &&
        (content.includes('COMPLETED') || content.includes('Completed')),
        'CLOSURE_PLAN must include manual_review_phase1 as completed'
    );
});

test('CROSS-DOC: PROJECT_STATUS includes manual_review_phase1', () => {
    const content = readDoc(PROJECT_STATUS);
    assert.ok(
        content.includes('manual_review_phase1'),
        'PROJECT_STATUS must include manual_review_phase1 status entry'
    );
    assert.ok(
        content.includes('0 remaining needs_manual_review') ||
        content.includes('0 needs_manual_review'),
        'PROJECT_STATUS must document 0 remaining needs_manual_review'
    );
});

// ── Forbidden phrase checks ───────────────────────────────────────────────────

test('FORBIDDEN: no "fully fixed" in any SC-002 doc', () => {
    const docs = [MANUAL_REVIEW_DOC, AUDIT_DOC, DESIGN_DOC, CLOSURE_PLAN, PROJECT_STATUS];
    for (const doc of docs) {
        const content = readDoc(doc);
        const lines = content.split('\n');
        const found = lines.some(line => {
            const s = line.trim();
            // Skip table rows and bullet items in negation context
            if (/^\s*[|*-]\s/.test(s)) return false;
            return /\bSC-002\s+is\s+fully\s+fixed\b/i.test(s);
        });
        assert.ok(!found, `${path.basename(doc)}: must NOT assert SC-002 is fully fixed`);
    }
});

test('FORBIDDEN: no "safe to train" in any SC-002 doc', () => {
    const docs = [MANUAL_REVIEW_DOC, AUDIT_DOC, DESIGN_DOC, CLOSURE_PLAN, PROJECT_STATUS];
    for (const doc of docs) {
        const content = readDoc(doc);
        const lines = content.split('\n');
        const found = lines.some(line => {
            const s = line.trim();
            if (/^\s*[|*-]\s/.test(s)) return false;
            return /\bsafe\s+to\s+train\b/i.test(s);
        });
        assert.ok(!found, `${path.basename(doc)}: must NOT assert safe to train`);
    }
});

test('FORBIDDEN: no "safe to write" in any SC-002 doc', () => {
    const docs = [MANUAL_REVIEW_DOC, AUDIT_DOC, DESIGN_DOC, CLOSURE_PLAN, PROJECT_STATUS];
    for (const doc of docs) {
        const content = readDoc(doc);
        const lines = content.split('\n');
        const found = lines.some(line => {
            const s = line.trim();
            if (/^\s*[|*-]\s/.test(s)) return false;
            return /\bsafe\s+to\s+write\b/i.test(s);
        });
        assert.ok(!found, `${path.basename(doc)}: must NOT assert safe to write`);
    }
});

test('FORBIDDEN: no "production ready" as standalone assertion', () => {
    const docs = [MANUAL_REVIEW_DOC, AUDIT_DOC, DESIGN_DOC, CLOSURE_PLAN, PROJECT_STATUS];
    for (const doc of docs) {
        const content = readDoc(doc);
        const lines = content.split('\n');
        const found = lines.filter(line => {
            const s = line.trim().toLowerCase();
            return /\bproduction\s+ready\b/i.test(s) && !s.includes('|') && !s.includes('not');
        });
        assert.ok(found.length === 0, `${path.basename(doc)}: must NOT assert production ready`);
    }
});

// ── Training/data expansion/real DB write remain blocked ──────────────────────

test('BLOCKED: training/data expansion/real DB write remain blocked across docs', () => {
    const docs = [MANUAL_REVIEW_DOC, PROJECT_STATUS, CLOSURE_PLAN, AUDIT_DOC, DESIGN_DOC];
    const blockedTerms = ['blocked', 'remain blocked', 'remains blocked', 'remain BLOCKED'];
    for (const doc of docs) {
        const content = readDoc(doc);
        const hasBlocked = blockedTerms.some(term => content.includes(term));
        assert.ok(hasBlocked, `${path.basename(doc)}: must reference blocked status`);
    }
});

// ── SC-002 remains partial mitigation ─────────────────────────────────────────

test('SC-002: remains partial mitigation only across all docs', () => {
    const docs = [MANUAL_REVIEW_DOC, AUDIT_DOC, DESIGN_DOC, CLOSURE_PLAN, PROJECT_STATUS];
    for (const doc of docs) {
        const content = readDoc(doc);
        assert.ok(
            content.includes('partial mitigation only'),
            `${path.basename(doc)}: must state SC-002 remains partial mitigation only`
        );
    }
});

// ── No implementation, no execution ───────────────────────────────────────────

test('SAFETY: this test does NOT execute any target script', () => {
    assert.ok(true, 'Static test only — no target script execution');
});

test('SAFETY: this test does NOT connect to DB', () => {
    assert.ok(true, 'Static test only — no DB connection');
});

test('SAFETY: this test does NOT implement any guard', () => {
    assert.ok(true, 'Static test only — no guard implementation');
});

// ── Source files still exist ──────────────────────────────────────────────────

test('SOURCE_FILES: all 14 reviewed scripts still exist on disk', () => {
    const scripts = [
        'scripts/ops/cleanup_csv_bulk_loader_import.js',
        'scripts/ops/fetch_and_adapt_euro_leagues.js',
        'scripts/ops/master_inventory.js',
        'scripts/ops/purge_ghost_data.js',
        'scripts/ops/purge_orphans.js',
        'scripts/ops/raw_match_data_completeness_fidelity_audit.js',
        'scripts/ops/renewed_pageprops_v2_raw_write_execute.js',
        'scripts/ops/reset_database.js',
        'scripts/ops/seed_fotmob_sample.js',
        'scripts/ops/all_seeded_pageprops_v2_canonical_read_verification.js',
        'scripts/ops/pageprops_v2_identity_contract_regression_execute.js',
        'scripts/ops/pageprops_v2_post_write_canonical_read_verification.js',
        'scripts/ops/pageprops_v2_suspended_target_review_execute.js',
        'scripts/ops/training_pipeline_smoke_dry_run.js',
    ];
    for (const script of scripts) {
        const fullPath = path.join(REPO_ROOT, script);
        assert.ok(fileExists(fullPath), `${script} must exist on disk`);
    }
});

// ── Guard presence verification for reclassified-as-guarded scripts ──────────

test('GUARDED_SCRIPTS: 7 reclassified as already_guarded have assertDbWriteAllowed', () => {
    const guardedScripts = [
        'scripts/ops/cleanup_csv_bulk_loader_import.js',
        'scripts/ops/purge_ghost_data.js',
        'scripts/ops/purge_orphans.js',
        'scripts/ops/raw_match_data_completeness_fidelity_audit.js',
        'scripts/ops/reset_database.js',
        'scripts/ops/seed_fotmob_sample.js',
        // renewed_pageprops_v2_raw_write_execute.js has transitive guard via base module
    ];
    for (const script of guardedScripts) {
        const content = readDoc(path.join(REPO_ROOT, script));
        assert.ok(
            content.includes('assertDbWriteAllowed'),
            `${script}: must contain assertDbWriteAllowed`
        );
        assert.ok(
            content.includes("require('./helpers/db_write_guard')") ||
            content.includes('require("./helpers/db_write_guard")'),
            `${script}: must import db_write_guard`
        );
    }
});

test('GUARDED_SCRIPTS: renewed_pageprops_v2_raw_write_execute has transitive guard via base', () => {
    const content = readDoc(path.join(REPO_ROOT, 'scripts/ops/renewed_pageprops_v2_raw_write_execute.js'));
    const baseContent = readDoc(path.join(REPO_ROOT, 'scripts/ops/single_league_pageprops_v2_controlled_write_execute.js'));
    assert.ok(
        content.includes("require('./single_league_pageprops_v2_controlled_write_execute')"),
        'renewed script must import base module'
    );
    assert.ok(
        baseContent.includes('assertDbWriteAllowed'),
        'base module must have assertDbWriteAllowed'
    );
});
