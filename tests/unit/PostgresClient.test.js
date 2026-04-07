'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');

const {
  DatabaseConfig,
  ProxyConfig,
  HarvestConfig,
  LogConfig,
  validateConfig,
  getConfigSummary
} = require('../../src/infrastructure/database/PostgresClient');

describe('PostgresClient config', () => {
  const originalEnv = {
    DB_HOST: process.env.DB_HOST,
    DB_PORT: process.env.DB_PORT,
    DB_NAME: process.env.DB_NAME,
    DB_USER: process.env.DB_USER,
    DB_PASSWORD: process.env.DB_PASSWORD,
    ENABLE_PROXY_ROTATION: process.env.ENABLE_PROXY_ROTATION,
    PROXY_HOST: process.env.PROXY_HOST,
    PROXY_PORT_START: process.env.PROXY_PORT_START,
    PROXY_PORT_END: process.env.PROXY_PORT_END,
    PROXY_PROTOCOL: process.env.PROXY_PROTOCOL,
    CONCURRENT_THREADS: process.env.CONCURRENT_THREADS,
    HEADLESS_MODE: process.env.HEADLESS_MODE,
    WAIT_BASE_MS: process.env.WAIT_BASE_MS,
    WAIT_JITTER_MS: process.env.WAIT_JITTER_MS,
    LOG_LEVEL: process.env.LOG_LEVEL,
    LOG_DIR: process.env.LOG_DIR,
    NODE_ENV: process.env.NODE_ENV
  };
  const originalWarn = console.warn;

  afterEach(() => {
    Object.entries(originalEnv).forEach(([key, value]) => {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    });
    console.warn = originalWarn;
  });

  it('应从环境变量读取数据库、代理、收割与日志配置', () => {
    process.env.DB_HOST = 'db.internal';
    process.env.DB_PORT = '5544';
    process.env.DB_NAME = 'matches';
    process.env.DB_USER = 'analyst';
    process.env.DB_PASSWORD = 'secret';
    process.env.ENABLE_PROXY_ROTATION = 'true';
    process.env.PROXY_HOST = '10.0.0.8';
    process.env.PROXY_PORT_START = '8000';
    process.env.PROXY_PORT_END = '8010';
    process.env.PROXY_PROTOCOL = 'https';
    process.env.CONCURRENT_THREADS = '12';
    process.env.HEADLESS_MODE = 'false';
    process.env.WAIT_BASE_MS = '900';
    process.env.WAIT_JITTER_MS = '300';
    process.env.LOG_LEVEL = 'debug';
    process.env.LOG_DIR = '/tmp/custom-logs';

    assert.strictEqual(DatabaseConfig.host, 'db.internal');
    assert.strictEqual(DatabaseConfig.port, 5544);
    assert.strictEqual(DatabaseConfig.database, 'matches');
    assert.strictEqual(DatabaseConfig.user, 'analyst');
    assert.strictEqual(DatabaseConfig.password, 'secret');
    assert.strictEqual(
      DatabaseConfig.connectionString,
      'postgresql://analyst:secret@db.internal:5544/matches'
    );

    assert.strictEqual(ProxyConfig.enabled, true);
    assert.strictEqual(ProxyConfig.host, '10.0.0.8');
    assert.strictEqual(ProxyConfig.portStart, 8000);
    assert.strictEqual(ProxyConfig.portEnd, 8010);
    assert.strictEqual(ProxyConfig.protocol, 'https');

    assert.strictEqual(HarvestConfig.concurrentThreads, 12);
    assert.strictEqual(HarvestConfig.headless, false);
    assert.strictEqual(HarvestConfig.waitBaseMs, 900);
    assert.strictEqual(HarvestConfig.waitJitterMs, 300);

    assert.strictEqual(LogConfig.level, 'debug');
    assert.strictEqual(LogConfig.logDir, '/tmp/custom-logs');

    assert.deepStrictEqual(getConfigSummary(), {
      database: {
        host: 'db.internal',
        port: 5544,
        database: 'matches',
        user: 'analyst',
        passwordSet: true
      },
      proxy: {
        enabled: true,
        host: '10.0.0.8',
        portRange: '8000-8010'
      },
      harvest: {
        concurrentThreads: 12,
        headless: false
      },
      log: {
        level: 'debug',
        logDir: '/tmp/custom-logs'
      }
    });
  });

  it('缺少密码时应告警，并在生产环境下返回无效配置', () => {
    const warnings = [];
    delete process.env.DB_PASSWORD;
    process.env.NODE_ENV = 'production';
    console.warn = (message) => {
      warnings.push(message);
    };

    assert.strictEqual(DatabaseConfig.password, '');
    assert.ok(warnings.some((message) => message.includes('DB_PASSWORD 未设置')));
    assert.deepStrictEqual(validateConfig(), {
      errors: ['生产环境必须设置 DB_PASSWORD'],
      warnings: ['DB_PASSWORD 未设置'],
      valid: false
    });
  });

  it('非生产环境缺少密码时应只产生警告，不阻断配置有效性', () => {
    delete process.env.DB_PASSWORD;
    process.env.NODE_ENV = 'development';

    assert.deepStrictEqual(validateConfig(), {
      errors: [],
      warnings: ['DB_PASSWORD 未设置'],
      valid: true
    });
  });
});
