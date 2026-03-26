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

const { ReconScanner } = require('../../scripts/ops/recon_scanner');
const { ReconEngine } = require('../../src/infrastructure/recon/ReconEngine');
const { ReconNavigator } = require('../../src/infrastructure/recon/ReconNavigator');
const {
  FixtureRepository,
  RepositoryError
} = require('../../src/infrastructure/services/FixtureRepository');

describe('ReconScanner Robustness - Fallback Safety', () => {
  it('应在 API 失败后进入 fallback 路径且不再因 dbSeason 崩溃', async () => {
    let unstitchedCalls = 0;

    const repository = {
      async getUnstitchedMatches() {
        unstitchedCalls++;
        return [{
          match_id: '54_20242025_001',
          home_team: 'Bayern Munich',
          away_team: 'Borussia Dortmund',
          match_date: '2024-08-10T18:30:00Z'
        }];
      }
    };

    const navigator = {
      async protocolArchiveExtract() {
        return { matches: [], pagesScanned: 0 };
      }
    };

    const engine = new ReconEngine({
      repository,
      navigator,
      parser: { calculateSimilarity: () => 0 },
      stitcher: { stitchWithHashLock: async () => ({ inserted: 0 }) },
      logger: { info() {}, warn() {}, error() {} }
    });

    engine.domFallbackScan = async () => ({
      success: true,
      inserted: 1,
      durationMs: 10
    });

    const result = await engine.smartScan('2024-2025', {
      name: 'Bundesliga',
      country: 'germany',
      slug: 'bundesliga'
    });

    assert.strictEqual(result.success, true, 'fallback 结束后应返回成功');
    assert.strictEqual(result.strategy, 'hybrid', '应落入 hybrid 策略');
    assert.strictEqual(result.totalInserted, 1, 'DOM fallback 插入数应被累计');
    assert.strictEqual(Number(result.coverage), 100, '覆盖率应基于 dbSeason 正确回算');
    assert.strictEqual(unstitchedCalls, 3, '协议扫描、日期扫描和 fallback 回算都应访问未缝合比赛');
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
            { column_name: 'mapping_method' }
          ]
        };
      },
      async connect() {
        connectCount++;
        return {
          async query(sql) {
            const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
            events.push(normalized);
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
            { column_name: 'mapping_method' }
          ]
        };
      },
      async connect() {
        return {
          async query(sql) {
            const normalized = sql.trim().split(/\s+/).slice(0, 4).join(' ');
            events.push(normalized);

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
      (error) => error instanceof RepositoryError && error.code === 'MAX_RETRIES_EXCEEDED'
    );

    assert.deepStrictEqual(
      events,
      [
        'BEGIN',
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
