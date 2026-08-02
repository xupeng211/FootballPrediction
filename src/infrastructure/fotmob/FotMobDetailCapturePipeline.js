'use strict';

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
    canonicalJsonHash,
    isPlainObject,
    evaluateContentValidity,
    BLOCK_MARKERS,
    assertNoSymlinkAncestors,
} = require('./FotMobDetailCaptureContract');

const {
    fetchFotMobRawDetail,
    buildStableRawPayload,
    sha256StableRawPayload,
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
 *   now? ()
 * }
 * @returns {{ fetchOnce: (url, opts) => Promise<object>, budget: { used, max }, requestCount: () => number }}
 */
function createBoundedFetchAdapter(options = {}) {
    const fetchImpl = options.fetchImpl || globalThis.fetch;
    const maxRequests = Number(options.maxRequests || 0);
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

    let requestCount = 0;
    let lastRequestAt = 0;

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
        if (requestCount >= maxRequests) {
            throw Object.assign(
                new Error(`SAFETY_ERROR:budget_exhausted:${requestCount}/${maxRequests}`),
                { code: 'SAFETY_ERROR' }
            );
        }
        requestCount += 1;
        if (options.onBeforeFetch) options.onBeforeFetch(url, requestCount);

        // Serialization: enforce the minimum inter-request delay.
        if (lastRequestAt > 0) {
            const elapsed = Date.now() - lastRequestAt;
            if (elapsed < delayMs) {
                await sleepImpl(delayMs - elapsed);
            }
        }
        lastRequestAt = Date.now();

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

            // A redirect response counts as the request itself; body is not read.
            const bodyBytes = redirected ? Buffer.alloc(0) : Buffer.from(await res.arrayBuffer());
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
            };
        } finally {
            clearTimeout(timer);
        }
    }

    return {
        fetchOnce,
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

    if (options.execute !== true) {
        errors.push('execute flag required (--execute)');
    }
    if (options.networkAuthorization !== true) {
        errors.push('networkAuthorization must be true');
    }
    if (String(env[REQUIRED_ENV_VAR] || '') !== '1') {
        errors.push(`environment variable ${REQUIRED_ENV_VAR}=1 required`);
    }
    const authorizationId = String(options.authorizationId || '').trim();
    if (!authorizationId) {
        errors.push('authorization id required (--authorization-id)');
    }
    const expectedPlanSha256 = String(options.expectedPlanSha256 || '').trim();
    if (!/^[0-9a-f]{64}$/.test(expectedPlanSha256)) {
        errors.push('expected-plan-sha256 must be 64 lowercase hex');
    }
    if (String(options.plan?.plan_business_sha256 || '') !== expectedPlanSha256) {
        errors.push('plan SHA-256 does not match expected-plan-sha256');
    }
    const maxRequests = Number(options.maxRequests || 0);
    if (!Number.isInteger(maxRequests) || maxRequests < 1) {
        errors.push('max-requests must be a positive integer');
    } else if (String(env[REQUIRED_ENV_BUDGET] || '') !== String(maxRequests)) {
        errors.push(`environment variable ${REQUIRED_ENV_BUDGET} must equal max-requests`);
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
        const root = path.resolve(String(options.outputRoot));
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
        request_method: 'GET',
        request_url: context.requestUrl,
        candidate_id: context.candidate.candidate_id,
        source_match_id: context.candidate.source_match_id,
        competition: context.candidate.competition,
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
        capture_started_at: context.captureStartedAt,
        capture_completed_at: context.captureCompletedAt,
        http_status: context.fetcherResult.http_status,
        content_type: context.fetcherResult.content_type,
        body_byte_size: context.fetcherResult.body_byte_length,
        body_sha256: context.fetcherResult.body_sha256,
        observed_match_id: context.observedMatchId,
        observed_match_id_match: context.observedMatchId === context.candidate.source_match_id,
        hydration_parse_ok: context.fetcherResult.hydration_parse_ok === true,
        transformed_api_format: context.fetcherResult.transformed_api_format === true,
        looks_like_valid_match_detail: context.fetcherResult.looks_like_valid_match_detail === true,
        has_stats: context.meta && context.meta.has_stats === true,
        has_lineup: context.meta && context.meta.has_lineup === true,
        has_shotmap: context.meta && context.meta.has_shotmap === true,
        stable_raw_payload_sha256: context.stableRawPayloadSha256,
        parser_component: 'NextDataParser',
        parser_version: 'V174.0.0',
        collector_component: GENERATOR_COMPONENT,
        collector_code_revision: context.collectorCodeRevision,
        raw_file_relative_path: context.rawFileName,
        network_authorization_mode: NETWORK_AUTHORIZATION_MODE,
    };
    const selfHash = canonicalJsonHash(
        Object.fromEntries(Object.entries(manifest).filter(([k]) => k !== 'capture_manifest_sha256'))
    );
    manifest.capture_manifest_sha256 = selfHash;
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
 *   resume? (default true)
 * }
 * @returns {Promise<object>} run result
 */
/* eslint-disable-next-line complexity */
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

    fsImpl.mkdirSync(capturesDir, { recursive: true });
    fsImpl.mkdirSync(replayDir, { recursive: true });

    // Resume: load existing run state bound to this plan SHA.
    let runState = readRunState(runDir, fsImpl);
    if (runState) {
        if (runState.plan_sha256 !== plan.plan_business_sha256) {
            throw Object.assign(
                new Error('run state plan SHA mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
        if (runState.authorization_id !== binding.authorizationId) {
            throw Object.assign(
                new Error('run state authorization id mismatch — refusing to continue'),
                { code: 'SAFETY_ERROR' }
            );
        }
    } else {
        runState = defaultRunState(plan, {
            runId: binding.runId,
            authorizationId: binding.authorizationId,
            maxRequests: binding.maxRequests,
            delayMs,
            startedAt: now(),
        });
        writeRunState(runDir, runState, fsImpl);
    }

    const budgetedFetch = createBoundedFetchAdapter({
        fetchImpl: options.fetchImpl,
        maxRequests: binding.maxRequests,
        delayMs,
        timeoutMs: options.timeoutMs,
        sleepImpl: options.sleepImpl,
    });

    const completedOrdinals = new Set(
        Array.isArray(runState.completed_ordinals) ? runState.completed_ordinals.map(Number) : []
    );
    // Budget counts only THIS run's real fetches (resume must not inherit
    // earlier runs' counts); the run-state record keeps the cumulative total
    // for the run id's audit trail.
    const priorNetworkRequests = Number(runState.network_requests_made || 0);
    let runNetworkRequests = 0;
    let stopReason = null;
    let stoppedAtOrdinal = null;

    for (const candidate of plan.candidates) {
        const ordinal = Number(candidate.ordinal || 0);
        if (ordinal === 0) continue;

        // Resume check BEFORE any fetch: completed pairs are never fetched again.
        if (options.resume !== false) {
            const pairCheck = checkCompletedPair({
                runDir,
                ordinal,
                sourceMatchId: candidate.source_match_id,
                fsImpl,
            });
            if (pairCheck.state === 'complete') {
                completedOrdinals.add(ordinal);
                continue;
            }
            if (pairCheck.state === 'partial' || pairCheck.state === 'mismatch') {
                stopReason = `resume_pair_${pairCheck.state}:ordinal_${ordinal}`;
                stoppedAtOrdinal = ordinal;
                break;
            }
        }

        // Serial per-candidate execution: exactly one bounded fetch per
        // candidate. The fetched response is passed to the detail fetcher
        // as a CACHED response — the fetcher's injected fetchFn must never
        // hit the network or consume budget a second time.
        const requestUrl = `${FOTMOB_BASE_URL}${candidate.expected_request_path}`;
        const captureStartedAt = now();

        let fetchResult;
        try {
            fetchResult = await budgetedFetch.fetchOnce(requestUrl);
            runNetworkRequests += 1;
        } catch (err) {
            // Fetch adapter errors (budget exhausted, protocol/host/path
            // violations, timeouts) stop the run.
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
        // enforces 17 checks: the 15 mandated gates plus 2 hex-format gates
        // (body_sha256_hex, stable_hash_64hex) — a fail-closed superset.
        let fetcherResult = null;
        let observedMatchId = null;
        let meta = null;
        let stableRawPayloadSha256 = null;
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
                observedMatchId = fetcherResult.raw_data && (fetcherResult.raw_data.matchId ?? null) !== null
                    ? String(fetcherResult.raw_data.matchId)
                    : null;
                meta = fetcherResult.raw_data && fetcherResult.raw_data._meta
                    ? fetcherResult.raw_data._meta
                    : null;
                const stable = fetcherResult.raw_data
                    ? buildStableRawPayload(fetcherResult.raw_data, {}, {})
                    : null;
                stableRawPayloadSha256 = stable ? sha256StableRawPayload(stable) : null;
                const extracted = parser.extractFromHtml
                    ? parser.extractFromHtml(fetchResult.body)
                    : null;
                nextData = extracted && extracted.success === true ? extracted.data : null;
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

        // Retention: raw + manifest paired, atomic, verified.
        const rawFileName = `${ordinal}-${candidate.source_match_id}.html`;
        const manifest = buildCaptureManifest({
            candidate,
            plan,
            runId: binding.runId,
            authorizationId: binding.authorizationId,
            ordinal,
            maxRequests: binding.maxRequests,
            delayMs,
            captureStartedAt,
            captureCompletedAt: now(),
            fetcherResult,
            observedMatchId,
            meta,
            stableRawPayloadSha256,
            rawFileName,
            collectorCodeRevision: binding.collectorCodeRevision,
            requestUrl,
        });

        try {
            writeCapturePair({
                rawBody: fetchResult.bodyBytes,
                manifest,
                rawFileName,
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
        runState.completed_ordinals = [...completedOrdinals].sort((a, b) => a - b);
        runState.network_requests_made = priorNetworkRequests + runNetworkRequests;
        runState.real_fotmob_network_requests = runState.network_requests_made;
        writeRunState(runDir, runState, fsImpl);
    }

    const completed = completedOrdinals.size;
    const total = plan.candidates.length;
    runState.status = stopReason ? 'stopped' : (completed === total ? 'complete' : 'in_progress');
    runState.stopped_at_ordinal = stoppedAtOrdinal;
    runState.stop_reason = stopReason;
    runState.network_requests_made = priorNetworkRequests + runNetworkRequests;
    runState.real_fotmob_network_requests = runState.network_requests_made;
    runState.completed_ordinals = [...completedOrdinals].sort((a, b) => a - b);
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
