'use strict';

const crypto = require('node:crypto');
const { chromium: playwrightChromium } = require('playwright');
const {
  getAntiDetectionScripts,
  getEnhancedStealthConfig
} = require('../../network/enhanced_stealth_config');
const {
  FIXED_FINGERPRINT,
  generateStealthHeaders
} = require('../../network/StealthFingerprint');
const { ReconBookmakerUnlocker } = require('./ReconBookmakerUnlocker');
const {
  ReconStealthProvider,
  DEFAULT_ACCEPT_LANGUAGE,
  DEFAULT_CONSENT_LABELS
} = require('./ReconStealthProvider');
const { RECON_CONFIG, getReconConfigSection } = require('./ReconServiceConfig');
const { ReconSessionManager } = require('./ReconSessionManager');

const DEFAULT_READY_SELECTORS = [
  ...((RECON_CONFIG.oddsportal?.selectors?.match_row) || []),
  'div[role="row"] a[href]',
  'div[data-testid*="event"] a[href]',
  'div[data-testid*="match"] a[href]',
  '[class*="event-row"] a[href]',
  '[class*="EventRow"] a[href]',
  'div[class*="sportName"] a[href]',
  '.pagination a[href]',
  'main',
  'body'
];
const BACKEND_FETCH_FAILED_RE = /backend fetch failed|guru meditation/i;
const SUPPORTED_STEALTH_UA_RE = /(?:Chrome\/(?:130|131|132)\.0\.0\.0|Edg\/(?:130|131)\.0\.0\.0|Version\/18(?:\.0)?\b)/;
const ROTATING_BROWSER_PROFILES = [
  {
    family: 'chrome',
    platform: 'Win32',
    locale: 'en-US',
    timezoneId: 'Europe/London',
    deviceScaleFactor: 1,
    hasTouch: false,
    isMobile: false,
    acceptLanguage: 'en-US,en;q=0.9',
    secChPlatform: '"Windows"',
    viewportBase: { width: 1920, height: 1080 },
    versions: [130, 131, 132],
    createUserAgent(version) {
      return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${version}.0.0.0 Safari/537.36`;
    }
  },
  {
    family: 'edge',
    platform: 'Win32',
    locale: 'en-US',
    timezoneId: 'Europe/London',
    deviceScaleFactor: 1,
    hasTouch: false,
    isMobile: false,
    acceptLanguage: 'en-US,en;q=0.9',
    secChPlatform: '"Windows"',
    viewportBase: { width: 1920, height: 1080 },
    versions: [130, 131],
    createUserAgent(version) {
      return `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${version}.0.0.0 Safari/537.36 Edg/${version}.0.0.0`;
    }
  },
  {
    family: 'safari',
    platform: 'MacIntel',
    locale: 'en-US',
    timezoneId: 'Europe/London',
    deviceScaleFactor: 2,
    hasTouch: false,
    isMobile: false,
    acceptLanguage: 'en-US,en;q=0.9',
    secChPlatform: '"macOS"',
    viewportBase: { width: 1728, height: 972 },
    versions: [18],
    createUserAgent() {
      return 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15';
    }
  }
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
  {
    vendor: 'Google Inc. (NVIDIA)',
    renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'
  },
  {
    vendor: 'Google Inc. (NVIDIA)',
    renderer: 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)'
  },
  {
    vendor: 'Google Inc. (AMD)',
    renderer: 'ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)'
  },
  {
    vendor: 'Google Inc. (Intel)',
    renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'
  },
  {
    vendor: 'Google Inc. (Intel)',
    renderer: 'ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)'
  }
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
  if (normalizedMax <= normalizedMin) {
    return normalizedMin;
  }

  return crypto.randomInt(normalizedMin, normalizedMax + 1);
}

function secureSample(items = []) {
  if (!Array.isArray(items) || items.length === 0) {
    return null;
  }

  return items[secureRandomInt(0, items.length - 1)];
}

function clampValue(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function buildRotatingViewport(baseViewport = FIXED_FINGERPRINT.viewport) {
  const preset = secureSample(ROTATING_VIEWPORT_PRESETS) || baseViewport;
  const width = clampValue(
    preset.width + secureRandomInt(-18, 18),
    1366,
    1920
  );
  const height = clampValue(
    preset.height + secureRandomInt(-14, 14),
    768,
    1080
  );

  return {
    width,
    height
  };
}

function buildStealthHeadersForProfile(profile, version) {
  const acceptLanguage = profile?.acceptLanguage || 'en-US,en;q=0.9';
  const extraHTTPHeaders = {
    'accept-language': acceptLanguage,
    'accept-encoding': 'gzip, deflate, br',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1'
  };

  if (profile?.family === 'chrome') {
    extraHTTPHeaders['sec-ch-ua'] = `"Chromium";v="${version}", "Google Chrome";v="${version}", "Not_A Brand";v="24"`;
    extraHTTPHeaders['sec-ch-ua-mobile'] = '?0';
    extraHTTPHeaders['sec-ch-ua-platform'] = profile.secChPlatform;
  } else if (profile?.family === 'edge') {
    extraHTTPHeaders['sec-ch-ua'] = `"Chromium";v="${version}", "Microsoft Edge";v="${version}", "Not_A Brand";v="24"`;
    extraHTTPHeaders['sec-ch-ua-mobile'] = '?0';
    extraHTTPHeaders['sec-ch-ua-platform'] = profile.secChPlatform;
  }

  return extraHTTPHeaders;
}

function buildFixedStealthIdentity(traceId = '', proxy = null) {
  const workerId = deriveStealthWorkerId(traceId, proxy);
  const enhancedConfig = getEnhancedStealthConfig({ platform: 'win32' });
  const fixedHeaders = generateStealthHeaders(true);
  const fixedFingerprintSeed = crypto
    .createHash('sha256')
    .update(`${traceId}:${workerId}:fixed`)
    .digest('hex');

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
    extraHTTPHeaders: {
      ...(fixedHeaders.extraHTTPHeaders || {})
    },
    hardwareConcurrency: 8,
    deviceMemory: 8,
    webgl: {
      vendor: 'Google Inc. (Intel)',
      renderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
      maxTextureSize: 8192,
      maxRenderbufferSize: 16384,
      maxSamples: 4
    },
    fingerprintSeed: fixedFingerprintSeed,
    canvasSalt: fixedFingerprintSeed.slice(0, 16),
    audioSalt: fixedFingerprintSeed.slice(16, 32),
    webglSalt: fixedFingerprintSeed.slice(32, 48),
    antiDetectionScript: getAntiDetectionScripts({
      workerId,
      fingerprintSeed: fixedFingerprintSeed,
      webglVendor: 'Google Inc. (Intel)',
      webglRenderer: 'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)',
      hardwareConcurrency: 8,
      deviceMemory: 8,
      platform: enhancedConfig.platform || FIXED_FINGERPRINT.platform || 'Win32',
      canvasSalt: fixedFingerprintSeed.slice(0, 16),
      audioSalt: fixedFingerprintSeed.slice(16, 32),
      webglSalt: fixedFingerprintSeed.slice(32, 48),
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
  const userAgent = profile.createUserAgent(version);
  const webgl = secureSample(ROTATING_WEBGL_PROFILES) || ROTATING_WEBGL_PROFILES[0];
  const viewport = buildRotatingViewport(profile.viewportBase);
  const fingerprintSeed = crypto.randomUUID();
  const entropy = crypto
    .createHash('sha256')
    .update(`${traceId}:${workerId}:${options.generation || 0}:${fingerprintSeed}`)
    .digest('hex');
  const hardwareConcurrency = secureSample(HARDWARE_CONCURRENCY_POOL) || 8;
  const deviceMemory = secureSample(DEVICE_MEMORY_POOL) || 8;
  const maxTextureSize = secureSample(WEBGL_TEXTURE_SIZE_POOL) || 8192;
  const maxRenderbufferSize = secureSample(WEBGL_RENDERBUFFER_SIZE_POOL) || 16384;
  const maxSamples = secureSample(WEBGL_MAX_SAMPLES_POOL) || 4;

  return {
    workerId,
    userAgent,
    viewport,
    locale: profile.locale,
    timezoneId: profile.timezoneId,
    platform: profile.platform,
    deviceScaleFactor: Number(profile.deviceScaleFactor ?? 1) || 1,
    hasTouch: profile.hasTouch === true,
    isMobile: profile.isMobile === true,
    extraHTTPHeaders: buildStealthHeadersForProfile(profile, version),
    hardwareConcurrency,
    deviceMemory,
    webgl: {
      ...webgl,
      maxTextureSize,
      maxRenderbufferSize,
      maxSamples
    },
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
  if (options.enableFingerprintRotation === true) {
    return buildRotatingStealthIdentity(traceId, proxy, options);
  }

  return buildFixedStealthIdentity(traceId, proxy);
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

function resolveContextUserAgent(candidate, fallback) {
  const value = String(candidate || '').trim();
  return SUPPORTED_STEALTH_UA_RE.test(value) ? value : fallback;
}

function resolveList(primary, secondary, fallback) {
  if (Array.isArray(primary) && primary.length > 0) {
    return [...primary];
  }
  if (Array.isArray(secondary) && secondary.length > 0) {
    return [...secondary];
  }
  return [...fallback];
}

function pageClosed(page) { return !page || (typeof page.isClosed === 'function' && page.isClosed()); }

function buildHttpStatusError(statusCode, message, meta = {}) {
  const error = new Error(message);
  error.statusCode = statusCode;
  Object.assign(error, meta);
  return error;
}

class ReconBrowserContext {
  constructor(options = {}) {
    const runtimeConfig = getReconConfigSection(['recon_runtime', 'browser_context'], {});
    const networkMonitorConfig = getReconConfigSection(['recon_runtime', 'network_monitor'], {});
    const unlockStrategiesConfig = getReconConfigSection(['recon_runtime', 'unlock_strategies'], {});
    const enableFingerprintRotation = options.enableFingerprintRotation === true;
    const resetContextPerBatch = options.resetContextPerBatch === true;
    const stealthIdentity = buildStealthIdentity(options.traceId, options.proxy, {
      enableFingerprintRotation,
      generation: 1
    });

    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.chromium = options.chromium || playwrightChromium;
    this.headless = options.headless !== false;
    this.proxy = options.proxy;
    this.browser = null;
    this.context = null;
    this.page = null;
    this.isClosed = false;
    this.launchTimeoutMs = Number(options.launchTimeoutMs ?? runtimeConfig.launch_timeout_ms);
    this.navigationTimeoutMs = Number(options.navigationTimeoutMs ?? runtimeConfig.navigation_timeout_ms);
    this.runtimeConfig = runtimeConfig;
    this.enableFingerprintRotation = enableFingerprintRotation;
    this.resetContextPerBatchEnabled = resetContextPerBatch;
    this.userAgentOverride = options.userAgent || runtimeConfig.user_agent;
    this.viewportOverride = options.viewport || null;
    this.localeOverride = options.locale || runtimeConfig.locale || '';
    this.timezoneOverride = options.timezoneId || runtimeConfig.timezone_id || '';
    this.hardwareConcurrencyOverride = options.hardwareConcurrency;
    this.deviceMemoryOverride = options.deviceMemory;
    this.platformOverride = options.platform || runtimeConfig.platform || '';
    this.deviceScaleFactorOverride = options.deviceScaleFactor;
    this.hasTouchOverride = options.hasTouch;
    this.isMobileOverride = options.isMobile;
    this.acceptLanguageOverride = options.acceptLanguage || runtimeConfig.accept_language || '';
    this.baseLaunchArgs = Array.isArray(options.launchArgs)
      ? [...options.launchArgs]
      : Array.isArray(runtimeConfig.launch_args)
        ? [...runtimeConfig.launch_args]
        : [];
    this.contextGeneration = 0;
    this.warmupDelayMs = Number(options.warmupDelayMs ?? runtimeConfig.warmup_delay_ms);
    this.scrollIterations = Number(options.scrollIterations ?? runtimeConfig.scroll_iterations);
    this.scrollStepPx = Number(options.scrollStepPx ?? runtimeConfig.scroll_step_px);
    this.scrollDelayMs = Number(options.scrollDelayMs ?? runtimeConfig.scroll_delay_ms);
    this.consentVisibilityTimeoutMs = Number(options.consentVisibilityTimeoutMs ?? runtimeConfig.consent_visibility_timeout_ms);
    this.consentClickTimeoutMs = Number(options.consentClickTimeoutMs ?? runtimeConfig.consent_click_timeout_ms);
    this.consentPostClickWaitMs = Number(options.consentPostClickWaitMs ?? runtimeConfig.consent_post_click_wait_ms);
    this.closeTimeoutMs = Number(options.closeTimeoutMs ?? runtimeConfig.close_timeout_ms ?? 5000);
    this.navigationReadySelectors = resolveList(
      options.navigationReadySelectors,
      runtimeConfig.navigation_ready_selectors,
      DEFAULT_READY_SELECTORS
    );
    this.navigationReadyTimeoutMs = Number(
      options.navigationReadyTimeoutMs
      ?? runtimeConfig.navigation_ready_timeout_ms
      ?? this.navigationTimeoutMs
    );
    this.homeWarmupEnabled = options.homeWarmupEnabled ?? networkMonitorConfig.home_warmup_enabled ?? false;
    this.homeWarmupUrl = String(
      options.homeWarmupUrl
      || networkMonitorConfig.home_warmup_url
      || RECON_CONFIG.oddsportal?.base_url
      || ''
    ).trim();
    this.homeWarmupWaitMs = Number(options.homeWarmupWaitMs ?? networkMonitorConfig.home_warmup_wait_ms ?? 5000);
    this.enableStealthFingerprint = true;
    this.externalSessionPath = String(options.externalSessionPath || runtimeConfig.external_session_path || '');
    this.preferFullChromium = options.preferFullChromium ?? runtimeConfig.prefer_full_chromium ?? false;
    this.persistentProfileEnabled = (
      options.persistentProfileEnabled
      ?? runtimeConfig.persistent_profile_enabled
      ?? true
    ) && this.resetContextPerBatchEnabled !== true;
    this.explicitExecutablePath = String(
      options.executablePath
      || runtimeConfig.executable_path
      || process.env.PLAYWRIGHT_EXECUTABLE_PATH
      || ''
    ).trim();
    this.playwrightCacheRoot = String(
      options.cachePath
      || options.playwrightCacheRoot
      || runtimeConfig.cache_path
      || runtimeConfig.playwright_cache_root
      || process.env.PLAYWRIGHT_CACHE_PATH
      || ''
    ).trim();
    this.userDataDirRoot = String(options.userDataDirRoot || runtimeConfig.user_data_dir_root || '');
    this._applyStealthIdentity(stealthIdentity);
    this.stealthProvider = options.stealthProvider || new ReconStealthProvider({
      logger: this.logger,
      traceId: this.traceId,
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory,
      platform: this.platform,
      userDataDirRoot: this.userDataDirRoot,
      cachePath: this.playwrightCacheRoot
    });
    this.resolvePreferredExecutablePath = options.resolvePreferredExecutablePath
      || (() => this.stealthProvider.resolvePreferredExecutablePath());
    this.userDataDir = null;
    this.sessionManager = options.sessionManager || new ReconSessionManager({
      logger: this.logger,
      traceId: this.traceId,
      sessionPath: this.externalSessionPath,
      defaultSourceUrl: RECON_CONFIG.oddsportal?.base_url
    });
    this.bookmakerUnlocker = options.bookmakerUnlocker || new ReconBookmakerUnlocker({
      logger: this.logger,
      traceId: this.traceId,
      forceUnlockJ1: options.forceUnlockJ1 || unlockStrategiesConfig.force_unlock_j1 || runtimeConfig.force_unlock_j1 || {}
    });
    this.forceUnlockJ1 = this.bookmakerUnlocker.config;
    this._sessionPrimed = false;
    this.consentLabels = resolveList(options.consentLabels, runtimeConfig.consent_labels, DEFAULT_CONSENT_LABELS);
    this._syncStealthProviderProfile();
  }

  _buildStealthIdentity() {
    return buildStealthIdentity(this.traceId, this.proxy, {
      enableFingerprintRotation: this.enableFingerprintRotation,
      generation: this.contextGeneration + 1
    });
  }

  _applyStealthIdentity(stealthIdentity) {
    this.stealthIdentity = stealthIdentity || buildFixedStealthIdentity(this.traceId, this.proxy);
    this.contextGeneration += 1;
    this.userAgent = resolveContextUserAgent(
      this.userAgentOverride,
      this.stealthIdentity.userAgent
    );
    this.viewport = this.viewportOverride || this.stealthIdentity.viewport || this.runtimeConfig.viewport;
    this.locale = String(this.localeOverride || this.stealthIdentity.locale || this.runtimeConfig.locale || 'en-US');
    this.timezoneId = String(
      this.timezoneOverride
      || this.stealthIdentity.timezoneId
      || this.runtimeConfig.timezone_id
      || 'Europe/London'
    );
    this.hardwareConcurrency = Number(
      this.hardwareConcurrencyOverride
      ?? this.stealthIdentity.hardwareConcurrency
      ?? this.runtimeConfig.hardware_concurrency
      ?? 8
    );
    this.deviceMemory = Number(
      this.deviceMemoryOverride
      ?? this.stealthIdentity.deviceMemory
      ?? this.runtimeConfig.device_memory
      ?? 8
    );
    this.platform = String(this.platformOverride || this.stealthIdentity.platform || this.runtimeConfig.platform || 'Win32');
    this.deviceScaleFactor = Number(
      this.deviceScaleFactorOverride
      ?? this.stealthIdentity.deviceScaleFactor
      ?? 1
    ) || 1;
    this.hasTouch = this.hasTouchOverride ?? this.stealthIdentity.hasTouch ?? false;
    this.isMobile = this.isMobileOverride ?? this.stealthIdentity.isMobile ?? false;
    this.acceptLanguage = String(
      this.acceptLanguageOverride
      || this.stealthIdentity.extraHTTPHeaders?.['accept-language']
      || DEFAULT_ACCEPT_LANGUAGE
    );
    this.stealthExtraHTTPHeaders = {
      ...(this.stealthIdentity.extraHTTPHeaders || {})
    };
    this.antiDetectionScript = String(this.stealthIdentity.antiDetectionScript || '');
    this.launchArgs = buildStealthLaunchArgs(this.baseLaunchArgs, this.viewport, this.locale);
    this._syncStealthProviderProfile();
  }

  _syncStealthProviderProfile() {
    if (!this.stealthProvider) {
      return;
    }

    this.stealthProvider.hardwareConcurrency = this.hardwareConcurrency;
    this.stealthProvider.deviceMemory = this.deviceMemory;
    this.stealthProvider.platform = this.platform;
  }

  buildLaunchOptions(options = {}) {
    const launchOptions = {
      headless: this.headless,
      args: this.launchArgs,
      timeout: options.timeout || this.launchTimeoutMs
    };

    if (this.proxy?.host && this.proxy?.port) {
      launchOptions.proxy = { server: `http://${this.proxy.host}:${this.proxy.port}` };
    }

    const explicitExecutablePath = String(options.executablePath || this.explicitExecutablePath || '').trim();
    if (explicitExecutablePath) {
      launchOptions.executablePath = explicitExecutablePath;
    } else if (this.preferFullChromium) {
      const executablePath = this.resolvePreferredExecutablePath();
      if (executablePath) {
        launchOptions.executablePath = executablePath;
        this.logger.info('recon_browser_full_chromium_selected', {
          traceId: this.traceId,
          executablePath
        });
      } else if (typeof this.logger.debug === 'function') {
        this.logger.debug('recon_browser_full_chromium_unavailable', {
          traceId: this.traceId,
          cacheRoot: this.playwrightCacheRoot
        });
      }
    }

    return launchOptions;
  }

  _buildContextOptions(externalSession = null) {
    const sessionHeaders = externalSession?.extraHTTPHeaders || {};
    const contextUserAgent = resolveContextUserAgent(externalSession?.userAgent, this.userAgent);

    return {
      userAgent: contextUserAgent,
      viewport: this.viewport,
      locale: this.locale,
      timezoneId: this.timezoneId,
      deviceScaleFactor: this.deviceScaleFactor,
      screen: this.viewport,
      hasTouch: this.hasTouch,
      isMobile: this.isMobile,
      extraHTTPHeaders: {
        ...sessionHeaders,
        ...this.stealthExtraHTTPHeaders,
        'accept-language': this.acceptLanguage,
        ...(contextUserAgent ? { 'user-agent': contextUserAgent } : {})
      }
    };
  }

  async _initializeFreshPage(context, externalSession = null) {
    await this.injectExternalSession(context, externalSession);
    const page = await context.newPage();
    await this.stealthProvider.applyStealthFingerprint(page, this.enableStealthFingerprint, {
      fingerprintSeed: this.stealthIdentity?.fingerprintSeed || '',
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory,
      platform: this.platform,
      language: this.locale,
      languages: [this.locale, 'en', 'en-GB'],
      webgl: this.stealthIdentity?.webgl || null,
      canvasSalt: this.stealthIdentity?.canvasSalt || '',
      webglSalt: this.stealthIdentity?.webglSalt || ''
    });
    if (this.antiDetectionScript && typeof page.addInitScript === 'function') {
      await page.addInitScript(this.antiDetectionScript);
    }

    return page;
  }

  async _closeActiveContext() {
    const context = this.context;
    const page = this.page;
    this.context = null;
    this.page = null;
    this._sessionPrimed = false;

    if (page && typeof page.close === 'function' && !pageClosed(page)) {
      try {
        await page.close();
      } catch (_error) {
        // 页面已挂时允许继续关闭 context
      }
    }

    return this._closeTargetWithTimeout('context', context);
  }

  async launch(options = {}) {
    if (
      this.enableFingerprintRotation === true
      && this.contextGeneration > 0
      && this.isClosed === true
      && options.skipAutoRotate !== true
    ) {
      this._applyStealthIdentity(this._buildStealthIdentity());
    }

    const launchOptions = options.launchOptions || this.buildLaunchOptions(options);
    const externalSession = this.sessionManager.load();

    let browser = null;
    let context = null;
    let page = null;
    let userDataDir = null;

    try {
      const contextOptions = this._buildContextOptions(externalSession);

      if (this.persistentProfileEnabled && typeof this.chromium.launchPersistentContext === 'function') {
        userDataDir = await this.stealthProvider.createUserDataDir();
        context = await this.chromium.launchPersistentContext(userDataDir, {
          ...launchOptions,
          ...contextOptions
        });
        browser = typeof context.browser === 'function' ? context.browser() : null;
        this.userDataDir = userDataDir;
        this.logger.info('recon_browser_context_profile_created', {
          traceId: this.traceId,
          userDataDir
        });
      } else {
        browser = await this.chromium.launch(launchOptions);
        context = await browser.newContext(contextOptions);
      }

      page = await this._initializeFreshPage(context, externalSession);

      this.browser = browser;
      this.context = context;
      this.page = page;
      this.isClosed = false;
      this._sessionPrimed = false;
      return this.page;
    } catch (error) {
      await this._cleanupPartialLaunch(browser, context, page);
      if (userDataDir) {
        this.userDataDir = null;
        await this.stealthProvider.cleanupUserDataDir(userDataDir);
      }
      this.browser = null;
      this.context = null;
      this.page = null;
      this.isClosed = true;
      throw error;
    }
  }

  getFingerprintSummary() {
    return {
      contextGeneration: this.contextGeneration,
      fingerprintSeed: this.stealthIdentity?.fingerprintSeed || null,
      userAgent: this.userAgent,
      viewport: this.viewport,
      platform: this.platform,
      hardwareConcurrency: this.hardwareConcurrency,
      deviceMemory: this.deviceMemory
    };
  }

  async resetContext(options = {}) {
    this._applyStealthIdentity(this._buildStealthIdentity());

    if (
      !this.browser
      || this.persistentProfileEnabled === true
      || (typeof this.browser.isConnected === 'function' && !this.browser.isConnected())
    ) {
      await this.close();
      return this.launch({
        ...options,
        reason: options.reason || 'batch_reset',
        skipAutoRotate: true
      });
    }

    if (typeof this.browser.newContext !== 'function') {
      this.logger.warn('recon_browser_context_batch_reset_skipped', {
        traceId: this.traceId,
        reason: options.reason || 'batch_reset',
        hasBrowser: Boolean(this.browser),
        hasContext: Boolean(this.context)
      });
      return this.page;
    }

    const contextCloseTimedOut = await this._closeActiveContext();
    if (contextCloseTimedOut) {
      await this.close();
      return this.launch({
        ...options,
        reason: options.reason || 'batch_reset',
        skipAutoRotate: true
      });
    }

    const externalSession = this.sessionManager.load();
    const contextOptions = this._buildContextOptions(externalSession);
    const context = await this.browser.newContext(contextOptions);
    const page = await this._initializeFreshPage(context, externalSession);

    this.context = context;
    this.page = page;
    this.isClosed = false;
    return page;
  }

  async injectExternalSession(context = this.context, sessionSnapshot = null) {
    if (!context || typeof context.addCookies !== 'function') {
      return { applied: false, cookies: 0, sourceFormat: 'unavailable' };
    }

    const snapshot = sessionSnapshot || this.sessionManager.load();
    const cookies = Array.isArray(snapshot?.cookies) ? snapshot.cookies : [];
    if (cookies.length === 0) {
      return {
        applied: false,
        cookies: 0,
        sourceFormat: snapshot?.sourceFormat || 'empty'
      };
    }

    await context.addCookies(cookies);
    this.logger.info('recon_external_session_injected', {
      traceId: this.traceId,
      sourceFormat: snapshot?.sourceFormat || 'unknown',
      cookies: cookies.length
    });
    return {
      applied: true,
      cookies: cookies.length,
      sourceFormat: snapshot?.sourceFormat || 'unknown'
    };
  }

  isHealthy() {
    try {
      return Boolean(
        this.browser
        && typeof this.browser.isConnected === 'function'
        && this.browser.isConnected()
        && this.context
        && this.page
        && !pageClosed(this.page)
      );
    } catch (_error) {
      return false;
    }
  }

  async navigate(url, options = {}) {
    if (!this.page) {
      throw new Error('browser_page_unavailable');
    }

    const timeout = options.timeout || this.navigationTimeoutMs;
    const waitUntil = options.waitUntil || 'domcontentloaded';
    await this.primeSession(url, { timeout, waitUntil });
    const response = await this.page.goto(url, { timeout, waitUntil });
    await this.throwIfBackendFetchFailed(response, url, 'target');
    await this.handleConsent();
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForNavigationReady({
      selectors: options.readySelectors,
      timeout: options.readyTimeoutMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    await this.waitForKnownContent({
      selector: options.contentReadySelector,
      timeout: options.readyTimeoutMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    const warmupDelayMs = options.warmupDelayMs ?? this.warmupDelayMs;
    if (warmupDelayMs > 0) {
      await this.page.waitForTimeout(warmupDelayMs);
    }
    if (pageClosed(this.page)) {
      return;
    }

    await this.triggerDataLoading({
      iterations: options.scrollIterations || this.scrollIterations,
      stepPx: options.scrollStepPx || this.scrollStepPx,
      delayMs: options.scrollDelayMs || this.scrollDelayMs
    });
    if (pageClosed(this.page)) {
      return;
    }

    await this.maybeForceUnlockJ1(url);
  }

  async primeSession(targetUrl, options = {}) {
    if (
      this._sessionPrimed
      || !this.page
      || !this.homeWarmupEnabled
      || !this.homeWarmupUrl
      || !targetUrl
      || String(targetUrl).startsWith(this.homeWarmupUrl)
    ) {
      return;
    }

    await this.page.goto(this.homeWarmupUrl, {
      timeout: options.timeout || this.navigationTimeoutMs,
      waitUntil: options.waitUntil || 'domcontentloaded'
    });
    await this.throwIfBackendFetchFailed(null, this.homeWarmupUrl, 'warmup');
    await this.handleConsent();
    if (this.homeWarmupWaitMs > 0) {
      await this.page.waitForTimeout(this.homeWarmupWaitMs);
    }
    this._sessionPrimed = true;
  }

  async waitForKnownContent(options = {}) {
    if (!this.page || typeof this.page.waitForSelector !== 'function') {
      return false;
    }

    const selector = typeof options.selector === 'string' ? options.selector.trim() : '';
    if (!selector) {
      return false;
    }

    try {
      await this.page.waitForSelector(selector, {
        timeout: Number(options.timeout ?? this.navigationReadyTimeoutMs),
        state: 'visible'
      });
      return true;
    } catch (_error) {
      this.logger.warn('recon_known_content_selector_missed', {
        traceId: this.traceId,
        selector
      });
      return false;
    }
  }

  async waitForNavigationReady(options = {}) {
    if (!this.page || typeof this.page.waitForSelector !== 'function') {
      return false;
    }

    const selectors = resolveList(options.selectors, this.navigationReadySelectors, this.navigationReadySelectors);
    const timeout = Number(options.timeout ?? this.navigationReadyTimeoutMs);

    for (const selector of selectors) {
      if (!selector || typeof selector !== 'string') {
        continue;
      }

      try {
        await this.page.waitForSelector(selector, { timeout, state: 'attached' });
        return true;
      } catch (_error) {
        // 尝试下一组选择器，直到命中首个稳定锚点
      }
    }

    this.logger.warn('recon_navigation_ready_selector_missed', {
      traceId: this.traceId,
      selectors,
      timeout
    });
    return false;
  }

  async readBackendFailureSignal() {
    if (!this.page || pageClosed(this.page)) {
      return null;
    }

    let title = '';
    let bodyText = '';

    try {
      if (typeof this.page.title === 'function') {
        title = String(await this.page.title() || '');
      }
    } catch (_error) {
      title = '';
    }

    try {
      if (typeof this.page.evaluate === 'function') {
        bodyText = String(await this.page.evaluate(() => document.body?.innerText || '') || '');
      }
    } catch (_error) {
      bodyText = '';
    }

    const combined = `${title}\n${bodyText}`.trim();
    if (!combined || !BACKEND_FETCH_FAILED_RE.test(combined)) {
      return null;
    }

    return {
      statusCode: 503,
      title,
      snippet: combined.slice(0, 200)
    };
  }

  async throwIfBackendFetchFailed(response, url, phase = 'target') {
    if (response && typeof response.status === 'function') {
      const statusCode = Number(response.status()) || 0;
      if (statusCode >= 500) {
        this.logger.warn('recon_navigation_http_failure', {
          traceId: this.traceId,
          url,
          phase,
          statusCode
        });
        throw buildHttpStatusError(statusCode, `HTTP_${statusCode}`, {
          url,
          phase
        });
      }
    }

    const embeddedFailure = await this.readBackendFailureSignal();
    if (!embeddedFailure) {
      return;
    }

    this.logger.warn('recon_navigation_backend_fetch_failed', {
      traceId: this.traceId,
      url,
      phase,
      title: embeddedFailure.title,
      snippet: embeddedFailure.snippet
    });
    throw buildHttpStatusError(
      embeddedFailure.statusCode,
      `HTTP_${embeddedFailure.statusCode} backend_fetch_failed`,
      {
        url,
        phase
      }
    );
  }

  async triggerDataLoading(options = {}) {
    if (!this.page) {
      return;
    }

    const iterations = options.iterations || this.scrollIterations;
    const stepPx = options.stepPx || this.scrollStepPx;
    const delayMs = options.delayMs || this.scrollDelayMs;
    for (let i = 0; i < iterations; i++) {
      await this.page.evaluate((amount) => window.scrollBy(0, amount), stepPx);
      await this.page.waitForTimeout(delayMs);
    }
  }

  shouldForceUnlockJ1(url) {
    return this.bookmakerUnlocker.shouldForceUnlockJ1(url);
  }

  async maybeForceUnlockJ1(url) {
    return this.bookmakerUnlocker.maybeForceUnlockJ1(this.page, url, {
      shouldForceUnlockJ1: (targetUrl) => this.shouldForceUnlockJ1(targetUrl),
      readBookmakerState: () => this.readBookmakerState(),
      openBookmakerMenu: () => this.openBookmakerMenu(),
      applyBookmakerSelection: () => this.applyBookmakerSelection(),
      waitForBookmakerStateChange: (beforeState, timeoutMs) => this.waitForBookmakerStateChange(beforeState, timeoutMs),
      retriggerArchiveRequest: (options) => this.retriggerArchiveRequest(options)
    });
  }

  async openBookmakerMenu() {
    return this.bookmakerUnlocker.openBookmakerMenu(this.page);
  }

  async applyBookmakerSelection() {
    return this.bookmakerUnlocker.applyBookmakerSelection(this.page);
  }

  async readBookmakerState() {
    return this.bookmakerUnlocker.readBookmakerState(this.page);
  }

  async waitForBookmakerStateChange(beforeState, timeoutMs) {
    return this.bookmakerUnlocker.waitForBookmakerStateChange(this.page, beforeState, timeoutMs);
  }

  async retriggerArchiveRequest(options = {}) {
    return this.bookmakerUnlocker.retriggerArchiveRequest(this.page, options);
  }

  async handleConsent() {
    return this.stealthProvider.dismissConsent(this.page, {
      labels: this.consentLabels,
      visibilityTimeoutMs: this.consentVisibilityTimeoutMs,
      clickTimeoutMs: this.consentClickTimeoutMs,
      postClickWaitMs: this.consentPostClickWaitMs
    });
  }

  async close() {
    this.isClosed = true;

    const browser = this.browser;
    const context = this.context;
    const userDataDir = this.userDataDir;
    this.browser = null;
    this.context = null;
    this.page = null;
    this.userDataDir = null;
    this._sessionPrimed = false;

    try {
      let forceKillRequired = false;
      forceKillRequired = await this._closeTargetWithTimeout('context', context) || forceKillRequired;
      forceKillRequired = await this._closeTargetWithTimeout('browser', browser, {
        skipWhenSameAsContext: browser === context
      }) || forceKillRequired;

      if (forceKillRequired) {
        await this._forceKillBrowserProcess(browser, context);
      }
    } finally {
      await this.stealthProvider.cleanupUserDataDir(userDataDir);
    }
  }

  async _closeTargetWithTimeout(label, target, options = {}) {
    if (!target || typeof target.close !== 'function' || options.skipWhenSameAsContext) {
      return false;
    }

    const timeoutMs = Math.max(1, Number(this.closeTimeoutMs) || 5000);
    let timedOut = false;
    let timer = null;

    try {
      await Promise.race([
        Promise.resolve().then(() => target.close()),
        new Promise((_, reject) => {
          timer = setTimeout(() => {
            timedOut = true;
            reject(new Error(`${label}_close_timeout`));
          }, timeoutMs);
        })
      ]);
      return false;
    } catch (error) {
      this.logger.warn('recon_browser_context_close_failed', {
        traceId: this.traceId,
        target: label,
        timeoutMs,
        timedOut,
        error: error.message
      });
      return true;
    } finally {
      if (timer) {
        clearTimeout(timer);
      }
    }
  }

  async _forceKillBrowserProcess(browser, context) {
    const processHandle = this._resolveBrowserProcessHandle(browser, context);
    if (!processHandle || typeof processHandle.kill !== 'function') {
      return false;
    }

    try {
      processHandle.kill('SIGKILL');
      this.logger.warn('recon_browser_context_process_killed', {
        traceId: this.traceId,
        signal: 'SIGKILL'
      });
      return true;
    } catch (error) {
      this.logger.warn('recon_browser_context_process_kill_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return false;
    }
  }

  _resolveBrowserProcessHandle(browser, context) {
    const candidates = [
      browser,
      context && typeof context.browser === 'function' ? context.browser() : null
    ];

    for (const candidate of candidates) {
      if (!candidate || typeof candidate.process !== 'function') {
        continue;
      }

      const processHandle = candidate.process();
      if (processHandle) {
        return processHandle;
      }
    }

    return null;
  }

  async _cleanupPartialLaunch(browser, context, page) {
    for (const target of [page, context, browser]) {
      if (!target || typeof target.close !== 'function') {
        continue;
      }

      try {
        await target.close();
      } catch (_error) {
        // 启动补偿阶段不再抛出二次清理异常
      }
    }
  }
}

module.exports = { ReconBrowserContext };
