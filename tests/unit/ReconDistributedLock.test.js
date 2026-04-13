'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/recon/ReconDistributedLock.js');
const REDLOCK_ID = require.resolve('redlock');

function overrideModule(moduleId, exportsValue) {
  const previous = require.cache[moduleId];
  require.cache[moduleId] = {
    id: moduleId,
    filename: moduleId,
    loaded: true,
    exports: exportsValue,
  };

  return () => {
    if (previous) {
      require.cache[moduleId] = previous;
    } else {
      delete require.cache[moduleId];
    }
  };
}

function loadReconDistributedLock(behavior = {}) {
  const state = {
    constructorArgs: [],
    acquireCalls: [],
  };

  class FakeResourceLockedError extends Error {
    constructor(message) {
      super(message);
      this.name = 'ResourceLockedError';
    }
  }

  class FakeExecutionError extends Error {
    constructor(message, attempts = []) {
      super(message);
      this.name = 'ExecutionError';
      this.attempts = attempts;
    }
  }

  class FakeRedLock {
    constructor(clients, options) {
      state.constructorArgs.push({ clients, options });
    }

    async acquire(resources, ttl) {
      state.acquireCalls.push({ resources, ttl });
      if (behavior.onAcquire) {
        return behavior.onAcquire(resources, ttl, {
          ResourceLockedError: FakeResourceLockedError,
          ExecutionError: FakeExecutionError
        });
      }

      return {
        async release() {},
      };
    }
  }

  const restoreRedlock = overrideModule(REDLOCK_ID, {
    default: FakeRedLock,
    ResourceLockedError: FakeResourceLockedError,
    ExecutionError: FakeExecutionError
  });
  delete require.cache[MODULE_PATH];

  try {
    return { ...require(MODULE_PATH), state };
  } finally {
    restoreRedlock();
  }
}

describe('src/infrastructure/recon/ReconDistributedLock', () => {
  const originalDateNow = Date.now;

  afterEach(() => {
    Date.now = originalDateNow;
    delete require.cache[MODULE_PATH];
  });

  test('应获取单锁、包装 release、报告状态并处理 release 异常', async () => {
    const logs = [];
    let releaseShouldFail = false;
    const loaded = loadReconDistributedLock({
      onAcquire(resources, ttl) {
        return {
          lockKey: resources[0],
          ttl,
          async release() {
            if (releaseShouldFail) {
              throw new Error('release failed');
            }
          },
        };
      },
    });
    const redis = { disconnect: async () => {} };
    const lockManager = new loaded.ReconDistributedLock(redis, {
      logger: {
        debug: (event, meta) => logs.push(['debug', event, meta]),
        info: (event, meta) => logs.push(['info', event, meta]),
        warn: (event, meta) => logs.push(['warn', event, meta]),
      },
      retryCount: 5,
    });

    Date.now = () => 2000;
    const lock = await lockManager.acquireRowLock('hash-1', 7000);
    assert.strictEqual(lockManager.hasLock('hash-1'), true);
    assert.strictEqual(lockManager.getLockCount(), 1);
    assert.deepStrictEqual(loaded.state.constructorArgs[0].options, {
      driftFactor: 0.01,
      retryCount: 5,
      retryDelay: 200,
      retryJitter: 200,
    });
    assert.deepStrictEqual(lockManager.getLockStatus(), {
      totalLocks: 1,
      locks: [{
        hash: 'hash-1',
        acquiredAt: 2000,
        heldFor: 0,
        key: 'recon:lock:hash-1',
      }],
    });

    await lock.release();
    assert.strictEqual(lockManager.hasLock('hash-1'), false);
    assert.ok(logs.some(([level, event]) => level === 'info' && event === 'acquire_lock'));
    assert.ok(logs.some(([level, event]) => level === 'info' && event === 'lock_released'));

    releaseShouldFail = true;
    const failingLock = await lockManager.acquireRowLock('hash-2');
    await assert.rejects(
      failingLock.release(),
      /release failed/,
    );
    assert.ok(logs.some(([level, event]) => level === 'warn' && event === 'lock_release_error'));
  });

  test('应按排序批量获取锁，并在超时或中途失败时释放已获得的锁', async () => {
    const releaseLog = [];
    let now = 1000;
    Date.now = () => now;

    const loaded = loadReconDistributedLock({
      onAcquire(resources) {
        const lockKey = resources[0];
        if (lockKey.endsWith('b')) {
          throw new Error('b failed');
        }

        return {
          async release() {
            releaseLog.push(lockKey);
          },
        };
      },
    });
    const manager = new loaded.ReconDistributedLock({}, {
      logger: { debug() {}, info() {}, warn() {} },
    });

    await assert.rejects(
      manager.acquireBatchLocks(['b', 'a']),
      /b failed/,
    );
    assert.deepStrictEqual(
      loaded.state.acquireCalls.map(call => call.resources[0]),
      ['recon:lock:a', 'recon:lock:b'],
    );
    assert.deepStrictEqual(releaseLog, ['recon:lock:a']);

    const timeoutLoaded = loadReconDistributedLock({
      onAcquire(resources) {
        const lockKey = resources[0];
        now += 60;
        return {
          async release() {
            releaseLog.push(`timeout:${lockKey}`);
          },
        };
      },
    });
    const timeoutManager = new timeoutLoaded.ReconDistributedLock({}, {
      logger: { debug() {}, info() {}, warn() {} },
    });

    await assert.rejects(
      timeoutManager.acquireBatchLocks(['a', 'b', 'c'], { timeout: 50 }),
      /timeout after 50ms/,
    );
    assert.ok(releaseLog.includes('timeout:recon:lock:a'));
  });

  test('应处理批量释放、强制释放全部锁、断开连接与获取失败包装', async () => {
    const warnings = [];
    const loaded = loadReconDistributedLock({
      onAcquire(_resources, _ttl, errors) {
        throw new errors.ExecutionError('quorum failed', [{
          votesAgainst: new Map([
            ['redis-1', { error: new errors.ResourceLockedError('busy') }]
          ])
        }]);
      },
    });
    const redis = {
      disconnected: false,
      async disconnect() {
        this.disconnected = true;
      },
    };
    const manager = new loaded.ReconDistributedLock(redis, {
      logger: {
        debug() {},
        info() {},
        warn(event, meta) {
          warnings.push([event, meta]);
        },
      },
    });

    await assert.rejects(
      manager.acquireRowLock('hash-fail'),
      error => (
        error instanceof loaded.LockAcquireFailure
        && error.message.includes('hash-fail')
        && error.code === 'LOCK_CONTENDED'
      ),
    );

    const batchLocks = new Map([
      ['a', { release: async () => {} }],
      ['b', {
        release: async () => {
          throw new Error('batch fail');
        },
      }],
    ]);
    await manager.releaseBatchLocks(batchLocks);
    assert.ok(warnings.some(([event]) => event === 'batch_release_error'));

    manager.locks.set('x', {
      key: 'recon:lock:x',
      acquiredAt: 1,
      lock: { release: async () => {} },
    });
    manager.locks.set('y', {
      key: 'recon:lock:y',
      acquiredAt: 2,
      lock: {
        release: async () => {
          throw new Error('force fail');
        },
      },
    });

    await manager.releaseAllLocks();
    assert.strictEqual(manager.getLockCount(), 0);
    assert.ok(warnings.some(([event]) => event === 'releasing_all_locks'));
    assert.ok(warnings.some(([event]) => event === 'force_release_error'));

    manager.locks.set('z', {
      key: 'recon:lock:z',
      acquiredAt: 3,
      lock: { release: async () => {} },
    });
    await manager.disconnect();
    assert.strictEqual(redis.disconnected, true);
  });
});
