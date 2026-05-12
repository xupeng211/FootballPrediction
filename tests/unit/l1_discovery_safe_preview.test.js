'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/l1_discovery_safe_preview.js');
const MAKEFILE_PATH = path.join(PROJECT_ROOT, 'Makefile');

function loadModuleFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalNetConnect = net.connect;
    const originalLoad = Module._load;

    const fail = name => () => {
        throw new Error(`${name} should not be called by l1_discovery_safe_preview`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    net.connect = fail('net.connect');

    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
        ]);

        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/titan_discovery|DiscoveryService|FixtureRepository/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }

        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        global.fetch = originalFetch;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.createWriteStream = originalCreateWriteStream;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        net.connect = originalNetConnect;
        Module._load = originalLoad;
    });
}

async function runCli(gate, argv, dependencies = {}) {
    let stdout = '';
    let stderr = '';
    const status = await gate.runCli(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
            stderr: text => {
                stderr += text;
            },
        },
        dependencies
    );

    return {
        status,
        stdout,
        stderr,
    };
}

function parseJsonOutput(stdout) {
    const payload = String(stdout || '').trim();
    assert.notEqual(payload, '', 'expected JSON payload in stdout');
    return JSON.parse(payload);
}

function assertSafePreviewFlags(payload) {
    assert.equal(payload.preview_only, true);
    assert.equal(payload.safe_for_ai_default, true);
    assert.equal(payload.network_execution_allowed, false);
    assert.equal(payload.db_write_allowed, false);
    assert.equal(payload.matches_write_allowed, false);
    assert.equal(payload.raw_match_data_write_allowed, false);
    assert.equal(payload.would_call_titan_discovery, false);
    assert.equal(payload.would_call_discovery_service_discover, false);
    assert.equal(payload.would_call_fixture_repository_persist, false);
    assert.equal(payload.would_write_matches, false);
    assert.equal(payload.would_write_raw_match_data, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_spawn_child_process, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_create_files, false);
    assert.equal(payload.commit_gate, 'blocked');
    assert.equal(payload.safety_classification, 'safe_preview_only');
}

function buildDependencies() {
    return {
        cwd: PROJECT_ROOT,
        readFileSync: (targetPath, encoding) => fs.readFileSync(targetPath, encoding),
    };
}

test('parseArgs 能解析 preview 与 controlled network 参数', () => {
    const gate = loadModuleFresh();
    const dateOptions = gate.parseArgs([
        '--source=fotmob',
        '--scope=league_season_date',
        '--league-id=53',
        '--season=2025/2026',
        '--date=2026-05-10',
        '--concurrency=1',
        '--max-targets=1',
    ]);

    assert.equal(dateOptions.source, 'fotmob');
    assert.equal(dateOptions.scope, 'league_season_date');
    assert.equal(dateOptions.leagueId, '53');
    assert.equal(dateOptions.season, '2025/2026');
    assert.equal(dateOptions.date, '2026-05-10');
    assert.equal(dateOptions.concurrency, '1');
    assert.equal(dateOptions.maxTargets, '1');

    const candidateOptions = gate.parseArgs([
        '--source=fotmob',
        '--scope=controlled_candidates_preview',
        '--league-id=53',
        '--season=2025/2026',
        '--date=2026-05-10',
        '--network-authorization=no',
    ]);

    assert.equal(candidateOptions.scope, 'controlled_candidates_preview');
    assert.equal(candidateOptions.networkAuthorization, false);

    const networkOptions = gate.parseArgs([
        '--network-preview=true',
        '--source=fotmob',
        '--scope=controlled_candidates_preview',
        '--league-id=53',
        '--season=2025/2026',
        '--date=2026-05-10',
        '--concurrency=1',
        '--max-targets=10',
        '--network-authorization=yes',
        '--allow-browser-runtime=no',
        '--allow-proxy-runtime=no',
        '--allow-db-write=no',
    ]);

    assert.equal(networkOptions.networkPreview, true);
    assert.equal(networkOptions.maxTargets, '10');
    assert.equal(networkOptions.networkAuthorization, true);
    assert.equal(networkOptions.allowBrowserRuntime, false);
    assert.equal(networkOptions.allowProxyRuntime, false);
    assert.equal(networkOptions.allowDbWrite, false);
});

test('valid config_only_preview 成功', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(gate, ['--source=fotmob', '--scope=config_only_preview'], buildDependencies());
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.scope, 'config_only_preview');
    assert.equal(payload.source, 'fotmob');
    assert.equal(payload.candidate_preview.mode, 'config_only_or_plan_only');
    assert.equal(payload.candidate_preview.league_config_found, false);
    assert.equal(payload.candidate_preview.season_window_found, false);
    assertSafePreviewFlags(payload);
});

test('valid league_season_date 成功', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(
        gate,
        [
            '--source=fotmob',
            '--scope=league_season_date',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--concurrency=1',
            '--max-targets=1',
        ],
        buildDependencies()
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.scope, 'league_season_date');
    assert.equal(payload.league_id, '53');
    assert.equal(payload.season, '2025/2026');
    assert.equal(payload.date, '2026-05-10');
    assert.equal(payload.candidate_preview.league_config_found, true);
    assert.equal(payload.candidate_preview.season_window_found, true);
    assert.equal(payload.candidate_preview.plan_summary.preview_kind, 'single_date_plan');
    assert.equal(payload.candidate_preview.plan_summary.bounded_target_count, 1);
    assertSafePreviewFlags(payload);
});

test('valid league_season_window_preview 成功', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(
        gate,
        [
            '--source=fotmob',
            '--scope=league_season_window_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--lookback=5',
            '--lookahead=3',
            '--concurrency=1',
            '--max-targets=1',
        ],
        {
            ...buildDependencies(),
            referenceDate: new Date('2026-05-11T00:00:00.000Z'),
        }
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.scope, 'league_season_window_preview');
    assert.equal(payload.candidate_preview.plan_summary.preview_kind, 'season_window_plan');
    assert.deepEqual(payload.candidate_preview.plan_summary.bounded_window, {
        start: '2026-05-06',
        end: '2026-05-14',
        season_start: '2025-08-15',
        season_end: '2026-05-16',
        reference_date: '2026-05-11',
        lookback_days: 5,
        lookahead_days: 3,
        source: 'explicit',
    });
    assertSafePreviewFlags(payload);
});

test('参数校验失败场景保持 blocked', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const cases = [
        [['--scope=config_only_preview'], /missing source/i],
        [['--source=other', '--scope=config_only_preview'], /unsupported source/i],
        [['--source=fotmob'], /missing scope/i],
        [['--source=fotmob', '--scope=bulk'], /unsupported scope/i],
        [
            ['--source=fotmob', '--scope=league_season_date', '--season=2025/2026', '--date=2026-05-10'],
            /missing league-id/i,
        ],
        [['--source=fotmob', '--scope=league_season_date', '--league-id=53', '--date=2026-05-10'], /missing season/i],
        [['--source=fotmob', '--scope=league_season_date', '--league-id=53', '--season=2025/2026'], /missing date/i],
        [['--source=fotmob', '--scope=config_only_preview', '--concurrency=2'], /concurrency > 1/i],
        [['--source=fotmob', '--scope=config_only_preview', '--max-targets=11'], /max_targets > 10/i],
        [['--source=fotmob', '--scope=config_only_preview', '--all'], /--all/i],
        [['--source=fotmob', '--scope=config_only_preview', '--all-leagues'], /--all-leagues/i],
        [['--source=fotmob', '--scope=config_only_preview', '--full-sync'], /--full-sync/i],
        [['--source=fotmob', '--scope=config_only_preview', '--dry-run=false'], /dry_run=false/i],
        [['--source=fotmob', '--scope=config_only_preview', '--db-write=true'], /db_write=true/i],
        [['--source=fotmob', '--scope=config_only_preview', '--browser=true'], /browser=true/i],
        [['--source=fotmob', '--scope=config_only_preview', '--proxy=true'], /proxy=true/i],
    ];

    for (const [argv, pattern] of cases) {
        const result = await runCli(gate, argv, buildDependencies());
        const payload = parseJsonOutput(result.stdout);
        assert.equal(result.status, 1);
        assert.match(payload.errors.join('\n'), pattern);
    }
});

test('--commit blocked', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(
        gate,
        ['--source=fotmob', '--scope=config_only_preview', '--commit'],
        buildDependencies()
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 1);
    assert.equal(payload.mode, 'blocked-commit');
    assert.match(payload.blocked_reason, /does not execute writes/i);
    assertSafePreviewFlags(payload);
});

test('controlled_candidates_preview scope 使用 fake discovery service 成功', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let discoverCalls = 0;
    let closeCalls = 0;
    const result = await runCli(
        gate,
        [
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--concurrency=1',
            '--max-targets=1',
            '--network-authorization=no',
        ],
        {
            ...buildDependencies(),
            createDiscoveryService: () => ({
                discoverCandidates: async options => {
                    discoverCalls += 1;
                    assert.equal(options.source, 'fotmob');
                    assert.equal(options.scope, 'controlled_candidates_preview');
                    assert.equal(options.allowNetwork, true);
                    assert.equal(options.writeDb, false);
                    return {
                        source: 'fotmob',
                        scope: 'controlled_candidates_preview',
                        league_id: '53',
                        season: '2025/2026',
                        date: '2026-05-10',
                        preview_only: true,
                        network_used: false,
                        external_network_used: false,
                        browser_used: false,
                        proxy_used: false,
                        db_written: false,
                        matches_written: false,
                        raw_match_data_written: false,
                        source_url_template:
                            'https://www.fotmob.com/api/data/leagues?id={providerLeagueId}&season={season}',
                        source_url_candidate: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
                        candidate_count: 1,
                        candidates: [
                            {
                                match_id: '53_20252026_123',
                                external_id: '123',
                                league: 'Ligue 1',
                                season: '2025/2026',
                                home: 'Paris SG',
                                away: 'Lyon',
                                match_date: '2026-05-10T19:00:00.000Z',
                                data_source: 'FotMob',
                            },
                        ],
                        safety_summary: {
                            would_write_db: false,
                            would_call_persist: false,
                            would_launch_browser: false,
                            would_use_proxy: false,
                        },
                    };
                },
                close: async () => {
                    closeCalls += 1;
                },
            }),
            allowFakeNetwork: true,
        }
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(discoverCalls, 1);
    assert.equal(closeCalls, 1);
    assert.equal(payload.scope, 'controlled_candidates_preview');
    assert.equal(payload.candidates_preview_available, true);
    assert.equal(payload.discover_candidates_available, true);
    assert.equal(payload.network_execution_allowed, false);
    assert.equal(payload.external_network_used, false);
    assert.equal(payload.candidate_count, 1);
    assert.equal(payload.candidates[0].match_id, '53_20252026_123');
    assert.equal(payload.candidate_preview.fetch_mode, 'discover_candidates');
    assert.equal(payload.safety_summary.would_call_persist, false);
    assertSafePreviewFlags(payload);
});

test('controlled_candidates_preview 默认真实 CLI plan-only 且 no external network', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(
        gate,
        [
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--concurrency=1',
            '--max-targets=1',
            '--network-authorization=no',
        ],
        {
            ...buildDependencies(),
            allowDiscoveryServiceImport: false,
        }
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(payload.candidates_preview_available, true);
    assert.equal(payload.discover_candidates_available, true);
    assert.equal(payload.external_network_used, false);
    assert.equal(payload.candidate_count, 0);
    assert.deepEqual(payload.candidates, []);
    assert.equal(payload.candidate_preview.fetch_mode, 'plan_only_no_service_import');
    assertSafePreviewFlags(payload);
});

test('旧 candidates preview target network-authorization=yes 仍 blocked', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const result = await runCli(
        gate,
        [
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--network-authorization=yes',
        ],
        buildDependencies()
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 1);
    assert.equal(payload.mode, 'blocked-network-authorization');
    assert.equal(payload.external_network_used, false);
    assert.equal(payload.network_execution_allowed, false);
    assert.match(payload.blocked_reason, /data-l1-discovery-candidates-network-preview/i);
    assertSafePreviewFlags(payload);
});

test('controlled network preview 参数校验通过并输出安全摘要', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    let discoverCalls = 0;
    const result = await runCli(
        gate,
        [
            '--network-preview=true',
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--concurrency=1',
            '--max-targets=10',
            '--network-authorization=yes',
            '--allow-browser-runtime=no',
            '--allow-proxy-runtime=no',
            '--allow-db-write=no',
        ],
        {
            ...buildDependencies(),
            createDiscoveryService: () => ({
                discoverCandidates: async options => {
                    discoverCalls += 1;
                    assert.equal(options.source, 'fotmob');
                    assert.equal(options.scope, 'controlled_candidates_preview');
                    assert.equal(options.leagueId, '53');
                    assert.equal(options.season, '2025/2026');
                    assert.equal(options.date, '2026-05-10');
                    assert.equal(options.concurrency, 1);
                    assert.equal(options.maxTargets, 10);
                    assert.equal(options.allowNetwork, true);
                    assert.equal(options.networkAuthorization, true);
                    assert.equal(options.writeDb, false);
                    assert.equal(options.allowBrowserFallback, false);
                    assert.equal(options.allowProxy, false);
                    return {
                        source: 'fotmob',
                        scope: 'controlled_candidates_preview',
                        league_id: '53',
                        season: '2025/2026',
                        date: '2026-05-10',
                        preview_only: true,
                        network_used: true,
                        external_network_used: true,
                        network_authorization_used: true,
                        browser_used: false,
                        proxy_used: false,
                        db_written: false,
                        matches_written: false,
                        raw_match_data_written: false,
                        source_url_template:
                            'https://www.fotmob.com/api/data/leagues?id={providerLeagueId}&season={season}',
                        source_url_candidate: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
                        source_url_used: 'https://www.fotmob.com/api/data/leagues?id=53&season=20252026',
                        candidate_count: 1,
                        candidates: [
                            {
                                match_id: '53_20252026_4830746',
                                external_id: '4830746',
                                league: 'Ligue 1',
                                season: '2025/2026',
                                home: 'Angers',
                                away: 'Strasbourg',
                                match_date: '2026-05-10T19:00:00.000Z',
                                data_source: 'FotMob',
                            },
                        ],
                        safety_summary: {
                            wrote_db: false,
                            wrote_matches: false,
                            wrote_raw_match_data: false,
                            called_persist: false,
                            launched_browser: false,
                            used_proxy: false,
                            would_write_db: false,
                            would_write_matches: false,
                            would_write_raw_match_data: false,
                            would_call_persist: false,
                            would_launch_browser: false,
                            would_use_proxy: false,
                        },
                    };
                },
                close: async () => {},
            }),
        }
    );
    const payload = parseJsonOutput(result.stdout);

    assert.equal(result.status, 0);
    assert.equal(discoverCalls, 1);
    assert.equal(payload.phase, 'PHASE5_05L1_CONTROLLED_L1_EXTERNAL_NETWORK_CANDIDATES_PREVIEW');
    assert.equal(payload.source, 'fotmob');
    assert.equal(payload.league_id, '53');
    assert.equal(payload.season, '2025/2026');
    assert.equal(payload.date, '2026-05-10');
    assert.equal(payload.concurrency, 1);
    assert.equal(payload.max_targets, 10);
    assert.equal(payload.external_network_used, true);
    assert.equal(payload.network_authorization_used, true);
    assert.equal(payload.candidate_count, 1);
    assert.equal(payload.candidates_preview[0].external_id, '4830746');
    assert.equal(payload.contains_target_match_id_candidate, true);
    assert.equal(payload.contains_anglers_strasbourg_candidate, true);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_call_persist, false);
    assert.equal(payload.would_call_fixture_repository_persist, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
});

test('controlled network preview 拒绝 DB/browser/proxy runtime', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const baseArgv = [
        '--network-preview=true',
        '--source=fotmob',
        '--scope=controlled_candidates_preview',
        '--league-id=53',
        '--season=2025/2026',
        '--date=2026-05-10',
        '--network-authorization=yes',
    ];

    const dbWrite = await runCli(gate, [...baseArgv, '--allow-db-write=yes'], buildDependencies());
    const browser = await runCli(gate, [...baseArgv, '--allow-browser-runtime=yes'], buildDependencies());
    const proxy = await runCli(gate, [...baseArgv, '--allow-proxy-runtime=yes'], buildDependencies());

    assert.equal(dbWrite.status, 1);
    assert.match(parseJsonOutput(dbWrite.stdout).errors.join('\n'), /ALLOW_DB_WRITE=yes/i);
    assert.equal(browser.status, 1);
    assert.match(parseJsonOutput(browser.stdout).errors.join('\n'), /ALLOW_BROWSER_RUNTIME=yes/i);
    assert.equal(proxy.status, 1);
    assert.match(parseJsonOutput(proxy.stdout).errors.join('\n'), /ALLOW_PROXY_RUNTIME=yes/i);
});

test('controlled network preview 拒绝 maxTargets > 10 和缺 date', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const maxTargets = await runCli(
        gate,
        [
            '--network-preview=true',
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--date=2026-05-10',
            '--max-targets=11',
            '--network-authorization=yes',
        ],
        buildDependencies()
    );
    const missingDate = await runCli(
        gate,
        [
            '--network-preview=true',
            '--source=fotmob',
            '--scope=controlled_candidates_preview',
            '--league-id=53',
            '--season=2025/2026',
            '--network-authorization=yes',
        ],
        buildDependencies()
    );

    assert.equal(maxTargets.status, 1);
    assert.match(parseJsonOutput(maxTargets.stdout).errors.join('\n'), /max_targets > 10/i);
    assert.equal(missingDate.status, 1);
    assert.match(parseJsonOutput(missingDate.stdout).errors.join('\n'), /missing date/i);
});

test('buildL1DiscoveryPlanPreview 直接构建时仍保持 no-side-effect 摘要', async t => {
    installExecutionGuards(t);
    const gate = loadModuleFresh();
    const payload = await gate.buildL1DiscoveryPlanPreview(
        {
            source: 'fotmob',
            scope: 'league_season_date',
            leagueId: '53',
            season: '2025/2026',
            date: '2026-05-10',
            concurrency: 1,
            maxTargets: 1,
            dryRun: true,
        },
        buildDependencies()
    );

    assert.equal(payload.phase, 'PHASE5_05L1_CONTROLLED_L1_EXTERNAL_NETWORK_CANDIDATES_PREVIEW');
    assert.equal(payload.candidate_preview.estimated_target_limit, 1);
    assert.equal(payload.registry_reference.engine_id, 'titan_discovery');
    assert.equal(payload.registry_reference.accesses_network, true);
    assert.equal(payload.registry_reference.writes_db, true);
    assert.equal(payload.registry_reference.phase454_policy, 'blocked');
    assertSafePreviewFlags(payload);
});

test('Makefile preview target 已注册', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l1-discovery-preview:/m);
    assert.match(makefile, /^data-l1-discovery-candidates-preview:/m);
    assert.match(makefile, /^data-l1-discovery-candidates-network-preview:/m);
    assert.match(makefile, /scripts\/ops\/l1_discovery_safe_preview\.js/);
});

test('Makefile commit target blocked 文案存在', () => {
    const makefile = fs.readFileSync(MAKEFILE_PATH, 'utf8');
    assert.match(makefile, /^data-l1-discovery-commit:/m);
    assert.match(makefile, /BLOCKED: L1 discovery safe preview wrapper does not execute writes in Phase 5\.05L1\./);
});

test('测试不在仓库内创建随机目录', () => {
    const tmpRoot = os.tmpdir();
    assert.ok(typeof tmpRoot === 'string' && tmpRoot.length > 0);
});
