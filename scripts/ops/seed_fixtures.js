#!/usr/bin/env node
/**
 * V6.0 严谨版赛程播种入口脚本
 * =========================
 *
 * 融合三道铁门安检逻辑的工业级赛程采集器
 * - 强制参数校验
 * - 数据过滤（leagueId/赛季窗口/占位符）
 * - 批量写入 + 并发处理
 *
 * 用法:
 *   node seed_fixtures.js --season=2024/2025 --league=47  # 推荐：纯净英超24/25
 *   node seed_fixtures.js --all                           # 全量收割（谨慎）
 * @module scripts/ops/seed_fixtures
 * @version V6.0-STRICT
 */

'use strict';

const { FixtureSeeder, loadLeagueConfig, Logger } = require('../../src/infrastructure/FixtureSeeder');
const {
    threeGatesFilter,
    validateLeagueId,
    validateSeasonWindow,
    isPlaceholder,
    validateBasicData,
    ValidationConfig
} = require('../../src/core/validation/MatchValidator');

const log = new Logger('seed_fixtures');

// ============================================================================
// V6.0: 配置通过 MatchValidator 加载
// ============================================================================

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

// ============================================================================
// V6.0: 严格参数解析
// ============================================================================

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
            options.league = parseInt(arg.split('=')[1]);
        } else if (arg.startsWith('--season=')) {
            let season = arg.split('=')[1];
            // 支持 20242025 格式自动转换
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

/**
 * V6.0: 严格参数校验
 */
function validateArgs(options) {
    // 如果是 --all 模式，跳过强制校验
    if (options.all) {
        log.warn('⚠️ 全量收割模式 (--all) 将处理所有配置联赛，可能包含非英超数据');
        return;
    }

    // 强制要求 --season 和 --league 成对出现
    if (!options.season && !options.league) {
        log.error('❌ 参数错误: 必须提供 --season 和 --league（或 --all）');
        log.error('   推荐用法: node seed_fixtures.js --season=2024/2025 --league=47');
        printHelp();
        process.exit(1);
    }

    if (!options.season) {
        log.error('❌ 参数错误: 缺少 --season (例如: 2024/2025)');
        process.exit(1);
    }

    if (!options.league) {
        log.error('❌ 参数错误: 缺少 --league (英超: 47)');
        process.exit(1);
    }

    // 赛季格式校验
    const seasonPattern = /^\d{4}\/\d{4}$/;
    if (!seasonPattern.test(options.season)) {
        log.error(`❌ 参数错误: season 格式错误 "${options.season}"，必须为 YYYY/YYYY 格式`);
        process.exit(1);
    }

    // 检查赛季是否在支持列表中
    const window = STRICT_VALIDATION.SEASON_WINDOWS[options.season];
    if (!window) {
        log.warn(`⚠️ 赛季 ${options.season} 没有预定义的时间窗口，将跳过时间校验`);
    }

    // 联赛限制（当前只支持英超 47）
    if (options.league !== 47) {
        log.warn(`⚠️ 联赛 ID ${options.league} 不是英超(47)，将应用通用过滤规则`);
    }

    log.info('✅ 参数校验通过', { season: options.season, league: options.league });
}

function printHelp() {
    console.log(`
V6.0 严谨版赛程播种器 - 用法说明
=================================

Usage:
  node seed_fixtures.js --season=<SEASON> --league=<ID>  # 推荐：纯净模式
  node seed_fixtures.js --all                            # 全量收割（谨慎）

Required (纯净模式):
  --season=<SEASON>    目标赛季 (格式: YYYY/YYYY, 例如: 2024/2025)
  --league=<ID>        联赛 FotMob ID (英超: 47)

Options:
  --all                全量收割模式（处理所有配置联赛）
  --help               显示帮助

Examples:
  # 拉取 24/25 赛季英超（推荐 - 三道铁门全面防护）
  node seed_fixtures.js --season=2024/2025 --league=47

  # 拉取 23/24 赛季英超
  node seed_fixtures.js --season=2023/2024 --league=47

  # 使用数字格式赛季
  node seed_fixtures.js --season=20242025 --league=47

Security:
  三道铁门: leagueId校验 → 赛季窗口校验 → 占位符剔除
`);
}

// ============================================================================
// 主函数
// ============================================================================

async function main() {
    log.info('========================================');
    log.info('V6.0 严谨版赛程播种器');
    log.info('三道铁门: leagueId → 赛季窗口 → 占位符检测');
    log.info('========================================');

    const options = parseArgs();

    // V6.0: 严格参数校验
    validateArgs(options);

    const leagueConfig = loadLeagueConfig();

    // 构建运行时配置
    let customLeagues = leagueConfig.active_leagues;
    let customSeasons = leagueConfig.active_seasons;

    if (!options.all) {
        if (options.league) {
            const leagueInfo = customLeagues.find(l => l.id === options.league);
            if (leagueInfo) {
                customLeagues = [leagueInfo];
                log.info(`🎯 目标联赛: ${leagueInfo.name} (ID: ${options.league})`);
            } else {
                log.error(`❌ 未知的联赛 ID: ${options.league}`);
                log.info('可用联赛:');
                customLeagues.forEach(l => log.info(`  ${l.id}: ${l.name}`));
                process.exit(1);
            }
        }

        if (options.season) {
            customSeasons = [options.season];
            log.info(`📅 目标赛季: ${options.season}`);
        }

        // 显示时间窗口信息
        const window = STRICT_VALIDATION.SEASON_WINDOWS[options.season];
        if (window) {
            log.info(`⏰ 时间窗口: ${window.start} ~ ${window.end} (±14天缓冲)`);
        }
    } else {
        log.info('🌐 模式: 全量收割');
        log.info(`联赛: ${customLeagues.map(l => l.name).join(', ')}`);
        log.info(`赛季: ${customSeasons.join(', ')}`);
    }

    log.info('========================================');

    // V6.0: 创建 Seeder 实例，启用严格模式（自动使用三道铁门）
    const seeder = new FixtureSeeder({
        leagues: customLeagues,
        seasons: customSeasons,
        strictMode: !options.all  // 非 --all 模式启用严格过滤
    });

    try {
        await seeder.init();
        const stats = await seeder.seedAll();

        log.info('========================================');
        log.success('播种完成!');

        // V6.0: 显示三道铁门统计
        if (!options.all) {
            log.info('🛡️ 三道铁门拦截统计:', {
                wrongLeague: seeder.rejectionStats.wrongLeague || 0,
                outsideWindow: seeder.rejectionStats.outsideWindow || 0,
                placeholder: seeder.rejectionStats.placeholder || 0,
                invalidData: seeder.rejectionStats.invalidData || 0
            });
        }

        log.info('📊 入库统计', {
            total: stats.fixtures,
            inserted: stats.inserted,
            updated: stats.updated,
            errors: stats.errors
        });

        // 英超 380 场校验
        if (options.league === 47 && stats.fixtures !== 380) {
            log.warn(`⚠️ 警告: 实际入库 ${stats.fixtures} 场，英超应有 380 场`);
        }

        log.info('========================================');

        // 非零退出码（如果有错误）
        if (stats.errors > 0) {
            process.exit(2);
        }

    } catch (error) {
        log.error('❌ 播种失败', error);
        process.exit(1);
    } finally {
        await seeder.close();
    }
}

// ============================================================================
// 入口
// ============================================================================

if (require.main === module) {
    main().catch(err => {
        log.error('致命错误', err);
        process.exit(1);
    });
}

module.exports = {
    main,
    parseArgs,
    validateArgs,
    // V6.0: 从 MatchValidator 重新导出供测试使用
    threeGatesFilter,
    validateLeagueId,
    validateSeasonWindow,
    isPlaceholder,
    validateBasicData,
    STRICT_VALIDATION
};
