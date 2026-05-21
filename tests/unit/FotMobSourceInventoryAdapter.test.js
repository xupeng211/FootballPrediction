'use strict';

const assert = require('node:assert/strict');
const Module = require('node:module');
const test = require('node:test');

const {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND,
    deriveSourceInventoryIdentityEvidence,
    parseSourcePageUrl,
} = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');

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
        getProviderLeagueId: leagueId => (Number(leagueId) === 53 ? 53 : null),
        getSingleYearLeagueIds: () => [],
        getSeasonDateWindow: () => ({
            start: '2025-08-15',
            end: '2026-05-16',
            source: 'test',
        }),
        buildLeagueApiUrl: (leagueId, season) =>
            `https://www.fotmob.com/api/data/leagues?id=${leagueId}&season=${encodeURIComponent(season)}`,
    };
}

function createAdapter(overrides = {}) {
    return new FotMobSourceInventoryAdapter({
        configManager: overrides.configManager || createConfigManager(),
        parser: overrides.parser,
        seasonStrategyFactory: overrides.seasonStrategyFactory,
        logger: {
            info() {},
            warn() {},
            error() {},
        },
    });
}

function sourceMatch(id, overrides = {}) {
    return {
        id,
        home: { name: `Home ${id}` },
        away: { name: `Away ${id}` },
        status: {
            utcTime: '2026-03-15T19:00:00.000Z',
            finished: true,
        },
        ...overrides,
    };
}

function installImportGuard(t, pattern) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (pattern.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('buildSourceInventoryUrl reuses existing L1 /api/data/leagues route and season formatting', () => {
    const adapter = createAdapter();

    const url = adapter.buildSourceInventoryUrl({
        source: 'fotmob',
        leagueId: 53,
        season: '2025/2026',
    });

    assert.equal(url, 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026');
    assert.ok(!url.includes('/api/leagues?'));
    assert.ok(!url.includes('/matchDetails'));
});

test('existing L1 parser output normalizes to manifest-compatible candidate seed', () => {
    const adapter = createAdapter();

    const candidates = adapter.parseSourceInventory(
        {
            fixtures: {
                allMatches: [sourceMatch('6000001')],
            },
        },
        {
            source: 'fotmob',
            leagueId: 53,
            season: '2025/2026',
        }
    );

    assert.equal(candidates.length, 1);
    assert.equal(candidates[0].source, 'fotmob');
    assert.equal(candidates[0].source_inventory_route, ROUTE_KIND);
    assert.equal(candidates[0].external_id, '6000001');
    assert.equal(candidates[0].valid_external_id, true);
    assert.equal(candidates[0].match_id, '53_20252026_6000001');
    assert.equal(candidates[0].home_team, 'Home 6000001');
    assert.equal(candidates[0].away_team, 'Away 6000001');
    assert.equal(candidates[0].kickoff_time, '2026-03-15T19:00:00.000Z');
    assert.equal(candidates[0].match_date, '2026-03-15T19:00:00.000Z');
    assert.equal(candidates[0].status, 'finished');
});

test('adapter enriches candidate seed with source URL identity evidence from source-controlled inventory metadata', () => {
    const adapter = createAdapter();

    const candidates = adapter.parseSourceInventory(
        {
            fixtures: {
                allMatches: [
                    sourceMatch('6000001', {
                        pageUrl: '/matches/home-vs-away/abcd12#6000001',
                    }),
                ],
            },
        },
        {
            source: 'fotmob',
            leagueId: 53,
            season: '2025/2026',
            sourceInventoryGeneratedAt: '2026-05-21T09:00:00Z',
        }
    );

    assert.equal(candidates.length, 1);
    assert.equal(candidates[0].source_url, '/matches/home-vs-away/abcd12#6000001');
    assert.equal(candidates[0].source_page_url, '/matches/home-vs-away/abcd12#6000001');
    assert.equal(candidates[0].source_page_url_base, '/matches/home-vs-away/abcd12');
    assert.equal(candidates[0].source_url_fragment_external_id, '6000001');
    assert.equal(candidates[0].source_slug, 'home-vs-away');
    assert.equal(candidates[0].source_route_code, 'abcd12');
    assert.equal(candidates[0].schedule_external_id, '6000001');
    assert.equal(candidates[0].schedule_date, '2026-03-15T19:00:00.000Z');
    assert.equal(candidates[0].schedule_home_team, 'Home 6000001');
    assert.equal(candidates[0].schedule_away_team, 'Away 6000001');
    assert.equal(candidates[0].source_inventory_record_key, 'l1_api_data_leagues:fixtures.allMatches.0:6000001');
    assert.equal(candidates[0].source_inventory_generated_at, '2026-05-21T09:00:00Z');
    assert.equal(candidates[0].identity_evidence_status, 'complete');
});

test('missing pageUrl remains missing and is not fabricated from external_id', () => {
    const adapter = createAdapter();

    const candidates = adapter.parseSourceInventory(
        {
            fixtures: {
                allMatches: [sourceMatch('6000002')],
            },
        },
        {
            source: 'fotmob',
            leagueId: 53,
            season: '2025/2026',
        }
    );

    assert.equal(candidates.length, 1);
    assert.equal(candidates[0].source_url, null);
    assert.equal(candidates[0].source_page_url, null);
    assert.equal(candidates[0].source_page_url_base, null);
    assert.equal(candidates[0].source_url_fragment_external_id, null);
    assert.equal(candidates[0].source_inventory_record_key, 'l1_api_data_leagues:fixtures.allMatches.0:6000002');
    assert.equal(candidates[0].identity_evidence_status, 'missing');
});

test('source URL helpers parse fragments without accepting mismatched identity evidence', () => {
    const parsed = parseSourcePageUrl('https://www.fotmob.com/matches/home-vs-away/abcd12#6000003');
    const mismatched = deriveSourceInventoryIdentityEvidence({
        match: {
            id: '6000004',
            pageUrl: '/matches/home-vs-away/abcd12#6000003',
        },
        sourcePath: 'fixtures.allMatches.0',
        externalId: '6000004',
    });

    assert.equal(parsed.source_page_url_base, 'https://www.fotmob.com/matches/home-vs-away/abcd12');
    assert.equal(parsed.source_url_fragment_external_id, '6000003');
    assert.equal(parsed.source_slug, 'home-vs-away');
    assert.equal(parsed.source_route_code, 'abcd12');
    assert.equal(mismatched.identity_evidence_status, 'partial');
});

test('adapter marks non-numeric external_id invalid without fabricating replacement target', () => {
    const adapter = createAdapter();

    const candidates = adapter.parseSourceInventory(
        {
            matches: {
                allMatches: [sourceMatch('abc123')],
            },
        },
        {
            source: 'fotmob',
            leagueId: 53,
            season: '2025/2026',
        }
    );

    assert.equal(candidates.length, 1);
    assert.equal(candidates[0].external_id, 'abc123');
    assert.equal(candidates[0].valid_external_id, false);
});

test('adapter does not fetch network by itself and empty source yields no invented targets', () => {
    const adapter = createAdapter();
    let fetchCalls = 0;
    const originalFetch = global.fetch;
    global.fetch = async () => {
        fetchCalls += 1;
        throw new Error('global fetch should not be called');
    };

    try {
        const candidates = adapter.parseSourceInventory(
            {
                fixtures: {
                    allMatches: [],
                },
            },
            {
                source: 'fotmob',
                leagueId: 53,
                season: '2025/2026',
            }
        );

        assert.equal(fetchCalls, 0);
        assert.deepEqual(candidates, []);
    } finally {
        global.fetch = originalFetch;
    }
});

test('adapter import avoids unsafe runners, DB writers, browser, proxy, odds, and harvest modules', t => {
    installImportGuard(
        t,
        /ProductionHarvester|titan_discovery|run_production|odds_harvest_pipeline|BrowserProvider|ProxyProvider|playwright|pg/i
    );

    delete require.cache[require.resolve('../../src/infrastructure/services/FotMobSourceInventoryAdapter')];
    const loaded = require('../../src/infrastructure/services/FotMobSourceInventoryAdapter');
    assert.equal(typeof loaded.FotMobSourceInventoryAdapter, 'function');
});

test('resolveTarget fails closed for wrong source, missing league id, missing season and unknown league', () => {
    const adapter = createAdapter();

    assert.throws(
        () => adapter.resolveTarget({ source: 'other', leagueId: 53, season: '2025/2026' }),
        /only supports source=fotmob/
    );
    assert.throws(
        () => adapter.resolveTarget({ source: 'fotmob', leagueId: 0, season: '2025/2026' }),
        /positive leagueId/
    );
    assert.throws(() => adapter.resolveTarget({ source: 'fotmob', leagueId: 53, season: '' }), /requires season/);
    assert.throws(
        () => adapter.resolveTarget({ source: 'fotmob', leagueId: 999, season: '2025/2026' }),
        /league config not found/
    );
});

test('resolveTarget supports league_id input and provider id fallback without fabricating source identity', () => {
    const configManager = {
        getRuntimeConfig: () => ({ active_leagues: [], single_year_league_ids: [] }),
        getLeagueById: leagueId => ({
            id: Number(leagueId),
            providerId: 777,
            name: 'Fallback League',
        }),
        buildLeagueApiUrl: (leagueId, season) => `https://example.test/${leagueId}/${season}`,
    };
    const adapter = createAdapter({
        configManager,
        seasonStrategyFactory: {
            format: (_leagueId, season) => `formatted-${season}`,
        },
    });

    const target = adapter.resolveTarget({
        source: ' FOTMOB ',
        league_id: '53',
        season: '2025/2026',
    });

    assert.equal(target.source, 'fotmob');
    assert.equal(target.leagueId, 53);
    assert.equal(target.providerLeagueId, 777);
    assert.equal(target.formattedSeason, 'formatted-2025/2026');
    assert.equal(target.routeKind, ROUTE_KIND);
});

test('buildFetchRequest returns safe source inventory request metadata only', () => {
    const adapter = createAdapter();

    const request = adapter.buildFetchRequest({
        source: 'fotmob',
        leagueId: 53,
        season: '2025/2026',
    });

    assert.equal(request.source, 'fotmob');
    assert.equal(request.routeKind, ROUTE_KIND);
    assert.equal(request.leagueId, 53);
    assert.equal(request.providerLeagueId, 53);
    assert.equal(request.formattedSeason, '20252026');
    assert.match(request.sourceUrl, /\/api\/data\/leagues\?id=53&season=20252026/);
    assert.equal(Object.hasOwn(request, 'body'), false);
    assert.equal(Object.hasOwn(request, 'pageProps'), false);
});

test('filterBySeasonWindow handles absent or invalid windows and filters out-of-window fixtures', () => {
    const fixtures = [
        { match_date: '2025-08-15T12:00:00.000Z', external_id: '1' },
        { match_date: '2026-06-01T12:00:00.000Z', external_id: '2' },
        { match_date: 'not-a-date', external_id: '3' },
        { external_id: '4' },
    ];

    const noWindowAdapter = createAdapter({
        configManager: {
            ...createConfigManager(),
            getSeasonDateWindow: () => null,
        },
    });
    assert.equal(noWindowAdapter.filterBySeasonWindow(fixtures, 53, '2025/2026').length, 4);
    assert.deepEqual(noWindowAdapter.filterBySeasonWindow(null, 53, '2025/2026'), []);

    const invalidWindowAdapter = createAdapter({
        configManager: {
            ...createConfigManager(),
            getSeasonDateWindow: () => ({ start: 'bad-date', end: '2026-05-16' }),
        },
    });
    assert.equal(invalidWindowAdapter.filterBySeasonWindow(fixtures, 53, '2025/2026').length, 4);

    const guarded = createAdapter().filterBySeasonWindow(fixtures, 53, '2025/2026');
    assert.deepEqual(
        guarded.map(fixture => fixture.external_id),
        ['1', '3', '4']
    );
});

test('toManifestCandidateSeed preserves separate identity fields and defaults nullable metadata safely', () => {
    const adapter = createAdapter();

    const seed = adapter.toManifestCandidateSeed(
        {
            external_id: ' 7000001 ',
            match_id: '',
            league_name: '',
            season: '',
            home_team: '',
            away_team: '',
            match_date: 'not-a-date',
            status: '',
            data_source: '',
        },
        9
    );

    assert.equal(seed.source, 'fotmob');
    assert.equal(seed.source_inventory_route, ROUTE_KIND);
    assert.equal(seed.external_id, '7000001');
    assert.equal(seed.valid_external_id, true);
    assert.equal(seed.match_id, null);
    assert.equal(seed.kickoff_time, null);
    assert.equal(seed.match_date, null);
    assert.equal(seed.status, 'scheduled');
    assert.equal(seed.data_source, 'FotMob');
    assert.equal(seed.source_url, null);
    assert.equal(seed.priority, 9);
});

test('parseSourceInventory can use injected parser without network or DB side effects', () => {
    const calls = [];
    const adapter = createAdapter({
        parser: {
            parse: (sourceJson, leagueId, season, commit, options) => {
                calls.push({ sourceJson, leagueId, season, commit, options });
                return [
                    {
                        match_id: '53_20252026_8000001',
                        external_id: '8000001',
                        league_name: 'Ligue 1',
                        season: '2025/2026',
                        home_team: 'Home',
                        away_team: 'Away',
                        match_date: '2025-09-01T19:00:00.000Z',
                        status: 'scheduled',
                        data_source: 'FotMob',
                    },
                ];
            },
        },
    });

    const candidates = adapter.parseSourceInventory(
        { safe: true },
        {
            source: 'fotmob',
            leagueId: 53,
            season: '2025/2026',
        }
    );

    assert.equal(calls.length, 1);
    assert.equal(calls[0].commit, false);
    assert.deepEqual(calls[0].options, { fullSync: true });
    assert.equal(candidates.length, 1);
    assert.equal(candidates[0].match_id, '53_20252026_8000001');
    assert.equal(candidates[0].external_id, '8000001');
});
