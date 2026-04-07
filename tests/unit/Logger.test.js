'use strict';

const { afterEach, describe, test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const MODULE_PATH = path.resolve(__dirname, '../../src/infrastructure/utils/Logger.js');
const WINSTON_ID = require.resolve('winston');
const ROTATE_ID = require.resolve('winston-daily-rotate-file');

function overrideModule(moduleId, exportsValue) {
  const previous = require.cache[moduleId];
  require.cache[moduleId] = {
    id: moduleId,
    filename: moduleId,
    loaded: true,
    exports: exportsValue,
  };

  return () => {
    if (previous) {
      require.cache[moduleId] = previous;
    } else {
      delete require.cache[moduleId];
    }
  };
}

function loadLoggerModule(options = {}) {
  const {
    env = {},
    argv = ['node', '--test', 'tests/unit/Logger.test.js'],
    chdir = null,
    fakeCwd = null,
  } = options;

  const envKeys = ['NODE_ENV', 'LOG_LEVEL', 'DISABLE_FILE_LOG', 'NODE_TEST_CONTEXT'];
  const envSnapshot = new Map();
  for (const key of envKeys) {
    envSnapshot.set(key, process.env[key]);
  }

  for (const key of envKeys) {
    if (Object.prototype.hasOwnProperty.call(env, key)) {
      process.env[key] = env[key];
    } else {
      delete process.env[key];
    }
  }

  const consoleMessages = [];
  const originalConsoleLog = console.log;
  const originalConsoleWarn = console.warn;
  const originalArgv = process.argv;
  const originalCwd = process.cwd;
  const previousDir = process.cwd();

  console.log = (...args) => {
    consoleMessages.push(['log', args.join(' ')]);
  };
  console.warn = (...args) => {
    consoleMessages.push(['warn', args.join(' ')]);
  };
  process.argv = argv.slice();

  if (chdir) {
    process.chdir(chdir);
  }
  if (fakeCwd) {
    process.cwd = () => fakeCwd;
  }

  const winstonState = { created: [] };

  class FakeConsoleTransport {
    constructor(options) {
      this.options = options;
    }
  }

  class FakeRotateFile {
    constructor(options) {
      this.options = options;
    }
  }

  const fakeWinston = {
    format: {
      combine: (...parts) => ({ type: 'combine', parts }),
      timestamp: options => ({ type: 'timestamp', options }),
      printf: formatter => ({ type: 'printf', formatter }),
      errors: options => ({ type: 'errors', options }),
      json: () => ({ type: 'json' }),
    },
    transports: {
      Console: FakeConsoleTransport,
    },
    createLogger(options) {
      const calls = [];
      const logger = {
        options,
        transports: options.transports,
        calls,
        info: (...args) => calls.push(['info', ...args]),
        warn: (...args) => calls.push(['warn', ...args]),
        error: (...args) => calls.push(['error', ...args]),
        debug: (...args) => calls.push(['debug', ...args]),
        verbose: (...args) => calls.push(['verbose', ...args]),
      };
      winstonState.created.push(logger);
      return logger;
    },
  };

  const restoreWinston = overrideModule(WINSTON_ID, fakeWinston);
  const restoreRotate = overrideModule(ROTATE_ID, FakeRotateFile);

  delete require.cache[MODULE_PATH];

  let loaded;
  try {
    loaded = require(MODULE_PATH);
  } finally {
    restoreWinston();
    restoreRotate();
    process.argv = originalArgv;
    process.cwd = originalCwd;
    if (chdir) {
      process.chdir(previousDir);
    }
    console.log = originalConsoleLog;
    console.warn = originalConsoleWarn;

    for (const key of envKeys) {
      const value = envSnapshot.get(key);
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }

  return { ...loaded, consoleMessages, winstonState };
}

describe('infrastructure/utils/Logger', () => {
  afterEach(() => {
    delete require.cache[MODULE_PATH];
  });

  test('测试环境应仅启用控制台传输，并覆盖基础与企业日志方法', () => {
    const loaded = loadLoggerModule({
      env: {
        NODE_ENV: 'test',
        DISABLE_FILE_LOG: 'true',
      },
    });
    const instance = loaded.getLogger();
    const createdLogger = loaded.winstonState.created[0];

    assert.strictEqual(instance, loaded.logger);
    assert.strictEqual(new loaded.EnterpriseLogger(), instance);
    assert.strictEqual(createdLogger.options.transports.length, 1);
    assert.strictEqual(createdLogger.options.exceptionHandlers, undefined);
    assert.strictEqual(createdLogger.options.rejectionHandlers, undefined);

    instance.info('info-message', { workerId: 1 });
    instance.warn('warn-message', { proxyPort: 7890 });
    instance.error('error-with-error', new Error('boom'), { matchId: 'abcdefghi' });
    instance.error('error-with-meta', { reason: 'plain' }, { event: 'meta' });
    instance.debug('debug-message', { trace: true });
    instance.verbose('verbose-message', { detail: 1 });
    instance.logWorkerStart(2, 7891, { source: 'suite' });
    instance.logHarvestSuccess(2, 'match-1', 7891, { season: '2025/2026' });
    instance.logRetry(3, 'match-2', 2, 7891, 7892, 'TIMEOUT', 'network');
    instance.logFatal('fatal-message', new Error('fatal'));
    instance.logRetryableError(4, 'match-3', 'TIMEOUT', 'slow proxy', { stage: 'recon' });
    instance.logWebGLFingerprint(5, 'RendererNameLongEnoughToBeTrimmedForPreview');
    instance.logGracefulShutdown('SIGTERM', 6);
    instance.logShutdownComplete(3500, { completed: 12 });

    const workerLogger = instance.createWorkerLogger(8, 9000);
    workerLogger.info('child-info', { round: 1 });
    workerLogger.warn('child-warn');
    workerLogger.error('child-error', new Error('child-fail'));
    workerLogger.debug('child-debug');
    workerLogger.logRetry('match-4', 3, 9001, 'CAPTCHA', 'escalated');
    workerLogger.logSuccess('match-5', { attempts: 1 });
    workerLogger.logWebGL('WorkerRenderer');

    const levels = createdLogger.calls.map(entry => entry[0]);
    assert.ok(levels.includes('info'));
    assert.ok(levels.includes('warn'));
    assert.ok(levels.includes('error'));
    assert.ok(levels.includes('debug'));
    assert.ok(levels.includes('verbose'));

    const errorEntry = createdLogger.calls.find(entry => entry[1] === 'error-with-error');
    assert.strictEqual(errorEntry[2].errorName, 'Error');
    assert.strictEqual(errorEntry[2].errorMessage, 'boom');

    const fatalEntry = createdLogger.calls.find(entry => entry[1] === '💀 FATAL: fatal-message');
    assert.strictEqual(fatalEntry[2].severity, 'FATAL');

    const childInfo = createdLogger.calls.find(entry => entry[1] === 'child-info');
    assert.strictEqual(childInfo[2].workerId, 8);
    assert.strictEqual(childInfo[2].proxyPort, 9000);
  });

  test('非测试环境应创建日志目录并启用文件传输、异常处理器与拒绝处理器', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'logger-suite-'));
    const logsDir = path.join(tempDir, 'logs');

    assert.strictEqual(fs.existsSync(logsDir), false);

    const loaded = loadLoggerModule({
      env: {
        NODE_ENV: 'production',
      },
      argv: ['node', 'scripts/run.js'],
      chdir: tempDir,
    });

    assert.strictEqual(fs.existsSync(logsDir), true);
    assert.strictEqual(loaded.winstonState.created[0].options.transports.length, 3);
    assert.strictEqual(loaded.winstonState.created[0].options.exceptionHandlers.length, 1);
    assert.strictEqual(loaded.winstonState.created[0].options.rejectionHandlers.length, 1);
    assert.ok(
      loaded.consoleMessages.some(
        ([level, message]) => level === 'log' && message.includes('日志目录已创建'),
      ),
    );
  });

  test('WSL 路径下应禁用文件日志并打印告警', () => {
    const loaded = loadLoggerModule({
      env: {
        NODE_ENV: 'production',
      },
      argv: ['node', 'scripts/run.js'],
      fakeCwd: '\\\\wsl.localhost\\Ubuntu\\FootballPrediction',
    });

    assert.strictEqual(loaded.winstonState.created[0].options.transports.length, 1);
    assert.ok(
      loaded.consoleMessages.some(
        ([level, message]) => level === 'warn' && message.includes('检测到 WSL 路径'),
      ),
    );
  });
});
