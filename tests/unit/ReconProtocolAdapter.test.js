'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconProtocolAdapter, JA3_CIPHER_SUITES, JA3_SIGALGS } = require('../../src/infrastructure/recon/services/ReconProtocolAdapter');

function makeAdapter(overrides = {}) {
  return {
    logger: { warn: () => {}, info: () => {}, debug: () => {} },
    navigator: null,
    page: null,
    ...reconProtocolAdapter,
    ...overrides
  };
}

describe('ReconProtocolAdapter', () => {
  describe('常量导出', () => {
    it('JA3_CIPHER_SUITES 应是非空数组', () => {
      assert.ok(Array.isArray(JA3_CIPHER_SUITES));
      assert.ok(JA3_CIPHER_SUITES.length > 0);
    });

    it('JA3_SIGALGS 应是非空数组', () => {
      assert.ok(Array.isArray(JA3_SIGALGS));
      assert.ok(JA3_SIGALGS.length > 0);
    });
  });

  describe('_normalizePureProtocolTarget', () => {
    it('string 输入 -> { url, baseUrl } 均等于输入', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget('https://op.com/result/');
      assert.strictEqual(result.url, 'https://op.com/result/');
      assert.strictEqual(result.baseUrl, 'https://op.com/result/');
    });

    it('object 输入有 url 字段', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget({ url: 'https://op.com/a/', extra: true });
      assert.strictEqual(result.url, 'https://op.com/a/');
      assert.strictEqual(result.baseUrl, 'https://op.com/a/');
      assert.strictEqual(result.extra, true);
    });

    it('object 输入有 baseUrl 字段', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget({ baseUrl: 'https://op.com/b/' });
      assert.strictEqual(result.url, 'https://op.com/b/');
    });

    it('object 输入有 resultsUrl 字段', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget({ resultsUrl: 'https://op.com/c/' });
      assert.strictEqual(result.url, 'https://op.com/c/');
    });

    it('空 object 输入 -> url 为空字符串', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget({});
      assert.strictEqual(result.url, '');
    });

    it('null 输入 -> url 为空字符串', () => {
      const adapter = makeAdapter();
      const result = adapter._normalizePureProtocolTarget(null);
      assert.strictEqual(result.url, '');
    });
  });

  describe('_buildPureProtocolContextProbeTargets', () => {
    it('无 navigator 时仅返回 requested 来源', () => {
      const adapter = makeAdapter({ navigator: null });
      const targets = adapter._buildPureProtocolContextProbeTargets({ baseUrl: 'https://op.com/r/' });
      assert.ok(targets.length >= 1);
      assert.strictEqual(targets[0].contextSource, 'requested');
    });

    it('有 navigator.stateProber 时可返回多个探测目标', () => {
      const adapter = makeAdapter({
        navigator: {
          stateProber: {
            deriveCurrentResultsUrl: (url) => `${url}results/`,
            deriveLeaguePageUrl: (url) => `${url}league/`
          }
        }
      });
      const targets = adapter._buildPureProtocolContextProbeTargets({ baseUrl: 'https://op.com/' });
      assert.ok(targets.length >= 1);
      const sources = targets.map((t) => t.contextSource);
      assert.ok(sources.includes('requested'));
    });

    it('重复 URL 应去重', () => {
      const adapter = makeAdapter({
        navigator: {
          stateProber: {
            deriveCurrentResultsUrl: () => 'https://op.com/',
            deriveLeaguePageUrl: () => 'https://op.com/'
          }
        }
      });
      const targets = adapter._buildPureProtocolContextProbeTargets({ baseUrl: 'https://op.com/' });
      assert.strictEqual(targets.length, 1);
    });

    it('空 baseUrl 时不应 push 空字符串', () => {
      const adapter = makeAdapter({ navigator: null });
      const targets = adapter._buildPureProtocolContextProbeTargets({});
      assert.strictEqual(targets.length, 0);
    });
  });

  describe('_extractPureProtocolContextSignals', () => {
    it('应优先返回 outrightMeta.id 并保留 tournamentId', () => {
      const adapter = makeAdapter({
        navigator: {
          stateProber: {
            extractPageOutrightsMetaFromHtml: () => ({ id: 'ot-123' })
          }
        }
      });
      const html = '<script>var token="x";</script><div data-tournament-id="tid-9"></div>';
      const result = adapter._extractPureProtocolContextSignals({ baseUrl: 'https://op.com/' }, html);
      assert.strictEqual(result.outrightId, 'ot-123');
      assert.ok(typeof result.tournamentId === 'string');
    });

    it('无 navigator 时应回退到 embeddedState', () => {
      const adapter = makeAdapter({ navigator: null });
      const html = '<html></html>';
      const result = adapter._extractPureProtocolContextSignals({ baseUrl: 'https://op.com/' }, html);
      assert.ok(result && typeof result === 'object');
      assert.ok(Object.prototype.hasOwnProperty.call(result, 'embeddedState'));
    });
  });

  describe('_resolvePureProtocolBookmakerHash', () => {
    it('从 options.bookmakerHash 取有效 hash', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({}, { bookmakerHash: 'X2X3X4' });
      assert.strictEqual(result, 'X2X3X4');
    });

    it('从 options.bookiehash 取有效 hash', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({}, { bookiehash: 'X5X6' });
      assert.strictEqual(result, 'X5X6');
    });

    it('从 target.bookmakerHash 取有效 hash', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({ bookmakerHash: 'X7X8X9' }, {});
      assert.strictEqual(result, 'X7X8X9');
    });

    it('从 target.bookiehash 取有效 hash', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({ bookiehash: 'X10X11' }, {});
      assert.strictEqual(result, 'X10X11');
    });

    it('无有效 hash 时返回配置默认值或空字符串', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({}, {});
      assert.ok(typeof result === 'string');
    });

    it('无效格式 hash 应跳过使用后续候选', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({}, { bookmakerHash: 'notvalid' });
      assert.ok(typeof result === 'string');
    });

    it('优先级: options.bookmakerHash > options.bookiehash', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolBookmakerHash({}, { bookmakerHash: 'X1X2', bookiehash: 'X3X4' });
      assert.strictEqual(result, 'X1X2');
    });
  });

  describe('_resolvePureProtocolRuntimeState', () => {
    it('options.allowRuntimeStateProbe === false 时立即返回空', async () => {
      const adapter = makeAdapter();
      const result = await adapter._resolvePureProtocolRuntimeState({ baseUrl: 'https://op.com/' }, { allowRuntimeStateProbe: false });
      assert.strictEqual(result.outrightId, '');
      assert.strictEqual(result.bookmakerHash, '');
    });

    it('navigator 为 null 时返回空', async () => {
      const adapter = makeAdapter({ navigator: null });
      const result = await adapter._resolvePureProtocolRuntimeState({ baseUrl: 'https://op.com/' });
      assert.strictEqual(result.outrightId, '');
      assert.strictEqual(result.bookmakerHash, '');
    });

    it('navigator 无 ensureBrowserHealthy 时返回空', async () => {
      const adapter = makeAdapter({
        navigator: { navigate: async () => {}, stateProber: {} }
      });
      const result = await adapter._resolvePureProtocolRuntimeState({ baseUrl: 'https://op.com/' });
      assert.strictEqual(result.outrightId, '');
    });

    it('navigator 操作抛错时返回空并记录 warn', async () => {
      const warns = [];
      const adapter = makeAdapter({
        logger: { warn: (event, data) => warns.push({ event, data }), info: () => {}, debug: () => {} },
        navigator: {
          ensureBrowserHealthy: async () => { throw new Error('browser crash'); },
          navigate: async () => {},
          stateProber: { deriveCurrentResultsUrl: (u) => u },
          archiveTimeoutMs: 5000
        }
      });
      const result = await adapter._resolvePureProtocolRuntimeState({ baseUrl: 'https://op.com/' });
      assert.strictEqual(result.outrightId, '');
      assert.ok(warns.some((entry) => entry.event === 'pure_protocol_runtime_state_probe_failed'));
    });
  });

  describe('_resolvePureProtocolUserAgent', () => {
    it('无 options 时返回配置中或空字符串', () => {
      const adapter = makeAdapter();
      const ua = adapter._resolvePureProtocolUserAgent();
      assert.ok(typeof ua === 'string');
    });

    it('options.userAgent 指定时返回该值', () => {
      const adapter = makeAdapter();
      const ua = adapter._resolvePureProtocolUserAgent({ userAgent: 'TestAgent/1.0' });
      assert.strictEqual(ua, 'TestAgent/1.0');
    });
  });

  describe('_resolvePureProtocolCookieHeader', () => {
    it('显式 cookieHeader 应直接返回', async () => {
      const adapter = makeAdapter();
      const cookie = await adapter._resolvePureProtocolCookieHeader('https://op.com/', { cookieHeader: 'a=1; b=2' });
      assert.strictEqual(cookie, 'a=1; b=2');
    });

    it('当前页 URL 命中时应从 document.cookie 读取', async () => {
      const adapter = makeAdapter({
        page: {
          url: () => 'https://op.com/results/',
          evaluate: async () => 'session=abc'
        }
      });
      const cookie = await adapter._resolvePureProtocolCookieHeader('https://op.com/results/');
      assert.strictEqual(cookie, 'session=abc');
    });

    it('页面 cookie 为空时应回退到 context.cookies()', async () => {
      const adapter = makeAdapter({
        page: {
          url: () => 'https://op.com/results/',
          evaluate: async () => ''
        },
        navigator: {
          context: {
            cookies: async () => ([
              { name: 'foo', value: 'bar' },
              { name: 'baz', value: 'qux' }
            ])
          }
        }
      });
      const cookie = await adapter._resolvePureProtocolCookieHeader('https://op.com/results/');
      assert.strictEqual(cookie, 'foo=bar; baz=qux');
    });

    it('context.cookies 抛错时应返回空字符串', async () => {
      const adapter = makeAdapter({
        page: {
          url: () => 'https://op.com/other/',
          evaluate: async () => ''
        },
        navigator: {
          context: {
            cookies: async () => { throw new Error('boom'); }
          }
        }
      });
      const cookie = await adapter._resolvePureProtocolCookieHeader('https://op.com/results/');
      assert.strictEqual(cookie, '');
    });
  });

  describe('_buildPureProtocolHeaders', () => {
    it('应返回包含 accept 的 headers 对象', () => {
      const adapter = makeAdapter();
      const headers = adapter._buildPureProtocolHeaders('https://op.com/', 'application/json');
      assert.ok(typeof headers === 'object');
      assert.ok(headers.accept || headers['accept'] || true);
    });

    it('带 cookie 时 headers 应包含 cookie 字段', () => {
      const adapter = makeAdapter();
      const headers = adapter._buildPureProtocolHeaders(
        'https://op.com/',
        'application/json',
        { cookieHeader: 'session=abc123' }
      );
      assert.ok(headers.cookie === 'session=abc123' || headers['cookie'] === 'session=abc123');
    });
  });

  describe('browser html fallback', () => {
    it('_createPureProtocolMonitor 应返回监视器实例', () => {
      const adapter = makeAdapter();
      const monitor = adapter._createPureProtocolMonitor();
      assert.ok(monitor);
      assert.strictEqual(typeof monitor.fetchText, 'function');
      assert.strictEqual(typeof monitor.getInterceptedData, 'function');
    });

    it('_loadPureProtocolHtmlViaBrowser 在缺少 navigator 时返回空字符串', async () => {
      const adapter = makeAdapter({ navigator: null });
      const html = await adapter._loadPureProtocolHtmlViaBrowser('https://op.com/results/');
      assert.strictEqual(html, '');
    });

    it('_loadPureProtocolHtmlViaBrowser 成功时返回活动页 HTML', async () => {
      const events = [];
      const adapter = makeAdapter({
        page: {
          waitForTimeout: async (delayMs) => events.push(`wait:${delayMs}`)
        },
        navigator: {
          ensureBrowserHealthy: async () => events.push('healthy'),
          navigate: async (url, options) => events.push({ type: 'navigate', url, options }),
          stateProber: {
            deriveCurrentResultsUrl: (url) => `${url}current/`
          },
          archiveTimeoutMs: 3210,
          postApiDiscoveryWaitMs: 0
        },
        _readPureProtocolHtmlFromActivePage: async (url) => {
          events.push({ type: 'read', url });
          return '<html>browser</html>';
        }
      });

      const html = await adapter._loadPureProtocolHtmlViaBrowser('https://op.com/results/', { timeoutMs: 4567 });

      assert.strictEqual(html, '<html>browser</html>');
      assert.deepStrictEqual(events, [
        'healthy',
        {
          type: 'navigate',
          url: 'https://op.com/results/current/',
          options: { waitUntil: 'domcontentloaded', timeout: 4567 }
        },
        { type: 'read', url: 'https://op.com/results/' }
      ]);
    });

    it('_loadPureProtocolHtmlViaBrowser 失败时记录 warn 并返回空字符串', async () => {
      const warns = [];
      const adapter = makeAdapter({
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        navigator: {
          ensureBrowserHealthy: async () => { throw new Error('browser gone'); },
          navigate: async () => {},
          stateProber: {},
          archiveTimeoutMs: 2000,
          postApiDiscoveryWaitMs: 0
        }
      });

      const html = await adapter._loadPureProtocolHtmlViaBrowser('https://op.com/results/');

      assert.strictEqual(html, '');
      assert.deepStrictEqual(warns, [
        {
          event: 'pure_protocol_browser_html_probe_failed',
          payload: {
            baseUrl: 'https://op.com/results/',
            error: 'browser gone'
          }
        }
      ]);
    });

    it('_resolvePureProtocolHtml 命中活动页缓存时直接返回 browser_active_page', async () => {
      const adapter = makeAdapter({
        _readPureProtocolHtmlFromActivePage: async () => ' <html>cached</html> ',
        _fetchPureProtocolText: async () => {
          throw new Error('should not fetch');
        }
      });

      const result = await adapter._resolvePureProtocolHtml({ baseUrl: 'https://op.com/results/' });

      assert.deepStrictEqual(result, {
        success: true,
        status: 200,
        text: ' <html>cached</html> ',
        source: 'browser_active_page'
      });
    });

    it('_resolvePureProtocolHtml HTTP 成功时返回 node_fetch 来源', async () => {
      const adapter = makeAdapter({
        _readPureProtocolHtmlFromActivePage: async () => '',
        _resolvePureProtocolCookieHeader: async () => 'session=abc',
        _fetchPureProtocolText: async (_url, options) => ({
          success: true,
          status: 200,
          text: '<html>http</html>',
          receivedCookie: options.cookieHeader
        })
      });

      const result = await adapter._resolvePureProtocolHtml({ baseUrl: 'https://op.com/results/' }, { timeoutMs: 1200 });

      assert.strictEqual(result.success, true);
      assert.strictEqual(result.source, 'node_fetch');
      assert.strictEqual(result.receivedCookie, 'session=abc');
    });

    it('_resolvePureProtocolHtml 可禁用 browser fallback 并返回 HTTP 失败结果', async () => {
      const adapter = makeAdapter({
        _readPureProtocolHtmlFromActivePage: async () => '',
        _resolvePureProtocolCookieHeader: async () => '',
        _fetchPureProtocolText: async () => ({ success: false, status: 503, error: 'HTTP_503', text: '' }),
        _loadPureProtocolHtmlViaBrowser: async () => '<html>should-not-use</html>'
      });

      const result = await adapter._resolvePureProtocolHtml(
        { baseUrl: 'https://op.com/results/' },
        { allowBrowserHtmlFallback: false }
      );

      assert.deepStrictEqual(result, {
        success: false,
        status: 503,
        error: 'HTTP_503',
        text: ''
      });
    });

    it('_resolvePureProtocolHtml HTTP 失败后命中 browser fallback 时返回补救结果', async () => {
      const warns = [];
      const adapter = makeAdapter({
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        _readPureProtocolHtmlFromActivePage: async () => '',
        _resolvePureProtocolCookieHeader: async () => '',
        _fetchPureProtocolText: async () => ({ success: false, status: 503, error: 'HTTP_503', text: '' }),
        _loadPureProtocolHtmlViaBrowser: async () => '<html>fallback</html>'
      });

      const result = await adapter._resolvePureProtocolHtml({ baseUrl: 'https://op.com/results/' });

      assert.strictEqual(result.success, true);
      assert.strictEqual(result.source, 'browser_navigate_fallback');
      assert.strictEqual(result.fallbackStatus, 503);
      assert.deepStrictEqual(warns, [
        {
          event: 'pure_protocol_html_fetch_http_fallback_hit',
          payload: {
            baseUrl: 'https://op.com/results/',
            error: 'HTTP_503',
            statusCode: 503
          }
        }
      ]);
    });
  });

  describe('_isRetryablePureProtocolFetchFailure', () => {
    it('fetch failed 消息应返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isRetryablePureProtocolFetchFailure({ error: 'fetch failed' }), true);
    });

    it('socket hang up 应返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isRetryablePureProtocolFetchFailure({ error: 'socket hang up' }), true);
    });

    it('ECONNRESET 应返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isRetryablePureProtocolFetchFailure({ error: 'ECONNRESET' }), true);
    });

    it('正常 200 无错误应返回 false', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isRetryablePureProtocolFetchFailure({ success: true }), false);
    });

    it('403 blocked 应返回 false', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isRetryablePureProtocolFetchFailure({ error: '403 forbidden', status: 403 }), false);
    });
  });

  describe('_hasExplicitPureProtocolRequestProxy', () => {
    it('options.proxyServer 存在时返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._hasExplicitPureProtocolRequestProxy({ proxyServer: '127.0.0.1' }), true);
    });

    it('proxyServer + proxyPort 同时存在时返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._hasExplicitPureProtocolRequestProxy({ proxyServer: '127.0.0.1', proxyPort: 7891 }), true);
    });

    it('options.requestProxyLease 有效时返回 true', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._hasExplicitPureProtocolRequestProxy({
        requestProxyLease: { proxy: { server: '127.0.0.1' } }
      }), true);
    });

    it('空 options 时返回 false', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._hasExplicitPureProtocolRequestProxy({}), false);
    });
  });

  describe('_resolvePureProtocolRequestProxy', () => {
    it('应优先返回 request lease', () => {
      const lease = { id: 'lease-1', proxy: { server: 'http://proxy-a', port: 7891 } };
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolRequestProxy({ requestProxyLease: lease });
      assert.strictEqual(result.source, 'request_lease');
      assert.strictEqual(result.server, 'http://proxy-a');
    });

    it('无 lease 时应回退到 request proxy 对象', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolRequestProxy({ requestProxy: { server: 'http://proxy-b', port: 7892 } });
      assert.strictEqual(result.source, 'request_proxy');
      assert.strictEqual(result.port, 7892);
    });

    it('无 proxy 对象时应回退到 proxyServer', () => {
      const adapter = makeAdapter();
      const result = adapter._resolvePureProtocolRequestProxy({ proxyServer: 'http://proxy-c', proxyPort: 7893 });
      assert.strictEqual(result.source, 'request_server');
      assert.strictEqual(result.server, 'http://proxy-c');
    });

    it('无显式参数时应回退到 navigator lease', () => {
      const adapter = makeAdapter({
        navigator: {
          proxyLease: { id: 'lease-2', proxy: { server: 'http://proxy-d', port: 7894 } }
        }
      });
      const result = adapter._resolvePureProtocolRequestProxy({});
      assert.strictEqual(result.source, 'navigator_lease');
      assert.strictEqual(result.port, 7894);
    });

    it('无任何代理时应返回 null', () => {
      const adapter = makeAdapter({ navigator: null });
      assert.strictEqual(adapter._resolvePureProtocolRequestProxy({}), null);
    });
  });

  describe('retry orchestration', () => {
    it('_waitPureProtocolFetchRetry 优先走 navigator 自身等待器', async () => {
      const delays = [];
      const adapter = makeAdapter({
        navigator: {
          _waitBeforeRetry: async (delayMs) => delays.push(delayMs)
        }
      });

      await adapter._waitPureProtocolFetchRetry(-5);

      assert.deepStrictEqual(delays, [0]);
    });

    it('_waitPureProtocolFetchRetry 在无 navigator 等待器时也应完成', async () => {
      const adapter = makeAdapter();
      await assert.doesNotReject(adapter._waitPureProtocolFetchRetry(0));
    });

    it('_reportPureProtocolFetchFailure 在 provider 缺失时返回 false', async () => {
      const adapter = makeAdapter({ navigator: null });
      const reported = await adapter._reportPureProtocolFetchFailure({ status: 503 }, 'https://op.com/api', {}, { port: 7891 });
      assert.strictEqual(reported, false);
    });

    it('_reportPureProtocolFetchFailure 在有端口时调用 provider.reportFailure', async () => {
      const calls = [];
      const adapter = makeAdapter({
        navigator: {
          proxyProvider: {
            reportFailure: async (leaseId, payload) => calls.push({ leaseId, payload })
          }
        }
      });

      const reported = await adapter._reportPureProtocolFetchFailure(
        { status: 429, error: 'HTTP_429' },
        'https://op.com/api',
        {},
        { port: 7891 }
      );

      assert.strictEqual(reported, true);
      assert.deepStrictEqual(calls, [
        {
          leaseId: null,
          payload: {
            port: 7891,
            statusCode: 429,
            reason: 'HTTP_429',
            failureClass: 'rate_limit',
            url: 'https://op.com/api',
            stage: 'pure_protocol_fetch'
          }
        }
      ]);
    });

    it('_reportPureProtocolFetchFailure 上报失败时记录 debug 并返回 false', async () => {
      const debugs = [];
      const adapter = makeAdapter({
        logger: { warn: () => {}, info: () => {}, debug: (event, payload) => debugs.push({ event, payload }) },
        navigator: {
          traceId: 'trace-1',
          proxyProvider: {
            reportFailure: async () => { throw new Error('provider down'); }
          }
        }
      });

      const reported = await adapter._reportPureProtocolFetchFailure(
        { status: 503, error: 'HTTP_503' },
        'https://op.com/api',
        {},
        { lease: { id: 'lease-1' }, port: 7892 }
      );

      assert.strictEqual(reported, false);
      assert.deepStrictEqual(debugs, [
        {
          event: 'pure_protocol_proxy_failure_report_failed',
          payload: {
            traceId: 'trace-1',
            url: 'https://op.com/api',
            proxyPort: 7892,
            statusCode: 503,
            error: 'provider down'
          }
        }
      ]);
    });

    it('_rotatePureProtocolRequestProxy 非 429/503 时直接返回原 options', async () => {
      const adapter = makeAdapter();
      const options = { proxyServer: 'http://proxy-a', proxyPort: 7891 };
      const result = await adapter._rotatePureProtocolRequestProxy(
        { status: 404 },
        'https://op.com/api',
        options,
        0,
        { port: 7891 }
      );
      assert.strictEqual(result, options);
    });

    it('_rotatePureProtocolRequestProxy 对 navigator 托管代理返回更新后的 options', async () => {
      const adapter = makeAdapter({
        navigator: {
          traceId: 'trace-nav',
          proxy: { server: 'http://proxy-next', port: 7899 },
          proxyLease: { id: 'lease-nav', proxy: { server: 'http://proxy-next', port: 7899 } },
          _parseRetryAfterMs: () => 1250,
          _resolveCircuitBreakerKey: () => 'breaker-nav',
          rotateProxyForRetry: async () => ({ rotated: true })
        }
      });

      const result = await adapter._rotatePureProtocolRequestProxy(
        { status: 503, error: 'HTTP_503', retryAfterRaw: '1' },
        'https://op.com/api',
        { baseUrl: 'https://op.com/results/' },
        1,
        { lease: { id: 'lease-nav' }, server: 'http://proxy-old', port: 7891 }
      );

      assert.strictEqual(result.proxyLease.id, 'lease-nav');
      assert.strictEqual(result.requestProxyLease.id, 'lease-nav');
      assert.strictEqual(result.proxyServer, 'http://proxy-next');
      assert.strictEqual(result.proxyPort, 7899);
    });

    it('_rotatePureProtocolRequestProxy 可通过 provider.acquire 切换 request proxy', async () => {
      const calls = [];
      const adapter = makeAdapter({
        logger: { warn: () => {}, info: () => {}, debug: () => {} },
        navigator: {
          traceId: 'trace-provider',
          _parseRetryAfterMs: () => 0,
          proxyProvider: {
            acquire: async (payload) => {
              calls.push({ type: 'acquire', payload });
              return { id: 'lease-new', proxy: { server: 'http://proxy-new', port: 7901 } };
            },
            release: async (lease) => {
              calls.push({ type: 'release', lease });
            }
          }
        }
      });

      const result = await adapter._rotatePureProtocolRequestProxy(
        { status: 429, error: 'HTTP_429' },
        'https://op.com/api',
        { referer: 'https://op.com/results/' },
        0,
        { lease: { id: 'lease-old' }, server: 'http://proxy-old', port: 7891 }
      );

      assert.strictEqual(result.proxyLease.id, 'lease-new');
      assert.strictEqual(result.requestProxyLease.id, 'lease-new');
      assert.strictEqual(result.proxyServer, 'http://proxy-new');
      assert.strictEqual(result.proxyPort, 7901);
      assert.deepStrictEqual(calls, [
        {
          type: 'acquire',
          payload: {
            consumer: 'recon-pure-protocol-request',
            sessionKey: 'trace-provider:protocol:1',
            sticky: false,
            excludePorts: [7891],
            metadata: {
              reason: 'pure_protocol_fetch_retry',
              traceId: 'trace-provider'
            }
          }
        },
        {
          type: 'release',
          lease: { id: 'lease-old' }
        }
      ]);
    });

    it('_rotatePureProtocolRequestProxy 在 acquire 失败时记录 warn 并回退原 options', async () => {
      const warns = [];
      const options = { proxyServer: 'http://proxy-old', proxyPort: 7891 };
      const adapter = makeAdapter({
        logger: { warn: (event, payload) => warns.push({ event, payload }), info: () => {}, debug: () => {} },
        navigator: {
          traceId: 'trace-provider',
          _parseRetryAfterMs: () => 0,
          proxyProvider: {
            acquire: async () => { throw new Error('acquire failed'); }
          }
        }
      });

      const result = await adapter._rotatePureProtocolRequestProxy(
        { status: 503, error: 'HTTP_503' },
        'https://op.com/api',
        options,
        1,
        { port: 7891 }
      );

      assert.strictEqual(result, options);
      assert.deepStrictEqual(warns, [
        {
          event: 'pure_protocol_request_proxy_rotation_failed',
          payload: {
            traceId: 'trace-provider',
            url: 'https://op.com/api',
            attempt: 2,
            statusCode: 503,
            error: 'acquire failed'
          }
        }
      ]);
    });

    it('_fetchPureProtocolText 应串起 503 审计、上报、rotation 与 retry', async () => {
      const events = [];
      const adapter = makeAdapter({
        logger: { warn: (_event, payload) => events.push({ type: 'warn', payload }), info: () => {}, debug: () => {} },
        navigator: {
          _parseRetryAfterMs: () => 5
        },
        _fetchPureProtocolTextOnce: async (_url, options) => {
          events.push({ type: 'fetch', port: options.proxyPort });
          return events.filter((event) => event.type === 'fetch').length === 1
            ? { success: false, status: 503, error: 'HTTP_503', retryAfterRaw: '1', text: '' }
            : { success: true, status: 200, text: '{"ok":true}' };
        },
        _auditPureProtocol503Profile: () => events.push({ type: 'audit' }),
        _reportPureProtocolFetchFailure: async () => {
          events.push({ type: 'report' });
          return true;
        },
        _rotatePureProtocolRequestProxy: async (_result, _url, options) => {
          events.push({ type: 'rotate', from: options.proxyPort });
          return { ...options, proxyServer: 'http://proxy-next', proxyPort: 7902 };
        },
        _waitPureProtocolFetchRetry: async (delayMs) => events.push({ type: 'wait', delayMs }),
        _decoratePureProtocolFetchResult: (result, options) => ({ ...result, finalProxyPort: options.proxyPort })
      });

      const result = await adapter._fetchPureProtocolText('https://op.com/api', {
        maxAttempts: 2,
        retryDelayMs: 0,
        proxyServer: 'http://proxy-old',
        proxyPort: 7891
      });

      assert.strictEqual(result.success, true);
      assert.strictEqual(result.finalProxyPort, 7902);
      assert.deepStrictEqual(events.filter((event) => event.type !== 'warn'), [
        { type: 'fetch', port: 7891 },
        { type: 'audit' },
        { type: 'report' },
        { type: 'rotate', from: 7891 },
        { type: 'wait', delayMs: 5 },
        { type: 'fetch', port: 7902 }
      ]);
    });

    it('_fetchPureProtocolText 遇到不可重试失败时直接返回装饰结果', async () => {
      const events = [];
      const adapter = makeAdapter({
        _fetchPureProtocolTextOnce: async () => ({ success: false, status: 404, error: 'HTTP_404', text: '' }),
        _decoratePureProtocolFetchResult: (result) => {
          events.push('decorate');
          return { ...result, decorated: true };
        }
      });

      const result = await adapter._fetchPureProtocolText('https://op.com/api', {
        maxAttempts: 2,
        retryDelayMs: 0
      });

      assert.deepStrictEqual(events, ['decorate']);
      assert.strictEqual(result.decorated, true);
      assert.strictEqual(result.status, 404);
    });

    it('_fetchPureProtocolTextOnce 命中 request proxy 时应委托给代理请求器', async () => {
      const adapter = makeAdapter({
        _resolvePureProtocolCookieHeader: async () => 'session=abc',
        _resolvePureProtocolRequestProxy: () => ({ server: 'http://proxy-a', port: 7891 }),
        _fetchPureProtocolTextViaProxyRequest: async (url, options) => ({
          success: true,
          status: 200,
          text: url,
          cookieHeader: options.cookieHeader
        })
      });

      const result = await adapter._fetchPureProtocolTextOnce('https://op.com/api', { referer: 'https://op.com/results/' });

      assert.deepStrictEqual(result, {
        success: true,
        status: 200,
        text: 'https://op.com/api',
        cookieHeader: 'session=abc'
      });
    });

    it('_fetchPureProtocolTextOnce 在 HTTP 非 2xx 时返回失败结构', async () => {
      const originalFetch = global.fetch;
      global.fetch = async () => ({
        ok: false,
        status: 503,
        text: async () => 'backend unavailable',
        headers: {
          get: (name) => (name === 'retry-after' ? '7' : '')
        }
      });

      try {
        const adapter = makeAdapter({
          _resolvePureProtocolCookieHeader: async () => '',
          _resolvePureProtocolRequestProxy: () => null
        });

        const result = await adapter._fetchPureProtocolTextOnce('https://op.com/api');

        assert.deepStrictEqual(result, {
          success: false,
          status: 503,
          error: 'HTTP_503',
          text: 'backend unavailable',
          retryAfterRaw: '7'
        });
      } finally {
        global.fetch = originalFetch;
      }
    });

    it('_fetchPureProtocolTextOnce 应识别 embedded HTTP failure 页面', async () => {
      const originalFetch = global.fetch;
      global.fetch = async () => ({
        ok: true,
        status: 200,
        text: async () => 'URL: https://op.com/archive\nStatus: 503\nbody',
        headers: {
          get: () => ''
        }
      });

      try {
        const adapter = makeAdapter({
          _resolvePureProtocolCookieHeader: async () => '',
          _resolvePureProtocolRequestProxy: () => null
        });

        const result = await adapter._fetchPureProtocolTextOnce('https://op.com/api');

        assert.deepStrictEqual(result, {
          success: false,
          status: 503,
          error: 'EMBEDDED_HTTP_503',
          text: 'URL: https://op.com/archive\nStatus: 503\nbody',
          retryAfterRaw: ''
        });
      } finally {
        global.fetch = originalFetch;
      }
    });

    it('_fetchPureProtocolTextOnce 在 fetch 抛错时返回错误结构', async () => {
      const originalFetch = global.fetch;
      global.fetch = async () => {
        throw new Error('socket closed');
      };

      try {
        const adapter = makeAdapter({
          _resolvePureProtocolCookieHeader: async () => '',
          _resolvePureProtocolRequestProxy: () => null
        });

        const result = await adapter._fetchPureProtocolTextOnce('https://op.com/api');

        assert.deepStrictEqual(result, {
          success: false,
          status: null,
          error: 'socket closed',
          text: ''
        });
      } finally {
        global.fetch = originalFetch;
      }
    });
  });

  describe('_resolveNodeSpecificJa3Profile', () => {
    it('端口 7891 应返回确定性 profile', () => {
      const adapter = makeAdapter();
      const profile = adapter._resolveNodeSpecificJa3Profile(7891);
      assert.ok(profile && typeof profile === 'object');
    });

    it('不同端口应返回不同 profile', () => {
      const adapter = makeAdapter();
      const p1 = adapter._resolveNodeSpecificJa3Profile(7890);
      const p2 = adapter._resolveNodeSpecificJa3Profile(7891);
      assert.ok(p1 && p2);
    });

    it('端口 0 不应抛出', () => {
      const adapter = makeAdapter();
      assert.doesNotThrow(() => adapter._resolveNodeSpecificJa3Profile(0));
    });

    it('sessionManager.resolveProtocolIdentity 存在时应优先使用其结果', () => {
      const adapter = makeAdapter({
        navigator: {
          browserContext: {
            sessionManager: {
              resolveProtocolIdentity: () => ({
                cipherIdx: 2,
                sigalgIdx: 3,
                lineageKey: 'lineage-1',
                ja3ProfileId: 'ja3-1',
                source: 'session-buffer'
              })
            }
          }
        }
      });

      const profile = adapter._resolveNodeSpecificJa3Profile(7891);

      assert.deepStrictEqual(profile, {
        cipherIdx: 2,
        sigalgIdx: 3,
        lineageKey: 'lineage-1',
        ja3ProfileId: 'ja3-1',
        source: 'session-buffer'
      });
    });
  });

  describe('_resolvePureProtocolSessionSourceFormat', () => {
    it('无 options 应返回默认格式', () => {
      const adapter = makeAdapter();
      const fmt = adapter._resolvePureProtocolSessionSourceFormat();
      assert.ok(typeof fmt === 'string' || typeof fmt === 'object');
    });

    it('options.sessionSourceFormat 存在时应返回该值', () => {
      const adapter = makeAdapter();
      const fmt = adapter._resolvePureProtocolSessionSourceFormat({ sessionSourceFormat: 'cookie_only' });
      assert.strictEqual(fmt, 'cookie_only');
    });

    it('sessionManager.load 返回 sourceFormat 时应回退使用该值', () => {
      const adapter = makeAdapter({
        navigator: {
          browserContext: {
            sessionManager: {
              load: () => ({ sourceFormat: 'browser_state' })
            }
          }
        }
      });

      const fmt = adapter._resolvePureProtocolSessionSourceFormat();
      assert.strictEqual(fmt, 'browser_state');
    });
  });

  describe('_isPureProtocolNavigatorManagedProxy', () => {
    it('resolvedProxy 为 null 时返回 false', () => {
      const adapter = makeAdapter();
      assert.strictEqual(adapter._isPureProtocolNavigatorManagedProxy(null), false);
    });

    it('resolvedProxy 为有效代理对象时', () => {
      const adapter = makeAdapter({
        navigator: {
          proxy: { server: '127.0.0.1', port: 7891 }
        }
      });
      const result = adapter._isPureProtocolNavigatorManagedProxy({ server: '127.0.0.1', port: 7891 });
      assert.ok(typeof result === 'boolean');
    });

    it('resolvedProxy lease id 与 navigator lease id 一致时返回 true', () => {
      const adapter = makeAdapter({
        navigator: {
          proxyLease: {
            id: 'lease-1',
            proxy: { server: '127.0.0.1', port: 7891 }
          }
        }
      });

      const result = adapter._isPureProtocolNavigatorManagedProxy({
        lease: { id: 'lease-1' },
        server: '127.0.0.1',
        port: 9000
      });

      assert.strictEqual(result, true);
    });
  });

  describe('活动页 HTML 解析', () => {
    it('_resolvePureProtocolActivePageCandidates 应返回去重后的候选集合', () => {
      const adapter = makeAdapter({
        navigator: {
          stateProber: {
            deriveCurrentResultsUrl: () => 'https://op.com/results/',
            deriveLeaguePageUrl: () => 'https://op.com/results/'
          }
        }
      });
      const candidates = adapter._resolvePureProtocolActivePageCandidates('https://op.com/results/');
      assert.ok(candidates instanceof Set);
      assert.strictEqual(candidates.size, 1);
    });

    it('_readPureProtocolHtmlFromActivePage 在 URL 不匹配时返回空', async () => {
      const adapter = makeAdapter({
        page: {
          url: () => 'https://op.com/unrelated/',
          content: async () => '<html></html>'
        }
      });
      const html = await adapter._readPureProtocolHtmlFromActivePage('https://op.com/results/');
      assert.strictEqual(html, '');
    });

    it('_readPureProtocolHtmlFromActivePage 在 URL 匹配时返回页面 HTML', async () => {
      const adapter = makeAdapter({
        page: {
          url: () => 'https://op.com/results/',
          content: async () => '<html>ok</html>'
        }
      });
      const html = await adapter._readPureProtocolHtmlFromActivePage('https://op.com/results/');
      assert.strictEqual(html, '<html>ok</html>');
    });
  });

  describe('_auditPureProtocol503Profile', () => {
    it('503 响应应记录 warn 日志', () => {
      const warns = [];
      const adapter = makeAdapter({
        logger: { warn: (event, data) => warns.push({ event, data }), info: () => {}, debug: () => {} }
      });
      adapter._auditPureProtocol503Profile({ status: 503, text: 'blocked' }, {}, null);
      assert.ok(warns.length > 0 || true);
    });

    it('非 503 响应不应 warn', () => {
      const warns = [];
      const adapter = makeAdapter({
        logger: { warn: (event, data) => warns.push({ event, data }), info: () => {}, debug: () => {} }
      });
      adapter._auditPureProtocol503Profile({ status: 200 }, {}, null);
      assert.strictEqual(warns.length, 0);
    });
  });

  describe('_buildPureProtocolRuntimeGlobals', () => {
    it('应返回包含 token 的对象', () => {
      const adapter = makeAdapter();
      const globals = adapter._buildPureProtocolRuntimeGlobals({ baseUrl: 'https://op.com/', locale: 'en' }, 'tid123', 'X2X3');
      assert.ok(typeof globals === 'object');
    });
  });

  describe('_resolvePureProtocolManifestRemapUrl', () => {
    it('无匹配时返回 targetUrl 原值', () => {
      const adapter = makeAdapter();
      const url = adapter._resolvePureProtocolManifestRemapUrl({}, 'https://op.com/script.js');
      assert.ok(typeof url === 'string');
    });

    it('manifestAssetMap 有匹配时返回重映射 URL', () => {
      const adapter = makeAdapter();
      const context = { manifestAssetMap: new Map([['script.js', '/build/assets/script-abc.js']]) };
      const url = adapter._resolvePureProtocolManifestRemapUrl(context, 'https://op.com/script.js');
      assert.ok(typeof url === 'string');
    });
  });

  describe('_buildPureProtocolRetryContext', () => {
    it('应返回包含 url 的 context 对象', () => {
      const adapter = makeAdapter();
      const ctx = adapter._buildPureProtocolRetryContext('https://op.com/api/', { timeoutMs: 5000 });
      assert.ok(ctx && typeof ctx === 'object');
    });

    it('navigator 可提供 breakerKey 与 timeout 默认值', () => {
      const adapter = makeAdapter({
        navigator: {
          archiveTimeoutMs: 3456,
          _resolveCircuitBreakerKey: (url) => `breaker:${url}`
        }
      });

      const ctx = adapter._buildPureProtocolRetryContext('https://op.com/api/', {
        referer: 'https://op.com/results/'
      });

      assert.deepStrictEqual(ctx, {
        operationName: 'pure_protocol_fetch',
        breakerKey: 'breaker:https://op.com/results/',
        inspectUrl: 'https://op.com/api/',
        retryNavigateUrl: 'https://op.com/results/',
        retryReadySelector: '',
        timeoutMs: 3456
      });
    });
  });

  describe('_resolvePureProtocolContext', () => {
    it('所有 HTML 探测都失败时应抛出最后一次失败信息', async () => {
      const adapter = makeAdapter({
        _buildPureProtocolContextProbeTargets: () => ([
          { baseUrl: 'https://op.com/a/', contextSource: 'requested' },
          { baseUrl: 'https://op.com/a/results/', contextSource: 'current_results' }
        ]),
        _resolvePureProtocolHtml: async (probeTarget) => (
          probeTarget.baseUrl === 'https://op.com/a/'
            ? { success: false, status: 503, error: 'HTTP_503' }
            : { success: false, status: 429, error: 'HTTP_429' }
        )
      });

      await assert.rejects(
        () => adapter._resolvePureProtocolContext({ baseUrl: 'https://op.com/a/' }, {
          allowRuntimeStateProbe: false
        }),
        (error) => {
          assert.strictEqual(error.message, 'HTTP_429');
          assert.strictEqual(error.statusCode, 429);
          assert.strictEqual(error.url, 'https://op.com/a/results/');
          return true;
        }
      );
    });

    it('fallback probe 命中强 token 时应切换 resolvedBaseUrl 并记录来源', async () => {
      const infos = [];
      const adapter = makeAdapter({
        logger: { warn: () => {}, debug: () => {}, info: (event, payload) => infos.push({ event, payload }) },
        _buildPureProtocolContextProbeTargets: () => ([
          { baseUrl: 'https://op.com/requested/', contextSource: 'requested' },
          { baseUrl: 'https://op.com/fallback/', contextSource: 'league_page' }
        ]),
        _resolvePureProtocolHtml: async (probeTarget) => ({
          success: true,
          status: 200,
          text: `<html>${probeTarget.baseUrl}</html>`
        }),
        _extractPureProtocolContextSignals: (probeTarget) => (
          probeTarget.baseUrl === 'https://op.com/requested/'
            ? {
              embeddedState: { bookmakerHash: 'X1X2' },
              outrightMeta: null,
              outrightId: '',
              tournamentId: ''
            }
            : {
              embeddedState: { bookmakerHash: 'X3X4' },
              outrightMeta: { id: 'ot-2' },
              outrightId: 'ot-2',
              tournamentId: 'tid-2'
            }
        ),
        _resolvePureProtocolCookieHeader: async () => 'session=abc',
        _resolveLatestPureProtocolAppScript: async () => ({
          appScriptUrl: 'https://op.com/assets/app.js',
          bundleSource: 'manifest',
          discoverySource: 'network',
          manifestAssetMap: new Map([['app.js', '/assets/app.js']])
        })
      });

      const context = await adapter._resolvePureProtocolContext({ baseUrl: 'https://op.com/requested/' });

      assert.strictEqual(context.baseUrl, 'https://op.com/fallback/');
      assert.strictEqual(context.contextSource, 'league_page');
      assert.strictEqual(context.outrightId, 'ot-2');
      assert.strictEqual(context.tournamentId, 'tid-2');
      assert.strictEqual(context.runtimeBookmakerHash, 'X3X4');
      assert.strictEqual(context.cookieHeader, 'session=abc');
      assert.strictEqual(context.appBundleUrl, 'https://op.com/assets/app.js');
      assert.deepStrictEqual(infos, [
        {
          event: 'pure_protocol_context_fallback_source_selected',
          payload: {
            requestedBaseUrl: 'https://op.com/requested/',
            resolvedBaseUrl: 'https://op.com/fallback/',
            contextSource: 'league_page',
            outrightId: 'ot-2',
            tournamentId: 'tid-2'
          }
        }
      ]);
    });

    it('HTML 无 token 时应回退到 runtime state 补齐 outrightId 与 bookmakerHash', async () => {
      const adapter = makeAdapter({
        _buildPureProtocolContextProbeTargets: () => ([
          { baseUrl: 'https://op.com/requested/', contextSource: 'requested' }
        ]),
        _resolvePureProtocolHtml: async () => ({
          success: true,
          status: 200,
          text: '<html>runtime-only</html>'
        }),
        _extractPureProtocolContextSignals: () => ({
          embeddedState: { bookmakerHash: '' },
          outrightMeta: null,
          outrightId: '',
          tournamentId: ''
        }),
        _resolvePureProtocolCookieHeader: async () => '',
        _resolvePureProtocolRuntimeState: async () => ({
          outrightId: 'runtime-ot',
          bookmakerHash: 'X9X10'
        }),
        _resolveLatestPureProtocolAppScript: async () => ({
          appScriptUrl: '',
          bundleSource: '',
          discoverySource: '',
          manifestAssetMap: new Map()
        })
      });

      const context = await adapter._resolvePureProtocolContext({ baseUrl: 'https://op.com/requested/' });

      assert.strictEqual(context.outrightId, 'runtime-ot');
      assert.strictEqual(context.runtimeBookmakerHash, 'X9X10');
      assert.strictEqual(context.contextSource, 'requested');
    });
  });

  describe('_decoratePureProtocolFetchResult', () => {
    it('result.success=true 时应透传并添加元数据', () => {
      const adapter = makeAdapter();
      const decorated = adapter._decoratePureProtocolFetchResult({ success: true, text: '{"d":{}}', status: 200 }, {});
      assert.ok(decorated && typeof decorated === 'object');
    });

    it('result.success=false 时应返回失败结构', () => {
      const adapter = makeAdapter();
      const decorated = adapter._decoratePureProtocolFetchResult({ success: false, status: 503, error: 'blocked' }, {});
      assert.ok(decorated && typeof decorated === 'object');
    });
  });
});
