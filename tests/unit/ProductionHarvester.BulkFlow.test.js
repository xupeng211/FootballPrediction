'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ProductionHarvester } = require('../../src/infrastructure/harvesters/ProductionHarvester');

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function createMatches(count) {
  return Array.from({ length: count }, (_, index) => ({
    match_id: `47_20242025_${1000 + index}`,
    external_id: `${1000 + index}`,
    home_team: `Home ${index}`,
    away_team: `Away ${index}`,
    match_date: new Date(Date.UTC(2024, 7, 1, 12, index % 60, 0)).toISOString()
  }));
}

function offsetMatches(matches, offset) {
  return matches.map((match, index) => ({
    ...match,
    match_id: `47_20242025_${2000 + offset + index}`,
    external_id: `${2000 + offset + index}`
  }));
}

describe('ProductionHarvester - Bulk Flow', () => {
  it('应从100场待处理比赛中以10并发完成批量收割', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 10,
      maxRetries: 1,
      verboseLogging: false
    });

    const pendingMatches = createMatches(100);
    const processed = [];
    let active = 0;
    let maxObservedConcurrency = 0;

    harvester.getPendingMatches = async (limit) => pendingMatches.slice(0, limit);
    harvester.harvestWithRetry = async (match) => {
      active++;
      maxObservedConcurrency = Math.max(maxObservedConcurrency, active);
      await delay(5);
      processed.push(match.match_id);
      active--;

      return {
        success: true,
        match_id: match.match_id
      };
    };

    const result = await harvester.run({ limit: 100, concurrency: 10 });

    assert.strictEqual(result.mode, 'bulk');
    assert.strictEqual(result.total, 100);
    assert.strictEqual(result.success, 100);
    assert.strictEqual(result.failed, 0);
    assert.strictEqual(result.concurrency, 10);
    assert.strictEqual(maxObservedConcurrency, 10);
    assert.strictEqual(new Set(processed).size, 100);
  });

  it('应在重启后通过待处理查询自动跳过已收割比赛', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 10,
      verboseLogging: false
    });

    const remainingMatches = createMatches(80);
    const processed = [];

    let hasReturned = false;
    harvester.getPendingMatches = async () => {
      if (hasReturned) {
        return [];
      }
      hasReturned = true;
      return remainingMatches;
    };
    harvester.harvestWithRetry = async (match) => {
      processed.push(match.match_id);
      return { success: true, match_id: match.match_id };
    };

    const result = await harvester.run({ limit: 100, concurrency: 10 });

    assert.strictEqual(result.total, 80);
    assert.strictEqual(result.success, 80);
    assert.strictEqual(processed.length, 80);
    assert.strictEqual(new Set(processed).size, 80);
  });

  it('未显式设置 limit 时应持续分批拉取直到 pending 用尽', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 10,
      batchSize: 60,
      verboseLogging: false
    });

    const queue = [createMatches(60), offsetMatches(createMatches(40), 60), []];
    const processed = [];

    harvester.getPendingMatches = async () => queue.shift() || [];
    harvester.harvestWithRetry = async (match) => {
      processed.push(match.match_id);
      return {
        success: true,
        match_id: match.match_id,
        duration: 5
      };
    };

    const result = await harvester.run({ concurrency: 10 });

    assert.strictEqual(result.total, 100);
    assert.strictEqual(result.success, 100);
    assert.strictEqual(result.failed, 0);
    assert.strictEqual(result.batches, 2);
    assert.strictEqual(processed.length, 100);
    assert.strictEqual(new Set(processed).size, 100);
  });

  it('达到进度间隔时应输出进度快照', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 8,
      bulkProgressEvery: 2,
      verboseLogging: false
    });

    const queue = [createMatches(3), []];
    const logs = [];
    const originalLog = console.log;
    console.log = (...args) => logs.push(args.join(' '));

    try {
      harvester.getPendingMatches = async () => queue.shift() || [];
      harvester.harvestWithRetry = async (match) => ({
        success: true,
        match_id: match.match_id,
        duration: 10
      });

      const result = await harvester.run({ concurrency: 8, progressEvery: 2 });

      assert.strictEqual(result.total, 3);
      assert.ok(logs.some(line => line.includes('[PROGRESS] 已完成 2/')));
    } finally {
      console.log = originalLog;
    }
  });

  it('查询待处理比赛时应使用 pipeline_status 并跳过已有 raw 数据', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      verboseLogging: false
    });

    let capturedSql = '';
    let capturedParams = [];

    harvester.persistence.ensurePipelineStatusSchema = async () => 'pipeline_status';
    harvester.db = {
      query: async (sql, params) => {
        capturedSql = sql;
        capturedParams = params;
        return { rows: [{ match_id: '47_20242025_1001' }] };
      }
    };

    const matches = await harvester.getPendingMatches(25);

    assert.strictEqual(matches.length, 1);
    assert.ok(capturedSql.includes('LEFT JOIN raw_match_data r ON m.match_id = r.match_id'));
    assert.ok(capturedSql.includes('COALESCE(m.pipeline_status, \'pending\') = \'pending\''));
    assert.ok(capturedSql.includes('r.match_id IS NULL'));
    assert.ok(capturedSql.includes('ORDER BY m.match_id ASC'));
    assert.deepStrictEqual(capturedParams, [25]);
  });

  it('待处理比赛查询异常时应显式中断批量任务，而不是静默结束', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 10,
      verboseLogging: false
    });

    harvester.getPendingMatches = async () => {
      throw new Error('db offline');
    };

    await assert.rejects(
      () => harvester.run({ limit: 10, concurrency: 10 }),
      /PENDING_MATCH_QUERY_FAILED|BULK_ABORT/
    );
  });

  it('达到 browserRecycleEvery 阈值时应在批次边界重启浏览器', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 10,
      batchSize: 500,
      browserRecycleEvery: 50,
      browserRecycleRssBytes: 1024 * 1024 * 1024,
      verboseLogging: false
    });

    const batchLimits = [];
    const queue = [createMatches(50), offsetMatches(createMatches(10), 50), []];
    let recycleCount = 0;

    harvester.getPendingMatches = async (limit) => {
      batchLimits.push(limit);
      return queue.shift() || [];
    };
    harvester.harvestWithRetry = async (match) => ({
      success: true,
      match_id: match.match_id,
      duration: 5
    });
    harvester._recycleBrowserFactory = async () => {
      recycleCount++;
    };
    harvester._getProcessMemoryUsage = () => ({ rss: 128 * 1024 * 1024, heapUsed: 32 * 1024 * 1024 });

    const result = await harvester.run({ limit: 60, concurrency: 10 });

    assert.strictEqual(result.total, 60);
    assert.strictEqual(result.browserRecycles, 1);
    assert.strictEqual(recycleCount, 1);
    assert.deepStrictEqual(batchLimits, [50, 10]);
  });

  it('rss 超过阈值时应强制回收浏览器工厂', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      bulkConcurrency: 8,
      batchSize: 100,
      browserRecycleEvery: 1000,
      browserRecycleRssBytes: 100,
      verboseLogging: false
    });

    const queue = [createMatches(40), offsetMatches(createMatches(40), 40), []];
    let recycleCount = 0;
    let memoryReads = 0;

    harvester.getPendingMatches = async () => queue.shift() || [];
    harvester.harvestWithRetry = async (match) => ({
      success: true,
      match_id: match.match_id,
      duration: 5
    });
    harvester._recycleBrowserFactory = async () => {
      recycleCount++;
    };
    harvester._getProcessMemoryUsage = () => {
      memoryReads++;
      return {
        rss: memoryReads >= 1 ? 200 : 50,
        heapUsed: 32
      };
    };

    const result = await harvester.run({ limit: 80, concurrency: 8 });

    assert.strictEqual(result.total, 80);
    assert.strictEqual(result.browserRecycles, 1);
    assert.strictEqual(recycleCount, 1);
  });

  it('显式传入单场 payload 时应保持兼容路径', async () => {
    const harvester = new ProductionHarvester({
      dryRun: true,
      verboseLogging: false
    });

    let calledWith = null;
    harvester.harvestWithRetry = async (match, index, maxRetries) => {
      calledWith = { match, index, maxRetries };
      return { success: true, match_id: match.match_id };
    };

    const result = await harvester.run({
      match: {
        match_id: '47_20242025_5555',
        external_id: '5555',
        home_team: 'Arsenal',
        away_team: 'Chelsea'
      }
    });

    assert.strictEqual(result.success, true);
    assert.strictEqual(calledWith.match.match_id, '47_20242025_5555');
    assert.strictEqual(calledWith.index, 0);
    assert.strictEqual(calledWith.maxRetries, harvester.config.maxRetries);
  });
});
