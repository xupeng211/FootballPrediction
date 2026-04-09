'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconMatrixFlow } = require('../../src/infrastructure/recon/services/ReconMatrixFlow');
const { reconMatchExtractor } = require('../../src/infrastructure/recon/services/ReconMatchExtractor');

describe('ReconMatrixFlow', () => {
    it('应将 season_mirror 与 pure_protocol source 归一化为 protocol_extract', () => {
        const flow = { ...reconMatrixFlow };

        assert.strictEqual(
            flow._normalizeMappingMethod({
                method: 'season_mirror',
                candidate: { source: 'pure_protocol_archive:xbsqV0go' },
            }),
            'protocol_extract'
        );
    });

    it('应保留数据库白名单中的 mapping_method', () => {
        const flow = { ...reconMatrixFlow };

        assert.strictEqual(
            flow._normalizeMappingMethod({
                method: 'exact',
                candidate: { source: 'pure_protocol_archive:xbsqV0go' },
            }),
            'exact'
        );
    });

    it('SOURCE_EMPTY 回退到本地字典时应尊重 matchLimit', async () => {
        const captured = [];
        const flow = {
            ...reconMatrixFlow,
            defaultReconConcurrency: 2,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            mirrorManager: { buildSeasonMirror: () => new Map() },
            taskPlanner: {
                resolveReconPolicy: () => ({ effectiveConfidenceThreshold: 0.75 }),
                selectProcessablePendingMatches: () => {
                    throw new Error('不应进入 selectProcessablePendingMatches');
                },
            },
            _primeLeagueDictionary: async () => [{ remote_name: 'Alpha', local_team_name: 'Alpha' }],
            _canUseLocalDictionaryFallback: () => true,
            _shouldUseLocalDictionaryOnly: () => false,
            _selectCandidateSourceWithLocalFallback: async () => ({
                candidates: [],
                source: {
                    season: '2025/2026',
                    url: 'https://example.com/results/',
                },
                extractResult: {
                    sourceState: 'SOURCE_EMPTY',
                },
            }),
            _runLocalDictionaryOnlyTarget: async (_target, pendingMatches) => {
                captured.push(pendingMatches.map(match => match.match_id));
                return {
                    pendingTotal: pendingMatches.length,
                    linked: 0,
                    mismatched: pendingMatches.length,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'dictionary://recon/1/2025%2F2026',
                    candidateCount: pendingMatches.length,
                    effectiveConfidenceThreshold: 0.75,
                };
            },
            _buildLocalDictionarySourceUrl: () => 'dictionary://recon/1/2025%2F2026',
        };

        const result = await flow._runReconTarget(
            {
                leagueId: 1,
                dbSeason: '2025/2026',
                season: '2025/2026',
                league: { id: 1, name: 'Test League' },
            },
            {
                pendingMatches: [
                    { match_id: 'm3', pipeline_status: 'harvested' },
                    { match_id: 'm1', pipeline_status: 'harvested' },
                    { match_id: 'm2', pipeline_status: 'harvested' },
                ],
                matchLimit: 2,
            }
        );

        assert.deepStrictEqual(captured, [['m1', 'm2']]);
        assert.strictEqual(result.pendingTotal, 2);
        assert.strictEqual(result.mismatched, 2);
    });

    it('全量 RECON_MISMATCH 也应先回源选择 source，不得被本地字典短路', async () => {
        const selectedCalls = [];
        const persisted = [];
        const flow = {
            ...reconMatrixFlow,
            baseUrl: 'https://www.oddsportal.com',
            defaultReconConcurrency: 1,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            mirrorManager: { buildSeasonMirror: () => new Map() },
            taskPlanner: {
                resolveReconPolicy: () => ({ effectiveConfidenceThreshold: 0.75 }),
                selectProcessablePendingMatches: (pendingMatches, _candidates, _threshold, matchLimit) =>
                    Number.isInteger(matchLimit) && matchLimit > 0
                        ? pendingMatches.slice(0, matchLimit)
                        : pendingMatches,
            },
            matchExtractor: reconMatchExtractor,
            _primeLeagueDictionary: async () => [{ remote_name: 'Alpha', local_team_name: 'Alpha' }],
            _canUseLocalDictionaryFallback: () => true,
            _runLocalDictionaryOnlyTarget: async () => {
                throw new Error('不应在全量 mismatch 时直接短路到本地字典');
            },
            _selectCandidateSourceWithLocalFallback: async (_target, pendingMatches) => {
                selectedCalls.push(pendingMatches.map(match => match.match_id));
                return {
                    candidates: [
                        {
                            hash: 'AbCd1234',
                            url: 'https://www.oddsportal.com/football/test-country/test-league/alpha-beta-AbCd1234/',
                            homeTeam: 'Alpha',
                            awayTeam: 'Beta',
                            matchDate: '2026-04-05T05:00:00.000Z',
                            source: 'current_results_dom',
                        },
                    ],
                    source: {
                        season: '2025/2026',
                        url: 'https://www.oddsportal.com/football/test-country/test-league/results/',
                    },
                    seasonMirror: new Map(),
                };
            },
            _findBestCandidate: () => ({
                candidate: {
                    hash: 'AbCd1234',
                    url: 'https://www.oddsportal.com/football/test-country/test-league/alpha-beta-AbCd1234/',
                    homeTeam: 'Alpha',
                    awayTeam: 'Beta',
                    matchDate: '2026-04-05T05:00:00.000Z',
                    source: 'current_results_dom',
                },
                confidence: 1,
                method: 'exact',
                isReversed: false,
            }),
            _createReconRunId: () => 'run-remote-first',
            _shouldEmitReconProgressSnapshot: () => false,
            _emitReconProgressSnapshot() {},
            _persistReconBatches: async (mappings, mismatches) => {
                persisted.push({ mappings, mismatches });
                return {
                    linkedApplied: mappings.length,
                    mismatchUpdated: mismatches.length,
                };
            },
        };

        const result = await flow._runReconTarget(
            {
                leagueId: 223,
                dbSeason: '2025/2026',
                season: '2025/2026',
                resultsUrl: 'https://www.oddsportal.com/football/test-country/test-league/results/',
                league: { id: 223, name: 'J1 League' },
            },
            {
                pendingMatches: [
                    {
                        match_id: 'm2',
                        pipeline_status: 'RECON_MISMATCH',
                        home_team: 'Alpha',
                        away_team: 'Beta',
                        match_date: '2026-04-05T05:00:00.000Z',
                    },
                    {
                        match_id: 'm1',
                        pipeline_status: 'RECON_MISMATCH',
                        home_team: 'Alpha',
                        away_team: 'Beta',
                        match_date: '2026-04-05T05:00:00.000Z',
                    },
                ],
                matchLimit: 1,
            }
        );

        assert.deepStrictEqual(selectedCalls, [['m1', 'm2']]);
        assert.strictEqual(persisted.length, 1);
        assert.strictEqual(persisted[0].mappings.length, 1);
        assert.strictEqual(result.pendingTotal, 1);
        assert.strictEqual(result.linked, 1);
    });

    it('linked 前应先把 h2h 候选洗白为 canonical URL', async () => {
        const flow = {
            ...reconMatrixFlow,
            baseUrl: 'https://www.oddsportal.com',
            logger: { info() {}, warn() {}, error() {} },
            matchExtractor: reconMatchExtractor,
            _findBestCandidate: () => ({
                candidate: {
                    hash: 'QwErTy12',
                    url: 'https://www.oddsportal.com/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12',
                    homeTeam: 'Kashiwa Reysol',
                    awayTeam: 'Yokohama F.Marinos',
                    matchDate: '2026-04-05T05:00:00.000Z',
                    source: 'current_results_dom',
                },
                confidence: 1,
                method: 'exact',
                isReversed: false,
            }),
        };

        const outcome = await flow._reconcilePendingMatch(
            {
                match_id: '223_20252026_4691098',
                home_team: 'Kashiwa Reysol',
                away_team: 'Yokohama F.Marinos',
                match_date: '2026-04-05T05:00:00.000Z',
                pipeline_status: 'harvested',
            },
            [],
            {
                dbSeason: '2025/2026',
                resultsUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
                reconSourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
                league: { name: 'J1 League' },
            },
            0.15,
            null
        );

        assert.strictEqual(outcome.status, 'linked');
        assert.strictEqual(
            outcome.mapping.full_url,
            'https://www.oddsportal.com/football/japan/j1-league/kashiwa-reysol-yokohama-f-marinos-QwErTy12/'
        );
    });

    it('应将 results、fixtures、search 三路候选合并为统一候选池', async () => {
        const flow = {
            ...reconMatrixFlow,
            logger: { info() {}, warn() {}, error() {} },
            taskPlanner: {
                sampleSize: 2,
                filterPlaceholderFixtures(matches) {
                    return matches;
                },
                async selectCandidateSource() {
                    return {
                        source: {
                            season: '2025/2026',
                            url: 'oddsportal://results'
                        },
                        extractResult: {
                            matches: [{ match_id: 'm1', hash: 'hash-results', url: 'oddsportal://results/m1' }],
                            pagesScanned: 1,
                            totalCandidates: 1,
                            sourceState: 'SOURCE_READY'
                        },
                        candidates: [{ match_id: 'm1', hash: 'hash-results', url: 'oddsportal://results/m1' }],
                        seasonMirror: new Map(),
                        sampleLinked: 1
                    };
                }
            },
            mirrorManager: {
                buildSeasonMirror() {
                    return new Map();
                }
            },
            matchEvaluator: {
                findBestCandidate(match, candidates) {
                    const candidate = candidates.find((item) => item.match_id === match.match_id);
                    return candidate ? { candidate, confidence: 1 } : null;
                }
            },
            _probeFixturesCandidateSource: async () => ({
                routeKind: 'fixtures',
                source: {
                    season: '2025/2026',
                    url: 'oddsportal://fixtures'
                },
                extractResult: {
                    matches: [{ match_id: 'm2', hash: 'hash-fixtures', url: 'oddsportal://fixtures/m2' }],
                    pagesScanned: 1,
                    totalCandidates: 1,
                    sourceState: 'FIXTURES_SWEEP_READY'
                },
                candidates: [{ match_id: 'm2', hash: 'hash-fixtures', url: 'oddsportal://fixtures/m2' }],
                seasonMirror: new Map(),
                sampleLinked: 1
            }),
            _probeSearchCandidateSource: async () => ({
                routeKind: 'search',
                source: {
                    season: '2025/2026',
                    url: 'oddsportal://search'
                },
                extractResult: {
                    matches: [{ match_id: 'm3', hash: 'hash-search', url: 'oddsportal://search/m3' }],
                    pagesScanned: 1,
                    totalCandidates: 1,
                    sourceState: 'SEARCH_SWEEP_READY'
                },
                candidates: [{ match_id: 'm3', hash: 'hash-search', url: 'oddsportal://search/m3' }],
                seasonMirror: new Map(),
                sampleLinked: 0
            }),
            _canUseLocalDictionaryFallback: () => false
        };

        const selectedSource = await flow._selectCandidateSourceWithLocalFallback(
            {
                dbSeason: '2025/2026',
                resultsUrl: 'oddsportal://results',
                league: { name: 'Test League' }
            },
            [
                { match_id: 'm1' },
                { match_id: 'm2' }
            ],
            0.75
        );

        assert.deepStrictEqual(selectedSource.routeKinds, ['results', 'fixtures', 'search']);
        assert.strictEqual(selectedSource.extractResult.sourceState, 'MULTI_ROUTE_SWEEP');
        assert.strictEqual(selectedSource.candidates.length, 3);
        assert.strictEqual(selectedSource.sampleLinked, 2);
    });

    it('perpetualReconMode 开启后只要仍有 pending 且代理可用就应继续下一轮', async () => {
        let prepareCalls = 0;
        const target = {
            leagueId: 1,
            league: { id: 1, name: 'Premier League' },
            dbSeason: '2025/2026',
        };
        const flow = {
            ...reconMatrixFlow,
            perpetualReconMode: true,
            perpetualReconPassDelayMs: 0,
            defaultReconConcurrency: 1,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            buildScanTargets: async () => [target],
            taskPlanner: {
                async prepareReconPendingTargets() {
                    prepareCalls += 1;
                    if (prepareCalls === 1) {
                        return [{ target, pendingMatches: [{ match_id: 'm1' }], desiredLimit: 1 }];
                    }
                    if (prepareCalls === 2) {
                        return [{ target, pendingMatches: [{ match_id: 'm2' }], desiredLimit: 1 }];
                    }
                    return [];
                }
            },
            _runAdaptiveLeagueWorkers: async (targetPendingMap) => targetPendingMap.map(({ target: itemTarget, pendingMatches }) => ({
                target: itemTarget,
                result: {
                    pendingTotal: pendingMatches.length,
                    linked: pendingMatches.length,
                    mismatched: 0,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'oddsportal://results/',
                    candidateCount: 1
                }
            })),
            _resolveAvailableProxyCount: () => 1,
            shouldContinuePerpetualRecon(remainingPending, options = {}) {
                return remainingPending > 0 && Number(options.availableProxyCount || 0) > 0;
            }
        };

        const result = await flow.runReconMatrix({
            season: '2025/2026',
            leagueStartupStaggerMs: 0,
            perpetualReconMode: true,
            perpetualReconPassDelayMs: 0
        });

        assert.strictEqual(prepareCalls, 3);
        assert.strictEqual(result.passes, 2);
        assert.strictEqual(result.linked, 2);
        assert.strictEqual(result.remainingPending, 0);
        assert.strictEqual(result.perLeague.length, 1);
        assert.strictEqual(result.perLeague[0].passes, 2);
    });

    it('runReconMatrix 应在联赛级扇出中分配独立 navigator 端口并受 p-limit 限流', async () => {
        const workerStarts = [];
        let active = 0;
        let maxActive = 0;
        let nextPort = 7890;

        const preparedTargets = ['Premier League', 'Serie A', 'Bundesliga'].map((leagueName, index) => ({
            target: {
                leagueId: index + 1,
                league: { id: index + 1, name: leagueName },
                dbSeason: '2025/2026',
            },
            pendingMatches: [{ match_id: `${index + 1}` }],
            desiredLimit: 1,
        }));

        const flow = {
            ...reconMatrixFlow,
            defaultReconConcurrency: 22,
            leagueParallelism: 22,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            navigatorFactory: async () => {
                const port = nextPort++;
                return {
                    proxyPort: port,
                    ownsNavigator: true,
                    navigator: {
                        proxy: { port },
                        async ensureBrowserHealthy() {},
                        async close() {},
                    },
                };
            },
            buildScanTargets: async () => preparedTargets.map(item => item.target),
            taskPlanner: {
                prepareReconPendingTargets: async () => preparedTargets,
            },
            _runReconTarget: async (target, options = {}) => {
                active++;
                maxActive = Math.max(maxActive, active);
                workerStarts.push({
                    league: target.league.name,
                    port: options.navigator?.proxy?.port || null,
                });
                await new Promise(resolve => {
                    setTimeout(resolve, 25);
                });
                active--;
                return {
                    pendingTotal: 1,
                    linked: 1,
                    mismatched: 0,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'oddsportal://results/',
                    candidateCount: 1,
                };
            },
        };

        const result = await flow.runReconMatrix({
            season: '2025/2026',
            concurrency: 1,
            leagueConcurrency: 2,
            leagueStartupStaggerMs: 0,
            limit: 3,
        });

        assert.equal(maxActive, 2);
        assert.deepStrictEqual(workerStarts, [
            { league: 'Premier League', port: 7890 },
            { league: 'Serie A', port: 7891 },
            { league: 'Bundesliga', port: 7892 },
        ]);
        assert.equal(result.scannedLeagues, 3);
        assert.equal(result.linked, 3);
    });

    it('未显式传入 leagueConcurrency 时，应以 5 冷启动并把请求 concurrency 作为动态上限', async () => {
        let active = 0;
        let maxActive = 0;
        const events = [];

        const preparedTargets = Array.from({ length: 10 }, (_, index) => ({
            target: {
                leagueId: index + 1,
                league: { id: index + 1, name: `League-${index + 1}` },
                dbSeason: '2025/2026',
            },
            pendingMatches: [{ match_id: `${index + 1}` }],
            desiredLimit: 1,
        }));

        const flow = {
            ...reconMatrixFlow,
            defaultReconConcurrency: 5,
            leagueParallelism: 2,
            dynamicConcurrencyInitial: 5,
            dynamicConcurrencySuccessWindow: 1,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: {
                info(event, payload) {
                    events.push({ level: 'info', event, payload });
                },
                warn(event, payload) {
                    events.push({ level: 'warn', event, payload });
                },
                error(event, payload) {
                    events.push({ level: 'error', event, payload });
                },
            },
            navigatorFactory: async () => ({
                proxyPort: null,
                ownsNavigator: true,
                navigator: {
                    async ensureBrowserHealthy() {},
                    async close() {},
                },
            }),
            buildScanTargets: async () => preparedTargets.map(item => item.target),
            taskPlanner: {
                prepareReconPendingTargets: async () => preparedTargets,
            },
            _runReconTarget: async () => {
                active++;
                maxActive = Math.max(maxActive, active);
                await new Promise(resolve => {
                    setTimeout(resolve, 25);
                });
                active--;
                return {
                    pendingTotal: 1,
                    linked: 1,
                    mismatched: 0,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'oddsportal://results/',
                    candidateCount: 1,
                };
            },
        };

        await flow.runReconMatrix({
            season: '2025/2026',
            concurrency: 6,
            leagueStartupStaggerMs: 0,
            limit: 10,
        });

        const firstStart = events.find(entry => entry.event === 'recon_league_worker_start');
        assert.equal(firstStart.payload.allowedLeagueWorkers, 5);
        assert.ok(
            events.some(
                entry =>
                    entry.event === 'recon_dynamic_concurrency_adjusted' &&
                    entry.payload.reason === 'success_feedback' &&
                    entry.payload.maxActiveWorkers === 6
            )
        );
        assert.equal(maxActive, 6);
    });

    it('runReconMatrix 应按 index * 2000ms 对联赛 worker 启动错峰', async () => {
        const delays = [];
        const preparedTargets = ['Premier League', 'Serie A', 'Bundesliga'].map((leagueName, index) => ({
            target: {
                leagueId: index + 1,
                league: { id: index + 1, name: leagueName },
                dbSeason: '2025/2026',
            },
            pendingMatches: [{ match_id: `${index + 1}` }],
            desiredLimit: 1,
        }));

        const flow = {
            ...reconMatrixFlow,
            defaultReconConcurrency: 22,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            _sleep: async delayMs => {
                delays.push(delayMs);
            },
            navigatorFactory: async () => ({
                proxyPort: 7890,
                ownsNavigator: true,
                navigator: {
                    proxy: { port: 7890 },
                    async ensureBrowserHealthy() {},
                    async close() {},
                },
            }),
            buildScanTargets: async () => preparedTargets.map(item => item.target),
            taskPlanner: {
                prepareReconPendingTargets: async () => preparedTargets,
            },
            _runReconTarget: async () => ({
                pendingTotal: 1,
                linked: 1,
                mismatched: 0,
                sourceSeason: '2025/2026',
                sourceUrl: 'oddsportal://results/',
                candidateCount: 1,
            }),
        };

        await flow.runReconMatrix({
            season: '2025/2026',
            concurrency: 1,
            leagueConcurrency: 3,
            limit: 3,
        });

        assert.deepStrictEqual(delays, [2000, 4000]);
    });

    it('runReconMatrix 遇到 503 时应将联赛级动态并发从 5 立刻削减到 2', async () => {
        const events = [];
        const preparedTargets = Array.from({ length: 8 }, (_, index) => ({
            target: {
                leagueId: index + 1,
                league: { id: index + 1, name: `League-${index + 1}` },
                dbSeason: '2025/2026',
            },
            pendingMatches: [{ match_id: `${index + 1}` }],
            desiredLimit: 1,
        }));

        const flow = {
            ...reconMatrixFlow,
            dynamicConcurrencyInitial: 5,
            dynamicConcurrencySuccessWindow: 99,
            defaultReconConcurrency: 8,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: {
                info(event, payload) {
                    events.push({ level: 'info', event, payload });
                },
                warn(event, payload) {
                    events.push({ level: 'warn', event, payload });
                },
                error(event, payload) {
                    events.push({ level: 'error', event, payload });
                },
            },
            navigatorFactory: async () => ({
                proxyPort: 7890,
                ownsNavigator: true,
                navigator: {
                    proxy: { port: 7890 },
                    async ensureBrowserHealthy() {},
                    async close() {},
                },
            }),
            buildScanTargets: async () => preparedTargets.map(item => item.target),
            taskPlanner: {
                prepareReconPendingTargets: async () => preparedTargets,
            },
            _runReconTarget: async target => {
                if (target.league.name === 'League-3') {
                    await new Promise(resolve => {
                        setTimeout(resolve, 5);
                    });
                    const error = new Error('HTTP_503');
                    error.statusCode = 503;
                    throw error;
                }

                await new Promise(resolve => {
                    setTimeout(resolve, 40);
                });
                return {
                    pendingTotal: 1,
                    linked: 1,
                    mismatched: 0,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'oddsportal://results/',
                    candidateCount: 1,
                };
            },
        };

        await flow.runReconMatrix({
            season: '2025/2026',
            concurrency: 1,
            leagueConcurrency: 8,
            leagueStartupStaggerMs: 0,
            limit: 8,
        });

        const backoffIndex = events.findIndex(
            entry =>
                entry.level === 'warn' &&
                entry.event === 'recon_dynamic_concurrency_adjusted' &&
                entry.payload.reason === 'network_failure'
        );
        assert.ok(backoffIndex >= 0);
        assert.equal(events[backoffIndex].payload.previousMaxActiveWorkers, 5);
        assert.equal(events[backoffIndex].payload.maxActiveWorkers, 2);

        const postBackoffStarts = events
            .slice(backoffIndex + 1)
            .filter(entry => entry.event === 'recon_league_worker_start');

        assert.ok(postBackoffStarts.length > 0);
        assert.ok(postBackoffStarts.every(entry => entry.payload.allowedLeagueWorkers <= 2));
    });

    it('22-IP 绿灯数下降时应把 MatrixFlow 的联赛并发夹到可用代理数', async () => {
        let active = 0;
        let maxActive = 0;
        const preparedTargets = Array.from({ length: 6 }, (_, index) => ({
            target: {
                leagueId: index + 1,
                league: { id: index + 1, name: `League-${index + 1}` },
                dbSeason: '2025/2026',
            },
            pendingMatches: [{ match_id: `${index + 1}` }],
            desiredLimit: 1,
        }));

        const flow = {
            ...reconMatrixFlow,
            dynamicConcurrencyInitial: 5,
            dynamicConcurrencySuccessWindow: 99,
            defaultReconConcurrency: 6,
            reconBatchSize: 25,
            confidenceThreshold: 0.75,
            logger: { info() {}, warn() {}, error() {} },
            proxyRotator: {
                getHealthStatus() {
                    return { total: 22, healthy: 3, cooling: 19, dead: 0, available: 3 };
                },
            },
            navigatorFactory: async () => ({
                proxyPort: 7890,
                ownsNavigator: true,
                navigator: {
                    proxy: { port: 7890 },
                    async ensureBrowserHealthy() {},
                    async close() {},
                },
            }),
            buildScanTargets: async () => preparedTargets.map(item => item.target),
            taskPlanner: {
                prepareReconPendingTargets: async () => preparedTargets,
            },
            _runReconTarget: async () => {
                active++;
                maxActive = Math.max(maxActive, active);
                await new Promise(resolve => {
                    setTimeout(resolve, 20);
                });
                active--;
                return {
                    pendingTotal: 1,
                    linked: 1,
                    mismatched: 0,
                    sourceSeason: '2025/2026',
                    sourceUrl: 'oddsportal://results/',
                    candidateCount: 1,
                };
            },
        };

        await flow.runReconMatrix({
            season: '2025/2026',
            concurrency: 1,
            leagueConcurrency: 6,
            leagueStartupStaggerMs: 0,
            limit: 6,
        });

        assert.equal(maxActive, 3);
    });
});
