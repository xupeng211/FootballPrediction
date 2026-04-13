#!/usr/bin/env node
/* eslint-disable complexity, max-lines */
/**
 * @file titan_discovery.js - TITAN V6.7 L1 发现引擎入口 (Project Hound)
 * @description 超薄 CLI 入口，支持多联赛自动扫描
 * @version V6.7.6-FINAL-ULTRATHIN
 *
 * 用法:
 *   node scripts/ops/titan_discovery.js [选项]
 *
 * 选项:
 *   --league=ID       指定联赛ID (如 47=EPL)
 *   --all             扫描所有 P0 联赛
 *   --all-leagues     扫描所有已启用联赛
 *   --tier=TIER       扫描指定级别 (P0/P1/P2/P3/P4)
 *   --all-tiers       扫描所有级别
 *   --list            列出所有支持的联赛
 *   --search=关键词   搜索联赛实时坐标
 *   --season=YYYY/YYYY    指定赛季 (如 2024/2025)
 *   --full-sync       绕过 recent 时间窗口，执行全赛季种子注入
 *   --concurrency=N   并发数 (默认: 5)
 *   --lookback=N      历史回看天数 (默认: 30)
 *   --lookahead=N     未来扫描天数 (默认: 7)
 *   --dry-run         试运行模式 (不写入数据库)
 *   --silent          静默模式
 *   --verbose, -v     详细输出模式
 *   --help, -h        显示帮助
 */

'use strict';

const { DiscoveryService } = require('../../src/infrastructure/services/DiscoveryService');
const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');
const { UIHelper } = require('../../src/infrastructure/services/UIHelper');

/**
 * 解析命令行参数
 * @returns {Object} 解析后的选项
 */
function parseArgs(argv = process.argv.slice(2)) {
  const args = argv;
  const options = {
    league: null, all: false, allLeagues: false, tier: null, allTiers: false, list: false,
    search: null, season: null, concurrency: 5, lookback: 30, lookahead: 7,
    dryRun: false, silent: false, verbose: false, fullSync: false
  };

  for (const arg of args) {
    if (arg === '--help' || arg === '-h') { showHelp(); process.exit(0); }
    else if (arg === '--all') options.all = true;
    else if (arg === '--all-leagues') options.allLeagues = true;
    else if (arg === '--list') options.list = true;
    else if (arg === '--all-tiers') options.allTiers = true;
    else if (arg === '--full-sync') options.fullSync = true;
    else if (arg === '--dry-run') options.dryRun = true;
    else if (arg === '--silent') options.silent = true;
    else if (arg === '--verbose' || arg === '-v') options.verbose = true;
    else if (arg.startsWith('--league=')) options.league = parseInt(arg.split('=')[1]);
    else if (arg.startsWith('--tier=')) options.tier = arg.split('=')[1].toUpperCase();
    else if (arg.startsWith('--season=')) options.season = arg.split('=')[1];
    else if (arg.startsWith('--search=')) options.search = arg.split('=')[1];
    else if (arg.startsWith('--concurrency=')) options.concurrency = parseInt(arg.split('=')[1]);
    else if (arg.startsWith('--lookback=')) options.lookback = parseInt(arg.split('=')[1]);
    else if (arg.startsWith('--lookahead=')) options.lookahead = parseInt(arg.split('=')[1]);
  }

  // 默认行为: 如果没有指定操作，扫描所有 P0
  if (!options.league && !options.all && !options.allLeagues && !options.list && !options.tier && !options.allTiers && !options.search) {
    options.all = true;
  }

  return options;
}

/**
 * 显示帮助信息
 */
function showHelp() {
  console.log(`
🐕 TITAN DISCOVERY V6.7 - Project Hound

用法:
  node scripts/ops/titan_discovery.js [选项]

选项:
  --league=ID       指定联赛ID (如 47=EPL, 87=La Liga)
  --all             扫描所有 P0 联赛 (默认)
  --all-leagues     扫描所有已启用联赛
  --tier=TIER       扫描指定级别 (P0/P1/P2/P3/P4)
  --all-tiers       扫描所有级别
  --list            列出所有支持的联赛
  --search=关键词   搜索联赛实时坐标 (如 "J1", "中超")
  --season=YYYY/YYYY    指定赛季 (如 2024/2025)
  --full-sync       绕过 recent 时间窗口，执行全赛季种子注入
  --concurrency=N   并发扫描数 (默认: 5)
  --lookback=N      历史回看天数 (默认: 30)
  --lookahead=N     未来扫描天数 (默认: 7)
  --dry-run         试运行模式 (不写入数据库)
  --silent          静默模式
  --verbose, -v     详细输出模式
  --help, -h        显示帮助

示例:
  node scripts/ops/titan_discovery.js --list
  node scripts/ops/titan_discovery.js --search="J1"
  node scripts/ops/titan_discovery.js --league=47
  node scripts/ops/titan_discovery.js --all
  node scripts/ops/titan_discovery.js --all-leagues --full-sync
  node scripts/ops/titan_discovery.js --tier=P1
`);
}

/**
 * 主函数
 */
async function main() {
  const options = parseArgs();
  const configManager = new L1ConfigManager();

  // 设置环境变量
  if (options.silent) process.env.SILENT_MODE = 'true';

  // --list 模式: 显示联赛列表
  if (options.list) {
    const uiHelper = new UIHelper({ silent: false });
    uiHelper.printLeagueList(configManager.getActiveLeagues());
    process.exit(0);
  }

  // 创建服务实例
  const service = new DiscoveryService({
    configManager,
    concurrency: options.concurrency,
    lookbackDays: options.lookback,
    lookaheadDays: options.lookahead,
    fullSync: options.fullSync,
    silent: options.silent,
    verbose: options.verbose
  });

  // --search 模式: 搜索联赛
  if (options.search) {
    try {
      const results = await service.search(options.search);
      const uiHelper = new UIHelper({ silent: false });
      uiHelper.printSearchResults(results);
    } catch (e) {
      console.error(`\n❌ 搜索失败: ${e.message}`);
      process.exit(1);
    } finally {
      await service.close();
    }
    process.exit(0);
  }

  // 试运行模式警告
  if (options.dryRun) {
    console.log('\n⚠️  DRY-RUN 模式: 不会写入数据库\n');
  }

  // 确定扫描目标
  let targetLeagues = [];

  if (options.league) {
    const league = configManager.getLeagueById(options.league);
    if (!league) { console.error(`\n❌ 联赛 ID ${options.league} 未找到`); process.exit(1); }
    targetLeagues = [league];
  } else if (options.allLeagues) {
    targetLeagues = configManager.getActiveLeagues();
    console.log(`\n🌍 扫描所有已启用联赛: ${targetLeagues.length} 个联赛`);
  } else if (options.tier) {
    targetLeagues = configManager.getActiveLeagues({ tier: options.tier });
    console.log(`\n🎯 扫描 ${options.tier} 级别: ${targetLeagues.length} 个联赛`);
  } else if (options.allTiers) {
    targetLeagues = configManager.getActiveLeagues();
    console.log(`\n🌍 扫描所有级别: ${targetLeagues.length} 个联赛`);
  } else if (options.all) {
    targetLeagues = configManager.getActiveLeagues({ tier: 'P0' });
    console.log(`\n⭐ 扫描 P0 核心联赛: ${targetLeagues.length} 个联赛`);
  }

  // 执行扫描
  try {
    const uiHelper = new UIHelper({ silent: options.silent });
    uiHelper.printBanner();

    const results = [];
    if (options.league) {
      const result = await service.discover({
        leagueId: options.league,
        season: options.season,
        allLeagues: false,
        fullSync: options.fullSync
      });
      results.push(result);
    } else if (options.allLeagues || options.allTiers) {
      const result = await service.discover({
        season: options.season,
        allLeagues: true,
        fullSync: options.fullSync
      });
      results.push(result);
    } else if (options.all) {
      const result = await service.discover({
        season: options.season,
        allLeagues: false,
        fullSync: options.fullSync
      });
      results.push(result);
    } else {
      for (const league of targetLeagues) {
        console.log(`\n🔍 扫描: ${league.name} [${league.country}]`);
        const result = await service.discover({
          leagueId: league.id,
          season: options.season,
          allLeagues: false,
          fullSync: options.fullSync
        });
        results.push(result);
      }
    }

    // 汇总统计
    const totals = results.reduce((acc, r) => ({
      total: acc.total + (r.total || 0),
      inserted: acc.inserted + (r.inserted || 0),
      updated: acc.updated + (r.updated || 0),
      failed: acc.failed + (r.failed || 0)
    }), { total: 0, inserted: 0, updated: 0, failed: 0 });

    // 打印汇总报告
    console.log('\n╔══════════════════════════════════════════════════════════════════╗');
    console.log('║  📊 全局扫描汇总                                                 ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║  ✅ 新增: ${totals.inserted.toString().padStart(5)} 场                                               ║`);
    console.log(`║  🔄 更新: ${totals.updated.toString().padStart(5)} 场                                               ║`);
    console.log(`║  ❌ 失败: ${totals.failed.toString().padStart(5)} 场                                               ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝\n');

    if (options.dryRun) {
      console.log('⚠️  DRY-RUN 完成: 以上数据未实际写入\n');
    }

  } catch (error) {
    console.error(`\n❌ 扫描失败: ${error.message}`);
    process.exit(1);
  } finally {
    await service.close();
  }
}

if (require.main === module) {
  main().then(() => {
    process.exit(0);
  }).catch((error) => {
    console.error('\n❌ 程序执行失败:', error.message);
    process.exit(1);
  });
}

module.exports = {
  parseArgs,
  main
};
