'use strict';

// lifecycle: permanent；验证离线赔率 staging 的来源、语义、去重、关联和隔离行为。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { matchesForbiddenImport } = require('../helpers/module_load_guard');
const {
    appendObservationSignals,
    createCanonicalObservation,
    stableStringify,
} = require('../../src/infrastructure/odds_staging/contracts');
const { deduplicateObservations } = require('../../src/infrastructure/odds_staging/deduplication');
const { detectFakeOdds } = require('../../src/infrastructure/odds_staging/fakeOddsDetector');
const { decideMatchLink } = require('../../src/infrastructure/odds_staging/matchLinker');
const { runOfflineStaging } = require('../../src/infrastructure/odds_staging/pipeline');
const { loadSourceBundle, validateSourceManifest } = require('../../src/infrastructure/odds_staging/sourceManifest');
const { validateObservation } = require('../../src/infrastructure/odds_staging/validators');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const STAGING_ROOT = path.join(PROJECT_ROOT, 'src/infrastructure/odds_staging');
const CSV_FIXTURE = path.join(PROJECT_ROOT, 'tests/fixtures/odds_staging/football_data_explicit.fixture.csv');
const HTML_FIXTURE = path.join(PROJECT_ROOT, 'tests/fixtures/odds_staging/oddsportal_explicit.fixture.html');
const FIXED_INGESTED_AT = '2026-07-16T00:00:00.000Z';

function sha256File(filePath) {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function createTempDirectory(t) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-odds-staging-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return directory;
}

function writeFixtureManifest(t, rawPath, adapter, overrides = {}) {
    const directory = createTempDirectory(t);
    const manifestPath = path.join(directory, 'source-manifest.fixture.json');
    const rawBuffer = fs.readFileSync(rawPath);
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: adapter === 'football-data-csv' ? 'football-data-fixture' : 'oddsportal-fixture',
        acquisition_mode: 'fixture',
        source_url:
            adapter === 'football-data-csv'
                ? 'fixture://football-data/fixture-fd-001'
                : 'fixture://oddsportal-explicit/fixture-html-001',
        source_match_id: null,
        captured_at: '2025-08-01T10:00:00Z',
        source_timezone: 'UTC',
        raw_path: rawPath,
        raw_media_type: adapter === 'football-data-csv' ? 'text/csv' : 'text/html',
        raw_size_bytes: rawBuffer.length,
        raw_sha256: sha256File(rawPath),
        adapter,
        adapter_version: '1.0.0',
        provenance_status: 'fixture',
        ...overrides,
    };
    fs.writeFileSync(manifestPath, `${JSON.stringify(manifest)}\n`, 'utf8');
    return { manifest, manifestPath };
}

function candidates(sourceMatchId, id = 'local-match-001') {
    return [
        {
            id,
            source_match_id: sourceMatchId,
            competition: 'Fixture League',
            season: '2025/2026',
            kickoff_at: sourceMatchId === 'fixture-html-001' ? '2025-08-02T18:00:00Z' : '2025-08-01T18:00:00Z',
            home_team: sourceMatchId === 'fixture-html-001' ? 'Gamma FC' : 'Alpha FC',
            away_team: sourceMatchId === 'fixture-html-001' ? 'Delta FC' : 'Beta FC',
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
        adapter_version: '1.0.0',
        extraction_method: 'explicit_fixture_field',
        provenance_status: 'fixture',
        ingested_at: FIXED_INGESTED_AT,
        ...overrides,
    });
}

test('离线 staging 模块加载不引入网络、浏览器、数据库或写入副作用', t => {
    const originalLoad = Module._load;
    const originalWriteFileSync = fs.writeFileSync;
    const originalMkdirSync = fs.mkdirSync;
    // 拆分 package 名称，避免测试自身被网络调用静态扫描误判为调用点。
    const networkClientPackage = ['ax', 'ios'].join('');
    const forbidden = [
        new RegExp(`^(?:playwright|pg|dotenv|${networkClientPackage}|node:http|node:https|http|https)$`),
        /OddsPortalHarvester|odds_harvest_pipeline|odds_sniper|gold_pilot/,
    ];
    t.after(() => {
        Module._load = originalLoad;
        fs.writeFileSync = originalWriteFileSync;
        fs.mkdirSync = originalMkdirSync;
    });

    Module._load = function guardedLoad(request, parent, isMain) {
        if (forbidden.some(pattern => matchesForbiddenImport(request, PROJECT_ROOT, pattern))) {
            throw new Error(`forbidden dependency requested: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    fs.writeFileSync = () => {
        throw new Error('module load must not write files');
    };
    fs.mkdirSync = () => {
        throw new Error('module load must not create directories');
    };

    for (const filename of fs.readdirSync(STAGING_ROOT)) {
        if (filename.endsWith('.js')) {
            delete require.cache[path.join(STAGING_ROOT, filename)];
        }
    }
    const loaded = require('../../src/infrastructure/odds_staging/pipeline');
    assert.equal(typeof loaded.runOfflineStaging, 'function');
});

test('manifest 只接受本地绝对路径并校验真实 SHA-256 与大小', t => {
    const { manifest, manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const bundle = loadSourceBundle({ manifestPath, sourcePath: CSV_FIXTURE });

    assert.equal(bundle.manifest.raw_sha256, sha256File(CSV_FIXTURE));
    assert.equal(bundle.manifest.raw_size_bytes, fs.statSync(CSV_FIXTURE).size);
    assert.equal(bundle.manifest.provenance_status, 'fixture');
    assert.equal(validateSourceManifest({ ...manifest, raw_path: 'https://example.invalid/input.csv' }).valid, false);
    assert.throws(
        () => loadSourceBundle({ manifestPath, sourcePath: 'https://example.invalid/input.csv' }),
        /local path, not a network URL/
    );
    assert.throws(
        () =>
            loadSourceBundle(
                { manifestPath, sourcePath: CSV_FIXTURE },
                {
                    fileSystem: {
                        ...fs,
                        readFileSync: filePath => {
                            if (filePath === CSV_FIXTURE) {
                                return Buffer.from('altered');
                            }
                            return fs.readFileSync(filePath);
                        },
                    },
                }
            ),
        /raw_size_bytes|raw_sha256/
    );
});

test('Football-Data CSV 只从明确列展开 selection，且不把 captured_at 冒充来源时间', t => {
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('fixture-fd-001'),
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(result.summary.accepted_count, 9);
    assert.equal(result.summary.quarantine_count, 0);
    assert.deepEqual([...new Set(result.accepted_observations.map(observation => observation.bookmaker))].sort(), [
        'Bet365',
        'Pinnacle',
    ]);
    assert.ok(result.accepted_observations.every(observation => observation.market === '1X2'));
    assert.ok(result.accepted_observations.every(observation => observation.source_observed_at === null));
    assert.ok(result.accepted_observations.every(observation => observation.captured_at === '2025-08-01T10:00:00Z'));
    assert.ok(result.accepted_observations.every(observation => observation.match_link.status === 'matched'));
    assert.ok(result.accepted_observations.some(observation => observation.snapshot_type === 'opening'));
    assert.ok(result.accepted_observations.some(observation => observation.snapshot_type === 'unknown'));
});

test('同一固定输入输出稳定，且源文件保持字节不变', t => {
    const before = sha256File(CSV_FIXTURE);
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const options = {
        sourcePath: CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('fixture-fd-001'),
        ingestedAt: FIXED_INGESTED_AT,
    };
    const first = runOfflineStaging(options);
    const second = runOfflineStaging(options);

    assert.equal(sha256File(CSV_FIXTURE), before);
    assert.equal(stableStringify(first), stableStringify(second));
    assert.deepEqual(
        first.accepted_observations.map(observation => observation.idempotency_key),
        second.accepted_observations.map(observation => observation.idempotency_key)
    );
});

test('缺少明确 bookmaker 或 market 列时必须 quarantine，不降低标准', t => {
    const directory = createTempDirectory(t);
    const rawPath = path.join(directory, 'missing-columns.fixture.csv');
    fs.writeFileSync(
        rawPath,
        'SourceMatchId,Competition,Season,Date,Time,HomeTeam,AwayTeam\nfixture-fd-002,Fixture League,2025/2026,01/08/2025,18:00,Alpha FC,Beta FC\n',
        'utf8'
    );
    const { manifestPath } = writeFixtureManifest(t, rawPath, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: rawPath,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('fixture-fd-002'),
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(result.summary.accepted_count, 0);
    assert.equal(result.summary.quarantine_count, 1);
    assert.ok(result.quarantine[0].reasons.includes('bookmaker_or_market_explicit_columns_missing'));
    assert.equal(result.quarantine[0].raw_sha256, sha256File(rawPath));
    assert.equal(result.quarantine[0].raw_record_locator, 'csv:row=2');
});

test('explicit HTML envelope 保留标签语义；generic triplet 不会被赋予 Pinnacle', t => {
    const { manifestPath } = writeFixtureManifest(t, HTML_FIXTURE, 'oddsportal-explicit-html');
    const accepted = runOfflineStaging({
        sourcePath: HTML_FIXTURE,
        manifestPath,
        adapter: 'oddsportal-explicit-html',
        candidates: candidates('fixture-html-001'),
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(accepted.summary.accepted_count, 3);
    assert.ok(accepted.accepted_observations.every(observation => observation.bookmaker === 'Fixture Book'));
    assert.ok(accepted.accepted_observations.every(observation => observation.snapshot_type === 'opening'));
    assert.ok(
        accepted.accepted_observations.every(observation => observation.source_observed_at === '2025-08-01T09:00:00Z')
    );

    const directory = createTempDirectory(t);
    const rawPath = path.join(directory, 'generic-triplet.fixture.html');
    fs.writeFileSync(
        rawPath,
        '<script type="application/json" data-odds-staging="explicit">{"schema_version":"oddsportal-explicit-html/v1","match":{"source_match_id":"fixture-html-002"},"triplet":[2.1,3.2,3.4]}</script>',
        'utf8'
    );
    const genericManifest = writeFixtureManifest(t, rawPath, 'oddsportal-explicit-html');
    const quarantined = runOfflineStaging({
        sourcePath: rawPath,
        manifestPath: genericManifest.manifestPath,
        adapter: 'oddsportal-explicit-html',
        candidates: candidates('fixture-html-002'),
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(quarantined.summary.accepted_count, 0);
    assert.ok(quarantined.quarantine[0].reasons.includes('generic_triplet_without_explicit_bookmaker'));
    assert.equal(
        quarantined.quarantine.some(entry => entry.evidence?.bookmaker === 'Pinnacle'),
        false
    );
});

test('验证器拒绝非法赔率、缺失字段和顺序推断，并保留未知来源时间', () => {
    const invalid = validateObservation(
        baseObservation({
            bookmaker: null,
            market: null,
            decimal_odds: 1,
            snapshot_type: 'opening',
            extraction_method: 'record_order_first',
            source_observed_at: null,
        })
    );

    assert.ok(invalid.quarantine_reasons.includes('bookmaker_missing_or_ambiguous'));
    assert.ok(invalid.quarantine_reasons.includes('market_missing_or_unsupported'));
    assert.ok(invalid.quarantine_reasons.includes('decimal_odds_invalid'));
    assert.ok(invalid.quarantine_reasons.includes('snapshot_order_inference_prohibited'));
    assert.equal(invalid.source_observed_at, null);
    assert.ok(invalid.quality_flags.includes('snapshot_source_time_unknown'));
});

test('假赔率检测识别异常概率和与跨比赛重复完整1X2向量', () => {
    const abnormal = ['home', 'draw', 'away'].map((selection, index) =>
        baseObservation({
            selection,
            decimal_odds: [10, 11, 13][index],
            raw_record_locator: `abnormal:${selection}`,
        })
    );
    const repeated = ['fixture-match-2', 'fixture-match-3'].flatMap(matchId =>
        ['home', 'draw', 'away'].map((selection, index) =>
            baseObservation({
                source_match_id: matchId,
                selection,
                decimal_odds: [2.1, 3.2, 3.4][index],
                raw_sha256: matchId.endsWith('2') ? 'b'.repeat(64) : 'c'.repeat(64),
                raw_record_locator: `${matchId}:${selection}`,
            })
        )
    );
    const detected = detectFakeOdds([...abnormal, ...repeated]);

    assert.ok(
        detected
            .slice(0, 3)
            .every(entry => entry.quarantine_reasons.includes('one_x_two_implied_probability_out_of_bounds'))
    );
    assert.ok(
        detected
            .slice(3)
            .every(entry => entry.quarantine_reasons.includes('repeated_one_x_two_vector_across_source_matches'))
    );
});

test('exact duplicate 稳定合并，semantic conflict 必须 quarantine', () => {
    const exact = baseObservation();
    const exactResult = deduplicateObservations([exact, { ...exact }]);
    assert.equal(exactResult.observations.length, 1);
    assert.equal(exactResult.exact_duplicate_count, 1);
    assert.equal(exactResult.observations[0].duplicate_evidence.exact_duplicates.length, 1);

    const semanticSame = baseObservation({
        raw_sha256: 'b'.repeat(64),
        raw_record_locator: 'fixture:record=2',
    });
    const semanticResult = deduplicateObservations([exact, semanticSame]);
    assert.equal(semanticResult.observations.length, 1);
    assert.equal(semanticResult.semantic_duplicate_count, 1);
    assert.equal(semanticResult.observations[0].duplicate_evidence.semantic_duplicates.length, 1);

    const conflict = baseObservation({
        raw_sha256: 'c'.repeat(64),
        raw_record_locator: 'fixture:record=3',
        decimal_odds: 2.3,
    });
    const conflictResult = deduplicateObservations([exact, conflict]);
    assert.equal(conflictResult.semantic_conflict_count, 1);
    assert.ok(
        conflictResult.observations.every(entry => entry.quarantine_reasons.includes('semantic_duplicate_conflict'))
    );
});

test('match linker 只接受唯一确定候选，反向或多候选都保持 ambiguous', () => {
    const observation = baseObservation();
    const direct = decideMatchLink(observation, candidates('fixture-match-1'));
    assert.equal(direct.status, 'matched');
    assert.equal(direct.method, 'source_match_id');

    const multiple = decideMatchLink(observation, [
        ...candidates('fixture-match-1', 'candidate-one'),
        ...candidates('fixture-match-1', 'candidate-two'),
    ]);
    assert.equal(multiple.status, 'ambiguous');

    const reversed = decideMatchLink({ ...observation, source_match_id: null }, [
        {
            id: 'reversed',
            competition: 'Fixture League',
            season: '2025/2026',
            kickoff_at: '2025-08-01T18:00:00Z',
            home_team: 'Beta FC',
            away_team: 'Alpha FC',
        },
    ]);
    assert.equal(reversed.status, 'ambiguous');
    assert.equal(reversed.matched_id, null);

    const unmatched = decideMatchLink({ ...observation, source_match_id: 'missing' }, []);
    assert.equal(unmatched.status, 'unmatched');
});

test('所有 observation quarantine 都保留 raw hash、locator、原因和关联证据', t => {
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: [],
        ingestedAt: FIXED_INGESTED_AT,
    });

    assert.equal(result.summary.accepted_count, 0);
    assert.ok(result.quarantine.length > 0);
    assert.ok(result.quarantine.every(entry => /^[a-f0-9]{64}$/.test(entry.raw_sha256)));
    assert.ok(result.quarantine.every(entry => entry.raw_record_locator));
    assert.ok(result.quarantine.every(entry => entry.reasons.length > 0));
    assert.ok(result.quarantine.every(entry => entry.evidence));
    assert.ok(result.quarantine.some(entry => entry.reasons.includes('match_link_unmatched')));

    const flagged = appendObservationSignals(baseObservation(), ['manual_reason']);
    assert.ok(flagged.quarantine_reasons.includes('manual_reason'));
});
