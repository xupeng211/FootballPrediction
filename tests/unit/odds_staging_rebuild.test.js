'use strict';

// lifecycle: permanent；M3-R1 有界重建入口回归测试（source identity ×4、output safety ×3、
// semantic boundary ×5、determinism ×2、receipt ×4、no-forbidden-capability ×2）。
// 全部使用运行时生成的临时 bundle fixture；不写入仓库、不访问网络/数据库。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    EXIT_CODES,
    buildPopulationEntries,
    compareIdentitySortKey,
    computeSourcePopulationBusinessHash,
    main,
    runRebuild,
    validateRebuildReceipt,
} = require('../../scripts/ops/odds_staging/historical_odds_rebuild');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const REBUILD_SCRIPT = path.join(
    PROJECT_ROOT,
    'scripts/ops/odds_staging/historical_odds_rebuild.js'
);
const INGESTED_AT = '2026-08-09T06:15:00Z';

function sha256File(filePath) {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function createTempDirectory(t, prefix = 'fp-odds-staging-rebuild-') {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return directory;
}

// 4-row fixture: A1/A2 = same match spelled with aliases (Bournemouth/Man City vs
// AFC Bournemouth/Manchester City), B = Chelsea vs Arsenal, C = Liverpool vs Everton.
const FIXTURE_CSV = [
    'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,B365CH,B365CD,B365CA',
    'test-fixture,E0,05/08/2023,15:00,Bournemouth,Man City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,05/08/2023,15:00,AFC Bournemouth,Manchester City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,06/08/2023,17:30,Chelsea,Arsenal,2,1,1.80,3.80,4.50,1.84,3.76,4.44',
    'test-fixture,E0,06/08/2023,19:00,Liverpool,Everton,0,0,2.05,3.30,3.90,2.10,3.28,3.85',
].join('\n');

// 4 FotMob-style candidates: A matched, B matched, C kickoff +15m conflict, D unused.
function writeCandidates(t, directory) {
    const candidatesPath = path.join(directory, 'candidates.json');
    fs.writeFileSync(
        candidatesPath,
        `${JSON.stringify({
            schema_version: 'candidate-match-identity/v1',
            extracted_at: '2026-07-17T18:51:14.657Z',
            snapshot: {
                source_provider: 'FotMob',
                league_id: '47',
                competition: 'Premier League',
                seasons: ['2023/2024'],
                candidate_count: 4,
                business_content_sha256: 'a'.repeat(64),
            },
            candidates: [
                { id: '47_20232024_0000001', source_provider: 'FotMob', source_match_id: '0000001', competition: 'Premier League', season: '2023/2024', home_team: 'AFC Bournemouth', away_team: 'Manchester City', kickoff_at: '2023-08-05T14:00:00Z' },
                { id: '47_20232024_0000002', source_provider: 'FotMob', source_match_id: '0000002', competition: 'Premier League', season: '2023/2024', home_team: 'Chelsea', away_team: 'Arsenal', kickoff_at: '2023-08-06T16:30:00Z' },
                { id: '47_20232024_0000003', source_provider: 'FotMob', source_match_id: '0000003', competition: 'Premier League', season: '2023/2024', home_team: 'Liverpool', away_team: 'Everton', kickoff_at: '2023-08-06T18:15:00Z' },
                { id: '47_20232024_0000004', source_provider: 'FotMob', source_match_id: '0000004', competition: 'Premier League', season: '2023/2024', home_team: 'Newcastle United', away_team: 'Aston Villa', kickoff_at: '2023-08-07T14:00:00Z' },
            ],
        })}\n`,
        'utf8'
    );
    return candidatesPath;
}

function writeHistoricalManifest(t, rawPath, directory) {
    const manifestPath = path.join(directory, 'source.manifest.json');
    fs.writeFileSync(
        manifestPath,
        `${JSON.stringify({
            schema_version: 'odds-source-manifest/v1',
            source_provider: 'football-data-csv',
            acquisition_mode: 'historical_git_recovery',
            source_url: 'git+repository://xupeng211/FootballPrediction@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/fixtures/rebuild.csv',
            declared_upstream_url: null,
            source_match_id: null,
            captured_at: null,
            capture_time_status: 'unknown',
            recovered_at: '2026-08-09T06:14:00Z',
            source_timezone: 'unknown',
            raw_path: rawPath,
            raw_media_type: 'text/csv',
            raw_size_bytes: fs.readFileSync(rawPath).length,
            raw_sha256: sha256File(rawPath),
            adapter: 'football-data-csv',
            adapter_version: '1.2.0',
            provenance_status: 'declared',
            upstream_provenance_status: 'unverified',
            license_status: 'unverified',
            repository_provenance: {
                repository: 'xupeng211/FootballPrediction',
                commit_sha: 'a'.repeat(40),
                blob_sha: 'b'.repeat(40),
                path: 'tests/fixtures/odds_staging/rebuild.fixture.csv',
                commit_timestamp: '2026-01-29T19:22:29+08:00',
            },
            kickoff_time_interpretation: {
                status: 'derived',
                timezone: 'Europe/London',
                method: 'source_local_calendar_time',
                evidence_level: 'empirical_cross_source',
                official_source_declaration: false,
                evidence_reference: 'M3-R1 orchestration regression fixture',
                allowed_competitions: ['Premier League'],
                allowed_seasons: ['2023/2024'],
            },
        })}\n`,
        'utf8'
    );
    return manifestPath;
}

function writeBundle(t, overrides = {}) {
    const directory = createTempDirectory(t);
    const csvPath = path.join(directory, 'source.csv');
    fs.writeFileSync(csvPath, overrides.csv ?? FIXTURE_CSV, 'utf8');
    const manifestPath = overrides.manifest
        ? overrides.manifest(csvPath, directory)
        : writeHistoricalManifest(t, csvPath, directory);
    const candidatesPath = overrides.candidates === null ? null : writeCandidates(t, directory);
    fs.writeFileSync(
        path.join(directory, 'sources.json'),
        `${JSON.stringify({
            schema_version: 'm3-historical-odds-rebuild-bundle/v1',
            sources: overrides.sources ?? [{ id: 'fixture', csv: 'source.csv', manifest: 'source.manifest.json' }],
        })}\n`,
        'utf8'
    );
    const emitDirectory = path.join(directory, 'emit');
    fs.mkdirSync(emitDirectory);
    return { directory, csvPath, manifestPath, candidatesPath, emitDirectory };
}

function runBundle(t, options = {}) {
    const bundle = writeBundle(t, options);
    const receipt = runRebuild({
        bundle: bundle.directory,
        candidates: options.candidates === null ? undefined : bundle.candidatesPath,
        emitDir: bundle.emitDirectory,
        ingestedAt: INGESTED_AT,
    });
    return { bundle, receipt };
}

function readEmittedObservations(bundle, kind = 'accepted-observations.jsonl') {
    const filePath = path.join(bundle.emitDirectory, 'fixture', kind);
    return fs
        .readFileSync(filePath, 'utf8')
        .trim()
        .split('\n')
        .filter(Boolean)
        .map(line => JSON.parse(line));
}

function quarantineToObservationView(entry) {
    const sourceFields = entry.evidence.source_fields;
    return {
        source_provider: entry.source_provider,
        source_match_id: entry.source_match_id,
        competition: sourceFields.competition,
        season: sourceFields.season,
        kickoff_at: sourceFields.kickoff_at,
        home_team: sourceFields.home_team,
        away_team: sourceFields.away_team,
    };
}

function readAllObservationViews(bundle) {
    return [
        ...readEmittedObservations(bundle, 'accepted-observations.jsonl'),
        ...readEmittedObservations(bundle, 'quarantine.jsonl').map(quarantineToObservationView),
    ];
}

// ---- source identity ×4 ----------------------------------------------------

test('rebuild: unique source candidates from fixture are canonical match identities', t => {
    const { receipt } = runBundle(t, { candidates: null });
    assert.equal(receipt.source_population.unique_candidates, 3);
    assert.deepEqual(receipt.source_population.per_season, { '2023/2024': 3 });
    assert.equal(receipt.source_population.identity_mode, 'canonical_match_identity');
});

test('rebuild: source-scoped exact aliases resolve two spellings to one identity', t => {
    const { bundle } = runBundle(t, { candidates: null });
    const entries = buildPopulationEntries(readAllObservationViews(bundle));
    const bournemouth = entries.find(
        entry => entry.identity.home_team === 'AFC Bournemouth' && entry.identity.away_team === 'Manchester City'
    );
    assert.ok(bournemouth, 'alias-resolved identity must exist');
    assert.equal(bournemouth.identity.kickoff_at, '2023-08-05T14:00:00Z');
    assert.equal(bournemouth.identity.competition, 'Premier League');
    assert.equal(bournemouth.identity.season, '2023/2024');
});

test('rebuild: source population business hash is deterministic and consistent with the receipt', t => {
    const { bundle, receipt } = runBundle(t, { candidates: null });
    const observations = readAllObservationViews(bundle);
    // The hash is a pure function of the identities; recompute from the same source population path used by the orchestrator.
    const entries = buildPopulationEntries(observations);
    const first = computeSourcePopulationBusinessHash(entries.map(entry => entry.identity));
    const second = computeSourcePopulationBusinessHash(entries.map(entry => entry.identity));
    assert.equal(first, second);
    assert.equal(receipt.source_population.business_content_sha256, first);
    assert.match(first, /^[a-f0-9]{64}$/);
});

test('rebuild: no synthetic source IDs are invented for any source candidate', t => {
    const { bundle } = runBundle(t, { candidates: null });
    const entries = buildPopulationEntries(readAllObservationViews(bundle));
    assert.ok(entries.length > 0);
    for (const entry of entries) {
        assert.equal(entry.identity.identity_mode, 'canonical_match_identity');
    }
});

// ---- output safety ×3 ------------------------------------------------------

test('rebuild: emit directory inside the repository is refused (safety boundary)', t => {
    const directory = createTempDirectory(t);
    const exitCode = main(
        ['--bundle', directory, '--emit-dir', PROJECT_ROOT, '--ingested-at', INGESTED_AT],
        { stdout: () => {}, stderr: () => {} }
    );
    assert.equal(exitCode, EXIT_CODES.safety_boundary_error);
});

test('rebuild: bundle directory inside the repository is refused (safety boundary)', t => {
    const directory = createTempDirectory(t);
    fs.mkdirSync(path.join(directory, 'emit'));
    const exitCode = main(
        ['--bundle', PROJECT_ROOT, '--emit-dir', path.join(directory, 'emit'), '--ingested-at', INGESTED_AT],
        { stdout: () => {}, stderr: () => {} }
    );
    assert.equal(exitCode, EXIT_CODES.safety_boundary_error);
});

test('rebuild: non-empty emit directory is refused and mid-run failure rolls back all staged output', t => {
    const bundle = writeBundle(t);
    fs.writeFileSync(path.join(bundle.emitDirectory, 'pre-existing.txt'), 'x', 'utf8');
    assert.throws(
        () =>
            runRebuild({
                bundle: bundle.directory,
                candidates: bundle.candidatesPath,
                emitDir: bundle.emitDirectory,
                ingestedAt: INGESTED_AT,
            }),
        error => error.code === 'SAFETY_ERROR'
    );

    // Mid-run failure: second source has a manifest whose raw_sha256 does not match its CSV.
    // Only the second source's manifest is corrupted — the first source must emit
    // successfully so the rollback path (removing the first source's staged output)
    // is genuinely exercised rather than trivially passing with nothing staged.
    const failing = writeBundle(t, {
        sources: [
            { id: 'first', csv: 'source.csv', manifest: 'source.manifest.json' },
            { id: 'second', csv: 'source.csv', manifest: 'broken.manifest.json' },
        ],
    });
    const brokenManifest = JSON.parse(fs.readFileSync(failing.manifestPath, 'utf8'));
    brokenManifest.raw_sha256 = '0'.repeat(64);
    fs.writeFileSync(path.join(failing.directory, 'broken.manifest.json'), `${JSON.stringify(brokenManifest)}\n`, 'utf8');
    assert.throws(
        () =>
            runRebuild({
                bundle: failing.directory,
                candidates: failing.candidatesPath,
                emitDir: failing.emitDirectory,
                ingestedAt: INGESTED_AT,
            }),
        error => error.code === 'INPUT_ERROR' || error.code === 'SAFETY_ERROR'
    );
    assert.deepEqual(fs.readdirSync(failing.emitDirectory), [], 'no partial output may remain after a failed rebuild');
});

// ---- semantic boundary ×5 --------------------------------------------------

test('rebuild: plain and C-series columns stay snapshot_type unknown with their own quote series', t => {
    const { bundle } = runBundle(t);
    const observations = readEmittedObservations(bundle);
    assert.equal(observations.length, 12);
    const seriesCounts = {};
    for (const observation of observations) {
        assert.equal(observation.snapshot_type, 'unknown');
        seriesCounts[observation.source_quote_series] = (seriesCounts[observation.source_quote_series] || 0) + 1;
    }
    assert.deepEqual(seriesCounts, { B365: 6, B365C: 6 });
});

test('rebuild: captured_at stays null and capture_time_status stays unknown on every observation', t => {
    const { bundle } = runBundle(t);
    const observations = readEmittedObservations(bundle);
    assert.ok(observations.length > 0);
    for (const observation of observations) {
        assert.equal(observation.captured_at, null);
        assert.equal(observation.capture_time_status, 'unknown');
    }
});

test('rebuild: with empty candidate set every observation quarantines only as match_link_unmatched', t => {
    const { bundle, receipt } = runBundle(t, { candidates: null });
    assert.equal(receipt.sources[0].accepted_count, 0);
    assert.equal(receipt.sources[0].quarantine_count, 18);
    assert.deepEqual(receipt.sources[0].quarantine_reasons, { match_link_unmatched: 18 });
    for (const entry of readEmittedObservations(bundle, 'quarantine.jsonl')) {
        assert.deepEqual(entry.reasons, ['match_link_unmatched']);
    }
});

test('rebuild: kickoff conflict quarantine carries only the conflict reason, never an opening/closing claim', t => {
    const { receipt } = runBundle(t);
    assert.deepEqual(receipt.sources[0].quarantine_reasons, { kickoff_conflict_15m: 6 });
    assert.equal(receipt.sources[0].accepted_count, 12);
});

test('rebuild: emitted receipt and observations never claim temporal semantics', t => {
    const { bundle, receipt } = runBundle(t);
    const receiptText = JSON.stringify(receipt);
    assert.ok(!receiptText.includes('opening'), 'receipt must not contain opening claims');
    assert.ok(!receiptText.includes('closing'), 'receipt must not contain closing claims');
    for (const observation of readEmittedObservations(bundle)) {
        assert.ok(!JSON.stringify(observation).includes('opening'));
        assert.ok(!JSON.stringify(observation).includes('closing'));
    }
});

// ---- determinism ×2 --------------------------------------------------------

function collectTree(directory) {
    const files = {};
    for (const name of fs.readdirSync(directory).sort()) {
        const full = path.join(directory, name);
        if (fs.statSync(full).isDirectory()) {
            for (const [relative, content] of Object.entries(collectTree(full))) {
                files[path.join(name, relative)] = content;
            }
        } else {
            files[name] = fs.readFileSync(full, 'utf8');
        }
    }
    return files;
}

test('rebuild: identical inputs into two fresh emit dirs produce byte-identical output', t => {
    // Determinism contract: same bundle + candidates + ingested_at → byte-identical
    // emit trees. One bundle, two fresh emit dirs (mirrors BUILD_A / BUILD_B).
    const bundle = writeBundle(t);
    const emitB = path.join(bundle.directory, 'emit-b');
    fs.mkdirSync(emitB);
    const options = { bundle: bundle.directory, candidates: bundle.candidatesPath, emitDir: bundle.emitDirectory, ingestedAt: INGESTED_AT };
    const optionsB = { bundle: bundle.directory, candidates: bundle.candidatesPath, emitDir: emitB, ingestedAt: INGESTED_AT };
    const receiptA = runRebuild(options);
    const receiptB = runRebuild(optionsB);
    assert.equal(receiptA.source_population.business_content_sha256, receiptB.source_population.business_content_sha256);
    assert.deepEqual(collectTree(bundle.emitDirectory), collectTree(emitB));
});

test('rebuild: observation idempotency keys are identical across deterministic rebuilds', t => {
    const bundle = writeBundle(t);
    const emitB = path.join(bundle.directory, 'emit-b');
    fs.mkdirSync(emitB);
    runRebuild({ bundle: bundle.directory, candidates: bundle.candidatesPath, emitDir: bundle.emitDirectory, ingestedAt: INGESTED_AT });
    runRebuild({ bundle: bundle.directory, candidates: bundle.candidatesPath, emitDir: emitB, ingestedAt: INGESTED_AT });
    const keysA = readEmittedObservations(bundle).map(observation => observation.idempotency_key).sort();
    const keysB = readEmittedObservations({ ...bundle, emitDirectory: emitB }).map(observation => observation.idempotency_key).sort();
    assert.deepEqual(keysA, keysB);
    assert.equal(new Set(keysA).size, keysA.length);
});

// ---- receipt ×4 ------------------------------------------------------------

test('rebuild: produced receipt validates as m3-historical-odds-rebuild-receipt/v1', t => {
    const { receipt } = runBundle(t);
    const validation = validateRebuildReceipt(receipt);
    assert.deepEqual(validation, { valid: true, errors: [] });
    assert.equal(receipt.schema_version, 'm3-historical-odds-rebuild-receipt/v1');
});

test('rebuild: receipt validation rejects an unsupported schema version', t => {
    const { receipt } = runBundle(t);
    const validation = validateRebuildReceipt({ ...receipt, schema_version: 'other/v1' });
    assert.equal(validation.valid, false);
    assert.ok(validation.errors.some(error => error.includes('schema_version')));
});

test('rebuild: receipt validation rejects a missing required field', t => {
    const { receipt } = runBundle(t);
    const mutated = { ...receipt };
    delete mutated.ingested_at;
    const validation = validateRebuildReceipt(mutated);
    assert.equal(validation.valid, false);
    assert.ok(validation.errors.some(error => error.includes('ingested_at')));
});

test('rebuild: receipt validation rejects wrong field types', t => {
    const { receipt } = runBundle(t);
    const mutated = {
        ...receipt,
        sources: receipt.sources.map(source => ({ ...source, quarantine_count: 'many' })),
    };
    const validation = validateRebuildReceipt(mutated);
    assert.equal(validation.valid, false);
    assert.ok(validation.errors.some(error => error.includes('quarantine_count')));
});

// ---- codex round-2 regression fixes ----------------------------------------

test('rebuild: business hash sort is locale-independent code-unit ordering', t => {
    // Characters where locale collation disagrees with code-unit order (e.g. 'ä'
    // vs 'z'): the recorded hash must follow UTF-16 code-unit order everywhere.
    const identities = [
        { season: '2023/2024', kickoff_at: '2023-08-05T14:00:00Z', home_team: 'Zürich FC', away_team: 'Alpha FC', competition: 'Premier League', source_provider: 'football-data-csv' },
        { season: '2023/2024', kickoff_at: '2023-08-05T14:00:00Z', home_team: 'Atletico Madrid', away_team: 'Beta FC', competition: 'Premier League', source_provider: 'football-data-csv' },
        { season: '2023/2024', kickoff_at: '2023-08-06T16:30:00Z', home_team: 'Mönchengladbach', away_team: 'Gamma FC', competition: 'Premier League', source_provider: 'football-data-csv' },
    ];
    const expectedOrder = [...identities].sort((left, right) => {
        const leftKey = `${left.season}|${left.kickoff_at}|${left.home_team}|${left.away_team}`;
        const rightKey = `${right.season}|${right.kickoff_at}|${right.home_team}|${right.away_team}`;
        return leftKey < rightKey ? -1 : leftKey > rightKey ? 1 : 0;
    });
    assert.deepEqual([...identities].sort(compareIdentitySortKey), expectedOrder);
    const first = computeSourcePopulationBusinessHash(identities);
    const second = computeSourcePopulationBusinessHash([...identities].reverse());
    assert.equal(first, second, 'hash must not depend on input order or locale collation');
});

test('rebuild: emit directory pointing at a regular file is a clean safety error', t => {
    const directory = createTempDirectory(t);
    const filePath = path.join(directory, 'not-a-dir');
    fs.writeFileSync(filePath, 'x', 'utf8');
    const exitCode = main(
        ['--bundle', directory, '--emit-dir', filePath, '--ingested-at', INGESTED_AT],
        { stdout: () => {}, stderr: () => {} }
    );
    assert.equal(exitCode, EXIT_CODES.safety_boundary_error);
});

// ---- codex round-1 regression fixes ----------------------------------------

test('rebuild: malicious bundle source id cannot escape the emit directory', t => {
    const bundle = writeBundle(t, {
        sources: [{ id: '../escaped', csv: 'source.csv', manifest: 'source.manifest.json' }],
    });
    assert.throws(
        () =>
            runRebuild({
                bundle: bundle.directory,
                candidates: bundle.candidatesPath,
                emitDir: bundle.emitDirectory,
                ingestedAt: INGESTED_AT,
            }),
        error => error.code === 'SAFETY_ERROR'
    );
    const escaped = path.join(path.dirname(bundle.emitDirectory), 'escaped');
    assert.ok(!fs.existsSync(escaped), 'nothing may be written outside the emit directory');
    assert.deepEqual(fs.readdirSync(bundle.emitDirectory), [], 'emit directory stays empty');
});

test('rebuild: adapter-quarantine rows never inflate the source population', t => {
    // Row 5 has an incomplete B365 1X2 (empty draw) -> adapter quarantine
    // (incomplete_explicit_1x2_values); its B365C group is complete, so the row
    // still contributes canonical observations. The population must count only
    // canonical identities (4 matches), never unresolved adapter rows.
    const csv = [
        'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,B365CH,B365CD,B365CA',
        'test-fixture,E0,05/08/2023,15:00,Bournemouth,Man City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
        'test-fixture,E0,05/08/2023,15:00,AFC Bournemouth,Manchester City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
        'test-fixture,E0,06/08/2023,17:30,Chelsea,Arsenal,2,1,1.80,3.80,4.50,1.84,3.76,4.44',
        'test-fixture,E0,06/08/2023,19:00,Liverpool,Everton,0,0,2.05,3.30,3.90,2.10,3.28,3.85',
        'test-fixture,E0,07/08/2023,15:00,Newcastle United,Aston Villa,1,1,2.30,,3.10,2.35,3.25,2.90',
    ].join('\n');
    const { receipt } = runBundle(t, { candidates: null, csv });
    assert.ok(receipt.sources[0].quarantine_count >= 1, 'adapter quarantine must exist in the output');
    assert.equal(receipt.source_population.unique_candidates, 4);
    assert.deepEqual(receipt.source_population.per_season, { '2023/2024': 4 });
    assert.equal(receipt.source_population.identity_mode, 'canonical_match_identity');
});

// ---- no-forbidden-capability ×2 --------------------------------------------

test('rebuild: orchestrator source imports no network, browser, or database capability', t => {
    const source = fs.readFileSync(REBUILD_SCRIPT, 'utf8');
    const forbiddenRequires = [
        'node:http',
        'node:https',
        'node:net',
        'node:tls',
        'node:dgram',
        'node:dns',
        'node:child_process',
        'node:worker_threads',
        "'pg'",
        '"pg"',
        "'pg'",
        'node-fetch',
        'undici',
        'playwright',
        'puppeteer',
        'selenium',
    ];
    for (const token of forbiddenRequires) {
        assert.ok(!source.includes(token), `forbidden import token present: ${token}`);
    }
    assert.ok(!/fetch\(/.test(source), 'no global fetch usage');
    assert.ok(!/child_process|spawn|exec/.test(source), 'no process execution');
});

test('rebuild: receipt boundary declares no network, no database, no repository write', t => {
    const { receipt } = runBundle(t);
    assert.equal(receipt.boundary.network, false);
    assert.equal(receipt.boundary.database, false);
    assert.equal(receipt.boundary.repository_write, false);
    assert.equal(receipt.boundary.default_mode, 'dry_run_no_write');
    assert.equal(validateRebuildReceipt(receipt).valid, true);
});
