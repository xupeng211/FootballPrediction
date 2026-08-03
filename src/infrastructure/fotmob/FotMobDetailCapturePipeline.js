'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
//
// FotMob bounded detail capture — CAPTURE stage pipeline.
//
// Bounded serial executor connecting a validated plan to
// FotMobRawDetailFetcher with a shared budgeted fetch adapter.
//
// Safety properties enforced here:
//   - CAPTURE is off by default: --execute + networkAuthorization === true
//     + CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1 + authorization id +
//     expected-plan-sha256 + max-requests + CONFIRM_MAX_FOTMOB_REQUESTS
//     + clean git worktree + full 40-hex HEAD revision + repository-external
//     non-symlink output dir + non-symlink source plan; all validated before
//     any network call;
//   - single allowed URL shape https://www.fotmob.com/match/<digits>;
//   - GET only, manual redirect (never followed), no cookie / auth header /
//     proxy / browser, concurrency 1, retry 0;
//   - request count incremented before every native fetch; budget exhausted
//     stops before the next fetch;
//   - minimum inter-request delay 60 000 ms; timeout 30 s; fixed UA;
//   - access-control signals (401/403/407/429, any 3xx redirect, captcha /
//     challenge markers) stop the whole run immediately;
//   - content-validity gate before retention (EMPTY_SSR_SHELL fails);
//   - resume: completed matching pairs are never fetched again; partial or
//     mismatched pairs stop the run;
//   - the pipeline is database-free.

const path = require('node:path');
const fs = require('node:fs');

const {
    GENERATOR_COMPONENT,
    NETWORK_AUTHORIZATION_MODE,
    REQUIRED_LEAGUE_ID,
    MAX_BODY_BYTES,
    isPlainObject,
    evaluateContentValidity,
    validateAndRecomputeCapturePlan,
    buildCapturePayload,
    computeCaptureManifestSelfHash,
    BLOCK_MARKERS,
    assertNoSymlinkAncestors,
    ensureRealDirectoryTree,
} = require('./FotMobDetailCaptureContract');

const {
    fetchFotMobRawDetail,
} = require('../services/FotMobRawDetailFetcher');

const {
    validateCollectorCodeRevision,
    resolveGitState,
} = require('./FotMobCandidateExporter');

const {
    writeCapturePair,
    defaultRunState,
    writeRunState,
    readRunState,
    writePlanSnapshot,
    checkCompletedPair,
    buildRunSummary,
    writeRunSummary,
    sha256Bytes,
} = require('./FotMobDetailCaptureRetention');

// ─────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────

const FOTMOB_BASE_URL = 'https://www.fotmob.com';
const DEFAULT_DELAY_MS = 60000;
const MIN_DELAY_MS = 60000;
const REQUEST_TIMEOUT_MS = 30000;
const FIXED_USER_AGENT =
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36';

const ACCESS_CONTROL_STATUSES = new Set([401, 403, 407, 429]);
const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);

// Block markers are imported from the shared contract module (single source).

// ─────────────────────────────────────────────────────────────
// Bounded fetch adapter
// ─────────────────────────────────────────────────────────────

/**
 * Create a bounded fetch function enforcing the strict network contract.
 * The adapter is the ONLY place a native fetch may be invoked; the caller
 * injects `fetchImpl` so tests can substitute mocks (default is the global
 * fetch, which tests forbid via global.fetch = throwing stub).
 *
 * @param {object} options - {
 *   fetchImpl?, delayMs?, timeoutMs?, sleepImpl?,
 *   onBeforeFetch? (called with (url, count) before native fetch),
 *   initialUsed? (already-consumed requests from a resumed run; the
 *   budget cap is enforced against the CUMULATIVE count so a resume can
 *   never exceed the declared max-requests budget),
 *   initialLastRequestAt? (ISO timestamp of the last request attempted by a
 *   prior process; the inter-request delay continues across processes —
 *   remainingDelay = delayMs - (now - initialLastRequestAt). An invalid
 *   timestamp fails closed (R3-P2-5)),
 *   now? (() => ms epoch; defaults to Date.now)
 * }
 * @returns {{ fetchOnce: (url, opts) => Promise<object>, budget: { used, max }, requestCount: () => number }}
 */
/* eslint-disable-next-line complexity */
function createBoundedFetchAdapter(options = {}) {
    const fetchImpl = options.fetchImpl || globalThis.fetch;
    const maxRequests = Number(options.maxRequests || 0);
    // Already-consumed requests from a prior run cycle (P1: resume budget).
    // The cap is checked against initialUsed + local count, so resuming a
    // run whose budget was exhausted performs zero further fetches.
    const initialUsed = Math.max(0, Number(options.initialUsed || 0));
    const delayMs = options.delayMs === undefined ? DEFAULT_DELAY_MS : Number(options.delayMs);
    const timeoutMs = options.timeoutMs === undefined ? REQUEST_TIMEOUT_MS : Number(options.timeoutMs);

    if (!Number.isInteger(maxRequests) || maxRequests < 1) {
        throw Object.assign(new Error('maxRequests must be a positive integer'), { code: 'INPUT_ERROR' });
    }
    if (!Number.isInteger(delayMs) || delayMs < MIN_DELAY_MS) {
        throw Object.assign(
            new Error(`delayMs must be at least ${MIN_DELAY_MS}`),
            { code: 'INPUT_ERROR' }
        );
    }
    if (typeof fetchImpl !== 'function') {
        throw Object.assign(new Error('fetch implementation missing'), { code: 'INPUT_ERROR' });
    }

    // Injectable clock (ms epoch) so cross-process delay tests are
    // deterministic; the default is the wall clock.
    const nowMs = options.now || (() => Date.now());

    // R3-P2-5: seed the inter-request delay from the persisted
    // last_network_request_attempted_at of the prior process, so a resumed
    // run never issues a request sooner than delayMs after the previous
    // attempt. An invalid / unparseable timestamp fails closed — guessing
    // is not an option.
    let lastRequestAt = 0;
    if (options.initialLastRequestAt !== undefined && options.initialLastRequestAt !== null &&
        String(options.initialLastRequestAt).trim() !== '') {
        const parsed = Date.parse(String(options.initialLastRequestAt));
        if (Number.isNaN(parsed)) {
            throw Object.assign(
                new Error(`SAFETY_ERROR:invalid_last_request_attempted_at:${String(options.initialLastRequestAt).slice(0, 80)}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        lastRequestAt = parsed;
    }

    let requestCount = 0;

    // Injectable sleep keeps multi-candidate tests fast while the delayMs
    // value gate (>= 60000) is still enforced on the real path.
    const sleepImpl = options.sleepImpl || ((ms) => new Promise((resolve) => { setTimeout(resolve, ms); }));

    /**
     * Execute one bounded GET. Budget is incremented BEFORE the native
     * fetch; exhaustion raises SAFETY_ERROR before the next fetch.
     * Redirect responses (3xx) count as the request and are never followed.
     *
     * @param {string} url - must match https://www.fotmob.com/match/<digits>
     * @returns {Promise<object>} response-like { status, url, headers.get, text, body, bodyBytes }
     */
    // eslint-disable-next-line complexity
    async function fetchOnce(url) {
        const u = new URL(String(url));
        if (u.protocol !== 'https:') {
            throw Object.assign(new Error(`SAFETY_ERROR:protocol_not_https:${u.protocol}`), { code: 'SAFETY_ERROR' });
        }
        if (u.hostname !== 'www.fotmob.com') {
            throw Object.assign(new Error(`SAFETY_ERROR:host_not_authorized:${u.hostname}`), { code: 'SAFETY_ERROR' });
        }
        if (!/^\/match\/[0-9]+$/.test(u.pathname)) {
            throw Object.assign(new Error(`SAFETY_ERROR:path_not_authorized:${u.pathname}`), { code: 'SAFETY_ERROR' });
        }
        if (u.search !== '' || u.hash !== '') {
            throw Object.assign(
                new Error(`SAFETY_ERROR:query_or_fragment_not_authorized:${u.search}${u.hash}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (initialUsed + requestCount >= maxRequests) {
            throw Object.assign(
                new Error(`SAFETY_ERROR:budget_exhausted:${initialUsed + requestCount}/${maxRequests}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        requestCount += 1;

        // Serialization: enforce the minimum inter-request delay measured
        // from the previous request's attempt. Runs AFTER the budget gate
        // (exhaustion raises before any wait) and BEFORE the attempt
        // timestamp is persisted, so the persisted value is exactly the
        // moment this request starts (cross-process continuity, R3-P2-5).
        // A clock that went backwards between processes (now < lastRequestAt)
        // clamps the elapsed time to zero — the full delay is enforced.
        if (lastRequestAt > 0) {
            const elapsed = Math.max(0, nowMs() - lastRequestAt);
            if (elapsed < delayMs) {
                await sleepImpl(delayMs - elapsed);
            }
        }
        lastRequestAt = nowMs();
        // The attempt is persisted (budget + timestamp) BEFORE the native
        // fetch — a timeout / abort / read failure can never be recorded as
        // zero attempts (P2-4) or as an unrecorded request time (R3-P2-5).
        let requestAttemptedAt = new Date(lastRequestAt).toISOString();
        if (options.onBeforeFetch) {
            // P2 (Codex re-review on cdcb7ae18): the pre-fetch callback may
            // return the ACTUAL attempt timestamp (taken after any inter-
            // request delay, immediately before the native fetch); that value
            // is what the manifest records — never the pre-wait moment.
            const returned = options.onBeforeFetch(url, requestCount);
            if (typeof returned === 'string' && returned) requestAttemptedAt = returned;
        }

        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), timeoutMs);
        try {
            const res = await fetchImpl(u.href, {
                method: 'GET',
                redirect: 'manual',
                signal: ctrl.signal,
                headers: {
                    'User-Agent': FIXED_USER_AGENT,
                    accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'accept-language': 'en-US,en;q=0.9',
                    'accept-encoding': 'identity',
                    referer: FOTMOB_BASE_URL,
                },
            });
            const status = Number(res.status || 0);
            const contentType = String(res.headers && res.headers.get ? (res.headers.get('content-type') || '') : '');
            const location = String(res.headers && res.headers.get ? (res.headers.get('location') || '') : '');
            const finalUrl = String(res.url || u.href);
            const redirected = REDIRECT_STATUSES.has(status);

            // P2 (Codex re-review on 047f6afcb): enforce the body-size cap
            // WHILE reading, not after. Reading the whole body with
            // arrayBuffer() before the content gates check the cap would let
            // a single oversized response consume unbounded memory (OOM).
            // An over-limit Content-Length is rejected up front; otherwise
            // the stream is accumulated in chunks and aborted as soon as the
            // cap is exceeded. (A redirect response counts as the request
            // itself; its body is never read.)
            let bodyBytes;
            if (redirected) {
                bodyBytes = Buffer.alloc(0);
            } else {
                const declaredLength = Number(
                    res.headers && res.headers.get ? (res.headers.get('content-length') || 0) : 0
                );
                if (declaredLength > MAX_BODY_BYTES) {
                    throw Object.assign(
                        new Error(`SAFETY_ERROR:oversized_response_body:declared_${declaredLength}/${MAX_BODY_BYTES}`),
                        { code: 'SAFETY_ERROR' }
                    );
                }
                const stream = res.body && typeof res.body.getReader === 'function' ? res.body.getReader() : null;
                if (stream) {
                    const chunks = [];
                    let total = 0;
                    for (;;) {
                        const { done, value } = await stream.read();
                        if (done) break;
                        total += value ? value.byteLength : 0;
                        if (total > MAX_BODY_BYTES) {
                            throw Object.assign(
                                new Error(`SAFETY_ERROR:oversized_response_body:stream_${total}/${MAX_BODY_BYTES}`),
                                { code: 'SAFETY_ERROR' }
                            );
                        }
                        chunks.push(value);
                    }
                    bodyBytes = Buffer.concat(chunks.map((chunk) => Buffer.from(chunk)));
                } else {
                    const ab = await res.arrayBuffer();
                    if (ab.byteLength > MAX_BODY_BYTES) {
                        throw Object.assign(
                            new Error(`SAFETY_ERROR:oversized_response_body:read_${ab.byteLength}/${MAX_BODY_BYTES}`),
                            { code: 'SAFETY_ERROR' }
                        );
                    }
                    bodyBytes = Buffer.from(ab);
                }
            }
            const body = bodyBytes.toString('utf8');

            return {
                status,
                url: finalUrl,
                headers: {
                    get: (name) => {
                        const n = String(name || '').toLowerCase();
                        if (n === 'content-type') return contentType;
                        if (n === 'location') return location;
                        return null;
                    },
                },
                text: async () => body,
                body,
                bodyBytes,
                contentType,
                location,
                finalUrl,
                redirected,
                // Actual attempt instant (after any inter-request delay),
                // recorded by the adapter and/or its pre-fetch callback.
                requestAttemptedAt,
            };
        } finally {
            clearTimeout(timer);
        }
    }

    return {
        fetchOnce,
        // Run-local request count (this adapter instance's own fetches); the
        // absolute consumed budget is initialUsed + this count.
        requestCount: () => requestCount,
        budget: { used: () => requestCount, max: maxRequests },
    };
}

// ─────────────────────────────────────────────────────────────
// Authorization binding
// ─────────────────────────────────────────────────────────────

const REQUIRED_ENV_VAR = 'CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE';
const REQUIRED_ENV_BUDGET = 'CONFIRM_MAX_FOTMOB_REQUESTS';

/**
 * Resolve the full 40-hex git revision of the repository, failing closed on
 * a dirty worktree. Delegates to the exporter's shared resolveGitState so the
 * clean-worktree / 40-hex contract is not re-implemented.
 */
function resolveGitRevision(options = {}) {
    const { revision } = resolveGitState({
        repositoryRoot: options.repositoryRoot,
        deps: { execSync: options.execSync },
    });
    return revision;
}

/**
 * Validate every authorization gate BEFORE any network call.
 * Returns the normalized execution context.
 *
 * @param {object} options - {
 *   plan (object), planPath (string), expectedPlanSha256 (string),
 *   authorizationId (string), maxRequests (number),
 *   outputRoot (string), runId (string),
 *   execute (boolean), networkAuthorization (boolean),
 *   env (object), repositoryRoot, execSync?, fsImpl?
 * }
 */
/* eslint-disable-next-line complexity */
function validateAuthorizationBinding(options = {}) {
    const env = options.env || process.env;
    const errors = [];
    // Preflight (requireExecute: false) validates every gate that can be
    // checked without --execute: plan schema + recomputed hash, git
    // revision, paths, run id, budget and authorization id. The execute-only
    // confirmations (--execute, networkAuthorization, CONFIRM_* env vars)
    // are only enforced for the capture path.
    const requireExecute = options.requireExecute !== false;

    // FIRST gate, before anything else: the plan itself is re-validated and
    // its business hash RECOMPUTED from the actual business fields. A plan
    // with tampered candidates, ordinals, teams, seasons, kickoffs, count or
    // expected_request_path can never keep its old self-declared hash
    // (P1-2). Runs before any mkdir, run-state write, fetch or artifact
    // write.
    const planCheck = validateAndRecomputeCapturePlan(options.plan);
    if (!planCheck.ok) {
        errors.push(`plan validation failed: ${planCheck.errors.join('; ')}`);
    }
    const recomputedPlanSha256 = planCheck.recomputed_sha256;

    if (requireExecute) {
        if (options.execute !== true) {
            errors.push('execute flag required (--execute)');
        }
        if (options.networkAuthorization !== true) {
            errors.push('networkAuthorization must be true');
        }
        if (String(env[REQUIRED_ENV_VAR] || '') !== '1') {
            errors.push(`environment variable ${REQUIRED_ENV_VAR}=1 required`);
        }
        // The network authorization declaration must be re-confirmed in
        // Node, not only in make (Internal Reviewer A P2): a direct Node
        // invocation with the CONFIRM vars but no NETWORK_AUTHORIZATION=yes
        // must fail closed before any fetch.
        if (String(env.NETWORK_AUTHORIZATION || '') !== 'yes') {
            errors.push('environment variable NETWORK_AUTHORIZATION=yes required');
        }
    }
    const authorizationId = String(options.authorizationId || '').trim();
    if (!authorizationId) {
        errors.push('authorization id required (--authorization-id)');
    } else if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(authorizationId)) {
        // P2 (Codex re-review on cdcb7ae18): the gate must never admit an id
        // that the run-state contract rejects — same [a-zA-Z0-9][a-zA-Z0-9._-]*
        // contract as validateRunState's authorization_id, so the persistent
        // record always satisfies its own consumer (resume / replay).
        errors.push('authorization id must match [a-zA-Z0-9][a-zA-Z0-9._-]*');
    }
    const expectedPlanSha256 = String(options.expectedPlanSha256 || '').trim();
    if (!/^[0-9a-f]{64}$/.test(expectedPlanSha256)) {
        errors.push('expected-plan-sha256 must be 64 lowercase hex');
    }
    if (recomputedPlanSha256 !== expectedPlanSha256) {
        errors.push('recomputed plan SHA-256 does not match expected-plan-sha256');
    }
    const maxRequests = Number(options.maxRequests || 0);
    if (!Number.isInteger(maxRequests) || maxRequests < 1) {
        errors.push('max-requests must be a positive integer');
    } else if (requireExecute && String(env[REQUIRED_ENV_BUDGET] || '') !== String(maxRequests)) {
        errors.push(`environment variable ${REQUIRED_ENV_BUDGET} must equal max-requests`);
    }
    // P2 (Codex re-review on d95b91d53): the delay contract is validated
    // HERE — before any directory creation, plan-snapshot or run-state
    // write. The adapter re-validates the same contract later, but a direct
    // CLI call with --delay-ms=1 / non-integer / NaN would otherwise create
    // the run directory and persist run-state.json + plan.json first and
    // only then fail — leaving a POISONED run that a retry with the same
    // RUN_ID can never recover (the persisted delay contract mismatch is
    // permanent, since the run-state validator enforces it on every read).
    const gateDelayMs = options.delayMs === undefined ? DEFAULT_DELAY_MS : Number(options.delayMs);
    if (!Number.isInteger(gateDelayMs) || gateDelayMs < MIN_DELAY_MS) {
        errors.push(`delay-ms must be an integer >= ${MIN_DELAY_MS}`);
    }

    // Plan file must be a regular non-symlink file whose parsed document
    // carries the expected deterministic business hash. (File bytes are not
    // compared: the serialized file includes non-business metadata such as
    // generated_at, so the deterministic contract is the business hash.)
    if (options.planPath) {
        const fsImpl = options.fsImpl || fs;
        try {
            assertNoSymlinkAncestors(String(options.planPath), fsImpl);
        } catch (err) {
            errors.push(String(err.message));
        }
        let stat;
        try {
            stat = fsImpl.lstatSync(String(options.planPath));
        } catch {
            stat = null;
        }
        if (!stat || stat.isSymbolicLink() || !stat.isFile()) {
            errors.push('plan file must be a regular file, not a symlink');
        } else {
            let parsed;
            try {
                parsed = JSON.parse(fsImpl.readFileSync(String(options.planPath), 'utf8'));
            } catch {
                parsed = null;
            }
            if (!parsed || String(parsed.plan_business_sha256 || '') !== expectedPlanSha256) {
                errors.push('plan file document does not match expected-plan-sha256');
            }
        }
    }

    // Run id: a plain identifier — never a path. Rejects traversal ('..',
    // absolute paths, nested separators) that could escape the output root.
    const runId = String(options.runId || '').trim();
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(runId)) {
        errors.push('run id must match [a-zA-Z0-9][a-zA-Z0-9._-]*');
    }

    // Output root: repository-external, absolute, non-symlink (leaf AND every
    // ancestor component — an intermediate symlink can escape the repo).
    if (options.outputRoot) {
        const fsImpl = options.fsImpl || fs;
        // P2 (Codex re-review on 670504754): reject RELATIVE forms before any
        // resolution. path.resolve() would otherwise turn e.g.
        // OUTPUT_ROOT=../../external/captures into an absolute repository-
        // external path, passing every gate and making the path's meaning
        // depend on the container working directory. PLAN and REPLAY already
        // require absolute paths — capture must be consistent with them.
        const rawOutputRoot = String(options.outputRoot);
        if (!path.isAbsolute(rawOutputRoot)) {
            errors.push('output root must be an absolute path, not a relative path');
        }
        const root = path.resolve(rawOutputRoot);
        const repositoryRoot = options.repositoryRoot
            ? path.resolve(options.repositoryRoot)
            : path.resolve(__dirname, '..', '..', '..');
        const rel = path.relative(repositoryRoot, root);
        if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) {
            errors.push('output root must be outside the repository');
        }
        try {
            assertNoSymlinkAncestors(root, fsImpl);
        } catch (err) {
            errors.push(String(err.message));
        }
        let stat = null;
        try {
            stat = fsImpl.lstatSync(root);
        } catch { /* absent is fine */ }
        if (stat && (stat.isSymbolicLink() || !stat.isDirectory())) {
            errors.push('output root must be a real directory, not a symlink');
        }
    }

    if (errors.length > 0) {
        throw Object.assign(
            new Error(`authorization binding failed: ${errors.join('; ')}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Git revision binding happens last (only when all other gates pass).
    const collectorCodeRevision = resolveGitRevision({
        repositoryRoot: options.repositoryRoot,
        execSync: options.execSync,
    });
    validateCollectorCodeRevision(collectorCodeRevision);

    // R3-P2-3 (Codex final-head review): the collector HEAD must be EXACTLY
    // the revision that generated the plan. The plan generator binds
    // generator_code_revision to the generating HEAD (clean worktree, full
    // 40-hex); a plan generated at any other HEAD must fail closed before a
    // native fetch or a formal run-state write. Both preflight and execute
    // surface PLAN_REVISION_HEAD_MISMATCH.
    const planGeneratorRevision = String(options.plan && options.plan.generator_code_revision || '');
    if (planGeneratorRevision !== collectorCodeRevision) {
        throw Object.assign(
            new Error(
                `PLAN_REVISION_HEAD_MISMATCH: plan generator_code_revision ${planGeneratorRevision || '(missing)'} ` +
                `does not match collector HEAD ${collectorCodeRevision}`
            ),
            { code: 'SAFETY_ERROR' }
        );
    }

    return {
        authorizationId,
        expectedPlanSha256,
        maxRequests,
        collectorCodeRevision,
        outputRoot: options.outputRoot ? path.resolve(String(options.outputRoot)) : null,
        runId: String(options.runId || ''),
    };
}

// ─────────────────────────────────────────────────────────────
// Manifest builder
// ─────────────────────────────────────────────────────────────

function buildCaptureManifest(context) {
    const manifest = {
        schema_version: 'fotmob-match-detail-capture-manifest/v1',
        source_provider: 'FotMob',
        source_kind: 'match_detail_page',
        candidate_id: context.candidate.candidate_id,
        source_match_id: context.candidate.source_match_id,
        competition: context.candidate.competition,
        league_id: REQUIRED_LEAGUE_ID,
        season: context.candidate.season,
        home_team: context.candidate.home_team,
        away_team: context.candidate.away_team,
        kickoff_at: context.candidate.kickoff_at,
        candidate_identity_sha256: context.candidate.candidate_identity_sha256,
        source_plan_sha256: context.plan.plan_business_sha256,
        source_artifact_sha256: context.plan.source_artifact_sha256,
        capture_run_id: context.runId,
        authorization_id: context.authorizationId,
        request_ordinal: context.ordinal,
        request_budget: context.maxRequests,
        delay_ms: context.delayMs,
        request_method: 'GET',
        request_url: context.requestUrl,
        request_attempted_at: context.requestAttemptedAt,
        response_received_at: context.responseReceivedAt,
        http_status: context.fetcherResult.http_status,
        content_type: context.fetcherResult.content_type,
        response_body_byte_size: context.fetcherResult.body_byte_length,
        response_body_sha256: context.fetcherResult.body_sha256,
        observed_match_id: context.observedMatchId,
        observed_match_id_source: context.observedMatchIdSource,
        observed_match_id_match: context.observedMatchId === context.candidate.source_match_id,
        observed_match_id_conflict: context.observedMatchIdConflict === true,
        // R3-P1: provenance — the observed id was extracted from the raw
        // hydration allowlist pre-transform (never a transformer-injected
        // request-side id).
        observed_match_id_is_response_derived: context.observedMatchIdResponseDerived === true,
        hydration_parse_ok: context.fetcherResult.hydration_parse_ok === true,
        transformed_api_format: context.fetcherResult.transformed_api_format === true,
        looks_like_valid_match_detail: context.fetcherResult.looks_like_valid_match_detail === true,
        has_stats: context.meta && context.meta.has_stats === true,
        has_lineup: context.meta && context.meta.has_lineup === true,
        has_shotmap: context.meta && context.meta.has_shotmap === true,
        stable_raw_payload_sha256: context.stableRawPayloadSha256,
        stable_payload_sha256: context.stablePayloadSha256,
        payload_file_sha256: context.payloadFileSha256,
        payload_file_relative_path: context.payloadFileName,
        parser_component: 'NextDataParser+FotMobRawParser',
        parser_version: 'V174.0.0',
        collector_component: GENERATOR_COMPONENT,
        collector_code_revision: context.collectorCodeRevision,
        network_authorization_mode: NETWORK_AUTHORIZATION_MODE,
    };
    // Shared helper: self-hash over every field except itself.
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    return manifest;
}

// ─────────────────────────────────────────────────────────────
// Access control evaluation
// ─────────────────────────────────────────────────────────────

/**
 * Detect access-control / challenge signals that must stop the run
 * immediately. Returns null when the run may continue.
 */
function evaluateAccessControl(response, body) {
    const status = Number(response.status || 0);
    if (ACCESS_CONTROL_STATUSES.has(status)) return `http_${status}`;
    if (REDIRECT_STATUSES.has(status)) {
        let loc = null;
        try {
            loc = response.location ? new URL(response.location).hostname : null;
        } catch { loc = 'invalid'; }
        if (loc && loc !== 'www.fotmob.com') return `cross_origin_redirect:${loc}`;
        return `redirect_${status}`;
    }
    const lower = String(body || '').slice(0, 200000).toLowerCase();
    for (const marker of BLOCK_MARKERS) {
        if (lower.includes(marker)) return `block_marker:${marker}`;
    }
    return null;
}

// ─────────────────────────────────────────────────────────────
// Run directory layout
// ─────────────────────────────────────────────────────────────

function resolveRunDirs(outputRoot, runId) {
    const runsDir = path.join(outputRoot, 'runs');
    const runDir = path.join(runsDir, runId);
    const capturesDir = path.join(runDir, 'captures');
    const replayDir = path.join(runDir, 'replay');
    return { runsDir, runDir, capturesDir, replayDir };
}

// ─────────────────────────────────────────────────────────────
// Capture executor
// ─────────────────────────────────────────────────────────────

/**
 * Execute a capture run over the plan.
 *
 * @param {object} options - {
 *   plan (object), planPath (string),
 *   expectedPlanSha256, authorizationId, maxRequests,
 *   outputRoot, runId,
 *   execute (true), networkAuthorization (true),
 *   delayMs (>= 60000), timeoutMs (default 30000),
 *   fetchImpl? (mock), parser? {extractFromHtml, transformToApiFormat},
 *   now? (), env?, repositoryRoot?, execSync?, fsImpl?,
 *   resume? (default true),
 *   pid? (run-lock holder pid, default process.pid),
 *   pidAlive? ((pid) => boolean, injectable for lock tests)
 * }
 * @returns {Promise<object>} run result
 */
const RUN_LOCK_DIR_NAME = '.capture-run.lock';

// R10-P1 (Codex re-review on 047f6afcb): cross-process exclusive lock for a
// capture run id. mkdir is atomic, so a dedicated lock directory inside the
// run dir is an exclusive marker: the first process to create it wins and
// holds it until releaseRunLock removes it. The holder's pid is persisted
// inside so a crashed holder can be detected: a pid that is no longer alive
// marks a STALE lock, which is broken exactly once and retried; a live pid
// means another process owns the run — the competing run stops with
// SAFETY_ERROR before it can read or overwrite run state.
/* eslint-disable-next-line complexity */
function acquireRunLock(runDir, { fsImpl = fs, pid = process.pid, pidAlive } = {}) {
    const isPidAlive = pidAlive || ((candidatePid) => {
        try {
            process.kill(candidatePid, 0);
            return true;
        } catch (err) {
            // EPERM: the pid exists but belongs to another user — alive.
            return err && err.code === 'EPERM';
        }
    });
    const lockDir = path.join(runDir, RUN_LOCK_DIR_NAME);
    for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
            fsImpl.mkdirSync(lockDir);
        } catch (err) {
            if (!err || err.code !== 'EEXIST') {
                throw Object.assign(
                    new Error(`SAFETY_ERROR:run lock could not be created: ${String(err && err.message || err)}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
            // Lock exists: is the holder still alive?
            let holderPid = null;
            try {
                const pidText = String(fsImpl.readFileSync(path.join(lockDir, 'pid'), 'utf8') || '').trim();
                if (/^\d+$/.test(pidText)) holderPid = Number(pidText);
            } catch { /* missing / unreadable pid file */ }
            if (holderPid !== null && holderPid !== Number(pid) && isPidAlive(holderPid)) {
                throw Object.assign(
                    new Error(`SAFETY_ERROR:another capture process (pid ${holderPid}) holds the run lock`),
                    { code: 'SAFETY_ERROR' }
                );
            }
            // Stale (dead holder or unreadable pid): break it exactly once
            // and retry; a second failure means the lock cannot be taken.
            if (attempt === 0) {
                try {
                    fsImpl.rmSync(lockDir, { recursive: true, force: true });
                } catch { /* best effort — the retry reports failure */ }
                continue;
            }
            throw Object.assign(
                new Error('SAFETY_ERROR:run lock could not be acquired'),
                { code: 'SAFETY_ERROR' }
            );
        }
        // Lock acquired — record the holder pid (best effort: a lock without
        // a pid file is still exclusive; stale recovery covers missing pids).
        try {
            fsImpl.writeFileSync(path.join(lockDir, 'pid'), String(pid), 'utf8');
        } catch { /* non-fatal: the lock itself remains exclusive */ }
        return lockDir;
    }
    /* istanbul ignore next -- loop always returns or throws */
    throw Object.assign(new Error('SAFETY_ERROR:run lock could not be acquired'), { code: 'SAFETY_ERROR' });
}

function releaseRunLock(runDir, lockDir, fsImpl = fs) {
    if (!lockDir) return;
    try {
        // Symlink-safe removal: lstat first — a symlink planted at the lock
        // location is unlinked (never followed).
        const st = fsImpl.lstatSync(lockDir);
        if (st.isSymbolicLink() || !st.isDirectory()) {
            fsImpl.rmSync(lockDir, { force: true });
        } else {
            fsImpl.rmSync(lockDir, { recursive: true, force: true });
        }
    } catch {
        // A failed release is not a run failure: the stale-lock recovery in
        // acquireRunLock handles it on the next attempt. Never mask the run
        // result with a cleanup error.
    }
}

async function executeCaptureRun(options = {}) {
    const plan = options.plan;
    if (!isPlainObject(plan) || !Array.isArray(plan.candidates)) {
        throw Object.assign(new Error('plan is required and must contain candidates'), { code: 'INPUT_ERROR' });
    }
    const delayMs = options.delayMs === undefined ? DEFAULT_DELAY_MS : Number(options.delayMs);

    // All authorization gates before any network call.
    const binding = validateAuthorizationBinding({
        ...options,
        plan,
        delayMs,
        maxRequests: Number(options.maxRequests || 0),
    });

    const fsImpl = options.fsImpl || fs;
    const now = options.now || (() => new Date().toISOString());
    const parser = options.parser || {};
    const { runsDir, runDir, capturesDir, replayDir } = resolveRunDirs(binding.outputRoot, binding.runId);

    // Containment: the resolved run dir must stay lexically inside the
    // validated output root (belt-and-suspenders behind the run-id pattern
    // gate in validateAuthorizationBinding).
    const runRel = path.relative(binding.outputRoot, runDir);
    if (runRel === '' || runRel.startsWith('..') || path.isAbsolute(runRel)) {
        throw Object.assign(
            new Error(`run dir escapes the output root: ${runDir}`),
            { code: 'SAFETY_ERROR' }
        );
    }

    // Directory creation is symlink-safe: every component below the output
    // root is lstat-verified; pre-existing symlinked runs / run-id /
    // captures / replay descendants are rejected (P2-3).
    ensureRealDirectoryTree(runsDir, fsImpl);
    ensureRealDirectoryTree(runDir, fsImpl);
    ensureRealDirectoryTree(capturesDir, fsImpl);
    ensureRealDirectoryTree(replayDir, fsImpl);

    // R10-P1 (Codex re-review on 047f6afcb): cross-process exclusive lock
    // for this run id. Two processes must never interleave run-state reads
    // and writes — the lock is acquired BEFORE reading run state and held
    // until the final run-state write completes (released in finally, so
    // every path — success, error, stop — releases it).
    const runLock = acquireRunLock(runDir, {
        fsImpl,
        pid: options.pid,
        pidAlive: options.pidAlive,
    });
    try {
        return await executeCaptureRunLocked(options, plan, binding, delayMs, fsImpl, now, parser, {
            runsDir,
            runDir,
            capturesDir,
            replayDir,
        });
    } finally {
        releaseRunLock(runDir, runLock, fsImpl);
    }
}

/* eslint-disable-next-line complexity */
async function executeCaptureRunLocked(options, plan, binding, delayMs, fsImpl, now, parser, dirs) {
    const { runsDir, runDir, capturesDir, replayDir } = dirs;

    // Resume: load existing run state bound to this exact run context.
    let runState = readRunState(runDir, fsImpl);
    if (runState) {
        // Full binding validation — run, plan, artifact, authorization,
        // budget contract, delay contract, collector revision (P1-5).
        if (String(runState.run_id || '') !== binding.runId) {
            throw Object.assign(
                new Error('run state run id mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (runState.plan_sha256 !== plan.plan_business_sha256) {
            throw Object.assign(
                new Error('run state plan SHA mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(runState.source_artifact_sha256 || '') !== String(plan.source_artifact_sha256 || '')) {
            throw Object.assign(
                new Error('run state source artifact SHA mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (runState.authorization_id !== binding.authorizationId) {
            throw Object.assign(
                new Error('run state authorization id mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (Number(runState.max_requests) !== binding.maxRequests) {
            throw Object.assign(
                new Error('run state max-requests contract mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (Number(runState.delay_ms) !== delayMs) {
            throw Object.assign(
                new Error('run state delay contract mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(runState.collector_code_revision || '') !== binding.collectorCodeRevision) {
            throw Object.assign(
                new Error('run state collector revision mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
    } else {
        // Fail closed: captures present without run-state must not be
        // guessed-and-continued from file names (P1-5).
        let existingPairs = 0;
        try {
            existingPairs = fsImpl.readdirSync(capturesDir)
                .filter(f => f.endsWith('.payload.json')).length;
        } catch { /* absent dir is fine */ }
        if (existingPairs > 0) {
            throw Object.assign(
                new Error('run state missing but capture pairs exist — refusing to guess'),
                { code: 'SAFETY_ERROR' }
            );
        }
        runState = defaultRunState(plan, {
            runId: binding.runId,
            authorizationId: binding.authorizationId,
            maxRequests: binding.maxRequests,
            delayMs,
            collectorCodeRevision: binding.collectorCodeRevision,
            startedAt: now(),
        });
        writeRunState(runDir, runState, fsImpl);
    }

    // Run-bound immutable plan snapshot BEFORE any real network request:
    // REPLAY binds candidate identity to this snapshot (P2-6).
    writePlanSnapshot({ runDir, plan, fsImpl });

    const completedOrdinals = new Set(
        Array.isArray(runState.completed_ordinals) ? runState.completed_ordinals.map(Number) : []
    );
    // Budget counts only THIS run's real fetches (resume must not inherit
    // earlier runs' counts); the run-state record keeps the cumulative
    // ATTEMPTED total for the run id's audit trail. The attempted count and
    // the request timestamp are persisted BEFORE the native fetch is issued
    // (P2-4 / R3-P2-5): a timeout/abort/read failure can never be recorded
    // as zero.
    const priorNetworkRequests = Number(runState.network_requests_attempted || 0);
    // R3-P2-4: response and capture totals are accumulated independently of
    // attempts — a RESOLVED response (even non-200) is a response, a
    // timeout/abort/read failure is an attempt that is never a response, and
    // resume must never infer responses from attempts.
    const priorResponsesReceived = Number(runState.network_responses_received || 0);
    const priorCapturesCompleted = Number(runState.captures_completed || 0);
    let runNetworkRequests = 0;
    let runResponsesReceived = 0;
    let runCapturesCompleted = 0;
    let stopReason = null;
    let stoppedAtOrdinal = null;

    // R3-P2-5: resume the inter-request delay from the timestamp persisted
    // by the prior process. The run-state contract requires the timestamp
    // whenever attempts exist — a missing or invalid timestamp fails closed
    // (no guessing), and a clock that went backwards yields a full wait.
    let initialLastRequestAt = null;
    if (priorNetworkRequests > 0) {
        initialLastRequestAt = runState.last_network_request_attempted_at || null;
        if (!initialLastRequestAt) {
            throw Object.assign(
                new Error(
                    'SAFETY_ERROR:run state missing last_network_request_attempted_at despite network_requests_attempted > 0'
                ),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (Number.isNaN(Date.parse(String(initialLastRequestAt)))) {
            throw Object.assign(
                new Error('SAFETY_ERROR:invalid last_network_request_attempted_at in run state'),
                { code: 'SAFETY_ERROR' }
            );
        }
    }

    const budgetedFetch = createBoundedFetchAdapter({
        fetchImpl: options.fetchImpl,
        maxRequests: binding.maxRequests,
        // P1 (Codex re-review): the budget cap is cumulative — a resumed run
        // seeds the adapter with the already-consumed attempted count, so it
        // can never fetch past the declared max-requests under the same
        // authorization context.
        initialUsed: priorNetworkRequests,
        initialLastRequestAt,
        delayMs,
        timeoutMs: options.timeoutMs,
        sleepImpl: options.sleepImpl,
        // The injected ISO clock and the adapter's ms clock derive from the
        // same source so the persisted timestamp equals the adapter's
        // lastRequestAt exactly.
        now: () => Date.parse(now()),
        onBeforeFetch: (url, count) => {
            runNetworkRequests = count;
            // P2 (Codex round-2 review on 85bc0ee43): the attempt timestamp
            // is taken ONCE — the same value persists the run-state
            // timestamp, the updated_at marker, and the manifest's
            // request_attempted_at. Separate now() calls could straddle a
            // millisecond boundary on the real clock and make the manifest
            // time differ from the persisted run-state time.
            const attemptAt = now();
            runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
            runState.network_requests_made = runState.network_requests_attempted;
            runState.real_fotmob_network_requests = runState.network_requests_attempted;
            runState.last_network_request_attempted_at = attemptAt;
            runState.updated_at = attemptAt;
            writeRunState(runDir, runState, fsImpl);
            // Return the actual attempt timestamp: the adapter records it on
            // the fetch result so the manifest never antedates the request
            // by the inter-request delay (P2, Codex re-review).
            return attemptAt;
        },
    });

    for (const candidate of plan.candidates) {
        const ordinal = Number(candidate.ordinal || 0);
        if (ordinal === 0) continue;

        // Resume check BEFORE any fetch: completed pairs bound to THIS run
        // context are never fetched again; anything else stops the run
        // (P1-5: cross-run / cross-plan / cross-authorization pairs are
        // RESUME_PAIR_CONTEXT_MISMATCH, never treated as completed).
        if (options.resume !== false) {
            const pairCheck = checkCompletedPair({
                runDir,
                ordinal,
                sourceMatchId: candidate.source_match_id,
                expectedRunId: binding.runId,
                expectedAuthorizationId: binding.authorizationId,
                expectedPlanSha256: plan.plan_business_sha256,
                expectedSourceArtifactSha256: String(plan.source_artifact_sha256 || ''),
                expectedCandidate: candidate,
                expectedRequestUrl: `${FOTMOB_BASE_URL}${candidate.expected_request_path}`,
                expectedRequestBudget: binding.maxRequests,
                expectedDelayMs: delayMs,
                expectedCollectorCodeRevision: binding.collectorCodeRevision,
                fsImpl,
            });
            if (pairCheck.state === 'complete') {
                // P1 (Codex re-review on cdcb7ae18): a pair left on disk by a
                // prior process that crashed between writeCapturePair() and
                // the run-state update is still one of THIS run's completed
                // pairs. Count it here so the persisted captures_completed
                // stays equal to completed_ordinals.length (the run-state
                // contract); an ordinal already recorded in the prior state
                // is never recounted.
                if (!completedOrdinals.has(ordinal)) {
                    runCapturesCompleted += 1;
                }
                completedOrdinals.add(ordinal);
                continue;
            }
            if (pairCheck.state === 'partial' || pairCheck.state === 'mismatch') {
                stopReason = `resume_pair_${pairCheck.state}:${pairCheck.detail || `ordinal_${ordinal}`}`;
                stoppedAtOrdinal = ordinal;
                break;
            }
            // P2 (Codex round-2 review on 85bc0ee43): the run state records
            // this ordinal as completed but the pair files are missing —
            // data loss or tampering, never a reason to re-fetch. Re-capturing
            // would inflate captures_completed without growing
            // completed_ordinals (the ordinal is already recorded), producing
            // a state its own validator rejects. Fail closed instead.
            if (pairCheck.state === 'absent' && completedOrdinals.has(ordinal)) {
                stopReason = `resume_pair_absent:state records ordinal_${ordinal} as completed but the pair is missing`;
                stoppedAtOrdinal = ordinal;
                break;
            }
        }

        // Serial per-candidate execution: exactly one bounded fetch per
        // candidate. The fetched response is passed to the detail fetcher
        // as a CACHED response — the fetcher's injected fetchFn must never
        // hit the network or consume budget a second time.
        const requestUrl = `${FOTMOB_BASE_URL}${candidate.expected_request_path}`;

        let fetchResult;
        let requestAttemptedAt = null;
        try {
            fetchResult = await budgetedFetch.fetchOnce(requestUrl);
            // The manifest timestamp is the adapter's recorded ACTUAL attempt
            // instant — taken after the inter-request delay, immediately
            // before the native network request (P2, Codex re-review). Never
            // the pre-wait moment, which would antedate the audit record by
            // up to a full delay and diverge from the persisted run-state
            // time.
            requestAttemptedAt = fetchResult.requestAttemptedAt || now();
            // A resolved response was received (even non-200): record it as
            // a response. R3-P2-4: responses accumulate INDEPENDENTLY of
            // attempts — a resolved response counts once, and resume never
            // infers responses from the attempted total.
            runNetworkRequests = budgetedFetch.requestCount();
            runResponsesReceived += 1;
            runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
            runState.network_responses_received = priorResponsesReceived + runResponsesReceived;
            runState.network_requests_made = runState.network_requests_attempted;
            runState.real_fotmob_network_requests = runState.network_requests_attempted;
            runState.updated_at = now();
            writeRunState(runDir, runState, fsImpl);
        } catch (err) {
            // Fetch adapter errors (budget exhausted, protocol/host/path
            // violations, timeouts, abort, read failures) stop the run. The
            // attempted count was already persisted before the fetch and is
            // synced from the adapter so failures are never zero (P2-4). A
            // failed attempt is NOT a response (R3-P2-4).
            runNetworkRequests = budgetedFetch.requestCount();
            runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
            runState.network_requests_made = runState.network_requests_attempted;
            runState.real_fotmob_network_requests = runState.network_requests_attempted;
            runState.updated_at = now();
            writeRunState(runDir, runState, fsImpl);
            const msg = String(err.message || err);
            stopReason = msg.includes('budget_exhausted')
                ? 'budget_exhausted'
                : `fetch_error:${msg.slice(0, 200)}`;
            stoppedAtOrdinal = ordinal;
            break;
        }

        const accessControl = evaluateAccessControl(fetchResult, fetchResult.body);
        if (accessControl) {
            stopReason = `access_control:${accessControl}`;
            stoppedAtOrdinal = ordinal;
            break;
        }

        // Content validity gate (HTTP 200 is not sufficient). The contract
        // enforces 19 checks: the mandated gates plus hex-format gates and
        // the trusted observed-match-id provenance gates — a fail-closed
        // superset. The observed match id must come from a trusted response
        // payload field; an input-external-id fallback fails closed (P1-4).
        let fetcherResult = null;
        let observedMatchId = null;
        let observedMatchIdSource = null;
        let observedMatchIdConflict = false;
        let observedMatchIdResponseDerived = false;
        let observedHome = null;
        let observedAway = null;
        let meta = null;
        let stableRawPayloadSha256 = null;
        let parsedRaw = null;
        let nextData = null;
        let contentValidity = null;

        if (fetchResult.status === 200 && !fetchResult.redirected) {
            try {
                fetcherResult = await fetchFotMobRawDetail(
                    {
                        externalId: candidate.source_match_id,
                        matchId: `${candidate.season.replace('/', '')}_${candidate.source_match_id}`,
                        homeTeam: candidate.home_team,
                        awayTeam: candidate.away_team,
                        matchDate: candidate.kickoff_at,
                        dataVersion: 'fotmob_capture_v1',
                    },
                    {
                        // Cached response: zero network, zero budget.
                        fetchFn: async () => fetchResult,
                        parser,
                        now,
                    }
                );
                const rawData = fetcherResult.raw_data || null;
                observedMatchId = rawData && (rawData.matchId ?? null) !== null
                    ? String(rawData.matchId)
                    : null;
                observedMatchIdSource = String(fetcherResult.match_id_source ||
                    (rawData && rawData._meta ? rawData._meta.match_id_source : null) || '');
                observedMatchIdConflict = fetcherResult.observed_match_id_conflict === true;
                observedMatchIdResponseDerived = fetcherResult.observed_match_id_response_derived === true;
                const g = rawData && rawData.general ? rawData.general : {};
                observedHome = String(g.homeTeam?.name ?? g.home_team?.name ?? g.home_team ?? '').trim() || null;
                observedAway = String(g.awayTeam?.name ?? g.away_team?.name ?? g.away_team ?? '').trim() || null;
                meta = rawData && rawData._meta ? rawData._meta : null;
                // The authoritative stable-raw-payload hash is the fetcher's,
                // computed with the trusted response-derived identity
                // (R3-P1). Rebuilding here with an empty context would null
                // out the matchId (normalizeMatchId no longer trusts
                // rawData.matchId) and diverge from the real hash, leaving
                // the manifest unbound to the actual observed match id
                // (P2, Codex round-2 review on 85bc0ee43).
                stableRawPayloadSha256 = fetcherResult.stable_raw_payload_hash || null;
                const extracted = parser.extractFromHtml
                    ? parser.extractFromHtml(fetchResult.body)
                    : null;
                nextData = extracted && extracted.success === true ? extracted.data : null;
                // Full parse chain: HTML → __NEXT_DATA__ → transform →
                // FotMobRawParser. The parser output feeds the persisted
                // stable payload (never the raw HTML). A missing/invalid
                // raw data (e.g. an EMPTY_SSR_SHELL page) is NOT a parser
                // error: it falls through to the content-validity gate,
                // which reports the structural failure code.
                if (typeof parser.parseFotMobRaw === 'function' && rawData && typeof rawData === 'object') {
                    parsedRaw = parser.parseFotMobRaw(rawData, candidate.source_match_id);
                    if (!parsedRaw || parsedRaw.ok !== true || !parsedRaw.data) {
                        const errMsg = parsedRaw && parsedRaw.error ? parsedRaw.error : 'unknown parser error';
                        throw Object.assign(new Error(`parseFotMobRaw: ${errMsg}`), { code: 'PARSER_ERROR' });
                    }
                }
                contentValidity = evaluateContentValidity({
                    http_status: fetchResult.status,
                    content_type: fetchResult.contentType,
                    body: fetchResult.body,
                    body_sha256: fetcherResult.body_sha256 || sha256Bytes(fetchResult.bodyBytes),
                    fetcherResult,
                    expected_match_id: candidate.source_match_id,
                    expected_home_team: candidate.home_team,
                    expected_away_team: candidate.away_team,
                    next_data: nextData,
                });
            } catch (err) {
                stopReason = `detail_fetch_error:${String(err.message || err).slice(0, 200)}`;
                stoppedAtOrdinal = ordinal;
                break;
            }
        } else {
            // Non-200 or redirect: fail closed.
            contentValidity = evaluateContentValidity({
                http_status: fetchResult.status,
                content_type: fetchResult.contentType,
                body: fetchResult.body,
                body_sha256: sha256Bytes(fetchResult.bodyBytes),
                fetcherResult: {},
                expected_match_id: candidate.source_match_id,
                next_data: null,
            });
        }

        if (!contentValidity || contentValidity.ok !== true) {
            stopReason = `content_validity:${contentValidity ? contentValidity.error_code : 'UNKNOWN'}:ordinal_${ordinal}`;
            stoppedAtOrdinal = ordinal;
            break;
        }
        if (!parsedRaw) {
            stopReason = 'content_validity:PARSER_OUTPUT_MISSING';
            stoppedAtOrdinal = ordinal;
            break;
        }

        // Retention: stable allowlisted payload + manifest paired, atomic,
        // verified. The full HTML response body exists only in memory (it is
        // hashed for audit, never persisted) (P1-1).
        const stablePayload = buildCapturePayload({
            candidate,
            parsedData: parsedRaw.data,
            observedIdentity: {
                home_team: observedHome,
                away_team: observedAway,
                observed_match_id: observedMatchId,
                observed_match_id_source: observedMatchIdSource,
                observed_match_id_conflict: observedMatchIdConflict,
                observed_match_id_is_response_derived: observedMatchIdResponseDerived,
            },
        });
        const payloadBody = JSON.stringify(stablePayload, null, 2) + '\n';
        const payloadFileSha256 = sha256Bytes(Buffer.from(payloadBody, 'utf8'));
        const payloadFileName = `${ordinal}-${candidate.source_match_id}.payload.json`;
        const manifest = buildCaptureManifest({
            candidate,
            plan,
            runId: binding.runId,
            authorizationId: binding.authorizationId,
            ordinal,
            maxRequests: binding.maxRequests,
            delayMs,
            requestAttemptedAt,
            responseReceivedAt: now(),
            fetcherResult,
            observedMatchId,
            observedMatchIdSource,
            observedMatchIdConflict,
            observedMatchIdResponseDerived,
            meta,
            stableRawPayloadSha256,
            stablePayloadSha256: stablePayload.stable_payload_sha256,
            payloadFileSha256,
            payloadFileName,
            collectorCodeRevision: binding.collectorCodeRevision,
            requestUrl,
        });

        try {
            writeCapturePair({
                payloadBody,
                manifest,
                payloadFileName,
                manifestFileName: `${ordinal}-${candidate.source_match_id}.manifest.json`,
                pairDir: capturesDir,
                fsImpl,
            });
        } catch (err) {
            stopReason = `retention_error:${String(err.message || err).slice(0, 200)}`;
            stoppedAtOrdinal = ordinal;
            break;
        }

        completedOrdinals.add(ordinal);

        // Persist run state after each completed candidate (resume safety).
        // R3-P2-4: captures accumulate independently — only pairs actually
        // written by this process increment the per-run counter; the
        // cumulative total always equals the completed ordinals set size.
        runCapturesCompleted += 1;
        runState.completed_ordinals = [...completedOrdinals].sort((a, b) => a - b);
        runState.captures_completed = priorCapturesCompleted + runCapturesCompleted;
        runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
        runState.network_requests_made = runState.network_requests_attempted;
        runState.real_fotmob_network_requests = runState.network_requests_attempted;
        runState.updated_at = now();
        writeRunState(runDir, runState, fsImpl);
    }

    const completed = completedOrdinals.size;
    const total = plan.candidates.length;
    runState.status = stopReason ? 'stopped' : (completed === total ? 'complete' : 'in_progress');
    runState.stopped_at_ordinal = stoppedAtOrdinal;
    runState.stop_reason = stopReason;
    runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
    runState.network_requests_made = runState.network_requests_attempted;
    runState.real_fotmob_network_requests = runState.network_requests_attempted;
    runState.captures_completed = priorCapturesCompleted + runCapturesCompleted;
    runState.completed_ordinals = [...completedOrdinals].sort((a, b) => a - b);
    runState.updated_at = now();
    writeRunState(runDir, runState, fsImpl);

    const summary = buildRunSummary(runState, plan, [...completedOrdinals]);
    writeRunSummary(runDir, summary, fsImpl);

    return {
        runId: binding.runId,
        planSha256: plan.plan_business_sha256,
        status: runState.status,
        completedCount: completed,
        totalCount: total,
        stoppedAtOrdinal,
        stopReason,
        networkRequestsMade: runNetworkRequests,
        completedOrdinals: [...completedOrdinals].sort((a, b) => a - b),
        runDir,
        summary,
    };
}

module.exports = {
    FOTMOB_BASE_URL,
    DEFAULT_DELAY_MS,
    MIN_DELAY_MS,
    REQUEST_TIMEOUT_MS,
    FIXED_USER_AGENT,
    ACCESS_CONTROL_STATUSES,
    REDIRECT_STATUSES,
    REQUIRED_ENV_VAR,
    REQUIRED_ENV_BUDGET,
    createBoundedFetchAdapter,
    resolveGitRevision,
    validateAuthorizationBinding,
    buildCaptureManifest,
    evaluateAccessControl,
    resolveRunDirs,
    executeCaptureRun,
};
