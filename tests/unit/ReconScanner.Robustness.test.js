/**
 * TITAN V11.0 RECON SCANNER - 鲁棒性回归测试
 * ==========================================
 *
 * 测试目标:
 * 1. API 失效后进入 fallback 路径时不再崩溃
 * 2. FixtureRepository 批量保存使用单一事务连接
 * 3. TraceID 从 Scanner 显式贯通到组件日志与 Navigator
 *
 * @module tests/unit/ReconScanner.Robustness.test
 * @version V11.0-HOTFIX
 * @date 2026-03-26
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { ReconScanner, parseArgs, loadConfig, computeExitCode } = require('../../scripts/ops/recon_scanner');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ReconNavigator } = require('../../src/infrastructure/recon/ReconNavigator');
const {
  FixtureRepository,
  RepositoryError
} = require('../../src/infrastructure/services/FixtureRepository');

describe('ReconScanner Robustness - Fallback Safety', () => {
  it('smartScan 应直接走 season mirror，不再进入 date-driven fallback', async () => {
    let pendingCalls = 0;
    let domFallbackCalls = 0;
    const repository = {
      async getUnstitchedMatches() {
        pendingCalls++;
        return [{
          match_id: '54_20242025_001',
          home_team: 'Bayern Munich',
          away_team: 'Borussia Dortmund',
          match_date: '2024-08-10T18:30:00Z'
        }];
      },
      async batchSaveOddsPortalMappings(mappings) {
        return { success: true, inserted: mappings.length };
      },
      async batchUpdateMatchPipelineStatus(matchIds) {
        return { updated: matchIds.length };
      }
    };

    const navigator = {
      async fetchFullSeasonArchive() {
        return {
          matches: [{
            hash: 'mirror-hash',
            url: 'oddsportal://bundesliga/bayern-dortmund',
            homeTeam: 'Bayern Munich',
            awayTeam: 'Borussia Dortmund',
            matchDate: '2024-08-10T18:30:00Z'
          }],
          pagesScanned: 3,
          totalCandidates: 1,
          sourceState: 'FULL_SEASON_SWEEP'
        };
      }
    };

    const engine = new ReconEngine({
      repository,
      navigator,
      parser: { calculateSimilarity: () => 1 },
      logger: { info() {}, warn() {}, error() {} }
    });

    engine.domFallbackScan = async () => {
      domFallbackCalls++;
      return {
        success: true,
        inserted: 1,
        durationMs: 10
      };
    };

    const result = await engine.smartScan('2024-2025', {
      name: 'Bundesliga',
      country: 'germany',
      slug: 'bundesliga'
    });

    assert.strictEqual(result.success, true, 'season mirror 应直接成功');
    assert.strictEqual(result.strategy, 'season_mirror', '不应再进入 date-driven 混合策略');
    assert.strictEqual(result.totalInserted, 1, 'season mirror 应直接产出链接');
    assert.strictEqual(Number(result.coverage), 100, '覆盖率应直接按 pendingTotal 回算');
    assert.strictEqual(pendingCalls, 1, 'season mirror 只应加载一次待处理比赛');
    assert.strictEqual(domFallbackCalls, 0, '有 season mirror 候选时不应进入 DOM fallback');
  });
});

describe('ReconScanner Robustness - Config Fail Fast', () => {
  it('loadConfig 遇到非法字段类型时必须抛出带字段名的 FATAL_CONFIG', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-config-invalid-'));
    const configPath = path.join(tempDir, 'recon_config.json');
    const invalidConfig = structuredClone(require('../../config/recon_config.json'));
    invalidConfig.recon_runtime.network_monitor.page_size = 'invalid';
    fs.writeFileSync(configPath, JSON.stringify(invalidConfig), 'utf8');

    assert.throws(
      () => loadConfig(configPath),
      (error) => {
        assert.strictEqual(error.code, 'FATAL_CONFIG');
        assert.match(error.message, /recon_runtime\.network_monitor\.page_size/);
        return true;
      }
    );
  });
});

describe('ReconScanner Robustness - Repository Transactions', () => {
  it('应在 batchSaveOddsPortalMappings 中复用同一个 client', async () => {
    const events = [];
    let connectCount = 0;

    const pool = {
      async query() {
        return {
          rows: [
            { column_name: 'match_confidence' },
            { column_name: 'mapping_method' },
            { column_name: 'is_reversed' }
          ]
        };
      },
      async connect() {
        connectCount++;
        return {
          async query(sql) {
            const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
            events.push(normalized);
            if (sql.includes('SELECT season, oddsportal_hash')) {
              return { rows: [] };
            }
            if (sql.includes('RETURNING match_id')) {
              return { rows: [{ match_id: 'saved' }] };
            }
            return { rows: [] };
          },
          release() {
            events.push('RELEASE');
          }
        };
      }
    };

    const repository = new FixtureRepository({
      dbPool: pool,
      maxRetries: 1,
      logger: { info() {}, warn() {}, error() {} }
    });

    const result = await repository.batchSaveOddsPortalMappings([
      {
        match_id: 'm1',
        oddsportal_hash: 'h1',
        full_url: 'https://example.com/1',
        season: '2024/2025',
        league_name: 'Bundesliga',
        home_team: 'A',
        away_team: 'B'
      },
      {
        match_id: 'm2',
        oddsportal_hash: 'h2',
        full_url: 'https://example.com/2',
        season: '2024/2025',
        league_name: 'Bundesliga',
        home_team: 'C',
        away_team: 'D'
      }
    ]);

    assert.strictEqual(result.success, true, '批量保存应成功');
    assert.strictEqual(result.inserted, 2, '应成功插入两条');
    assert.strictEqual(connectCount, 1, '整个批次只能 connect 一次');
    assert.deepStrictEqual(
      events,
      [
        'BEGIN',
        'SELECT season, oddsportal_hash, match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'COMMIT',
        'RELEASE'
      ],
      '批量写入应表现为单连接单事务'
    );
  });

  it('应在批量写入中途失败时整体回滚', async () => {
    let insertCount = 0;
    const events = [];

    const pool = {
      async query() {
        return {
          rows: [
            { column_name: 'match_confidence' },
            { column_name: 'mapping_method' },
            { column_name: 'is_reversed' }
          ]
        };
      },
      async connect() {
        return {
          async query(sql) {
            const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
            events.push(normalized);

            if (sql.includes('SELECT season, oddsportal_hash')) {
              return { rows: [] };
            }

            if (sql.includes('RETURNING match_id')) {
              insertCount++;
              if (insertCount === 2) {
                const error = new Error('duplicate failure');
                error.code = '23505';
                throw error;
              }
              return { rows: [{ match_id: 'saved' }] };
            }

            return { rows: [] };
          },
          release() {
            events.push('RELEASE');
          }
        };
      }
    };

    const repository = new FixtureRepository({
      dbPool: pool,
      maxRetries: 1,
      logger: { info() {}, warn() {}, error() {} }
    });

    await assert.rejects(
      () => repository.batchSaveOddsPortalMappings([
        {
          match_id: 'm1',
          oddsportal_hash: 'h1',
          full_url: 'https://example.com/1',
          season: '2024/2025',
          league_name: 'Bundesliga',
          home_team: 'A',
          away_team: 'B'
        },
        {
          match_id: 'm2',
          oddsportal_hash: 'h2',
          full_url: 'https://example.com/2',
          season: '2024/2025',
          league_name: 'Bundesliga',
          home_team: 'C',
          away_team: 'D'
        }
      ]),
      (error) => error instanceof RepositoryError && error.code === 'UNIQUE_VIOLATION'
    );

    assert.deepStrictEqual(
      events,
      [
        'BEGIN',
        'SELECT season, oddsportal_hash, match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'INSERT INTO matches_oddsportal_mapping (match_id,',
        'ROLLBACK',
        'RELEASE'
      ],
      '任意单条失败都应触发整批回滚'
    );
  });
});

describe('ReconScanner Robustness - TraceID Propagation', () => {
  it('应将 scanner.traceId 透传到 Repository、Parser、Engine、Navigator 及日志', async () => {
    const logs = [];
    let navigatorTraceId = null;

    const originalLaunch = ReconNavigator.prototype.launch;
    const originalClose = ReconNavigator.prototype.close;

    ReconNavigator.prototype.launch = async function launchStub() {
      navigatorTraceId = this.traceId;
      this.page = { waitForTimeout: async () => {} };
      return this.page;
    };

    ReconNavigator.prototype.close = async function closeStub() {
      return undefined;
    };

    try {
      const repository = {
        logger: {
          info(event, data) { logs.push({ level: 'info', event, data }); },
          warn(event, data) { logs.push({ level: 'warn', event, data }); },
          error(event, data) { logs.push({ level: 'error', event, data }); }
        },
        async init() {},
        async close() {}
      };

      const scanner = new ReconScanner({
        logger: {
          info(event, data) { logs.push({ level: 'info', event, data }); },
          warn(event, data) { logs.push({ level: 'warn', event, data }); },
          error(event, data) { logs.push({ level: 'error', event, data }); },
          debug(event, data) { logs.push({ level: 'debug', event, data }); }
        },
        guardian: {
          async start() {},
          async stop() {}
        },
        repository,
        engine: {
          async smartScan() {
            return { success: true, inserted: 0, pendingTotal: 0, coverage: 100 };
          }
        },
        proxyRotator: { getNextProxy: () => null }
      });

      await scanner.initialize();
      const result = await scanner.scan('2024-2025', { name: 'Bundesliga', country: 'germany', slug: 'bundesliga' });

      repository.logger.info('repository_probe', { stage: 'post_scan' });

      assert.strictEqual(scanner.repository.traceId, scanner.traceId, 'Repository traceId 必须同步');
      assert.strictEqual(scanner.parser.traceId, scanner.traceId, 'Parser traceId 必须同步');
      assert.strictEqual(scanner.engine.traceId, scanner.traceId, 'Engine traceId 必须同步');
      assert.strictEqual(navigatorTraceId, scanner.traceId, 'Navigator traceId 必须沿用 scanner.traceId');
      assert.strictEqual(result.traceId, scanner.traceId, '最终扫描结果必须携带统一 traceId');

      const tracedLogs = logs.filter(entry => entry.data && entry.data.traceId === scanner.traceId);
      assert.ok(tracedLogs.length >= 3, '日志中应存在多条携带统一 traceId 的记录');
      assert.ok(
        tracedLogs.every(entry => typeof entry.data.component === 'string' && entry.data.component.length > 0),
        '所有结构化日志必须包含 component'
      );

      await scanner.close();
    } finally {
      ReconNavigator.prototype.launch = originalLaunch;
      ReconNavigator.prototype.close = originalClose;
    }
  });
});

describe('ReconScanner Robustness - Runtime Kill Switch', () => {
  it('ReconEngine smartScan 在 RECON_STRATEGY=legacy 时必须回退到 protocolArchive 路径', async () => {
    const engine = new ReconEngine({
      repository: {
        async getUnstitchedMatches() {
          throw new Error('legacy path should not ask getUnstitchedMatches directly');
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      reconStrategy: 'legacy',
      taskPlanner: {
        formatSeasonForUrl(season) {
          return season;
        },
        buildResultsUrl(leagueConfig, season) {
          return `https://example.com/${leagueConfig.slug}/${season}`;
        }
      }
    });

    engine.protocolArchiveScan = async () => ({
      success: true,
      pendingTotal: 4,
      inserted: 3,
      unmatched: 1,
      coverage: 75,
      candidatesFound: 9
    });

    const result = await engine.smartScan('2024-2025', {
      name: 'Bundesliga',
      slug: 'bundesliga'
    });

    assert.strictEqual(result.strategy, 'legacy_protocol_archive');
    assert.strictEqual(result.linked, 3);
    assert.strictEqual(result.mismatched, 1);
    assert.strictEqual(result.candidateCount, 9);
  });

  it('ReconEngine smartScan 在禁用 DOM fallback 时遇到 SOURCE_EMPTY 必须直接失败返回', async () => {
    let domFallbackCalls = 0;
    const engine = new ReconEngine({
      repository: {
        async getUnstitchedMatches() {
          return [{ match_id: 'm1', home_team: 'A', away_team: 'B', match_date: '2024-08-10T18:30:00Z' }];
        }
      },
      taskPlanner: {
        buildTarget() {
          return {
            dbSeason: '2024/2025',
            season: '2024-2025',
            league: { name: 'Bundesliga', slug: 'bundesliga', country: 'germany' },
            resultsUrl: 'https://example.com/results/'
          };
        },
        async loadReconPendingMatches() {
          return [{ match_id: 'm1', home_team: 'A', away_team: 'B', match_date: '2024-08-10T18:30:00Z' }];
        }
      },
      logger: { info() {}, warn() {}, error() {} },
      disableDomFallback: true
    });

    engine._runReconTarget = async () => {
      const error = new Error('SOURCE_EMPTY');
      error.code = 'SOURCE_EMPTY';
      throw error;
    };
    engine.domFallbackScan = async () => {
      domFallbackCalls++;
      return { success: true, inserted: 1 };
    };

    const result = await engine.smartScan('2024-2025', {
      name: 'Bundesliga',
      slug: 'bundesliga',
      country: 'germany'
    });

    assert.strictEqual(result.success, false);
    assert.strictEqual(result.strategy, 'season_mirror_dom_disabled');
    assert.strictEqual(domFallbackCalls, 0);
  });
});

describe('ReconScanner Robustness - Navigator Lifecycle', () => {
  it('多联赛连续 scan 时不应在单联赛结束后提前关闭 Navigator', async () => {
    let launchCount = 0;
    let closeCount = 0;

    const originalLaunch = ReconNavigator.prototype.launch;
    const originalClose = ReconNavigator.prototype.close;

    ReconNavigator.prototype.launch = async function launchStub() {
      launchCount++;
      this.browser = { isConnected: () => true };
      this.context = {};
      this.page = { isClosed: () => false, waitForTimeout: async () => {} };
      this.isClosed = false;
      return this.page;
    };

    ReconNavigator.prototype.close = async function closeStub() {
      closeCount++;
      this.browser = null;
      this.context = null;
      this.page = null;
      this.isClosed = true;
    };

    try {
      const scanner = new ReconScanner({
        logger: { info() {}, warn() {}, error() {}, debug() {} },
        guardian: { async start() {}, async stop() {} },
        repository: { async init() {}, async close() {} },
        engine: {
          async smartScan(_season, leagueConfig) {
            return {
              success: true,
              league: leagueConfig.name,
              inserted: 0,
              pendingTotal: 0,
              coverage: 100
            };
          }
        },
        proxyRotator: { getNextProxy: () => null }
      });

      await scanner.initialize();
      await scanner.scan('2025-2026', { name: 'Premier League', country: 'england', slug: 'premier-league' });
      await scanner.scan('2025-2026', { name: 'Bundesliga', country: 'germany', slug: 'bundesliga' });

      assert.strictEqual(launchCount, 1, '全局扫描期间应复用同一个 Navigator');
      assert.strictEqual(closeCount, 0, '单联赛结束后不得提前 close Navigator');

      await scanner.close();
      assert.strictEqual(closeCount, 1, '全局任务结束后才允许关闭 Navigator');
    } finally {
      ReconNavigator.prototype.launch = originalLaunch;
      ReconNavigator.prototype.close = originalClose;
    }
  });

  it('已存在的 Navigator 不健康时，ensureNavigator 应自动重启', async () => {
    let launchCount = 0;

    const unhealthyNavigator = {
      isHealthy: () => false,
      async ensureBrowserHealthy() {
        launchCount++;
      }
    };

    const scanner = new ReconScanner({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      guardian: { async start() {}, async stop() {} },
      repository: { async init() {}, async close() {} },
      engine: { navigator: unhealthyNavigator },
      proxyRotator: { getNextProxy: () => null }
    });

    await scanner.initialize();
    const navigator = await scanner.ensureNavigator();

    assert.strictEqual(navigator, unhealthyNavigator);
    assert.strictEqual(launchCount, 1, '发现不健康 Navigator 后必须触发自愈');
  });
});

describe('ReconScanner Robustness - CLI Defaults', () => {
  it('默认命令行应走直连模式，只有显式传入 --use-proxy 才启用代理', () => {
    const originalArgv = process.argv;

    try {
      process.argv = ['node', 'scripts/ops/recon_scanner.js', '--season', '2025-2026', '--league', 'EPL'];
      const directArgs = parseArgs();
      assert.strictEqual(directArgs.useProxy, false);

      process.argv = ['node', 'scripts/ops/recon_scanner.js', '--season', '2025-2026', '--league', 'EPL', '--use-proxy'];
      const proxiedArgs = parseArgs();
      assert.strictEqual(proxiedArgs.useProxy, true);
    } finally {
      process.argv = originalArgv;
    }
  });

  it('任一联赛失败时，整体退出码必须为 1', () => {
    const exitCode = computeExitCode([
      { success: true, league: 'Premier League', inserted: 20, pendingTotal: 20, coverage: 100 },
      { success: false, league: 'Bundesliga', error: 'SOURCE_EMPTY' }
    ], '100.00');

    assert.strictEqual(exitCode, 1);
  });

  it('无待对齐比赛且无失败时，整体退出码必须为 0', () => {
    const exitCode = computeExitCode([
      { success: true, league: 'Premier League', inserted: 0, pendingTotal: 0, coverage: 0 }
    ], '0.00');

    assert.strictEqual(exitCode, 0);
  });
});

describe('ReconScanner Robustness - Strict Config', () => {
  it('recon_config.json 解析失败时应抛出致命错误，而不是静默回退', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'recon-config-'));
    const badConfigPath = path.join(tempDir, 'recon_config.bad.json');
    fs.writeFileSync(badConfigPath, '{"broken":', 'utf8');

    assert.throws(
      () => loadConfig(badConfigPath),
      (error) => error instanceof Error && error.code === 'FATAL_CONFIG'
    );
  });
});

describe('ReconNavigator Robustness - Launch Mutex', () => {
  it('并发 launch 调用应复用同一个启动 Promise', async () => {
    const navigator = new ReconNavigator({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    let launchCalls = 0;
    navigator.circuitBreaker = { execute: async (fn) => fn() };
    navigator._performLaunch = async () => {
      launchCalls++;
      await new Promise((resolve) => setTimeout(resolve, 5));
      navigator.browser = { isConnected: () => true, close: async () => {} };
      navigator.context = {};
      navigator.page = { isClosed: () => false };
      navigator.isClosed = false;
      return navigator.page;
    };

    const [pageA, pageB] = await Promise.all([
      navigator.launch({ timeout: 10 }),
      navigator.launch({ timeout: 10 })
    ]);

    assert.strictEqual(launchCalls, 1);
    assert.strictEqual(pageA, pageB);
  });
});
