'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');

const { ReconPureDecryptor } = require('../../src/infrastructure/recon/services/ReconPureDecryptor');
const {
  reconDecryptorSourceExtractor,
  findLatestAppScript,
} = require('../../src/infrastructure/recon/services/ReconDecryptorSourceExtractor');

function createLogger() {
  const events = {
    info: [],
    warn: [],
    debug: [],
    error: [],
  };

  return {
    events,
    logger: {
      info(event, payload) {
        events.info.push({ event, payload });
      },
      warn(event, payload) {
        events.warn.push({ event, payload });
      },
      debug(event, payload) {
        events.debug.push({ event, payload });
      },
      error(event, payload) {
        events.error.push({ event, payload });
      },
    },
  };
}

function createExtractor(overrides = {}) {
  const { events, logger } = createLogger();
  return {
    ...reconDecryptorSourceExtractor,
    logger,
    traceId: 'trace-test',
    readinessTimeoutMs: 10,
    readinessPollMs: 2,
    rememberedSamples: [],
    __events: events,
    ...overrides,
  };
}

function installFetchStub(responseMap) {
  const originalFetch = globalThis.fetch;
  const calls = [];

  globalThis.fetch = async (url, options = {}) => {
    const normalizedUrl = String(url);
    calls.push({ url: normalizedUrl, options });
    const response = responseMap[normalizedUrl];
    if (response instanceof Error) {
      throw response;
    }
    if (!response) {
      throw new Error(`Unexpected fetch: ${normalizedUrl}`);
    }

    return {
      ok: response.ok !== false,
      status: response.status ?? 200,
      url: response.url || normalizedUrl,
      async text() {
        return typeof response.text === 'function' ? response.text() : (response.text || '');
      },
    };
  };

  return {
    calls,
    restore() {
      globalThis.fetch = originalFetch;
    },
  };
}

async function withDom(html, globals, callback) {
  const dom = new JSDOM(html, {
    url: globals.locationHref || 'https://www.oddsportal.com/football/usa/mls/',
  });
  const previousWindow = globalThis.window;
  const previousDocument = globalThis.document;
  const previousLocation = globalThis.location;

  Object.assign(dom.window, globals.window || {});
  globalThis.window = dom.window;
  globalThis.document = dom.window.document;
  globalThis.location = dom.window.location;

  try {
    return await callback(dom.window);
  } finally {
    dom.window.close();
    globalThis.window = previousWindow;
    globalThis.document = previousDocument;
    globalThis.location = previousLocation;
  }
}

function createDomPage(html, globals = {}, pageOverrides = {}) {
  const baseUrl = pageOverrides.baseUrl || 'https://www.oddsportal.com/football/usa/mls/';

  return {
    url() {
      return baseUrl;
    },
    async content() {
      return html;
    },
    async evaluate(fn, ...args) {
      return withDom(html, {
        locationHref: baseUrl,
        window: globals,
      }, async () => fn(...args));
    },
    ...pageOverrides,
  };
}

describe('ReconDecryptorSourceExtractor', () => {
  it('findLatestAppScript 应在 HTML 候选失效后回落到 manifest 中的最新 app bundle', async () => {
    const baseUrl = 'https://www.oddsportal.com/football/usa/mls/';
    const fetchStub = installFetchStub({
      [baseUrl]: {
        text: '<link rel="modulepreload" href="/build/assets/app-stale.js">',
      },
      'https://www.oddsportal.com/': {
        text: '<script src="/build/assets/app-root-stale.js"></script>',
      },
      'https://www.oddsportal.com/build/manifest.json': {
        text: JSON.stringify({
          'resources/js/app.js': {
            file: 'assets/app-live-123456.js',
            name: 'app',
            isEntry: true,
          },
        }),
      },
      'https://www.oddsportal.com/build/assets/app-stale.js': {
        ok: false,
        status: 404,
        text: '',
      },
      'https://www.oddsportal.com/build/assets/app-root-stale.js': {
        ok: false,
        status: 404,
        text: '',
      },
      'https://www.oddsportal.com/build/assets/app-live-123456.js': {
        text: 'export const ai = () => "{}";',
      },
    });
    const { events, logger } = createLogger();

    try {
      const result = await findLatestAppScript(baseUrl, {
        logger,
        traceId: 'trace-app',
      });

      assert.equal(result.appScriptUrl, 'https://www.oddsportal.com/build/assets/app-live-123456.js');
      assert.equal(result.discoverySource, 'build_manifest');
      assert.equal(result.manifestAssetMap.get('app'), 'https://www.oddsportal.com/build/assets/app-live-123456.js');
      assert.equal(events.debug.length, 2);
      assert.equal(events.info[0].event, 'app_script_bundle_fetch_success');
    } finally {
      fetchStub.restore();
    }
  });

  it('findLatestAppScript 在候选全部失效时应返回 unresolved', async () => {
    const fetchStub = installFetchStub({
      'https://www.oddsportal.com/build/assets/app-missing.js': {
        ok: false,
        status: 404,
        text: '',
      },
      'https://www.oddsportal.com/build/manifest.json': {
        text: 'not-json',
      },
    });

    try {
      const result = await findLatestAppScript('https://www.oddsportal.com/football/usa/mls/', {
        html: '<html><body></body></html>',
        allowRootFallback: false,
        candidateUrls: ['https://www.oddsportal.com/build/assets/app-missing.js'],
      });

      assert.equal(result.appScriptUrl, '');
      assert.equal(result.discoverySource, 'unresolved');
      assert.equal(result.attempted.length, 1);
      assert.equal(result.manifestAssetMap.size, 0);
    } finally {
      fetchStub.restore();
    }
  });

  it('findLatestAppScript 应覆盖 malformed baseUrl、缺失 fetch 与 manifest 杂质分支', async () => {
    const originalFetch = globalThis.fetch;
    delete globalThis.fetch;

    try {
      const result = await findLatestAppScript('::bad-url', {
        html: [
          '<script src="/build/assets/not-app.js"></script>',
          '<script src="http://[broken-url"></script>',
          '<script src="/build/assets/app-dup.js"></script>',
        ].join(''),
        allowRootFallback: false,
        candidateUrls: [
          'https://www.oddsportal.com/build/assets/app-dup.js',
          'https://www.oddsportal.com/build/assets/app-dup.js',
        ],
      });

      assert.equal(result.appScriptUrl, '');
      assert.equal(result.discoverySource, 'unresolved');
      assert.equal(result.attempted.length, 1);
      assert.equal(result.manifestUrl, 'https://www.oddsportal.com/build/manifest.json');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('findLatestAppScript 应跳过 manifest 中的非 JS、非 entry 与畸形资源', async () => {
    const fetchStub = installFetchStub({
      'https://www.oddsportal.com/football/usa/mls/': {
        text: '<html></html>',
      },
      'https://www.oddsportal.com/': {
        text: '<html></html>',
      },
      'https://www.oddsportal.com/build/manifest.json': {
        text: JSON.stringify({
          'resources/js/style.css': { file: 'assets/style.css' },
          'resources/js/non-entry.js': { file: 'assets/app-non-entry.js', name: 'non-entry', isEntry: false },
          'resources/js/bad.js': { file: 'http://[broken' },
          'resources/js/app.ts': { file: 'assets/app-live-654321.js', name: 'app', isEntry: true },
        }),
      },
      'https://www.oddsportal.com/build/assets/app-live-654321.js': {
        text: 'export const ai = () => "{}";',
      },
    });

    try {
      const result = await findLatestAppScript('https://www.oddsportal.com/football/usa/mls/', {
        allowRootFallback: true,
      });

      assert.equal(result.appScriptUrl, 'https://www.oddsportal.com/build/assets/app-live-654321.js');
      assert.equal(result.discoverySource, 'build_manifest');
    } finally {
      fetchStub.restore();
    }
  });

  it('_readPageCookieHeader 应返回 cookie，并在 evaluate 失败时降级为空串', async () => {
    const extractor = createExtractor();

    const cookie = await extractor._readPageCookieHeader({
      async evaluate(fn) {
        globalThis.document = { cookie: 'session=abc123' };
        try {
          return fn();
        } finally {
          delete globalThis.document;
        }
      },
    });
    assert.equal(cookie, 'session=abc123');

    const fallback = await extractor._readPageCookieHeader({
      async evaluate() {
        throw new Error('page crashed');
      },
    });
    assert.equal(fallback, '');
    assert.equal(await extractor._readPageCookieHeader(null), '');
  });

  it('_resolveLiveAppScript 应携带页面 cookie 并缓存最新的 app script 解析结果', async () => {
    const baseUrl = 'https://www.oddsportal.com/football/usa/mls/';
    const fetchStub = installFetchStub({
      [baseUrl]: {
        text: '<script src="/build/assets/app-live-abcdef.js"></script>',
      },
      'https://www.oddsportal.com/': {
        text: '<html></html>',
      },
      'https://www.oddsportal.com/build/manifest.json': {
        text: JSON.stringify({}),
      },
      'https://www.oddsportal.com/build/assets/app-live-abcdef.js': {
        text: 'export const ai = () => "{}";',
      },
    });
    const extractor = createExtractor();

    try {
      const resolution = await extractor._resolveLiveAppScript({
        url() {
          return baseUrl;
        },
        async evaluate(fn) {
          globalThis.document = { cookie: 'token=secure' };
          try {
            return fn();
          } finally {
            delete globalThis.document;
          }
        },
      }, 'https://www.oddsportal.com/build/assets/app-stale.js');

      assert.equal(resolution.appScriptUrl, 'https://www.oddsportal.com/build/assets/app-live-abcdef.js');
      assert.equal(extractor._lastResolvedAppScriptUrl, resolution.appScriptUrl);
      assert.ok(extractor._lastResolvedAppScriptManifestMap instanceof Map);
      assert.equal(fetchStub.calls[0].options.headers.cookie, 'token=secure');
    } finally {
      fetchStub.restore();
    }
  });

  it('_fetchBundleSource 应优先复用 live resolution 中已经拿到的 bundle', async () => {
    const extractor = createExtractor({
      async _resolveLiveAppScript() {
        return {
          appScriptUrl: 'https://www.oddsportal.com/build/assets/app-live.js',
          bundleSource: 'export const ai = () => "{}";',
        };
      },
    });

    const source = await extractor._fetchBundleSource(
      { url() { return 'https://www.oddsportal.com/football/usa/mls/'; } },
      'https://www.oddsportal.com/build/assets/app-live.js'
    );

    assert.equal(source, 'export const ai = () => "{}";');
  });

  it('_fetchBundleSource 在页面抓取失败时应回落到 Node fetch', async () => {
    const fetchStub = installFetchStub({
      'https://www.oddsportal.com/build/assets/app-live.js': {
        text: 'export const ai = () => "{}";',
      },
    });
    const extractor = createExtractor({
      async _resolveLiveAppScript() {
        return {
          appScriptUrl: 'https://www.oddsportal.com/build/assets/app-live.js',
          bundleSource: '',
        };
      },
    });

    try {
      const source = await extractor._fetchBundleSource(
        {
          url() {
            return 'https://www.oddsportal.com/football/usa/mls/';
          },
          async evaluate() {
            throw new Error('page_fetch_failed');
          },
        },
        'https://www.oddsportal.com/build/assets/app-live.js'
      );

      assert.equal(source, 'export const ai = () => "{}";');
      assert.equal(extractor.__events.debug[0].event, 'app_script_bundle_fetch_failed');
      assert.equal(extractor.__events.debug[1].event, 'app_script_bundle_fetch_fallback_node_hit');
    } finally {
      fetchStub.restore();
    }
  });

  it('_waitForDecryptorReady 应吞掉 readiness 超时并记录 debug 事件', async () => {
    const extractor = createExtractor();
    const calls = [];

    await extractor._waitForDecryptorReady({
      async waitForFunction(_fn, options) {
        calls.push(options.timeout);
        throw new Error('Timeout 5000ms exceeded');
      },
    });

    assert.deepEqual(calls, [10, 10]);
    assert.equal(extractor.__events.debug[0].event, 'decryptor_readiness_wait_script_timeout');
    assert.equal(extractor.__events.debug[1].event, 'decryptor_readiness_wait_otcode_timeout');
  });

  it('_waitForDecryptorReady 在 otCode/pageOutrights 命中时应允许成功返回', async () => {
    const extractor = createExtractor();
    const page = {
      callIndex: 0,
      async waitForFunction(fn) {
        this.callIndex += 1;
        if (this.callIndex === 1) {
          const originalDocument = globalThis.document;
          globalThis.document = {
            querySelector() {
              return { src: '/build/assets/app-live.js' };
            },
          };
          try {
            assert.equal(fn(), true);
          } finally {
            globalThis.document = originalDocument;
          }
          return;
        }

        return withDom('<html><body></body></html>', {
          window: {
            pageVar: { otCode: 'MLS' },
          },
        }, async () => {
          assert.equal(fn(), true);
        });
      },
    };

    await extractor._waitForDecryptorReady(page);
    assert.equal(extractor.__events.debug.length, 0);
  });

  it('_readSerializableRuntimeState 应提取 window.pageVar 与 pageOutrightsVar 的可序列化子集', async () => {
    const extractor = createExtractor();
    const page = createDomPage('<html><body></body></html>', {
      pageVar: JSON.stringify({
        locale: 'en',
        localeBox: 'us',
        localeUrlPrefix: '/football',
        otCode: 'MLS',
        bookiehash: 'bookie',
        myot: ['a'],
        myBookmakers: ['b'],
        userData: { id: 1 },
        ignored: 'x',
      }),
      pageOutrightsVar: {
        id: 'out-1',
        sid: 'sid-1',
        cid: 'cid-1',
        archive: true,
        ignored: false,
      },
    });

    const state = await extractor._readSerializableRuntimeState(page);

    assert.equal(state.pageVar.locale, 'en');
    assert.equal(state.pageVar.otCode, 'MLS');
    assert.equal(state.pageOutrightsVar.id, 'out-1');
    assert.equal(state.locationHref, 'https://www.oddsportal.com/football/usa/mls/');
  });

  it('_readSerializableRuntimeState 应覆盖空页面、坏 JSON 与异常降级', async () => {
    const extractor = createExtractor();

    assert.deepEqual(await extractor._readSerializableRuntimeState(null), {
      locationHref: '',
      pageVar: null,
      pageOutrightsVar: null,
    });

    const invalidState = await extractor._readSerializableRuntimeState(createDomPage('<html></html>', {
      pageVar: '{bad-json',
      pageOutrightsVar: ' ',
    }));
    assert.equal(invalidState.pageVar, null);
    assert.equal(invalidState.pageOutrightsVar, null);

    const failedState = await extractor._readSerializableRuntimeState({
      async evaluate() {
        throw new Error('runtime probe failed');
      },
    });
    assert.deepEqual(failedState, {
      locationHref: '',
      pageVar: null,
      pageOutrightsVar: null,
    });
    assert.equal(extractor.__events.debug.at(-1).event, 'pure_runtime_state_probe_failed');
  });

  it('_readPageHtml 在 page.content 失败后应回退到 documentElement.outerHTML', async () => {
    const extractor = createExtractor();

    const html = await extractor._readPageHtml(createDomPage('<html><body><div id="app"></div></body></html>', {}, {
      async content() {
        throw new Error('content failed');
      },
    }));

    assert.match(html, /<div id="app"><\/div>/);
    assert.equal(extractor.__events.debug[0].event, 'pure_runtime_page_content_failed');
  });

  it('_readPageHtml 应覆盖空页面、无 evaluate 与 evaluate 失败分支', async () => {
    const extractor = createExtractor();

    assert.equal(await extractor._readPageHtml(null), '');
    assert.equal(await extractor._readPageHtml({}), '');
    assert.equal(await extractor._readPageHtml({
      async evaluate() {
        throw new Error('html probe failed');
      },
    }), '');
    assert.equal(extractor.__events.debug.at(-1).event, 'pure_runtime_page_html_failed');
  });

  it('_createPageBoundModuleLoader 应支持页面内抓取、manifest remap 与 unavailable 终态', async () => {
    const baseUrl = 'https://www.oddsportal.com/football/usa/mls/';
    const fetchStub = installFetchStub({
      'https://www.oddsportal.com/build/assets/direct-page.js': {
        text: 'export const direct = true;',
      },
      'https://www.oddsportal.com/build/assets/chunk-live-123456.js': {
        ok: false,
        status: 404,
        text: '',
      },
      'https://www.oddsportal.com/build/assets/chunk-live-abcdef.js': {
        text: 'export const helper = true;',
      },
    });
    const extractor = createExtractor();

    try {
      const pageLoader = extractor._createPageBoundModuleLoader(
        createDomPage('<html><body></body></html>', {}, { baseUrl }),
        baseUrl
      );
      const pageSource = await pageLoader('/build/assets/direct-page.js');
      assert.equal(pageSource, 'export const direct = true;');

      const remapLoader = extractor._createPageBoundModuleLoader(null, baseUrl, {
        manifestAssetMap: new Map([
          ['chunk', 'https://www.oddsportal.com/build/assets/chunk-live-abcdef.js'],
        ]),
      });
      const remapped = await remapLoader('/build/assets/chunk-live-123456.js');
      assert.equal(remapped, 'export const helper = true;');
      assert.equal(extractor.__events.info[0].event, 'app_script_manifest_remap_hit');

      await assert.rejects(
        remapLoader('/build/assets/unknown-bundle.js'),
        /PURE_RUNTIME_PAGE_UNAVAILABLE/
      );
    } finally {
      fetchStub.restore();
    }
  });

  it('_extractFromPureRuntime 应构建可调用的包装 decrypt 函数并透传元信息', async () => {
    const extractor = createExtractor({
      async _readSerializableRuntimeState() {
        return {
          locationHref: 'https://www.oddsportal.com/football/usa/mls/',
          pageVar: { otCode: 'MLS' },
          pageOutrightsVar: { id: 'out-1' },
        };
      },
      async _readPageHtml() {
        return '<html><body>runtime</body></html>';
      },
      async _resolveLiveAppScript() {
        return {
          appScriptUrl: 'https://www.oddsportal.com/build/assets/app-live.js',
          bundleSource: 'export const ai = () => "{}";',
          manifestAssetMap: new Map(),
        };
      },
    });
    const originalLoadFromBundleUrl = ReconPureDecryptor.prototype.loadFromBundleUrl;
    const originalDecrypt = ReconPureDecryptor.prototype.decrypt;
    const originalGetAlgorithmVersion = ReconPureDecryptor.prototype.getAlgorithmVersion;

    ReconPureDecryptor.prototype.loadFromBundleUrl = async function loadFromBundleUrl() {
      this.selectedCandidate = { validated: true };
      this.algorithmVersion = 'pure_ai';
      return async () => '{}';
    };
    ReconPureDecryptor.prototype.decrypt = async function decrypt(payload) {
      return { payload, algorithmVersion: this.algorithmVersion };
    };
    ReconPureDecryptor.prototype.getAlgorithmVersion = function getAlgorithmVersion() {
      return this.algorithmVersion;
    };

    try {
      const wrapped = await extractor._extractFromPureRuntime(
        createDomPage('<html><body></body></html>'),
        'https://www.oddsportal.com/build/assets/app-live.js',
        { primarySample: 'cipher-sample' }
      );

      assert.equal(typeof wrapped, 'function');
      assert.equal(wrapped.__algorithmVersion, 'pure_ai');
      assert.equal(wrapped.__extractMethod, 'pure_runtime');
      assert.deepEqual(await wrapped('cipher:0011'), {
        payload: 'cipher:0011',
        algorithmVersion: 'pure_ai',
      });
    } finally {
      ReconPureDecryptor.prototype.loadFromBundleUrl = originalLoadFromBundleUrl;
      ReconPureDecryptor.prototype.decrypt = originalDecrypt;
      ReconPureDecryptor.prototype.getAlgorithmVersion = originalGetAlgorithmVersion;
    }
  });

  it('_extractFromPureRuntime 应覆盖空输入、空 bundle 与 load 失败分支', async () => {
    const extractor = createExtractor({
      async _readSerializableRuntimeState() {
        return { locationHref: '', pageVar: null, pageOutrightsVar: null };
      },
      async _readPageHtml() {
        return '';
      },
      async _resolveLiveAppScript() {
        return {
          appScriptUrl: 'https://www.oddsportal.com/build/assets/app-live.js',
          bundleSource: '',
          manifestAssetMap: new Map(),
        };
      },
      async _fetchBundleSource() {
        return '';
      },
    });

    assert.equal(await extractor._extractFromPureRuntime(null, 'https://www.oddsportal.com/build/assets/app-live.js'), null);
    assert.equal(await extractor._extractFromPureRuntime(createDomPage('<html></html>'), ''), null);
    assert.equal(await extractor._extractFromPureRuntime(createDomPage('<html></html>'), 'https://www.oddsportal.com/build/assets/app-live.js'), null);

    const originalLoadFromBundleUrl = ReconPureDecryptor.prototype.loadFromBundleUrl;
    ReconPureDecryptor.prototype.loadFromBundleUrl = async function loadFromBundleUrl() {
      throw new Error('load failed');
    };

    try {
      const failingExtractor = createExtractor({
        async _readSerializableRuntimeState() {
          return { locationHref: 'https://www.oddsportal.com/football/usa/mls/', pageVar: null, pageOutrightsVar: null };
        },
        async _readPageHtml() {
          return '<html></html>';
        },
        async _resolveLiveAppScript() {
          return {
            appScriptUrl: 'https://www.oddsportal.com/build/assets/app-live.js',
            bundleSource: 'export const ai = () => "{}";',
            manifestAssetMap: new Map(),
          };
        },
      });

      assert.equal(
        await failingExtractor._extractFromPureRuntime(createDomPage('<html></html>'), 'https://www.oddsportal.com/build/assets/app-live.js'),
        null
      );
      assert.equal(failingExtractor.__events.warn[0].event, 'pure_runtime_extraction_failed');
    } finally {
      ReconPureDecryptor.prototype.loadFromBundleUrl = originalLoadFromBundleUrl;
    }
  });

  it('_extractFromInlineScripts 应识别 inline decryptor，并在后续调用时执行页面内函数', async () => {
    const extractor = createExtractor();
    const page = createDomPage(
      '<html><body><script>window.inlineDecode = function(data) { return "decoded:" + data; };</script></body></html>',
      {
        inlineDecode(data) {
          return `decoded:${data}`;
        },
      }
    );

    const decryptFn = await extractor._extractFromInlineScripts(page);

    assert.equal(typeof decryptFn, 'function');
    assert.equal(extractor.algorithmVersion, 'inline_inlineDecode');
    assert.equal(await decryptFn('cipher'), 'decoded:cipher');
  });

  it('_extractFromInlineScripts 应覆盖未命中、函数缺失与 page closed 分支', async () => {
    const extractor = createExtractor();
    assert.equal(await extractor._extractFromInlineScripts(createDomPage('<html><body><script>const noop = 1;</script></body></html>')), null);

    const missingFnPage = createDomPage('<html><body><script>window.inlineDecode = function(data) { return data; };</script></body></html>');
    const missingFn = await extractor._extractFromInlineScripts(missingFnPage);
    await assert.rejects(
      missingFn('cipher'),
      /Decryptor function inlineDecode not found/
    );

    const closedExtractor = createExtractor({
      _isPageContextClosedError(error) {
        return error?.message === 'Target page, context or browser has been closed';
      },
    });
    const closedResult = await closedExtractor._extractFromInlineScripts({
      async evaluate() {
        throw new Error('Target page, context or browser has been closed');
      },
    });
    assert.equal(closedResult, null);
    assert.equal(closedExtractor.__events.debug[0].event, 'inline_script_extraction_skipped_page_closed');
  });

  it('_extractFromGlobalScope 应优先匹配常见名称并返回页面绑定函数', async () => {
    const extractor = createExtractor();
    const page = createDomPage('<html><body></body></html>', {
      decodePayload(data) {
        return `global:${data}`;
      },
    });

    const decryptFn = await extractor._extractFromGlobalScope(page);

    assert.equal(typeof decryptFn, 'function');
    assert.equal(extractor.algorithmVersion, 'global_decodePayload');
    assert.equal(await decryptFn('cipher'), 'global:cipher');
  });

  it('_extractFromGlobalScope 应覆盖 heuristic、未命中与 page closed 分支', async () => {
    const extractor = createExtractor();
    const heuristicPage = createDomPage('<html><body></body></html>', {
      customDecryptPayload(data) {
        return `heuristic:${data}`;
      },
    });
    const heuristicFn = await extractor._extractFromGlobalScope(heuristicPage);
    assert.equal(await heuristicFn('cipher'), 'heuristic:cipher');

    assert.equal(await extractor._extractFromGlobalScope(createDomPage('<html><body></body></html>')), null);

    const closedExtractor = createExtractor({
      _isPageContextClosedError(error) {
        return error?.message === 'Target page, context or browser has been closed';
      },
    });
    const closedResult = await closedExtractor._extractFromGlobalScope({
      async evaluate() {
        throw new Error('Target page, context or browser has been closed');
      },
    });
    assert.equal(closedResult, null);
    assert.equal(closedExtractor.__events.debug[0].event, 'global_scope_extraction_skipped_page_closed');
  });
});
