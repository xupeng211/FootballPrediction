'use strict';

const {
  ReconCliArgumentError,
  parseArgs,
  printUsage,
  buildDbPoolConfig,
  printBanner,
  printResultsSummary
} = require('./helpers/reconCliPresentation');

async function cleanupRuntime({ scanner, repository, dbPool, output = console }) {
  let repositoryClosed = false;

  if (scanner && typeof scanner.close === 'function') {
    try {
      await scanner.close();
    } catch (error) {
      output.error('[cleanup] scanner.close 失败:', error.message);
    }
  }

  if (repository && typeof repository.close === 'function') {
    try {
      await repository.close();
      repositoryClosed = true;
    } catch (error) {
      output.error('[cleanup] repository.close 失败:', error.message);
    }
  }

  if (!repositoryClosed && dbPool && typeof dbPool.end === 'function') {
    try {
      await dbPool.end();
    } catch (error) {
      output.error('[cleanup] dbPool.end 失败:', error.message);
    }
  }
}

function createCleanupRunner(cleanupFn) {
  let cleanupPromise = null;
  return async () => {
    if (!cleanupPromise) {
      cleanupPromise = Promise.resolve().then(() => cleanupFn());
    }
    return cleanupPromise;
  };
}

function registerSignalHandlers(signalEmitter, onSignal) {
  if (!signalEmitter || typeof onSignal !== 'function') {
    return () => {};
  }

  const subscriptions = [];
  const bindMethod = typeof signalEmitter.once === 'function' ? 'once' : 'on';
  for (const signal of ['SIGINT', 'SIGTERM']) {
    const handler = () => {
      void onSignal(signal);
    };
    signalEmitter[bindMethod](signal, handler);
    subscriptions.push([signal, handler]);
  }

  return () => {
    for (const [signal, handler] of subscriptions) {
      if (typeof signalEmitter.off === 'function') {
        signalEmitter.off(signal, handler);
      } else if (typeof signalEmitter.removeListener === 'function') {
        signalEmitter.removeListener(signal, handler);
      }
    }
  };
}

function signalToExitCode(signal) {
  if (signal === 'SIGINT') {
    return 130;
  }
  if (signal === 'SIGTERM') {
    return 143;
  }
  return 1;
}

function resolveLeagues(output, configManager, args) {
  const activeLeagues = configManager.getActiveLeagues();
  const selectedLeague = configManager.getLeagueByCode(args.league)
    || configManager.getLeagueById(Number(args.league));
  const leagues = args.allLeagues ? activeLeagues : [selectedLeague].filter(Boolean);

  if (leagues.length === 0 || !leagues[0]) {
    output.error(`❌ 错误: 找不到联赛配置: ${args.league}`);
    output.error('可用联赛:', activeLeagues.map((league) => `${league.code}(${league.id})`).join(', '));
    return null;
  }

  return leagues;
}

function createScannerOptions(args) {
  return {
    proxyRotator: args.useProxy ? undefined : null,
    currentSeasonOnly: args.currentSeasonOnly,
    allNonLinked: args.allNonLinked,
    forceDomMode: args.forceDomMode,
    enforceDistributedLocking: true
  };
}

function buildReconMatrixRunOptions(scanner, args, leagues) {
  return {
    season: args.season,
    leagueIds: leagues.map((league) => Number(league.id)),
    concurrency: Number.isInteger(args.concurrency) && args.concurrency > 0 ? args.concurrency : 5,
    leagueConcurrency: Number.isInteger(args.concurrency) && args.concurrency > 0 ? args.concurrency : 5,
    limit: args.limit,
    confidenceThreshold: Number.isFinite(args.threshold) ? args.threshold : scanner.engine.confidenceThreshold,
    currentSeasonOnly: args.currentSeasonOnly,
    forceDomMode: args.forceDomMode,
    forceJsonExtract: args.forceJsonExtract,
    forcePureProtocol: args.forcePureProtocol,
    mismatchRetryOnly: args.mismatchRetryOnly,
    allNonLinked: args.allNonLinked
  };
}

function formatReconMatrixResult(args, leagues, result) {
  return {
    success: result.success,
    league: args.allLeagues ? 'Recon Matrix' : (leagues[0]?.name || 'Recon Matrix'),
    inserted: result.linked || 0,
    mismatched: result.mismatched || 0,
    pendingTotal: result.totalPending || 0,
    coverage: result.totalPending > 0 ? (result.linked / result.totalPending * 100) : 0,
    perLeague: result.perLeague || [],
    errors: result.errors || [],
    error: Array.isArray(result.errors) && result.errors.length > 0
      ? result.errors.map((item) => `${item.league}: ${item.error}`).join(' | ')
      : undefined
  };
}

async function runReconMatrixMode(scanner, args, leagues) {
  const requiresSharedNavigator = args.forcePureProtocol !== true
    && typeof scanner.engine?.navigatorFactory !== 'function';
  if (requiresSharedNavigator) {
    await scanner.ensureNavigator({ launchBrowser: true });
  }

  const result = await scanner.engine.runReconMatrix(buildReconMatrixRunOptions(scanner, args, leagues));
  return [formatReconMatrixResult(args, leagues, result)];
}

async function runPerLeagueMode(runtime, args, leagues) {
  const results = [];
  const isolatePerLeague = args.allLeagues && leagues.length > 1;

  if (isolatePerLeague) {
    await runtime.scanner.close();
    runtime.scanner = null;
  }

  for (const league of leagues) {
    if (isolatePerLeague) {
      runtime.scanner = runtime.createScanner({
        repository: runtime.repository,
        ...createScannerOptions(args)
      });
      await runtime.scanner.initialize();
    }

    results.push(await runtime.scanner.scan(args.season, league, {
      dateDriven: args.dateDriven,
      crossLeague: args.crossLeague,
      additionalSlugs: args.additionalSlugs,
      forceDomMode: args.forceDomMode
    }));

    if (isolatePerLeague) {
      await runtime.scanner.close();
      runtime.scanner = null;
    }
  }

  return results;
}

async function executeScannerWork(args, runtime) {
  runtime.dbPool = runtime.createPool(runtime.buildDbPoolConfigFn());
  runtime.repository = runtime.createRepository({ dbPool: runtime.dbPool });
  runtime.scanner = runtime.createScanner({
    repository: runtime.repository,
    ...createScannerOptions(args)
  });

  await runtime.scanner.initialize();
  if (Number.isFinite(args.threshold)) {
    runtime.scanner.engine.confidenceThreshold = args.threshold;
  }

  const leagues = resolveLeagues(runtime.output, runtime.scanner.configManager, args);
  if (!leagues) {
    return 1;
  }

  const results = Number.isInteger(args.limit) && args.limit > 0
    ? await runReconMatrixMode(runtime.scanner, args, leagues)
    : await runPerLeagueMode(runtime, args, leagues);
  const totalCoverage = printResultsSummary(runtime.output, results, runtime.isSkippedFutureFinalsResultFn);
  return runtime.computeExitCodeFn(results, totalCoverage);
}

async function main(argv = process.argv.slice(2), dependencies = {}) {
  const output = dependencies.console || console;
  const parseArgsFn = dependencies.parseArgsFn || parseArgs;
  const runtime = {
    output,
    createPool: dependencies.createPool,
    createRepository: dependencies.createRepository,
    createScanner: dependencies.createScanner,
    buildDbPoolConfigFn: dependencies.buildDbPoolConfigFn || buildDbPoolConfig,
    computeExitCodeFn: dependencies.computeExitCodeFn,
    isSkippedFutureFinalsResultFn: dependencies.isSkippedFutureFinalsResultFn || (() => false),
    signalEmitter: dependencies.signalEmitter || process,
    dbPool: null,
    repository: null,
    scanner: null
  };

  let args;
  try {
    args = parseArgsFn(argv);
  } catch (error) {
    if (error?.code === 'ARGUMENT_ERROR') {
      if (typeof output.error === 'function') {
        output.error(error.message);
      }
      printUsage(output);
      return 1;
    }
    throw error;
  }

  if (args.help) {
    printUsage(output);
    return 0;
  }

  let shutdownRequested = false;
  let resolveShutdown;
  const shutdownSignalPromise = new Promise((resolve) => {
    resolveShutdown = resolve;
  });

  printBanner(output, args);

  const runCleanup = createCleanupRunner(async () => {
    await cleanupRuntime({
      scanner: runtime.scanner,
      repository: runtime.repository,
      dbPool: runtime.dbPool,
      output
    });
  });

  const unregisterSignalHandlers = registerSignalHandlers(runtime.signalEmitter, async (signal) => {
    if (shutdownRequested) {
      return;
    }

    shutdownRequested = true;
    if (typeof output.warn === 'function') {
      output.warn(`[shutdown] 收到 ${signal}，开始清理 Recon 运行时资源`);
    }
    await runCleanup();
    resolveShutdown({ interrupted: true, signal });
  });

  try {
    const guardedWorkPromise = executeScannerWork(args, runtime).catch((error) => {
      if (shutdownRequested) {
        return signalToExitCode('SIGTERM');
      }
      throw error;
    });
    const raceResult = await Promise.race([guardedWorkPromise, shutdownSignalPromise]);
    if (raceResult && typeof raceResult === 'object' && raceResult.interrupted) {
      return signalToExitCode(raceResult.signal);
    }

    return raceResult;
  } finally {
    unregisterSignalHandlers();
    await runCleanup();
  }
}

class ReconCLIHandler {
  constructor(dependencies = {}) {
    this.dependencies = dependencies;
  }

  async run(argv = process.argv.slice(2)) {
    return main(argv, this.dependencies);
  }
}

module.exports = {
  ReconCLIHandler,
  ReconCliArgumentError,
  parseArgs,
  buildDbPoolConfig,
  printUsage,
  printBanner,
  cleanupRuntime,
  createCleanupRunner,
  registerSignalHandlers,
  signalToExitCode,
  main
};
