'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/harvesters/workers/WorkerPool.js');

function loadWorkerPoolModule() {
  delete require.cache[MODULE_PATH];
  return require(MODULE_PATH);
}

describe('src/infrastructure/harvesters/workers/WorkerPool', () => {
  const originalDateNow = Date.now;

  afterEach(() => {
    Date.now = originalDateNow;
    delete require.cache[MODULE_PATH];
  });

  test('应管理活跃 Worker、背压等待与进度轮询', async () => {
    Date.now = (() => {
      let now = 1000;
      return () => {
        now += 500;
        return now;
      };
    })();

    const { WorkerPool } = loadWorkerPoolModule();
    const logs = [];
    const pool = new WorkerPool({
      maxWorkers: 2,
      logger: message => {
        logs.push(message);
      },
      maxPendingOperations: 2,
      backpressurePollInterval: 5,
    });

    pool.register(1);
    pool.register(2);
    assert.strictEqual(pool.isActive(1), true);
    assert.strictEqual(pool.getActiveCount(), 2);
    assert.strictEqual(pool.stats.peakConcurrency, 2);

    pool.unregister(2);
    assert.strictEqual(pool.isActive(2), false);
    assert.strictEqual(pool.getActiveCount(), 1);

    pool.pendingOperations = 2;
    let delayCalls = 0;
    pool._delay = async () => {
      delayCalls += 1;
      if (delayCalls === 2) {
        pool.pendingOperations = 1;
      }
    };

    await pool._waitForBackpressureRelease();
    assert.strictEqual(pool.stats.backpressureDelays, 1);
    assert.ok(logs.some(message => message.includes('背压解除')));

    let progress = 0;
    pool._delay = async () => {
      progress += 1;
      if (progress === 2) {
        pool.unregister(1);
      }
    };
    await pool.waitForAll(activeCount => {
      logs.push(`progress:${activeCount}`);
    });
    assert.ok(logs.some(message => message.includes('progress:1')));
  });

  test('executeAll 应覆盖成功、异常失败与统计更新', async () => {
    const { WorkerPool } = loadWorkerPoolModule();
    const pool = new WorkerPool({ maxWorkers: 2, logger: () => {} });
    pool._waitForBackpressureRelease = async () => {};

    const results = await pool.executeAll(
      ['A', 'B', 'C'],
      async (task, index, workerId) => {
        if (task === 'B') {
          throw new Error('boom');
        }
        return { success: true, task, index, workerId };
      },
    );

    assert.deepStrictEqual(results, [
      { success: true, task: 'A', index: 0, workerId: 1 },
      { success: false, error: 'boom', workerId: 2 },
      { success: true, task: 'C', index: 2, workerId: 1 },
    ]);
    assert.strictEqual(pool.stats.totalTasks, 3);
    assert.strictEqual(pool.stats.completedTasks, 2);
    assert.strictEqual(pool.stats.failedTasks, 1);
    assert.strictEqual(pool.pendingOperations, 0);
    assert.strictEqual(pool.stats.activeWorkers, 0);
  });

  test('executeWithRetry 应覆盖重试成功、不可重试与重试耗尽分支', async () => {
    const logs = [];
    const { WorkerPool } = loadWorkerPoolModule();
    const pool = new WorkerPool({
      maxWorkers: 2,
      logger: message => {
        logs.push(message);
      },
    });
    const delays = [];

    pool._waitForBackpressureRelease = async () => {};
    pool._delay = async ms => {
      delays.push(ms);
    };

    const attempts = new Map();
    const results = await pool.executeWithRetry(
      ['retry-ok', 'fatal-throw', 'always-fail'],
      async (task, index, workerId, attempt) => {
        attempts.set(`${task}:${attempt}`, { index, workerId });

        if (task === 'retry-ok') {
          return attempt === 1
            ? { success: false, error: 'TEMP' }
            : { success: true, workerId, attempt };
        }

        if (task === 'fatal-throw') {
          throw new Error('fatal');
        }

        return { success: false, error: 'TEMP' };
      },
      {
        maxRetries: 2,
        shouldRetry(error) {
          return !(error instanceof Error) && error !== 'fatal';
        },
        async onRetry(workerId, attempt) {
          logs.push(`retry:${workerId}:${attempt}`);
        },
      },
    );

    assert.deepStrictEqual(results, [
      { success: true, workerId: 1, attempt: 2 },
      { success: false, error: 'fatal', attempts: 1 },
      { success: false, error: '重试 2 次后仍失败: TEMP', attempts: 2 },
    ]);
    assert.ok(logs.some(message => message.includes('retry:1:1')));
    assert.ok(logs.some(message => message.includes('重试成功')));
    assert.deepStrictEqual(delays, [pool._getBackoff(1), pool._getBackoff(1)]);
    assert.strictEqual(pool.stats.totalTasks, 3);
    assert.strictEqual(pool.stats.completedTasks, 1);
    assert.strictEqual(pool.stats.failedTasks, 2);
    assert.ok(attempts.has('retry-ok:2'));
  });

  test('辅助方法、状态报告与单例导出应工作正常', async () => {
    const { WorkerPool, getWorkerPool, resetWorkerPool } = loadWorkerPoolModule();
    const pool = new WorkerPool({
      maxWorkers: 4,
      logger: () => {},
      maxPendingOperations: 8,
    });

    pool._incrementPending();
    pool._incrementPending();
    assert.strictEqual(pool.pendingOperations, 2);
    assert.strictEqual(pool._needsBackpressure(), false);
    pool.pendingOperations = 8;
    assert.strictEqual(pool._needsBackpressure(), true);
    pool._decrementPending();
    assert.strictEqual(pool.pendingOperations, 7);
    pool.pendingOperations = 0;
    pool._decrementPending();
    assert.strictEqual(pool.pendingOperations, 0);

    assert.strictEqual(pool.getWorkerId(0), 1);
    assert.strictEqual(pool.getWorkerId(5), 2);
    assert.strictEqual(pool._getBackoff(1), 2000);
    assert.strictEqual(pool._getBackoff(5), 10000);

    const delayed = [];
    const originalSetTimeout = global.setTimeout;
    global.setTimeout = (callback, ms) => {
      delayed.push(ms);
      callback();
      return 1;
    };

    try {
      await pool._delay(25);
    } finally {
      global.setTimeout = originalSetTimeout;
    }
    assert.deepStrictEqual(delayed, [25]);

    pool.stats.totalTasks = 10;
    pool.stats.completedTasks = 6;
    pool.stats.failedTasks = 4;
    pool.stats.backpressureDelays = 3;
    pool.pendingOperations = 2;

    assert.deepStrictEqual(pool.getStats(), {
      totalTasks: 10,
      completedTasks: 6,
      failedTasks: 4,
      activeWorkers: 0,
      peakConcurrency: 0,
      backpressureDelays: 3,
      pendingOperations: 2,
      maxPendingOperations: 8,
    });
    assert.deepStrictEqual(pool.getBackpressureReport(), {
      pendingOperations: 2,
      maxPendingOperations: 8,
      pressureRatio: '0.25',
      isThrottling: false,
      totalDelays: 3,
    });

    pool.resetStats();
    assert.deepStrictEqual(pool.stats, {
      totalTasks: 0,
      completedTasks: 0,
      failedTasks: 0,
      activeWorkers: 0,
      peakConcurrency: 0,
    });

    const first = getWorkerPool({ maxWorkers: 3 });
    const second = getWorkerPool({ maxWorkers: 9 });
    assert.strictEqual(first, second);
    assert.strictEqual(first.maxWorkers, 3);
    resetWorkerPool();
    const third = getWorkerPool({ maxWorkers: 7 });
    assert.notStrictEqual(third, first);
    assert.strictEqual(third.maxWorkers, 7);
  });
});
