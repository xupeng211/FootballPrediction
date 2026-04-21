'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

const { ReconSessionManager } = require('../../src/infrastructure/recon/services/ReconSessionManager');
const { TotalWarPipeline, parseArgs, sleep } = require('../../scripts/ops/total_war_pipeline');

const silentLogger = {
  info() {},
  warn() {},
  error() {}
};

function createFakeChild({ closeAfterMs = null, exitCode = 0 } = {}) {
  const child = new EventEmitter();
  child.pid = 4242;
  child.stdout = new EventEmitter();
  child.stderr = new EventEmitter();
  child.killSignals = [];
  child.kill = (signal) => {
    child.killSignals.push(signal);
    return true;
  };

  if (Number.isInteger(closeAfterMs) && closeAfterMs >= 0) {
    setTimeout(() => {
      child.emit('close', exitCode);
    }, closeAfterMs);
  }

  return child;
}

test('TotalWarPipeline.monitorChild 超时后必须先发 SIGTERM，再补发 SIGKILL', async () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });
  const child = createFakeChild({ closeAfterMs: 220 });

  pipeline.monitorChild(child, {
    maxRuntimeMs: 100,
    killGraceMs: 50
  });

  await sleep(210);

  assert.deepEqual(child.killSignals, ['SIGTERM', 'SIGKILL']);
});

test('TotalWarPipeline.runChild 应通过受监管的 spawn 记录 activeChild，并在 close 后清空', async () => {
  const monitored = [];
  const child = createFakeChild({ closeAfterMs: 10, exitCode: 0 });
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']));

  pipeline.processSupervisor = {
    spawnChild() {
      return child;
    },
    monitorChild(monitoredChild) {
      monitored.push(monitoredChild);
      return {
        cancel() {}
      };
    }
  };

  const exitCode = await pipeline.runChild({
    task: 'recon',
    command: 'not-a-real-command',
    args: []
  });

  assert.equal(exitCode, 0);
  assert.equal(monitored.length, 1);
  assert.equal(monitored[0], child);
  assert.equal(pipeline.activeChild, null);
});

test('TotalWarPipeline.runManagedTask 在子进程返回 0 时必须记为 task_success', async () => {
  const infoLogs = [];
  let saveCount = 0;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info(event, payload) {
        infoLogs.push({ event, payload });
      },
      warn() {},
      error() {}
    }
  });

  pipeline.stateStore = {
    save() {
      saveCount++;
    }
  };
  pipeline.ensureReconGoldenSnapshot = async () => ({ exitCode: 0, skipped: true });
  pipeline.runChild = async () => 0;

  await pipeline.runManagedTask('recon', {
    pendingCount: 0,
    harvestedCount: 104,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 0,
    rawDeltaSinceRecon: 0
  });

  assert.equal(pipeline.state.tasks.recon.consecutiveFailures, 0);
  assert.equal(pipeline.state.tasks.recon.cooldownUntil, null);
  assert.equal(saveCount, 1);
  assert.ok(infoLogs.some((entry) => entry.event === 'task_success' && entry.payload?.task === 'recon' && entry.payload?.exitCode === 0));
});

test('TotalWarPipeline.runManagedTask 在 Recon 时应先执行 preflight，再并行挂载正式 worker', async () => {
  const roles = [];
  const limits = [];
  const concurrencyLevels = [];
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.options.reconSessionBufferPath = path.join(
    os.tmpdir(),
    `total-war-session-buffer-${Date.now()}-${Math.random().toString(36).slice(2)}.json`
  );
  pipeline.options.reconPreflightWaitMs = 0;
  pipeline.stateStore = {
    save() {}
  };
  pipeline.runChild = async (taskConfig) => {
    roles.push(taskConfig.env?.RECON_SESSION_BUFFER_ROLE || null);
    const limitIndex = taskConfig.args.indexOf('--limit');
    const concurrencyIndex = taskConfig.args.indexOf('--concurrency');
    limits.push(limitIndex >= 0 ? taskConfig.args[limitIndex + 1] : null);
    concurrencyLevels.push(concurrencyIndex >= 0 ? taskConfig.args[concurrencyIndex + 1] : null);
    if (taskConfig.env?.RECON_SESSION_BUFFER_ROLE === 'preflight') {
      const sessionManager = new ReconSessionManager({
        logger: { info() {}, warn() {}, error() {}, debug() {} },
        traceId: 'trace-total-war-preflight',
        sessionPath: '',
        bufferPoolPath: pipeline.options.reconSessionBufferPath,
        bufferPoolRole: 'preflight'
      });
      sessionManager.setRuntimeSnapshot({
        cookies: [{
          name: 'preflight_seed',
          value: '1',
          domain: '.oddsportal.com',
          path: '/'
        }],
        userAgent: 'Preflight-UA/1.0'
      });
    }
    pipeline.lastChildTrace = {
      task: taskConfig.task,
      lines: []
    };
    return 0;
  };

  await pipeline.runManagedTask('recon', {
    pendingCount: 0,
    harvestedCount: 42,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 100,
    rawDeltaSinceRecon: 10
  });

  assert.deepEqual(roles, ['preflight', 'worker']);
  assert.deepEqual(limits, ['1', String(pipeline.options.reconLimit)]);
  assert.deepEqual(concurrencyLevels, ['1', String(pipeline.options.reconConcurrency)]);
});

test('TotalWarPipeline.ensureReconGoldenSnapshot 在已写入 GOLDEN_SNAPSHOT 时应容忍业务样本失败并继续放行', async () => {
  const warnLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info() {},
      warn(event, payload) {
        warnLogs.push({ event, payload });
      },
      error() {}
    }
  });
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-preflight-'));

  pipeline.options.reconSessionBufferPath = path.join(tempDir, 'recon_session_buffer_pool.json');
  pipeline.options.reconPreflightWaitMs = 0;
  pipeline.runChild = async () => {
    const sessionManager = new ReconSessionManager({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-total-war-preflight-tolerated',
      sessionPath: '',
      bufferPoolPath: pipeline.options.reconSessionBufferPath,
      bufferPoolRole: 'preflight'
    });
    sessionManager.setRuntimeSnapshot({
      cookies: [{
        name: 'preflight_seed',
        value: '1',
        domain: '.oddsportal.com',
        path: '/'
      }],
      userAgent: 'Preflight-UA/1.0'
    });
    pipeline.lastChildTrace = {
      task: 'recon',
      lines: ['{"status":"RECON_MISMATCH"}']
    };
    return 1;
  };

  const result = await pipeline.ensureReconGoldenSnapshot({
    pendingCount: 0,
    harvestedCount: 1,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 1,
    rawDeltaSinceRecon: 1
  });

  assert.equal(result.exitCode, 0);
  assert.equal(result.bufferStateAfter.hasGoldenSnapshot, true);
  assert.ok(warnLogs.some((entry) => entry.event === 'recon_session_preflight_tolerated_failure'));
});

test('TotalWarPipeline.ensureReconGoldenSnapshot 在 LEAGUE_TIMEOUT 时即使已有 GOLDEN_SNAPSHOT 也不得放行', async () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season', '2025/2026',
    '--once',
    '--recon-defer-cooldown-ms', '20'
  ]), {
    logger: silentLogger
  });
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'total-war-preflight-timeout-'));

  pipeline.options.reconSessionBufferPath = path.join(tempDir, 'recon_session_buffer_pool.json');
  pipeline.options.reconPreflightWaitMs = 0;
  pipeline.runChild = async () => {
    const sessionManager = new ReconSessionManager({
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      traceId: 'trace-total-war-preflight-timeout',
      sessionPath: '',
      bufferPoolPath: pipeline.options.reconSessionBufferPath,
      bufferPoolRole: 'preflight'
    });
    sessionManager.setRuntimeSnapshot({
      cookies: [{
        name: 'preflight_seed',
        value: '1',
        domain: '.oddsportal.com',
        path: '/'
      }],
      userAgent: 'Preflight-UA/1.0'
    });
    pipeline.lastChildTrace = {
      task: 'recon',
      lines: ['{"error":"LEAGUE_TIMEOUT"}']
    };
    return 1;
  };

  const result = await pipeline.ensureReconGoldenSnapshot({
    pendingCount: 0,
    harvestedCount: 1,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 1,
    rawDeltaSinceRecon: 1
  });

  assert.equal(result.exitCode, 1);
  assert.equal(result.bufferStateAfter.hasGoldenSnapshot, true);
});

test('TotalWarPipeline.close 在存在 activeChild 时必须触发终止信号', async () => {
  let poolClosed = 0;
  let stateSaved = 0;
  let lockReleased = 0;

  const child = createFakeChild();
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once', '--failure-cooldown-ms', '10']), {
    logger: silentLogger
  });

  pipeline.pool = {
    async end() {
      poolClosed++;
    }
  };
  pipeline.stateStore = {
    save() {
      stateSaved++;
    }
  };
  pipeline.lockManager = {
    release() {
      lockReleased++;
    }
  };
  pipeline.options.killGraceMs = 5;

  pipeline.monitorChild(child, {
    maxRuntimeMs: 0,
    killGraceMs: 5
  });

  await pipeline.close();

  assert.deepEqual(child.killSignals, ['SIGTERM', 'SIGKILL']);
  assert.equal(pipeline.activeChild, null);
  assert.equal(poolClosed, 1);
  assert.equal(stateSaved, 1);
  assert.equal(lockReleased, 1);
});

test('TotalWarPipeline.retry-failed-only 模式应优先推进 harvest，并跳过 discovery', () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once', '--retry-failed-only']));
  const metrics = {
    pendingCount: 12,
    harvestedCount: 200,
    mismatchCount: 50,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 0,
    rawDeltaSinceRecon: 0
  };

  assert.equal(pipeline.decideNextTask(metrics), 'harvest');
});

test('TotalWarPipeline.parseArgs 应支持 --concurrency 作为 Harvest/Recon 并发别名', () => {
  const options = parseArgs(['--season', '2025-2026', '--concurrency', '15']);

  assert.equal(options.harvestConcurrency, 15);
  assert.equal(options.reconConcurrency, 15);
  assert.equal(options.discoveryConcurrency, 5);
});

test('TotalWarPipeline.runManagedTask 在 Recon LEAGUE_TIMEOUT 时应标记 deferred', async () => {
  const warnLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season', '2025/2026',
    '--once',
    '--recon-defer-cooldown-ms', '20'
  ]), {
    logger: {
      info() {},
      warn(event, payload) {
        warnLogs.push({ event, payload });
      },
      error() {}
    }
  });

  pipeline.stateStore = {
    save() {}
  };
  pipeline.runChild = async () => {
    pipeline.lastChildTrace = {
      task: 'recon',
      lines: ['{"error":"LEAGUE_TIMEOUT"}']
    };
    return 1;
  };

  await pipeline.runManagedTask('recon', {
    pendingCount: 0,
    harvestedCount: 20,
    mismatchCount: 5,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 100,
    rawDeltaSinceRecon: 10
  });

  assert.equal(pipeline.state.tasks.recon.consecutiveFailures, 0);
  assert.equal(pipeline.state.tasks.recon.lastDeferredReason, 'LEAGUE_TIMEOUT');
  assert.ok(pipeline.state.tasks.recon.deferredUntil);
  assert.ok(warnLogs.some((entry) => entry.event === 'task_deferred'));
});

test('TotalWarPipeline.runCycle 在无任务时应保存状态并直接返回', async () => {
  let saveCount = 0;
  let managedTaskCount = 0;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.collectMetrics = async () => ({
    pendingCount: 0,
    harvestedCount: 0,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 0,
    rawDeltaSinceRecon: 0
  });
  pipeline.decideNextTask = () => null;
  pipeline.stateStore = {
    save() {
      saveCount++;
    }
  };
  pipeline.runManagedTask = async () => {
    managedTaskCount++;
  };

  await pipeline.runCycle();

  assert.equal(saveCount, 1);
  assert.equal(managedTaskCount, 0);
});

test('TotalWarPipeline.runCycle 在 dry-run 下应记录待执行任务但不启动子任务', async () => {
  const infoLogs = [];
  let managedTaskCount = 0;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once', '--dry-run']), {
    logger: {
      info(event, payload) {
        infoLogs.push({ event, payload });
      },
      warn() {},
      error() {}
    }
  });

  pipeline.collectMetrics = async () => ({
    pendingCount: 3,
    harvestedCount: 0,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 0,
    rawDeltaSinceRecon: 0
  });
  pipeline.runManagedTask = async () => {
    managedTaskCount++;
  };

  await pipeline.runCycle();

  assert.equal(managedTaskCount, 0);
  assert.ok(infoLogs.some((entry) => entry.event === 'dry_run_task_selected'));
});

test('TotalWarPipeline.monitorChild 应取消旧监视器，并避免被非活动子进程误清理', () => {
  let childACancelled = 0;
  let childBCancelled = 0;
  const childA = createFakeChild();
  const childB = createFakeChild();
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.processSupervisor = {
    monitorChild(child) {
      return {
        cancel() {
          if (child === childA) {
            childACancelled++;
          } else if (child === childB) {
            childBCancelled++;
          }
        }
      };
    }
  };

  pipeline.monitorChild(childA, {});
  pipeline.monitorChild(childB, {});
  assert.equal(childACancelled, 1);
  assert.equal(pipeline.activeChild, childB);

  pipeline._clearActiveChild(childA);
  assert.equal(pipeline.activeChild, childB);

  pipeline._clearActiveChild(childB);
  assert.equal(childBCancelled, 1);
  assert.equal(pipeline.activeChild, null);
});

test('TotalWarPipeline.runChild 在 spawn error 时应 reject 并清空 activeChild', async () => {
  const child = createFakeChild();
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.processSupervisor = {
    spawnChild() {
      setImmediate(() => {
        child.emit('error', new Error('spawn failed'));
      });
      return child;
    },
    monitorChild() {
      return {
        cancel() {}
      };
    }
  };

  await assert.rejects(
    () => pipeline.runChild({
      task: 'harvest',
      command: 'not-a-real-command',
      args: []
    }),
    /spawn failed/
  );

  assert.equal(pipeline.activeChild, null);
});

test('TotalWarPipeline.collectMetrics 应解析数据库计数与 raw 增量', async () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.state.lastReconRawCount = 10;
  pipeline.pool = {
    async query(sql) {
      if (sql.includes('raw_match_data')) {
        return {
          rows: [{ raw_count: '25' }]
        };
      }

      return {
        rows: [{
          pending_count: '1',
          harvested_count: '2',
          mismatch_count: '3',
          failed_count: '4',
          linked_count: '5'
        }]
      };
    }
  };

  const metrics = await pipeline.collectMetrics();

  assert.deepEqual(metrics, {
    pendingCount: 1,
    harvestedCount: 2,
    mismatchCount: 3,
    failedCount: 4,
    linkedCount: 5,
    rawCount: 25,
    rawDeltaSinceRecon: 15
  });
});

test('TotalWarPipeline.markTaskFailure 达到阈值时应进入 cooldown', () => {
  const warnLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season',
    '2025/2026',
    '--once',
    '--failure-limit',
    '2',
    '--failure-cooldown-ms',
    '50'
  ]), {
    logger: {
      info() {},
      warn(event, payload) {
        warnLogs.push({ event, payload });
      },
      error() {}
    }
  });

  pipeline.markTaskFailure('harvest');
  assert.equal(pipeline.state.tasks.harvest.consecutiveFailures, 1);
  assert.equal(pipeline.state.tasks.harvest.cooldownUntil, null);

  pipeline.markTaskFailure('harvest');
  assert.equal(pipeline.state.tasks.harvest.consecutiveFailures, 2);
  assert.ok(pipeline.state.tasks.harvest.cooldownUntil);
  assert.ok(warnLogs.some((entry) => entry.event === 'task_cooldown_armed'));
});

test('TotalWarPipeline.init 应加载持久状态并注册信号处理', { concurrency: false }, async () => {
  const signals = [];
  let acquired = 0;
  const originalOnce = process.once;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  pipeline.lockManager = {
    acquire() {
      acquired += 1;
    },
    release() {}
  };
  pipeline.stateStore = {
    load() {
      return {
        lastDiscoveryAt: '2026-04-21T08:00:00.000Z',
        tasks: {
          harvest: {
            consecutiveFailures: 2
          }
        }
      };
    },
    save() {}
  };

  process.once = (signal, handler) => {
    signals.push({ signal, handler });
    return process;
  };

  try {
    pipeline.init();
  } finally {
    process.once = originalOnce;
  }

  assert.equal(acquired, 1);
  assert.deepEqual(signals.map((entry) => entry.signal), ['SIGINT', 'SIGTERM']);
  assert.equal(pipeline.state.lastDiscoveryAt, '2026-04-21T08:00:00.000Z');
  assert.equal(pipeline.state.tasks.harvest.consecutiveFailures, 2);

  await pipeline.close();
});

test('TotalWarPipeline.run 在循环失败后应记录错误并继续执行到 stopRequested', async () => {
  const errorLogs = [];
  let cycles = 0;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--loop-ms', '0']), {
    logger: {
      info() {},
      warn() {},
      error(event, payload) {
        errorLogs.push({ event, payload });
      }
    }
  });

  pipeline.options.once = false;
  pipeline.runCycle = async () => {
    cycles += 1;
    if (cycles === 1) {
      throw new Error('cycle boom');
    }
    pipeline.stopRequested = true;
  };

  await pipeline.run();

  assert.equal(cycles, 2);
  assert.ok(errorLogs.some((entry) => entry.event === 'cycle_failed' && entry.payload?.error === 'cycle boom'));
});

test('TotalWarPipeline.decideNextTask 遇到 cooldown 时应记录告警并返回 null', () => {
  const warnLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info() {},
      warn(event, payload) {
        warnLogs.push({ event, payload });
      },
      error() {}
    }
  });

  pipeline.state.lastDiscoveryAt = new Date().toISOString();
  pipeline.state.tasks.harvest.cooldownUntil = new Date(Date.now() + 60_000).toISOString();

  const task = pipeline.decideNextTask({
    pendingCount: 3,
    harvestedCount: 0,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 10,
    rawDeltaSinceRecon: 0
  });

  assert.equal(task, null);
  assert.ok(warnLogs.some((entry) => entry.event === 'task_in_cooldown' && entry.payload?.task === 'harvest'));
});

test('TotalWarPipeline 辅助状态判断应覆盖 recon 阈值与 blockedUntil 合并', () => {
  const pipeline = new TotalWarPipeline(parseArgs([
    '--season', '2025/2026',
    '--once',
    '--recon-threshold', '10'
  ]), {
    logger: silentLogger
  });

  assert.equal(pipeline._isReconDue({
    pendingCount: 2,
    harvestedCount: 3,
    mismatchCount: 0,
    rawCount: 5
  }), false);
  assert.equal(pipeline._isReconDue({
    pendingCount: 0,
    harvestedCount: 0,
    mismatchCount: 0,
    rawCount: 0
  }), false);

  assert.equal(pipeline._resolveTaskBlockedUntil(null), null);
  assert.equal(pipeline._resolveTaskBlockedUntil({
    cooldownUntil: 'bad-date',
    deferredUntil: '2026-04-21T09:00:00.000Z'
  }), '2026-04-21T09:00:00.000Z');
});

test('TotalWarPipeline.runManagedTask 在 preflight 失败且非超时时应记失败', async () => {
  const warnLogs = [];
  let saveCount = 0;
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info() {},
      warn(event, payload) {
        warnLogs.push({ event, payload });
      },
      error() {}
    }
  });

  pipeline.stateStore = {
    save() {
      saveCount += 1;
    }
  };
  pipeline.ensureReconGoldenSnapshot = async () => ({ exitCode: 2, skipped: false });
  pipeline.lastChildTrace = {
    task: 'recon',
    lines: ['{"error":"SOFT_FAILURE"}']
  };

  await pipeline.runManagedTask('recon', {
    pendingCount: 0,
    harvestedCount: 1,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 10,
    rawDeltaSinceRecon: 1
  });

  assert.equal(pipeline.state.tasks.recon.consecutiveFailures, 1);
  assert.equal(pipeline.state.tasks.recon.lastDeferredReason, null);
  assert.equal(saveCount, 1);
  assert.ok(warnLogs.some((entry) => entry.event === 'task_failure' && entry.payload?.phase === 'preflight'));
});

test('TotalWarPipeline.ensureReconGoldenSnapshot 应覆盖 skip、lease busy 与缺失 golden snapshot', async () => {
  const errorLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info() {},
      warn() {},
      error(event, payload) {
        errorLogs.push({ event, payload });
      }
    }
  });

  const releasedLeases = [];
  let inspectCount = 0;
  pipeline._createReconSessionManager = () => ({
    inspectBufferPool() {
      inspectCount += 1;
      if (inspectCount === 1) {
        return {
          needsRefresh: false,
          path: '/tmp/buffer.json',
          goldenUpdatedAt: '2026-04-21T08:00:00.000Z',
          goldenAgeMs: 10,
          ttlMs: 1000
        };
      }
      if (inspectCount === 2) {
        return {
          needsRefresh: true,
          path: '/tmp/buffer.json',
          goldenUpdatedAt: null,
          goldenAgeMs: null,
          ttlMs: 1000
        };
      }
      if (inspectCount === 3) {
        return {
          needsRefresh: true,
          path: '/tmp/buffer.json',
          goldenUpdatedAt: null,
          goldenAgeMs: null,
          ttlMs: 1000
        };
      }
      return {
        hasGoldenSnapshot: false,
        goldenUpdatedAt: null,
        goldenAgeMs: null,
        ttlMs: 1000
      };
    },
    acquireGoldenRefreshLease() {
      if (inspectCount === 2) {
        return { acquired: false, lease: { id: 'busy-lease' } };
      }
      return { acquired: true, lease: { id: 'refresh-lease' } };
    },
    releaseGoldenRefreshLease(lease) {
      releasedLeases.push(lease?.id || null);
    }
  });

  const skipped = await pipeline.ensureReconGoldenSnapshot({});
  assert.equal(skipped.exitCode, 0);
  assert.equal(skipped.skipped, true);

  const busy = await pipeline.ensureReconGoldenSnapshot({});
  assert.equal(busy.exitCode, 0);
  assert.equal(busy.leaseBusy, true);

  pipeline.runChild = async () => 0;
  const missingGolden = await pipeline.ensureReconGoldenSnapshot({});
  assert.equal(missingGolden.exitCode, 1);
  assert.equal(missingGolden.skipped, false);
  assert.ok(releasedLeases.includes('refresh-lease'));
  assert.ok(errorLogs.some((entry) => entry.event === 'recon_session_preflight_missing_golden_snapshot'));
});

test('TotalWarPipeline.buildTaskEnv、buildTaskCommand 与 markTaskSuccess 应覆盖收口分支', () => {
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger
  });

  const nonReconEnv = pipeline.buildTaskEnv('harvest');
  assert.notEqual(nonReconEnv, process.env);
  assert.equal(nonReconEnv.DB_HOST, process.env.DB_HOST);

  const reconEnv = pipeline.buildTaskEnv('recon', {
    phase: 'preflight',
    forceGoldenRefresh: true
  });
  assert.equal(reconEnv.RECON_SESSION_BUFFER_ROLE, 'preflight');
  assert.equal(reconEnv.RECON_SESSION_FORCE_REFRESH, 'true');

  assert.throws(() => pipeline.buildTaskCommand('unknown-task'), /未知任务/);

  pipeline.markTaskSuccess('discovery', { rawCount: 0 });
  pipeline.markTaskSuccess('harvest', { rawCount: 0 });
  pipeline.markTaskSuccess('recon', { rawCount: 33 });

  assert.ok(pipeline.state.lastDiscoveryAt);
  assert.ok(pipeline.state.lastHarvestAt);
  assert.ok(pipeline.state.lastReconAt);
  assert.equal(pipeline.state.lastReconRawCount, 33);
});

test('TotalWarPipeline.runChild 与 collectMetrics 应覆盖默认兜底分支', async () => {
  const child = new EventEmitter();
  child.stdout = null;
  child.stderr = null;
  child.kill = () => true;

  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: silentLogger,
    spawnImpl() {
      setImmediate(() => {
        child.emit('close', null);
      });
      return child;
    }
  });

  const exitCode = await pipeline.runChild({
    task: 'discovery',
    command: 'node',
    args: []
  });

  assert.equal(exitCode, 1);

  pipeline.pool = {
    async query(sql) {
      return sql.includes('raw_match_data')
        ? { rows: [] }
        : { rows: [] };
    }
  };

  const metrics = await pipeline.collectMetrics();
  assert.deepEqual(metrics, {
    pendingCount: 0,
    harvestedCount: 0,
    mismatchCount: 0,
    failedCount: 0,
    linkedCount: 0,
    rawCount: 0,
    rawDeltaSinceRecon: 0
  });
});

test('TotalWarPipeline.close 应优先复用 closePromise、走 terminateChild 并记录 kill 失败', async () => {
  const errorLogs = [];
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']), {
    logger: {
      info() {},
      warn() {},
      error(event, payload) {
        errorLogs.push({ event, payload });
      }
    }
  });

  const reusedPromise = Promise.resolve('reused');
  pipeline.closePromise = reusedPromise;
  assert.equal(await pipeline.close(), 'reused');

  let terminated = 0;
  let saved = 0;
  let released = 0;
  const activeChild = createFakeChild();
  pipeline.closePromise = null;
  pipeline.activeChild = activeChild;
  pipeline.activeChildMonitor = {
    cancel() {}
  };
  pipeline.processSupervisor = {
    async terminateChild(child) {
      assert.equal(child, activeChild);
      terminated += 1;
    }
  };
  pipeline.pool = {
    async end() {}
  };
  pipeline.stateStore = {
    save() {
      saved += 1;
    }
  };
  pipeline.lockManager = {
    release() {
      released += 1;
    }
  };

  await pipeline.close();
  assert.equal(terminated, 1);
  assert.equal(saved, 1);
  assert.equal(released, 1);

  const failingChild = {
    pid: 999,
    kill() {
      throw new Error('sigterm failed');
    }
  };
  pipeline.closePromise = null;
  pipeline.activeChild = failingChild;
  pipeline.activeChildMonitor = null;
  pipeline.processSupervisor = null;
  pipeline.pool = null;

  await pipeline.close();

  assert.ok(errorLogs.some((entry) => entry.event === 'child_sigterm_failed' && entry.payload?.pid === 999));
});
