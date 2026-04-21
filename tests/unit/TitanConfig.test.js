const { describe, it } = require('node:test');
const assert = require('node:assert');
const Module = require('node:module');
const { TitanConfig } = require('../../src/infrastructure/config/TitanConfig');

function restoreEnv(key, value) {
  if (typeof value === 'undefined') {
    delete process.env[key];
    return;
  }

  process.env[key] = value;
}

describe('TitanConfig', () => {
  it('应该加载默认配置', () => {
    const config = new TitanConfig();
    const db = config.getDatabase();

    assert.strictEqual(db.name, 'football_db');
    assert.strictEqual(db.user, 'football_user');
    assert.strictEqual(db.port, 5432);
  });

  it('应该验证必填配置', () => {
    const originalPassword = process.env.DB_PASSWORD;
    process.env.DB_PASSWORD = '';

    try {
      const config = new TitanConfig();

      assert.throws(() => {
        config.validateConfig();
      }, /DB_PASSWORD 未设置/);
    } finally {
      if (typeof originalPassword === 'undefined') {
        delete process.env.DB_PASSWORD;
      } else {
        process.env.DB_PASSWORD = originalPassword;
      }
    }
  });

  it('应该通过路径访问配置', () => {
    const config = new TitanConfig();
    const db = config.get('database');

    assert.ok(db);
    assert.strictEqual(db.name, 'football_db');
  });

  it('应该返回环境信息', () => {
    const config = new TitanConfig();
    const env = config.getEnvironment();

    assert.strictEqual(typeof env.nodeEnv, 'string');
    assert.strictEqual(typeof env.dockerEnv, 'boolean');
  });

  it('应该加载代理配置', () => {
    const config = new TitanConfig();
    const proxy = config.getProxy();

    assert.ok(proxy.host);
    assert.ok(Array.isArray(proxy.ports));
  });

  it('应该在代理池配置加载失败时回退到环境变量代理配置', () => {
    const originalHost = process.env.PROXY_HOST;
    const originalProtocol = process.env.PROXY_PROTOCOL;
    const originalRequire = Module.prototype.require;

    process.env.PROXY_HOST = 'proxy.internal';
    process.env.PROXY_PROTOCOL = 'socks5';
    Module.prototype.require = function patchedRequire(specifier, ...args) {
      if (specifier === '../../../config/proxy_pool') {
        throw new Error('proxy pool unavailable');
      }

      return originalRequire.call(this, specifier, ...args);
    };

    try {
      const config = new TitanConfig();

      assert.deepStrictEqual(config.getProxy(), {
        host: 'proxy.internal',
        ports: [],
        portStart: 0,
        portEnd: 0,
        protocol: 'socks5'
      });
    } finally {
      Module.prototype.require = originalRequire;
      restoreEnv('PROXY_HOST', originalHost);
      restoreEnv('PROXY_PROTOCOL', originalProtocol);
    }
  });

  it('应该聚合配置错误并暴露所有核心配置分区', () => {
    const snapshot = {
      DB_PASSWORD: process.env.DB_PASSWORD,
      DB_PORT: process.env.DB_PORT,
      MAX_WORKERS: process.env.MAX_WORKERS,
      MIN_DELAY_MS: process.env.MIN_DELAY_MS,
      MAX_DELAY_MS: process.env.MAX_DELAY_MS,
      NODE_ENV: process.env.NODE_ENV,
      DOCKER_ENV: process.env.DOCKER_ENV,
      REDIS_PASSWORD: process.env.REDIS_PASSWORD,
      BROWSER_HEADLESS: process.env.BROWSER_HEADLESS
    };

    Object.assign(process.env, {
      DB_PASSWORD: 'db-secret',
      DB_PORT: '70000',
      MAX_WORKERS: '0',
      MIN_DELAY_MS: '5000',
      MAX_DELAY_MS: '5000',
      NODE_ENV: 'production',
      DOCKER_ENV: 'true',
      REDIS_PASSWORD: 'redis-secret',
      BROWSER_HEADLESS: 'false'
    });

    try {
      const config = new TitanConfig();

      assert.throws(() => {
        config.validateConfig();
      }, /DB_PORT 无效: 70000[\s\S]*MAX_WORKERS 必须 >= 1[\s\S]*MIN_DELAY_MS 必须小于 MAX_DELAY_MS/);

      assert.strictEqual(config.get('database.missing'), undefined);
      assert.strictEqual(config.getRedis().password, 'redis-secret');
      assert.strictEqual(config.getBrowser().headless, false);
      assert.strictEqual(config.getHarvester().maxWorkers, 0);
      assert.strictEqual(config.getLogging().level, process.env.LOG_LEVEL || 'info');
      assert.strictEqual(config.isProduction(), true);
      assert.strictEqual(config.isDevelopment(), false);
      assert.strictEqual(config.isDocker(), true);
      assert.deepStrictEqual(config.toJSON().database.password, '***');
      assert.deepStrictEqual(config.toJSON().redis.password, '***');
    } finally {
      for (const [key, value] of Object.entries(snapshot)) {
        restoreEnv(key, value);
      }
    }
  });

  it('应该通过模块导出包装访问默认实例', () => {
    const modulePath = require.resolve('../../src/infrastructure/config/TitanConfig');
    delete require.cache[modulePath];
    const configModule = require('../../src/infrastructure/config/TitanConfig');

    assert.ok(configModule.titanConfig);
    assert.strictEqual(configModule.getConfig('database.name'), 'football_db');
    assert.ok(configModule.getDatabase());
    assert.ok(configModule.getRedis());
    assert.ok(configModule.getProxy());
    assert.ok(configModule.getBrowser());
    assert.ok(configModule.getHarvester());
    assert.ok(configModule.getLogging());
    assert.ok(configModule.getEnvironment());
  });
});
