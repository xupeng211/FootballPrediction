'use strict';

// lifecycle: permanent
// CLI tests for scripts/ops/fotmob_detail_capture.js.
// Fully offline: no network (structurally forbidden), no database.

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
    main,
    parseArgs,
    runPlan,
    runCapture,
    runReplay,
    USAGE,
} = require('../../scripts/ops/fotmob_detail_capture');
const {
    buildDeterministicCapturePlan,
    writePlanDocument,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const {
    computeBusinessContentHash,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const {
    executeCaptureRun,
    REQUIRED_ENV_VAR,
    REQUIRED_ENV_BUDGET,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePipeline');
const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CLI_PATH = path.join(REPO_ROOT, 'scripts/ops/fotmob_detail_capture.js');
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

function writeV1Artifact(dir, candidates) {
    const doc = {
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
    const p = path.join(dir, 'artifact.json');
    fs.writeFileSync(p, JSON.stringify(doc, null, 2));
    return p;
}

function makePageHtml({ matchId, homeTeam, awayTeam, kickoffAt }) {
    const content = { stats: { periods: ['x'] }, lineup: { lineups: [] }, shotmap: { shots: [] } };
    const general = { matchId: String(matchId), homeTeam: { name: homeTeam }, awayTeam: { name: awayTeam }, matchTimeUTC: kickoffAt, season: '2024/2025' };
    const header = { homeTeam: { name: homeTeam }, awayTeam: { name: awayTeam }, status: { utcTime: kickoffAt } };
    const nextData = { props: { pageProps: { content, general, header, ssr: true } } };
    return `<!doctype html><html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script>${'x'.repeat(300)}</body></html>`;
}

function captureStdout() {
    let out = '';
    return {
        write: (s) => { out += s; },
        read: () => out,
    };
}

test('CLI: help mode prints usage and exits cleanly', () => {
    const stdout = captureStdout();
    return main([], { stdout }).then((r) => {
        assert.equal(r.mode, 'help');
        assert.ok(stdout.read().includes('fotmob_detail_capture.js'));
    });
});

test('CLI: parseArgs handles repeated flags and kebab-case', () => {
    const { args, positionals } = parseArgs(['plan', '--season=2024/2025', '--season', '2023/2024', '--match-id=42', '--limit=3', '--output=/tmp/x.json']);
    assert.deepEqual(positionals, ['plan']);
    assert.deepEqual(args.season, ['2024/2025', '2023/2024']);
    assert.deepEqual(args['match-id'], ['42']);
    assert.equal(args.limit, '3');
    assert.equal(args.output, '/tmp/x.json');
});

test('CLI: plan subcommand writes a valid plan', () => {
    const dir = tmpDir('fotmob-cli-plan-');
    try {
        const candidates = [makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' })];
        const artifact = writeV1Artifact(dir, candidates);
        const outputPath = path.join(dir, 'plan.json');
        const stdout = captureStdout();
        const result = runPlan({
            'candidate-artifact': artifact,
            season: ['2024/2025'],
            output: outputPath,
        }, { stdout, now: () => FIXED_CLOCK, repositoryRoot: REPO_ROOT, execSync: CLEAN_EXEC });
        assert.equal(result.mode, 'plan');
        assert.equal(result.selected_candidate_count, 1);
        assert.ok(fs.existsSync(outputPath));
        const plan = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
        assert.equal(plan.schema_version, 'fotmob-detail-capture-plan/v1');
        assert.equal(plan.candidates[0].source_match_id, '4506263');
        assert.ok(stdout.read().includes('plan_business_sha256'));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: plan subcommand rejects missing selection (exit code 2)', () => {
    const dir = tmpDir('fotmob-cli-nofilter-');
    try {
        const candidates = [makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' })];
        const artifact = writeV1Artifact(dir, candidates);
        const outputPath = path.join(dir, 'plan.json');
        const spawned = spawnSync(process.execPath, [
            CLI_PATH, 'plan',
            `--candidate-artifact=${artifact}`,
            `--output=${outputPath}`,
        ], { encoding: 'utf8' });
        assert.equal(spawned.status, 2);
        assert.match(spawned.stderr, /explicit selection required/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: plan subcommand rejects unknown schema (exit code 2)', () => {
    const dir = tmpDir('fotmob-cli-schema-');
    try {
        const doc = {
            schema_version: 'bogus-schema/v1',
            source_provider: 'FotMob',
            candidates: [makeCandidate({ id: 1, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' })],
        };
        const artifact = path.join(dir, 'artifact.json');
        fs.writeFileSync(artifact, JSON.stringify(doc));
        const spawned = spawnSync(process.execPath, [
            CLI_PATH, 'plan',
            `--candidate-artifact=${artifact}`,
            '--season=2024/2025',
            `--output=${path.join(dir, 'plan.json')}`,
        ], { encoding: 'utf8' });
        assert.equal(spawned.status, 2);
        assert.match(spawned.stderr, /artifact validation failed/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: capture subcommand without --execute fails with zero fetches', async () => {
    const dir = tmpDir('fotmob-cli-capture-');
    try {
        const candidates = [makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' })];
        const artifact = writeV1Artifact(dir, candidates);
        const planResult = buildDeterministicCapturePlan({
            artifactPath: artifact,
            seasons: ['2024/2025'],
            generatedAt: FIXED_CLOCK,
            collectorCodeRevision: TEST_REVISION,
        });
        const planPath = path.join(dir, 'plan.json');
        writePlanDocument(planResult.plan, planPath);
        const outputRoot = path.join(dir, 'out');
        const calls = [];
        const fetchImpl = async (url, opts) => {
            calls.push(url);
            const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
            return { status: 200, url, headers: { get: () => 'text/html; charset=utf-8' }, text: async () => page, arrayBuffer: async () => Buffer.from(page) };
        };
        const stdout = captureStdout();
        await assert.rejects(
            runCapture({
                plan: planPath,
                'output-root': outputRoot,
                'expected-plan-sha256': planResult.plan.plan_business_sha256,
                'authorization-id': 'cli-auth',
                'max-requests': 1,
                'delay-ms': 60000,
                'run-id': 'cli-run',
            }, {
                stdout,
                env: { [REQUIRED_ENV_VAR]: '1', [REQUIRED_ENV_BUDGET]: '1' },
                repositoryRoot: REPO_ROOT,
                execSync: CLEAN_EXEC,
                fetchImpl,
                parser: { extractFromHtml: NextDataParser.extractFromHtml, transformToApiFormat: NextDataParser.transformToApiFormat, parseFotMobRaw: FotMobRawParser.parseFotMobRaw },
                now: () => FIXED_CLOCK,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /--execute/.test(e.message)
        );
        assert.equal(calls.length, 0);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: capture subcommand succeeds with all gates (mocked fetch)', async () => {
    const dir = tmpDir('fotmob-cli-capture-ok-');
    try {
        const candidates = [makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' })];
        const artifact = writeV1Artifact(dir, candidates);
        const planResult = buildDeterministicCapturePlan({
            artifactPath: artifact,
            seasons: ['2024/2025'],
            generatedAt: FIXED_CLOCK,
            collectorCodeRevision: TEST_REVISION,
        });
        const planPath = path.join(dir, 'plan.json');
        writePlanDocument(planResult.plan, planPath);
        const outputRoot = path.join(dir, 'out');
        const calls = [];
        const fetchImpl = async (url, opts) => {
            calls.push(url);
            const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
            return { status: 200, url, headers: { get: () => 'text/html; charset=utf-8' }, text: async () => page, arrayBuffer: async () => Buffer.from(page) };
        };
        const stdout = captureStdout();
        const result = await runCapture({
            plan: planPath,
            'output-root': outputRoot,
            'expected-plan-sha256': planResult.plan.plan_business_sha256,
            'authorization-id': 'cli-auth',
            'max-requests': 1,
            'delay-ms': 60000,
            'run-id': 'cli-run',
            execute: true,
        }, {
            stdout,
            env: { [REQUIRED_ENV_VAR]: '1', [REQUIRED_ENV_BUDGET]: '1' },
            repositoryRoot: REPO_ROOT,
            execSync: CLEAN_EXEC,
            fetchImpl,
            parser: { extractFromHtml: NextDataParser.extractFromHtml, transformToApiFormat: NextDataParser.transformToApiFormat, parseFotMobRaw: FotMobRawParser.parseFotMobRaw },
            now: () => FIXED_CLOCK,
        });
        assert.equal(result.mode, 'capture');
        assert.equal(result.status, 'complete');
        assert.equal(result.completed_count, 1);
        assert.equal(calls.length, 1);
        assert.ok(stdout.read().includes('"run_id"'));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: replay subcommand replays a completed run offline', async () => {
    const dir = tmpDir('fotmob-cli-replay-');
    try {
        // Build a complete run via executeCaptureRun (mocked fetch).
        const candidates = [makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' })];
        const artifact = writeV1Artifact(dir, candidates);
        const planResult = buildDeterministicCapturePlan({
            artifactPath: artifact,
            seasons: ['2024/2025'],
            generatedAt: FIXED_CLOCK,
            collectorCodeRevision: TEST_REVISION,
        });
        const planPath = path.join(dir, 'plan.json');
        writePlanDocument(planResult.plan, planPath);
        const outputRoot = path.join(dir, 'out');
        const fetchImpl = async (url, opts) => {
            const page = makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' });
            return { status: 200, url, headers: { get: () => 'text/html; charset=utf-8' }, text: async () => page, arrayBuffer: async () => Buffer.from(page) };
        };
        const run = await executeCaptureRun({
            plan: planResult.plan,
            planPath,
            expectedPlanSha256: planResult.plan.plan_business_sha256,
            authorizationId: 'cli-auth',
            maxRequests: 1,
            outputRoot,
            runId: 'cli-run-replay',
            execute: true,
            networkAuthorization: true,
            delayMs: 60000,
            sleepImpl: async () => {},
            fetchImpl,
            parser: { extractFromHtml: NextDataParser.extractFromHtml, transformToApiFormat: NextDataParser.transformToApiFormat, parseFotMobRaw: FotMobRawParser.parseFotMobRaw },
            now: () => FIXED_CLOCK,
            env: { [REQUIRED_ENV_VAR]: '1', [REQUIRED_ENV_BUDGET]: '1' },
            repositoryRoot: REPO_ROOT,
            execSync: CLEAN_EXEC,
        });
        assert.equal(run.status, 'complete');

        const stdout = captureStdout();
        const result = runReplay({
            'run-dir': run.runDir,
            plan: planPath,
        }, {
            stdout,
            parser: {
                extractFromHtml: NextDataParser.extractFromHtml,
                transformToApiFormat: NextDataParser.transformToApiFormat,
                parseFotMobRaw: require('../../src/parsers/fotmob/FotMobRawParser').parseFotMobRaw,
            },
            now: () => FIXED_CLOCK,
            parserCodeRevision: TEST_REVISION,
        });
        assert.equal(result.mode, 'replay');
        assert.equal(result.replayed_count, 1);
        assert.ok(fs.existsSync(path.join(run.runDir, 'replay', '1-4506263.detail.json')));
        assert.ok(stdout.read().includes('structured_payload_sha256'));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('CLI: replay subcommand fails on missing run-state', () => {
    const dir = tmpDir('fotmob-cli-replay-missing-');
    try {
        const stdout = captureStdout();
        // runReplay uses fail() → process.exit — catch via child process
        // is safer; here we assert the guard by spawning.
        const spawned = spawnSync(process.execPath, [
            CLI_PATH, 'replay',
            `--run-dir=${dir}`,
        ], { encoding: 'utf8' });
        assert.equal(spawned.status, 2);
        assert.match(spawned.stderr, /run-state.json not found/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
