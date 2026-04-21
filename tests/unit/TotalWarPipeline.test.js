'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const { Logger, parseArgs, TotalWarPipeline, getTotalWarLogSettings } = require('../../scripts/ops/total_war_pipeline');

function createWritableBuffer(chunks) {
  return {
    write(chunk) {
      chunks.push(String(chunk));
    }
  };
}

function createExitTrap() {
  return (code) => {
    const error = new Error(`EXIT_${code}`);
    error.exitCode = code;
    throw error;
  };
}

function withTemporaryEnv(tempEnv, callback) {
  const previousEnv = {};
  for (const [key, value] of Object.entries(tempEnv)) {
    previousEnv[key] = process.env[key];
    if (value === null || value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = String(value);
    }
  }

  try {
    return callback();
  } finally {
    for (const [key, value] of Object.entries(previousEnv)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
}

test('parseArgs 应兼容 --season=2025/2026', () => {
  const result = parseArgs(['--season=2025/2026', '--once']);

  assert.equal(result.seasonInput, '2025/2026');
  assert.equal(result.dbSeason, '2025/2026');
  assert.equal(result.reconSeason, '2025-2026');
  assert.equal(result.once, true);
});

test('parseArgs 应兼容 --season 2025/2026', () => {
  const result = parseArgs(['--season', '2025/2026', '--dry-run']);

  assert.equal(result.seasonInput, '2025/2026');
  assert.equal(result.dbSeason, '2025/2026');
  assert.equal(result.reconSeason, '2025-2026');
  assert.equal(result.dryRun, true);
});

test('parseArgs 应支持 --task-stage recon', () => {
  const result = parseArgs(['--season', '2025/2026', '--task-stage', 'recon', '--once']);

  assert.equal(result.taskStage, 'recon');
});

test('parseArgs 应支持 Recon 阈值与 mismatch-only 透传参数', () => {
  const result = parseArgs([
    '--season',
    '2025/2026',
    '--task-stage',
    'recon',
    '--threshold',
    '0.55',
    '--mismatch-retry-only',
    '--once'
  ]);

  assert.equal(result.taskStage, 'recon');
  assert.equal(result.threshold, 0.55);
  assert.equal(result.mismatchRetryOnly, true);
});

test('parseArgs 应能容忍原始 process.argv 前缀', () => {
  const result = parseArgs([
    '/usr/local/bin/node',
    '/app/scripts/ops/total_war_pipeline.js',
    '--season',
    '2025-2026',
    '--loop-ms',
    '120000'
  ]);

  assert.equal(result.seasonInput, '2025-2026');
  assert.equal(result.dbSeason, '2025/2026');
  assert.equal(result.reconSeason, '2025-2026');
  assert.equal(result.loopMs, 120000);
});

test('当 pending=0 且 harvested>0 时，编排器应强制进入 recon', () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']));

  const task = pipeline.decideNextTask({
    pendingCount: 0,
    harvestedCount: 7001,
    failedCount: 155,
    linkedCount: 1425,
    rawCount: 8426,
    rawDeltaSinceRecon: 0
  });

  assert.equal(task, 'discovery');

  pipeline.state.lastDiscoveryAt = new Date().toISOString();

  const reconTask = pipeline.decideNextTask({
    pendingCount: 0,
    harvestedCount: 7001,
    failedCount: 155,
    linkedCount: 1425,
    rawCount: 8426,
    rawDeltaSinceRecon: 0
  });

  assert.equal(reconTask, 'recon');
});

test('Recon 子任务应透传 reconLimit 以强制进入 Matrix 模式', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--recon-limit',
    '8000',
    '--recon-threshold',
    '200',
    '--recon-concurrency',
    '15'
  ]));

  const task = pipeline.buildTaskCommand('recon');

  assert.equal(task.args[0].endsWith(path.join('scripts', 'ops', 'recon_scanner.js')), true);
  assert.deepStrictEqual(task.args.slice(1), [
    '--season',
    '2025-2026',
    '--all-leagues',
    '--limit',
    '8000',
    '--concurrency',
    '15',
    '--skip-leagues',
    'J1 League'
  ]);
});

test('Recon 子任务应按需透传代理与 pure protocol 开关', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--recon-threshold',
    '200',
    '--recon-concurrency',
    '15',
    '--use-proxy',
    '--force-pure-protocol'
  ]));

  const task = pipeline.buildTaskCommand('recon');

  assert.deepStrictEqual(task.args.slice(-2), [
    '--use-proxy',
    '--force-pure-protocol'
  ]);
});

test('Recon 子任务应显式透传 threshold 与 mismatch-only 开关', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--include-all-leagues',
    '--recon-limit',
    '500',
    '--recon-concurrency',
    '4',
    '--threshold',
    '0.55',
    '--mismatch-retry-only'
  ]));

  const task = pipeline.buildTaskCommand('recon');

  assert.deepStrictEqual(task.args.slice(1), [
    '--season',
    '2025-2026',
    '--all-leagues',
    '--limit',
    '500',
    '--concurrency',
    '4',
    '--threshold',
    '0.55',
    '--mismatch-retry-only'
  ]);
});

test('Recon 子任务启用 include-all-leagues 时不应继承默认 skip_list', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--include-all-leagues',
    '--recon-limit',
    '8000',
    '--recon-concurrency',
    '4'
  ]));

  const task = pipeline.buildTaskCommand('recon');

  assert.deepStrictEqual(task.args.slice(1), [
    '--season',
    '2025-2026',
    '--all-leagues',
    '--limit',
    '8000',
    '--concurrency',
    '4'
  ]);
});

test('Recon preflight 子任务应以单点 Worker 模式启动并注入 session buffer 环境', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--recon-limit',
    '8000',
    '--recon-concurrency',
    '8'
  ]));

  const task = pipeline.buildTaskCommand('recon', {}, {
    phase: 'preflight',
    concurrency: 1,
    reconLimit: 1
  });

  assert.deepStrictEqual(task.args.slice(1), [
    '--season',
    '2025-2026',
    '--all-leagues',
    '--limit',
    '1',
    '--concurrency',
    '1',
    '--skip-leagues',
    'J1 League'
  ]);
  assert.equal(task.env.RECON_SESSION_BUFFER_ROLE, 'preflight');
  assert.equal(task.env.RECON_SESSION_BUFFER_TTL_MS, String(pipeline.options.reconSessionBufferTtlMs));
  assert.equal(
    task.env.RECON_SESSION_BUFFER_PATH.endsWith(path.join('tmp', 'total_war_pipeline', 'recon_session_buffer_pool.json')),
    true
  );
});

test('task-stage=recon 时应跳过 pending 优先级并直接推进 recon', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--task-stage',
    'recon',
    '--retry-failed-only'
  ]));

  const task = pipeline.decideNextTask({
    pendingCount: 2187,
    harvestedCount: 2391,
    mismatchCount: 293,
    failedCount: 0,
    linkedCount: 3712,
    rawCount: 4005,
    rawDeltaSinceRecon: 0
  });

  assert.equal(task, 'recon');
});

test('task-stage=harvest 时应禁止 recon 抢占调度', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--task-stage',
    'harvest',
    '--retry-failed-only'
  ]));

  const task = pipeline.decideNextTask({
    pendingCount: 15,
    harvestedCount: 2391,
    mismatchCount: 293,
    failedCount: 0,
    linkedCount: 3712,
    rawCount: 4005,
    rawDeltaSinceRecon: 0
  });

  assert.equal(task, 'harvest');
});

test('Discovery 子任务应显式透传安全并发，避免依赖脚本默认值', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--discovery-concurrency',
    '5'
  ]));

  const task = pipeline.buildTaskCommand('discovery');

  assert.equal(task.args[0].endsWith(path.join('scripts', 'ops', 'titan_discovery.js')), true);
  assert.deepStrictEqual(task.args.slice(1), [
    '--all-leagues',
    '--season=2025/2026',
    '--concurrency',
    '5'
  ]);
});

test('Logger 在日志文件超过阈值时必须执行轮转并保留最新内容', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-log-'));
  const logPath = path.join(tempDir, 'pipeline.log');
  const logger = new Logger(logPath, {
    maxBytes: 160,
    retainedFiles: 2,
    consoleImpl: { log() {} }
  });

  logger.info('entry_one', { payload: 'x'.repeat(80) });
  logger.info('entry_two', { payload: 'y'.repeat(80) });
  logger.info('entry_three', { payload: 'z'.repeat(80) });

  assert.equal(fs.existsSync(logPath), true);
  assert.equal(fs.existsSync(`${logPath}.1`), true);
  assert.match(fs.readFileSync(logPath, 'utf8'), /entry_three/);
  assert.match(fs.readFileSync(`${logPath}.1`, 'utf8'), /entry_two/);
});

test('parseArgs 遇到 --help 时应输出帮助并请求退出', () => {
  const stdoutChunks = [];
  const shown = [];

  assert.throws(
    () => parseArgs(['--help'], {
      stdout: createWritableBuffer(stdoutChunks),
      showHelp(output) {
        shown.push(output);
      },
      exit: createExitTrap()
    }),
    (error) => error?.exitCode === 0
  );

  assert.equal(shown.length, 1);
  assert.equal(stdoutChunks.length, 0);
});

test('parseArgs 缺少 season 时应输出错误与帮助并请求退出', () => {
  const stdoutChunks = [];
  const stderrChunks = [];
  const shown = [];

  assert.throws(
    () => parseArgs([], {
      stdout: createWritableBuffer(stdoutChunks),
      stderr: createWritableBuffer(stderrChunks),
      showHelp(output) {
        shown.push(output);
        output.write('HELP\n');
      },
      exit: createExitTrap()
    }),
    (error) => error?.exitCode === 1
  );

  assert.match(stderrChunks.join(''), /--season 参数是必需的/);
  assert.match(stdoutChunks.join(''), /HELP/);
  assert.equal(shown.length, 1);
});

test('parseArgs 应从配置与环境装载默认值并去重 skip leagues', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-config-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        recon_threshold: 55,
        recon_limit: 75,
        recon_defer_cooldown_ms: 6200,
        recon_session_buffer_ttl_ms: 8800,
        recon_preflight_wait_ms: 1400,
        skip_list: ['Bundesliga', 'MLS'],
        log_max_bytes: 1024,
        log_retained_files: 2
      }
    }
  }), 'utf8');

  withTemporaryEnv({
    RECON_CONFIG_PATH: configPath,
    RECON_THRESHOLD: '88',
    RECON_LIMIT: '144',
    RECON_SESSION_BUFFER_TTL_MS: '777',
    RECON_PREFLIGHT_WAIT_MS: '999',
    TOTAL_WAR_LOG_MAX_BYTES: '2048',
    TOTAL_WAR_LOG_RETAINED_FILES: '3'
  }, () => {
    const options = parseArgs([
      '--season',
      '2025/2026',
      '--skip-leagues',
      'MLS,J1 League',
      '--skip-leagues=Serie A'
    ]);

    assert.equal(options.reconThreshold, 88);
    assert.equal(options.reconLimit, 144);
    assert.equal(options.reconDeferCooldownMs, 6200);
    assert.equal(options.reconSessionBufferTtlMs, 777);
    assert.equal(options.reconPreflightWaitMs, 999);
    assert.deepEqual(options.skipLeagues, ['Bundesliga', 'MLS', 'J1 League', 'Serie A']);
    assert.deepEqual(getTotalWarLogSettings(), {
      maxBytes: 2048,
      retainedFiles: 3
    });
  });
});

test('parseArgs 应在 include-all-leagues 下清空默认 skip list 并支持扩展参数', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-config-'));
  const configPath = path.join(tempDir, 'recon_config.json');
  fs.writeFileSync(configPath, JSON.stringify({
    automation: {
      total_war: {
        skip_list: ['MLS', 'J1 League']
      }
    }
  }), 'utf8');

  withTemporaryEnv({
    RECON_CONFIG_PATH: configPath
  }, () => {
    const options = parseArgs([
      '--season',
      '2025/2026',
      '--include-all-leagues',
      '--concurrency',
      '12',
      '--discovery-interval-ms=1200',
      '--discovery-concurrency',
      '7',
      '--harvest-concurrency=8',
      '--harvest-limit',
      '900',
      '--recon-defer-cooldown-ms=7000',
      '--failure-limit=4',
      '--failure-cooldown-ms',
      '6000',
      '--use-proxy',
      '--force-pure-protocol'
    ]);

    assert.equal(options.includeAllLeagues, true);
    assert.deepEqual(options.skipLeagues, []);
    assert.equal(options.harvestConcurrency, 8);
    assert.equal(options.reconConcurrency, 12);
    assert.equal(options.discoveryIntervalMs, 1200);
    assert.equal(options.discoveryConcurrency, 7);
    assert.equal(options.harvestLimit, 900);
    assert.equal(options.reconDeferCooldownMs, 7000);
    assert.equal(options.failureLimit, 4);
    assert.equal(options.failureCooldownMs, 6000);
    assert.equal(options.useProxy, true);
    assert.equal(options.forcePureProtocol, true);
  });
});

test('LockManager 应清理僵尸锁并拒绝存活进程锁', () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']));
  const LockManagerClass = pipeline.lockManager.constructor;
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-lock-'));
  const staleLockPath = path.join(tempDir, 'stale.lock');
  fs.writeFileSync(staleLockPath, JSON.stringify({
    pid: 999999,
    createdAt: new Date().toISOString()
  }), 'utf8');

  const staleManager = new LockManagerClass(staleLockPath);
  staleManager.acquire();
  assert.equal(staleManager.acquired, true);
  staleManager.release();
  assert.equal(fs.existsSync(staleLockPath), false);

  const liveLockPath = path.join(tempDir, 'live.lock');
  fs.writeFileSync(liveLockPath, JSON.stringify({
    pid: process.pid,
    createdAt: new Date().toISOString()
  }), 'utf8');
  const liveManager = new LockManagerClass(liveLockPath);
  assert.throws(() => liveManager.acquire(), /已有编排器实例在运行/);
});

test('StateStore 应支持保存、读取与空文件返回 null', () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']));
  const StateStoreClass = pipeline.stateStore.constructor;
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-state-'));
  const statePath = path.join(tempDir, 'state.json');
  const store = new StateStoreClass(statePath);

  assert.equal(store.load(), null);

  store.save({
    version: 1,
    task: 'recon'
  });

  assert.deepEqual(store.load(), {
    version: 1,
    task: 'recon'
  });
});

test('buildTaskCommand 在 retry-failed-only 且仅剩 mismatch 时应透传 mismatch-retry-only', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--retry-failed-only'
  ]));

  const task = pipeline.buildTaskCommand('recon', {
    harvestedCount: 0,
    mismatchCount: 12
  });

  assert.equal(task.args.includes('--mismatch-retry-only'), true);
});
