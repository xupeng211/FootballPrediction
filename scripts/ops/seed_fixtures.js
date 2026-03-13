#!/usr/bin/env node
/**
 * V178 赛程播种入口脚本
 * =========================
 *
 * 从 FotMob API 批量获取赛程数据并存入 matches 表
 *
 * 用法:
 *   node seed_fixtures.js                    # 使用配置文件默认值
 *   node seed_fixtures.js --league=47        # 指定联赛
 *   node seed_fixtures.js --season=2024/2025 # 指定赛季
 *   node seed_fixtures.js --all              # 全量收割
 * @module scripts/ops/seed_fixtures
 * @version V178.0.0
 */

'use strict';

const path = require('path');
const { FixtureSeeder, loadLeagueConfig, Logger } = require('../../src/infrastructure/FixtureSeeder');

const log = new Logger('seed_fixtures');

// ============================================================================
// 参数解析
// ============================================================================

/**
 *
 */
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
            if (season.length === 8 && /^\d+$/.test(season)) {
                season = `${season.substring(0, 4)}/${season.substring(4)}`;
            }
            options.season = season;
        }
    }

    return options;
}

// ============================================================================
// 主函数
// ============================================================================

/**
 *
 */
async function main() {
    log.info('========================================');
    log.info('V178 赛程播种器');
    log.info('========================================');

    const options = parseArgs();
    const leagueConfig = loadLeagueConfig();

    // 构建运行时配置
    let customLeagues = leagueConfig.active_leagues;
    let customSeasons = leagueConfig.active_seasons;

    if (!options.all) {
        if (options.league) {
            const leagueInfo = customLeagues.find(l => l.id === options.league);
            if (leagueInfo) {
                customLeagues = [leagueInfo];
                log.info(`目标联赛: ${leagueInfo.name} (ID: ${options.league})`);
            } else {
                log.error(`未知的联赛 ID: ${options.league}`);
                log.info('可用联赛:');
                customLeagues.forEach(l => log.info(`  ${l.id}: ${l.name}`));
                process.exit(1);
            }
        }

        if (options.season) {
            customSeasons = [options.season];
            log.info(`目标赛季: ${options.season}`);
        }
    } else {
        log.info('模式: 全量收割');
        log.info(`联赛: ${customLeagues.map(l => l.name).join(', ')}`);
        log.info(`赛季: ${customSeasons.join(', ')}`);
    }

    log.info('========================================');

    // 创建 Seeder 实例
    const seeder = new FixtureSeeder({
        leagues: customLeagues,
        seasons: customSeasons
    });

    try {
        await seeder.init();
        const stats = await seeder.seedAll();

        log.info('========================================');
        log.success('播种完成!');
        log.info('统计', {
            total: stats.fixtures,
            inserted: stats.inserted,
            updated: stats.updated,
            errors: stats.errors
        });
        log.info('========================================');

        // 非零退出码（如果有错误）
        if (stats.errors > 0) {
            process.exit(2);
        }

    } catch (error) {
        log.error('播种失败', error);
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

module.exports = { main, parseArgs };
