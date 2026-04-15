'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconProtocolFetchFlow } = require('../../src/infrastructure/recon/services/ReconProtocolFetchFlow');

function createAppScriptResolution(overrides = {}) {
  return {
    appScriptUrl: 'https://www.oddsportal.com/build/assets/app-HnniEWV5.js',
    bundleSource: 'export const ai = (value) => value;',
    discoverySource: 'html',
    manifestAssetMap: new Map(),
    ...overrides
  };
}

function attachProtocolAdapterStubs(fakeHandler, options = {}) {
  Object.assign(fakeHandler, reconProtocolFetchFlow);
  fakeHandler._resolvePureProtocolCookieHeader = async () => options.cookieHeader || '';
  fakeHandler._resolveLatestPureProtocolAppScript = async () => (
    options.appScriptResolution || createAppScriptResolution()
  );
  return fakeHandler;
}

describe('ReconProtocolFetchFlow', () => {
  it('应从 HTML 中提取 pure protocol 所需的 bundle、token 与赛季信息', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          extractPageOutrightsMetaFromHtml() {
            return {
              id: 'xbsqV0go',
              sid: 1,
              cid: 200,
              archive: true
            };
          }
        }
      },
      async _fetchPureProtocolText() {
        return {
          success: true,
          status: 200,
          text: [
            '<html lang="en"><head>',
            '<script>var pageOutrightsVar = \'{"id":"xbsqV0go","sid":1,"cid":200,"archive":true}\';</script>',
            '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
            '</head><body>',
            '<div data-json="&quot;_tournamentId&quot;:80299,&quot;_lang&quot;:&quot;en&quot;"></div>',
            '</body></html>'
          ].join('')
        };
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script>var pageOutrightsVar = \'{"id":"xbsqV0go","sid":1,"cid":200,"archive":true}\';</script>',
          '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
          '</head><body>',
          '<div data-json="&quot;_tournamentId&quot;:80299,&quot;_lang&quot;:&quot;en&quot;"></div>',
          '</body></html>'
        ].join('')
      };
    };
    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/usa/mls-2025/results/',
      {}
    );

    assert.strictEqual(context.outrightId, 'xbsqV0go');
    assert.strictEqual(context.tournamentId, '80299');
    assert.strictEqual(context.seasonToken, '2025');
    assert.strictEqual(context.locale, 'en');
    assert.strictEqual(
      context.appBundleUrl,
      'https://www.oddsportal.com/build/assets/app-HnniEWV5.js'
    );
  });

  it('应从 __INITIAL_STATE__ 的 tournament 对象中反查 token', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          extractPageOutrightsMetaFromHtml() {
            return {
              id: '',
              sid: 1,
              cid: 100,
              archive: true
            };
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
          '<script>',
          'window.__INITIAL_STATE__ = {"bootstrap":{"pageVar":{"otCode":"state-ot-token","bookiehash":"X1024"},"tournament":{"name":"J1 League 2026","id":"state-j1-token"}}};',
          '</script>',
          '</head><body></body></html>'
        ].join('')
      };
    };

    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/japan/j1-league-2026/results/',
      {}
    );

    assert.strictEqual(context.outrightId, 'state-j1-token');
    assert.strictEqual(context.runtimeBookmakerHash, 'X1024');
  });

  it('应从组件 sport-data 属性中提取 encodedTurnamentId 与 tournamentId', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          extractPageOutrightsMetaFromHtml() {
            return {
              id: '',
              sid: 1,
              cid: 198,
              archive: true
            };
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
          '</head><body>',
          '<star-component :sport-data="{&quot;oddsRequest&quot;:{&quot;url&quot;:&quot;/ajax-sport-country-tournament-archive_/1/KKay4EE8/&quot;},&quot;tournamentId&quot;:91201,&quot;encodedTurnamentId&quot;:&quot;KKay4EE8&quot;}"></star-component>',
          '</body></html>'
        ].join('')
      };
    };

    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/england/premier-league/results/',
      {}
    );

    assert.strictEqual(context.outrightId, 'KKay4EE8');
    assert.strictEqual(context.tournamentId, '91201');
  });

  it('season URL 为空壳时应回探 current results URL 提取 token', async () => {
    const requestedUrl = 'https://www.oddsportal.com/football/england/premier-league-2025-2026/results/';
    const currentResultsUrl = 'https://www.oddsportal.com/football/england/premier-league/results/';
    const requests = [];
    const infoLogs = [];
    const fakeHandler = {
      logger: {
        info(event, payload) {
          infoLogs.push({ event, payload });
        },
        warn() {},
        error() {},
        debug() {}
      },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          deriveCurrentResultsUrl(url) {
            return url.replace('-2025-2026/results/', '/results/');
          },
          deriveLeaguePageUrl(url) {
            return url.replace(/\/results\/?$/i, '/');
          },
          extractPageOutrightsMetaFromHtml(html) {
            return html.includes('"id":"KKay4EE8"')
              ? {
                id: 'KKay4EE8',
                sid: 1,
                cid: 198,
                archive: true
              }
              : {
                id: '',
                sid: 1,
                cid: 198,
                archive: true
              };
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText(url) {
      requests.push(url);
      if (url === requestedUrl) {
        return {
          success: true,
          status: 200,
          text: [
            '<html lang="en"><head>',
            '<script>var pageOutrightsVar = \'{"id":"","sid":1,"cid":198,"archive":true}\';</script>',
            '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
            '</head><body>',
            '<star-component :sport-data="{&quot;oddsRequest&quot;:{&quot;url&quot;:&quot;/ajax-sport-country-tournament-archive_/1//&quot;},&quot;tournamentId&quot;:null,&quot;encodedTurnamentId&quot;:&quot;&quot;}"></star-component>',
            '</body></html>'
          ].join('')
        };
      }

      if (url === currentResultsUrl) {
        return {
          success: true,
          status: 200,
          text: [
            '<html lang="en"><head>',
            '<script>var pageOutrightsVar = \'{"id":"KKay4EE8","sid":1,"cid":198,"archive":true}\';</script>',
            '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
            '</head><body>',
            '<star-component :sport-data="{&quot;oddsRequest&quot;:{&quot;url&quot;:&quot;/ajax-sport-country-tournament-archive_/1/KKay4EE8/&quot;},&quot;tournamentId&quot;:91201,&quot;encodedTurnamentId&quot;:&quot;KKay4EE8&quot;}"></star-component>',
            '</body></html>'
          ].join('')
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    };

    const context = await fakeHandler._resolvePureProtocolContext(requestedUrl, {});

    assert.deepStrictEqual(requests, [requestedUrl, currentResultsUrl]);
    assert.strictEqual(context.requestedBaseUrl, requestedUrl);
    assert.strictEqual(context.baseUrl, currentResultsUrl);
    assert.strictEqual(context.contextSource, 'current_results');
    assert.strictEqual(context.outrightId, 'KKay4EE8');
    assert.strictEqual(context.tournamentId, '91201');
    assert.ok(infoLogs.some((entry) => entry.event === 'pure_protocol_context_fallback_source_selected'));
  });

  it('HTML 缺失 token 时应回退到 runtime pageVar.otCode', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      page: {
        async evaluate() {
          return {
            otCode: '5fdb38ad-528a-4fb9-a576-b8c42e07565d',
            bookiehash: 'X262144',
            myot: ''
          };
        },
        async waitForTimeout() {}
      },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        postApiDiscoveryWaitMs: 1,
        async ensureBrowserHealthy() {},
        async navigate() {},
        stateProber: {
          deriveCurrentResultsUrl(url) {
            return url;
          },
          extractPageOutrightsMetaFromHtml() {
            return {
              id: '',
              sid: 1,
              cid: 100,
              archive: true
            };
          },
          async extractTournamentToken() {
            return '5fdb38ad-528a-4fb9-a576-b8c42e07565d';
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script>var pageOutrightsVar = \'{"id":"","sid":1,"cid":100,"archive":true}\';</script>',
          '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
          '</head><body>',
          '<div data-json="&quot;_tournamentId&quot;:null,&quot;_lang&quot;:&quot;en&quot;"></div>',
          '</body></html>'
        ].join('')
      };
    };

    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/japan/j1-league-2026/results/',
      {}
    );

    assert.strictEqual(context.outrightId, '5fdb38ad-528a-4fb9-a576-b8c42e07565d');
    assert.strictEqual(context.runtimeBookmakerHash, 'X262144');
  });

  it('Node 侧 HTML 抓取失败时应回退到当前浏览器页面内容', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      page: {
        url() {
          return 'https://www.oddsportal.com/football/japan/j2-league/results/';
        },
        async content() {
          return [
            '<html lang="en"><head>',
            '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
            '<script>',
            'window.__INITIAL_STATE__ = {"bootstrap":{"pageVar":{"otCode":"j2-page-token","bookiehash":"X262144"},"tournament":{"name":"J2 League","id":"j2-page-token"}}};',
            '</script>',
            '</head><body></body></html>'
          ].join('');
        }
      },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          deriveCurrentResultsUrl(url) {
            return url;
          },
          deriveLeaguePageUrl(url) {
            return url.replace(/\/results\/?$/i, '');
          },
          extractPageOutrightsMetaFromHtml() {
            return {
              id: '',
              sid: 1,
              cid: 100,
              archive: true
            };
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: false,
        status: null,
        error: 'fetch failed',
        text: ''
      };
    };

    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/japan/j2-league/results/',
      {}
    );

    assert.strictEqual(context.outrightId, 'j2-page-token');
    assert.strictEqual(context.runtimeBookmakerHash, 'X262144');
      assert.strictEqual(
        context.appBundleUrl,
        'https://www.oddsportal.com/build/assets/app-HnniEWV5.js'
      );
  });

  it('动态 app bundle 解析应覆盖页面中的陈旧脚本链接', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          extractPageOutrightsMetaFromHtml() {
            return {
              id: 'tUfctlzI',
              sid: 1,
              cid: 200,
              archive: true
            };
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler, {
      cookieHeader: 'session=mls',
      appScriptResolution: createAppScriptResolution({
        appScriptUrl: 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js',
        discoverySource: 'root_html',
        manifestAssetMap: new Map([
          ['NowOnOddsPortal', 'https://www.oddsportal.com/build/assets/NowOnOddsPortal-otpvwymg.js']
        ])
      })
    });
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script>var pageOutrightsVar = \'{"id":"tUfctlzI","sid":1,"cid":200,"archive":true}\';</script>',
          '<script type="module" src="/build/assets/app-BVYnMZqo.js"></script>',
          '</head><body></body></html>'
        ].join('')
      };
    };

    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/usa/mls-2025/results/',
      {}
    );

    assert.strictEqual(
      context.appBundleUrl,
      'https://www.oddsportal.com/build/assets/app-JoAS42xl.js'
    );
    assert.strictEqual(context.appScriptDiscoverySource, 'root_html');
    assert.strictEqual(
      context.appScriptManifestMap.get('NowOnOddsPortal'),
      'https://www.oddsportal.com/build/assets/NowOnOddsPortal-otpvwymg.js'
    );
    assert.strictEqual(context.cookieHeader, 'session=mls');
  });

  it('pure protocol 文本抓取应重试瞬时网络失败', async () => {
    const originalFetch = global.fetch;
    let attempts = 0;

    global.fetch = async () => {
      attempts++;
      if (attempts === 1) {
        const error = new TypeError('fetch failed');
        error.cause = new Error('SocketError: other side closed');
        throw error;
      }

      return {
        ok: true,
        status: 200,
        headers: {
          get() {
            return '';
          }
        },
        async text() {
          return '{"ok":true}';
        }
      };
    };

    try {
      const fakeHandler = {
        logger: { info() {}, warn() {}, error() {}, debug() {} },
        navigator: {
          archiveTimeoutMs: 1234
        }
      };

      Object.assign(fakeHandler, reconProtocolFetchFlow);
      const response = await fakeHandler._fetchPureProtocolText(
        'https://example.com/pure-protocol',
        { maxAttempts: 2, retryDelayMs: 0 }
      );

      assert.strictEqual(response.success, true);
      assert.strictEqual(response.status, 200);
      assert.strictEqual(response.text, '{"ok":true}');
      assert.strictEqual(attempts, 2);
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('pure protocol 请求应携带 referer、x-requested-with 与 cookie', async () => {
    const originalFetch = global.fetch;
    const requests = [];

    global.fetch = async (url, options = {}) => {
      requests.push({ url, headers: options.headers });
      return {
        ok: true,
        status: 200,
        headers: {
          get() {
            return '';
          }
        },
        async text() {
          return '{"ok":true}';
        }
      };
    };

    try {
      const fakeHandler = {
        logger: { info() {}, warn() {}, error() {}, debug() {} },
        navigator: {
          archiveTimeoutMs: 1234
        }
      };
      attachProtocolAdapterStubs(fakeHandler, { cookieHeader: 'sid=mls; locale=en' });

      const response = await fakeHandler._fetchPureProtocolTextOnce(
        'https://www.oddsportal.com/ajax-sport-country-tournament_/1/tUfctlzI/X262144/1/',
        {
          referer: 'https://www.oddsportal.com/football/usa/mls-2025/results/',
          accept: 'application/json, text/plain, */*'
        }
      );

      assert.strictEqual(response.success, true);
      assert.strictEqual(requests.length, 1);
      assert.strictEqual(
        requests[0].headers.referer,
        'https://www.oddsportal.com/football/usa/mls-2025/results/'
      );
      assert.strictEqual(requests[0].headers['x-requested-with'], 'XMLHttpRequest');
      assert.strictEqual(requests[0].headers.cookie, 'sid=mls; locale=en');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('pure protocol 模块抓取遇到 404 chunk 时应按 manifest 重映射', async () => {
    const originalFetch = global.fetch;
    const requestedUrls = [];
    const infoLogs = [];

    global.fetch = async (url, options = {}) => {
      requestedUrls.push({ url, headers: options.headers });
      if (url === 'https://www.oddsportal.com/build/assets/NowOnOddsPortal-CpZAkcJZ.js') {
        return {
          ok: false,
          status: 404,
          async text() {
            return '';
          }
        };
      }

      if (url === 'https://www.oddsportal.com/build/assets/NowOnOddsPortal-otpvwymg.js') {
        return {
          ok: true,
          status: 200,
          async text() {
            return 'export const NowOnOddsPortal = {};';
          }
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    };

    try {
      const fakeHandler = {
        logger: {
          info(event, payload) {
            infoLogs.push({ event, payload });
          },
          warn() {},
          error() {},
          debug() {}
        },
        navigator: {
          traceId: 'trace-pure-protocol'
        }
      };
      attachProtocolAdapterStubs(fakeHandler);

      const loadModule = fakeHandler._createPureProtocolSourceLoader({
        baseUrl: 'https://www.oddsportal.com/football/usa/mls-2025/results/',
        appBundleUrl: 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js',
        cookieHeader: 'sid=mls',
        appScriptManifestMap: new Map([
          ['NowOnOddsPortal', 'https://www.oddsportal.com/build/assets/NowOnOddsPortal-otpvwymg.js']
        ])
      });

      const source = await loadModule('/build/assets/NowOnOddsPortal-CpZAkcJZ.js');

      assert.strictEqual(source, 'export const NowOnOddsPortal = {};');
      assert.strictEqual(requestedUrls.length, 2);
      assert.strictEqual(requestedUrls[0].headers.cookie, 'sid=mls');
      assert.strictEqual(requestedUrls[1].url, 'https://www.oddsportal.com/build/assets/NowOnOddsPortal-otpvwymg.js');
      assert.ok(infoLogs.some((entry) => entry.event === 'app_script_manifest_remap_hit'));
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('pure protocol 模块抓取回跳旧 app bundle 时应重映射到 live bundle', async () => {
    const originalFetch = global.fetch;
    const requestedUrls = [];

    global.fetch = async (url, options = {}) => {
      requestedUrls.push({ url, headers: options.headers });
      if (url === 'https://www.oddsportal.com/build/assets/app-BVYnMZqo.js') {
        return {
          ok: false,
          status: 404,
          async text() {
            return '';
          }
        };
      }

      if (url === 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js') {
        return {
          ok: true,
          status: 200,
          async text() {
            return 'export const ai = (value) => value;';
          }
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    };

    try {
      const fakeHandler = {
        logger: { info() {}, warn() {}, error() {}, debug() {} },
        navigator: {
          traceId: 'trace-pure-protocol'
        }
      };
      attachProtocolAdapterStubs(fakeHandler);

      const loadModule = fakeHandler._createPureProtocolSourceLoader({
        baseUrl: 'https://www.oddsportal.com/football/usa/mls-2025/results/',
        appBundleUrl: 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js',
        cookieHeader: 'sid=mls',
        appScriptManifestMap: new Map()
      });

      const source = await loadModule('/build/assets/app-BVYnMZqo.js');

      assert.strictEqual(source, 'export const ai = (value) => value;');
      assert.strictEqual(requestedUrls.length, 2);
      assert.strictEqual(requestedUrls[1].url, 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js');
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('sample payload 遇到 503 时应局部切换代理并复用新 lease 拉取分页', async () => {
    const infoLogs = [];
    const warnLogs = [];
    const acquired = [];
    const released = [];
    const failures = [];
    const successes = [];
    const sampleAttempts = [];
    const pageFetchPorts = [];
    const fakeHandler = {
      logger: {
        info(event, payload) {
          infoLogs.push({ event, payload });
        },
        warn(event, payload) {
          warnLogs.push({ event, payload });
        },
        error() {},
        debug() {}
      },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        proxyLease: {
          id: 'LEASE-7890',
          proxy: {
            server: 'http://host.docker.internal:7890',
            port: 7890
          }
        },
        proxyProvider: {
          async acquire(options = {}) {
            acquired.push(options);
            return {
              id: 'LEASE-7911',
              proxy: {
                server: 'http://host.docker.internal:7911',
                port: 7911
              }
            };
          },
          async release(leaseOrId) {
            released.push(leaseOrId);
            return true;
          },
          async reportFailure(leaseOrId, metadata = {}) {
            failures.push({ leaseOrId, metadata });
            return true;
          },
          async reportSuccess(leaseOrId, metadata = {}) {
            successes.push({ leaseOrId, metadata });
            return true;
          }
        }
      }
    };

    attachProtocolAdapterStubs(fakeHandler);
    fakeHandler._waitPureProtocolFetchRetry = async function _waitPureProtocolFetchRetry() {};
    fakeHandler._resolvePureProtocolContext = async function _resolvePureProtocolContext() {
      return {
        baseUrl: 'https://www.oddsportal.com/football/england/premier-league/results/',
        outrightId: 'KKay4EE8',
        tournamentId: '91201',
        appBundleUrl: 'https://www.oddsportal.com/build/assets/app-HnniEWV5.js',
        seasonToken: '2025-2026',
        locale: 'en'
      };
    };
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText(url, options = {}) {
      const port = Number(options.proxyLease?.proxy?.port || options.proxyPort || 0) || null;
      if (url.includes('/ajax-sport-country-tournament-archive_/')) {
        sampleAttempts.push({ url, port });
        if (options.maxAttempts !== 1) {
          pageFetchPorts.push(port);
          return {
            success: true,
            status: 200,
            text: '{"d":{"rows":[],"total":0}}'
          };
        }

        if (url.includes('/1/0/?_=')) {
          if (port === 7890) {
            return {
              success: false,
              status: 503,
              error: 'EMBEDDED_HTTP_503',
              text: ''
            };
          }

          return {
            success: true,
            status: 200,
            text: 'encrypted-sample'
          };
        }

        throw new Error(`Unexpected archive URL: ${url}`);
      }

      throw new Error(`Unexpected URL: ${url}`);
    };
    fakeHandler._createPureProtocolDecryptor = async function _createPureProtocolDecryptor() {
      return {
        async decrypt() {
          return {
            d: {
              rows: [],
              total: 0
            }
          };
        },
        getAlgorithmVersion() {
          return 'unit-test';
        }
      };
    };

    const result = await fakeHandler._extractViaPureProtocol(
      {
        url: 'https://www.oddsportal.com/football/england/premier-league-2025-2026/results/'
      },
      {}
    );

    assert.strictEqual(result.sourceState, 'SOURCE_EMPTY');
    assert.ok(sampleAttempts.some((entry) => entry.port === 7890));
    assert.ok(sampleAttempts.some((entry) => entry.port === 7911));
    assert.deepStrictEqual(pageFetchPorts, [7911]);
    assert.strictEqual(failures.length, 1);
    assert.strictEqual(failures[0].leaseOrId, 'LEASE-7890');
    assert.strictEqual(failures[0].metadata.port, 7890);
    assert.strictEqual(successes.length, 1);
    assert.strictEqual(successes[0].leaseOrId, 'LEASE-7911');
    assert.strictEqual(successes[0].metadata.port, 7911);
    assert.strictEqual(acquired.length, 1);
    assert.deepStrictEqual(acquired[0].excludePorts, [7890]);
    const archivePreflightLogs = infoLogs.filter((entry) => entry.event === 'pure_protocol_archive_request_preflight');
    assert.strictEqual(archivePreflightLogs.length, 1);
    assert.strictEqual(archivePreflightLogs[0].payload.archiveToken, 'KKay4EE8');
    assert.ok(warnLogs.some((entry) => entry.event === 'pure_protocol_sample_proxy_switching'));
    assert.ok(warnLogs.some((entry) => entry.event === 'pure_protocol_archive_zero_candidate_payload'));
    assert.strictEqual(released.length, 1);
    assert.strictEqual(released[0].id || released[0], 'LEASE-7911');
  });
});
