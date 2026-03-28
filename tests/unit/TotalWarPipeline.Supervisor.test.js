'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

const { TotalWarPipeline, parseArgs, sleep } = require('../../scripts/ops/total_war_pipeline');

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
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once']));
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

test('TotalWarPipeline.close 在存在 activeChild 时必须触发终止信号', async () => {
  let poolClosed = 0;
  let stateSaved = 0;
  let lockReleased = 0;

  const child = createFakeChild();
  const pipeline = new TotalWarPipeline(parseArgs(['--season', '2025/2026', '--once', '--failure-cooldown-ms', '10']));

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
