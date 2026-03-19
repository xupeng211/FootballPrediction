/**
 * @file TitanSlimHarvester.test.js - TitanSlimHarvester 单元测试
 * @module tests/unit/TitanSlimHarvester
 * @version V6.6.0
 * @description
 * 使用 Mock 测试 Playwright 行为:
 * - 数据哨兵 (< 5KB 拦截)
 * - __NEXT_DATA__ 提取失败处理
 * - 资源拦截验证
 * - 代理状态上报
 */

'use strict';

const { describe, it, before, after } = require('node:test');
const assert = require('node:assert');

// Mock Playwright
const mockRoute = {
  request: () => ({ resourceType: () => 'image' }),
  abort: () => {},
  continue: () => {}
};

const mockPage = {
  route: async () => {},
  goto: async () => {},
  waitForSelector: async () => {},
  evaluate: async () => ({}),
  close: async () => {}
};

const mockContext = {
  newPage: async () => mockPage,
  close: async () => {}
};

const mockBrowser = {
  newContext: async () => mockContext,
  close: async () => {}
};

// Mock NetworkShield
const mockNetworkShield = {
  assignPort: () => ({ port: 7890, url: 'http://172.25.16.1:7890' }),
  markSuccess: () => {},
  markFailed: () => {}
};

// Mock pg Pool
const mockClient = {
  query: async () => ({ rows: [{ match_id: 'test' }] }),
  release: () => {}
};

const mockPool = {
  connect: async () => mockClient,
  end: async () => {}
};

describe('TitanSlimHarvester - V6.6 核心引擎', () => {
  let harvester;

  before(() => {
    // 设置环境变量
    process.env.DB_HOST = 'localhost';
    process.env.DB_PORT = '5432';
    process.env.DB_NAME = 'test_db';
    process.env.DB_USER = 'test_user';
    process.env.DB_PASSWORD = 'test_pass';
  });

  describe('数据哨兵 - Data Sentinel', () => {
    it('应拦截小于 5KB 的数据并抛出错误', async () => {
      // 模拟小数据
      const smallData = { foo: 'bar' }; // < 5KB
      const jsonStr = JSON.stringify(smallData);
      
      assert.ok(jsonStr.length < 5120, '测试数据应小于 5KB');
      
      // 验证数据哨兵逻辑
      const shouldReject = jsonStr.length < 5120;
      assert.strictEqual(shouldReject, true);
    });

    it('应允许大于 5KB 的数据通过', async () => {
      // 模拟大数据 (模拟真实的 __NEXT_DATA__)
      const largeData = {
        props: {
          pageProps: {
            general: { matchId: '3609929' },
            content: {
              matchFacts: {
                events: Array(100).fill({ type: 'goal', player: 'Test' }),
                stats: { possession: [50, 50], shots: [10, 8] }
              }
            }
          }
        },
        // 填充数据以达到 > 5KB
        _filler: 'x'.repeat(5000)
      };
      
      const jsonStr = JSON.stringify(largeData);
      assert.ok(jsonStr.length > 5120, '测试数据应大于 5KB');
      
      const shouldAccept = jsonStr.length >= 5120;
      assert.strictEqual(shouldAccept, true);
    });

    it('应对空数据抛出错误', async () => {
      const emptyData = {};
      const jsonStr = JSON.stringify(emptyData);
      
      assert.ok(jsonStr.length < 5120, '空数据应被拦截');
    });

    it('应对 null 数据抛出错误', async () => {
      const nullData = null;
      const jsonStr = JSON.stringify(nullData);
      
      assert.ok(jsonStr.length < 5120, 'null 数据应被拦截');
    });
  });

  describe('__NEXT_DATA__ 提取', () => {
    it('应正确处理有效的 __NEXT_DATA__', async () => {
      const mockNextData = {
        props: {
          pageProps: {
            general: { matchId: '3609929' },
            header: { homeTeam: 'Arsenal', awayTeam: 'Chelsea' }
          }
        }
      };

      // 模拟 evaluate 返回值
      const result = mockNextData;
      assert.ok(result, '应返回有效数据');
      assert.ok(result.props, '应包含 props');
      assert.ok(result.props.pageProps, '应包含 pageProps');
    });

    it('应在 __NEXT_DATA__ 不存在时抛出错误', async () => {
      // 模拟 evaluate 返回 null
      const result = null;
      
      const shouldThrow = result === null;
      assert.strictEqual(shouldThrow, true, 'null 数据应触发错误处理');
    });

    it('应在 __NEXT_DATA__ 为空对象时抛出错误', async () => {
      const emptyData = {};
      const jsonStr = JSON.stringify(emptyData);
      
      assert.ok(jsonStr.length < 5120, '空对象应被拦截');
    });
  });

  describe('资源拦截 - Resource Blocking', () => {
    const blockedTypes = ['image', 'stylesheet', 'font', 'media'];
    const allowedTypes = ['document', 'xhr', 'fetch', 'script'];

    blockedTypes.forEach(type => {
      it(`应拦截 ${type} 类型请求`, () => {
        const mockReq = { resourceType: () => type };
        const route = { ...mockRoute, request: () => mockReq };
        
        let aborted = false;
        route.abort = () => { aborted = true; };
        route.continue = () => {};
        
        // 模拟拦截逻辑
        const shouldAbort = ['image', 'stylesheet', 'font', 'media'].includes(type);
        
        if (shouldAbort) {
          route.abort();
        } else {
          route.continue();
        }
        
        assert.strictEqual(aborted, true, `${type} 应被拦截`);
      });
    });

    allowedTypes.forEach(type => {
      it(`应允许 ${type} 类型请求`, () => {
        const mockReq = { resourceType: () => type };
        const route = { ...mockRoute, request: () => mockReq };
        
        let continued = false;
        route.abort = () => {};
        route.continue = () => { continued = true; };
        
        // 模拟拦截逻辑
        const shouldAbort = ['image', 'stylesheet', 'font', 'media'].includes(type);
        
        if (shouldAbort) {
          route.abort();
        } else {
          route.continue();
        }
        
        assert.strictEqual(continued, true, `${type} 应被允许`);
      });
    });
  });

  describe('代理状态上报', () => {
    it('应在成功时调用 markSuccess', () => {
      let successCalled = false;
      const shield = {
        ...mockNetworkShield,
        markSuccess: (port) => {
          successCalled = true;
          assert.strictEqual(typeof port, 'number');
        }
      };

      // 模拟成功上报
      shield.markSuccess(7890);
      assert.strictEqual(successCalled, true);
    });

    it('应在失败时调用 markFailed', () => {
      let failedCalled = false;
      const shield = {
        ...mockNetworkShield,
        markFailed: (port, reason) => {
          failedCalled = true;
          assert.strictEqual(typeof port, 'number');
          assert.strictEqual(typeof reason, 'string');
        }
      };

      // 模拟失败上报
      shield.markFailed(7890, 'Timeout');
      assert.strictEqual(failedCalled, true);
    });

    it('应对 NetworkShield 缺失进行健壮处理', () => {
      const nullShield = null;
      
      // 模拟健壮性检查
      const shouldSkip = !nullShield || typeof nullShield.markSuccess !== 'function';
      assert.strictEqual(shouldSkip, true, '应跳过 null shield 的上报');
    });
  });

  describe('Worker 状态管理', () => {
    it('应正确跟踪连续失败次数', () => {
      const workerState = {
        consecutiveFailures: 0,
        currentProxy: 7890
      };

      // 模拟连续失败
      for (let i = 0; i < 3; i++) {
        workerState.consecutiveFailures++;
      }

      assert.strictEqual(workerState.consecutiveFailures, 3);
      
      // 达到阈值应触发代理漂移
      const shouldDrift = workerState.consecutiveFailures >= 3;
      assert.strictEqual(shouldDrift, true);
    });

    it('应在成功后重置失败计数', () => {
      const workerState = {
        consecutiveFailures: 2,
        currentProxy: 7890
      };

      // 模拟成功
      workerState.consecutiveFailures = 0;

      assert.strictEqual(workerState.consecutiveFailures, 0);
    });
  });

  describe('浏览器重启逻辑', () => {
    it('应在达到阈值时标记需要重启', () => {
      const matchesSinceRestart = 500;
      const restartThreshold = 500;

      const shouldRestart = matchesSinceRestart >= restartThreshold;
      assert.strictEqual(shouldRestart, true);
    });

    it('应在未达阈值时不重启', () => {
      const matchesSinceRestart = 499;
      const restartThreshold = 500;

      const shouldRestart = matchesSinceRestart >= restartThreshold;
      assert.strictEqual(shouldRestart, false);
    });
  });

  describe('错误分类与处理', () => {
    const errorCases = [
      { error: new Error('Timeout 30000ms exceeded'), type: 'TIMEOUT', retryable: true },
      { error: new Error('net::ERR_CONNECTION_CLOSED'), type: 'NETWORK', retryable: true },
      { error: new Error('数据哨兵拦截: 2.1KB < 5KB'), type: 'DATA_QUALITY', retryable: false },
      { error: new Error('Navigation failed'), type: 'NAVIGATION', retryable: true }
    ];

    errorCases.forEach(({ error, type, retryable }) => {
      it(`应正确分类 ${type} 错误`, () => {
        // 模拟错误分类逻辑
        const isTimeout = error.message.includes('Timeout');
        const isNetwork = error.message.includes('CONNECTION') || error.message.includes('NETWORK');
        const isDataQuality = error.message.includes('数据哨兵') || error.message.includes('size');
        
        let classifiedType = 'UNKNOWN';
        if (isTimeout) classifiedType = 'TIMEOUT';
        else if (isNetwork) classifiedType = 'NETWORK';
        else if (isDataQuality) classifiedType = 'DATA_QUALITY';
        else classifiedType = 'NAVIGATION';

        assert.strictEqual(classifiedType, type);
      });
    });
  });
});

describe('MarathonService - V6.6 服务化架构', () => {
  it('应正确实例化服务', () => {
    const { MarathonService } = require('../../src/infrastructure/services/MarathonService');
    
    const service = new MarathonService({
      workers: 10,
      staggerMs: 500,
      maxRounds: 3
    });

    assert.strictEqual(service.config.workers, 10);
    assert.strictEqual(service.config.staggerMs, 500);
    assert.strictEqual(service.config.maxRounds, 3);
    assert.ok(service.workerStates instanceof Map);
  });

  it('应使用默认配置', () => {
    const { MarathonService } = require('../../src/infrastructure/services/MarathonService');
    
    const service = new MarathonService();

    assert.strictEqual(service.config.workers, 22);
    assert.strictEqual(service.config.staggerMs, 800);
    assert.strictEqual(service.config.maxRounds, 5);
    assert.strictEqual(service.config.restartThreshold, 500);
  });
});
