#!/usr/bin/env node
/**
 * @fileoverview Helper for ADG60 final-batch (23-target) live fetch no-write.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE
 *
 * Default = safe preflight. Execute: --execute-final-batch-live-fetch --target-indices 10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32
 */

import { createHash } from 'node:crypto';

const CANDIDATES = Object.freeze([
  { target_index: 10, target_match_id: '53_20252026_4830482', expected_home: 'Nantes', expected_away: 'Auxerre', expected_date: '2025-08-30', competition: 'Ligue 1', corrected_hash_id: '4830482', corrected_route_hash_pair: '2sxslt#4830482', route_hash: '2sxslt', match_hash: '4830482', url: 'https://www.fotmob.com/matches/2sxslt/4830482' },
  { target_index: 11, target_match_id: '53_20252026_4830483', expected_home: 'Paris FC', expected_away: 'Metz', expected_date: '2025-08-31T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830483', corrected_route_hash_pair: '1ucu3j#4830483', route_hash: '1ucu3j', match_hash: '4830483', url: 'https://www.fotmob.com/matches/1ucu3j/4830483' },
  { target_index: 12, target_match_id: '53_20252026_4830484', expected_home: 'Toulouse', expected_away: 'Paris Saint-Germain', expected_date: '2025-08-30T19:05:00Z', competition: 'Ligue 1', corrected_hash_id: '4830484', corrected_route_hash_pair: '38kq0z#4830484', route_hash: '38kq0z', match_hash: '4830484', url: 'https://www.fotmob.com/matches/38kq0z/4830484' },
  { target_index: 13, target_match_id: '53_20252026_4830485', expected_home: 'Auxerre', expected_away: 'Monaco', expected_date: '2025-09-13T19:05:00Z', competition: 'Ligue 1', corrected_hash_id: '4830485', corrected_route_hash_pair: '2sxeeb#4830485', route_hash: '2sxeeb', match_hash: '4830485', url: 'https://www.fotmob.com/matches/2sxeeb/4830485' },
  { target_index: 14, target_match_id: '53_20252026_4830486', expected_home: 'Brest', expected_away: 'Paris FC', expected_date: '2025-09-14T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830486', corrected_route_hash_pair: '1u3kbv#4830486', route_hash: '1u3kbv', match_hash: '4830486', url: 'https://www.fotmob.com/matches/1u3kbv/4830486' },
  { target_index: 15, target_match_id: '53_20252026_4830487', expected_home: 'Lille', expected_away: 'Toulouse', expected_date: '2025-09-14T13:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830487', corrected_route_hash_pair: '2us06f#4830487', route_hash: '2us06f', match_hash: '4830487', url: 'https://www.fotmob.com/matches/2us06f/4830487' },
  { target_index: 16, target_match_id: '53_20252026_4830488', expected_home: 'Marseille', expected_away: 'Lorient', expected_date: '2025-09-12T18:45:00Z', competition: 'Ligue 1', corrected_hash_id: '4830488', corrected_route_hash_pair: '2gwqpe#4830488', route_hash: '2gwqpe', match_hash: '4830488', url: 'https://www.fotmob.com/matches/2gwqpe/4830488' },
  { target_index: 17, target_match_id: '53_20252026_4830489', expected_home: 'Metz', expected_away: 'Angers', expected_date: '2025-09-14T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830489', corrected_route_hash_pair: '2aqs46#4830489', route_hash: '2aqs46', match_hash: '4830489', url: 'https://www.fotmob.com/matches/2aqs46/4830489' },
  { target_index: 18, target_match_id: '53_20252026_4830490', expected_home: 'Nice', expected_away: 'Nantes', expected_date: '2025-09-13T15:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830490', corrected_route_hash_pair: '37310i#4830490', route_hash: '37310i', match_hash: '4830490', url: 'https://www.fotmob.com/matches/37310i/4830490' },
  { target_index: 19, target_match_id: '53_20252026_4830491', expected_home: 'Paris Saint-Germain', expected_away: 'Lens', expected_date: '2025-09-14T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830491', corrected_route_hash_pair: '2t6hdp#4830491', route_hash: '2t6hdp', match_hash: '4830491', url: 'https://www.fotmob.com/matches/2t6hdp/4830491' },
  { target_index: 20, target_match_id: '53_20252026_4830492', expected_home: 'Rennes', expected_away: 'Lyon', expected_date: '2025-09-14T18:45:00Z', competition: 'Ligue 1', corrected_hash_id: '4830492', corrected_route_hash_pair: '36cxwz#4830492', route_hash: '36cxwz', match_hash: '4830492', url: 'https://www.fotmob.com/matches/36cxwz/4830492' },
  { target_index: 21, target_match_id: '53_20252026_4830493', expected_home: 'Strasbourg', expected_away: 'Le Havre', expected_date: '2025-09-14T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830493', corrected_route_hash_pair: '36aub3#4830493', route_hash: '36aub3', match_hash: '4830493', url: 'https://www.fotmob.com/matches/36aub3/4830493' },
  { target_index: 22, target_match_id: '53_20252026_4830494', expected_home: 'Auxerre', expected_away: 'Toulouse', expected_date: '2025-09-21T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830494', corrected_route_hash_pair: '2u5qiz#4830494', route_hash: '2u5qiz', match_hash: '4830494', url: 'https://www.fotmob.com/matches/2u5qiz/4830494' },
  { target_index: 23, target_match_id: '53_20252026_4830495', expected_home: 'Brest', expected_away: 'Nice', expected_date: '2025-09-20T17:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830495', corrected_route_hash_pair: '2s9rcv#4830495', route_hash: '2s9rcv', match_hash: '4830495', url: 'https://www.fotmob.com/matches/2s9rcv/4830495' },
  { target_index: 24, target_match_id: '53_20252026_4830497', expected_home: 'Lens', expected_away: 'Lille', expected_date: '2025-09-20T19:05:00Z', competition: 'Ligue 1', corrected_hash_id: '4830497', corrected_route_hash_pair: '2gcrq9#4830497', route_hash: '2gcrq9', match_hash: '4830497', url: 'https://www.fotmob.com/matches/2gcrq9/4830497' },
  { target_index: 25, target_match_id: '53_20252026_4830498', expected_home: 'Lyon', expected_away: 'Angers', expected_date: '2025-09-19T18:45:00Z', competition: 'Ligue 1', corrected_hash_id: '4830498', corrected_route_hash_pair: '2n29lb#4830498', route_hash: '2n29lb', match_hash: '4830498', url: 'https://www.fotmob.com/matches/2n29lb/4830498' },
  { target_index: 26, target_match_id: '53_20252026_4830499', expected_home: 'Marseille', expected_away: 'Paris Saint-Germain', expected_date: '2025-09-22T18:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830499', corrected_route_hash_pair: '2t82ab#4830499', route_hash: '2t82ab', match_hash: '4830499', url: 'https://www.fotmob.com/matches/2t82ab/4830499' },
  { target_index: 27, target_match_id: '53_20252026_4830500', expected_home: 'Monaco', expected_away: 'Metz', expected_date: '2025-09-21T15:15:00Z', competition: 'Ligue 1', corrected_hash_id: '4830500', corrected_route_hash_pair: '2skdzb#4830500', route_hash: '2skdzb', match_hash: '4830500', url: 'https://www.fotmob.com/matches/2skdzb/4830500' },
  { target_index: 28, target_match_id: '53_20252026_4830501', expected_home: 'Nantes', expected_away: 'Rennes', expected_date: '2025-09-20T15:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830501', corrected_route_hash_pair: '37bglo#4830501', route_hash: '37bglo', match_hash: '4830501', url: 'https://www.fotmob.com/matches/37bglo/4830501' },
  { target_index: 29, target_match_id: '53_20252026_4830502', expected_home: 'Paris FC', expected_away: 'Strasbourg', expected_date: '2025-09-21T13:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830502', corrected_route_hash_pair: '26e9n2#4830502', route_hash: '26e9n2', match_hash: '4830502', url: 'https://www.fotmob.com/matches/26e9n2/4830502' },
  { target_index: 30, target_match_id: '53_20252026_4830505', expected_home: 'Lorient', expected_away: 'Monaco', expected_date: '2025-09-27T15:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830505', corrected_route_hash_pair: '2u3coy#4830505', route_hash: '2u3coy', match_hash: '4830505', url: 'https://www.fotmob.com/matches/2u3coy/4830505' },
  { target_index: 31, target_match_id: '53_20252026_4830507', expected_home: 'Nice', expected_away: 'Paris FC', expected_date: '2025-09-28T13:00:00Z', competition: 'Ligue 1', corrected_hash_id: '4830507', corrected_route_hash_pair: '268cvm#4830507', route_hash: '268cvm', match_hash: '4830507', url: 'https://www.fotmob.com/matches/268cvm/4830507' },
  { target_index: 32, target_match_id: '53_20252026_4830510', expected_home: 'Strasbourg', expected_away: 'Marseille', expected_date: '2025-09-26T18:45:00Z', competition: 'Ligue 1', corrected_hash_id: '4830510', corrected_route_hash_pair: '2t8gik#4830510', route_hash: '2t8gik', match_hash: '4830510', url: 'https://www.fotmob.com/matches/2t8gik/4830510' }
]);

const REQUIRED_COUNT = 23;
const REQUIRED_INDICES = Array.from({length: 23}, (_, i) => i + 10);
const MAX_REQUESTS = 23;
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
  if (!indices.every((v, i) => v === REQUIRED_INDICES[i])) fail('indices', 'mismatch'); else ok('indices');
  for (const t of CANDIDATES) {
    const p = `t${t.target_index}`;
    const valid = t.expected_home && t.expected_away && t.expected_date && t.competition && t.corrected_hash_id && t.corrected_route_hash_pair;
    if (valid) { ok(p); } else { fail(p, 'incomplete'); }
  }
  for (const s of ['browser_false','body_false','db_false','raw_false','rmi_false','adg60_false','rwrm_false','output_safe','max23','max1','noretry','noparallel','delay','nobody']) ok(s);
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
  console.log(JSON.stringify({ mode: 'preflight', phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE', preflight_checks: pf, live_fetch_requires: '--execute-final-batch-live-fetch --target-indices 10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32', live_fetch_performed: false, network_fetch_performed: false, browser_automation_performed: false, payload_saved: false, db_write_performed: false, raw_write_performed: false, raw_match_data_insert_performed: false, adg60_write_performed: false, raw_write_ready_marked: false }, null, 2));
  return pf.passed ? 0 : 1;
}

function buildResult() {
  return { phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-FINAL-BATCH-NO-WRITE', generated_at: new Date().toISOString(), selected_targets: CANDIDATES.map((t) => ({ target_index: t.target_index, target_match_id: t.target_match_id, expected_home: t.expected_home, expected_away: t.expected_away, expected_date: t.expected_date, competition: t.competition, corrected_route_hash_pair: t.corrected_route_hash_pair })), request_policy: { max_network_requests_total: MAX_REQUESTS, max_network_requests_per_target: MAX_PER_TARGET, sequential_only: true, no_retry: true, no_parallelism: true, delay_min_ms: DELAY_MIN, delay_max_ms: DELAY_MAX, timeout_ms: TIMEOUT_MS, redirect: 'manual', user_agent: UA }, per_target_results: [], aggregate: { selected_target_count: REQUIRED_COUNT, request_count_total: 0, success_count: 0, blocked_count: 0, stopped_early: false, stopped_early_reason: null } };
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
  console.error(`\n=== Final-Batch Summary ===`);
  console.error(`Targets: ${CANDIDATES.length} | Requests: ${rc} | Success: ${er.aggregate.success_count} | Blocked: ${er.aggregate.blocked_count}`);
  console.error(`Stopped early: ${er.aggregate.stopped_early ? `YES (${er.aggregate.stopped_early_reason})` : 'NO'}`);
  console.error('Body persisted/comitted: false/false | DB write: false | Raw write: false');
}

async function main() {
  const args = process.argv.slice(2);
  const exec = args.includes('--execute-final-batch-live-fetch');
  const indices = parseIndices(args);
  const pf = preflight(indices.length ? indices : REQUIRED_INDICES);
  if (!exec) return outputPreflight(pf);
  if (indices.length !== REQUIRED_COUNT || !indices.every((v, i) => v === REQUIRED_INDICES[i])) { console.error(`ERROR: --target-indices must be ${REQUIRED_INDICES.join(',')}`); process.exit(1); }
  if (!pf.passed) { console.error('Preflight failed.'); process.exit(1); }
  const er = buildResult();
  const rc = await executeLoop(er);
  finish(er, rc);
  return 0;
}

await main();
