'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const { ReconDecryptor } = require('../../src/infrastructure/recon/ReconDecryptor');
const { findLatestAppScript } = require('../../src/infrastructure/recon/services/ReconDecryptorSourceExtractor');

const fixturesDir = path.resolve(__dirname, '../fixtures/recon_decryptor');

function stubLiveAppScriptResolution(decryptor, overrides = {}) {
  decryptor._resolveLiveAppScript = async (_page, appScriptUrl) => ({
    appScriptUrl,
    bundleSource: '',
    manifestAssetMap: new Map(),
    ...overrides
  });
  return decryptor;
}

describe('ReconDecryptor', () => {
  it('页面已关闭时应快速退出，避免记录 decryptor_extraction_failed', async () => {
    const errorEvents = [];

    const decryptor = new ReconDecryptor({
      logger: {
        info() {},
        warn() {},
        debug() {},
        error(event) {
          errorEvents.push(event);
        }
      }
    });

    await assert.rejects(
      decryptor.extractDecryptor({ isClosed: () => true }, 'encrypted-sample'),
      (error) => error?.code === 'PAGE_CONTEXT_CLOSED'
    );

    assert.strictEqual(errorEvents.includes('decryptor_extraction_failed'), false);
  });

  it('样本验证失败时不应接受 app bundle 的未验证候选函数', async () => {
    let evaluateCalls = 0;

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    stubLiveAppScriptResolution(decryptor);
    decryptor._extractFromPureRuntime = async () => null;

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          return '';
        }

        assert.strictEqual(payload.allowBestEffort, false);

        return {
          found: false,
          validated: false
        };
      }
    };

    const result = await decryptor._extractFromAppScript(page, 'encrypted-sample');

    assert.strictEqual(result, null);
    assert.strictEqual(decryptor.getAlgorithmVersion(), null);
    assert.ok(evaluateCalls >= 3);
  });

  it('启用 best-effort 模式时，应允许回退到 ai 导出函数', async () => {
    let evaluateCalls = 0;

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      allowBestEffortCandidate: true
    });
    stubLiveAppScriptResolution(decryptor);

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          return 'export{Y7t as ai};';
        }

        if ((payload?.url || payload?.urls) && Array.isArray(payload?.samplePool)) {
          return {
            found: true,
            name: 'ai',
            type: 'named_export',
            validated: false,
            bestEffort: true
          };
        }

        return '{"d":{"rows":[]}}';
      }
    };

    const result = await decryptor._extractFromAppScript(page, 'encrypted-sample');

    assert.ok(result);
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'app_ai');
    assert.strictEqual(result.__bestEffort, true);
    assert.strictEqual(result.__validated, false);
  });

  it('首样本无效时应复用缓存样本做交叉验证并成功提取', async () => {
    const validSample = Buffer.from('cipher:0011', 'utf8').toString('base64');

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      allowBestEffortCandidate: false,
      sampleCrossValidateCount: 3,
      randomInt: () => 0
    });
    stubLiveAppScriptResolution(decryptor);
    decryptor.rememberSample(validSample);

    let evaluateCalls = 0;
    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          return '';
        }

        assert.ok(Array.isArray(payload.samplePool));
        assert.ok(payload.samplePool.includes(validSample));
        assert.strictEqual(payload.allowBestEffort, false);
        return {
          found: true,
          name: 'ai',
          type: 'named_export',
          validated: true
        };
      }
    };

    const result = await decryptor._extractFromAppScript(
      page,
      'URL:/ajax-sport-country-tournament-archive_/1//X/2025-2026/1/0/ Status: 404'
    );

    assert.ok(result);
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'app_ai');
  });

  it('app script 导入失败时应回退到 pure runtime decryptor', async () => {
    let evaluateCalls = 0;
    const runtimeDecryptFn = async () => '{"d":{"rows":[]}}';
    runtimeDecryptFn.__validated = true;
    runtimeDecryptFn.__bestEffort = false;
    runtimeDecryptFn.__algorithmVersion = 'pure_ai';
    runtimeDecryptFn.__extractMethod = 'pure_runtime';

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    stubLiveAppScriptResolution(decryptor);
    decryptor._extractFromPureRuntime = async () => runtimeDecryptFn;

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          return 'export{Y7t as ai};';
        }

        assert.ok(Array.isArray(payload.urls));
        return {
          found: false,
          validated: false,
          error: 'Failed to fetch dynamically imported module'
        };
      }
    };

    const result = await decryptor._extractFromAppScript(
      page,
      Buffer.from('cipher:0011', 'utf8').toString('base64')
    );

    assert.strictEqual(result, runtimeDecryptFn);
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'pure_ai');
  });

  it('bundle 页面内抓取失败时应回退到 Node fetch', async () => {
    const originalFetch = globalThis.fetch;
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    stubLiveAppScriptResolution(decryptor);

    globalThis.fetch = async (url, options = {}) => {
      assert.strictEqual(url, 'https://www.oddsportal.com/build/assets/app-test.js');
      assert.strictEqual(options.headers.referer, 'https://www.oddsportal.com/football/usa/mls/');
      return {
        ok: true,
        async text() {
          return 'export{Y7t as ai};';
        }
      };
    };

    try {
      const page = {
        url() {
          return 'https://www.oddsportal.com/football/usa/mls/';
        },
        async evaluate() {
          throw new Error('page_fetch_failed');
        }
      };

      const source = await decryptor._fetchBundleSource(
        page,
        'https://www.oddsportal.com/build/assets/app-test.js'
      );

      assert.strictEqual(source, 'export{Y7t as ai};');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('应在页面 app-*.js 失效时回退到根页面 live bundle', async () => {
    const originalFetch = globalThis.fetch;
    const requestedUrls = [];

    globalThis.fetch = async (url) => {
      requestedUrls.push(url);
      if (url === 'https://www.oddsportal.com/football/usa/mls-2025/results/') {
        return {
          ok: true,
          status: 200,
          url,
          async text() {
            return '<html><head><script type="module" src="/build/assets/app-BVYnMZqo.js"></script></head></html>';
          }
        };
      }

      if (url === 'https://www.oddsportal.com/') {
        return {
          ok: true,
          status: 200,
          url,
          async text() {
            return '<html><head><link rel="modulepreload" href="/build/assets/app-JoAS42xl.js"></head></html>';
          }
        };
      }

      if (url === 'https://www.oddsportal.com/build/manifest.json') {
        return {
          ok: true,
          status: 200,
          url,
          async text() {
            return JSON.stringify({
              'resources/js/app.js': {
                file: 'assets/app-BVYnMZqo.js',
                isEntry: true,
                name: 'app'
              }
            });
          }
        };
      }

      if (url === 'https://www.oddsportal.com/build/assets/app-BVYnMZqo.js') {
        return {
          ok: false,
          status: 404,
          url,
          async text() {
            return '';
          }
        };
      }

      if (url === 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js') {
        return {
          ok: true,
          status: 200,
          url,
          async text() {
            return 'export{Y7t as ai};';
          }
        };
      }

      throw new Error(`Unexpected URL: ${url}`);
    };

    try {
      const resolution = await findLatestAppScript(
        'https://www.oddsportal.com/football/usa/mls-2025/results/',
        {
          logger: { info() {}, warn() {}, error() {}, debug() {} },
          traceId: 'trace-app-script-test',
          allowRootFallback: true,
          headers: {
            referer: 'https://www.oddsportal.com/football/usa/mls-2025/results/'
          }
        }
      );

      assert.strictEqual(
        resolution.appScriptUrl,
        'https://www.oddsportal.com/build/assets/app-JoAS42xl.js'
      );
      assert.strictEqual(resolution.discoverySource, 'root_html');
      assert.strictEqual(resolution.bundleSource, 'export{Y7t as ai};');
      assert.ok(requestedUrls.includes('https://www.oddsportal.com/build/assets/app-BVYnMZqo.js'));
      assert.ok(requestedUrls.includes('https://www.oddsportal.com/build/assets/app-JoAS42xl.js'));
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('module 页面内抓取失败时应回退到 Node fetch', async () => {
    const originalFetch = globalThis.fetch;
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    globalThis.fetch = async (url, options = {}) => {
      assert.strictEqual(url, 'https://www.oddsportal.com/build/assets/CountriesLeagues-BRjH3qxG.js');
      assert.strictEqual(options.headers.referer, 'https://www.oddsportal.com/football/usa/mls/');
      return {
        ok: true,
        async text() {
          return 'export const CountriesLeagues = {};';
        }
      };
    };

    try {
      const page = {
        async evaluate() {
          throw new Error('module_fetch_failed');
        }
      };

      const loadModule = decryptor._createPageBoundModuleLoader(
        page,
        'https://www.oddsportal.com/football/usa/mls/'
      );

      const source = await loadModule('/build/assets/CountriesLeagues-BRjH3qxG.js');

      assert.strictEqual(source, 'export const CountriesLeagues = {};');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('页面绑定 loader 回跳旧 app bundle 时应重映射到 live bundle', async () => {
    const originalFetch = globalThis.fetch;
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    const requestedUrls = [];

    globalThis.fetch = async (url, options = {}) => {
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
      const page = {
        async evaluate() {
          throw new Error('module_fetch_failed');
        }
      };

      const loadModule = decryptor._createPageBoundModuleLoader(
        page,
        'https://www.oddsportal.com/football/usa/mls/',
        {
          entryBundleUrl: 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js'
        }
      );

      const source = await loadModule('/build/assets/app-BVYnMZqo.js');

      assert.strictEqual(source, 'export const ai = (value) => value;');
      assert.strictEqual(requestedUrls.length, 2);
      assert.strictEqual(requestedUrls[1].url, 'https://www.oddsportal.com/build/assets/app-JoAS42xl.js');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it('样本本身是伪 404 payload 时，不应启用 best-effort 回退', async () => {
    let evaluateCalls = 0;
    const invalidPayload = fs.readFileSync(path.join(fixturesDir, 'payload_invalid_404.txt'), 'utf8');

    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      allowBestEffortCandidate: true
    });
    stubLiveAppScriptResolution(decryptor);

    const page = {
      async evaluate(_fn, payload) {
        evaluateCalls++;
        if (evaluateCalls === 1) {
          return 'https://www.oddsportal.com/build/assets/app-test.js';
        }

        if (evaluateCalls === 2) {
          assert.strictEqual(payload.allowBestEffort, false);
          assert.ok(Array.isArray(payload.candidateNames));
          assert.ok(payload.candidateNames.includes('ai'));
          return {
            found: false,
            validated: false
          };
        }

        return '';
      }
    };

    const result = await decryptor._extractFromAppScript(page, invalidPayload);

    assert.strictEqual(result, null);
    assert.strictEqual(decryptor.getAlgorithmVersion(), null);
  });

  it('malformed payload 应在调用解密函数前 fail-fast', async () => {
    let decryptCalls = 0;
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    decryptor.decryptFn = async () => {
      decryptCalls++;
      return '{}';
    };
    decryptor.algorithmVersion = 'app_ai';

    await assert.rejects(
      decryptor.decrypt('URL:/ajax-sport-country-tournament-archive_/1//X/2025-2026/1/ Status: 404'),
      (error) => {
        assert.strictEqual(error.code, 'INVALID_ENCRYPTED_PAYLOAD');
        return true;
      }
    );

    assert.strictEqual(decryptCalls, 0);
  });

  it('应优先从 bundle 函数体特征中识别 ai 解密导出', () => {
    const bundleExcerpt = fs.readFileSync(path.join(fixturesDir, 'oddsportal_bundle_excerpt.js'), 'utf8');
    const decryptor = new ReconDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const candidates = decryptor._extractFromBundle(bundleExcerpt);

    assert.ok(Array.isArray(candidates));
    assert.strictEqual(candidates[0], 'ai');
  });
});
