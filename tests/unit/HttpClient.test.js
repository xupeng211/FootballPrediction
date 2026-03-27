/**
 * @file HttpClient.test.js
 * @description HttpClient 防御性行为测试
 */

'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { HttpClient } = require('../../src/infrastructure/services/HttpClient');

describe('HttpClient', () => {
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
});
