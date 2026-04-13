#!/usr/bin/env node
/**
 * @file titan_marathon.js - TITAN V6.6 马拉松收割超薄入口
 * @module scripts/ops/titan_marathon
 * @version V6.6.0
 * @description
 * 超薄 CLI 入口脚本，仅负责:
 * 1. 解析命令行参数
 * 2. 实例化 MarathonService
 * 3. 启动 reconcile 流程
 * 
 * 核心逻辑已迁移至: src/infrastructure/services/MarathonService.js
 */

'use strict';

const { MarathonService } = require('../../src/infrastructure/services/MarathonService');

/**
 * 解析命令行参数
 * @returns {Object} 配置对象
 */
const NUMERIC_FLAG_PARSERS = new Map([
  ['--workers=', { key: 'workers', fallback: 22 }],
  ['--limit=', { key: 'limit', fallback: 10000 }],
  ['--stagger=', { key: 'stagger', fallback: 800 }],
  ['--restart=', { key: 'restart', fallback: 500 }],
  ['--rounds=', { key: 'maxRounds', fallback: 5 }]
]);

function applyNumericArg(args, arg) {
  for (const [prefix, config] of NUMERIC_FLAG_PARSERS.entries()) {
    if (!arg.startsWith(prefix)) {
      continue;
    }

    args[config.key] = parseInt(arg.split('=')[1]) || config.fallback;
    return true;
  }

  return false;
}

function parseArgs() {
  const args = {
    workers: 22,
    limit: 10000,
    stagger: 800,
    restart: 500,
    verbose: false,
    dryRun: false,
    maxRounds: 5
  };

  for (let i = 2; i < process.argv.length; i++) {
    const arg = process.argv[i];
    if (applyNumericArg(args, arg)) {
      continue;
    }

    if (arg === '--verbose' || arg === '-v') {
      args.verbose = true;
    } else if (arg === '--dry-run') {
      args.dryRun = true;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    }
  }

  return args;
}

/**
 * 打印帮助信息
 */
function printHelp() {
  console.log(`
TITAN MARATHON V6.6 - 万场饱和收割引擎

用法:
  node scripts/ops/titan_marathon.js [选项]

选项:
  --workers=N     并发数 (默认: 22)
  --limit=N       最大采集数 (默认: 10000)
  --stagger=N     错峰启动间隔 ms (默认: 800)
  --restart=N     浏览器重启阈值 (默认: 500)
  --rounds=N      最大对齐轮数 (默认: 5)
  --verbose, -v   详细输出
  --dry-run       试运行模式
  --help, -h      显示帮助

示例:
  # 标准万场模式
  node scripts/ops/titan_marathon.js --workers=22 --limit=10000

  # 保守测试模式
  node scripts/ops/titan_marathon.js --workers=5 --limit=100

  # 快速对齐 (最多3轮)
  node scripts/ops/titan_marathon.js --rounds=3
`);
}

/**
 * 主函数
 */
async function main() {
  const args = parseArgs();

  // 试运行模式
  if (args.dryRun) {
    console.log('\n🏃 [DRY RUN] 试运行模式');
    console.log('📊 配置预览:', JSON.stringify(args, null, 2));
    
    const service = new MarathonService(args);
    const pendingCount = await service._getPendingCount();
    console.log(`📊 当前待采集: ${pendingCount} 场`);
    
    await service.cleanup();
    process.exit(0);
  }

  // 创建服务实例
  const service = new MarathonService({
    workers: args.workers,
    staggerMs: args.stagger,
    restartThreshold: args.restart,
    maxRounds: args.maxRounds,
    verbose: args.verbose
  });

  try {
    // 初始化
    await service.init();

    // 执行对齐循环
    const result = await service.reconcile({ limit: args.limit });

    // 输出最终报告
    console.log('');
    console.log('╔══════════════════════════════════════════════════════════════════╗');
    console.log('║  🏁 MARATHON 最终报告                                            ║');
    console.log('╠══════════════════════════════════════════════════════════════════╣');
    console.log(`║  📊 对齐轮数: ${result.rounds} 轮                                            ║`);
    console.log(`║  ✅ 成功: ${result.totalStats.success.toString().padStart(6)} 场 | ❌ 失败: ${result.totalStats.failed.toString().padStart(5)} 场          ║`);
    console.log(`║  📋 剩余缺口: ${result.finalPending.toString().padStart(5)} 场                                        ║`);
    console.log('╚══════════════════════════════════════════════════════════════════╝');

    // 清理资源
    await service.cleanup();

    // 如果有剩余缺口且达到最大轮数，非零退出
    if (result.finalPending > 0) {
      console.log('\n⚠️  存在未采集场次，请检查死信清单');
      process.exit(2);
    }

    console.log('\n✅ [MARATHON] 零缺口对齐完成！');
    process.exit(0);

  } catch (error) {
    console.error('\n❌ [MARATHON] 致命错误:', error.message);
    console.error(error.stack);
    
    try {
      await service.cleanup();
    } catch (e) {
      // 忽略清理错误
    }
    
    process.exit(1);
  }
}

// 启动
main().catch(err => {
  console.error('❌ 未捕获的错误:', err);
  process.exit(1);
});

module.exports = { main, parseArgs };
