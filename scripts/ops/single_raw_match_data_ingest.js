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

const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

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
        '  node scripts/ops/single_raw_match_data_ingest.js \\',
        '    --fixture <path> \\',
        '    --match-id <id> \\',
        '    [--data-version <version>] \\',
        '    [--commit] [--dry-run] [--help]',
        '',
        'SAFETY: Dry-run is the DEFAULT.',
        '        DB write REQUIRES: CONFIRM_LOCAL_DB_WRITE=1 AND --commit.',
    ].join('\n');
}

function parseArgs(argv) {
    let args = { fixture: null, matchId: null, dataVersion: 'fp_v2_smoke',
        commit: false, dryRun: true, help: false };
    for (let i = 0; i < argv.length; i++) {
        let t = argv[i];
        if (t === '--fixture') { args.fixture = argv[++i]; }
        else if (t === '--match-id') { args.matchId = argv[++i]; }
        else if (t === '--data-version') { args.dataVersion = argv[++i]; }
        else if (t === '--commit') { args.commit = true; args.dryRun = false; }
        else if (t === '--dry-run') { args.dryRun = true; args.commit = false; }
        else if (t === '--help' || t === '-h') { args.help = true; }
        else { throw new Error('Unknown argument: ' + t); }
    }
    return args;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Safety Guards
// ═══════════════════════════════════════════════════════════════════════════════

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

function guardNoNetwork(fixturePath) {
    if (/^https?:\/\//i.test(fixturePath)) {
        console.error('BLOCKED (G3): fixture path looks like a URL. Only local files allowed.');
        return false;
    }
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

function runSafetyGuards(args) {
    console.log('\n── Safety Guards ──');
    if (!guardNoNetwork(args.fixture)) process.exit(1);
    console.log('  [G3 PASS] Fixture is a local path (no network).');
    if (!guardDataVersionLength(args.dataVersion)) process.exit(1);
    if (!guardConfirmLocalDbWrite(args.commit)) process.exit(1);

    // DB Write Safety Gate — unified guard (complements existing G1-G9)
    if (args.commit) {
        try {
            assertDbWriteAllowed({
                script: 'single_raw_match_data_ingest.js',
                tables: ['raw_match_data'],
                operations: ['INSERT', 'UPDATE'],
            });
            console.log('  [Unified Guard PASS] All DB write safety gates satisfied.');
        } catch (err) {
            console.error('[Unified Guard BLOCKED]', err.message);
            process.exit(1);
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// HTML Extraction
// ═══════════════════════════════════════════════════════════════════════════════

function extractNextData(html) {
    let re = /<script[^>]*id="__NEXT_DATA__"[^>]*type="application\/json"[^>]*>([^<]+)<\/script>/;
    let m = html.match(re);
    if (!m) return null;
    try { return JSON.parse(m[1]); } catch (e) { return { _parse_error: e.message }; }
}

function extractPageProps(nextData) {
    if (!nextData || !nextData.props) return null;
    return nextData.props.pageProps || null;
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
    console.log('='.repeat(70));
    console.log('Single Raw Fixture Ingestion Smoke Tool');
    console.log('='.repeat(70));
    console.log('Fixture:       ' + args.fixture);
    console.log('Match ID:      ' + args.matchId);
    console.log('Data Version:  ' + args.dataVersion);
    console.log('Mode:          ' + (args.commit ? 'COMMIT' : 'DRY-RUN'));
    console.log('='.repeat(70));
}

// ═══════════════════════════════════════════════════════════════════════════════
// Fixture processing — returns {html, nextData, pageProps}, exits on failure
// ═══════════════════════════════════════════════════════════════════════════════

function processFixture(fixturePath) {
    console.log('\n── Fixture Processing ──');

    let resolved = path.resolve(process.cwd(), fixturePath);
    if (!fs.existsSync(resolved)) {
        fail('fixture not found', resolved);
        process.exit(1);
    }
    ok('fixture exists', resolved);

    let html = fs.readFileSync(resolved, 'utf8');
    ok('HTML read', html.length + ' bytes');

    let nextData = extractNextData(html);
    if (!nextData) { fail('__NEXT_DATA__ extraction', 'not found in HTML (G7)'); process.exit(1); }
    if (nextData._parse_error) { fail('__NEXT_DATA__ parse', nextData._parse_error + ' (G7)'); process.exit(1); }
    ok('__NEXT_DATA__ extracted', 'keys: ' + Object.keys(nextData).join(', '));

    let pageProps = extractPageProps(nextData);
    if (!pageProps) { fail('pageProps extraction', 'not found (G7)'); process.exit(1); }
    ok('pageProps extracted', 'keys: ' + Object.keys(pageProps).join(', '));

    return { html: html, nextData: nextData, pageProps: pageProps };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Payload builder — returns {externalId, rawDataJson, dataHash}, exits on fail
// ═══════════════════════════════════════════════════════════════════════════════

function buildPayload(args, pageProps, htmlLength) {
    let externalId = args.matchId.split('_').pop();

    let rawData = {
        matchId: externalId,
        pageProps: pageProps,
        _meta: {
            source: 'fotmob', route: 'html_hydration',
            match_id: args.matchId, external_id: externalId,
            data_version: args.dataVersion,
            hash_strategy: 'stable_pageprops_payload_v1',
            body_byte_length: htmlLength,
            fixture_path: args.fixture,
            generated_at: new Date().toISOString(),
            smoke_test: true,
        },
    };

    let rawDataJson = JSON.stringify(rawData);
    let dataHash = crypto.createHash('sha256').update(rawDataJson).digest('hex');
    ok('payload built', rawDataJson.length + ' bytes, hash=' + dataHash.substring(0, 16) + '...');

    // Pre-flight CHECK constraint validation
    let ckFormat = /^\d+_\d{8}_\d+$/.test(args.matchId) || /^\d+$/.test(args.matchId);
    if (!ckFormat) fail('CHECK match_id_format', args.matchId);
    if (!rawData.matchId) fail('CHECK raw_data_has_match_id');
    if (rawDataJson.length <= 2) fail('CHECK raw_data_not_empty');

    if (errorCount > 0) {
        console.error('\nPre-flight CHECK constraint validation FAILED. Aborting.');
        process.exit(1);
    }
    ok('CHECK constraints pre-flight', 'all passed');

    return { externalId: externalId, rawDataJson: rawDataJson, dataHash: dataHash };
}

// ═══════════════════════════════════════════════════════════════════════════════
// Dry-run summary — prints and exits
// ═══════════════════════════════════════════════════════════════════════════════

function printDryRunSummary(args, externalId, rawDataJson, dataHash) {
    console.log('\n── Dry-Run Summary ──');
    console.log('  Would UPSERT → raw_match_data');
    console.log('    match_id     = ' + args.matchId);
    console.log('    external_id  = ' + externalId);
    console.log('    data_version = ' + args.dataVersion);
    console.log('    data_hash    = ' + dataHash);
    console.log('    raw_data     = ' + rawDataJson.length + ' bytes JSONB');
    console.log('');
    console.log('  To write to DB:  CONFIRM_LOCAL_DB_WRITE=1 ... --commit');
    console.log('='.repeat(70));
    console.log('DRY-RUN COMPLETE. No DB connection opened. No writes.');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Verify a single read-back row against expected values
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
// Run idempotency check: re-UPSERT, verify single row, same id, same hash
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
// Run cleanup: DELETE test row, then verify 0 rows remain
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
// Main DB write path: connect → FK → UPSERT → read-back → idempotency → cleanup
// ═══════════════════════════════════════════════════════════════════════════════

async function executeDbWrite(dbConfig, args, payload) {
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
    let upsertParams = [args.matchId, payload.externalId, payload.rawDataJson, args.dataVersion, payload.dataHash];

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
        else { ok('row exists', 'id=' + sel.rows[0].id); verifyReadback(sel.rows[0], args.matchId, args.dataVersion, payload.dataHash, payload.externalId); }

        // Idempotency
        await verifyIdempotency(client, upsertParams, insertedId, payload.dataHash);

        // Cleanup
        await runCleanup(client, args.matchId, args.dataVersion);

    } catch (err) {
        fail('DB operation', err.message);
        if (client && insertedId) {
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
// Final verdict
// ═══════════════════════════════════════════════════════════════════════════════

function printVerdict() {
    console.log('\n' + '='.repeat(70));
    if (errorCount === 0) {
        console.log('ALL CHECKS PASSED. Smoke test SUCCESS.');
        console.log('The test row has been cleaned up from the database.');
    } else {
        console.error('FAILED: ' + errorCount + ' check(s) did not pass.');
    }
    console.log('='.repeat(70));
    process.exit(errorCount === 0 ? 0 : 1);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main — orchestrate the smoke test
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

async function main() {
    let args = parseArgs(process.argv.slice(2));
    if (args.help) { console.log(usage()); process.exit(0); }
    if (!args.fixture || !args.matchId) { console.error('ERROR: --fixture and --match-id are required.\n'); console.log(usage()); process.exit(1); }

    printBanner(args);
    runSafetyGuards(args);

    let fixture = processFixture(args.fixture);
    let payload = buildPayload(args, fixture.pageProps, fixture.html.length);

    if (args.dryRun) {
        printDryRunSummary(args, payload.externalId, payload.rawDataJson, payload.dataHash);
        process.exit(0);
    }

    let dbConfig = getDbConfig();
    await executeDbWrite(dbConfig, args, payload);
    printVerdict();
}

main().catch(function (err) {
    console.error('FATAL:', err.message || err);
    process.exit(1);
});
