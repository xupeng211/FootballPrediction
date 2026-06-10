#!/usr/bin/env node
/**
 * FotMob retained raw data quality audit.
 *
 * lifecycle: permanent / audit-tool
 *
 * READ-ONLY audit of all raw_match_data rows with data_version='fotmob_live_v1'.
 * Checks row count, field completeness, JSON parseability, inner matchId alignment,
 * structural consistency, and hash stability.  No INSERT/UPDATE/DELETE/UPSERT.
 *
 * SAFETY:
 *   - Production DB detection (hard-block)
 *   - READ-ONLY: only SELECT statements
 *   - No live fetch, no network
 *   - Does NOT print full raw_data / pageProps
 *
 * Usage:
 *   make data-raw-fotmob-retained-quality-audit
 */

'use strict';

const PRODUCTION_DB_HOST_PATTERNS = [
    /rds\.amazonaws\.com/i, /\.rds\.amazonaws/i, /cloudsql\.google/i,
    /\.supabase\./i, /\.supabase\.co/i, /\.vercel/i, /\.fly\.dev/i,
    /\.railway\.app/i, /\.render\.com/i, /\.heroku/i, /prod/i, /production/i,
];

const LOCAL_DB_HOST_WHITELIST = [
    '127.0.0.1', 'localhost', 'db', 'football_db', 'football_db_dev',
];

const AUDIT_VERSION = 'fotmob_live_v1';
const EXPECTED_MATCH_IDS = [
    '53_20252026_4830507',
    '53_20252026_4830466',
    '53_20252026_4830461',
    '53_20252026_4830464',
];

let errorCount = 0;
let warnCount = 0;

function ok(label, detail) {
    console.log('  [OK] ' + label + (detail ? ': ' + detail : ''));
}

function warn(label, detail) {
    console.log('  [WARN] ' + label + (detail ? ': ' + detail : ''));
    warnCount += 1;
}

function fail(label, detail) {
    console.error('  [FAIL] ' + label + (detail ? ': ' + detail : ''));
    errorCount += 1;
}

function guardLocalDb(host) {
    let h = String(host || '').trim().toLowerCase();
    for (let pat of PRODUCTION_DB_HOST_PATTERNS) {
        if (pat.test(h)) {
            console.error('BLOCKED: DB host "' + host + '" matches production pattern.');
            process.exit(1);
        }
    }
    if (!LOCAL_DB_HOST_WHITELIST.some(a => h === a.toLowerCase())) {
        console.error('BLOCKED: DB host "' + host + '" not in local/dev whitelist.');
        process.exit(1);
    }
    ok('local DB guard', h);
}

function isValidSha256(hash) {
    return /^[a-f0-9]{64}$/.test(hash);
}

function auditMetadataFields(row, tag) {
    let metaOk = true;
    if (row.data_version === AUDIT_VERSION) ok('data_version', tag);
    else { fail('data_version', tag + ' got ' + row.data_version); metaOk = false; }

    if (row.external_id && /^\d+$/.test(String(row.external_id))) {
        ok('external_id numeric', tag + ' = ' + row.external_id);
    } else { fail('external_id numeric', tag); metaOk = false; }

    if (row.data_hash && isValidSha256(row.data_hash)) {
        ok('data_hash SHA256', tag + ' ' + row.data_hash.substring(0, 16) + '...');
    } else { fail('data_hash SHA256', tag); metaOk = false; }

    let bytes = parseInt(row.json_bytes, 10);
    if (bytes > 10000) ok('json_bytes', tag + ' ' + bytes.toLocaleString());
    else { fail('json_bytes', tag + ' got ' + bytes); metaOk = false; }

    if (row.collected_at) ok('collected_at', tag + ' ' + row.collected_at);
    else { fail('collected_at', tag); metaOk = false; }

    return metaOk;
}

function parseRowJson(row, tag) {
    try { return JSON.parse(row.raw_data_text); }
    catch (e) { fail('raw_data JSON parse', tag + ' ' + e.message); return null; }
}

function auditInnerMatchId(parsed, externalId, tag) {
    let innerId = parsed && parsed.matchId ? String(parsed.matchId) : null;
    let extId = String(externalId || '');
    if (innerId === extId) { ok('inner matchId', tag + ' = ' + innerId); return true; }
    fail('inner matchId', tag + ' expected ' + extId + ' got ' + innerId);
    return false;
}

function auditCGHTriple(parsed, tag) {
    let result = { content: parsed && parsed.content, general: parsed && parsed.general, header: parsed && parsed.header };
    ['content', 'general', 'header'].forEach(function (key) {
        let val = result[key];
        if (val && typeof val === 'object') { ok(key + ' keys', tag + ' ' + Object.keys(val).length + ' keys'); }
        else { warn(key + ' structure', tag + ' missing'); }
    });
    return result;
}

function auditContentPayload(row, tag) {
    let parsed = parseRowJson(row, tag);
    if (!parsed) { return null; }
    ok('raw_data JSON parse', tag);

    auditInnerMatchId(parsed, row.external_id, tag);

    // Live-retained rows use {matchId, content, general, header} format;
    // fixture rows use {matchId, pageProps}. Accept either.
    let hasPP = parsed && parsed.pageProps && typeof parsed.pageProps === 'object';
    let hasCGH = parsed && parsed.content && parsed.general && parsed.header;
    if (hasPP || hasCGH) {
        let fmt = hasCGH ? 'live (content+general+header)' : 'fixture (pageProps)';
        ok('payload format', tag + ' ' + fmt);
    } else { fail('payload format', tag + ' no recognized structure'); }

    let hasMeta = parsed && parsed._meta && typeof parsed._meta === 'object';
    if (hasMeta) { ok('_meta present', tag); } else { warn('_meta missing', tag); }

    let cgh = auditCGHTriple(parsed, tag);

    return { parsed, hasPP, hasMeta, content: cgh.content, general: cgh.general, header: cgh.header };
}

function auditSingleRow(row, idx) {
    let tag = '[' + (idx + 1) + '] ' + (row.match_id || '?');
    if (row.match_id === EXPECTED_MATCH_IDS[idx]) ok('match_id', tag);
    else fail('match_id', tag + ' expected ' + EXPECTED_MATCH_IDS[idx] + ' got ' + row.match_id);

    let metaOk = auditMetadataFields(row, tag);
    let payload = auditContentPayload(row, tag);
    if (!metaOk || !payload) return null;

    let bytes = parseInt(row.json_bytes, 10);
    return { parsed: payload.parsed, content: payload.content, general: payload.general, header: payload.header, bytes };
}

function auditTopLevelKeys(structs) {
    let refKeys = Object.keys(structs[0].parsed || {}).sort();
    for (let i = 1; i < structs.length; i++) {
        let curKeys = Object.keys(structs[i].parsed || {}).sort();
        let onlyRef = refKeys.filter(k => !curKeys.includes(k));
        let onlyCur = curKeys.filter(k => !refKeys.includes(k));
        if (onlyRef.length === 0 && onlyCur.length === 0) ok('top-level keys match', 'row 1 vs row ' + (i + 1));
        else { if (onlyRef.length) warn('keys missing in row ' + (i + 1), onlyRef.join(', ')); if (onlyCur.length) warn('keys extra in row ' + (i + 1), onlyCur.join(', ')); }
    }
}

function auditPagePropsKeys(structs) {
    let pp0 = Object.keys(structs[0].parsed?.pageProps || {}).sort();
    for (let i = 1; i < structs.length; i++) {
        let ppI = Object.keys(structs[i].parsed?.pageProps || {}).sort();
        let missing = pp0.filter(k => !ppI.includes(k));
        let extra = ppI.filter(k => !pp0.includes(k));
        if (missing.length === 0 && extra.length === 0) ok('pageProps keys match', 'row 1 vs row ' + (i + 1));
        else { if (missing.length) warn('pageProps keys missing in row ' + (i + 1), missing.join(', ')); if (extra.length) warn('pageProps keys extra in row ' + (i + 1), extra.join(', ')); }
    }
}

function auditCGHConsistency(structs) {
    if (structs.every(s => s.content)) ok('all rows have content'); else warn('content not uniform');
    if (structs.every(s => s.general)) ok('all rows have general'); else warn('general not uniform');
    if (structs.every(s => s.header)) ok('all rows have header'); else warn('header not uniform');
}

function auditRowCount(client, expected) {
    return client.query(
        "SELECT COUNT(*)::int AS cnt FROM raw_match_data WHERE data_version = $1",
        [AUDIT_VERSION]
    ).then(function (r) {
        let total = r.rows[0].cnt;
        if (total === expected) ok('row count', total + ' = ' + expected);
        else fail('row count', 'expected ' + expected + ' got ' + total);
        return total;
    });
}

function auditAllRows(client) {
    return client.query(
        `SELECT id, match_id, external_id, data_version, data_hash,
                collected_at, length(raw_data::text) AS json_bytes,
                raw_data::text AS raw_data_text
         FROM raw_match_data WHERE data_version = $1 ORDER BY id`,
        [AUDIT_VERSION]
    );
}

function auditCoverage(rows) {
    let foundIds = new Set(rows.map(r => r.match_id));
    EXPECTED_MATCH_IDS.forEach(function (mid) {
        if (foundIds.has(mid)) ok('coverage', mid);
        else fail('coverage missing', mid);
    });
}

function auditHashUniqueness(rows) {
    let hashes = rows.map(r => r.data_hash);
    let uniqueHashes = new Set(hashes);
    if (uniqueHashes.size === hashes.length) ok('all data_hash values unique', uniqueHashes.size + '/' + hashes.length);
    else warn('duplicate data_hash detected', uniqueHashes.size + ' unique / ' + hashes.length + ' total');
}

function auditSizeDistribution(rows) {
    let sizes = rows.map(r => parseInt(r.json_bytes, 10));
    let minS = Math.min(...sizes), maxS = Math.max(...sizes);
    let avgS = Math.round(sizes.reduce((a, b) => a + b, 0) / sizes.length);
    console.log('  min=' + minS.toLocaleString() + '  max=' + maxS.toLocaleString() +
        '  avg=' + avgS.toLocaleString() + '  range=' + (maxS - minS).toLocaleString());
    if (minS > 10000 && maxS < 10000000) ok('size range reasonable');
    else warn('size range unusual');
}

function printVerdict() {
    console.log('\n' + '='.repeat(70));
    if (errorCount === 0 && warnCount === 0) {
        console.log('AUDIT PASSED. All ' + EXPECTED_MATCH_IDS.length + ' retained rows are clean and consistent.');
        console.log('0 errors, 0 warnings.');
    } else if (errorCount === 0) {
        console.log('AUDIT PASSED with ' + warnCount + ' warning(s). 0 errors.');
    } else {
        console.log('AUDIT FAILED: ' + errorCount + ' error(s), ' + warnCount + ' warning(s).');
    }
    console.log('='.repeat(70));
}

async function runAudit() {
    console.log('='.repeat(70));
    console.log('FotMob Retained Raw Data Quality Audit');
    console.log('='.repeat(70));
    console.log('Audit version:   ' + AUDIT_VERSION);
    console.log('Expected rows:   ' + EXPECTED_MATCH_IDS.length);
    console.log('='.repeat(70));

    let dbConfig = {
        host: process.env.PGHOST || 'db',
        port: parseInt(process.env.PGPORT || '5432', 10),
        database: process.env.PGDATABASE || 'football_db',
        user: process.env.PGUSER || 'football_user',
        password: process.env.PGPASSWORD || '',
    };

    console.log('\n── Safety ──');
    guardLocalDb(dbConfig.host);

    console.log('\n── DB Connection ──');
    console.log('  Host: ' + dbConfig.host + '  DB: ' + dbConfig.database);

    let Pg;
    try { Pg = require('pg'); } catch (e) { fail('pg module', e.message); process.exit(1); }

    let pool = new Pg.Pool({
        host: dbConfig.host, port: dbConfig.port,
        database: dbConfig.database, user: dbConfig.user, password: dbConfig.password,
        max: 2, connectionTimeoutMillis: 10000,
    });

    let client;
    try {
        client = await pool.connect();
        ok('DB connected');

        console.log('\n── Row Count ──');
        await auditRowCount(client, EXPECTED_MATCH_IDS.length);

        console.log('\n── Per-Row Audit ──');
        let selRes = await auditAllRows(client);
        let structs = [];
        for (let i = 0; i < selRes.rows.length; i++) {
            console.log('\n  ── Row ' + (i + 1) + ': ' + selRes.rows[i].match_id + ' ──');
            let s = auditSingleRow(selRes.rows[i], i);
            if (s) structs.push(s);
        }

        console.log('\n── Coverage Check ──');
        auditCoverage(selRes.rows);

        if (structs.length >= 2) {
            console.log('\n── Cross-Row Structural Consistency ──');
            auditTopLevelKeys(structs);
            auditPagePropsKeys(structs);
            auditCGHConsistency(structs);
        } else {
            warn('structural consistency', 'need >= 2 rows');
        }

        console.log('\n── Hash Uniqueness ──');
        auditHashUniqueness(selRes.rows);

        console.log('\n── Size Distribution ──');
        auditSizeDistribution(selRes.rows);

        console.log('\n── Write Audit ──');
        ok('zero INSERT/UPDATE/DELETE/UPSERT executed');
        ok('READ-ONLY audit complete');

    } catch (err) {
        fail('audit error', err.message);
        if (client) client.release();
        await pool.end();
        process.exit(1);
    }

    client.release();
    await pool.end();
    printVerdict();
    process.exit(errorCount === 0 ? 0 : 1);
}

runAudit().catch(function (err) {
    console.error('FATAL:', err.message || err);
    process.exit(1);
});
