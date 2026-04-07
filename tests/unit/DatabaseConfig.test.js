'use strict';

const { afterEach, beforeEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('path');
const pg = require('pg');

const MODULE_PATH = path.resolve(__dirname, '../../config/database.js');
const ENV_KEYS = [
  'DB_HOST',
  'DB_PORT',
  'DB_NAME',
  'DB_USER',
  'DB_PASSWORD',
];

function setEnv(overrides = {}) {
  const snapshot = new Map();
  for (const key of ENV_KEYS) {
    snapshot.set(key, process.env[key]);
  }

  for (const key of ENV_KEYS) {
    if (Object.prototype.hasOwnProperty.call(overrides, key)) {
      process.env[key] = overrides[key];
    } else {
      delete process.env[key];
    }
  }

  return () => {
    for (const key of ENV_KEYS) {
      const value = snapshot.get(key);
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  };
}

function createPoolController() {
  const instances = [];

  class FakePool {
    constructor(config) {
      this.config = config;
      this.connectImpl = async () => ({
        query: async () => ({ rows: [{ ok: 1 }] }),
        release: () => {},
      });
      this.endCalls = 0;
      instances.push(this);
    }

    async connect() {
      return this.connectImpl();
    }

    async end() {
      this.endCalls += 1;
    }
  }

  return { FakePool, instances };
}

function loadDatabaseModule(options = {}) {
  const { env = {}, poolImpl } = options;
  const restoreEnv = setEnv(env);
  const originalPool = pg.Pool;

  delete require.cache[MODULE_PATH];
  pg.Pool = poolImpl;

  try {
    return require(MODULE_PATH);
  } finally {
    pg.Pool = originalPool;
    restoreEnv();
  }
}

describe('config/database', () => {
  let originalSetTimeout;
  let originalConsoleLog;

  beforeEach(() => {
    originalSetTimeout = global.setTimeout;
    originalConsoleLog = console.log;
  });

  afterEach(() => {
    global.setTimeout = originalSetTimeout;
    console.log = originalConsoleLog;
    delete require.cache[MODULE_PATH];
  });

  test('应按环境变量构建 DB_CONFIG，并缓存连接池单例', () => {
    const controller = createPoolController();
    const database = loadDatabaseModule({
      env: {
        DB_HOST: 'db.internal',
        DB_PORT: '6543',
        DB_NAME: 'metrics',
        DB_USER: 'tester',
        DB_PASSWORD: 'secret',
      },
      poolImpl: controller.FakePool,
    });

    assert.deepStrictEqual(database.DB_CONFIG, {
      host: 'db.internal',
      port: 6543,
      database: 'metrics',
      user: 'tester',
      password: 'secret',
      max: 50,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });

    const firstPool = database.getPool();
    const secondPool = database.getPool();

    assert.strictEqual(firstPool, secondPool);
    assert.strictEqual(controller.instances.length, 1);
    assert.deepStrictEqual(controller.instances[0].config, database.DB_CONFIG);
  });

  test('测试辅助器应恢复未定义环境变量，并允许默认 fake client 执行 query/release', async () => {
    const originalPassword = process.env.DB_PASSWORD;
    delete process.env.DB_PASSWORD;

    const restoreEnv = setEnv({ DB_PASSWORD: 'temporary-secret' });
    restoreEnv();
    assert.strictEqual(process.env.DB_PASSWORD, undefined);

    if (originalPassword !== undefined) {
      process.env.DB_PASSWORD = originalPassword;
    }

    const controller = createPoolController();
    const database = loadDatabaseModule({ poolImpl: controller.FakePool });
    const client = await database.getPool().connect();
    const result = await client.query('SELECT 1');

    assert.deepStrictEqual(result, { rows: [{ ok: 1 }] });
    assert.doesNotThrow(() => client.release());
  });

  test('withRetry 应支持旧签名、对象签名与命名签名的退避重试', async () => {
    const controller = createPoolController();
    const database = loadDatabaseModule({ poolImpl: controller.FakePool });
    const delays = [];
    const logs = [];

    global.setTimeout = (callback, delay) => {
      delays.push(delay);
      callback();
      return 1;
    };
    console.log = message => {
      logs.push(message);
    };

    let numericAttempts = 0;
    const numericResult = await database.withRetry(async () => {
      numericAttempts += 1;
      if (numericAttempts === 1) {
        const error = new Error('temporary');
        error.code = 'ECONNRESET';
        throw error;
      }
      return 'numeric-ok';
    }, 2, 5);
    assert.strictEqual(numericResult, 'numeric-ok');

    let objectAttempts = 0;
    const objectResult = await database.withRetry(async () => {
      objectAttempts += 1;
      if (objectAttempts === 1) {
        const error = new Error('08006 connection_failure');
        throw error;
      }
      return 'object-ok';
    }, { maxRetries: 2, initialDelayMs: 7 });
    assert.strictEqual(objectResult, 'object-ok');

    let namedAttempts = 0;
    const namedResult = await database.withRetry(async () => {
      namedAttempts += 1;
      if (namedAttempts === 1) {
        const error = new Error('still retryable');
        error.code = 'ETIMEDOUT';
        throw error;
      }
      return 'named-ok';
    }, 'smelter', { maxRetries: 2, initialDelayMs: 11 });
    assert.strictEqual(namedResult, 'named-ok');

    assert.deepStrictEqual(delays, [5, 7, 11]);
    assert.ok(logs.some(message => message.includes('[DB] 重试 1/2')));
    assert.ok(logs.some(message => message.includes('[smelter] [DB] 重试 1/2')));
  });

  test('withRetry 应在不可重试错误时立即抛出，并在重试耗尽后返回最后一次错误', async () => {
    const controller = createPoolController();
    const database = loadDatabaseModule({ poolImpl: controller.FakePool });
    const delays = [];

    global.setTimeout = (callback, delay) => {
      delays.push(delay);
      callback();
      return 1;
    };

    let fatalAttempts = 0;
    const fatalError = new Error('fatal');
    fatalError.code = 'EINVAL';

    await assert.rejects(
      database.withRetry(async () => {
        fatalAttempts += 1;
        throw fatalError;
      }, 4, 3),
      fatalError,
    );
    assert.strictEqual(fatalAttempts, 1);
    assert.deepStrictEqual(delays, []);

    let exhaustedAttempts = 0;
    const exhaustedError = new Error('timeout forever');
    exhaustedError.code = 'ETIMEDOUT';

    await assert.rejects(
      database.withRetry(async () => {
        exhaustedAttempts += 1;
        throw exhaustedError;
      }, 2, 9),
      exhaustedError,
    );
    assert.strictEqual(exhaustedAttempts, 2);
    assert.deepStrictEqual(delays, [9]);
  });

  test('isRetryableError、checkHealth 与 closePool 应覆盖成功和失败分支', async () => {
    const controller = createPoolController();
    const database = loadDatabaseModule({ poolImpl: controller.FakePool });
    const logs = [];

    console.log = message => {
      logs.push(message);
    };

    assert.strictEqual(database.isRetryableError({ code: 'ECONNREFUSED' }), true);
    assert.strictEqual(database.isRetryableError({ message: '08001 transient failure' }), true);
    assert.strictEqual(database.isRetryableError({ code: 'EINVAL', message: 'permanent failure' }), false);

    const pool = database.getPool();
    let released = false;
    pool.connectImpl = async () => ({
      query: async sql => {
        assert.strictEqual(sql, 'SELECT 1');
        return { rowCount: 1 };
      },
      release: () => {
        released = true;
      },
    });

    const healthy = await database.checkHealth();
    assert.strictEqual(healthy.healthy, true);
    assert.strictEqual(typeof healthy.latency, 'number');
    assert.strictEqual(released, true);

    pool.connectImpl = async () => {
      throw new Error('db unavailable');
    };

    const unhealthy = await database.checkHealth();
    assert.deepStrictEqual(unhealthy, {
      healthy: false,
      error: 'db unavailable',
    });

    await database.closePool();
    assert.strictEqual(pool.endCalls, 1);
    assert.ok(logs.some(message => message.includes('连接池已关闭')));

    const reopened = database.getPool();
    assert.notStrictEqual(reopened, pool);
    assert.strictEqual(controller.instances.length, 2);
  });
});
