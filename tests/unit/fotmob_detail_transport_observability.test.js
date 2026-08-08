'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
// Transport-phase observability tests for the bounded FotMob detail capture
// pipeline (FOTMOB_DETAIL_TRANSPORT_PHASE_OBSERVABILITY_PR).
//
// Fully offline: real network is structurally forbidden (global.fetch
// throws). Two allowed exception patterns per the owner contract:
//   - mock fetchImpl / stream implementations (no network at all);
//   - loopback HTTP servers bound to 127.0.0.1 ONLY (never 0.0.0.0), reached
//     through the adapter's injected fetchImpl — the adapter's URL gate still
//     validates the https://www.fotmob.com/match/<digits> shape before the
//     injected implementation is ever called, and the only global.fetch use
//     is the captured REAL_FETCH inside those loopback implementations.

const REAL_FETCH = globalThis.fetch; // captured BEFORE the guard — loopback tests only
global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');

const {
    buildDeterministicCapturePlan,
    writePlanDocument,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const { computeBusinessContentHash } = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const {
    executeCaptureRun,
    createBoundedFetchAdapter,
    REQUIRED_ENV_VAR,
    REQUIRED_ENV_BUDGET,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const {
    buildTransportObservation,
    defaultObservationsDoc,
    settleObservationInDoc,
    validateTransportObservation,
    validateObservationsDoc,
    computeObservationsSelfHash,
    readTransportObservationsFile,
    writeTransportObservationsFile,
    reconcilePersistedObservationsDoc,
    OBSERVATIONS_FILE_NAME,
    OBSERVATION_ENTRY_SCHEMA,
} = require('../../src/infrastructure/fotmob/FotMobTransportObservation');
const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const TEST_REVISION = 'a7da729fd29675c6f16e1bfc49511772d2bd590d';
const FIXED_CLOCK = '2026-08-02T12:00:00.000Z';
const CLEAN_EXEC = cmd => (String(cmd).includes('rev-parse') ? `${TEST_REVISION}\n` : '');

const OBSERVATIONS_PATH = runDir => path.join(runDir, OBSERVATIONS_FILE_NAME);

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function makeCandidate({ id, season, home, away, kickoff }) {
    return {
        id: String(id),
        source_provider: 'FotMob',
        source_match_id: String(id),
        competition: 'Premier League',
        season,
        home_team: home,
        away_team: away,
        kickoff_at: kickoff,
    };
}

function makeV1Artifact(candidates) {
    return {
        schema_version: 'candidate-match-identity/v1',
        extracted_at: '2026-07-17T18:51:14.657Z',
        snapshot: {
            source_provider: 'FotMob',
            league_id: 47,
            competition: 'Premier League',
            seasons: [...new Set(candidates.map(c => c.season))].sort(),
            candidate_count: candidates.length,
            business_content_sha256: computeBusinessContentHash(candidates),
        },
        candidates,
    };
}

function makePlanFixture(dir, candidates, { seasons, matchIds, limit } = {}) {
    const artifactPath = path.join(dir, 'artifact.json');
    fs.writeFileSync(artifactPath, JSON.stringify(makeV1Artifact(candidates), null, 2));
    const result = buildDeterministicCapturePlan({
        artifactPath,
        seasons: seasons || [],
        matchIds: matchIds || [],
        limit,
        generatedAt: FIXED_CLOCK,
        collectorCodeRevision: TEST_REVISION,
    });
    const planPath = path.join(dir, 'plan.json');
    writePlanDocument(result.plan, planPath);
    return { plan: result.plan, planPath };
}

function makePageHtml({ matchId, homeTeam, awayTeam, kickoffAt }) {
    const general = {
        matchId: String(matchId),
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        matchTimeUTC: kickoffAt,
        season: '2024/2025',
    };
    const header = {
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        status: { utcTime: kickoffAt },
    };
    const pageProps = {
        content: {
            stats: { periods: ['x'] },
            lineup: { lineups: [{ team: homeTeam }] },
            shotmap: { shots: [{ x: 1 }] },
            liveticker: [],
        },
        general,
        header,
        ssr: true,
    };
    const nextData = { props: { pageProps } };
    const json = JSON.stringify(nextData);
    return `<!doctype html><html><head></head><body><script id="__NEXT_DATA__" type="application/json">${json}</script><div class="app">${'x'.repeat(200)}</div></body></html>`;
}

function pageFor(candidate) {
    return makePageHtml({
        matchId: candidate.source_match_id,
        homeTeam: candidate.home_team,
        awayTeam: candidate.away_team,
        kickoffAt: candidate.kickoff_at,
    });
}

function mockFetchImpl(responseBuilder, calls = []) {
    return async (url, opts) => {
        calls.push({ url, opts });
        const r = responseBuilder(url, calls.length, opts);
        return {
            status: r.status,
            url,
            headers: {
                get: n =>
                    n === 'content-type'
                        ? r.contentType || 'text/html; charset=utf-8'
                        : n === 'location'
                          ? r.location || null
                          : null,
            },
            text: async () => r.body,
            arrayBuffer: async () => Buffer.from(r.body, 'utf8'),
        };
    };
}

function okResponse(body, contentType = 'text/html; charset=utf-8') {
    return { status: 200, body, contentType };
}

function makeCaptureOptions({
    dir,
    plan,
    planPath,
    runId,
    maxRequests,
    outputRoot,
    env,
    fetchImpl,
    sleepImpl,
    execSync,
    fsImpl,
    timeoutMs,
    extra,
}) {
    return {
        plan,
        planPath,
        expectedPlanSha256: plan.plan_business_sha256,
        authorizationId: 'test-authorization-id',
        maxRequests,
        outputRoot: outputRoot || path.join(dir, 'out'),
        runId: runId || 'run-test',
        execute: true,
        networkAuthorization: true,
        delayMs: 60000,
        timeoutMs: timeoutMs || 30000,
        sleepImpl: sleepImpl || (async () => {}),
        fetchImpl,
        parser: {
            extractFromHtml: NextDataParser.extractFromHtml,
            transformToApiFormat: NextDataParser.transformToApiFormat,
            parseFotMobRaw: FotMobRawParser.parseFotMobRaw,
        },
        now: () => FIXED_CLOCK,
        env: env || {
            [REQUIRED_ENV_VAR]: '1',
            [REQUIRED_ENV_BUDGET]: String(maxRequests),
            NETWORK_AUTHORIZATION: 'yes',
        },
        repositoryRoot: REPO_ROOT,
        execSync: execSync || CLEAN_EXEC,
        fsImpl,
    };
}

// ─────────────────────────────────────────────────────────────
// Response / stream mocks that mirror undici semantics
// ─────────────────────────────────────────────────────────────

/**
 * A body-reader mock whose read() behaves like undici's: chunks are
 * delivered in order; once exhausted the read STALLS and settles only when
 * the adapter's AbortSignal aborts (rejecting with an AbortError). Optional
 * real-time chunk delays exercise the abort-during-delivery window.
 * `state` records what actually happened (chunks delivered, stalled,
 * cancelled, aborted reads).
 */
function makeStallingReader({ chunks = [], chunkDelayMs = 0, signal = null, state = {} }) {
    let index = 0;
    const reader = {
        async read() {
            if (index < chunks.length) {
                const value = Buffer.from(chunks[index], 'utf8');
                index += 1;
                state.chunksDelivered = index;
                if (chunkDelayMs > 0) {
                    return new Promise(resolve => {
                        setTimeout(() => resolve({ done: false, value }), chunkDelayMs);
                    });
                }
                return { done: false, value };
            }
            state.stalled = true;
            return new Promise((resolve, reject) => {
                if (!signal) { return; } // test-only corner: never settles
                const onAbort = () => {
                    state.abortedReads = (state.abortedReads || 0) + 1;
                    const e = new Error('The operation was aborted');
                    e.name = 'AbortError';
                    reject(e);
                };
                if (signal.aborted) {
                    onAbort();
                    return;
                }
                signal.addEventListener('abort', onAbort, { once: true });
            });
        },
        cancel: async () => {
            state.cancelled = true;
        },
    };
    return reader;
}

function makeResponse({
    status = 200,
    contentType = 'text/html; charset=utf-8',
    location = null,
    contentLength = null,
    body = null,
    reader = null,
    state = {},
}) {
    return {
        status,
        url: 'https://www.fotmob.com/match/123',
        headers: {
            get: n => {
                const name = String(n || '').toLowerCase();
                if (name === 'content-type') return contentType;
                if (name === 'location') return location;
                if (name === 'content-length') return contentLength;
                return null;
            },
        },
        body: reader
            ? {
                  getReader: () => reader,
                  cancel: async () => {
                      state.cancelled = true;
                  },
              }
            : null,
        arrayBuffer: async () => (body === null ? new ArrayBuffer(0) : Buffer.from(body, 'utf8')),
    };
}

// fetchImpl that forwards the adapter's opts (including the AbortSignal) to
// the response builder — needed whenever the mock must react to aborts.
const signalFetchImpl = buildResponse => async (url, opts) => buildResponse({ url, opts });

function readObservations(runDir) {
    const doc = readTransportObservationsFile(runDir, fs);
    return doc;
}

// ─────────────────────────────────────────────────────────────
// P2-1 failure-injection fsImpl wrappers (telemetry paths only)
// ─────────────────────────────────────────────────────────────

/**
 * fsImpl wrapper that fails ONLY the transport-observations file WRITE
 * paths (writeFileSync / renameSync when the target path carries the
 * observations file name — including the temp+rename names). Every other
 * fs operation passes through to the base fs. Simulates a final telemetry
 * write failure (e.g. ENOSPC) while the rest of the run writes normally.
 */
function observationsWriteFailingFsImpl(base = fs) {
    return new Proxy(base, {
        get(target, prop) {
            const value = target[prop];
            if (prop === 'writeFileSync' || prop === 'renameSync') {
                return (...args) => {
                    const p = String(args[0] || '');
                    if (p.includes(OBSERVATIONS_FILE_NAME)) {
                        const err = new Error('ENOSPC: simulated telemetry write failure');
                        err.code = 'ENOSPC';
                        throw err;
                    }
                    return value.apply(target, args);
                };
            }
            return typeof value === 'function' ? value.bind(target) : value;
        },
    });
}

/**
 * fsImpl wrapper that fails the FIRST read of the transport-observations
 * file (simulates the write-internal read-back failing after the rename
 * landed — "read-back uncertainty where the intended document DID land").
 * Later reads pass through to the base fs.
 */
function observationsFirstReadFailingFsImpl(base = fs) {
    let failedOnce = false;
    return new Proxy(base, {
        get(target, prop) {
            const value = target[prop];
            if (prop === 'readFileSync') {
                return (...args) => {
                    const p = String(args[0] || '');
                    if (p.includes(OBSERVATIONS_FILE_NAME) && !failedOnce) {
                        failedOnce = true;
                        const err = new Error('EIO: simulated telemetry read-back failure');
                        err.code = 'EIO';
                        throw err;
                    }
                    return value.apply(target, args);
                };
            }
            return typeof value === 'function' ? value.bind(target) : value;
        },
    });
}

// ─────────────────────────────────────────────────────────────
// A. Observation entry builder + validation (fail closed)
// ─────────────────────────────────────────────────────────────

test('OBSERVATION: fast success entry carries exact phases, bytes and metadata', () => {
    const entry = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-06T17:39:04.538Z',
        requestFinishedAtIso: '2026-08-06T17:39:04.800Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-06T17:39:04.600Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-06T17:39:04.601Z',
        bodyBytesReceived: 120000,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-06T17:39:04.800Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: {
            content_type: 'text/html; charset=utf-8',
            declared_content_length: 120000,
            location_present: false,
            redirected: false,
        },
    });
    assert.equal(entry.schema_version, OBSERVATION_ENTRY_SCHEMA);
    assert.equal(entry.terminal_outcome, 'COMPLETED');
    assert.equal(entry.last_reliable_phase, 'RESPONSE_BODY_COMPLETED');
    assert.equal(entry.body_bytes_received, 120000);
    const check = validateTransportObservation(entry);
    assert.ok(check.ok, `entry must validate: ${check.errors.join('; ')}`);
});

test('OBSERVATION: no observation is built when no request started (budget/contract errors are not attempts)', () => {
    assert.equal(buildTransportObservation({ ordinal: 1, sourceMatchId: 'x' }), null);
    assert.equal(buildTransportObservation({ requestStartedAtIso: null }), null);
    assert.equal(buildTransportObservation({ requestStartedAtIso: '' }), null);
});

test('OBSERVATION: builder normalizes — negative/NaN numbers become 0, long strings bounded, unknown metadata keys dropped', () => {
    const entry = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-06T17:39:04.538Z',
        requestFinishedAtIso: '2026-08-06T17:39:04.800Z',
        elapsedMs: -5,
        lastReliablePhase: 'AWAITING_RESPONSE_HEADERS',
        terminalOutcome: 'TIMEOUT',
        responseHeadersReceived: false,
        httpStatus: 9999,
        bodyBytesReceived: Number.NaN,
        timeoutConfiguredMs: 30000,
        timeoutTriggered: true,
        abortSource: 'REQUEST_TIMEOUT',
        errorName: 'x'.repeat(500),
        errorCode: 'y'.repeat(500),
        errorCauseName: 'z'.repeat(500),
        errorCauseCode: 'w'.repeat(500),
        responseMetadata: {
            content_type: 'a'.repeat(5000),
            declared_content_length: 5,
            location_present: false,
            redirected: false,
            set_cookie: 'session=SECRET', // must never survive
            authorization: 'Bearer SECRET',
        },
    });
    assert.equal(entry.elapsed_ms, 0);
    assert.equal(entry.body_bytes_received, 0);
    assert.equal(entry.http_status, null);
    assert.equal(entry.error_name.length, 64);
    assert.equal(entry.error_code.length, 64);
    assert.equal(entry.error_cause_name.length, 64);
    assert.equal(entry.error_cause_code.length, 64);
    assert.equal(entry.response_metadata.content_type.length, 200);
    assert.deepEqual(Object.keys(entry.response_metadata).sort(), [
        'content_type',
        'declared_content_length',
        'location_present',
        'redirected',
    ]);
    assert.equal(entry.response_metadata.set_cookie, undefined);
    assert.equal(entry.response_metadata.authorization, undefined);
});

test('OBSERVATION: validator fails closed on invalid phases, negative bytes, invalid timestamps, impossible states', () => {
    const base = {
        schema_version: OBSERVATION_ENTRY_SCHEMA,
        ordinal: 1,
        source_match_id: '4193752',
        request_started_at: '2026-08-06T17:39:04.538Z',
        request_finished_at: '2026-08-06T17:39:04.800Z',
        elapsed_ms: 262,
        last_reliable_phase: 'AWAITING_RESPONSE_HEADERS',
        terminal_outcome: 'TIMEOUT',
        response_headers_received: false,
        response_headers_received_at: null,
        http_status: null,
        body_reading_started: false,
        body_reading_started_at: null,
        body_bytes_received: 0,
        body_completed: false,
        body_completed_at: null,
        timeout_configured_ms: 30000,
        timeout_triggered: true,
        abort_source: 'REQUEST_TIMEOUT',
        error_name: 'AbortError',
        error_code: null,
        error_cause_name: null,
        error_cause_code: null,
        response_metadata: null,
    };
    assert.ok(validateTransportObservation(base).ok);
    assert.ok(!validateTransportObservation({ ...base, last_reliable_phase: 'NOT_A_PHASE' }).ok);
    assert.ok(!validateTransportObservation({ ...base, terminal_outcome: 'NOT_AN_OUTCOME' }).ok);
    assert.ok(!validateTransportObservation({ ...base, body_bytes_received: -1 }).ok);
    assert.ok(!validateTransportObservation({ ...base, body_bytes_received: Number.MAX_SAFE_INTEGER + 1 }).ok);
    assert.ok(!validateTransportObservation({ ...base, request_started_at: 'not-a-timestamp' }).ok);
    assert.ok(!validateTransportObservation({ ...base, timeout_triggered: false }).ok, 'TIMEOUT requires the flag');
    assert.ok(!validateTransportObservation({ ...base, abort_source: 'EXTERNAL_ABORT' }).ok);
    assert.ok(!validateTransportObservation({ ...base, timeout_configured_ms: 0 }).ok);
    assert.ok(!validateTransportObservation({ ...base, ordinal: 0 }).ok);
    // Headers + bytes must be consistent with the phase.
    assert.ok(
        !validateTransportObservation({
            ...base,
            response_headers_received: true,
            response_headers_received_at: '2026-08-06T17:39:04.600Z',
            http_status: 200,
        }).ok
    );
    // COMPLETED cannot carry errors or a timeout flag.
    const completed = {
        ...base,
        terminal_outcome: 'COMPLETED',
        timeout_triggered: false,
        abort_source: null,
        error_name: null,
        error_code: null,
        response_headers_received: true,
        response_headers_received_at: '2026-08-06T17:39:04.600Z',
        http_status: 200,
        body_reading_started: true,
        body_reading_started_at: '2026-08-06T17:39:04.601Z',
        body_completed: true,
        body_completed_at: '2026-08-06T17:39:04.800Z',
        last_reliable_phase: 'RESPONSE_BODY_COMPLETED',
    };
    assert.ok(validateTransportObservation(completed).ok);
    assert.ok(!validateTransportObservation({ ...completed, error_name: 'Error' }).ok);
    assert.ok(!validateTransportObservation({ ...completed, timeout_triggered: true }).ok);
    // Reading body requires headers; body completed requires reading started.
    assert.ok(
        !validateTransportObservation({
            ...base,
            terminal_outcome: 'BODY_READ_ERROR',
            error_name: 'Error',
            body_reading_started: true,
            body_reading_started_at: '2026-08-06T17:39:04.601Z',
        }).ok
    );
});

test('OBSERVATION: doc validation fails closed — schema, bounds, duplicates, order, self-hash', () => {
    const ctx = {
        runId: 'run-1',
        planSha256: 'a'.repeat(64),
        authorizationId: 'AUTH',
        maxRequests: 2,
        collectorCodeRevision: 'b'.repeat(40),
    };
    let doc = defaultObservationsDoc(ctx);
    assert.ok(validateObservationsDoc(doc).ok);
    assert.equal(doc.observations_sha256, computeObservationsSelfHash(doc));

    const entry = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-06T17:39:04.538Z',
        requestFinishedAtIso: '2026-08-06T17:39:04.800Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-06T17:39:04.600Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-06T17:39:04.601Z',
        bodyBytesReceived: 100,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-06T17:39:04.800Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: null,
    });
    doc = settleObservationInDoc(doc, entry);
    assert.ok(validateObservationsDoc(doc).ok);
    assert.equal(doc.observations.length, 1);
    assert.ok(!validateObservationsDoc({ ...doc, schema_version: 'fotmob-detail-transport-observations/v2' }).ok);
    assert.ok(!validateObservationsDoc({ ...doc, run_id: '' }).ok);
    assert.ok(!validateObservationsDoc({ ...doc, plan_sha256: 'zz' }).ok);
    assert.ok(!validateObservationsDoc({ ...doc, collector_code_revision: 'zz' }).ok);
    assert.ok(!validateObservationsDoc({ ...doc, max_requests: 0 }).ok);
    assert.ok(!validateObservationsDoc({ ...doc, observations_sha256: 'f'.repeat(64) }).ok, 'tampered self-hash fails');
    assert.ok(!validateObservationsDoc({ ...doc, observations: [] }).ok, 'stale hash fails when entries change');

    // Bounds: more entries than max_requests, duplicates, disorder.
    const docBig = defaultObservationsDoc(ctx);
    const e2 = buildTransportObservation({
        ordinal: 2,
        sourceMatchId: '4506625',
        requestStartedAtIso: '2026-08-06T17:40:04.538Z',
        requestFinishedAtIso: '2026-08-06T17:40:04.900Z',
        elapsedMs: 362,
        lastReliablePhase: 'AWAITING_RESPONSE_HEADERS',
        terminalOutcome: 'TIMEOUT',
        responseHeadersReceived: false,
        httpStatus: null,
        bodyBytesReceived: 0,
        timeoutConfiguredMs: 30000,
        timeoutTriggered: true,
        abortSource: 'REQUEST_TIMEOUT',
        errorName: 'AbortError',
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: null,
    });
    const settled = settleObservationInDoc(docBig, entry);
    assert.ok(validateObservationsDoc(settleObservationInDoc(settled, e2)).ok);
    const three = settleObservationInDoc(settleObservationInDoc(settled, e2), {
        ...entry,
        ordinal: 3,
    });
    assert.ok(!validateObservationsDoc(three).ok, '3 entries > max_requests 2');
    // duplicate ordinal: settle replaces (last attempt wins) — no duplicates
    const replaced = settleObservationInDoc(settleObservationInDoc(docBig, entry), {
        ...entry,
        body_bytes_received: 999,
    });
    assert.equal(replaced.observations.length, 1);
    assert.equal(replaced.observations[0].body_bytes_received, 999);
    assert.ok(validateObservationsDoc(replaced).ok);
});

// ─────────────────────────────────────────────────────────────
// B. Adapter transport-phase behavior (the 7 owner scenarios)
// ─────────────────────────────────────────────────────────────

test('TRANSPORT: fast success — all phases reached, exact bytes, timer cleaned, no timeout classification', async () => {
    const state = {};
    const adapter = createBoundedFetchAdapter({
        fetchImpl: signalFetchImpl(() =>
            makeResponse({
                body: 'hello-world',
                contentType: 'text/html; charset=utf-8',
                state,
            })
        ),
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    const res = await adapter.fetchOnce('https://www.fotmob.com/match/123', { ordinal: 1, sourceMatchId: '123' });
    const obs = res.transportObservation;
    assert.equal(obs.terminal_outcome, 'COMPLETED');
    assert.equal(obs.last_reliable_phase, 'RESPONSE_BODY_COMPLETED');
    assert.equal(obs.response_headers_received, true);
    assert.equal(obs.http_status, 200);
    assert.equal(obs.body_reading_started, true);
    assert.equal(obs.body_completed, true);
    assert.equal(obs.body_bytes_received, Buffer.byteLength('hello-world'));
    assert.equal(obs.timeout_triggered, false);
    assert.equal(obs.abort_source, null);
    assert.equal(obs.response_metadata.content_type, 'text/html; charset=utf-8');
    assert.equal(obs.response_metadata.declared_content_length, 0, 'no declared length header → 0');
    assert.equal(obs.response_metadata.redirected, false);
    assert.equal(obs.error_name, null);
    assert.ok(validateTransportObservation(obs).ok);
});

test('TRANSPORT: SCENARIO A — headers delayed past the timeout → AWAITING_RESPONSE_HEADERS, no headers, 0 bytes, TIMEOUT, no retry', async () => {
    const calls = [];
    const state = {};
    const adapter = createBoundedFetchAdapter({
        fetchImpl: (url, opts) =>
            new Promise((resolve, reject) => {
                calls.push(url);
                opts.signal.addEventListener('abort', () => {
                    const e = new Error('This operation was aborted');
                    e.name = 'AbortError';
                    reject(e);
                });
            }),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 60,
    });
    let err = null;
    try {
        await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err = e;
    }
    assert.ok(err, 'must reject');
    assert.ok(err.transportObservation, 'the observation rides the error');
    const obs = err.transportObservation;
    // Owner minimum-capability spec, scenario A — verbatim field contract.
    assert.equal(obs.last_reliable_phase, 'AWAITING_RESPONSE_HEADERS');
    assert.equal(obs.response_headers_received, false);
    assert.equal(obs.body_reading_started, false);
    assert.equal(obs.body_bytes_received, 0);
    assert.equal(obs.terminal_outcome, 'TIMEOUT');
    assert.equal(obs.timeout_triggered, true);
    assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
    assert.equal(obs.body_completed, false);
    assert.equal(obs.http_status, null);
    assert.equal(obs.response_metadata, null);
    assert.ok(validateTransportObservation(obs).ok);
    // retry=0: exactly one fetch attempt happened.
    assert.equal(calls.length, 1);
});

test('TRANSPORT: SCENARIO B — headers immediate, body never returns → READING_RESPONSE_BODY, headers true, http status real, body incomplete', async () => {
    const state = {};
    const adapter = createBoundedFetchAdapter({
        fetchImpl: signalFetchImpl(({ opts }) =>
            makeResponse({
                status: 200,
                contentType: 'text/html; charset=utf-8',
                reader: makeStallingReader({ signal: opts.signal, state }),
                state,
            })
        ),
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 60,
    });
    let err = null;
    try {
        await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err = e;
    }
    assert.ok(err, 'must reject');
    const obs = err.transportObservation;
    // Owner minimum-capability spec, scenario B — verbatim field contract.
    assert.equal(obs.last_reliable_phase, 'READING_RESPONSE_BODY');
    assert.equal(obs.response_headers_received, true);
    assert.equal(obs.http_status, 200);
    assert.equal(obs.body_reading_started, true);
    assert.equal(obs.body_bytes_received, 0);
    assert.equal(obs.body_completed, false);
    assert.equal(obs.terminal_outcome, 'TIMEOUT');
    assert.equal(obs.timeout_triggered, true);
    assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
    assert.equal(obs.response_metadata.content_type, 'text/html; charset=utf-8');
    assert.ok(validateTransportObservation(obs).ok);
    assert.ok(state.stalled, 'the body read stalled and only the abort settled it');
    assert.ok(state.abortedReads >= 1, 'the stalled read settled on abort');
});

test('TRANSPORT: partial body then stall → exact accumulated bytes, no completion, stream released on abort', async () => {
    const state = {};
    const adapter = createBoundedFetchAdapter({
        fetchImpl: signalFetchImpl(({ opts }) =>
            makeResponse({
                status: 200,
                reader: makeStallingReader({ chunks: ['aaaa', 'bbbb'], signal: opts.signal, state }),
                state,
            })
        ),
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 60,
    });
    let err = null;
    try {
        await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err = e;
    }
    assert.ok(err, 'must reject');
    const obs = err.transportObservation;
    assert.equal(obs.last_reliable_phase, 'READING_RESPONSE_BODY');
    assert.equal(obs.body_bytes_received, 8, 'exact accumulated byte count');
    assert.equal(obs.body_completed, false);
    assert.equal(obs.terminal_outcome, 'TIMEOUT');
    assert.equal(obs.timeout_triggered, true);
    assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
    assert.ok(validateTransportObservation(obs).ok);
    assert.equal(state.chunksDelivered, 2, 'exactly two chunks were delivered');
    assert.ok(state.stalled, 'stall reached before the abort');
    // No dangling read: the stalled read settled (rejected) on abort.
    assert.ok(state.abortedReads >= 1);
});

test('TRANSPORT: a non-timeout fetch error is FETCH_ERROR — never TIMEOUT, even when the message says "aborted"', async () => {
    // 1) Plain rejection, no signal, no timer.
    const adapter1 = createBoundedFetchAdapter({
        fetchImpl: async () => {
            throw new TypeError('fetch failed');
        },
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    let err1 = null;
    try {
        await adapter1.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err1 = e;
    }
    const obs1 = err1.transportObservation;
    assert.equal(obs1.terminal_outcome, 'FETCH_ERROR');
    assert.equal(obs1.timeout_triggered, false);
    assert.equal(obs1.abort_source, null);
    assert.equal(obs1.error_name, 'TypeError');
    assert.equal(obs1.last_reliable_phase, 'AWAITING_RESPONSE_HEADERS');
    assert.equal(obs1.response_headers_received, false);
    assert.ok(validateTransportObservation(obs1).ok);

    // 2) "This operation was aborted" message WITHOUT the local timer flag —
    // an external/user abort must classify ABORTED/EXTERNAL_ABORT, never
    // REQUEST_TIMEOUT (owner: never classify a timeout from error text).
    const adapter2 = createBoundedFetchAdapter({
        fetchImpl: async () => {
            throw new Error('This operation was aborted');
        },
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    let err2 = null;
    try {
        await adapter2.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err2 = e;
    }
    const obs2 = err2.transportObservation;
    assert.equal(obs2.terminal_outcome, 'ABORTED');
    assert.equal(obs2.abort_source, 'EXTERNAL_ABORT');
    assert.equal(obs2.timeout_triggered, false);
    assert.notEqual(obs2.terminal_outcome, 'TIMEOUT');
    assert.ok(validateTransportObservation(obs2).ok);
});

test('TRANSPORT: oversized body — cap semantics unchanged, telemetry records actual bytes, stream canceled', async () => {
    // Declared-length overflow: rejected before any read; cancel called.
    const state1 = {};
    const adapter1 = createBoundedFetchAdapter({
        fetchImpl: signalFetchImpl(() =>
            makeResponse({
                status: 200,
                contentLength: String(MAX_BODY_BYTES + 1),
                reader: makeStallingReader({ chunks: ['x'], state: state1 }),
                state: state1,
            })
        ),
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    let err1 = null;
    try {
        await adapter1.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err1 = e;
    }
    assert.equal(err1.code, 'SAFETY_ERROR');
    assert.match(err1.message, /oversized_response_body:declared_/);
    const obs1 = err1.transportObservation;
    assert.equal(obs1.terminal_outcome, 'SAFETY_ERROR');
    assert.equal(obs1.body_reading_started, true, 'the body-read phase was entered');
    assert.equal(obs1.body_bytes_received, 0, 'no bytes were read');
    assert.equal(obs1.timeout_triggered, false);
    assert.equal(state1.cancelled, true, 'the declared-length path cancels the stream');
    assert.equal(state1.chunksDelivered, undefined, 'no chunk was read');
    assert.ok(validateTransportObservation(obs1).ok);

    // Chunked overflow: the cap fires mid-read; actual bytes are recorded.
    const bigChunk = Buffer.alloc(1024 * 1024, 'x').toString('utf8');
    const chunks = [];
    for (let i = 0; i < 9; i += 1) chunks.push(bigChunk);
    const state2 = {};
    const adapter2 = createBoundedFetchAdapter({
        fetchImpl: signalFetchImpl(() =>
            makeResponse({
                status: 200,
                reader: makeStallingReader({ chunks, state: state2 }),
                state: state2,
            })
        ),
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    let err2 = null;
    try {
        await adapter2.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err2 = e;
    }
    assert.equal(err2.code, 'SAFETY_ERROR');
    assert.match(err2.message, /oversized_response_body:stream_/);
    const obs2 = err2.transportObservation;
    assert.equal(obs2.terminal_outcome, 'SAFETY_ERROR');
    assert.ok(obs2.body_bytes_received > MAX_BODY_BYTES, 'actual received bytes exceed the cap');
    assert.equal(obs2.body_completed, false);
    assert.equal(state2.cancelled, true, 'the chunked path cancels the stream');
    assert.ok(validateTransportObservation(obs2).ok);
});

test('TRANSPORT: redirect stays manual — not followed, single request, observation marks redirected with no body read', async () => {
    const calls = [];
    const adapter = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl(() => ({ status: 302, body: '', location: 'https://www.fotmob.com/other' }), calls),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    const res = await adapter.fetchOnce('https://www.fotmob.com/match/123', { ordinal: 1, sourceMatchId: '123' });
    assert.equal(res.status, 302);
    assert.equal(res.redirected, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].opts.redirect, 'manual');
    const obs = res.transportObservation;
    assert.equal(obs.terminal_outcome, 'COMPLETED');
    assert.equal(obs.response_headers_received, true);
    assert.equal(obs.http_status, 302);
    assert.equal(obs.body_reading_started, false, 'a redirect body is never read');
    assert.equal(obs.body_completed, false);
    assert.equal(obs.body_bytes_received, 0);
    assert.equal(obs.response_metadata.redirected, true);
    assert.equal(obs.response_metadata.location_present, true);
    assert.ok(validateTransportObservation(obs).ok);
});

test('TRANSPORT: locationless redirect — 302 without a Location header still records redirected with no body read and validates', async () => {
    const calls = [];
    const adapter = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl(() => ({ status: 302, body: 'mock-redirect-body-not-read' }), calls),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    const res = await adapter.fetchOnce('https://www.fotmob.com/match/123', { ordinal: 1, sourceMatchId: '123' });
    assert.equal(res.status, 302);
    assert.equal(res.redirected, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].opts.redirect, 'manual');
    const obs = res.transportObservation;
    assert.equal(obs.terminal_outcome, 'COMPLETED');
    assert.equal(obs.http_status, 302);
    assert.equal(obs.body_reading_started, false, 'a redirect body is never read');
    assert.equal(obs.body_completed, false);
    assert.equal(obs.body_bytes_received, 0);
    assert.equal(obs.response_metadata.redirected, true, 'redirected is derived from the http status alone');
    assert.equal(obs.response_metadata.location_present, false, 'no Location header was sent');
    assert.ok(validateTransportObservation(obs).ok, 'a locationless redirect observation must validate');
});

test('VALIDATION: redirected is status-derived — locationless 302 valid, tampered redirected=false rejected, 200 with Location valid', async () => {
    // Case B: 302 without Location — the fixed contract (redirected=true, location_present=false).
    const callsB = [];
    const adapterB = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl(() => ({ status: 302, body: 'mock-redirect-body-not-read' }), callsB),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    const obsB = (await adapterB.fetchOnce('https://www.fotmob.com/match/123', { ordinal: 1, sourceMatchId: '123' })).transportObservation;
    assert.equal(validateTransportObservation(obsB).ok, true, '302 without Location must validate');
    assert.equal(obsB.response_metadata.redirected, true);
    assert.equal(obsB.response_metadata.location_present, false);

    // Case C: tampering redirected=false on a 302 is still rejected — the invariant is guarded.
    const tampered = JSON.parse(JSON.stringify(obsB));
    tampered.response_metadata.redirected = false;
    const checkC = validateTransportObservation(tampered);
    assert.equal(checkC.ok, false);
    assert.ok(checkC.errors.some(e => /redirected must match the http status/.test(e)), 'tampered redirected must be caught');

    // Case D: 200 with a Location header stays a non-redirect and validates.
    const callsD = [];
    const adapterD = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl(() => ({ status: 200, body: '<html>ok</html>', location: 'https://www.fotmob.com/other' }), callsD),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 30000,
    });
    const obsD = (await adapterD.fetchOnce('https://www.fotmob.com/match/123', { ordinal: 1, sourceMatchId: '123' })).transportObservation;
    assert.equal(validateTransportObservation(obsD).ok, true, '200 with Location must validate');
    assert.equal(obsD.response_metadata.redirected, false);
    assert.equal(obsD.response_metadata.location_present, true);
});

// ─────────────────────────────────────────────────────────────
// B2. Builder ↔ validator bound re-enforcement (TD-02 + #1826 follow-up)
//
// TD-02 covered the persisted string fields for which the builder already
// had an explicit max-length bound (source_match_id → MAX_MATCH_ID_LEN=32,
// request_finished_at → MAX_STRING_LEN=200, error_* → MAX_SHORT_STRING_LEN=64,
// response_metadata.content_type → MAX_STRING_LEN=200; all present since the
// module's #1819 introduction). The validator must fail closed on an
// externally supplied over-bound value — without being stricter than the
// builder for legitimate builder output.
//
// The remaining timestamp fields (request_started_at, response_headers_received_at,
// body_reading_started_at, body_completed_at) had NO builder max-length bound
// (raw String() / || null passthrough) — the SEPARATE_BUILDER_BOUND_GAP,
// recorded in TD-02 and fixed by #1826. #1826's follow-up additionally
// eliminated the pre-existing request_finished_at TRUNCATION edge (an
// oversized timestamp truncated to 200 could silently re-parse into a
// different valid instant). All 5 persisted timestamps now use the same
// fail-closed builder bound (TIMESTAMP_TOO_LONG marker) plus an explicit
// validator length check.
// ─────────────────────────────────────────────────────────────

test('BOUNDS: builder behavior remains unchanged at existing string bounds (6 bounded-valid fields; request_finished_at fail-closed marker)', () => {
    const mk = (overrides = {}) =>
        buildTransportObservation({
            ordinal: 1,
            sourceMatchId: '4193752',
            requestStartedAtIso: '2026-08-02T12:00:00.000Z',
            requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
            elapsedMs: 262,
            lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
            terminalOutcome: 'COMPLETED',
            responseHeadersReceived: true,
            responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
            httpStatus: 200,
            bodyReadingStarted: true,
            bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
            bodyBytesReceived: 100,
            bodyCompleted: true,
            bodyCompletedAt: '2026-08-02T12:00:00.000Z',
            timeoutConfiguredMs: 30000,
            timeoutTriggered: false,
            abortSource: null,
            errorName: null,
            errorCode: null,
            errorCauseName: null,
            errorCauseCode: null,
            responseMetadata: {
                content_type: 'text/html; charset=utf-8',
                declared_content_length: 100,
                location_present: false,
                redirected: false,
            },
            ...overrides,
        });
    const mkErr = (overrides = {}) =>
        buildTransportObservation({
            ordinal: 1,
            sourceMatchId: '4193752',
            requestStartedAtIso: '2026-08-02T12:00:00.000Z',
            requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
            elapsedMs: 5,
            lastReliablePhase: 'REQUEST_STARTED',
            terminalOutcome: 'FETCH_ERROR',
            responseHeadersReceived: false,
            httpStatus: null,
            bodyReadingStarted: false,
            bodyBytesReceived: 0,
            bodyCompleted: false,
            timeoutConfiguredMs: 30000,
            timeoutTriggered: false,
            abortSource: null,
            errorName: 'boom',
            errorCode: 'E1',
            errorCauseName: 'cause',
            errorCauseCode: 'C1',
            responseMetadata: null,
            ...overrides,
        });

    // source_match_id: 60-char input → bounded to 32 → valid.
    const matchId = mk({ sourceMatchId: 'm'.repeat(60) });
    assert.equal(matchId.source_match_id.length, 32);
    assert.ok(validateTransportObservation(matchId).ok);

    // error fields (4): 80-char inputs → bounded to 64 → valid (per-field).
    const e1 = mkErr({ errorName: 'z'.repeat(80) });
    assert.equal(e1.error_name.length, 64);
    assert.ok(validateTransportObservation(e1).ok);
    const e2 = mkErr({ errorCode: 'z'.repeat(80) });
    assert.equal(e2.error_code.length, 64);
    assert.ok(validateTransportObservation(e2).ok);
    const e3 = mkErr({ errorCauseName: 'z'.repeat(80) });
    assert.equal(e3.error_cause_name.length, 64);
    assert.ok(validateTransportObservation(e3).ok);
    const e4 = mkErr({ errorCauseCode: 'z'.repeat(80) });
    assert.equal(e4.error_cause_code.length, 64);
    assert.ok(validateTransportObservation(e4).ok);

    // content_type: 500-char input → bounded to 200 → valid.
    const ct = mk({ responseMetadata: { content_type: 'w'.repeat(500), declared_content_length: 100, location_present: false, redirected: false } });
    assert.equal(ct.response_metadata.content_type.length, 200);
    assert.ok(validateTransportObservation(ct).ok);

    // request_finished_at: an oversized input is NOT truncated — it yields the
    // deterministic fail-closed marker TIMESTAMP_TOO_LONG (18 chars, ≤200,
    // ISO-invalid), so validation rejects the entry. Truncating an oversized
    // timestamp was the pre-existing #1825 builder property; it could silently
    // re-parse into a DIFFERENT valid instant (e.g. a long-fraction ISO losing
    // its trailing 'Z'), so timestamps are now bounded fail-closed instead.
    const finishBig = mk({ requestFinishedAtIso: '2026-08-02T12:00:00.000Z' + 'y'.repeat(500) });
    assert.equal(finishBig.request_finished_at, 'TIMESTAMP_TOO_LONG', 'oversized requestFinishedAtIso must fail closed, never truncated');
    const finishCheck = validateTransportObservation(finishBig);
    assert.equal(finishCheck.ok, false);
    assert.ok(
        finishCheck.errors.some(e => /valid ISO/.test(e)),
        'the fail-closed marker is ISO-invalid and rejected'
    );
    // A realistic in-bounds ISO input still produces a validator-valid entry.
    assert.ok(validateTransportObservation(mk()).ok);
});

test('BOUNDS: direct persisted MAX accepted, MAX+1 rejected specifically for the length bound', () => {
    // Validator explicit bound fields = 7 (source_match_id, request_finished_at,
    // error_name/error_code/error_cause_name/error_cause_code, content_type).
    // This is distinct from the 6 builder oversized→bounded→valid cases in the
    // previous test: request_finished_at fail-closes at the builder (an oversized
    // timestamp input yields the ISO-invalid TIMESTAMP_TOO_LONG marker), so it is
    // NOT counted among the builder-valid cases while it IS counted among the
    // 7 validator boundary contracts (length rule verified directly here).
    const good = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-02T12:00:00.000Z',
        requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
        bodyBytesReceived: 100,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-02T12:00:00.000Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: {
            content_type: 'text/html; charset=utf-8',
            declared_content_length: 100,
            location_present: false,
            redirected: false,
        },
    });
    const errGood = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-02T12:00:00.000Z',
        requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
        elapsedMs: 5,
        lastReliablePhase: 'REQUEST_STARTED',
        terminalOutcome: 'FETCH_ERROR',
        responseHeadersReceived: false,
        httpStatus: null,
        bodyReadingStarted: false,
        bodyBytesReceived: 0,
        bodyCompleted: false,
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: 'boom',
        errorCode: 'E1',
        errorCauseName: 'cause',
        errorCauseCode: 'C1',
        responseMetadata: null,
    });
    const clone = o => JSON.parse(JSON.stringify(o));

    // source_match_id: 32 accepted, 33 rejected for length.
    const smid = clone(good);
    smid.source_match_id = 'x'.repeat(32);
    assert.ok(validateTransportObservation(smid).ok, '32-char source_match_id must validate');
    const smidOver = clone(good);
    smidOver.source_match_id = 'x'.repeat(33);
    const smidCheck = validateTransportObservation(smidOver);
    assert.equal(smidCheck.ok, false);
    assert.ok(smidCheck.errors.some(e => /at most 32/.test(e)), '33-char source_match_id must be rejected for the length bound');

    // error fields (4): 64 accepted, 65 rejected for length.
    for (const field of ['error_name', 'error_code', 'error_cause_name', 'error_cause_code']) {
        const atMax = clone(errGood);
        atMax[field] = 'y'.repeat(64);
        assert.ok(validateTransportObservation(atMax).ok, `${field} at 64 must validate`);
        const over = clone(errGood);
        over[field] = 'y'.repeat(65);
        const ck = validateTransportObservation(over);
        assert.equal(ck.ok, false);
        assert.ok(ck.errors.some(e => /at most 64/.test(e)), `${field} at 65 must be rejected for the length bound`);
    }

    // content_type: 200 accepted, 201 rejected for length.
    const ct = clone(good);
    ct.response_metadata.content_type = 'z'.repeat(200);
    assert.ok(validateTransportObservation(ct).ok, '200-char content_type must validate');
    const ctOver = clone(good);
    ctOver.response_metadata.content_type = 'z'.repeat(201);
    const ctCheck = validateTransportObservation(ctOver);
    assert.equal(ctCheck.ok, false);
    assert.ok(ctCheck.errors.some(e => /at most 200/.test(e)), '201-char content_type must be rejected for the length bound');

    // request_finished_at: a normal ISO timestamp (well within 200) accepted;
    // an over-bound value produces an explicit max-length violation.
    assert.ok(validateTransportObservation(good).ok, 'normal request_finished_at must validate');
    const finOver = clone(good);
    finOver.request_finished_at = '2026-08-02T12:00:00.000Z' + ' '.repeat(200);
    const finCheck = validateTransportObservation(finOver);
    assert.equal(finCheck.ok, false);
    assert.ok(
        finCheck.errors.some(e => /at most 200/.test(e)),
        'over-bound request_finished_at must carry the explicit max-length violation'
    );
});

test('BOUNDS: nested document fails closed on an over-bound entry even with a recomputed self-hash', () => {
    const good = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-02T12:00:00.000Z',
        requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
        bodyBytesReceived: 100,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-02T12:00:00.000Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: {
            content_type: 'text/html; charset=utf-8',
            declared_content_length: 100,
            location_present: false,
            redirected: false,
        },
    });
    const doc = defaultObservationsDoc({
        runId: 'run-td02-nested',
        planSha256: '0'.repeat(64),
        authorizationId: 'test-authorization-id',
        maxRequests: 2,
        collectorCodeRevision: TEST_REVISION,
    });
    const tampered = JSON.parse(JSON.stringify(good));
    tampered.source_match_id = 'x'.repeat(33);
    const nestedDoc = { ...doc, observations: [tampered] };
    nestedDoc.observations_sha256 = computeObservationsSelfHash(nestedDoc);
    const check = validateObservationsDoc(nestedDoc);
    assert.equal(check.ok, false, 'an over-bound entry must fail the nested doc validation');
    assert.ok(
        check.errors.some(e => /at most 32/.test(e)),
        'the nested validation must surface the length-bound violation'
    );
});

test('BOUNDS: persisted read fails closed on an over-bound entry — recomputing the self-hash cannot bypass', () => {
    const dir = tmpDir('obs-td02-read-');
    try {
        const good = buildTransportObservation({
            ordinal: 1,
            sourceMatchId: '4193752',
            requestStartedAtIso: '2026-08-02T12:00:00.000Z',
            requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
            elapsedMs: 262,
            lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
            terminalOutcome: 'COMPLETED',
            responseHeadersReceived: true,
            responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
            httpStatus: 200,
            bodyReadingStarted: true,
            bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
            bodyBytesReceived: 100,
            bodyCompleted: true,
            bodyCompletedAt: '2026-08-02T12:00:00.000Z',
            timeoutConfiguredMs: 30000,
            timeoutTriggered: false,
            abortSource: null,
            errorName: null,
            errorCode: null,
            errorCauseName: null,
            errorCauseCode: null,
            responseMetadata: {
                content_type: 'text/html; charset=utf-8',
                declared_content_length: 100,
                location_present: false,
                redirected: false,
            },
        });
        const doc = defaultObservationsDoc({
            runId: 'run-td02-read',
            planSha256: '0'.repeat(64),
            authorizationId: 'test-authorization-id',
            maxRequests: 2,
            collectorCodeRevision: TEST_REVISION,
        });
        const tampered = JSON.parse(JSON.stringify(good));
        tampered.response_metadata.content_type = 'z'.repeat(201);
        const nestedDoc = { ...doc, observations: [tampered] };
        nestedDoc.observations_sha256 = computeObservationsSelfHash(nestedDoc);
        // The write path refuses the invalid doc (fail closed)…
        assert.throws(
            () => writeTransportObservationsFile(dir, nestedDoc, fs, null),
            /SAFETY_ERROR:refusing to persist invalid transport observations/
        );
        // …and a hand-written file with a valid JSON shape, valid schema and a
        // correct recomputed self-hash still fails closed on read.
        const filePath = path.join(dir, OBSERVATIONS_FILE_NAME);
        fs.writeFileSync(filePath, JSON.stringify(nestedDoc, null, 2) + '\n', 'utf8');
        assert.throws(
            () => readTransportObservationsFile(dir, fs),
            err => err.code === 'SAFETY_ERROR' && /at most 200/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// B3. Timestamp builder-bound gap (TD-02 follow-up)
//
// All 5 persisted timestamp strings must share the builder's existing
// MAX_STRING_LEN=200 contract. Before #1826 the builder emitted 4 of them
// unbound (request_started_at via raw String(), the three optional *_at
// fields via || null passthrough) — and because V8's Date.parse accepts
// arbitrarily long fractional-second digits, a >200-char string like
// '2026-08-02T12:00:00.' + 200 zeros + 'Z' is ISO-valid, so the validator's
// ISO rule alone did NOT fail closed: such an entry passed validation and
// was persisted. The 5th field (request_finished_at) was truncated to 200
// by boundString, but the truncated prefix could also silently re-parse as
// a different valid instant (a long-fraction ISO losing its trailing 'Z'
// becomes an offset-less local datetime). #1826's follow-up now bounds all
// 5 builder outputs FAIL-CLOSED (an over-bound timestamp yields a
// deterministically ISO-invalid marker, never a truncated value that could
// re-parse as a different instant) and gives the validator an explicit
// length check per timestamp, independent of ISO validity.
// ─────────────────────────────────────────────────────────────

test('BOUNDS: builder fails closed on over-bound timestamps instead of rewriting evidence (5 fields)', () => {
    const longIso = '2026-08-02T12:00:00.' + '0'.repeat(200) + 'Z'; // 221 chars, ISO-valid in V8
    assert.equal(Number.isNaN(Date.parse(longIso)), false, 'precondition: long-fraction ISO is parseable');
    // Precondition for the fail-closed design: a naive truncation of longIso to
    // 200 chars would drop the trailing 'Z' and RE-PARSE as a valid offset-less
    // local datetime (a different instant, shifted by the machine timezone).
    // Truncation would therefore rewrite evidence instead of failing closed.
    const truncated = longIso.slice(0, 200);
    assert.equal(truncated.endsWith('Z'), false);
    assert.equal(Number.isNaN(Date.parse(truncated)), false, 'naive truncation would silently re-parse as a different valid instant');
    const mk = (overrides = {}) =>
        buildTransportObservation({
            ordinal: 1,
            sourceMatchId: '4193752',
            requestStartedAtIso: '2026-08-02T12:00:00.000Z',
            requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
            elapsedMs: 262,
            lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
            terminalOutcome: 'COMPLETED',
            responseHeadersReceived: true,
            responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
            httpStatus: 200,
            bodyReadingStarted: true,
            bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
            bodyBytesReceived: 100,
            bodyCompleted: true,
            bodyCompletedAt: '2026-08-02T12:00:00.000Z',
            timeoutConfiguredMs: 30000,
            timeoutTriggered: false,
            abortSource: null,
            errorName: null,
            errorCode: null,
            errorCauseName: null,
            errorCauseCode: null,
            responseMetadata: {
                content_type: 'text/html; charset=utf-8',
                declared_content_length: 100,
                location_present: false,
                redirected: false,
            },
            ...overrides,
        });

    // request_started_at: over-bound input → bounded but deterministically
    // ISO-invalid marker (never a truncated timestamp that could re-parse as a
    // different instant) → the entry fails validation, fail closed.
    const e1 = mk({ requestStartedAtIso: longIso });
    assert.equal(e1.request_started_at, 'TIMESTAMP_TOO_LONG');
    assert.equal(e1.request_started_at.length <= 200, true);
    assert.equal(validateTransportObservation(e1).ok, false, 'an over-bound request_started_at must fail closed');

    // The three optional timestamps follow the same fail-closed rule.
    const e2 = mk({ responseHeadersReceivedAt: longIso });
    assert.equal(e2.response_headers_received_at, 'TIMESTAMP_TOO_LONG');
    assert.equal(validateTransportObservation(e2).ok, false);

    const e3 = mk({ bodyReadingStartedAt: longIso });
    assert.equal(e3.body_reading_started_at, 'TIMESTAMP_TOO_LONG');
    assert.equal(validateTransportObservation(e3).ok, false);

    const e4 = mk({ bodyCompletedAt: longIso });
    assert.equal(e4.body_completed_at, 'TIMESTAMP_TOO_LONG');
    assert.equal(validateTransportObservation(e4).ok, false);

    // request_finished_at: same fail-closed rule. The pre-existing #1825
    // truncation edge (a 200-char truncated prefix could re-parse as a
    // different valid instant, e.g. losing the trailing 'Z') is eliminated —
    // the over-bound input now yields the ISO-invalid marker and the entry
    // fails validation, so a silently rewritten finish timestamp can never be
    // persisted.
    const e5 = mk({ requestFinishedAtIso: longIso });
    assert.equal(e5.request_finished_at, 'TIMESTAMP_TOO_LONG', 'request_finished_at must fail closed, never truncated to a re-parseable prefix');
    assert.equal(e5.request_finished_at.length <= 200, true);
    assert.equal(validateTransportObservation(e5).ok, false, 'an over-bound request_finished_at must fail closed');

    // Normal runtime inputs are unaffected: ordinary 24-char toISOString
    // timestamps pass through byte-for-byte and the complete observation still
    // validates (the fail-closed rule only triggers on over-bound inputs).
    const runtimeIso = '2026-08-02T12:00:00.000Z';
    const runtime = mk({
        requestStartedAtIso: runtimeIso,
        requestFinishedAtIso: runtimeIso,
        responseHeadersReceivedAt: runtimeIso,
        bodyReadingStartedAt: runtimeIso,
        bodyCompletedAt: runtimeIso,
    });
    assert.equal(runtime.request_started_at, runtimeIso);
    assert.equal(runtime.request_finished_at, runtimeIso);
    assert.equal(runtime.response_headers_received_at, runtimeIso);
    assert.equal(runtime.body_reading_started_at, runtimeIso);
    assert.equal(runtime.body_completed_at, runtimeIso);
    assert.ok(validateTransportObservation(runtime).ok, 'normal runtime timestamps still validate');
});

test('BOUNDS: validator rejects over-bound timestamps with explicit length violations (5 fields)', () => {
    const longIso = '2026-08-02T12:00:00.' + '0'.repeat(200) + 'Z'; // 221 chars, ISO-valid in V8
    assert.equal(Number.isNaN(Date.parse(longIso)), false, 'precondition: long-fraction ISO is parseable');
    const good = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-02T12:00:00.000Z',
        requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
        bodyBytesReceived: 100,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-02T12:00:00.000Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: {
            content_type: 'text/html; charset=utf-8',
            declared_content_length: 100,
            location_present: false,
            redirected: false,
        },
    });
    const clone = o => JSON.parse(JSON.stringify(o));

    // request_started_at: 221-char ISO-valid value → explicit length violation.
    const e1 = clone(good);
    e1.request_started_at = longIso;
    const c1 = validateTransportObservation(e1);
    assert.equal(c1.ok, false);
    assert.ok(c1.errors.some(e => /at most 200/.test(e)), 'request_started_at must carry the explicit max-length violation');

    // request_finished_at: 221-char ISO-valid value → explicit length violation (matrix completeness).
    const e2 = clone(good);
    e2.request_finished_at = longIso;
    const c2 = validateTransportObservation(e2);
    assert.equal(c2.ok, false);
    assert.ok(c2.errors.some(e => /at most 200/.test(e)), 'request_finished_at must carry the explicit max-length violation');

    // response_headers_received_at (headers were received): explicit length violation.
    const e3 = clone(good);
    e3.response_headers_received_at = longIso;
    const c3 = validateTransportObservation(e3);
    assert.equal(c3.ok, false);
    assert.ok(c3.errors.some(e => /at most 200/.test(e)), 'response_headers_received_at must carry the explicit max-length violation');

    // body_reading_started_at (body reading started): explicit length violation.
    const e4 = clone(good);
    e4.body_reading_started_at = longIso;
    const c4 = validateTransportObservation(e4);
    assert.equal(c4.ok, false);
    assert.ok(c4.errors.some(e => /at most 200/.test(e)), 'body_reading_started_at must carry the explicit max-length violation');

    // body_completed_at (body completed): explicit length violation.
    const e5 = clone(good);
    e5.body_completed_at = longIso;
    const c5 = validateTransportObservation(e5);
    assert.equal(c5.ok, false);
    assert.ok(c5.errors.some(e => /at most 200/.test(e)), 'body_completed_at must carry the explicit max-length violation');
});

test('BOUNDS: nested document fails closed on an over-bound timestamp even with a recomputed self-hash', () => {
    const longIso = '2026-08-02T12:00:00.' + '0'.repeat(200) + 'Z'; // 221 chars, ISO-valid in V8
    const good = buildTransportObservation({
        ordinal: 1,
        sourceMatchId: '4193752',
        requestStartedAtIso: '2026-08-02T12:00:00.000Z',
        requestFinishedAtIso: '2026-08-02T12:00:00.000Z',
        elapsedMs: 262,
        lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
        terminalOutcome: 'COMPLETED',
        responseHeadersReceived: true,
        responseHeadersReceivedAt: '2026-08-02T12:00:00.000Z',
        httpStatus: 200,
        bodyReadingStarted: true,
        bodyReadingStartedAt: '2026-08-02T12:00:00.000Z',
        bodyBytesReceived: 100,
        bodyCompleted: true,
        bodyCompletedAt: '2026-08-02T12:00:00.000Z',
        timeoutConfiguredMs: 30000,
        timeoutTriggered: false,
        abortSource: null,
        errorName: null,
        errorCode: null,
        errorCauseName: null,
        errorCauseCode: null,
        responseMetadata: {
            content_type: 'text/html; charset=utf-8',
            declared_content_length: 100,
            location_present: false,
            redirected: false,
        },
    });
    const tampered = JSON.parse(JSON.stringify(good));
    tampered.request_started_at = longIso;
    const doc = defaultObservationsDoc({
        runId: 'run-td02f-nested',
        planSha256: '0'.repeat(64),
        authorizationId: 'test-authorization-id',
        maxRequests: 2,
        collectorCodeRevision: TEST_REVISION,
    });
    const nestedDoc = { ...doc, observations: [tampered] };
    nestedDoc.observations_sha256 = computeObservationsSelfHash(nestedDoc);
    const check = validateObservationsDoc(nestedDoc);
    assert.equal(check.ok, false, 'an over-bound timestamp must fail the nested doc validation');
    assert.ok(
        check.errors.some(e => /at most 200/.test(e)),
        'the nested validation must surface the length-bound violation'
    );
    // The persistence path also fails closed for the same doc.
    const dir = tmpDir('obs-td02f-nested-');
    try {
        assert.throws(
            () => writeTransportObservationsFile(dir, nestedDoc, fs, null),
            /SAFETY_ERROR:refusing to persist invalid transport observations/
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// C. Run-level integration: budget, fail-stop, resume, summary
// ─────────────────────────────────────────────────────────────

test('RUN: budget — telemetry never adds request count; exhausted budget performs zero fetches and zero observations', async () => {
    const dir = tmpDir('obs-budget-');
    try {
        const cand1 = makeCandidate({
            id: 4193752,
            season: '2024/2025',
            home: 'A',
            away: 'B',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const cand2 = makeCandidate({
            id: 4506625,
            season: '2024/2025',
            home: 'C',
            away: 'D',
            kickoff: '2024-08-17T11:30:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand1, cand2], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(url => {
            if (String(url).includes('4193752')) return okResponse(pageFor(cand1));
            return okResponse('x');
        }, calls);
        const result = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-budget',
                maxRequests: 1,
                fetchImpl,
            })
        );
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /budget_exhausted/);
        assert.equal(calls.length, 1, 'one and only one fetch — telemetry adds zero requests');
        assert.equal(result.networkRequestsMade, 1);
        assert.equal(result.completedCount, 1, 'the one allowed request completed its capture');
        const doc = readObservations(result.runDir);
        assert.equal(doc.observations.length, 1, 'one observation for the one attempt');
        assert.ok(doc.observations.length <= Number(doc.max_requests));
        // The run summary references the telemetry.
        const summary = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.transport_observations_file, OBSERVATIONS_FILE_NAME);
        assert.equal(summary.transport_observations_count, 1);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: locationless 3xx — observation survives to persistence while the access-control stop is unchanged', async () => {
    const dir = tmpDir('obs-locationless-redirect-');
    try {
        const cand1 = makeCandidate({
            id: 4193752,
            season: '2024/2025',
            home: 'A',
            away: 'B',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand1], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => ({ status: 302, body: 'mock-redirect-body-not-read' }), calls);
        const result = await executeCaptureRun(
            makeCaptureOptions({ dir, plan, planPath, runId: 'run-obs-locationless', maxRequests: 2, fetchImpl })
        );
        // The 3xx policy is unchanged: the run stops exactly as before...
        assert.equal(result.status, 'stopped');
        assert.equal(result.stopReason, 'access_control:redirect_302');
        assert.equal(result.networkRequestsMade, 1);
        assert.equal(calls.length, 1, 'one and only one fetch — the redirect is never followed');
        // ...and the transport observation now survives to the normal settlement/persistence path.
        const doc = readObservations(result.runDir);
        const obs = doc.observations.find(o => o.ordinal === 1);
        assert.ok(obs, 'the locationless-redirect observation must be persisted');
        assert.equal(obs.http_status, 302);
        assert.equal(obs.body_reading_started, false, 'the redirect body is never read');
        assert.equal(obs.response_metadata.redirected, true);
        assert.equal(obs.response_metadata.location_present, false);
        assert.ok(validateTransportObservation(obs).ok);
        // The summary telemetry linkage reflects the persisted observation.
        const summary = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.transport_observations_count, 1);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: stop-on-first-failure — first timeout stops the run, the second candidate (4506625) is NEVER requested', async () => {
    const dir = tmpDir('obs-failstop-');
    try {
        const { plan, planPath } = makePlanFixture(
            dir,
            [
                makeCandidate({
                    id: 4193752,
                    season: '2024/2025',
                    home: 'A',
                    away: 'B',
                    kickoff: '2024-08-16T19:00:00Z',
                }),
                makeCandidate({
                    id: 4506625,
                    season: '2024/2025',
                    home: 'C',
                    away: 'D',
                    kickoff: '2024-08-17T11:30:00Z',
                }),
            ],
            { seasons: ['2024/2025'] }
        );
        const calls = [];
        const fetchImpl = (url, opts) =>
            new Promise((resolve, reject) => {
                calls.push(url);
                opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
            });
        const result = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-failstop',
                maxRequests: 2,
                fetchImpl,
                timeoutMs: 50,
            })
        );
        assert.equal(result.status, 'stopped');
        assert.equal(result.stoppedAtOrdinal, 1);
        assert.equal(result.completedCount, 0);
        assert.equal(calls.length, 1, '4193752 failed → 4506625 never requested (retry=0, fail-stop)');
        const state = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-state.json'), 'utf8'));
        assert.equal(state.network_requests_attempted, 1);
        assert.equal(state.network_responses_received, 0);
        const doc = readObservations(result.runDir);
        assert.equal(doc.observations.length, 1);
        const obs = doc.observations[0];
        assert.equal(obs.ordinal, 1);
        assert.equal(obs.source_match_id, '4193752');
        assert.equal(obs.last_reliable_phase, 'AWAITING_RESPONSE_HEADERS');
        assert.equal(obs.terminal_outcome, 'TIMEOUT');
        assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
        assert.equal(obs.timeout_triggered, true);
        assert.equal(obs.response_headers_received, false);
        assert.equal(obs.body_bytes_received, 0);
        // The fail-stop contract survives telemetry: the run stopped with
        // the ORIGINAL fetch error, unchanged.
        assert.match(result.stopReason, /fetch_error/);
        // No capture pair ever materialized (failed attempt ≠ capture).
        const capturesDir = path.join(result.runDir, 'captures');
        let captureFiles = [];
        try {
            captureFiles = fs.readdirSync(capturesDir);
        } catch {
            /* absent dir == no captures */
        }
        assert.equal(captureFiles.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: success — observation persisted in the run dir; no HTML / body content anywhere', async () => {
    const dir = tmpDir('obs-success-');
    try {
        const cand = makeCandidate({
            id: 4506263,
            season: '2024/2025',
            home: 'Manchester United',
            away: 'Fulham',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(cand)));
        const result = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-success',
                maxRequests: 1,
                fetchImpl,
            })
        );
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        const doc = readObservations(result.runDir);
        assert.equal(doc.observations.length, 1);
        const obs = doc.observations[0];
        assert.equal(obs.terminal_outcome, 'COMPLETED');
        assert.equal(obs.last_reliable_phase, 'RESPONSE_BODY_COMPLETED');
        assert.equal(obs.body_completed, true);
        assert.ok(obs.body_bytes_received > 0);
        // The observations file is derived data — no body fragments/HTML.
        const raw = fs.readFileSync(OBSERVATIONS_PATH(result.runDir), 'utf8');
        assert.ok(!raw.includes('<!doctype'));
        assert.ok(!raw.includes('__NEXT_DATA__'));
        assert.ok(!raw.includes(pageFor(cand)));
        // Summary references the telemetry deterministically.
        const summary = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.transport_observations_file, OBSERVATIONS_FILE_NAME);
        assert.equal(summary.transport_observations_count, 1);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: resume — v1 run state (no telemetry file) reads fine; the cumulative budget is unchanged; a failed ordinal under an exhausted budget is never re-fetched', async () => {
    const dir = tmpDir('obs-resume1-');
    try {
        const cand = makeCandidate({
            id: 4506263,
            season: '2024/2025',
            home: 'Manchester United',
            away: 'Fulham',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });

        // Cycle 1: timeout → stopped run, one observation persisted.
        const fetchImplTimeout = (url, opts) =>
            new Promise((resolve, reject) => {
                opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
            });
        const run1 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-resume1',
                maxRequests: 1,
                fetchImpl: fetchImplTimeout,
                timeoutMs: 50,
            })
        );
        assert.equal(run1.status, 'stopped');
        let doc = readObservations(run1.runDir);
        assert.equal(doc.observations.length, 1);

        // Simulate a v1 run: strip the telemetry file — the run state alone
        // must still read and drive the resume, exactly like before this PR.
        fs.rmSync(OBSERVATIONS_PATH(run1.runDir), { force: true });

        // Cycle 2: resume — v1 run state loads; the budget is CUMULATIVE
        // (1 of 1 already attempted) so the same-budget resume issues ZERO
        // fetches: the failed ordinal is never silently re-fetched.
        const calls = [];
        const fetchImplOk = mockFetchImpl(() => okResponse(pageFor(cand)), calls);
        const run2 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-resume1',
                maxRequests: 1,
                fetchImpl: fetchImplOk,
                timeoutMs: 30000,
            })
        );
        assert.equal(run2.status, 'stopped');
        assert.match(run2.stopReason, /budget_exhausted/);
        assert.equal(calls.length, 0, 'no re-fetch under an exhausted budget');
        const state = JSON.parse(fs.readFileSync(path.join(run2.runDir, 'run-state.json'), 'utf8'));
        assert.equal(state.network_requests_attempted, 1, 'attempted count unchanged');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: resume — completed pairs are never re-fetched; re-attempted ordinals replace (last attempt wins) without duplication', async () => {
    const dir = tmpDir('obs-resume2-');
    try {
        const cand1 = makeCandidate({
            id: 4193752,
            season: '2024/2025',
            home: 'A',
            away: 'B',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const cand2 = makeCandidate({
            id: 4506625,
            season: '2024/2025',
            home: 'C',
            away: 'D',
            kickoff: '2024-08-17T11:30:00Z',
        });
        const cand3 = makeCandidate({
            id: 4506265,
            season: '2024/2025',
            home: 'E',
            away: 'F',
            kickoff: '2024-08-17T14:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand1, cand2, cand3], { seasons: ['2024/2025'] });

        // Cycle 1 (max_requests=4 — the contract is FIXED per run; the
        // cumulative budget covers 3 attempts in cycle 2 as well): ordinal 1
        // completes; ordinal 2 is a 403 → access-control stop (attempted
        // 2/4); ordinal 3 never requested.
        const calls1 = [];
        const fetchImpl1 = mockFetchImpl(url => {
            if (String(url).includes('4506625')) return { status: 403, body: '<html>forbidden</html>' };
            return okResponse(pageFor(cand1));
        }, calls1);
        const run1 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-resume2',
                maxRequests: 4,
                fetchImpl: fetchImpl1,
            })
        );
        assert.equal(run1.status, 'stopped');
        assert.equal(run1.completedCount, 1);
        assert.equal(run1.stoppedAtOrdinal, 2);
        assert.equal(calls1.length, 2);
        let doc = readObservations(run1.runDir);
        assert.equal(doc.observations.length, 2);
        assert.deepEqual(
            doc.observations.map(o => o.ordinal),
            [1, 2]
        );
        assert.equal(doc.observations[1].http_status, 403);

        // Cycle 2: resume — ordinal 1's pair is complete and NEVER
        // re-fetched; ordinal 2 is re-attempted (its failed attempt left no
        // pair) and succeeds; ordinal 3 appends. Observations: 3 entries,
        // no duplicates — ordinal 2's 403 entry replaced by the new
        // COMPLETED entry (last attempt per ordinal wins).
        const calls2 = [];
        const fetchImpl2 = mockFetchImpl(url => {
            if (String(url).includes('4193752')) return okResponse(pageFor(cand1));
            if (String(url).includes('4506625')) return okResponse(pageFor(cand2));
            return okResponse(pageFor(cand3));
        }, calls2);
        const run2 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-resume2',
                maxRequests: 4,
                fetchImpl: fetchImpl2,
            })
        );
        assert.equal(run2.status, 'complete');
        assert.equal(run2.completedCount, 3);
        assert.equal(calls2.length, 2, 'ordinal 1 skipped on resume; ordinals 2 and 3 fetched');
        doc = readObservations(run2.runDir);
        assert.equal(doc.observations.length, 3, 'one observation per ordinal — no duplicates');
        assert.deepEqual(
            doc.observations.map(o => o.ordinal),
            [1, 2, 3]
        );
        assert.equal(doc.observations[1].http_status, 200, 'the 403 entry was replaced by the successful attempt');
        assert.ok(validateObservationsDoc(doc).ok);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RUN: replay stays deterministic with telemetry — rebuilt summary byte-identical; a v1 run without telemetry replays with the old summary shape', async () => {
    const dir = tmpDir('obs-replay-');
    try {
        const cand = makeCandidate({
            id: 4506263,
            season: '2024/2025',
            home: 'Manchester United',
            away: 'Fulham',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(cand)));
        const run = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-replay',
                maxRequests: 1,
                fetchImpl,
            })
        );
        assert.equal(run.status, 'complete');
        const summaryBefore = fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8');
        assert.ok(summaryBefore.includes('transport_observations_count'));

        // Replay with telemetry present: rebuilt summary == stored summary.
        const { runReplay } = require('../../scripts/ops/fotmob_detail_capture');
        const replay1 = runReplay(
            { 'run-dir': run.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay1.replayed_count, 1);
        assert.equal(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'), summaryBefore);

        // v1 simulation: telemetry file AND its summary reference removed —
        // replay rebuilds the OLD summary shape (no telemetry fields) and
        // still succeeds; the stored summary is rewritten identically.
        fs.rmSync(OBSERVATIONS_PATH(run.runDir), { force: true });
        fs.rmSync(path.join(run.runDir, 'run-summary.json'), { force: true });
        const replay2 = runReplay(
            { 'run-dir': run.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay2.replayed_count, 1);
        const summaryAfter = JSON.parse(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summaryAfter.transport_observations_file, undefined);
        assert.equal(summaryAfter.transport_observations_count, undefined);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REDACTION: no cookies / auth / tokens / body / headers / secrets anywhere in the persisted file; long strings bounded', async () => {
    const dir = tmpDir('obs-redaction-');
    try {
        const cand = makeCandidate({
            id: 4506263,
            season: '2024/2025',
            home: 'Manchester United',
            away: 'Fulham',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const SECRET = 'sessionid=abc123secret';
        const fetchImpl = async (url, opts) =>
            new Promise((resolve, reject) => {
                opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
            });
        const result = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-obs-redact',
                maxRequests: 1,
                fetchImpl,
                timeoutMs: 50,
            })
        );
        assert.equal(result.status, 'stopped');
        const raw = fs.readFileSync(OBSERVATIONS_PATH(result.runDir), 'utf8');
        // The doc legitimately carries run metadata (authorization_id etc.) —
        // the needles below are CREDENTIAL shapes that must never appear.
        // 'authorization:' (a header shape) is distinct from authorization_id.
        for (const needle of [
            SECRET,
            'set-cookie',
            'authorization:',
            'cookie:',
            'bearer',
            'sessionid',
            'x-auth',
            'token=',
        ]) {
            assert.ok(!raw.toLowerCase().includes(needle.toLowerCase()), `no ${needle} in telemetry`);
        }
        const doc = readObservations(result.runDir);
        const obs = doc.observations[0];
        assert.equal(obs.error_name, 'Error');
        // Observed values in this real-run document stay within the builder
        // max-length bounds for the fields that have them (error_name → 64,
        // source_match_id → 32). request_started_at is a builder-passthrough
        // timestamp with NO builder max-length bound (see B2 / the recorded
        // SEPARATE_BUILDER_BOUND_GAP) — the 40-char value here is a runtime
        // observation, not a contract.
        assert.ok(obs.error_name.length <= 64);
        assert.ok(obs.source_match_id.length <= 32);
        assert.ok(obs.request_started_at.length <= 40);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// D. Persistence safety: atomicity, symlinks, tampering
// ─────────────────────────────────────────────────────────────

test('PERSIST: symlink targets and non-regular files fail closed on read and write', () => {
    const dir = tmpDir('obs-persist-');
    try {
        const runDir = path.join(dir, 'run');
        fs.mkdirSync(runDir, { recursive: true });
        const doc = defaultObservationsDoc({
            runId: 'run-1',
            planSha256: 'a'.repeat(64),
            authorizationId: 'AUTH',
            maxRequests: 1,
            collectorCodeRevision: 'b'.repeat(40),
        });

        // Symlink target.
        const otherDir = path.join(dir, 'other');
        fs.mkdirSync(otherDir, { recursive: true });
        writeTransportObservationsFile(otherDir, doc, fs);
        fs.symlinkSync(OBSERVATIONS_PATH(otherDir), OBSERVATIONS_PATH(runDir));
        assert.throws(
            () => readTransportObservationsFile(runDir, fs),
            e => e.code === 'SAFETY_ERROR'
        );
        assert.throws(
            () => writeTransportObservationsFile(runDir, doc, fs),
            e => e.code === 'SAFETY_ERROR'
        );

        // Directory at the target path.
        fs.rmSync(OBSERVATIONS_PATH(runDir), { force: true });
        fs.mkdirSync(OBSERVATIONS_PATH(runDir));
        assert.throws(
            () => readTransportObservationsFile(runDir, fs),
            e => e.code === 'SAFETY_ERROR'
        );
        assert.throws(
            () => writeTransportObservationsFile(runDir, doc, fs),
            e => e.code === 'SAFETY_ERROR'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PERSIST: interrupted writes leave no valid file (crash-safe); temp residue is ignored', () => {
    const dir = tmpDir('obs-persist2-');
    try {
        const runDir = path.join(dir, 'run');
        fs.mkdirSync(runDir, { recursive: true });
        const doc = defaultObservationsDoc({
            runId: 'run-1',
            planSha256: 'a'.repeat(64),
            authorizationId: 'AUTH',
            maxRequests: 1,
            collectorCodeRevision: 'b'.repeat(40),
        });
        // A crashed writer left only the temp file: not a valid target.
        fs.writeFileSync(`${OBSERVATIONS_PATH(runDir)}.tmp-9999-1`, 'garbage');
        assert.equal(readTransportObservationsFile(runDir, fs), null, 'temp residue is not a valid doc');
        // The first real write succeeds despite the residue.
        assert.equal(writeTransportObservationsFile(runDir, doc, fs), 'written');
        assert.ok(readTransportObservationsFile(runDir, fs), 'now readable');
        // Idempotent second write.
        assert.equal(writeTransportObservationsFile(runDir, doc, fs), 'unchanged');
        // Unparseable JSON fails closed.
        fs.writeFileSync(OBSERVATIONS_PATH(runDir), 'not json');
        assert.throws(
            () => readTransportObservationsFile(runDir, fs),
            e => e.code === 'SAFETY_ERROR'
        );
        assert.throws(
            () => writeTransportObservationsFile(runDir, doc, fs),
            e => e.code === 'SAFETY_ERROR'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PERSIST: never silently overwrites different valid content — evolution only from the base doc', () => {
    const dir = tmpDir('obs-persist3-');
    try {
        const runDir = path.join(dir, 'run');
        fs.mkdirSync(runDir, { recursive: true });
        const ctx = {
            runId: 'run-1',
            planSha256: 'a'.repeat(64),
            authorizationId: 'AUTH',
            maxRequests: 2,
            collectorCodeRevision: 'b'.repeat(40),
        };
        const docA = defaultObservationsDoc(ctx);
        writeTransportObservationsFile(runDir, docA, fs);

        const entry = buildTransportObservation({
            ordinal: 1,
            sourceMatchId: '4193752',
            requestStartedAtIso: '2026-08-06T17:39:04.538Z',
            requestFinishedAtIso: '2026-08-06T17:39:04.800Z',
            elapsedMs: 262,
            lastReliablePhase: 'RESPONSE_BODY_COMPLETED',
            terminalOutcome: 'COMPLETED',
            responseHeadersReceived: true,
            responseHeadersReceivedAt: '2026-08-06T17:39:04.600Z',
            httpStatus: 200,
            bodyReadingStarted: true,
            bodyReadingStartedAt: '2026-08-06T17:39:04.601Z',
            bodyBytesReceived: 100,
            bodyCompleted: true,
            bodyCompletedAt: '2026-08-06T17:39:04.800Z',
            timeoutConfiguredMs: 30000,
            timeoutTriggered: false,
            abortSource: null,
            errorName: null,
            errorCode: null,
            errorCauseName: null,
            errorCauseCode: null,
            responseMetadata: null,
        });
        const docB = settleObservationInDoc(docA, entry);
        // Different valid content with NO base → refused.
        assert.throws(
            () => writeTransportObservationsFile(runDir, docB, fs),
            e => e.code === 'SAFETY_ERROR'
        );
        // Same doc, base = the on-disk doc → the run's own evolution, allowed.
        assert.equal(writeTransportObservationsFile(runDir, docB, fs, docA), 'written');
        // A tampered file (valid JSON, broken hash) is never overwritten.
        const tampered = JSON.parse(fs.readFileSync(OBSERVATIONS_PATH(runDir), 'utf8'));
        tampered.observations_sha256 = '0'.repeat(64);
        fs.writeFileSync(OBSERVATIONS_PATH(runDir), JSON.stringify(tampered));
        assert.throws(
            () => writeTransportObservationsFile(runDir, docB, fs, docB),
            e => e.code === 'SAFETY_ERROR'
        );
        assert.throws(
            () => readTransportObservationsFile(runDir, fs),
            e => e.code === 'SAFETY_ERROR'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// E. Loopback: real HTTP bound to 127.0.0.1 only
// ─────────────────────────────────────────────────────────────

function startLoopbackServer(handler) {
    const server = http.createServer((req, res) => {
        Promise.resolve(handler(req, res)).catch(() => {
            try {
                res.destroy();
            } catch {
                /* ignore */
            }
        });
    });
    return new Promise(resolve => {
        server.listen(0, '127.0.0.1', () => {
            const { port } = server.address();
            resolve({
                server,
                port,
                close: () =>
                    new Promise(r => {
                        try {
                            server.closeAllConnections();
                        } catch {
                            /* ignore */
                        }
                        server.close(() => r());
                    }),
            });
        });
    });
}

const makeLoopbackFetch = (port, state) => async (url, opts) => {
    state.loopbackCalls = (state.loopbackCalls || 0) + 1;
    // The adapter already validated the fotmob.com URL shape; the injected
    // implementation here talks ONLY to the 127.0.0.1 loopback server,
    // forwarding the adapter's AbortSignal and redirect mode verbatim.
    return REAL_FETCH(`http://127.0.0.1:${port}/match/123`, {
        method: opts.method,
        redirect: opts.redirect,
        signal: opts.signal,
        headers: opts.headers,
    });
};

test('LOOPBACK: real 127.0.0.1 HTTP fast success — observation matches the true bytes and status', async () => {
    const serverCtl = await startLoopbackServer((req, res) => {
        const body = '<html>loopback-ok</html>';
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Content-Length': Buffer.byteLength(body) });
        res.end(body);
    });
    const state = {};
    try {
        const adapter = createBoundedFetchAdapter({
            fetchImpl: makeLoopbackFetch(serverCtl.port, state),
            maxRequests: 1,
            delayMs: 60000,
            sleepImpl: async () => {},
            timeoutMs: 5000,
        });
        const res = await adapter.fetchOnce('https://www.fotmob.com/match/4193752', {
            ordinal: 1,
            sourceMatchId: '4193752',
        });
        assert.equal(res.status, 200);
        const obs = res.transportObservation;
        assert.equal(obs.terminal_outcome, 'COMPLETED');
        assert.equal(obs.last_reliable_phase, 'RESPONSE_BODY_COMPLETED');
        assert.equal(obs.http_status, 200);
        assert.equal(obs.body_completed, true);
        assert.equal(obs.body_bytes_received, Buffer.byteLength('<html>loopback-ok</html>'));
        assert.equal(obs.response_metadata.content_type, 'text/html; charset=utf-8');
        assert.equal(obs.response_metadata.declared_content_length, Buffer.byteLength('<html>loopback-ok</html>'));
        assert.equal(obs.response_metadata.redirected, false);
        assert.ok(validateTransportObservation(obs).ok);
    } finally {
        await serverCtl.close();
    }
});

test('LOOPBACK: real headers stall past the timeout — AWAITING_RESPONSE_HEADERS, TIMEOUT, 0 bytes', async () => {
    const serverCtl = await startLoopbackServer((req, res) => {
        setTimeout(() => {
            try {
                res.writeHead(200, { 'Content-Type': 'text/html' });
                res.end('<html>too-late</html>');
            } catch {
                /* socket gone after abort — expected */
            }
        }, 400);
    });
    const state = {};
    try {
        const adapter = createBoundedFetchAdapter({
            fetchImpl: makeLoopbackFetch(serverCtl.port, state),
            maxRequests: 1,
            delayMs: 60000,
            sleepImpl: async () => {},
            timeoutMs: 120,
        });
        let err = null;
        try {
            await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
        } catch (e) {
            err = e;
        }
        assert.ok(err, 'must reject');
        const obs = err.transportObservation;
        assert.equal(obs.last_reliable_phase, 'AWAITING_RESPONSE_HEADERS');
        assert.equal(obs.response_headers_received, false);
        assert.equal(obs.body_bytes_received, 0);
        assert.equal(obs.terminal_outcome, 'TIMEOUT');
        assert.equal(obs.timeout_triggered, true);
        assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
        assert.ok(validateTransportObservation(obs).ok);
    } finally {
        await serverCtl.close();
    }
});

test('LOOPBACK: real body stall after headers — READING_RESPONSE_BODY, real status, partial bytes', async () => {
    const serverCtl = await startLoopbackServer((req, res) => {
        res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Transfer-Encoding': 'chunked' });
        res.write('<html>partial-');
        // Never end: the body stalls after the first chunk.
    });
    const state = {};
    try {
        const adapter = createBoundedFetchAdapter({
            fetchImpl: makeLoopbackFetch(serverCtl.port, state),
            maxRequests: 1,
            delayMs: 60000,
            sleepImpl: async () => {},
            timeoutMs: 120,
        });
        let err = null;
        try {
            await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
        } catch (e) {
            err = e;
        }
        assert.ok(err, 'must reject');
        const obs = err.transportObservation;
        assert.equal(obs.last_reliable_phase, 'READING_RESPONSE_BODY');
        assert.equal(obs.response_headers_received, true);
        assert.equal(obs.http_status, 200);
        assert.equal(obs.body_reading_started, true);
        assert.equal(obs.body_completed, false);
        assert.ok(obs.body_bytes_received > 0, 'the delivered chunk is counted');
        assert.equal(obs.terminal_outcome, 'TIMEOUT');
        assert.equal(obs.timeout_triggered, true);
        assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
        assert.ok(validateTransportObservation(obs).ok);
    } finally {
        await serverCtl.close();
    }
});

// ─────────────────────────────────────────────────────────────
// F. Timer / resource cleanup — the process must exit promptly
// ─────────────────────────────────────────────────────────────

test('TIMERS: no residual timers — the adapter process exits promptly after success and timeout', () => {
    // Child script: (1) fast success with the REAL 30 s default timeout — a
    // leaked timer would keep the process alive 30 s; (2) a real 150 ms
    // timeout abort. The parent fails the test if the child does not exit
    // quickly with both markers.
    const modulePath = path.resolve(__dirname, '../../src/infrastructure/fotmob/FotMobDetailCapturePipeline.js');
    const script = `
'use strict';
const { createBoundedFetchAdapter } = require(${JSON.stringify(modulePath)});
(async () => {
    const fast = createBoundedFetchAdapter({
        fetchImpl: async () => ({
            status: 200,
            url: 'https://www.fotmob.com/match/1',
            headers: { get: () => null },
            arrayBuffer: async () => new TextEncoder().encode('ok'),
        }),
        maxRequests: 4,
        delayMs: 60000,
        sleepImpl: async () => {},
    });
    await fast.fetchOnce('https://www.fotmob.com/match/1', { ordinal: 1, sourceMatchId: '1' });
    process.stdout.write('FAST_OK\\n');

    const slow = createBoundedFetchAdapter({
        fetchImpl: (url, opts) => new Promise((resolve, reject) => {
            opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
        }),
        maxRequests: 4,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs: 150,
    });
    try {
        await slow.fetchOnce('https://www.fotmob.com/match/2', { ordinal: 2, sourceMatchId: '2' });
    } catch { /* expected timeout */ }
    process.stdout.write('TIMEOUT_OK\\n');
})();
`;
    const child = spawnSync(process.execPath, ['-e', script], {
        cwd: REPO_ROOT,
        timeout: 10000,
        encoding: 'utf8',
    });
    assert.equal(child.status, 0, `child must exit 0: ${child.stderr}`);
    assert.ok(child.stdout.includes('FAST_OK'), 'fast success completed');
    assert.ok(child.stdout.includes('TIMEOUT_OK'), 'timeout path completed');
});

// ─────────────────────────────────────────────────────────────
// P2-1 remediation: run-summary telemetry linkage reflects the
// VERIFIED FINAL ON-DISK state, never the pending in-memory doc
// (Codex F2-1: a final telemetry write failure must not produce a
// summary that references an unwritten observations file).
// ─────────────────────────────────────────────────────────────

function makeObsDocFixture({ runId, planSha, authId, maxRequests, revision }) {
    return defaultObservationsDoc({
        runId,
        planSha256: planSha,
        authorizationId: authId,
        maxRequests,
        collectorCodeRevision: revision,
    });
}

test('P2-1 helper: absent file → null (no telemetry linkage claim possible)', () => {
    const dir = tmpDir('p21-helper-absent-');
    try {
        const expected = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        assert.equal(reconcilePersistedObservationsDoc({ runDir: dir, expectedDoc: expected }), null);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1 helper: valid persisted doc with matching bindings → the ACTUAL doc is returned', () => {
    const dir = tmpDir('p21-helper-valid-');
    try {
        const doc = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        assert.equal(writeTransportObservationsFile(dir, doc, fs), 'written');
        const persisted = reconcilePersistedObservationsDoc({ runDir: dir, expectedDoc: doc });
        assert.ok(persisted, 'persisted doc must be returned');
        assert.equal(persisted.run_id, 'run-p21');
        assert.equal(persisted.observations.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1 helper: foreign valid doc (binding mismatch) → null, file untouched', () => {
    const dir = tmpDir('p21-helper-foreign-');
    try {
        const doc = makeObsDocFixture({
            runId: 'run-foreign',
            planSha: 'a'.repeat(64),
            authId: 'other-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        assert.equal(writeTransportObservationsFile(dir, doc, fs), 'written');
        const expected = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        assert.equal(
            reconcilePersistedObservationsDoc({ runDir: dir, expectedDoc: expected }),
            null,
            'a foreign valid doc is never claimed'
        );
        // The foreign file is NOT overwritten or deleted.
        assert.deepEqual(readTransportObservationsFile(dir, fs).run_id, 'run-foreign');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1 helper: unreadable / invalid file → null, file untouched', () => {
    const dir = tmpDir('p21-helper-invalid-');
    try {
        const expected = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        fs.writeFileSync(OBSERVATIONS_PATH(dir), '{ not valid json\n', 'utf8');
        assert.equal(reconcilePersistedObservationsDoc({ runDir: dir, expectedDoc: expected }), null);
        assert.equal(fs.readFileSync(OBSERVATIONS_PATH(dir), 'utf8'), '{ not valid json\n');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1 helper: symlink / non-regular target → null, target untouched', () => {
    const dir = tmpDir('p21-helper-symlink-');
    try {
        const expected = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        const targetDir = path.join(dir, 'target');
        fs.mkdirSync(targetDir);
        const doc = makeObsDocFixture({
            runId: 'run-p21',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        writeTransportObservationsFile(targetDir, doc, fs);
        fs.symlinkSync(path.join(targetDir, OBSERVATIONS_FILE_NAME), OBSERVATIONS_PATH(dir));
        assert.equal(reconcilePersistedObservationsDoc({ runDir: dir, expectedDoc: expected }), null);
        assert.ok(fs.lstatSync(OBSERVATIONS_PATH(dir)).isSymbolicLink(), 'symlink untouched');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1: normal fresh telemetry write — summary links to the ACTUAL persisted file, count matches, replay byte-identical', async () => {
    const dir = tmpDir('p21-fresh-');
    try {
        const cand1 = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const cand2 = makeCandidate({ id: 4506625, season: '2024/2025', home: 'C', away: 'D', kickoff: '2024-08-17T11:30:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand1, cand2], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(
            url => (String(url).includes('4506625') ? okResponse(pageFor(cand2)) : okResponse(pageFor(cand1))),
            calls
        );
        const run = await executeCaptureRun(
            makeCaptureOptions({ dir, plan, planPath, runId: 'run-p21-fresh', maxRequests: 2, fetchImpl })
        );
        assert.equal(run.status, 'complete');
        assert.equal(calls.length, 2);
        const persisted = readObservations(run.runDir);
        assert.equal(persisted.observations.length, 2);
        const summary = JSON.parse(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.transport_observations_file, OBSERVATIONS_FILE_NAME);
        assert.equal(summary.transport_observations_count, persisted.observations.length, 'count matches the ACTUAL persisted file');
        // Replay reads the SAME file — rebuilt summary byte-identical.
        const summaryBefore = fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8');
        const { runReplay } = require('../../scripts/ops/fotmob_detail_capture');
        const replay = runReplay(
            { 'run-dir': run.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay.replayed_count, 2);
        assert.equal(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'), summaryBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1: final write reports unchanged — summary reflects the ACTUAL persisted doc', async () => {
    const dir = tmpDir('p21-unchanged-');
    try {
        const cand = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const run1 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-p21-unchanged',
                maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(cand))),
            })
        );
        assert.equal(run1.status, 'complete');
        const summary1 = fs.readFileSync(path.join(run1.runDir, 'run-summary.json'), 'utf8');
        // Resume: everything is already complete — the final write returns
        // 'unchanged' (identical bytes); the summary still reflects the
        // ACTUAL persisted doc.
        const calls2 = [];
        const run2 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-p21-unchanged',
                maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(cand)), calls2),
            })
        );
        assert.equal(run2.status, 'complete');
        assert.equal(calls2.length, 0, 'no re-fetch on resume');
        const persisted = readObservations(run2.runDir);
        const summary2 = JSON.parse(fs.readFileSync(path.join(run2.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary2.transport_observations_count, persisted.observations.length, 'summary reflects the actual persisted doc');
        assert.equal(fs.readFileSync(path.join(run2.runDir, 'run-summary.json'), 'utf8'), summary1, 'resume summary byte-identical');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1: fresh run + FINAL telemetry write failure + no file persisted — primary outcome unchanged, summary has NO phantom linkage, replay byte-identical', async () => {
    const dir = tmpDir('p21-failfresh-');
    try {
        const cand = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const calls = [];
        const run = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-p21-failfresh',
                maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(cand)), calls),
                fsImpl: observationsWriteFailingFsImpl(),
            })
        );
        // Primary capture outcome unchanged: complete, one request, one capture.
        assert.equal(run.status, 'complete');
        assert.equal(run.completedCount, 1);
        assert.equal(calls.length, 1, 'no extra network request');
        assert.equal(fs.existsSync(OBSERVATIONS_PATH(run.runDir)), false, 'no file persisted');
        const summary = JSON.parse(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.status, 'complete');
        assert.equal(summary.network_requests_attempted, 1);
        assert.equal(summary.captures_completed, 1);
        assert.equal(summary.database_writes, 0);
        assert.equal(summary.transport_observations_file, undefined, 'NO phantom file link');
        assert.equal(summary.transport_observations_count, undefined, 'NO phantom count');
        // CAPTURE ↔ REPLAY consistency on the failure path: replay reads the
        // same disk truth (absent file) and rebuilds the same summary.
        const summaryBefore = fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8');
        const { runReplay } = require('../../scripts/ops/fotmob_detail_capture');
        const replay = runReplay(
            { 'run-dir': run.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay.replayed_count, 1);
        assert.equal(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'), summaryBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1: resume + valid base observations file + evolved final write fails — summary reflects the ACTUAL persisted base doc, not the failed in-memory evolution; replay byte-identical', async () => {
    const dir = tmpDir('p21-failresume-');
    try {
        const cand1 = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const cand2 = makeCandidate({ id: 4506625, season: '2024/2025', home: 'C', away: 'D', kickoff: '2024-08-17T11:30:00Z' });
        const cand3 = makeCandidate({ id: 4506265, season: '2024/2025', home: 'E', away: 'F', kickoff: '2024-08-17T14:00:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand1, cand2, cand3], { seasons: ['2024/2025'] });

        // Cycle 1: ordinal 1 completes, ordinal 2 is 403 → access-control
        // stop; the persisted base file has exactly 2 observations.
        const calls1 = [];
        const fetchImpl1 = mockFetchImpl(
            url => (String(url).includes('4506625') ? { status: 403, body: '<html>forbidden</html>' } : okResponse(pageFor(cand1))),
            calls1
        );
        const run1 = await executeCaptureRun(
            makeCaptureOptions({ dir, plan, planPath, runId: 'run-p21-failresume', maxRequests: 4, fetchImpl: fetchImpl1 })
        );
        assert.equal(run1.status, 'stopped');
        assert.equal(run1.completedCount, 1);
        assert.equal(calls1.length, 2);
        const baseDoc = readObservations(run1.runDir);
        assert.equal(baseDoc.observations.length, 2);

        // Cycle 2 (resume) with failing observations WRITES: ordinals 2 and
        // 3 succeed in memory (pending doc would hold 3 observations), but
        // the FINAL telemetry write fails. The old valid base file remains
        // on disk — the summary must reflect THAT ACTUAL persisted state.
        const calls2 = [];
        const fetchImpl2 = mockFetchImpl(
            url => okResponse(pageFor(String(url).includes('4506625') ? cand2 : cand3)),
            calls2
        );
        const run2 = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-p21-failresume',
                maxRequests: 4,
                fetchImpl: fetchImpl2,
                fsImpl: observationsWriteFailingFsImpl(),
            })
        );
        assert.equal(run2.status, 'complete');
        assert.equal(run2.completedCount, 3);
        assert.equal(calls2.length, 2, 'ordinal 1 skipped on resume; ordinals 2 and 3 fetched — no extra request');
        const persistedAfter = readObservations(run2.runDir);
        assert.equal(persistedAfter.observations.length, 2, 'old persisted base file remains (2 entries)');
        const summary = JSON.parse(fs.readFileSync(path.join(run2.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.status, 'complete');
        assert.equal(summary.network_requests_attempted, 4, 'primary attempt counts unchanged by telemetry failure (2 in cycle 1 + 2 in cycle 2)');
        assert.equal(summary.captures_completed, 3);
        assert.equal(
            summary.transport_observations_count,
            persistedAfter.observations.length,
            'summary count matches the ACTUAL persisted base doc — it does NOT claim the failed in-memory newer observation (3)'
        );
        // Replay reads the same base file → same summary, byte-identical.
        const summaryBefore = fs.readFileSync(path.join(run2.runDir, 'run-summary.json'), 'utf8');
        const { runReplay } = require('../../scripts/ops/fotmob_detail_capture');
        const replay = runReplay(
            { 'run-dir': run2.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay.replayed_count, 3);
        assert.equal(fs.readFileSync(path.join(run2.runDir, 'run-summary.json'), 'utf8'), summaryBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-1: read-back uncertainty — final write throws after the rename landed but the file re-reads and validates → reconciliation uses the ACTUAL validated file', async () => {
    const dir = tmpDir('p21-readback-');
    try {
        const cand = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const calls = [];
        const run = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-p21-readback',
                maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(cand)), calls),
                fsImpl: observationsFirstReadFailingFsImpl(),
            })
        );
        assert.equal(run.status, 'complete');
        assert.equal(calls.length, 1, 'no extra network request');
        assert.equal(fs.existsSync(OBSERVATIONS_PATH(run.runDir)), true, 'the intended document DID land');
        const persisted = readObservations(run.runDir);
        assert.equal(persisted.observations.length, 1);
        const summary = JSON.parse(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(
            summary.transport_observations_count,
            persisted.observations.length,
            'summary links the ACTUAL validated persisted document, not an assumption'
        );
        const summaryBefore = fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8');
        const { runReplay } = require('../../scripts/ops/fotmob_detail_capture');
        const replay = runReplay(
            { 'run-dir': run.runDir },
            { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }
        );
        assert.equal(replay.replayed_count, 1);
        assert.equal(fs.readFileSync(path.join(run.runDir, 'run-summary.json'), 'utf8'), summaryBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// P2-LSTAT: only ENOENT means absent — all other lstatSync failures
// fail closed (SAFETY_ERROR) on both read and write paths, and the
// pipeline fails BEFORE any network request when a pre-existing
// telemetry target cannot be inspected.
// ─────────────────────────────────────────────────────────────

/**
 * fsImpl wrapper that fails lstatSync for the transport-observations target
 * with a chosen error code (ENOENT / EACCES / EIO / ...). With `once: true`
 * only the FIRST such lstat fails (the "ENOENT first inspection sees absent"
 * case — the write and its read-back then proceed normally); with
 * `once: false` every observations-path lstat fails. Also counts
 * observations-path writeFileSync / renameSync / readFileSync calls so
 * tests can prove no write or read is ever attempted after an inspection
 * failure. Every other fs operation passes through to the base fs.
 */
function observationsLstatFailingFsImpl({ code, once = false }, base = fs) {
    let failed = false;
    const calls = { writeFileSync: 0, renameSync: 0, readFileSync: 0 };
    return {
        calls,
        fsImpl: new Proxy(base, {
            get(target, prop) {
                const value = target[prop];
                if (prop === 'lstatSync') {
                    return (...args) => {
                        const p = String(args[0] || '');
                        if (p.includes(OBSERVATIONS_FILE_NAME) && (!once || !failed)) {
                            failed = true;
                            const err = new Error(`simulated lstat failure: ${code}`);
                            err.code = code;
                            throw err;
                        }
                        return value.apply(target, args);
                    };
                }
                if (prop === 'writeFileSync' || prop === 'renameSync' || prop === 'readFileSync') {
                    return (...args) => {
                        const p = String(args[0] || '');
                        if (p.includes(OBSERVATIONS_FILE_NAME)) {
                            calls[prop] += 1;
                        }
                        return value.apply(target, args);
                    };
                }
                return typeof value === 'function' ? value.bind(target) : value;
            },
        }),
    };
}

test('P2-LSTAT A: read — ENOENT is valid absence, returns null, no safety failure', () => {
    const dir = tmpDir('p22-lstat-a-');
    try {
        const { fsImpl } = observationsLstatFailingFsImpl({ code: 'ENOENT' });
        assert.equal(readTransportObservationsFile(dir, fsImpl), null);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT B: read — EACCES fails closed with SAFETY_ERROR, no readFileSync attempted', () => {
    const dir = tmpDir('p22-lstat-b-');
    try {
        const { calls, fsImpl } = observationsLstatFailingFsImpl({ code: 'EACCES' });
        assert.throws(
            () => readTransportObservationsFile(dir, fsImpl),
            err => {
                assert.equal(err.code, 'SAFETY_ERROR');
                assert.ok(
                    String(err.message).includes('cannot inspect transport observations target'),
                    'error identifies the uninspectable observations target'
                );
                assert.ok(String(err.message).includes('EACCES'), 'error carries the bounded code');
                return true;
            }
        );
        assert.equal(calls.readFileSync, 0, 'no readFileSync after a failed inspection');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT C: read — EIO fails closed with SAFETY_ERROR, no readFileSync attempted', () => {
    const dir = tmpDir('p22-lstat-c-');
    try {
        const { calls, fsImpl } = observationsLstatFailingFsImpl({ code: 'EIO' });
        assert.throws(
            () => readTransportObservationsFile(dir, fsImpl),
            err => {
                assert.equal(err.code, 'SAFETY_ERROR');
                assert.ok(String(err.message).includes('cannot inspect transport observations target'));
                assert.ok(String(err.message).includes('EIO'));
                return true;
            }
        );
        assert.equal(calls.readFileSync, 0, 'no readFileSync after a failed inspection');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT D: write — ENOENT target inspection allows the normal first write', () => {
    const dir = tmpDir('p22-lstat-d-');
    try {
        const doc = makeObsDocFixture({
            runId: 'run-p22-d',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        const { fsImpl } = observationsLstatFailingFsImpl({ code: 'ENOENT', once: true });
        assert.equal(writeTransportObservationsFile(dir, doc, fsImpl), 'written');
        assert.ok(fs.existsSync(OBSERVATIONS_PATH(dir)), 'intended file was created');
        const readBack = readTransportObservationsFile(dir, fs);
        assert.equal(readBack.run_id, 'run-p22-d');
        assert.equal(readBack.observations.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT E: write — EACCES fails closed, NO temp write, NO rename, target untouched', () => {
    const dir = tmpDir('p22-lstat-e-');
    try {
        const doc = makeObsDocFixture({
            runId: 'run-p22-e',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        const { calls, fsImpl } = observationsLstatFailingFsImpl({ code: 'EACCES' });
        assert.throws(
            () => writeTransportObservationsFile(dir, doc, fsImpl),
            err => {
                assert.equal(err.code, 'SAFETY_ERROR');
                assert.ok(String(err.message).includes('cannot inspect transport observations target'));
                return true;
            }
        );
        assert.equal(calls.writeFileSync, 0, 'temp file write NEVER called after inspection failure');
        assert.equal(calls.renameSync, 0, 'renameSync NEVER called after inspection failure');
        assert.equal(fs.existsSync(OBSERVATIONS_PATH(dir)), false, 'target remains untouched (absent)');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT F: write — EIO fails closed, NO temp write, NO rename, target untouched', () => {
    const dir = tmpDir('p22-lstat-f-');
    try {
        const doc = makeObsDocFixture({
            runId: 'run-p22-f',
            planSha: 'a'.repeat(64),
            authId: 'test-authorization-id',
            maxRequests: 1,
            revision: TEST_REVISION,
        });
        const { calls, fsImpl } = observationsLstatFailingFsImpl({ code: 'EIO' });
        assert.throws(
            () => writeTransportObservationsFile(dir, doc, fsImpl),
            err => {
                assert.equal(err.code, 'SAFETY_ERROR');
                assert.ok(String(err.message).includes('cannot inspect transport observations target'));
                return true;
            }
        );
        assert.equal(calls.writeFileSync, 0, 'temp file write NEVER called after inspection failure');
        assert.equal(calls.renameSync, 0, 'renameSync NEVER called after inspection failure');
        assert.equal(fs.existsSync(OBSERVATIONS_PATH(dir)), false, 'target remains untouched (absent)');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-LSTAT G: pipeline — uninspectable pre-existing telemetry fails closed BEFORE any network request', async () => {
    const dir = tmpDir('p22-lstat-g-');
    try {
        const cand = makeCandidate({ id: 4193752, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const runId = 'run-p22-g';
        const calls = [];
        const { fsImpl } = observationsLstatFailingFsImpl({ code: 'EACCES' });
        await assert.rejects(
            executeCaptureRun(
                makeCaptureOptions({
                    dir,
                    plan,
                    planPath,
                    runId,
                    maxRequests: 1,
                    fetchImpl: mockFetchImpl(() => okResponse(pageFor(cand)), calls),
                    fsImpl,
                })
            ),
            err => {
                assert.equal(err.code, 'SAFETY_ERROR');
                assert.ok(
                    String(err.message).includes('cannot inspect transport observations target'),
                    'pipeline surfaces the uninspectable telemetry target'
                );
                return true;
            }
        );
        assert.equal(calls.length, 0, 'fetch implementation NEVER called — fail closed before any request');
        const runDir = path.join(dir, 'out', 'runs', runId);
        assert.equal(fs.existsSync(OBSERVATIONS_PATH(runDir)), false, 'no telemetry target written');
        const capturesDir = path.join(runDir, 'captures');
        if (fs.existsSync(capturesDir)) {
            assert.deepEqual(fs.readdirSync(capturesDir), [], 'no capture pair produced');
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// TD-03 / EXOTIC ERROR DIAGNOSTIC SAFETY
// ─────────────────────────────────────────────────────────────
// Owner contract (TD-03): diagnostic inspection must NEVER mask or replace
// the original thrown value — even when a diagnostic property getter / Proxy
// get trap / value coercion throws. Throwing diagnostic getters are treated
// as unreadable metadata: classification continues from the remaining
// trustworthy evidence (phase flags + the local ctrl.signal), each diagnostic
// property is read AT MOST ONCE per snapshot (a stateful getter must not be
// re-triggered), and the ORIGINAL thrown value is rethrown unchanged
// (identity `error === original`). All tests offline: mocked fetchImpl only;
// global.fetch throws (REAL_FOTMOB_REQUESTS=0).

const SENTINEL_PREFIX = 'SENTINEL_GETTER_';

function sentinelError(name) {
    return new Error(SENTINEL_PREFIX + name);
}

function throwingGetter(obj, key, sentinel) {
    Object.defineProperty(obj, key, {
        configurable: true,
        get() {
            throw sentinel;
        },
    });
    return obj;
}

// A fresh, fully-readable transport error used as the base "original thrown
// value" for the hostile variants.
function originalTransportError() {
    const e = new Error('original transport failure');
    e.name = 'OriginalTransportError';
    e.code = 'E_ORIGINAL';
    const cause = new Error('original cause failure');
    cause.name = 'CauseError';
    cause.code = 'E_CAUSE';
    e.cause = cause;
    return e;
}

// Run one adapter fetch that must reject; returns the outward (rethrown)
// value.
async function adapterRejectsWith(fetchImpl, { timeoutMs = 30000 } = {}) {
    const adapter = createBoundedFetchAdapter({
        fetchImpl,
        maxRequests: 1,
        delayMs: 60000,
        sleepImpl: async () => {},
        timeoutMs,
    });
    let err = null;
    try {
        await adapter.fetchOnce('https://www.fotmob.com/match/4193752', { ordinal: 1, sourceMatchId: '4193752' });
    } catch (e) {
        err = e;
    }
    assert.ok(err !== null, 'the adapter must reject');
    return err;
}

// Matrix A–I: [label, decorate, expectedFallbacks]. Default expectations for
// the readable base error; each case overrides the fields whose getters are
// hostile (unavailable metadata must fall back deterministically).
const TD03_HOSTILE_CASES = [
    // A: err.code getter throws → code unavailable ('' fallback, never
    //    misclassified as SAFETY_ERROR), rest readable.
    ['A_CODE_GETTER', e => throwingGetter(e, 'code', sentinelError('code')), { error_code: '' }],
    // B: err.name getter throws → name falls back to 'Error' (never guessed
    //    as AbortError from nothing).
    ['B_NAME_GETTER', e => throwingGetter(e, 'name', sentinelError('name')), { error_name: 'Error' }],
    // C: err.message getter throws → abort-text heuristic unavailable (no
    //    misclassification from unavailable text).
    ['C_MESSAGE_GETTER', e => throwingGetter(e, 'message', sentinelError('message')), {}],
    // D: err.signal getter throws → signal-abort heuristic unavailable.
    ['D_SIGNAL_GETTER', e => throwingGetter(e, 'signal', sentinelError('signal')), {}],
    // E: err.cause getter throws → whole cause metadata unavailable (''), the
    //    cause getter is never re-triggered.
    ['E_CAUSE_GETTER', e => throwingGetter(e, 'cause', sentinelError('cause')), { error_cause_name: '', error_cause_code: '' }],
    // F: err.cause.name getter throws → cause name unavailable, cause code
    //    still readable. (The decorator returns the ORIGINAL error — the
    //    cause is only decorated, never substituted.)
    ['F_CAUSE_NAME_GETTER', e => {
        throwingGetter(e.cause, 'name', sentinelError('cause.name'));
        return e;
    }, { error_cause_name: '' }],
    // G: err.cause.code getter throws → cause code unavailable, cause name
    //    still readable.
    ['G_CAUSE_CODE_GETTER', e => {
        throwingGetter(e.cause, 'code', sentinelError('cause.code'));
        return e;
    }, { error_cause_code: '' }],
    // H: Proxy get trap throwing on the diagnostic core (code/name/message).
    ['H_PROXY_GET_TRAP', e => new Proxy(e, {
        get(target, key, receiver) {
            if (key === 'code' || key === 'name' || key === 'message') throw sentinelError('proxy.trap');
            return Reflect.get(target, key, receiver);
        },
    }), { error_code: '', error_name: 'Error' }],
    // I: hostile Symbol.toPrimitive coercion on err.code — the value itself
    //    reads fine, only String() throws → '' fallback, never a crash.
    ['I_HOSTILE_COERCION_CODE', e => {
        e.code = { [Symbol.toPrimitive]() { throw sentinelError('toPrimitive'); } };
        return e;
    }, { error_code: '' }],
];

const TD03_DEFAULT_EXPECTED = {
    error_name: 'OriginalTransportError',
    error_code: 'E_ORIGINAL',
    error_cause_name: 'CauseError',
    error_cause_code: 'E_CAUSE',
};

test('TD-03: matrix A–I — throwing diagnostic getters / Proxy trap / hostile coercion: original identity preserved, safe fallbacks, no sentinel leakage', async () => {
    for (const [label, decorate, expectedOverrides] of TD03_HOSTILE_CASES) {
        const original = originalTransportError();
        const hostile = decorate(original);
        const err = await adapterRejectsWith(async () => {
            throw hostile;
        });
        // 1) The ORIGINAL thrown value is rethrown unchanged — identity,
        //    never a message/name/code comparison that could be spoofed.
        assert.strictEqual(err, hostile, `${label}: original error identity preserved`);
        // 2) A getter sentinel must never escape outward.
        let outwardMsg = null;
        try {
            outwardMsg = String(err.message);
        } catch {
            /* unreadable message getter — the identity check above is authoritative */
        }
        if (outwardMsg !== null) {
            assert.ok(!outwardMsg.includes(SENTINEL_PREFIX), `${label}: no sentinel leaks outward`);
        }
        // 3) The observation rides the original error, validates, and the
        //    classification never crashes.
        const obs = err.transportObservation;
        assert.ok(obs, `${label}: observation attaches to the original error`);
        assert.ok(validateTransportObservation(obs).ok, `${label}: observation validates`);
        assert.equal(obs.terminal_outcome, 'FETCH_ERROR', `${label}: stays FETCH_ERROR (no guessed classification)`);
        // 4) Unreadable metadata falls back deterministically.
        const expected = { ...TD03_DEFAULT_EXPECTED, ...expectedOverrides };
        assert.equal(obs.error_code, expected.error_code, `${label}: error_code fallback`);
        assert.equal(obs.error_name, expected.error_name, `${label}: error_name fallback`);
        assert.equal(obs.error_cause_name, expected.error_cause_name, `${label}: error_cause_name fallback`);
        assert.equal(obs.error_cause_code, expected.error_cause_code, `${label}: error_cause_code fallback`);
        // 5) No raw hostile value is persisted into telemetry.
        for (const key of ['error_code', 'error_name', 'error_cause_name', 'error_cause_code']) {
            assert.ok(!String(obs[key] || '').includes(SENTINEL_PREFIX), `${label}: no sentinel text in ${key}`);
        }
    }
});

test('TD-03: snapshot-once — every diagnostic property is read AT MOST ONCE per snapshot', async () => {
    const counts = {};
    const e = originalTransportError();
    const makeCountingGetter = (obj, key, countKey) => {
        const value = obj[key];
        Object.defineProperty(obj, key, {
            configurable: true,
            get() {
                counts[countKey] = (counts[countKey] || 0) + 1;
                return value;
            },
        });
        return obj;
    };
    makeCountingGetter(e, 'code', 'code');
    makeCountingGetter(e, 'name', 'name');
    makeCountingGetter(e, 'message', 'message');
    makeCountingGetter(e, 'signal', 'signal');
    // Capture the cause object BEFORE installing the counting getter on
    // `cause` — argument evaluation would otherwise re-read the getter and
    // pollute the read count.
    const causeObj = e.cause;
    makeCountingGetter(e, 'cause', 'cause');
    makeCountingGetter(causeObj, 'name', 'causeName');
    makeCountingGetter(causeObj, 'code', 'causeCode');
    const err = await adapterRejectsWith(async () => {
        throw e;
    });
    assert.strictEqual(err, e, 'identity preserved through the snapshot reads');
    assert.equal(counts.code, 1, 'err.code read exactly once');
    assert.equal(counts.name, 1, 'err.name read exactly once');
    assert.equal(counts.message, 1, 'err.message read exactly once');
    assert.equal(counts.signal, 1, 'err.signal read exactly once');
    assert.equal(counts.cause, 1, 'err.cause read exactly once');
    assert.equal(counts.causeName, 1, 'err.cause.name read exactly once');
    assert.equal(counts.causeCode, 1, 'err.cause.code read exactly once');
    const obs = err.transportObservation;
    assert.equal(obs.error_name, 'OriginalTransportError', 'readable metadata still flows through');
    assert.equal(obs.error_code, 'E_ORIGINAL');
    assert.ok(validateTransportObservation(obs).ok);
});

test('TD-03: J — frozen original error: identity preserved, attachment loss acceptable, no crash', async () => {
    const e = Object.freeze(originalTransportError());
    const err = await adapterRejectsWith(async () => {
        throw e;
    });
    assert.strictEqual(err, e, 'frozen original error rethrown unchanged');
    assert.equal(err.transportObservation, undefined, 'frozen error cannot carry the observation — attachment loss is acceptable, identity is not');
});

test('TD-03: K — normal SAFETY_ERROR classification unchanged', async () => {
    const e = new Error('safety gate');
    e.code = 'SAFETY_ERROR';
    const err = await adapterRejectsWith(async () => {
        throw e;
    });
    assert.strictEqual(err, e);
    const obs = err.transportObservation;
    assert.equal(obs.terminal_outcome, 'SAFETY_ERROR');
    assert.equal(obs.error_code, 'SAFETY_ERROR');
    assert.equal(obs.error_name, 'Error');
    assert.ok(validateTransportObservation(obs).ok);
});

test('TD-03: L — normal AbortError classification unchanged', async () => {
    const e = new Error('This operation was aborted');
    e.name = 'AbortError';
    const err = await adapterRejectsWith(async () => {
        throw e;
    });
    assert.strictEqual(err, e);
    const obs = err.transportObservation;
    assert.equal(obs.terminal_outcome, 'ABORTED');
    assert.equal(obs.abort_source, 'EXTERNAL_ABORT');
    assert.equal(obs.error_name, 'AbortError');
    assert.ok(validateTransportObservation(obs).ok);
});

test('TD-03: M — normal FETCH_ERROR classification unchanged; primitive throws are never wrapped', async () => {
    const err1 = await adapterRejectsWith(async () => {
        throw new TypeError('fetch failed');
    });
    const obs1 = err1.transportObservation;
    assert.equal(obs1.terminal_outcome, 'FETCH_ERROR');
    assert.equal(obs1.error_name, 'TypeError');
    assert.equal(obs1.error_code, '');
    assert.ok(validateTransportObservation(obs1).ok);

    const primitive = 'plain-string';
    const err2 = await adapterRejectsWith(async () => {
        throw primitive;
    });
    assert.strictEqual(err2, primitive, 'primitive thrown values are rethrown unchanged, never wrapped');

    // 3) A thrown object without a `name` property (or with `name: null`)
    //    must fall back to 'Error' — never the literal strings 'undefined' /
    //    'null' (TD-03 F-01, Codex P3), matching the pre-fix behavior.
    const nameless = { message: 'boom' };
    const err3 = await adapterRejectsWith(async () => {
        throw nameless;
    });
    assert.strictEqual(err3, nameless, 'plain thrown objects are rethrown unchanged');
    const obs3 = err3.transportObservation;
    assert.equal(obs3.terminal_outcome, 'FETCH_ERROR');
    assert.equal(obs3.error_name, 'Error', 'missing name falls back to Error, not "undefined"');
    assert.equal(obs3.error_code, '', 'missing code falls back to empty string');
    assert.ok(validateTransportObservation(obs3).ok);

    const nullName = { name: null, message: 'boom' };
    const err4 = await adapterRejectsWith(async () => {
        throw nullName;
    });
    const obs4 = err4.transportObservation;
    assert.equal(obs4.error_name, 'Error', 'null name falls back to Error, not "null"');
    assert.ok(validateTransportObservation(obs4).ok);
});

test('TD-03: N — normal BODY_READ_ERROR classification unchanged', async () => {
    const err = await adapterRejectsWith(
        signalFetchImpl(() =>
            makeResponse({
                status: 200,
                reader: {
                    async read() {
                        throw Object.assign(new Error('stream corrupt'), { name: 'StreamCorruptError' });
                    },
                },
            })
        )
    );
    assert.equal(err.name, 'StreamCorruptError');
    const obs = err.transportObservation;
    assert.equal(obs.terminal_outcome, 'BODY_READ_ERROR');
    assert.equal(obs.body_reading_started, true, 'the body-read phase was entered before the failure');
    assert.equal(obs.error_name, 'StreamCorruptError');
    assert.ok(validateTransportObservation(obs).ok);
});

test('TD-03: O — TIMEOUT classification survives hostile getters on the abort error', async () => {
    const hostile = originalTransportError();
    throwingGetter(hostile, 'code', sentinelError('code'));
    throwingGetter(hostile, 'name', sentinelError('name'));
    throwingGetter(hostile, 'message', sentinelError('message'));
    throwingGetter(hostile, 'signal', sentinelError('signal'));
    throwingGetter(hostile, 'cause', sentinelError('cause'));
    const err = await adapterRejectsWith(
        (url, opts) =>
            new Promise((resolve, reject) => {
                opts.signal.addEventListener('abort', () => reject(hostile));
            }),
        { timeoutMs: 60 }
    );
    assert.strictEqual(err, hostile, 'identity preserved under TIMEOUT');
    const obs = err.transportObservation;
    assert.ok(obs, 'observation rides the original error');
    assert.equal(obs.terminal_outcome, 'TIMEOUT', 'the local timeout flag keeps priority');
    assert.equal(obs.abort_source, 'REQUEST_TIMEOUT');
    assert.equal(obs.timeout_triggered, true);
    assert.equal(obs.error_code, '', 'unavailable code falls back');
    assert.equal(obs.error_name, 'Error', 'unavailable name falls back');
    assert.equal(obs.error_cause_name, '', 'unavailable cause metadata falls back');
    assert.equal(obs.error_cause_code, '');
    assert.ok(validateTransportObservation(obs).ok);
});

test('TD-03: run path — executeCaptureRun with hostile getters: original error preserved end-to-end, safe stop reason, observation settled', async () => {
    const dir = tmpDir('td03-run-');
    try {
        const cand = makeCandidate({
            id: 4193752,
            season: '2024/2025',
            home: 'A',
            away: 'B',
            kickoff: '2024-08-16T19:00:00Z',
        });
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const hostile = originalTransportError();
        throwingGetter(hostile, 'code', sentinelError('code'));
        throwingGetter(hostile, 'name', sentinelError('name'));
        throwingGetter(hostile, 'message', sentinelError('message'));
        const result = await executeCaptureRun(
            makeCaptureOptions({
                dir,
                plan,
                planPath,
                runId: 'run-td03',
                maxRequests: 1,
                fetchImpl: async () => {
                    throw hostile;
                },
            })
        );
        assert.equal(result.status, 'stopped');
        assert.equal(result.stoppedAtOrdinal, 1);
        assert.match(result.stopReason, /^fetch_error:/, 'stop reason derived safely — no getter exception replaces the run outcome');
        const doc = readObservations(result.runDir);
        assert.equal(doc.observations.length, 1);
        const obs = doc.observations[0];
        assert.equal(obs.terminal_outcome, 'FETCH_ERROR');
        assert.equal(obs.error_code, '', 'unavailable code falls back in the persisted telemetry');
        assert.equal(obs.error_name, 'Error', 'unavailable name falls back');
        assert.ok(validateTransportObservation(obs).ok);
        const state = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-state.json'), 'utf8'));
        assert.equal(state.network_requests_attempted, 1);
        assert.match(state.last_network_request_attempted_at, /^\d{4}-\d{2}-\d{2}T/, 'requestAttemptedAt safely read and actualized');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
