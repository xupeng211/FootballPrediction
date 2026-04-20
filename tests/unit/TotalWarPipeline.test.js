'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');

const { Logger, parseArgs, TotalWarPipeline } = require('../../scripts/ops/total_war_pipeline');

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
