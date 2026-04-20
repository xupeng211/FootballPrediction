/* eslint-disable complexity, max-lines */
'use strict';

const fs = require('fs');
const path = require('path');

const DEFAULT_RECON_CONFIG_PATH = path.resolve(__dirname, '../../../../config/recon_config.json');
const VALID_RECON_STRATEGIES = new Set(['v11', 'legacy']);

class ReconConfigValidationError extends Error {
  constructor(message, field = null, configPath = DEFAULT_RECON_CONFIG_PATH, cause = null) {
    super(message);
    this.name = 'ReconConfigValidationError';
    this.code = 'FATAL_CONFIG';
    this.field = field;
    this.configPath = configPath;
    this.cause = cause || null;
  }
}

function buildFieldError(fieldPath, message, configPath, cause = null) {
  const suffix = fieldPath ? ` [field=${fieldPath}]` : '';
  return new ReconConfigValidationError(`[FATAL_CONFIG] ${message}${suffix}`, fieldPath, configPath, cause);
}

function readConfigFile(configPath = DEFAULT_RECON_CONFIG_PATH) {
  const effectiveConfigPath = configPath || DEFAULT_RECON_CONFIG_PATH;

  try {
    const raw = fs.readFileSync(effectiveConfigPath, 'utf8');
    return resolveEnvPlaceholders(JSON.parse(raw));
  } catch (error) {
    throw buildFieldError(
      null,
      `recon_config.json 加载失败: ${error.message}`,
      effectiveConfigPath,
      error
    );
  }
}

function resolveEnvPlaceholders(value) {
  if (Array.isArray(value)) {
    return value.map((item) => resolveEnvPlaceholders(item));
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, nestedValue]) => [key, resolveEnvPlaceholders(nestedValue)])
    );
  }

  if (typeof value !== 'string') {
    return value;
  }

  return value.replace(/\$\{([A-Z0-9_]+)\}/g, (_match, envName) => process.env[envName] || '');
}

function getNestedValue(root, pathSegments = []) {
  return pathSegments.reduce((current, segment) => (
    current && Object.prototype.hasOwnProperty.call(current, segment)
      ? current[segment]
      : undefined
  ), root);
}

function assertObject(value, fieldPath, configPath) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw buildFieldError(fieldPath, '必须是对象', configPath);
  }
}

function assertString(value, fieldPath, configPath, { allowEmpty = false } = {}) {
  if (typeof value !== 'string') {
    throw buildFieldError(fieldPath, '必须是字符串', configPath);
  }

  if (!allowEmpty && value.trim() === '') {
    throw buildFieldError(fieldPath, '不能为空字符串', configPath);
  }
}

function assertBoolean(value, fieldPath, configPath) {
  if (typeof value !== 'boolean') {
    throw buildFieldError(fieldPath, '必须是布尔值', configPath);
  }
}

function assertFiniteNumber(value, fieldPath, configPath, { integer = false, min = null, max = null } = {}) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw buildFieldError(fieldPath, '必须是有限数字', configPath);
  }

  if (integer && !Number.isInteger(value)) {
    throw buildFieldError(fieldPath, '必须是整数', configPath);
  }

  if (min !== null && value < min) {
    throw buildFieldError(fieldPath, `必须大于等于 ${min}`, configPath);
  }

  if (max !== null && value > max) {
    throw buildFieldError(fieldPath, `必须小于等于 ${max}`, configPath);
  }
}

function assertArray(value, fieldPath, configPath, { minLength = 0 } = {}) {
  if (!Array.isArray(value)) {
    throw buildFieldError(fieldPath, '必须是数组', configPath);
  }

  if (value.length < minLength) {
    throw buildFieldError(fieldPath, `至少需要 ${minLength} 个元素`, configPath);
  }
}

function assertStringArray(value, fieldPath, configPath, { allowEmpty = false, minLength = 0 } = {}) {
  assertArray(value, fieldPath, configPath, { minLength });
  value.forEach((item, index) => {
    assertString(item, `${fieldPath}[${index}]`, configPath, { allowEmpty });
  });
}

function assertObjectArray(value, fieldPath, configPath, { minLength = 0 } = {}) {
  assertArray(value, fieldPath, configPath, { minLength });
  value.forEach((item, index) => {
    assertObject(item, `${fieldPath}[${index}]`, configPath);
  });
}

function assertRequired(root, pathSegments, configPath) {
  const fieldPath = pathSegments.join('.');
  const value = getNestedValue(root, pathSegments);
  if (value === undefined) {
    throw buildFieldError(fieldPath, '缺少必填配置', configPath);
  }
  return value;
}

function validateThreshold(value, fieldPath, configPath) {
  assertFiniteNumber(value, fieldPath, configPath, { min: 0, max: 1 });
}

function validateConfig(config, options = {}) {
  const configPath = options.configPath || DEFAULT_RECON_CONFIG_PATH;
  assertObject(config, 'root', configPath);

  const oddsportal = assertRequired(config, ['oddsportal'], configPath);
  assertObject(oddsportal, 'oddsportal', configPath);
  assertString(assertRequired(config, ['oddsportal', 'base_url'], configPath), 'oddsportal.base_url', configPath);
  assertString(assertRequired(config, ['oddsportal', 'results_path'], configPath), 'oddsportal.results_path', configPath);

  const repository = assertRequired(config, ['repository'], configPath);
  assertObject(repository, 'repository', configPath);
  assertFiniteNumber(assertRequired(config, ['repository', 'batch_size'], configPath), 'repository.batch_size', configPath, { integer: true, min: 1 });
  assertFiniteNumber(assertRequired(config, ['repository', 'pool', 'max'], configPath), 'repository.pool.max', configPath, { integer: true, min: 1 });
  assertFiniteNumber(assertRequired(config, ['repository', 'pool', 'idle_timeout_ms'], configPath), 'repository.pool.idle_timeout_ms', configPath, { integer: true, min: 0 });
  assertFiniteNumber(assertRequired(config, ['repository', 'retry', 'max_retries'], configPath), 'repository.retry.max_retries', configPath, { integer: true, min: 1 });
  assertFiniteNumber(assertRequired(config, ['repository', 'retry', 'retry_delay_ms'], configPath), 'repository.retry.retry_delay_ms', configPath, { integer: true, min: 0 });
  assertFiniteNumber(assertRequired(config, ['repository', 'retry', 'max_retry_window_ms'], configPath), 'repository.retry.max_retry_window_ms', configPath, { integer: true, min: 1 });
  assertFiniteNumber(assertRequired(config, ['repository', 'retry', 'backoff_multiplier'], configPath), 'repository.retry.backoff_multiplier', configPath, { min: 0 });
  assertFiniteNumber(
    assertRequired(config, ['repository', 'conflict_arbiter', 'same_fixture_threshold'], configPath),
    'repository.conflict_arbiter.same_fixture_threshold',
    configPath,
    { min: 0, max: 2 }
  );
  assertFiniteNumber(
    assertRequired(config, ['repository', 'conflict_arbiter', 'same_fixture_window_ms'], configPath),
    'repository.conflict_arbiter.same_fixture_window_ms',
    configPath,
    { integer: true, min: 1 }
  );
  assertFiniteNumber(
    assertRequired(config, ['repository', 'conflict_arbiter', 'linked_rebind_min_date_gap_ms'], configPath),
    'repository.conflict_arbiter.linked_rebind_min_date_gap_ms',
    configPath,
    { integer: true, min: 1 }
  );
  validateThreshold(
    assertRequired(config, ['repository', 'conflict_arbiter', 'linked_rebind_min_incoming_confidence'], configPath),
    'repository.conflict_arbiter.linked_rebind_min_incoming_confidence',
    configPath
  );
  validateThreshold(
    assertRequired(config, ['repository', 'conflict_arbiter', 'linked_rebind_min_confidence_delta'], configPath),
    'repository.conflict_arbiter.linked_rebind_min_confidence_delta',
    configPath
  );
  assertFiniteNumber(
    assertRequired(config, ['repository', 'conflict_arbiter', 'linked_rebind_min_score_delta'], configPath),
    'repository.conflict_arbiter.linked_rebind_min_score_delta',
    configPath,
    { min: 0, max: 2 }
  );
  assertStringArray(
    assertRequired(config, ['repository', 'identity_inactive_statuses'], configPath),
    'repository.identity_inactive_statuses',
    configPath,
    { minLength: 1 }
  );

  const matching = assertRequired(config, ['matching'], configPath);
  assertObject(matching, 'matching', configPath);
  validateThreshold(assertRequired(config, ['matching', 'confidence_threshold'], configPath), 'matching.confidence_threshold', configPath);
  validateThreshold(assertRequired(config, ['matching', 'orientation_similarity_threshold'], configPath), 'matching.orientation_similarity_threshold', configPath);
  validateThreshold(assertRequired(config, ['matching', 'exact_match_threshold'], configPath), 'matching.exact_match_threshold', configPath);
  validateThreshold(assertRequired(config, ['matching', 'team_weight'], configPath), 'matching.team_weight', configPath);
  validateThreshold(assertRequired(config, ['matching', 'date_weight'], configPath), 'matching.date_weight', configPath);
  const dateConfidenceBands = assertRequired(config, ['matching', 'date_confidence_bands'], configPath);
  assertObjectArray(dateConfidenceBands, 'matching.date_confidence_bands', configPath, { minLength: 1 });
  dateConfidenceBands.forEach((band, index) => {
    assertFiniteNumber(
      assertRequired(config, ['matching', 'date_confidence_bands', index, 'max_diff_days'], configPath),
      `matching.date_confidence_bands[${index}].max_diff_days`,
      configPath,
      { min: 0 }
    );
    validateThreshold(
      assertRequired(config, ['matching', 'date_confidence_bands', index, 'score'], configPath),
      `matching.date_confidence_bands[${index}].score`,
      configPath
    );
  });
  assertStringArray(assertRequired(config, ['matching', 'common_suffixes'], configPath), 'matching.common_suffixes', configPath, { minLength: 1 });

  const reconRuntime = assertRequired(config, ['recon_runtime'], configPath);
  assertObject(reconRuntime, 'recon_runtime', configPath);

  const runtimeNumberFields = [
    ['engine', 'recon_batch_size', { integer: true, min: 1 }],
    ['engine', 'default_concurrency', { integer: true, min: 1 }],
    ['engine', 'adaptive_concurrency_initial', { integer: true, min: 1 }],
    ['engine', 'adaptive_concurrency_success_window', { integer: true, min: 1 }],
    ['engine', 'suspend_proxy_threshold', { integer: true, min: 1 }],
    ['engine', 'suspend_poll_interval_ms', { integer: true, min: 1 }],
    ['engine', 'proxy_min_health_score', { integer: true, min: 1, max: 100 }],
    ['engine', 'proxy_critical_error_cooldown_ms', { integer: true, min: 1 }],
    ['engine', 'confidence_threshold', { min: 0, max: 1 }],
    ['engine', 'archive_max_pages', { integer: true, min: 1 }],
    ['engine', 'archive_timeout_ms', { integer: true, min: 1 }],
    ['engine', 'page_settle_wait_ms', { integer: true, min: 0 }],
    ['engine', 'dom_scroll_step_px', { integer: true, min: 1 }],
    ['engine', 'dom_scroll_delay_ms', { integer: true, min: 0 }],
    ['engine', 'progress_log_every', { integer: true, min: 1 }],
    ['engine', 'progress_high_success_threshold', { min: 0, max: 1 }],
    ['engine', 'progress_sample_multiplier', { integer: true, min: 1 }],
    ['navigator', 'scroll_attempts', { integer: true, min: 1 }],
    ['navigator', 'scroll_delay_ms', { integer: true, min: 0 }],
    ['navigator', 'launch_timeout_ms', { integer: true, min: 1 }],
    ['navigator', 'navigation_timeout_ms', { integer: true, min: 1 }],
    ['navigator', 'warmup_delay_ms', { integer: true, min: 0 }],
    ['navigator', 'scroll_iterations', { integer: true, min: 1 }],
    ['navigator', 'scroll_step_px', { integer: true, min: 1 }],
    ['navigator', 'navigate_scroll_delay_ms', { integer: true, min: 0 }],
    ['navigator', 'archive_max_pages', { integer: true, min: 1 }],
    ['navigator', 'archive_timeout_ms', { integer: true, min: 1 }],
    ['navigator', 'post_api_discovery_wait_ms', { integer: true, min: 0 }],
    ['navigator', 'page_revisit_wait_ms', { integer: true, min: 0 }],
    ['navigator', 'circuit_breaker', 'failure_threshold', { integer: true, min: 1 }],
    ['navigator', 'circuit_breaker', 'reset_timeout_ms', { integer: true, min: 1 }],
    ['protocol_fetch', 'fetch_max_attempts', { integer: true, min: 1 }],
    ['protocol_fetch', 'fetch_retry_delay_ms', { integer: true, min: 0 }],
    ['protocol_fetch', 'sample_proxy_failover_max_attempts', { integer: true, min: 1 }],
    ['protocol_fetch', 'sample_proxy_failover_retry_delay_ms', { integer: true, min: 0 }],
    ['protocol_fetch', 'sample_fetch_attempts_per_proxy', { integer: true, min: 1 }],
    ['browser_context', 'launch_timeout_ms', { integer: true, min: 1 }],
    ['browser_context', 'navigation_timeout_ms', { integer: true, min: 1 }],
    ['browser_context', 'warmup_delay_ms', { integer: true, min: 0 }],
    ['browser_context', 'scroll_iterations', { integer: true, min: 1 }],
    ['browser_context', 'scroll_step_px', { integer: true, min: 1 }],
    ['browser_context', 'scroll_delay_ms', { integer: true, min: 0 }],
    ['browser_context', 'consent_visibility_timeout_ms', { integer: true, min: 0 }],
    ['browser_context', 'consent_click_timeout_ms', { integer: true, min: 0 }],
    ['browser_context', 'consent_post_click_wait_ms', { integer: true, min: 0 }],
    ['browser_context', 'close_timeout_ms', { integer: true, min: 1 }],
    ['task_planner', 'sample_size', { integer: true, min: 1 }],
    ['task_planner', 'archive_max_pages', { integer: true, min: 1 }],
    ['task_planner', 'archive_timeout_ms', { integer: true, min: 1 }],
    ['match_evaluator', 'orientation_similarity_threshold', { min: 0, max: 1 }],
    ['match_evaluator', 'exact_match_threshold', { min: 0, max: 1 }],
    ['match_evaluator', 'team_weight', { min: 0, max: 1 }],
    ['match_evaluator', 'date_weight', { min: 0, max: 1 }],
    ['mirror_manager', 'team_weight', { min: 0, max: 1 }],
    ['mirror_manager', 'date_weight', { min: 0, max: 1 }],
    ['network_monitor', 'script_eval_timeout_ms', { integer: true, min: 1 }],
    ['network_monitor', 'extract_max_depth', { integer: true, min: 1 }],
    ['network_monitor', 'page_size', { integer: true, min: 1 }],
    ['network_monitor', 'fetch_timeout_ms', { integer: true, min: 1 }],
    ['network_monitor', 'decrypt_timeout_ms', { integer: true, min: 1 }],
    ['dom_scraper', 'timeout_ms', { integer: true, min: 1 }],
    ['dom_scraper', 'max_pages', { integer: true, min: 1 }],
    ['dom_scraper', 'post_navigation_wait_ms', { integer: true, min: 0 }],
    ['dom_scraper', 'scroll_attempts', { integer: true, min: 1 }],
    ['dom_scraper', 'scroll_delay_ms', { integer: true, min: 0 }],
    ['dom_scraper', 'min_scroll_rounds', { integer: true, min: 1 }],
    ['dom_scraper', 'stagnant_rounds_threshold', { integer: true, min: 0 }],
    ['dom_scraper', 'page_scroll_floor_px', { integer: true, min: 1 }],
    ['dom_scraper', 'page_scroll_step_base_px', { integer: true, min: 1 }],
    ['dom_scraper', 'page_scroll_wait_cap_ms', { integer: true, min: 0 }],
    ['dom_scraper', 'page_scroll_wait_ms', { integer: true, min: 0 }],
    ['dom_scraper', 'wake_mouse_x', { integer: true, min: 0 }],
    ['dom_scraper', 'wake_mouse_y', { integer: true, min: 0 }],
    ['dom_scraper', 'wake_scroll_step_px', { integer: true, min: 1 }],
    ['state_prober', 'timeout_ms', { integer: true, min: 1 }],
    ['state_prober', 'max_pages', { integer: true, min: 1 }],
    ['state_prober', 'post_navigation_wait_ms', { integer: true, min: 0 }]
  ];

  runtimeNumberFields.forEach((parts) => {
    const optionsForField = parts[parts.length - 1];
    const fieldPathParts = parts.slice(0, -1);
    const fieldPath = ['recon_runtime', ...fieldPathParts].join('.');
    const value = assertRequired(config, ['recon_runtime', ...fieldPathParts], configPath);
    assertFiniteNumber(value, fieldPath, configPath, optionsForField);
  });

  assertString(assertRequired(config, ['recon_runtime', 'navigator', 'base_url'], configPath), 'recon_runtime.navigator.base_url', configPath);
  assertString(assertRequired(config, ['recon_runtime', 'browser_context', 'user_agent'], configPath), 'recon_runtime.browser_context.user_agent', configPath);
  assertObject(assertRequired(config, ['recon_runtime', 'browser_context', 'viewport'], configPath), 'recon_runtime.browser_context.viewport', configPath);
  assertFiniteNumber(assertRequired(config, ['recon_runtime', 'browser_context', 'viewport', 'width'], configPath), 'recon_runtime.browser_context.viewport.width', configPath, { integer: true, min: 1 });
  assertFiniteNumber(assertRequired(config, ['recon_runtime', 'browser_context', 'viewport', 'height'], configPath), 'recon_runtime.browser_context.viewport.height', configPath, { integer: true, min: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'browser_context', 'launch_args'], configPath), 'recon_runtime.browser_context.launch_args', configPath);
  assertStringArray(assertRequired(config, ['recon_runtime', 'browser_context', 'consent_labels'], configPath), 'recon_runtime.browser_context.consent_labels', configPath, { minLength: 1 });
  const externalSessionPath = getNestedValue(config, ['recon_runtime', 'browser_context', 'external_session_path']);
  if (externalSessionPath !== undefined) {
    assertString(externalSessionPath, 'recon_runtime.browser_context.external_session_path', configPath, { allowEmpty: true });
  }
  const executablePath = getNestedValue(config, ['recon_runtime', 'browser_context', 'executable_path']);
  if (executablePath !== undefined) {
    assertString(executablePath, 'recon_runtime.browser_context.executable_path', configPath, { allowEmpty: true });
  }
  const cachePath = getNestedValue(config, ['recon_runtime', 'browser_context', 'cache_path']);
  if (cachePath !== undefined) {
    assertString(cachePath, 'recon_runtime.browser_context.cache_path', configPath, { allowEmpty: true });
  }
  assertString(assertRequired(config, ['recon_runtime', 'task_planner', 'base_url'], configPath), 'recon_runtime.task_planner.base_url', configPath);
  assertString(assertRequired(config, ['recon_runtime', 'task_planner', 'results_path'], configPath), 'recon_runtime.task_planner.results_path', configPath);
  assertString(assertRequired(config, ['recon_runtime', 'dom_scraper', 'base_url'], configPath), 'recon_runtime.dom_scraper.base_url', configPath);
  assertStringArray(assertRequired(config, ['recon_runtime', 'network_monitor', 'match_api_patterns'], configPath), 'recon_runtime.network_monitor.match_api_patterns', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'network_monitor', 'script_wrapper_patterns'], configPath), 'recon_runtime.network_monitor.script_wrapper_patterns', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'network_monitor', 'known_error_patterns'], configPath), 'recon_runtime.network_monitor.known_error_patterns', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'dom_scraper', 'result_anchor_selectors'], configPath), 'recon_runtime.dom_scraper.result_anchor_selectors', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'dom_scraper', 'pagination_selectors'], configPath), 'recon_runtime.dom_scraper.pagination_selectors', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'dom_scraper', 'home_selectors'], configPath), 'recon_runtime.dom_scraper.home_selectors', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'dom_scraper', 'away_selectors'], configPath), 'recon_runtime.dom_scraper.away_selectors', configPath, { minLength: 1 });
  assertStringArray(assertRequired(config, ['recon_runtime', 'dom_scraper', 'participant_selectors'], configPath), 'recon_runtime.dom_scraper.participant_selectors', configPath, { minLength: 1 });

  const enableStealthFingerprint = getNestedValue(config, ['recon_runtime', 'browser_context', 'enable_stealth_fingerprint']);
  if (enableStealthFingerprint !== undefined) {
    assertBoolean(enableStealthFingerprint, 'recon_runtime.browser_context.enable_stealth_fingerprint', configPath);
  }
  const homeWarmupEnabled = getNestedValue(config, ['recon_runtime', 'network_monitor', 'home_warmup_enabled']);
  if (homeWarmupEnabled !== undefined) {
    assertBoolean(homeWarmupEnabled, 'recon_runtime.network_monitor.home_warmup_enabled', configPath);
  }
  const homeWarmupUrl = getNestedValue(config, ['recon_runtime', 'network_monitor', 'home_warmup_url']);
  if (homeWarmupUrl !== undefined) {
    assertString(homeWarmupUrl, 'recon_runtime.network_monitor.home_warmup_url', configPath);
  }
  const homeWarmupWaitMs = getNestedValue(config, ['recon_runtime', 'network_monitor', 'home_warmup_wait_ms']);
  if (homeWarmupWaitMs !== undefined) {
    assertFiniteNumber(homeWarmupWaitMs, 'recon_runtime.network_monitor.home_warmup_wait_ms', configPath, { integer: true, min: 0 });
  }
  const unlockStrategies = getNestedValue(config, ['recon_runtime', 'unlock_strategies']);
  if (unlockStrategies !== undefined) {
    assertObject(unlockStrategies, 'recon_runtime.unlock_strategies', configPath);
  }
  const forceUnlockJ1 = getNestedValue(config, ['recon_runtime', 'unlock_strategies', 'force_unlock_j1']);
  if (forceUnlockJ1 !== undefined) {
    assertObject(forceUnlockJ1, 'recon_runtime.unlock_strategies.force_unlock_j1', configPath);
    const enabled = getNestedValue(config, ['recon_runtime', 'unlock_strategies', 'force_unlock_j1', 'enabled']);
    if (enabled !== undefined) {
      assertBoolean(enabled, 'recon_runtime.unlock_strategies.force_unlock_j1.enabled', configPath);
    }
    const stringArrayFields = [
      'url_patterns',
      'menu_labels',
      'select_all_labels',
      'fallback_bookmakers'
    ];
    for (const fieldName of stringArrayFields) {
      const value = getNestedValue(config, ['recon_runtime', 'unlock_strategies', 'force_unlock_j1', fieldName]);
      if (value !== undefined) {
        assertStringArray(
          value,
          `recon_runtime.unlock_strategies.force_unlock_j1.${fieldName}`,
          configPath,
          { allowEmpty: true }
        );
      }
    }
    const timeoutFields = [
      'open_wait_ms',
      'post_select_wait_ms',
      'state_wait_ms',
      'retrigger_timeout_ms'
    ];
    for (const fieldName of timeoutFields) {
      const value = getNestedValue(config, ['recon_runtime', 'unlock_strategies', 'force_unlock_j1', fieldName]);
      if (value !== undefined) {
        assertFiniteNumber(
          value,
          `recon_runtime.unlock_strategies.force_unlock_j1.${fieldName}`,
          configPath,
          { integer: true, min: 0 }
        );
      }
    }
  }

  const featureFlags = config.feature_flags || {};
  assertObject(featureFlags, 'feature_flags', configPath);
  assertBoolean(assertRequired(config, ['feature_flags', 'disable_dom_fallback'], configPath), 'feature_flags.disable_dom_fallback', configPath);
  const reconStrategy = assertRequired(config, ['feature_flags', 'recon_strategy'], configPath);
  assertString(reconStrategy, 'feature_flags.recon_strategy', configPath);
  if (!VALID_RECON_STRATEGIES.has(reconStrategy)) {
    throw buildFieldError('feature_flags.recon_strategy', `必须为 ${[...VALID_RECON_STRATEGIES].join(' / ')}`, configPath);
  }

  const reconThreshold = getNestedValue(config, ['automation', 'total_war', 'recon_threshold']);
  if (reconThreshold !== undefined) {
    assertFiniteNumber(reconThreshold, 'automation.total_war.recon_threshold', configPath, { integer: true, min: 1 });
  }
  const logMaxBytes = getNestedValue(config, ['automation', 'total_war', 'log_max_bytes']);
  if (logMaxBytes !== undefined) {
    assertFiniteNumber(logMaxBytes, 'automation.total_war.log_max_bytes', configPath, { integer: true, min: 1 });
  }
  const logRetainedFiles = getNestedValue(config, ['automation', 'total_war', 'log_retained_files']);
  if (logRetainedFiles !== undefined) {
    assertFiniteNumber(logRetainedFiles, 'automation.total_war.log_retained_files', configPath, { integer: true, min: 1 });
  }

  return config;
}

function loadReconConfig(configPath = process.env.RECON_CONFIG_PATH || DEFAULT_RECON_CONFIG_PATH) {
  return validateConfig(readConfigFile(configPath), { configPath });
}

function getReconConfigSection(pathSegments = [], fallback = {}) {
  const resolved = getNestedValue(RECON_CONFIG, pathSegments);
  if (resolved === undefined) {
    return fallback;
  }

  return resolved;
}

function parseBooleanEnvValue(rawValue, fieldName) {
  if (rawValue === undefined || rawValue === null || rawValue === '') {
    return undefined;
  }

  const normalized = String(rawValue).trim().toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(normalized)) {
    return true;
  }
  if (['0', 'false', 'no', 'off'].includes(normalized)) {
    return false;
  }

  throw buildFieldError(fieldName, '环境变量必须是布尔值 (true/false)', DEFAULT_RECON_CONFIG_PATH);
}

function getFeatureFlags(config = RECON_CONFIG) {
  const featureFlags = config?.feature_flags || {};
  return {
    disableDomFallback: featureFlags.disable_dom_fallback === true,
    reconStrategy: featureFlags.recon_strategy || 'v11'
  };
}

function resolveReconStrategy(envValue = process.env.RECON_STRATEGY, configValue = getFeatureFlags().reconStrategy) {
  const resolved = envValue || configValue || 'v11';
  if (!VALID_RECON_STRATEGIES.has(resolved)) {
    throw buildFieldError('RECON_STRATEGY', `环境变量必须为 ${[...VALID_RECON_STRATEGIES].join(' / ')}`, DEFAULT_RECON_CONFIG_PATH);
  }
  return resolved;
}

function resolveRuntimeFeatureFlags(env = process.env, config = RECON_CONFIG) {
  const configFlags = getFeatureFlags(config);
  const disableDomFallback = parseBooleanEnvValue(env.DISABLE_DOM_FALLBACK, 'DISABLE_DOM_FALLBACK');

  return {
    disableDomFallback: disableDomFallback ?? configFlags.disableDomFallback,
    reconStrategy: resolveReconStrategy(env.RECON_STRATEGY, configFlags.reconStrategy)
  };
}

const RECON_CONFIG = loadReconConfig();

module.exports = {
  DEFAULT_RECON_CONFIG_PATH,
  RECON_CONFIG,
  ReconConfigValidationError,
  getFeatureFlags,
  getNestedValue,
  getReconConfigSection,
  loadReconConfig,
  resolveReconStrategy,
  resolveRuntimeFeatureFlags,
  resolveEnvPlaceholders,
  validateConfig
};
