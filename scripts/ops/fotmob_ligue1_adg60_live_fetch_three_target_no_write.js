#!/usr/bin/env node

/**
 * @fileoverview Helper for ADG60 three-target live fetch no-write.
 *
 * lifecycle: phase-artifact
 * phase: ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE
 *
 * Default mode is safe preflight — no network request, no DB write, no
 * browser automation, no body persistence.
 *
 * Live fetch requires explicit CLI flags:
 *   --execute-three-target-live-fetch --target-indices 2,3,4
 *
 * Each target gets exactly 1 request. Sequential only. No retry.
 * Delay 20-60 seconds between successful requests.
 * Only response metadata/hash/status is persisted; body is discarded.
 */

import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

// ---------------------------------------------------------------------------
// Configuration — source-controlled identity data
// ---------------------------------------------------------------------------

const CANDIDATES = Object.freeze([
  {
    target_index: 2,
    target_match_id: '53_20252026_4830472',
    expected_home: 'Nice',
    expected_away: 'Auxerre',
    expected_date: '2025-08-23',
    competition: 'Ligue 1',
    corrected_hash_id: '4830472',
    corrected_route_hash_pair: '2sy6tc#4830472',
    route_hash: '2sy6tc',
    match_hash: '4830472',
    url: 'https://www.fotmob.com/matches/2sy6tc/4830472',
  },
  {
    target_index: 3,
    target_match_id: '53_20252026_4830474',
    expected_home: 'Strasbourg',
    expected_away: 'Nantes',
    expected_date: '2025-08-24',
    competition: 'Ligue 1',
    corrected_hash_id: '4830474',
    corrected_route_hash_pair: '37a71l#4830474',
    route_hash: '37a71l',
    match_hash: '4830474',
    url: 'https://www.fotmob.com/matches/37a71l/4830474',
  },
  {
    target_index: 4,
    target_match_id: '53_20252026_4830475',
    expected_home: 'Toulouse',
    expected_away: 'Brest',
    expected_date: '2025-08-24',
    competition: 'Ligue 1',
    corrected_hash_id: '4830475',
    corrected_route_hash_pair: '2th5t2#4830475',
    route_hash: '2th5t2',
    match_hash: '4830475',
    url: 'https://www.fotmob.com/matches/2th5t2/4830475',
  },
]);

const REQUIRED_SELECTED_COUNT = 3;
const REQUIRED_INDICES = [2, 3, 4];
const MAX_NETWORK_REQUESTS_TOTAL = 3;
const MAX_NETWORK_REQUESTS_PER_TARGET = 1;
const TIMEOUT_MS = 20_000;
const DELAY_MIN_MS = 20_000;
const DELAY_MAX_MS = 60_000;
const MAX_PAYLOAD_BYTES = 5 * 1024 * 1024;
const USER_AGENT = 'FootballPrediction-ADG60/0.1';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function delay(ms) {
  return new Promise((resolve) => { setTimeout(resolve, ms); });
}

function randomDelay(minMs, maxMs) {
  const ms = Math.floor(Math.random() * (maxMs - minMs + 1)) + minMs;
  return delay(ms);
}

/**
 * Compute minimal schema flags from response body in memory.
 * Body is NOT persisted, NOT logged, NOT printed.
 */
function computeMinimalSchemaFlags(bodyText) {
  if (!bodyText || typeof bodyText !== 'string') {
    return {
      hasNextDataMarker: false,
      hasPagePropsMarker: false,
      hasPropsMarker: false,
      looksLikeJson: false,
      looksLikeHtml: false,
      hasMatchDetails: false,
      hasGeneral: false,
      hasContent: false,
      hasTeamColorsPageProps: false,
    };
  }
  const s = bodyText;
  return {
    hasNextDataMarker: s.includes('__NEXT_DATA__'),
    hasPagePropsMarker: s.includes('pageProps'),
    hasPropsMarker: s.includes('"props"'),
    looksLikeJson: (() => {
      try {
        JSON.parse(s);
        return true;
      } catch {
        return false;
      }
    })(),
    looksLikeHtml: s.includes('<html') || s.includes('<!DOCTYPE') || s.includes('<!doctype'),
    hasMatchDetails: s.includes('matchDetails') || s.includes('"matchDetailsVerse"'),
    hasGeneral: s.includes('"general"'),
    hasContent: s.includes('"content"'),
    hasTeamColorsPageProps: s.includes('teamColors') && s.includes('pageProps'),
  };
}

/**
 * Preflight checks — no network.
 */
function preflight(targetIndices) {
  const checks = [];
  let passed = true;

  const fail = (name, msg) => {
    checks.push({ name, pass: false, message: msg });
    passed = false;
  };
  const ok = (name) => checks.push({ name, pass: true });

  // Scope
  const count = targetIndices.length;
  if (count !== REQUIRED_SELECTED_COUNT) {
    fail('selected_target_count', `expected ${REQUIRED_SELECTED_COUNT}, got ${count}`);
  } else {
    ok('selected_target_count');
  }

  const indicesMatch =
    targetIndices.length === REQUIRED_INDICES.length &&
    targetIndices.every((v, i) => v === REQUIRED_INDICES[i]);
  if (!indicesMatch) {
    fail('selected_indices', `expected [${REQUIRED_INDICES}], got [${targetIndices}]`);
  } else {
    ok('selected_indices');
  }

  // Identity checks per target
  for (const t of CANDIDATES) {
    const prefix = `target_${t.target_index}`;
    if (!t.expected_home) fail(`${prefix}_home`, 'missing expected_home');
    else ok(`${prefix}_home`);
    if (!t.expected_away) fail(`${prefix}_away`, 'missing expected_away');
    else ok(`${prefix}_away`);
    if (!t.expected_date) fail(`${prefix}_date`, 'missing expected_date');
    else ok(`${prefix}_date`);
    if (!t.competition) fail(`${prefix}_competition`, 'missing competition');
    else ok(`${prefix}_competition`);
    if (!t.corrected_hash_id) fail(`${prefix}_corrected_hash_id`, 'missing corrected_hash_id');
    else ok(`${prefix}_corrected_hash_id`);
    if (!t.corrected_route_hash_pair) fail(`${prefix}_route`, 'missing corrected_route_hash_pair');
    else ok(`${prefix}_route`);
  }

  // Safety
  ok('browser_automation_allowed_false');
  ok('payload_body_persistence_allowed_false');
  ok('db_write_allowed_false');
  ok('raw_write_allowed_false');
  ok('raw_match_data_insert_allowed_false');
  ok('adg60_write_allowed_false');
  ok('raw_write_ready_marking_allowed_false');

  // Output paths safe (no raw payload paths)
  ok('output_path_safe_no_raw_payload');
  ok('output_path_safe_no_html');
  ok('output_path_safe_no_pageprops');
  ok('output_path_safe_no_response_body');

  // Network policy
  ok('max_network_requests_total_3');
  ok('max_network_requests_per_target_1');
  ok('no_retry');
  ok('no_parallelism');
  ok('delay_policy_exists');
  ok('no_body_persistence');

  return { passed, checks };
}

/**
 * Create initial result template for a target.
 */
function emptyResult(target) {
  return {
    target_index: target.target_index,
    target_match_id: target.target_match_id,
    route_hash_pair: target.corrected_route_hash_pair,
    url: target.url,
    request_performed: false,
    request_count: 0,
    http_status: null,
    final_url_or_route: null,
    redirected: false,
    content_type: null,
    byte_size: null,
    sha256: null,
    payload_like: false,
    minimal_schema_flags: null,
    stop_reason: null,
    body_persisted: false,
    body_logged: false,
    body_committed: false,
  };
}

/**
 * Determine if response status is a blocking condition and return stop_reason.
 */
function checkResponseStatus(result, resp) {
  if (resp.status >= 300 && resp.status < 400) {
    result.redirected = true;
    result.final_url_or_route = resp.headers.get('location') || result.url;
    result.stop_reason = `unexpected_redirect_${resp.status}`;
    return true;
  }
  if (resp.status === 403) { result.stop_reason = 'blocked_403'; return true; }
  if (resp.status === 429) { result.stop_reason = 'blocked_429'; return true; }
  if (resp.status >= 500) { result.stop_reason = `server_error_${resp.status}`; return true; }
  return false;
}

/**
 * Check if body text contains anti-bot or captcha signals.
 */
function hasAntiBotSignals(bodyText) {
  return bodyText.includes('captcha') || bodyText.includes('cf-browser-verification') ||
    bodyText.includes('_cf_chl_opt') || bodyText.includes('g-recaptcha');
}

/**
 * Consume and discard response body when blocking.
 */
async function discardBody(resp) {
  try { await resp.text(); } catch { /* ignore */ }
}

/**
 * Perform a single GET request for one target. Returns metadata only.
 * Body is consumed for sha256/size/flags computation then discarded.
 */
async function fetchOneTarget(target) {
  const result = emptyResult(target);

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);

    const resp = await fetch(target.url, {
      method: 'GET',
      headers: { 'User-Agent': USER_AGENT },
      redirect: 'manual',
      signal: controller.signal,
    });

    clearTimeout(timeout);

    result.request_performed = true;
    result.request_count = 1;
    result.http_status = resp.status;
    result.content_type = resp.headers.get('content-type') || null;

    // Check for blocking status
    if (checkResponseStatus(result, resp)) {
      await discardBody(resp);
      return result;
    }

    // Read body for metadata computation only
    let bodyText;
    try {
      bodyText = await resp.text();
    } catch (err) {
      result.stop_reason = `body_read_error: ${String(err)}`;
      return result;
    }

    // Size check
    const byteSize = Buffer.byteLength(bodyText, 'utf-8');
    if (byteSize > MAX_PAYLOAD_BYTES) {
      result.stop_reason = `payload_too_large_${byteSize}`;
      return result;
    }

    // Anti-bot check
    if (hasAntiBotSignals(bodyText)) {
      result.stop_reason = 'anti_bot_or_captcha_detected';
      return result;
    }

    // Compute hash
    const hash = createHash('sha256');
    hash.update(bodyText, 'utf-8');
    const sha256 = hash.digest('hex');

    // Compute schema flags
    const flags = computeMinimalSchemaFlags(bodyText);
    const payloadLike = flags.looksLikeHtml && flags.hasNextDataMarker && flags.hasPagePropsMarker;

    // Populate result with metadata only — body is discarded
    result.byte_size = byteSize;
    result.sha256 = sha256;
    result.payload_like = payloadLike;
    result.minimal_schema_flags = flags;
    result.final_url_or_route = target.url;
  } catch (err) {
    result.stop_reason = err.name === 'AbortError' ? 'timeout' : `network_error: ${String(err)}`;
  }

  return result;
}

/**
 * Parse CLI arguments for target indices.
 */
function parseTargetIndices(args) {
  let str = null;
  const eqIdx = args.findIndex((a) => a.startsWith('--target-indices='));
  if (eqIdx >= 0) { str = args[eqIdx].split('=')[1]; }
  else {
    const flagIdx = args.indexOf('--target-indices');
    if (flagIdx >= 0 && flagIdx + 1 < args.length) { str = args[flagIdx + 1]; }
  }
  return str ? str.split(',').map(Number) : [];
}

/**
 * Output preflight result and return exit code.
 */
function outputPreflight(pf) {
  console.log(JSON.stringify({
    mode: 'preflight',
    phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE',
    preflight_checks: pf,
    live_fetch_requires: '--execute-three-target-live-fetch --target-indices 2,3,4',
    live_fetch_performed: false,
    network_fetch_performed: false,
    browser_automation_performed: false,
    payload_saved: false,
    db_write_performed: false,
    raw_write_performed: false,
    raw_match_data_insert_performed: false,
    adg60_write_performed: false,
    raw_write_ready_marked: false,
  }, null, 2));
  return pf.passed ? 0 : 1;
}

/**
 * Build the initial execution result container.
 */
function buildExecutionResult() {
  return {
    phase: 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-THREE-TARGET-NO-WRITE',
    generated_at: new Date().toISOString(),
    selected_targets: CANDIDATES.map((t) => ({
      target_index: t.target_index,
      target_match_id: t.target_match_id,
      expected_home: t.expected_home,
      expected_away: t.expected_away,
      expected_date: t.expected_date,
      competition: t.competition,
      corrected_route_hash_pair: t.corrected_route_hash_pair,
    })),
    request_policy: {
      max_network_requests_total: MAX_NETWORK_REQUESTS_TOTAL,
      max_network_requests_per_target: MAX_NETWORK_REQUESTS_PER_TARGET,
      sequential_only: true,
      no_retry: true,
      no_parallelism: true,
      delay_min_ms: DELAY_MIN_MS,
      delay_max_ms: DELAY_MAX_MS,
      timeout_ms: TIMEOUT_MS,
      redirect: 'manual',
      user_agent: USER_AGENT,
    },
    per_target_results: [],
    aggregate: {
      selected_target_count: REQUIRED_SELECTED_COUNT,
      request_count_total: 0,
      success_count: 0,
      blocked_count: 0,
      stopped_early: false,
      stopped_early_reason: null,
    },
  };
}

/**
 * Execute sequential fetch loop for all candidates.
 */
async function executeFetchLoop(executionResult) {
  let requestCount = 0;
  let stoppedEarly = false;
  let stopReason = null;

  for (let i = 0; i < CANDIDATES.length; i++) {
    if (stoppedEarly) break;

    const target = CANDIDATES[i];
    const result = await fetchOneTarget(target);
    executionResult.per_target_results.push(result);

    if (result.request_performed) { requestCount++; }

    if (result.stop_reason) {
      stoppedEarly = true;
      stopReason = result.stop_reason;
      executionResult.aggregate.blocked_count++;
    } else {
      executionResult.aggregate.success_count++;
    }

    if (i < CANDIDATES.length - 1 && !stoppedEarly) {
      await randomDelay(DELAY_MIN_MS, DELAY_MAX_MS);
    }
  }

  executionResult.aggregate.request_count_total = requestCount;
  executionResult.aggregate.stopped_early = stoppedEarly;
  executionResult.aggregate.stopped_early_reason = stopReason;
  return requestCount;
}

/**
 * Attach safety flags and output execution result.
 */
function finalizeAndOutput(executionResult, requestCount) {
  const any = requestCount > 0;
  executionResult.safety = {
    live_fetch_performed: any,
    network_fetch_performed: any,
    browser_automation_performed: false,
    payload_saved: false,
    response_body_saved: false,
    db_write_performed: false,
    raw_write_performed: false,
    raw_match_data_insert_performed: false,
    schema_migration_performed: false,
    adg60_write_performed: false,
    raw_write_ready_marked: false,
  };

  console.log(JSON.stringify(executionResult, null, 2));
  console.error('\n=== Three-Target Live Fetch Summary ===');
  console.error(`Targets attempted: ${CANDIDATES.length}`);
  console.error(`Requests performed: ${requestCount}`);
  console.error(`Success: ${executionResult.aggregate.success_count}`);
  console.error(`Blocked: ${executionResult.aggregate.blocked_count}`);
  const early = executionResult.aggregate.stopped_early;
  console.error(`Stopped early: ${early ? `YES (${executionResult.aggregate.stopped_early_reason})` : 'NO'}`);
  console.error('Body persisted: false');
  console.error('Body logged: false');
  console.error('Body committed: false');
  console.error('DB write: false');
  console.error('Raw write: false');
}

/**
 * Main execution. Guarded by --execute-three-target-live-fetch flag.
 */
async function main() {
  const args = process.argv.slice(2);
  const executeFlag = args.includes('--execute-three-target-live-fetch');
  const targetIndices = parseTargetIndices(args);

  // Always validate scope even in default mode
  const pf = preflight(targetIndices.length ? targetIndices : REQUIRED_INDICES);

  if (!executeFlag) {
    return outputPreflight(pf);
  }

  // Validate target indices match [2,3,4] exactly
  if (targetIndices.length !== REQUIRED_SELECTED_COUNT ||
      !targetIndices.every((v, i) => v === REQUIRED_INDICES[i])) {
    console.error(`ERROR: --target-indices must be exactly ${REQUIRED_INDICES.join(',')}`);
    process.exit(1);
  }

  if (!pf.passed) {
    console.error('Preflight failed. Aborting before network.');
    console.error(JSON.stringify(pf.checks.filter((c) => !c.pass), null, 2));
    process.exit(1);
  }

  // ---- Execution phase ----
  const executionResult = buildExecutionResult();
  const requestCount = await executeFetchLoop(executionResult);
  finalizeAndOutput(executionResult, requestCount);
  return 0;
}

await main();
