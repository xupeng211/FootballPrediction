'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const config = require('../../config/recon_config.json');
const {
  ReconConfigValidationError,
  loadReconConfig,
  resolveEnvPlaceholders,
  resolveRuntimeFeatureFlags,
  validateConfig
} = require('../../src/infrastructure/recon/services/ReconServiceConfig');
const { ReconMirrorManager } = require('../../src/infrastructure/recon/services/ReconMirrorManager');
const { ReconMatchEvaluator } = require('../../src/infrastructure/recon/services/ReconMatchEvaluator');
const { ReconTaskPlanner } = require('../../src/infrastructure/recon/services/ReconTaskPlanner');
const { ReconBrowserContext } = require('../../src/infrastructure/recon/services/ReconBrowserContext');
const { ReconNetworkMonitor } = require('../../src/infrastructure/recon/services/ReconNetworkMonitor');
const { ReconDomScraper } = require('../../src/infrastructure/recon/services/ReconDomScraper');
const { ReconStateProber } = require('../../src/infrastructure/recon/services/ReconStateProber');

test('Recon services 应默认从 recon_config.json 读取运行时参数，并对 BrowserContext 注入工业 stealth 基线', async () => {
  const mirrorManager = new ReconMirrorManager();
  const matchEvaluator = new ReconMatchEvaluator();
  const taskPlanner = new ReconTaskPlanner();
  const browserContext = new ReconBrowserContext();
  const networkMonitor = new ReconNetworkMonitor();
  const domScraper = new ReconDomScraper();
  const stateProber = new ReconStateProber();

  assert.equal(mirrorManager.teamWeight, config.recon_runtime.mirror_manager.team_weight);
  assert.equal(matchEvaluator.orientationSimilarityThreshold, config.recon_runtime.match_evaluator.orientation_similarity_threshold);
  assert.equal(taskPlanner.archiveTimeoutMs, config.recon_runtime.task_planner.archive_timeout_ms);
  assert.equal(taskPlanner.resultsPathTemplate, config.recon_runtime.task_planner.results_path);
  assert.equal(browserContext.warmupDelayMs, config.recon_runtime.browser_context.warmup_delay_ms);
  assert.deepEqual(browserContext.viewport, config.recon_runtime.browser_context.viewport);
  assert.equal(browserContext.enableStealthFingerprint, true);
  assert.match(browserContext.userAgent, /Chrome\/131\.0\.0\.0/);
  assert.equal(browserContext.locale, 'en-US');
  assert.equal(browserContext.timezoneId, 'Europe/London');
  assert.equal(browserContext.homeWarmupEnabled, config.recon_runtime.network_monitor.home_warmup_enabled);
  assert.equal(networkMonitor.scriptEvalTimeoutMs, config.recon_runtime.network_monitor.script_eval_timeout_ms);
  assert.equal(networkMonitor.fetchTimeoutMs, config.recon_runtime.network_monitor.fetch_timeout_ms);
  assert.equal(domScraper.scrollAttempts, config.recon_runtime.dom_scraper.scroll_attempts);
  assert.equal(domScraper.postNavigationWaitMs, config.recon_runtime.dom_scraper.post_navigation_wait_ms);
  assert.equal(stateProber.timeoutMs, config.recon_runtime.state_prober.timeout_ms);
  assert.equal(stateProber.postNavigationWaitMs, config.recon_runtime.state_prober.post_navigation_wait_ms);
});

test('ReconServiceConfig.validateConfig 在关键字段类型非法时必须 fail-fast 并指出字段名', () => {
  const invalidConfig = structuredClone(config);
  invalidConfig.recon_runtime.state_prober.max_pages = 'invalid';

  assert.throws(
    () => validateConfig(invalidConfig, { configPath: '/tmp/recon_config.invalid.json' }),
    (error) => {
      assert.equal(error instanceof ReconConfigValidationError, true);
      assert.equal(error.code, 'FATAL_CONFIG');
      assert.equal(error.field, 'recon_runtime.state_prober.max_pages');
      assert.match(error.message, /recon_runtime\.state_prober\.max_pages/);
      return true;
    }
  );
});

test('ReconServiceConfig.validateConfig 在 conflict arbiter 阈值类型非法时必须 fail-fast 并指出字段名', () => {
  const invalidConfig = structuredClone(config);
  invalidConfig.repository.conflict_arbiter.same_fixture_threshold = 'invalid';

  assert.throws(
    () => validateConfig(invalidConfig, { configPath: '/tmp/recon_config.invalid_conflict_arbiter.json' }),
    (error) => {
      assert.equal(error instanceof ReconConfigValidationError, true);
      assert.equal(error.code, 'FATAL_CONFIG');
      assert.equal(error.field, 'repository.conflict_arbiter.same_fixture_threshold');
      assert.match(error.message, /repository\.conflict_arbiter\.same_fixture_threshold/);
      return true;
    }
  );
});

test('ReconServiceConfig.validateConfig 在 identity_inactive_statuses 缺失时必须 fail-fast', () => {
  const invalidConfig = structuredClone(config);
  delete invalidConfig.repository.identity_inactive_statuses;

  assert.throws(
    () => validateConfig(invalidConfig, { configPath: '/tmp/recon_config.missing_identity_statuses.json' }),
    (error) => {
      assert.equal(error instanceof ReconConfigValidationError, true);
      assert.equal(error.field, 'repository.identity_inactive_statuses');
      assert.match(error.message, /repository\.identity_inactive_statuses/);
      return true;
    }
  );
});

test('ReconServiceConfig.validateConfig 在缺少关键配置节时必须 fail-fast', () => {
  const invalidConfig = structuredClone(config);
  delete invalidConfig.recon_runtime.browser_context;

  assert.throws(
    () => validateConfig(invalidConfig, { configPath: '/tmp/recon_config.missing.json' }),
    (error) => {
      assert.equal(error instanceof ReconConfigValidationError, true);
      assert.equal(error.field, 'recon_runtime.browser_context.launch_timeout_ms');
      assert.match(error.message, /缺少必填配置/);
      return true;
    }
  );
});

test('ReconServiceConfig.validateConfig 在缺少新引入的高仿真字段时仍应使用默认保护', () => {
  const backwardCompatibleConfig = structuredClone(config);
  delete backwardCompatibleConfig.recon_runtime.browser_context.enable_stealth_fingerprint;
  delete backwardCompatibleConfig.recon_runtime.network_monitor.home_warmup_enabled;
  delete backwardCompatibleConfig.recon_runtime.network_monitor.home_warmup_url;
  delete backwardCompatibleConfig.recon_runtime.network_monitor.home_warmup_wait_ms;

  assert.doesNotThrow(() => validateConfig(backwardCompatibleConfig, {
    configPath: '/tmp/recon_config.backward-compatible.json'
  }));
});

test('ReconServiceConfig.resolveRuntimeFeatureFlags 应支持环境变量覆盖配置开关', () => {
  const featureFlags = resolveRuntimeFeatureFlags({
    DISABLE_DOM_FALLBACK: 'true',
    RECON_STRATEGY: 'legacy'
  }, config);

  assert.deepEqual(featureFlags, {
    disableDomFallback: true,
    reconStrategy: 'legacy'
  });
});

test('ReconServiceConfig 应解析 external_session_path 环境变量占位符', () => {
  const resolved = resolveEnvPlaceholders({
    recon_runtime: {
      browser_context: {
        external_session_path: '${RECON_SESSION_PATH}'
      }
    }
  });

  assert.equal(resolved.recon_runtime.browser_context.external_session_path, '');
});

test('ReconServiceConfig.loadReconConfig 应使用 RECON_SESSION_PATH 覆盖 external_session_path', () => {
  const originalPath = process.env.RECON_SESSION_PATH;
  process.env.RECON_SESSION_PATH = '/app/runtime/session.txt';

  try {
    const loaded = loadReconConfig();
    assert.equal(loaded.recon_runtime.browser_context.external_session_path, '/app/runtime/session.txt');
  } finally {
    if (originalPath === undefined) {
      delete process.env.RECON_SESSION_PATH;
    } else {
      process.env.RECON_SESSION_PATH = originalPath;
    }
  }
});
