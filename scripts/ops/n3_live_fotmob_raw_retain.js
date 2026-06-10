#!/usr/bin/env node
/**
 * N=3 FotMob small-batch raw retain tool.
 *
 * lifecycle: permanent / retain-tool
 *
 * Reads a candidate list from a JSON config file, iterates through exactly
 * 3 FotMob matches, performs live fetch + UPSERT + read-back + idempotency
 * for each, and RETAINS all 3 rows. Fail-fast on any error.
 *
 * SAFETY GUARDS:
 *   G1. CONFIRM_LOCAL_DB_WRITE=1 REQUIRED
 *   G2. Production DB detection (hard-block)
 *   G3. CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 REQUIRED for any live fetch
 *   G4. CONFIRM_RETAIN_RAW_DATA=1 REQUIRED for retain
 *   G5. CONFIRM_MAX_MATCHES=3 REQUIRED — must match candidate count exactly
 *   G6. data_version ≤ 20 chars
 *   G7. Single request per match, no retry
 *   G8. N must be exactly count of candidates in config (hardcoded check)
 *   G9. Dry-run is DEFAULT (no DB write, no live fetch without confirm)
 *   G10. Fail-fast: any match fails → stop immediately, report which failed
 *   G11. No cleanup — all 3 rows retained
 *
 * Usage:
 *   # Dry-run:
 *   CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 \
 *     node scripts/ops/n3_live_fotmob_raw_retain.js \
 *     --config configs/data/fotmob_n3_raw_retain_candidates.json
 *
 *   # Retain (commit):
 *   CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 \
 *   CONFIRM_LOCAL_DB_WRITE=1 \
 *   CONFIRM_RETAIN_RAW_DATA=1 \
 *   CONFIRM_MAX_MATCHES=3 \
 *     node scripts/ops/n3_live_fotmob_raw_retain.js \
 *     --config configs/data/fotmob_n3_raw_retain_candidates.json \
 *     --commit --retain
 *
 *   # Via Makefile:
 *   CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 \
 *   CONFIRM_LOCAL_DB_WRITE=1 \
 *   CONFIRM_RETAIN_RAW_DATA=1 \
 *   CONFIRM_MAX_MATCHES=3 \
 *     make data-raw-n3-live-fotmob-retain
 */

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ═══════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════

const MAX_DATA_VERSION_LENGTH = 20;
const ALLOWED_CANDIDATE_COUNT = 3;

const PRODUCTION_DB_HOST_PATTERNS = [
    /rds\.amazonaws\.com/i, /\.rds\.amazonaws/i, /cloudsql\.google/i,
    /\.supabase\./i, /\.supabase\.co/i, /\.vercel/i, /\.fly\.dev/i,
    /\.railway\.app/i, /\.render\.com/i, /\.heroku/i, /prod/i, /production/i,
];

const LOCAL_DB_HOST_WHITELIST = [
    '127.0.0.1', 'localhost', 'db', 'football_db', 'football_db_dev',
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

let errorCount = 0;
let results = [];

// ═══════════════════════════════════════════════════════════════
// Argument parsing
// ═══════════════════════════════════════════════════════════════

function usage() {
    return [
        'Usage:',
        '  node scripts/ops/n3_live_fotmob_raw_retain.js \\',
        '    --config <path> \\',
        '    [--data-version <version>] \\',
        '    [--commit] [--dry-run] [--retain] [--help]',
        '',
        'SAFETY: Dry-run is the DEFAULT.',
        '  Live fetch REQUIRES: CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1.',
        '  DB write REQUIRES: CONFIRM_LOCAL_DB_WRITE=1 AND --commit.',
        '  Retain REQUIRES: CONFIRM_RETAIN_RAW_DATA=1.',
        '  Batch REQUIRES: CONFIRM_MAX_MATCHES=3.',
        '  Exactly 3 matches in config. Single request per match.',
        '  WARNING: Retain mode keeps ALL 3 rows permanently.',
    ].join('\n');
}

function parseArgs(argv) {
    let args = {
        config: null, dataVersion: 'fotmob_live_v1',
        commit: false, dryRun: true, retain: false, help: false,
    };
    for (let i = 0; i < argv.length; i++) {
        let t = argv[i];
        if (t === '--config') { args.config = argv[++i]; }
        else if (t === '--data-version') { args.dataVersion = argv[++i]; }
        else if (t === '--commit') { args.commit = true; args.dryRun = false; }
        else if (t === '--dry-run') { args.dryRun = true; args.commit = false; }
        else if (t === '--retain') { args.retain = true; }
        else if (t === '--help' || t === '-h') { args.help = true; }
        else { throw new Error('Unknown argument: ' + t); }
    }
    return args;
}

// ═══════════════════════════════════════════════════════════════
// Safety Guards
// ═══════════════════════════════════════════════════════════════

function guardConfirmLiveFotmobSmallBatch() {
    let val = (process.env.CONFIRM_LIVE_FOTMOB_SMALL_BATCH || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G3): Small-batch live FotMob fetch requires CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1.\n' +
            '  Set CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 to confirm you intend to perform\n' +
            '  3 real HTTP requests to www.fotmob.com.'
        );
        return false;
    }
    console.log('  [G3 PASS] CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 confirmed.');
    return true;
}

function guardConfirmLocalDbWrite(commitRequested) {
    if (!commitRequested) return true;
    let val = (process.env.CONFIRM_LOCAL_DB_WRITE || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G1): DB write requires CONFIRM_LOCAL_DB_WRITE=1.\n' +
            '  Set CONFIRM_LOCAL_DB_WRITE=1 to confirm local/dev DB writes.'
        );
        return false;
    }
    console.log('  [G1 PASS] CONFIRM_LOCAL_DB_WRITE=1 confirmed.');
    return true;
}

function guardConfirmRetainRawData(retainRequested) {
    if (!retainRequested) return true;
    let val = (process.env.CONFIRM_RETAIN_RAW_DATA || '').trim();
    if (val !== '1') {
        console.error(
            'BLOCKED (G4): Retain requires CONFIRM_RETAIN_RAW_DATA=1.\n' +
            '  Set CONFIRM_RETAIN_RAW_DATA=1 to confirm permanent retention.'
        );
        return false;
    }
    console.log('  [G4 PASS] CONFIRM_RETAIN_RAW_DATA=1 confirmed.');
    return true;
}

function guardMaxMatches(actual) {
    let val = (process.env.CONFIRM_MAX_MATCHES || '').trim();
    if (val !== String(ALLOWED_CANDIDATE_COUNT)) {
        console.error(
            'BLOCKED (G5): CONFIRM_MAX_MATCHES must be ' + ALLOWED_CANDIDATE_COUNT +
            ', got "' + val + '".'
        );
        return false;
    }
    console.log('  [G5 PASS] CONFIRM_MAX_MATCHES=' + ALLOWED_CANDIDATE_COUNT + ' matches.');
    return true;
}

function guardCandidateCount(actual) {
    if (actual !== ALLOWED_CANDIDATE_COUNT) {
        console.error(
            'BLOCKED (G8): Config contains ' + actual + ' candidates, ' +
            'expected exactly ' + ALLOWED_CANDIDATE_COUNT + '.'
        );
        return false;
    }
    console.log('  [G8 PASS] Candidate count = ' + actual + '.');
    return true;
}

function guardLocalDb(host) {
    let hostStr = String(host || '').trim().toLowerCase();
    for (let pat of PRODUCTION_DB_HOST_PATTERNS) {
        if (pat.test(hostStr)) {
            console.error('BLOCKED (G2): DB host "' + host + '" matches production pattern.');
            return false;
        }
    }
    let isLocal = LOCAL_DB_HOST_WHITELIST.some(a => hostStr === a.toLowerCase());
    if (!isLocal) {
        console.error('BLOCKED (G2): DB host "' + host + '" not in local/dev whitelist.');
        return false;
    }
    console.log('  [G2 PASS] DB host "' + host + '" is in local/dev whitelist.');
    return true;
}

function guardDataVersionLength(version) {
    if (version.length > MAX_DATA_VERSION_LENGTH) {
        console.error('BLOCKED (G6): data_version "' + version + '" is ' +
            version.length + ' chars; max ' + MAX_DATA_VERSION_LENGTH + '.');
        return false;
    }
    console.log('  [G6 PASS] data_version length ' + version.length + ' ≤ ' + MAX_DATA_VERSION_LENGTH + '.');
    return true;
}

function runSafetyGuards(args, candidateCount) {
    console.log('\n── Safety Guards ──');
    if (!guardConfirmLiveFotmobSmallBatch()) process.exit(1);
    if (!guardDataVersionLength(args.dataVersion)) process.exit(1);
    if (!guardConfirmLocalDbWrite(args.commit)) process.exit(1);
    if (!guardConfirmRetainRawData(args.retain)) process.exit(1);
    if (!guardMaxMatches(candidateCount)) process.exit(1);
    if (!guardCandidateCount(candidateCount)) process.exit(1);
}

// ═══════════════════════════════════════════════════════════════
// Output helpers
// ═══════════════════════════════════════════════════════════════

function ok(label, detail) {
    console.log('  [OK] ' + label + (detail ? ': ' + detail : ''));
}

function fail(label, detail) {
    console.error('  [FAIL] ' + label + (detail ? ': ' + detail : ''));
    errorCount += 1;
}

function printBanner(args, candidates) {
    let mode = args.retain ? 'COMMIT (RETAIN)' : (args.commit ? 'COMMIT' : 'DRY-RUN');
    console.log('='.repeat(70));
    console.log('N=3 FotMob Small-Batch Raw Retain Tool');
    console.log('='.repeat(70));
    console.log('Config:        ' + args.config);
    console.log('Candidates:    ' + candidates.length);
    console.log('Data Version:  ' + args.dataVersion);
    console.log('Mode:          ' + mode);
    console.log('='.repeat(70));
    candidates.forEach(function (c, i) {
        console.log('  [' + (i + 1) + '] ' + c.match_id + '  ' +
            c.home_team + ' vs ' + c.away_team + '  ' + c.match_date);
    });
    console.log('='.repeat(70));
}

// ═══════════════════════════════════════════════════════════════
// Live fetch for a single candidate
// ═══════════════════════════════════════════════════════════════

async function executeLiveFetch(candidate, dataVersion) {
    const { fetchFotMobRawDetail } = require('../../src/infrastructure/services/FotMobRawDetailFetcher');
    const { extractFromHtml, transformToApiFormat } = require('../../src/parsers/fotmob/NextDataParser');

    const fetchInput = {
        externalId: candidate.external_id,
        matchId: candidate.match_id,
        homeTeam: candidate.home_team,
        awayTeam: candidate.away_team,
        matchDate: candidate.match_date || undefined,
        dataVersion: dataVersion,
    };

    const result = await fetchFotMobRawDetail(fetchInput, {
        fetchFn: fetch,
        parser: { extractFromHtml, transformToApiFormat },
    });

    console.log('  HTTP status:    ' + result.http_status);
    console.log('  Body bytes:     ' + result.body_byte_length);
    console.log('  Body SHA256:    ' + result.body_sha256);

    if (!result.ok) {
        fail('live fetch', result.controlled_error || 'unknown error');
        console.error('  HTTP status: ' + result.http_status);
        console.error('  Hydration parse OK: ' + result.hydration_parse_ok);
        return null;
    }

    ok('live fetch', 'HTTP ' + result.http_status + ', ' + result.body_byte_length + ' bytes');
    ok('stable_raw_payload_hash', result.stable_raw_payload_hash);
    ok('looks_like_valid_match_detail', String(result.looks_like_valid_match_detail));

    return result;
}

// ═══════════════════════════════════════════════════════════════
// DB write + read-back + idempotency for one match
// ═══════════════════════════════════════════════════════════════

async function executeDbWriteForMatch(client, candidate, dataVersion, fetchResult) {
    let rawDataJson = JSON.stringify(fetchResult.raw_data);
    let upsertParams = [
        candidate.match_id, candidate.external_id, rawDataJson,
        dataVersion, fetchResult.raw_data_hash
    ];

    // FK check
    let fk = await client.query(
        'SELECT match_id, home_team, away_team FROM matches WHERE match_id = $1',
        [candidate.match_id]
    );
    if (fk.rows.length === 0) {
        fail('FK check', candidate.match_id + ' not in matches table');
        return false;
    }
    ok('FK check', fk.rows[0].home_team + ' vs ' + fk.rows[0].away_team);

    // UPSERT
    let upsert = await client.query(UPSERT_SQL, upsertParams);
    let insertedId = upsert.rows[0].id;
    ok('UPSERT', 'id=' + insertedId);

    // Read-back
    let sel = await client.query(SELECT_SQL, [candidate.match_id, dataVersion]);
    if (sel.rows.length === 0) { fail('read-back', 'no row'); return false; }
    let row = sel.rows[0];
    let ok_readback = true;
    if (row.match_id !== candidate.match_id) { fail('match_id', row.match_id); ok_readback = false; }
    else { ok('match_id matches'); }
    if (row.data_version !== dataVersion) { fail('data_version', row.data_version); ok_readback = false; }
    else { ok('data_version matches'); }
    if (row.data_hash !== fetchResult.raw_data_hash) { fail('data_hash'); ok_readback = false; }
    else { ok('data_hash matches'); }
    if (row.json_size <= 10) { fail('raw_data empty'); ok_readback = false; }
    else { ok('raw_data non-empty', row.json_size + ' bytes'); }
    if (row.inner_match_id !== candidate.external_id) { fail('inner matchId', row.inner_match_id); ok_readback = false; }
    else { ok('inner matchId matches'); }
    if (!row.collected_at) { fail('collected_at'); ok_readback = false; }
    else { ok('collected_at set'); }

    if (!ok_readback) return false;

    // Idempotency
    let upsert2 = await client.query(UPSERT_SQL, upsertParams);
    let row2 = upsert2.rows[0];
    let cnt = await client.query(
        'SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE match_id = $1 AND data_version = $2',
        [candidate.match_id, dataVersion]
    );
    let rowCount = cnt.rows[0].cnt;
    let ok_idem = true;
    if (rowCount !== 1) { fail('row count after re-UPSERT', String(rowCount)); ok_idem = false; }
    else { ok('single row', 'no duplicate'); }
    if (row2.id !== insertedId) { fail('same id', String(row2.id)); ok_idem = false; }
    else { ok('same id on re-UPSERT'); }
    if (row2.data_hash !== fetchResult.raw_data_hash) { fail('same hash'); ok_idem = false; }
    else { ok('same hash on re-UPSERT'); }

    if (!ok_idem) return false;

    return {
        candidate: candidate,
        dbId: insertedId,
        dataHash: fetchResult.raw_data_hash,
        jsonBytes: row.json_size,
    };
}

// ═══════════════════════════════════════════════════════════════
// Dry-run summary
// ═══════════════════════════════════════════════════════════════

function printDryRunSummary(candidates) {
    console.log('\n── N=3 Dry-Run Summary ──');
    console.log('  Would perform 3 live fetches + UPSERTs → raw_match_data');
    candidates.forEach(function (c, i) {
        console.log('  [' + (i + 1) + '] ' + c.match_id + '  ' +
            c.home_team + ' vs ' + c.away_team);
    });
    console.log('');
    console.log('  To commit: CONFIRM_LIVE_FOTMOB_SMALL_BATCH=1 ' +
        'CONFIRM_LOCAL_DB_WRITE=1 CONFIRM_RETAIN_RAW_DATA=1 ' +
        'CONFIRM_MAX_MATCHES=3 --commit --retain');
    console.log('='.repeat(70));
    console.log('DRY-RUN COMPLETE. No network requests. No DB writes.');
}

// ═══════════════════════════════════════════════════════════════
// Consolidated retain summary + rollback SQL
// ═══════════════════════════════════════════════════════════════

function printConsolidatedReport(dataVersion) {
    console.log('\n' + '='.repeat(70));
    console.log('N=3 RETAIN COMPLETE');
    console.log('='.repeat(70));
    results.forEach(function (r, i) {
        console.log('  [' + (i + 1) + '] ' + r.candidate.match_id +
            '  id=' + r.dbId + '  hash=' + r.dataHash.substring(0, 16) + '...');
    });
    console.log('');
    console.log('── Consolidated Rollback SQL (run manually only) ──');
    console.log('-- WARNING: This deletes all 3 retained raw payloads.');
    results.forEach(function (r) {
        console.log('DELETE FROM raw_match_data');
        console.log('WHERE match_id = \'' + r.candidate.match_id + '\'');
        console.log('  AND data_version = \'' + dataVersion + '\';');
    });
    console.log('');
    console.log('-- Verify:');
    console.log('SELECT COUNT(*) FROM raw_match_data');
    console.log('WHERE data_version = \'' + dataVersion + '\'');
    console.log('  AND match_id IN (' +
        results.map(function (r) { return '\'' + r.candidate.match_id + '\''; }).join(', ') + ');');
    console.log('-- Expected after deletion: 0');
}

// ═══════════════════════════════════════════════════════════════
// Batch processor — iterate through candidates with fail-fast
// ═══════════════════════════════════════════════════════════════

async function processBatchMatches(client, candidates, dataVersion) {
    for (let i = 0; i < candidates.length; i++) {
        let c = candidates[i];
        console.log('\n' + '─'.repeat(70));
        console.log('[' + (i + 1) + '/' + candidates.length + '] ' +
            c.match_id + '  ' + c.home_team + ' vs ' + c.away_team);
        console.log('─'.repeat(70));

        // Phase 1: Live fetch
        console.log('\n── Live FotMob Fetch [' + (i + 1) + '/' + candidates.length + '] ──');
        console.log('  Target: https://www.fotmob.com/match/' + c.external_id);
        let fetchResult = await executeLiveFetch(c, dataVersion);
        if (!fetchResult) {
            console.error('\nFAIL: Fetch failed for ' + c.match_id +
                '. Stopping batch. No more matches will be processed.');
            console.error('Previously successful matches are retained in DB.');
            return false;
        }

        // Phase 2: DB write
        console.log('\n── DB Write [' + (i + 1) + '/' + candidates.length + '] ──');
        let writeResult = await executeDbWriteForMatch(client, c, dataVersion, fetchResult);
        if (!writeResult) {
            console.error('\nFAIL: DB write/verify failed for ' + c.match_id +
                '. Stopping batch.');
            console.error('Previously successful matches are retained.');
            return false;
        }
        results.push(writeResult);
        ok('MATCH COMPLETE', c.match_id);
    }
    return true;
}

// ═══════════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════════

function getDbConfig() {
    return {
        host: process.env.PGHOST || 'db',
        port: parseInt(process.env.PGPORT || '5432', 10),
        database: process.env.PGDATABASE || 'football_db',
        user: process.env.PGUSER || 'football_user',
        password: process.env.PGPASSWORD || '',
    };
}

function loadCandidates(configPath) {
    let resolved = path.resolve(process.cwd(), configPath);
    if (!fs.existsSync(resolved)) {
        console.error('ERROR: Config file not found: ' + resolved);
        process.exit(1);
    }
    try { return JSON.parse(fs.readFileSync(resolved, 'utf8')).candidates || []; }
    catch (e) { console.error('ERROR: Invalid JSON in config: ' + e.message); process.exit(1); }
}

async function main() {
    let args = parseArgs(process.argv.slice(2));
    if (args.help) { console.log(usage()); process.exit(0); }
    if (!args.config) {
        console.error('ERROR: --config is required.\n');
        console.log(usage());
        process.exit(1);
    }

    let candidates = loadCandidates(args.config);
    printBanner(args, candidates);
    runSafetyGuards(args, candidates.length);

    if (args.dryRun) {
        printDryRunSummary(candidates);
        process.exit(0);
    }

    if (!args.retain) {
        console.error('ERROR: This tool requires --retain in commit mode.');
        process.exit(1);
    }

    let dbConfig = getDbConfig();
    console.log('\n── Database Connection ──');
    console.log('  Host: ' + dbConfig.host + '  DB: ' + dbConfig.database);
    if (!guardLocalDb(dbConfig.host)) process.exit(1);

    let Pg;
    try { Pg = require('pg'); } catch (e) { fail('pg module load', e.message); process.exit(1); }

    let pool = new Pg.Pool({
        host: dbConfig.host, port: dbConfig.port,
        database: dbConfig.database, user: dbConfig.user, password: dbConfig.password,
        max: 3, connectionTimeoutMillis: 10000,
    });

    let client;
    try {
        client = await pool.connect();
        ok('DB connected', dbConfig.host + ':' + dbConfig.port + '/' + dbConfig.database);
        let allOk = await processBatchMatches(client, candidates, args.dataVersion);
        if (!allOk) { client.release(); await pool.end(); process.exit(1); }
    } catch (err) {
        fail('Batch operation', err.message);
        if (client) client.release();
        await pool.end();
        process.exit(1);
    }

    client.release();
    await pool.end();

    printConsolidatedReport(args.dataVersion);
    console.log('\n' + '='.repeat(70));
    if (errorCount === 0) {
        console.log('ALL 3 MATCHES RETAINED SUCCESSFULLY.');
        console.log('Rows are RETAINED in local/dev DB. NOT auto-cleaned up.');
        console.log('3 live fetches performed. 3 rows written.');
    } else {
        console.error('FAILED: ' + errorCount + ' check(s) did not pass.');
    }
    console.log('='.repeat(70));
    process.exit(errorCount === 0 ? 0 : 1);
}

main().catch(function (err) {
    console.error('FATAL:', err.message || err);
    process.exit(1);
});
