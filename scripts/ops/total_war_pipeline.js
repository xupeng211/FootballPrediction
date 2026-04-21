#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
/**
 * @file total_war_pipeline.js
 * @description TOTAL WAR 自动编排器，串行调度 Discovery / Harvest / Recon
 */

'use strict';

/* eslint-disable jsdoc/require-jsdoc */

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { Pool } = require('pg');
const { ProcessSupervisor } = require('../../src/core/process/ProcessSupervisor');
const { ReconSessionManager } = require('../../src/infrastructure/recon/services/ReconSessionManager');
const { TitanLogger } = require('../../src/infrastructure/utils/TitanLogger');

const ROOT_DIR = path.resolve(__dirname, '../..');
const RUNTIME_DIR = path.join(ROOT_DIR, 'tmp', 'total_war_pipeline');
const STATE_PATH = path.join(RUNTIME_DIR, 'state.json');
const LOCK_PATH = path.join(RUNTIME_DIR, 'pipeline.lock');
const LOG_PATH = path.join(RUNTIME_DIR, 'pipeline.log');
const RECON_SESSION_BUFFER_PATH = path.join(RUNTIME_DIR, 'recon_session_buffer_pool.json');
const DEFAULT_RECON_CONFIG_PATH = path.join(ROOT_DIR, 'config', 'recon_config.json');
const DEFAULT_LOG_MAX_BYTES = 100 * 1024 * 1024;
const DEFAULT_LOG_RETAINED_FILES = 5;
const DEFAULT_RECON_PREFLIGHT_WAIT_MS = 2000;
const DEFAULT_RECON_SESSION_BUFFER_TTL_MS = 30 * 60 * 1000;

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function ensureRuntimeDir() {
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
}

function writeToStream(stream, message) {
  const normalizedMessage = String(message ?? '');
  const payload = normalizedMessage.endsWith('\n')
    ? normalizedMessage
    : `${normalizedMessage}\n`;
  if (stream && typeof stream.write === 'function') {
    stream.write(payload);
    return;
  }

  process.stdout.write(payload);
}

function showHelp(output = process.stdout) {
  writeToStream(output, `
TOTAL WAR PIPELINE - 24 小时自动编排器

用法:
  node scripts/ops/total_war_pipeline.js --season 2025/2026 [选项]

选项:
  --season=SEASON            赛季，支持 2025/2026 或 2025-2026
  --loop-ms=N                主循环间隔，默认 60000
  --discovery-interval-ms=N  Discovery 间隔，默认 3600000
  --discovery-concurrency=N  Discovery 并发，默认 5
  --concurrency=N            主任务并发别名，同时设置 Harvest/Recon 并发
  --harvest-concurrency=N    Harvest 并发，默认 10
  --harvest-limit=N          Harvest 单批上限，默认 500
  --recon-concurrency=N      Recon 并发，默认 5
  --recon-limit=N            Recon 单批上限，默认读取配置
  --recon-threshold=N        触发 Recon 的新增 raw 阈值，默认 50
  --threshold=0.X            Recon 匹配置信度阈值，透传给 recon_scanner
  --task-stage=STAGE         指定阶段: auto|discovery|harvest|recon，默认 auto
  --skip-leagues=LIST        Recon 跳过联赛（逗号分隔，可重复）
  --include-all-leagues      Recon 忽略默认 skip_list，显式纳入全部联赛
  --retry-failed-only        仅执行 pending/harvested/mismatch 收尾，不再触发 Discovery
  --mismatch-retry-only      Recon 仅重扫 RECON_MISMATCH
  --recon-defer-cooldown-ms  Recon 因 LEAGUE_TIMEOUT 延迟重试时长，默认 600000ms
  --use-proxy                Recon 子任务显式启用代理
  --force-pure-protocol      Recon 子任务强制 pure protocol
  --failure-limit=N          连续失败熔断阈值，默认 3
  --failure-cooldown-ms=N    失败熔断冷却时间，默认 1800000
  --once                     只执行一个调度周期
  --dry-run                  只输出将执行的任务，不真正启动子任务
  --help, -h                 显示帮助

示例:
  node scripts/ops/total_war_pipeline.js --season 2025/2026
  node scripts/ops/total_war_pipeline.js --season 2025/2026 --once --dry-run
`);
}

function parseCommaSeparatedList(value) {
  if (!value) {
    return [];
  }

  return String(value)
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function mergeLeagueLists(...lists) {
  const merged = [];
  for (const list of lists) {
    for (const item of Array.isArray(list) ? list : []) {
      const normalized = String(item || '').trim();
      if (!normalized || merged.includes(normalized)) {
        continue;
      }
      merged.push(normalized);
    }
  }
  return merged;
}

function normalizeTaskStage(value) {
  const normalized = String(value || 'auto').trim().toLowerCase();
  const allowedStages = new Set(['auto', 'discovery', 'harvest', 'recon']);
  if (allowedStages.has(normalized)) {
    return normalized;
  }
  throw new Error(`不支持的 --task-stage: ${value}`);
}

function getDefaultReconThreshold() {
  const config = readReconConfigFile();
  const envThreshold = parseInt(process.env.RECON_THRESHOLD || '', 10);
  if (Number.isInteger(envThreshold) && envThreshold > 0) {
    return envThreshold;
  }

  const configThreshold = Number(config?.automation?.total_war?.recon_threshold);
  if (Number.isInteger(configThreshold) && configThreshold > 0) {
    return configThreshold;
  }

  return 50;
}

function getDefaultReconLimit() {
  const config = readReconConfigFile();
  const envLimit = parseInt(process.env.RECON_LIMIT || '', 10);
  if (Number.isInteger(envLimit) && envLimit > 0) {
    return envLimit;
  }

  const configLimit = Number(config?.automation?.total_war?.recon_limit);
  if (Number.isInteger(configLimit) && configLimit > 0) {
    return configLimit;
  }

  return getDefaultReconThreshold();
}

function getDefaultReconDeferCooldownMs() {
  const config = readReconConfigFile();
  const configCooldown = Number(config?.automation?.total_war?.recon_defer_cooldown_ms);
  if (Number.isInteger(configCooldown) && configCooldown > 0) {
    return configCooldown;
  }

  return 10 * 60 * 1000;
}

function getDefaultReconSessionBufferTtlMs() {
  const config = readReconConfigFile();
  const envTtl = parseInt(process.env.RECON_SESSION_BUFFER_TTL_MS || '', 10);
  if (Number.isInteger(envTtl) && envTtl > 0) {
    return envTtl;
  }

  const configTtl = Number(config?.automation?.total_war?.recon_session_buffer_ttl_ms);
  if (Number.isInteger(configTtl) && configTtl > 0) {
    return configTtl;
  }

  return DEFAULT_RECON_SESSION_BUFFER_TTL_MS;
}

function getDefaultReconPreflightWaitMs() {
  const config = readReconConfigFile();
  const envWaitMs = parseInt(process.env.RECON_PREFLIGHT_WAIT_MS || '', 10);
  if (Number.isInteger(envWaitMs) && envWaitMs >= 0) {
    return envWaitMs;
  }

  const configWaitMs = Number(config?.automation?.total_war?.recon_preflight_wait_ms);
  if (Number.isInteger(configWaitMs) && configWaitMs >= 0) {
    return configWaitMs;
  }

  return DEFAULT_RECON_PREFLIGHT_WAIT_MS;
}

function getDefaultSkipLeagues() {
  const config = readReconConfigFile();
  return mergeLeagueLists(config?.automation?.total_war?.skip_list || []);
}

function readReconConfigFile() {
  const configPath = process.env.RECON_CONFIG_PATH || DEFAULT_RECON_CONFIG_PATH;
  try {
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'));
    }
  } catch (_error) {
    // 配置读取失败时回退到默认值
  }

  return {};
}

function getTotalWarLogSettings() {
  const config = readReconConfigFile();
  const envMaxBytes = parseInt(process.env.TOTAL_WAR_LOG_MAX_BYTES || '', 10);
  const envRetainedFiles = parseInt(process.env.TOTAL_WAR_LOG_RETAINED_FILES || '', 10);
  const configMaxBytes = Number(config?.automation?.total_war?.log_max_bytes);
  const configRetainedFiles = Number(config?.automation?.total_war?.log_retained_files);

  return {
    maxBytes: Number.isInteger(envMaxBytes) && envMaxBytes > 0
      ? envMaxBytes
      : Number.isInteger(configMaxBytes) && configMaxBytes > 0
        ? configMaxBytes
        : DEFAULT_LOG_MAX_BYTES,
    retainedFiles: Number.isInteger(envRetainedFiles) && envRetainedFiles > 0
      ? envRetainedFiles
      : Number.isInteger(configRetainedFiles) && configRetainedFiles > 0
        ? configRetainedFiles
        : DEFAULT_LOG_RETAINED_FILES
  };
}

function parseArgs(argv = process.argv.slice(2), runtime = {}) {
  const normalizedArgv = Array.isArray(argv) ? [...argv] : [];
  const firstOptionIndex = normalizedArgv.findIndex((arg) => String(arg).startsWith('-'));
  const args = firstOptionIndex > 0 ? normalizedArgv.slice(firstOptionIndex) : normalizedArgv;
  const stdout = runtime.stdout || process.stdout;
  const stderr = runtime.stderr || process.stderr;
  const exit = typeof runtime.exit === 'function'
    ? runtime.exit
    : (code) => process.exit(code);
  const showHelpFn = typeof runtime.showHelp === 'function'
    ? runtime.showHelp
    : showHelp;
  const options = {
    seasonInput: null,
    loopMs: 60_000,
    discoveryIntervalMs: 60 * 60 * 1000,
    discoveryConcurrency: 5,
    harvestConcurrency: 10,
    harvestLimit: 500,
    reconConcurrency: 5,
    reconLimit: getDefaultReconLimit(),
    reconThreshold: getDefaultReconThreshold(),
    threshold: null,
    reconDeferCooldownMs: getDefaultReconDeferCooldownMs(),
    reconSessionBufferPath: String(process.env.RECON_SESSION_BUFFER_PATH || RECON_SESSION_BUFFER_PATH),
    reconSessionBufferTtlMs: getDefaultReconSessionBufferTtlMs(),
    reconPreflightWaitMs: getDefaultReconPreflightWaitMs(),
    taskStage: 'auto',
    skipLeagues: getDefaultSkipLeagues(),
    includeAllLeagues: false,
    retryFailedOnly: false,
    mismatchRetryOnly: false,
    useProxy: false,
    forcePureProtocol: false,
    maxRuntimeMs: parseInt(process.env.TOTAL_WAR_MAX_RUNTIME_MS || '0', 10) || 0,
    killGraceMs: parseInt(process.env.TOTAL_WAR_KILL_GRACE_MS || '5000', 10) || 5000,
    failureLimit: 3,
    failureCooldownMs: 30 * 60 * 1000,
    once: false,
    dryRun: false
  };

  const readNextValue = (index, flagName) => {
    const nextArg = args[index + 1];
    if (nextArg === undefined || String(nextArg).startsWith('-')) {
      throw new Error(`参数 ${flagName} 缺少取值`);
    }
    return String(nextArg);
  };

  const readNumericValue = (index, flagName, fallback) => {
    const rawValue = readNextValue(index, flagName);
    const parsed = parseInt(rawValue, 10);
    return Number.isNaN(parsed) ? fallback : parsed;
  };

  const readFloatValue = (index, flagName, fallback) => {
    const rawValue = readNextValue(index, flagName);
    const parsed = parseFloat(rawValue);
    return Number.isFinite(parsed) ? parsed : fallback;
  };

  const setPrimaryConcurrency = (value) => {
    const parsed = parseInt(String(value), 10);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      return;
    }
    options.harvestConcurrency = parsed;
    options.reconConcurrency = parsed;
  };

  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    if (arg === '--help' || arg === '-h') {
      showHelpFn(stdout);
      return exit(0);
    } else if (arg === '--once') {
      options.once = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--retry-failed-only') {
      options.retryFailedOnly = true;
    } else if (arg === '--mismatch-retry-only') {
      options.mismatchRetryOnly = true;
    } else if (arg.startsWith('--season=')) {
      options.seasonInput = arg.split('=')[1];
    } else if (arg === '--season') {
      options.seasonInput = readNextValue(index, '--season');
      index++;
    } else if (arg.startsWith('--loop-ms=')) {
      options.loopMs = parseInt(arg.split('=')[1], 10) || options.loopMs;
    } else if (arg === '--loop-ms') {
      options.loopMs = readNumericValue(index, '--loop-ms', options.loopMs);
      index++;
    } else if (arg.startsWith('--discovery-interval-ms=')) {
      options.discoveryIntervalMs = parseInt(arg.split('=')[1], 10) || options.discoveryIntervalMs;
    } else if (arg === '--discovery-interval-ms') {
      options.discoveryIntervalMs = readNumericValue(index, '--discovery-interval-ms', options.discoveryIntervalMs);
      index++;
    } else if (arg.startsWith('--discovery-concurrency=')) {
      options.discoveryConcurrency = parseInt(arg.split('=')[1], 10) || options.discoveryConcurrency;
    } else if (arg === '--discovery-concurrency') {
      options.discoveryConcurrency = readNumericValue(index, '--discovery-concurrency', options.discoveryConcurrency);
      index++;
    } else if (arg.startsWith('--concurrency=')) {
      setPrimaryConcurrency(arg.split('=')[1]);
    } else if (arg === '--concurrency') {
      setPrimaryConcurrency(readNextValue(index, '--concurrency'));
      index++;
    } else if (arg.startsWith('--harvest-concurrency=')) {
      options.harvestConcurrency = parseInt(arg.split('=')[1], 10) || options.harvestConcurrency;
    } else if (arg === '--harvest-concurrency') {
      options.harvestConcurrency = readNumericValue(index, '--harvest-concurrency', options.harvestConcurrency);
      index++;
    } else if (arg.startsWith('--harvest-limit=')) {
      options.harvestLimit = parseInt(arg.split('=')[1], 10) || options.harvestLimit;
    } else if (arg === '--harvest-limit') {
      options.harvestLimit = readNumericValue(index, '--harvest-limit', options.harvestLimit);
      index++;
    } else if (arg.startsWith('--recon-concurrency=')) {
      options.reconConcurrency = parseInt(arg.split('=')[1], 10) || options.reconConcurrency;
    } else if (arg === '--recon-concurrency') {
      options.reconConcurrency = readNumericValue(index, '--recon-concurrency', options.reconConcurrency);
      index++;
    } else if (arg.startsWith('--recon-limit=')) {
      options.reconLimit = parseInt(arg.split('=')[1], 10) || options.reconLimit;
    } else if (arg === '--recon-limit') {
      options.reconLimit = readNumericValue(index, '--recon-limit', options.reconLimit);
      index++;
    } else if (arg.startsWith('--recon-threshold=')) {
      options.reconThreshold = parseInt(arg.split('=')[1], 10) || options.reconThreshold;
    } else if (arg === '--recon-threshold') {
      options.reconThreshold = readNumericValue(index, '--recon-threshold', options.reconThreshold);
      index++;
    } else if (arg.startsWith('--threshold=')) {
      options.threshold = Number.parseFloat(arg.split('=')[1]);
      if (!Number.isFinite(options.threshold)) {
        options.threshold = null;
      }
    } else if (arg === '--threshold') {
      options.threshold = readFloatValue(index, '--threshold', options.threshold);
      index++;
    } else if (arg.startsWith('--task-stage=')) {
      options.taskStage = normalizeTaskStage(arg.split('=')[1]);
    } else if (arg === '--task-stage') {
      options.taskStage = normalizeTaskStage(readNextValue(index, '--task-stage'));
      index++;
    } else if (arg.startsWith('--skip-leagues=')) {
      options.skipLeagues = mergeLeagueLists(options.skipLeagues, parseCommaSeparatedList(arg.split('=')[1]));
    } else if (arg === '--skip-leagues') {
      options.skipLeagues = mergeLeagueLists(options.skipLeagues, parseCommaSeparatedList(readNextValue(index, '--skip-leagues')));
      index++;
    } else if (arg === '--include-all-leagues') {
      options.includeAllLeagues = true;
      options.skipLeagues = [];
    } else if (arg.startsWith('--recon-defer-cooldown-ms=')) {
      options.reconDeferCooldownMs = parseInt(arg.split('=')[1], 10) || options.reconDeferCooldownMs;
    } else if (arg === '--recon-defer-cooldown-ms') {
      options.reconDeferCooldownMs = readNumericValue(
        index,
        '--recon-defer-cooldown-ms',
        options.reconDeferCooldownMs
      );
      index++;
    } else if (arg === '--use-proxy') {
      options.useProxy = true;
    } else if (arg === '--force-pure-protocol') {
      options.forcePureProtocol = true;
    } else if (arg.startsWith('--failure-limit=')) {
      options.failureLimit = parseInt(arg.split('=')[1], 10) || options.failureLimit;
    } else if (arg === '--failure-limit') {
      options.failureLimit = readNumericValue(index, '--failure-limit', options.failureLimit);
      index++;
    } else if (arg.startsWith('--failure-cooldown-ms=')) {
      options.failureCooldownMs = parseInt(arg.split('=')[1], 10) || options.failureCooldownMs;
    } else if (arg === '--failure-cooldown-ms') {
      options.failureCooldownMs = readNumericValue(index, '--failure-cooldown-ms', options.failureCooldownMs);
      index++;
    }
  }

  if (!options.seasonInput) {
    writeToStream(stderr, '❌ 错误: --season 参数是必需的');
    showHelpFn(stdout);
    return exit(1);
  }

  options.dbSeason = options.seasonInput.includes('-')
    ? options.seasonInput.replace('-', '/')
    : options.seasonInput;
  options.reconSeason = options.seasonInput.includes('/')
    ? options.seasonInput.replace('/', '-')
    : options.seasonInput;

  return options;
}

class Logger {
  constructor(logPath, options = {}) {
    this.logPath = logPath;
    this.fs = options.fsImpl || fs;
    this.consoleWriter = options.consoleImpl || null;
    this.titanLogger = options.titanLogger || new TitanLogger({
      serviceName: 'total-war-pipeline',
      enableFileLogging: false
    });
    this.maxBytes = Math.max(1, Number(options.maxBytes || DEFAULT_LOG_MAX_BYTES));
    this.retainedFiles = Math.max(1, Number(options.retainedFiles || DEFAULT_LOG_RETAINED_FILES));
  }

  _fileSize(targetPath) {
    try {
      return this.fs.statSync(targetPath).size || 0;
    } catch (_error) {
      return 0;
    }
  }

  _rotateIfNeeded(nextLine) {
    const incomingBytes = Buffer.byteLength(nextLine);
    const currentSize = this._fileSize(this.logPath);
    if (currentSize + incomingBytes <= this.maxBytes) {
      return;
    }

    for (let index = this.retainedFiles - 1; index >= 1; index--) {
      const source = `${this.logPath}.${index}`;
      const destination = `${this.logPath}.${index + 1}`;

      if (!this.fs.existsSync(source)) {
        continue;
      }

      if (this.fs.existsSync(destination)) {
        this.fs.unlinkSync(destination);
      }

      this.fs.renameSync(source, destination);
    }

    if (this.fs.existsSync(this.logPath)) {
      this.fs.renameSync(this.logPath, `${this.logPath}.1`);
    }
  }

  write(level, message, meta = {}) {
    ensureRuntimeDir();
    const entry = {
      ts: new Date().toISOString(),
      level,
      message,
      ...meta
    };
    const line = `${JSON.stringify(entry)}\n`;
    this._rotateIfNeeded(line);
    this.fs.appendFileSync(this.logPath, line);
    if (this.consoleWriter && typeof this.consoleWriter.log === 'function') {
      this.consoleWriter.log(`[${level}] ${message}${Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : ''}`);
      return;
    }

    const normalizedLevel = String(level || 'INFO').toLowerCase();
    const logMethod = typeof this.titanLogger?.[normalizedLevel] === 'function'
      ? this.titanLogger[normalizedLevel].bind(this.titanLogger)
      : this.titanLogger.info.bind(this.titanLogger);
    logMethod(message, {
      pipelineLevel: level,
      ...meta
    });
  }

  info(message, meta = {}) {
    this.write('INFO', message, meta);
  }

  warn(message, meta = {}) {
    this.write('WARN', message, meta);
  }

  error(message, meta = {}) {
    this.write('ERROR', message, meta);
  }
}

class LockManager {
  constructor(lockPath) {
    this.lockPath = lockPath;
    this.acquired = false;
  }

  acquire() {
    ensureRuntimeDir();

    if (fs.existsSync(this.lockPath)) {
      try {
        const raw = JSON.parse(fs.readFileSync(this.lockPath, 'utf8'));
        if (raw.pid) {
          process.kill(raw.pid, 0);
          throw new Error(`已有编排器实例在运行: pid=${raw.pid}`);
        }
      } catch (error) {
        if (error.code !== 'ESRCH') {
          throw error;
        }
      }
    }

    fs.writeFileSync(this.lockPath, JSON.stringify({
      pid: process.pid,
      createdAt: new Date().toISOString()
    }, null, 2));
    this.acquired = true;
  }

  release() {
    if (this.acquired && fs.existsSync(this.lockPath)) {
      fs.unlinkSync(this.lockPath);
    }
    this.acquired = false;
  }
}

class StateStore {
  constructor(statePath) {
    this.statePath = statePath;
  }

  load() {
    if (!fs.existsSync(this.statePath)) {
      return null;
    }

    return JSON.parse(fs.readFileSync(this.statePath, 'utf8'));
  }

  save(state) {
    ensureRuntimeDir();
    fs.writeFileSync(this.statePath, JSON.stringify(state, null, 2));
  }
}

class TotalWarPipeline {
  constructor(options, dependencies = {}) {
    this.options = options;
    this.logger = dependencies.logger || new Logger(LOG_PATH, {
      ...getTotalWarLogSettings(),
      ...(dependencies.loggerOptions || {})
    });
    this.lockManager = new LockManager(LOCK_PATH);
    this.stateStore = new StateStore(STATE_PATH);
    this.stopRequested = false;
    this.spawnImpl = dependencies.spawnImpl || spawn;
    this.processSupervisor = dependencies.processSupervisor || new ProcessSupervisor({
      logger: this.logger,
      spawnImpl: this.spawnImpl,
      maxRuntimeMs: options.maxRuntimeMs || 0,
      killGraceMs: options.killGraceMs || 5000
    });
    this.activeChild = null;
    this.activeChildMonitor = null;
    this.pool = null;
    this.state = this._buildDefaultState();
    this.closePromise = null;
  }

  _buildDefaultState() {
    return {
      version: 1,
      dbSeason: this.options.dbSeason,
      reconSeason: this.options.reconSeason,
      lastDiscoveryAt: null,
      lastHarvestAt: null,
      lastReconAt: null,
      lastReconRawCount: 0,
      tasks: {
        discovery: this._defaultTaskState(),
        harvest: this._defaultTaskState(),
        recon: this._defaultTaskState()
      }
    };
  }

  _defaultTaskState() {
    return {
      consecutiveFailures: 0,
      lastFailureAt: null,
      lastSuccessAt: null,
      cooldownUntil: null,
      deferredUntil: null,
      lastDeferredAt: null,
      lastDeferredReason: null
    };
  }

  init() {
    ensureRuntimeDir();
    this.lockManager.acquire();
    this.pool = new Pool({
      host: process.env.DB_HOST || 'host.docker.internal',
      port: parseInt(process.env.DB_PORT || '5432', 10),
      database: process.env.DB_NAME || 'football_db',
      user: process.env.DB_USER || 'football_user',
      password: process.env.DB_PASSWORD || 'football_pass',
      max: 4,
      idleTimeoutMillis: 30_000
    });

    const persisted = this.stateStore.load();
    if (persisted) {
      this.state = {
        ...this._buildDefaultState(),
        ...persisted,
        tasks: {
          discovery: { ...this._defaultTaskState(), ...(persisted.tasks || {}).discovery },
          harvest: { ...this._defaultTaskState(), ...(persisted.tasks || {}).harvest },
          recon: { ...this._defaultTaskState(), ...(persisted.tasks || {}).recon }
        }
      };
    }

    this._attachSignalHandlers();
    this.logger.info('pipeline_initialized', {
      dbSeason: this.options.dbSeason,
      reconSeason: this.options.reconSeason,
      taskStage: this.options.taskStage,
      retryFailedOnly: this.options.retryFailedOnly,
      skipLeagues: this.options.skipLeagues,
      dryRun: this.options.dryRun,
      once: this.options.once
    });
  }

  _attachSignalHandlers() {
    const shutdown = async (signal) => {
      this.logger.warn('shutdown_requested', { signal });
      this.stopRequested = true;
      await this.close();
      process.exit(0);
    };

    process.once('SIGINT', shutdown);
    process.once('SIGTERM', shutdown);
  }

  async run() {
    if (this.options.once) {
      await this.runCycle();
      return;
    }

    while (!this.stopRequested) {
      try {
        await this.runCycle();
      } catch (error) {
        this.logger.error('cycle_failed', { error: error.message });
      }
      await sleep(this.options.loopMs);
    }
  }

  async runCycle() {
    const metrics = await this.collectMetrics();
    const task = this.decideNextTask(metrics);

    this.logger.info('cycle_metrics', { ...metrics, nextTask: task || null });

    if (!task) {
      this.stateStore.save(this.state);
      return;
    }

    if (this.options.dryRun) {
      this.logger.info('dry_run_task_selected', {
        task,
        dbSeason: this.options.dbSeason,
        reconSeason: this.options.reconSeason
      });
      return;
    }

    await this.runManagedTask(task, metrics);
  }

  decideNextTask(metrics) {
    const candidates = [
      {
        name: 'discovery',
        enabled: this._isTaskStageAllowed('discovery')
          && !this.options.retryFailedOnly
          && this._isDiscoveryDue()
      },
      {
        name: 'harvest',
        enabled: this._isTaskStageAllowed('harvest')
          && metrics.pendingCount > 0
      },
      {
        name: 'recon',
        enabled: this._isTaskStageAllowed('recon')
          && this._isReconDue(metrics)
      }
    ];

    for (const candidate of candidates) {
      if (!candidate.enabled) {
        continue;
      }

      if (this._isTaskCoolingDown(candidate.name)) {
        const cooldownUntil = this._resolveTaskBlockedUntil(this.state.tasks[candidate.name]);
        this.logger.warn('task_in_cooldown', {
          task: candidate.name,
          cooldownUntil
        });
        continue;
      }

      return candidate.name;
    }

    return null;
  }

  _isTaskStageAllowed(taskName) {
    const taskStage = this.options.taskStage || 'auto';
    return taskStage === 'auto' || taskStage === taskName;
  }

  _isDiscoveryDue() {
    if (!this.state.lastDiscoveryAt) {
      return true;
    }
    return Date.now() - new Date(this.state.lastDiscoveryAt).getTime() >= this.options.discoveryIntervalMs;
  }

  _isReconDue(metrics) {
    const hasReconBacklog = metrics.harvestedCount > 0 || metrics.mismatchCount > 0;
    if (!hasReconBacklog) {
      return false;
    }

    if (this.options.retryFailedOnly) {
      return true;
    }

    const rawDelta = Math.max(0, metrics.rawCount - (this.state.lastReconRawCount || 0));
    if (metrics.pendingCount === 0) {
      return true;
    }
    return rawDelta >= this.options.reconThreshold;
  }

  _isTaskCoolingDown(taskName) {
    const taskState = this.state.tasks[taskName];
    const blockedUntil = this._resolveTaskBlockedUntil(taskState);
    if (!blockedUntil) {
      return false;
    }
    return Date.now() < new Date(blockedUntil).getTime();
  }

  _resolveTaskBlockedUntil(taskState) {
    if (!taskState) {
      return null;
    }

    const blockedAtList = [taskState.cooldownUntil, taskState.deferredUntil]
      .filter(Boolean)
      .map((value) => new Date(value).getTime())
      .filter((value) => Number.isFinite(value));
    if (blockedAtList.length === 0) {
      return null;
    }

    return new Date(Math.max(...blockedAtList)).toISOString();
  }

  async runManagedTask(taskName, metrics) {
    if (taskName === 'recon') {
      const preflightResult = await this.ensureReconGoldenSnapshot(metrics);
      if (preflightResult.exitCode !== 0) {
        if (this._shouldDeferReconAfterFailure()) {
          this.markTaskDeferred(taskName, 'LEAGUE_TIMEOUT');
          this.logger.warn('task_deferred', {
            task: taskName,
            reason: 'LEAGUE_TIMEOUT',
            exitCode: preflightResult.exitCode,
            deferredUntil: this.state.tasks[taskName].deferredUntil
          });
        } else {
          this.markTaskFailure(taskName);
          this.logger.warn('task_failure', {
            task: taskName,
            exitCode: preflightResult.exitCode,
            consecutiveFailures: this.state.tasks[taskName].consecutiveFailures,
            phase: 'preflight'
          });
        }

        this.stateStore.save(this.state);
        return;
      }
    }

    const taskConfig = this.buildTaskCommand(taskName, metrics);
    this.logger.info('task_start', {
      task: taskName,
      command: taskConfig.command,
      args: taskConfig.args
    });

    const exitCode = await this.runChild(taskConfig);

    if (exitCode === 0) {
      this.markTaskSuccess(taskName, metrics);
      this.logger.info('task_success', { task: taskName, exitCode });
    } else if (taskName === 'recon' && this._shouldDeferReconAfterFailure()) {
      this.markTaskDeferred(taskName, 'LEAGUE_TIMEOUT');
      this.logger.warn('task_deferred', {
        task: taskName,
        reason: 'LEAGUE_TIMEOUT',
        exitCode,
        deferredUntil: this.state.tasks[taskName].deferredUntil
      });
    } else {
      this.markTaskFailure(taskName);
      this.logger.warn('task_failure', {
        task: taskName,
        exitCode,
        consecutiveFailures: this.state.tasks[taskName].consecutiveFailures
      });
    }

    this.stateStore.save(this.state);
  }

  _shouldDeferReconAfterFailure() {
    const lines = Array.isArray(this.lastChildTrace?.lines)
      ? this.lastChildTrace.lines
      : [];
    if (lines.length === 0) {
      return false;
    }

    return lines.some((line) => /LEAGUE_TIMEOUT|recon_league_timeout/i.test(String(line)));
  }

  _createReconSessionManager(bufferPoolRole = 'worker') {
    return new ReconSessionManager({
      logger: this.logger,
      traceId: `total-war-${bufferPoolRole}`,
      defaultSourceUrl: 'https://www.oddsportal.com/',
      bufferPoolPath: this.options.reconSessionBufferPath,
      bufferPoolTtlMs: this.options.reconSessionBufferTtlMs,
      bufferPoolRole
    });
  }

  buildTaskEnv(taskName, options = {}) {
    const env = { ...process.env };
    if (taskName !== 'recon') {
      return env;
    }

    const phase = String(options.phase || 'cluster').trim().toLowerCase();
    env.RECON_SESSION_BUFFER_PATH = this.options.reconSessionBufferPath;
    env.RECON_SESSION_BUFFER_TTL_MS = String(this.options.reconSessionBufferTtlMs);
    env.RECON_SESSION_BUFFER_ROLE = phase === 'preflight' ? 'preflight' : 'worker';
    env.RECON_SESSION_SNAPSHOT_ROLE = phase === 'preflight' ? 'golden' : 'lineage';
    env.RECON_SESSION_BUFFER_PHASE = phase;
    if (options.forceGoldenRefresh === true) {
      env.RECON_SESSION_FORCE_REFRESH = 'true';
    }
    return env;
  }

  async ensureReconGoldenSnapshot(metrics = {}) {
    const sessionManager = this._createReconSessionManager('preflight');
    const bufferState = sessionManager.inspectBufferPool();
    if (bufferState.needsRefresh !== true) {
      this.logger.info('recon_session_preflight_skipped', {
        bufferPoolPath: bufferState.path,
        goldenUpdatedAt: bufferState.goldenUpdatedAt,
        goldenAgeMs: bufferState.goldenAgeMs,
        ttlMs: bufferState.ttlMs
      });
      return {
        exitCode: 0,
        skipped: true,
        bufferState
      };
    }

    const refreshLeaseResult = sessionManager.acquireGoldenRefreshLease();
    if (refreshLeaseResult.acquired !== true) {
      this.logger.warn('recon_session_preflight_refresh_busy', {
        bufferPoolPath: this.options.reconSessionBufferPath,
        activeLease: refreshLeaseResult.lease || null
      });
      return {
        exitCode: 0,
        skipped: true,
        bufferState,
        leaseBusy: true
      };
    }

    try {
      this.logger.info('recon_session_preflight_start', {
        bufferPoolPath: this.options.reconSessionBufferPath,
        ttlMs: this.options.reconSessionBufferTtlMs,
        goldenAgeMs: bufferState.goldenAgeMs
      });
      const preflightConfig = this.buildTaskCommand('recon', metrics, {
        phase: 'preflight',
        concurrency: 1,
        reconLimit: 1,
        forceGoldenRefresh: true
      });
      const exitCode = await this.runChild(preflightConfig);
      const refreshedState = sessionManager.inspectBufferPool();
      const hasGoldenSnapshot = refreshedState.hasGoldenSnapshot === true;
      const toleratedFailure = exitCode !== 0
        && hasGoldenSnapshot
        && !this._shouldDeferReconAfterFailure();
      const effectiveExitCode = exitCode === 0 && hasGoldenSnapshot !== true
        ? 1
        : (toleratedFailure ? 0 : exitCode);
      if (exitCode === 0 && effectiveExitCode !== 0) {
        this.logger.error('recon_session_preflight_missing_golden_snapshot', {
          bufferPoolPath: this.options.reconSessionBufferPath
        });
      }
      if (toleratedFailure) {
        this.logger.warn('recon_session_preflight_tolerated_failure', {
          exitCode,
          bufferPoolPath: this.options.reconSessionBufferPath,
          goldenUpdatedAt: refreshedState.goldenUpdatedAt
        });
      }
      this.logger.info('recon_session_preflight_complete', {
        exitCode: effectiveExitCode,
        bufferPoolPath: this.options.reconSessionBufferPath,
        goldenUpdatedAt: refreshedState.goldenUpdatedAt,
        goldenAgeMs: refreshedState.goldenAgeMs,
        hasGoldenSnapshot,
        toleratedFailure
      });

      if (effectiveExitCode === 0 && this.options.reconPreflightWaitMs > 0) {
        await sleep(this.options.reconPreflightWaitMs);
      }

      return {
        exitCode: effectiveExitCode,
        skipped: false,
        bufferStateBefore: bufferState,
        bufferStateAfter: refreshedState
      };
    } finally {
      sessionManager.releaseGoldenRefreshLease(refreshLeaseResult.lease);
    }
  }

  buildTaskCommand(taskName, metrics = {}, options = {}) {
    const command = process.execPath;

    if (taskName === 'discovery') {
      return {
        task: taskName,
        command,
        args: [
          path.join(ROOT_DIR, 'scripts/ops/titan_discovery.js'),
          '--all-leagues',
          `--season=${this.options.dbSeason}`,
          '--concurrency',
          String(this.options.discoveryConcurrency)
        ]
      };
    }

    if (taskName === 'harvest') {
      return {
        task: taskName,
        command,
        args: [
          path.join(ROOT_DIR, 'scripts/ops/run_production.js'),
          '--concurrency',
          String(this.options.harvestConcurrency),
          '--limit',
          String(this.options.harvestLimit)
        ]
      };
    }

    if (taskName === 'recon') {
      const reconLimit = Math.max(1, Number(options.reconLimit ?? options.limit ?? this.options.reconLimit) || 0);
      const reconConcurrency = Math.max(
        1,
        Number(options.reconConcurrency ?? options.concurrency ?? this.options.reconConcurrency) || 0
      );
      const args = [
        path.join(ROOT_DIR, 'scripts/ops/recon_scanner.js'),
        '--season',
        this.options.reconSeason,
        '--all-leagues',
        '--limit',
        String(reconLimit),
        '--concurrency',
        String(reconConcurrency)
      ];
      if (Number.isFinite(this.options.threshold)) {
        args.push('--threshold', String(this.options.threshold));
      }
      if (this.options.mismatchRetryOnly) {
        args.push('--mismatch-retry-only');
      } else if (this.options.retryFailedOnly) {
        const harvestedCount = Number(metrics.harvestedCount || 0);
        const mismatchCount = Number(metrics.mismatchCount || 0);
        if (harvestedCount === 0 && mismatchCount > 0) {
          args.push('--mismatch-retry-only');
        }
      }
      if (Array.isArray(this.options.skipLeagues) && this.options.skipLeagues.length > 0) {
        args.push('--skip-leagues', this.options.skipLeagues.join(','));
      }
      if (this.options.useProxy) {
        args.push('--use-proxy');
      }
      if (this.options.forcePureProtocol) {
        args.push('--force-pure-protocol');
      }
      return {
        task: taskName,
        command,
        args,
        env: this.buildTaskEnv(taskName, {
          phase: options.phase || 'cluster',
          forceGoldenRefresh: options.forceGoldenRefresh === true
        })
      };
    }

    throw new Error(`未知任务: ${taskName}`);
  }

  monitorChild(child, options = {}) {
    if (this.activeChildMonitor && typeof this.activeChildMonitor.cancel === 'function') {
      this.activeChildMonitor.cancel();
    }

    this.activeChild = child || null;
    this.activeChildMonitor = this.processSupervisor && typeof this.processSupervisor.monitorChild === 'function'
      ? this.processSupervisor.monitorChild(child, options)
      : { cancel() {} };

    return this.activeChildMonitor;
  }

  _clearActiveChild(child = null) {
    if (child && this.activeChild && child !== this.activeChild) {
      return;
    }

    if (this.activeChildMonitor && typeof this.activeChildMonitor.cancel === 'function') {
      this.activeChildMonitor.cancel();
    }

    this.activeChildMonitor = null;
    this.activeChild = null;
  }

  runChild(taskConfig) {
    return new Promise((resolve, reject) => {
      this.lastChildTrace = {
        task: taskConfig.task,
        lines: []
      };
      const spawnOptions = {
        cwd: ROOT_DIR,
        env: taskConfig.env || process.env,
        stdio: ['ignore', 'pipe', 'pipe']
      };
      const child = this.processSupervisor && typeof this.processSupervisor.spawnChild === 'function'
        ? this.processSupervisor.spawnChild(taskConfig.command, taskConfig.args, spawnOptions)
        : this.spawnImpl(taskConfig.command, taskConfig.args, spawnOptions);
      this.monitorChild(child, {
        maxRuntimeMs: this.options.maxRuntimeMs || 0,
        killGraceMs: this.options.killGraceMs || 5000
      });

      const forward = (stream, level) => {
        if (!stream || typeof stream.on !== 'function') {
          return;
        }
        stream.on('data', (chunk) => {
          for (const line of String(chunk).split(/\r?\n/)) {
            if (!line.trim()) {
              continue;
            }
            this.lastChildTrace.lines.push(line);
            if (this.lastChildTrace.lines.length > 200) {
              this.lastChildTrace.lines.shift();
            }
            this.logger[level](`child_${taskConfig.task}`, { line });
          }
        });
      };

      forward(child.stdout, 'info');
      forward(child.stderr, 'warn');

      child.on('error', (error) => {
        this._clearActiveChild(child);
        reject(error);
      });
      child.on('close', (code) => {
        this._clearActiveChild(child);
        resolve(code ?? 1);
      });
    });
  }

  markTaskSuccess(taskName, metrics) {
    const taskState = this.state.tasks[taskName];
    taskState.consecutiveFailures = 0;
    taskState.lastSuccessAt = new Date().toISOString();
    taskState.cooldownUntil = null;
    taskState.deferredUntil = null;
    taskState.lastDeferredAt = null;
    taskState.lastDeferredReason = null;

    if (taskName === 'discovery') {
      this.state.lastDiscoveryAt = taskState.lastSuccessAt;
    } else if (taskName === 'harvest') {
      this.state.lastHarvestAt = taskState.lastSuccessAt;
    } else if (taskName === 'recon') {
      this.state.lastReconAt = taskState.lastSuccessAt;
      this.state.lastReconRawCount = metrics.rawCount;
    }
  }

  markTaskFailure(taskName) {
    const taskState = this.state.tasks[taskName];
    taskState.consecutiveFailures += 1;
    taskState.lastFailureAt = new Date().toISOString();

    if (taskState.consecutiveFailures >= this.options.failureLimit) {
      taskState.cooldownUntil = new Date(Date.now() + this.options.failureCooldownMs).toISOString();
      this.logger.warn('task_cooldown_armed', {
        task: taskName,
        consecutiveFailures: taskState.consecutiveFailures,
        cooldownUntil: taskState.cooldownUntil
      });
    }
  }

  markTaskDeferred(taskName, reason = 'DEFERRED') {
    const taskState = this.state.tasks[taskName];
    taskState.consecutiveFailures = 0;
    taskState.lastDeferredAt = new Date().toISOString();
    taskState.lastDeferredReason = reason;
    taskState.deferredUntil = new Date(
      Date.now() + Math.max(1, Number(this.options.reconDeferCooldownMs) || 0)
    ).toISOString();
  }

  async collectMetrics() {
    const countsQuery = `
      SELECT
        COUNT(*) FILTER (WHERE pipeline_status = 'pending') AS pending_count,
        COUNT(*) FILTER (WHERE pipeline_status = 'harvested') AS harvested_count,
        COUNT(*) FILTER (WHERE pipeline_status = 'RECON_MISMATCH') AS mismatch_count,
        COUNT(*) FILTER (WHERE pipeline_status = 'failed') AS failed_count,
        COUNT(*) FILTER (WHERE pipeline_status = 'RECON_LINKED') AS linked_count
      FROM matches
      WHERE season = $1
    `;

    const rawQuery = `
      SELECT COUNT(*) AS raw_count
      FROM raw_match_data r
      JOIN matches m USING (match_id)
      WHERE m.season = $1
    `;

    const [countsResult, rawResult] = await Promise.all([
      this.pool.query(countsQuery, [this.options.dbSeason]),
      this.pool.query(rawQuery, [this.options.dbSeason])
    ]);

    const counts = countsResult.rows[0] || {};
    const rawRow = rawResult.rows[0] || {};
    const rawCount = parseInt(rawRow.raw_count || 0, 10);

    return {
      pendingCount: parseInt(counts.pending_count || 0, 10),
      harvestedCount: parseInt(counts.harvested_count || 0, 10),
      mismatchCount: parseInt(counts.mismatch_count || 0, 10),
      failedCount: parseInt(counts.failed_count || 0, 10),
      linkedCount: parseInt(counts.linked_count || 0, 10),
      rawCount,
      rawDeltaSinceRecon: Math.max(0, rawCount - (this.state.lastReconRawCount || 0))
    };
  }

  async close() {
    if (this.closePromise) {
      return this.closePromise;
    }

    this.closePromise = (async () => {
      try {
        const activeChild = this.activeChild;
        if (this.activeChildMonitor && typeof this.activeChildMonitor.cancel === 'function') {
          this.activeChildMonitor.cancel();
        }

        if (activeChild && this.processSupervisor && typeof this.processSupervisor.terminateChild === 'function') {
          await this.processSupervisor.terminateChild(activeChild, {
            killGraceMs: this.options.killGraceMs || 5000
          });
        } else if (activeChild && typeof activeChild.kill === 'function') {
          try {
            activeChild.kill('SIGTERM');
          } catch (error) {
            this.logger.error('child_sigterm_failed', {
              pid: activeChild.pid || null,
              error: error.message
            });
          }
        }

        this._clearActiveChild();

        if (this.pool) {
          const pool = this.pool;
          this.pool = null;
          await pool.end();
        }
      } finally {
        this.stateStore.save(this.state);
        this.lockManager.release();
      }
    })();

    return this.closePromise;
  }
}

async function main(argv = process.argv.slice(2)) {
  const options = parseArgs(argv);
  const pipeline = new TotalWarPipeline(options);

  try {
    await pipeline.init();
    await pipeline.run();
  } finally {
    await pipeline.close();
  }
}

if (require.main === module) {
  main().then(
    () => process.exit(0),
    (error) => {
      const bootstrapLogger = new TitanLogger({
        serviceName: 'total-war-pipeline',
        enableFileLogging: false
      });
      bootstrapLogger.error('total_war_pipeline_unhandled_error', {
        error: error.message
      });
      writeToStream(process.stderr, `❌ TOTAL WAR 编排器异常: ${error.message}`);
      process.exit(1);
    }
  );
}

module.exports = {
  Logger,
  TotalWarPipeline,
  parseArgs,
  sleep,
  getDefaultReconLimit,
  getDefaultReconThreshold,
  getTotalWarLogSettings
};
