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
    isStrictAbsoluteTimestamp,
} = require('../../src/infrastructure/odds_staging/contracts');
const {
    adaptFootballDataCsv,
    adaptOddsPortalExplicitEnvelopeHtml,
} = require('../../src/infrastructure/odds_staging/adapters');
const { deduplicateObservations } = require('../../src/infrastructure/odds_staging/deduplication');
const { decideMatchLink } = require('../../src/infrastructure/odds_staging/matchLinker');
const { emitDeterministicResult, runOfflineStaging } = require('../../src/infrastructure/odds_staging/pipeline');
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
                : 'fixture://oddsportal-explicit-envelope/fixture-html-001',
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

function candidates(sourceMatchId, id = 'local-match-001', sourceProvider) {
    const resolvedProvider =
        sourceProvider || (sourceMatchId === 'fixture-html-001' ? 'oddsportal-fixture' : 'football-data-fixture');
    return [
        {
            id,
            source_provider: resolvedProvider,
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

function matchingCandidate(observation, overrides = {}) {
    return {
        id: 'candidate-stable-001',
        source_provider: observation.source_provider,
        source_match_id: observation.source_match_id,
        competition: observation.competition,
        season: observation.season,
        kickoff_at: observation.kickoff_at,
        home_team: observation.home_team,
        away_team: observation.away_team,
        ...overrides,
    };
}

function writeRawText(t, filename, content) {
    const rawPath = path.join(createTempDirectory(t), filename);
    fs.writeFileSync(rawPath, content, 'utf8');
    return rawPath;
}

const CSV_HEADER = 'SourceMatchId,Competition,Season,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A';
const csvRow = (sourceMatchId, homeOdds, drawOdds, awayOdds) =>
    `${sourceMatchId},Fixture League,2025/2026,01/08/2025,18:00,Alpha FC,Beta FC,${homeOdds},${drawOdds},${awayOdds}`;
function matchObservations({ odds = [2.1, 3.4, 3.3], rawMarker = 'a', ...overrides } = {}) {
    return ['home', 'draw', 'away'].map((selection, index) =>
        baseObservation({
            ...overrides,
            source_match_id: overrides.source_match_id ?? null,
            selection,
            decimal_odds: odds[index],
            raw_sha256: rawMarker.repeat(64),
            raw_record_locator: `fixture:${rawMarker}:${selection}`,
        })
    );
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
    const before = sha256File(CSV_FIXTURE);
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
    assert.equal(sha256File(CSV_FIXTURE), before);
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
    const { manifestPath } = writeFixtureManifest(t, HTML_FIXTURE, 'oddsportal-explicit-envelope-html');
    const accepted = runOfflineStaging({
        sourcePath: HTML_FIXTURE,
        manifestPath,
        adapter: 'oddsportal-explicit-envelope-html',
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
        '<script type="application/json" data-odds-staging="explicit">{"schema_version":"oddsportal-explicit-envelope-html/v1","match":{"source_match_id":"fixture-html-002"},"triplet":[2.1,3.2,3.4]}</script>',
        'utf8'
    );
    const genericManifest = writeFixtureManifest(t, rawPath, 'oddsportal-explicit-envelope-html');
    const quarantined = runOfflineStaging({
        sourcePath: rawPath,
        manifestPath: genericManifest.manifestPath,
        adapter: 'oddsportal-explicit-envelope-html',
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

test('semantic duplicate identity 对 source ID、fallback 与 unresolved raw 身份保持隔离', async t => {
    const identities = {
        source: { source_match_id: 'complete-key' },
        one: { competition: 'League One' },
        two: {
            competition: 'League Two',
            kickoff_at: '2025-08-02T18:00:00Z',
            home_team: 'Gamma FC',
            away_team: 'Delta FC',
        },
        unresolved: { competition: null, kickoff_at: null, home_team: null, away_team: null },
    };
    const scenarios = [
        ['provider/source ID: 相同赔率', 'source', 'source', false, [3, 0, 3, 0]],
        ['provider/source ID: 不同赔率', 'source', 'source', true, [0, 6, 0, 3]],
        ['无 source ID: 不同 fallback、不同赔率', 'one', 'two', true, [6, 0, 0, 0]],
        ['无 source ID: 不同 fallback、相同赔率', 'one', 'two', false, [6, 0, 0, 0]],
        ['无 source ID: 同一 fallback、相同赔率', 'one', 'one', false, [3, 0, 3, 0]],
        ['无 source ID: 同一 fallback、不同赔率', 'one', 'one', true, [0, 6, 0, 3]],
        ['无 source ID: 仅 season 不同', 'one', 'one', 'season', [6, 0, 0, 0]],
        ['身份不足: 不同 raw record', 'unresolved', 'unresolved', false, [6, 0, 0, 0]],
    ];
    for (const [name, left, right, change, expected] of scenarios) {
        await t.test(name, () => {
            const rightInput = {
                ...identities[right],
                rawMarker: 'b',
                ...(change === true ? { odds: [2.2, 3.5, 3.4] } : {}),
                ...(change === 'season' ? { season: '2026/2027' } : {}),
            };
            const result = deduplicateObservations([
                ...matchObservations({ ...identities[left], rawMarker: 'a' }),
                ...matchObservations(rightInput),
            ]);
            const quarantined = result.observations.filter(entry => entry.quarantine_reasons.length).length;
            assert.equal(result.observations.length - quarantined, expected[0]);
            assert.equal(quarantined, expected[1]);
            assert.equal(result.semantic_duplicate_count, expected[2]);
            assert.equal(result.semantic_conflict_count, expected[3]);
        });
    }
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

test('严格绝对时间接受 Z 和正负数值 offset', () => {
    for (const value of [
        '2026-07-16T18:00:00Z',
        '2026-07-16T18:00:00.123Z',
        '2026-07-16T18:00:00+08:00',
        '2026-07-16T18:00:00.123-05:00',
    ]) {
        assert.equal(isStrictAbsoluteTimestamp(value), true);
    }
});

test('严格绝对时间拒绝 naive 或非法日期，并隔离 observation 时间语义', t => {
    for (const value of ['2026-07-16T18:00:00', '2026-07-16 18:00:00', '2026-07-16', '2026-02-30T18:00:00Z']) {
        assert.equal(isStrictAbsoluteTimestamp(value), false);
    }

    const { manifest } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    assert.equal(validateSourceManifest({ ...manifest, captured_at: '2026-07-16T18:00:00' }).valid, false);
    for (const [field, reason] of [
        ['kickoff_at', 'kickoff_at_invalid'],
        ['source_observed_at', 'source_observed_at_invalid'],
        ['captured_at', 'captured_at_invalid'],
    ]) {
        const validated = validateObservation(baseObservation({ [field]: '2026-07-16T18:00:00' }));
        assert.ok(validated.quarantine_reasons.includes(reason));
    }
});

test('CSV source match ID 只在 manifest 与原始行不冲突时解析为 observation', () => {
    const rawText = fs.readFileSync(CSV_FIXTURE, 'utf8');
    const context = { manifest: { source_timezone: 'UTC', source_match_id: 'fixture-fd-001' } };
    const equal = adaptFootballDataCsv(rawText, context);
    assert.equal(equal.quarantine.length, 0);
    assert.ok(equal.observations.every(observation => observation.source_match_id === 'fixture-fd-001'));

    const manifestMissing = adaptFootballDataCsv(rawText, {
        manifest: { source_timezone: 'UTC', source_match_id: null },
    });
    assert.ok(manifestMissing.observations.every(observation => observation.source_match_id === 'fixture-fd-001'));

    const rawMissing = adaptFootballDataCsv(rawText.replace('fixture-fd-001', ''), context);
    assert.ok(rawMissing.observations.every(observation => observation.source_match_id === 'fixture-fd-001'));

    const bothMissing = adaptFootballDataCsv(rawText.replace('fixture-fd-001', ''), {
        manifest: { source_timezone: 'UTC', source_match_id: null },
    });
    assert.ok(bothMissing.observations.every(observation => observation.source_match_id === null));

    const conflict = adaptFootballDataCsv(rawText, {
        manifest: { source_timezone: 'UTC', source_match_id: 'manifest-match-999' },
    });
    assert.equal(conflict.observations.length, 0);
    assert.equal(conflict.quarantine.length, 1);
    assert.ok(conflict.quarantine[0].reasons.includes('manifest_source_match_id_conflict'));
    assert.deepEqual(conflict.quarantine[0].evidence, {
        manifest_source_match_id: 'manifest-match-999',
        raw_source_match_id: 'fixture-fd-001',
        row_number: 2,
    });
});

test('CSV header 在行转换前 fail-closed，唯一 header 保持解析行为', async t => {
    const prefix = 'SourceMatchId,Competition,Season,KickoffAt,';
    const standardRow =
        'fixture-fd-001,Fixture League,2025/2026,2025-08-01T18:00:00Z,Alpha FC,Beta FC,2.10,2.20,3.40,3.30';
    const scenarios = [
        [
            '重复 B365H',
            'HomeTeam,AwayTeam,B365H,B365H,B365D,B365A',
            standardRow,
            { canonical_name: 'b365h', positions: [7, 8], declared_names: ['B365H', 'B365H'] },
        ],
        [
            '重复 HomeTeam',
            'HomeTeam,HomeTeam,AwayTeam,B365H,B365D,B365A',
            'fixture-fd-001,Fixture League,2025/2026,2025-08-01T18:00:00Z,Alpha FC,Altered Alpha,Beta FC,2.10,3.40,3.30',
            { canonical_name: 'hometeam', positions: [5, 6], declared_names: ['HomeTeam', 'HomeTeam'] },
        ],
        [
            '大小写/空白重复 B365H',
            'HomeTeam,AwayTeam,B365H, b365h,B365D,B365A',
            standardRow,
            { canonical_name: 'b365h', positions: [7, 8], declared_names: ['B365H', ' b365h'] },
        ],
        [
            '空 header',
            'HomeTeam,AwayTeam,,B365H,B365D,B365A',
            'fixture-fd-001,Fixture League,2025/2026,2025-08-01T18:00:00Z,Alpha FC,Beta FC,ignored,2.10,3.40,3.30',
            [7],
        ],
    ];
    for (const [name, suffix, row, expected] of scenarios) {
        await t.test(name, () => {
            const result = adaptFootballDataCsv(`${prefix}${suffix}\n${row}\n`, {
                manifest: { source_timezone: 'UTC' },
            });
            const evidence = result.quarantine[0].evidence;
            const reason = Array.isArray(expected) ? 'csv_empty_header' : 'csv_duplicate_header';
            assert.equal(result.observations.length, 0);
            assert.equal(result.quarantine.length, 1);
            assert.ok(result.quarantine[0].reasons.includes(reason));
            assert.equal(evidence.header_count, 10);
            assert.deepEqual(
                reason === 'csv_duplicate_header' ? evidence.duplicate_headers[0] : evidence.empty_header_positions,
                expected
            );
        });
    }
    await t.test('唯一且明确的 CSV header 保持既有解析行为', () => {
        const result = adaptFootballDataCsv(`${CSV_HEADER}\n${csvRow('fixture-fd-001', 2.1, 3.4, 3.3)}\n`, {
            manifest: { source_timezone: 'UTC', source_match_id: null },
        });
        assert.equal(result.quarantine.length, 0);
        assert.equal(result.observations.length, 3);
        assert.equal(result.observations.find(observation => observation.selection === 'home').decimal_odds, 2.1);
    });
});

test('HTML adapter 只接受 explicit JSON envelope，并将非对象 payload 明确 quarantine', () => {
    const ordinary = adaptOddsPortalExplicitEnvelopeHtml('<html><body>2.10 3.40 3.30</body></html>');
    assert.equal(ordinary.observations.length, 0);
    assert.ok(ordinary.quarantine[0].reasons.includes('explicit_html_evidence_payload_missing'));

    for (const payload of ['null', '[]', '"text"']) {
        const result = adaptOddsPortalExplicitEnvelopeHtml(
            '<script data-odds-staging="explicit">' + payload + '</script>'
        );
        assert.equal(result.observations.length, 0);
        assert.ok(result.quarantine[0].reasons.includes('explicit_html_payload_not_object'));
    }

    const missingSchema = adaptOddsPortalExplicitEnvelopeHtml(
        '<script data-odds-staging="explicit">{"observations":[]}</script>'
    );
    assert.ok(missingSchema.quarantine[0].reasons.includes('explicit_html_schema_version_unsupported'));
    const legal = adaptOddsPortalExplicitEnvelopeHtml(fs.readFileSync(HTML_FIXTURE, 'utf8'));
    assert.equal(legal.quarantine.length, 0);
    assert.equal(legal.observations.length, 3);
});

test('合理重复 1X2 向量默认仅作质量标记，独立概率异常仍 quarantine', t => {
    const normalRaw = writeRawText(
        t,
        'normal-repeated.fixture.csv',
        [CSV_HEADER, csvRow('normal-one', 2.1, 3.4, 3.3), csvRow('normal-two', 2.1, 3.4, 3.3)].join('\n') + '\n'
    );
    const { manifestPath: normalManifest } = writeFixtureManifest(t, normalRaw, 'football-data-csv');
    const normal = runOfflineStaging({
        sourcePath: normalRaw,
        manifestPath: normalManifest,
        adapter: 'football-data-csv',
        candidates: [...candidates('normal-one'), ...candidates('normal-two')],
        ingestedAt: FIXED_INGESTED_AT,
    });
    assert.equal(normal.summary.accepted_count, 6);
    assert.equal(normal.summary.quarantine_count, 0);
    assert.ok(
        normal.accepted_observations.every(observation =>
            observation.quality_flags.includes('repeated_one_x_two_vector_across_source_matches')
        )
    );

    const abnormalRaw = writeRawText(
        t,
        'abnormal-repeated.fixture.csv',
        [CSV_HEADER, csvRow('abnormal-one', 10, 11, 13), csvRow('abnormal-two', 10, 11, 13)].join('\n') + '\n'
    );
    const { manifestPath: abnormalManifest } = writeFixtureManifest(t, abnormalRaw, 'football-data-csv');
    const abnormal = runOfflineStaging({
        sourcePath: abnormalRaw,
        manifestPath: abnormalManifest,
        adapter: 'football-data-csv',
        candidates: [...candidates('abnormal-one'), ...candidates('abnormal-two')],
        ingestedAt: FIXED_INGESTED_AT,
    });
    assert.equal(abnormal.summary.accepted_count, 0);
    assert.equal(abnormal.summary.quarantine_count, 6);
    assert.ok(
        abnormal.quarantine.every(entry => entry.reasons.includes('one_x_two_implied_probability_out_of_bounds'))
    );

    const singleRaw = writeRawText(
        t,
        'abnormal-single.fixture.csv',
        [CSV_HEADER, csvRow('abnormal-single', 10, 11, 13)].join('\n') + '\n'
    );
    const { manifestPath: singleManifest } = writeFixtureManifest(t, singleRaw, 'football-data-csv');
    const single = runOfflineStaging({
        sourcePath: singleRaw,
        manifestPath: singleManifest,
        adapter: 'football-data-csv',
        candidates: candidates('abnormal-single'),
        ingestedAt: FIXED_INGESTED_AT,
    });
    assert.equal(single.summary.quarantine_count, 3);
    assert.ok(single.quarantine.every(entry => entry.reasons.includes('one_x_two_implied_probability_out_of_bounds')));
});

test('显式严格重复向量配置才会将合理重复向量送入 quarantine', t => {
    const rawPath = writeRawText(
        t,
        'normal-repeated-strict.fixture.csv',
        [CSV_HEADER, csvRow('strict-one', 2.1, 3.4, 3.3), csvRow('strict-two', 2.1, 3.4, 3.3)].join('\n') + '\n'
    );
    const { manifestPath } = writeFixtureManifest(t, rawPath, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: rawPath,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: [...candidates('strict-one'), ...candidates('strict-two')],
        ingestedAt: FIXED_INGESTED_AT,
        fakeOddsConfig: { quarantine_repeated_vectors: true },
    });
    assert.equal(result.summary.accepted_count, 0);
    assert.equal(result.summary.quarantine_count, 6);
    assert.ok(
        result.quarantine.every(entry => entry.reasons.includes('repeated_one_x_two_vector_across_source_matches'))
    );
});

test('source ID 仅在 provider 一致且身份字段不冲突时可直接 matched', () => {
    const observation = baseObservation();
    const direct = decideMatchLink(observation, [matchingCandidate(observation)]);
    assert.equal(direct.status, 'matched');
    assert.equal(direct.method, 'source_match_id');

    const providerMismatch = decideMatchLink(observation, [
        matchingCandidate(observation, { source_provider: 'other-provider' }),
    ]);
    assert.equal(providerMismatch.status, 'matched');
    assert.equal(providerMismatch.method, 'exact_home_away_kickoff');

    for (const [field, value] of [
        ['home_team', 'Wrong Home'],
        ['kickoff_at', '2025-08-01T19:00:00Z'],
        ['competition', 'Other League'],
        ['season', '2024/2025'],
    ]) {
        const conflict = decideMatchLink(observation, [matchingCandidate(observation, { [field]: value })]);
        assert.equal(conflict.status, 'ambiguous');
        assert.equal(conflict.method, 'source_match_id_identity_conflict');
        assert.ok(conflict.evidence.identity.conflicts.some(entry => entry.field === field));
    }
});

test('exact identity、reverse identity、多个候选和缺失稳定 ID 均保留安全决策', () => {
    const observation = baseObservation({ source_match_id: null });
    const exact = decideMatchLink(observation, [matchingCandidate(observation, { source_match_id: null })]);
    assert.equal(exact.status, 'matched');
    assert.equal(exact.method, 'exact_home_away_kickoff');

    const idless = matchingCandidate(baseObservation());
    delete idless.id;
    const idlessDecision = decideMatchLink(baseObservation(), [idless]);
    assert.equal(idlessDecision.status, 'ambiguous');
    assert.equal(idlessDecision.method, 'candidate_stable_id_missing');
    assert.equal(idlessDecision.matched_id, null);
    assert.deepEqual(idlessDecision.candidate_ids, []);

    const reversed = decideMatchLink(observation, [
        matchingCandidate(observation, {
            source_match_id: null,
            home_team: 'Beta FC',
            away_team: 'Alpha FC',
        }),
    ]);
    assert.equal(reversed.status, 'ambiguous');
    assert.equal(reversed.method, 'candidate_identity_conflict');

    const multiple = decideMatchLink(baseObservation(), [
        matchingCandidate(baseObservation(), { id: 'candidate-a' }),
        matchingCandidate(baseObservation(), { id: 'candidate-b' }),
    ]);
    assert.equal(multiple.status, 'ambiguous');
    assert.equal(multiple.method, 'source_match_id_multiple_candidates');
});

test('semantic conflict quarantine 保留 bookmaker、赔率、snapshot 和重复证据', t => {
    const rawPath = writeRawText(
        t,
        'semantic-conflict.fixture.csv',
        [CSV_HEADER, csvRow('semantic-conflict', 2.1, 3.4, 3.3), csvRow('semantic-conflict', 2.2, 3.4, 3.3)].join(
            '\n'
        ) + '\n'
    );
    const { manifestPath } = writeFixtureManifest(t, rawPath, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: rawPath,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('semantic-conflict'),
        ingestedAt: FIXED_INGESTED_AT,
    });
    const conflictEntries = result.quarantine.filter(entry => entry.reasons.includes('semantic_duplicate_conflict'));
    assert.equal(conflictEntries.length, 2);
    for (const entry of conflictEntries) {
        assert.equal(entry.evidence.parsed_fields.bookmaker, 'Bet365');
        assert.equal(entry.evidence.parsed_fields.snapshot_type, 'unknown');
        assert.ok([2.1, 2.2].includes(entry.evidence.parsed_fields.decimal_odds));
        assert.deepEqual(entry.evidence.duplicate_evidence.semantic_conflict.decimal_odds_values, ['2.1', '2.2']);
        assert.ok(entry.raw_record_locator);
    }
});

test('emit 写入失败会回滚临时文件和已完成输出，但保留既有无关文件', t => {
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('fixture-fd-001'),
        ingestedAt: FIXED_INGESTED_AT,
    });
    const emitDirectory = createTempDirectory(t);
    fs.writeFileSync(path.join(emitDirectory, 'keep.txt'), 'keep', 'utf8');
    let writeCount = 0;
    const fileSystem = Object.create(fs);
    fileSystem.writeFileSync = (...args) => {
        writeCount += 1;
        if (writeCount === 2) {
            throw new Error('injected write failure');
        }
        return fs.writeFileSync(...args);
    };

    assert.throws(
        () =>
            emitDeterministicResult(
                result,
                emitDirectory,
                { repositoryRoot: PROJECT_ROOT, temporaryToken: 'write-failure' },
                fileSystem
            ),
        /rolled back/
    );
    assert.deepEqual(fs.readdirSync(emitDirectory).sort(), ['keep.txt']);
});

test('emit rename 失败会删除本次已 rename 的最终文件和临时文件', t => {
    const { manifestPath } = writeFixtureManifest(t, CSV_FIXTURE, 'football-data-csv');
    const result = runOfflineStaging({
        sourcePath: CSV_FIXTURE,
        manifestPath,
        adapter: 'football-data-csv',
        candidates: candidates('fixture-fd-001'),
        ingestedAt: FIXED_INGESTED_AT,
    });
    const emitDirectory = createTempDirectory(t);
    fs.writeFileSync(path.join(emitDirectory, 'keep.txt'), 'keep', 'utf8');
    let renameCount = 0;
    const fileSystem = Object.create(fs);
    fileSystem.renameSync = (...args) => {
        renameCount += 1;
        if (renameCount === 2) {
            throw new Error('injected rename failure');
        }
        return fs.renameSync(...args);
    };

    assert.throws(
        () =>
            emitDeterministicResult(
                result,
                emitDirectory,
                { repositoryRoot: PROJECT_ROOT, temporaryToken: 'rename-failure' },
                fileSystem
            ),
        /rolled back/
    );
    assert.deepEqual(fs.readdirSync(emitDirectory).sort(), ['keep.txt']);
});
