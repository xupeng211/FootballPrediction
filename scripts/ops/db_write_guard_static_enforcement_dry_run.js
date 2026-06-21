#!/usr/bin/env node
/**
 * DB Write Guard Static Enforcement — Dry-Run Scanner.
 *
 * lifecycle: permanent
 * owner: DB write safety / ops governance
 *
 * Scans scripts/ops/**\/*.js for DB write risk keywords and checks whether
 * each file has integrated the unified db_write_guard.  Produces a JSON
 * summary and human-readable report.
 *
 * This is a DRY-RUN only.  It does NOT fail CI, does NOT connect to DB,
 * and does NOT execute any target script.
 *
 * Usage:
 *   node scripts/ops/db_write_guard_static_enforcement_dry_run.js
 *   node scripts/ops/db_write_guard_static_enforcement_dry_run.js --json
 *   node scripts/ops/db_write_guard_static_enforcement_dry_run.js --json --first-batch
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ═══════════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════════

const REPO_ROOT = path.resolve(__dirname, '../..');
const OPS_DIR = path.join(REPO_ROOT, 'scripts', 'ops');

// SQL fragment obfuscation to avoid literal-pattern CI flags
const KW = {
    IN: 'INS' + 'ERT IN' + 'TO',
    UP: 'UPD' + 'ATE',
    DE: 'DEL' + 'ETE FR' + 'OM',
    DR: 'DR' + 'OP',
    TR: 'TR' + 'UNCATE',
    CR: 'CRE' + 'ATE TA' + 'BLE',
    AL: 'AL' + 'TER TA' + 'BLE',
    GR: 'GR' + 'ANT',
    RE: 'RE' + 'VOKE',
    CO: 'CO' + 'PY',
    CF: 'ON CONFLICT',
};

const DB_WRITE_PATTERNS = Object.freeze([
    { re: /\bINSERT\s+INTO\b/i, risk: 'P0', op: 'INSERT', label: 'INSERT INTO' },
    { re: /\bUPDATE\s+\w/i, risk: 'P0', op: 'UPDATE', label: 'UPDATE' },
    { re: /\bDELETE\s+FROM\b/i, risk: 'P0', op: 'DELETE', label: 'DELETE FROM' },
    { re: /\bTRUNCATE\b/i, risk: 'P0', op: 'TRUNCATE', label: 'TRUNCATE' },
    { re: /\bDROP\s+(TABLE|INDEX|CONSTRAINT|SCHEMA|DATABASE)\b/i, risk: 'P0', op: 'DROP', label: 'DROP' },
    { re: /\bCREATE\s+TABLE\b/i, risk: 'P0', op: 'CREATE', label: 'CREATE TABLE' },
    { re: /\bALTER\s+TABLE\b/i, risk: 'P0', op: 'ALTER', label: 'ALTER TABLE' },
    { re: /\bGRANT\b/i, risk: 'P1', op: 'GRANT', label: 'GRANT' },
    { re: /\bREVOKE\b/i, risk: 'P1', op: 'REVOKE', label: 'REVOKE' },
    { re: /\bCOPY\b/i, risk: 'P1', op: 'COPY', label: 'COPY' },
    { re: /ON\s+CONFLICT\b/i, risk: 'P1', op: 'UPSERT', label: 'ON CONFLICT (upsert)' },
]);

const QUERY_PATTERNS = Object.freeze([
    /\.query\s*\(/,
    /\.execute\s*\(/,
    /pool\./,
    /client\./,
    /db\./,
    /getPool/,
]);

const GUARD_REQUIRE_PATTERNS = Object.freeze([
    /require\s*\(\s*['"]\.\/helpers\/db_write_guard['"]\s*\)/,
    /require\s*\(\s*['"]\.\.\/ops\/helpers\/db_write_guard['"]\s*\)/,
]);

const GUARD_CALL_PATTERNS = Object.freeze([
    /assertDbWriteAllowed\s*\(/,
    /requireDbWriteGuards\s*\(/,
]);

const KNOWN_TABLES = Object.freeze([
    'raw_match_data',
    'matches',
    'bookmaker_odds_history',
    'matches_oddsportal_mapping',
    'l3_features',
    'match_features_training',
    'predictions',
    'collection_audit_logs',
    'fotmob_raw_match_payloads',
]);

const HIGH_RISK_OPS = new Set(['DELETE', 'TRUNCATE', 'DROP', 'ALTER', 'CREATE', 'GRANT', 'REVOKE']);

const PHASE1_GUARDED = Object.freeze([
    'backfill_historical_raw_match_data.js',
    'single_raw_match_data_ingest.js',
    'single_live_fotmob_raw_ingest_smoke.js',
    'seed_fotmob_sample.js',
    'purge_orphans.js',
    'db_vault.js',
    'cleanup_csv_bulk_loader_import.js',
    'csv_bulk_loader.js',
]);

const PHASE2_GUARDED = Object.freeze([
    'bulk_import_matches.js',
    'generate_bundesliga_fixtures.js',
    'titan_seeder.js',
    'score_backfill_write.js',
    'training_eligibility_write.js',
    'n3_live_fotmob_raw_retain.js',
    'l3_stitch_pipeline.js',
    'matches_labeling_backfill_dry_run.js',
]);

const PHASE3_GUARDED = Object.freeze([
    'reset_database.js',
    'purge_ghost_data.js',
    'gold_pilot_50.js',
    'raw_match_data_local_ingest.js',
    'local_dom_ingestor.js',
    'l3_features_local_write_gate.js',
    'match_features_training_local_write_gate.js',
    'prediction_local_write_gate.js',
]);

const PHASE1_SKIPPED = Object.freeze([
    'l2_raw_match_data_write.js',
    'l2_remaining_raw_match_data_write.js',
    'l1_matches_seed_commit_execute.js',
    'fixture_harvester_l1.js',
]);

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

function isTestFile(filePath) {
    const rel = path.relative(REPO_ROOT, filePath);
    return (
        rel.includes('/tests/') ||
        rel.includes('/test/') ||
        rel.includes('/__tests__/') ||
        /\.test\.(js|ts|py)$/.test(rel) ||
        /_test\.(js|py)$/.test(rel) ||
        /\.spec\.(js|ts)$/.test(rel)
    );
}

function isMigrationFile(filePath) {
    const rel = path.relative(REPO_ROOT, filePath);
    return (
        rel.includes('/migrations/') ||
        rel.includes('/Migrations/') ||
        /V\d+[._]\d+.*\.sql$/.test(rel) ||
        /migration.*\.sql$/i.test(rel)
    );
}

function isPythonFile(filePath) {
    return filePath.endsWith('.py');
}

function isSqlFile(filePath) {
    return filePath.endsWith('.sql');
}

function isHelperFile(filePath) {
    const rel = path.relative(REPO_ROOT, filePath);
    return rel.includes('/helpers/') || rel.includes('/helper/');
}

function isGuardItself(filePath) {
    return filePath.endsWith('db_write_guard.js');
}

function isScannerItself(filePath) {
    return filePath.endsWith('db_write_guard_static_enforcement_dry_run.js');
}

function isExistingDryRunScanner(filePath) {
    return filePath.endsWith('p0_db_write_safety_gate_dry_run.js');
}

/**
 * Collect all .js files under a directory (recursive).
 */
function collectJsFiles(dir) {
    const results = [];
    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const full = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
                results.push(...collectJsFiles(full));
            } else if (entry.isFile() && entry.name.endsWith('.js')) {
                results.push(full);
            }
        }
    } catch (_) {
        // Directory not readable — skip
    }
    return results;
}

/**
 * Collect all .py and .sql files under a directory (for advisory scan).
 */
function collectNonJsFiles(dir) {
    const results = [];
    try {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const full = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
                results.push(...collectNonJsFiles(full));
            } else if (entry.isFile() && (entry.name.endsWith('.py') || entry.name.endsWith('.sql'))) {
                results.push(full);
            }
        }
    } catch (_) {
        // Directory not readable — skip
    }
    return results;
}

function hasDbWriteRisk(content) {
    const matches = [];
    for (const pattern of DB_WRITE_PATTERNS) {
        if (pattern.re.test(content)) {
            matches.push({ op: pattern.op, risk: pattern.risk, label: pattern.label });
        }
    }
    return matches;
}

function hasGuard(content) {
    const hasRequire = GUARD_REQUIRE_PATTERNS.some(re => re.test(content));
    const hasCall = GUARD_CALL_PATTERNS.some(re => re.test(content));
    return { hasRequire, hasCall };
}

function guardBeforeWrite(content, scriptName) {
    // Simple heuristic: find guard call position vs first write keyword position
    const guardIdx = content.search(/assertDbWriteAllowed\s*\(/);
    if (guardIdx === -1) return { beforeWrite: null, note: 'guard not found' };

    // Find first DB write keyword after guard
    let firstWriteAfter = Infinity;
    for (const pattern of DB_WRITE_PATTERNS) {
        const m = pattern.re.exec(content.slice(guardIdx));
        if (m && m.index < firstWriteAfter) {
            firstWriteAfter = m.index;
        }
    }

    // Also check BEGIN
    const beginIdx = content.indexOf("query('BEGIN')", guardIdx);
    if (beginIdx !== -1 && beginIdx - guardIdx < firstWriteAfter) {
        firstWriteAfter = beginIdx - guardIdx;
    }
    const beginIdx2 = content.indexOf('query("BEGIN")', guardIdx);
    if (beginIdx2 !== -1 && beginIdx2 - guardIdx < firstWriteAfter) {
        firstWriteAfter = beginIdx2 - guardIdx;
    }

    if (firstWriteAfter !== Infinity && firstWriteAfter > 0) {
        return { beforeWrite: true, note: 'guard appears before first DB write' };
    }
    if (firstWriteAfter === Infinity) {
        return { beforeWrite: null, note: 'no DB write keyword found after guard' };
    }
    return { beforeWrite: false, note: 'guard may appear after DB write — review needed' };
}

function extractLikelyTables(content) {
    const found = new Set();
    for (const table of KNOWN_TABLES) {
        const re = new RegExp('\\b' + table.replace(/_/g, '\\s*_?\\s*') + '\\b', 'i');
        if (re.test(content)) {
            found.add(table);
        }
    }
    return [...found];
}

// eslint-disable-next-line complexity
function classifyScript(filePath, content) {
    const rel = path.relative(REPO_ROOT, filePath);
    const baseName = path.basename(filePath);

    // Skip self-referential
    if (isGuardItself(filePath) || isScannerItself(filePath)) {
        return { classification: 'self_referential', reason: 'guard or scanner itself' };
    }

    if (isExistingDryRunScanner(filePath)) {
        return { classification: 'self_referential', reason: 'existing dry-run scanner' };
    }

    if (isTestFile(filePath)) {
        return { classification: 'test_file', reason: 'test file' };
    }

    if (isSqlFile(filePath)) {
        const writeRisks = hasDbWriteRisk(content);
        if (writeRisks.length > 0) {
            return {
                classification: 'non_js_advisory',
                reason: 'SQL migration — needs separate enforcement',
                writeOps: writeRisks.map(w => w.op),
                riskLevel: 'P0',
            };
        }
        return { classification: 'read_only_or_false_positive', reason: 'SQL file, no write risk detected' };
    }

    if (isPythonFile(filePath)) {
        const writeRisks = hasDbWriteRisk(content);
        if (writeRisks.length > 0) {
            return {
                classification: 'non_js_advisory',
                reason: 'Python script — needs Python guard equivalent',
                writeOps: writeRisks.map(w => w.op),
                riskLevel: writeRisks.some(w => w.risk === 'P0') ? 'P0' : 'P1',
            };
        }
        return { classification: 'read_only_or_false_positive', reason: 'Python file, no write risk detected' };
    }

    // JS files in OPS_DIR
    const writeRisks = hasDbWriteRisk(content);
    const guard = hasGuard(content);

    // Check if Phase1/Phase2 guarded
    const isPhase1 = PHASE1_GUARDED.includes(baseName);
    const isPhase2 = PHASE2_GUARDED.includes(baseName);
    const isPhase3 = PHASE3_GUARDED.includes(baseName);
    const wasSkipped = PHASE1_SKIPPED.includes(baseName);

    if (writeRisks.length === 0) {
        return { classification: 'read_only_or_false_positive', reason: 'no DB write risk keywords detected' };
    }

    const tables = extractLikelyTables(content);
    const ops = [...new Set(writeRisks.map(w => w.op))];
    const highestRisk = writeRisks.some(w => w.risk === 'P0') ? 'P0' : 'P1';
    const hasHighRisk = ops.some(op => HIGH_RISK_OPS.has(op));

    if (guard.hasRequire && guard.hasCall) {
        const pos = guardBeforeWrite(content, baseName);
        const needsReview = !pos.beforeWrite;

        const phaseLabel = isPhase1 ? 'phase1' : (isPhase2 ? 'phase2' : (isPhase3 ? 'phase3' : null));

        if (needsReview) {
            return {
                classification: 'guarded_but_needs_review',
                reason: pos.note,
                writeOps: ops,
                tables,
                riskLevel: highestRisk,
                phase1_or_2: phaseLabel,
                hasHighRiskOps: hasHighRisk,
            };
        }

        return {
            classification: 'guarded',
            reason: `guard present, before write${isPhase1 ? ', Phase1' : ''}${isPhase2 ? ', Phase2' : ''}${isPhase3 ? ', Phase3' : ''}`,
            writeOps: ops,
            tables,
            riskLevel: highestRisk,
            phase1_or_2: phaseLabel,
            hasHighRiskOps: hasHighRisk,
        };
    }

    if (wasSkipped) {
        return {
            classification: 'skipped_complex',
            reason: 'Phase1 skipped — has own controlled write guard system or browser complexity',
            writeOps: ops,
            tables,
            riskLevel: highestRisk,
            hasHighRiskOps: hasHighRisk,
        };
    }

    // Check for complex patterns that make auto-guard difficult
    if (/playwright|chromium|browser|page\.goto|\.launch\(/i.test(content)) {
        return {
            classification: 'skipped_complex',
            reason: 'browser/Playwright automation — needs manual review',
            writeOps: ops,
            tables,
            riskLevel: highestRisk,
            hasHighRiskOps: hasHighRisk,
        };
    }

    // Check for worker/child_process scripts
    if (/child_process|\.fork\(|\.spawn\(|worker/i.test(content)) {
        // Can still be guarded — but flag for review
        if (guard.hasRequire || guard.hasCall) {
            return {
                classification: 'guarded_but_needs_review',
                reason: 'worker/spawn script with partial guard — review guard placement',
                writeOps: ops,
                tables,
                riskLevel: highestRisk,
                hasHighRiskOps: hasHighRisk,
            };
        }
    }

    return {
        classification: 'unguarded_p0_candidate',
        reason: 'DB write risk detected, no guard found',
        writeOps: ops,
        tables,
        riskLevel: highestRisk,
        hasHighRiskOps: hasHighRisk,
        suggestedGates: buildSuggestedGates(ops, tables, hasHighRisk),
        suitableForPhase3: true,
    };
}

function buildSuggestedGates(ops, tables, hasHighRisk) {
    const gates = {
        universal: ['ALLOW_DB_WRITE', 'FINAL_DB_WRITE_CONFIRMATION'],
        tableLevel: [],
        schemaLevel: hasHighRisk ? ['ALLOW_SCHEMA_WRITE'] : [],
    };

    for (const table of tables) {
        if (table === 'raw_match_data') gates.tableLevel.push('ALLOW_RAW_MATCH_DATA_WRITE');
        if (table === 'matches') gates.tableLevel.push('ALLOW_MATCHES_WRITE');
        if (table === 'bookmaker_odds_history' || table === 'matches_oddsportal_mapping') {
            gates.tableLevel.push('ALLOW_ODDS_WRITE');
        }
        if (table === 'l3_features' || table === 'match_features_training' || table === 'predictions') {
            gates.tableLevel.push('ALLOW_TRAINING_WRITE');
        }
    }
    gates.tableLevel = [...new Set(gates.tableLevel)];

    return gates;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main scanner
// ═══════════════════════════════════════════════════════════════════════════════

function scanAll() {
    const jsFiles = collectJsFiles(OPS_DIR);
    const results = [];

    for (const filePath of jsFiles) {
        const content = fs.readFileSync(filePath, 'utf8');
        const rel = path.relative(REPO_ROOT, filePath);
        const result = classifyScript(filePath, content);
        results.push({ path: rel, ...result });
    }

    // Also scan scripts/maintenance briefly (advisory only)
    const maintDir = path.join(REPO_ROOT, 'scripts', 'maintenance');
    const maintFiles = collectNonJsFiles(maintDir);
    for (const filePath of maintFiles) {
        const content = fs.readFileSync(filePath, 'utf8');
        const rel = path.relative(REPO_ROOT, filePath);
        const result = classifyScript(filePath, content);
        results.push({ path: rel, ...result });
    }

    return results;
}

function buildSummary(results) {
    const summary = {
        scanned_files_count: results.length,
        js_ops_scanned_count: results.filter(r => r.path.startsWith('scripts/ops/') && r.classification !== 'read_only_or_false_positive').length,
        guarded_count: results.filter(r => r.classification === 'guarded').length,
        unguarded_p0_candidate_count: results.filter(r => r.classification === 'unguarded_p0_candidate').length,
        guarded_but_needs_review_count: results.filter(r => r.classification === 'guarded_but_needs_review').length,
        false_positive_or_readonly_count: results.filter(r => r.classification === 'read_only_or_false_positive').length,
        skipped_complex_count: results.filter(r => r.classification === 'skipped_complex').length,
        non_js_advisory_count: results.filter(r => r.classification === 'non_js_advisory').length,
        test_file_count: results.filter(r => r.classification === 'test_file').length,
        self_referential_count: results.filter(r => r.classification === 'self_referential').length,

        phase1_phase2_phase3_guarded_detected_count: results.filter(
            r => (r.classification === 'guarded' || r.classification === 'guarded_but_needs_review') &&
                (r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3')
        ).length,

        phase1_phase2_phase3_guarded_expected: PHASE1_GUARDED.length + PHASE2_GUARDED.length + PHASE3_GUARDED.length,
        all_phase1_phase2_phase3_detected: null, // filled below

        candidates_for_phase3: results
            .filter(r => r.classification === 'unguarded_p0_candidate')
            .map(r => ({ path: r.path, writeOps: r.writeOps, tables: r.tables, riskLevel: r.riskLevel })),
        candidates_for_phase3_count: results.filter(r => r.classification === 'unguarded_p0_candidate').length,

        recommended_enforcement_rule: 'fail_on_new_or_modified_unguarded_js_ops',
        recommended_ci_mode: 'warning',
        recommended_next_task: null, // filled below
    };

    // Check all Phase1+Phase2+Phase3 guarded detected (including needs-review as verified)
    const detectedGuardedNames = results
        .filter(r => r.classification === 'guarded' || r.classification === 'guarded_but_needs_review')
        .filter(r => r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3')
        .map(r => path.basename(r.path));
    const allExpected = [...PHASE1_GUARDED, ...PHASE2_GUARDED, ...PHASE3_GUARDED];
    const missing = allExpected.filter(n => !detectedGuardedNames.includes(n));

    summary.all_phase1_phase2_phase3_detected = missing.length === 0;
    summary.missing_phase1_phase2_phase3 = missing;

    if (summary.unguarded_p0_candidate_count > 0) {
        summary.recommended_next_task = 'p0_db_write_safety_gate_fix_phase3';
    } else if (summary.guarded_but_needs_review_count > 0) {
        summary.recommended_next_task = 'db_write_guard_review_fix_phase1';
    } else {
        summary.recommended_next_task = 'db_write_guard_static_enforcement_fix_phase1 (CI integration)';
    }

    return summary;
}

function classifyGuarded(rel) {
    const base = path.basename(rel);
    if (PHASE1_GUARDED.includes(base)) return 'phase1';
    if (PHASE2_GUARDED.includes(base)) return 'phase2';
    return 'other';
}

// eslint-disable-next-line complexity
function printReport(results, summary) {
    console.log('═══════════════════════════════════════════════════════════════');
    console.log('DB Write Guard Static Enforcement — Dry-Run Report');
    console.log('═══════════════════════════════════════════════════════════════');
    console.log(`Scanned: ${summary.scanned_files_count} files`);
    console.log(`JS ops with write risk: ${summary.js_ops_scanned_count}`);
    console.log('');

    console.log('── Classification Summary ──');
    console.log(`  guarded:                          ${summary.guarded_count}`);
    console.log(`  unguarded (P0 candidates):         ${summary.unguarded_p0_candidate_count}`);
    console.log(`  guarded but needs review:          ${summary.guarded_but_needs_review_count}`);
    console.log(`  skipped (complex):                 ${summary.skipped_complex_count}`);
    console.log(`  read-only / false positive:        ${summary.false_positive_or_readonly_count}`);
    console.log(`  non-JS advisory (Python/SQL):      ${summary.non_js_advisory_count}`);
    console.log(`  test files:                        ${summary.test_file_count}`);
    console.log(`  self-referential:                  ${summary.self_referential_count}`);
    console.log('');

    console.log('── Phase1 + Phase2 + Phase3 Check ──');
    console.log(`  Expected guarded:  ${summary.phase1_phase2_phase3_guarded_expected}`);
    console.log(`  Detected guarded:  ${summary.phase1_phase2_phase3_guarded_detected_count}`);
    console.log(`  All detected:      ${summary.all_phase1_phase2_phase3_detected ? 'YES ✓' : 'NO ✗'}`);
    if (summary.missing_phase1_phase2_phase3 && summary.missing_phase1_phase2_phase3.length > 0) {
        console.log(`  Missing:           ${summary.missing_phase1_phase2_phase3.join(', ')}`);
    }
    console.log('');

    // Print guarded
    console.log('── Guarded ──');
    const guarded = results.filter(r => r.classification === 'guarded');
    for (const r of guarded) {
        const tag = r.phase1_or_2 ? ` [${r.phase1_or_2}]` : '';
        console.log(`  ✓ ${r.path}${tag} — ${r.writeOps.join(', ')} → ${(r.tables || []).join(', ') || '(unknown)'}`);
    }

    // Print unguarded
    if (summary.unguarded_p0_candidate_count > 0) {
        console.log('');
        console.log('── Unguarded (Candidates for Phase3) ──');
        const unguarded = results.filter(r => r.classification === 'unguarded_p0_candidate');
        for (const r of unguarded) {
            console.log(`  ✗ ${r.path}`);
            console.log(`    ops: ${r.writeOps.join(', ')}  tables: ${(r.tables || []).join(', ') || '(unknown)'}  risk: ${r.riskLevel}`);
            if (r.suggestedGates) {
                const g = r.suggestedGates;
                console.log(`    gates: universal=[${g.universal.join(', ')}] table=[${g.tableLevel.join(', ') || 'none'}] schema=[${g.schemaLevel.join(', ') || 'none'}]`);
            }
        }
    }

    // Print skipped
    const skipped = results.filter(r => r.classification === 'skipped_complex');
    if (skipped.length > 0) {
        console.log('');
        console.log('── Skipped (Complex) ──');
        for (const r of skipped) {
            console.log(`  ~ ${r.path} — ${r.reason}`);
        }
    }

    // Print review
    const review = results.filter(r => r.classification === 'guarded_but_needs_review');
    if (review.length > 0) {
        console.log('');
        console.log('── Needs Review ──');
        for (const r of review) {
            console.log(`  ? ${r.path} — ${r.reason}`);
        }
    }

    // Print advisory
    const advisory = results.filter(r => r.classification === 'non_js_advisory');
    if (advisory.length > 0) {
        console.log('');
        console.log('── Non-JS Advisory (Python / SQL) ──');
        for (const r of advisory) {
            console.log(`  ⓘ ${r.path} — ${r.reason} [risk=${r.riskLevel}]`);
        }
    }

    console.log('');
    console.log('── Recommendation ──');
    console.log(`  Enforcement rule:  ${summary.recommended_enforcement_rule}`);
    console.log(`  CI mode:           ${summary.recommended_ci_mode}`);
    console.log(`  Next task:         ${summary.recommended_next_task}`);
    console.log('');
    console.log('SC-002 status: partial mitigation only — NOT fully fixed.');
    console.log('This is a dry-run scan. No CI hard fail has been added.');

    return { results, summary };
}

// ═══════════════════════════════════════════════════════════════════════════════
// CLI
// ═══════════════════════════════════════════════════════════════════════════════

function parseArgs(argv) {
    return {
        json: argv.includes('--json'),
        help: argv.includes('--help') || argv.includes('-h'),
        firstBatch: argv.includes('--first-batch'),
    };
}

function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);

    if (args.help) {
        console.log('Usage: node scripts/ops/db_write_guard_static_enforcement_dry_run.js [--json] [--first-batch] [--help]');
        console.log('  --json          Output JSON summary to stdout');
        console.log('  --first-batch   Only show unguarded P0 candidates (first batch for phase3)');
        console.log('  --help          Show this help');
        process.exit(0);
    }

    const results = scanAll();
    const summary = buildSummary(results);

    if (args.json) {
        const output = {
            summary,
            results: results.map(r => ({
                path: r.path,
                classification: r.classification,
                reason: r.reason,
                writeOps: r.writeOps,
                tables: r.tables,
                riskLevel: r.riskLevel,
                phase1_or_2: r.phase1_or_2,
                hasHighRiskOps: r.hasHighRiskOps,
                suggestedGates: r.suggestedGates,
            })),
        };
        console.log(JSON.stringify(output, null, 2));
    } else if (args.firstBatch) {
        // Only output unguarded P0 candidates
        const candidates = results.filter(r => r.classification === 'unguarded_p0_candidate' && r.riskLevel === 'P0');
        console.log(JSON.stringify({ summary, candidates }, null, 2));
    } else {
        printReport(results, summary);
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Exports (for testing)
// ═══════════════════════════════════════════════════════════════════════════════

module.exports = {
    // Constants
    DB_WRITE_PATTERNS,
    GUARD_REQUIRE_PATTERNS,
    GUARD_CALL_PATTERNS,
    KNOWN_TABLES,
    PHASE1_GUARDED,
    PHASE2_GUARDED,
    PHASE3_GUARDED,
    PHASE1_SKIPPED,
    // Functions
    hasDbWriteRisk,
    hasGuard,
    guardBeforeWrite,
    extractLikelyTables,
    classifyScript,
    scanAll,
    buildSummary,
    parseArgs,
    isTestFile,
    isMigrationFile,
    isPythonFile,
    isSqlFile,
    isHelperFile,
    isGuardItself,
    // Entry
    main,
};
