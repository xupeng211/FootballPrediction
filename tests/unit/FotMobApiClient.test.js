'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const {
    FotMobApiClient,
    buildCookieHeader,
    parseSetCookieHeader
} = require('../../src/infrastructure/network/FotMobApiClient');

describe('FotMobApiClient', () => {
    it('缺少缓存 Session 时应先探测首页 Cookie，再携带 Cookie 请求 matchDetails API', async () => {
        const persistedSessions = [];
        const requests = [];
        const client = new FotMobApiClient({
            logger: {
                info() {},
                warn() {}
            },
            sessionManager: {
                async getOrRefreshSession() {
                    return null;
                },
                async storeSession(port, session) {
                    const stored = { ...session, storedPort: port };
                    persistedSessions.push(stored);
                    return stored;
                }
            }
        });

        client._applyJitter = async () => {};
        client._requestRaw = async (url, options = {}) => {
            requests.push({
                url: url.href,
                headers: options.headers || {}
            });

            if (requests.length === 1) {
                return {
                    statusCode: 200,
                    headers: {
                        'set-cookie': [
                            'cf_clearance=token-1; Path=/; HttpOnly; Secure',
                            '_cfuvid=token-2; Path=/; Secure'
                        ]
                    },
                    body: '<html>ok</html>'
                };
            }

            return {
                statusCode: 200,
                headers: {},
                body: JSON.stringify({
                    general: { matchId: '12345' },
                    content: { stats: {}, lineup: {} },
                    header: {}
                })
            };
        };

        const payload = await client.fetchMatchDetails(
            { external_id: '12345' },
            {
                port: 10001,
                proxyServer: 'socks5://127.0.0.1:10001',
                referer: 'https://www.fotmob.com/match/12345'
            }
        );

        assert.strictEqual(requests.length, 2);
        assert.match(requests[0].url, /^https:\/\/www\.fotmob\.com\/$/);
        assert.match(requests[1].url, /api\/data\/matchDetails\?matchId=12345$/);
        assert.strictEqual(
            requests[1].headers.cookie,
            'cf_clearance=token-1; _cfuvid=token-2'
        );
        assert.strictEqual(persistedSessions.length, 1);
        assert.strictEqual(persistedSessions[0].storedPort, 10001);
        assert.strictEqual(payload.general.matchId, '12345');
    });

    it('已有有效 Cookie Session 时不应重复执行首页探测', async () => {
        const requests = [];
        const client = new FotMobApiClient({
            sessionManager: {
                async getOrRefreshSession() {
                    return {
                        cookies: [
                            { name: 'cf_clearance', value: 'cached-token' }
                        ],
                        userAgent: 'UA-CACHED'
                    };
                }
            }
        });

        client._applyJitter = async () => {};
        client._requestRaw = async (url, options = {}) => {
            requests.push({ url: url.href, headers: options.headers || {} });
            return {
                statusCode: 200,
                headers: {},
                body: JSON.stringify({
                    general: { matchId: '67890' },
                    content: { stats: {} },
                    header: {}
                })
            };
        };

        await client.fetchMatchDetails(
            { external_id: '67890' },
            {
                port: 10002,
                proxyServer: 'socks5://127.0.0.1:10002',
                referer: 'https://www.fotmob.com/match/67890'
            }
        );

        assert.strictEqual(requests.length, 1);
        assert.strictEqual(requests[0].headers.cookie, 'cf_clearance=cached-token');
        assert.strictEqual(requests[0].headers['user-agent'], 'UA-CACHED');
    });

    it('应正确解析 Set-Cookie 并生成 Cookie Header', () => {
        const cookie = parseSetCookieHeader(
            'cf_clearance=token-1; Path=/; Domain=fotmob.com; HttpOnly; Secure',
            '.fotmob.com'
        );

        assert.deepStrictEqual(cookie, {
            name: 'cf_clearance',
            value: 'token-1',
            domain: '.fotmob.com',
            path: '/',
            httpOnly: true,
            secure: true
        });
        assert.strictEqual(
            buildCookieHeader([cookie, { name: '_cfuvid', value: 'token-2' }]),
            'cf_clearance=token-1; _cfuvid=token-2'
        );
    });
});
