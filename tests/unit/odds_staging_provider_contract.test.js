'use strict';

// lifecycle: permanent；M3-R2 Football-Data provider temporal contract 单元测试：
// contract 模块（不可变 + 官方证据字段）、applyProviderContractToGroup 语义 overlay
// （C → closing；第一组 → first_collection_after_market_open；fail closed）、
// season 作用域、manifest provider_contract 校验、adapter overlay 端到端行为、
// validators 对非法 phase 的隔离。不写入仓库、不访问网络/数据库。

const assert = require('node:assert/strict');
const test = require('node:test');
const {
    CLOSING_PHASE,
    FIRST_COLLECTION_PHASE,
    FOOTBALL_DATA_PROVIDER_CONTRACT,
    applyProviderContractToGroup,
    isSeasonWithinProviderContract,
    parseSeasonStartYear,
} = require('../../src/infrastructure/odds_staging/footballDataProviderContract');
const { adaptFootballDataCsv } = require('../../src/infrastructure/odds_staging/adapters');
const { createCanonicalObservation } = require('../../src/infrastructure/odds_staging/contracts');
const { validateSourceManifest } = require('../../src/infrastructure/odds_staging/sourceManifest');
const { validateObservation } = require('../../src/infrastructure/odds_staging/validators');

const VALID_PROVIDER_CONTRACT_BLOCK = Object.freeze({
    contract_id: FOOTBALL_DATA_PROVIDER_CONTRACT.contract_id,
    provider_id: FOOTBALL_DATA_PROVIDER_CONTRACT.provider_id,
    applicable: true,
    effective_from_season: FOOTBALL_DATA_PROVIDER_CONTRACT.effective_from_season,
    evidence_checked_at: FOOTBALL_DATA_PROVIDER_CONTRACT.evidence_checked_at,
});

// 2-row fixture，2023/2024（在 contract 作用域与 kickoff 解释 allowed seasons 内）。
const CONTRACT_CSV = [
    'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365CH,B365CD,B365CA',
    'test-fixture,E0,05/08/2023,15:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,06/08/2023,17:30,Gamma FC,Delta FC,1.80,3.80,4.50,1.84,3.76,4.44',
].join('\n');

// 2018/2019 赛季日期 —— 在 provider contract（2019/20 起）生效之前。
const PRE_CONTRACT_CSV = [
    'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365CH,B365CD,B365CA',
    'test-fixture,E0,05/08/2018,15:00,Alpha FC,Beta FC,2.10,3.40,3.60,2.15,3.35,3.50',
].join('\n');

function contractManifest() {
    return {
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        acquisition_mode: 'historical_git_recovery',
        source_timezone: 'unknown',
        provider_contract: { ...VALID_PROVIDER_CONTRACT_BLOCK },
        kickoff_time_interpretation: {
            status: 'derived',
            timezone: 'Europe/London',
            method: 'source_local_calendar_time',
            evidence_level: 'empirical_cross_source',
            official_source_declaration: false,
            evidence_reference: 'M3-R2 provider contract unit test',
            allowed_competitions: ['Premier League'],
            allowed_seasons: ['2022/2023', '2023/2024', '2024/2025'],
        },
    };
}

function adapt(csv, manifest) {
    return adaptFootballDataCsv(csv, manifest ? { manifest } : {});
}

function seriesOf(observations, series) {
    return observations.filter(observation => observation.source_quote_series === series);
}

// ---- contract module --------------------------------------------------------

test('contract: the provider contract is frozen and carries only proven official evidence fields', t => {
    assert.ok(Object.isFrozen(FOOTBALL_DATA_PROVIDER_CONTRACT));
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.contract_id, 'football-data-provider-contract/v1');
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.provider_id, 'football-data.co.uk');
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.evidence_type, 'primary_provider_documentation');
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.effective_from_season, '2019/20');
    // Provider 措辞是 "collected after market opening"，不是 opening odds。
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.first_set_is_exact_opening_price, false);
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.closing_series_marker, 'C');
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.closing_series_semantics, 'closing');
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.closing_series_is_exact_closing_tick, false);
    // 没有任何 per-row 观察/采集时间戳（schedule 规则 ≠ 行级时间戳）。
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.exact_observation_timestamp_available, false);
    assert.equal(FOOTBALL_DATA_PROVIDER_CONTRACT.exact_capture_timestamp_available, false);
    assert.deepEqual(FOOTBALL_DATA_PROVIDER_CONTRACT.collection_phase_values, [
        FIRST_COLLECTION_PHASE,
        CLOSING_PHASE,
    ]);
    assert.deepEqual(FOOTBALL_DATA_PROVIDER_CONTRACT.pinnacle_warning.applicable_to_canonical_seasons, false);
});

test('contract: season scope starts at the official 2019/20 evidence claim', t => {
    assert.equal(parseSeasonStartYear('2019/20'), 2019);
    assert.equal(parseSeasonStartYear('2022/23'), 2022);
    assert.equal(parseSeasonStartYear('2023/2024'), 2023);
    assert.equal(parseSeasonStartYear('garbage'), null);
    assert.equal(isSeasonWithinProviderContract('2019/20'), true);
    assert.equal(isSeasonWithinProviderContract('2022/23'), true);
    assert.equal(isSeasonWithinProviderContract('2023/2024'), true);
    assert.equal(isSeasonWithinProviderContract('2018/2019'), false);
    assert.equal(isSeasonWithinProviderContract('2001/2002'), false);
    assert.equal(isSeasonWithinProviderContract(null), false);
    assert.equal(isSeasonWithinProviderContract('not-a-season'), false);
});

// ---- applyProviderContractToGroup -------------------------------------------

const GROUP_SHAPES = {
    'bet365-unknown': { id: 'bet365-unknown', bookmaker: 'Bet365', bookmaker_source_id: 'B365', source_quote_series: 'B365', snapshot_type: 'unknown' },
    'bet365-c-series-unknown': { id: 'bet365-c-series-unknown', bookmaker: 'Bet365', bookmaker_source_id: 'B365', source_quote_series: 'B365C', snapshot_type: 'unknown' },
    'bet365-snake-unknown': { id: 'bet365-snake-unknown', bookmaker: 'Bet365', bookmaker_source_id: 'B365', source_quote_series: 'B365', snapshot_type: 'unknown' },
    'bet365-opening-explicit': { id: 'bet365-opening-explicit', bookmaker: 'Bet365', bookmaker_source_id: 'B365', snapshot_type: 'opening' },
};

test('overlay: C-series groups map to closing snapshot_type + closing phase', t => {
    const overlay = applyProviderContractToGroup(GROUP_SHAPES['bet365-c-series-unknown'], {
        applicable: true,
        season: '2023/2024',
    });
    assert.deepEqual(overlay, { snapshot_type: 'closing', provider_collection_phase: CLOSING_PHASE });
});

test('overlay: plain and snake groups map to unknown snapshot_type + first_collection_after_market_open', t => {
    const plain = applyProviderContractToGroup(GROUP_SHAPES['bet365-unknown'], {
        applicable: true,
        season: '2023/2024',
    });
    assert.deepEqual(plain, { snapshot_type: 'unknown', provider_collection_phase: FIRST_COLLECTION_PHASE });
    const snake = applyProviderContractToGroup(GROUP_SHAPES['bet365-snake-unknown'], {
        applicable: true,
        season: '2023/2024',
    });
    assert.deepEqual(snake, { snapshot_type: 'unknown', provider_collection_phase: FIRST_COLLECTION_PHASE });
});

test('overlay: explicit opening/current/closing groups are never touched by the overlay', t => {
    const overlay = applyProviderContractToGroup(GROUP_SHAPES['bet365-opening-explicit'], {
        applicable: true,
        season: '2023/2024',
    });
    assert.equal(overlay, null);
});

test('overlay: applicable=false fails closed — no overlay even for C-series columns', t => {
    assert.equal(
        applyProviderContractToGroup(GROUP_SHAPES['bet365-c-series-unknown'], { applicable: false, season: '2023/2024' }),
        null
    );
    assert.equal(
        applyProviderContractToGroup(GROUP_SHAPES['bet365-c-series-unknown'], { applicable: true, season: null }),
        null
    );
});

test('overlay: seasons before the contract effective date never get the overlay', t => {
    assert.equal(
        applyProviderContractToGroup(GROUP_SHAPES['bet365-c-series-unknown'], { applicable: true, season: '2018/2019' }),
        null
    );
    assert.equal(
        applyProviderContractToGroup(GROUP_SHAPES['bet365-unknown'], { applicable: true, season: '2001/2002' }),
        null
    );
});

// ---- adapter end-to-end -----------------------------------------------------

test('adapter: with a declared provider contract C-series becomes closing and plain becomes first_collection', t => {
    const result = adapt(CONTRACT_CSV, contractManifest());
    assert.equal(result.observations.length, 12);
    const plain = seriesOf(result.observations, 'B365');
    const closing = seriesOf(result.observations, 'B365C');
    assert.equal(plain.length, 6);
    assert.equal(closing.length, 6);
    for (const observation of plain) {
        assert.equal(observation.snapshot_type, 'unknown');
        assert.equal(observation.provider_collection_phase, FIRST_COLLECTION_PHASE);
        assert.equal(observation.source_observed_at, null);
    }
    for (const observation of closing) {
        assert.equal(observation.snapshot_type, 'closing');
        assert.equal(observation.provider_collection_phase, CLOSING_PHASE);
        assert.equal(observation.source_observed_at, null);
    }
});

test('adapter: without a declared contract every series stays unknown with no phase (fail closed)', t => {
    const result = adapt(CONTRACT_CSV, null);
    assert.equal(result.observations.length, 12);
    for (const observation of result.observations) {
        assert.equal(observation.snapshot_type, 'unknown');
        assert.ok(!Object.prototype.hasOwnProperty.call(observation, 'provider_collection_phase'));
    }
});

test('adapter: a contract declared but with a pre-contract season gets no overlay', t => {
    const result = adapt(PRE_CONTRACT_CSV, contractManifest());
    assert.equal(result.observations.length, 6);
    for (const observation of result.observations) {
        assert.equal(observation.snapshot_type, 'unknown');
        assert.ok(!Object.prototype.hasOwnProperty.call(observation, 'provider_collection_phase'));
    }
});

test('adapter: a manifest with the wrong provider_id never gets the overlay', t => {
    const manifest = contractManifest();
    manifest.provider_contract = { ...VALID_PROVIDER_CONTRACT_BLOCK, provider_id: 'some-other-provider' };
    const result = adapt(CONTRACT_CSV, manifest);
    for (const observation of result.observations) {
        assert.equal(observation.snapshot_type, 'unknown');
        assert.ok(!Object.prototype.hasOwnProperty.call(observation, 'provider_collection_phase'));
    }
});

test('adapter: aggregate columns (Max*/Avg*) never produce observations even with a declared contract', t => {
    // Transformed source（real_odds_raw）的 Max/Avg 是聚合值，不是单一博彩公司报价：
    // M3-R2 不为其赋予任何 provider phase，也不产生 observation（不写死为 closing）。
    const aggregateCsv = [
        'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,MaxH,MaxD,MaxA,AvgH,AvgD,AvgA',
        'test-fixture,E0,05/08/2023,15:00,Alpha FC,Beta FC,2.20,3.50,3.70,2.10,3.40,3.58',
    ].join('\n');
    const result = adapt(aggregateCsv, contractManifest());
    assert.equal(result.observations.length, 0);
    assert.equal(result.quarantine.length, 1);
    assert.ok(result.quarantine[0].reasons.includes('bookmaker_or_market_explicit_columns_missing'));
});

// ---- manifest validation ----------------------------------------------------

test('manifest: a well-formed provider_contract block passes source manifest validation', t => {
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-csv',
        acquisition_mode: 'historical_git_recovery',
        source_url: `git+repository://x@${'a'.repeat(40)}/x.csv`,
        source_match_id: null,
        captured_at: null,
        capture_time_status: 'unknown',
        recovered_at: '2026-08-09T06:14:00Z',
        source_timezone: 'unknown',
        raw_path: '/tmp/x.csv',
        raw_media_type: 'text/csv',
        raw_size_bytes: 100,
        raw_sha256: 'a'.repeat(64),
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        provenance_status: 'declared',
        upstream_provenance_status: 'unverified',
        repository_provenance: {
            repository: 'x/p',
            commit_sha: 'a'.repeat(40),
            blob_sha: 'b'.repeat(40),
            path: 'x.csv',
            commit_timestamp: '2026-01-29T19:22:29+08:00',
        },
        provider_contract: { ...VALID_PROVIDER_CONTRACT_BLOCK },
    };
    assert.deepEqual(validateSourceManifest(manifest).errors, []);
});

test('manifest: provider_contract.applicable=false fails closed', t => {
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-csv',
        acquisition_mode: 'historical_git_recovery',
        source_url: `git+repository://x@${'a'.repeat(40)}/x.csv`,
        source_match_id: null,
        captured_at: null,
        capture_time_status: 'unknown',
        recovered_at: '2026-08-09T06:14:00Z',
        source_timezone: 'unknown',
        raw_path: '/tmp/x.csv',
        raw_media_type: 'text/csv',
        raw_size_bytes: 100,
        raw_sha256: 'a'.repeat(64),
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        provenance_status: 'declared',
        upstream_provenance_status: 'unverified',
        repository_provenance: {
            repository: 'x/p',
            commit_sha: 'a'.repeat(40),
            blob_sha: 'b'.repeat(40),
            path: 'x.csv',
            commit_timestamp: '2026-01-29T19:22:29+08:00',
        },
        provider_contract: { ...VALID_PROVIDER_CONTRACT_BLOCK, applicable: false },
    };
    const result = validateSourceManifest(manifest);
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('applicable')));
});

test('manifest: provider_contract missing required identity fields is rejected', t => {
    const manifest = {
        schema_version: 'odds-source-manifest/v1',
        source_provider: 'football-data-csv',
        acquisition_mode: 'historical_git_recovery',
        source_url: `git+repository://x@${'a'.repeat(40)}/x.csv`,
        source_match_id: null,
        captured_at: null,
        capture_time_status: 'unknown',
        recovered_at: '2026-08-09T06:14:00Z',
        source_timezone: 'unknown',
        raw_path: '/tmp/x.csv',
        raw_media_type: 'text/csv',
        raw_size_bytes: 100,
        raw_sha256: 'a'.repeat(64),
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        provenance_status: 'declared',
        upstream_provenance_status: 'unverified',
        repository_provenance: {
            repository: 'x/p',
            commit_sha: 'a'.repeat(40),
            blob_sha: 'b'.repeat(40),
            path: 'x.csv',
            commit_timestamp: '2026-01-29T19:22:29+08:00',
        },
        provider_contract: { applicable: true },
    };
    const result = validateSourceManifest(manifest);
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('contract_id')));
});

// ---- observation validator --------------------------------------------------

test('validator: an observation with an unknown provider_collection_phase quarantines', t => {
    const observation = createCanonicalObservation({
        source_provider: 'football-data-csv',
        source_match_id: null,
        competition: 'Premier League',
        season: '2023/2024',
        kickoff_at: '2023-08-05T14:00:00Z',
        home_team: 'Alpha FC',
        away_team: 'Beta FC',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        market: '1X2',
        selection: 'home',
        decimal_odds: 2.1,
        snapshot_type: 'unknown',
        provider_collection_phase: 'not-a-real-phase',
        source_observed_at: null,
        raw_record_locator: 'csv:row=2:bet365-unknown:home',
        adapter: 'football-data-csv',
        adapter_version: '1.3.0',
        ingestion_provenance: 'unit-test',
    });
    const result = validateObservation(observation);
    assert.ok(result.quarantine_reasons.includes('provider_collection_phase_invalid'));
});

test('validator: the two contract phases pass observation validation', t => {
    for (const phase of [FIRST_COLLECTION_PHASE, CLOSING_PHASE]) {
        const observation = createCanonicalObservation({
            source_provider: 'football-data-csv',
            source_match_id: null,
            competition: 'Premier League',
            season: '2023/2024',
            kickoff_at: '2023-08-05T14:00:00Z',
            home_team: 'Alpha FC',
            away_team: 'Beta FC',
            bookmaker: 'Bet365',
            bookmaker_source_id: 'B365',
            market: '1X2',
            selection: 'home',
            decimal_odds: 2.1,
            snapshot_type: phase === CLOSING_PHASE ? 'closing' : 'unknown',
            provider_collection_phase: phase,
            source_observed_at: null,
            raw_record_locator: 'csv:row=2:unit',
            adapter: 'football-data-csv',
            adapter_version: '1.3.0',
            ingestion_provenance: 'unit-test',
        });
        const result = validateObservation(observation);
        assert.ok(!result.quarantine_reasons.includes('provider_collection_phase_invalid'));
    }
});
