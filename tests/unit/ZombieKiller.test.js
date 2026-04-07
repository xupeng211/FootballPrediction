'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const childProcess = require('node:child_process');

const MODULE_PATH = path.resolve(__dirname, '../../src/core/process/ZombieKiller.js');

function loadZombieKiller(execSyncImpl) {
  const originalExecSync = childProcess.execSync;
  childProcess.execSync = execSyncImpl;
  delete require.cache[MODULE_PATH];

  try {
    return require(MODULE_PATH);
  } finally {
    childProcess.execSync = originalExecSync;
  }
}

describe('src/core/process/ZombieKiller', () => {
  const originalConsoleLog = console.log;
  const originalSetInterval = global.setInterval;
  const originalClearInterval = global.clearInterval;

  afterEach(() => {
    console.log = originalConsoleLog;
    global.setInterval = originalSetInterval;
    global.clearInterval = originalClearInterval;
    delete require.cache[MODULE_PATH];
  });

  test('应解析常规进程、defunct 进程、超时进程与 elapsed time', () => {
    const commands = [];
    const { ZombieKiller } = loadZombieKiller((command, options) => {
      commands.push({ command, options });

      if (command.startsWith('pgrep -f')) {
        return '123\n456\nabc\n';
      }
      if (command.startsWith('ps aux')) {
        return 'root 222 111 0.0 0.0 0 0 Z 00:00 0:00 node <defunct>\n';
      }
      if (command.startsWith('ps -eo pid,etime,cmd')) {
        return '333 00:10:00 /usr/bin/chromium --headless\n444 04:59 chrome --new-window';
      }

      throw new Error(`unexpected command: ${command}`);
    });

    const killer = new ZombieKiller({
      maxProcessAge: 5 * 60 * 1000,
      silent: true,
      targetProcesses: ['chromium', 'chrome'],
    });

    assert.deepStrictEqual(killer.findZombieProcesses(), ['123', '456']);
    assert.deepStrictEqual(killer.findDefunctProcesses(), [{
      user: 'root',
      pid: '222',
      ppid: '111',
      stat: 'Z',
      cmd: 'node <defunct>',
    }]);
    assert.deepStrictEqual(killer.findStaleProcesses(), [{
      pid: '333',
      etime: '00:10:00',
      cmd: '/usr/bin/chromium --headless',
      ageMs: 600000,
    }]);

    assert.strictEqual(killer._parseElapsedTime('00:05:00'), 300000);
    assert.strictEqual(killer._parseElapsedTime('5:30'), 330000);
    assert.strictEqual(killer._parseElapsedTime('invalid'), 0);
    assert.ok(commands.every(entry => typeof entry.options.timeout === 'number'));
  });

  test('命令失败时应优雅降级并输出告警日志', () => {
    const logs = [];
    console.log = message => {
      logs.push(message);
    };

    const { ZombieKiller } = loadZombieKiller(command => {
      if (
        command.startsWith('pgrep -f')
        || command.startsWith('ps aux')
        || command.startsWith('ps -eo pid,etime,cmd')
      ) {
        throw new Error('command unavailable');
      }

      return '';
    });

    const killer = new ZombieKiller({ silent: false });

    assert.deepStrictEqual(killer.findZombieProcesses(), []);
    assert.deepStrictEqual(killer.findDefunctProcesses(), []);
    assert.deepStrictEqual(killer.findStaleProcesses(), []);
    assert.strictEqual(killer.hasZombieProcesses(), false);
    assert.strictEqual(killer.hasDefunctProcesses(), false);
    assert.deepStrictEqual(killer.getZombieStats(), {
      regular: 0,
      defunct: 0,
      stale: 0,
    });
    assert.ok(logs.some(message => message.includes('查找进程失败')));
    assert.ok(logs.some(message => message.includes('查找 defunct 进程失败')));
    assert.ok(logs.some(message => message.includes('查找超时进程失败')));
  });

  test('killProcess 与 killProcessTree 应处理成功、失败与递归子进程', () => {
    const calls = [];
    const { ZombieKiller } = loadZombieKiller(command => {
      calls.push(command);

      if (command === 'kill -9 100 2>/dev/null || true') {
        return '';
      }
      if (command === 'kill -15 200 2>/dev/null || true') {
        throw new Error('EPERM');
      }
      if (command === 'pgrep -P 10 2>/dev/null || true') {
        return '11\n12';
      }
      if (command === 'pgrep -P 11 2>/dev/null || true') {
        return '';
      }
      if (command === 'pgrep -P 12 2>/dev/null || true') {
        return '';
      }
      if (
        command === 'kill -9 10 2>/dev/null || true'
        || command === 'kill -9 11 2>/dev/null || true'
        || command === 'kill -9 12 2>/dev/null || true'
      ) {
        return '';
      }

      throw new Error(`unexpected command: ${command}`);
    });

    const killer = new ZombieKiller({ silent: true });

    assert.strictEqual(killer.killProcess('100', true), true);
    assert.strictEqual(killer.killProcess('200', false), false);
    assert.strictEqual(killer.killProcessTree('10'), 3);
    assert.ok(calls.includes('pgrep -P 10 2>/dev/null || true'));
  });

  test('preFlightCleanup 应汇总常规、defunct 与超时进程统计，并记录异常兜底', () => {
    const { ZombieKiller } = loadZombieKiller(() => '');
    const killer = new ZombieKiller({ silent: true, maxProcessAge: 10 * 60 * 1000 });
    const logs = [];
    const parentKillCalls = [];

    killer._log = (level, message) => {
      logs.push([level, message]);
    };
    killer.findZombieProcesses = () => ['101', '102'];
    killer.findDefunctProcesses = () => [
      { ppid: '201', pid: '301' },
      { ppid: '1', pid: '302' },
    ];
    killer.findStaleProcesses = () => [
      { pid: '401', etime: '00:12:00' },
      { pid: '402', etime: '00:15:00' },
    ];
    killer.killProcess = (pid, force) => {
      parentKillCalls.push({ pid, force });
      return true;
    };
    killer.killProcessTree = pid => ({
      '101': 2,
      '102': 0,
      '401': 1,
      '402': 1,
    }[pid] ?? 0);

    const stats = killer.preFlightCleanup(9);
    assert.deepStrictEqual(stats, {
      found: 2,
      killed: 4,
      failed: 1,
      defunct: 2,
      stale: 2,
      pids: ['101'],
    });
    assert.strictEqual(killer.getLastStats(), stats);
    assert.deepStrictEqual(parentKillCalls, [{ pid: '201', force: false }]);
    assert.ok(logs.some(([level, message]) => level === 'info' && message.includes('[W9] 发现 2 个进程')));
    assert.ok(logs.some(([level, message]) => level === 'warn' && message.includes('defunct')));
    assert.ok(logs.some(([level, message]) => level === 'debug' && message.includes('清理超时进程 PID 401')));
    assert.ok(logs.some(([level, message]) => level === 'info' && message.includes('清理完成')));

    killer.findZombieProcesses = () => {
      throw new Error('probe failed');
    };
    const fallbackStats = killer.preFlightCleanup();
    assert.deepStrictEqual(fallbackStats, {
      found: 0,
      killed: 0,
      failed: 0,
      defunct: 0,
      stale: 0,
      pids: [],
    });
    assert.ok(logs.some(([level, message]) => level === 'warn' && message.includes('清理检查失败')));
  });

  test('forceKillBrowser、定期扫描、静态入口与便捷函数应正常工作', () => {
    let intervalId = 0;
    let scheduledCallback = null;
    const cleared = [];

    global.setInterval = (callback, interval) => {
      scheduledCallback = callback;
      intervalId += 1;
      return { id: intervalId, interval };
    };
    global.clearInterval = timer => {
      cleared.push(timer);
    };

    const { ZombieKiller, preFlightCleanup, forceKillBrowser, getZombieStats } = loadZombieKiller(command => {
      if (command === 'pgrep -P $$ 2>/dev/null || true') {
        return '501\n502';
      }

      throw new Error(`unexpected command: ${command}`);
    });

    const killer = new ZombieKiller({ silent: false });
    const logs = [];
    killer._log = (level, message) => {
      logs.push([level, message]);
    };
    killer.killProcessTree = () => 1;

    const forceStats = killer.forceKillBrowser(3);
    assert.deepStrictEqual(forceStats, {
      found: 2,
      killed: 2,
      pids: ['501', '502'],
    });
    assert.ok(logs.some(([level, message]) => level === 'debug' && message.includes('[W3] 已强制清理 2 个子进程')));

    killer._scanInterval = { id: 'old' };
    killer.preFlightCleanup = () => ({ defunct: 6 });
    killer.startPeriodicScan(1500);
    assert.strictEqual(cleared.length, 1);
    assert.deepStrictEqual(killer._scanInterval, { id: 1, interval: 1500 });
    assert.ok(logs.some(([, message]) => message.includes('启动定期僵尸扫描')));

    scheduledCallback();
    assert.ok(logs.some(([level, message]) => level === 'warn' && message.includes('可能需要重启容器')));

    killer.stopPeriodicScan();
    assert.strictEqual(killer._scanInterval, null);
    assert.strictEqual(cleared.length, 2);
    assert.ok(logs.some(([, message]) => message.includes('定期僵尸扫描已停止')));

    const originalPreFlightCleanup = ZombieKiller.prototype.preFlightCleanup;
    const originalForceKill = ZombieKiller.prototype.forceKillBrowser;
    const originalGetStats = ZombieKiller.prototype.getZombieStats;

    ZombieKiller.prototype.preFlightCleanup = function(workerId) {
      return { workerId, source: 'quick' };
    };
    ZombieKiller.prototype.forceKillBrowser = function(workerId) {
      return { workerId, source: 'force' };
    };
    ZombieKiller.prototype.getZombieStats = function() {
      return { source: 'stats' };
    };

    try {
      assert.deepStrictEqual(ZombieKiller.quickClean(11), { workerId: 11, source: 'quick' });
      assert.deepStrictEqual(ZombieKiller.forceKillBrowser(12), { workerId: 12, source: 'force' });
      assert.deepStrictEqual(ZombieKiller.getStats(), { source: 'stats' });
      assert.deepStrictEqual(preFlightCleanup(21), { workerId: 21, source: 'quick' });
      assert.deepStrictEqual(forceKillBrowser(22), { workerId: 22, source: 'force' });
      assert.deepStrictEqual(getZombieStats(), { source: 'stats' });
    } finally {
      ZombieKiller.prototype.preFlightCleanup = originalPreFlightCleanup;
      ZombieKiller.prototype.forceKillBrowser = originalForceKill;
      ZombieKiller.prototype.getZombieStats = originalGetStats;
    }
  });
});
