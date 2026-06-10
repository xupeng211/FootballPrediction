#!/usr/bin/env node
/**
 * Single-match LIVE FotMob raw ingestion smoke tool.
 *
 * lifecycle: permanent / smoke-tool
 *
 * Performs a SINGLE live HTTP fetch to FotMob match detail page, extracts
 * __NEXT_DATA__ via FotMobRawDetailFetcher, UPSERTs one row into
 * raw_match_data (local/dev DB only), reads back, verifies idempotency,
 * then CLEANS UP the test row (default smoke mode) or RETAINS it (--retain
 * mode).
 *
 * SAFETY GUARDS (hard-block, cannot be bypassed by flags):
 *   G1. CONFIRM_LOCAL_DB_WRITE=1 env var REQUIRED for any DB write.
 *       Without it, the script is dry-run only.
 *   G2. Production DB detection: rejects DB hosts matching known production
 *       patterns (RDS, Cloud SQL, Supabase, non-local IPs, etc.).
 *   G3. CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 env var REQUIRED for any live
 *       network request. Without it, NO HTTP fetch is made.
 *   G4. Single match only: exactly one --match-id accepted.
 *   G5. data_version length ≤ 20 (raw_match_data.data_version is varchar(20)).
 *   G6. FK guard: if the match does not exist in the matches table, fails with
 *       a clear error. Does NOT auto-seed.
 *   G7. Single request only: retry=0, concurrency=1, no batch.
 *   G8. Cleanup always runs after successful write in smoke mode (default);
 *       script exits non-zero if cleanup fails. In --retain mode, cleanup is
 *       SKIPPED and the row is permanently kept.
 *   G9. Dry-run is the DEFAULT. --commit is only honored when
 *       CONFIRM_LOCAL_DB_WRITE=1 AND CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1.
 *   G10. No browser, no proxy, no printBody, no saveBody.
 *   G11. CONFIRM_RETAIN_RAW_DATA=1 env var REQUIRED for --retain mode.
 *        Without it, --retain is blocked. Retained rows are NOT cleaned up.
 *
 * Usage:
 *   # Dry-run (live fetch, no DB write):
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 node scripts/ops/single_live_fotmob_raw_ingest_smoke.js \
 *     --match-id 53_20252026_4830507 \
 *     --external-id 4830507 \
 *     --home-team Nice \
 *     --away-team "Paris FC"
 *
 *   # Commit to local/dev DB (smoke mode — cleans up after):
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 \
 *     node scripts/ops/single_live_fotmob_raw_ingest_smoke.js \
 *     --match-id 53_20252026_4830507 \
 *     --external-id 4830507 \
 *     --home-team Nice \
 *     --away-team "Paris FC" \
 *     --commit
 *
 *   # Retain mode (commits AND keeps the row):
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 \
 *     CONFIRM_RETAIN_RAW_DATA=1 \
 *     node scripts/ops/single_live_fotmob_raw_ingest_smoke.js \
 *     --match-id 53_20252026_4830507 \
 *     --external-id 4830507 \
 *     --home-team Nice \
 *     --away-team "Paris FC" \
 *     --commit --retain \
 *     --data-version fotmob_live_v1
 *
 *   # Via Makefile:
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 make data-raw-single-live-fotmob-smoke  # dry-run
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 \
 *     make data-raw-single-live-fotmob-smoke  # commit (smoke)
 *   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 \
 *     CONFIRM_RETAIN_RAW_DATA=1 \
 *     make data-raw-single-live-fotmob-retain  # retain
 */

'use strict';

const crypto = require('crypto');

// ═══════════════════════════════════════════════════════════════════════════════
// Constants — keep in sync with raw_match_data schema
// ═══════════════════════════════════════════════════════════════════════════════

const MAX_DATA_VERSION_LENGTH = 20;

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

const LOCAL_DB_HOST_WHITELIST = [
    '127.0.0.1',
    'localhost',
    'db',
    'football_db',
    'football_db_dev',
];

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

let errorCount = 0;

// ═══════════════════════════════════════════════════════════════════════════════
// Argument parsing
// ═══════════════════════════════════════════════════════════════════════════════

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/single_live_fotmob_raw_ingest_smoke.js \\',
        '    --match-id <id> \\',
        '    --external-id <fotmob_id> \\',
        '    --home-team <name> \\',
        '    --away-team <name> \\',
        '    [--match-date <date>] \\',
        '    [--data-version <version>] \\',
        '    [--commit] [--dry-run] [--retain] [--help]',
        '',
        'SAFETY: Dry-run is the DEFAULT.',
        '        Live fetch REQUIRES: CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1.',
        '        DB write REQUIRES: CONFIRM_LOCAL_DB_WRITE=1 AND --commit.',
        '        Retain REQUIRES: CONFIRM_RETAIN_RAW_DATA=1 AND --retain.',
        '        Single match only. Single request only.',
        '        WARNING: --retain keeps the row in the DB permanently.',
        '        Smoke mode (default) ALWAYS cleans up after success.',
    ].join('\n');
}

function parseArgs(argv) {
    let args = {
        matchId: null, externalId: null, homeTeam: null, awayTeam: null,
        matchDate: null, dataVersion: 'fp_live_smoke',
        commit: false, dryRun: true, retain: false, help: false,
    };
    for (let i = 0; i < argv.length; i++) {
        let t = argv[i];
        if (t === '--match-id') { args.matchId = argv[++i]; }
        else if (t === '--external-id') { args.externalId = argv[++i]; }
        else if (t === '--home-team') { args.homeTeam = argv[++i]; }
        else if (t === '--away-team') { args.awayTeam = argv[++i]; }
        else if (t === '--match-date') { args.matchDate = argv[++i]; }
        else if (t === '--data-version') { args.dataVersion = argv[++i]; }
        else if (t === '--commit') { args.commit = true; args.dryRun = false; }
        else if (t === '--dry-run') { args.dryRun = true; args.commit = false; }
        else if (t === '--retain') { args.retain = true; }
        else if (t === '--help' || t === '-h') { args.help = true; }
        else { throw new Error('Unknown argument: ' + t); }
    }
    return args;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Safety Guards
// ═══════════════════════════════════════════════════════════════════════════════

function guardConfirmLiveFotmobSingleFetch() {
    let val = (process.env.CONFIRM_LIVE_FOTMOB_SINGLE_FETCH || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G3): Live FotMob fetch requires CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1.\n' +
            '  This script makes a real HTTP request to www.fotmob.com.\n' +
            '  Set CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 to confirm you intend to perform\n' +
            '  a single, low-frequency live network fetch.'
        );
        return false;
    }
    console.log('  [G3 PASS] CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 confirmed.');
    return true;
}

function guardConfirmLocalDbWrite(commitRequested) {
    if (!commitRequested) return true;
    let val = (process.env.CONFIRM_LOCAL_DB_WRITE || '').trim();
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

function guardLocalDb(host) {
    let hostStr = String(host || '').trim().toLowerCase();
    for (let i = 0; i < PRODUCTION_DB_HOST_PATTERNS.length; i++) {
        if (PRODUCTION_DB_HOST_PATTERNS[i].test(hostStr)) {
            console.error(
                'BLOCKED (G2): DB host "' + host + '" matches production pattern.\n' +
                '  This tool only connects to local/dev databases.'
            );
            return false;
        }
    }
    let isLocal = LOCAL_DB_HOST_WHITELIST.some(function (a) { return hostStr === a.toLowerCase(); });
    if (!isLocal) {
        console.error(
            'BLOCKED (G2): DB host "' + host + '" is not in the local/dev whitelist.\n' +
            '  Allowed hosts: ' + LOCAL_DB_HOST_WHITELIST.join(', ') + '.'
        );
        return false;
    }
    console.log('  [G2 PASS] DB host "' + host + '" is in local/dev whitelist.');
    return true;
}

function guardDataVersionLength(version) {
    if (version.length > MAX_DATA_VERSION_LENGTH) {
        console.error(
            'BLOCKED (G5): data_version "' + version + '" is ' + version.length +
            ' chars; max is ' + MAX_DATA_VERSION_LENGTH + '.'
        );
        return false;
    }
    console.log('  [G5 PASS] data_version length ' + version.length + ' ≤ ' + MAX_DATA_VERSION_LENGTH + '.');
    return true;
}

function guardConfirmRetainRawData(retainRequested) {
    if (!retainRequested) return true;
    let val = (process.env.CONFIRM_RETAIN_RAW_DATA || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G11): --retain mode requires CONFIRM_RETAIN_RAW_DATA=1.\n' +
            '  Retained rows are NOT automatically cleaned up. This is a permanent\n' +
            '  write to the local/dev raw_match_data table.\n' +
            '  Set CONFIRM_RETAIN_RAW_DATA=1 to confirm you intend to permanently\n' +
            '  retain this raw payload as a data asset.'
        );
        return false;
    }
    console.log('  [G11 PASS] CONFIRM_RETAIN_RAW_DATA=1 confirmed. Row will be RETAINED.');
    return true;
}

function runSafetyGuards(args) {
    console.log('\n── Safety Guards ──');
    if (!guardConfirmLiveFotmobSingleFetch()) process.exit(1);
    if (!guardDataVersionLength(args.dataVersion)) process.exit(1);
    if (!guardConfirmLocalDbWrite(args.commit)) process.exit(1);
    if (!guardConfirmRetainRawData(args.retain)) process.exit(1);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Output helpers
// ═══════════════════════════════════════════════════════════════════════════════

function ok(label, detail) {
    console.log('  [OK] ' + label + (detail ? ': ' + detail : ''));
}

function fail(label, detail) {
    console.error('  [FAIL] ' + label + (detail ? ': ' + detail : ''));
    errorCount += 1;
}

function printBanner(args) {
    let mode = args.retain ? 'COMMIT (RETAIN)' : (args.commit ? 'COMMIT (SMOKE)' : 'DRY-RUN');
    console.log('='.repeat(70));
    console.log('Single Live FotMob Raw Ingestion Smoke Tool');
    console.log('='.repeat(70));
    console.log('Match ID:      ' + args.matchId);
    console.log('External ID:   ' + args.externalId);
    console.log('Home:          ' + args.homeTeam);
    console.log('Away:          ' + args.awayTeam);
    console.log('Match Date:    ' + (args.matchDate || 'N/A'));
    console.log('Data Version:  ' + args.dataVersion);
    console.log('Mode:          ' + mode);
    console.log('='.repeat(70));
}

// ═══════════════════════════════════════════════════════════════════════════════
// Live FotMob Fetch — uses FotMobRawDetailFetcher with real node:fetch
// ═══════════════════════════════════════════════════════════════════════════════

async function executeLiveFetch(args) {
    console.log('\n── Live FotMob Fetch ──');
    console.log('  Target URL: https://www.fotmob.com/match/' + args.externalId);

    // Late-load to avoid require() side-effects before guards pass
    const { fetchFotMobRawDetail } = require('../../src/infrastructure/services/FotMobRawDetailFetcher');
    const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');

    const fetchInput = {
        externalId: args.externalId,
        matchId: args.matchId,
        homeTeam: args.homeTeam,
        awayTeam: args.awayTeam,
        matchDate: args.matchDate || undefined,
        dataVersion: args.dataVersion,
    };

    const result = await fetchFotMobRawDetail(fetchInput, {
        fetchFn: fetch,
        parser: { extractFromHtml, transformToApiFormat },
    });

    console.log('  HTTP status:    ' + result.http_status);
    console.log('  Content-Type:   ' + result.content_type);
    console.log('  Body bytes:     ' + result.body_byte_length);
    console.log('  Body SHA256:    ' + result.body_sha256);

    if (!result.ok) {
        fail('live fetch', result.controlled_error || 'unknown error');
        console.error('\n── Fetch Failure Report ──');
        console.error('  HTTP status:            ' + result.http_status);
        console.error('  Has HTML:               ' + (result.body_byte_length > 0 ? 'YES' : 'NO'));
        console.error('  Hydration parse OK:     ' + result.hydration_parse_ok);
        console.error('  Error:                  ' + (result.controlled_error || 'unknown'));
        return null;
    }

    ok('live fetch', 'HTTP ' + result.http_status + ', ' + result.body_byte_length + ' bytes');
    ok('__NEXT_DATA__ parse', 'hydration_parse_ok=' + result.hydration_parse_ok);
    ok('transformToApiFormat', 'transformed=' + result.transformed_api_format);
    ok('stable_raw_payload_hash', result.stable_raw_payload_hash);
    ok('match_id_source', result.match_id_source);

    if (result.stable_raw_payload) {
        let sp = result.stable_raw_payload;
        ok('payload.matchId', sp.matchId);
        ok('content keys', Object.keys(sp.content || {}).length + ' keys');
        ok('general keys', Object.keys(sp.general || {}).length + ' keys');
        ok('header keys', Object.keys(sp.header || {}).length + ' keys');
    }

    ok('looks_like_valid_match_detail', String(result.looks_like_valid_match_detail));

    return result;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Dry-run summary — prints live fetch result and exits without DB write
// ═══════════════════════════════════════════════════════════════════════════════

function printDryRunSummary(args, fetchResult) {
    console.log('\n── Dry-Run Summary ──');
    console.log('  Live fetch completed successfully.');
    console.log('  Would UPSERT → raw_match_data');
    console.log('    match_id     = ' + args.matchId);
    console.log('    external_id  = ' + args.externalId);
    console.log('    data_version = ' + args.dataVersion);
    console.log('    data_hash    = ' + fetchResult.raw_data_hash);
    console.log('    raw_data     = ' + JSON.stringify(fetchResult.raw_data).length + ' bytes JSONB');
    console.log('');
    console.log('  To write to DB (smoke):  CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 ... --commit');
    console.log('  To retain permanently:   CONFIRM_LIVE_FOTMOB_SINGLE_FETCH=1 CONFIRM_LOCAL_DB_WRITE=1 CONFIRM_RETAIN_RAW_DATA=1 ... --commit --retain');
    console.log('='.repeat(70));
    console.log('DRY-RUN COMPLETE. No DB connection opened. No writes.');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Read-back verification
// ═══════════════════════════════════════════════════════════════════════════════

function verifyReadback(row, matchId, dataVersion, dataHash, externalId) {
    if (row.match_id === matchId) ok('match_id matches'); else fail('match_id matches', row.match_id + ' vs ' + matchId);
    if (row.data_version === dataVersion) ok('data_version matches'); else fail('data_version matches', row.data_version + ' vs ' + dataVersion);
    if (row.data_hash === dataHash) ok('data_hash matches'); else fail('data_hash matches');
    if (row.json_size > 10) ok('raw_data non-empty', row.json_size + ' bytes'); else fail('raw_data non-empty');
    if (row.inner_match_id === externalId) ok('inner matchId', row.inner_match_id); else fail('inner matchId');
    if (row.collected_at) ok('collected_at set', String(row.collected_at)); else fail('collected_at');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Idempotency check
// ═══════════════════════════════════════════════════════════════════════════════

async function verifyIdempotency(client, params, originalId, dataHash) {
    console.log('\n── Idempotency Test ──');
    let upsert2 = await client.query(UPSERT_SQL, params);
    let row2 = upsert2.rows[0];
    let cnt = await client.query(
        'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
        [params[0], params[3]]
    );
    let rowCount = cnt.rows[0].cnt;
    if (rowCount === 1) ok('single row', 'no duplicate'); else fail('single row', 'found ' + rowCount + ' rows');
    if (row2.id === originalId) ok('same id on re-UPSERT'); else fail('same id on re-UPSERT', row2.id + ' vs ' + originalId);
    if (row2.data_hash === dataHash) ok('same hash on re-UPSERT'); else fail('same hash on re-UPSERT');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Cleanup
// ═══════════════════════════════════════════════════════════════════════════════

async function runCleanup(client, matchId, dataVersion) {
    console.log('\n── Cleanup ──');
    let del = await client.query(CLEANUP_SQL, [matchId, dataVersion]);
    if (del.rows.length === 0) {
        fail('cleanup (G8)', 'no row deleted for ' + matchId + '/' + dataVersion);
    } else {
        ok('test row removed', 'deleted id=' + del.rows[0].id);
    }
    let after = await client.query(
        'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
        [matchId, dataVersion]
    );
    if (after.rows[0].cnt === 0) ok('cleanup verified', '0 rows remaining');
    else fail('cleanup verified', after.rows[0].cnt + ' rows remaining (G8)');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main DB write path
// ═══════════════════════════════════════════════════════════════════════════════

async function executeDbWrite(dbConfig, args, fetchResult) {
    console.log('\n── Database Connection ──');
    console.log('  Host:     ' + dbConfig.host);
    console.log('  Port:     ' + dbConfig.port);
    console.log('  Database: ' + dbConfig.database);
    console.log('  User:     ' + dbConfig.user);

    if (!guardLocalDb(dbConfig.host)) process.exit(1);

    let Pg;
    try { Pg = require('pg'); } catch (e) { fail('pg module load', e.message); process.exit(1); }

    let pool = new Pg.Pool({
        host: dbConfig.host, port: dbConfig.port,
        database: dbConfig.database, user: dbConfig.user, password: dbConfig.password,
        max: 2, connectionTimeoutMillis: 10000,
    });

    let client, insertedId;
    let rawDataJson = JSON.stringify(fetchResult.raw_data);
    let upsertParams = [args.matchId, args.externalId, rawDataJson, args.dataVersion, fetchResult.raw_data_hash];

    try {
        client = await pool.connect();
        ok('DB connected', dbConfig.host + ':' + dbConfig.port + '/' + dbConfig.database);

        // G6: FK check
        let fk = await client.query('SELECT match_id, home_team, away_team FROM matches WHERE match_id = $1', [args.matchId]);
        if (fk.rows.length === 0) {
            fail('FK check (G6)', 'match_id ' + args.matchId + ' not found in matches table. Seed it first.');
            client.release(); await pool.end(); process.exit(1);
        }
        ok('FK check', fk.rows[0].match_id + ' (' + fk.rows[0].home_team + ' vs ' + fk.rows[0].away_team + ')');

        // UPSERT
        console.log('\n── DB Write ──');
        let upsert = await client.query(UPSERT_SQL, upsertParams);
        insertedId = upsert.rows[0].id;
        ok('UPSERT', 'id=' + insertedId + ', version=' + upsert.rows[0].data_version);

        // Read-back
        console.log('\n── Read-Back Verification ──');
        let sel = await client.query(SELECT_SQL, [args.matchId, args.dataVersion]);
        if (sel.rows.length === 0) { fail('read-back', 'no row found after UPSERT'); }
        else {
            ok('row exists', 'id=' + sel.rows[0].id);
            verifyReadback(sel.rows[0], args.matchId, args.dataVersion, fetchResult.raw_data_hash, args.externalId);
        }

        // Idempotency
        await verifyIdempotency(client, upsertParams, insertedId, fetchResult.raw_data_hash);

        // Retain or Cleanup
        if (args.retain) {
            await printRetainSummary(client, args, fetchResult);
        } else {
            await runCleanup(client, args.matchId, args.dataVersion);
        }

    } catch (err) {
        fail('DB operation', err.message);
        if (client && insertedId && !args.retain) {
            try { await client.query(CLEANUP_SQL, [args.matchId, args.dataVersion]); }
            catch (_) { /* ignore */ }
        }
        if (client) client.release();
        await pool.end();
        process.exit(1);
    }

    client.release();
    await pool.end();
}

// ═══════════════════════════════════════════════════════════════════════════════
// Retain summary — prints retention confirmation and rollback SQL
// ═══════════════════════════════════════════════════════════════════════════════

async function printRetainSummary(client, args, fetchResult) {
    console.log('\n── Retain Summary ──');
    let cnt = await client.query(
        'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
        [args.matchId, args.dataVersion]
    );
    let rowCount = cnt.rows[0].cnt;
    ok('retained row count', String(rowCount));
    ok('retained match_id', args.matchId);
    ok('retained data_version', args.dataVersion);
    ok('retained data_hash', fetchResult.raw_data_hash);

    console.log('\n── Rollback SQL (run manually only if needed) ──');
    console.log('-- WARNING: This deletes the retained raw payload. Only run if explicitly requested.');
    console.log('DELETE FROM raw_match_data');
    console.log('WHERE match_id = \'' + args.matchId + '\'');
    console.log('  AND data_version = \'' + args.dataVersion + '\';');
    console.log('');
    console.log('-- Verify deletion:');
    console.log('SELECT COUNT(*) FROM raw_match_data');
    console.log('WHERE match_id = \'' + args.matchId + '\'');
    console.log('  AND data_version = \'' + args.dataVersion + '\';');
    console.log('-- Expected after deletion: 0');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Final verdict
// ═══════════════════════════════════════════════════════════════════════════════

function printVerdict(retainMode) {
    console.log('\n' + '='.repeat(70));
    if (errorCount === 0) {
        if (retainMode) {
            console.log('ALL CHECKS PASSED. Live FotMob retain SUCCESS.');
            console.log('The row has been RETAINED in the local/dev database.');
            console.log('It will NOT be automatically cleaned up.');
        } else {
            console.log('ALL CHECKS PASSED. Live FotMob smoke test SUCCESS.');
            console.log('The test row has been cleaned up from the database.');
        }
    } else {
        console.error('FAILED: ' + errorCount + ' check(s) did not pass.');
    }
    console.log('='.repeat(70));
    process.exit(errorCount === 0 ? 0 : 1);
}

// ═══════════════════════════════════════════════════════════════════════════════
// DB config
// ═══════════════════════════════════════════════════════════════════════════════

function getDbConfig() {
    return {
        host: process.env.PGHOST || 'db',
        port: parseInt(process.env.PGPORT || '5432', 10),
        database: process.env.PGDATABASE || 'football_db',
        user: process.env.PGUSER || 'football_user',
        password: process.env.PGPASSWORD || '',
    };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════════════════════

async function main() {
    let args = parseArgs(process.argv.slice(2));
    if (args.help) { console.log(usage()); process.exit(0); }
    if (!args.matchId || !args.externalId || !args.homeTeam || !args.awayTeam) {
        console.error('ERROR: --match-id, --external-id, --home-team, and --away-team are required.\n');
        console.log(usage());
        process.exit(1);
    }
    if (!/^\d+$/.test(args.externalId)) {
        console.error('ERROR: --external-id must be numeric (FotMob match ID).');
        process.exit(1);
    }

    printBanner(args);
    runSafetyGuards(args);

    // ── Phase 1: Live fetch (always) ──
    let fetchResult = await executeLiveFetch(args);
    if (!fetchResult) {
        console.error('\nLive fetch FAILED. Aborting.');
        process.exit(1);
    }

    // ── Phase 2: DB write (commit only) ──
    if (args.dryRun) {
        printDryRunSummary(args, fetchResult);
        process.exit(0);
    }

    let dbConfig = getDbConfig();
    await executeDbWrite(dbConfig, args, fetchResult);
    printVerdict(args.retain);
}

main().catch(function (err) {
    console.error('FATAL:', err.message || err);
    process.exit(1);
});
