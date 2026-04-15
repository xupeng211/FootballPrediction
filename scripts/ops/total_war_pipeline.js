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

const ROOT_DIR = path.resolve(__dirname, '../..');
const RUNTIME_DIR = path.join(ROOT_DIR, 'tmp', 'total_war_pipeline');
const STATE_PATH = path.join(RUNTIME_DIR, 'state.json');
const LOCK_PATH = path.join(RUNTIME_DIR, 'pipeline.lock');
const LOG_PATH = path.join(RUNTIME_DIR, 'pipeline.log');
const DEFAULT_RECON_CONFIG_PATH = path.join(ROOT_DIR, 'config', 'recon_config.json');
const DEFAULT_LOG_MAX_BYTES = 100 * 1024 * 1024;
const DEFAULT_LOG_RETAINED_FILES = 5;

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function ensureRuntimeDir() {
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
}

function showHelp() {
  console.log(`
TOTAL WAR PIPELINE - 24 小时自动编排器

用法:
  node scripts/ops/total_war_pipeline.js --season 2025/2026 [选项]

选项:
  --season=SEASON            赛季，支持 2025/2026 或 2025-2026
  --loop-ms=N                主循环间隔，默认 60000
  --discovery-interval-ms=N  Discovery 间隔，默认 3600000
  --discovery-concurrency=N  Discovery 并发，默认 5
  --harvest-concurrency=N    Harvest 并发，默认 10
  --harvest-limit=N          Harvest 单批上限，默认 500
  --recon-concurrency=N      Recon 并发，默认 5
  --recon-limit=N            Recon 单批上限，默认读取配置
  --recon-threshold=N        触发 Recon 的新增 raw 阈值，默认 50
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

function parseArgs(argv = process.argv.slice(2)) {
  const normalizedArgv = Array.isArray(argv) ? [...argv] : [];
  const firstOptionIndex = normalizedArgv.findIndex((arg) => String(arg).startsWith('-'));
  const args = firstOptionIndex > 0 ? normalizedArgv.slice(firstOptionIndex) : normalizedArgv;
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

  for (let index = 0; index < args.length; index++) {
    const arg = args[index];
    if (arg === '--help' || arg === '-h') {
      showHelp();
      process.exit(0);
    } else if (arg === '--once') {
      options.once = true;
    } else if (arg === '--dry-run') {
      options.dryRun = true;
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
    console.error('❌ 错误: --season 参数是必需的');
    showHelp();
    process.exit(1);
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
    this.console = options.consoleImpl || console;
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
    this.console.log(`[${level}] ${message}${Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : ''}`);
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
      cooldownUntil: null
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
        enabled: this._isDiscoveryDue()
      },
      {
        name: 'recon',
        enabled: this._isReconDue(metrics)
      },
      {
        name: 'harvest',
        enabled: metrics.pendingCount > 0
      }
    ];

    for (const candidate of candidates) {
      if (!candidate.enabled) {
        continue;
      }

      if (this._isTaskCoolingDown(candidate.name)) {
        const cooldownUntil = this.state.tasks[candidate.name].cooldownUntil;
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

  _isDiscoveryDue() {
    if (!this.state.lastDiscoveryAt) {
      return true;
    }
    return Date.now() - new Date(this.state.lastDiscoveryAt).getTime() >= this.options.discoveryIntervalMs;
  }

  _isReconDue(metrics) {
    const rawDelta = Math.max(0, metrics.rawCount - (this.state.lastReconRawCount || 0));
    if (metrics.pendingCount === 0 && metrics.harvestedCount > 0) {
      return true;
    }
    return rawDelta >= this.options.reconThreshold;
  }

  _isTaskCoolingDown(taskName) {
    const taskState = this.state.tasks[taskName];
    if (!taskState?.cooldownUntil) {
      return false;
    }
    return Date.now() < new Date(taskState.cooldownUntil).getTime();
  }

  async runManagedTask(taskName, metrics) {
    const taskConfig = this.buildTaskCommand(taskName);
    this.logger.info('task_start', {
      task: taskName,
      command: taskConfig.command,
      args: taskConfig.args
    });

    const exitCode = await this.runChild(taskConfig);

    if (exitCode === 0) {
      this.markTaskSuccess(taskName, metrics);
      this.logger.info('task_success', { task: taskName, exitCode });
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

  buildTaskCommand(taskName) {
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
      const reconLimit = Math.max(1, Number(this.options.reconLimit) || 0);
      const args = [
        path.join(ROOT_DIR, 'scripts/ops/recon_scanner.js'),
        '--season',
        this.options.reconSeason,
        '--all-leagues',
        '--limit',
        String(reconLimit),
        '--concurrency',
        String(this.options.reconConcurrency)
      ];
      if (this.options.useProxy) {
        args.push('--use-proxy');
      }
      if (this.options.forcePureProtocol) {
        args.push('--force-pure-protocol');
      }
      return {
        task: taskName,
        command,
        args
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
      const spawnOptions = {
        cwd: ROOT_DIR,
        env: process.env,
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

  async collectMetrics() {
    const countsQuery = `
      SELECT
        COUNT(*) FILTER (WHERE pipeline_status = 'pending') AS pending_count,
        COUNT(*) FILTER (WHERE pipeline_status = 'harvested') AS harvested_count,
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
      console.error('❌ TOTAL WAR 编排器异常:', error.message);
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
