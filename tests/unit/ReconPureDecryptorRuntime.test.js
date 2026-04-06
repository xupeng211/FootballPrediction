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
  'pageVar',
  'pageOutrightsVar',
  'MutationObserver',
  'ResizeObserver',
  'IntersectionObserver',
  'Event',
  'CustomEvent',
  'Image',
  'requestAnimationFrame',
  'cancelAnimationFrame',
  'matchMedia',
  'getComputedStyle'
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

describe('ReconPureDecryptorRuntime', () => {
  let globalSnapshot = null;

  afterEach(() => {
    if (globalSnapshot) {
      restoreGlobals(globalSnapshot);
      globalSnapshot = null;
    }
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
});
