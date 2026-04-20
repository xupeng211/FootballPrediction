'use strict';

const { buildStealthIdentity, buildStealthLaunchArgs } = require('./StealthIdentityFactory');
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
const SUPPORTED_STEALTH_UA_RE = /(?:Chrome\/(?:130|131|132)\.0\.0\.0|Edg\/(?:130|131)\.0\.0\.0|Version\/18(?:\.0)?\b)/;

function firstDefined(...values) {
  for (const value of values) {
    if (value !== undefined) {
      return value;
    }
  }
  return undefined;
}

function firstNonEmpty(...values) {
  for (const value of values) {
    const normalized = String(value || '').trim();
    if (normalized) {
      return normalized;
    }
  }
  return '';
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

function syncStealthProviderProfile(target) {
  if (!target.stealthProvider) {
    return;
  }

  target.stealthProvider.hardwareConcurrency = target.hardwareConcurrency;
  target.stealthProvider.deviceMemory = target.deviceMemory;
  target.stealthProvider.platform = target.platform;
}

function buildIdentityDisplayState(target, stealthIdentity) {
  const userAgent = resolveContextUserAgent(target.userAgentOverride, stealthIdentity.userAgent);
  const viewport = target.viewportOverride || stealthIdentity.viewport || target.runtimeConfig.viewport;
  const locale = firstNonEmpty(target.localeOverride, stealthIdentity.locale, target.runtimeConfig.locale, 'en-US');
  const timezoneId = firstNonEmpty(
    target.timezoneOverride,
    stealthIdentity.timezoneId,
    target.runtimeConfig.timezone_id,
    'Europe/London'
  );
  const platform = firstNonEmpty(target.platformOverride, stealthIdentity.platform, target.runtimeConfig.platform, 'Win32');
  const acceptLanguage = firstNonEmpty(
    target.acceptLanguageOverride,
    stealthIdentity.extraHTTPHeaders?.['accept-language'],
    DEFAULT_ACCEPT_LANGUAGE
  );
  const deviceScaleFactor = Number(firstDefined(target.deviceScaleFactorOverride, stealthIdentity.deviceScaleFactor, 1)) || 1;
  const hasTouch = Boolean(firstDefined(target.hasTouchOverride, stealthIdentity.hasTouch, false));
  const isMobile = Boolean(firstDefined(target.isMobileOverride, stealthIdentity.isMobile, false));

  return {
    userAgent,
    viewport,
    locale: String(locale),
    timezoneId: String(timezoneId),
    platform: String(platform),
    deviceScaleFactor,
    hasTouch,
    isMobile,
    acceptLanguage: String(acceptLanguage),
    stealthExtraHTTPHeaders: { ...(stealthIdentity.extraHTTPHeaders || {}) },
    antiDetectionScript: String(stealthIdentity.antiDetectionScript || ''),
    launchArgs: buildStealthLaunchArgs(target.baseLaunchArgs, viewport, locale)
  };
}

function buildIdentityHardwareState(target, stealthIdentity) {
  return {
    hardwareConcurrency: Number(
      firstDefined(
        target.hardwareConcurrencyOverride,
        stealthIdentity.hardwareConcurrency,
        target.runtimeConfig.hardware_concurrency,
        8
      )
    ),
    deviceMemory: Number(
      firstDefined(
        target.deviceMemoryOverride,
        stealthIdentity.deviceMemory,
        target.runtimeConfig.device_memory,
        8
      )
    )
  };
}

function applyStealthIdentityState(target, stealthIdentity) {
  const resolvedIdentity = stealthIdentity || buildStealthIdentity(target.traceId, target.proxy);
  target.stealthIdentity = resolvedIdentity;
  target.contextGeneration += 1;
  Object.assign(
    target,
    buildIdentityDisplayState(target, resolvedIdentity),
    buildIdentityHardwareState(target, resolvedIdentity)
  );
  syncStealthProviderProfile(target);
}

function buildCoreState(options, runtimeConfig) {
  return {
    logger: options.logger || console,
    traceId: options.traceId || 'trace-unknown',
    headless: options.headless !== false,
    proxy: options.proxy,
    browser: null,
    context: null,
    page: null,
    isClosed: false,
    runtimeConfig,
    enableFingerprintRotation: options.enableFingerprintRotation === true,
    resetContextPerBatchEnabled: options.resetContextPerBatch === true,
    enableStealthFingerprint: true,
    contextGeneration: 0
  };
}

function buildOverrideState(options, runtimeConfig) {
  return {
    userAgentOverride: firstNonEmpty(options.userAgent, runtimeConfig.user_agent),
    viewportOverride: options.viewport || null,
    localeOverride: firstNonEmpty(options.locale, runtimeConfig.locale),
    timezoneOverride: firstNonEmpty(options.timezoneId, runtimeConfig.timezone_id),
    hardwareConcurrencyOverride: options.hardwareConcurrency,
    deviceMemoryOverride: options.deviceMemory,
    platformOverride: firstNonEmpty(options.platform, runtimeConfig.platform),
    deviceScaleFactorOverride: options.deviceScaleFactor,
    hasTouchOverride: options.hasTouch,
    isMobileOverride: options.isMobile,
    acceptLanguageOverride: firstNonEmpty(options.acceptLanguage, runtimeConfig.accept_language),
    baseLaunchArgs: Array.isArray(options.launchArgs)
      ? [...options.launchArgs]
      : resolveList(runtimeConfig.launch_args, [], [])
  };
}

function buildTimingState(options, runtimeConfig) {
  return {
    launchTimeoutMs: Number(firstDefined(options.launchTimeoutMs, runtimeConfig.launch_timeout_ms)),
    navigationTimeoutMs: Number(firstDefined(options.navigationTimeoutMs, runtimeConfig.navigation_timeout_ms)),
    warmupDelayMs: Number(firstDefined(options.warmupDelayMs, runtimeConfig.warmup_delay_ms)),
    scrollIterations: Number(firstDefined(options.scrollIterations, runtimeConfig.scroll_iterations)),
    scrollStepPx: Number(firstDefined(options.scrollStepPx, runtimeConfig.scroll_step_px)),
    scrollDelayMs: Number(firstDefined(options.scrollDelayMs, runtimeConfig.scroll_delay_ms)),
    consentVisibilityTimeoutMs: Number(firstDefined(options.consentVisibilityTimeoutMs, runtimeConfig.consent_visibility_timeout_ms)),
    consentClickTimeoutMs: Number(firstDefined(options.consentClickTimeoutMs, runtimeConfig.consent_click_timeout_ms)),
    consentPostClickWaitMs: Number(firstDefined(options.consentPostClickWaitMs, runtimeConfig.consent_post_click_wait_ms)),
    closeTimeoutMs: Number(firstDefined(options.closeTimeoutMs, runtimeConfig.close_timeout_ms, 5000)),
    navigationReadyTimeoutMs: Number(
      firstDefined(options.navigationReadyTimeoutMs, runtimeConfig.navigation_ready_timeout_ms, runtimeConfig.navigation_timeout_ms)
    )
  };
}

function buildNavigationState(options, runtimeConfig) {
  return {
    navigationReadySelectors: resolveList(
      options.navigationReadySelectors,
      runtimeConfig.navigation_ready_selectors,
      DEFAULT_READY_SELECTORS
    ),
    consentLabels: resolveList(options.consentLabels, runtimeConfig.consent_labels, DEFAULT_CONSENT_LABELS)
  };
}

function buildWarmupState(options, runtimeConfig, networkMonitorConfig) {
  return {
    homeWarmupEnabled: firstDefined(options.homeWarmupEnabled, networkMonitorConfig.home_warmup_enabled, false),
    homeWarmupUrl: firstNonEmpty(
      options.homeWarmupUrl,
      networkMonitorConfig.home_warmup_url,
      RECON_CONFIG.oddsportal?.base_url
    ),
    homeWarmupWaitMs: Number(firstDefined(options.homeWarmupWaitMs, networkMonitorConfig.home_warmup_wait_ms, 5000)),
    externalSessionPath: firstNonEmpty(options.externalSessionPath, runtimeConfig.external_session_path),
    _sessionPrimed: false
  };
}

function buildLaunchProfileState(options, runtimeConfig) {
  const resetContextPerBatch = options.resetContextPerBatch === true;
  const persistentProfileEnabled = Boolean(firstDefined(
    options.persistentProfileEnabled,
    runtimeConfig.persistent_profile_enabled,
    true
  ));

  return {
    preferFullChromium: firstDefined(options.preferFullChromium, runtimeConfig.prefer_full_chromium, false),
    persistentProfileEnabled: persistentProfileEnabled && !resetContextPerBatch,
    explicitExecutablePath: firstNonEmpty(
      options.executablePath,
      runtimeConfig.executable_path,
      process.env.PLAYWRIGHT_EXECUTABLE_PATH
    ),
    playwrightCacheRoot: firstNonEmpty(
      options.cachePath,
      options.playwrightCacheRoot,
      runtimeConfig.cache_path,
      runtimeConfig.playwright_cache_root,
      process.env.PLAYWRIGHT_CACHE_PATH
    ),
    userDataDirRoot: firstNonEmpty(options.userDataDirRoot, runtimeConfig.user_data_dir_root),
    userDataDir: null
  };
}

function buildBaseState(options = {}, runtimeConfig, networkMonitorConfig) {
  return {
    ...buildCoreState(options, runtimeConfig),
    ...buildOverrideState(options, runtimeConfig),
    ...buildTimingState(options, runtimeConfig),
    ...buildNavigationState(options, runtimeConfig),
    ...buildWarmupState(options, runtimeConfig, networkMonitorConfig),
    ...buildLaunchProfileState(options, runtimeConfig)
  };
}

function attachRuntimeCollaborators(state, options, runtimeConfig, unlockStrategiesConfig) {
  state.stealthProvider = options.stealthProvider || new ReconStealthProvider({
    logger: state.logger,
    traceId: state.traceId,
    hardwareConcurrency: state.hardwareConcurrency,
    deviceMemory: state.deviceMemory,
    platform: state.platform,
    userDataDirRoot: state.userDataDirRoot,
    cachePath: state.playwrightCacheRoot
  });
  state.resolvePreferredExecutablePath = options.resolvePreferredExecutablePath
    || (() => state.stealthProvider.resolvePreferredExecutablePath());
  state.sessionManager = options.sessionManager || new ReconSessionManager({
    logger: state.logger,
    traceId: state.traceId,
    sessionPath: state.externalSessionPath,
    defaultSourceUrl: RECON_CONFIG.oddsportal?.base_url,
    proxyPort: state.proxy?.port
  });
  state.bookmakerUnlocker = options.bookmakerUnlocker || new ReconBookmakerUnlocker({
    logger: state.logger,
    traceId: state.traceId,
    forceUnlockJ1: firstDefined(
      options.forceUnlockJ1,
      unlockStrategiesConfig.force_unlock_j1,
      runtimeConfig.force_unlock_j1,
      {}
    )
  });
  state.forceUnlockJ1 = state.bookmakerUnlocker.config;
  syncStealthProviderProfile(state);
}

function createPageContextState(options = {}) {
  const runtimeConfig = getReconConfigSection(['recon_runtime', 'browser_context'], {});
  const networkMonitorConfig = getReconConfigSection(['recon_runtime', 'network_monitor'], {});
  const unlockStrategiesConfig = getReconConfigSection(['recon_runtime', 'unlock_strategies'], {});
  const state = buildBaseState(options, runtimeConfig, networkMonitorConfig);

  applyStealthIdentityState(state, buildStealthIdentity(state.traceId, state.proxy, {
    enableFingerprintRotation: state.enableFingerprintRotation,
    generation: 1
  }));
  attachRuntimeCollaborators(state, options, runtimeConfig, unlockStrategiesConfig);
  return state;
}

module.exports = {
  applyStealthIdentityState,
  createPageContextState,
  resolveContextUserAgent,
  resolveList,
  syncStealthProviderProfile
};
