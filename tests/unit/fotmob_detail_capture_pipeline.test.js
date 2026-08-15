'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
// CAPTURE-stage tests for the bounded FotMob detail capture pipeline.
// Fully offline and mocked: real network is structurally forbidden.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const {
    buildDeterministicCapturePlan,
    writePlanDocument,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const {
    computeBusinessContentHash,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const {
    executeCaptureRun,
    createBoundedFetchAdapter,
    validateAuthorizationBinding,
    evaluateAccessControl,
    REQUIRED_ENV_VAR,
    REQUIRED_ENV_BUDGET,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
const {
    computeCaptureManifestSelfHash,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const TEST_REVISION = 'a7da729fd29675c6f16e1bfc49511772d2bd590d';
const FIXED_CLOCK = '2026-08-02T12:00:00.000Z';
const CLEAN_EXEC = (cmd) => (String(cmd).includes('rev-parse') ? `${TEST_REVISION}\n` : '');

function sha256Text(text) {
    return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

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

/**
 * Build a valid SSR match detail page fixture.
 * general/header carry the team markers + match time so the route identity
 * reconciler sees an identity_match / date_match.
 */
function makePageHtml({ matchId, homeTeam, awayTeam, kickoffAt, content, pagePropsExtra, homeTeamId, awayTeamId }) {
    const safeContent = content !== undefined
        ? content
        : { stats: { periods: ['x'] }, lineup: { lineups: [{ team: homeTeam }] }, shotmap: { shots: [{ x: 1 }] }, liveticker: [] };
    const general = {
        matchId: String(matchId),
        homeTeam: { name: homeTeam, ...(homeTeamId === undefined ? {} : { id: homeTeamId }) },
        awayTeam: { name: awayTeam, ...(awayTeamId === undefined ? {} : { id: awayTeamId }) },
        matchTimeUTC: kickoffAt,
        season: '2024/2025',
    };
    const header = {
        homeTeam: { name: homeTeam, ...(homeTeamId === undefined ? {} : { id: homeTeamId }) },
        awayTeam: { name: awayTeam, ...(awayTeamId === undefined ? {} : { id: awayTeamId }) },
        status: { utcTime: kickoffAt },
    };
    const pageProps = { content: safeContent, general, header, ssr: true, ...(pagePropsExtra || {}) };
    const nextData = { props: { pageProps } };
    const json = JSON.stringify(nextData);
    // Padding so the body is within the reasonable size window.
    return `<!doctype html><html><head></head><body><script id="__NEXT_DATA__" type="application/json">${json}</script><div class="app">${'x'.repeat(200)}</div></body></html>`;
}

function makeShellPage({ ssr = false, onlyTranslations = false }) {
    const pageProps = onlyTranslations
        ? { ssr: true, translations: { en: {} }, fallback: {} }
        : { ssr, translations: { en: {} }, fallback: {} };
    const nextData = { props: { pageProps } };
    return `<!doctype html><html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script>${'y'.repeat(200)}</body></html>`;
}

function mockFetchImpl(responseBuilder, calls = []) {
    return async (url, opts) => {
        calls.push({ url, opts });
        const r = responseBuilder(url, calls.length);
        return {
            status: r.status,
            url,
            headers: { get: (n) => (n === 'content-type' ? (r.contentType || 'text/html; charset=utf-8') : (n === 'location' ? (r.location || null) : null)) },
            text: async () => r.body,
            arrayBuffer: async () => Buffer.from(r.body, 'utf8'),
        };
    };
}

function okResponse(body, contentType = 'text/html; charset=utf-8') {
    return { status: 200, body, contentType };
}

function makeCaptureOptions({ dir, plan, planPath, runId, maxRequests, outputRoot, env, fetchImpl, sleepImpl, execSync, fsImpl, timeoutMs, extra }) {
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

const TWO_CANDIDATES = [
    makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' }),
    makeCandidate({ id: 4506264, season: '2024/2025', home: 'Ipswich Town', away: 'Liverpool', kickoff: '2024-08-17T11:30:00Z' }),
];

// ─────────────────────────────────────────────────────────────
// C. Network contract
// ─────────────────────────────────────────────────────────────

test('NETWORK: only https://www.fotmob.com/match/<digits> allowed', async () => {
    const adapter = createBoundedFetchAdapter({ fetchImpl: mockFetchImpl(() => okResponse('x')), maxRequests: 5, delayMs: 60000, sleepImpl: async () => {} });
    await adapter.fetchOnce('https://www.fotmob.com/match/123');
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/api/data/123'), (e) => e.code === 'SAFETY_ERROR' && /path_not_authorized/.test(e.message));
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/matches/sevilla/sevilla-h2h'), (e) => e.code === 'SAFETY_ERROR' && /path_not_authorized/.test(e.message));
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/match/'), (e) => e.code === 'SAFETY_ERROR');
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/match/123x'), (e) => e.code === 'SAFETY_ERROR');
    await assert.rejects(adapter.fetchOnce('http://www.fotmob.com/match/123'), (e) => e.code === 'SAFETY_ERROR' && /protocol/.test(e.message));
    await assert.rejects(adapter.fetchOnce('https://evil.com/match/123'), (e) => e.code === 'SAFETY_ERROR' && /host/.test(e.message));
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/match/123?x=1'), (e) => e.code === 'SAFETY_ERROR' && /query_or_fragment/.test(e.message));
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/match/123#frag'), (e) => e.code === 'SAFETY_ERROR' && /query_or_fragment/.test(e.message));
});

test('NETWORK: redirect never followed; 3xx response counts as the request', async () => {
    const calls = [];
    const adapter = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl((url) => ({ status: 302, body: '', location: 'https://www.fotmob.com/other' }), calls),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
    });
    const res = await adapter.fetchOnce('https://www.fotmob.com/match/123');
    assert.equal(res.status, 302);
    assert.equal(res.redirected, true);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].opts.redirect, 'manual');
    assert.equal(adapter.requestCount(), 1);
});

test('NETWORK: cross-origin redirect is an access-control stop', () => {
    const res = { status: 302, location: 'https://evil.example.com/cb' };
    assert.equal(evaluateAccessControl(res, ''), 'cross_origin_redirect:evil.example.com');
});

test('NETWORK: serial only, exact request counting, budget before fetch', async () => {
    const calls = [];
    const adapter = createBoundedFetchAdapter({
        fetchImpl: mockFetchImpl(() => okResponse('body'), calls),
        maxRequests: 2,
        delayMs: 60000,
        sleepImpl: async () => {},
        onBeforeFetch: (url, count) => calls.push({ url, count }),
    });
    await adapter.fetchOnce('https://www.fotmob.com/match/1');
    await adapter.fetchOnce('https://www.fotmob.com/match/2');
    assert.equal(adapter.requestCount(), 2);
    assert.equal(calls.length, 4); // 2 onBeforeFetch + 2 fetchImpl
    assert.deepEqual(calls.filter(c => c.count).map(c => c.count), [1, 2]);
    // Budget exhausted BEFORE next fetch — the fetch implementation must
    // not be called again.
    await assert.rejects(adapter.fetchOnce('https://www.fotmob.com/match/3'), (e) => e.code === 'SAFETY_ERROR' && /budget_exhausted/.test(e.message));
    assert.equal(calls.length, 4);
});

test('NETWORK: delayMs < 60000 rejected', () => {
    assert.throws(
        () => createBoundedFetchAdapter({ fetchImpl: async () => ({}), maxRequests: 1, delayMs: 1000 }),
        (e) => e.code === 'INPUT_ERROR' && /60000/.test(e.message)
    );
});

test('NETWORK: timeout aborts the request and stops the run', async () => {
    const dir = tmpDir('fotmob-net-timeout-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const neverResolves = (url, opts) => new Promise((resolve, reject) => {
            opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, maxRequests: 1, fetchImpl: neverResolves, timeoutMs: 50,
        }));
        assert.equal(result.completedCount, 0);
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error|timeout|abort/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: 403 stops the run immediately; next candidate not fetched', async () => {
    const dir = tmpDir('fotmob-net-403-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => ({ status: 403, body: 'forbidden' }), calls);
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 2, fetchImpl: fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.equal(result.stopReason, 'access_control:http_403');
        assert.equal(result.completedCount, 0);
        assert.equal(result.stoppedAtOrdinal, 1);
        assert.equal(calls.length, 1);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: locationless 3xx stops the run exactly like a located redirect — access_control:redirect_302, single request, body never read', async () => {
    const dir = tmpDir('fotmob-net-redirect-noloc-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => ({ status: 302, body: 'mock-redirect-body-not-read' }), calls);
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 2, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.equal(result.stopReason, 'access_control:redirect_302');
        assert.equal(result.completedCount, 0);
        assert.equal(result.stoppedAtOrdinal, 1);
        assert.equal(calls.length, 1, 'one and only one fetch — the redirect is never followed');
        assert.equal(calls[0].opts.redirect, 'manual');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: 429 stops the run immediately', async () => {
    const dir = tmpDir('fotmob-net-429-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => ({ status: 429, body: 'rate limited' }));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.stopReason, 'access_control:http_429');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: captcha marker stops the run', async () => {
    const dir = tmpDir('fotmob-net-captcha-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse('<html>captcha challenge page</html>'));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /access_control:block_marker/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: challenge marker stops the run', async () => {
    const dir = tmpDir('fotmob-net-challenge-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse('<html>cf-challenge cloudflare</html>'));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /access_control:block_marker/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: retry=0 — a failing response is fetched exactly once', async () => {
    const dir = tmpDir('fotmob-net-retry-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => ({ status: 500, body: 'oops' }), calls);
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 3, fetchImpl }));
        assert.equal(calls.length, 1);
        assert.equal(result.status, 'stopped');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('NETWORK: budget exhausted before next fetch stops the run at the right ordinal', async () => {
    const dir = tmpDir('fotmob-net-budget-');
    try {
        const three = [TWO_CANDIDATES[0], TWO_CANDIDATES[1],
            makeCandidate({ id: 4506265, season: '2024/2025', home: 'Arsenal', away: 'Wolves', kickoff: '2024-08-17T14:00:00Z' })];
        const { plan, planPath } = makePlanFixture(dir, three, { seasons: ['2024/2025'] });
        const calls = [];
        // Serve the page matching each requested candidate so ordinals 1-2
        // complete and only ordinal 3 hits the budget gate.
        const fetchImpl = mockFetchImpl((url) => {
            const id = url.match(/match\/(\d+)/)[1];
            if (id === '4506263') return okResponse(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' }));
            if (id === '4506264') return okResponse(makePageHtml({ matchId: 4506264, homeTeam: 'Ipswich Town', awayTeam: 'Liverpool', kickoffAt: '2024-08-17T11:30:00Z' }));
            return okResponse(makePageHtml({ matchId: 4506265, homeTeam: 'Arsenal', awayTeam: 'Wolves', kickoffAt: '2024-08-17T14:00:00Z' }));
        }, calls);
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 2, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.equal(result.stopReason, 'budget_exhausted');
        assert.equal(result.stoppedAtOrdinal, 3);
        assert.equal(result.completedCount, 2);
        assert.equal(calls.length, 2);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// B. Authorization
// ─────────────────────────────────────────────────────────────

function zeroFetchEnv(maxRequests) {
    return {
        [REQUIRED_ENV_VAR]: '1',
        [REQUIRED_ENV_BUDGET]: String(maxRequests),
        NETWORK_AUTHORIZATION: 'yes',
    };
}

test('AUTH: missing --execute → SAFETY_ERROR, zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-exec-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.execute = false;
        opts.networkAuthorization = false;
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR');
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: missing environment variable → SAFETY_ERROR, zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-env-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.env = { [REQUIRED_ENV_BUDGET]: '1' };
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: missing NETWORK_AUTHORIZATION=yes → SAFETY_ERROR, zero fetches (Node re-enforcement)', async () => {
    const dir = tmpDir('fotmob-auth-netauth-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        // Direct Node invocation with the CONFIRM vars but no
        // NETWORK_AUTHORIZATION declaration must fail closed (Reviewer A P2:
        // the gate is enforced in Node, not only in make).
        opts.env = { [REQUIRED_ENV_VAR]: '1', [REQUIRED_ENV_BUDGET]: '1' };
        await assert.rejects(
            executeCaptureRun(opts),
            (e) => e.code === 'SAFETY_ERROR' && /NETWORK_AUTHORIZATION=yes/.test(e.message)
        );
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: missing authorization id → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-id-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.authorizationId = '';
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR');
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: plan hash mismatch → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-planhash-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.expectedPlanSha256 = 'f'.repeat(64);
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /plan SHA-256/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: request budget env mismatch → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-budget-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.env = zeroFetchEnv(99);
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /CONFIRM_MAX_FOTMOB_REQUESTS/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: dirty worktree → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-dirty-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.execSync = () => ' M src/x.js\n';
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /dirty/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: invalid git revision → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-sha-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        // Clean worktree (''), but a non-hex revision from rev-parse.
        opts.execSync = (cmd) => (String(cmd).includes('rev-parse') ? 'abc\n' : '');
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /40-hex/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: output root inside repository → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-repoout-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.outputRoot = REPO_ROOT;
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /outside the repository/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: symlink output root → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-symout-');
    try {
        const realOut = path.join(dir, 'real-out');
        fs.mkdirSync(realOut);
        const linkOut = path.join(dir, 'link-out');
        fs.symlinkSync(realOut, linkOut, 'dir');
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.outputRoot = linkOut;
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /symlink/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: run id escaping the output root → zero fetches', async () => {
    const dir = tmpDir('fotmob-auth-runid-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        const opts = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts.runId = '..';
        await assert.rejects(executeCaptureRun(opts), (e) => e.code === 'SAFETY_ERROR' && /run id/.test(e.message));
        assert.equal(calls.length, 0);
        const opts2 = makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl });
        opts2.runId = '/tmp/escape';
        await assert.rejects(executeCaptureRun(opts2), (e) => e.code === 'SAFETY_ERROR' && /run id/.test(e.message));
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('AUTH: all gates satisfied → capture proceeds', async () => {
    const dir = tmpDir('fotmob-auth-ok-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({
            matchId: 4506263,
            homeTeam: 'Manchester United',
            awayTeam: 'Fulham',
            kickoffAt: '2024-08-16T19:00:00Z',
            homeTeamId: 1001,
            awayTeamId: 1002,
        });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        assert.equal(result.networkRequestsMade, 1);
        const runDir = result.runDir;
        assert.ok(fs.existsSync(path.join(runDir, 'captures', '1-4506263.payload.json')));
        assert.ok(fs.existsSync(path.join(runDir, 'captures', '1-4506263.manifest.json')));
        // P1-1: the full HTML body is never persisted — no .html file, no
        // __NEXT_DATA__ / pageProps / raw_data inside the outputs.
        assert.equal(fs.readdirSync(path.join(runDir, 'captures')).some(f => f.endsWith('.html')), false);
        assert.ok(fs.existsSync(path.join(runDir, 'plan.json')), 'run plan snapshot must exist');
        const payload = JSON.parse(fs.readFileSync(path.join(runDir, 'captures', '1-4506263.payload.json'), 'utf8'));
        assert.equal(payload.observed_identity.observed_home_team_id, 1001);
        assert.equal(payload.observed_identity.observed_home_team_id_source, 'general.homeTeam.id');
        assert.equal(payload.observed_identity.observed_away_team_id, 1002);
        assert.equal(payload.observed_identity.observed_away_team_id_source, 'general.awayTeam.id');
        const serialized = JSON.stringify(payload);
        for (const marker of ['__NEXT_DATA__', 'pageProps', 'raw_data', '<!doctype']) {
            assert.ok(!serialized.includes(marker), `payload must not contain ${marker}`);
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// D. Content validity
// ─────────────────────────────────────────────────────────────

test('CONTENT: complete retained fixture succeeds with full manifest', async () => {
    const dir = tmpDir('fotmob-content-ok-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'complete');
        const manifestPath = path.join(result.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        assert.equal(manifest.schema_version, 'fotmob-match-detail-capture-manifest/v1');
        assert.equal(manifest.source_kind, 'match_detail_page');
        assert.equal(manifest.request_method, 'GET');
        assert.equal(manifest.observed_match_id, '4506263');
        assert.equal(manifest.observed_match_id_match, true);
        // R3-P1: the observed id comes from the raw hydration allowlist
        // (raw pageProps.general.matchId), NEVER from the transformer-
        // injected payload.matchId.
        assert.equal(manifest.observed_match_id_source, 'general.matchId');
        assert.equal(manifest.observed_match_id_is_response_derived, true);
        assert.equal(manifest.observed_match_id_conflict, false);
        assert.equal(manifest.league_id, 47);
        assert.equal(manifest.looks_like_valid_match_detail, true);
        assert.equal(manifest.has_stats, true);
        assert.equal(manifest.has_lineup, true);
        assert.equal(manifest.has_shotmap, true);
        assert.match(manifest.response_body_sha256, /^[0-9a-f]{64}$/);
        assert.match(manifest.stable_raw_payload_sha256, /^[0-9a-f]{64}$/);
        assert.match(manifest.stable_payload_sha256, /^[0-9a-f]{64}$/);
        assert.match(manifest.payload_file_sha256, /^[0-9a-f]{64}$/);
        assert.equal(manifest.payload_file_relative_path, '1-4506263.payload.json');
        // P2-1: manifest self-hash is present and recomputes exactly.
        assert.match(manifest.capture_manifest_sha256, /^[0-9a-f]{64}$/);
        assert.equal(manifest.capture_manifest_sha256, computeCaptureManifestSelfHash(manifest));
        assert.equal(manifest.authorization_id, 'test-authorization-id');
        assert.equal(manifest.collector_code_revision, TEST_REVISION);
        assert.equal(manifest.network_authorization_mode, 'explicit_network_authorization');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: response body hash covers the in-memory HTML; payload file hash covers the retained file', async () => {
    const dir = tmpDir('fotmob-content-hash-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        // P1-1: the full HTML body exists only in memory — its hash is bound
        // by the manifest, but the HTML itself is never written to disk.
        const manifest = JSON.parse(fs.readFileSync(path.join(result.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        assert.equal(manifest.response_body_sha256, sha256Text(page));
        assert.equal(manifest.response_body_byte_size, Buffer.byteLength(page));
        assert.equal(fs.readdirSync(path.join(result.runDir, 'captures')).some(f => f.endsWith('.html')), false);
        // The retained payload file hash binds the actual persisted bytes.
        const payloadPath = path.join(result.runDir, 'captures', '1-4506263.payload.json');
        const payloadBytes = fs.readFileSync(payloadPath);
        assert.equal(manifest.payload_file_sha256, sha256Text(payloadBytes.toString('utf8')));
        assert.equal(manifest.payload_file_sha256, crypto.createHash('sha256').update(payloadBytes).digest('hex'));
        // Payload stable hash equals the manifest binding (same document).
        const payload = JSON.parse(payloadBytes.toString('utf8'));
        assert.equal(payload.stable_payload_sha256, manifest.stable_payload_sha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: ssr=false empty shell rejected with EMPTY_SSR_SHELL', async () => {
    const dir = tmpDir('fotmob-content-shell-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(makeShellPage({ ssr: false })));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.equal(result.stopReason, 'content_validity:EMPTY_SSR_SHELL:ordinal_1');
        assert.equal(result.completedCount, 0);
        assert.ok(!fs.existsSync(path.join(result.runDir, 'captures', '1-4506263.payload.json')));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: translations/fallback-only shell rejected', async () => {
    const dir = tmpDir('fotmob-content-translations-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(makeShellPage({ onlyTranslations: true })));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /EMPTY_SSR_SHELL/);
        assert.equal(result.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: no __NEXT_DATA__ rejected', async () => {
    const dir = tmpDir('fotmob-content-nonext-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse('<html><body>no next data here</body></html>'));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /content_validity:/);
        assert.equal(result.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: malformed JSON rejected', async () => {
    const dir = tmpDir('fotmob-content-maljson-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse('<script id="__NEXT_DATA__" type="application/json">{broken json</script>'));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /content_validity:/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: inner matchId mismatch rejected', async () => {
    const dir = tmpDir('fotmob-content-mismatch-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({ matchId: 9999999, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /content_validity:/);
        assert.equal(result.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: route identity date conflict rejected', async () => {
    const dir = tmpDir('fotmob-content-dateconflict-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // Observed date far away from the expected kickoff → deterministic
        // date incompatibility.
        const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2026-01-01T12:00:00Z' });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /content_validity:/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: valid stats/lineup/shotmap flags recorded in manifest', async () => {
    const dir = tmpDir('fotmob-content-flags-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        const manifest = JSON.parse(fs.readFileSync(path.join(result.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        assert.equal(manifest.has_stats, true);
        assert.equal(manifest.has_lineup, true);
        assert.equal(manifest.has_shotmap, true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CONTENT: no stats but otherwise valid — contract accepts, has_stats=false', async () => {
    const dir = tmpDir('fotmob-content-nostats-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({
            matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z',
            content: { lineup: { lineups: [] }, shotmap: { shots: [] }, liveticker: [] },
        });
        const fetchImpl = mockFetchImpl(() => okResponse(page));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'complete');
        const manifest = JSON.parse(fs.readFileSync(path.join(result.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        assert.equal(manifest.has_stats, false);
        assert.equal(manifest.looks_like_valid_match_detail, true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// F. Resume
// ─────────────────────────────────────────────────────────────

test('RESUME: completed candidates are never fetched again', async () => {
    const dir = tmpDir('fotmob-resume-completed-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl((url) => {
            const id = url.match(/match\/(\d+)/)[1];
            if (id === '4506263') return okResponse(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' }));
            return okResponse(makePageHtml({ matchId: 4506264, homeTeam: 'Ipswich Town', awayTeam: 'Liverpool', kickoffAt: '2024-08-17T11:30:00Z' }));
        }, calls);
        const runId = 'run-resume';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 2, fetchImpl });
        const first = await executeCaptureRun(opts);
        assert.equal(first.status, 'complete');
        assert.equal(first.completedCount, 2);
        assert.equal(calls.length, 2);

        // Second run over the same plan + run id: zero fetches.
        const second = await executeCaptureRun(opts);
        assert.equal(second.status, 'complete');
        assert.equal(second.completedCount, 2);
        assert.equal(second.networkRequestsMade, 0);
        assert.equal(calls.length, 2);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RESUME: completed pair hash mismatch stops without fetching', async () => {
    const dir = tmpDir('fotmob-resume-mismatch-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' })), calls);
        const runId = 'run-mismatch';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 1, fetchImpl });
        await executeCaptureRun(opts);
        // Corrupt the payload file — resume must detect the mismatch.
        const payloadPath = path.join(opts.outputRoot, 'runs', runId, 'captures', '1-4506263.payload.json');
        fs.writeFileSync(payloadPath, 'CORRUPTED CONTENT');
        const callsBefore = calls.length;
        const second = await executeCaptureRun(opts);
        assert.equal(second.status, 'stopped');
        assert.match(second.stopReason, /resume_pair_mismatch/);
        assert.equal(calls.length, callsBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RESUME: run state plan SHA mismatch refuses to continue', async () => {
    const dir = tmpDir('fotmob-resume-plansha-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' })));
        const runId = 'run-plansha';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 1, fetchImpl });
        await executeCaptureRun(opts);
        // Different plan, same run id.
        const other = makePlanFixture(dir, [TWO_CANDIDATES[1]], { seasons: ['2024/2025'] });
        const opts2 = makeCaptureOptions({ dir, plan: other.plan, planPath: other.planPath, runId, maxRequests: 1, fetchImpl });
        await assert.rejects(executeCaptureRun(opts2), (e) => e.code === 'SAFETY_ERROR' && /plan SHA mismatch/.test(e.message));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RESUME: failure at Nth candidate keeps previous N-1 pairs', async () => {
    const dir = tmpDir('fotmob-resume-keep-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl((url) => {
            const id = url.match(/match\/(\d+)/)[1];
            if (id === '4506264') return { status: 403, body: 'forbidden' };
            return okResponse(makePageHtml({ matchId: id, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' }));
        });
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 2, fetchImpl }));
        assert.equal(result.status, 'stopped');
        assert.equal(result.stoppedAtOrdinal, 2);
        assert.equal(result.completedCount, 1);
        const capturesDir = path.join(result.runDir, 'captures');
        const files = fs.readdirSync(capturesDir);
        assert.deepEqual(files.sort(), ['1-4506263.manifest.json', '1-4506263.payload.json']);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RESUME: budget is cumulative across runs; a resumed run never fetches past the declared cap', async () => {
    const dir = tmpDir('fotmob-resume-budget-');
    try {
        const three = [TWO_CANDIDATES[0], TWO_CANDIDATES[1],
            makeCandidate({ id: 4506265, season: '2024/2025', home: 'Arsenal', away: 'Wolves', kickoff: '2024-08-17T14:00:00Z' })];
        const { plan, planPath } = makePlanFixture(dir, three, { seasons: ['2024/2025'] });
        const calls = [];
        // Per-candidate pages: ordinal 3 (Arsenal vs Wolves) is the only one
        // whose team markers match the generic response below.
        const fetchImpl = mockFetchImpl((url) => {
            const id = url.match(/match\/(\d+)/)[1];
            if (id === '4506263') return okResponse(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' }));
            if (id === '4506264') return okResponse(makePageHtml({ matchId: 4506264, homeTeam: 'Ipswich Town', awayTeam: 'Liverpool', kickoffAt: '2024-08-17T11:30:00Z' }));
            return okResponse(makePageHtml({ matchId: 4506265, homeTeam: 'Arsenal', awayTeam: 'Wolves', kickoffAt: '2024-08-17T14:00:00Z' }));
        }, calls);
        const runId = 'run-budget';
        // First run: budget 2 → completes 2, stops at ordinal 3.
        const first = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 2, fetchImpl }));
        assert.equal(first.status, 'stopped');
        assert.equal(first.stopReason, 'budget_exhausted');
        assert.equal(first.completedCount, 2);
        assert.equal(calls.length, 2);
        // Second run: the budget cap is CUMULATIVE (Codex re-review P1) —
        // the persisted attempted count seeds the adapter, so ordinal 3 is
        // stopped BEFORE any fetch. The run can never exceed the declared
        // max-requests total across resume cycles.
        const second = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 2, fetchImpl }));
        assert.equal(second.status, 'stopped');
        assert.equal(second.stopReason, 'budget_exhausted');
        assert.equal(second.completedCount, 2);
        assert.equal(second.networkRequestsMade, 0);
        assert.equal(calls.length, 2);
        // Changing the budget contract across runs is refused (P1-5).
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 3, fetchImpl })),
            (e) => e.code === 'SAFETY_ERROR' && /max-requests contract mismatch/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RESUME: stable hash may differ across separate runs (page drift allowed)', async () => {
    const dir = tmpDir('fotmob-resume-drift-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const pageA = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
        const pageB = makePageHtml({
            matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z',
            content: { stats: { periods: ['y'] }, lineup: { lineups: [] }, shotmap: { shots: [] } },
        });
        const fetchImplA = mockFetchImpl(() => okResponse(pageA));
        const runA = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId: 'run-drift-a', maxRequests: 1, fetchImpl: fetchImplA }));
        assert.equal(runA.status, 'complete');
        const fetchImplB = mockFetchImpl(() => okResponse(pageB));
        const runB = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId: 'run-drift-b', maxRequests: 1, fetchImpl: fetchImplB }));
        assert.equal(runB.status, 'complete');
        const manifestA = JSON.parse(fs.readFileSync(path.join(runA.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        const manifestB = JSON.parse(fs.readFileSync(path.join(runB.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        // Different page content → different stable hash across runs is
        // allowed and never treated as failure.
        assert.notEqual(manifestA.stable_raw_payload_sha256, manifestB.stable_raw_payload_sha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
