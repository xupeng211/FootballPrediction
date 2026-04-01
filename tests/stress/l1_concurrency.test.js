'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const { FixtureRepository } = require('../../src/infrastructure/services/FixtureRepository');

class SimulatedLockPool {
  constructor(options = {}) {
    this.lockOwners = new Map();
    this.persistedIds = new Set();
    this.activeQueries = 0;
    this.maxConcurrentQueries = 0;
    this.waitCount = 0;
    this.deadlocks = 0;
    this.releaseCount = 0;
    this.connectCount = 0;
    this.queryExecutions = [];
    this.holdMs = options.holdMs || 15;
    this.acquireTimeoutMs = options.acquireTimeoutMs || 400;
  }

  async query() {
    return { rows: [] };
  }

  async connect() {
    this.connectCount += 1;
    return {
      query: async (query, values = []) => {
        if (typeof query === 'string' && query.includes('INSERT INTO matches')) {
          return this._handlePersist(values);
        }

        return { rows: [] };
      },
      release: () => {
        this.releaseCount += 1;
      }
    };
  }

  async _handlePersist(values) {
    const matchIds = this._extractMatchIds(values);
    const owner = Symbol('persist-owner');
    this.queryExecutions.push([...matchIds]);
    this.activeQueries += 1;
    this.maxConcurrentQueries = Math.max(this.maxConcurrentQueries, this.activeQueries);

    try {
      for (const matchId of matchIds) {
        await this._acquireLock(matchId, owner);
      }

      await this._sleep(this.holdMs);

      const rows = matchIds.map((matchId) => {
        const inserted = !this.persistedIds.has(matchId);
        this.persistedIds.add(matchId);
        return { inserted };
      });

      return { rows };
    } finally {
      for (const matchId of matchIds) {
        if (this.lockOwners.get(matchId) === owner) {
          this.lockOwners.delete(matchId);
        }
      }
      this.activeQueries -= 1;
    }
  }

  _extractMatchIds(values) {
    const ids = [];
    for (let index = 0; index < values.length; index += 12) {
      ids.push(String(values[index]));
    }
    return ids;
  }

  async _acquireLock(matchId, owner) {
    const start = Date.now();

    while (true) {
      const holder = this.lockOwners.get(matchId);

      if (!holder || holder === owner) {
        this.lockOwners.set(matchId, owner);
        return;
      }

      this.waitCount += 1;

      if (Date.now() - start > this.acquireTimeoutMs) {
        this.deadlocks += 1;
        throw new Error(`simulated deadlock on ${matchId}`);
      }

      await this._sleep(2);
    }
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

function createFixture(matchId, overrides = {}) {
  const externalId = matchId.split('_').pop();
  return {
    match_id: matchId,
    external_id: externalId,
    league_name: 'Bundesliga',
    season: '2025/2026',
    home_team: `Home ${externalId}`,
    away_team: `Away ${externalId}`,
    match_date: new Date('2025-08-22T18:30:00Z'),
    home_score: null,
    away_score: null,
    status: 'scheduled',
    is_finished: false,
    data_source: 'FotMob',
    ...overrides
  };
}

describe('L1 并发压力 - FixtureRepository.persist', () => {
  it('应在持久化前按 match_id 排序，消除输入顺序抖动', async () => {
    const capturedOrders = [];
    const dbPool = {
      query: async () => ({ rows: [] }),
      connect: async () => ({
        query: async (query, values = []) => {
          if (typeof query === 'string' && query.includes('INSERT INTO matches')) {
            const ids = [];
            for (let index = 0; index < values.length; index += 12) {
              ids.push(String(values[index]));
            }
            capturedOrders.push(ids);
            return { rows: ids.map(() => ({ inserted: true })) };
          }
          return { rows: [] };
        },
        release: () => {}
      })
    };

    const repository = new FixtureRepository({
      dbPool,
      batchSize: 10,
      logger: { info: () => {}, warn: () => {}, error: () => {} }
    });

    const fixtures = [
      createFixture('54_20252026_300'),
      createFixture('54_20252026_100'),
      createFixture('54_20252026_200')
    ];

    const result = await repository.persist(fixtures);

    assert.deepStrictEqual(capturedOrders[0], [
      '54_20252026_100',
      '54_20252026_200',
      '54_20252026_300'
    ]);
    assert.strictEqual(result.inserted, 3);
    assert.strictEqual(result.failed, 0);
  });

  it('高频并发冲突下应稳定完成，且释放连接、不触发模拟死锁', async () => {
    const dbPool = new SimulatedLockPool({
      holdMs: 12,
      acquireTimeoutMs: 500
    });

    const repository = new FixtureRepository({
      dbPool,
      batchSize: 6,
      maxRetries: 1,
      logger: { info: () => {}, warn: () => {}, error: () => {} }
    });

    const overlappingFixtures = [
      '54_20252026_006',
      '54_20252026_005',
      '54_20252026_004',
      '54_20252026_003',
      '54_20252026_002',
      '54_20252026_001'
    ].map((matchId) => createFixture(matchId));

    const workerCount = 12;
    const startedAt = Date.now();

    const results = await Promise.all(
      Array.from({ length: workerCount }, () => repository.persist(overlappingFixtures))
    );

    const durationMs = Date.now() - startedAt;

    assert.ok(
      results.every((result) => result.failed === 0),
      '并发写入不应出现失败批次'
    );
    assert.ok(
      dbPool.queryExecutions.every((ids) => {
        const sorted = [...ids].sort((a, b) => a.localeCompare(b));
        return JSON.stringify(ids) === JSON.stringify(sorted);
      }),
      '每个批次都应以稳定顺序申请锁'
    );
    assert.ok(dbPool.waitCount > 0, '应观测到真实锁等待');
    assert.ok(dbPool.maxConcurrentQueries >= 2, '应出现并发写入');
    assert.strictEqual(dbPool.deadlocks, 0, '排序后不应触发模拟死锁');
    assert.strictEqual(dbPool.releaseCount, dbPool.connectCount, '每次 connect 都应成对 release');
    assert.ok(durationMs < 2500, `并发压力测试耗时异常: ${durationMs}ms`);
  });
});
