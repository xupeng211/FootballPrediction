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

const {
    buildTransportObservation,
    defaultObservationsDoc,
    readTransportObservationsFile,
    writeTransportObservationsFile,
    settleObservationInDoc,
} = require('./FotMobTransportObservation');

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
    async function fetchOnce(url, opts = {}) {
        // Optional per-attempt context for the transport observation
        // (ordinal + source match id). Never part of the URL / request.
        const { ordinal = null, sourceMatchId = null } = opts || {};
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
        let fetchStartIso = null;
        if (options.onBeforeFetch) {
            // P2 (Codex re-review on cdcb7ae18): the pre-fetch callback runs
            // after the inter-request delay and persists the attempt (budget
            // + timestamp) BEFORE the native fetch — a timeout / abort / read
            // failure can never be recorded as zero attempts (P2-4). Its
            // return value is NOT used as the audit timestamp: the callback
            // takes it before its OWN last run-state write, so it still
            // antedates the real fetch by one write duration (R20-P1) — the
            // adapter re-stamps below with the true post-callback moment.
            options.onBeforeFetch(url, requestCount);
        }
        // R18-P1 + R19-P1 (Codex re-review on 6ca5e90be / 52fadcf09): the
        // pacing anchor is the ACTUAL fetch-start moment. The pre-fetch
        // callback runs a synchronous run-state write between the anchor
        // taken above and the native fetch; the adapter re-takes the anchor
        // NOW — after the callback (and its write) completed, microseconds
        // before fetchImpl — so the next request's wait is measured from the
        // TRUE start of this request and the real gap between two request
        // STARTS can never fall below delayMs, regardless of how long the
        // per-request state writes took.
        lastRequestAt = nowMs();
        // R20-P1 (Codex re-review on 0bfe90629): the audit timestamp on the
        // fetch result is THIS true fetch-start moment — taken after every
        // pre-fetch write, microseconds before fetchImpl. The pipeline
        // persists it after the request settles (completion / failure
        // actualization), so the cross-process resume gate starts from the
        // REAL request start and covers the last pre-fetch run-state write's
        // duration; the callback's own earlier timestamp remains only the
        // crash-window value. On failure the same ISO is attached to the
        // thrown error.
        requestAttemptedAt = new Date(lastRequestAt).toISOString();
        fetchStartIso = requestAttemptedAt;
        const startedMs = lastRequestAt;

        // ── Transport-phase observation (bounded, redacted, persistable) ──
        // Phases are set by ACTUAL code-execution boundaries below — never
        // inferred from error text. The local timer callback flips
        // timeoutTriggered BEFORE aborting, so a request timeout is
        // recognized by the flag, not by matching error.message (owner
        // contract: never guess the phase or the timeout from error text).
        let lastReliablePhase = 'REQUEST_STARTED';
        let timeoutTriggered = false;
        let responseHeadersReceived = false;
        let responseHeadersReceivedAt = null;
        let httpStatus = null;
        let bodyReadingStarted = false;
        let bodyReadingStartedAt = null;
        let bodyBytesReceived = 0;
        let bodyCompleted = false;
        let bodyCompletedAt = null;
        let responseMetadata = null;

        const ctrl = new AbortController();
        const timer = setTimeout(() => {
            timeoutTriggered = true;
            ctrl.abort();
        }, timeoutMs);
        try {
            // Phase boundary: the request is now WAITING for response
            // headers. A failure or timeout from here until the fetch
            // resolves happens in AWAITING_RESPONSE_HEADERS.
            lastReliablePhase = 'AWAITING_RESPONSE_HEADERS';
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
            // Phase boundary: the response headers are IN — the request
            // stopped waiting. Only allowlisted metadata is captured
            // (content type bounded, declared length as a NUMBER, location
            // presence, redirect flag); raw headers are never persisted.
            lastReliablePhase = 'RESPONSE_HEADERS_RECEIVED';
            responseHeadersReceived = true;
            responseHeadersReceivedAt = new Date(nowMs()).toISOString();
            const status = Number(res.status || 0);
            httpStatus = status;
            const contentType = String(res.headers && res.headers.get ? (res.headers.get('content-type') || '') : '');
            const location = String(res.headers && res.headers.get ? (res.headers.get('location') || '') : '');
            const finalUrl = String(res.url || u.href);
            const redirected = REDIRECT_STATUSES.has(status);
            const declaredLength = Number(
                res.headers && res.headers.get ? (res.headers.get('content-length') || 0) : 0
            );
            responseMetadata = {
                content_type: String(contentType).slice(0, 200),
                declared_content_length: Number.isSafeInteger(declaredLength) && declaredLength >= 0
                    ? declaredLength
                    : null,
                location_present: location !== '',
                redirected,
            };

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
                // A redirect response counts as the request itself; its body
                // is never read — body reading stays false in the
                // observation, exactly as the transport behaved.
                bodyBytes = Buffer.alloc(0);
            } else {
                // Phase boundary: the response body read started.
                lastReliablePhase = 'READING_RESPONSE_BODY';
                bodyReadingStarted = true;
                bodyReadingStartedAt = new Date(nowMs()).toISOString();
                if (declaredLength > MAX_BODY_BYTES) {
                    // R17-P1 (Codex re-review on 317fdb0d8): the response is
                    // already established — CANCEL the body stream BEFORE
                    // throwing, exactly like the chunked-read path below. A
                    // server that keeps streaming or never closes the
                    // connection would otherwise leave the underlying socket
                    // owned by this unread response, stalling subsequent
                    // runs; the outer finally only clears the timeout timer.
                    if (res.body && typeof res.body.cancel === 'function') {
                        try {
                            await res.body.cancel();
                        } catch { /* best effort — the SAFETY_ERROR below is the outcome */ }
                    }
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
                        // bodyBytesReceived mirrors the cap counter exactly —
                        // a timeout / abort mid-read keeps the last completed
                        // chunk count as the actual received byte count.
                        bodyBytesReceived = total;
                        if (total > MAX_BODY_BYTES) {
                            // R11-P2-3 (Codex re-review on abf6fbc65): cancel
                            // the underlying stream BEFORE throwing — a
                            // chunked server that keeps streaming past the
                            // cap would otherwise leave the socket owned by
                            // this request, blocking reuse and holding the
                            // process.
                            if (typeof stream.cancel === 'function') {
                                try {
                                    await stream.cancel();
                                } catch { /* best effort — the error below is the outcome */ }
                            }
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
                    bodyBytesReceived = ab.byteLength;
                    if (ab.byteLength > MAX_BODY_BYTES) {
                        throw Object.assign(
                            new Error(`SAFETY_ERROR:oversized_response_body:read_${ab.byteLength}/${MAX_BODY_BYTES}`),
                            { code: 'SAFETY_ERROR' }
                        );
                    }
                    bodyBytes = Buffer.from(ab);
                }
            }
            // Phase boundary: the response body completed. NEVER for
            // redirect responses — their bodies are not read, so the last
            // reliable phase stays RESPONSE_HEADERS_RECEIVED and the body
            // fields stay false/0, exactly as the transport behaved.
            if (!redirected) {
                lastReliablePhase = 'RESPONSE_BODY_COMPLETED';
                bodyCompleted = true;
                bodyCompletedAt = new Date(nowMs()).toISOString();
            }
            const body = bodyBytes.toString('utf8');

            // Transport observation for the COMPLETED outcome — phases and
            // byte counts come from the boundaries above, never from guesses.
            const finishedMs = nowMs();
            const transportObservation = buildTransportObservation({
                ordinal,
                sourceMatchId,
                requestStartedAtIso: requestAttemptedAt,
                requestFinishedAtIso: new Date(finishedMs).toISOString(),
                elapsedMs: Math.max(0, finishedMs - startedMs),
                lastReliablePhase,
                terminalOutcome: 'COMPLETED',
                responseHeadersReceived,
                responseHeadersReceivedAt,
                httpStatus,
                bodyReadingStarted,
                bodyReadingStartedAt,
                bodyBytesReceived,
                bodyCompleted,
                bodyCompletedAt,
                timeoutConfiguredMs: timeoutMs,
                timeoutTriggered,
                abortSource: null,
                errorName: null,
                errorCode: null,
                errorCauseName: null,
                errorCauseCode: null,
                responseMetadata,
            });

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
                transportObservation,
            };
        } catch (err) {
            // Transport-phase classification. The timeout signal comes ONLY
            // from the local timer flag (timeoutTriggered) or the abort
            // mechanics it drives — never from matching error text, so a
            // same-message error from another source cannot be mislabeled
            // REQUEST_TIMEOUT (owner scenario: headers-vs-body evidence).
            // Classification priority: timeout > safety > external abort >
            // body read error > generic fetch error. Observation fields
            // never mutate the original error and never swallow it.
            const isSafetyError = Boolean(err && typeof err === 'object' && err.code === 'SAFETY_ERROR');
            const errName = String((err && typeof err === 'object' && err.name) || 'Error');
            const isAbortError =
                errName === 'AbortError' ||
                errName === 'DOMException' ||
                (err && typeof err === 'object' && err.message && String(err.message).toLowerCase().includes('aborted')) ||
                Boolean(err && typeof err === 'object' && err.signal && err.signal.aborted) ||
                ctrl.signal.aborted;

            let terminalOutcome;
            let abortSource = null;
            let errorName = null;
            let errorCode = null;
            let errorCauseName = null;
            let errorCauseCode = null;
            if (timeoutTriggered && !isSafetyError) {
                terminalOutcome = 'TIMEOUT';
                abortSource = 'REQUEST_TIMEOUT';
                // AWAITING vs READING must come from code boundaries, not
                // from error text: whichever PROGRESS phase was reached last
                // is kept; REQUEST_ABORTED_BY_TIMEOUT is the vocabulary
                // terminal marker the validator accepts for this outcome.
                lastReliablePhase =
                    lastReliablePhase === 'READING_RESPONSE_BODY' ? 'READING_RESPONSE_BODY' : 'AWAITING_RESPONSE_HEADERS';
            } else if (isSafetyError) {
                terminalOutcome = 'SAFETY_ERROR';
                lastReliablePhase = lastReliablePhase === 'READING_RESPONSE_BODY' ? 'READING_RESPONSE_BODY' : lastReliablePhase;
            } else if (isAbortError) {
                terminalOutcome = 'ABORTED';
                abortSource = 'EXTERNAL_ABORT';
            } else if (bodyReadingStarted) {
                terminalOutcome = 'BODY_READ_ERROR';
            } else {
                terminalOutcome = 'FETCH_ERROR';
            }
            if (terminalOutcome !== 'COMPLETED' && terminalOutcome !== 'TIMEOUT' && !isSafetyError) {
                // Non-timeout failure: the most specific PROGRESS phase that
                // was actually reached stays the last reliable phase.
                if (bodyReadingStarted) lastReliablePhase = 'READING_RESPONSE_BODY';
                else if (responseHeadersReceived) lastReliablePhase = 'RESPONSE_HEADERS_RECEIVED';
                else lastReliablePhase = 'AWAITING_RESPONSE_HEADERS';
            }
            errorName = errName;
            errorCode = String((err && typeof err === 'object' && err.code) || '');
            if (err && typeof err === 'object' && err.cause && typeof err.cause === 'object') {
                errorCauseName = String(err.cause.name || '');
                errorCauseCode = String(err.cause.code || '');
            }
            const finishedMs = nowMs();
            const transportObservation = buildTransportObservation({
                ordinal,
                sourceMatchId,
                requestStartedAtIso: requestAttemptedAt,
                requestFinishedAtIso: new Date(finishedMs).toISOString(),
                elapsedMs: Math.max(0, finishedMs - startedMs),
                lastReliablePhase,
                terminalOutcome,
                responseHeadersReceived,
                responseHeadersReceivedAt,
                httpStatus,
                bodyReadingStarted,
                bodyReadingStartedAt,
                bodyBytesReceived,
                bodyCompleted,
                bodyCompletedAt,
                timeoutConfiguredMs: timeoutMs,
                timeoutTriggered,
                abortSource,
                errorName,
                errorCode,
                errorCauseName,
                errorCauseCode,
                responseMetadata,
            });
            if (err !== null && typeof err === 'object') {
                try {
                    err.transportObservation = transportObservation;
                } catch { /* frozen error object — observation is attached or lost */ }
            }
            // R20-P1 (Codex re-review on 0bfe90629): convey the TRUE
            // fetch-start moment even on failure — the run's stop-path state
            // write actualizes the persisted resume seed with it, so a resume
            // after a failed attempt still waits the full delay from the real
            // request start (the attempt DID reach the network). Budget /
            // contract errors that precede the fetch carry no timestamp.
            if (fetchStartIso !== null && err !== null && typeof err === 'object') {
                try {
                    err.requestAttemptedAt = fetchStartIso;
                } catch { /* frozen error object — the value stays unset */ }
            }
            throw err;
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

// R10-P1 + R11-P1 + R12-P1 + R13-P1 (Codex re-review on 047f6afcb /
// abf6fbc65 / cf500786e / 13b27d5b9): cross-process exclusive lock for a
// capture run id.
//
// NON-REUSABLE OWNER TOKEN: the token is `pid:<pid>:<startTicks>:<nonce>`
// where the nonce is the monotonic process uptime and startTicks is the
// kernel's process-start identity (/proc/<pid>/stat field 22, in clock
// ticks since boot — R13-P1). The same token can never be produced by a
// later process (OS pid recycling cannot reproduce either the nonce or a
// different instance's start ticks). The lock is a directory that appears
// atomically COMPLETE: the holder writes its token into a private temp dir
// and renames the whole dir into place (rename is atomic), so a competitor
// can never observe a "live lock without an owner".
//
// INSTANCE-IDENTITY LIVENESS (R13-P1): a token's holder is judged alive by
// PROCESS INSTANCE, not by pid liveness alone — `kill(pid, 0)` would keep a
// crashed holder's lock forever live once an unrelated long-lived process
// recycled the pid. The judge re-reads /proc/<pid>/stat: identical start
// ticks → the same instance still runs (live); different (or unreadable
// but existing) ticks → the recorded instance is GONE — the pid belongs to
// a different process, the lock is stale and can be taken over. Legacy
// tokens without start ticks (pre-R13 format) and pids whose /proc cannot
// be read fall back to pid-liveness (conservative — an unreadable live pid
// is treated as alive).
//
// TAKEOVER NEVER DELETES A CHANGED TOKEN (R12-P1): a stale lock is grabbed
// by renaming the lock dir to the taker's PRIVATE trash name (atomic —
// whatever sits at the lock path at that instant moves there), and only if
// the moved dir still carries the EXACT token that was verified dead (or
// both are absent) is it deleted; otherwise it is renamed BACK. Rename is
// the only destructive primitive, so a takeover can never delete a token
// it did not verify — a new owner's lock is either restored or the taker
// fails SAFETY_ERROR. Release follows the same rename-verify-restore
// protocol: only the dir carrying OUR token is ever removed.
//
// OWNERSHIP RE-VERIFICATION (R12-P1): the holder re-reads its token before
// every run-state write (verifyRunLockOwnership). If a concurrent takeover
// displaced the lock, the displaced holder fails closed at its next write
// BEFORE the next fetch — two processes can never both continue fetching
// under the same run id.
//
// A live holder stops the competing run with SAFETY_ERROR before it can
// read or overwrite run state. The lock is held until releaseRunLock and
// released in finally on every path.
function readRunLockToken(lockDir, fsImpl) {
    try {
        return String(fsImpl.readFileSync(path.join(lockDir, 'pid'), 'utf8') || '').trim() || null;
    } catch {
        return null;
    }
}

function parseRunLockToken(token) {
    const m = /^pid:(\d+):/.exec(String(token || ''));
    return m ? Number(m[1]) : null;
}

// R13-P1: the kernel's process-start identity — /proc/<pid>/stat field 22
// (starttime, clock ticks since boot). Two distinct process instances can
// never share (pid, starttime), so this distinguishes a recycled pid from
// the recorded holder. Null when the pid does not exist or /proc is
// unavailable (non-Linux / unreadable).
function readProcStarttimeTicks(pid, fsImpl = fs) {
    try {
        const stat = String(fsImpl.readFileSync(`/proc/${pid}/stat`, 'utf8') || '');
        const closeParen = stat.lastIndexOf(')');
        if (closeParen < 0) return null;
        // Fields after the closing paren restart at state=1; starttime is
        // field 20 there (22 overall, including pid and comm).
        const fields = stat.slice(closeParen + 1).trim().split(/\s+/);
        const starttime = Number(fields[19]);
        return Number.isFinite(starttime) ? starttime : null;
    } catch {
        return null;
    }
}

function parseRunLockStartTicks(token) {
    const m = /^pid:\d+:(\d+):/.exec(String(token || ''));
    return m ? Number(m[1]) : null;
}

// R13-P1: is the recorded holder INSTANCE alive? Instance-identity check
// when the token records start ticks and /proc is readable; pid-liveness
// fallback otherwise (legacy tokens, non-Linux, unreadable-but-alive pids).
function isHolderAlive(holderPid, holderStartTicks, isPidAlive, fsImpl) {
    if (holderStartTicks !== null) {
        const currentTicks = readProcStarttimeTicks(holderPid, fsImpl);
        if (currentTicks !== null && currentTicks !== holderStartTicks) {
            // The pid is alive (kill would say so) but belongs to a
            // DIFFERENT process instance — the recorded holder crashed and
            // its pid was recycled. Stale.
            return false;
        }
        if (currentTicks === holderStartTicks) {
            return true; // the same instance still runs
        }
        // /proc unreadable for this pid — fall through to pid-liveness.
    }
    return isPidAlive(holderPid);
}

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
    const ourStartTicks = readProcStarttimeTicks(pid, fsImpl);
    const ourToken = `pid:${pid}:${ourStartTicks === null ? '' : ourStartTicks}:${process.hrtime.bigint()}`;
    const lockDir = path.join(runDir, RUN_LOCK_DIR_NAME);
    for (let attempt = 0; attempt < 2; attempt += 1) {
        const tmpDir = path.join(runDir, `${RUN_LOCK_DIR_NAME}.tmp.${pid}.${Date.now()}`);
        try {
            fsImpl.mkdirSync(tmpDir);
            fsImpl.writeFileSync(path.join(tmpDir, 'pid'), ourToken, 'utf8');
            // Atomic publish: the lock dir appears complete (dir + token).
            // rename over an existing EMPTY dir replaces it (a crashed
            // holder's empty lock); over a complete lock it fails ENOTEMPTY.
            fsImpl.renameSync(tmpDir, lockDir);
        } catch (err) {
            // Best effort cleanup of OUR temp dir (never anyone else's).
            try { fsImpl.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
            if (!err || (err.code !== 'EEXIST' && err.code !== 'ENOTEMPTY')) {
                throw Object.assign(
                    new Error(`SAFETY_ERROR:run lock could not be created: ${String(err && err.message || err)}`),
                    { code: 'SAFETY_ERROR' }
                );
            }
            // Lock exists: evaluate the CURRENT token. R13-P1 + R16-P1:
            // liveness is decided by PROCESS INSTANCE (recorded start ticks
            // vs the pid's current /proc identity), never by pid liveness
            // alone — a recycled pid must not keep a crashed holder's lock
            // alive, and PID EQUALITY MUST NOT be treated as takeable: a
            // concurrent executeCaptureRun() in the SAME process (same pid,
            // same start ticks, different nonce) is a LIVE holder of the
            // same run id and fails closed instead of stealing the lock
            // mid-request (two real requests consumed for one pair).
            const token = readRunLockToken(lockDir, fsImpl);
            const holderPid = parseRunLockToken(token);
            const holderStartTicks = parseRunLockStartTicks(token);
            if (holderPid !== null
                && isHolderAlive(holderPid, holderStartTicks, isPidAlive, fsImpl)) {
                throw Object.assign(
                    new Error(`SAFETY_ERROR:another capture process (pid ${holderPid}) holds the run lock`),
                    { code: 'SAFETY_ERROR' }
                );
            }
            // Stale (dead holder, or a token-less lock — only a crashed
            // holder can produce one): take over exactly once and retry.
            if (attempt === 0) {
                // ATOMIC GRAB: rename the lock dir to OUR private trash
                // name. Whatever sits at the lock path at this instant is
                // what we get — and only we can reach the trash name.
                const trash = path.join(runDir, `${RUN_LOCK_DIR_NAME}.trash.${pid}.${Date.now()}`);
                try {
                    fsImpl.renameSync(lockDir, trash);
                } catch { continue; } // raced out — the retry re-evaluates
                const movedToken = readRunLockToken(trash, fsImpl);
                if (String(movedToken ?? '') === String(token ?? '')) {
                    // The moved dir still carries the EXACT token we
                    // verified as stale — delete it and retry the publish.
                    try { fsImpl.rmSync(trash, { recursive: true, force: true }); } catch { /* best effort */ }
                } else {
                    // The lock changed between evaluation and grab: a NEW
                    // owner's lock was moved. Restore it — never delete a
                    // token we did not verify.
                    try {
                        fsImpl.renameSync(trash, lockDir);
                    } catch {
                        // lockDir occupied again — the displaced owner will
                        // fail its own ownership re-verification before its
                        // next state write; leave the moved lock in trash.
                    }
                }
                continue;
            }
            throw Object.assign(
                new Error('SAFETY_ERROR:run lock could not be acquired'),
                { code: 'SAFETY_ERROR' }
            );
        }
        // Owned — verify OUR token is at the lock path (R11-P1 / R12-P1).
        if (readRunLockToken(lockDir, fsImpl) !== ourToken) {
            throw Object.assign(
                new Error('SAFETY_ERROR:run lock ownership lost during acquisition'),
                { code: 'SAFETY_ERROR' }
            );
        }
        return { lockDir, ourToken };
    }
    /* istanbul ignore next -- loop always returns or throws */
    throw Object.assign(new Error('SAFETY_ERROR:run lock could not be acquired'), { code: 'SAFETY_ERROR' });
}

function releaseRunLock(runDir, runLock, fsImpl = fs) {
    if (!runLock || !runLock.lockDir) return;
    const { lockDir, ourToken } = runLock;
    // Atomic rename-verify-restore: move whatever is at the lock path to a
    // private trash name, delete it ONLY if it still carries OUR token;
    // otherwise restore it (a takeover displaced us — never delete).
    const trash = path.join(runDir, `${RUN_LOCK_DIR_NAME}.trash.${process.pid}.${Date.now()}`);
    try {
        fsImpl.renameSync(lockDir, trash);
    } catch { return; /* already released */ }
    if (readRunLockToken(trash, fsImpl) === ourToken) {
        try { fsImpl.rmSync(trash, { recursive: true, force: true }); } catch { /* best effort */ }
    } else {
        try {
            fsImpl.renameSync(trash, lockDir);
        } catch { /* occupied again — leave the moved lock; its owner re-verifies */ }
    }
}

function verifyRunLockOwnership(runLock, fsImpl = fs) {
    if (!runLock || !runLock.lockDir) return;
    if (readRunLockToken(runLock.lockDir, fsImpl) !== runLock.ourToken) {
        throw Object.assign(
            new Error('SAFETY_ERROR:run lock ownership lost — another process took over the run lock'),
            { code: 'SAFETY_ERROR' }
        );
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
    // R12-P1 (Codex re-review on cf500786e): the holder additionally
    // re-verifies ownership of the lock token before EVERY run-state write
    // (writeRunStateLocked) — a displaced holder fails closed at its next
    // write, so two processes can never both keep fetching under this id.
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
        }, runLock);
    } finally {
        releaseRunLock(runDir, runLock, fsImpl);
    }
}

/* eslint-disable-next-line complexity */
async function executeCaptureRunLocked(options, plan, binding, delayMs, fsImpl, now, parser, dirs, runLock) {
    const { runsDir, runDir, capturesDir, replayDir } = dirs;

    // R12-P1: every run-state write first re-verifies that we still hold
    // the run lock's ownership token — fail closed at the next write if a
    // concurrent takeover displaced us (before the next fetch can issue).
    const writeRunStateLocked = (runState) => {
        verifyRunLockOwnership(runLock, fsImpl);
        writeRunState(runDir, runState, fsImpl);
    };

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
        writeRunStateLocked(runState);
    }

    // Transport observations document: same bindings as run state. It is a
    // NEW bounded telemetry file (the run-state schema is unchanged — resume
    // semantics of old v1 runs are untouched); a stale or foreign
    // observations file must fail closed rather than be silently adopted.
    let observationsDoc = null;
    try {
        observationsDoc = readTransportObservationsFile(runDir, fsImpl);
    } catch (err) {
        throw Object.assign(
            new Error(`SAFETY_ERROR:transport observations file unreadable: ${String(err.message)}`),
            { code: 'SAFETY_ERROR' }
        );
    }
    if (observationsDoc) {
        if (String(observationsDoc.run_id || '') !== binding.runId) {
            throw Object.assign(
                new Error('SAFETY_ERROR:transport observations run id mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(observationsDoc.plan_sha256 || '') !== plan.plan_business_sha256) {
            throw Object.assign(
                new Error('SAFETY_ERROR:transport observations plan SHA mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(observationsDoc.authorization_id || '') !== binding.authorizationId) {
            throw Object.assign(
                new Error('SAFETY_ERROR:transport observations authorization id mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (Number(observationsDoc.max_requests) !== binding.maxRequests) {
            throw Object.assign(
                new Error('SAFETY_ERROR:transport observations max-requests contract mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (String(observationsDoc.collector_code_revision || '') !== binding.collectorCodeRevision) {
            throw Object.assign(
                new Error('SAFETY_ERROR:transport observations collector revision mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
    } else {
        observationsDoc = defaultObservationsDoc({
            runId: binding.runId,
            planSha256: plan.plan_business_sha256,
            authorizationId: binding.authorizationId,
            maxRequests: binding.maxRequests,
            collectorCodeRevision: binding.collectorCodeRevision,
        });
    }
    // Base doc = the file as it exists at run start (null when absent).
    // In-place settlement evolves it; the final write passes it back so a
    // resume's in-place evolution is recognized as the run's own write and
    // never refused as "different valid content".
    const baseObservationsDoc = observationsDoc;
    // Diagnostic-only settlement: a telemetry persistence failure NEVER
    // changes the run outcome or fail-stop behavior of the capture itself.
    const settleObservation = (observation) => {
        if (!observation) return;
        try {
            observationsDoc = settleObservationInDoc(observationsDoc, observation);
        } catch { /* diagnostic-only — the run continues unchanged */ }
    };

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
        // R24-P1 (Codex re-review on 0e0ba8988): the marker decision is made
        // REGARDLESS of the deadline — a state written before 05cd23c55
        // carries neither next_allowed_request_at nor fetch_in_flight, and
        // such a legacy process could have died in the crash window with its
        // persisted request time still antedating the true fetch start.
        // Whenever the marker is NOT an explicit `false` (true / null /
        // absent), the gate executes the FULL delay from the recovery moment
        // — with or without a deadline. Only an explicit `false` (proof of
        // settlement) may use the exact anchors below.
        if (runState.fetch_in_flight !== false) {
            // R22-P1 (Codex re-review on 0bc69dad9): the run-state file's
            // mtime is NOT a reliable write-completion moment — writeRunState
            // persists via temp+rename and real filesystems keep the TEMP
            // file's write mtime (rename never refreshes the target's mtime,
            // and the kernel sets mtime during the write syscalls, before
            // writeFileSync returns). A gate anchored at mtime could still
            // antedate the true fetch start. The crash-window decision now
            // uses the persisted `fetch_in_flight` marker instead: it is set
            // TRUE by the LAST pre-fetch write and cleared by both
            // actualization writes. A true marker means the prior process
            // died with a request possibly in flight — the gate executes the
            // FULL delay from the recovery moment (Codex's suggested remedy:
            // no assumption about when the write completed, and recovery
            // always follows the true fetch start).
            // R23-P1 (Codex re-review on ab6aca8ca): only an EXPLICIT `false`
            // is proof of settlement. A MISSING marker is a LEGACY state
            // written by 0bc69dad9 or earlier — that process could have died
            // in the crash window (fetch started, actualization never landed)
            // with its deadline still antedating the true fetch start, so the
            // absent marker must NOT take the exact deadline path. Absent (or
            // any non-false) marker → FULL delay from the recovery moment.
            // (An explicit null is rejected by the read-side validator before
            // seeding; the non-false branch would also treat it
            // conservatively, belt and suspenders.)
            initialLastRequestAt = now();
        } else {
            // Settled state. R20-P1 (Codex re-review on 0bfe90629): the
            // persisted next_allowed_request_at DEADLINE is the exact anchor —
            // deadline − delayMs equals the true fetch start for every request
            // whose actualization write landed. A present-but-invalid deadline
            // fails closed (tampering); an absent deadline (a pre-05cd23c55
            // SETTLED state) keeps the timestamp formula — its actualized
            // value IS the true fetch start.
            const deadlineRaw = runState.next_allowed_request_at;
            if (deadlineRaw !== undefined && deadlineRaw !== null && String(deadlineRaw).trim() !== '') {
                const deadlineMs = Date.parse(String(deadlineRaw));
                if (Number.isNaN(deadlineMs)) {
                    throw Object.assign(
                        new Error('SAFETY_ERROR:invalid next_allowed_request_at in run state'),
                        { code: 'SAFETY_ERROR' }
                    );
                }
                // R21-P2 (Codex re-review on 05cd23c55): when the deadline is
                // present it is a fail-closed GATE — it must equal the
                // persisted request time + delayMs exactly (every legit write
                // maintains this invariant). A syntactically valid but EARLY
                // deadline (tampered below last + delayMs) would loosen the
                // gate and let the next request start before the full delay;
                // the read-side validator rejects it too, belt and suspenders.
                const lastMs = Date.parse(String(runState.last_network_request_attempted_at));
                if (!Number.isNaN(lastMs) && deadlineMs !== lastMs + delayMs) {
                    throw Object.assign(
                        new Error(
                            'SAFETY_ERROR:next_allowed_request_at must equal last_network_request_attempted_at + delay_ms in run state'
                        ),
                        { code: 'SAFETY_ERROR' }
                    );
                }
                initialLastRequestAt = new Date(deadlineMs - delayMs).toISOString();
            }
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
            // P2 (Codex round-2 review on 85bc0ee43): the pre-fetch attempt
            // timestamp is taken ONCE per write so the crash-window value is
            // internally consistent (separate now() calls could straddle a
            // millisecond boundary). R20-P1: this is the CRASH-WINDOW seed —
            // the pipeline ACTUALIZES the persisted
            // last_network_request_attempted_at to the adapter's true
            // fetch-start after the fetch, so the manifest, the run-state and
            // the cross-process resume gate all settle on the real request
            // start (which covers the last pre-fetch write's duration).
            const attemptAt = now();
            runState.network_requests_attempted = priorNetworkRequests + runNetworkRequests;
            runState.network_requests_made = runState.network_requests_attempted;
            runState.real_fotmob_network_requests = runState.network_requests_attempted;
            runState.last_network_request_attempted_at = attemptAt;
            // R22-P1 (Codex re-review on 0bc69dad9): no request is in flight
            // yet at write-1 — the marker stays false until the LAST
            // pre-fetch write flips it to true, and both actualization
            // writes clear it. A true marker on disk means the prior process
            // died with a request possibly in flight.
            runState.fetch_in_flight = false;
            // R20-P1 (Codex re-review on 0bfe90629): the persisted
            // next-allowed-request DEADLINE covers the last pre-fetch
            // run-state write's duration. EVERY pre-fetch write refreshes it
            // (a crash mid-path must never leave a stale past deadline from a
            // previous request); the actualization after the request settles
            // overwrites it with the exact true-fetch-start deadline.
            runState.next_allowed_request_at = new Date(Date.parse(attemptAt) + delayMs).toISOString();
            runState.updated_at = attemptAt;
            writeRunStateLocked(runState);
            // R19-P1 (Codex re-review on 52fadcf09): the synchronous write
            // above is part of the pre-fetch path and takes real time — the
            // native fetch only starts AFTER it completes, so an anchor
            // taken before it is still too early: with state-write
            // durations that vary between requests, the real gap between
            // two request STARTS could fall below delayMs. Re-take the
            // ACTUAL fetch-start moment AFTER the write and persist it
            // (one follow-up write), so the pacing anchor, the manifest and
            // the cross-process resume seed all agree on the same
            // conservative post-write instant. (R20-P1: this persisted value
            // is the crash-window seed — the pipeline actualizes the
            // authoritative resume value to the adapter's true fetch-start
            // moment after the fetch.)
            const actualAt = now();
            runState.last_network_request_attempted_at = actualAt;
            // R20-P1: the crash-window deadline uses the LATEST pre-fetch
            // moment available (post-write-1, pre-write-2) — the tightest
            // value a pre-fetch write can carry.
            runState.next_allowed_request_at = new Date(Date.parse(actualAt) + delayMs).toISOString();
            // R22-P1 (Codex re-review on 0bc69dad9): the LAST pre-fetch
            // write marks the request as possibly in flight. The native
            // fetch starts immediately after this write completes; if the
            // process hard-crashes before the actualization, the resume
            // gate sees the true marker and executes the FULL delay from
            // the recovery moment — no mtime assumption.
            runState.fetch_in_flight = true;
            runState.updated_at = actualAt;
            writeRunStateLocked(runState);
            // Return the actual attempt timestamp (post-write-1) for
            // compatibility — the adapter re-stamps the fetch result with its
            // OWN post-callback moment (R20-P1), so the authoritative
            // manifest / resume value is the true fetch start.
            return actualAt;
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
                expectedLeagueId: REQUIRED_LEAGUE_ID,
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
            fetchResult = await budgetedFetch.fetchOnce(requestUrl, {
                ordinal,
                sourceMatchId: candidate.source_match_id,
            });
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
            // R20-P1 (Codex re-review on 0bfe90629): ACTUALIZE the persisted
            // resume seed with the adapter's TRUE fetch-start moment (taken
            // after every pre-fetch write, microseconds before the native
            // request). The pre-fetch callback persisted an earlier value
            // (taken before its own last write); keeping it would make a
            // cross-process resume wait from a moment one write-duration
            // before the real request start — the real gap could fall below
            // delayMs. The manifest and the run-state use the SAME value, so
            // the single-timestamp invariant is preserved.
            runState.last_network_request_attempted_at = requestAttemptedAt;
            // R20-P1: actualize the persisted next-allowed-request deadline
            // with the SAME true fetch start — the resume gate waits until
            // F + delayMs exactly; the callback's crash-window deadline is
            // overwritten here for every request whose process survives.
            const deadlineMs = Date.parse(String(requestAttemptedAt));
            if (!Number.isNaN(deadlineMs)) {
                runState.next_allowed_request_at = new Date(deadlineMs + delayMs).toISOString();
            }
            // R22-P1 (Codex re-review on 0bc69dad9): the request SETTLED — the
            // in-flight marker is cleared in the SAME write as the
            // actualization, so a true marker on disk can only mean the
            // actualization never landed.
            runState.fetch_in_flight = false;
            writeRunStateLocked(runState);
            // Diagnostic-only: settle the success-path transport observation
            // into the in-memory document (never persisted here — the final
            // settlement happens once at run end).
            settleObservation(fetchResult.transportObservation);
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
            // R20-P1: the failure path actualizes the seed too — the adapter
            // attaches the TRUE fetch-start moment to the thrown error (the
            // attempt DID reach the network, so a resume must wait the full
            // delay from the real start). Budget-exhausted / contract errors
            // carry no timestamp (no fetch started) and keep the prior value.
            if (err && err.requestAttemptedAt) {
                runState.last_network_request_attempted_at = String(err.requestAttemptedAt);
                // R20-P1: the failure path actualizes the deadline too — the
                // attempt DID reach the network, so a resume must wait the
                // full delay from the real request start.
                const deadlineMs = Date.parse(String(err.requestAttemptedAt));
                if (!Number.isNaN(deadlineMs)) {
                    runState.next_allowed_request_at = new Date(deadlineMs + delayMs).toISOString();
                }
            }
            // R22-P1 (Codex re-review on 0bc69dad9): the failure SETTLED (or
            // no fetch started at all — budget/contract errors) — the
            // in-flight marker is cleared in the same write as the failure
            // actualization, so a true marker on disk can only mean the
            // actualization never landed.
            runState.fetch_in_flight = false;
            writeRunStateLocked(runState);
            // Diagnostic-only: settle the failure-path transport observation
            // (timeout / abort / safety / read / fetch errors) into the
            // in-memory document. The observation never changes fail-stop.
            settleObservation(err.transportObservation);
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
        writeRunStateLocked(runState);
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
    writeRunStateLocked(runState);

    // Final settlement: exactly one bounded observations file per run,
    // written only when at least one observation exists, crash-safe and
    // never silently overwriting different content. Persistence failure is
    // diagnostic-only — the run outcome and fail-stop behavior are already
    // finalized above and cannot be changed by telemetry.
    if (observationsDoc.observations.length > 0) {
        try {
            writeTransportObservationsFile(runDir, observationsDoc, fsImpl, baseObservationsDoc);
        } catch { /* diagnostic-only — the run continues unchanged */ }
    }

    const summary = buildRunSummary(runState, plan, [...completedOrdinals], observationsDoc);
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
    acquireRunLock,
    releaseRunLock,
    verifyRunLockOwnership,
    readProcStarttimeTicks,
};
