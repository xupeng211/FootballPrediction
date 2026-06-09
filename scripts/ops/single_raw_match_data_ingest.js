#!/usr/bin/env node
/**
 * Single-match raw_match_data ingestion smoke tool.
 *
 * lifecycle: permanent / smoke-tool
 *
 * Reads a LOCAL FotMob HTML fixture (no network), extracts __NEXT_DATA__,
 * UPSERTs one row into raw_match_data (local/dev DB only), reads back,
 * verifies idempotency, then CLEANS UP the test row.
 *
 * SAFETY GUARDS (hard-block, cannot be bypassed by flags):
 *   G1. CONFIRM_LOCAL_DB_WRITE=1 env var REQUIRED for any DB write.
 *       Without it, the script is dry-run only.
 *   G2. Production DB detection: rejects DB hosts matching known production
 *       patterns (RDS, Cloud SQL, Supabase, non-local IPs, etc.).
 *   G3. No network: only reads a LOCAL file. No HTTP/HTTPS/playwright/browser.
 *   G4. Single match only: exactly one --match-id accepted.
 *   G5. data_version length ≤ 20 (raw_match_data.data_version is varchar(20)).
 *   G6. FK guard: if the match does not exist in the matches table, fails with
 *       a clear error. Does NOT auto-seed.
 *   G7. Fixture format guard: must contain __NEXT_DATA__ with parseable JSON.
 *   G8. Cleanup always runs after successful write; script exits non-zero if
 *       cleanup fails.
 *   G9. Dry-run is the DEFAULT. --commit is only honored when
 *       CONFIRM_LOCAL_DB_WRITE=1.
 *
 * Usage:
 *   # Dry-run (always safe, no env var needed):
 *   node scripts/ops/single_raw_match_data_ingest.js \
 *     --fixture data/raw/fotmob/match_detail/53_20252026_4830474.payload.html \
 *     --match-id 53_20252026_4830474
 *
 *   # Commit to local/dev DB:
 *   CONFIRM_LOCAL_DB_WRITE=1 node scripts/ops/single_raw_match_data_ingest.js \
 *     --fixture data/raw/fotmob/match_detail/53_20252026_4830474.payload.html \
 *     --match-id 53_20252026_4830474 \
 *     --commit
 *
 *   # Via Makefile:
 *   make data-raw-single-fixture-smoke                        # dry-run
 *   CONFIRM_LOCAL_DB_WRITE=1 make data-raw-single-fixture-smoke  # commit
 */

'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

// ═══════════════════════════════════════════════════════════════════════════════
// Constants — keep in sync with raw_match_data schema
// ═══════════════════════════════════════════════════════════════════════════════

const MAX_DATA_VERSION_LENGTH = 20;

// Production DB host patterns that this tool will NEVER connect to.
// Matches are case-insensitive and substring-based.
const PRODUCTION_DB_HOST_PATTERNS = [
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
    /prod/i,
    /production/i,
];

// Local-only DB host patterns that are explicitly allowed
const LOCAL_DB_HOST_WHITELIST = [
    '127.0.0.1',
    'localhost',
    'db',               // Docker compose service name
    'football_db',      // Docker compose container name
    'football_db_dev',
];

// ── Argument parsing ──────────────────────────────────────────────────────────

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_raw_match_data_ingest.js \\',
        '    --fixture <path> \\',
        '    --match-id <id> \\',
        '    [--data-version <version>] \\',
        '    [--commit] [--dry-run] [--help]',
        '',
        'SAFETY: Dry-run is the DEFAULT.',
        '        DB write REQUIRES: CONFIRM_LOCAL_DB_WRITE=1 AND --commit.',
        '',
        'Examples:',
        '  # Dry-run (always safe)',
        '  node scripts/ops/single_raw_match_data_ingest.js \\',
        '    --fixture data/raw/fotmob/match_detail/53_20252026_4830474.payload.html \\',
        '    --match-id 53_20252026_4830474',
        '',
        '  # Commit (explicit opt-in)',
        '  CONFIRM_LOCAL_DB_WRITE=1 node scripts/ops/single_raw_match_data_ingest.js \\',
        '    --fixture data/raw/fotmob/match_detail/53_20252026_4830474.payload.html \\',
        '    --match-id 53_20252026_4830474 \\',
        '    --commit',
    ].join('\n');
}

function parseArgs(argv) {
    const args = {
        fixture: null,
        matchId: null,
        dataVersion: 'fp_v2_smoke',
        commit: false,
        dryRun: true,
        help: false,
    };

    for (let i = 0; i < argv.length; i++) {
        const t = argv[i];
        if (t === '--fixture') { args.fixture = argv[++i]; }
        else if (t === '--match-id') { args.matchId = argv[++i]; }
        else if (t === '--data-version') { args.dataVersion = argv[++i]; }
        else if (t === '--commit') { args.commit = true; args.dryRun = false; }
        else if (t === '--dry-run') { args.dryRun = true; args.commit = false; }
        else if (t === '--help' || t === '-h') { args.help = true; }
        else { throw new Error(`Unknown argument: ${t}`); }
    }
    return args;
}

// ── Safety Guards (executed BEFORE any DB connection) ─────────────────────────

/**
 * G1: CONFIRM_LOCAL_DB_WRITE gate.
 * Without this env var set to '1', refuse to open any DB connection for writes.
 */
function guardConfirmLocalDbWrite(commitRequested) {
    if (!commitRequested) return true; // dry-run is always allowed
    const val = (process.env.CONFIRM_LOCAL_DB_WRITE || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G1): DB write requires CONFIRM_LOCAL_DB_WRITE=1.\n' +
            '  The --commit flag alone is not sufficient.\n' +
            '  Set CONFIRM_LOCAL_DB_WRITE=1 to confirm you are targeting a local/dev DB.'
        );
        return false;
    }
    console.log('  [G1 PASS] CONFIRM_LOCAL_DB_WRITE=1 confirmed.');
    return true;
}

/**
 * G2: Production DB detection.
 * If the effective DB host matches any production pattern, refuse.
 * If the host is NOT in the local whitelist, warn and refuse (fail-closed).
 */
function guardLocalDb(host) {
    const hostStr = String(host || '').trim().toLowerCase();

    // Check against known production patterns
    for (const pattern of PRODUCTION_DB_HOST_PATTERNS) {
        if (pattern.test(hostStr)) {
            console.error(
                `BLOCKED (G2): DB host "${host}" matches production pattern: ${pattern}.\n` +
                '  This tool only connects to local/dev databases.'
            );
            return false;
        }
    }

    // Check against local whitelist (fail-closed: if not in whitelist, reject)
    const isLocal = LOCAL_DB_HOST_WHITELIST.some(
        (allowed) => hostStr === allowed.toLowerCase()
    );
    if (!isLocal) {
        console.error(
            `BLOCKED (G2): DB host "${host}" is not in the local/dev whitelist.\n` +
            `  Allowed hosts: ${LOCAL_DB_HOST_WHITELIST.join(', ')}.\n` +
            '  If this is truly a local/dev host, add it to LOCAL_DB_HOST_WHITELIST.'
        );
        return false;
    }

    console.log(`  [G2 PASS] DB host "${host}" is in local/dev whitelist.`);
    return true;
}

/**
 * G3: No network guard — this tool only reads local files. Hard-coded.
 */
function guardNoNetwork(fixturePath) {
    if (/^https?:\/\//i.test(fixturePath)) {
        console.error(
            'BLOCKED (G3): fixture path looks like a URL.\n' +
            '  This tool only reads LOCAL files. Network fetch is forbidden.'
        );
        return false;
    }
    return true;
}

/**
 * G5: data_version length check (varchar(20) in raw_match_data).
 */
function guardDataVersionLength(version) {
    if (version.length > MAX_DATA_VERSION_LENGTH) {
        console.error(
            `BLOCKED (G5): data_version "${version}" is ${version.length} chars; ` +
            `max is ${MAX_DATA_VERSION_LENGTH}.\n` +
            '  raw_match_data.data_version is varchar(20).'
        );
        return false;
    }
    console.log(`  [G5 PASS] data_version length ${version.length} ≤ ${MAX_DATA_VERSION_LENGTH}.`);
    return true;
}

// ── HTML Extraction ───────────────────────────────────────────────────────────

function extractNextData(html) {
    const re = /<script[^>]*id="__NEXT_DATA__"[^>]*type="application\/json"[^>]*>([^<]+)<\/script>/;
    const m = html.match(re);
    if (!m) return null;
    try { return JSON.parse(m[1]); }
    catch (e) { return { _parse_error: e.message }; }
}

function extractPageProps(nextData) {
    if (!nextData || !nextData.props) return null;
    return nextData.props.pageProps || null;
}

// ── DB helpers ────────────────────────────────────────────────────────────────

function getDbConfig() {
    return {
        host: process.env.PGHOST || 'db',
        port: parseInt(process.env.PGPORT || '5432', 10),
        database: process.env.PGDATABASE || 'football_db',
        user: process.env.PGUSER || 'football_user',
        password: process.env.PGPASSWORD || '',
    };
}

function createPool(dbConfig) {
    // Dynamic import to avoid requiring pg at module load (allows --help without pg installed)
    const { Pool } = require('pg');
    return new Pool({
        host: dbConfig.host,
        port: dbConfig.port,
        database: dbConfig.database,
        user: dbConfig.user,
        password: dbConfig.password,
        max: 2,
        connectionTimeoutMillis: 10000,
    });
}

const UPSERT_SQL = `
    INSERT INTO raw_match_data (match_id, external_id, raw_data, data_version, data_hash, collected_at)
    VALUES ($1, $2, $3::jsonb, $4, $5, NOW())
    ON CONFLICT (match_id, data_version)
    DO UPDATE SET
        raw_data = EXCLUDED.raw_data,
        data_hash = EXCLUDED.data_hash,
        collected_at = NOW()
    RETURNING id, match_id, data_version, data_hash, collected_at
`;

const SELECT_SQL = `
    SELECT id, match_id, external_id, data_version, data_hash,
           collected_at,
           length(raw_data::text) AS json_size,
           raw_data->>'matchId' AS inner_match_id
    FROM raw_match_data
    WHERE match_id = $1 AND data_version = $2
`;

const CLEANUP_SQL = `
    DELETE FROM raw_match_data
    WHERE match_id = $1 AND data_version = $2
    RETURNING id
`;

// ── Output helpers ────────────────────────────────────────────────────────────

let errorCount = 0;

function ok(label, detail) {
    console.log(`  [OK] ${label}${detail ? ': ' + detail : ''}`);
}

function fail(label, detail) {
    console.error(`  [FAIL] ${label}${detail ? ': ' + detail : ''}`);
    errorCount += 1;
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.help) { console.log(usage()); process.exit(0); }

    // Validate args
    if (!args.fixture || !args.matchId) {
        console.error('ERROR: --fixture and --match-id are required.\n');
        console.log(usage());
        process.exit(1);
    }

    // ── Run ALL guards BEFORE any work ──────────────────────────────────────

    console.log('='.repeat(70));
    console.log('Single Raw Fixture Ingestion Smoke Tool');
    console.log('='.repeat(70));
    console.log(`Fixture:       ${args.fixture}`);
    console.log(`Match ID:      ${args.matchId}`);
    console.log(`Data Version:  ${args.dataVersion}`);
    console.log(`Mode:          ${args.commit ? 'COMMIT' : 'DRY-RUN'}`);
    console.log('='.repeat(70));

    console.log('\n── Safety Guards ──');

    // G3: No network
    if (!guardNoNetwork(args.fixture)) process.exit(1);
    console.log('  [G3 PASS] Fixture is a local path (no network).');

    // G5: data_version length
    if (!guardDataVersionLength(args.dataVersion)) process.exit(1);

    // G1: CONFIRM_LOCAL_DB_WRITE (only relevant for commit mode)
    if (!guardConfirmLocalDbWrite(args.commit)) process.exit(1);

    // ── Read and parse fixture ──────────────────────────────────────────────

    console.log('\n── Fixture Processing ──');

    const fixturePath = path.resolve(process.cwd(), args.fixture);
    if (!fs.existsSync(fixturePath)) {
        fail('fixture not found', fixturePath);
        process.exit(1);
    }
    ok('fixture exists', fixturePath);

    const html = fs.readFileSync(fixturePath, 'utf8');
    ok('HTML read', `${html.length} bytes`);

    const nextData = extractNextData(html);
    if (!nextData) {
        fail('__NEXT_DATA__ extraction', 'not found in HTML (G7)');
        process.exit(1);
    }
    if (nextData._parse_error) {
        fail('__NEXT_DATA__ parse', nextData._parse_error + ' (G7)');
        process.exit(1);
    }
    ok('__NEXT_DATA__ extracted', `keys: ${Object.keys(nextData).join(', ')}`);

    const pageProps = extractPageProps(nextData);
    if (!pageProps) {
        fail('pageProps extraction', 'not found in __NEXT_DATA__ (G7)');
        process.exit(1);
    }
    ok('pageProps extracted', `keys: ${Object.keys(pageProps).join(', ')}`);

    // ── Build payload ───────────────────────────────────────────────────────

    const externalId = args.matchId.split('_').pop();

    const rawData = {
        matchId: externalId,
        pageProps: pageProps,
        _meta: {
            source: 'fotmob',
            route: 'html_hydration',
            match_id: args.matchId,
            external_id: externalId,
            data_version: args.dataVersion,
            hash_strategy: 'stable_pageprops_payload_v1',
            body_byte_length: html.length,
            fixture_path: args.fixture,
            generated_at: new Date().toISOString(),
            smoke_test: true,
        },
    };

    const rawDataJson = JSON.stringify(rawData);
    const dataHash = crypto.createHash('sha256').update(rawDataJson).digest('hex');
    ok('payload built', `${rawDataJson.length} bytes, hash=${dataHash.substring(0, 16)}...`);

    // Pre-flight CHECK constraint validation
    const ckFormat = /^\d+_\d{8}_\d+$/.test(args.matchId) || /^\d+$/.test(args.matchId);
    if (!ckFormat) fail('CHECK match_id_format', args.matchId);
    if (!rawData.matchId) fail('CHECK raw_data_has_match_id');
    if (rawDataJson.length <= 2) fail('CHECK raw_data_not_empty');

    if (errorCount > 0) {
        console.error('\nPre-flight CHECK constraint validation FAILED. Aborting.');
        process.exit(1);
    }
    ok('CHECK constraints pre-flight', 'all passed');

    // ── Dry-run exit ────────────────────────────────────────────────────────
    if (args.dryRun) {
        console.log('\n── Dry-Run Summary ──');
        console.log(`  Would UPSERT → raw_match_data`);
        console.log(`    match_id     = ${args.matchId}`);
        console.log(`    external_id  = ${externalId}`);
        console.log(`    data_version = ${args.dataVersion}`);
        console.log(`    data_hash    = ${dataHash}`);
        console.log(`    raw_data     = ${rawDataJson.length} bytes JSONB`);
        console.log('');
        console.log('  To write to DB:  CONFIRM_LOCAL_DB_WRITE=1 ... --commit');
        console.log('='.repeat(70));
        console.log('DRY-RUN COMPLETE. No DB connection opened. No writes.');
        process.exit(0);
    }

    // ── Commit path: DB connection + G2 guard ────────────────────────────────
    console.log('\n── Database Connection ──');

    const dbConfig = getDbConfig();
    console.log(`  Host:     ${dbConfig.host}`);
    console.log(`  Port:     ${dbConfig.port}`);
    console.log(`  Database: ${dbConfig.database}`);
    console.log(`  User:     ${dbConfig.user}`);

    // G2: Production DB detection — runs RIGHT before connecting
    if (!guardLocalDb(dbConfig.host)) process.exit(1);

    // Late require — pg is only loaded when we actually need to connect
    let Pool;
    try {
        Pool = require('pg').Pool;
    } catch (e) {
        fail('pg module load', e.message);
        process.exit(1);
    }

    const pool = new Pool({
        host: dbConfig.host,
        port: dbConfig.port,
        database: dbConfig.database,
        user: dbConfig.user,
        password: dbConfig.password,
        max: 2,
        connectionTimeoutMillis: 10000,
    });

    let client;
    let insertedId = null;

    try {
        client = await pool.connect();
        ok('DB connected', `${dbConfig.host}:${dbConfig.port}/${dbConfig.database}`);

        // ── G6: FK check ────────────────────────────────────────────────────
        const fkResult = await client.query(
            'SELECT match_id, home_team, away_team FROM matches WHERE match_id = $1',
            [args.matchId]
        );
        if (fkResult.rows.length === 0) {
            fail('FK check (G6)', `match_id ${args.matchId} not found in matches table. Seed it first.`);
            client.release();
            await pool.end();
            process.exit(1);
        }
        const fkRow = fkResult.rows[0];
        ok('FK check', `${fkRow.match_id} (${fkRow.home_team} vs ${fkRow.away_team})`);

        // ── UPSERT ──────────────────────────────────────────────────────────
        console.log('\n── DB Write ──');
        const upsertResult = await client.query(UPSERT_SQL, [
            args.matchId,
            externalId,
            rawDataJson,
            args.dataVersion,
            dataHash,
        ]);
        const row = upsertResult.rows[0];
        insertedId = row.id;
        ok('UPSERT', `id=${row.id}, version=${row.data_version}, hash=${row.data_hash.substring(0, 16)}...`);

        // ── Read-back ───────────────────────────────────────────────────────
        console.log('\n── Read-Back Verification ──');
        const selResult = await client.query(SELECT_SQL, [args.matchId, args.dataVersion]);
        if (selResult.rows.length === 0) {
            fail('read-back', 'no row found after UPSERT');
        } else {
            const rb = selResult.rows[0];
            ok('row exists', `id=${rb.id}`);
            if (rb.match_id === args.matchId) ok('match_id matches'); else fail('match_id matches', `${rb.match_id} vs ${args.matchId}`);
            if (rb.data_version === args.dataVersion) ok('data_version matches'); else fail('data_version matches');
            if (rb.data_hash === dataHash) ok('data_hash matches'); else fail('data_hash matches');
            if (rb.json_size > 10) ok('raw_data non-empty', `${rb.json_size} bytes`); else fail('raw_data non-empty');
            if (rb.inner_match_id === externalId) ok('inner matchId', rb.inner_match_id); else fail('inner matchId');
            if (rb.collected_at) ok('collected_at set', String(rb.collected_at)); else fail('collected_at');
        }

        // ── Idempotency ─────────────────────────────────────────────────────
        console.log('\n── Idempotency Test ──');
        const upsert2 = await client.query(UPSERT_SQL, [
            args.matchId, externalId, rawDataJson, args.dataVersion, dataHash,
        ]);
        const row2 = upsert2.rows[0];
        const cntResult = await client.query(
            'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
            [args.matchId, args.dataVersion]
        );
        const rowCount = cntResult.rows[0].cnt;
        if (rowCount === 1) ok('single row', 'no duplicate');
        else fail('single row', `found ${rowCount} rows`);
        if (row2.id === insertedId) ok('same id on re-UPSERT');
        else fail('same id on re-UPSERT', `${row2.id} vs ${insertedId}`);
        if (row2.data_hash === dataHash) ok('same hash on re-UPSERT');
        else fail('same hash on re-UPSERT');

        // ── Cleanup (G8: always, mandatory) ─────────────────────────────────
        console.log('\n── Cleanup ──');
        const delResult = await client.query(CLEANUP_SQL, [args.matchId, args.dataVersion]);
        if (delResult.rows.length === 0) {
            fail('cleanup (G8)', `no row deleted for ${args.matchId}/${args.dataVersion}`);
        } else {
            ok('test row removed', `deleted id=${delResult.rows[0].id}`);
        }

        // Verify cleanup
        const afterCleanup = await client.query(
            'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
            [args.matchId, args.dataVersion]
        );
        if (afterCleanup.rows[0].cnt === 0) {
            ok('cleanup verified', '0 rows remaining');
        } else {
            fail('cleanup verified', `${afterCleanup.rows[0].cnt} rows remaining (G8)`);
        }

    } catch (err) {
        fail('DB operation', err.message);
        // Attempt emergency cleanup even on error
        if (client && insertedId) {
            try {
                await client.query(CLEANUP_SQL, [args.matchId, args.dataVersion]);
                console.error('  (emergency cleanup attempted)');
            } catch (_) { /* ignore cleanup errors during error recovery */ }
        }
        if (client) client.release();
        await pool.end();
        process.exit(1);
    }

    client.release();
    await pool.end();

    // ── Final verdict ───────────────────────────────────────────────────────
    console.log('\n' + '='.repeat(70));
    if (errorCount === 0) {
        console.log('ALL CHECKS PASSED. Smoke test SUCCESS.');
        console.log('The test row has been cleaned up from the database.');
    } else {
        console.error(`FAILED: ${errorCount} check(s) did not pass.`);
    }
    console.log('='.repeat(70));

    process.exit(errorCount === 0 ? 0 : 1);
}

main().catch(err => {
    console.error('FATAL:', err.message || err);
    process.exit(1);
});
