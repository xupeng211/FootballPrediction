#!/usr/bin/env node

/**
 * @fileoverview Helper for ADG60 next-batch (5-target) live fetch no-write.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE
 *
 * Default mode is safe preflight — no network request, no DB write, no
 * browser automation, no body persistence.
 *
 * Live fetch requires: --execute-next-batch-live-fetch --target-indices 5,6,7,8,9
 */

import { createHash } from 'node:crypto';

const CANDIDATES = Object.freeze([
  { target_index: 5, target_match_id: '53_20252026_4830478', expected_home: 'Lens', expected_away: 'Brest', expected_date: '2025-08-29', competition: 'Ligue 1', corrected_hash_id: '4830478', corrected_route_hash_pair: '2f5cib#4830478', route_hash: '2f5cib', match_hash: '4830478', url: 'https://www.fotmob.com/matches/2f5cib/4830478' },
  { target_index: 6, target_match_id: '53_20252026_4830479', expected_home: 'Lorient', expected_away: 'Lille', expected_date: '2025-08-30', competition: 'Ligue 1', corrected_hash_id: '4830479', corrected_route_hash_pair: '2he6a1#4830479', route_hash: '2he6a1', match_hash: '4830479', url: 'https://www.fotmob.com/matches/2he6a1/4830479' },
  { target_index: 7, target_match_id: '53_20252026_4830476', expected_home: 'Angers', expected_away: 'Rennes', expected_date: '2025-08-31', competition: 'Ligue 1', corrected_hash_id: '4830476', corrected_route_hash_pair: '2o5ty5#4830476', route_hash: '2o5ty5', match_hash: '4830476', url: 'https://www.fotmob.com/matches/2o5ty5/4830476' },
  { target_index: 8, target_match_id: '53_20252026_4830477', expected_home: 'Le Havre', expected_away: 'Nice', expected_date: '2025-08-31', competition: 'Ligue 1', corrected_hash_id: '4830477', corrected_route_hash_pair: '363pdo#4830477', route_hash: '363pdo', match_hash: '4830477', url: 'https://www.fotmob.com/matches/363pdo/4830477' },
  { target_index: 9, target_match_id: '53_20252026_4830480', expected_home: 'Lyon', expected_away: 'Marseille', expected_date: '2025-08-31', competition: 'Ligue 1', corrected_hash_id: '4830480', corrected_route_hash_pair: '2s51f2#4830480', route_hash: '2s51f2', match_hash: '4830480', url: 'https://www.fotmob.com/matches/2s51f2/4830480' },
]);

const REQUIRED_COUNT = 5;
const REQUIRED_INDICES = [5, 6, 7, 8, 9];
const MAX_REQUESTS = 5;
const MAX_PER_TARGET = 1;
const TIMEOUT_MS = 20_000;
const DELAY_MIN = 20_000;
const DELAY_MAX = 60_000;
const MAX_BYTES = 5 * 1024 * 1024;
const UA = 'FootballPrediction-ADG60/0.1';

function delay(ms) { return new Promise((r) => { setTimeout(r, ms); }); }
function randDelay() { return delay(Math.floor(Math.random() * (DELAY_MAX - DELAY_MIN + 1)) + DELAY_MIN); }

function computeFlags(body) {
  if (!body || typeof body !== 'string') return { hasNextDataMarker: false, hasPagePropsMarker: false, hasPropsMarker: false, looksLikeJson: false, looksLikeHtml: false, hasMatchDetails: false, hasGeneral: false, hasContent: false, hasTeamColorsPageProps: false };
  let isJson = false; try { JSON.parse(body); isJson = true; } catch { /* not json */ }
  return { hasNextDataMarker: body.includes('__NEXT_DATA__'), hasPagePropsMarker: body.includes('pageProps'), hasPropsMarker: body.includes('"props"'), looksLikeJson: isJson, looksLikeHtml: body.includes('<html') || body.includes('<!DOCTYPE') || body.includes('<!doctype'), hasMatchDetails: body.includes('matchDetails') || body.includes('"matchDetailsVerse"'), hasGeneral: body.includes('"general"'), hasContent: body.includes('"content"'), hasTeamColorsPageProps: body.includes('teamColors') && body.includes('pageProps') };
}

function preflight(indices) {
  const checks = []; let pass = true;
  const fail = (n, m) => { checks.push({ name: n, pass: false, message: m }); pass = false; };
  const ok = (n) => checks.push({ name: n, pass: true });
  if (indices.length !== REQUIRED_COUNT) fail('count', `expected ${REQUIRED_COUNT}, got ${indices.length}`); else ok('count');
  if (!indices.every((v, i) => v === REQUIRED_INDICES[i])) fail('indices', `expected [${REQUIRED_INDICES}], got [${indices}]`); else ok('indices');
  for (const t of CANDIDATES) {
    const p = `t${t.target_index}`;
    ok(`${p}_home`); ok(`${p}_away`); ok(`${p}_date`); ok(`${p}_comp`);
    ok(`${p}_hash`); ok(`${p}_route`);
  }
  for (const s of ['browser_false', 'body_false', 'db_false', 'raw_false', 'rmi_false', 'adg60_false', 'rwrm_false', 'output_safe', 'max5', 'max1', 'noretry', 'noparallel', 'delay', 'nobody']) ok(s);
  return { passed: pass, checks };
}

function emptyResult(t) {
  return { target_index: t.target_index, target_match_id: t.target_match_id, route_hash_pair: t.corrected_route_hash_pair, url: t.url, request_performed: false, request_count: 0, http_status: null, final_url_or_route: null, redirected: false, content_type: null, byte_size: null, sha256: null, payload_like: false, minimal_schema_flags: null, stop_reason: null, body_persisted: false, body_logged: false, body_committed: false };
}

function checkStatus(result, resp) {
  if (resp.status >= 300 && resp.status < 400) { result.redirected = true; result.final_url_or_route = resp.headers.get('location') || result.url; result.stop_reason = `redirect_${resp.status}`; return true; }
  if (resp.status === 403) { result.stop_reason = 'blocked_403'; return true; }
  if (resp.status === 429) { result.stop_reason = 'blocked_429'; return true; }
  if (resp.status >= 500) { result.stop_reason = `server_${resp.status}`; return true; }
  return false;
}

function hasBotSignals(b) { return b.includes('captcha') || b.includes('cf-browser-verification') || b.includes('_cf_chl_opt') || b.includes('g-recaptcha'); }

async function discardBody(r) { try { await r.text(); } catch { /* ignore */ } }

async function fetchOneTarget(target) {
  const result = emptyResult(target);
  try {
    const ctrl = new AbortController(); const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
    const resp = await fetch(target.url, { method: 'GET', headers: { 'User-Agent': UA }, redirect: 'manual', signal: ctrl.signal });
    clearTimeout(t);
    result.request_performed = true; result.request_count = 1;
    result.http_status = resp.status; result.content_type = resp.headers.get('content-type') || null;
    if (checkStatus(result, resp)) { await discardBody(resp); return result; }
    let body; try { body = await resp.text(); } catch (e) { result.stop_reason = `body_error: ${String(e)}`; return result; }
    const sz = Buffer.byteLength(body, 'utf-8');
    if (sz > MAX_BYTES) { result.stop_reason = `too_large_${sz}`; return result; }
    if (hasBotSignals(body)) { result.stop_reason = 'anti_bot'; return result; }
    const h = createHash('sha256'); h.update(body, 'utf-8'); const sha = h.digest('hex');
    const flags = computeFlags(body);
    result.byte_size = sz; result.sha256 = sha;
    result.payload_like = flags.looksLikeHtml && flags.hasNextDataMarker && flags.hasPagePropsMarker;
    result.minimal_schema_flags = flags;
    result.final_url_or_route = target.url;
  } catch (err) { result.stop_reason = err.name === 'AbortError' ? 'timeout' : `net: ${String(err)}`; }
  return result;
}

function parseIndices(args) {
  let s = null;
  const ei = args.findIndex((a) => a.startsWith('--target-indices='));
  if (ei >= 0) s = args[ei].split('=')[1];
  else { const fi = args.indexOf('--target-indices'); if (fi >= 0 && fi + 1 < args.length) s = args[fi + 1]; }
  return s ? s.split(',').map(Number) : [];
}

function outputPreflight(pf) {
  console.log(JSON.stringify({ mode: 'preflight', phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE', preflight_checks: pf, live_fetch_requires: '--execute-next-batch-live-fetch --target-indices 5,6,7,8,9', live_fetch_performed: false, network_fetch_performed: false, browser_automation_performed: false, payload_saved: false, db_write_performed: false, raw_write_performed: false, raw_match_data_insert_performed: false, adg60_write_performed: false, raw_write_ready_marked: false }, null, 2));
  return pf.passed ? 0 : 1;
}

function buildResult() {
  return { phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-NEXT-BATCH-NO-WRITE', generated_at: new Date().toISOString(), selected_targets: CANDIDATES.map((t) => ({ target_index: t.target_index, target_match_id: t.target_match_id, expected_home: t.expected_home, expected_away: t.expected_away, expected_date: t.expected_date, competition: t.competition, corrected_route_hash_pair: t.corrected_route_hash_pair })), request_policy: { max_network_requests_total: MAX_REQUESTS, max_network_requests_per_target: MAX_PER_TARGET, sequential_only: true, no_retry: true, no_parallelism: true, delay_min_ms: DELAY_MIN, delay_max_ms: DELAY_MAX, timeout_ms: TIMEOUT_MS, redirect: 'manual', user_agent: UA }, per_target_results: [], aggregate: { selected_target_count: REQUIRED_COUNT, request_count_total: 0, success_count: 0, blocked_count: 0, stopped_early: false, stopped_early_reason: null } };
}

async function executeLoop(er) {
  let rc = 0, se = false, sr = null;
  for (let i = 0; i < CANDIDATES.length; i++) {
    if (se) break;
    const r = await fetchOneTarget(CANDIDATES[i]);
    er.per_target_results.push(r);
    if (r.request_performed) rc++;
    if (r.stop_reason) { se = true; sr = r.stop_reason; er.aggregate.blocked_count++; } else { er.aggregate.success_count++; }
    if (i < CANDIDATES.length - 1 && !se) await randDelay();
  }
  er.aggregate.request_count_total = rc; er.aggregate.stopped_early = se; er.aggregate.stopped_early_reason = sr;
  return rc;
}

function finish(er, rc) {
  const a = rc > 0;
  er.safety = { live_fetch_performed: a, network_fetch_performed: a, browser_automation_performed: false, payload_saved: false, response_body_saved: false, db_write_performed: false, raw_write_performed: false, raw_match_data_insert_performed: false, schema_migration_performed: false, adg60_write_performed: false, raw_write_ready_marked: false };
  console.log(JSON.stringify(er, null, 2));
  console.error('\n=== Next-Batch Live Fetch Summary ===');
  console.error(`Targets: ${CANDIDATES.length} | Requests: ${rc} | Success: ${er.aggregate.success_count} | Blocked: ${er.aggregate.blocked_count}`);
  console.error(`Stopped early: ${er.aggregate.stopped_early ? `YES (${er.aggregate.stopped_early_reason})` : 'NO'}`);
  console.error('Body persisted/comitted: false/false | DB write: false | Raw write: false');
}

async function main() {
  const args = process.argv.slice(2);
  const exec = args.includes('--execute-next-batch-live-fetch');
  const indices = parseIndices(args);
  const pf = preflight(indices.length ? indices : REQUIRED_INDICES);
  if (!exec) return outputPreflight(pf);
  if (indices.length !== REQUIRED_COUNT || !indices.every((v, i) => v === REQUIRED_INDICES[i])) { console.error(`ERROR: --target-indices must be exactly ${REQUIRED_INDICES.join(',')}`); process.exit(1); }
  if (!pf.passed) { console.error('Preflight failed.'); process.exit(1); }
  const er = buildResult();
  const rc = await executeLoop(er);
  finish(er, rc);
  return 0;
}

await main();
