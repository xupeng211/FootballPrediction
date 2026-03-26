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
});
