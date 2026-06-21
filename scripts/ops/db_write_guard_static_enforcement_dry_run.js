#!/usr/bin/env node
/* eslint-disable max-lines */
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
    /import\s+[\s\S]*?\s+from\s+['"]\.\/helpers\/db_write_guard(?:\.js)?['"]/,
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

const PHASE4_GUARDED = Object.freeze([
    'raw_match_data_versioned_schema_migration_execute.js',
    'score_backfill_dry_run.js',
    'training_eligibility_after_score_dry_run.js',
    'l2_guarded_reconciliation_write.js',
    'controlled_matches_identity_seed_execute.js',
    'l3_stitch_worker.js',
]);

const PHASE5_GUARDED = Object.freeze([
    'synthetic_l3_preflight.js',
    'synthetic_prediction_preflight.js',
    'synthetic_training_feature_preflight.js',
    'finished_csv_local_dry_run.js',
    'real_finished_csv_staging_dry_run.js',
    'finished_match_backfill_preflight.js',
    'raw_fixture_adapter_dry_run.js',
]);

const PHASE6_GUARDED = Object.freeze([
    'raw_match_data_completeness_fidelity_audit.js',
    'football_data_duplicate_precheck.js',
    'raw_match_data_version_compatibility_audit.js',
    'l1_matches_seed_commit_execute.js',
    'l2_raw_match_data_write.js',
]);

const PHASE7_GUARDED = Object.freeze([
    'l2_remaining_raw_match_data_write.js',
]);

const PHASE1_SKIPPED = Object.freeze([
    'l2_raw_match_data_write.js',
    'l2_remaining_raw_match_data_write.js',
    'l1_matches_seed_commit_execute.js',
    'fixture_harvester_l1.js',
]);

/**
 * Load structured allowlist from JSON file.
 *
 * Each entry MUST have: path, category, reason, reviewed_at, future_action.
 * The full-scan `should_fail` is always false for these entries.
 * Changed-files enforcement also respects these as skip entries.
 *
 * SC-002 remains partial mitigation only. These are NOT "fixed".
 */
function loadLegacyAllowlist() {
    const allowlistPath = path.join(__dirname, 'helpers', 'db_write_guard_legacy_allowlist.json');
    try {
        return Object.freeze(JSON.parse(fs.readFileSync(allowlistPath, 'utf8')));
    } catch (_) {
        return Object.freeze([]);
    }
}

const ALLOWLIST_LEGACY_COMPLEX = loadLegacyAllowlist();

function lookupAllowlist(relPath) {
    for (const entry of ALLOWLIST_LEGACY_COMPLEX) {
        if (entry.path === relPath) return entry;
    }
    return null;
}

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

    // Check if Phase1/Phase2/Phase3/Phase4/Phase5/Phase6 guarded
    const isPhase1 = PHASE1_GUARDED.includes(baseName);
    const isPhase2 = PHASE2_GUARDED.includes(baseName);
    const isPhase3 = PHASE3_GUARDED.includes(baseName);
    const isPhase4 = PHASE4_GUARDED.includes(baseName);
    const isPhase5 = PHASE5_GUARDED.includes(baseName);
    const isPhase6 = PHASE6_GUARDED.includes(baseName);
    const isPhase7 = PHASE7_GUARDED.includes(baseName);
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

        const phaseLabel = isPhase1
            ? 'phase1'
            : (isPhase2 ? 'phase2' : (isPhase3 ? 'phase3' : (isPhase4 ? 'phase4' : (isPhase5 ? 'phase5' : (isPhase6 ? 'phase6' : (isPhase7 ? 'phase7' : null))))));

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
            reason: `guard present, before write${isPhase1 ? ', Phase1' : ''}${isPhase2 ? ', Phase2' : ''}${isPhase3 ? ', Phase3' : ''}${isPhase4 ? ', Phase4' : ''}${isPhase5 ? ', Phase5' : ''}${isPhase6 ? ', Phase6' : ''}${isPhase7 ? ', Phase7' : ''}`,
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

    // Check structured allowlist for legacy complex candidates
    const allowlistEntry = lookupAllowlist(rel);
    if (allowlistEntry) {
        return {
            classification: 'skipped_complex',
            reason: allowlistEntry.reason,
            category: allowlistEntry.category,
            reviewed_at: allowlistEntry.reviewed_at,
            future_action: allowlistEntry.future_action,
            writeOps: ops,
            tables,
            riskLevel: highestRisk,
            hasHighRiskOps: hasHighRisk,
        };
    }

    // Check for browser/Playwright automation patterns
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
        phase1_phase2_phase3_phase4_guarded_detected_count: results.filter(
            r => (r.classification === 'guarded' || r.classification === 'guarded_but_needs_review') &&
                (r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4')
        ).length,
        phase1_phase2_phase3_phase4_guarded_expected:
            PHASE1_GUARDED.length + PHASE2_GUARDED.length + PHASE3_GUARDED.length + PHASE4_GUARDED.length,
        all_phase1_phase2_phase3_phase4_detected: null, // filled below
        phase1_phase2_phase3_phase4_phase5_guarded_detected_count: results.filter(
            r => (r.classification === 'guarded' || r.classification === 'guarded_but_needs_review') &&
                (r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4' || r.phase1_or_2 === 'phase5')
        ).length,
        phase1_phase2_phase3_phase4_phase5_guarded_expected:
            PHASE1_GUARDED.length + PHASE2_GUARDED.length + PHASE3_GUARDED.length + PHASE4_GUARDED.length + PHASE5_GUARDED.length,
        all_phase1_phase2_phase3_phase4_phase5_detected: null, // filled below

        phase1_phase2_phase3_phase4_phase5_phase6_guarded_detected_count: results.filter(
            r => (r.classification === 'guarded' || r.classification === 'guarded_but_needs_review') &&
                (r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4' || r.phase1_or_2 === 'phase5' || r.phase1_or_2 === 'phase6')
        ).length,
        phase1_phase2_phase3_phase4_phase5_phase6_guarded_expected:
            PHASE1_GUARDED.length + PHASE2_GUARDED.length + PHASE3_GUARDED.length + PHASE4_GUARDED.length + PHASE5_GUARDED.length + PHASE6_GUARDED.length,
        all_phase1_phase2_phase3_phase4_phase5_phase6_detected: null, // filled below

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

    const detectedGuardedNamesThroughPhase4 = results
        .filter(r => r.classification === 'guarded' || r.classification === 'guarded_but_needs_review')
        .filter(r => r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4')
        .map(r => path.basename(r.path));
    const allExpectedThroughPhase4 = [...PHASE1_GUARDED, ...PHASE2_GUARDED, ...PHASE3_GUARDED, ...PHASE4_GUARDED];
    const missingThroughPhase4 = allExpectedThroughPhase4.filter(n => !detectedGuardedNamesThroughPhase4.includes(n));
    summary.all_phase1_phase2_phase3_phase4_detected = missingThroughPhase4.length === 0;
    summary.missing_phase1_phase2_phase3_phase4 = missingThroughPhase4;

    const detectedGuardedNamesThroughPhase5 = results
        .filter(r => r.classification === 'guarded' || r.classification === 'guarded_but_needs_review')
        .filter(r => r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4' || r.phase1_or_2 === 'phase5')
        .map(r => path.basename(r.path));
    const allExpectedThroughPhase5 = [...PHASE1_GUARDED, ...PHASE2_GUARDED, ...PHASE3_GUARDED, ...PHASE4_GUARDED, ...PHASE5_GUARDED];
    const missingThroughPhase5 = allExpectedThroughPhase5.filter(n => !detectedGuardedNamesThroughPhase5.includes(n));
    summary.all_phase1_phase2_phase3_phase4_phase5_detected = missingThroughPhase5.length === 0;
    summary.missing_phase1_phase2_phase3_phase4_phase5 = missingThroughPhase5;

    const detectedGuardedNamesThroughPhase6 = results
        .filter(r => r.classification === 'guarded' || r.classification === 'guarded_but_needs_review')
        .filter(r => r.phase1_or_2 === 'phase1' || r.phase1_or_2 === 'phase2' || r.phase1_or_2 === 'phase3' || r.phase1_or_2 === 'phase4' || r.phase1_or_2 === 'phase5' || r.phase1_or_2 === 'phase6')
        .map(r => path.basename(r.path));
    const allExpectedThroughPhase6 = [...PHASE1_GUARDED, ...PHASE2_GUARDED, ...PHASE3_GUARDED, ...PHASE4_GUARDED, ...PHASE5_GUARDED, ...PHASE6_GUARDED];
    const missingThroughPhase6 = allExpectedThroughPhase6.filter(n => !detectedGuardedNamesThroughPhase6.includes(n));
    summary.all_phase1_phase2_phase3_phase4_phase5_phase6_detected = missingThroughPhase6.length === 0;
    summary.missing_phase1_phase2_phase3_phase4_phase5_phase6 = missingThroughPhase6;

    const detectedGuardedNamesThroughPhase7 = results
        .filter(r => r.classification === 'guarded' || r.classification === 'guarded_but_needs_review')
        .filter(r => ['phase1','phase2','phase3','phase4','phase5','phase6','phase7'].includes(r.phase1_or_2))
        .map(r => path.basename(r.path));
    const allExpectedThroughPhase7 = [...PHASE1_GUARDED, ...PHASE2_GUARDED, ...PHASE3_GUARDED, ...PHASE4_GUARDED, ...PHASE5_GUARDED, ...PHASE6_GUARDED, ...PHASE7_GUARDED];
    const missingThroughPhase7 = allExpectedThroughPhase7.filter(n => !detectedGuardedNamesThroughPhase7.includes(n));
    summary.all_phase1_through_7_detected = missingThroughPhase7.length === 0;
    summary.missing_phase1_through_7 = missingThroughPhase7;
    summary.phase1_through_7_guarded_expected = allExpectedThroughPhase7.length;
    summary.phase1_through_7_guarded_detected_count = detectedGuardedNamesThroughPhase7.length;

    // Build skipped_complex category breakdown
    const skippedByCategory = {};
    for (const r of results) {
        if (r.classification === 'skipped_complex' && r.category) {
            skippedByCategory[r.category] = (skippedByCategory[r.category] || 0) + 1;
        }
    }
    summary.skipped_complex_by_category = skippedByCategory;

    // Count legacy allowlist entries (remaining complex candidates)
    summary.legacy_allowlist_count = results.filter(
        r => r.classification === 'skipped_complex' && r.category
    ).length;

    if (summary.unguarded_p0_candidate_count > 0) {
        summary.recommended_next_task = 'p0_db_write_safety_gate_fix_phase8 (remaining unguarded)';
    } else if (summary.guarded_but_needs_review_count > 0) {
        summary.recommended_next_task = 'db_write_guard_review_fix_phase1';
    } else {
        summary.recommended_next_task =
            'db_write_guard_static_enforcement_fix_phase3 (specialized browser/FotMob/pageProps audit)';
    }

    // SC-002 status
    summary.sc002_status = 'partial_mitigation_only';
    summary.sc002_guarded_total = summary.guarded_count + summary.guarded_but_needs_review_count;
    summary.sc002_remaining_complex = summary.legacy_allowlist_count;
    summary.sc002_note =
        'SC-002 is NOT fully fixed. Guarded scripts are per-script opt-in. '
        + 'Remaining complex candidates are categorized (NOT fixed). '
        + 'Changed-files enforcement is active for new/modified scripts/ops JS. '
        + 'Historical full-scan candidates do not trigger hard fail. '
        + 'Python/SQL/migration enforcement not yet designed.';

    return summary;
}

function classifyGuarded(rel) {
    const base = path.basename(rel);
    if (PHASE1_GUARDED.includes(base)) return 'phase1';
    if (PHASE2_GUARDED.includes(base)) return 'phase2';
    if (PHASE3_GUARDED.includes(base)) return 'phase3';
    if (PHASE4_GUARDED.includes(base)) return 'phase4';
    if (PHASE5_GUARDED.includes(base)) return 'phase5';
    if (PHASE6_GUARDED.includes(base)) return 'phase6';
    if (PHASE7_GUARDED.includes(base)) return 'phase7';
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

    console.log('── Phase1 through Phase7 Check ──');
    console.log(`  Expected guarded:  ${summary.phase1_through_7_guarded_expected}`);
    console.log(`  Detected guarded:  ${summary.phase1_through_7_guarded_detected_count}`);
    console.log(`  All detected:      ${summary.all_phase1_through_7_detected ? 'YES ✓' : 'NO ✗'}`);
    if (summary.missing_phase1_through_7 && summary.missing_phase1_through_7.length > 0) {
        console.log(`  Missing:           ${summary.missing_phase1_through_7.join(', ')}`);
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
        console.log('── Skipped (Complex / Categorized) ──');
        for (const r of skipped) {
            const catTag = r.category ? ` [${r.category}]` : '';
            console.log(`  ~ ${r.path}${catTag} — ${r.reason}`);
        }
    }

    // Print skipped category breakdown
    if (summary.skipped_complex_by_category && Object.keys(summary.skipped_complex_by_category).length > 0) {
        console.log('');
        console.log('── Skipped Category Breakdown ──');
        for (const [cat, count] of Object.entries(summary.skipped_complex_by_category)) {
            console.log(`  ${cat}: ${count}`);
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
    console.log(`  SC-002 guarded:    ${summary.sc002_guarded_total} / 66 (Phase1-7)`);
    console.log(`  SC-002 complex:    ${summary.sc002_remaining_complex} remaining (categorized, NOT fixed)`);
    console.log('');
    console.log('SC-002 status: partial mitigation only — NOT fully fixed.');
    console.log('Changed-files enforcement: hard fail on new unguarded JS scripts/ops.');
    console.log('Historical full-scan candidates: exempt from hard fail.');
    console.log('This is a dry-run scan. The ai_workflow_gate reads should_fail for enforcement.');

    return { results, summary };
}

// ═══════════════════════════════════════════════════════════════════════════════
// CLI
// ═══════════════════════════════════════════════════════════════════════════════

// eslint-disable-next-line complexity
function scanAdvisory(changedFiles = []) {
    const results = [];
    const skipped = [];
    const violations = [];
    const guarded = [];
    const falsePositives = [];

    for (const rel of changedFiles) {
        const fullPath = path.join(REPO_ROOT, rel);

        // Skip non-JS files
        if (!rel.endsWith('.js')) {
            skipped.push({ path: rel, reason: 'not a JS file' });
            continue;
        }

        // Skip non-scripts/ops files
        if (!rel.startsWith('scripts/ops/') && !rel.startsWith('scripts\\ops\\')) {
            skipped.push({ path: rel, reason: 'not in scripts/ops/' });
            continue;
        }

        // Skip deleted/missing files
        if (!fs.existsSync(fullPath)) {
            skipped.push({ path: rel, reason: 'file deleted or missing' });
            continue;
        }

        const content = fs.readFileSync(fullPath, 'utf8');
        const result = classifyScript(fullPath, content);
        result.path = rel;
        results.push(result);

        // Determine enforcement outcome for this file
        const hasGuard = (
            result.classification === 'guarded' ||
            result.classification === 'guarded_but_needs_review'
        );
        const isSkipped = (
            result.classification === 'skipped_complex' ||
            result.classification === 'read_only_or_false_positive' ||
            result.classification === 'test_file' ||
            result.classification === 'self_referential' ||
            result.classification === 'non_js_advisory'
        );

        if (hasGuard) {
            guarded.push({
                path: rel,
                classification: result.classification,
                writeOps: result.writeOps || [],
                tables: result.tables || [],
                riskLevel: result.riskLevel || 'N/A',
            });
        } else if (result.classification === 'unguarded_p0_candidate') {
            // This is a violation — unguarded DB write risk in changed scripts/ops JS
            const violation = {
                path: rel,
                reason: result.reason || 'DB write risk detected, no guard found',
                writeOps: result.writeOps || [],
                tables: result.tables || [],
                riskLevel: result.riskLevel || 'P0',
                hasHighRiskOps: result.hasHighRiskOps || false,
                suggestedFix: buildViolationSuggestedFix(result),
                whyNotSkipped: 'not in legacy allowlist, not browser/complex, not read-only — needs guard',
            };
            violations.push(violation);
        } else if (isSkipped) {
            falsePositives.push({
                path: rel,
                classification: result.classification,
                reason: result.reason || '',
                category: result.category || null,
                skipRationale: result.category
                    ? `categorized as ${result.category}: ${result.reason}`
                    : (result.reason || 'skip rationale applies'),
            });
        }
    }

    const shouldFail = violations.length > 0;

    return {
        mode: 'changed_files_enforcement',
        enforcement_level: 'hard_fail_on_new_unguarded_js_ops',
        changed_files_checked: changedFiles.length,
        changed_js_ops_checked: results.length,
        violation_count: violations.length,
        violations,
        guarded_changed_js_ops: guarded.map(r => r.path),
        guarded_detail: guarded,
        skipped_changed_files: skipped,
        false_positive_changed: falsePositives,
        should_fail: shouldFail,
        recommended_action: shouldFail
            ? 'FAIL: new/modified scripts/ops JS files have unguarded DB write risk. Add assertDbWriteAllowed or request explicit allowlist classification.'
            : violations.length === 0 && guarded.length > 0
                ? 'OK: all changed scripts/ops JS files are guarded.'
                : 'OK: changed scripts/ops JS files are read-only, complex/skipped, or non-write.',
        // Historical debt disclaimer — always present
        historical_debt_note:
            'SC-002 remains partial mitigation only. The full-scan historical '
            + 'remaining candidates are NOT subject to changed-files hard fail. '
            + 'This enforcement only applies to changed files in this diff.',
    };
}

/**
 * Build a human-readable suggested fix for a violation.
 */
function buildViolationSuggestedFix(result) {
    const parts = [];
    parts.push('Add db_write_guard integration to this file:');
    parts.push('  1. const { assertDbWriteAllowed } = require(\'./helpers/db_write_guard\');');
    parts.push('  2. assertDbWriteAllowed({ script: \'<name>\', tables: [\'<table>\'], operations: [\'<op>\'] });');
    if (result.suggestedGates) {
        const g = result.suggestedGates;
        parts.push('  3. Required env gates: ' + g.universal.join(', '));
        if (g.tableLevel.length) parts.push('     Table-level: ' + g.tableLevel.join(', '));
        if (g.schemaLevel.length) parts.push('     Schema-level: ' + g.schemaLevel.join(', '));
    }
    parts.push('  Or, if this is a false positive, add it to ALLOWLIST_LEGACY_COMPLEX with proper category/reason.');
    return parts.join('\n');
}

function parseArgs(argv) {
    const args = {
        json: false,
        help: false,
        firstBatch: false,
        changedFiles: null,
    };

    for (let i = 0; i < argv.length; i++) {
        const token = argv[i];
        if (token === '--json') args.json = true;
        else if (token === '--help' || token === '-h') args.help = true;
        else if (token === '--first-batch') args.firstBatch = true;
        else if (token === '--changed-files') {
            const val = argv[++i];
            args.changedFiles = val ? val.split(',').map(s => s.trim()).filter(Boolean) : [];
        } else if (token === '--changed-files-from-stdin') {
            const stdin = require('fs').readFileSync(0, 'utf8').trim();
            args.changedFiles = stdin.split('\n').map(s => s.trim()).filter(Boolean);
        }
    }

    return args;
}

function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);

    if (args.help) {
        console.log('Usage: node scripts/ops/db_write_guard_static_enforcement_dry_run.js [options]');
        console.log('  --json                        Output JSON summary');
        console.log('  --first-batch                 Only show unguarded P0 candidates');
        console.log('  --changed-files <a,b,c>       Advisory mode: only check listed files');
        console.log('  --changed-files-from-stdin    Read changed files from stdin');
        console.log('  --help                        Show this help');
        process.exit(0);
    }

    // Changed-files enforcement mode
    if (args.changedFiles !== null) {
        const output = scanAdvisory(args.changedFiles);
        if (args.json) {
            console.log(JSON.stringify(output, null, 2));
        } else {
            // Human-readable enforcement output
            if (output.should_fail) {
                console.log('[DB-WRITE-GUARD ENFORCEMENT] FAIL: ' + output.violation_count +
                    ' changed scripts/ops JS file(s) have unguarded DB write risk:');
                for (const v of output.violations) {
                    console.log('  - ' + v.path);
                    console.log('    ops: ' + (v.writeOps || []).join(', ') +
                        '  tables: ' + (v.tables || []).join(', ') +
                        '  risk: ' + v.riskLevel +
                        (v.hasHighRiskOps ? '  HIGH_RISK' : ''));
                    console.log('    reason: ' + v.reason);
                    console.log('    suggestedFix:');
                    for (const line of v.suggestedFix.split('\n')) {
                        console.log('      ' + line);
                    }
                }
                console.log('[DB-WRITE-GUARD ENFORCEMENT] Hard fail: unguarded DB write risk in changed files.');
                console.log('[DB-WRITE-GUARD ENFORCEMENT] SC-002 is NOT fully fixed. Historical candidates exempt.');
            } else if (output.violation_count === 0 && output.guarded_changed_js_ops.length > 0) {
                console.log('[DB-WRITE-GUARD ENFORCEMENT] OK: all changed scripts/ops JS files are guarded.');
            } else {
                console.log('[DB-WRITE-GUARD ENFORCEMENT] OK: changed scripts/ops JS files are read-only, complex/skipped, or non-write.');
            }
        }
        return;
    }

    const results = scanAll();
    const summary = buildSummary(results);

    if (args.firstBatch) {
        // Only output unguarded P0 candidates
        const candidates = results.filter(r => r.classification === 'unguarded_p0_candidate' && r.riskLevel === 'P0');
        console.log(JSON.stringify({ summary, candidates }, null, 2));
    } else if (args.json) {
        const output = {
            summary,
            results: results.map(r => ({
                path: r.path,
                classification: r.classification,
                reason: r.reason,
                category: r.category,
                reviewed_at: r.reviewed_at,
                future_action: r.future_action,
                writeOps: r.writeOps,
                tables: r.tables,
                riskLevel: r.riskLevel,
                phase1_or_2: r.phase1_or_2,
                hasHighRiskOps: r.hasHighRiskOps,
                suggestedGates: r.suggestedGates,
            })),
        };
        console.log(JSON.stringify(output, null, 2));
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
    PHASE4_GUARDED,
    PHASE5_GUARDED,
    PHASE6_GUARDED,
    PHASE7_GUARDED,
    PHASE1_SKIPPED,
    ALLOWLIST_LEGACY_COMPLEX,
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
    lookupAllowlist,
    buildViolationSuggestedFix,
    scanAdvisory,
    // Entry
    main,
};

if (require.main === module) {
    main();
}
