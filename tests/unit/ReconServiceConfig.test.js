'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const config = require('../../config/recon_config.json');
const {
  ReconConfigValidationError,
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

test('Recon services 应默认从 recon_config.json 读取运行时参数', async () => {
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
