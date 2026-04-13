'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');

const { ReconStealthProvider } = require('../../src/infrastructure/recon/services/ReconStealthProvider');
const { getAntiDetectionScripts } = require('../../src/infrastructure/network/enhanced_stealth_config');

function createBrowserLikeContext() {
  const navigator = {
    permissions: {
      query(parameters) {
        return Promise.resolve({ state: parameters?.name === 'notifications' ? 'default' : 'prompt' });
      }
    },
    connection: {}
  };
  const window = {
    navigator,
    chrome: { runtime: {} },
    JSON
  };

  function WebGLRenderingContext() {}
  WebGLRenderingContext.prototype.getParameter = function getParameter() {
    return 0;
  };

  function WebGL2RenderingContext() {}
  WebGL2RenderingContext.prototype.getParameter = function getParameter() {
    return 0;
  };

  function HTMLCanvasElement() {}
  HTMLCanvasElement.prototype.toDataURL = function toDataURL() {
    return 'data:image/png;base64,';
  };
  HTMLCanvasElement.prototype.toBlob = function toBlob() {
    return undefined;
  };
  HTMLCanvasElement.prototype.getContext = function getContext() {
    return {
      getImageData() {
        return { data: new Uint8ClampedArray(8) };
      },
      putImageData() {}
    };
  };

  function AudioBuffer() {}
  AudioBuffer.prototype.getChannelData = function getChannelData() {
    return new Float32Array(16);
  };

  return {
    navigator,
    window,
    Notification: { permission: 'default' },
    WebGLRenderingContext,
    WebGL2RenderingContext,
    HTMLCanvasElement,
    AudioBuffer,
    Uint8ClampedArray,
    Float32Array,
    Object,
    Array,
    String,
    Number,
    Boolean,
    Date,
    Math,
    JSON,
    Proxy,
    Promise,
    Function,
    Intl,
    console: {
      log() {},
      warn() {},
      error() {}
    }
  };
}

function runInContext(source, context) {
  return vm.runInNewContext(source, context);
}

test('ReconStealthProvider 应将关键 navigator 属性定义为 configurable', async () => {
  const provider = new ReconStealthProvider();
  let captured = null;
  const page = {
    async addInitScript(fn, args) {
      captured = { fn, args };
    }
  };

  await provider.applyStealthFingerprint(page, true, {
    hardwareConcurrency: 12,
    deviceMemory: 16,
    platform: 'Win32',
    language: 'en-US',
    languages: ['en-US', 'en']
  });

  assert.ok(captured);

  const context = createBrowserLikeContext();
  runInContext(`(${captured.fn.toString()})(${JSON.stringify(captured.args)})`, context);

  const descriptor = Object.getOwnPropertyDescriptor(context.navigator, 'hardwareConcurrency');
  assert.equal(context.navigator.hardwareConcurrency, 12);
  assert.equal(context.navigator.deviceMemory, 16);
  assert.equal(context.navigator.platform, 'Win32');
  assert.equal(descriptor?.configurable, true);
});

test('增强 stealth 脚本遇到不可重定义的 hardwareConcurrency 时不应抛错', () => {
  const context = createBrowserLikeContext();
  Object.defineProperty(context.navigator, 'hardwareConcurrency', {
    get: () => 4,
    configurable: false
  });

  const script = getAntiDetectionScripts({
    workerId: 3,
    fingerprintSeed: 'seed-redefine-guard',
    hardwareConcurrency: 16,
    deviceMemory: 8,
    platform: 'Win32'
  });

  assert.doesNotThrow(() => {
    runInContext(script, context);
  });
  assert.equal(context.navigator.hardwareConcurrency, 4);
});
