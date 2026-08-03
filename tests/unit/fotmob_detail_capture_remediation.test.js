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
    looksLikeValidRawDetail,
    buildRawDataFromStablePayload,
    buildFetchMetadata,
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
    // R22-P1 (Codex re-review on 0bc69dad9): NO mtime shim. The resume gate
    // deliberately never assumes the run-state file's mtime is the write's
    // completion moment (temp+rename keeps the temp file's mtime on real
    // filesystems), so the crash-window decision comes from the persisted
    // fetch_in_flight marker — tests use plain fs semantics throughout.
    const effExtra = { ...(extra || {}) };
    const effNow = effExtra.now || (() => FIXED_CLOCK);
    const rawFs = effExtra.fsImpl || fsImpl || fs;
    delete effExtra.fsImpl;
    const effFs = rawFs;
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
        now: effNow,
        env: env || {
            [REQUIRED_ENV_VAR]: '1',
            [REQUIRED_ENV_BUDGET]: String(maxRequests),
            NETWORK_AUTHORIZATION: 'yes',
        },
        repositoryRoot: REPO_ROOT,
        execSync: execSync || CLEAN_EXEC,
        fsImpl: effFs,
        ...effExtra,
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

test('P1 (Codex re-review on cdcb7ae18): resume counts a pair left on disk by a crashed prior process, keeping captures_completed === completed_ordinals.length', async () => {
    const dir = tmpDir('fotmob-p1-resume-count-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // Run 1: complete the pair.
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p1resume', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Simulate the crash window: the pair file exists on disk but the
        // run-state update that recorded it never happened (process exited
        // between writeCapturePair() and writeRunState()). The state is a
        // valid empty state: no ordinals, zero captures.
        const state = readStateJson(run.runDir);
        state.completed_ordinals = [];
        state.captures_completed = 0;
        state.status = 'in_progress';
        writeStateJson(run.runDir, state);

        // Resume: the pre-existing pair must be recognized AND counted, so
        // the persisted state satisfies the run-state contract. Any fetch
        // here would be a bug — the pair is already complete.
        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p1resume', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'complete', 'resume completes without any fetch');
        assert.equal(resumed.completedCount, 1);

        const stateAfter = readStateJson(run.runDir);
        assert.equal(stateAfter.captures_completed, 1, 'crashed-pair capture is counted');
        assert.deepEqual(stateAfter.completed_ordinals, [1]);
        const { validateRunState } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
        assert.equal(validateRunState(stateAfter).ok, true, 'resumed state satisfies the run-state contract');

        // A second resume stays consistent (no double counting).
        const again = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p1resume', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(again.status, 'complete');
        const stateAgain = readStateJson(run.runDir);
        assert.equal(stateAgain.captures_completed, 1);
        assert.equal(validateRunState(stateAgain).ok, true);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex re-review on cdcb7ae18): replay binds the payload observed identity to the verified manifest — a request-side/conflicting identity with recomputed hashes still fails closed', async () => {
    const dir = tmpDir('fotmob-p2-obsid-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2obs', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Sanity: a clean replay passes.
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1);
        fs.rmSync(path.join(run.runDir, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(run.runDir, 'run-summary.json'), { force: true });

        // Tamper ONLY the payload's observed identity: swap in a request-side
        // id with a conflict flag, then refresh EVERY hash replay checks
        // (payload file hash, payload business hash, manifest business hash,
        // manifest self-hash). Only the new per-field binding can catch it.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.observed_identity.observed_match_id = '9999999';
        payload.observed_identity.observed_match_id_source = 'payload.matchId';
        payload.observed_identity.observed_match_id_conflict = true;
        payload.observed_identity.observed_match_id_is_response_derived = false;
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');

        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAYLOAD_OBSERVED_IDENTITY_MISMATCH/.test(e.message)
        );
        const replayDir = path.join(run.runDir, 'replay');
        assert.equal(
            !fs.existsSync(replayDir) || fs.readdirSync(replayDir).length === 0,
            true,
            'zero artifacts written for a swapped observed identity'
        );
        assert.equal(fs.existsSync(path.join(run.runDir, 'run-summary.json')), false, 'no summary written');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex re-review on cdcb7ae18): replay validates ALL pairs before writing ANY artifact — a mismatch on a later pair leaves zero artifacts', async () => {
    const dir = tmpDir('fotmob-p2-twophase-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        // Complete BOTH candidates.
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2phase', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).split('/match/')[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }),
        }));
        assert.equal(run.status, 'complete');
        assert.equal(run.completedCount, 2);

        // Copy the run, then tamper ONLY pair 2's manifest capture_run_id
        // (refreshing its self-hash so validation stays self-consistent) —
        // pair 1 stays fully valid. The replay must fail on pair 2 in the
        // validation phase WITHOUT leaving pair 1's artifact on disk.
        const runB = path.join(run.runDir, '..', 'run-p2phase-b');
        copyDirRecursive(run.runDir, runB);
        const manifest2Path = path.join(runB, 'captures', '2-4506264.manifest.json');
        const manifest2 = JSON.parse(fs.readFileSync(manifest2Path, 'utf8'));
        manifest2.capture_run_id = 'some-other-run';
        manifest2.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest2);
        fs.writeFileSync(manifest2Path, JSON.stringify(manifest2));
        fs.rmSync(path.join(runB, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(runB, 'run-summary.json'), { force: true });

        assert.throws(
            () => runReplay({ 'run-dir': runB }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAIR_CONTEXT_MISMATCH/.test(e.message)
        );
        assert.equal(
            !fs.existsSync(path.join(runB, 'replay')) || fs.readdirSync(path.join(runB, 'replay')).length === 0,
            true,
            'zero artifacts written even though pair 1 validated fine'
        );
        assert.equal(fs.existsSync(path.join(runB, 'run-summary.json')), false, 'no summary for a failed replay');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex re-review on cdcb7ae18): the authorization gate rejects ids the run-state contract rejects (/, :, #, space)', () => {
    const dir = tmpDir('fotmob-p2-authid-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const good = makeCaptureOptions({
            dir, plan, planPath, runId: 'run-auth', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse('x')),
        });
        assert.doesNotThrow(
            () => validateAuthorizationBinding(good),
            'a contract-valid authorization id passes the gate'
        );
        for (const bad of ['auth/one', 'auth:two', 'auth#three', 'auth two', '../auth', '-leading-dash']) {
            assert.throws(
                () => validateAuthorizationBinding({ ...good, authorizationId: bad }),
                (e) => e.code === 'SAFETY_ERROR' && /authorization id must match/.test(e.message),
                `authorization id ${bad} is rejected by the gate`
            );
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex re-review on cdcb7ae18): the manifest request_attempted_at is the ACTUAL attempt instant — after the inter-request delay, matching the persisted run-state timestamp', async () => {
    const dir = tmpDir('fotmob-p2-attemptat-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const now = () => new Date(clockMs).toISOString();
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        const fetchImpl = mockFetchImpl((url) => {
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        });
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2attemptat', maxRequests: 2,
            fetchImpl, sleepImpl, extra: { now },
        }));
        assert.equal(run.status, 'complete');
        assert.equal(sleeps.length, 1, 'the second request waited the inter-request delay');

        const man1 = JSON.parse(fs.readFileSync(path.join(run.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'));
        const man2 = JSON.parse(fs.readFileSync(path.join(run.runDir, 'captures', '2-4506264.manifest.json'), 'utf8'));
        const state = readStateJson(run.runDir);
        // First request: no wait — recorded at the run clock start.
        assert.equal(man1.request_attempted_at, FIXED_CLOCK);
        // Second request: recorded AFTER the 60s wait — never the pre-wait
        // moment that would antedate the audit record by a full delay.
        const afterDelay = new Date(Date.parse(FIXED_CLOCK) + 60000).toISOString();
        assert.equal(man2.request_attempted_at, afterDelay, 'second attempt recorded after the delay');
        assert.equal(
            man2.request_attempted_at, state.last_network_request_attempted_at,
            'manifest attempt time equals the persisted run-state attempt time'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 85bc0ee43): resume treats a completed ordinal with a MISSING pair as a safety error — never a re-fetch', async () => {
    const dir = tmpDir('fotmob-p2-absent-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2absent', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Simulate pair data loss: the run state records the ordinal as
        // completed, the pair files are gone. Re-fetching would inflate
        // captures_completed without growing completed_ordinals.
        fs.rmSync(path.join(run.runDir, 'captures'), { recursive: true, force: true });
        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2absent', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'resume stops instead of re-fetching');
        assert.match(resumed.stopReason, /resume_pair_absent/);
        const stateAfter = readStateJson(run.runDir);
        const { validateRunState } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
        assert.equal(validateRunState(stateAfter).ok, true, 'the failed-closed state stays contract-valid');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 85bc0ee43): manifest stable_raw_payload_sha256 is the fetcher hash computed with the trusted observed identity — never a null-matchId rebuild', async () => {
    const dir = tmpDir('fotmob-p2-rawhash-');
    try {
        const cand = TWO_CANDIDATES[0];
        const { plan, planPath } = makePlanFixture(dir, [cand], { seasons: ['2024/2025'] });
        const page = pageFor(cand);
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2rawhash', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(page)),
        }));
        assert.equal(run.status, 'complete');

        // Re-run the fetcher against the SAME cached page to obtain its
        // authoritative stable-raw-payload hash (computed with the trusted
        // response-derived identity). The manifest must record exactly that
        // hash — not a rebuild with an empty context that nulls the matchId.
        const fetcherResult = await fetchFotMobRawDetail(
            {
                externalId: cand.source_match_id,
                matchId: `${cand.season.replace('/', '')}_${cand.source_match_id}`,
                homeTeam: cand.home_team,
                awayTeam: cand.away_team,
                matchDate: cand.kickoff_at,
                dataVersion: 'fotmob_capture_v1',
            },
            {
                fetchFn: async () => ({
                    status: 200,
                    url: `https://www.fotmob.com/match/${cand.source_match_id}`,
                    headers: { get: (name) => (String(name).toLowerCase() === 'content-type' ? 'text/html; charset=utf-8' : null) },
                    body: page,
                    bodyBytes: Buffer.from(page, 'utf8'),
                    text: async () => page,
                    contentType: 'text/html; charset=utf-8',
                    redirected: false,
                }),
                parser: {
                    extractFromHtml: NextDataParser.extractFromHtml,
                    transformToApiFormat: NextDataParser.transformToApiFormat,
                },
                now: () => FIXED_CLOCK,
            }
        );
        assert.ok(fetcherResult.stable_raw_payload_hash, 'fetcher produced a stable hash');
        const manifest = JSON.parse(fs.readFileSync(
            path.join(run.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'
        ));
        assert.equal(
            manifest.stable_raw_payload_sha256, fetcherResult.stable_raw_payload_hash,
            'manifest hash is the fetcher hash computed with the trusted observed identity'
        );
        // The old behavior (empty-context rebuild) nulled the matchId and
        // diverged — prove the stored hash is NOT that divergent value.
        const { buildStableRawPayload, sha256StableRawPayload } = require('../../src/infrastructure/services/FotMobRawDetailFetcher');
        const nullMatchIdHash = sha256StableRawPayload(buildStableRawPayload(fetcherResult.raw_data, {}, {}));
        assert.notEqual(manifest.stable_raw_payload_sha256, nullMatchIdHash, 'hash binds the observed match id');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 85bc0ee43): the attempt timestamp is taken ONCE — manifest time equals the persisted run-state time even on a clock that advances per call', async () => {
    const dir = tmpDir('fotmob-p2-singlets-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // A clock that advances 1 ms per call: three separate now() calls in
        // the pre-fetch callback would produce three different timestamps.
        let tick = 0;
        const advancingNow = () => new Date(Date.parse(FIXED_CLOCK) + (tick += 1)).toISOString();
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2singlets', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            extra: { now: advancingNow },
        }));
        assert.equal(run.status, 'complete');
        const state = readStateJson(run.runDir);
        const manifest = JSON.parse(fs.readFileSync(
            path.join(run.runDir, 'captures', '1-4506263.manifest.json'), 'utf8'
        ));
        assert.equal(
            manifest.request_attempted_at, state.last_network_request_attempted_at,
            'single timestamp: manifest and run-state record the same attempt instant'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 85bc0ee43): checkCompletedPair RECOMPUTES the payload business hash — a tampered payload with refreshed file/self hashes is never treated as completed', async () => {
    const dir = tmpDir('fotmob-p2-rehash-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2rehash', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Tamper a business field; refresh the payload file hash and the
        // manifest self-hash; KEEP the same declared stable_payload_sha256 in
        // both payload and manifest (exactly the R3-P2-1 tamper scenario, but
        // for the RESUME path). Resume must fail closed, not skip the pair.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.normalized.home_team = 'Tampered United';
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2rehash', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'tampered pair stops the resume');
        assert.match(resumed.stopReason, /RESUME_PAIR_BUSINESS_HASH_MISMATCH/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 85bc0ee43): replay rejects relative, in-repo and symlink-ancestor run dirs before any read or write', async () => {
    const dir = tmpDir('fotmob-p2-replaybound-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2bound', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Relative run dir → rejected at the boundary gate.
        assert.throws(
            () => runReplay({ 'run-dir': 'relative/run-dir' }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'INPUT_ERROR'
        );
        // In-repo absolute path → SAFETY_ERROR before any read/write.
        const inRepo = path.join(REPO_ROOT, 'some-run-dir');
        assert.throws(
            () => runReplay({ 'run-dir': inRepo }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /outside the repository/.test(e.message)
        );
        // A valid external run dir still replays.
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 670504754): checkCompletedPair binds the payload identity to the verified manifest — a swapped source/candidate/observed identity with RECOMPUTED business hash and refreshed file hashes is never treated as completed', async () => {
    const dir = tmpDir('fotmob-p2-payloadid-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2payloadid', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Tamper the payload's OWN identity (source_match_id) AND recompute
        // its declared business hash — the projection includes the identity
        // fields, so a tamperer who recomputes the hash stays internally
        // self-consistent. Refresh the payload file hash and the manifest
        // self-hash so every file-level check passes. Only the NEW identity
        // binding can catch the swap; the manifest still declares the real
        // 4506263 identity.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.source_match_id = '9999999';
        payload.observed_identity.observed_match_id = '9999999';
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        // The tamperer refreshes the manifest's declared business hash too,
        // so every self-consistent hash check passes; the manifest still
        // declares the REAL identity (4506263) while the payload now claims
        // 9999999 — only the identity binding can catch the swap.
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2payloadid', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'swapped payload identity stops the resume');
        assert.match(resumed.stopReason, /RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 670504754): replay pre-checks EVERY output target before materializing — a later target with different content leaves zero partial output', async () => {
    const dir = tmpDir('fotmob-p2-outprecheck-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2outcheck', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).match(/(\d+)$/)?.[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }, calls),
        }));
        assert.equal(run.status, 'complete');
        assert.equal(calls.length, 2);

        // First replay materializes both artifacts.
        const first = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(first.replayed_count, 2);
        const target1 = path.join(run.runDir, 'replay', '1-4506263.detail.json');
        const target2 = path.join(run.runDir, 'replay', '2-4506264.detail.json');
        const bytes1Before = fs.readFileSync(target1);
        const bytes2Before = fs.readFileSync(target2);

        // Corrupt the LATER target; the pre-check must fail BEFORE any write,
        // so the earlier artifact is untouched and the corrupt file is not
        // overwritten.
        fs.writeFileSync(target2, '{ "corrupted": true }\n');
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /target exists with different content/.test(e.message)
        );
        assert.deepStrictEqual(fs.readFileSync(target1), bytes1Before, 'earlier artifact never rewritten');
        assert.equal(fs.readFileSync(target2, 'utf8'), '{ "corrupted": true }\n', 'conflicting target untouched');
        const leftovers = fs.readdirSync(path.join(run.runDir, 'replay')).filter(f => f.includes('.tmp-'));
        assert.deepStrictEqual(leftovers, [], 'no partial tmp files remain');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 670504754): capture rejects a RELATIVE output root before any resolution — zero fetches, consistent with PLAN and REPLAY boundaries', async () => {
    const dir = tmpDir('fotmob-p2-reloadout-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchCalls = [];
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-p2relout', maxRequests: 1,
                outputRoot: 'relative/external/captures',
                fetchImpl: mockFetchImpl(() => { throw new Error('RELATIVE_ROOT_SHOULD_NOT_FETCH'); }, fetchCalls),
            })),
            (e) => e.code === 'SAFETY_ERROR' && /output root must be an absolute path/.test(e.message)
        );
        assert.equal(fetchCalls.length, 0, 'no fetch is attempted when the output root is relative');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 9568ea33e): the replay output pre-check rejects SYMLINK targets — a later symlink with byte-identical content fails closed with zero partial output', async () => {
    const dir = tmpDir('fotmob-p2-symtarget-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2symtarget', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).match(/(\d+)$/)?.[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }, calls),
        }));
        assert.equal(run.status, 'complete');

        // First replay materializes both targets as regular files.
        const first = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(first.replayed_count, 2);
        const target1 = path.join(run.runDir, 'replay', '1-4506263.detail.json');
        const target2 = path.join(run.runDir, 'replay', '2-4506264.detail.json');

        // Scenario from the finding: the EARLIER target is missing (would be
        // written), the LATER target is a symlink to byte-identical content.
        // readFileSync follows the link so the content comparison passes; the
        // pre-check must reject the non-regular target BEFORE any write —
        // otherwise writeDetailArtifact's symlink rejection would fail after
        // the earlier artifact was already written (partial output).
        fs.rmSync(target1);
        const content2 = fs.readFileSync(target2);
        fs.rmSync(target2);
        fs.writeFileSync(path.join(dir, 'target2-copy.bin'), content2);
        fs.symlinkSync(path.join(dir, 'target2-copy.bin'), target2);

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /not a regular file/.test(e.message)
        );
        assert.ok(!fs.existsSync(target1), 'earlier target was never written — zero partial output');
        assert.ok(fs.lstatSync(target2).isSymbolicLink(), 'conflicting symlink untouched');
        const leftovers = fs.readdirSync(path.join(run.runDir, 'replay')).filter(f => f.includes('.tmp-'));
        assert.deepStrictEqual(leftovers, [], 'no partial tmp files remain');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on 9568ea33e): replay binds the pair ordinal to the snapshot candidate — a copied pair replayed under the wrong ordinal fails closed with zero artifacts', async () => {
    const dir = tmpDir('fotmob-p2-ordbind-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        const calls = [];
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2ordbind', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).match(/(\d+)$/)?.[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }, calls),
        }));
        assert.equal(run.status, 'complete');
        assert.deepStrictEqual(run.completedOrdinals, [1, 2]);

        // Tamper scenario from the finding: candidate 2's pair REPLACES the
        // ordinal-1 pair (the original 1-4506263 pair is removed so the CLI
        // still sees exactly one manifest for ordinal 1), its request_ordinal
        // set to 1 and the manifest self-hash refreshed. Every existing check
        // (source id lookup, manifest.request_ordinal === file prefix,
        // self-hash) passes; only the snapshot candidate's ordinal can catch
        // the swap.
        fs.rmSync(path.join(run.runDir, 'captures', '1-4506263.payload.json'));
        fs.rmSync(path.join(run.runDir, 'captures', '1-4506263.manifest.json'));
        const srcPayload = path.join(run.runDir, 'captures', '2-4506264.payload.json');
        const srcManifest = path.join(run.runDir, 'captures', '2-4506264.manifest.json');
        const copyPayload = path.join(run.runDir, 'captures', '1-4506264.payload.json');
        const copyManifest = path.join(run.runDir, 'captures', '1-4506264.manifest.json');
        fs.copyFileSync(srcPayload, copyPayload);
        const copied = JSON.parse(fs.readFileSync(srcManifest, 'utf8'));
        copied.request_ordinal = 1;
        copied.capture_manifest_sha256 = computeCaptureManifestSelfHash(copied);
        fs.writeFileSync(copyManifest, JSON.stringify(copied));

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /ordinal mismatch/.test(e.message)
        );
        const replayDir = path.join(run.runDir, 'replay');
        const artifactFiles = fs.readdirSync(replayDir).filter(f => f.endsWith('.detail.json'));
        assert.deepStrictEqual(artifactFiles, [], 'no artifact was materialized');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on a5d63af60): the plan validator cross-checks each candidate against the declared scope — a candidate competition outside the plan or a season outside selected_seasons fails even with a recomputed plan hash', () => {
    const dir = tmpDir('fotmob-p2-scope-');
    try {
        const { plan } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { canonicalJsonHash, computeCapturePlanBusinessProjection, validateAndRecomputeCapturePlan: validate } =
            require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');

        // A self-consistent plan whose candidate declares a DIFFERENT
        // competition: the business hash is recomputed so the hash gate
        // passes — only the per-candidate scope cross-check can reject it.
        const planA = JSON.parse(JSON.stringify(plan));
        planA.candidates[0].competition = 'Championship';
        planA.plan_business_sha256 = canonicalJsonHash(computeCapturePlanBusinessProjection(planA));
        const checkA = validate(planA);
        assert.equal(checkA.ok, false, 'out-of-scope candidate competition must be rejected');
        assert.ok(checkA.errors.some((e) => /must equal the plan's declared competition/.test(e)),
            `errors: ${checkA.errors.join('; ')}`);

        // A candidate season outside the plan's declared selected_seasons.
        const planB = JSON.parse(JSON.stringify(plan));
        planB.candidates[0].season = '2023/2024';
        planB.plan_business_sha256 = canonicalJsonHash(computeCapturePlanBusinessProjection(planB));
        const checkB = validate(planB);
        assert.equal(checkB.ok, false, 'out-of-scope candidate season must be rejected');
        assert.ok(checkB.errors.some((e) => /selected_seasons/.test(e)),
            `errors: ${checkB.errors.join('; ')}`);

        // The untouched plan still validates.
        const checkOk = validate(plan);
        assert.equal(checkOk.ok, true, checkOk.errors.join('; '));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on a5d63af60): resume and replay bind the pair to the FULL execution context — budget mismatch stops resume, revision mismatch stops replay', async () => {
    const dir = tmpDir('fotmob-p2-execctx-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2execctx', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // (a) Resume: manifest records a DIFFERENT request budget — e.g. a
        // pair copied from a prior run that ran with budget 1 while this run
        // binds budget 2. checkCompletedPair must fail closed (it compares
        // against the current binding, not the declared hash).
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.request_budget = 999;
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));
        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2execctx', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'budget mismatch stops the resume');
        assert.match(resumed.stopReason, /RESUME_PAIR_CONTEXT_MISMATCH:manifest.request_budget/);

        // (b) Replay: manifest collector_code_revision differs from the run
        // state's — replay must fail closed instead of declaring parser
        // provenance of the wrong revision.
        manifest.request_budget = 1;
        manifest.collector_code_revision = 'b'.repeat(40);
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAIR_REVISION_MISMATCH/.test(e.message)
        );
        assert.deepStrictEqual(
            fs.readdirSync(path.join(run.runDir, 'replay')).filter(f => f.endsWith('.detail.json')),
            [],
            'no artifact was materialized'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on a5d63af60): the run-summary target is pre-checked before any artifact write — a conflicting or non-regular summary fails closed with zero partial output', async () => {
    const dir = tmpDir('fotmob-p2-summary-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2summary', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // First replay materializes the artifact AND the run summary.
        const first = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(first.replayed_count, 1);
        const detailPath = path.join(run.runDir, 'replay', '1-4506263.detail.json');
        const summaryPath = path.join(run.runDir, 'run-summary.json');
        const detailBytes = fs.readFileSync(detailPath);
        assert.ok(fs.existsSync(summaryPath));

        // (a) A summary with DIFFERENT content: writeRunSummary overwrites
        // unconditionally, so only the pre-check can surface the conflict —
        // and it must do so BEFORE any artifact is written.
        fs.writeFileSync(summaryPath, '{ "tampered": true }\n');
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /run summary target exists with different content/.test(e.message)
        );
        assert.deepStrictEqual(fs.readFileSync(detailPath), detailBytes, 'artifact untouched');

        // (b) A summary target that is a DIRECTORY: the pre-check rejects it
        // before any artifact write (writeRunSummary would fail AFTER all
        // artifacts were materialized).
        fs.rmSync(summaryPath);
        fs.mkdirSync(summaryPath);
        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /run summary target is not a regular file/.test(e.message)
        );
        assert.deepStrictEqual(fs.readFileSync(detailPath), detailBytes, 'artifact untouched again');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on d95b91d53): the delay contract is validated BEFORE any directory or run-state write — a sub-minimum delay leaves no poisoned run behind', async () => {
    const dir = tmpDir('fotmob-p2-delaygate-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const fetchCalls = [];
        const opts = makeCaptureOptions({
            dir, plan, planPath, runId: 'run-p2delaygate', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('DELAY_GATE_SHOULD_NOT_FETCH'); }, fetchCalls),
        });
        opts.delayMs = 1;
        await assert.rejects(
            executeCaptureRun(opts),
            (e) => e.code === 'SAFETY_ERROR' && /delay-ms must be an integer >= 60000/.test(e.message)
        );
        assert.equal(fetchCalls.length, 0, 'zero fetches');
        assert.ok(
            !fs.existsSync(path.join(dir, 'out', 'runs', 'run-p2delaygate')),
            'the run directory must not be created — no run-state.json, no plan.json, no poisoned run'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('P2 (Codex round-2 review on d95b91d53): replay rejects a symlinked captures directory before any read — the link target is never treated as this run\'s retained evidence', async () => {
    const dir = tmpDir('fotmob-p2-capsym-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-p2capsym', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // A completed run whose captures/ is replaced by a symlink to
        // another directory. existsSync / readdirSync / pair reads follow
        // the link; only the lstat check can reject it before any read or
        // artifact write.
        const captures = path.join(run.runDir, 'captures');
        const realCaptures = path.join(dir, 'real-captures');
        fs.renameSync(captures, realCaptures);
        fs.symlinkSync(realCaptures, captures, 'dir');

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /captures directory must be a real directory, not a symlink/.test(e.message)
        );
        const artifactFiles = fs.readdirSync(path.join(run.runDir, 'replay')).filter(f => f.endsWith('.detail.json'));
        assert.deepStrictEqual(artifactFiles, [], 'no artifact was materialized from the link target');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-8 (Codex re-review on 047f6afcb) — R10-P1 / R10-P2-1 / R10-P2-2
// ─────────────────────────────────────────────────────────────

test('R10-P2-2 (Codex re-review on 047f6afcb): resume binds the payload PLAN identity to the manifest — a swapped competition with recomputed business hash and refreshed file hashes is never treated as completed', async () => {
    const dir = tmpDir('fotmob-r10p22-resume-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r10p22a', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Swap the payload's PLAN identity (competition) and recompute its
        // business hash — the projection includes competition, so the
        // tamperer stays internally self-consistent. Refresh the payload
        // file hash and the manifest's declared business hash + self-hash so
        // every file-level check passes. Only the new per-field
        // plan-identity binding can catch the swap; the manifest still
        // declares the real competition.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.competition = 'Some Other League';
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r10p22a', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'swapped payload plan identity stops the resume');
        assert.match(resumed.stopReason, /RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH:payload\.competition/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P2-2 (Codex re-review on 047f6afcb): replay binds the payload PLAN identity to the manifest and plan snapshot — a swapped expected_identity with refreshed hashes fails closed with zero artifacts', async () => {
    const dir = tmpDir('fotmob-r10p22-replay-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r10p22b', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Sanity: a clean replay passes.
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1);
        fs.rmSync(path.join(run.runDir, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(run.runDir, 'run-summary.json'), { force: true });

        // Swap ONLY the payload's expected_identity.home_team and refresh
        // every hash replay checks — only the new per-field plan-identity
        // binding can catch it.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.expected_identity.home_team = 'Tottenham Hotspur';
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAYLOAD_PLAN_IDENTITY_MISMATCH/.test(e.message)
        );
        const replayDir = path.join(run.runDir, 'replay');
        assert.equal(
            !fs.existsSync(replayDir) || fs.readdirSync(replayDir).length === 0,
            true,
            'zero artifacts written for a swapped plan identity'
        );
        assert.equal(fs.existsSync(path.join(run.runDir, 'run-summary.json')), false, 'no summary written');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P1 (Codex re-review on 047f6afcb): a live holder of the run lock stops the competing run with SAFETY_ERROR before any fetch or run-state write', async () => {
    const dir = tmpDir('fotmob-r10p1-live-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r10p1live');
        // R12-P1 (Codex re-review on cf500786e): the ownership token is
        // non-reusable — `pid:<pid>:<nonce>` (a bare pid is no token).
        fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });
        fs.writeFileSync(path.join(runDir, '.capture-run.lock', 'pid'), 'pid:12345:9999', 'utf8');

        const calls = [];
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-r10p1live', maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls),
                extra: { pid: 54321, pidAlive: () => true },
            })),
            (e) => e.code === 'SAFETY_ERROR' && /another capture process \(pid 12345\) holds the run lock/.test(e.message)
        );
        assert.equal(calls.length, 0, 'no fetch may be issued while another process holds the lock');
        assert.equal(fs.existsSync(path.join(runDir, 'run-state.json')), false, 'run state is never written by the blocked process');
        assert.equal(fs.existsSync(path.join(runDir, 'plan.json')), false, 'plan snapshot is never written by the blocked process');
        assert.equal(fs.existsSync(path.join(runDir, '.capture-run.lock')), true, 'the live holder lock is never removed');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P1 (Codex re-review on 047f6afcb): a stale lock left by a dead holder is broken exactly once and the capture proceeds normally', async () => {
    const dir = tmpDir('fotmob-r10p1-stale-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r10p1stale');
        const lockDir = path.join(runDir, '.capture-run.lock');
        fs.mkdirSync(lockDir, { recursive: true });
        // R12-P1: token-format lock left by a crashed (dead) holder.
        fs.writeFileSync(path.join(lockDir, 'pid'), 'pid:999999:7777', 'utf8');

        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r10p1stale', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            extra: { pid: 54321, pidAlive: () => false },
        }));
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        assert.equal(fs.existsSync(lockDir), false, 'the lock is released after the run');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P1 (Codex re-review on 047f6afcb): the run lock is acquired and released on the normal path — no lock residue after completion', async () => {
    const dir = tmpDir('fotmob-r10p1-normal-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r10p1normal', maxRequests: 1 });
        assert.equal(run.status, 'complete');
        assert.equal(fs.existsSync(path.join(run.runDir, '.capture-run.lock')), false, 'no lock residue after completion');
        assert.deepEqual(
            fs.readdirSync(run.runDir).sort(),
            ['captures', 'plan.json', 'replay', 'run-state.json', 'run-summary.json']
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P2-1 (Codex re-review on 047f6afcb): an oversized declared Content-Length stops the run before the body is read', async () => {
    const dir = tmpDir('fotmob-r10p21-declared-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: (n) => (n === 'content-length' ? String(MAX_BODY_BYTES + 1) : null) },
            arrayBuffer: async () => { throw new Error('BODY_SHOULD_NOT_BE_READ'); },
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r10p21a', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:declared_/);
        assert.equal(result.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P2-1 (Codex re-review on 047f6afcb): an oversized streamed body is aborted mid-read once the cap is exceeded', async () => {
    const dir = tmpDir('fotmob-r10p21-stream-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        const { ReadableStream } = require('node:stream/web');
        const half = Math.floor(MAX_BODY_BYTES / 2);
        let enqueued = 0;
        const body = new ReadableStream({
            start(controller) {
                controller.enqueue(new Uint8Array(half));
                enqueued += 1;
                controller.enqueue(new Uint8Array(half + 1));
                enqueued += 1;
                controller.close();
            },
        });
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: () => null },
            body,
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r10p21b', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:stream_/);
        assert.equal(result.completedCount, 0);
        assert.equal(enqueued, 2, 'both mock chunks were enqueued; the pipeline aborted while reading them');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R10-P2-1 (Codex re-review on 047f6afcb): a body without a readable stream is size-checked after the buffer read — over the cap stops the run with no retained pair', async () => {
    const dir = tmpDir('fotmob-r10p21-fallback-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        const big = Buffer.alloc(MAX_BODY_BYTES + 1, 0x61);
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: () => null },
            arrayBuffer: async () => big,
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r10p21c', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:read_/);
        assert.equal(result.completedCount, 0);
        assert.equal(
            fs.existsSync(path.join(result.runDir, 'captures', '1-4506263.payload.json')),
            false,
            'no pair retained for an oversized body'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-9 (Codex re-review on abf6fbc65) — R11-P1 / R11-P2-1 / R11-P2-2 / R11-P2-3
// ─────────────────────────────────────────────────────────────

test('R11-P1 (Codex re-review on abf6fbc65): a pid-less lock dir (crashed holder) is taken over atomically and the capture proceeds', async () => {
    const dir = tmpDir('fotmob-r11p1-empty-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r11p1empty');
        fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });

        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r11p1empty', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            extra: { pid: 54321, pidAlive: () => false },
        }));
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        assert.equal(fs.existsSync(path.join(runDir, '.capture-run.lock')), false, 'lock released after the run');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R11-P2-1 (Codex re-review on abf6fbc65): resume binds manifest AND payload plan identity to the CURRENT plan candidate — a consistent dual-tamper (both files swapped) never counts the pair complete', async () => {
    const dir = tmpDir('fotmob-r11p21-dual-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r11p21', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Swap the SAME identity field (competition) in BOTH the payload AND
        // the manifest — the payload↔manifest checks pass because both agree.
        // Recompute the payload business hash (the projection covers
        // competition), refresh the payload file hash, the manifest's
        // declared business hash and its self-hash, and KEEP the original
        // candidate_identity_sha256 (nothing recomputes it from the manifest
        // identity fields). Only the direct binding to expectedCandidate can
        // catch the swap; the manifest still must match the CURRENT plan.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.competition = 'Some Other League';
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.competition = 'Some Other League';
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        const resumed = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r11p21', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => { throw new Error('RESUME_SHOULD_NOT_FETCH'); }),
        }));
        assert.equal(resumed.status, 'stopped', 'a consistent dual-tamper stops the resume');
        assert.match(resumed.stopReason, /RESUME_PAIR_PAYLOAD_IDENTITY_MISMATCH:manifest\.competition vs plan candidate/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R11-P2-2 (Codex re-review on abf6fbc65): replay binds league_id to the run plan — a synchronized payload+manifest league swap fails closed with zero artifacts', async () => {
    const dir = tmpDir('fotmob-r11p22-league-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r11p22', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Sanity: a clean replay passes.
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1);
        fs.rmSync(path.join(run.runDir, 'replay'), { recursive: true, force: true });
        fs.rmSync(path.join(run.runDir, 'run-summary.json'), { force: true });

        // Swap league_id in BOTH files to a wrong league and refresh every
        // hash replay checks — the payload↔manifest comparison passes; only
        // the binding to the run plan's top-level league id can catch it.
        const payloadPath = path.join(run.runDir, 'captures', '1-4506263.payload.json');
        const payload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        payload.league_id = '99';
        const { computeStableCapturePayloadSha256 } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
        fs.writeFileSync(payloadPath, JSON.stringify(payload, null, 2) + '\n');
        const manifestPath = path.join(run.runDir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        manifest.league_id = '99';
        manifest.stable_payload_sha256 = payload.stable_payload_sha256;
        manifest.payload_file_sha256 = sha256Text(fs.readFileSync(payloadPath, 'utf8'));
        manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));

        assert.throws(
            () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
            (e) => e.code === 'SAFETY_ERROR' && /REPLAY_PAYLOAD_PLAN_IDENTITY_MISMATCH: league_id does not match verified manifest \/ run plan league id/.test(e.message)
        );
        const replayDir = path.join(run.runDir, 'replay');
        assert.equal(
            !fs.existsSync(replayDir) || fs.readdirSync(replayDir).length === 0,
            true,
            'zero artifacts written for a swapped league id'
        );
        assert.equal(fs.existsSync(path.join(run.runDir, 'run-summary.json')), false, 'no summary written');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R11-P2-3 (Codex re-review on abf6fbc65): an oversized streamed body cancels the underlying reader before the run stops', async () => {
    const dir = tmpDir('fotmob-r11p23-cancel-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        // chunk = half the cap + 1: two chunks exceed the cap on the second read.
        const chunk = Math.floor(MAX_BODY_BYTES / 2) + 1;
        let cancelled = 0;
        let reads = 0;
        // A server that keeps streaming forever (chunked, never closes):
        // the pre-close test stream would mask whether cancel() is issued.
        const body = {
            getReader() {
                return {
                    async read() {
                        reads += 1;
                        return { done: false, value: new Uint8Array(chunk) };
                    },
                    async cancel() {
                        cancelled += 1;
                    },
                };
            },
        };
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: () => null },
            body,
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r11p23', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:stream_/);
        assert.equal(cancelled, 1, 'the reader is cancelled once the cap is exceeded');
        assert.equal(reads, 2, 'reading stops as soon as the cap is exceeded');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-10 (Codex re-review on cf500786e) — R12-P1 / R12-P2
// ─────────────────────────────────────────────────────────────

test('R12-P1 (Codex re-review on cf500786e): release never deletes a changed ownership token — a displaced holder leaves the new owner\'s lock intact', async () => {
    const dir = tmpDir('fotmob-r12p1-release-');
    try {
        const { acquireRunLock, releaseRunLock } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        const runDir = path.join(dir, 'run');
        fs.mkdirSync(runDir, { recursive: true });
        const runLock = acquireRunLock(runDir, { fsImpl: fs, pid: 1111, pidAlive: () => true });

        // A concurrent process takes over while we hold the lock: the lock
        // path now carries a FOREIGN token (never ours, never empty).
        const lockDir = path.join(runDir, '.capture-run.lock');
        fs.rmSync(lockDir, { recursive: true, force: true });
        fs.mkdirSync(lockDir, { recursive: true });
        fs.writeFileSync(path.join(lockDir, 'pid'), 'pid:2222:55', 'utf8');

        // Our release must rename-verify-restore: the foreign token is
        // NEVER deleted (R12-P1 — process C must not delete B\'s lock).
        releaseRunLock(runDir, runLock, fs);
        assert.equal(fs.existsSync(lockDir), true, 'a foreign token is never deleted by our release');
        assert.equal(
            fs.readFileSync(path.join(lockDir, 'pid'), 'utf8'),
            'pid:2222:55',
            'the foreign ownership token is preserved verbatim'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R12-P1 (Codex re-review on cf500786e): a holder displaced mid-run fails closed at its next run-state write — the run stops with SAFETY_ERROR, zero further fetches, zero pairs', async () => {
    const dir = tmpDir('fotmob-r12p1-theft-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const calls = [];
        let theftDone = false;
        // Proxy the fs so that right after the FIRST run-state write (the
        // initial state), a concurrent process steals the run lock: the lock
        // path is replaced with a foreign token.
        const thievingFs = new Proxy(fs, {
            get(target, prop) {
                if (prop === 'writeFileSync') {
                    return (...args) => {
                        const ret = target.writeFileSync(...args);
                        // writeRunState stages to a `.tmp-<pid>-<nonce>`
                        // sibling first — match the run-state target by
                        // containment, not suffix.
                        if (!theftDone && String(args[0]).includes('run-state.json')) {
                            theftDone = true;
                            const runDir = path.dirname(String(args[0]));
                            const lockDir = path.join(runDir, '.capture-run.lock');
                            target.rmSync(lockDir, { recursive: true, force: true });
                            target.mkdirSync(lockDir, { recursive: true });
                            target.writeFileSync(path.join(lockDir, 'pid'), 'pid:77777:9', 'utf8');
                        }
                        return ret;
                    };
                }
                return target[prop];
            },
        });

        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-r12p1theft', maxRequests: 1,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls),
                extra: { fsImpl: thievingFs },
            })),
            (e) => e.code === 'SAFETY_ERROR' && /run lock ownership lost/.test(e.message)
        );
        assert.equal(calls.length, 0, 'no fetch may issue once ownership is lost (onBeforeFetch write verifies first)');
        assert.equal(
            fs.existsSync(path.join(dir, 'out', 'runs', 'run-r12p1theft', 'captures', '1-4506263.payload.json')),
            false,
            'no pair is retained by the displaced holder'
        );
        // The thief\'s lock survives (our release restored it).
        assert.equal(
            fs.readFileSync(path.join(dir, 'out', 'runs', 'run-r12p1theft', '.capture-run.lock', 'pid'), 'utf8'),
            'pid:77777:9',
            'the thief\'s token is never deleted'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R12-P2 (Codex re-review on cf500786e): replay shares the run lock — a live holder blocks replay with SAFETY_ERROR and zero artifacts; replay proceeds once the lock is released', async () => {
    const dir = tmpDir('fotmob-r12p2-replaylock-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const run = await awaitRunCapture({ dir, plan, planPath, runId: 'run-r12p2', maxRequests: 1 });
        assert.equal(run.status, 'complete');

        // Simulate a concurrent capture process holding the SAME run lock
        // the pipeline uses (the lock replay must now share). The holder is
        // a REAL live child process — the CLI's default liveness check must
        // see it as alive (an invented pid would be judged dead and taken
        // over, masking the lock).
        const { spawn } = require('node:child_process');
        const holder = spawn('sleep', ['30']);
        try {
            const { acquireRunLock, releaseRunLock } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
            const held = acquireRunLock(run.runDir, { fsImpl: fs, pid: holder.pid });

            assert.throws(
                () => runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION }),
                (e) => e.code === 'SAFETY_ERROR' && new RegExp(`another capture process \\(pid ${holder.pid}\\) holds the run lock`).test(e.message)
            );
            assert.equal(
                fs.readdirSync(path.join(run.runDir, 'replay')).length,
                0,
                'zero replay artifacts while the lock is held'
            );
            assert.equal(
                fs.existsSync(path.join(run.runDir, 'run-summary.json')),
                true,
                'the capture summary is untouched while the lock is held'
            );

            releaseRunLock(run.runDir, held, fs);
        } finally {
            holder.kill();
        }
        const ok = runReplay({ 'run-dir': run.runDir }, { stdout: { write: () => {} }, parserCodeRevision: TEST_REVISION });
        assert.equal(ok.replayed_count, 1, 'replay proceeds once the lock is released');
        assert.equal(
            fs.existsSync(path.join(run.runDir, '.capture-run.lock')),
            false,
            'replay releases the run lock afterwards — no residue'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-11 (Codex re-review on 13b27d5b9) — R13-P1
// ─────────────────────────────────────────────────────────────

test('R13-P1 (Codex re-review on 13b27d5b9): a lock whose token records the CURRENT process instance is judged live by INSTANCE identity — SAFETY_ERROR with zero fetches, no pidAlive injection needed', async () => {
    const dir = tmpDir('fotmob-r13p1-live-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r13p1live');
        const { readProcStarttimeTicks } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        const { spawn } = require('node:child_process');
        const holder = spawn('sleep', ['30']);
        try {
            const startTicks = readProcStarttimeTicks(holder.pid);
            assert.notEqual(startTicks, null, 'requires a Linux /proc start-time identity in the test environment');
            fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });
            fs.writeFileSync(path.join(runDir, '.capture-run.lock', 'pid'), `pid:${holder.pid}:${startTicks}:9999`, 'utf8');

            const calls = [];
            await assert.rejects(
                executeCaptureRun(makeCaptureOptions({
                    dir, plan, planPath, runId: 'run-r13p1live', maxRequests: 1,
                    fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls),
                    extra: { pid: 54321 },
                })),
                (e) => e.code === 'SAFETY_ERROR'
                    && new RegExp(`another capture process \\(pid ${holder.pid}\\) holds the run lock`).test(e.message)
            );
            assert.equal(calls.length, 0, 'no fetch while the same-instance holder lives');
            assert.equal(fs.existsSync(path.join(runDir, 'run-state.json')), false, 'run state never written');
            assert.equal(fs.existsSync(path.join(runDir, '.capture-run.lock')), true, 'the live instance lock is never removed');
        } finally {
            holder.kill();
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R13-P1 (Codex re-review on 13b27d5b9): a pid recycled to a DIFFERENT process instance is judged STALE despite kill() reporting it alive — capture takes over and recovers', async () => {
    const dir = tmpDir('fotmob-r13p1-recycled-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r13p1recycled');
        const { readProcStarttimeTicks } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        // Our OWN pid is verifiably alive (kill(pid,0) succeeds), but the
        // token records a start-time that belongs to NO live instance —
        // exactly the crashed-holder-then-pid-recycled scenario.
        const myTicks = readProcStarttimeTicks(process.pid);
        assert.notEqual(myTicks, null, 'requires a Linux /proc start-time identity in the test environment');
        const fakeTicks = myTicks + 1000;
        fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });
        fs.writeFileSync(path.join(runDir, '.capture-run.lock', 'pid'), `pid:${process.pid}:${fakeTicks}:9999`, 'utf8');

        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r13p1recycled', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            extra: { pid: 54321 },
        }));
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        assert.equal(fs.existsSync(path.join(runDir, '.capture-run.lock')), false, 'the recycled-instance lock is taken over and released');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-12 (Codex re-review on 948e0d23f) — R14-P1
// ─────────────────────────────────────────────────────────────

test('R14-P1 (Codex re-review on 948e0d23f): a season filter that matches NO candidate fails as INPUT_ERROR — an empty capture plan can never be built', () => {
    const dir = tmpDir('fotmob-r14p1-season-');
    try {
        assert.throws(
            () => makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2099/2100'] }),
            (err) => err.code === 'INPUT_ERROR'
                && /selection matched no candidates \(season filter \(2099\/2100\)\)/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R14-P1 (Codex re-review on 948e0d23f): a match-id filter that matches NO candidate fails as INPUT_ERROR', () => {
    const dir = tmpDir('fotmob-r14p1-mid-');
    try {
        assert.throws(
            () => makePlanFixture(dir, [TWO_CANDIDATES[0]], { matchIds: ['999999999'] }),
            (err) => err.code === 'INPUT_ERROR'
                && /selection matched no candidates \(match id filter \(999999999\)\)/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R14-P1 (Codex re-review on 948e0d23f): a zero-candidate plan fails the CONTRACT validator too — belt and suspenders behind the builder, so EXECUTE can never report a zero-request run as complete', () => {
    const dir = tmpDir('fotmob-r14p1-validator-');
    try {
        const { plan } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { validateAndRecomputeCapturePlan } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        // A tampered / legacy zero-candidate plan: wipe the candidates.
        const tampered = { ...plan, candidates: [], selected_candidate_count: 0 };
        const check = validateAndRecomputeCapturePlan(tampered);
        assert.equal(check.ok, false);
        assert.ok(
            check.errors.some((e) => /candidates must not be empty/.test(e)),
            `expected 'candidates must not be empty' in: ${check.errors.join('; ')}`
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-13 (Codex re-review on 55c450096) — R15-P1
// ─────────────────────────────────────────────────────────────

function r15Raw(stablePayload) {
    return buildRawDataFromStablePayload(
        { content: {}, general: {}, header: {}, matchId: null, ...stablePayload },
        buildFetchMetadata({ dataHash: 'x', matchIdSource: 'general.matchId' })
    );
}

test('R15-P1 (Codex re-review on 55c450096): reversed header.teams fail closed — both names present somewhere in the payload are NOT enough when the parser\'s ordered chain yields the wrong side', () => {
    // general provides NO team names, header.teams places them REVERSED:
    // the loose anywhere-in-text check passes, but FotMobRawParser.
    // extractTeams() would emit Fulham as home. Must fail.
    const raw = r15Raw({
        general: { matchId: '4506263' },
        header: {
            teams: [{ name: 'Fulham' }, { name: 'Manchester United' }],
            homeTeam: { name: 'Fulham' },
            awayTeam: { name: 'Manchester United' },
        },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        false,
        'reversed team placement must not pass the marker gate'
    );
});

test('R15-P1 (Codex re-review on 55c450096): correctly-placed header.teams pass — the parser chain yields the expected sides', () => {
    const raw = r15Raw({
        general: { matchId: '4506263' },
        header: {
            teams: [{ name: 'Manchester United' }, { name: 'Fulham' }],
            homeTeam: { name: 'Manchester United' },
            awayTeam: { name: 'Fulham' },
        },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        true
    );
});

test('R15-P1 (Codex re-review on 55c450096): incomplete team markers fail closed — names found only OUTSIDE the parser chain never pass', () => {
    // Both names appear in the payload text, but NONE of the parser's
    // fallback sources (general / header.teams / lineup / shortName) carry
    // them — the parser would emit empty team names. Must fail closed.
    const raw = r15Raw({
        general: { matchId: '4506263' },
        header: {},
        content: { liveticker: [{ text: 'Manchester United vs Fulham' }] },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        false,
        'incomplete team markers must fail closed'
    );
});

test('R15-P1 (Codex re-review on 55c450096): a page with the correct match id but REVERSED teams stops the capture run with zero retained pairs', async () => {
    const dir = tmpDir('fotmob-r15p1-e2e-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        // general provides BOTH team names but SWAPPED (home slot holds
        // the away team), header.teams consistent with the swap: the loose
        // anywhere-in-text check passes (both names present), the parser
        // chain yields the wrong sides, and only the ordered marker gate
        // can stop the run before anything is persisted.
        const html = makePageHtml({
            matchId: TWO_CANDIDATES[0].source_match_id,
            homeTeam: TWO_CANDIDATES[0].home_team,
            awayTeam: TWO_CANDIDATES[0].away_team,
            kickoffAt: TWO_CANDIDATES[0].kickoff_at,
            generalOverride: {
                homeTeam: { name: TWO_CANDIDATES[0].away_team },
                awayTeam: { name: TWO_CANDIDATES[0].home_team },
            },
            pagePropsExtra: {
                header: {
                    teams: [
                        { name: TWO_CANDIDATES[0].away_team },
                        { name: TWO_CANDIDATES[0].home_team },
                    ],
                    homeTeam: { name: TWO_CANDIDATES[0].away_team },
                    awayTeam: { name: TWO_CANDIDATES[0].home_team },
                    status: { utcTime: TWO_CANDIDATES[0].kickoff_at },
                },
            },
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r15p1e2e', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(html)),
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /content_validity:/);
        assert.equal(result.completedCount, 0);
        assert.equal(
            fs.existsSync(path.join(result.runDir, 'captures', '1-4506263.payload.json')),
            false,
            'no pair may be retained for a page with reversed teams'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// Round-14 (Codex re-review on 101028e1a) — R16-P1 / R16-P2
// ─────────────────────────────────────────────────────────────

test('R16-P1 (Codex re-review on 101028e1a): a lock held by the SAME process instance (same pid, same start ticks, different nonce) is a LIVE holder — in-process concurrency fails closed instead of stealing the lock', async () => {
    const dir = tmpDir('fotmob-r16p1-samepid-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r16p1samepid');
        const { readProcStarttimeTicks } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        // A concurrent executeCaptureRun() in THIS process wrote its token
        // first: identical (pid, start ticks) — only the nonce differs. The
        // old `holderPid !== ourPid` gate skipped the liveness check here
        // and STOLE the live lock; instance identity must judge it alive.
        const myTicks = readProcStarttimeTicks(process.pid);
        assert.notEqual(myTicks, null, 'requires a Linux /proc start-time identity in the test environment');
        fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });
        fs.writeFileSync(path.join(runDir, '.capture-run.lock', 'pid'), `pid:${process.pid}:${myTicks}:1111`, 'utf8');

        const calls = [];
        await assert.rejects(
            executeCaptureRun(makeCaptureOptions({
                dir, plan, planPath, runId: 'run-r16p1samepid', maxRequests: 2,
                fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0])), calls),
                extra: { pid: process.pid },
            })),
            (e) => e.code === 'SAFETY_ERROR'
                && new RegExp(`another capture process \\(pid ${process.pid}\\) holds the run lock`).test(e.message)
        );
        assert.equal(calls.length, 0, 'no fetch — the same-process holder is never displaced');
        assert.equal(fs.existsSync(path.join(runDir, 'run-state.json')), false, 'run state never written');
        assert.equal(
            fs.readFileSync(path.join(runDir, '.capture-run.lock', 'pid'), 'utf8'),
            `pid:${process.pid}:${myTicks}:1111`,
            'the live same-process lock is untouched — no takeover'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R16-P1 (Codex re-review on 101028e1a): a SAME-pid lock whose recorded instance is GONE (different start ticks) is still judged STALE — pid equality is decided by instance identity, not blocked outright', async () => {
    const dir = tmpDir('fotmob-r16p1-samepidrec-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const runDir = path.join(dir, 'out', 'runs', 'run-r16p1samepidrec');
        const { readProcStarttimeTicks } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
        // The token records OUR pid with a start-time belonging to NO live
        // instance (the crashed holder's instance, since recycled to us):
        // instance identity says stale, so the takeover must still proceed.
        const myTicks = readProcStarttimeTicks(process.pid);
        assert.notEqual(myTicks, null, 'requires a Linux /proc start-time identity in the test environment');
        fs.mkdirSync(path.join(runDir, '.capture-run.lock'), { recursive: true });
        fs.writeFileSync(path.join(runDir, '.capture-run.lock', 'pid'), `pid:${process.pid}:${myTicks + 1000}:9999`, 'utf8');

        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r16p1samepidrec', maxRequests: 1,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            extra: { pid: process.pid },
        }));
        assert.equal(result.status, 'complete');
        assert.equal(result.completedCount, 1);
        assert.equal(
            fs.existsSync(path.join(runDir, '.capture-run.lock')),
            false,
            'the stale same-pid lock is taken over and released'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R16-P2 (Codex re-review on 101028e1a): a WHITESPACE-ONLY general team name is what the parser SELECTS (firstValue skips only exact \'\') — the gate fails closed instead of skipping to header.teams', () => {
    // FotMobRawParser.firstValue() skips undefined / null / '' but NOT a
    // whitespace-only string: it selects general.homeTeam.name === '   ' and
    // persists a whitespace normalized.home_team.name. The old gate trimmed
    // it away, jumped to header.teams[0].name and PASSED — inconsistent with
    // the parser output. Selection must mirror firstValue exactly.
    const raw = r15Raw({
        general: { matchId: '4506263', homeTeam: { name: '   ' }, awayTeam: { name: '   ' } },
        header: {
            teams: [{ name: 'Manchester United' }, { name: 'Fulham' }],
            homeTeam: { name: 'Manchester United' },
            awayTeam: { name: 'Fulham' },
        },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        false,
        'a whitespace-only name is parser-selected and must fail the expected-team comparison'
    );
});

test('R16-P2 (Codex re-review on 101028e1a): whitespace-only names at LOWER chain positions are selected too — the gate never skips to a lower source the parser would not reach', () => {
    // general carries NO name at all (undefined — skipped), header.teams[0]
    // carries a whitespace-only name: firstValue selects the whitespace, so
    // the gate must fail — the parser would emit a whitespace home team
    // even though a perfectly good name sits in lineup below.
    const raw = r15Raw({
        general: { matchId: '4506263' },
        header: {
            teams: [{ name: ' ' }, { name: 'Fulham' }],
            homeTeam: { name: ' ' },
            awayTeam: { name: 'Fulham' },
        },
        content: {
            lineup: { homeTeam: { name: 'Manchester United' }, awayTeam: { name: 'Fulham' } },
        },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        false,
        'a whitespace-only lower-source name is selected (as the parser does) and fails closed'
    );
});

test('R16-P2 (Codex re-review on 101028e1a): a whitespace-only name BELOW a correct name does not disturb the gate — the parser selects the first non-empty value and it matches', () => {
    // general.homeTeam.name is the correct name, header.teams[0].name is
    // whitespace-only: firstValue stops at general, both sides match → pass.
    const raw = r15Raw({
        general: { matchId: '4506263', homeTeam: { name: 'Manchester United' }, awayTeam: { name: 'Fulham' } },
        header: {
            teams: [{ name: '   ' }, { name: '   ' }],
            homeTeam: { name: '   ' },
            awayTeam: { name: '   ' },
        },
        matchId: '4506263',
    });
    assert.equal(
        looksLikeValidRawDetail(raw, { externalId: '4506263', homeTeam: 'Manchester United', awayTeam: 'Fulham' }),
        true
    );
});

// ─────────────────────────────────────────────────────────────
// Round-15 (Codex re-review on 317fdb0d8) — R17-P1
// ─────────────────────────────────────────────────────────────

test('R17-P1 (Codex re-review on 317fdb0d8): an over-limit DECLARED Content-Length cancels the response body stream BEFORE the safety error — the socket is never left owned by an unread response', async () => {
    const dir = tmpDir('fotmob-r17p1-cancel-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        const { ReadableStream } = require('node:stream/web');
        // The response is established (headers received) with a REAL
        // cancellable body stream; the server declares an over-limit
        // Content-Length. The branch must cancel the body before throwing —
        // an uncancelled body would keep the underlying socket owned even
        // after the run stops.
        let cancelCalls = 0;
        const body = new ReadableStream({});
        const originalCancel = body.cancel.bind(body);
        body.cancel = async (...args) => {
            cancelCalls += 1;
            return originalCancel(...args);
        };
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: (n) => (n === 'content-length' ? String(MAX_BODY_BYTES + 1) : null) },
            body,
            arrayBuffer: async () => { throw new Error('BODY_SHOULD_NOT_BE_READ'); },
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r17p1cancel', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:declared_/);
        assert.equal(result.completedCount, 0);
        assert.equal(cancelCalls, 1, 'the response body stream is cancelled before the safety error is thrown');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R18-P1 (Codex re-review on 6ca5e90be): the pacing anchor is RE-ANCHORED on the ACTUAL fetch-start moment returned by onBeforeFetch — a slow pre-fetch state write can no longer shrink the real inter-request gap below delayMs', async () => {
    // The first request's pre-fetch callback (which synchronously writes
    // run-state) takes 200 ms of wall-clock time; the returned attempt
    // timestamp is the ACTUAL fetch-start moment. The old code kept the
    // pre-callback anchor, so the second request waited only 59800 ms and
    // the real gap between the two request STARTS was 59800 < 60000. The
    // fixed adapter anchors on the returned moment: full 60000 ms wait.
    const { createBoundedFetchAdapter } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
    let clockMs = Date.parse(FIXED_CLOCK);
    const sleeps = [];
    const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
    const fetches = [];
    const fetchImpl = async (url) => {
        fetches.push(String(url));
        return {
            status: 200,
            url: String(url),
            headers: { get: () => null },
            arrayBuffer: async () => new TextEncoder().encode('<html>x</html>'),
            body: new TextEncoder().encode('<html>x</html>'),
        };
    };
    const adapter = createBoundedFetchAdapter({
        fetchImpl,
        maxRequests: 2,
        delayMs: 60000,
        now: () => clockMs,
        sleepImpl,
        onBeforeFetch: (url, count) => {
            // Simulate the synchronous run-state write: the wall clock
            // advances DURING the callback, before the native fetch.
            clockMs += 200;
            return new Date(clockMs).toISOString();
        },
    });
    await adapter.fetchOnce('https://www.fotmob.com/match/4506263');
    assert.equal(sleeps.length, 0, 'first request never waits');
    await adapter.fetchOnce('https://www.fotmob.com/match/4506264');
    assert.equal(
        sleeps[0], 60000,
        `the second request waits the FULL delay (got ${sleeps[0]}): anchored on the actual fetch start, not the pre-callback moment`
    );
    assert.equal(fetches.length, 2, 'both requests issued');
});

test('R18-P1 (Codex re-review on 6ca5e90be): executeCaptureRun persists the SAME actual fetch-start moment that anchors the pacing — cross-process resume cannot start earlier than delayMs after the real request start', async () => {
    const dir = tmpDir('fotmob-r18p1-e2e-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        // A clock that advances DURING the callback: the adapter's ms clock
        // (Date.parse(now())) is read pre-callback and the run-state write
        // lands on a LATER tick — the persisted timestamp must be that later
        // (conservative) instant, identical to the pacing anchor.
        let tick = 0;
        let nextTimestamp = Date.parse(FIXED_CLOCK);
        const advancingNow = () => new Date((nextTimestamp += 1)).toISOString();
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); };
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r18p1e2e', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).split('/match/')[1];
                const cand = TWO_CANDIDATES.find(c => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }),
            sleepImpl,
            extra: { now: advancingNow },
        }));
        assert.equal(run.status, 'complete');
        assert.equal(run.completedCount, 2);
        const state = readStateJson(run.runDir);
        // The run-state anchor is the LAST request's attempt — compare it
        // with the SECOND candidate's manifest (candidate 2's attempt).
        const manifest = JSON.parse(fs.readFileSync(
            path.join(run.runDir, 'captures', '2-4506264.manifest.json'), 'utf8'
        ));
        // The persisted timestamp is the callback's returned attempt instant
        // (taken after the pre-callback anchor, immediately before the native
        // fetch) — the SAME value the adapter re-anchors on. A resume seeds
        // initialLastRequestAt with the ACTUAL fetch start and never starts
        // earlier than delayMs after the previous real request.
        assert.ok(
            Date.parse(state.last_network_request_attempted_at) > Date.parse(FIXED_CLOCK),
            'the persisted anchor is the later, actual fetch-start moment, not the pre-callback moment'
        );
        assert.equal(
            manifest.request_attempted_at, state.last_network_request_attempted_at,
            'the persisted anchor and the manifest agree on the actual fetch-start moment'
        );
        assert.equal(sleeps.length, 1, 'one inter-request wait across the two candidates');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R19-P1 (Codex re-review on 52fadcf09): even when onBeforeFetch returns a PRE-write timestamp, the adapter re-anchors AFTER the callback returns — the real gap between two request STARTS never falls below delayMs', async () => {
    const { createBoundedFetchAdapter } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
    let clockMs = Date.parse(FIXED_CLOCK);
    const sleeps = [];
    const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
    const fetchesAt = [];
    const fetches = [];
    const fetchImpl = async (url) => {
        fetchesAt.push(clockMs);
        fetches.push(String(url));
        return {
            status: 200,
            url: String(url),
            headers: { get: () => null },
            arrayBuffer: async () => new TextEncoder().encode('<html>x</html>'),
            body: new TextEncoder().encode('<html>x</html>'),
        };
    };
    const adapter = createBoundedFetchAdapter({
        fetchImpl,
        maxRequests: 2,
        delayMs: 60000,
        now: () => clockMs,
        sleepImpl,
        onBeforeFetch: (url, count) => {
            // Models the R18-P1 pipeline callback: the returned timestamp is
            // taken BEFORE the synchronous run-state write, and that write
            // advances the wall clock by 200 ms. R18-P1 anchored on the
            // returned (pre-write) moment, so the second request started
            // only 59800 ms after the first request's START. The adapter
            // must ignore the return value for PACING and anchor on the
            // post-callback moment — the true fetch start.
            const returned = new Date(clockMs).toISOString();
            clockMs += 200;
            return returned;
        },
    });
    await adapter.fetchOnce('https://www.fotmob.com/match/4506263');
    assert.equal(sleeps.length, 0, 'first request never waits');
    await adapter.fetchOnce('https://www.fotmob.com/match/4506264');
    assert.equal(
        sleeps[0], 60000,
        `the second request waits the FULL delay (got ${sleeps[0]}): the anchor is the post-callback moment, not the returned pre-write timestamp`
    );
    assert.ok(
        fetchesAt[1] - fetchesAt[0] >= 60000,
        `the real gap between the two request STARTS never falls below delayMs (got ${fetchesAt[1] - fetchesAt[0]}): the second callback's own write can only ENLARGE the gap, never shrink it`
    );
    assert.equal(fetches.length, 2, 'both requests issued');
});

test('R19-P1 (Codex re-review on 52fadcf09): executeCaptureRun anchors pacing on the moment AFTER its run-state write completes — when the FIRST candidate\'s state write is slower than the second\'s, the real fetch-start gap still never falls below delayMs', async () => {
    const dir = tmpDir('fotmob-r19p1-e2e-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        // Each synchronous run-state write for the FIRST candidate takes
        // 200 ms of wall-clock time; the second candidate's writes are fast.
        // The finding's exact scenario: if the first candidate's state write
        // is slower than the second's, an anchor taken BEFORE the write makes
        // the real gap between the two request STARTS
        // delayMs + write2 - write1 < delayMs. The R19-P1 callback re-takes
        // the anchor AFTER its own write (and the adapter re-anchors after
        // the callback), so the gap stays at the full delay.
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        const fetchesAt = [];
        const wrappedFs = {
            ...fs,
            writeFileSync: (p, data, enc) => {
                // Key the write duration on the request the payload belongs
                // to (the callback sets network_requests_attempted before
                // writing) — deterministic and independent of how many
                // run-state writes each version performs per request.
                if (String(p).includes('run-state')) {
                    let attempts = 0;
                    try { attempts = Number(JSON.parse(String(data)).network_requests_attempted || 0); } catch { /* non-JSON write */ }
                    if (attempts === 1) clockMs += 200;
                }
                return fs.writeFileSync(p, data, enc);
            },
        };
        const run = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r19p1e2e', maxRequests: 2,
            fetchImpl: mockFetchImpl((url) => {
                const id = String(url).split('/match/')[1];
                const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                fetchesAt.push(clockMs);
                return okResponse(pageFor(cand));
            }),
            sleepImpl,
            extra: {
                now: () => new Date(clockMs).toISOString(),
                fsImpl: wrappedFs,
            },
        }));
        assert.equal(run.status, 'complete');
        assert.equal(run.completedCount, 2);
        assert.ok(sleeps.length >= 1, 'inter-request wait enforced');
        const state = readStateJson(run.runDir);
        // Compare with the SECOND candidate's manifest — the run-state
        // anchor is the last request's attempt moment.
        const manifest = JSON.parse(fs.readFileSync(
            path.join(run.runDir, 'captures', '2-4506264.manifest.json'), 'utf8'
        ));
        assert.equal(
            manifest.request_attempted_at, state.last_network_request_attempted_at,
            'the persisted anchor is the callback\'s post-write moment — identical to the manifest'
        );
        assert.ok(
            Date.parse(state.last_network_request_attempted_at) > Date.parse(FIXED_CLOCK),
            'the persisted anchor is a post-write (later) instant, not the pre-write moment'
        );
        // THE invariant from the finding: two real request STARTS are never
        // closer than delayMs, regardless of how the per-request state-write
        // durations vary (R18-P1 code yields 59800 here — the bug).
        assert.ok(
            fetchesAt[1] - fetchesAt[0] >= 60000,
            `the real gap between the two request STARTS is at least delayMs (got ${fetchesAt[1] - fetchesAt[0]})`
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R20-P1 (Codex re-review on 0bfe90629): the fetch result records the TRUE post-callback fetch-start moment — the callback\'s pre-write return is never used as the audit timestamp', async () => {
    const { createBoundedFetchAdapter } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
    let clockMs = Date.parse(FIXED_CLOCK);
    const fetchImpl = async (url) => ({
        status: 200,
        url: String(url),
        headers: { get: () => null },
        arrayBuffer: async () => new TextEncoder().encode('<html>x</html>'),
        body: new TextEncoder().encode('<html>x</html>'),
    });
    const adapter = createBoundedFetchAdapter({
        fetchImpl,
        maxRequests: 1,
        delayMs: 60000,
        now: () => clockMs,
        sleepImpl: async () => {},
        onBeforeFetch: () => {
            // The callback's own timestamp is taken BEFORE its final
            // run-state write (the write takes 200 ms): the returned value
            // antedates the real fetch by one write duration and must NEVER
            // become the audit timestamp (R20-P1).
            const preWrite = new Date(clockMs).toISOString();
            clockMs += 200;
            return preWrite;
        },
    });
    const result = await adapter.fetchOnce('https://www.fotmob.com/match/4506263');
    assert.equal(
        result.requestAttemptedAt, new Date(Date.parse(FIXED_CLOCK) + 200).toISOString(),
        'the audit timestamp is the post-callback true fetch start, not the pre-write return'
    );
});

test('R20-P1 (Codex re-review on 0bfe90629): a FAILED fetch still conveys the TRUE fetch-start moment on the thrown error — the run\'s stop-path state write can actualize the persisted resume seed', async () => {
    const { createBoundedFetchAdapter } = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
    let clockMs = Date.parse(FIXED_CLOCK);
    const fetchImpl = async () => { throw new Error('NETWORK_TIMEOUT_SIMULATED'); };
    const adapter = createBoundedFetchAdapter({
        fetchImpl,
        maxRequests: 1,
        delayMs: 60000,
        now: () => clockMs,
        sleepImpl: async () => {},
        onBeforeFetch: () => {
            clockMs += 200; // the pre-fetch write takes 200 ms
            return new Date(clockMs).toISOString();
        },
    });
    let caught = null;
    try {
        await adapter.fetchOnce('https://www.fotmob.com/match/4506263');
    } catch (err) {
        caught = err;
    }
    assert.ok(caught, 'the fetch failure surfaces');
    assert.equal(
        caught.requestAttemptedAt, new Date(Date.parse(FIXED_CLOCK) + 200).toISOString(),
        'the error carries the true post-callback fetch-start moment (the attempt DID reach the network)'
    );
});

test('R20-P1 (Codex re-review on 0bfe90629): the PERSISTED resume seed is actualized to the true fetch-start after the fetch — a cross-process resume never starts earlier than delayMs after the REAL previous request start (the last run-state write\'s duration is covered)', async () => {
    const dir = tmpDir('fotmob-r20p1-resume-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        const fetchesAt = [];
        const wrappedFs = {
            ...fs,
            writeFileSync: (p, data, enc) => {
                // The LAST request's run-state writes (network_requests_
                // attempted = 2 — the second attempt) take 200 ms each — the
                // finding's scenario: the pre-fetch callback's last write
                // takes real time, and the persisted seed taken before it
                // antedates that request's true start by one write duration.
                if (String(p).includes('run-state')) {
                    let attempts = 0;
                    try { attempts = Number(JSON.parse(String(data)).network_requests_attempted || 0); } catch { /* non-JSON write */ }
                    if (attempts === 2) clockMs += 200;
                }
                return fs.writeFileSync(p, data, enc);
            },
        };
        const optionsFor = (fetchImpl) => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r20p1', maxRequests: 3,
            fetchImpl, sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString(), fsImpl: wrappedFs },
        });
        // Process 1 (immutable budget 3): candidate 1 captured, candidate 2
        // 403s — a real request that consumes budget but never completes, so
        // the resume keeps exactly one budget unit for its retry. The
        // persisted resume seed (the LAST request's seed) must equal the REAL
        // fetch-start moment of that 403 request.
        const firstRunFetch = mockFetchImpl((url) => {
            fetchesAt.push(clockMs);
            if (String(url).includes('4506264')) return { status: 403, body: '<html>forbidden</html>' };
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        });
        const workingFetch = mockFetchImpl((url) => {
            fetchesAt.push(clockMs);
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        });
        const run1 = await executeCaptureRun(optionsFor(firstRunFetch));
        assert.equal(run1.status, 'stopped');
        assert.equal(run1.completedCount, 1);
        const state1 = readStateJson(run1.runDir);
        assert.equal(
            state1.last_network_request_attempted_at, new Date(fetchesAt[1]).toISOString(),
            'the persisted resume seed equals the REAL last request start (R19-P1 code persisted the pre-last-write moment, 200 ms earlier)'
        );
        assert.equal(
            state1.next_allowed_request_at, new Date(fetchesAt[1] + 60000).toISOString(),
            'the persisted next-allowed-request deadline = true fetch start + delayMs — the resume gate covers the last pre-fetch write\'s duration'
        );
        assert.equal(
            Date.parse(state1.next_allowed_request_at) - Date.parse(state1.last_network_request_attempted_at), 60000,
            'the deadline and the seed timestamp maintain the delay invariant'
        );
        // The operator waits 30 s between the two processes.
        clockMs += 30000;
        // Process 2: resume with the SAME immutable budget of 3 — 2 already
        // consumed, exactly one unit left for the 403'd candidate's retry.
        const run2 = await executeCaptureRun(optionsFor(workingFetch));
        assert.equal(run2.status, 'complete');
        assert.equal(run2.completedCount, 2);
        assert.equal(fetchesAt.length, 3, 'two real requests in process 1, one in process 2');
        assert.ok(sleeps.length >= 1, 'the resumed process enforces the inter-request wait');
        assert.ok(
            fetchesAt[2] - fetchesAt[1] >= 60000,
            `the resumed process never starts earlier than delayMs after the REAL previous request start (got ${fetchesAt[2] - fetchesAt[1]}): the actualized seed covers the last run-state write's duration (R19-P1 code yields 59800)`
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R20-P1 (Codex re-review on 0bfe90629): the persisted next-allowed-request DEADLINE is exactly delayMs after the seed, and a PRESENT-but-invalid deadline fails closed on resume (tampering)', async () => {
    const dir = tmpDir('fotmob-r20p1-deadline-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleepImpl = async () => {};
        const optionsFor = () => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r20p1dl', maxRequests: 3,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString() },
        });
        const run = await executeCaptureRun(optionsFor());
        assert.equal(run.status, 'complete');
        const state = readStateJson(run.runDir);
        assert.equal(
            Date.parse(state.next_allowed_request_at) - Date.parse(state.last_network_request_attempted_at), 60000,
            'the persisted deadline is exactly delayMs after the persisted seed (both the crash-window and the actualized values maintain this invariant)'
        );
        // A present-but-invalid deadline fails closed on resume — the
        // read-side validator and the resume seeding both reject it.
        state.next_allowed_request_at = 'garbage';
        writeStateJson(run.runDir, state);
        await assert.rejects(
            executeCaptureRun(optionsFor()),
            (e) => e.code === 'SAFETY_ERROR' && /next_allowed_request_at/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R22-P1 (Codex re-review on 0bc69dad9): a HARD CRASH immediately after the fetch started — before ANY actualization write — leaves fetch_in_flight=true on disk, and the resume executes the FULL delay from the recovery moment (no mtime assumption)', async () => {
    const dir = tmpDir('fotmob-r21p1-crash-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        const fetchesAt = [];
        let runStateWriteCount = 0;
        let crashing = true;
        // The LAST pre-fetch run-state writes (run-state writes #2 and #3 —
        // the callback's write-1 and its follow-up write-2) take 200 ms each,
        // and the completion actualization (run-state write #4) is replaced
        // by a SIMULATED HARD CRASH: nothing is written after the fetch
        // started — exactly like a process death between fetchImpl() and the
        // actualization write, the finding's scenario.
        const wrappedFs = {
            ...fs,
            writeFileSync: (p, data, enc) => {
                if (String(p).includes('run-state')) {
                    runStateWriteCount += 1;
                    if (crashing && runStateWriteCount >= 4) {
                        throw new Error('SIMULATED_HARD_CRASH_AFTER_FETCH_START');
                    }
                    if (runStateWriteCount === 2 || runStateWriteCount === 3) clockMs += 200;
                }
                return fs.writeFileSync(p, data, enc);
            },
        };
        const optionsFor = (fetchImpl) => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r21p1', maxRequests: 3,
            fetchImpl, sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString(), fsImpl: wrappedFs },
        });
        const runDir = path.join(dir, 'out', 'runs', 'run-r21p1');
        // Process 1: candidate 1's fetch starts (TRUE start = T0 + 400) and
        // the process hard-crashes before the actualization — the on-disk
        // state is the LAST PRE-FETCH write's crash-window values.
        await assert.rejects(
            executeCaptureRun(optionsFor(mockFetchImpl(() => {
                fetchesAt.push(clockMs);
                return okResponse(pageFor(TWO_CANDIDATES[0]));
            }))),
            (e) => /SIMULATED_HARD_CRASH_AFTER_FETCH_START/.test(e.message),
            'the simulated hard crash stops the run exactly at the actualization write'
        );
        assert.equal(fetchesAt.length, 1, 'exactly one real request was issued before the crash');
        const state1 = readStateJson(runDir);
        assert.equal(state1.network_requests_attempted, 1);
        assert.equal(state1.captures_completed, 0, 'the actualization never landed — the crash preceded it');
        assert.equal(
            state1.fetch_in_flight, true,
            'the LAST pre-fetch write marked the request as possibly in flight — the crash left the marker true'
        );
        assert.equal(
            Date.parse(state1.next_allowed_request_at) - Date.parse(state1.last_network_request_attempted_at), 60000,
            'the crash-window deadline keeps the delay invariant'
        );
        assert.equal(
            Date.parse(state1.next_allowed_request_at),
            fetchesAt[0] - 200 + 60000,
            'the disk deadline = the pre-fetch basis + delayMs = TRUE fetch start + delayMs − (last pre-fetch write duration) — the reviewer\'s exact gap'
        );
        // The operator resumes 59900 ms after the TRUE fetch start. The
        // deadline-only gate (anchored at the pre-fetch basis) would already
        // be satisfied and issue the request 100 ms early; a mtime-anchored
        // gate would claim to cover the write's duration by assuming mtime is
        // the write's completion moment — a semantic real filesystems do not
        // provide (temp+rename keeps the TEMP file's mtime). The in-flight
        // marker instead forces the FULL delay from the recovery moment.
        clockMs = fetchesAt[0] + 59900;
        sleeps.length = 0;
        crashing = false;
        // Process 2: resume — candidate 1 has no pair (the crash preceded the
        // pair write), so it is re-fetched after the full-delay wait.
        const run2 = await executeCaptureRun(optionsFor(mockFetchImpl((url) => {
            fetchesAt.push(clockMs);
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        })));
        assert.equal(run2.status, 'complete');
        assert.equal(run2.completedCount, 2, 'the retried candidate and the second candidate both complete');
        assert.equal(fetchesAt.length, 3, 'one fetch before the crash, two after the resume');
        assert.equal(
            fetchesAt[1] - (fetchesAt[0] + 59900), 60000,
            `the resumed request waits the FULL delay from the recovery moment (got ${fetchesAt[1] - (fetchesAt[0] + 59900)}): the marker=true crash window never assumes when the last write completed`
        );
        assert.equal(
            fetchesAt[1] - fetchesAt[0], 119900,
            'the total gap from the TRUE previous fetch start is recovery + full delay — strictly later than any mtime or deadline-only anchor'
        );
        const state2 = readStateJson(runDir);
        assert.equal(
            state2.fetch_in_flight, false,
            'the completion actualization cleared the marker — the settled state is unambiguous for a future resume'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R21-P2 (Codex re-review on 05cd23c55): a deadline tampered to a SYNTACTICALLY VALID ISO time EARLIER than last + delay_ms fails closed on resume — parseability alone is not a gate', async () => {
    const dir = tmpDir('fotmob-r21p2-invariant-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleepImpl = async () => {};
        const optionsFor = () => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r21p2', maxRequests: 3,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString() },
        });
        const run = await executeCaptureRun(optionsFor());
        assert.equal(run.status, 'complete');
        const state = readStateJson(run.runDir);
        assert.equal(
            Date.parse(state.next_allowed_request_at) - Date.parse(state.last_network_request_attempted_at), 60000,
            'a clean run keeps the deadline === last + delayMs invariant'
        );
        // Tamper the deadline to a VALID ISO timestamp 1000 ms EARLY —
        // syntactically fine, but the resume gate would wait 1000 ms too
        // little. Both the read-side validator and the resume seeding reject
        // it before any request can be issued (the seeding's check is belt
        // and suspenders).
        state.next_allowed_request_at = new Date(
            Date.parse(state.last_network_request_attempted_at) + 59000
        ).toISOString();
        writeStateJson(run.runDir, state);
        await assert.rejects(
            executeCaptureRun(optionsFor()),
            (e) => e.code === 'SAFETY_ERROR' && /next_allowed_request_at/.test(e.message),
            'an EARLY-but-valid deadline fails closed on resume'
        );
        // The LATER direction (deadline beyond last + delayMs) is equally
        // outside the invariant — fail closed, never silently accepted.
        state.next_allowed_request_at = new Date(
            Date.parse(state.last_network_request_attempted_at) + 61000
        ).toISOString();
        writeStateJson(run.runDir, state);
        await assert.rejects(
            executeCaptureRun(optionsFor()),
            (e) => e.code === 'SAFETY_ERROR' && /next_allowed_request_at/.test(e.message),
            'a LATE-but-valid deadline also fails closed (the invariant is exact, not one-sided)'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R22-P1 (Codex re-review on 0bc69dad9): a SETTLED process death (marker cleared) resumes with the EXACT deadline anchor — the full-delay-from-recovery path is reserved for the crash window, never wasted on actualized state', async () => {
    const dir = tmpDir('fotmob-r22p1-settled-');
    try {
        const { plan, planPath } = makePlanFixture(dir, TWO_CANDIDATES, { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleeps = [];
        const sleepImpl = async (ms) => { sleeps.push(ms); clockMs += ms; };
        const fetchesAt = [];
        let runStateWriteCount = 0;
        let crashing = true;
        // Writes #2/#3 (candidate 1's pre-fetch writes) take 200 ms each —
        // same slow-write machinery as the crash test. Candidate 1 fully
        // settles (write #4 actualization clears the marker, write #5 records
        // captures_completed=1), the process sleeps out the inter-request
        // delay, and "dies" at write #6 — candidate 2's write-1, during the
        // WAIT between two settled requests: the on-disk state is fully
        // actualized (marker=false) and the crash window does not apply.
        const wrappedFs = {
            ...fs,
            writeFileSync: (p, data, enc) => {
                if (String(p).includes('run-state')) {
                    runStateWriteCount += 1;
                    if (crashing && runStateWriteCount >= 6) {
                        throw new Error('SIMULATED_HARD_CRASH_AFTER_SETTLEMENT');
                    }
                    if (runStateWriteCount === 2 || runStateWriteCount === 3) clockMs += 200;
                }
                return fs.writeFileSync(p, data, enc);
            },
        };
        const optionsFor = (fetchImpl) => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r22p1-settled', maxRequests: 3,
            fetchImpl, sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString(), fsImpl: wrappedFs },
        });
        const runDir = path.join(dir, 'out', 'runs', 'run-r22p1-settled');
        await assert.rejects(
            executeCaptureRun(optionsFor(mockFetchImpl((url) => {
                fetchesAt.push(clockMs);
                const id = String(url).split('/match/')[1];
                const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
                return okResponse(pageFor(cand));
            }))),
            (e) => /SIMULATED_HARD_CRASH_AFTER_SETTLEMENT/.test(e.message),
            'the simulated death stops the run at candidate 2\'s write-1'
        );
        assert.equal(fetchesAt.length, 1, 'candidate 1 was captured; candidate 2 never fetched');
        const state1 = readStateJson(runDir);
        assert.equal(state1.captures_completed, 1, 'candidate 1 fully captured and actualized');
        assert.equal(
            state1.fetch_in_flight, false,
            'the completion actualization cleared the marker — this is NOT a crash window'
        );
        // Resume 59900 ms after the REAL fetch start (1000 ms before the
        // deadline): the settled state anchors at deadline − delayMs = the
        // true fetch start, so the resumed request fires at EXACTLY
        // trueStart + 60000 — the efficient remaining-delay path.
        clockMs = fetchesAt[0] + 59900;
        sleeps.length = 0;
        crashing = false;
        const run2 = await executeCaptureRun(optionsFor(mockFetchImpl((url) => {
            fetchesAt.push(clockMs);
            const id = String(url).split('/match/')[1];
            const cand = TWO_CANDIDATES.find((c) => String(c.source_match_id) === id) || TWO_CANDIDATES[0];
            return okResponse(pageFor(cand));
        })));
        assert.equal(run2.status, 'complete');
        assert.equal(run2.completedCount, 2, 'candidate 1 completed in run-1, candidate 2 completed in run-2');
        assert.equal(fetchesAt.length, 2, 'one fetch in run-1, one in run-2 (the completed pair is never re-fetched)');
        assert.equal(
            fetchesAt[1] - fetchesAt[0], 60000,
            `the settled-state resume anchors at the EXACT deadline — the real gap is delayMs, not recovery + delayMs (got ${fetchesAt[1] - fetchesAt[0]})`
        );
        assert.ok(
            sleeps.some((ms) => ms === 100),
            'the resumed process sleeps only the REMAINING delay (100 ms) — no full-delay waste on actualized state'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R22-P1 (Codex re-review on 0bc69dad9): a NON-BOOLEAN fetch_in_flight fails closed on resume — the marker contract is exact, no magic values', async () => {
    const dir = tmpDir('fotmob-r22p1-marker-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        let clockMs = Date.parse(FIXED_CLOCK);
        const sleepImpl = async () => {};
        const optionsFor = () => makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r22p1-marker', maxRequests: 3,
            fetchImpl: mockFetchImpl(() => okResponse(pageFor(TWO_CANDIDATES[0]))),
            sleepImpl,
            extra: { now: () => new Date(clockMs).toISOString() },
        });
        const run = await executeCaptureRun(optionsFor());
        assert.equal(run.status, 'complete');
        const state = readStateJson(run.runDir);
        assert.equal(state.fetch_in_flight, false, 'a clean run ends with the marker cleared');
        state.fetch_in_flight = 'yes';
        writeStateJson(run.runDir, state);
        await assert.rejects(
            executeCaptureRun(optionsFor()),
            (e) => e.code === 'SAFETY_ERROR' && /fetch_in_flight/.test(e.message),
            'a non-boolean marker fails closed — the pipeline can only ever write true or false'
        );
        // An ABSENT marker (legacy state) is tolerated and treated as settled
        // — backward compatible with pre-marker states.
        delete state.fetch_in_flight;
        writeStateJson(run.runDir, state);
        const run2 = await executeCaptureRun(optionsFor());
        assert.equal(run2.status, 'complete', 'an absent marker is a settled legacy state — resume proceeds');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('R17-P1 (Codex re-review on 317fdb0d8): the declared-length cancel is best-effort — a body without a cancel method still stops the run with the same safety error', async () => {
    const dir = tmpDir('fotmob-r17p1-nocancel-');
    try {
        const { plan, planPath } = makePlanFixture(dir, [TWO_CANDIDATES[0]], { seasons: ['2024/2025'] });
        const { MAX_BODY_BYTES } = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
        // Mock body object that is NOT cancellable (no cancel method): the
        // branch must degrade gracefully and still fail closed.
        const fetchImpl = async (url) => ({
            status: 200,
            url,
            headers: { get: (n) => (n === 'content-length' ? String(MAX_BODY_BYTES + 1) : null) },
            body: { getReader: () => { throw new Error('READER_SHOULD_NOT_BE_CREATED'); } },
            arrayBuffer: async () => { throw new Error('BODY_SHOULD_NOT_BE_READ'); },
        });
        const result = await executeCaptureRun(makeCaptureOptions({
            dir, plan, planPath, runId: 'run-r17p1nocancel', maxRequests: 1, fetchImpl,
        }));
        assert.equal(result.status, 'stopped');
        assert.match(result.stopReason, /fetch_error:SAFETY_ERROR:oversized_response_body:declared_/);
        assert.equal(result.completedCount, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
