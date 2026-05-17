'use strict';

const assert = require('node:assert/strict');
const Module = require('node:module');
const test = require('node:test');

const {
    FotMobSourceInventoryAdapter,
    ROUTE_KIND,
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

function createAdapter() {
    return new FotMobSourceInventoryAdapter({
        configManager: createConfigManager(),
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
