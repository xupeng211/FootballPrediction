'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconNetworkMonitor } = require('../../src/infrastructure/recon/services/ReconNetworkMonitor');

describe('ReconNetworkMonitor', () => {
  it('应在响应拦截中收集、解密并去重比赛数据', async () => {
    let responseHandler = null;
    const decryptCalls = [];
    const page = {
      on(eventName, handler) {
        if (eventName === 'response') {
          responseHandler = handler;
        }
      }
    };

    const decryptor = {
      getAlgorithmVersion() {
        return 'mock-v1';
      },
      async decrypt(payload) {
        decryptCalls.push(payload);
        return JSON.stringify({
          d: {
            total: 1,
            rows: [
              {
                encodeEventId: 'hash-1',
                url: '/football/england/premier-league-2025-2026/a-b-hash-1/',
                'home-name': 'A',
                'away-name': 'B',
                'date-start-timestamp': 1748185200
              }
            ]
          }
        });
      },
      async extractDecryptor() {
        throw new Error('should_not_extract');
      }
    };

    const monitor = new ReconNetworkMonitor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-network',
      decryptorFactory: () => decryptor
    });

    monitor.attach(page);

    assert.ok(responseHandler, 'attach 后应注册 response 监听器');

    const encryptedResponse = {
      url() {
        return 'https://www.oddsportal.com/ajax-user-data/t/premier-league-2025-2026/';
      },
      async text() {
        return 'encrypted-payload';
      }
    };

    await responseHandler(encryptedResponse);
    await responseHandler(encryptedResponse);

    assert.deepStrictEqual(decryptCalls, ['encrypted-payload', 'encrypted-payload']);
    assert.strictEqual(monitor.apiEndpoints.size, 1);
    assert.strictEqual(monitor.getInterceptedData().length, 1);
    assert.strictEqual(monitor.getInterceptedData()[0].hash, 'hash-1');
    assert.strictEqual(monitor.stats.requestsTotal, 2);
    assert.strictEqual(monitor.stats.requestsSuccess, 2);
    assert.strictEqual(monitor.stats.decryptedSuccess, 2);
  });

  it('脚本包装响应应直接解包，不应误触发 decryptor', async () => {
    let decryptCalls = 0;
    let extractCalls = 0;

    const monitor = new ReconNetworkMonitor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-script-wrapper',
      decryptorFactory: () => ({
        getAlgorithmVersion: () => null,
        async decrypt() {
          decryptCalls++;
          throw new Error('should_not_decrypt');
        },
        async extractDecryptor() {
          extractCalls++;
          throw new Error('should_not_extract');
        }
      })
    });

    const wrappedBody = [
      "if (typeof pageVar == 'string') { pageVar = JSON.parse(pageVar); }",
      'if (typeof pageVar != "undefined") {',
      '  pageVar = pageOutrightsVar = Object.assign(pageVar, JSON.parse("{\\"d\\":{\\"total\\":1,\\"rows\\":[{\\"encodeEventId\\":\\"wrapped-hash\\",\\"url\\":\\"/football/europe/champions-league-2025-2026/a-b-wrapped-hash/\\",\\"home-name\\":\\"A\\",\\"away-name\\":\\"B\\",\\"date-start-timestamp\\":1748185200}]}}"));',
      '}'
    ].join(' ');

    const matches = await monitor.parseApiResponse(
      wrappedBody,
      'https://www.oddsportal.com/ajax-user-data/t/champions-league-2025-2026/'
    );

    assert.strictEqual(extractCalls, 0);
    assert.strictEqual(decryptCalls, 0);
    assert.strictEqual(matches.length, 1);
    assert.strictEqual(matches[0].hash, 'wrapped-hash');
  });

  it('archive fetch 遇到 HTTP 404 时不应继续走 decryptor', async () => {
    let decryptCalls = 0;
    let extractCalls = 0;

    const monitor = new ReconNetworkMonitor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-http-404',
      page: {
        async evaluate() {
          return {
            success: false,
            status: 404,
            error: 'HTTP_404',
            text: 'URL:/ajax-sport-country-tournament-archive_/1//X/2025-2026/1/ Status: 404'
          };
        }
      },
      decryptorFactory: () => ({
        getAlgorithmVersion: () => null,
        async decrypt() {
          decryptCalls++;
          throw new Error('should_not_decrypt_http_404');
        },
        async extractDecryptor() {
          extractCalls++;
          throw new Error('should_not_extract_http_404');
        }
      })
    });

    const result = await monitor.fetchArchivePages(
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X/2025-2026/1/',
      3,
      1000
    );

    assert.strictEqual(extractCalls, 0);
    assert.strictEqual(decryptCalls, 0);
    assert.deepStrictEqual(result.matches, []);
    assert.deepStrictEqual(result.pageStats, [
      { page: 1, rows: 0, error: 'HTTP_404' }
    ]);
  });
});
