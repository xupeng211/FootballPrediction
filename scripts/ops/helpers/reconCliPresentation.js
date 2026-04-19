'use strict';

class ReconCliArgumentError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ReconCliArgumentError';
    this.code = 'ARGUMENT_ERROR';
  }
}

const VALUE_SETTERS = new Map([
  ['--season', (result, value) => {
    result.season = value;
  }],
  ['--league', (result, value) => {
    result.league = value;
  }],
  ['--with-slug', (result, value) => {
    result.additionalSlugs.push(value);
  }],
  ['--limit', (result, value) => {
    result.limit = parseInt(value, 10);
  }],
  ['--concurrency', (result, value) => {
    result.concurrency = parseInt(value, 10);
  }],
  ['--threshold', (result, value) => {
    result.threshold = parseFloat(value);
  }],
  ['--skip-leagues', (result, value) => {
    const skipLeagues = String(value || '')
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);
    result.skipLeagues = [...new Set([...result.skipLeagues, ...skipLeagues])];
  }]
]);

const FLAG_SETTERS = new Map([
  ['-h', (result) => {
    result.help = true;
  }],
  ['--help', (result) => {
    result.help = true;
  }],
  ['--all-leagues', (result) => {
    result.allLeagues = true;
  }],
  ['--all-non-linked', (result) => {
    result.allNonLinked = true;
  }],
  ['--use-proxy', (result) => {
    result.useProxy = true;
  }],
  ['--no-proxy', (result) => {
    result.useProxy = false;
  }],
  ['--date-driven', (result) => {
    result.dateDriven = true;
  }],
  ['--cross-league', (result) => {
    result.crossLeague = true;
  }],
  ['--current-season-only', (result) => {
    result.currentSeasonOnly = true;
  }],
  ['--force-dom-mode', (result) => {
    result.forceDomMode = true;
  }],
  ['--force-json-extract', (result) => {
    result.forceJsonExtract = true;
  }],
  ['--force-pure-protocol', (result) => {
    result.forcePureProtocol = true;
  }],
  ['--mismatch-retry-only', (result) => {
    result.mismatchRetryOnly = true;
  }]
]);

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
    mismatchRetryOnly: false,
    skipLeagues: []
  };

  for (let index = 0; index < args.length; index++) {
    const token = args[index];
    const valueSetter = VALUE_SETTERS.get(token);
    if (valueSetter) {
      valueSetter(result, args[++index]);
      continue;
    }

    const flagSetter = FLAG_SETTERS.get(token);
    if (flagSetter) {
      flagSetter(result);
    }
  }

  if (!result.help && !result.season) {
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
    '  --skip-leagues <A,B,...>     跳过指定联赛（按名称/代码/ID）',
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

function printPerLeagueSummary(output, result) {
  if (!Array.isArray(result.perLeague)) {
    return;
  }

  for (const item of result.perLeague) {
    const leagueStatus = item.pendingTotal > 0 && item.linked === item.pendingTotal
      ? '✅'
      : item.linked > 0
        ? '⚠️'
        : '❌';
    output.log(`║    ${leagueStatus} ${(item.league || 'Unknown').padEnd(16)}: ${String(item.linked || 0).padStart(3)} 链接 / ${String(item.mismatched || 0).padStart(3)} 失配`);
  }
}

function printSingleResultSummary(output, result, isSkippedFutureFinalsResultFn) {
  if (isSkippedFutureFinalsResultFn(result)) {
    output.log(`║  ⏭️ ${(result.league || 'Unknown').padEnd(18)}: 跳过未来正赛 (${String(result.skippedPendingTotal || 0).padStart(3)} 待处理)`);
    return { inserted: 0, pending: 0 };
  }

  if (!result.success) {
    output.log(`║  ❌ ${(result.league || 'Unknown').padEnd(18)}: 错误 - ${result.error}`);
    return { inserted: 0, pending: 0 };
  }

  const inserted = result.inserted || 0;
  const pending = result.pendingTotal || 0;
  const coverage = result.coverage || 0;
  const status = coverage >= 95 ? '✅' : coverage >= 80 ? '⚠️' : '❌';
  output.log(`║  ${status} ${(result.league || 'Unknown').padEnd(18)}: ${String(inserted).padStart(3)} / ${String(pending).padStart(3)} (${coverage.toFixed(1)}%)`);
  printPerLeagueSummary(output, result);
  return { inserted, pending };
}

function printResultsSummary(output, results, isSkippedFutureFinalsResultFn) {
  output.log('\n╔══════════════════════════════════════════════════════════════════╗');
  output.log('║                    📊 侦察任务汇总报告 📊                        ║');
  output.log('╠══════════════════════════════════════════════════════════════════╣');

  let totalInserted = 0;
  let totalPending = 0;
  for (const result of results) {
    const totals = printSingleResultSummary(output, result, isSkippedFutureFinalsResultFn);
    totalInserted += totals.inserted;
    totalPending += totals.pending;
  }

  const totalCoverage = totalPending > 0 ? (totalInserted / totalPending * 100).toFixed(2) : '0.00';
  output.log('╠══════════════════════════════════════════════════════════════════╣');
  output.log(`║  总计: ${totalInserted} / ${totalPending} 场 (${totalCoverage}%)                         ║`);
  output.log('╚══════════════════════════════════════════════════════════════════╝\n');
  return totalCoverage;
}

module.exports = {
  ReconCliArgumentError,
  parseArgs,
  printUsage,
  buildDbPoolConfig,
  printBanner,
  printResultsSummary
};
