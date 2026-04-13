'use strict';

const crypto = require('node:crypto');

const {
  getAntiDetectionScripts,
  getEnhancedStealthConfig
} = require('../../network/enhanced_stealth_config');
const {
  FIXED_FINGERPRINT,
  generateStealthHeaders
} = require('../../network/StealthFingerprint');

const ROTATING_BROWSER_PROFILES = [
  { family: 'chrome', platform: 'Win32', locale: 'en-US', timezoneId: 'Europe/London', deviceScaleFactor: 1, hasTouch: false, isMobile: false, acceptLanguage: 'en-US,en;q=0.9', secChPlatform: '"Windows"', viewportBase: { width: 1920, height: 1080 }, versions: [130, 131, 132], createUserAgent(version) { return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${version}.0.0.0 Safari/537.36`; } },
  { family: 'edge', platform: 'Win32', locale: 'en-US', timezoneId: 'Europe/London', deviceScaleFactor: 1, hasTouch: false, isMobile: false, acceptLanguage: 'en-US,en;q=0.9', secChPlatform: '"Windows"', viewportBase: { width: 1920, height: 1080 }, versions: [130, 131], createUserAgent(version) { return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${version}.0.0.0 Safari/537.36 Edg/${version}.0.0.0`; } },
  { family: 'safari', platform: 'MacIntel', locale: 'en-US', timezoneId: 'Europe/London', deviceScaleFactor: 2, hasTouch: false, isMobile: false, acceptLanguage: 'en-US,en;q=0.9', secChPlatform: '"macOS"', viewportBase: { width: 1728, height: 972 }, versions: [18], createUserAgent() { return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'; } }
];
const ROTATING_VIEWPORT_PRESETS = [
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1536, height: 864 },
  { width: 1600, height: 900 },
  { width: 1728, height: 972 },
  { width: 1792, height: 1008 },
  { width: 1920, height: 1080 }
];
const ROTATING_WEBGL_PROFILES = [
  { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { vendor: 'Google Inc. (NVIDIA)', renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { vendor: 'Google Inc. (AMD)', renderer: 'ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { vendor: 'Google Inc. (Intel)', renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)' },
  { vendor: 'Google Inc. (Intel)', renderer: 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)' }
];
const HARDWARE_CONCURRENCY_POOL = [8, 10, 12, 16, 20, 24];
const DEVICE_MEMORY_POOL = [4, 8, 8, 16, 16, 32];
const WEBGL_TEXTURE_SIZE_POOL = [8192, 12288, 16384];
const WEBGL_RENDERBUFFER_SIZE_POOL = [8192, 16384];
const WEBGL_MAX_SAMPLES_POOL = [4, 8];

function deriveStealthWorkerId(traceId = '', proxy = null) {
  const port = Number(proxy?.port || 0);
  if (Number.isInteger(port) && port > 0) {
    return port;
  }

  let hash = 0;
  for (const character of String(traceId || 'recon-stealth')) {
    hash = ((hash * 31) + character.charCodeAt(0)) % 10000;
  }
  return hash + 1;
}

function secureRandomInt(min, max) {
  const normalizedMin = Math.ceil(Number(min) || 0);
  const normalizedMax = Math.floor(Number(max) || 0);
  return normalizedMax <= normalizedMin
    ? normalizedMin
    : crypto.randomInt(normalizedMin, normalizedMax + 1);
}

function secureSample(items = []) {
  return Array.isArray(items) && items.length > 0
    ? items[secureRandomInt(0, items.length - 1)]
    : null;
}

function clampValue(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function buildRotatingViewport(baseViewport = FIXED_FINGERPRINT.viewport) {
  const preset = secureSample(ROTATING_VIEWPORT_PRESETS) || baseViewport;
  return {
    width: clampValue(preset.width + secureRandomInt(-18, 18), 1366, 1920),
    height: clampValue(preset.height + secureRandomInt(-14, 14), 768, 1080)
  };
}

function buildStealthHeadersForProfile(profile, version) {
  const extraHTTPHeaders = {
    'accept-language': profile?.acceptLanguage || 'en-US,en;q=0.9',
    'accept-encoding': 'gzip, deflate, br',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1'
  };

  if (profile?.family === 'chrome' || profile?.family === 'edge') {
    extraHTTPHeaders['sec-ch-ua'] = profile.family === 'chrome'
      ? `"Chromium";v="${version}", "Google Chrome";v="${version}", "Not_A Brand";v="24"`
      : `"Chromium";v="${version}", "Microsoft Edge";v="${version}", "Not_A Brand";v="24"`;
    extraHTTPHeaders['sec-ch-ua-mobile'] = '?0';
    extraHTTPHeaders['sec-ch-ua-platform'] = profile.secChPlatform;
  }

  return extraHTTPHeaders;
}

function buildFixedStealthIdentity(traceId = '', proxy = null) {
  const workerId = deriveStealthWorkerId(traceId, proxy);
  const enhancedConfig = getEnhancedStealthConfig({ platform: 'win32' });
  const fixedHeaders = generateStealthHeaders(true);
  const fingerprintSeed = crypto.createHash('sha256').update(`${traceId}:${workerId}:fixed`).digest('hex');

  return {
    workerId,
    userAgent: String(fixedHeaders.userAgent || enhancedConfig.userAgent || FIXED_FINGERPRINT.userAgent),
    viewport: enhancedConfig.viewport || fixedHeaders.viewport || FIXED_FINGERPRINT.viewport,
    locale: FIXED_FINGERPRINT.locale || 'en-US',
    timezoneId: FIXED_FINGERPRINT.timezoneId || 'Europe/London',
    platform: enhancedConfig.platform || FIXED_FINGERPRINT.platform || 'Win32',
    deviceScaleFactor: Number(enhancedConfig.deviceScaleFactor ?? FIXED_FINGERPRINT.deviceScaleFactor ?? 1) || 1,
    hasTouch: enhancedConfig.hasTouch === true,
    isMobile: enhancedConfig.isMobile === true,
    extraHTTPHeaders: { ...(fixedHeaders.extraHTTPHeaders || {}) },
    hardwareConcurrency: 8,
    deviceMemory: 8,
    webgl: {
      vendor: 'Google Inc. (Intel)',
      renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
      maxTextureSize: 8192,
      maxRenderbufferSize: 16384,
      maxSamples: 4
    },
    fingerprintSeed,
    canvasSalt: fingerprintSeed.slice(0, 16),
    audioSalt: fingerprintSeed.slice(16, 32),
    webglSalt: fingerprintSeed.slice(32, 48),
    antiDetectionScript: getAntiDetectionScripts({
      workerId,
      fingerprintSeed,
      webglVendor: 'Google Inc. (Intel)',
      webglRenderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
      hardwareConcurrency: 8,
      deviceMemory: 8,
      platform: enhancedConfig.platform || FIXED_FINGERPRINT.platform || 'Win32',
      canvasSalt: fingerprintSeed.slice(0, 16),
      audioSalt: fingerprintSeed.slice(16, 32),
      webglSalt: fingerprintSeed.slice(32, 48),
      maxTextureSize: 8192,
      maxRenderbufferSize: 16384,
      maxSamples: 4
    })
  };
}

function buildRotatingStealthIdentity(traceId = '', proxy = null, options = {}) {
  const workerId = deriveStealthWorkerId(traceId, proxy);
  const profile = secureSample(ROTATING_BROWSER_PROFILES) || ROTATING_BROWSER_PROFILES[0];
  const version = secureSample(profile.versions) || profile.versions[0];
  const webgl = secureSample(ROTATING_WEBGL_PROFILES) || ROTATING_WEBGL_PROFILES[0];
  const fingerprintSeed = crypto.randomUUID();
  const entropy = crypto.createHash('sha256').update(
    `${traceId}:${workerId}:${options.generation || 0}:${fingerprintSeed}`
  ).digest('hex');
  const hardwareConcurrency = secureSample(HARDWARE_CONCURRENCY_POOL) || 8;
  const deviceMemory = secureSample(DEVICE_MEMORY_POOL) || 8;
  const maxTextureSize = secureSample(WEBGL_TEXTURE_SIZE_POOL) || 8192;
  const maxRenderbufferSize = secureSample(WEBGL_RENDERBUFFER_SIZE_POOL) || 16384;
  const maxSamples = secureSample(WEBGL_MAX_SAMPLES_POOL) || 4;

  return {
    workerId,
    userAgent: profile.createUserAgent(version),
    viewport: buildRotatingViewport(profile.viewportBase),
    locale: profile.locale,
    timezoneId: profile.timezoneId,
    platform: profile.platform,
    deviceScaleFactor: Number(profile.deviceScaleFactor ?? 1) || 1,
    hasTouch: profile.hasTouch === true,
    isMobile: profile.isMobile === true,
    extraHTTPHeaders: buildStealthHeadersForProfile(profile, version),
    hardwareConcurrency,
    deviceMemory,
    webgl: { ...webgl, maxTextureSize, maxRenderbufferSize, maxSamples },
    fingerprintSeed,
    canvasSalt: entropy.slice(0, 16),
    audioSalt: entropy.slice(16, 32),
    webglSalt: entropy.slice(32, 48),
    antiDetectionScript: getAntiDetectionScripts({
      workerId,
      fingerprintSeed,
      webglVendor: webgl.vendor,
      webglRenderer: webgl.renderer,
      hardwareConcurrency,
      deviceMemory,
      platform: profile.platform,
      canvasSalt: entropy.slice(0, 16),
      audioSalt: entropy.slice(16, 32),
      webglSalt: entropy.slice(32, 48),
      maxTextureSize,
      maxRenderbufferSize,
      maxSamples
    })
  };
}

function buildStealthIdentity(traceId = '', proxy = null, options = {}) {
  return options.enableFingerprintRotation === true
    ? buildRotatingStealthIdentity(traceId, proxy, options)
    : buildFixedStealthIdentity(traceId, proxy);
}

function buildStealthLaunchArgs(baseArgs = [], viewport = FIXED_FINGERPRINT.viewport, locale = 'en-US') {
  return Array.from(new Set([
    ...baseArgs,
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
    `--window-size=${viewport.width},${viewport.height}`,
    `--lang=${String(locale || 'en-US').split(',')[0]}`
  ]));
}

module.exports = {
  buildStealthIdentity,
  buildStealthLaunchArgs
};
