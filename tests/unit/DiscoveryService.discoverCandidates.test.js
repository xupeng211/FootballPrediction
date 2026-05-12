'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');

const SERVICE_PATH = '../../src/infrastructure/services/DiscoveryService';

function installNoSideEffectGuards(t) {
    const originalLoad = Module._load;
    const originalFetch = global.fetch;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalNetConnect = net.connect;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;

    const fail = name => () => {
        throw new Error(`${name} should not be called by discoverCandidates`);
    };

    global.fetch = fail('global.fetch');
    http.request = fail('http.request');
    https.request = fail('https.request');
    net.connect = fail('net.connect');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');

    Module._load = function patchedLoad(request, parent, isMain) {
        if (['pg', 'playwright', 'playwright-core', 'redis', 'ioredis'].includes(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/titan_discovery/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        Module._load = originalLoad;
        global.fetch = originalFetch;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        net.connect = originalNetConnect;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.createWriteStream = originalCreateWriteStream;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
    });
}

function loadDiscoveryServiceFresh() {
    delete require.cache[require.resolve(SERVICE_PATH)];
    return require(SERVICE_PATH).DiscoveryService;
}

function createConfigManager() {
    const league = {
        id: 53,
        providerId: 53,
        code: 'LIGUE1',
        name: 'Ligue 1',
        country: 'France',
        tier: 'P0',
        enabled: true,
        defaultSeason: '2025/2026',
    };
    return {
        getRuntimeConfig: () => ({
            active_leagues: [league],
            active_seasons: ['2025/2026'],
            default_season: '2025/2026',
            single_year_league_ids: [],
        }),
        getLeagueById: leagueId => (Number(leagueId) === 53 ? league : null),
        getLeagueByCode: code => (code === 'LIGUE1' ? league : null),
        getActiveLeagues: () => [league],
        getDefaultSeason: () => '2025/2026',
        getSingleYearLeagueIds: () => [],
        getExpectedMatches: () => null,
        getSeasonDateWindow: () => ({
            start: '2025-08-15',
            end: '2026-05-16',
            source: 'test',
        }),
        buildLeagueApiUrl: (leagueId, season) =>
            `https://www.fotmob.com/api/data/leagues?id=${leagueId}&season=${encodeURIComponent(season)}`,
    };
}

function createService() {
    const DiscoveryService = loadDiscoveryServiceFresh();
    const calls = {
        persist: 0,
        browserInitialize: 0,
        proxyAcquire: 0,
        httpRequest: 0,
    };
    const service = new DiscoveryService({
        silent: true,
        delayMs: 0,
        concurrency: 1,
        disableDbPool: true,
        disableBrowserProvider: true,
        disableProxyProvider: true,
        disableHttpClient: true,
        disableFixtureRepository: true,
        configManager: createConfigManager(),
        dbPool: null,
        browserProvider: {
            proxyProvider: null,
            isInitialized: () => false,
            initialize: async () => {
                calls.browserInitialize += 1;
                throw new Error('browser should not initialize');
            },
            close: async () => {},
        },
        networkInterceptor: {
            getCapturedApis: () => new Map(),
            reset: () => {},
        },
        fixtureRepository: {
            persist: async () => {
                calls.persist += 1;
                throw new Error('persist should not be called');
            },
        },
        httpClient: {
            proxyProvider: null,
            request: async () => {
                calls.httpRequest += 1;
                throw new Error('http should not be called');
            },
            close: async () => {},
        },
        proxyProvider: {
            acquire: async () => {
                calls.proxyAcquire += 1;
                throw new Error('proxy should not be used');
            },
        },
    });
    return { service, calls };
}

function fakeMatch(id, home, away, utcTime = '2026-05-10T19:00:00.000Z') {
    return {
        id,
        home: { name: home },
        away: { name: away },
        status: {
            scheduled: true,
            utcTime,
        },
    };
}

function fakePayload(matches = null) {
    return {
        fixtures: {
            allMatches: matches || [
                fakeMatch(123, 'Paris SG', 'Lyon', '2026-05-10T19:00:00.000Z'),
                fakeMatch(124, 'Marseille', 'Nice', '2026-05-10T21:00:00.000Z'),
            ],
        },
    };
}

function baseOptions(overrides = {}) {
    return {
        source: 'fotmob',
        scope: 'controlled_candidates_preview',
        leagueId: 53,
        season: '2025/2026',
        date: '2026-05-10',
        concurrency: 1,
        maxTargets: 1,
        allowNetwork: false,
        networkAuthorization: false,
        ...overrides,
    };
}

function assertSafetySummaryAllFalse(result) {
    assert.equal(result.safety_summary.wrote_db, false);
    assert.equal(result.safety_summary.wrote_matches, false);
    assert.equal(result.safety_summary.wrote_raw_match_data, false);
    assert.equal(result.safety_summary.called_persist, false);
    assert.equal(result.safety_summary.launched_browser, false);
    assert.equal(result.safety_summary.used_proxy, false);
    assert.equal(result.safety_summary.would_write_db, false);
    assert.equal(result.safety_summary.would_write_matches, false);
    assert.equal(result.safety_summary.would_write_raw_match_data, false);
    assert.equal(result.safety_summary.would_call_persist, false);
    assert.equal(result.safety_summary.would_launch_browser, false);
    assert.equal(result.safety_summary.would_use_proxy, false);
}

test('discoverCandidates 存在并默认 safe preview/no network/no DB', async t => {
    installNoSideEffectGuards(t);
    const { service, calls } = createService();

    const result = await service.discoverCandidates(baseOptions());

    assert.equal(typeof service.discoverCandidates, 'function');
    assert.equal(result.preview_only, true);
    assert.equal(result.dry_run, true);
    assert.equal(result.allow_network, false);
    assert.equal(result.db_written, false);
    assert.equal(result.matches_written, false);
    assert.equal(result.raw_match_data_written, false);
    assert.equal(result.candidate_count, 0);
    assert.equal(calls.persist, 0);
    assert.equal(calls.browserInitialize, 0);
    assert.equal(calls.proxyAcquire, 0);
    assert.equal(calls.httpRequest, 0);
    assertSafetySummaryAllFalse(result);
});

test('discoverCandidates source 缺失或非 fotmob 会失败', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();

    await assert.rejects(() => service.discoverCandidates({}), /missing source/i);
    await assert.rejects(() => service.discoverCandidates({ source: 'other' }), /unsupported source/i);
    await assert.rejects(() => service.discoverCandidates(baseOptions({ scope: 'bulk' })), /unsupported scope/i);
});

test('discoverCandidates 拒绝并发、批量、写库、browser fallback 和 proxy', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();

    await assert.rejects(() => service.discoverCandidates(baseOptions({ concurrency: 2 })), /concurrency > 1/i);
    await assert.rejects(() => service.discoverCandidates(baseOptions({ maxTargets: 11 })), /maxTargets > 10/i);
    await assert.rejects(() => service.discoverCandidates(baseOptions({ writeDb: true })), /writeDb=true/i);
    await assert.rejects(
        () => service.discoverCandidates(baseOptions({ allowBrowserFallback: true })),
        /allowBrowserFallback=true/i
    );
    await assert.rejects(() => service.discoverCandidates(baseOptions({ allowProxy: true })), /allowProxy=true/i);
});

test('discoverCandidates 要求显式 leagueId/season/date', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();

    await assert.rejects(() => service.discoverCandidates(baseOptions({ leagueId: null })), /missing leagueId/i);
    await assert.rejects(() => service.discoverCandidates(baseOptions({ season: null })), /missing season/i);
    await assert.rejects(() => service.discoverCandidates(baseOptions({ date: null })), /missing date/i);
});

test('allowNetwork=true 但 networkAuthorization=false 失败', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();

    await assert.rejects(
        () => service.discoverCandidates(baseOptions({ allowNetwork: true, networkAuthorization: false })),
        /networkAuthorization=true is required/i
    );
});

test('allowNetwork=false 时不调用注入的真实 fetch', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();
    let fetchCalls = 0;

    const result = await service.discoverCandidates(baseOptions(), {
        fetchLeagueFixtures: async () => {
            fetchCalls += 1;
            return fakePayload();
        },
    });

    assert.equal(fetchCalls, 0);
    assert.equal(result.fetch_mode, 'not_executed');
    assert.equal(result.candidate_count, 0);
    assert.equal(result.external_network_used, false);
    assert.equal(result.network_authorization_used, false);
});

test('allowNetwork=true 且 networkAuthorization=true 时调用 fake client 并返回 normalized candidates', async t => {
    installNoSideEffectGuards(t);
    const { service, calls } = createService();
    let fetchCalls = 0;

    const result = await service.discoverCandidates(baseOptions({ allowNetwork: true, networkAuthorization: true }), {
        networkKind: 'fake',
        fetchLeagueFixtures: async request => {
            fetchCalls += 1;
            assert.equal(request.leagueId, 53);
            assert.equal(request.season, '2025/2026');
            assert.equal(request.date, '2026-05-10');
            assert.match(request.sourceUrl, /fotmob\.com\/api\/data\/leagues/);
            return fakePayload();
        },
    });

    assert.equal(fetchCalls, 1);
    assert.equal(result.fetch_mode, 'fake_injected_client');
    assert.equal(result.external_network_used, false);
    assert.equal(result.network_used, true);
    assert.equal(result.network_authorization_used, true);
    assert.equal(result.source_url_used, 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026');
    assert.equal(result.raw_candidate_count, 2);
    assert.equal(result.candidate_count, 1);
    assert.equal(result.candidates.length, 1);
    assert.equal(result.candidates[0].match_id, '53_20252026_123');
    assert.equal(result.candidates[0].external_id, '123');
    assert.equal(result.candidates[0].league, 'Ligue 1');
    assert.equal(result.candidates[0].season, '2025/2026');
    assert.equal(result.candidates[0].home, 'Paris SG');
    assert.equal(result.candidates[0].away, 'Lyon');
    assert.equal(result.candidates[0].match_date, '2026-05-10T19:00:00.000Z');
    assert.equal(result.candidates[0].data_source, 'FotMob');
    assert.equal(calls.persist, 0);
    assert.equal(calls.browserInitialize, 0);
    assert.equal(calls.proxyAcquire, 0);
    assert.equal(calls.httpRequest, 0);
    assertSafetySummaryAllFalse(result);
});

test('candidates 受 maxTargets=10 限制', async t => {
    installNoSideEffectGuards(t);
    const { service } = createService();
    const matches = Array.from({ length: 12 }, (_, index) =>
        fakeMatch(200 + index, `Home ${index}`, `Away ${index}`, '2026-05-10T12:00:00.000Z')
    );

    const result = await service.discoverCandidates(
        baseOptions({ allowNetwork: true, networkAuthorization: true, maxTargets: 10 }),
        {
            networkKind: 'fake',
            fetchLeagueFixtures: async () => fakePayload(matches),
        }
    );

    assert.equal(result.raw_candidate_count, 12);
    assert.equal(result.candidate_count, 10);
    assert.equal(result.candidates.length, 10);
});

test('fake network error 返回 controlled error 且不 retry', async t => {
    installNoSideEffectGuards(t);
    const { service, calls } = createService();
    let fetchCalls = 0;

    await assert.rejects(
        () =>
            service.discoverCandidates(baseOptions({ allowNetwork: true, networkAuthorization: true }), {
                networkKind: 'fake',
                fetchLeagueFixtures: async () => {
                    fetchCalls += 1;
                    throw new Error('fake upstream down');
                },
            }),
        error => {
            assert.equal(error.code, 'L1_DISCOVERY_CANDIDATES_FETCH_FAILED');
            assert.equal(error.retryCount, 0);
            assert.equal(error.externalNetworkUsed, false);
            assert.equal(error.networkAuthorizationUsed, true);
            assert.match(error.message, /fake upstream down/);
            return true;
        }
    );

    assert.equal(fetchCalls, 1);
    assert.equal(calls.persist, 0);
    assert.equal(calls.browserInitialize, 0);
    assert.equal(calls.proxyAcquire, 0);
    assert.equal(calls.httpRequest, 0);
});
