'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ProcessSupervisor } = require('../../src/core/process/ProcessSupervisor');

function createChild(options = {}) {
  const listeners = new Map();
  const signals = [];
  const offCalls = [];
  const removeCalls = [];

  return {
    pid: options.pid || 4321,
    signals,
    offCalls,
    removeCalls,
    on(event, handler) {
      listeners.set(event, handler);
    },
    off(event, handler) {
      offCalls.push({ event, handler });
      listeners.delete(event);
    },
    removeListener(event, handler) {
      removeCalls.push({ event, handler });
      listeners.delete(event);
    },
    emit(event) {
      listeners.get(event)?.();
    },
    kill(signal) {
      if (options.throwOnSignal === signal) {
        throw new Error(`${signal} failed`);
      }
      signals.push(signal);
      return true;
    }
  };
}

describe('ProcessSupervisor', () => {
  it('默认 logger no-op 方法应可直接执行', () => {
    const supervisor = new ProcessSupervisor();

    assert.doesNotThrow(() => supervisor.logger.info('noop-info'));
    assert.doesNotThrow(() => supervisor.logger.warn('noop-warn'));
    assert.doesNotThrow(() => supervisor.logger.error('noop-error'));
  });

  it('spawnChild 应调用注入的 spawnImpl', () => {
    const calls = [];
    const childRef = {};
    const supervisor = new ProcessSupervisor({
      spawnImpl(command, args, spawnOptions) {
        calls.push({ command, args, spawnOptions });
        return childRef;
      }
    });

    const child = supervisor.spawnChild('node', ['app.js'], { cwd: '/tmp/app' });

    assert.strictEqual(child, childRef);
    assert.deepStrictEqual(calls, [{
      command: 'node',
      args: ['app.js'],
      spawnOptions: { cwd: '/tmp/app' }
    }]);
  });

  it('detachCloseListener 与 sendSignal 应覆盖 off/removeListener 和失败日志分支', () => {
    const errors = [];
    const childWithOff = createChild();
    const childWithoutOff = createChild();
    delete childWithoutOff.off;

    const supervisor = new ProcessSupervisor({
      logger: {
        info() {},
        warn() {},
        error(event, payload) {
          errors.push({ event, payload });
        }
      }
    });

    const noop = () => {};
    supervisor._detachCloseListener(null, noop);
    supervisor._detachCloseListener(childWithOff, null);
    supervisor._detachCloseListener(childWithOff, noop);
    supervisor._detachCloseListener(childWithoutOff, noop);

    assert.strictEqual(childWithOff.offCalls.length, 1);
    assert.strictEqual(childWithoutOff.removeCalls.length, 1);
    assert.strictEqual(supervisor._sendSignal(createChild(), 'SIGTERM', 'sigterm_failed'), true);
    assert.strictEqual(
      supervisor._sendSignal(createChild({ throwOnSignal: 'SIGKILL' }), 'SIGKILL', 'sigkill_failed'),
      false
    );
    assert.ok(errors.some((entry) => entry.event === 'sigkill_failed'));
  });

  it('terminateChild 应支持无效 child、优雅退出、立即完成与强杀路径', async () => {
    const warnings = [];
    const timers = [];
    const cleared = [];
    const supervisor = new ProcessSupervisor({
      logger: {
        info() {},
        warn(event, payload) {
          warnings.push({ event, payload });
        },
        error() {}
      },
      setTimeout(handler, ms) {
        const timer = { handler, ms };
        timers.push(timer);
        return timer;
      },
      clearTimeout(timer) {
        cleared.push(timer);
      }
    });

    assert.deepStrictEqual(
      await supervisor.terminateChild(null),
      { terminated: false, forced: false }
    );

    const gracefulChild = createChild({ pid: 11 });
    const gracefulPromise = supervisor.terminateChild(gracefulChild, { killGraceMs: 25 });
    gracefulChild.emit('close');
    assert.deepStrictEqual(await gracefulPromise, { terminated: true, forced: false });
    assert.deepStrictEqual(gracefulChild.signals, ['SIGTERM']);
    assert.strictEqual(cleared.length >= 1, true);

    const immediateChild = createChild({ pid: 12 });
    assert.deepStrictEqual(
      await supervisor.terminateChild(immediateChild, { killGraceMs: 0 }),
      { terminated: true, forced: false }
    );
    assert.deepStrictEqual(immediateChild.signals, ['SIGTERM']);

    const forcedChild = createChild({ pid: 13 });
    const forcedPromise = supervisor.terminateChild(forcedChild, { killGraceMs: 10 });
    const lastTimer = timers[timers.length - 1];
    lastTimer.handler();
    assert.deepStrictEqual(await forcedPromise, { terminated: true, forced: true });
    assert.deepStrictEqual(forcedChild.signals, ['SIGTERM', 'SIGKILL']);
    assert.ok(warnings.some((entry) => entry.event === 'child_force_kill'));

    const stickyChild = createChild({ pid: 14 });
    stickyChild.off = () => {};
    const stickyPromise = supervisor.terminateChild(stickyChild, { killGraceMs: 15 });
    const stickyTimer = timers[timers.length - 1];
    stickyChild.emit('close');
    stickyChild.emit('close');
    stickyTimer.handler();

    assert.deepStrictEqual(await stickyPromise, { terminated: true, forced: false });
  });

  it('monitorChild 应处理超时监控、强杀与 cancel', () => {
    const warnings = [];
    const timers = [];
    const cleared = [];
    const supervisor = new ProcessSupervisor({
      logger: {
        info() {},
        warn(event, payload) {
          warnings.push({ event, payload });
        },
        error() {}
      },
      setTimeout(handler, ms) {
        const timer = { handler, ms };
        timers.push(timer);
        return timer;
      },
      clearTimeout(timer) {
        cleared.push(timer);
      }
    });

    const invalidHandle = supervisor.monitorChild(null);
    assert.doesNotThrow(() => invalidHandle.cancel());

    const child = createChild({ pid: 21 });
    const handle = supervisor.monitorChild(child, { maxRuntimeMs: 30, killGraceMs: 10 });
    timers[0].handler();
    timers[1].handler();
    child.emit('close');

    assert.deepStrictEqual(child.signals, ['SIGTERM', 'SIGKILL']);
    assert.ok(warnings.some((entry) => entry.event === 'child_runtime_exceeded'));
    assert.ok(warnings.some((entry) => entry.event === 'child_force_kill'));
    assert.strictEqual(cleared.length >= 2, true);

    const cancelChild = createChild({ pid: 22 });
    const cancelHandle = supervisor.monitorChild(cancelChild, { maxRuntimeMs: 50, killGraceMs: 5 });
    cancelHandle.cancel();
    const cancelledTermTimer = timers[timers.length - 1];
    cancelledTermTimer.handler();

    assert.deepStrictEqual(cancelChild.signals, []);
    assert.strictEqual(cancelChild.offCalls.length, 1);
    assert.strictEqual(cleared.length >= 3, true);
    assert.doesNotThrow(() => handle.cancel());

    const lateCloseChild = createChild({ pid: 23 });
    const lateHandle = supervisor.monitorChild(lateCloseChild, { maxRuntimeMs: 40, killGraceMs: 5 });
    const lateTermTimer = timers[timers.length - 1];
    lateTermTimer.handler();
    const lateKillTimer = timers[timers.length - 1];
    lateCloseChild.emit('close');
    lateKillTimer.handler();

    assert.deepStrictEqual(lateCloseChild.signals, ['SIGTERM']);
    assert.doesNotThrow(() => lateHandle.cancel());
  });
});
