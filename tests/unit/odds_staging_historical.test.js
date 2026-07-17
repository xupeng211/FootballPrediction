'use strict';

// lifecycle: permanent；验证 Football-Data 历史列组、source-native quote series 与 historical_git_recovery 未知采集时间语义。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    buildIdempotencyPayload,
    buildSemanticDuplicateKey,
    createCanonicalObservation,
} = require('../../src/infrastructure/odds_staging/contracts');
const { ADAPTER_VERSIONS, adaptFootballDataCsv } = require('../../src/infrastructure/odds_staging/adapters');
const { detectFakeOdds } = require('../../src/infrastructure/odds_staging/fakeOddsDetector');
const { runOfflineStaging } = require('../../src/infrastructure/odds_staging/pipeline');
const { loadSourceBundle, validateSourceManifest } = require('../../src/infrastructure/odds_staging/sourceManifest');
const { validateObservation } = require('../../src/infrastructure/odds_staging/validators');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const CSV_FIXTURE = path.join(PROJECT_ROOT, 'tests/fixtures/odds_staging/football_data_explicit.fixture.csv');
const HISTORICAL_CSV_FIXTURE = path.join(
    PROJECT_ROOT,
    'tests/fixtures/odds_staging/football_data_historical_columns.fixture.csv'
);
const FIXED_INGESTED_AT = '2026-07-16T00:00:00.000Z';

function sha256File(filePath) {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function createTempDirectory(t) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-odds-staging-historical-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return directory;
}

function writeFixtureManifest(t, rawPath, overrides = {}) {
    const directory = createTempDirectory(t);
    const manifestPath = path.join(directory, 'source-manifest.fixture.json');
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-fixture',
        acquisition_mode: 'fixture',
        source_url: 'fixture://football-data/fixture-fd-001',
        source_match_id: null,
        captured_at: '2025-08-01T10:00:00Z',
        source_timezone: 'UTC',
        raw_path: rawPath,
        raw_media_type: 'text/csv',
        raw_size_bytes: fs.readFileSync(rawPath).length,
        raw_sha256: sha256File(rawPath),
        adapter: 'football-data-csv',
        adapter_version: ADAPTER_VERSIONS['football-data-csv'],
        provenance_status: 'fixture',
        ...overrides,
    };
    fs.writeFileSync(manifestPath, `${JSON.stringify(manifest)}\n`, 'utf8');
    return { manifest, manifestPath };
}

function writeHistoricalManifest(t, rawPath, overrides = {}) {
    const directory = createTempDirectory(t);
    const manifestPath = path.join(directory, 'source-manifest.historical.json');
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-historical',
        acquisition_mode: 'historical_git_recovery',
        source_url: `git+repository://example/repository@${'a'.repeat(40)}/data/history.csv`,
        declared_upstream_url: null,
        source_match_id: null,
        captured_at: null,
        capture_time_status: 'unknown',
        recovered_at: '2026-07-17T00:00:00Z',
        source_timezone: 'unknown',
        raw_path: rawPath,
        raw_media_type: 'text/csv',
        raw_size_bytes: fs.readFileSync(rawPath).length,
        raw_sha256: sha256File(rawPath),
        adapter: 'football-data-csv',
        adapter_version: ADAPTER_VERSIONS['football-data-csv'],
        provenance_status: 'declared',
        upstream_provenance_status: 'unverified',
        license_status: 'unverified',
        repository_provenance: {
            repository: 'example/repository',
            commit_sha: 'a'.repeat(40),
            blob_sha: 'b'.repeat(40),
            path: 'data/history.csv',
            commit_timestamp: '2026-01-29T19:22:29+08:00',
        },
        ...overrides,
    };
    fs.writeFileSync(manifestPath, `${JSON.stringify(manifest)}\n`, 'utf8');
    return { manifest, manifestPath };
}

function withoutField(object, field) {
    const clone = { ...object };
    delete clone[field];
    return clone;
}

function historicalCandidates() {
    return [
        {
            id: 'local-hist-001',
            source_provider: 'football-data-fixture',
            source_match_id: null,
            competition: 'E0',
            kickoff_at: '2025-08-05T19:00:00Z',
            home_team: 'Alpha FC',
            away_team: 'Beta FC',
        },
        {
            id: 'local-hist-002',
            source_provider: 'football-data-fixture',
            source_match_id: null,
            competition: 'E0',
            kickoff_at: '2025-08-06T17:30:00Z',
            home_team: 'Gamma FC',
            away_team: 'Delta FC',
        },
    ];
}

function baseObservation(overrides = {}) {
    return createCanonicalObservation({
        source_provider: 'fixture-provider',
        source_url: 'fixture://source/one',
        source_match_id: 'fixture-match-1',
        competition: 'Fixture League',
        season: '2025/2026',
        kickoff_at: '2025-08-01T18:00:00Z',
        home_team: 'Alpha FC',
        away_team: 'Beta FC',
        bookmaker: 'Fixture Book',
        bookmaker_source_id: 'fixture-book',
        market: '1X2',
        selection: 'home',
        line: null,
        decimal_odds: 2.1,
        snapshot_type: 'unknown',
        source_observed_at: null,
        captured_at: '2025-08-01T10:00:00Z',
        source_timezone: 'UTC',
        raw_sha256: 'a'.repeat(64),
        raw_record_locator: 'fixture:record=1',
        adapter: 'football-data-csv',
        adapter_version: ADAPTER_VERSIONS['football-data-csv'],
        extraction_method: 'explicit_fixture_field',
        provenance_status: 'fixture',
        ingested_at: FIXED_INGESTED_AT,
        ...overrides,
    });
}

function writeRawText(t, filename, content) {
    const rawPath = path.join(createTempDirectory(t), filename);
    fs.writeFileSync(rawPath, content, 'utf8');
    return rawPath;
}

test('historical_git_recovery manifest 只接受显式 unknown capture 语义与完整 Git 证据', async t => {
    const valid = writeHistoricalManifest(t, HISTORICAL_CSV_FIXTURE);
    await t.test('有效 historical manifest 通过校验并保持 captured_at=null', () => {
        assert.deepEqual(validateSourceManifest(valid.manifest).errors, []);
        const bundle = loadSourceBundle({
            manifestPath: valid.manifestPath,
            sourcePath: HISTORICAL_CSV_FIXTURE,
        });
        assert.equal(bundle.manifest.captured_at, null);
        assert.equal(bundle.manifest.capture_time_status, 'unknown');
        assert.equal(bundle.manifest.recovered_at, '2026-07-17T00:00:00Z');
        assert.equal(bundle.manifest.upstream_provenance_status, 'unverified');
        assert.equal(bundle.manifest.repository_provenance.blob_sha, 'b'.repeat(40));
    });

    await t.test('普通 fixture manifest 缺少 captured_at 仍然失败', () => {
        const { manifest } = writeFixtureManifest(t, CSV_FIXTURE);
        const result = validateSourceManifest(withoutField(manifest, 'captured_at'));
        assert.equal(result.valid, false);
        assert.ok(result.errors.some(error => /captured_at/.test(error)));
    });

    const invalidScenarios = [
        ['recovered_at 不得进入 captured_at', { captured_at: valid.manifest.recovered_at }, /explicitly null/],
        [
            'Git commit 时间不得冒充 captured_at',
            { captured_at: valid.manifest.repository_provenance.commit_timestamp },
            /explicitly null/,
        ],
        [
            '缺少 capture_time_status',
            withoutField(valid.manifest, 'capture_time_status'),
            /capture_time_status: unknown/,
        ],
        ['capture_time_status 不接受 estimated', { capture_time_status: 'estimated' }, /capture_time_status: unknown/],
        ['缺少 recovered_at', withoutField(valid.manifest, 'recovered_at'), /recovered_at/],
        ['recovered_at 拒绝 naive 时间', { recovered_at: '2026-07-17T00:00:00' }, /recovered_at/],
        ['provenance_status 不得为 verified', { provenance_status: 'verified' }, /provenance_status: declared/],
        [
            'upstream_provenance_status 必须 unverified',
            { upstream_provenance_status: 'verified' },
            /upstream_provenance_status: unverified/,
        ],
        [
            '缺少 repository_provenance',
            withoutField(valid.manifest, 'repository_provenance'),
            /repository_provenance object/,
        ],
        [
            'blob_sha 必须是完整 40 位 Git SHA',
            { repository_provenance: { ...valid.manifest.repository_provenance, blob_sha: 'b1ob' } },
            /blob_sha/,
        ],
        [
            'commit_timestamp 拒绝 naive 时间',
            {
                repository_provenance: {
                    ...valid.manifest.repository_provenance,
                    commit_timestamp: '2026-01-29 19:22:29',
                },
            },
            /commit_timestamp/,
        ],
    ];
    for (const [name, mutation, pattern] of invalidScenarios) {
        await t.test(name, () => {
            // withoutField 场景已是完整 manifest（自带 schema_version），其余场景与有效 manifest 合并。
            const manifest = Object.prototype.hasOwnProperty.call(mutation, 'schema_version')
                ? mutation
                : { ...valid.manifest, ...mutation };
            const result = validateSourceManifest(manifest);
            assert.equal(result.valid, false);
            assert.ok(
                result.errors.some(error => pattern.test(error)),
                `expected ${pattern} in ${JSON.stringify(result.errors)}`
            );
        });
    }

    await t.test('非 historical 模式不能滥用 unknown capture time', () => {
        const { manifest } = writeFixtureManifest(t, CSV_FIXTURE);
        const abusedStatus = validateSourceManifest({ ...manifest, capture_time_status: 'unknown' });
        assert.equal(abusedStatus.valid, false);
        assert.ok(abusedStatus.errors.some(error => /only allowed when acquisition_mode/.test(error)));
        const abusedRecoveredAt = validateSourceManifest({ ...manifest, recovered_at: '2026-07-17T00:00:00Z' });
        assert.equal(abusedRecoveredAt.valid, false);
        assert.ok(abusedRecoveredAt.errors.some(error => /recovered_at is only allowed/.test(error)));
        const nullCapture = validateSourceManifest({ ...manifest, captured_at: null });
        assert.equal(nullCapture.valid, false);
    });
});

test('capture_time_status 语义只在显式 unknown 时放行 null captured_at', () => {
    const historical = validateObservation(baseObservation({ captured_at: null, capture_time_status: 'unknown' }));
    assert.ok(!historical.quarantine_reasons.includes('captured_at_invalid'));
    assert.ok(historical.quality_flags.includes('source_capture_time_unknown'));

    const abused = validateObservation(
        baseObservation({ captured_at: '2025-08-01T10:00:00Z', capture_time_status: 'unknown' })
    );
    assert.ok(abused.quarantine_reasons.includes('captured_at_present_with_unknown_capture_time_status'));

    const missing = validateObservation(baseObservation({ captured_at: null }));
    assert.ok(missing.quarantine_reasons.includes('captured_at_invalid'));

    const invalidStatus = validateObservation(baseObservation({ captured_at: null, capture_time_status: 'estimated' }));
    assert.ok(invalidStatus.quarantine_reasons.includes('capture_time_status_invalid'));
});

test('historical recovery observation 保持 captured_at=null 并获得 source_capture_time_unknown flag', t => {
    const { manifestPath } = writeHistoricalManifest(t, HISTORICAL_CSV_FIXTURE);
    const result = runOfflineStaging({
        sourcePath: HISTORICAL_CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: [],
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(result.summary.accepted_count, 0);
    assert.ok(result.summary.total_observations > 0);
    const observationEntries = result.quarantine.filter(entry => entry.evidence?.parsed_fields);
    assert.ok(observationEntries.length > 0);
    for (const entry of observationEntries) {
        assert.equal(entry.evidence.parsed_fields.captured_at, null);
        assert.equal(entry.evidence.parsed_fields.capture_time_status, 'unknown');
        assert.ok(entry.evidence.quality_flags.includes('source_capture_time_unknown'));
        assert.ok(entry.reasons.includes('kickoff_timezone_unresolved'));
        assert.ok(entry.reasons.includes('source_match_identity_insufficient'));
        assert.ok(!Object.prototype.hasOwnProperty.call(entry.evidence.parsed_fields, 'recovered_at'));
    }
});

test('历史列组：逐博彩公司普通列与 C 列分别保留且 snapshot 保持 unknown', t => {
    const { manifestPath } = writeFixtureManifest(t, HISTORICAL_CSV_FIXTURE);
    const result = runOfflineStaging({
        sourcePath: HISTORICAL_CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: historicalCandidates(),
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(result.summary.accepted_count, 66);
    assert.equal(result.summary.quarantine_count, 1);
    assert.equal(result.summary.semantic_duplicate_count, 0);
    assert.equal(result.summary.semantic_conflict_count, 0);
    assert.ok(result.quarantine[0].reasons.includes('incomplete_explicit_1x2_values'));

    const accepted = result.accepted_observations;
    assert.deepEqual([...new Set(accepted.map(observation => observation.bookmaker))].sort(), [
        'Bet365',
        'Bwin',
        'Interwetten',
        'Pinnacle',
        'VC Bet',
        'William Hill',
    ]);
    assert.deepEqual([...new Set(accepted.map(observation => observation.source_quote_series))].sort(), [
        'B365',
        'B365C',
        'BW',
        'BWC',
        'IW',
        'IWC',
        'PS',
        'PSC',
        'VC',
        'VCC',
        'WH',
        'WHC',
    ]);
    assert.ok(accepted.every(observation => observation.snapshot_type === 'unknown'));
    assert.ok(accepted.every(observation => observation.source_observed_at === null));
    assert.ok(accepted.every(observation => !/max|avg|bbav|bbmx/i.test(observation.bookmaker)));
    assert.ok(accepted.every(observation => observation.match_link.status === 'matched'));

    const bet365Series = new Set(
        accepted
            .filter(observation => observation.bookmaker === 'Bet365' && observation.home_team === 'Alpha FC')
            .map(observation => observation.source_quote_series)
    );
    assert.deepEqual([...bet365Series].sort(), ['B365', 'B365C']);
});

test('source_quote_series 隔离普通列与 C 列语义，同 series 真正重复仍可去重', async t => {
    const header = 'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365CH,B365CD,B365CA';
    const identicalOddsRow = 'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.10,3.40,3.60';
    const candidates = [historicalCandidates()[0]];
    const run = (t2, rows) => {
        const rawPath = writeRawText(t2, 'series.fixture.csv', [header, ...rows].join('\n') + '\n');
        const { manifestPath } = writeFixtureManifest(t2, rawPath);
        return runOfflineStaging({
            sourcePath: rawPath,
            manifestPath,
            adapter: 'football-data-csv',
            candidates,
            ingestedAt: FIXED_INGESTED_AT,
        });
    };

    await t.test('普通列与 C 列同赔率并存，不发生 semantic collision', t2 => {
        const result = run(t2, [identicalOddsRow]);
        assert.equal(result.summary.accepted_count, 6);
        assert.equal(result.summary.semantic_duplicate_count, 0);
        assert.equal(result.summary.semantic_conflict_count, 0);
    });

    await t.test('同一 series 的真正重复行合并为 semantic duplicate', t2 => {
        const result = run(t2, [identicalOddsRow, identicalOddsRow]);
        assert.equal(result.summary.accepted_count, 6);
        assert.equal(result.summary.semantic_duplicate_count, 6);
        assert.equal(result.summary.semantic_conflict_count, 0);
    });

    await t.test('同一 series 的赔率冲突仍然 quarantine', t2 => {
        const result = run(t2, [
            'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.30,3.20,3.05',
            'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.40,3.10,3.15',
        ]);
        assert.equal(result.summary.semantic_conflict_count, 3);
        const conflicted = result.quarantine.filter(entry => entry.reasons.includes('semantic_duplicate_conflict'));
        assert.equal(conflicted.length, 6);
        assert.ok(conflicted.every(entry => entry.evidence.parsed_fields.source_quote_series === 'B365C'));
    });

    await t.test('缺席的可选字段不进入 idempotency payload；存在时才参与', () => {
        const withoutSeries = baseObservation();
        const payload = buildIdempotencyPayload(withoutSeries);
        assert.ok(!Object.prototype.hasOwnProperty.call(payload, 'source_quote_series'));
        assert.ok(!Object.prototype.hasOwnProperty.call(payload, 'capture_time_status'));

        const withSeries = baseObservation({ source_quote_series: 'B365C' });
        assert.equal(buildIdempotencyPayload(withSeries).source_quote_series, 'B365C');
        assert.notEqual(withSeries.idempotency_key, withoutSeries.idempotency_key);
        assert.notEqual(buildSemanticDuplicateKey(withSeries), buildSemanticDuplicateKey(withoutSeries));
        assert.equal(
            buildSemanticDuplicateKey(withSeries),
            buildSemanticDuplicateKey(baseObservation({ source_quote_series: 'B365C' }))
        );
    });
});

test('snake_case 历史列解析为同一博彩公司，未知 timezone 时 kickoff 保持 null', () => {
    const rawText =
        'Div,match_date,Time,home_team,away_team,b365_home_odds,b365_draw_odds,b365_away_odds,ps_home_odds,ps_draw_odds,ps_away_odds,B365CH,B365CD,B365CA\n' +
        'E0,2025-08-05,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.11,3.41,3.62,2.15,3.35,3.50\n';
    const result = adaptFootballDataCsv(rawText, {
        manifest: { source_timezone: 'unknown', source_match_id: null },
    });

    assert.equal(result.quarantine.length, 0);
    assert.equal(result.observations.length, 9);
    const byGroup = new Map();
    for (const observation of result.observations) {
        byGroup.set(observation.extraction_method, observation);
        assert.equal(observation.kickoff_at, null);
        assert.equal(observation.snapshot_type, 'unknown');
        assert.equal(observation.source_observed_at, null);
        assert.equal(observation.home_team, 'Alpha FC');
        assert.ok(observation.adapter_quarantine_reasons.includes('kickoff_timezone_unresolved'));
    }
    assert.equal(byGroup.get('explicit_csv_columns:bet365-snake-unknown').bookmaker, 'Bet365');
    assert.equal(byGroup.get('explicit_csv_columns:bet365-snake-unknown').source_quote_series, 'B365');
    assert.equal(byGroup.get('explicit_csv_columns:pinnacle-snake-unknown').bookmaker, 'Pinnacle');
    assert.equal(byGroup.get('explicit_csv_columns:pinnacle-snake-unknown').source_quote_series, 'PS');
    assert.equal(byGroup.get('explicit_csv_columns:bet365-c-series-unknown').source_quote_series, 'B365C');
});

test('聚合列不是博彩公司；不完整列组 quarantine；全空值组不伪造 observation', async t => {
    await t.test('只有 Max/Avg 聚合列的行 quarantine 为缺少明确博彩公司列', () => {
        const result = adaptFootballDataCsv(
            'Div,Date,Time,HomeTeam,AwayTeam,MaxH,MaxD,MaxA,AvgH,AvgD,AvgA\n' +
                'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.20,3.50,3.70,2.10,3.40,3.58\n',
            { manifest: { source_timezone: 'UTC', source_match_id: null } }
        );
        assert.equal(result.observations.length, 0);
        assert.ok(result.quarantine[0].reasons.includes('bookmaker_or_market_explicit_columns_missing'));
    });

    await t.test('William Hill 缺 away 列时 quarantine 且不生成部分三元组', () => {
        const result = adaptFootballDataCsv(
            'Div,Date,Time,HomeTeam,AwayTeam,WHH,WHD\nE0,05/08/2025,19:00,Alpha FC,Beta FC,2.09,3.39\n',
            { manifest: { source_timezone: 'UTC', source_match_id: null } }
        );
        assert.equal(result.observations.length, 0);
        assert.equal(result.quarantine.length, 1);
        assert.ok(result.quarantine[0].reasons.includes('incomplete_explicit_1x2_columns'));
    });

    await t.test('列存在但整组为空时跳过，不伪造 null 赔率 observation', () => {
        const result = adaptFootballDataCsv(
            'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,BWH,BWD,BWA\n' +
                'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,,,\n',
            { manifest: { source_timezone: 'UTC', source_match_id: null } }
        );
        assert.equal(result.quarantine.length, 0);
        assert.equal(result.observations.length, 3);
        assert.ok(result.observations.every(observation => observation.bookmaker === 'Bet365'));
    });

    await t.test('部分空值组 quarantine 为 incomplete_explicit_1x2_values', () => {
        const result = adaptFootballDataCsv(
            'Div,Date,Time,HomeTeam,AwayTeam,B365CH,B365CD,B365CA\n' +
                'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.30,,3.10\n',
            { manifest: { source_timezone: 'UTC', source_match_id: null } }
        );
        assert.equal(result.observations.length, 0);
        assert.equal(result.quarantine.length, 1);
        assert.ok(result.quarantine[0].reasons.includes('incomplete_explicit_1x2_values'));
        assert.deepEqual(result.quarantine[0].evidence.present_value_selections, ['home', 'away']);
    });
});

test('adapter 版本纪律：旧 1.0.0 manifest 被明确拒绝，不静默降级', t => {
    assert.equal(ADAPTER_VERSIONS['football-data-csv'], '1.1.0');
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, {
        adapter_version: '1.0.0',
    });
    assert.throws(
        () =>
            runOfflineStaging({
                sourcePath: CSV_FIXTURE,
                manifestPath,
                adapter: 'football-data-csv',
                candidates: [],
                ingestedAt: FIXED_INGESTED_AT,
            }),
        /adapter_version 1\.0\.0 is not supported.*football-data-csv@1\.1\.0/
    );
});

const IMPLIED_PROBABILITY_REASON = 'one_x_two_implied_probability_out_of_bounds';
const REPEATED_VECTOR_FLAG = 'repeated_one_x_two_vector_across_source_matches';

function runFakeOddsRow(t, header, row) {
    const rawPath = writeRawText(t, 'fake-odds.fixture.csv', `${header}\n${row}\n`);
    const { manifestPath } = writeFixtureManifest(t, rawPath);
    return runOfflineStaging({
        sourcePath: rawPath,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: [historicalCandidates()[0]],
        ingestedAt: FIXED_INGESTED_AT,
    });
}

test('fake-odds 检测按 source_quote_series 分组：plain 与 C 并存不再静默跳过', async t => {
    const header = 'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365CH,B365CD,B365CA';

    await t.test('plain 荒谬 + C 正常：只有 plain 三条获得隐含概率 reason', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,50,50,50,2.10,3.40,3.30');
        assert.equal(result.summary.accepted_count, 3);
        assert.equal(result.summary.quarantine_count, 3);
        assert.ok(result.accepted_observations.every(observation => observation.source_quote_series === 'B365C'));
        const flagged = result.quarantine.filter(entry => entry.reasons.includes(IMPLIED_PROBABILITY_REASON));
        assert.equal(flagged.length, 3);
        assert.ok(flagged.every(entry => entry.evidence.parsed_fields.source_quote_series === 'B365'));
    });

    await t.test('plain 正常 + C 荒谬：只有 C 三条获得隐含概率 reason', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.30,50,50,50');
        assert.equal(result.summary.accepted_count, 3);
        assert.ok(result.accepted_observations.every(observation => observation.source_quote_series === 'B365'));
        const flagged = result.quarantine.filter(entry => entry.reasons.includes(IMPLIED_PROBABILITY_REASON));
        assert.equal(flagged.length, 3);
        assert.ok(flagged.every(entry => entry.evidence.parsed_fields.source_quote_series === 'B365C'));
    });

    await t.test('两个 series 都荒谬：6 条全部获得隐含概率 reason', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,50,50,50,60,60,60');
        assert.equal(result.summary.accepted_count, 0);
        const flagged = result.quarantine.filter(entry => entry.reasons.includes(IMPLIED_PROBABILITY_REASON));
        assert.equal(flagged.length, 6);
    });
});

test('uppercase 与 snake_case 同 series 重复不再禁用检测，冲突保持 fail-closed', async t => {
    const header = 'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,b365_home_odds,b365_draw_odds,b365_away_odds';

    await t.test('相同荒谬值重复：reason 保留到合并后的 primary，series 保持 B365', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,50,50,50,50,50,50');
        assert.equal(result.summary.accepted_count, 0);
        assert.equal(result.summary.semantic_duplicate_count, 3);
        const flagged = result.quarantine.filter(entry => entry.reasons.includes(IMPLIED_PROBABILITY_REASON));
        assert.equal(flagged.length, 3);
        assert.ok(flagged.every(entry => entry.evidence.parsed_fields.source_quote_series === 'B365'));
    });

    await t.test('相同正常值重复：不误伤，semantic duplicate 照旧合并', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.10,3.40,3.60');
        assert.equal(result.summary.accepted_count, 3);
        assert.equal(result.summary.semantic_duplicate_count, 3);
        assert.equal(result.summary.quarantine_count, 0);
    });

    await t.test('冲突值：不任选其一，semantic_duplicate_conflict 双方隔离', t2 => {
        const result = runFakeOddsRow(t2, header, 'E0,05/08/2025,19:00,Alpha FC,Beta FC,50,50,50,2.10,3.40,3.60');
        assert.equal(result.summary.accepted_count, 0);
        assert.equal(result.summary.semantic_conflict_count, 3);
        assert.equal(
            result.quarantine.filter(entry => entry.reasons.includes('semantic_duplicate_conflict')).length,
            6
        );
        assert.equal(result.quarantine.filter(entry => entry.reasons.includes(IMPLIED_PROBABILITY_REASON)).length, 0);
    });
});

test('跨比赛重复向量按 series 隔离；旧无 series observation 行为保持', async t => {
    const vectorObservation = (matchId, selection, odds, series) =>
        baseObservation({
            source_match_id: matchId,
            selection,
            decimal_odds: odds,
            raw_record_locator: `fixture:${matchId}:${series || 'legacy'}:${selection}`,
            ...(series ? { source_quote_series: series } : {}),
        });
    const triplet = (matchId, odds, series) =>
        ['home', 'draw', 'away'].map((selection, index) => vectorObservation(matchId, selection, odds[index], series));

    await t.test('同一 series 两场相同向量仍获得 repeated 标记', () => {
        const checked = detectFakeOdds([
            ...triplet('m1', [2.8, 3.3, 2.7], 'B365'),
            ...triplet('m2', [2.8, 3.3, 2.7], 'B365'),
        ]);
        assert.equal(checked.length, 6);
        assert.ok(checked.every(observation => observation.quality_flags.includes(REPEATED_VECTOR_FLAG)));
    });

    await t.test('不同 series 相同向量不得互相制造 repeated 标记', () => {
        const checked = detectFakeOdds([
            ...triplet('m1', [2.8, 3.3, 2.7], 'B365'),
            ...triplet('m2', [2.8, 3.3, 2.7], 'B365C'),
        ]);
        assert.ok(checked.every(observation => !observation.quality_flags.includes(REPEATED_VECTOR_FLAG)));
    });

    await t.test('相同重复项异常时 reason 传播到包括重复项在内的全部 observation', () => {
        const checked = detectFakeOdds([
            ...triplet('m1', [50, 50, 50], 'B365'),
            ...triplet('m1', [50, 50, 50], 'B365'),
        ]);
        assert.equal(checked.length, 6);
        assert.ok(checked.every(observation => observation.quarantine_reasons.includes(IMPLIED_PROBABILITY_REASON)));
    });

    await t.test('旧无 series observation：隐含概率与 repeated 检测均保持，不注入新字段', () => {
        const absurd = detectFakeOdds(triplet('m1', [50, 50, 50], null));
        assert.ok(absurd.every(observation => observation.quarantine_reasons.includes(IMPLIED_PROBABILITY_REASON)));
        const repeated = detectFakeOdds([
            ...triplet('m1', [2.8, 3.3, 2.7], null),
            ...triplet('m2', [2.8, 3.3, 2.7], null),
        ]);
        assert.ok(repeated.every(observation => observation.quality_flags.includes(REPEATED_VECTOR_FLAG)));
        assert.ok(
            [...absurd, ...repeated].every(
                observation => !Object.prototype.hasOwnProperty.call(observation, 'source_quote_series')
            )
        );
    });
});
