'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');

const { ReconScanner, main } = require('../../scripts/ops/recon_scanner');

function createLeagueConfigManager() {
  const league = { id: 47, code: 'EPL', name: 'Premier League', country: 'england', slug: 'premier-league' };
  return {
    getActiveLeagues() {
      return [league];
    },
    getLeagueByCode(code) {
      return code === 'EPL' ? league : null;
    },
    getLeagueById(id) {
      return Number(id) === 47 ? league : null;
    }
  };
}

test('ReconScanner main 在 Recon Matrix 抛错时仍必须释放 scanner、guardian 与 dbPool', async () => {
  let scannerCloseCalls = 0;
  let guardianStopCalls = 0;
  let poolEndCalls = 0;

  const dbPool = {
    async end() {
      poolEndCalls++;
    }
  };

  const repository = {
    dbPool,
    logger: { info() {}, warn() {}, error() {} },
    async init() {},
    async close() {
      await dbPool.end();
    }
  };

  const guardian = {
    async start() {},
    async stop() {
      guardianStopCalls++;
    }
  };

  const scanner = new ReconScanner({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    guardian,
    repository,
    configManager: createLeagueConfigManager(),
    engine: {
      async runReconMatrix() {
        throw new Error('recon_matrix_boom');
      }
    },
    proxyRotator: null
  });

  const originalClose = scanner.close.bind(scanner);
  scanner.close = async function closeWithProbe() {
    scannerCloseCalls++;
    return originalClose();
  };

  await assert.rejects(
    () => main(['--season', '2025-2026', '--league', 'EPL', '--limit', '1'], {
      console,
      createPool: () => dbPool,
      createRepository: () => repository,
      createScanner: () => scanner
    }),
    /recon_matrix_boom/
  );

  assert.equal(scannerCloseCalls, 1);
  assert.equal(guardianStopCalls, 1);
  assert.equal(poolEndCalls, 1);
});

test('ReconScanner main 收到 SIGINT 时必须触发 cleanupRuntime，并关闭 browser', async () => {
  let browserCloseCalls = 0;
  let guardianStopCalls = 0;
  let poolEndCalls = 0;
  let runReconMatrixStarted;

  const signalEmitter = new EventEmitter();
  const runStarted = new Promise((resolve) => {
    runReconMatrixStarted = resolve;
  });

  const dbPool = {
    async end() {
      poolEndCalls++;
    }
  };

  const repository = {
    dbPool,
    logger: { info() {}, warn() {}, error() {} },
    async init() {},
    async close() {
      await dbPool.end();
    }
  };

  const guardian = {
    async start() {},
    async stop() {
      guardianStopCalls++;
    }
  };

  const scanner = new ReconScanner({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    guardian,
    repository,
    configManager: createLeagueConfigManager(),
    engine: {
      navigator: null,
      async runReconMatrix() {
        runReconMatrixStarted();
        return new Promise(() => {});
      }
    },
    proxyRotator: null
  });

  scanner.ensureNavigator = async () => {
    const navigator = {
      async close() {
        browserCloseCalls++;
      },
      async ensureBrowserHealthy() {},
      isHealthy() {
        return true;
      }
    };

    scanner.resources = [{ type: 'navigator', instance: navigator }];
    scanner.engine.navigator = navigator;
    return navigator;
  };

  const exitCodePromise = main(['--season', '2025-2026', '--league', 'EPL', '--limit', '1'], {
    console: { log() {}, warn() {}, error() {} },
    createPool: () => dbPool,
    createRepository: () => repository,
    createScanner: () => scanner,
    signalEmitter
  });

  await runStarted;
  signalEmitter.emit('SIGINT');

  const exitCode = await exitCodePromise;

  assert.equal(exitCode, 130);
  assert.equal(browserCloseCalls, 1);
  assert.equal(guardianStopCalls, 1);
  assert.equal(poolEndCalls, 1);
});

test('ReconScanner main 在 scanner.initialize 抛错时不应触发 undefined.close，且必须回收已创建资源', async () => {
  let scannerCloseCalls = 0;
  let guardianStopCalls = 0;
  let poolEndCalls = 0;

  const dbPool = {
    async end() {
      poolEndCalls++;
    }
  };

  const repository = {
    dbPool,
    logger: { info() {}, warn() {}, error() {} },
    async init() {},
    async close() {
      await dbPool.end();
    }
  };

  const guardian = {
    async start() {},
    async stop() {
      guardianStopCalls++;
    }
  };

  const scanner = new ReconScanner({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    guardian,
    repository,
    configManager: createLeagueConfigManager(),
    engine: {
      async runReconMatrix() {
        return { success: true, linked: 0, mismatched: 0, totalPending: 0, perLeague: [], errors: [] };
      }
    },
    proxyRotator: null
  });

  scanner.initialize = async () => {
    throw new Error('initialize_boom');
  };

  const originalClose = scanner.close.bind(scanner);
  scanner.close = async function closeWithProbe() {
    scannerCloseCalls++;
    return originalClose();
  };

  await assert.rejects(
    () => main(['--season', '2025-2026', '--league', 'EPL', '--limit', '1'], {
      console,
      createPool: () => dbPool,
      createRepository: () => repository,
      createScanner: () => scanner
    }),
    /initialize_boom/
  );

  assert.equal(scannerCloseCalls, 1);
  assert.equal(guardianStopCalls, 1);
  assert.equal(poolEndCalls, 1);
});

test('ReconScanner.initialize 在启用健康检查时必须注册 database readiness', async () => {
  let registeredRepository = null;
  let repositoryInitCalls = 0;

  const repository = {
    logger: { info() {}, warn() {}, error() {} },
    async init() {
      repositoryInitCalls++;
    }
  };

  const scanner = new ReconScanner({
    logger: { info() {}, warn() {}, error() {}, debug() {} },
    guardian: { async start() {}, async stop() {} },
    repository,
    healthServer: {
      registerDatabaseCheck(targetRepository) {
        registeredRepository = targetRepository;
      }
    },
    configManager: createLeagueConfigManager(),
    parser: { logger: { info() {}, warn() {}, error() {}, debug() {} } },
    engine: { logger: { info() {}, warn() {}, error() {}, debug() {} } },
    stitcher: { logger: { info() {}, warn() {}, error() {}, debug() {} } },
    proxyRotator: null
  });

  await scanner.initialize();

  assert.equal(repositoryInitCalls, 1);
  assert.equal(registeredRepository, repository);
});
