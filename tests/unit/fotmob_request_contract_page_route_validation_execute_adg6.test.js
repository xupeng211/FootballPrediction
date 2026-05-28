'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(
    PROJECT_ROOT,
    'scripts/ops/fotmob_request_contract_page_route_validation_execute_adg6.js'
);

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function planFixture() {
    return {
        planned_42_target_sample_count: 5,
        planned_suspended_reference_sample_count: 2,
        planned_samples: {
            positive_sample: {
                sample_id: 'positive:4813735',
                sample_group: 'positive_sample',
                source_page_url:
                    'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3#4813735',
                source_url_path_slug: '2feiv3',
                source_url_fragment_external_id: '4813735',
                detail_external_id_candidate: '4813735',
                detail_identity_source: 'url_hash_fragment',
                expected_home_team: 'AFC Bournemouth',
                expected_away_team: 'Manchester City',
                expected_match_date: null,
                expected_competition: null,
                page_route_url_without_fragment:
                    'https://www.fotmob.com/zh-Hans/matches/manchester-city-vs-afc-bournemouth/2feiv3',
            },
            request_contract_validation_required_samples: [
                {
                    sample_id: 'request-contract:4830458',
                    sample_group: 'request_contract_validation_required',
                    source_page_url: 'https://www.fotmob.com/matches/paris-fc-vs-angers/1qlitv#4830458',
                    source_url_path_slug: '1qlitv',
                    source_url_fragment_external_id: '4830458',
                    detail_external_id_candidate: '4830458',
                    detail_identity_source: 'url_hash_fragment',
                    expected_home_team: 'Angers',
                    expected_away_team: 'Paris FC',
                    expected_match_date: '2025-08-17T15:15:00.000Z',
                    expected_competition: 'Ligue 1',
                    page_route_url_without_fragment: 'https://www.fotmob.com/matches/paris-fc-vs-angers/1qlitv',
                },
            ],
            suspended_reference_samples: [
                {
                    sample_id: 'suspended-reference:4830461',
                    sample_group: 'suspended_reference',
                    source_page_url: 'https://www.fotmob.com/matches/lens-vs-lyon/2s3gtg#4830461',
                    source_url_path_slug: '2s3gtg',
                    source_url_fragment_external_id: '4830461',
                    detail_external_id_candidate: '4830461',
                    detail_identity_source: 'url_hash_fragment',
                    expected_home_team: 'Lens',
                    expected_away_team: 'Lyon',
                    expected_match_date: '2025-08-16T15:00:00.000Z',
                    expected_competition: 'Ligue 1',
                    page_route_url_without_fragment: 'https://www.fotmob.com/matches/lens-vs-lyon/2s3gtg',
                },
            ],
        },
    };
}

function nextDataHtml({ matchId, home, away, date }) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: {
            pageProps: {
                content: { stats: [] },
                general: {
                    matchId,
                    homeTeam: home,
                    awayTeam: away,
                    matchTimeUTC: date,
                    pageUrl: `/matches/${matchId}`,
                },
                header: {
                    teams: [{ name: home }, { name: away }],
                    status: { utcTime: date },
                },
            },
        },
    })}</script></body></html>`;
}

function fakeResponse({ status = 200, url, body }) {
    return {
        ok: status >= 200 && status < 300,
        status,
        url,
        headers: {
            get(name) {
                if (name.toLowerCase() === 'content-type') return 'text/html; charset=utf-8';
                return null;
            },
        },
        async text() {
            return body;
        },
    };
}

test('ADG6 buildSamples keeps bounded 1+5+2 shape from plan', () => {
    const samples = mod.buildSamples(readPlan());
    assert.equal(samples.length, 8);
    assert.equal(samples[0].sample_group, 'positive_sample');
    assert.equal(samples.filter(item => item.sample_group === 'request_contract_validation_required').length, 5);
    assert.equal(samples.filter(item => item.sample_group === 'suspended_reference').length, 2);
    assert.equal(mod.normalizeOutputSampleId(samples[0]), mod.POSITIVE_SAMPLE_OUTPUT_ID);
});

function readPlan() {
    const fixture = planFixture();
    fixture.planned_samples.request_contract_validation_required_samples = Array.from(
        { length: 5 },
        (_value, index) => ({
            ...fixture.planned_samples.request_contract_validation_required_samples[0],
            sample_id: `request-contract:${4830458 + index}`,
            source_url_fragment_external_id: String(4830458 + index),
            detail_external_id_candidate: String(4830458 + index),
        })
    );
    fixture.planned_samples.suspended_reference_samples = [
        fixture.planned_samples.suspended_reference_samples[0],
        {
            ...fixture.planned_samples.suspended_reference_samples[0],
            sample_id: 'suspended-reference:4830463',
            source_url_fragment_external_id: '4830463',
            detail_external_id_candidate: '4830463',
        },
    ];
    return fixture;
}

test('ADG6 executeSample classifies validated identity without saving full body', async () => {
    const sample = readPlan().planned_samples.request_contract_validation_required_samples[0];
    const result = await mod.executeSample(
        sample,
        { timeoutMs: 1000 },
        {
            fetchFn: async url =>
                fakeResponse({
                    url,
                    body: nextDataHtml({
                        matchId: '4830458',
                        home: 'Angers',
                        away: 'Paris FC',
                        date: '2025-08-17T15:15:00.000Z',
                    }),
                }),
        }
    );

    assert.equal(result.validation_classification, 'page_route_identity_validated');
    assert.equal(result.page_http_status, 200);
    assert.equal(result.no_full_body_saved, true);
    assert.equal(result.no_db_write, true);
    assert.equal(result.no_raw_write, true);
    assert.equal(result.observed_detail_id_if_safely_available, '4830458');
});

test('ADG6 executeSample classifies anti-bot 403 and stops', async () => {
    const sample = readPlan().planned_samples.request_contract_validation_required_samples[0];
    const result = await mod.executeSample(
        sample,
        { timeoutMs: 1000 },
        {
            fetchFn: async url =>
                fakeResponse({
                    status: 403,
                    url,
                    body: '<html><body>Forbidden</body></html>',
                }),
        }
    );

    assert.equal(result.validation_classification, 'anti_bot_or_access_block');
    assert.equal(result.request_contract_status, 'direct_api_request_contract_blocked');
});

test('ADG6 executeSample keeps suspended reference blocked even when identity validates', async () => {
    const sample = readPlan().planned_samples.suspended_reference_samples[0];
    const result = await mod.executeSample(
        sample,
        { timeoutMs: 1000 },
        {
            fetchFn: async url =>
                fakeResponse({
                    url,
                    body: nextDataHtml({
                        matchId: '4830461',
                        home: 'Lens',
                        away: 'Lyon',
                        date: '2025-08-16T15:00:00.000Z',
                    }),
                }),
        }
    );

    assert.equal(result.validation_classification, 'suspended_reference_blocked');
    assert.equal(result.reference_page_identity_validated, true);
});

test('ADG6 executeSample treats positive sample as validated when detail id and team order match without expected date', async () => {
    const sample = readPlan().planned_samples.positive_sample;
    const result = await mod.executeSample(
        sample,
        { timeoutMs: 1000 },
        {
            fetchFn: async url =>
                fakeResponse({
                    url,
                    body: nextDataHtml({
                        matchId: '4813735',
                        home: 'AFC Bournemouth',
                        away: 'Manchester City',
                        date: '2026-05-19T18:30:00.000Z',
                    }),
                }),
        }
    );

    assert.equal(result.validation_classification, 'page_route_identity_validated');
    assert.equal(result.observed_detail_id_if_safely_available, '4813735');
    assert.equal(result.sample_id, mod.POSITIVE_SAMPLE_OUTPUT_ID);
});

test('ADG6 run produces safe artifact without full payload markers', async () => {
    const result = await mod.runFotmobRequestContractPageRouteValidationExecuteAdg6(
        { writeFiles: false, timeoutMs: 1000 },
        {
            plan: readPlan(),
            generatedAt: '2026-05-28T03:00:00.000Z',
            fetchFn: async url => {
                const id = url.match(/#?(\d+)?$/)?.[1] || (url.includes('2feiv3') ? '4813735' : '4830458');
                const mapping = {
                    4813735: { home: 'AFC Bournemouth', away: 'Manchester City', date: null },
                    4830458: { home: 'Angers', away: 'Paris FC', date: '2025-08-17T15:15:00.000Z' },
                    4830459: { home: 'Auxerre', away: 'Lorient', date: '2025-08-17T15:15:00.000Z' },
                    4830460: { home: 'Brest', away: 'Lille', date: '2025-08-17T13:00:00.000Z' },
                    4830461: { home: 'Lens', away: 'Lyon', date: '2025-08-16T15:00:00.000Z' },
                    4830462: { home: 'Metz', away: 'Strasbourg', date: '2025-08-17T15:15:00.000Z' },
                    4830463: { home: 'Monaco', away: 'Le Havre', date: '2025-08-16T17:00:00.000Z' },
                    4830464: { home: 'Nantes', away: 'Paris Saint-Germain', date: '2025-08-17T18:45:00.000Z' },
                };
                const meta = mapping[id] || mapping['4830458'];
                return fakeResponse({
                    url,
                    body: nextDataHtml({
                        matchId: id,
                        home: meta.home,
                        away: meta.away,
                        date: meta.date,
                    }),
                });
            },
        }
    );

    assert.equal(result.ok, true);
    assert.equal(result.artifact.validation_execution_performed, true);
    assert.equal(result.artifact.adg6_execution_status, mod.STATUS);
    assert.equal(result.artifact.raw_write_ready_count, 0);
    assert.equal(result.artifact.db_write_performed, false);
    assert.equal(result.artifact.raw_write_execution_performed, false);

    const texts = [JSON.stringify(result.artifact), result.report];
    for (const text of texts) {
        assert.equal(text.includes('"body":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});
