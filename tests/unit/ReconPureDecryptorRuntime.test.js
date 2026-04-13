'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

const { ReconPureDecryptor } = require('../../src/infrastructure/recon/services/ReconPureDecryptor');

const GLOBAL_KEYS = [
  'window',
  'self',
  'navigator',
  'location',
  'document',
  'history',
  'performance',
  'localStorage',
  'sessionStorage',
  'pageVar',
  'pageOutrightsVar',
  'Node',
  'Element',
  'HTMLElement',
  'SVGElement',
  'MutationObserver',
  'ResizeObserver',
  'IntersectionObserver',
  'Event',
  'CustomEvent',
  'Image',
  'addEventListener',
  'removeEventListener',
  'dispatchEvent',
  'requestAnimationFrame',
  'cancelAnimationFrame',
  'matchMedia',
  'getComputedStyle',
  'atob',
  'btoa'
];

function snapshotGlobals() {
  return new Map(GLOBAL_KEYS.map((key) => [key, Object.prototype.hasOwnProperty.call(globalThis, key)
    ? globalThis[key]
    : Symbol.for('missing')]));
}

function restoreGlobals(snapshot) {
  for (const [key, value] of snapshot.entries()) {
    if (value === Symbol.for('missing')) {
      delete globalThis[key];
    } else {
      const descriptor = Object.getOwnPropertyDescriptor(globalThis, key);
      if (!descriptor || descriptor.writable || descriptor.set) {
        globalThis[key] = value;
      } else {
        Object.defineProperty(globalThis, key, {
          value,
          configurable: true,
          enumerable: descriptor.enumerable ?? true,
          writable: true
        });
      }
    }
  }
}

function unsetGlobalIfPossible(key) {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, key);
  if (!descriptor) {
    return;
  }

  try {
    if (descriptor.configurable) {
      delete globalThis[key];
      return;
    }

    if (descriptor.writable || descriptor.set) {
      globalThis[key] = undefined;
    }
  } catch {
    // 某些运行时内建属性不可重置，测试只在可安全覆盖时触发 fallback 分支
  }
}

describe('ReconPureDecryptorRuntime', () => {
  let globalSnapshot = null;

  afterEach(() => {
    if (globalSnapshot) {
      restoreGlobals(globalSnapshot);
      globalSnapshot = null;
    }
  });

  it('测试 helper 应覆盖 restoreGlobals 与 unsetGlobalIfPossible 的防御分支', () => {
    globalSnapshot = snapshotGlobals();

    Object.defineProperty(globalThis, 'navigator', {
      value: { language: 'de-DE' },
      configurable: true,
      enumerable: true,
      writable: false
    });
    restoreGlobals(new Map([
      ['navigator', { language: 'en-US' }]
    ]));
    assert.strictEqual(globalThis.navigator.language, 'en-US');

    Object.defineProperty(globalThis, 'pageVar', {
      value: { locale: 'fr' },
      configurable: true,
      enumerable: true,
      writable: true
    });
    unsetGlobalIfPossible('pageVar');
    assert.strictEqual(globalThis.pageVar, undefined);

    Object.defineProperty(globalThis, 'pageOutrightsVar', {
      configurable: true,
      enumerable: true,
      get() {
        return { archive: false };
      },
      set() {
        throw new Error('locked-setter');
      }
    });
    assert.doesNotThrow(() => unsetGlobalIfPossible('pageOutrightsVar'));
  });

  it('应补齐浏览器沙盒所需的全局对象与 #app 根节点', () => {
    globalSnapshot = snapshotGlobals();

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    decryptor.entryUrl = 'https://www.oddsportal.com/football/usa/mls-2025/results/';
    decryptor._installBrowserLikeGlobals({
      pageVar: {
        otCode: 'xbsqV0go'
      }
    });

    assert.strictEqual(typeof globalThis.document.addEventListener, 'function');
    assert.strictEqual(typeof globalThis.history.pushState, 'function');
    assert.strictEqual(typeof globalThis.MutationObserver, 'function');
    assert.strictEqual(globalThis.pageVar.locale, 'en');

    const appRoot = globalThis.document.querySelector('#app');
    assert.ok(appRoot);
    assert.strictEqual(typeof appRoot.setAttribute, 'function');
    assert.strictEqual(typeof appRoot.insertBefore, 'function');
  });

  it('应为语言动态导入准备本地 fallback 模板', async () => {
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-runtime-'));

    await decryptor._ensureLanguageFallbackModules(rootDir);

    const langDir = path.join(rootDir, 'build', 'assets', 'resources', 'lang');
    const english = await fs.readFile(path.join(langDir, 'en.json'), 'utf8');
    const fallback = await fs.readFile(path.join(langDir, 'undefined.json'), 'utf8');

    assert.strictEqual(english, '{}');
    assert.strictEqual(fallback, '{}');
  });

  it('installGlobal 遇到只读全局属性时应通过 defineProperty 强制覆盖', () => {
    globalSnapshot = snapshotGlobals();

    Object.defineProperty(globalThis, 'navigator', {
      value: { language: 'fr-FR' },
      configurable: true,
      enumerable: true,
      writable: false
    });

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    decryptor.entryUrl = 'https://www.oddsportal.com/football/spain/laliga/results/';
    decryptor._installBrowserLikeGlobals();

    const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'navigator');
    assert.ok(descriptor);
    assert.strictEqual(descriptor.writable, true);
    assert.strictEqual(descriptor.configurable, true);
    assert.strictEqual(globalThis.navigator.language, 'en-US');
    assert.strictEqual(typeof globalThis.navigator.userAgent, 'string');
  });

  it('浏览器沙盒 stub 应提供 storage、event、DOM 与 history 能力', () => {
    globalSnapshot = snapshotGlobals();

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    decryptor.entryUrl = 'https://www.oddsportal.com/football/usa/mls/results/';
    const runtimeGlobals = decryptor._createDefaultRuntimeGlobals({
      pageVar: {
        locale: '',
        myBookmakers: 'invalid',
        userData: null,
        myot: '',
        bookiehash: 'BOOK'
      }
    });

    assert.deepStrictEqual(runtimeGlobals.pageVar.myBookmakers, []);
    assert.deepStrictEqual(runtimeGlobals.pageVar.userData.myBookmakers, []);
    assert.strictEqual(runtimeGlobals.pageVar.myot, 'BOOK');
    assert.strictEqual(runtimeGlobals.pageVar.bookiehash, 'BOOK');
    assert.strictEqual(runtimeGlobals.pageVar.locale, '');

    const fallbackGlobals = decryptor._createDefaultRuntimeGlobals({
      pageVar: {
        locale: '',
        myot: 'MYOT',
        bookiehash: ''
      }
    });
    assert.strictEqual(fallbackGlobals.pageVar.bookiehash, 'MYOT');

    decryptor._installBrowserLikeGlobals({
      pageVar: {
        locale: '',
        myBookmakers: 'invalid',
        userData: null,
        myot: '',
        bookiehash: 'BOOK'
      }
    });

    globalThis.localStorage.setItem('token', 123);
    assert.strictEqual(globalThis.localStorage.getItem('token'), '123');
    globalThis.localStorage.removeItem('token');
    assert.strictEqual(globalThis.localStorage.getItem('token'), null);
    globalThis.sessionStorage.setItem('sid', 'abc');
    globalThis.sessionStorage.clear();
    assert.strictEqual(globalThis.sessionStorage.getItem('sid'), null);

    const button = globalThis.document.createElement('button');
    let clickCount = 0;
    const onClick = () => {
      clickCount += 1;
    };
    button.addEventListener('', onClick);
    button.addEventListener('noop', null);
    button.addEventListener('click', onClick);
    button.addEventListener('click', () => {
      throw new Error('listener boom');
    });
    assert.strictEqual(button.dispatchEvent(new globalThis.Event('click')), true);
    assert.strictEqual(button.dispatchEvent({}), true);
    button.removeEventListener('click', onClick);
    button.removeEventListener('missing', onClick);
    button.dispatchEvent(new globalThis.Event('click'));
    assert.strictEqual(clickCount, 1);

    button.classList.add('alpha', 'beta');
    assert.strictEqual(button.classList.contains('alpha'), true);
    assert.strictEqual(button.classList.toggle('forced', true), true);
    assert.strictEqual(button.classList.toggle('beta', false), false);
    assert.strictEqual(button.classList.toggle('gamma'), true);
    assert.strictEqual(button.classList.toggle('gamma'), false);
    button.classList.remove('alpha');
    assert.strictEqual(button.classList.contains('alpha'), false);
    assert.match(button.classList.toString(), /forced/);

    const childA = globalThis.document.createElement('span');
    const childB = globalThis.document.createElement('strong');
    const childC = globalThis.document.createElement('small');
    button.appendChild(childA);
    button.prepend(childB);
    button.append(childC);
    assert.strictEqual(button.appendChild(null), null);
    assert.strictEqual(button.children.includes(childA), true);
    assert.strictEqual(button.children.includes(childB), true);
    assert.strictEqual(button.children.includes(childC), true);
    assert.strictEqual(button.childNodes.includes(childB), true);
    assert.strictEqual(button.firstChild, button.children[0]);
    assert.strictEqual(button.lastChild, button.children[button.children.length - 1]);
    assert.strictEqual(button.contains(childA), true);
    button.insertBefore(globalThis.document.createElement('em'));
    assert.ok(button.children.length >= 3);

    const replacement = globalThis.document.createElement('i');
    button.replaceChild(replacement, childA);
    assert.strictEqual(button.contains(replacement), true);
    button.removeChild(replacement);
    assert.strictEqual(button.contains(replacement), false);

    button.setAttribute('data-role', 'action');
    assert.strictEqual(button.getAttribute('data-role'), 'action');
    assert.strictEqual(button.hasAttribute('data-role'), true);
    button.removeAttribute('data-role');
    assert.strictEqual(button.hasAttribute('data-role'), false);

    assert.ok(button.cloneNode());
    assert.ok(button.attachShadow());
    assert.strictEqual(button.closest('.anything'), button);
    assert.strictEqual(button.matches('.anything'), false);
    assert.strictEqual(typeof button.querySelector('.anything').appendChild, 'function');
    assert.deepStrictEqual(button.querySelectorAll('.anything'), []);
    assert.strictEqual(button.getRootNode(), globalThis.document);
    button.focus();
    button.blur();
    button.click();
    button.before();
    button.after();

    const removableParent = globalThis.document.createElement('section');
    removableParent.appendChild(button);
    button.remove();
    assert.strictEqual(removableParent.contains(button), false);

    assert.ok(globalThis.document.getElementById('app'));
    assert.strictEqual(globalThis.document.getElementsByTagName('html')[0], globalThis.document.documentElement);
    assert.strictEqual(globalThis.document.getElementsByTagName('head')[0], globalThis.document.head);
    assert.strictEqual(globalThis.document.getElementsByTagName('body')[0], globalThis.document.body);
    assert.deepStrictEqual(globalThis.document.getElementsByTagName('section'), []);
    assert.strictEqual(globalThis.document.querySelector('#app'), globalThis.document.getElementById('app'));
    assert.strictEqual(globalThis.document.querySelector('[data-app="true"]'), globalThis.document.getElementById('app'));
    assert.strictEqual(globalThis.document.querySelector('main'), globalThis.document.getElementById('app'));
    assert.strictEqual(globalThis.document.querySelector('html'), globalThis.document.documentElement);
    assert.strictEqual(globalThis.document.querySelector('head'), globalThis.document.head);
    assert.strictEqual(typeof globalThis.document.querySelector('.missing-node').appendChild, 'function');
    assert.strictEqual(globalThis.document.querySelectorAll('#app').length, 1);
    assert.deepStrictEqual(globalThis.document.querySelectorAll('.missing'), []);
    assert.deepStrictEqual(globalThis.document.getElementsByClassName('missing'), []);
    assert.strictEqual(globalThis.document.createTextNode('hello').textContent, 'hello');
    assert.strictEqual(globalThis.document.createComment('note').textContent, 'note');
    assert.strictEqual(globalThis.document.createElementNS('svg', 'circle').tagName, 'CIRCLE');
    globalThis.document.cookie = 'session=active; Path=/';
    assert.match(globalThis.document.cookie, /session=active/);

    globalThis.history.pushState({ step: 1 }, '', '/football/spain/laliga/results/');
    assert.strictEqual(globalThis.location.pathname, '/football/spain/laliga/results/');
    globalThis.history.replaceState({ step: 2 }, '', '/football/france/ligue-1/results/');
    assert.strictEqual(globalThis.location.pathname, '/football/france/ligue-1/results/');
    globalThis.location.assign('https://www.oddsportal.com/football/germany/bundesliga/results/');
    globalThis.location.replace('https://www.oddsportal.com/football/italy/serie-a/results/');
    globalThis.location.reload();
    assert.strictEqual(
      globalThis.location.toString(),
      'https://www.oddsportal.com/football/italy/serie-a/results/'
    );

    const media = globalThis.matchMedia('(min-width: 1px)');
    media.addListener(() => {});
    media.removeListener(() => {});
    media.addEventListener('change', () => {});
    media.removeEventListener('change', () => {});
    assert.strictEqual(media.dispatchEvent({ type: 'change' }), true);
    assert.strictEqual(media.media, '(min-width: 1px)');
    assert.strictEqual(globalThis.getComputedStyle(button).getPropertyValue('color'), '');
    assert.deepStrictEqual(globalThis.performance.getEntriesByType('resource'), []);

    const mutationObserver = new globalThis.MutationObserver(() => {});
    mutationObserver.observe(button);
    mutationObserver.disconnect();
    assert.deepStrictEqual(mutationObserver.takeRecords(), []);

    const resizeObserver = new globalThis.ResizeObserver(() => {});
    resizeObserver.observe(button);
    resizeObserver.unobserve(button);
    resizeObserver.disconnect();

    const intersectionObserver = new globalThis.IntersectionObserver(() => {});
    intersectionObserver.observe(button);
    intersectionObserver.unobserve(button);
    intersectionObserver.disconnect();
    assert.deepStrictEqual(intersectionObserver.takeRecords(), []);

    const customEvent = new globalThis.CustomEvent('demo', { detail: 7 });
    assert.strictEqual(customEvent.type, 'demo');
    assert.strictEqual(customEvent.detail, 7);

    const image = new globalThis.Image();
    image.src = 'asset.png';
    assert.strictEqual(image.src, 'asset.png');

    assert.strictEqual(globalThis.atob(globalThis.btoa('codex')), 'codex');
    assert.strictEqual(globalThis.pageVar.myBookmakers, 'invalid');
    assert.strictEqual(globalThis.pageVar.userData, null);
    assert.strictEqual(globalThis.pageVar.myot, '');
    assert.strictEqual(globalThis.pageVar.bookiehash, 'BOOK');
    assert.strictEqual(globalThis.pageVar.locale, '');
  });

  it('缺失浏览器全局时应安装 fallback 对象并回填 pageVar/pageOutrightsVar', async () => {
    globalSnapshot = snapshotGlobals();

    for (const key of [
      'crypto',
      'window',
      'self',
      'localStorage',
      'sessionStorage',
      'addEventListener',
      'removeEventListener',
      'dispatchEvent',
      'requestAnimationFrame',
      'cancelAnimationFrame',
      'MutationObserver',
      'ResizeObserver',
      'IntersectionObserver',
      'Event',
      'CustomEvent',
      'Image',
      'atob',
      'btoa',
      'matchMedia',
      'getComputedStyle'
    ]) {
      unsetGlobalIfPossible(key);
    }

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });
    decryptor.entryUrl = 'https://www.oddsportal.com/football/netherlands/eredivisie/results/';

    await decryptor._ensureLanguageFallbackModules();
    decryptor._installBrowserLikeGlobals({
      pageVar: null,
      pageOutrightsVar: null
    });

    assert.ok(globalThis.crypto);
    assert.strictEqual(globalThis.window, globalThis);
    assert.strictEqual(globalThis.self, globalThis);
    assert.strictEqual(typeof globalThis.localStorage.getItem, 'function');
    assert.strictEqual(typeof globalThis.sessionStorage.getItem, 'function');
    assert.strictEqual(typeof globalThis.MutationObserver, 'function');
    assert.strictEqual(typeof globalThis.ResizeObserver, 'function');
    assert.strictEqual(typeof globalThis.IntersectionObserver, 'function');
    assert.strictEqual(typeof globalThis.Event, 'function');
    assert.strictEqual(typeof globalThis.CustomEvent, 'function');
    assert.strictEqual(typeof globalThis.Image, 'function');
    assert.strictEqual(globalThis.atob(globalThis.btoa('fallback')), 'fallback');
    assert.strictEqual(globalThis.pageVar.locale, 'en');
    assert.strictEqual(globalThis.pageOutrightsVar.archive, true);
    assert.strictEqual(globalThis.dispatchEvent({ type: 'noop' }), true);
    assert.doesNotThrow(() => globalThis.addEventListener('noop', () => {}));
    assert.doesNotThrow(() => globalThis.removeEventListener('noop', () => {}));
    assert.doesNotThrow(() => globalThis.history.back());
    assert.doesNotThrow(() => globalThis.history.forward());
    assert.doesNotThrow(() => globalThis.history.go(-1));
    assert.doesNotThrow(() => globalThis.performance.mark('bootstrap'));
    assert.doesNotThrow(() => globalThis.performance.measure('bootstrap'));

    const fallbackEvent = new globalThis.Event('fallback', { bubbles: true, composed: true });
    const fallbackCustomEvent = new globalThis.CustomEvent('fallback-custom', {
      detail: 42,
      bubbles: true
    });
    assert.strictEqual(fallbackEvent.type, 'fallback');
    assert.strictEqual(fallbackEvent.bubbles, true);
    assert.strictEqual(fallbackEvent.composed, true);
    assert.strictEqual(fallbackCustomEvent.type, 'fallback-custom');
    assert.strictEqual(fallbackCustomEvent.detail, 42);
    assert.strictEqual(fallbackCustomEvent.bubbles, true);

    const frameTimes = [];
    const frameHandle = globalThis.requestAnimationFrame((timestamp) => {
      frameTimes.push(timestamp);
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    globalThis.cancelAnimationFrame(frameHandle);
    assert.ok(frameTimes.length >= 1);
  });

  it('语言 fallback 准备失败时应写 debug 日志而不是抛错', async () => {
    const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-runtime-fail-'));
    const blockingFile = path.join(rootDir, 'not-a-dir');
    const debugCalls = [];
    await fs.writeFile(blockingFile, 'occupied', 'utf8');

    const decryptor = new ReconPureDecryptor({
      logger: {
        info() {},
        warn() {},
        error() {},
        debug(event, payload) {
          debugCalls.push({ event, payload });
        }
      }
    });

    await decryptor._ensureLanguageFallbackModules(blockingFile);

    assert.ok(debugCalls.some(({ event, payload }) =>
      event === 'pure_decryptor_lang_fallback_prepare_failed' &&
      typeof payload?.error === 'string'
    ));
  });

  it('应能从 bundle 下载模块树并装载 pure decryptor 导出', async () => {
    const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-load-'));
    const responses = new Map([
      ['https://cdn.test/build/assets/app.js', [
        'import helper from "./helper.js";',
        'export async function ai(payload) {',
        '  return JSON.stringify({ matches: [helper(payload)] });',
        '}'
      ].join('\n')],
      ['https://cdn.test/build/assets/helper.js', [
        'export default function helper(payload) {',
        '  return { hash: String(payload || "").slice(0, 8) || "fallback1" };',
        '}'
      ].join('\n')]
    ]);

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      moduleRoot: rootDir,
      fetchImpl: async (url) => ({
        ok: responses.has(url),
        status: responses.has(url) ? 200 : 404,
        async text() {
          return responses.get(url);
        }
      })
    });

    const decryptFn = await decryptor.loadFromBundleUrl(
      'https://cdn.test/build/assets/app.js',
      { sampleEncryptedData: Buffer.from('cipher:0011', 'utf8').toString('base64') }
    );

    assert.strictEqual(typeof decryptFn, 'function');
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'pure_ai');
    const decrypted = await decryptor.decrypt(Buffer.from('cipher:0011', 'utf8').toString('base64'));

    assert.deepStrictEqual(decrypted, {
      matches: [{ hash: 'Y2lwaGVy' }]
    });
  });

  it('应支持通过 bundleSource/sourceLoader 与 DOM fallback 解析入口模块', async () => {
    const rootDir = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-dom-load-'));
    const entrySource = [
      'import helper from "./helper.js";',
      'export async function ai(payload) {',
      '  return JSON.stringify({ rows: [helper(payload)] });',
      '}'
    ].join('\n');
    const responses = new Map([
      ['https://www.oddsportal.com/build/assets/helper.js', [
        'export default function helper(payload) {',
        '  return { hash: String(payload || "").slice(0, 8) || "fallback2" };',
        '}'
      ].join('\n')]
    ]);

    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      moduleRoot: rootDir,
      fetchImpl: async () => {
        throw new Error('unexpected fetch');
      }
    });

    const decryptFn = await decryptor.loadFromBundleUrl('', {
      html: '<html lang="en"><head><script type=module src=/build/assets/app.js></script></head></html>',
      bundleSource: entrySource,
      sourceLoader: async (url) => {
        if (!responses.has(url)) {
          throw new Error(`missing:${url}`);
        }
        return responses.get(url);
      },
      sampleEncryptedData: Buffer.from('cipher:0022', 'utf8').toString('base64')
    });

    assert.strictEqual(typeof decryptFn, 'function');
    assert.strictEqual(decryptor.getAlgorithmVersion(), 'pure_ai');
    const decrypted = await decryptor.decrypt(Buffer.from('cipher:0022', 'utf8').toString('base64'));

    assert.deepStrictEqual(decrypted, {
      rows: [{ hash: 'Y2lwaGVy' }]
    });
  });

  it('候选导出选择应跳过异常函数并在无样本时回退首个候选', async () => {
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const validated = await decryptor._selectCandidate({
      broken: async () => {
        throw new Error('broken');
      },
      ai: async () => '{"rows":[]}'
    }, ['broken', 'ai'], 'cipher');
    const fallback = await decryptor._selectCandidate({
      default: async () => ({ ok: true }),
      ai: async () => ({ matches: [] })
    }, ['missing'], null);
    const empty = await decryptor._selectCandidate({}, [], 'cipher');

    assert.strictEqual(validated.name, 'ai');
    assert.strictEqual(validated.validated, true);
    assert.strictEqual(fallback.name, 'ai');
    assert.strictEqual(fallback.validated, false);
    assert.strictEqual(empty, null);
  });

  it('模块 specifier 提取与 fetchText 重试应按预期工作', async () => {
    const seenRequests = [];
    let attempt = 0;
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      fetchRetries: 2,
      fetchImpl: async (url, options) => {
        seenRequests.push({ url, options });
        attempt += 1;
        if (attempt === 1) {
          return {
            ok: false,
            status: 503,
            async text() {
              return '';
            }
          };
        }

        return {
          ok: true,
          status: 200,
          async text() {
            return 'payload';
          }
        };
      }
    });

    const specifiers = decryptor._extractModuleSpecifiers([
      'import helper from "./helper.js";',
      'import "./side-effect.js";',
      'const value = await import("./helper.js");',
      'const lazyOnly = await import("./lazy-only.js");',
      'import data from "../lang/en.json";'
    ].join('\n'));
    const localPath = decryptor._resolveLocalModulePath(
      '/tmp/recon-runtime',
      'https://cdn.test/build/assets/app.js'
    );
    const payload = await decryptor._fetchText('https://cdn.test/build/assets/app.js', {
      Authorization: 'Bearer token'
    });

    assert.deepStrictEqual(specifiers.sort(), ['../lang/en.json', './helper.js', './side-effect.js']);
    assert.strictEqual(localPath, '/tmp/recon-runtime/build/assets/app.js');
    assert.strictEqual(payload, 'payload');
    assert.strictEqual(seenRequests.length, 2);
    assert.strictEqual(seenRequests[0].options.redirect, 'follow');
    assert.deepStrictEqual(seenRequests[0].options.headers, {
      Authorization: 'Bearer token'
    });
  });

  it('fetchText 请求 OddsPortal bundle 时应自动补 referer', async () => {
    let observedHeaders = null;
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      fetchImpl: async (_url, options) => {
        observedHeaders = options.headers;
        return {
          ok: true,
          status: 200,
          async text() {
            return 'payload';
          }
        };
      }
    });
    decryptor.entryUrl = 'https://www.oddsportal.com/football/usa/mls/results/';

    const payload = await decryptor._fetchText(
      'https://www.oddsportal.com/build/assets/app.js',
      { 'user-agent': 'Mozilla/5.0' }
    );

    assert.strictEqual(payload, 'payload');
    assert.strictEqual(observedHeaders.referer, 'https://www.oddsportal.com/football/usa/mls/results/');
    assert.strictEqual(observedHeaders['user-agent'], 'Mozilla/5.0');
  });

  it('materialize/download 应处理入口缺失、visited 命中与非 JS specifier 跳过', async () => {
    const missingRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-missing-'));
    const missingEntryDecryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      moduleRoot: missingRoot
    });
    missingEntryDecryptor._downloadModuleRecursive = async () => {};

    await assert.rejects(
      missingEntryDecryptor._materializeModuleTree('https://cdn.test/build/assets/app.js'),
      /PURE_DECRYPTOR_ENTRY_MISSING/
    );

    const treeRoot = await fs.mkdtemp(path.join(os.tmpdir(), 'recon-pure-tree-'));
    const sourceMap = new Map([
      ['https://cdn.test/build/assets/app.js', [
        'import helper from "./helper.js";',
        'import "./styles.css";',
        'import "external-package";',
        'export default helper;'
      ].join('\n')],
      ['https://cdn.test/build/assets/helper.js', 'export default () => "ok";']
    ]);
    const requests = [];
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      fetchImpl: async (url) => {
        requests.push(url);
        return {
          ok: true,
          status: 200,
          async text() {
            return sourceMap.get(url);
          }
        };
      }
    });

    const visited = new Map();
    const appLocalPath = await decryptor._downloadModuleRecursive(
      'https://cdn.test/build/assets/app.js',
      treeRoot,
      {},
      visited
    );
    const cachedLocalPath = await decryptor._downloadModuleRecursive(
      'https://cdn.test/build/assets/app.js',
      treeRoot,
      {},
      visited
    );

    assert.strictEqual(cachedLocalPath, appLocalPath);
    assert.ok(visited.has('https://cdn.test/build/assets/helper.js'));
    assert.strictEqual(requests.filter((url) => url.endsWith('/app.js')).length, 1);
    assert.strictEqual(requests.includes('https://cdn.test/build/assets/styles.css'), false);
  });

  it('fetchText 在重试耗尽后应抛出最终错误', async () => {
    const decryptor = new ReconPureDecryptor({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      fetchRetries: 2,
      fetchImpl: async () => {
        throw new Error('network-down');
      }
    });

    await assert.rejects(
      decryptor._fetchText('https://cdn.test/build/assets/app.js'),
      /FETCH_FAILED:https:\/\/cdn\.test\/build\/assets\/app\.js:network-down/
    );
  });
});
