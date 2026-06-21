#!/usr/bin/env node
/**
 * Safe local raw_match_data ingest preview gate.
 *
 * Phase 4.21 deliberately keeps commit mode blocked. The script only reads a
 * local fixture and performs SELECT-only DB checks to produce an ingest preview.
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

const DATA_VERSION = 'PHASE4.21_DRY_RUN';
const FORBIDDEN_SQL = /\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|UPSERT|MERGE|GRANT|REVOKE)\b/i;

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/raw_match_data_local_ingest.js --fixture <path> --match-id <id> [--commit]',
        '',
        'Safety:',
        '  Dry-run only in Phase 4.21; --commit is blocked and not wired.',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        fixture: null,
        matchId: null,
        commit: false,
        help: false,
    };

    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--fixture') {
            args.fixture = argv[index + 1];
            index += 1;
        } else if (token === '--match-id') {
            args.matchId = argv[index + 1];
            index += 1;
        } else if (token === '--commit') {
            args.commit = true;
        } else if (token === '--help' || token === '-h') {
            args.help = true;
        } else {
            throw new Error(`Unknown argument: ${token}`);
        }
    }

    return args;
}

function readJsonFile(filePath) {
    const resolved = path.resolve(process.cwd(), filePath);
    const raw = fs.readFileSync(resolved, 'utf8');
    return {
        resolved,
        data: JSON.parse(raw),
    };
}

function normalizeFixtureMatchId(fixture) {
    return String(fixture.match_id || fixture.raw_data?.matchId || fixture.raw_data?.general?.matchId || '');
}

function assertFixture(fixture, expectedMatchId) {
    if (!fixture || typeof fixture !== 'object' || Array.isArray(fixture)) {
        throw new Error('Fixture root must be a JSON object');
    }

    const actualMatchId = normalizeFixtureMatchId(fixture);
    if (actualMatchId !== expectedMatchId) {
        throw new Error(`Fixture match_id does not match --match-id (${actualMatchId} != ${expectedMatchId})`);
    }

    const rawData = fixture.raw_data;
    if (!rawData || typeof rawData !== 'object' || Array.isArray(rawData)) {
        throw new Error('Fixture raw_data must be a JSON object');
    }
    if (!Object.prototype.hasOwnProperty.call(rawData, 'matchId')) {
        throw new Error('Fixture raw_data.matchId is required');
    }
    if (!rawData.general && !rawData.header) {
        throw new Error('Fixture raw_data.general or raw_data.header is required');
    }
}

function stableStringify(value) {
    if (Array.isArray(value)) {
        return `[${value.map(stableStringify).join(',')}]`;
    }
    if (value && typeof value === 'object') {
        const keys = Object.keys(value).sort();
        const entries = keys.map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`);
        return `{${entries.join(',')}}`;
    }
    return JSON.stringify(value);
}

function calculateDataHash(rawData) {
    return crypto.createHash('sha256').update(stableStringify(rawData)).digest('hex');
}

function assertSafeSelect(sql) {
    if (!/^\s*SELECT\b/i.test(sql)) {
        throw new Error('Unsafe SQL blocked: query must start with SELECT');
    }
    if (FORBIDDEN_SQL.test(sql)) {
        throw new Error('Unsafe SQL blocked: write/schema verb detected');
    }
}

async function safeSelect(pool, sql, params) {
    assertSafeSelect(sql);
    return pool.query(sql, params);
}

function buildDbConfig() {
    return {
        host: process.env.DB_HOST || process.env.POSTGRES_HOST || 'db',
        port: Number.parseInt(process.env.DB_PORT || process.env.POSTGRES_PORT || '5432', 10),
        database: process.env.DB_NAME || process.env.POSTGRES_DB || 'football_db',
        user: process.env.DB_USER || process.env.POSTGRES_USER || 'football_user',
        password: process.env.DB_PASSWORD || process.env.POSTGRES_PASSWORD,
        max: 2,
        connectionTimeoutMillis: 5000,
        idleTimeoutMillis: 5000,
    };
}

function buildBlockedCommitPayload() {
    return {
        mode: 'blocked-commit',
        ok: false,
        error: 'BLOCKED: raw_match_data commit is not wired in Phase 4.21.',
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_create_index',
            'no_l3',
            'no_elo',
            'no_external_network',
        ],
    };
}

function buildPreview({ args, fixturePath, fixture, matchFound, rawRows, oddsRows }) {
    const rawData = fixture.raw_data;
    const dataHash = calculateDataHash(rawData);

    return {
        mode: 'dry-run',
        match_id: args.matchId,
        fixture: {
            path: args.fixture,
            resolved_path: fixturePath,
            external_id: fixture.external_id || String(rawData.matchId),
            raw_data_keys: Object.keys(rawData).sort(),
            data_hash: dataHash,
        },
        db: {
            match_found: matchFound,
            raw_match_data_exists: rawRows.length > 0,
            raw_match_data_rows: rawRows.length,
            odds_history_rows: oddsRows.length,
        },
        preview: {
            would_insert_raw_match_data: false,
            target_table: 'raw_match_data',
            data_version: DATA_VERSION,
            insert_blocked_in_phase: 'Phase 4.21',
        },
        non_execution_confirmations: [
            'no_db_writes',
            'no_insert',
            'no_update',
            'no_delete',
            'no_create_index',
            'no_l3',
            'no_elo',
            'no_external_network',
        ],
    };
}

async function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) {
        console.log(usage());
        return;
    }
    if (args.commit) {
        // DB Write Safety Gate — unified guard (defense-in-depth)
        assertDbWriteAllowed({
            script: 'raw_match_data_local_ingest.js',
            tables: ['raw_match_data'],
            operations: ['INSERT', 'UPDATE'],
        });
        console.error(JSON.stringify(buildBlockedCommitPayload(), null, 2));
        process.exitCode = 1;
        return;
    }
    if (!args.fixture || !args.matchId) {
        console.error(usage());
        process.exitCode = 1;
        return;
    }

    const { resolved, data: fixture } = readJsonFile(args.fixture);
    assertFixture(fixture, args.matchId);

    const pool = new Pool(buildDbConfig());
    try {
        const matchSql = `
            SELECT match_id
            FROM matches
            WHERE match_id = $1
        `;
        const rawSql = `
            SELECT match_id, external_id, data_version, data_hash, collected_at
            FROM raw_match_data
            WHERE match_id = $1
            ORDER BY collected_at DESC
        `;
        const oddsSql = `
            SELECT match_id, bookmaker_name, market_type
            FROM bookmaker_odds_history
            WHERE match_id = $1
            ORDER BY bookmaker_name, market_type
        `;

        const matchResult = await safeSelect(pool, matchSql, [args.matchId]);
        if (matchResult.rowCount !== 1) {
            throw new Error(`Target match not found: ${args.matchId}`);
        }

        const rawResult = await safeSelect(pool, rawSql, [args.matchId]);
        const oddsResult = await safeSelect(pool, oddsSql, [args.matchId]);
        const preview = buildPreview({
            args,
            fixturePath: resolved,
            fixture,
            matchFound: true,
            rawRows: rawResult.rows,
            oddsRows: oddsResult.rows,
        });

        console.log(JSON.stringify(preview, null, 2));
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    console.error(
        JSON.stringify(
            {
                mode: 'dry-run',
                ok: false,
                error: error.message,
                non_execution_confirmations: [
                    'no_db_writes',
                    'no_insert',
                    'no_update',
                    'no_delete',
                    'no_create_index',
                    'no_l3',
                    'no_elo',
                    'no_external_network',
                ],
            },
            null,
            2
        )
    );
    process.exit(1);
});
