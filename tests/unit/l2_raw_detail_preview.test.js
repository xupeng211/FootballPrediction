'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const childProcess = require('node:child_process');
const http = require('node:http');
const https = require('node:https');
const Module = require('node:module');
const { pathToFileURL } = require('node:url');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l2_raw_detail_preview.js');

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function validArgs(overrides = {}) {
    return {
        source: 'fotmob',
        matchId: '53_20252026_4830746',
        externalId: '4830746',
        homeTeam: 'Angers',
        awayTeam: 'Strasbourg',
        route: 'auto',
        networkAuthorization: true,
        livePreviewAuthorization: false,
        allowDbWrite: false,
        allowRawMatchDataWrite: false,
        allowBrowserRuntime: false,
        allowProxyRuntime: false,
        concurrency: '1',
        retry: '0',
        printBody: false,
        saveBody: false,
        bulk: false,
        ...overrides,
    };
}

function cliArgs(overrides = {}) {
    const args = validArgs(overrides);
    const tokens = [
        `--source=${args.source}`,
        `--match-id=${args.matchId}`,
        `--external-id=${args.externalId}`,
        `--home-team=${args.homeTeam}`,
        `--away-team=${args.awayTeam}`,
        `--route=${args.route}`,
        `--network-authorization=${args.networkAuthorization ? 'yes' : 'no'}`,
        `--live-preview-authorization=${args.livePreviewAuthorization ? 'yes' : 'no'}`,
        `--allow-db-write=${args.allowDbWrite ? 'yes' : 'no'}`,
        `--allow-raw-match-data-write=${args.allowRawMatchDataWrite ? 'yes' : 'no'}`,
        `--allow-browser-runtime=${args.allowBrowserRuntime ? 'yes' : 'no'}`,
        `--allow-proxy-runtime=${args.allowProxyRuntime ? 'yes' : 'no'}`,
        `--concurrency=${args.concurrency}`,
        `--retry=${args.retry}`,
        `--print-body=${args.printBody ? 'yes' : 'no'}`,
        `--save-body=${args.saveBody ? 'yes' : 'no'}`,
    ];
    if (args.bulk) {
        tokens.push('--bulk=yes');
    }
    return tokens;
}

function fakeJsonBody() {
    return JSON.stringify({
        general: {
            matchId: 4830746,
            homeTeam: { name: 'Angers' },
            awayTeam: { name: 'Strasbourg' },
        },
        header: {
            teams: [{ name: 'Angers' }, { name: 'Strasbourg' }],
        },
        content: {
            matchFacts: {
                matchId: 4830746,
            },
            stats: {
                periods: [],
            },
            lineup: {
                homeTeam: 'Angers',
                awayTeam: 'Strasbourg',
            },
        },
    });
}

function fakeHtmlBody() {
    const nextData = {
        props: {
            pageProps: {
                general: {
                    matchId: 4830746,
                    homeTeam: { name: 'Angers' },
                    awayTeam: { name: 'Strasbourg' },
                },
                content: {
                    matchDetails: {
                        id: 4830746,
                        fixture: 'Angers vs Strasbourg',
                    },
                    stats: {
                        periods: [],
                    },
                    lineup: {
                        homeTeam: 'Angers',
                        awayTeam: 'Strasbourg',
                    },
                },
                header: {
                    teams: [{ name: 'Angers' }, { name: 'Strasbourg' }],
                },
            },
        },
    };
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script></body></html>`;
}

function createResponse(body, options = {}) {
    const status = options.status || 200;
    const url = options.url || 'https://www.fotmob.com/api/data/matchDetails?matchId=4830746';
    const contentType = options.contentType || 'application/json; charset=utf-8';
    return {
        status,
        ok: status >= 200 && status < 300,
        url,
        headers: {
            get(name) {
                return String(name).toLowerCase() === 'content-type' ? contentType : '';
            },
        },
        async text() {
            return body;
        },
    };
}

async function runCli(gate, argv, dependencies = {}) {
    let stdout = '';
    const status = await gate.runCli(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
        },
        dependencies.fetchImpl ? { allowRouteExecution: true, ...dependencies } : dependencies
    );
    return {
        status,
        stdout,
        payload: stdout.trim().startsWith('{') ? JSON.parse(stdout) : null,
    };
}

function installExecutionGuards(t) {
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalLoad = Module._load;

    const fail = name => () => {
        throw new Error(`${name} should not be called by l2_raw_detail_preview`);
    };

    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    http.request = fail('http.request');
    https.request = fail('https.request');

    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
            'child_process',
            'node:child_process',
        ]);
        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (
            /ProductionHarvester|FotMobStrategy|raw_match_data_local_ingest|backfill_historical_raw_match_data/i.test(
                request
            )
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        fs.createWriteStream = originalCreateWriteStream;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        Module._load = originalLoad;
    });
}

test('valid input succeeds', () => {
    const gate = loadModuleFresh();
    const validation = gate.validatePreviewInput(validArgs());
    assert.equal(validation.ok, true);
});

test('parseArgs maps dashed CLI flags', () => {
    const gate = loadModuleFresh();
    const parsed = gate.parseArgs(cliArgs());
    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.matchId, '53_20252026_4830746');
    assert.equal(parsed.externalId, '4830746');
    assert.equal(parsed.homeTeam, 'Angers');
    assert.equal(parsed.awayTeam, 'Strasbourg');
    assert.equal(parsed.route, 'auto');
    assert.equal(parsed.networkAuthorization, true);
    assert.equal(parsed.livePreviewAuthorization, false);
    assert.equal(parsed.allowDbWrite, false);
    assert.equal(parsed.allowRawMatchDataWrite, false);
});

test('normalizeBooleanFlag supports yes/no forms', () => {
    const gate = loadModuleFresh();
    assert.equal(gate.normalizeBooleanFlag('yes'), true);
    assert.equal(gate.normalizeBooleanFlag('true'), true);
    assert.equal(gate.normalizeBooleanFlag('no'), false);
    assert.equal(gate.normalizeBooleanFlag('false'), false);
    assert.equal(gate.normalizeBooleanFlag('', 'fallback'), 'fallback');
    assert.equal(gate.normalizeBooleanFlag(null, 'fallback'), 'fallback');
    assert.equal(gate.normalizeBooleanFlag('unknown', null), null);
});

test('parseArgs covers split values, positional unknown, and unknown flags', () => {
    const gate = loadModuleFresh();
    const parsed = gate.parseArgs([
        '--source',
        'fotmob',
        '--match-id',
        '53_20252026_4830746',
        '--unknown-flag=yes',
        'positional-value',
        '--help',
    ]);

    assert.equal(parsed.source, 'fotmob');
    assert.equal(parsed.matchId, '53_20252026_4830746');
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['unknown-flag', 'positional-value']);
});

const invalidInputCases = [
    ['source missing fails', { source: null }, /missing source/],
    ['source non-fotmob fails', { source: 'other' }, /unsupported source/],
    ['match-id missing fails', { matchId: null }, /missing match-id/],
    ['match-id not 53_20252026_4830746 fails', { matchId: '53_20252026_4830747' }, /match-id must be/],
    ['external-id missing fails', { externalId: null }, /missing external-id/],
    ['external-id not 4830746 fails', { externalId: '4830747' }, /external-id must be/],
    ['missing home-team fails', { homeTeam: null }, /missing home-team/],
    ['home-team mismatch fails', { homeTeam: 'Nice' }, /home-team must contain/],
    ['missing away-team fails', { awayTeam: null }, /missing away-team/],
    ['away-team mismatch fails', { awayTeam: 'Lyon' }, /away-team must contain/],
    ['unsupported route fails', { route: 'alternate_route' }, /unsupported route/],
    ['allow-db-write=yes blocked', { allowDbWrite: true }, /allow-db-write=yes/],
    ['allow-raw-match-data-write=yes blocked', { allowRawMatchDataWrite: true }, /allow-raw-match-data-write=yes/],
    ['allow-browser-runtime=yes blocked', { allowBrowserRuntime: true }, /allow-browser-runtime=yes/],
    ['allow-proxy-runtime=yes blocked', { allowProxyRuntime: true }, /allow-proxy-runtime=yes/],
    ['concurrency > 1 blocked', { concurrency: '2' }, /concurrency > 1/],
    ['retry > 0 blocked', { retry: '1' }, /retry > 0/],
    ['print-body=yes blocked', { printBody: true }, /print-body=yes/],
    ['save-body=yes blocked', { saveBody: true }, /save-body=yes/],
    ['bulk=yes blocked', { bulk: true }, /bulk=yes/],
    ['invalid concurrency fails', { concurrency: 'abc' }, /concurrency must be 1/],
    ['missing retry fails', { retry: null }, /retry must be 0/],
    ['unknown arguments fail validation', { unknown: ['--bad'] }, /unknown arguments/],
];

for (const [name, override, pattern] of invalidInputCases) {
    test(name, () => {
        const gate = loadModuleFresh();
        const validation = gate.validatePreviewInput(validArgs(override));
        assert.equal(validation.ok, false);
        assert.match(validation.errors.join('\n'), pattern);
    });
}

test('build request URL contains 4830746', () => {
    const gate = loadModuleFresh();
    const request = gate.buildFotMobDetailRequest(validArgs());
    assert.equal(request.method, 'GET');
    assert.equal(request.route, 'api_match_details');
    assert.match(request.url, /matchDetails/);
    assert.match(request.url, /matchId=4830746/);
});

test('build route plan defaults to html hydration, api fallback, and alternate plan-only', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildFotMobDetailRoutePlan(validArgs());
    assert.deepEqual(
        plan.map(route => route.route),
        ['html_hydration', 'api_match_details', 'alternate_route']
    );
    assert.match(plan[0].request.url, /\/match\/4830746$/);
    assert.match(plan[1].request.url, /\/api\/data\/matchDetails\?matchId=4830746$/);
    assert.match(plan[2].request.url, /\/api\/matchDetails\?matchId=4830746$/);
    assert.equal(plan[2].plan_only, true);
});

test('route=api_match_details builds only API route plus alternate plan', () => {
    const gate = loadModuleFresh();
    const plan = gate.buildFotMobDetailRoutePlan(validArgs({ route: 'api_match_details' }));
    assert.deepEqual(
        plan.map(route => route.route),
        ['api_match_details', 'alternate_route']
    );
});

test('build request rejects invalid input', () => {
    const gate = loadModuleFresh();
    assert.throws(() => gate.buildFotMobDetailRequest(validArgs({ externalId: '4830747' })), /INVALID_PREVIEW_INPUT/);
});

test('route=api_match_details fake JSON response preview succeeds', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let fetchCount = 0;
    const result = await runCli(gate, cliArgs({ route: 'api_match_details' }), {
        fetchImpl: async url => {
            fetchCount += 1;
            assert.match(url, /4830746/);
            assert.match(url, /api\/data\/matchDetails/);
            return createResponse(fakeJsonBody());
        },
    });

    assert.equal(result.status, 0);
    assert.equal(fetchCount, 1);
    assert.equal(result.payload.route_selector_enabled, true);
    assert.equal(result.payload.selected_route, 'api_match_details');
    assert.equal(result.payload.http_status, 200);
    assert.equal(result.payload.contains_match_id, true);
    assert.equal(result.payload.contains_home_team, true);
    assert.equal(result.payload.contains_away_team, true);
    assert.equal(result.payload.json_parse_ok, true);
    assert.equal(result.payload.looks_like_valid_match_detail, true);
    assert.ok(result.payload.top_level_keys.includes('content'));
    assert.ok(result.payload.candidate_raw_data_paths.includes('content.matchFacts'));
});

test('fake HTML __NEXT_DATA__ response preview succeeds', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const requestedUrls = [];
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async url => {
            requestedUrls.push(url);
            return createResponse(fakeHtmlBody(), {
                url,
                contentType: 'text/html; charset=utf-8',
            });
        },
    });

    assert.equal(result.status, 0);
    assert.deepEqual(requestedUrls, ['https://www.fotmob.com/match/4830746']);
    assert.equal(result.payload.selected_route, 'html_hydration');
    assert.equal(result.payload.attempted_routes[0].route, 'html_hydration');
    assert.equal(result.payload.attempted_routes[0].executed, true);
    assert.equal(result.payload.attempted_routes.at(-1).route, 'alternate_route');
    assert.equal(result.payload.attempted_routes.at(-1).executed, false);
    assert.equal(result.payload.hydration_parse_ok, true);
    assert.equal(result.payload.hydration_transform_ok, true);
    assert.equal(result.payload.hydration_or_json_markers.includes('__NEXT_DATA__'), true);
    assert.equal(result.payload.hydration_or_json_markers.includes('next_data_parser'), true);
    assert.equal(result.payload.contains_match_id, true);
    assert.equal(result.payload.contains_home_team, true);
    assert.equal(result.payload.contains_away_team, true);
    assert.equal(result.payload.looks_like_valid_match_detail, true);
    assert.equal(result.payload.body_printed, false);
    assert.equal(result.payload.body_saved, false);
});

test('route=auto falls back from missing hydration to fake API JSON', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const requestedUrls = [];
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async url => {
            requestedUrls.push(url);
            if (url.includes('/match/4830746')) {
                return createResponse('<html>Angers vs Strasbourg 4830746</html>', {
                    url,
                    contentType: 'text/html',
                });
            }
            return createResponse(fakeJsonBody(), {
                url,
                contentType: 'application/json',
            });
        },
    });

    assert.equal(result.status, 0);
    assert.deepEqual(requestedUrls, [
        'https://www.fotmob.com/match/4830746',
        'https://www.fotmob.com/api/data/matchDetails?matchId=4830746',
    ]);
    assert.equal(result.payload.selected_route, 'api_match_details');
    assert.equal(result.payload.attempted_routes.length, 3);
    assert.equal(result.payload.attempted_routes[0].looks_like_valid_match_detail, false);
    assert.equal(result.payload.attempted_routes[1].looks_like_valid_match_detail, true);
    assert.equal(result.payload.attempted_routes[2].route, 'alternate_route');
    assert.equal(result.payload.attempted_routes[2].executed, false);
});

test('invalid JSON response returns parse failure without printing body', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ route: 'api_match_details' }), {
        fetchImpl: async () =>
            createResponse('{not-json Angers Strasbourg 4830746', {
                contentType: 'application/json',
            }),
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.json_parse_ok, false);
    assert.equal(result.payload.hydration_parse_ok, false);
    assert.equal(result.payload.body_printed, false);
});

test('plain HTML without __NEXT_DATA__ is controlled invalid preview', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () =>
            createResponse('<html>Angers vs Strasbourg 4830746</html>', {
                contentType: 'text/html',
            }),
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.hydration_parse_ok, false);
    assert.equal(result.payload.looks_like_valid_match_detail, false);
});

test('extract preview handles null body and object headers', () => {
    const gate = loadModuleFresh();
    const extraction = gate.extractJsonOrHydrationPreview(null, '', {});
    assert.equal(extraction.contains_match_id, false);
    assert.equal(extraction.looks_like_valid_match_detail, false);

    const summary = gate.buildRawDetailPreviewSummary({
        input: validArgs(),
        request: { url: 'https://example.test/detail?matchId=4830746' },
        response: {
            statusCode: 200,
            url: 'https://example.test/final',
            headers: { 'Content-Type': 'application/json' },
        },
        body: fakeJsonBody(),
    });

    assert.equal(summary.content_type, 'application/json');
    assert.equal(summary.final_url, 'https://example.test/final');
    assert.equal(summary.ok, true);
});

test('summary handles missing headers, missing request url, and explicit error', () => {
    const gate = loadModuleFresh();
    const summary = gate.buildRawDetailPreviewSummary({
        input: validArgs({ networkAuthorization: false }),
        request: {},
        response: {},
        body: '',
        error: new Error('FETCH_FAILED'),
    });

    assert.equal(summary.external_network_used, false);
    assert.equal(summary.request_url, '');
    assert.equal(summary.final_url, '');
    assert.equal(summary.http_status, null);
    assert.equal(summary.content_type, '');
    assert.equal(summary.controlled_error, 'FETCH_FAILED');
    assert.equal(summary.network_authorization_used, false);
});

test('runCli --help prints usage and does not fetch', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--help'], {
        fetchImpl: async () => {
            throw new Error('fetch should not be called for help');
        },
    });

    assert.equal(result.status, 0);
    assert.match(result.stdout, /Usage:/);
});

test('runCli defaults to plan-only and does not use global fetch', async () => {
    const gate = loadModuleFresh();
    const originalFetch = global.fetch;
    let fetchCalled = false;
    global.fetch = async () => {
        fetchCalled = true;
        throw new Error('global fetch should not be called in plan-only mode');
    };

    try {
        const result = await runCli(gate, cliArgs());
        assert.equal(result.status, 1);
        assert.equal(fetchCalled, false);
        assert.equal(result.payload.plan_only, true);
        assert.equal(result.payload.route_selector_enabled, true);
        assert.equal(result.payload.selected_route, 'none');
        assert.equal(result.payload.attempted_routes[0].route, 'html_hydration');
        assert.equal(result.payload.attempted_routes[0].executed, false);
        assert.match(result.payload.controlled_error, /LIVE_PREVIEW_BLOCKED|PLAN_ONLY/);
    } finally {
        global.fetch = originalFetch;
    }
});

test('runCli validation failure returns controlled summary', async () => {
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs({ source: 'bad' }), {
        fetchImpl: async () => {
            throw new Error('fetch should not be called for invalid input');
        },
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.ok, false);
    assert.match(result.payload.errors.join('\n'), /unsupported source/);
    assert.equal(result.payload.would_write_db, false);
});

test('fetch unavailable returns controlled error summary', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const originalFetch = global.fetch;
    global.fetch = undefined;
    t.after(() => {
        global.fetch = originalFetch;
    });

    const result = await runCli(gate, cliArgs(), { allowRouteExecution: true });
    assert.equal(result.status, 1);
    assert.match(result.payload.controlled_error, /FETCH_UNAVAILABLE/);
    assert.equal(result.payload.body_saved, false);
});

test('fetch error returns controlled error summary without retry', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let fetchCount = 0;
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => {
            fetchCount += 1;
            throw new Error('NETWORK_DOWN');
        },
    });

    assert.equal(result.status, 1);
    assert.equal(fetchCount, 1);
    assert.match(result.payload.controlled_error, /NETWORK_DOWN/);
    assert.equal(result.payload.browser_used, false);
});

test('response without text method is handled as empty body', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => ({
            status: 204,
            ok: true,
            url: 'https://www.fotmob.com/api/data/matchDetails?matchId=4830746',
            headers: {},
        }),
    });

    assert.equal(result.status, 1);
    assert.equal(result.payload.body_byte_length, 0);
    assert.equal(result.payload.body_saved, false);
});

test('module can be imported as ESM URL without executing CLI main', async () => {
    const imported = await import(pathToFileURL(SCRIPT_PATH).href);
    assert.equal(typeof imported.default.runCli, 'function');
});

test('output safety flags remain false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });

    assert.equal(result.payload.body_printed, false);
    assert.equal(result.payload.body_saved, false);
    assert.equal(result.payload.would_write_raw_match_data, false);
    assert.equal(result.payload.would_write_db, false);
    assert.equal(result.payload.browser_used, false);
    assert.equal(result.payload.proxy_used, false);
    assert.equal(result.payload.raw_match_data_write_allowed, false);
    assert.equal(result.payload.db_write_allowed, false);
});

test('route selector summary exposes existing client integration flags', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async url =>
            createResponse(fakeHtmlBody(), {
                url,
                contentType: 'text/html; charset=utf-8',
            }),
    });

    assert.equal(result.payload.existing_client_integration.fotmob_api_client_considered, true);
    assert.equal(result.payload.existing_client_integration.fotmob_api_client_route_aligned, true);
    assert.equal(result.payload.existing_client_integration.fotmob_api_client_imported, false);
    assert.equal(result.payload.existing_client_integration.fotmob_strategy_hydration_considered, true);
    assert.equal(result.payload.existing_client_integration.next_data_parser_reused, true);
    assert.equal(result.payload.existing_client_integration.production_harvester_used, false);
    assert.equal(result.payload.existing_client_integration.legacy_backfill_used, false);
});

test('output body_printed=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.body_printed, false);
});

test('output body_saved=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.body_saved, false);
});

test('output would_write_raw_match_data=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.would_write_raw_match_data, false);
});

test('output would_write_db=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.would_write_db, false);
});

test('output browser_used=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.browser_used, false);
});

test('output proxy_used=false', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });
    assert.equal(result.payload.proxy_used, false);
});

test('controlled 403 error does not retry', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let fetchCount = 0;
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => {
            fetchCount += 1;
            return createResponse('Access denied cloudflare captcha', {
                status: 403,
                contentType: 'text/html',
            });
        },
    });

    assert.equal(result.status, 1);
    assert.equal(fetchCount, 1);
    assert.equal(result.payload.selected_route, 'none');
    assert.deepEqual(
        result.payload.attempted_routes.filter(route => route.executed).map(route => route.route),
        ['html_hydration']
    );
    assert.equal(result.payload.http_status, 403);
    assert.match(result.payload.controlled_error, /CONTROLLED_BLOCK_SIGNAL/);
    assert.equal(result.payload.browser_used, false);
    assert.equal(result.payload.proxy_used, false);
});

test('route=api_match_details fake 403 produces controlled error', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let fetchCount = 0;
    const result = await runCli(gate, cliArgs({ route: 'api_match_details' }), {
        fetchImpl: async url => {
            fetchCount += 1;
            assert.match(url, /api\/data\/matchDetails/);
            return createResponse(JSON.stringify({ code: 403, error: 'Forbidden' }), {
                url,
                status: 403,
                contentType: 'application/json',
            });
        },
    });

    assert.equal(result.status, 1);
    assert.equal(fetchCount, 1);
    assert.equal(result.payload.selected_route, 'none');
    assert.equal(result.payload.http_status, 403);
    assert.equal(result.payload.json_parse_ok, true);
    assert.match(result.payload.controlled_error, /CONTROLLED_BLOCK_SIGNAL:HTTP_403/);
    assert.equal(result.payload.body_printed, false);
    assert.equal(result.payload.body_saved, false);
});

test('no fs.writeFile / mkdir or child_process operations during preview', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, cliArgs(), {
        fetchImpl: async () => createResponse(fakeJsonBody()),
    });

    assert.equal(result.status, 0);
    assert.equal(result.payload.body_saved, false);
});

test('source audit: no DB client write', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source));
    assert.ok(!/\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bALTER\b|\bDROP\b|\bTRUNCATE\b/.test(source));
});

test('source audit: no child_process spawn', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"](?:node:)?child_process['"]/.test(source));
});

test('source audit: no native http or https request client', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"](?:node:)?https?['"]/.test(source));
    assert.ok(!/\bhttps?\.request\b/.test(source));
});

test('source audit: no ProductionHarvester', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/ProductionHarvester/.test(source));
});

test('source audit: no FotMobStrategy live harvest', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/FotMobStrategy/.test(source));
});

test('source audit: no raw ingest commit', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/raw_match_data_local_ingest/.test(source));
    assert.ok(!/backfill_historical_raw_match_data/.test(source));
});

test('source audit: no file writer calls', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/writeFile|createWriteStream|mkdir/.test(source));
});

test('source audit: no browser or proxy runtime imports', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/playwright|BrowserProvider|proxy runtime/i.test(source));
});
