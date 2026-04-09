'use strict';

const assert = require('node:assert/strict');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngineImpl');
const { ProxyProvider } = require('../../src/infrastructure/network/ProxyProvider');

const MIXED_LEAGUES = [
    'Premier League',
    'La Liga',
    'Serie A',
    'Bundesliga',
    'Ligue 1',
    'Eredivisie',
    'Primeira Liga',
    'Belgian Pro League',
    'Super Lig',
    'Scottish Premiership',
];

const TOTAL_MATCHES = 200;

function buildPreparedTargets() {
    return Array.from({ length: TOTAL_MATCHES }, (_, index) => ({
        target: {
            leagueId: index + 1,
            league: {
                id: (index % MIXED_LEAGUES.length) + 1,
                name: MIXED_LEAGUES[index % MIXED_LEAGUES.length],
            },
            dbSeason: '2025/2026',
        },
        pendingMatches: [{ match_id: `${index + 1}` }],
        desiredLimit: 1,
    }));
}

function resolveScenario(matchIndex) {
    if (matchIndex >= 61 && matchIndex <= 82) {
        return { type: '403', statusCode: 403, reason: 'Forbidden', latencyMs: 8 };
    }

    if (matchIndex >= 41 && matchIndex <= 60 && matchIndex % 3 === 0) {
        return { type: '503', statusCode: 503, reason: 'HTTP_503', latencyMs: 10 };
    }

    if (matchIndex >= 120 && matchIndex <= 140 && matchIndex % 4 === 0) {
        return { type: 'timeout', statusCode: null, reason: 'timeout', latencyMs: 12 };
    }

    return { type: 'success', statusCode: 200, reason: 'OK', latencyMs: 15 };
}

function formatPool(provider) {
    const stats = provider.getStats();
    return `available=${stats.available}/${stats.total} cooling=${stats.cooling} healthy=${stats.healthy} activeLeases=${stats.activeLeases}`;
}

async function main() {
    let virtualNow = Date.now();
    const preparedTargets = buildPreparedTargets();
    const activePorts = new Set();
    const report = {
        successes: 0,
        failures403: 0,
        failures503: 0,
        failuresTimeout: 0,
        suspendCount: 0,
        resumeCount: 0,
        sawDynamicBackoff: false,
        sawProxyClamp: false,
        maxActiveProxyPorts: 0,
    };

    const provider = new ProxyProvider({
        now: () => virtualNow,
        healthCheckIntervalMs: 0,
        criticalErrorCooldownMs: 1_800_000,
        http503CooldownMs: 90_000,
        failureCooldownMs: 60_000,
        minHealthScore: 60,
        probes: {
            tcp: async () => ({ ok: true }),
            http: async () => ({ ok: true, statusCode: 204, latencyMs: 4 }),
        },
    });

    const logger = {
        info(event, payload = {}) {
            if (event === 'recon_dynamic_concurrency_adjusted') {
                if (payload.reason === 'network_failure') {
                    report.sawDynamicBackoff = true;
                }
                if (payload.reason === 'proxy_feedback' && payload.proxyAvailable < payload.previousMaxActiveWorkers) {
                    report.sawProxyClamp = true;
                }
                console.log(
                    `[ADAPT] reason=${payload.reason} workers=${payload.previousMaxActiveWorkers ?? payload.maxActiveWorkers}->${payload.maxActiveWorkers} ceiling=${payload.ceiling} proxyAvailable=${payload.proxyAvailable ?? 'n/a'}`
                );
            }

            if (event === 'recon_league_worker_start') {
                console.log(
                    `[MATRIX] start league=${payload.league} proxyPort=${payload.proxyPort ?? 'none'} activeLeagueWorkers=${payload.activeLeagueWorkers} allowedLeagueWorkers=${payload.allowedLeagueWorkers} proxyAvailable=${payload.proxyAvailable ?? 'n/a'}`
                );
            }

            if (event === 'recon_engine_suspend_heartbeat') {
                console.log(
                    `[SUSPEND] heartbeat available=${payload.available}/${payload.total} cooling=${payload.cooling} reason=${payload.reason}`
                );
            }

            if (event === 'recon_engine_resumed') {
                report.resumeCount += 1;
                console.log(
                    `[RESUME] available=${payload.available}/${payload.total} previousSuspendedAt=${payload.previousSuspendedAt}`
                );
            }
        },
        warn(event, payload = {}) {
            if (event === 'recon_dynamic_concurrency_adjusted') {
                report.sawDynamicBackoff = true;
                console.log(
                    `[ADAPT] reason=${payload.reason} workers=${payload.previousMaxActiveWorkers}->${payload.maxActiveWorkers} ceiling=${payload.ceiling} proxyAvailable=${payload.proxyAvailable ?? 'n/a'} error=${payload.error ?? 'n/a'}`
                );
            }

            if (event === 'recon_engine_suspended') {
                report.suspendCount += 1;
                console.log(
                    `[SUSPEND] enter available=${payload.available}/${payload.total} cooling=${payload.cooling} reason=${payload.reason}`
                );
            }
        },
        error(event, payload = {}) {
            if (event === 'recon_matrix_target_failed') {
                console.log(
                    `[ERROR] league=${payload.league} proxyPort=${payload.proxyPort ?? 'none'} statusCode=${payload.statusCode ?? 'n/a'} message=${payload.error}`
                );
            }
        },
    };

    provider.on('alert', payload => {
        if (payload.type === 'proxy_cooled_down' || payload.type === 'proxy_health_score_blocked') {
            console.log(
                `[POOL] alert=${payload.type} port=${payload.port} healthScore=${payload.healthScore ?? 'n/a'} cooldownMs=${payload.cooldownMs ?? 'n/a'} ${formatPool(provider)}`
            );
        }
    });

    const proxyRotator = {
        proxyProvider: provider,
        getHealthStatus() {
            return provider.getStats();
        },
    };

    const engine = new ReconEngine({
        logger,
        proxyRotator,
        defaultReconConcurrency: 22,
        dynamicConcurrencyInitial: 5,
        dynamicConcurrencySuccessWindow: 2,
        minimumReadyProxyCount: 2,
        suspendPollIntervalMs: 1,
    });

    const originalRunHealthCheck = provider.runHealthCheck.bind(provider);
    provider.runHealthCheck = async () => {
        if (provider.getStats().available < 2) {
            virtualNow += 10 * 60 * 1000;
        }
        return originalRunHealthCheck();
    };

    let leaseSequence = 0;
    engine.navigatorFactory = async () => {
        const lease = await provider.acquire({
            consumer: 'recon-stress',
            sessionKey: `recon-stress-${++leaseSequence}`,
            sticky: false,
        });

        activePorts.add(lease.proxy.port);
        report.maxActiveProxyPorts = Math.max(report.maxActiveProxyPorts, activePorts.size);
        console.log(
            `[PORT] acquire proxyPort=${lease.proxy.port} activeProxyPorts=${activePorts.size} ${formatPool(provider)}`
        );

        return {
            proxyPort: lease.proxy.port,
            ownsNavigator: true,
            navigator: {
                proxy: { port: lease.proxy.port },
                async ensureBrowserHealthy() {},
                async close() {
                    activePorts.delete(lease.proxy.port);
                    await provider.release(lease.id);
                    console.log(
                        `[PORT] release proxyPort=${lease.proxy.port} activeProxyPorts=${activePorts.size} ${formatPool(provider)}`
                    );
                },
            },
        };
    };

    engine.buildScanTargets = async () => preparedTargets.map(item => item.target);
    engine.taskPlanner = {
        prepareReconPendingTargets: async () => preparedTargets,
    };
    engine._runReconTarget = async (target, options = {}) => {
        const matchIndex = Number(options.pendingMatches?.[0]?.match_id || target.leagueId || 0);
        const scenario = resolveScenario(matchIndex);
        const proxyPort = Number(options.navigator?.proxy?.port || 0) || null;

        await new Promise(resolve => {
            setTimeout(resolve, scenario.type === 'success' ? 6 : 4);
        });

        if (scenario.type === 'success') {
            report.successes += 1;
            await provider.reportPortSuccess(proxyPort, { statusCode: 200, latencyMs: scenario.latencyMs });
            return {
                pendingTotal: 1,
                linked: 1,
                mismatched: 0,
                sourceSeason: '2025/2026',
                sourceUrl: `stress://${target.league.name.toLowerCase().replace(/\s+/g, '-')}`,
                candidateCount: 1,
            };
        }

        if (scenario.type === '403') {
            report.failures403 += 1;
        } else if (scenario.type === '503') {
            report.failures503 += 1;
        } else {
            report.failuresTimeout += 1;
        }

        await provider.reportPortFailure(proxyPort, {
            statusCode: scenario.statusCode,
            reason: scenario.reason,
        });

        const error = new Error(scenario.reason);
        error.statusCode = scenario.statusCode;
        throw error;
    };

    const result = await engine.runReconMatrix({
        season: '2025/2026',
        concurrency: 1,
        leagueConcurrency: 22,
        leagueStartupStaggerMs: 0,
        limit: TOTAL_MATCHES,
    });

    console.log(
        '[REPORT] result=' +
            JSON.stringify({
                scannedLeagues: result.scannedLeagues,
                linked: result.linked,
                mismatched: result.mismatched,
                errors: result.errors.length,
            })
    );
    console.log('[REPORT] counters=' + JSON.stringify(report));
    console.log('[REPORT] pool=' + JSON.stringify(provider.getStats()));

    assert.equal(result.perLeague.length + result.errors.length, TOTAL_MATCHES);
    assert.ok(report.failures403 > 0);
    assert.ok(report.failures503 > 0);
    assert.ok(report.failuresTimeout > 0);
    assert.ok(report.sawDynamicBackoff);
    assert.ok(report.suspendCount > 0);
    assert.ok(report.resumeCount > 0);
    assert.ok(report.maxActiveProxyPorts >= 5);
    assert.equal(engine.getRuntimeState().status, 'RUNNING');
}

main().catch(error => {
    console.error('[STRESS-FAIL]', error);
    process.exitCode = 1;
});
