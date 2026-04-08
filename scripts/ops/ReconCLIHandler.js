'use strict';

class ReconCliArgumentError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ReconCliArgumentError';
    this.code = 'ARGUMENT_ERROR';
  }
}

function parseArgs(argv = process.argv.slice(2)) {
  const args = Array.isArray(argv) ? [...argv] : [];
  const result = {
    help: false,
    season: null,
    league: 'EPL',
    allLeagues: false,
    allNonLinked: false,
    useProxy: false,
    dateDriven: false,
    crossLeague: false,
    additionalSlugs: [],
    limit: null,
    concurrency: 5,
    currentSeasonOnly: false,
    threshold: null,
    forceDomMode: false,
    forceJsonExtract: false,
    forcePureProtocol: false,
    mismatchRetryOnly: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '-h':
      case '--help':
        result.help = true;
        break;
      case '--season':
        result.season = args[++i];
        break;
      case '--league':
        result.league = args[++i];
        break;
      case '--all-leagues':
        result.allLeagues = true;
        break;
      case '--all-non-linked':
        result.allNonLinked = true;
        break;
      case '--use-proxy':
        result.useProxy = true;
        break;
      case '--no-proxy':
        result.useProxy = false;
        break;
      case '--date-driven':
        result.dateDriven = true;
        break;
      case '--cross-league':
        result.crossLeague = true;
        break;
      case '--with-slug':
        result.additionalSlugs.push(args[++i]);
        break;
      case '--limit':
        result.limit = parseInt(args[++i], 10);
        break;
      case '--concurrency':
        result.concurrency = parseInt(args[++i], 10);
        break;
      case '--current-season-only':
        result.currentSeasonOnly = true;
        break;
      case '--threshold':
        result.threshold = parseFloat(args[++i]);
        break;
      case '--force-dom-mode':
        result.forceDomMode = true;
        break;
      case '--force-json-extract':
        result.forceJsonExtract = true;
        break;
      case '--force-pure-protocol':
        result.forcePureProtocol = true;
        break;
      case '--mismatch-retry-only':
        result.mismatchRetryOnly = true;
        break;
    }
  }

  if (result.help) {
    return result;
  }

  if (!result.season) {
    throw new ReconCliArgumentError('❌ 错误: --season 参数是必需的');
  }

  return result;
}

function printUsage(output = console.log) {
  const writer = typeof output === 'function'
    ? output
    : typeof output?.log === 'function'
      ? output.log.bind(output)
      : console.log;

  [
    '用法: node scripts/ops/recon_scanner.js --season 2024-2025 [选项]',
    '  --league <联赛代码|联赛ID>    指定单联赛扫描，默认 EPL',
    '  --all-leagues                扫描全部激活联赛',
    '  --all-non-linked             扫描所有非 RECON_LINKED 比赛',
    '  --limit <N>                  启用 Recon Matrix 并限制待处理场次',
    '  --concurrency <N>            设置并发数',
    '  --threshold <0-1>            覆盖默认置信度阈值',
    '  --force-dom-mode             强制浏览器 DOM 抽取，禁用 pure protocol 优先',
    '  --force-json-extract         强制 JSON 提取模式',
    '  --force-pure-protocol        强制 pure protocol 模式',
    '  --mismatch-retry-only        仅重扫 RECON_MISMATCH',
    '  --current-season-only        仅处理当前赛季窗口',
    '  -h, --help                   显示帮助'
  ].forEach((line) => writer(line));
}

function buildDbPoolConfig() {
  return {
    host: process.env.DB_HOST || 'host.docker.internal',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    database: process.env.DB_NAME || 'football_db',
    user: process.env.DB_USER || 'football_user',
    password: process.env.DB_PASSWORD || 'football_pass'
  };
}

function printBanner(output, args) {
  output.log('\n╔══════════════════════════════════════════════════════════════════╗');
  output.log('║     🔍 TITAN V11.0 RECON SCANNER - Clean Sweep Edition 🔍       ║');
  output.log('╠══════════════════════════════════════════════════════════════════╣');
  output.log('║     版本: V11.0-CLEAN-SWEEP                                      ║');
  output.log(`║     赛季: ${args.season}                                    ║`);
  output.log('║     架构: Navigator + Engine + Decryptor                         ║');
  output.log('║     特性: 动态 season 透传 | 协议解密 | Recon Matrix            ║');
  output.log('╚══════════════════════════════════════════════════════════════════╝\n');
}

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

function printResultsSummary(output, results, isSkippedFutureFinalsResultFn) {
  output.log('\n╔══════════════════════════════════════════════════════════════════╗');
  output.log('║                    📊 侦察任务汇总报告 📊                        ║');
  output.log('╠══════════════════════════════════════════════════════════════════╣');

  let totalInserted = 0;
  let totalPending = 0;

  for (const result of results) {
    if (isSkippedFutureFinalsResultFn(result)) {
      output.log(`║  ⏭️ ${(result.league || 'Unknown').padEnd(18)}: 跳过未来正赛 (${String(result.skippedPendingTotal || 0).padStart(3)} 待处理)`);
      continue;
    }

    if (result.success) {
      totalInserted += result.inserted || 0;
      totalPending += result.pendingTotal || 0;
      const coverage = result.coverage || 0;
      const status = coverage >= 95 ? '✅' : coverage >= 80 ? '⚠️' : '❌';
      output.log(`║  ${status} ${(result.league || 'Unknown').padEnd(18)}: ${String(result.inserted || 0).padStart(3)} / ${String(result.pendingTotal || 0).padStart(3)} (${coverage.toFixed(1)}%)`);
      if (Array.isArray(result.perLeague)) {
        for (const item of result.perLeague) {
          const leagueStatus = item.pendingTotal > 0 && item.linked === item.pendingTotal
            ? '✅'
            : item.linked > 0
              ? '⚠️'
              : '❌';
          output.log(`║    ${leagueStatus} ${(item.league || 'Unknown').padEnd(16)}: ${String(item.linked || 0).padStart(3)} 链接 / ${String(item.mismatched || 0).padStart(3)} 失配`);
        }
      }
    } else {
      output.log(`║  ❌ ${(result.league || 'Unknown').padEnd(18)}: 错误 - ${result.error}`);
    }
  }

  const totalCoverage = totalPending > 0 ? (totalInserted / totalPending * 100).toFixed(2) : '0.00';
  output.log('╠══════════════════════════════════════════════════════════════════╣');
  output.log(`║  总计: ${totalInserted} / ${totalPending} 场 (${totalCoverage}%)                         ║`);
  output.log('╚══════════════════════════════════════════════════════════════════╝\n');
  return totalCoverage;
}

async function main(argv = process.argv.slice(2), dependencies = {}) {
  const output = dependencies.console || console;
  const parseArgsFn = dependencies.parseArgsFn || parseArgs;
  const createPool = dependencies.createPool;
  const createRepository = dependencies.createRepository;
  const createScanner = dependencies.createScanner;
  const buildDbPoolConfigFn = dependencies.buildDbPoolConfigFn || buildDbPoolConfig;
  const computeExitCodeFn = dependencies.computeExitCodeFn;
  const isSkippedFutureFinalsResultFn = dependencies.isSkippedFutureFinalsResultFn || (() => false);
  const signalEmitter = dependencies.signalEmitter || process;

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
  let dbPool = null;
  let repository = null;
  let scanner = null;
  let shutdownRequested = false;
  let resolveShutdown;
  const shutdownSignalPromise = new Promise((resolve) => {
    resolveShutdown = resolve;
  });

  printBanner(output, args);

  const runCleanup = createCleanupRunner(async () => {
    await cleanupRuntime({ scanner, repository, dbPool, output });
  });

  const unregisterSignalHandlers = registerSignalHandlers(signalEmitter, async (signal) => {
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
    const workPromise = (async () => {
      dbPool = createPool(buildDbPoolConfigFn());
      repository = createRepository({ dbPool });
      scanner = createScanner({
        repository,
        proxyRotator: args.useProxy ? undefined : null,
        currentSeasonOnly: args.currentSeasonOnly,
        allNonLinked: args.allNonLinked,
        forceDomMode: args.forceDomMode
      });

      await scanner.initialize();
      if (Number.isFinite(args.threshold)) {
        scanner.engine.confidenceThreshold = args.threshold;
      }

      const activeLeagues = scanner.configManager.getActiveLeagues();
      const selectedLeague = scanner.configManager.getLeagueByCode(args.league)
        || scanner.configManager.getLeagueById(Number(args.league));
      const leagues = args.allLeagues ? activeLeagues : [selectedLeague].filter(Boolean);

      if (leagues.length === 0 || !leagues[0]) {
        output.error(`❌ 错误: 找不到联赛配置: ${args.league}`);
        output.error('可用联赛:', activeLeagues.map((league) => `${league.code}(${league.id})`).join(', '));
        return 1;
      }

      const useReconMatrix = Number.isInteger(args.limit) && args.limit > 0;
      const results = [];

      if (useReconMatrix) {
        const requiresSharedNavigator = (
          args.forcePureProtocol !== true
          && typeof scanner.engine?.navigatorFactory !== 'function'
        );
        if (requiresSharedNavigator) {
          await scanner.ensureNavigator({
            launchBrowser: true
          });
        }
        const result = await scanner.engine.runReconMatrix({
          season: args.season,
          leagueIds: leagues.map((league) => Number(league.id)),
          concurrency: Number.isInteger(args.concurrency) && args.concurrency > 0 ? args.concurrency : 5,
          limit: args.limit,
          confidenceThreshold: Number.isFinite(args.threshold) ? args.threshold : scanner.engine.confidenceThreshold,
          currentSeasonOnly: args.currentSeasonOnly,
          forceDomMode: args.forceDomMode,
          forceJsonExtract: args.forceJsonExtract,
          forcePureProtocol: args.forcePureProtocol,
          mismatchRetryOnly: args.mismatchRetryOnly,
          allNonLinked: args.allNonLinked
        });
        results.push({
          success: result.success,
          league: useReconMatrix && args.allLeagues ? 'Recon Matrix' : (leagues[0]?.name || 'Recon Matrix'),
          inserted: result.linked || 0,
          mismatched: result.mismatched || 0,
          pendingTotal: result.totalPending || 0,
          coverage: result.totalPending > 0 ? (result.linked / result.totalPending * 100) : 0,
          perLeague: result.perLeague || [],
          errors: result.errors || [],
          error: Array.isArray(result.errors) && result.errors.length > 0
            ? result.errors.map((item) => `${item.league}: ${item.error}`).join(' | ')
            : undefined
        });
      } else {
        const isolatePerLeague = args.allLeagues && leagues.length > 1;
        if (isolatePerLeague) {
          await scanner.close();
          scanner = null;
        }

        for (const league of leagues) {
          if (isolatePerLeague) {
            scanner = createScanner({
              repository,
              proxyRotator: args.useProxy ? undefined : null,
              currentSeasonOnly: args.currentSeasonOnly,
              allNonLinked: args.allNonLinked,
              forceDomMode: args.forceDomMode
            });
            await scanner.initialize();
          }

          results.push(await scanner.scan(args.season, league, {
            dateDriven: args.dateDriven,
            crossLeague: args.crossLeague,
            additionalSlugs: args.additionalSlugs,
            forceDomMode: args.forceDomMode
          }));

          if (isolatePerLeague) {
            await scanner.close();
            scanner = null;
          }
        }
      }

      const totalCoverage = printResultsSummary(output, results, isSkippedFutureFinalsResultFn);
      return computeExitCodeFn(results, totalCoverage);
    })();

    const guardedWorkPromise = workPromise.catch((error) => {
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
