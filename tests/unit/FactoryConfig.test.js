'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../config/factory_config.js');
const ENV_KEYS = [
  'MIN_SIZE_BYTES',
  'MIN_SIZE_BYTES_FUTURE',
  'MIN_DELAY_MS',
  'MAX_DELAY_MS',
  'MAX_RETRY_ATTEMPTS',
  'BACKOFF_BASE',
  'MAX_BACKOFF_MS',
  'PROXY_PORTS',
  'PROXY_PORT',
  'PROXY_SERVER',
  'BROWSER_PROFILE_PATH',
  'ENABLE_COOL_DOWN',
  'COOL_DOWN_THRESHOLD',
  'COOL_DOWN_DURATION_MS',
];

function withEnv(overrides = {}) {
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

function loadFactoryConfig(env = {}) {
  const restoreEnv = withEnv(env);
  delete require.cache[MODULE_PATH];

  try {
    return require(MODULE_PATH);
  } finally {
    restoreEnv();
  }
}

describe('config/factory_config', () => {
  const originalRandom = Math.random;
  const originalDateNow = Date.now;
  const originalConsoleLog = console.log;

  afterEach(() => {
    Math.random = originalRandom;
    Date.now = originalDateNow;
    console.log = originalConsoleLog;
    delete require.cache[MODULE_PATH];
  });

  test('QUALITY_GATE 应覆盖空数据、体积阈值、缺失路径、关键字与有效数据分支', () => {
    const smallThresholdConfig = loadFactoryConfig({
      MIN_SIZE_BYTES: '200',
      MIN_SIZE_BYTES_FUTURE: '1',
    });

    assert.deepStrictEqual(
      smallThresholdConfig.QUALITY_GATE.isValid(null),
      { valid: false, reason: 'NULL_DATA' },
    );

    assert.deepStrictEqual(
      smallThresholdConfig.QUALITY_GATE.isValid({ general: {}, header: {} }),
      { valid: false, reason: 'MISSING_CONTENT' },
    );

    const statsTooSmall = smallThresholdConfig.QUALITY_GATE.isValid({
      content: { stats: { shots: 1 } },
      general: {},
      header: {},
    });
    assert.strictEqual(statsTooSmall.valid, false);
    assert.strictEqual(statsTooSmall.reason, 'SIZE_TOO_SMALL');
    assert.strictEqual(statsTooSmall.hasStats, true);

    const keywordConfig = loadFactoryConfig({
      MIN_SIZE_BYTES: '1',
      MIN_SIZE_BYTES_FUTURE: '1',
    });
    const blocked = keywordConfig.QUALITY_GATE.isValid({
      content: { message: 'Verification required by CAPTCHA wall' },
      general: {},
      header: {},
    });
    assert.strictEqual(blocked.valid, false);
    assert.strictEqual(blocked.reason, 'CONTAINS_VERIFICATION REQUIRED');

    const valid = keywordConfig.QUALITY_GATE.isValid({
      content: { stats: { possession: 55 }, details: 'x'.repeat(32) },
      general: { stage: 'completed' },
      header: { league: 'EPL' },
    });
    assert.strictEqual(valid.valid, true);
    assert.strictEqual(valid.hasStats, true);
    assert.ok(valid.size > 1);
  });

  test('RETRY、PROXY_CONFIG、BROWSER 与 FINGERPRINT 应返回确定结果', () => {
    const logs = [];
    console.log = message => {
      logs.push(message);
    };

    const factoryConfig = loadFactoryConfig({
      PROXY_PORTS: '8001,8002,8003',
      PROXY_PORT: '8002',
      PROXY_SERVER: 'http://127.0.0.1:{port}',
      BROWSER_PROFILE_PATH: '/tmp/browser-profile',
    });

    Math.random = () => 0.99;

    assert.strictEqual(factoryConfig.RETRY.isRetryable('TIMEOUT_ERROR'), true);
    assert.strictEqual(factoryConfig.RETRY.isRetryable('ACCESS_DENIED'), false);

    assert.strictEqual(factoryConfig.PROXY_CONFIG.getServer(), 'http://127.0.0.1:8002');
    assert.strictEqual(factoryConfig.PROXY_CONFIG.getServer(8003), 'http://127.0.0.1:8003');
    assert.strictEqual(factoryConfig.PROXY_CONFIG.getPortByWorker(4), 8001);
    assert.strictEqual(factoryConfig.PROXY_CONFIG.getNextPort(8003), 8001);
    assert.strictEqual(factoryConfig.PROXY_CONFIG.getRandomPort(), 8003);

    factoryConfig.PROXY_CONFIG.expandPorts(5);
    assert.deepStrictEqual(factoryConfig.PROXY_CONFIG.ports, [8001, 8002, 8003, 8006, 8007]);

    factoryConfig.PROXY_CONFIG.printStatus();
    assert.strictEqual(logs.length, 2);
    assert.ok(logs[0].includes(String(factoryConfig.PROXY_CONFIG.ports.length)));
    assert.ok(logs[1].includes('8001 - 8007'));

    assert.strictEqual(
      factoryConfig.BROWSER.getStatePath(),
      '/tmp/browser-profile/browser_state.json',
    );
    assert.ok(factoryConfig.FINGERPRINT.getRandomUA().includes('Safari'));
    assert.deepStrictEqual(factoryConfig.FINGERPRINT.getRandomViewport(), {
      width: 1287,
      height: 1271,
    });
  });

  test('FOTMOB_COOL_DOWN 与辅助函数应覆盖触发、过期与随机工具分支', () => {
    const logs = [];
    console.log = message => {
      logs.push(message);
    };

    const factoryConfig = loadFactoryConfig({
      ENABLE_COOL_DOWN: 'true',
      COOL_DOWN_THRESHOLD: '2',
      COOL_DOWN_DURATION_MS: '60000',
      MIN_DELAY_MS: '10',
      MAX_DELAY_MS: '20',
    });

    const coolDown = factoryConfig.FOTMOB_COOL_DOWN;
    coolDown._activeCoolDowns.clear();

    Date.now = () => 1000;
    assert.strictEqual(coolDown.shouldTrigger('CAPTCHA_BLOCK', 2), true);
    assert.strictEqual(coolDown.shouldTrigger('NETWORK_ERROR', 5), false);

    coolDown.enterCoolDown(7);
    assert.ok(logs.some(message => message.includes('Worker 7')));
    assert.strictEqual(coolDown.isInCoolDown(7), true);
    assert.strictEqual(coolDown.getRemainingTime(7), 60000);

    Date.now = () => 62050;
    assert.strictEqual(coolDown.isInCoolDown(7), false);
    assert.strictEqual(coolDown.getRemainingTime(7), 0);

    Math.random = () => 0.5;
    assert.strictEqual(factoryConfig.getRandomDelay([10, 20]), 15);
    assert.strictEqual(factoryConfig.getExponentialBackoff(3), 4000);
    assert.strictEqual(factoryConfig.getExponentialBackoff(6), 4000);
    assert.strictEqual(factoryConfig.randomInRange(2, 6), 4);
    assert.strictEqual(factoryConfig.randomChoice(['home', 'draw', 'away']), 'draw');
  });
});
