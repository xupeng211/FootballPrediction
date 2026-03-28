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
