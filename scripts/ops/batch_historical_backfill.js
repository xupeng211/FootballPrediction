#!/usr/bin/env node

/**
 * 横向大扩军 - 批量历史数据回溯脚本
 *
 * 功能：
 * 1. 批量导入 CSV 历史数据到 matches 和 bookmaker_odds_history
 * 2. 触发 ELO 重算
 * 3. 触发 L3 特征生成
 * 4. FotMob 合规模式：极其保守的低频拉取缺失数据
 *
 * 使用方式：
 * node scripts/ops/batch_historical_backfill.js --season 2022/2023 --leagues 47,54,53,55,87
 * node scripts/ops/batch_historical_backfill.js --season 2022/2023 --leagues 48,77,88,56,60 --fotmob-compliance
 */

const path = require('path');
const fs = require('fs').promises;
const { execSync } = require('child_process');

// 配置
const CONFIG = {
  csvDataDir: path.join(__dirname, '../../data/historical_csv'),
  fotmobComplianceMode: process.env.FOTMOB_COMPLIANCE_MODE === 'true',
  fotmobDelayMs: 30000, // 30秒延迟，极其保守
  fotmobMaxRetries: 2,
  batchSize: 50,
  dryRun: process.argv.includes('--dry-run'),
};

// 联赛映射表
const LEAGUE_MAP = {
  47: { name: 'Premier League', csvCode: 'E0' },
  54: { name: 'Bundesliga', csvCode: 'D1' },
  53: { name: 'Ligue 1', csvCode: 'F1' },
  55: { name: 'Serie A', csvCode: 'I1' },
  87: { name: 'La Liga', csvCode: 'SP1' },
  48: { name: 'Championship', csvCode: 'E1' },
  77: { name: '2. Bundesliga', csvCode: 'D2' },
  88: { name: 'Segunda División', csvCode: 'SP2' },
  56: { name: 'Serie B', csvCode: 'I2' },
  60: { name: 'Ligue 2', csvCode: 'F2' },
};

// 解析命令行参数
function parseArgs() {
  const args = {
    season: null,
    leagues: [],
    fotmobCompliance: process.argv.includes('--fotmob-compliance'),
  };

  const seasonIdx = process.argv.indexOf('--season');
  if (seasonIdx !== -1 && process.argv[seasonIdx + 1]) {
    args.season = process.argv[seasonIdx + 1];
  }

  const leaguesIdx = process.argv.indexOf('--leagues');
  if (leaguesIdx !== -1 && process.argv[leaguesIdx + 1]) {
    args.leagues = process.argv[leaguesIdx + 1].split(',').map(Number);
  }

  return args;
}

// 获取 CSV 文件路径
function getCsvFilePath(leagueId, season) {
  const league = LEAGUE_MAP[leagueId];
  if (!league) {
    throw new Error(`Unknown league ID: ${leagueId}`);
  }

  const seasonYear = season.split('/')[0].slice(2); // "2022/2023" -> "22"
  const csvFileName = `${league.csvCode}_${seasonYear}${parseInt(seasonYear) + 1}.csv`;
  return path.join(CONFIG.csvDataDir, csvFileName);
}

// 执行 CSV 批量加载
async function loadCsvData(csvFilePath, leagueId) {
  console.log(`\n[CSV 加载] 开始导入: ${csvFilePath}`);

  if (CONFIG.dryRun) {
    console.log('[DRY-RUN] 跳过实际导入');
    return { success: true, matchCount: 0 };
  }

  try {
    const cmd = `node scripts/ops/csv_bulk_loader.js --file "${csvFilePath}" --league ${leagueId}`;
    const output = execSync(cmd, { encoding: 'utf-8', stdio: 'pipe' });

    const matchCountMatch = output.match(/导入成功: (\d+) 场比赛/);
    const matchCount = matchCountMatch ? parseInt(matchCountMatch[1]) : 0;

    console.log(`[CSV 加载] 完成: ${matchCount} 场比赛`);
    return { success: true, matchCount };
  } catch (error) {
    console.error(`[CSV 加载] 失败: ${error.message}`);
    return { success: false, matchCount: 0, error: error.message };
  }
}

// FotMob 合规模式拉取缺失数据
async function fotmobComplianceFetch(leagueId, season) {
  if (!CONFIG.fotmobComplianceMode) {
    console.log('[FotMob] 非合规模式，跳过');
    return { success: true, fetchCount: 0 };
  }

  console.log(`\n[FotMob 合规] 开始极保守拉取: League ${leagueId}, Season ${season}`);
  console.log(`[FotMob 合规] 延迟: ${CONFIG.fotmobDelayMs}ms, 最大重试: ${CONFIG.fotmobMaxRetries}`);

  if (CONFIG.dryRun) {
    console.log('[DRY-RUN] 跳过实际拉取');
    return { success: true, fetchCount: 0 };
  }

  try {
    const cmd = `node scripts/ops/fotmob_historical_backfill.js --league ${leagueId} --season ${season} --compliance --delay ${CONFIG.fotmobDelayMs} --max-retries ${CONFIG.fotmobMaxRetries}`;
    const output = execSync(cmd, { encoding: 'utf-8', stdio: 'pipe', timeout: 600000 }); // 10分钟超时

    const fetchCountMatch = output.match(/拉取成功: (\d+) 场比赛/);
    const fetchCount = fetchCountMatch ? parseInt(fetchCountMatch[1]) : 0;

    console.log(`[FotMob 合规] 完成: ${fetchCount} 场比赛`);
    return { success: true, fetchCount };
  } catch (error) {
    console.error(`[FotMob 合规] 失败: ${error.message}`);
    return { success: false, fetchCount: 0, error: error.message };
  }
}

// 触发 ELO 重算
async function recalculateElo(leagueId, season) {
  console.log(`\n[ELO 重算] 开始: League ${leagueId}, Season ${season}`);

  if (CONFIG.dryRun) {
    console.log('[DRY-RUN] 跳过实际重算');
    return { success: true };
  }

  try {
    const cmd = `python -m src.ml.elo_calculator --league ${leagueId} --season ${season}`;
    execSync(cmd, { encoding: 'utf-8', stdio: 'inherit' });

    console.log('[ELO 重算] 完成');
    return { success: true };
  } catch (error) {
    console.error(`[ELO 重算] 失败: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// 触发 L3 特征生成
async function generateL3Features(leagueId, season) {
  console.log(`\n[L3 特征] 开始生成: League ${leagueId}, Season ${season}`);

  if (CONFIG.dryRun) {
    console.log('[DRY-RUN] 跳过实际生成');
    return { success: true };
  }

  try {
    const cmd = `node scripts/ops/smelt_all.js --league ${leagueId} --season ${season}`;
    execSync(cmd, { encoding: 'utf-8', stdio: 'inherit' });

    console.log('[L3 特征] 完成');
    return { success: true };
  } catch (error) {
    console.error(`[L3 特征] 失败: ${error.message}`);
    return { success: false, error: error.message };
  }
}

// 主流程
async function main() {
  const args = parseArgs();

  if (!args.season || args.leagues.length === 0) {
    console.error('错误: 必须指定 --season 和 --leagues 参数');
    console.error('示例: node scripts/ops/batch_historical_backfill.js --season 2022/2023 --leagues 47,54,53,55,87');
    process.exit(1);
  }

  console.log('═══════════════════════════════════════════════════════════');
  console.log('  横向大扩军 - 批量历史数据回溯');
  console.log('═══════════════════════════════════════════════════════════');
  console.log(`赛季: ${args.season}`);
  console.log(`联赛: ${args.leagues.map(id => LEAGUE_MAP[id]?.name || id).join(', ')}`);
  console.log(`FotMob 合规模式: ${args.fotmobCompliance ? '启用' : '禁用'}`);
  console.log(`Dry-Run 模式: ${CONFIG.dryRun ? '启用' : '禁用'}`);
  console.log('═══════════════════════════════════════════════════════════\n');

  const results = {
    total: args.leagues.length,
    success: 0,
    failed: 0,
    totalMatches: 0,
    details: [],
  };

  for (const leagueId of args.leagues) {
    const leagueName = LEAGUE_MAP[leagueId]?.name || `League ${leagueId}`;
    console.log(`\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);
    console.log(`  处理联赛: ${leagueName} (ID: ${leagueId})`);
    console.log(`━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`);

    const leagueResult = {
      leagueId,
      leagueName,
      season: args.season,
      steps: {},
    };

    try {
      // Step 1: CSV 批量加载
      const csvFilePath = getCsvFilePath(leagueId, args.season);
      const csvResult = await loadCsvData(csvFilePath, leagueId);
      leagueResult.steps.csv = csvResult;
      results.totalMatches += csvResult.matchCount;

      if (!csvResult.success) {
        throw new Error(`CSV 加载失败: ${csvResult.error}`);
      }

      // Step 2: FotMob 合规拉取（如果启用）
      if (args.fotmobCompliance) {
        const fotmobResult = await fotmobComplianceFetch(leagueId, args.season);
        leagueResult.steps.fotmob = fotmobResult;

        if (!fotmobResult.success) {
          console.warn(`[警告] FotMob 拉取失败，继续后续步骤`);
        }
      }

      // Step 3: ELO 重算
      const eloResult = await recalculateElo(leagueId, args.season);
      leagueResult.steps.elo = eloResult;

      if (!eloResult.success) {
        throw new Error(`ELO 重算失败: ${eloResult.error}`);
      }

      // Step 4: L3 特征生成
      const l3Result = await generateL3Features(leagueId, args.season);
      leagueResult.steps.l3 = l3Result;

      if (!l3Result.success) {
        throw new Error(`L3 特征生成失败: ${l3Result.error}`);
      }

      results.success++;
      leagueResult.status = 'success';
      console.log(`\n✅ ${leagueName} 处理完成`);
    } catch (error) {
      results.failed++;
      leagueResult.status = 'failed';
      leagueResult.error = error.message;
      console.error(`\n❌ ${leagueName} 处理失败: ${error.message}`);
    }

    results.details.push(leagueResult);
  }

  // 输出最终报告
  console.log('\n\n═══════════════════════════════════════════════════════════');
  console.log('  批量回溯完成报告');
  console.log('═══════════════════════════════════════════════════════════');
  console.log(`总联赛数: ${results.total}`);
  console.log(`成功: ${results.success}`);
  console.log(`失败: ${results.failed}`);
  console.log(`总导入比赛数: ${results.totalMatches}`);
  console.log('═══════════════════════════════════════════════════════════\n');

  // 输出详细结果到 JSON 文件
  const reportPath = path.join(__dirname, `../../logs/backfill_report_${Date.now()}.json`);
  await fs.writeFile(reportPath, JSON.stringify(results, null, 2));
  console.log(`详细报告已保存: ${reportPath}\n`);

  process.exit(results.failed > 0 ? 1 : 0);
}

main().catch((error) => {
  console.error('致命错误:', error);
  process.exit(1);
});
