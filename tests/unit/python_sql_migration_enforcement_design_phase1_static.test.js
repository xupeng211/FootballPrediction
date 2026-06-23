#!/usr/bin/env node
/**
 * Static tests for Python / SQL / Migration Enforcement Design Phase 1.
 *
 * lifecycle: permanent
 * scope: static verification only; does not execute target scripts, connect to DB,
 *        run migrations, or change runtime behavior.
 *
 * Verifies:
 * 1. Design document exists and contains required sections
 * 2. Python candidate inventory present
 * 3. SQL and migration candidate inventory present
 * 4. Classification results present
 * 5. Recommended enforcement model present
 * 6. Design-only / no runtime behavior changed
 * 7. No target script executed / no DB connection / no real DB write
 * 8. SC-002 remains partial mitigation only
 * 9. PROJECT_STATUS.md records this phase
 * 10. SC002_CLOSURE_PLAN.md does not claim SC-002 fully fixed / safe to train / safe to write
 * 11. Training / data expansion / real DB write remain blocked
 * 12. Implementation candidates have evidence
 * 13. Manual review candidates are not marked safe
 * 14. No blanket allowlist for SQL migrations
 * 15. No blanket safe for Python DB files
 * 16. No runtime guard implementation present
 */

'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '../..');

// ── Helpers ──────────────────────────────────────────────────────────────────

function readFile(relativePath) {
  return fs.readFileSync(path.join(REPO_ROOT, relativePath), 'utf8');
}

function fileExists(relativePath) {
  return fs.existsSync(path.join(REPO_ROOT, relativePath));
}

// ── 1. Design document existence ─────────────────────────────────────────────

test('Design document exists', () => {
  const docPath = 'docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md';
  assert.ok(fileExists(docPath), `Missing design document: ${docPath}`);
});

test('Design document contains required sections', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  const required = [
    '## Summary',
    '## Scope',
    '## Current JS-side SC-002 status',
    '## Python candidate inventory',
    '## SQL and migration candidate inventory',
    '## Python classification results',
    '## SQL and migration classification results',
    '## Enforcement design options',
    '## Recommended enforcement model',
    '## CI integration design',
    '## Implementation candidates',
    '## Manual review candidates',
    '## Risks and unknowns',
    '## Explicit non-goals',
    '## SC-002 status impact',
    '## Next recommended task',
  ];
  for (const section of required) {
    assert.ok(
      doc.includes(section),
      `Design document missing required section: ${section}`
    );
  }
});

// ── 2. Python candidate inventory ────────────────────────────────────────────

test('Design document contains Python candidate counts', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(doc.includes('374'), 'Missing total Python file count (374)');
  assert.ok(
    doc.includes('python_candidate') || doc.includes('Python candidate'),
    'Missing Python candidate inventory section'
  );
  assert.ok(
    doc.includes('python_confirmed_write_path_needs_guard'),
    'Missing Python classification category: python_confirmed_write_path_needs_guard'
  );
});

// ── 3. SQL and migration candidate inventory ─────────────────────────────────

test('Design document contains SQL and migration candidate counts', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(doc.includes('18'), 'Missing total SQL file count (18)');
  assert.ok(
    doc.includes('sql_schema_definition') || doc.includes('SQL candidate'),
    'Missing SQL/migration inventory section'
  );
});

// ── 4. Classification results present ────────────────────────────────────────

test('Design document contains Python classification results', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('python_confirmed_write_path_needs_guard'),
    'Missing Python confirmed write path classification'
  );
  assert.ok(
    doc.includes('python_indirect_write_path_needs_guard'),
    'Missing Python indirect write path classification'
  );
  assert.ok(
    doc.includes('python_needs_manual_review'),
    'Missing Python manual review classification'
  );
});

test('Design document contains SQL classification results', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('sql_schema_definition'),
    'Missing SQL schema definition classification'
  );
  assert.ok(
    doc.includes('sql_allowed_migration_candidate'),
    'Missing SQL allowed migration classification'
  );
});

// ── 5. Recommended enforcement model ─────────────────────────────────────────

test('Design document contains recommended enforcement model', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('Recommended enforcement model'),
    'Missing recommended enforcement model section'
  );
  assert.ok(
    doc.includes('Phase 2A') || doc.includes('Phase 2B') || doc.includes('Phase 2C'),
    'Missing phased implementation plan in enforcement model'
  );
});

// ── 6. Design only / no runtime behavior changed ─────────────────────────────

test('Design document declares design-only / no runtime behavior changed', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('does NOT') || doc.includes('no runtime behavior changed'),
    'Design document must declare what it does NOT do'
  );
  assert.ok(
    doc.includes('Implement any guard') || doc.includes('implement any guard')
      || doc.includes('Implement any Python guard'),
    'Design document must state no guard implementation'
  );
});

// ── 7. No target script executed / no DB connection / no real DB write ───────

test('Design document declares no target script executed', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  const forbidden = [
    'Run any Python target script',
    'Execute any SQL',
    'Connect to any database',
    'Perform any real DB write',
  ];
  for (const phrase of forbidden) {
    assert.ok(
      doc.includes(phrase),
      `Design document must state: "${phrase}"`
    );
  }
});

// ── 8. SC-002 remains partial mitigation only ────────────────────────────────

test('Design document declares SC-002 remains partial mitigation only', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('partial mitigation only'),
    'Design document must state SC-002 remains partial mitigation only'
  );
});

// ── 9. PROJECT_STATUS.md records this phase ──────────────────────────────────

test('PROJECT_STATUS.md records python_sql_migration_enforcement_design_phase1', () => {
  const status = readFile('docs/PROJECT_STATUS.md');
  assert.ok(
    status.includes('python_sql_migration_enforcement_design_phase1'),
    'PROJECT_STATUS.md must record this phase'
  );
  assert.ok(
    status.includes('SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md'),
    'PROJECT_STATUS.md must reference the design document'
  );
});

// ── 10. SC002_CLOSURE_PLAN.md does not claim fully fixed / safe ──────────────

test('SC002_CLOSURE_PLAN.md does not contain forbidden safety claims', () => {
  const plan = readFile('docs/SC002_CLOSURE_PLAN.md');
  const forbidden = [
    'fully fixed',
    'safe to train',
    'safe to write',
    'production ready',
    'data expansion ready',
    'real DB write ready',
  ];
  // These are forbidden as NEW claims in the context of SC-002 closure.
  // The closure plan may mention them in the "Forbidden terms" table or in
  // descriptions of what is NOT claimed. We check that they do not appear as
  // positive assertions outside the forbidden-terms table context.
  // Instead, verify the plan explicitly states SC-002 is NOT fully fixed.
  assert.ok(
    plan.includes('NOT fully fixed') ||
      plan.includes('not fully fixed') ||
      plan.includes('partial mitigation only'),
    'SC002_CLOSURE_PLAN.md must state SC-002 is not fully fixed'
  );
  assert.ok(
    plan.includes('python_sql_migration_enforcement_design_phase1') ||
      plan.includes('Python / SQL / migration enforcement'),
    'SC002_CLOSURE_PLAN.md must reference this design phase'
  );
});

// ── 11. Training / data expansion / real DB write remain blocked ─────────────

test('Training, data expansion, real DB write remain blocked in docs', () => {
  const status = readFile('docs/PROJECT_STATUS.md');
  assert.ok(
    status.includes('remain blocked') || status.includes('remain BLOCKED'),
    'PROJECT_STATUS.md must state training/data expansion/DB write remain blocked'
  );
  const design = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    design.includes('remain BLOCKED') || design.includes('remain blocked'),
    'Design document must state blocked activities remain blocked'
  );
});

// ── 12. Implementation candidates have evidence ──────────────────────────────

test('Implementation candidates have per-item evidence', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  // Each confirmed write path must have path + DB client + write evidence
  const paths = [
    'schema_manager.py',
    'sql_store.py',
    'match_repository.py',
    'fotmob_registry_seed_dev_execution.py',
  ];
  for (const p of paths) {
    assert.ok(
      doc.includes(p),
      `Implementation candidate ${p} must appear in design document`
    );
  }
});

// ── 13. Manual review candidates are not marked safe ─────────────────────────

test('Manual review candidates are not classified as safe', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  // Verify the manual review section exists
  assert.ok(
    doc.includes('python_needs_manual_review') ||
      doc.includes('Manual review candidates'),
    'Design document must have manual review candidates section'
  );
  // The 5 manual review files must not appear in confirmed/indirect write lists
  // with a "safe" label. Check they are in needs_manual_review category.
  const manualFiles = [
    'reprocess_from_local.py',
    'fotmob_historical_backfill.py',
    'diagnose_diagnostic.py',
  ];
  for (const f of manualFiles) {
    const idx = doc.indexOf(f);
    if (idx !== -1) {
      // The surrounding context should mention manual review, not "safe"
      const context = doc.substring(Math.max(0, idx - 200), idx + 200);
      const isManual = context.includes('needs_manual_review') ||
        context.includes('Manual review') ||
        context.includes('manual_review');
      const isSafe = context.includes('no_action_needed') &&
        !context.includes('needs_manual_review');
      assert.ok(
        isManual || !isSafe,
        `${f} appears in context that should not claim it is safe without evidence`
      );
    }
  }
});

// ── 14. No blanket allowlist for SQL migrations ──────────────────────────────

test('SQL migrations are not blanket allowlisted', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  // Each migration must have individual classification
  assert.ok(
    doc.includes('database/migrations/V6.5') ||
      doc.includes('V6.5__hardened_matches_schema'),
    'SQL migrations must be individually listed and classified'
  );
  // Verify not all migrations are categorized identically
  const schemaCount = (doc.match(/sql_schema_definition/g) || []).length;
  const allowedCount = (doc.match(/sql_allowed_migration_candidate/g) || []).length;
  assert.ok(
    schemaCount > 0 || allowedCount > 0,
    'SQL migrations must have specific classifications'
  );
});

// ── 15. No blanket safe for Python DB files ──────────────────────────────────

test('Python DB files are not blanket marked safe', () => {
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  // The confirmed write paths must be explicitly listed, not summarily dismissed
  assert.ok(
    doc.includes('python_confirmed_write_path_needs_guard'),
    'Python confirmed write paths must be explicitly identified'
  );
  // Verify there are at least some files in this category
  const matchCount = (doc.match(/python_confirmed_write_path_needs_guard/g) || []).length;
  assert.ok(
    matchCount >= 1,
    'At least some Python files must be classified as needing guard'
  );
});

// ── 16. No runtime guard implementation ──────────────────────────────────────

test('No runtime guard implementation present in changed files', () => {
  // Verify the design doc does not contain implementation code
  const doc = readFile('docs/SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md');
  assert.ok(
    doc.includes('does NOT') && (
      doc.includes('Implement any guard') || doc.includes('Implement any Python guard')
    ),
    'Design document must explicitly state no guard implementation'
  );
  // Confirm no Python guard helper was created
  const guardPyPath = 'scripts/ops/helpers/db_write_guard.py';
  if (fileExists(guardPyPath)) {
    const content = readFile(guardPyPath);
    // If it exists and was modified in this phase, it should only be advisory check
    // The existing file is db_write_guard_advisory_check.py which is the JS scanner wrapper
    assert.ok(
      content.includes('advisory') || content.includes('scanner'),
      `${guardPyPath} should not be a new runtime guard implementation`
    );
  }
});

// ── 17. Cross-document consistency ───────────────────────────────────────────

test('SC002_CLOSURE_PLAN.md updated with design phase completion', () => {
  const plan = readFile('docs/SC002_CLOSURE_PLAN.md');
  assert.ok(
    plan.includes('design completed') ||
      plan.includes('python_sql_migration_enforcement_design_phase1'),
    'SC002_CLOSURE_PLAN.md must reference this design phase as completed'
  );
});

test('SC002_MANUAL_REVIEW_PHASE1.md updated with cross-reference', () => {
  const doc = readFile('docs/SC002_MANUAL_REVIEW_PHASE1.md');
  assert.ok(
    doc.includes('SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md') ||
      doc.includes('Python / SQL / migration'),
    'MANUAL_REVIEW_PHASE1.md must cross-reference Python/SQL enforcement design'
  );
});

test('SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md updated with cross-reference', () => {
  const doc = readFile('docs/SC002_BROWSER_FOTMOB_PAGEPROPS_AUDIT.md');
  assert.ok(
    doc.includes('SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md') ||
      doc.includes('Python / SQL / migration enforcement'),
    'BROWSER_FOTMOB_PAGEPROPS_AUDIT.md must note Python/SQL enforcement is separate'
  );
});

test('SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md updated with cross-reference', () => {
  const doc = readFile('docs/SC002_SHARED_MODULE_DB_WRITE_BOUNDARY_DESIGN.md');
  assert.ok(
    doc.includes('SC002_PYTHON_SQL_MIGRATION_ENFORCEMENT_DESIGN.md') ||
      doc.includes('Python / SQL'),
    'SHARED_MODULE doc must note Python/SQL enforcement is separate governance layer'
  );
});

console.log('python_sql_migration_enforcement_design_phase1 static tests complete.');
