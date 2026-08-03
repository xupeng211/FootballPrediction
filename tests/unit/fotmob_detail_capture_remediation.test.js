'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
// Codex review remediation tests (PR #1816) — one test group per finding:
//   A. P1-1 no full HTML persistence
//   B. P1-2 recompute plan hash
//   C. P1-3 make data-* gates (canonical entrypoints)
//   D. P1-4 trusted observed match id
//   E. P1-5 resume binding
//   F. P2-1 manifest self-hash
//   G. P2-2 replay determinism
//   H. P2-3 ensureRealDirectoryTree (symlink rejection)
//   I. P2-4 failed requests must count
//   J. P2-5 per-candidate provider/competition/league scope
//   K. P2-6 replay must not lose candidate identity
//
// Fully offline and mocked: real network is structurally forbidden and
// every fetch implementation is an injected mock.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');

const {
    buildDeterministicCapturePlan,
    writePlanDocument,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const {
    computeBusinessContentHash,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const {
    executeCaptureRun,
    validateAuthorizationBinding,
    REQUIRED_ENV_VAR,
    REQUIRED_ENV_BUDGET,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
const {
    validateAndRecomputeCapturePlan,
    computeCaptureManifestSelfHash,
    readAndValidateCandidateArtifact,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const {
    buildRunSummary,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
const {
    fetchFotMobRawDetail,
} = require('../../src/infrastructure/services/FotMobRawDetailFetcher');
const {
    runPreflight,
    runReplay,
} = require('../../scripts/ops/fotmob_detail_capture');
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

function makeV1Artifact(candidates, snapshotOverrides = {}) {
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
            ...snapshotOverrides,
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

function makePageHtml({ matchId, homeTeam, awayTeam, kickoffAt, content, generalOverride, pagePropsExtra }) {
    const safeContent = content !== undefined
        ? content
        : { stats: { periods: ['x'] }, lineup: { lineups: [{ team: homeTeam }] }, shotmap: { shots: [{ x: 1 }] }, liveticker: [] };
    const general = {
        matchId: String(matchId),
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        matchTimeUTC: kickoffAt,
        season: '2024/2025',
        ...(generalOverride || {}),
    };
    const header = {
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        status: { utcTime: kickoffAt },
    };
    const pageProps = { content: safeContent, general, header, ssr: true, ...(pagePropsExtra || {}) };
    const nextData = { props: { pageProps } };
    const json = JSON.stringify(nextData);
    // Sentinel marker the payload must NEVER contain.
    return `<!doctype html><html><head></head><body><script id="__NEXT_DATA__" type="application/json">${json}</script><div class="app">${'x'.repeat(200)}</div></body></html>`;
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
        runId: runId || 'run-remediation',
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
        ...extra,
    };
}

const TWO_CANDIDATES = [
    makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' }),
    makeCandidate({ id: 4506264, season: '2024/2025', home: 'Ipswich Town', away: 'Liverpool', kickoff: '2024-08-17T11:30:00Z' }),
];

function pageFor(candidate) {
    return makePageHtml({
        matchId: candidate.source_match_id,
        homeTeam: candidate.home_team,
        awayTeam: candidate.away_team,
        kickoffAt: candidate.kickoff_at,
    });
}

function walkFiles(dir) {
    const out = [];
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, entry.name);
        if (entry.isDirectory()) out.push(...walkFiles(p));
        else out.push(p);
    }
    return out;
}

// ─────────────────────────────────────────────────────────────
// A. P1-1 — no full HTML persistence
// ─────────────────────────────────────────────────────────────

test('P1-1: capture run persists only allowlisted payload + manifest; no HTML/markers/sentinel anywhere', async () => {
    const dir = tmpDir('fotmob-p11-scan-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])));
        const result = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, maxRequests: 1, fetchImpl }));
        assert.equal(result.status, 'complete');

        const runFiles = walkFiles(result.runDir);
        assert.ok(runFiles.length >= 3, 'plan.json + run-state + pair files expected');
        for (const file of runFiles) {
            assert.equal(path.extname(file), '.json', `no non-JSON files retained: ${file}`);
            const content = fs.readFileSync(file, 'utf8');
            for (const marker of ['__NEXT_DATA__', 'pageProps', 'raw_data', '<!doctype', '<div class="app">']) {
                assert.ok(!content.includes(marker), `file ${file} must not contain ${marker}`);
            }
        }
        const captures = fs.readdirSync(path.join(result.runDir, 'captures')).sort();
        assert.deepEqual(captures, ['1-4506263.manifest.json', '1-4506263.payload.json']);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-1: partial pair never resumed from a guess — both-or-neither enforced', async () => {
    const dir = tmpDir('fotmob-p11-partial-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls);
        const runId = 'run-partial';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 1, fetchImpl });
        const first = await executeCaptureRun(opts);
        assert.equal(first.status, 'complete');
        // Remove the manifest only — the payload alone must never be
        // treated as completed or fetched again.
        fs.unlinkSync(path.join(opts.outputRoot, 'runs', runId, 'captures', '1-4506263.manifest.json'));
        const callsBefore = calls.length;
        const second = await executeCaptureRun(opts);
        assert.equal(second.status, 'stopped');
        assert.match(second.stopReason, /resume_pair_partial/);
        assert.equal(calls.length, callsBefore, 'no fetch for a partial pair');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// B. P1-2 — recompute plan hash
// ─────────────────────────────────────────────────────────────

test('P1-2: built plan recomputes to the same hash the capture gate expects', () => {
    const dir = tmpDir('fotmob-p12-built-');
    try {
        const { plan } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const check = validateAndRecomputeCapturePlan(plan);
        assert.equal(check.ok, true, check.errors.join('; '));
        assert.match(check.recomputed_sha256, /^[0-9a-f]{64}$/);
        assert.equal(check.recomputed_sha256, plan.plan_business_sha256);
        assert.equal(check.recomputed_sha256, validateAuthorizationBinding({
            plan,
            expectedPlanSha256: plan.plan_business_sha256,
            authorizationId: 'auth',
            maxRequests: 1,
            runId: 'run-x',
            outputRoot: path.join(dir, 'out'),
            execute: true,
            networkAuthorization: true,
            env: { [REQUIRED_ENV_VAR]: '1', [REQUIRED_ENV_BUDGET]: '1', NETWORK_AUTHORIZATION: 'yes' },
            repositoryRoot: REPO_ROOT,
            execSync: CLEAN_EXEC,
        }).expectedPlanSha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-2: tampered candidate field → validation fails → zero fetch', async () => {
    const dir = tmpDir('fotmob-p12-tamper-');
    try {
        const { plan } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const tampered = JSON.parse(JSON.stringify(plan));
        tampered.candidates[0].kickoff_at = '2025-01-01T00:00:00Z';
        const check = validateAndRecomputeCapturePlan(tampered);
        assert.equal(check.ok, false);
        assert.ok(check.errors.some(e => /candidate_identity_sha256 mismatch|does not match recomputed/.test(e)));
        assert.equal(check.recomputed_sha256, null);

        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse('x'), calls);
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan: tampered, planPath: path.join(dir, 'plan.json'),
                maxRequests: 1, fetchImpl,
            })),
            (e) => e.code === 'SAFETY_ERROR' && /plan validation failed/.test(e.message)
        );
        assert.equal(calls.length, 0, 'tampered plan must never fetch');
        assert.equal(fs.existsSync(path.join(dir, 'out')), false, 'no run dir may be created');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-2: derived expected_request_path must equal /match/<source_match_id>', () => {
    const dir = tmpDir('fotmob-p12-path-');
    try {
        const { plan } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const tampered = JSON.parse(JSON.stringify(plan));
        tampered.candidates[0].expected_request_path = '/match/999999';
        const check = validateAndRecomputeCapturePlan(tampered);
        assert.equal(check.ok, false);
        assert.ok(check.errors.some(e => /expected_request_path must be derived/.test(e)));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-2: ordinal non-contiguous / duplicate ids / count mismatch / revision / scope tampering all rejected', () => {
    const dir = tmpDir('fotmob-p12-shape-');
    try {
        const { plan } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });

        // Non-contiguous ordinal.
        const gap = JSON.parse(JSON.stringify(plan));
        gap.candidates[1].ordinal = 3;
        assert.equal(validateAndRecomputeCapturePlan(gap).ok, false);

        // Duplicate source_match_id.
        const dupId = JSON.parse(JSON.stringify(plan));
        dupId.candidates[1].source_match_id = dupId.candidates[0].source_match_id;
        assert.equal(validateAndRecomputeCapturePlan(dupId).ok, false);

        // Duplicate candidate_id.
        const dupCid = JSON.parse(JSON.stringify(plan));
        dupCid.candidates[1].candidate_id = dupCid.candidates[0].candidate_id;
        assert.equal(validateAndRecomputeCapturePlan(dupCid).ok, false);

        // selected_candidate_count mismatch.
        const count = JSON.parse(JSON.stringify(plan));
        count.selected_candidate_count = 99;
        assert.equal(validateAndRecomputeCapturePlan(count).ok, false);

        // candidate_identity_sha256 tamper.
        const ident = JSON.parse(JSON.stringify(plan));
        ident.candidates[0].candidate_identity_sha256 = 'f'.repeat(64);
        assert.equal(validateAndRecomputeCapturePlan(ident).ok, false);

        // Non-hex source_artifact_sha256.
        const art = JSON.parse(JSON.stringify(plan));
        art.source_artifact_sha256 = 'xyz';
        assert.equal(validateAndRecomputeCapturePlan(art).ok, false);

        // Non-40-hex generator revision.
        const rev = JSON.parse(JSON.stringify(plan));
        rev.generator_code_revision = 'not-a-revision';
        assert.equal(validateAndRecomputeCapturePlan(rev).ok, false);

        // Provider / competition / league scope tampering.
        for (const [key, value] of [['source_provider', 'Other'], ['competition', 'La Liga'], ['league_id', '46']]) {
            const scope = JSON.parse(JSON.stringify(plan));
            scope[key] = value;
            assert.equal(validateAndRecomputeCapturePlan(scope).ok, false, `${key} tamper must fail`);
        }

        // Invalid season.
        const season = JSON.parse(JSON.stringify(plan));
        season.candidates[0].season = '2024';
        assert.equal(validateAndRecomputeCapturePlan(season).ok, false);

        // Empty identity is impossible: blank home/away rejected.
        const empty = JSON.parse(JSON.stringify(plan));
        empty.candidates[0].home_team = '';
        assert.equal(validateAndRecomputeCapturePlan(empty).ok, false);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// C. P1-3 — make data-* gates
// ─────────────────────────────────────────────────────────────

test('P1-3: Makefile defines the five canonical data-fotmob-detail-capture targets', () => {
    const makefile = fs.readFileSync(path.join(REPO_ROOT, 'Makefile'), 'utf8');
    for (const target of [
        'data-fotmob-detail-capture-help',
        'data-fotmob-detail-capture-plan',
        'data-fotmob-detail-capture-preflight',
        'data-fotmob-detail-capture-execute',
        'data-fotmob-detail-capture-replay',
    ]) {
        assert.match(makefile, new RegExp(`^${target}:`, 'm'), `Makefile must define ${target}`);
    }
});

function runMake(target, envVars) {
    const fakeBin = fs.mkdtempSync('/tmp/fotmob_make_bin_');
    const logPath = path.join(fakeBin, 'docker-calls.log');
    fs.writeFileSync(path.join(fakeBin, 'docker'),
        '#!/bin/sh\nprintf called >> "$FOTMOB_MAKE_DOCKER_LOG"\n');
    fs.chmodSync(path.join(fakeBin, 'docker'), 0o755);
    try {
        const env = { ...process.env, ...envVars, PATH: `${fakeBin}:${process.env.PATH}`, FOTMOB_MAKE_DOCKER_LOG: logPath };
        const result = spawnSync('make', [target], { cwd: REPO_ROOT, encoding: 'utf8', env });
        return { status: result.status, output: `${result.stdout}${result.stderr}`, dockerCalled: fs.existsSync(logPath) };
    } finally {
        fs.rmSync(fakeBin, { recursive: true, force: true });
    }
}

test('P1-3: execute target fails in make before Node unless every variable is explicit', () => {
    // No variables at all.
    const miss = runMake('data-fotmob-detail-capture-execute', {});
    assert.notEqual(miss.status, 0);
    assert.match(miss.output, /ERROR: provide PLAN, EXPECTED_PLAN_SHA256/);
    assert.equal(miss.dockerCalled, false);

    // All variables but NETWORK_AUTHORIZATION=no.
    const vars = {
        PLAN: '/tmp/plan.json',
        EXPECTED_PLAN_SHA256: 'a'.repeat(64),
        AUTHORIZATION_ID: 'auth-1',
        MAX_REQUESTS: '3',
        DELAY_MS: '60000',
        OUTPUT_ROOT: '/tmp/out',
        RUN_ID: 'run-1',
        CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE: '1',
        CONFIRM_MAX_FOTMOB_REQUESTS: '3',
        NETWORK_AUTHORIZATION: 'no',
    };
    const noAuth = runMake('data-fotmob-detail-capture-execute', vars);
    assert.notEqual(noAuth.status, 0);
    assert.match(noAuth.output, /requires NETWORK_AUTHORIZATION=yes before Node execution/);
    assert.equal(noAuth.dockerCalled, false);

    // Missing CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE.
    const noConfirm = runMake('data-fotmob-detail-capture-execute', { ...vars, NETWORK_AUTHORIZATION: 'yes', CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE: '' });
    assert.notEqual(noConfirm.status, 0);
    assert.match(noConfirm.output, /requires CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1/);
    assert.equal(noConfirm.dockerCalled, false);

    // CONFIRM_MAX_FOTMOB_REQUESTS != MAX_REQUESTS.
    const badBudget = runMake('data-fotmob-detail-capture-execute', { ...vars, NETWORK_AUTHORIZATION: 'yes', CONFIRM_MAX_FOTMOB_REQUESTS: '99' });
    assert.notEqual(badBudget.status, 0);
    assert.match(badBudget.output, /CONFIRM_MAX_FOTMOB_REQUESTS must equal MAX_REQUESTS/);
    assert.equal(badBudget.dockerCalled, false);

    // DELAY_MS below the 60000 lower bound is blocked in make (Reviewer A P2).
    const lowDelay = runMake('data-fotmob-detail-capture-execute', { ...vars, NETWORK_AUTHORIZATION: 'yes', DELAY_MS: '1' });
    assert.notEqual(lowDelay.status, 0);
    assert.match(lowDelay.output, /DELAY_MS must be an integer >= 60000/);
    assert.equal(lowDelay.dockerCalled, false);

    // Fully satisfied → reaches the Node invocation inside the container.
    const ok = runMake('data-fotmob-detail-capture-execute', {
        ...vars, NETWORK_AUTHORIZATION: 'yes', DELAY_MS: '60000',
    });
    assert.equal(ok.status, 0);
    assert.equal(ok.dockerCalled, true);
});

test('P1-3: execute dry-run passes every variable with no dangerous defaults', () => {
    const result = spawnSync('make', ['-n', 'data-fotmob-detail-capture-execute',
        'PLAN=/tmp/plan.json',
        'EXPECTED_PLAN_SHA256=' + 'a'.repeat(64),
        'AUTHORIZATION_ID=auth-1',
        'MAX_REQUESTS=3',
        'DELAY_MS=60000',
        'OUTPUT_ROOT=/tmp/out',
        'RUN_ID=run-1',
        'CONFIRM_REAL_FOTMOB_DETAIL_CAPTURE=1',
        'CONFIRM_MAX_FOTMOB_REQUESTS=3',
        'NETWORK_AUTHORIZATION=yes',
    ], { cwd: REPO_ROOT, encoding: 'utf8' });
    assert.equal(result.status, 0);
    const output = `${result.stdout}${result.stderr}`;
    assert.match(output, /cd \/app;/);
    assert.match(output, /node scripts\/ops\/fotmob_detail_capture\.js capture/);
    assert.match(output, /--execute/);
    assert.match(output, /--expected-plan-sha256/);
    assert.match(output, /--authorization-id/);
    assert.match(output, /--max-requests/);
    assert.match(output, /--delay-ms/);
    assert.match(output, /--output-root/);
    assert.match(output, /--run-id/);
});

test('P1-3: preflight subcommand is fully offline — validates, prints, creates nothing', async () => {
    const dir = tmpDir('fotmob-p13-preflight-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const fetchCalls = [];
        const stdout = { write: () => {} };
        const result = runPreflight({
            plan: planPath,
            'expected-plan-sha256': plan.plan_business_sha256,
            'authorization-id': 'auth-preflight',
            'max-requests': 2,
            'output-root': path.join(dir, 'out'),
            'run-id': 'run-preflight',
        }, {
            stdout,
            fetchImpl: async () => { fetchCalls.push(1); return okResponse('x'); },
            repositoryRoot: REPO_ROOT,
            execSync: CLEAN_EXEC,
        });
        assert.equal(result.mode, 'preflight');
        assert.equal(result.plan_sha256, plan.plan_business_sha256);
        assert.equal(result.selected_candidate_count, 2);
        assert.deepEqual(result.request_urls, ['/match/4506263', '/match/4506264']);
        assert.equal(result.execution_ready, true);
        // Zero side effects: no run dir, no state, no fetch.
        assert.equal(fs.existsSync(path.join(dir, 'out')), false);
        assert.equal(fetchCalls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// D. P1-4 — trusted observed match id
// ─────────────────────────────────────────────────────────────

test('P1-4: fetcher match_id_source comes only from pre-transform raw hydration fields', async () => {
    const baseTransform = NextDataParser.transformToApiFormat;
    const html = pageFor(TWO_CANDIDATES[0]);
    const mockResponse = () => ({
        status: 200,
        url: 'https://www.fotmob.com/match/4506263',
        headers: { get: () => 'text/html' },
        text: async () => html,
        arrayBuffer: async () => Buffer.from(html),
    });
    const fetcherDeps = (transformFn) => ({
        fetchFn: mockResponse,
        parser: { extractFromHtml: NextDataParser.extractFromHtml, transformToApiFormat: transformFn },
        now: () => FIXED_CLOCK,
    });
    const input = { externalId: '4506263', matchId: 'm1', homeTeam: 'Manchester United', awayTeam: 'Fulham', matchDate: '2024-08-16T19:00:00Z' };

    // R3-P1: the transformer INJECTS payload.matchId from the request-side
    // externalId — it must NEVER be the observed source. The trusted value
    // comes from the raw hydration allowlist (raw pageProps.general.matchId
    // → 'general.matchId'), extracted pre-transform.
    const viaPayload = await fetchFotMobRawDetail(input, fetcherDeps(baseTransform));
    assert.equal(viaPayload.ok, true, viaPayload.controlled_error || '');
    assert.equal(viaPayload.match_id_source, 'general.matchId');
    assert.equal(viaPayload.observed_match_id_response_derived, true);
    assert.equal(viaPayload.observed_match_id_conflict, false);

    // A transformer that REMOVES the synthetic payload.matchId changes
    // nothing — the trusted id is already response-derived.
    const noPayloadId = (nextData) => {
        const api = baseTransform(nextData, '4506263');
        delete api.matchId;
        return api;
    };
    const generalOnly = await fetchFotMobRawDetail(input, fetcherDeps(noPayloadId));
    assert.equal(generalOnly.ok, true, generalOnly.controlled_error || '');
    assert.equal(generalOnly.match_id_source, 'general.matchId');

    // R3-P1: mutating the TRANSFORMED payload's general.matchId is ignored —
    // the trusted identity was already extracted from the raw hydration
    // before the transformer ran (no conflict, source unchanged).
    const transformedMutation = (nextData) => {
        const api = baseTransform(nextData, '4506263');
        api.general.matchId = '999';
        return api;
    };
    const mutated = await fetchFotMobRawDetail(input, fetcherDeps(transformedMutation));
    assert.equal(mutated.ok, true, mutated.controlled_error || '');
    assert.equal(mutated.match_id_source, 'general.matchId');
    assert.equal(mutated.observed_match_id_conflict, false);

    // Conflict is detected in the RAW hydration: pageProps.general.matchId
    // vs raw top-level pageProps.matchId disagreeing → flagged.
    const conflictHtml = makePageHtml({
        matchId: 4506263,
        homeTeam: 'Manchester United',
        awayTeam: 'Fulham',
        kickoffAt: '2024-08-16T19:00:00Z',
        pagePropsExtra: { matchId: '999' },
    });
    const conflictingResponse = () => ({
        status: 200,
        url: 'https://www.fotmob.com/match/4506263',
        headers: { get: () => 'text/html' },
        text: async () => conflictHtml,
        arrayBuffer: async () => Buffer.from(conflictHtml),
    });
    const conflicting = await fetchFotMobRawDetail(input, {
        fetchFn: conflictingResponse,
        parser: { extractFromHtml: NextDataParser.extractFromHtml, transformToApiFormat: baseTransform },
        now: () => FIXED_CLOCK,
    });
    assert.equal(conflicting.ok, true, conflicting.controlled_error || '');
    assert.equal(conflicting.observed_match_id_conflict, true);
});

test('P1-4: successful capture records a trusted observed id; conflicting page fails closed', async () => {
    const dir = tmpDir('fotmob-p14-id-');
    try {
        const candidate = TWO_CANDIDATES[0];
        const { plan, planPath } = makePlanFixture(dir, [candidate], { seasons: ['2024/2025'] });

        // R3-P1: trusted observed id from the raw hydration allowlist
        // (raw pageProps.general.matchId), no conflict, matches candidate.
        const ok = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(candidate))),
        }));
        assert.equal(ok.status, 'complete');
        const manifest = JSON.parse(fs.readFileSync(path.join(ok.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        assert.equal(manifest.observed_match_id, '4506263');
        assert.equal(manifest.observed_match_id_source, 'general.matchId');
        assert.equal(manifest.observed_match_id_is_response_derived, true);
        assert.equal(manifest.observed_match_id_match, true);
        assert.equal(manifest.observed_match_id_conflict, false);

        // Conflicting inner ids → content validity fails closed.
        const conflictingPage = makePageHtml({
            matchId: 4506263,
            homeTeam: 'Manchester United',
            awayTeam: 'Fulham',
            kickoffAt: '2024-08-16T19:00:00Z',
            generalOverride: { matchId: '999' },
        });
        const stopped = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-conflict', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(conflictingPage)),
        }));
        assert.equal(stopped.status, 'stopped');
        assert.match(stopped.stopReason, /content_validity:/);
        assert.equal(stopped.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// E. P1-5 — resume binding
// ─────────────────────────────────────────────────────────────

test('P1-5: run-state missing but capture pairs exist → fail closed, zero fetch', async () => {
    const dir = tmpDir('fotmob-p15-nostate-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls);
        const runId = 'run-nostate';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 1, fetchImpl });
        await executeCaptureRun(opts);
        // Delete run-state; pairs remain — the run must refuse to guess.
        fs.unlinkSync(path.join(opts.outputRoot, 'runs', runId, 'run-state.json'));
        const callsBefore = calls.length;
        await assert.rejects(
            executeCaptureRun(opts),
            (e) => e.code === 'SAFETY_ERROR' && /refusing to guess/.test(e.message)
        );
        assert.equal(calls.length, callsBefore);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-5: run-state authorization id / collector revision tampering refuses to continue', async () => {
    const dir = tmpDir('fotmob-p15-bind-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])));
        const runId = 'run-bind';
        const opts = makeCaptureOptions({ dir, plan, planPath, runId, maxRequests: 1, fetchImpl });
        await executeCaptureRun(opts);
        const statePath = path.join(opts.outputRoot, 'runs', runId, 'run-state.json');

        const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        state.authorization_id = 'someone-else';
        fs.writeFileSync(statePath, JSON.stringify(state));
        await assert.rejects(
            executeCaptureRun(opts),
            (e) => e.code === 'SAFETY_ERROR' && /authorization id mismatch/.test(e.message)
        );

        const state2 = JSON.parse(fs.readFileSync(statePath, 'utf8'));
        state2.authorization_id = 'test-authorization-id';
        state2.collector_code_revision = 'f'.repeat(40);
        fs.writeFileSync(statePath, JSON.stringify(state2));
        await assert.rejects(
            executeCaptureRun(opts),
            (e) => e.code === 'SAFETY_ERROR' && /collector revision mismatch/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P1-5: pairs copied from another run id are a context mismatch, never completed', async () => {
    const dir = tmpDir('fotmob-p15-crossrun-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls);
        // Run A completes normally.
        const runA = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId: 'run-a', maxRequests: 1, fetchImpl }));
        assert.equal(runA.status, 'complete');

        // Run B reuses the SAME run id but a DIFFERENT authorization id —
        // run-state binding refuses before any pair check.
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-a', maxRequests: 1, fetchImpl,
                extra: { authorizationId: 'auth-b' },
            })),
            (e) => e.code === 'SAFETY_ERROR' && /authorization id mismatch/.test(e.message)
        );

        // Tamper the manifest's capture_run_id (self-hash breaks) — resume
        // must treat the pair as mismatched, never completed, zero fetch.
        const runB = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId: 'run-b', maxRequests: 1, fetchImpl }));
        assert.equal(runB.status, 'complete');
        const manifestPath = path.join(runB.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.capture_run_id = 'run-other';
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));
        const callsBefore = calls.length;
        const resume = await executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, runId: 'run-b', maxRequests: 1, fetchImpl }));
        assert.equal(resume.status, 'stopped');
        assert.match(resume.stopReason, /resume_pair_mismatch/);
        assert.equal(calls.length, callsBefore, 'mismatched pair must never be re-fetched');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// F. P2-1 — manifest self-hash
// ─────────────────────────────────────────────────────────────

test('P2-1: self-hash helper is canonical and single-sourced; missing hash never accepted', () => {
    const dir = tmpDir('fotmob-p21-selfhash-');
    try {
        // Build a manifest the same way the pipeline does, then verify the
        // validator accepts the recomputed hash and rejects tampering.
        const probe = {
            schema_version: 'fotmob-match-detail-capture-manifest/v1',
            source_provider: 'FotMob',
            source_kind: 'match_detail_page',
            candidate_id: '4506263',
            source_match_id: '4506263',
            competition: 'Premier League',
            league_id: 47,
            season: '2024/2025',
            home_team: 'Manchester United',
            away_team: 'Fulham',
            kickoff_at: '2024-08-16T19:00:00Z',
            candidate_identity_sha256: 'a'.repeat(64),
            source_plan_sha256: 'b'.repeat(64),
            source_artifact_sha256: 'c'.repeat(64),
            capture_run_id: 'run-x',
            authorization_id: 'auth-x',
            request_ordinal: 1,
            request_budget: 1,
            delay_ms: 60000,
            request_method: 'GET',
            request_url: 'https://www.fotmob.com/match/4506263',
            request_attempted_at: FIXED_CLOCK,
            response_received_at: FIXED_CLOCK,
            http_status: 200,
            content_type: 'text/html',
            response_body_byte_size: 100,
            response_body_sha256: 'd'.repeat(64),
            observed_match_id: '4506263',
            observed_match_id_source: 'general.matchId',
            observed_match_id_is_response_derived: true,
            observed_match_id_match: true,
            observed_match_id_conflict: false,
            hydration_parse_ok: true,
            transformed_api_format: true,
            looks_like_valid_match_detail: true,
            has_stats: true,
            has_lineup: true,
            has_shotmap: true,
            stable_raw_payload_sha256: 'e'.repeat(64),
            stable_payload_sha256: 'e'.repeat(64),
            payload_file_sha256: 'e'.repeat(64),
            payload_file_relative_path: '1-4506263.payload.json',
            parser_component: 'NextDataParser+FotMobRawParser',
            parser_version: 'V174.0.0',
            collector_component: 'FotMobDetailCapturePipeline',
            collector_code_revision: TEST_REVISION,
            network_authorization_mode: 'explicit_network_authorization',
        };
        const withHash = { ...probe, capture_manifest_sha256: computeCaptureManifestSelfHash(probe) };
        const { validateCaptureManifest } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        assert.equal(validateCaptureManifest(withHash).ok, true);
        assert.equal(validateCaptureManifest(probe).ok, false, 'missing self-hash must fail closed');
        const tampered = { ...withHash, http_status: 500 };
        assert.equal(validateCaptureManifest(tampered).ok, false, 'tampered field must fail closed');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// G. P2-2 — replay determinism
// ─────────────────────────────────────────────────────────────

test('P2-2: repeated CLI replays are byte-identical; parsed_at derives from the capture record', async () => {
    const dir = tmpDir('fotmob-p22-replay-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-replay', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        const replayOnce = () => runReplay({ 'run-dir': run.runDir, plan: planPath }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        const first = replayOnce();
        const artifactPath = path.join(run.runDir, 'replay', '1-4506263.detail.json');
        const bytesFirst = fs.readFileSync(artifactPath);
        const artifact = JSON.parse(bytesFirst.toString('utf8'));

        const manifest = JSON.parse(fs.readFileSync(path.join(run.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        // P2-2: parsed_at must equal the capture record time, never a wall clock.
        assert.equal(artifact.parsed_at, manifest.response_received_at);
        assert.equal(artifact.parsed_at, FIXED_CLOCK);
        assert.equal('captured_at' in artifact, false);

        // Second replay: byte-identical artifact, idempotent write.
        const second = replayOnce();
        assert.equal(second.replayed_count, 1);
        const bytesSecond = fs.readFileSync(artifactPath);
        assert.deepEqual(bytesSecond, bytesFirst);
        assert.equal(bytesFirst.length > 0, true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

async function awaitRunCapture({ dir, plan, planPath, runId, maxRequests }) {
    const { executeCaptureRun: exec } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
    return exec(makeCaptureOptions({
        dir, plan, planPath, runId, maxRequests,
        fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
    }));
}

// ─────────────────────────────────────────────────────────────
// H. P2-3 — ensureRealDirectoryTree (symlink rejection)
// ─────────────────────────────────────────────────────────────

test('P2-3: symlinked runs / run-id / captures / replay descendants all rejected before any fetch', async () => {
    const dir = tmpDir('fotmob-p23-symlink-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls);
        const outputRoot = path.join(dir, 'out');
        const target = path.join(dir, 'symtarget');
        fs.mkdirSync(target, { recursive: true });

        // runs dir as symlink.
        fs.mkdirSync(outputRoot, { recursive: true });
        fs.symlinkSync(target, path.join(outputRoot, 'runs'));
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, outputRoot, maxRequests: 1, fetchImpl })),
            (e) => e.code === 'SAFETY_ERROR' && /symlink/.test(e.message)
        );
        assert.equal(calls.length, 0);
        fs.rmSync(path.join(outputRoot, 'runs'));

        // run-id dir as symlink.
        fs.mkdirSync(path.join(outputRoot, 'runs'));
        fs.symlinkSync(target, path.join(outputRoot, 'runs', 'run-sym'));
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, outputRoot, runId: 'run-sym', maxRequests: 1, fetchImpl })),
            (e) => e.code === 'SAFETY_ERROR' && /symlink/.test(e.message)
        );
        assert.equal(calls.length, 0);
        fs.rmSync(path.join(outputRoot, 'runs', 'run-sym'));

        // captures dir as symlink.
        fs.mkdirSync(path.join(outputRoot, 'runs', 'run-sym'));
        fs.symlinkSync(target, path.join(outputRoot, 'runs', 'run-sym', 'captures'));
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, outputRoot, runId: 'run-sym', maxRequests: 1, fetchImpl })),
            (e) => e.code === 'SAFETY_ERROR' && /symlink/.test(e.message)
        );
        assert.equal(calls.length, 0);
        fs.rmSync(path.join(outputRoot, 'runs', 'run-sym', 'captures'));

        // replay dir as symlink.
        fs.symlinkSync(target, path.join(outputRoot, 'runs', 'run-sym', 'replay'));
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({ dir, plan, planPath, outputRoot, runId: 'run-sym', maxRequests: 1, fetchImpl })),
            (e) => e.code === 'SAFETY_ERROR' && /symlink/.test(e.message)
        );
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// I. P2-4 — failed requests must count
// ─────────────────────────────────────────────────────────────

test('P2-4: a throwing fetch is recorded as attempted=1, responses=0, captures=0', async () => {
    const dir = tmpDir('fotmob-p24-throw-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, maxRequests: 1,
            fetchImpl: async () => { throw new Error('network down'); },
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:network down/);
        const state = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-state.json'), 'utf8'));
        assert.equal(state.network_requests_attempted, 1, 'attempted must persist even when fetch fails');
        assert.equal(state.network_responses_received, 0);
        const summary = JSON.parse(fs.readFileSync(path.join(result.runDir, 'run-summary.json'), 'utf8'));
        assert.equal(summary.network_requests_attempted, 1);
        assert.equal(summary.network_responses_received, 0);
        assert.equal(summary.captures_completed, 0);
        assert.equal(summary.database_writes, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-4: timeout and non-200 responses are counted, never zero', async () => {
    const dir = tmpDir('fotmob-p24-count-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });

        // Timeout: attempted before abort, never recorded as zero.
        const timeout = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-timeout', maxRequests: 1, timeoutMs: 50,
            fetchImpl: (url, opts) => new Promise((resolve, reject) => {
                opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
            }),
        }));
        assert.equal(timeout.status, 'stopped');
        const timeoutState = JSON.parse(fs.readFileSync(path.join(timeout.runDir, 'run-state.json'), 'utf8'));
        assert.equal(timeoutState.network_requests_attempted, 1);
        assert.equal(timeoutState.network_responses_received, 0);

        // 403: a response WAS received → responses=1, captures=0.
        const forbidden = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-403', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => ({ status: 403, body: 'forbidden' })),
        }));
        assert.equal(forbidden.status, 'stopped');
        const forbiddenState = JSON.parse(fs.readFileSync(path.join(forbidden.runDir, 'run-state.json'), 'utf8'));
        assert.equal(forbiddenState.network_requests_attempted, 1);
        assert.equal(forbiddenState.network_responses_received, 1);
        assert.equal(forbiddenState.network_requests_made, 1);
        const summary = buildRunSummary(forbiddenState, { selected_candidate_count: 1 }, []);
        assert.equal(summary.network_requests_attempted, 1);
        assert.equal(summary.network_responses_received, 1);
        assert.equal(summary.captures_completed, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// J. P2-5 — per-candidate provider/competition/league scope
// ─────────────────────────────────────────────────────────────

test('P2-5: per-candidate scope enforced; inheritance only when the candidate omits', () => {
    const dir = tmpDir('fotmob-p25-scope-');
    try {
        const base = makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' });

        // Candidate overrides the scope to a non-FotMob provider → rejected.
        const wrongProvider = makeV1Artifact([{ ...base, source_provider: 'Other' }]);
        const p1 = path.join(dir, 'a1.json');
        fs.writeFileSync(p1, JSON.stringify(wrongProvider));
        const r1 = readAndValidateCandidateArtifact(p1);
        assert.equal(r1.ok, false);
        assert.ok(r1.errors.some(e => /source_provider/.test(e)));

        // Candidate declares a different league → rejected.
        const wrongLeague = makeV1Artifact([{ ...base, league_id: 46 }]);
        const p2 = path.join(dir, 'a2.json');
        fs.writeFileSync(p2, JSON.stringify(wrongLeague));
        const r2 = readAndValidateCandidateArtifact(p2);
        assert.equal(r2.ok, false);
        assert.ok(r2.errors.some(e => /league_id/.test(e)));

        // Candidate declares a different competition → rejected.
        const wrongCompetition = makeV1Artifact([{ ...base, competition: 'La Liga' }]);
        const p3 = path.join(dir, 'a3.json');
        fs.writeFileSync(p3, JSON.stringify(wrongCompetition));
        const r3 = readAndValidateCandidateArtifact(p3);
        assert.equal(r3.ok, false);
        assert.ok(r3.errors.some(e => /competition/.test(e)));

        // Candidate omits scope fields → deterministic inheritance from the
        // snapshot (FotMob / Premier League / 47) — accepted.
        const omits = makeV1Artifact([(delete base.competition, delete base.source_provider, { ...base })]);
        const p4 = path.join(dir, 'a4.json');
        fs.writeFileSync(p4, JSON.stringify(omits));
        const r4 = readAndValidateCandidateArtifact(p4);
        assert.equal(r4.ok, true, r4.errors ? r4.errors.join('; ') : '');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// K. P2-6 — replay must not lose candidate identity
// ─────────────────────────────────────────────────────────────

test('P2-6: plan snapshot is written before any network request', async () => {
    const dir = tmpDir('fotmob-p26-snapshot-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // First fetch throws — but the snapshot must already exist.
        let fetchCalls = 0;
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-snap', maxRequests: 1,
            fetchImpl: async () => { fetchCalls += 1; throw new Error('boom'); },
        }));
        assert.equal(result.status, 'stopped');
        assert.equal(fetchCalls, 1);
        const snapshot = JSON.parse(fs.readFileSync(path.join(result.runDir, 'plan.json'), 'utf8'));
        const check = validateAndRecomputeCapturePlan(snapshot);
        assert.equal(check.ok, true);
        assert.equal(snapshot.plan_business_sha256, plan.plan_business_sha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-6: replay without the run plan snapshot fails closed', async () => {
    const dir = tmpDir('fotmob-p26-nosnapshot-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-nosnap', maxRequests: 1 });
        fs.unlinkSync(path.join(run.runDir, 'plan.json'));
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} } }),
            (e) => e.code === 'SAFETY_ERROR' && /plan snapshot \(run-dir\/plan\.json\) not found/.test(e.message)
        );
        // No detail artifact may be produced (the empty replay/ dir from
        // capture time is fine; no .detail.json may exist).
        const replayDir = path.join(run.runDir, 'replay');
        assert.equal(
            fs.existsSync(replayDir) && fs.readdirSync(replayDir).some(f => f.endsWith('.detail.json')),
            false,
            'no replay artifact may be produced'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-6: external --plan is only an additional comparison; SHA mismatch fails', async () => {
    const dir = tmpDir('fotmob-p26-extplan-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-extplan', maxRequests: 1 });
        // A DIFFERENT plan document for the same candidate.
        const otherPlan = JSON.parse(JSON.stringify(plan));
        otherPlan.generated_at = '2099-01-01T00:00:00.000Z';
        otherPlan.plan_business_sha256 = 'f'.repeat(64);
        const otherPath = path.join(dir, 'other-plan.json');
        fs.writeFileSync(otherPath, JSON.stringify(otherPlan));
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir, plan: otherPath }, { stdout: { write: () => {} } }),
            (e) => /--plan does not match the run plan snapshot/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2-6: replay identity comes from the verified plan candidate, never empty', async () => {
    const dir = tmpDir('fotmob-p26-identity-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-ident', maxRequests: 1 });
        const result = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(result.replayed_count, 1);
        const artifact = JSON.parse(fs.readFileSync(path.join(run.runDir, 'replay', '1-4506263.detail.json'), 'utf8'));
        assert.equal(artifact.candidate_id, plan.candidates[0].candidate_id);
        assert.equal(artifact.expected_identity.home_team, plan.candidates[0].home_team);
        assert.equal(artifact.expected_identity.away_team, plan.candidates[0].away_team);
        assert.equal(artifact.expected_identity.kickoff_at, plan.candidates[0].kickoff_at);
        // Identity is never empty and never derived from file names.
        for (const v of [artifact.candidate_id, artifact.expected_identity.home_team,
            artifact.expected_identity.away_team, artifact.expected_identity.kickoff_at]) {
            assert.ok(typeof v === 'string' && v.length > 0);
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// L. Codex re-review round 2 (R2) — regression tests
//   L1. P1 resume budget is cumulative across cycles
//   L2. P2 replay binds the FULL run plan (snapshot + manifest)
//   L3. P2 replay derives a verified 40-hex parser code revision
//   L4. P2 block markers are structured-only (no football false positives)
// ─────────────────────────────────────────────────────────────

test('R2-P1: resumed run can never fetch past the declared max-requests budget', async () => {
    const dir = tmpDir('fotmob-r2p1-budget-');
    try {
        const THREE_CANDIDATES = [
            ...TWO_CANDIDATES,
            makeCandidate({ id: 4506265, season: '2024/2025', home: 'Brighton', away: 'Everton', kickoff: '2024-08-17T14:00:00Z' }),
        ];
        const { plan, planPath } = makePlanFixture(dir, THREE_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const opts = makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r2p1-budget', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).match(/(\d+)$/)?.[1];
                const cand = THREE_CANDIDATES.find(c => String(c.source_match_id) === id) || THREE_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }, calls),
        });

        // First run: budget of 2 lets ordinals 1-2 fetch; ordinal 3 is
        // stopped before any fetch is issued (budget_exhausted).
        const first = await executeCaptureRun(opts);
        assert.equal(first.status, 'stopped');
        assert.equal(first.stopReason, 'budget_exhausted');
        assert.equal(first.networkRequestsMade, 2);
        assert.equal(calls.length, 2);

        // Resume under the same run id + authorization context: the budget
        // is cumulative (initialUsed seeds the adapter with the persisted
        // attempted count) — zero further fetches may be issued.
        const resume = await executeCaptureRun(opts);
        assert.equal(resume.stopReason, 'budget_exhausted');
        assert.equal(resume.networkRequestsMade, 0, 'resume must not issue any fetch');
        assert.equal(calls.length, 2, 'no fetch may be issued after the cumulative budget is exhausted');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R2-P2: replay fails closed when the run plan snapshot or manifest comes from another plan', async () => {
    const dir = tmpDir('fotmob-r2p2-planbind-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r2p2-bind', maxRequests: 1 });
        assert.equal(run.status, 'complete');
        const originalSnapshot = fs.readFileSync(path.join(run.runDir, 'plan.json'));

        // A DIFFERENT valid plan over the same candidate (sibling set
        // changed) must not be accepted as the run snapshot: the run state
        // is bound to the snapshot by plan SHA and fails closed.
        const other = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        assert.notEqual(other.plan.plan_business_sha256, plan.plan_business_sha256);
        fs.writeFileSync(path.join(run.runDir, 'plan.json'), JSON.stringify(other.plan, null, 2) + '\n');
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} } }),
            (e) => e.code === 'SAFETY_ERROR' && /run state plan SHA does not match the run plan snapshot/.test(e.message)
        );

        // Restore the genuine snapshot; a manifest whose source_plan_sha256
        // belongs to another plan (self-hash kept consistent) still fails
        // closed at the pair level.
        fs.writeFileSync(path.join(run.runDir, 'plan.json'), originalSnapshot);
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.source_plan_sha256 = 'f'.repeat(64);
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} } }),
            (e) => e.code === 'SAFETY_ERROR' && /manifest source_plan_sha256 does not match the run plan snapshot/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R2-P3: canonical replay derives a verified 40-hex parser code revision from the plan snapshot', async () => {
    const dir = tmpDir('fotmob-r2p3-parserrev-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r2p3-rev', maxRequests: 1 });
        assert.equal(run.status, 'complete');
        assert.equal(plan.generator_code_revision, TEST_REVISION);

        // Canonical path: NO deps.parserCodeRevision (exactly like the
        // make data-fotmob-detail-capture-replay target) — the revision must
        // come from the verified run plan snapshot, never an empty string.
        const result = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} } });
        assert.equal(result.replayed_count, 1);
        const artifact = JSON.parse(fs.readFileSync(path.join(run.runDir, 'replay', '1-4506263.detail.json'), 'utf8'));
        assert.equal(artifact.parser_code_revision, TEST_REVISION);
        assert.match(artifact.parser_code_revision, /^[0-9a-f]{40}$/);

        // The artifact contract rejects empty / non-40-hex revisions.
        const { validateDetailArtifact } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        for (const bad of ['', 'abc', 'ABCABC']) {
            const check = validateDetailArtifact({ ...artifact, parser_code_revision: bad });
            assert.equal(check.ok, false, `revision ${JSON.stringify(bad)} must be rejected`);
            assert.ok(
                check.errors.some(e => /parser_code_revision must be 40 lowercase hex/.test(e)),
                `expected parser_code_revision error for ${JSON.stringify(bad)}, got: ${check.errors.join('; ')}`
            );
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R2-P4: generic challenge/blocked words in valid football pages do not stop the run', async () => {
    const dir = tmpDir('fotmob-r2p4-generic-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = makePageHtml({
            matchId: TWO_CANDIDATES[0].source_match_id,
            homeTeam: TWO_CANDIDATES[0].home_team,
            awayTeam: TWO_CANDIDATES[0].away_team,
            kickoffAt: TWO_CANDIDATES[0].kickoff_at,
            content: {
                stats: { periods: ['x'] },
                lineup: { lineups: [{ team: TWO_CANDIDATES[0].home_team }] },
                shotmap: { shots: [{ x: 1 }] },
                liveticker: [{ type: 'event', text: 'a late challenge, the shot was blocked' }],
            },
        }).replace('</body>', '<p class="x">a late challenge on the wing, the shot was blocked, cloud cover all afternoon</p></body>');
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r2p4-generic', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(page)),
        }));
        assert.equal(result.status, 'complete', 'generic football words must not be treated as WAF markers');
        assert.equal(result.stopReason, null);
        const captures = fs.readdirSync(path.join(result.runDir, 'captures')).sort();
        assert.deepEqual(captures, ['1-4506263.manifest.json', '1-4506263.payload.json']);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R2-P4: structured WAF challenge markers still stop the run before any pair is written', async () => {
    const dir = tmpDir('fotmob-r2p4-structured-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const page = pageFor(TWO_CANDIDATES[0]).replace(
            '</body>',
            '<div class="cf-challenge" data-sitekey="x">verify you are human</div></body>'
        );
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r2p4-waf', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(page)),
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /^access_control:block_marker:/);
        assert.equal(result.networkRequestsMade, 1, 'the fetch was attempted and counted');
        const capturesDir = path.join(result.runDir, 'captures');
        assert.equal(
            fs.readdirSync(capturesDir).filter(f => f.endsWith('.manifest.json')).length,
            0,
            'no pair may be persisted from a challenge page'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// L. R3 final-head review regressions (Codex round 3, 7 findings)
// ─────────────────────────────────────────────────────────────

function copyDirRecursive(src, dest) {
    fs.mkdirSync(dest, { recursive: true });
    for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
        const from = path.join(src, entry.name);
        const to = path.join(dest, entry.name);
        if (entry.isDirectory()) copyDirRecursive(from, to);
        else fs.copyFileSync(from, to);
    }
}

function readStateJson(runDir) {
    return JSON.parse(fs.readFileSync(path.join(runDir, 'run-state.json'), 'utf8'));
}

function writeStateJson(runDir, state) {
    fs.writeFileSync(path.join(runDir, 'run-state.json'), JSON.stringify(state));
}

test('R3-P1: transformer-injected payload.matchId is never trusted — a page with team data but no raw match id is rejected with zero pair writes', async () => {
    const dir = tmpDir('fotmob-r3p1-synthetic-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // Raw hydration carries team data but NO general.matchId and NO
        // top-level matchId; the NextData transformer still injects
        // payload.matchId from the request-side externalId (4506263).
        const page = makePageHtml({
            matchId: undefined,
            homeTeam: 'Manchester United',
            awayTeam: 'Fulham',
            kickoffAt: '2024-08-16T19:00:00Z',
            generalOverride: { matchId: undefined },
        });
        assert.equal(JSON.stringify(page).includes('"matchId":"undefined"'), false, 'fixture must not smuggle a raw match id');
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r3p1-synth', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(page)),
        }));
        // The only match id in the response is the transformer-synthetic
        // payload.matchId — content validity must fail closed.
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /^content_validity:/);
        assert.equal(result.completedCount, 0);
        const capturesDir = path.join(result.runDir, 'captures');
        assert.equal(
            fs.readdirSync(capturesDir).filter(f => f.endsWith('.manifest.json')).length,
            0,
            'zero pair writes from a page whose only match id is request-injected'
        );
        // Positive control: the same page WITH a real raw general.matchId
        // succeeds and records the response-derived provenance.
        const ok = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r3p1-ok', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
        }));
        assert.equal(ok.status, 'complete');
        const manifest = JSON.parse(fs.readFileSync(
            path.join(ok.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        assert.equal(manifest.observed_match_id_source, 'general.matchId');
        assert.equal(manifest.observed_match_id_is_response_derived, true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P1: extractTrustedObservedMatchIdentity allowlist — raw hydration paths only', () => {
    const { extractTrustedObservedMatchIdentity } = require('../../src/infrastructure/services/FotMobRawDetailFetcher');
    const general = extractTrustedObservedMatchIdentity({ props: { pageProps: { general: { matchId: '4506263' } } } });
    assert.deepEqual(general, {
        observed_match_id: '4506263',
        observed_match_id_source: 'general.matchId',
        response_derived: true,
        conflict: false,
    });
    const topLevel = extractTrustedObservedMatchIdentity({ props: { pageProps: { matchId: '4506263' } } });
    assert.equal(topLevel.observed_match_id_source, 'matchId');
    assert.equal(topLevel.response_derived, true);
    const conflicting = extractTrustedObservedMatchIdentity({
        props: { pageProps: { general: { matchId: '4506263' }, matchId: '999' } },
    });
    assert.equal(conflicting.observed_match_id, '4506263');
    assert.equal(conflicting.conflict, true);
    const none = extractTrustedObservedMatchIdentity({ props: { pageProps: { content: {} } } });
    assert.equal(none.observed_match_id, null);
    assert.equal(none.observed_match_id_source, 'unresolved');
    assert.equal(none.response_derived, false);
    assert.equal(none.conflict, false);
    // Direct pageProps shape (some parsers return it directly) also resolves.
    const direct = extractTrustedObservedMatchIdentity({ pageProps: { general: { matchId: '4506263' } } });
    assert.equal(direct.observed_match_id_source, 'general.matchId');
    assert.equal(direct.response_derived, true);
});

test('R3-P2-1: replay RECOMPUTES the payload business hash — tampered normalized data with refreshed file hash and manifest self-hash still fails closed', async () => {
    const dir = tmpDir('fotmob-r3p21-hash-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r3p21', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Tamper a nested business field; KEEP the old stable_payload_sha256.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.normalized.home_team = 'Tampered United';
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');

        // Refresh the payload file hash AND the manifest self-hash so every
        // file-level check passes — only the recomputed business hash can
        // catch the tampering (manifest.stable_payload_sha256 stays old).
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        // The capture run itself already wrote a summary — remove it so the
        // failed replay can be proven to have written nothing.
        fs.rmSync(path.join(run.runDir, 'run-summary.json'), { force: true });
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /business hash does not match/.test(e.message)
        );
        const replayDir = path.join(run.runDir, 'replay');
        assert.equal(
            !fs.existsSync(replayDir) || fs.readdirSync(replayDir).length === 0,
            true,
            'zero artifacts written for a tampered payload'
        );
        assert.equal(fs.existsSync(path.join(run.runDir, 'run-summary.json')), false, 'no summary written');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-2: replay is bound to the run state — pairs from another run/authorization are REPLAY_PAIR_CONTEXT_MISMATCH with zero writes', async () => {
    const dir = tmpDir('fotmob-r3p22-binding-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-a', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Identical context passes.
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1);

        // Copy A's valid pair + run state into run-b, change ONLY the
        // run-state run_id — A's pair must be rejected under B's identity.
        const runB = path.join(run.runDir, '..', 'run-b');
        copyDirRecursive(run.runDir, runB);
        const stateB = readStateJson(runB);
        stateB.run_id = 'run-b';
        writeStateJson(runB, stateB);
        fs.rmSync(path.join(runB, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(runB, 'run-summary.json'), { force: true });
        assert.throws(
            () => runReplay({ 'run-dir': runB }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAIR_CONTEXT_MISMATCH.*capture_run_id/.test(e.message)
        );
        assert.equal(fs.existsSync(path.join(runB, 'run-summary.json')), false, 'no summary for a mismatched replay');

        // Different authorization id.
        const runC = path.join(run.runDir, '..', 'run-c');
        copyDirRecursive(run.runDir, runC);
        const stateC = readStateJson(runC);
        stateC.authorization_id = 'auth-c';
        writeStateJson(runC, stateC);
        fs.rmSync(path.join(runC, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(runC, 'run-summary.json'), { force: true });
        assert.throws(
            () => runReplay({ 'run-dir': runC }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAIR_CONTEXT_MISMATCH.*authorization_id/.test(e.message)
        );

        // Both changed → still mismatch, zero artifacts.
        const runD = path.join(run.runDir, '..', 'run-d');
        copyDirRecursive(run.runDir, runD);
        const stateD = readStateJson(runD);
        stateD.run_id = 'run-d';
        stateD.authorization_id = 'auth-d';
        writeStateJson(runD, stateD);
        fs.rmSync(path.join(runD, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(runD, 'run-summary.json'), { force: true });
        assert.throws(
            () => runReplay({ 'run-dir': runD }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAIR_CONTEXT_MISMATCH/.test(e.message)
        );
        assert.equal(
            !fs.existsSync(path.join(runD, 'replay')) || fs.readdirSync(path.join(runD, 'replay')).length === 0,
            true,
            'zero artifacts for a mismatched replay'
        );
        assert.equal(fs.existsSync(path.join(runD, 'run-summary.json')), false);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-3: capture fails closed with PLAN_REVISION_HEAD_MISMATCH when the collector HEAD differs from the plan generator revision', async () => {
    const dir = tmpDir('fotmob-r3p23-head-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        assert.equal(plan.generator_code_revision, TEST_REVISION);
        const calls = [];
        const fetchImpl = mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls);
        // Fake git head: a different valid 40-hex revision (never touches
        // the real repository HEAD).
        const fakeHeadExec = (cmd) => (String(cmd).includes('rev-parse') ? `${'f'.repeat(40)}\n` : '');
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-r3p23', maxRequests: 1, fetchImpl,
                execSync: fakeHeadExec,
            })),
            (e) => e.code === 'SAFETY_ERROR' && /PLAN_REVISION_HEAD_MISMATCH/.test(e.message)
        );
        assert.equal(calls.length, 0, 'no native fetch before the revision gate');
        const runDir = path.join(dir, 'out', 'runs', 'run-r3p23');
        assert.equal(fs.existsSync(path.join(runDir, 'run-state.json')), false, 'no formal run-state write before the revision gate');
        assert.equal(fs.existsSync(path.join(runDir, 'plan.json')), false, 'no plan snapshot write before the revision gate');

        // Control: matching HEAD proceeds.
        const ok = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r3p23-ok', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
        }));
        assert.equal(ok.status, 'complete');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-4: independent accounting — a timed-out attempt then a successful resume yields attempted=2, responses=1, completed=1', async () => {
    const dir = tmpDir('fotmob-r3p24-timeout-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runId = 'run-r3p24';
        const neverResolves = (url, opts) => new Promise((resolve, reject) => {
            opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
        });
        const first = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId, maxRequests: 2, fetchImpl: neverResolves, timeoutMs: 50,
        }));
        assert.equal(first.status, 'stopped');
        assert.match(first.stopReason, /^fetch_error:/);
        let state = readStateJson(first.runDir);
        assert.equal(state.network_requests_attempted, 1, 'the timed-out attempt is recorded');
        assert.equal(state.network_responses_received, 0, 'a timed-out attempt is NOT a response');
        assert.equal(state.captures_completed, 0);

        // Resume with a working fetch: the same ordinal is retried; each
        // counter accumulates independently (never responses=priorAttempted+current).
        const second = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId, maxRequests: 2,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
        }));
        assert.equal(second.status, 'complete');
        assert.equal(second.completedCount, 1);
        state = readStateJson(second.runDir);
        assert.equal(state.network_requests_attempted, 2);
        assert.equal(state.network_responses_received, 1);
        assert.equal(state.captures_completed, 1);
        assert.deepEqual(state.completed_ordinals, [1]);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-4: a 403 is a response, never a completion', async () => {
    const dir = tmpDir('fotmob-r3p24-403-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r3p24-403', maxRequests: 2,
            fetchImpl: mockFetchImpl(() => ({ status: 403, body: '<html>forbidden</html>' })),
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /^access_control:http_403/);
        const state = readStateJson(result.runDir);
        assert.equal(state.network_requests_attempted, 1);
        assert.equal(state.network_responses_received, 1, 'a 403 is a resolved response');
        assert.equal(state.captures_completed, 0, 'a 403 is never a completion');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-4: body-read failure is an attempted non-response; multi-resume accounting stays exact', async () => {
    const dir = tmpDir('fotmob-r3p24-body-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const runId = 'run-r3p24-body';
        // Candidate 1 succeeds; candidate 2's body read throws (the response
        // resolves, the BODY does not — attempted, not a response).
        const bodyFailFetch = async (url, opts) => {
            if (String(url).includes('4506264')) {
                return {
                    status: 200,
                    url,
                    headers: { get: (n) => (n === 'content-type' ? 'text/html' : null) },
                    text: async () => { throw new Error('body read failed'); },
                    arrayBuffer: async () => { throw new Error('body read failed'); },
                };
            }
            return mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])))(url, opts);
        };
        const first = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId, maxRequests: 4, fetchImpl: bodyFailFetch,
        }));
        assert.equal(first.status, 'stopped');
        assert.match(first.stopReason, /^fetch_error:/);
        let state = readStateJson(first.runDir);
        assert.equal(state.network_requests_attempted, 2);
        assert.equal(state.network_responses_received, 1, 'the body-read failure is not a response');
        assert.equal(state.captures_completed, 1);

        // Resume: c1 skipped, c2 + c3 complete — totals stay exact across
        // multiple resumes.
        const second = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId, maxRequests: 4,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).split('/match/')[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }),
        }));
        assert.equal(second.status, 'complete');
        assert.equal(second.completedCount, 2);
        state = readStateJson(second.runDir);
        // Two-candidate plan: run 1 attempted c1+c2 (1 response, 1 capture);
        // resume retried only c2 — totals stay exact across the resume.
        assert.equal(state.network_requests_attempted, 3);
        assert.equal(state.network_responses_received, 2);
        assert.equal(state.captures_completed, 2);
        assert.deepEqual(state.completed_ordinals, [1, 2]);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-5: the inter-request delay continues across processes from the persisted last_network_request_attempted_at', async () => {
    const dir = tmpDir('fotmob-r3p25-delay-');
    try {
        // A single-candidate plan proves the fresh-run first request never
        // waits; the two-candidate plan exercises the cross-process resume.
        const dir1 = path.join(dir, 'plan1');
        const dir2 = path.join(dir, 'plan2');
        fs.mkdirSync(dir1, { recursive: true });
        fs.mkdirSync(dir2, { recursive: true });
        const { plan: plan1, planPath: planPath1 } = makePlanFixture(dir1, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { plan, planPath } = makePlanFixture(dir2, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const now = () => new Date(clockMs).toISOString();
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        // Each run anchors on candidate 1 and consumes a 403 on candidate 2,
        // leaving exactly one budget unit for the resume's retry — the
        // resume must respect max_requests equality (immutable contract) and
        // re-issue the retry with the persisted inter-request delay.
        const firstRunFetch = mockFetchImpl((url) => {
            if (String(url).includes('4506264')) return { status: 403, body: '<html>forbidden</html>' };
            return okResponse(pageFor(TWO_CANDIDATES[0]));
        });
        const workingFetch = mockFetchImpl((url) => {
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        });
        const optionsFor = (runId, fetchImpl, extra = {}) => makeCaptureOptions({
            dir, plan, planPath, runId, maxRequests: 3, fetchImpl, sleepImpl,
            extra: { now, ...extra },
        });

        // New run, first request: no wait.
        const fresh = await executeCaptureRun(makeCaptureOptions({
            dir, plan: plan1, planPath: planPath1, runId: 'run-r3p25-fresh', maxRequests: 3,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            sleepImpl,
            extra: { now },
        }));
        assert.equal(fresh.status, 'complete', 'single-candidate fresh run completes');
        assert.equal(sleeps.length, 0, 'first request of a fresh run never waits');

        // 5s after the persisted attempt, delay=60s → sleep ~55s.
        const runA = await executeCaptureRun(optionsFor('run-r3p25-a', firstRunFetch));
        assert.equal(runA.completedCount, 1);
        assert.equal(runA.status, 'stopped');
        const stateA = readStateJson(runA.runDir);
        assert.equal(stateA.network_requests_attempted, 2, 'c1 ok + c2 403 = two attempts');
        assert.equal(stateA.last_network_request_attempted_at, now());
        clockMs += 5000;
        sleeps.length = 0;
        const runB = await executeCaptureRun(optionsFor('run-r3p25-a', workingFetch));
        assert.equal(runB.status, 'complete');
        assert.equal(sleeps[0], 55000, '5s after the last attempt → sleep the remaining 55s');

        // >60s since the last attempt → no sleep at all.
        const runC = await executeCaptureRun(optionsFor('run-r3p25-b', firstRunFetch));
        assert.equal(runC.completedCount, 1);
        assert.equal(runC.status, 'stopped');
        clockMs += 61000;
        sleeps.length = 0;
        const runD = await executeCaptureRun(optionsFor('run-r3p25-b', workingFetch));
        assert.equal(runD.status, 'complete');
        assert.equal(sleeps.length, 0, 'elapsed 61s > 60s delay → no wait');

        // After a FAILED attempt the wait is still enforced on resume.
        const neverResolves = (url, opts) => new Promise((resolve, reject) => {
            opts.signal.addEventListener('abort', () => reject(new Error('aborted')));
        });
        const runE = await executeCaptureRun(optionsFor('run-r3p25-c', neverResolves, { timeoutMs: 50 }));
        assert.equal(runE.status, 'stopped');
        clockMs += 5000;
        sleeps.length = 0;
        const runF = await executeCaptureRun(optionsFor('run-r3p25-c', workingFetch));
        assert.equal(runF.status, 'complete');
        assert.equal(sleeps[0], 55000, 'a failed attempt still anchors the cross-process delay');

        // Clock going backwards → full wait (elapsed clamps to zero).
        const runG = await executeCaptureRun(optionsFor('run-r3p25-d', firstRunFetch));
        assert.equal(runG.completedCount, 1);
        assert.equal(runG.status, 'stopped');
        clockMs = Date.parse(FIXED_CLOCK) - 60000; // clock regression
        sleeps.length = 0;
        const runH = await executeCaptureRun(optionsFor('run-r3p25-d', workingFetch));
        assert.equal(runH.status, 'complete');
        assert.equal(sleeps[0], 60000, 'clock regression → the full delay is enforced');

        // Invalid persisted timestamp → fail closed at the adapter.
        const { createBoundedFetchAdapter } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        assert.throws(
            () => createBoundedFetchAdapter({
                maxRequests: 1, delayMs: 60000, initialLastRequestAt: 'not-a-timestamp',
                fetchImpl: mockFetchImpl(() => okResponse('x')),
            }),
            (e) => e.code === 'SAFETY_ERROR' && /invalid_last_request_attempted_at/.test(e.message)
        );

        // Run-state with attempts but a garbage timestamp → fail closed.
        const runI = await executeCaptureRun(optionsFor('run-r3p25-e', firstRunFetch));
        assert.equal(runI.completedCount, 1);
        assert.equal(runI.status, 'stopped');
        const stateI = readStateJson(runI.runDir);
        stateI.last_network_request_attempted_at = 'garbage';
        writeStateJson(runI.runDir, stateI);
        await assert.rejects(
            executeCaptureRun(optionsFor('run-r3p25-e', 2,
                mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))))),
            (e) => e.code === 'SAFETY_ERROR' && /last_network_request_attempted_at/.test(e.message)
        );

        // Run-state with attempts but NO timestamp → fail closed.
        const stateJ = readStateJson(runI.runDir);
        delete stateJ.last_network_request_attempted_at;
        stateJ.network_requests_attempted = 1;
        writeStateJson(runI.runDir, stateJ);
        await assert.rejects(
            executeCaptureRun(optionsFor('run-r3p25-e', 2,
                mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))))),
            (e) => e.code === 'SAFETY_ERROR' && /last_network_request_attempted_at/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3-P2-6: replay summary keeps the FULL plan scope — plan=3 completed=1 → plan_candidate_count=3, captures_completed=1; second replay idempotent', async () => {
    const dir = tmpDir('fotmob-r3p26-plan-');
    try {
        const threeCandidates = TWO_CANDIDATES.concat([
            makeCandidate({ id: 4506265, season: '2024/2025', home: 'Arsenal', away: 'Wolves', kickoff: '2024-08-17T14:00:00Z' }),
        ]);
        const { plan, planPath } = makePlanFixture(dir, threeCandidates, { seasons: ['2024/2025'] });
        assert.equal(plan.candidates.length, 3);
        // Candidate 1 succeeds; candidate 2 is a 403 → the run stops with
        // exactly one retained pair.
        const fetchImpl = mockFetchImpl((url) => {
            if (String(url).includes('4506264')) return { status: 403, body: '<html>forbidden</html>' };
            return okResponse(pageFor(TWO_CANDIDATES[0]));
        });
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r3p26', maxRequests: 2, fetchImpl,
        }));
        assert.equal(run.status, 'stopped');
        assert.equal(run.completedCount, 1);

        const first = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(first.replayed_count, 1);
        const summaryPath = path.join(run.runDir, 'run-summary.json');
        const summary = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
        assert.equal(summary.plan_candidate_count, 3, 'summary keeps the FULL plan scope');
        assert.equal(summary.captures_completed, 1);
        assert.equal(summary.completed_count, 1);

        // Second replay: idempotent, identical summary.
        const second = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(second.replayed_count, 1);
        const summary2 = JSON.parse(fs.readFileSync(summaryPath, 'utf8'));
        assert.deepEqual(summary2, summary);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R3: run-state validator enforces the contract — non-negative, monotonic, unique ordinals, timestamp invariant, no auto-fixing', () => {
    const { defaultRunState, validateRunState } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
    const plan = { plan_business_sha256: 'a'.repeat(64), source_artifact_sha256: 'b'.repeat(64) };
    const base = defaultRunState(plan, {
        runId: 'run-v', authorizationId: 'auth-v', maxRequests: 2, delayMs: 60000,
        collectorCodeRevision: TEST_REVISION, startedAt: FIXED_CLOCK,
    });
    assert.equal(validateRunState(base).ok, true, 'fresh default state is valid');

    // responses can never exceed attempts.
    const badResponses = { ...base, network_requests_attempted: 1, network_responses_received: 2 };
    assert.equal(validateRunState(badResponses).ok, false);
    // captures can never exceed responses.
    const badCaptures = { ...base, network_responses_received: 1, captures_completed: 2, completed_ordinals: [1, 2] };
    assert.equal(validateRunState(badCaptures).ok, false);
    // duplicate ordinals rejected.
    const dupOrdinals = { ...base, captures_completed: 2, completed_ordinals: [1, 1] };
    assert.equal(validateRunState(dupOrdinals).ok, false);
    // captures_completed must equal completed_ordinals length.
    const countMismatch = { ...base, captures_completed: 1, completed_ordinals: [1, 2] };
    assert.equal(validateRunState(countMismatch).ok, false);
    // negative counters rejected.
    const negative = { ...base, network_requests_attempted: -1 };
    assert.equal(validateRunState(negative).ok, false);
    // timestamp required once an attempt exists.
    const noTimestamp = { ...base, network_requests_attempted: 1, last_network_request_attempted_at: null };
    assert.equal(validateRunState(noTimestamp).ok, false);
    // garbage timestamp rejected.
    const garbageTimestamp = { ...base, network_requests_attempted: 1, last_network_request_attempted_at: 'garbage' };
    assert.equal(validateRunState(garbageTimestamp).ok, false);
    // consistent state with attempts + timestamp is valid.
    const validAttempts = {
        ...base,
        network_requests_attempted: 2,
        network_responses_received: 2,
        captures_completed: 2,
        completed_ordinals: [1, 2],
        last_network_request_attempted_at: FIXED_CLOCK,
    };
    assert.equal(validateRunState(validAttempts).ok, true);
    // no auto-fixing: the bad state object is never mutated by validation.
    assert.equal(badResponses.network_responses_received, 2);
});
