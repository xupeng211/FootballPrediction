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
