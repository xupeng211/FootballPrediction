#!/usr/bin/env node
/**
 * DB Write Safety Gate — unified guard helper.
 *
 * lifecycle: permanent
 * owner: DB write safety / ops governance
 *
 * Purpose: provide a single, minimal blocking guard that ops scripts call before
 * executing INSERT / UPDATE / DELETE / TRUNCATE / DROP.  It does NOT rewrite
 * business logic, introduce a unified writer layer, or replace existing
 * script-specific safety checks.
 *
 * ## Required env vars (all must be "yes" for a write-run)
 *
 * ### Universal gates (both required)
 *   ALLOW_DB_WRITE=yes
 *   FINAL_DB_WRITE_CONFIRMATION=yes
 *
 * ### Table-level gates (required based on operation)
 *   ALLOW_RAW_MATCH_DATA_WRITE=yes   — writes to raw_match_data
 *   ALLOW_MATCHES_WRITE=yes          — writes to matches
 *   ALLOW_SCHEMA_WRITE=yes           — DELETE / TRUNCATE / DROP / ALTER
 *   ALLOW_ODDS_WRITE=yes             — writes to bookmaker_odds_history
 *   ALLOW_TRAINING_WRITE=yes         — writes to training / predictions tables
 *
 * ### Dry-run
 *   DRY_RUN defaults to true.  A write-run requires DRY_RUN=false.
 *
 * ### Production protection
 *   NODE_ENV=production or APP_ENV=production blocks write by default.
 *   DB hosts matching known production patterns print high-risk warnings.
 *
 * ## Usage
 *
 *   const {
 *     requireDbWriteGuards,
 *     assertDbWriteAllowed,
 *     isDryRun,
 *     describeRequiredGates
 *   } = require('./helpers/db_write_guard');
 *
 *   // Option A: inspect result yourself
 *   const result = requireDbWriteGuards({
 *     script: 'my_script.js',
 *     tables: ['raw_match_data'],
 *     operations: ['INSERT']
 *   });
 *   if (!result.allowed) {
 *     console.error(result.error);
 *     process.exit(1);
 *   }
 *
 *   // Option B: throws on block (preferred for most scripts)
 *   assertDbWriteAllowed({
 *     script: 'my_script.js',
 *     tables: ['raw_match_data'],
 *     operations: ['INSERT']
 *   });
 *
 *   // Option C: guard dry-run mode
 *   if (isDryRun()) {
 *     console.log('[DRY-RUN] Would write … rows to raw_match_data');
 *     process.exit(0);
 *   }
 *
 * @module db_write_guard
 */

'use strict';

// ═══════════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════════

const REQUIRED_UNIVERSAL_GATES = Object.freeze([
    'ALLOW_DB_WRITE',
    'FINAL_DB_WRITE_CONFIRMATION',
]);

/**
 * Map table name (or prefix) to the env-var gate that must be 'yes'.
 * Order matters: first match wins.
 */
const TABLE_GATE_MAP = Object.freeze([
    { pattern: /^raw_match_data$/i, gate: 'ALLOW_RAW_MATCH_DATA_WRITE', label: 'raw_match_data' },
    { pattern: /^matches$/i, gate: 'ALLOW_MATCHES_WRITE', label: 'matches' },
    { pattern: /^bookmaker_odds_history$/i, gate: 'ALLOW_ODDS_WRITE', label: 'bookmaker_odds_history (odds)' },
    { pattern: /^l3_features$/i, gate: 'ALLOW_TRAINING_WRITE', label: 'l3_features (training)' },
    {
        pattern: /^match_features_training$/i,
        gate: 'ALLOW_TRAINING_WRITE',
        label: 'match_features_training (training)',
    },
    { pattern: /^predictions$/i, gate: 'ALLOW_TRAINING_WRITE', label: 'predictions (training)' },
    { pattern: /^training_/i, gate: 'ALLOW_TRAINING_WRITE', label: 'training_* (training)' },
    { pattern: /^odds_/i, gate: 'ALLOW_ODDS_WRITE', label: 'odds_* (odds)' },
]);

const HIGH_RISK_OPERATIONS = new Set([
    'DELETE',
    'TRUNCATE',
    'DROP',
    'ALTER',
    'CREATE',
    'GRANT',
    'REVOKE',
]);

const PRODUCTION_DB_HOST_PATTERNS = Object.freeze([
    /rds\.amazonaws\.com/i,
    /\.rds\.amazonaws/i,
    /cloudsql\.google/i,
    /\.supabase\./i,
    /\.supabase\.co/i,
    /\.vercel/i,
    /\.fly\.dev/i,
    /\.railway\.app/i,
    /\.render\.com/i,
    /\.heroku/i,
    /prod(?:uction)?-db/i,
    /db\.(?:prod|production)/i,
]);

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════════════

function normalizeBooleanEnv(value) {
    if (value === undefined || value === null || value === '') {
        return null;
    }
    const s = String(value).trim();
    if (['1', 'true', 'yes', 'y', 'on'].includes(s.toLowerCase())) {
        return true;
    }
    if (['0', 'false', 'no', 'n', 'off'].includes(s.toLowerCase())) {
        return false;
    }
    return null;
}

function env(name) {
    return process.env[name];
}

function isTruthy(name) {
    return normalizeBooleanEnv(env(name)) === true;
}

/**
 * Check whether the DB host looks like a production instance.
 * Returns { suspicious: boolean, warnings: string[] }.
 */
function checkProductionDbHost() {
    const host = (env('DB_HOST') || env('DATABASE_URL') || '').trim();
    const warnings = [];

    if (!host) {
        return { suspicious: false, warnings };
    }

    for (const pattern of PRODUCTION_DB_HOST_PATTERNS) {
        if (pattern.test(host)) {
            warnings.push(
                `HIGH-RISK: DB_HOST/DATABASE_URL (${host}) matches production pattern: ${pattern}`
            );
        }
    }

    return { suspicious: warnings.length > 0, warnings };
}

/**
 * Check whether the runtime environment looks like production.
 */
function checkProductionEnv() {
    const nodeEnv = (env('NODE_ENV') || '').trim().toLowerCase();
    const appEnv = (env('APP_ENV') || '').trim().toLowerCase();
    const isProductionEnv =
        nodeEnv === 'production' || appEnv === 'production';

    return { isProductionEnv, nodeEnv, appEnv };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Public API
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * @param {object} options
 * @param {string} options.script - calling script name (for error messages)
 * @param {string[]} options.tables - DB tables that would be written
 * @param {string[]} options.operations - SQL operations (INSERT, UPDATE, DELETE, …)
 * @returns {object} { allowed: boolean, dryRun: boolean, error: string|null, missingGates: string[], warnings: string[] }
 */
// eslint-disable-next-line complexity
function requireDbWriteGuards(options = {}) {
    const {
        script = '<unknown>',
        tables = [],
        operations = [],
    } = options;

    const warnings = [];
    const missingGates = [];

    // ── 1. Production env detection ──────────────────────────────────────────
    const prodEnv = checkProductionEnv();
    if (prodEnv.isProductionEnv) {
        return {
            allowed: false,
            dryRun: null,
            error: [
                `[${script}] BLOCKED: NODE_ENV/APP_ENV is "${prodEnv.nodeEnv || prodEnv.appEnv}".`,
                'DB write is not allowed in production environment by default.',
                'Set NODE_ENV=development or override explicitly if this is intentional.',
            ].join(' '),
            missingGates: [],
            warnings,
        };
    }

    // ── 2. Dry-run check ────────────────────────────────────────────────────
    const dryRunEnv = env('DRY_RUN');
    const isDryRunMode = dryRunEnv === undefined || dryRunEnv === null || dryRunEnv === ''
        ? true
        : normalizeBooleanEnv(dryRunEnv) !== false;

    // ── 3. Production DB host warning ───────────────────────────────────────
    const prodDb = checkProductionDbHost();
    warnings.push(...prodDb.warnings);

    // ── 4. Universal gates ──────────────────────────────────────────────────
    for (const gate of REQUIRED_UNIVERSAL_GATES) {
        if (!isTruthy(gate)) {
            missingGates.push(gate);
        }
    }

    // ── 5. Table-level gates ────────────────────────────────────────────────
    const requiredTableGates = new Set();
    for (const table of tables) {
        for (const entry of TABLE_GATE_MAP) {
            if (entry.pattern.test(table)) {
                requiredTableGates.add(entry.gate);
                break;
            }
        }
    }

    for (const gate of requiredTableGates) {
        if (!isTruthy(gate)) {
            missingGates.push(gate);
        }
    }

    // ── 6. Schema-level gate for high-risk operations ────────────────────────
    const hasHighRiskOp = operations.some(op => HIGH_RISK_OPERATIONS.has(String(op).toUpperCase()));
    if (hasHighRiskOp && !isTruthy('ALLOW_SCHEMA_WRITE')) {
        missingGates.push('ALLOW_SCHEMA_WRITE');
    }

    // ── 7. Decision ─────────────────────────────────────────────────────────
    if (!isDryRunMode && missingGates.length === 0) {
        // All gates satisfied, not dry-run → allowed
        if (prodDb.suspicious) {
            warnings.push(
                'WARNING: DB host matches production pattern but write is proceeding. Ensure this is intentional.'
            );
        }
        return {
            allowed: true,
            dryRun: false,
            error: null,
            missingGates: [],
            warnings,
        };
    }

    if (!isDryRunMode && missingGates.length > 0) {
        const gateList = missingGates.join(', ');
        return {
            allowed: false,
            dryRun: false,
            error: [
                `[${script}] BLOCKED: DB write requires the following env vars set to "yes": ${gateList}.`,
                `Currently missing: ${gateList}.`,
                'Set the missing env vars and try again.',
            ].join(' '),
            missingGates,
            warnings,
        };
    }

    // Dry-run mode
    return {
        allowed: false,
        dryRun: true,
        error: null, // dry-run is not an error
        missingGates: [],
        warnings,
    };
}

/**
 * Assert that DB write is allowed. Throws an Error if blocked.
 *
 * @param {object} options - same as requireDbWriteGuards
 * @throws {Error} if write is not allowed
 */
function assertDbWriteAllowed(options = {}) {
    const result = requireDbWriteGuards(options);

    // Print warnings regardless
    for (const warning of result.warnings) {
        console.warn(`[db_write_guard] ${warning}`);
    }

    if (!result.allowed) {
        if (result.dryRun) {
            const reason = result.error || 'DRY_RUN is enabled (default). Set DRY_RUN=false to execute.';
            throw new Error(reason);
        }
        throw new Error(result.error || 'DB write blocked by safety gate.');
    }
}

/**
 * @returns {boolean} — true if DRY_RUN mode is active (default)
 */
function isDryRun() {
    const dryRunEnv = env('DRY_RUN');
    if (dryRunEnv === undefined || dryRunEnv === null || dryRunEnv === '') {
        return true;
    }
    return normalizeBooleanEnv(dryRunEnv) !== false;
}

/**
 * @param {object} options
 * @param {string[]} options.tables
 * @param {string[]} options.operations
 * @returns {{ universal: string[], tableLevel: string[], schemaLevel: string[] }}
 */
function describeRequiredGates(options = {}) {
    const { tables = [], operations = [] } = options;

    const tableGates = new Set();
    for (const table of tables) {
        for (const entry of TABLE_GATE_MAP) {
            if (entry.pattern.test(table)) {
                tableGates.add(entry.gate);
                break;
            }
        }
    }

    const hasHighRiskOp = operations.some(op => HIGH_RISK_OPERATIONS.has(String(op).toUpperCase()));

    return {
        universal: [...REQUIRED_UNIVERSAL_GATES],
        tableLevel: [...tableGates],
        schemaLevel: hasHighRiskOp ? ['ALLOW_SCHEMA_WRITE'] : [],
    };
}

module.exports = {
    requireDbWriteGuards,
    assertDbWriteAllowed,
    isDryRun,
    describeRequiredGates,
    // Exported for testing
    _internals: {
        normalizeBooleanEnv,
        checkProductionDbHost,
        checkProductionEnv,
        REQUIRED_UNIVERSAL_GATES,
        TABLE_GATE_MAP,
        HIGH_RISK_OPERATIONS,
        PRODUCTION_DB_HOST_PATTERNS,
    },
};
