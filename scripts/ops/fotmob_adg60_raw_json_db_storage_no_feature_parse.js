#!/usr/bin/env node
/**
 * @fileoverview Ingests FotMob ADG60 raw __NEXT_DATA__/pageProps JSON into PostgreSQL jsonb.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-RAW-JSON-DB-STORAGE-NO-FEATURE-PARSE
 *
 * Reads gitignored local raw payloads, extracts JSON, stores in fotmob_raw_match_payloads.
 * Default: dry-run. Execute: --execute-db-storage
 * No feature parsing. No raw_match_data insert. raw_write_ready remains false.
 */

import { readFileSync, existsSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import pg from 'pg';
import { assertDbWriteAllowed } from './helpers/db_write_guard.js';

const { Pool } = pg;

const DEFAULT_CAPTURE_MANIFEST = 'docs/_manifests/fotmob_raw_payload_capture_adg60_manifest.json';
const DEFAULT_OUTPUT_MANIFEST = 'docs/_manifests/fotmob_raw_json_db_storage_adg60_manifest.json';
const SAFE_PREFIX = 'data/raw/fotmob/';
const SOURCE = 'fotmob';
const STORAGE_VERSION = 'adg60_raw_json_v1';
const INGESTION_RUN_ID = `adg60_raw_json_v1_${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}`;

function parseStrArg(args, flag) {
  const eq = args.findIndex((a) => a.startsWith(`${flag}=`));
  if (eq >= 0) return args[eq].split('=')[1];
  const fi = args.indexOf(flag);
  return fi >= 0 && fi + 1 < args.length ? args[fi + 1] : null;
}

function parseIndices(args) {
  let s = null;
  const ei = args.findIndex((a) => a.startsWith('--target-indices='));
  if (ei >= 0) s = args[ei].split('=')[1];
  else { const fi = args.indexOf('--target-indices'); if (fi >= 0 && fi + 1 < args.length) s = args[fi + 1]; }
  return s ? s.split(',').map(Number) : [];
}

function extractNextDataText(html) {
  const marker = '__NEXT_DATA__';
  const idx = html.indexOf(marker);
  if (idx === -1) return null;
  const ss = html.indexOf('>', idx);
  const se = html.indexOf('</script>', idx);
  if (ss === -1 || se === -1) return null;
  const text = html.substring(ss + 1, se).trim();
  if (!text) return null;
  const h = createHash('sha256'); h.update(text, 'utf-8');
  return { text, sha256: h.digest('hex') };
}

function extractPageProps(parsed) {
  let pp = null;
  if (parsed.props && parsed.props.pageProps) pp = parsed.props.pageProps;
  else if (parsed.pageProps) pp = parsed.pageProps;
  if (!pp) return { found: false, json: null, sha256: null };
  const s = JSON.stringify(pp);
  const h = createHash('sha256'); h.update(s, 'utf-8');
  return { found: true, json: pp, sha256: h.digest('hex') };
}

function checkGitSafety(fp) {
  if (!fp || !fp.startsWith(SAFE_PREFIX)) return { safe: false, reason: `not under ${SAFE_PREFIX}` };
  if (!existsSync(fp)) return { safe: false, reason: 'file missing' };
  return { safe: true };
}

function getDBConfig() {
  return {
    host: process.env.DEV_DB_HOST || process.env.DB_HOST || 'db',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass',
  };
}

async function processEntry(entry, executeDB, dbPool, runId) {
  const { target_index, target_match_id, expected_home, expected_away, expected_date,
    competition, raw_payload_relative_path, sha256, byte_size, content_type, captured_at } = entry;
  const row = {
    target_index, match_id: target_match_id, expected_home, expected_away,
    expected_date, competition, season: '2025-26',
    raw_payload_file_path: raw_payload_relative_path,
    raw_payload_sha256: sha256, raw_payload_byte_size: byte_size,
    inserted_or_existing: null, db_row_id: null,
    next_data_sha256: null, page_props_sha256: null, error: null,
  };

  const gc = checkGitSafety(raw_payload_relative_path);
  if (!gc.safe) { row.error = gc.reason; row.inserted_or_existing = 'skipped'; return row; }

  const html = readFileSync(raw_payload_relative_path, 'utf-8');
  const nd = extractNextDataText(html);
  if (!nd) { row.error = 'no __NEXT_DATA__'; row.inserted_or_existing = 'skipped'; return row; }

  let parsed;
  try { parsed = JSON.parse(nd.text); } catch { row.error = 'JSON parse failed'; row.inserted_or_existing = 'skipped'; return row; }

  const pp = extractPageProps(parsed);
  if (!pp.found) { row.error = 'no pageProps'; row.inserted_or_existing = 'skipped'; return row; }

  row.next_data_sha256 = nd.sha256;
  row.page_props_sha256 = pp.sha256;

  if (!executeDB) { row.inserted_or_existing = 'dry_run_planned'; return row; }

  assertDbWriteAllowed({
    script: 'fotmob_adg60_raw_json_db_storage_no_feature_parse.js',
    tables: ['fotmob_raw_match_payloads'],
    operations: ['INSERT'],
  });

  try {
    const res = await dbPool.query(
      `INSERT INTO fotmob_raw_match_payloads (source,competition,season,match_id,target_index,expected_home,expected_away,expected_date,raw_payload_file_path,raw_payload_sha256,raw_payload_byte_size,raw_payload_content_type,captured_at,next_data_found,next_data_sha256,next_data_json,page_props_found,page_props_sha256,page_props_json,json_storage_version,ingestion_run_id) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16::jsonb,$17,$18,$19::jsonb,$20,$21) ON CONFLICT (source,match_id,raw_payload_sha256) DO UPDATE SET ingested_at=NOW() RETURNING id, (xmax=0) AS was_inserted`,
      [SOURCE, competition, '2025-26', target_match_id, target_index, expected_home, expected_away, expected_date, raw_payload_relative_path, sha256, byte_size, content_type, captured_at, true, nd.sha256, nd.text, pp.found, pp.sha256, JSON.stringify(pp.json), STORAGE_VERSION, runId]
    );
    if (res.rows.length > 0) {
      row.db_row_id = res.rows[0].id;
      row.inserted_or_existing = res.rows[0].was_inserted ? 'inserted' : 'existing';
    }
  } catch (e) { row.error = `db: ${e.message}`; row.inserted_or_existing = 'failed'; }
  return row;
}

async function main() {
  const args = process.argv.slice(2);
  const executeDB = args.includes('--execute-db-storage');
  const indices = parseIndices(args);
  const capPath = parseStrArg(args, '--input-capture-manifest') || DEFAULT_CAPTURE_MANIFEST;
  const outPath = parseStrArg(args, '--output-manifest') || DEFAULT_OUTPUT_MANIFEST;
  const runId = parseStrArg(args, '--ingestion-run-id') || INGESTION_RUN_ID;

  const cap = JSON.parse(readFileSync(capPath, 'utf-8'));
  const entries = cap.per_target_results.filter((r) => r.file_saved);

  const results = {
    phase: 'ADG60-RAW-JSON-DB-STORAGE-NO-FEATURE-PARSE',
    ingestion_run_id: runId, generated_at: new Date().toISOString(), dry_run: !executeDB,
    per_target_rows: [], aggregate: { planned_count: entries.length, inserted_count: 0, existing_count: 0, skipped_count: 0, failed_count: 0, db_row_count: 0, distinct_match_id_count: 0, json_present_count: 0 },
  };

  let dbPool = null;
  if (executeDB) {
    const cfg = getDBConfig();
    dbPool = new Pool({ ...cfg, max: 2 });
    try { await dbPool.query('SELECT 1'); } catch (e) { console.error(`DB connect failed: ${e.message}`); process.exit(1); }
  }

  for (const entry of entries) {
    const row = await processEntry(entry, executeDB, dbPool, runId);
    results.per_target_rows.push(row);
    if (row.inserted_or_existing === 'inserted') results.aggregate.inserted_count++;
    else if (row.inserted_or_existing === 'existing') results.aggregate.existing_count++;
    else if (row.inserted_or_existing === 'failed') results.aggregate.failed_count++;
    else if (row.inserted_or_existing === 'skipped') results.aggregate.skipped_count++;
    else if (row.inserted_or_existing === 'dry_run_planned') results.aggregate.inserted_count++;
  }

  if (executeDB && dbPool) {
    const { rows: cr } = await dbPool.query("SELECT COUNT(*) as c FROM fotmob_raw_match_payloads WHERE source='fotmob'");
    const { rows: dr } = await dbPool.query("SELECT COUNT(DISTINCT match_id) as c FROM fotmob_raw_match_payloads WHERE source='fotmob'");
    const { rows: jr } = await dbPool.query("SELECT COUNT(*) as c FROM fotmob_raw_match_payloads WHERE source='fotmob' AND next_data_json IS NOT NULL");
    results.aggregate.db_row_count = parseInt(cr[0].c);
    results.aggregate.distinct_match_id_count = parseInt(dr[0].c);
    results.aggregate.json_present_count = parseInt(jr[0].c);
    await dbPool.end();
  }

  const manifestOutput = { ...results, safety: { feature_parse_performed: false, raw_match_data_insert_performed: false, l3_features_write_performed: false, match_features_training_write_performed: false, predictions_write_performed: false, raw_write_ready_marked: false, production_db_write_performed: false, body_committed_to_git: false } };
  writeFileSync(outPath, JSON.stringify(manifestOutput, null, 2));

  console.error(`\n=== Raw JSON DB Storage Summary ===`);
  console.error(`Planned: ${results.aggregate.planned_count} | Inserted: ${results.aggregate.inserted_count} | Existing: ${results.aggregate.existing_count} | Failed: ${results.aggregate.failed_count}`);
  if (executeDB) console.error(`DB rows: ${results.aggregate.db_row_count} | Distinct matches: ${results.aggregate.distinct_match_id_count} | JSON: ${results.aggregate.json_present_count}`);
  console.error(`Dry-run: ${!executeDB}`);
  console.error('Feature parse: false | raw_match_data: false | raw_write_ready: false');
  console.log(JSON.stringify(manifestOutput, null, 2));
  return 0;
}

await main();
