/**
 * @file HttpClient.test.js
 * @description HttpClient 防御性行为测试
 */

'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const { EventEmitter } = require('node:events');
const https = require('node:https');
const nock = require('nock');

const { HttpClient } = require('../../src/infrastructure/services/HttpClient');

describe('HttpClient', () => {
  const originalHttpsRequest = https.request;

  afterEach(() => {
    https.request = originalHttpsRequest;
    nock.cleanAll();
  });

  it('遇到 429 时应执行指数退避后重试成功', async () => {
    const sleeps = [];
    let calls = 0;

    const client = new HttpClient({
      browserProvider: {
        fetch: async () => {
          calls += 1;
          if (calls === 1) {
            return { error: 'HTTP 429', status: 429 };
          }
          return { success: true, status: 200, data: { ok: true } };
        },
        goto: async () => {},
        getCurrentUrl: async () => ''
      },
      baseBackoffMs: 10
    });

    client._sleep = async (ms) => {
      sleeps.push(ms);
    };

    const result = await client.request('https://www.fotmob.com/api/data/leagues?id=47&season=20242025');
    assert.deepStrictEqual(result, { ok: true });
    assert.strictEqual(calls, 2);
    assert.deepStrictEqual(sleeps, [20]);
  });

  it('纯净 URL 仍失败时应抛出错误', async () => {
    const client = new HttpClient({
      browserProvider: {
        fetch: async () => ({ error: 'HTTP 403', status: 403 }),
        goto: async () => {},
        getCurrentUrl: async () => ''
      },
      baseBackoffMs: 1
    });

    client._sleep = async () => {};

    await assert.rejects(
      client.request('https://www.fotmob.com/api/data/leagues?id=47&season=20242025'),
      /请求失败/
    );
  });

  it('返回 details.id 与请求 providerId 不一致时应抛出 IDENTITY_MISMATCH', async () => {
    const client = new HttpClient({
      browserProvider: {
        fetch: async () => ({
          success: true,
          status: 200,
          data: { details: { id: 110 }, fixtures: { allMatches: [] } }
        }),
        goto: async () => {},
        getCurrentUrl: async () => ''
      }
    });

    await assert.rejects(
      client.request('https://www.fotmob.com/api/data/leagues?id=86&season=20252026', {
        expectedLeagueId: 86
      }),
      /IDENTITY_MISMATCH/
    );
  });

  it('浏览器返回空数据时应触发真正的上下文重建后重试', async () => {
    const rebuilds = [];
    let calls = 0;

    const client = new HttpClient({
      browserProvider: {
        fetch: async () => {
          calls += 1;
          if (calls === 1) {
            return { success: true, status: 200, data: {} };
          }
          return { success: true, status: 200, data: { ok: true } };
        },
        goto: async () => {},
        getCurrentUrl: async () => ''
      },
      ensureBrowserHealthy: async (options = {}) => {
        rebuilds.push(options);
      },
      baseBackoffMs: 1
    });

    client._sleep = async () => {};

    const result = await client.request('https://www.fotmob.com/api/data/leagues?id=47&season=20242025');
    assert.deepStrictEqual(result, { ok: true });
    assert.strictEqual(rebuilds.length, 2);
    assert.strictEqual(rebuilds[0].reason, 'preflight');
    assert.strictEqual(rebuilds[1].forceRebuild, true);
  });

  it('已带 ccode3 的 URL 不应重复追加地区参数', () => {
    const client = new HttpClient();

    assert.strictEqual(
      client._addCcodeParam('https://www.fotmob.com/api/data/leagues?id=10004&ccode3=USA'),
      'https://www.fotmob.com/api/data/leagues?id=10004&ccode3=USA'
    );
  });

  [403, 404, 502, 503].forEach((statusCode) => {
    it(`原生 HTTP ${statusCode} 响应时应抛出带上下文的错误`, async () => {
      const client = new HttpClient({
        useStealthMode: false
      });

      const scope = nock('https://api.fotmob.test')
        .get('/league')
        .query({ season: '20252026', ccode3: 'USA' })
        .reply(statusCode, { error: `HTTP ${statusCode}` });

      await assert.rejects(
        client.request('https://api.fotmob.test/league?season=20252026'),
        (error) => {
          assert.strictEqual(error.name, 'HttpClientError');
          assert.strictEqual(error.mode, 'raw');
          assert.strictEqual(error.statusCode, statusCode);
          assert.strictEqual(error.url, 'https://api.fotmob.test/league?season=20252026&ccode3=USA');
          assert.match(error.message, new RegExp(`HTTP ${statusCode}`));
          return true;
        }
      );

      assert.ok(scope.isDone());
    });
  });

  it('原生 HTTP 返回畸形 JSON 时应抛出解析错误', async () => {
    const client = new HttpClient({
      useStealthMode: false
    });

    const scope = nock('https://api.fotmob.test')
      .get('/league')
      .query({ season: '20252026', ccode3: 'USA' })
      .reply(200, '{bad-json');

    await assert.rejects(
      client.request('https://api.fotmob.test/league?season=20252026'),
      (error) => {
        assert.strictEqual(error.mode, 'raw');
        assert.strictEqual(error.statusCode, undefined);
        assert.match(error.message, /JSON 解析失败/);
        assert.strictEqual(error.url, 'https://api.fotmob.test/league?season=20252026&ccode3=USA');
        return true;
      }
    );

    assert.ok(scope.isDone());
  });

  it('原生 HTTP timeout 时应抛出超时错误并保留上下文', async () => {
    https.request = (_options, _handler) => {
      const req = new EventEmitter();
      req.destroy = () => {};
      req.end = () => {
        process.nextTick(() => {
          req.emit('timeout');
        });
      };
      return req;
    };

    const client = new HttpClient({
      useStealthMode: false
    });

    await assert.rejects(
      client.request('https://api.fotmob.test/league?season=20252026'),
      (error) => {
        assert.strictEqual(error.name, 'HttpClientError');
        assert.strictEqual(error.mode, 'raw');
        assert.strictEqual(error.retryCount, 1);
        assert.match(error.message, /请求超时/);
        assert.strictEqual(error.url, 'https://api.fotmob.test/league?season=20252026&ccode3=USA');
        return true;
      }
    );
  });

  it('浏览器 fetch timeout 时应退避重试并强制重建上下文', async () => {
    const sleeps = [];
    const rebuilds = [];
    let calls = 0;

    const client = new HttpClient({
      browserProvider: {
        fetch: async () => {
          calls += 1;
          if (calls < 3) {
            throw new Error('browser fetch timeout');
          }
          return { success: true, status: 200, data: { ok: true } };
        },
        goto: async () => {
          throw new Error('timeout retry should rebuild instead of goto');
        },
        getCurrentUrl: async () => ''
      },
      ensureBrowserHealthy: async (options = {}) => {
        rebuilds.push(options);
      },
      baseBackoffMs: 10
    });

    client._sleep = async (ms) => {
      sleeps.push(ms);
    };

    const result = await client.request('https://www.fotmob.com/api/data/leagues?season=20252026');

    assert.deepStrictEqual(result, { ok: true });
    assert.strictEqual(calls, 3);
    assert.deepStrictEqual(sleeps, [10, 20]);
    assert.strictEqual(rebuilds.length, 3);
    assert.strictEqual(rebuilds[0].reason, 'preflight');
    assert.strictEqual(rebuilds[1].forceRebuild, true);
    assert.strictEqual(rebuilds[2].forceRebuild, true);
  });

  it('内部 helper 应覆盖 redirect、fallback leagueId、retryable 与 sleep 分支', async () => {
    const errors = [];
    const warnings = [];
    https.request = (_options, _handler) => {
      const req = new EventEmitter();
      req.destroy = () => {};
      req.end = () => {
        process.nextTick(() => {
          req.emit('error', new Error('socket hang up'));
        });
      };
      return req;
    };

    const client = new HttpClient({
      useStealthMode: false,
      logger: {
        info() {},
        warn(message) {
          warnings.push(message);
        },
        error(message) {
          errors.push(message);
        }
      },
      browserProvider: {
        async getCurrentUrl() {
          return 'https://www.fotmob.com/leagues/99/overview';
        }
      },
      baseBackoffMs: 10
    });

    await client._detectRedirect('https://www.fotmob.com/api/data/leagues?id=47&season=20252026');
    client.browserProvider.getCurrentUrl = async () => {
      throw new Error('redirect probe failed');
    };
    await assert.doesNotReject(async () => {
      await client._detectRedirect('https://www.fotmob.com/api/data/leagues?id=47&season=20252026');
    });

    assert.strictEqual(client._extractLeagueId({ id: '55' }), 55);
    assert.strictEqual(client._extractLeagueId({ leagueId: '56' }), 56);
    assert.strictEqual(client._extractLeagueId({ general: { leagueId: '57' } }), 57);
    assert.strictEqual(client._extractLeagueId({ details: { id: 'oops' } }), null);
    assert.doesNotThrow(() => client._assertLeagueIdentity({ ok: true }, null, 'https://api.test'));
    assert.doesNotThrow(() => client._assertLeagueIdentity({ details: { id: null } }, 47, 'https://api.test'));
    assert.strictEqual(client._shouldRebuildBrowserContext(null), false);
    assert.strictEqual(client._shouldRebuildBrowserContext({ code: 'IDENTITY_MISMATCH', message: 'mismatch' }), false);
    assert.strictEqual(client._shouldRebuildBrowserContext({ message: 'Target page closed unexpectedly' }), true);
    assert.strictEqual(client._isRetryableStatus(503), true);
    assert.strictEqual(client._isRetryableStatus(404), false);
    assert.strictEqual(client._computeBackoffMs(2, 429), 40);
    assert.strictEqual(client._getCleanUrl('https://api.test/league?season=20252026'), 'https://api.test/league?season=20252026');
    await client._sleep(1);

    await assert.rejects(
      client._rawRequest('https://api.fotmob.test/league?season=20252026'),
      /请求失败: socket hang up/
    );
    assert.ok(errors.some((message) => message.includes('ID 偏移重定向: 47 -> 99')));
    assert.deepStrictEqual(warnings, []);
  });
});
