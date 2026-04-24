'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/network/StealthFingerprint.js');

function loadStealthFingerprint() {
  delete require.cache[MODULE_PATH];
  return require(MODULE_PATH);
}

function mockRandomSequence(values) {
  let index = 0;
  return () => {
    const value = values[Math.min(index, values.length - 1)];
    index += 1;
    return value;
  };
}

describe('src/infrastructure/network/StealthFingerprint', () => {
  const originalRandom = Math.random;

  afterEach(() => {
    Math.random = originalRandom;
    delete require.cache[MODULE_PATH];
  });

  test('应返回确定的随机 UA、视口与深度隐身配置', () => {
    const fingerprint = loadStealthFingerprint();

    Math.random = mockRandomSequence([0, 0.999]);
    assert.strictEqual(fingerprint.getRandomUA(), fingerprint.GHOST_UA_POOL[0]);
    assert.deepStrictEqual(
      fingerprint.getRandomViewport(),
      fingerprint.GHOST_VIEWPORTS.at(-1),
    );

    const config = fingerprint.generateStealthConfig(3);
    assert.strictEqual(config.userAgent, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36');
    assert.deepStrictEqual(config.viewport, { width: 1940, height: 1095 });
    assert.strictEqual(config.hardwareConcurrency, 16);
    assert.strictEqual(config.deviceMemory, 8);
    assert.deepStrictEqual(config.webgl, {
      vendor: 'Google Inc. (Intel)',
      renderer: fingerprint.WEBGL_RENDERER_POOL[5],
    });
    assert.ok(config.fonts.includes('Segoe UI'));
  });

  test('generateStealthHeaders 应覆盖固定指纹、Chrome、Edge 与非 Chromium 分支', () => {
    const fingerprint = loadStealthFingerprint();

    const fixed = fingerprint.generateStealthHeaders(true);
    assert.deepStrictEqual(fixed.userAgent, fingerprint.FIXED_FINGERPRINT.userAgent);
    assert.deepStrictEqual(fixed.viewport, fingerprint.FIXED_FINGERPRINT.viewport);
    assert.strictEqual(fixed.locale, 'en-US');
    assert.strictEqual(fixed.timezoneId, 'Europe/London');
    assert.strictEqual(typeof fixed.hardwareConcurrency, 'number');
    assert.strictEqual(typeof fixed.deviceMemory, 'number');
    assert.ok(fixed.webgl.renderer.includes('ANGLE'));
    assert.strictEqual(fixed.extraHTTPHeaders['sec-ch-ua-platform'], '"Windows"');

    const seeded = fingerprint.generateStealthHeaders({ port: 7895, useFixed: true });
    const seededConfig = fingerprint.generateStealthConfig(7895);
    assert.strictEqual(seeded.hardwareConcurrency, seededConfig.hardwareConcurrency);
    assert.strictEqual(seeded.deviceMemory, seededConfig.deviceMemory);
    assert.deepStrictEqual(seeded.webgl, seededConfig.webgl);

    Math.random = mockRandomSequence([0, 0]);
    const chrome = fingerprint.generateStealthHeaders(false);
    assert.ok(chrome.userAgent.includes('Chrome/133.0.0.0'));
    assert.strictEqual(chrome.extraHTTPHeaders['sec-ch-ua-platform'], '"Windows"');
    assert.ok(chrome.extraHTTPHeaders['sec-ch-ua'].includes('Google Chrome'));

    Math.random = mockRandomSequence([0.6, 0.2]);
    const edge = fingerprint.generateStealthHeaders(false);
    assert.ok(edge.userAgent.includes('Edg/132.0.0.0'));
    assert.ok(edge.extraHTTPHeaders['sec-ch-ua'].includes('Microsoft Edge'));

    Math.random = mockRandomSequence([0.75, 0.4]);
    const firefox = fingerprint.generateStealthHeaders(false);
    assert.ok(firefox.userAgent.includes('Firefox/134.0'));
    assert.deepStrictEqual(firefox.extraHTTPHeaders, {});
  });
});
