'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/network/NetworkShield.js');
const LOGGER_ID = path.resolve(__dirname, '../../src/infrastructure/utils/Logger.js');
const FACTORY_ID = path.resolve(__dirname, '../../config/factory_config.js');

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

function loadNetworkShield(logger) {
  const restoreLogger = overrideModule(LOGGER_ID, { logger });
  const restoreFactory = overrideModule(FACTORY_ID, {});
  delete require.cache[MODULE_PATH];

  try {
    return require(MODULE_PATH);
  } finally {
    restoreLogger();
    restoreFactory();
  }
}

describe('src/infrastructure/network/NetworkShield', () => {
  const originalDateNow = Date.now;
  const originalRandom = Math.random;
  const originalSetTimeout = global.setTimeout;

  afterEach(() => {
    Date.now = originalDateNow;
    Math.random = originalRandom;
    global.setTimeout = originalSetTimeout;
    delete require.cache[MODULE_PATH];
  });

  test('应分配端口、复用绑定、更新成功状态并返回代理池状态', async () => {
    const logs = [];
    const logger = {
      info: (...args) => logs.push(['info', args]),
      warn: (...args) => logs.push(['warn', args]),
      error: (...args) => logs.push(['error', args]),
      debug: (...args) => logs.push(['debug', args]),
    };
    const { NetworkShield, getNetworkShield } = loadNetworkShield(logger);

    const shield = new NetworkShield({
      proxyNodes: [
        { host: 'h', port: 7890, url: 'http://h:7890', status: 'active', failureCount: 2, lastFailure: null },
        { host: 'h', port: 7891, url: 'http://h:7891', status: 'active', failureCount: 0, lastFailure: null },
      ],
    });

    const first = shield.assignPort(1);
    assert.deepStrictEqual(first, { host: 'h', port: 7891, url: 'http://h:7891' });
    assert.deepStrictEqual(shield.assignPort(1), first);

    shield.markSuccess(7890);
    assert.strictEqual(shield.proxyNodes[0].failureCount, 0);
    assert.strictEqual(shield.proxyNodes[0].status, 'active');

    assert.deepStrictEqual(await shield.getNextHealthyProxy('WORKER-2'), {
      sessionId: 'WORKER-2',
      port: 7890,
      url: 'http://h:7890',
    });
    assert.deepStrictEqual(shield.getStatus(), {
      total: 2,
      active: 2,
      cooldown: 0,
      assignments: { 1: 7891, 2: 7890 },
    });

    const singletonA = getNetworkShield({ proxyNodes: shield.proxyNodes });
    const singletonB = getNetworkShield({ proxyNodes: [] });
    assert.strictEqual(singletonA, singletonB);
    assert.ok(logs.some(([level]) => level === 'info'));
  });

  test('markFailed 应触发熔断恢复，assignPort/forceReassign 应覆盖全局熔断分支', async () => {
    const logs = [];
    const logger = {
      info: (...args) => logs.push(['info', args]),
      warn: (...args) => logs.push(['warn', args]),
      error: (...args) => logs.push(['error', args]),
      debug: (...args) => logs.push(['debug', args]),
    };
    const { NetworkShield } = loadNetworkShield(logger);

    let timerCallback = null;
    global.setTimeout = callback => {
      timerCallback = callback;
      return 1;
    };
    Date.now = () => 1000;

    const shield = new NetworkShield({
      proxyNodes: [
        { host: 'h', port: 7890, url: 'http://h:7890', status: 'active', failureCount: 4, lastFailure: null },
        { host: 'h', port: 7891, url: 'http://h:7891', status: 'cooldown', failureCount: 5, lastFailure: null },
      ],
    });

    shield.markFailed(7890, 'timeout');
    assert.strictEqual(shield.proxyNodes[0].status, 'cooldown');
    assert.deepStrictEqual(shield.proxyNodes[0].lastFailure, { time: 1000, reason: 'timeout' });
    timerCallback();
    assert.strictEqual(shield.proxyNodes[0].status, 'active');
    assert.strictEqual(shield.proxyNodes[0].failureCount, 0);

    shield.proxyNodes.forEach(node => {
      node.status = 'cooldown';
      node.failureCount = 5;
    });
    Math.random = () => 0;
    const reassigned = shield.assignPort(3);
    assert.strictEqual(reassigned.port, 7891);
    assert.ok(logs.some(([level, args]) => level === 'warn' && String(args[0]).includes('尝试重置')));

    shield.proxyNodes.forEach(node => {
      node.status = 'cooldown';
      node.failureCount = 5;
    });
    shield.lastGlobalResetTime = 2000;
    Date.now = () => 5000;
    assert.throws(
      () => shield.assignPort(4),
      error => error && error.code === 'CIRCUIT_BREAKER_OPEN',
    );

    shield.lastGlobalResetTime = 0;
    assert.throws(
      () => shield.assignPort(4, 3),
      error => error && error.code === 'CIRCUIT_BREAKER_OPEN' && error.message.includes('已重试 3 次'),
    );

    shield.proxyNodes = [
      { host: 'h', port: 7890, url: 'http://h:7890', status: 'active', failureCount: 0, lastFailure: null },
      { host: 'h', port: 7891, url: 'http://h:7891', status: 'active', failureCount: 0, lastFailure: null },
    ];
    shield.portAssignments.set(7, 7890);
    Math.random = () => 0;
    const changed = shield.forceReassign(7, 7890);
    assert.strictEqual(changed.port, 7891);

    shield.proxyNodes.forEach(node => {
      node.status = 'cooldown';
      node.failureCount = 5;
    });
    shield.lastGlobalResetTime = 2000;
    Date.now = () => 3000;
    assert.throws(
      () => shield.forceReassign(7, 7891),
      error => error && error.code === 'CIRCUIT_BREAKER_OPEN' && error.message.includes('全局冷却中'),
    );
    assert.ok(logs.some(([level]) => level === 'error'));
  });

  test('应保护页面并创建受保护上下文', async () => {
    const logger = { info() {}, warn() {}, error() {}, debug() {} };
    const { NetworkShield } = loadNetworkShield(logger);
    const shield = new NetworkShield({
      proxyNodes: [
        { host: 'h', port: 7890, url: 'http://h:7890', status: 'active', failureCount: 0, lastFailure: null },
      ],
    });

    const headerCalls = [];
    await shield.protect({
      async setExtraHTTPHeaders(headers) {
        headerCalls.push(headers);
      },
    });
    assert.strictEqual(headerCalls.length, 1);
    assert.strictEqual(headerCalls[0]['Accept-Language'], 'en-US,en;q=0.9');

    const context = await shield.getNewContext({
      async newContext(options) {
        return { options };
      },
    }, { viewport: { width: 1366, height: 768 }, locale: 'en-US' });

    assert.deepStrictEqual(context, {
      options: {
        viewport: { width: 1366, height: 768 },
        userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        locale: 'en-US',
      },
    });
  });
});
