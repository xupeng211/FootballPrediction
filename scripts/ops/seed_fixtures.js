#!/usr/bin/env node
/**
 * @file seed_fixtures.js
 * @description 配置驱动的 L1 播种入口，统一走 DiscoveryService + FixtureRepository.persist()
 */

'use strict';

const { DiscoveryService } = require('../../src/infrastructure/services/DiscoveryService');
const { L1ConfigManager } = require('../../src/infrastructure/services/L1ConfigManager');
const {
  threeGatesFilter,
  validateLeagueId,
  validateSeasonWindow,
  isPlaceholder,
  validateBasicData,
  ValidationConfig
} = require('../../src/core/validation/MatchValidator');

const STRICT_VALIDATION = {
  get SEASON_WINDOWS() {
    return {
      '2024/2025': ValidationConfig.getSeasonWindow('2024/2025'),
      '2023/2024': ValidationConfig.getSeasonWindow('2023/2024'),
      '2025/2026': ValidationConfig.getSeasonWindow('2025/2026')
    };
  },
  get PLACEHOLDER_KEYWORDS() {
    return ValidationConfig.getPlaceholderKeywords();
  },
  get DAILY_MATCH_THRESHOLD() {
    return ValidationConfig.getDailyThreshold();
  },
  get BUFFER_DAYS() {
    return ValidationConfig.getBufferDays();
  }
};

const log = {
  info: (...args) => console.log(...args),
  warn: (...args) => console.warn(...args),
  error: (...args) => console.error(...args),
  success: (...args) => console.log(...args)
};

function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    league: null,
    season: null,
    all: false
  };

  for (const arg of args) {
    if (arg === '--all') {
      options.all = true;
    } else if (arg.startsWith('--league=')) {
      options.league = parseInt(arg.split('=')[1], 10);
    } else if (arg.startsWith('--season=')) {
      let season = arg.split('=')[1];
      if (season.length === 8 && /^\d+$/.test(season)) {
        season = `${season.substring(0, 4)}/${season.substring(4)}`;
      }
      options.season = season;
    } else if (arg === '--help') {
      printHelp();
      process.exit(0);
    }
  }

  return options;
}

function validateArgs(options) {
  if (options.all) {
    return;
  }

  if (!options.season && !options.league) {
    log.error('❌ 参数错误: 必须提供 --season 和 --league（或 --all）');
    log.error('   推荐用法: node seed_fixtures.js --season=2024/2025 --league=47');
    process.exit(1);
  }

  if (!options.season) {
    log.error('❌ 参数错误: 缺少 --season');
    process.exit(1);
  }

  if (!options.league) {
    log.error('❌ 参数错误: 缺少 --league');
    process.exit(1);
  }
}

function printHelp() {
  console.log(`
L1 配置驱动播种入口

用法:
  node scripts/ops/seed_fixtures.js --season=<SEASON> --league=<ID>
  node scripts/ops/seed_fixtures.js --all

示例:
  node scripts/ops/seed_fixtures.js --season=2025/2026 --league=54
  node scripts/ops/seed_fixtures.js --season=20242025 --league=47
  node scripts/ops/seed_fixtures.js --all
`);
}

async function main() {
  const options = parseArgs();
  validateArgs(options);

  const configManager = new L1ConfigManager();
  const service = new DiscoveryService({
    configManager,
    silent: false,
    lookbackDays: 400,
    lookaheadDays: 400
  });

  try {
    let result;

    if (options.all) {
      log.info('🌍 执行全联赛 L1 播种');
      result = await service.discover({
        season: options.season || configManager.getDefaultSeason(),
        allLeagues: true
      });
    } else {
      const league = configManager.getLeagueById(options.league);
      if (!league) {
        throw new Error(`联赛 ID ${options.league} 未在 L1 配置中激活`);
      }

      log.info(`🎯 执行 L1 播种: ${league.name} (${league.id}) / ${options.season}`);
      result = await service.discover({
        leagueId: options.league,
        season: options.season,
        allLeagues: false
      });
    }

    log.success('✅ L1 播种完成');
    log.info('📊 入库统计', result);
    return result;
  } catch (error) {
    log.error(`❌ L1 播种失败: ${error.message}`);
    throw error;
  } finally {
    await service.close();
  }
}

if (require.main === module) {
  main().catch(() => {
    process.exit(1);
  });
}

module.exports = {
  main,
  parseArgs,
  validateArgs,
  threeGatesFilter,
  validateLeagueId,
  validateSeasonWindow,
  isPlaceholder,
  validateBasicData,
  STRICT_VALIDATION
};
